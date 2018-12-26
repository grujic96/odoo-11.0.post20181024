# See LICENSE file for full copyright and licensing details.
import time
import logging
import datetime
import binascii
import ast
import socket
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
import socket
_logger = logging.getLogger(__name__)

def _offset_format_timestamp1(src_tstamp_str, src_format, dst_format,
                              ignore_unparsable_time=True, context=None):
    """
    Convert a source timeStamp string into a destination timeStamp string,
    attempting to apply the correct offset if both the server and local
    timeZone are recognized,or no offset at all if they aren't or if
    tz_offset is false (i.e. assuming they are both in the same TZ).

    @param src_tstamp_str: the STR value containing the timeStamp.
    @param src_format: the format to use when parsing the local timeStamp.
    @param dst_format: the format to use when formatting the resulting
     timeStamp.
    @param server_to_client: specify timeZone offset direction (server=src
                             and client=dest if True, or client=src and
                             server=dest if False)
    @param ignore_unparsable_time: if True, return False if src_tstamp_str
                                   cannot be parsed using src_format or
                                   formatted using dst_format.
    @return: destination formatted timestamp, expressed in the destination
             timezone if possible and if tz_offset is true, or src_tstamp_str
             if timezone offset could not be determined.
    """
    if not src_tstamp_str:
        return False
    res = src_tstamp_str
    if src_format and dst_format:
        try:
            # dt_value needs to be a datetime.datetime object\
            # (so notime.struct_time or mx.DateTime.DateTime here!)
            dt_value = datetime.datetime.strptime(src_tstamp_str, src_format)
            if context.get('tz', False):
                try:
                    import pytz
                    src_tz = pytz.timezone(context['tz'])
                    dst_tz = pytz.timezone('UTC')
                    src_dt = src_tz.localize(dt_value, is_dst=True)
                    dt_value = src_dt.astimezone(dst_tz)
                except Exception:
                    pass
            res = dt_value.strftime(dst_format)
        except Exception:
            # Normal ways to end up here are if strptime or strftime failed
            if not ignore_unparsable_time:
                return False
            pass
    return res


class HotelFloor(models.Model):

    _name = "hotel.floor"
    _description = "Floor"

    name = fields.Char('Floor Name', required=True, index=True)
    sequence = fields.Integer(index=True)


class HotelRoomType(models.Model):

    _name = "hotel.room.type"
    _description = "Room Type"

    name = fields.Char(required=True)
    categ_id = fields.Many2one('hotel.room.type', 'Category')
    child_ids = fields.One2many('hotel.room.type', 'categ_id',
                               'Child Categories')

    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.categ_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.categ_id
            return res
        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symmetric to name_get
            category_names = name.split(' / ')
            parents = list(category_names)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args,
                                             operator='ilike', limit=limit)
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    categories = self.search([('id', 'not in', category_ids)])
                    domain = expression.OR([[('categ_id', 'in',
                                              categories.ids)], domain])
                else:
                    domain = expression.AND([[('categ_id', 'in',
                                               category_ids)], domain])
                for i in range(1, len(category_names)):
                    domain = [[('name', operator,
                                ' / '.join(category_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            categories = self.search(expression.AND([domain, args]),
                                     limit=limit)
        else:
            categories = self.search(args, limit=limit)
        return categories.name_get()


class ProductProduct(models.Model):

    _inherit = "product.product"
    isroom = fields.Boolean('Is Room')
    iscategid = fields.Boolean('Is Categ')
    isservice = fields.Boolean('Is Service')


class HotelRoomAmenitiesType(models.Model):

    _name = 'hotel.room.amenities.type'
    _description = 'amenities Type'

    name = fields.Char(required=True)
    amenity_id = fields.Many2one('hotel.room.amenities.type', 'Category')
    child_ids = fields.One2many('hotel.room.amenities.type', 'amenity_id',
                               'Child Categories')

    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.amenity_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.amenity_id
            return res
        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            category_names = name.split(' / ')
            parents = list(category_names)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args,
                                             operator='ilike', limit=limit)
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    categories = self.search([('id', 'not in', category_ids)])
                    domain = expression.OR([[('amenity_id', 'in',
                                              categories.ids)], domain])
                else:
                    domain = expression.AND([[('amenity_id', 'in',
                                               category_ids)], domain])
                for i in range(1, len(category_names)):
                    domain = [[('name', operator,
                                ' / '.join(category_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            categories = self.search(expression.AND([domain, args]),
                                     limit=limit)
        else:
            categories = self.search(args, limit=limit)
        return categories.name_get()


class HotelRoomAmenities(models.Model):

    _name = 'hotel.room.amenities'
    _description = 'Room amenities'

    product_id = fields.Many2one('product.product', 'Product Category',
                                 required=True, delegate=True,
                                 ondelete='cascade')
    categ_id = fields.Many2one('hotel.room.amenities.type',
                               string='Amenities Category', required=True)
    product_manager = fields.Many2one('res.users', string='Product Manager')


class FolioRoomLine(models.Model):

    _name = 'folio.room.line'
    _description = 'Hotel Room Reservation'
    _rec_name = 'room_id'

    room_id = fields.Many2one('hotel.room', 'Room id')
    check_in = fields.Datetime('Check In Date', required=True)
    check_out = fields.Datetime('Check Out Date', required=True)
    folio_id = fields.Many2one('hotel.folio', string='Folio Number')
    status = fields.Selection(string='state', related='folio_id.state')

#model za istoriju promene statusa



class HotelRoomStatusChangeHistory(models.Model):
    _name = 'hotel.room.status.change'
    _description = 'Hotel Room Status Change'

    room_status_change_id = fields.Many2one('hotel.room', 'Hotel Room id')
    time_of_change = fields.Datetime('Vreme Promene')
    broj_sobe = fields.Integer("Broj sobe")
    #ime_statusa = fields.Selection([('sos_status', 'Sos_status'), ('do_not_disturb', 'Do not disturb')], 'Promenjeni status')


    ime_statusa = fields.Char('Promenjeni status')



#TODO NAPRAVI MODEL PODATAKA ZA ZAPOSLENE,GOSTE

class HotelRecepcionist(models.Model):
    _name = 'hotel.recepcionist'
    recepcionist_id = fields.Many2one('hr.employee', string = 'Recepcionar')

    kartica = fields.Many2one('hotel.room.card')


class HotelGuest(models.Model):
    _name = 'hotel.guest'
    ime = fields.Char('Ime')
    prezime = fields.Char('Prezime')



class HotelRoomCardRelation(models.Model):
    _name = 'hotel.room.card.relation'

    kartica_id = fields.Many2one('hotel.room.card', store=True)
    soba_id = fields.Many2one('hotel.room', store = True)
    date_od = fields.Datetime('Datum kreiranja')
    date_do = fields.Datetime('Vazi do')
    lokacija_kartice = fields.Integer()
    broj_kartice = fields.Char('Broj kartice',related='kartica_id.broj_kartice', readonly = "True")


    def brisanje_po_datumu(self):
        rooms_cards = self.env['hotel.room.card.relation'].search([])
        for room_card in rooms_cards:
            print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            if room_card.date_do != False:
                if room_card.date_do < datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
                    _logger.warning('dosaooooo')
                    rec = self.env['hotel.room']
                    rec.brisanje_kartice(room_card.lokacija_kartice,room_card.soba_id.id)
                    room_card.unlink()
        model = self.env['hotel.room.card']

        model.env['bus.bus'].sendone('auto_refresh', model._name)


class HotelRoomCard(models.Model):
    _name = 'hotel.room.card'
    _description = 'kartica'
    sobe = fields.Many2many('hotel.room', 'hotel_room_card_relation', 'kartica_id', 'soba_id', store=True)
    broj_kartice = fields.Char('Broj Kartice')
    lokacija_kartice = fields.Selection([('gost', 'Gost'), ('sobarica', 'Sobarica'), ('recepcionar','Recepcionar')])

    sobe_lista = fields.Char(store=True)
    provera = fields.Boolean(default=True)




    def get_card_number(self):

            #menja se hidraw file usba
            fp = open('/dev/hidraw2', 'rb')
            i= 1
            while i>0:
                buffer = fp.read(16)
                print(str(buffer))

                print(str(buffer.hex()))
                print(str(buffer.hex()[1]))

                self.broj_kartice = str(buffer[0]-48) + str(buffer[1]-48)+ str(buffer[2]-48)+ str(buffer[3]-48) + str(buffer[4]-48)
                i=0

    @staticmethod
    def dtohex(self,ads):
        asd = hex(ads).split('x')[-1]
        return asd




    def chksum(self, dsa):
        a1 = bytearray(dsa)
        a3 = a1[3]
        for i in range(4, len(a1)):
            a3 = a3 ^ a1[i]
        a2 = bytes(a1)

        a3 = int(a3) & 127
        a4 = str(a3)
        if len(str(a3)) == 1:
            a4 = '0' + str(a3)
        a4 = int(a4)
        a4 = hex(a4)
        a4 = str(a4)
        a4 = a4[2:4]
        print('a4 ====' + a4)
        return a4

    def open_wizard_delete(self, ids, context=None):
        # context = {'search_default_internal_loc': 1, 'search_default_locationgroup':1}
        res_id = self
        view_id = self.env.ref('hotel.view_hotel_room_tree').id
        context = {'id_kartice':self.id}
        dodaj = {'delete': False}
        context.update(dodaj)

        dodaj = {'add': True}
        context.update(dodaj)

        print(self)
        rec = self.env['hotel.room'].search([])
        print(self.sobe)
        print(rec)
        res_id = self.sobe
        print(res_id)
        print(context)

        return {
            'name': _('Dodaj sobu'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'hotel.room',
            'view_id': view_id,
            'target': 'new',
            'context': context,
            'domain':[('id','in',res_id.ids)]

        }

    def open_wizard(self, ids, context=None):
        # context = {'search_default_internal_loc': 1, 'search_default_locationgroup':1}
        res_id = self
        view_id = self.env.ref('hotel.view_hotel_room_tree').id
        ## first delete previous data
        #self.env['stock.location.ptemplate'].search([('custom_template_id', '=', res_id)]).unlink()
        ## then create a new data - by referencing computed field
        #sbl = self.env['product.template'].search([('id', '=', res_id)]).stock_location
        #mro_context = {
        #    'mro_id': self.id,
        #}
        context = {'id_kartice':self.id}
        dodaj = {'delete': True}
        context.update(dodaj)

        dodaj = {'add':False}
        context.update(dodaj)
        print(self)
        rec = self.env['hotel.room'].search([])
        print(self.sobe)
        print(rec)
        res_id = rec - self.sobe
        print(res_id)
        print(context)

        return {
            'name': _('Dodaj sobu'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'hotel.room',
            'view_id': view_id,
            'target': 'new',
            'context': context,
            'domain':[('id','in',res_id.ids)]

        }


        # return {
        #     'name': _('Dodaj sobu'),
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'tree',
        #     'res_model': 'hotel.room',
        #     'view_id': view_id,
        #     'target': 'new',
        #     'context': context,
        #     'domain':[('id','in',res_id.ids)]
        #
        # }




    def broj_kartice_usb(self):
        fp = open('/dev/hidraw2', 'rb')
        i = 1
        while i > 0:
            buffer = fp.read(16)
            print(str(buffer))
            print(hex(buffer[0]))
            i = 0
            return buffer

    def programiranje_kartic(self):
        buffer = self.broj_kartice_usb()
        print('nastavi')

        b0 = hex(buffer[0])
        b0 = b0[2:4]
        b1 = hex(buffer[1])
        b1 = b1[2:4]
        b2 = hex(buffer[2])
        b2 = b2[2:4]
        b3 = hex(buffer[3])
        b3 = b3[2:4]
        b4 = hex(buffer[4])
        b4 = b4[2:4]

        dsa = binascii.unhexlify('DDDDDD01010165000001')
        dsa += binascii.unhexlify(b0)
        dsa += binascii.unhexlify(b1)
        dsa += binascii.unhexlify(b2)
        dsa += binascii.unhexlify(b3)
        dsa += binascii.unhexlify(b4)
        dsa += binascii.unhexlify('0000000000000000000000000000000000000000000000000000000000000000')
        print('stigo1')
        dsa += binascii.unhexlify(self.chksum(dsa))
        print('stigo2')
        dsa += binascii.unhexlify('BB')

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print('stigo')
        #na serverskoj strani salje se na .171

        server_address = ('192.168.1.116', 80)
        sent = sock.sendto(dsa, server_address)
        print('proso')

        # serverside
        # sad = 1
        # while sad > 0:
        #     data, address = sock.recvfrom(512)
        #     print('primljen paket ' + str(data))
        #     print(address)
        #
        #     if (len(data) == 7):
        #         self.provera_kartice()
        #         sad = 0

    def provera_kartice(self):
        dsa = binascii.unhexlify('DDDDDD0102')
        dsa += binascii.unhexlify('01')
        dsa += binascii.unhexlify('0200')
        dsa += binascii.unhexlify('01')

        #Todo dodaj broj sobe i lokaciju kartice dinamicki
        asd = bytes(dsa)
        dsa += binascii.unhexlify('0000000000000000000000000000000000000000000000000000000000000000000000000000')


        dsa += binascii.unhexlify(self.chksum(dsa))
        dsa += binascii.unhexlify('BB')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # na serverskoj strani salje se na .171
        server_address = ('192.168.1.116', 80)
        sent = sock.sendto(dsa, server_address)


    def brisanje_kartice(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 80))
        while True:
            buffer = self.broj_kartice_usb()
            data, address = sock.recvfrom(512)
            print('primljen paket ' + str(data))
            print(address)
            print('duzina' + str(len(data)))
            if (len(data) == 7):
                dsa = binascii.unhexlify('DDDDDD0101')
                dsa += binascii.unhexlify(self.sobe)    #==============================================>                  Todo ovde treba da vrati samo jedan broj sobe koja je izbacena
                dsa += binascii.unhexlify('650000')
                dsa += binascii.unhexlify(self.lokacija_kartice)
                asd = bytes(dsa)
                dsa += binascii.unhexlify('FFFFFFFFFF')
                dsa += binascii.unhexlify('0000000000000000000000000000000000000000000000000000000000000000')
                dsa += binascii.unhexlify(self.chksum(dsa))
                dsa += binascii.unhexlify('BB')
                print(dsa)

                # na serverskoj strani salje se na .171
                server_address = ('192.168.1.116', 80)
                sent = sock.sendto(dsa, server_address)

    def odazivanje(self):
        dsa = binascii.unhexlify('DDDDDD0100')
        asd = bytes(dsa)

        time_now = datetime.datetime.now()
        timee = time_now.timetuple()
        dsa += bytes([timee.tm_mday]) + bytes([timee.tm_mon]) + bytes([18]) + bytes([timee.tm_hour]) + bytes(
            [timee.tm_min]) + bytes([20])

        dsa += binascii.unhexlify('000000000000000000000000000000000000000000000000000000000000000000000000')
        dsa += binascii.unhexlify(self.chksum(dsa))
        dsa += binascii.unhexlify('BB')

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_address = ('192.168.1.171', 80)
        sent = sock.sendto(dsa, server_address)

    def find_card_by_card_number(self):
        cards = self.env['hotel.room.card'].search([])
        print('usosss')
        context =  None
        view_id = self.env.ref('hotel.view_hotel_room_card_tree').id
        res_id = self
       # for rec in cards:
            #if rec.broj_kartice == '0000000':
               # res_id = rec

        return {
            'name': _('Dodaj sobu'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'hotel.room',
            'view_id': view_id,
            'target': 'new',
            'context': context,
            'domain': [('id', 'in', res_id.ids)]
        }


class HotelRoom(models.Model):

    _name = 'hotel.room'
    _description = 'Hotel Room'

    product_id = fields.Many2one('product.product', 'Product_id',
                                 required=True, delegate=True,
                                 ondelete='cascade')
    floor_id = fields.Many2one('hotel.floor', 'Floor No',
                               help='At which floor the room is located.')
    max_adult = fields.Integer()
    max_child = fields.Integer()
    categ_id = fields.Many2one('hotel.room.type', string='Room Category',
                               required=True)

    room_amenities = fields.Many2many('hotel.room.amenities', 'temp_tab',
                                      'room_amenities', 'rcateg_id',
                                      help='List of room amenities. ')
    status = fields.Selection([('available', 'Available'), ('occupied', 'Occupied')], 'Status', default='available')
    capacity = fields.Integer('Capacity', required=True)
    #
    room_line_ids = fields.One2many('folio.room.line', 'room_id',
                                    string='Room Reservation Line')
    product_manager = fields.Many2one('res.users', 'Product Manager')

    #promena statusa
    hotel_room_status_change_id = fields.One2many('hotel.room.status.change' , 'room_status_change_id')
    do_not_disturb = fields.Boolean('Do Not Disturb', default=False)
    sos = fields.Boolean('SOS', default = False)
    sos_status = fields.Boolean('Sos status', default = False)
    poziv_osoblju = fields.Boolean('Poziv osoblju', default=False )
    gost_status = fields.Boolean('Gost', default=False)
    broj_sobe = fields.Integer('Broj Sobe')
    kartice = fields.Many2many('hotel.room.card', 'hotel_room_card_relation', 'soba_id', 'kartica_id', store=True)


    datum_od = fields.Datetime('Vazi od')
    datum_do = fields.Datetime('Vazi do')





    def id_by_broj_sobe(self, broj_sobee):
        asd = self.env['hotel.room'].search([("broj_sobe",'=',broj_sobee)])
        return asd.id

    def do_not_disturb_change(self, on_off):
            self.env['hotel.room.status.change'].create({
                'room_status_change_id': self.id_by_broj_sobe(self.broj_sobe),
                'time_of_change': datetime.datetime.now(),
                'broj_sobe': self.broj_sobe,
                'ime_statusa': 'do_not_disturb ' + on_off
            })

    def poziv_osoblju_change(self, on_off):
            self.env['hotel.room.status.change'].create({
                'room_status_change_id': self.id_by_broj_sobe(self.broj_sobe),
                'time_of_change': datetime.datetime.now(),
                'broj_sobe': self.broj_sobe,
                'ime_statusa': 'Poziv osoblju ' + on_off
            })

    def sos_status_change(self, on_off):
            self.env['hotel.room.status.change'].create({
                'room_status_change_id': self.id_by_broj_sobe(self.broj_sobe),
                'time_of_change': datetime.datetime.now(),
                'broj_sobe': self.broj_sobe,
                'ime_statusa': 'Sos ' + on_off
            })

    def gost_status_change(self, on_off):
            self.env['hotel.room.status.change'].create({
                'room_status_change_id': self.id_by_broj_sobe(self.broj_sobe),
                'time_of_change': datetime.datetime.now(),
                'broj_sobe': self.broj_sobe,
                'ime_statusa': 'Gost u sobi' + on_off
            })

    # @api.onchange('gost_status')
    # def do_not_disturb_change(self):
    #     for rec in self:
    #         self.env['hotel.room.status.change'].create({
    #             'room_status_change_id': rec.id_by_broj_sobe(),
    #             'time_of_change': datetime.datetime.now(),
    #             'broj_sobe': rec.broj_sobe,
    #             'ime_statusa': 'gost_status'
    #
    #         })


    @api.one
    def add_many2many_relation(self):
        if self.datum_do == False:
            raise ValidationError(_('Niste uneli datum vazenja kartice. '))
        _logger.warning('================_context %s', self._context)
        active_id = self._context.get('id_kartice')
        print('activeid')
        print(active_id)
        # id kartice iz url parametra


        _logger.warning('-------------------------------active_id%s', active_id)
        print(self.id)
        _logger.warning('================active_id %s', active_id)

        # _logger.warning('-------------------------------asd%s', asd)
        # for rec in self:
        asd = self.env['hotel.room.card'].browse(active_id)
        print(asd)
        records_with_room_iddd = self.env['hotel.room.card.relation'].search([])
        print(records_with_room_iddd)

        records_with_room_id = []
        for rec in records_with_room_iddd:
            ("soba_id", '=', self.id)
            if rec.soba_id.id == self.id:
                records_with_room_id.append(rec)
        lokacije_kartica = []
        lokacija_kartice_za_upisivanje = None
        if records_with_room_id != None:

            for rec in records_with_room_id:
                lokacije_kartica.append(rec.lokacija_kartice)

        print('lokacije_kartice ' + str(lokacije_kartica))
        if lokacije_kartica == []:
            if asd.lokacija_kartice == 'gost':
                lokacija_kartice_za_upisivanje = 1
            if asd.lokacija_kartice == 'sobarica':
                lokacija_kartice_za_upisivanje = 4
            if asd.lokacija_kartice == 'recepcionar':
                lokacija_kartice_za_upisivanje = 10
        else:

            if asd.lokacija_kartice == 'gost':
                if 1 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 1
                elif 2 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 2
                elif 3 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 3
            if asd.lokacija_kartice == 'sobarica':
                if 4 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 4
                elif 5 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 5
                elif 6 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 6
                elif 7 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 7
                elif 8 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 8
                elif 9 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 9
            if asd.lokacija_kartice == 'recepcionar':
                if 10 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 10
                elif 11 not in lokacije_kartica:
                    lokacija_kartice_za_upisivanje = 11


        if lokacija_kartice_za_upisivanje == None:
            if asd.lokacija_kartice =='gost':
                message ="goste"
            elif asd.lokacija_kartice == 'sobarice':
                message = "sobarice"
            else:
                message = "recepcionare"
            raise ValidationError(_('Izabrana soba vec ima maksimalan broj kartica za ' + message))
        print('lokacija kartice za upisivanje je ' + str(lokacija_kartice_za_upisivanje))
        print(self.id)
        self.programiranje_kartice(active_id, self.id, lokacija_kartice_za_upisivanje)
        # UPISUJE RELACIJU IZMEDJU SOBE I KARTICE U BAZI
        #self.write({'kartice': [(4, active_id, 0)]})
        datum_do = self._context.get('datum_doo')
        datum_od= self._context.get('datum_odd')
        record = self.env['hotel.room.card.relation'].create({'kartica_id' : active_id,'soba_id' : self.id,'date_od' : datum_od,'date_do' : datum_do, 'lokacija_kartice' : lokacija_kartice_za_upisivanje})
        print('doso123321313')
        #record.date_od = self.datum_od
        #record.date_do = self.datum_do
        #self.env.cr.commit()

        self.datum_do = None
        self.datum_od = None
        #SALJE PAKET ZA PROGRAMIRANJE GATEWAY-u






    @api.one
    def delete_record(self):
        active_id = self._context.get('id_kartice')
        print('activeid')
        print(active_id)
        # id kartice iz url parametra
        # id = request.__dict__
        # print(id)
        # id = id.get('params')
        # id = id.get('args')
        # id = str(id)
        # id = id[6:]
        # id = id[:-1]
        # id = ast.literal_eval(id)
        # id = id.get('params')
        # id = id.get('id')
        # print(id)
        print(self.id)

        asd = self.env['hotel.room.card'].browse(active_id)
        print(asd)
        hotel_room_card_relation_record = self.env['hotel.room.card.relation'].search([('kartica_id', '=', active_id),('soba_id','=', self.id)])
        self.brisanje_kartice(hotel_room_card_relation_record.lokacija_kartice,self.id)

        self.write({'kartice': [(3,active_id,0)]})

    @api.multi
    def status_soba(self):
        #self.env['bus.bus'].sendone('auto_refresh', self._name)
        #threading.Timer(10.0, status_sobaa).start()
        i = 0
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 80))
        paket_za_slanje = self.paket_za_odazivanje()
        while True:
            data, address = sock.recvfrom(512)


            rooms = self.env['hotel.room'].search([])
            print(data)
            if len(data) == 7:

                #odazivanje
                if len(paket_za_slanje1) == 49:
                    server_address = ('192.168.1.171', 80)
                    sent = sock.sendto(paket_za_slanje1, server_address)
                    paket_za_slanje1 = 0
                else:
                    server_address = ('192.168.1.171', 80)
                    sent = sock.sendto(paket_za_slanje, server_address)


            #proverava da li mu je stigo paket sa naredbom od pc-ja
            if len(data)==49:
                if(data[4] == 1):
                    paket_za_slanje1 = data


                elif(data[4] == 2):

                    paket_za_slanje1 = data
            # Todo dodaj proveru kad primi bytearray za proveru kartice
            #if len(data)== 12

            if data[3] == 241:
                data[2:]
                for room in rooms:
                    a = room.broj_sobe
                    self.bin = bin(data[a * 4])
                    databits = self.bin
                    s = databits[2:].zfill(8)
                    print(s)
                    if s[0] == '1':
                        if room.sos_status =='false':
                            room.sos_status_change

                            room.sos_status = 'true'

                    else:
                        if room.sos_status == 'true':
                            room.sos_status_change
                            room.sos_status = 'false'

                    if s[1] == '1':
                        if room.poziv_osoblju == 'false':
                            room.poziv_osoblju_change('Ukljucen')
                            room.poziv_osoblju = 'true'
                    else:
                        if room.poziv_osoblju == 'true':
                            room.poziv_osoblju_change('Iskljucen')
                            room.poziv_osoblju = 'false'
                    if s[2] == '1':
                        if room.do_not_disturb is  False:
                            room.do_not_disturb_change('Ukljucen')
                            room.do_not_disturb = True
                            time.sleep(20)

                    else:
                        if room.do_not_disturb:
                            room.do_not_disturb_change('Iskljucen')
                            room.write({'do_not_disturb':False})
                            time.sleep(20)
                    if s[7] == '1':
                        if room.gost_status == 'false':
                            room.gost_status_change('gost je uso u sobu')
                            room.gost_status = 'true'
                    else:
                        if room.gost_status == 'true':
                            room.gost_status_change('gost je izaso iz sobe')
                            room.gost_status = 'false'

            i += 1


           # time.sleep(5)

    def chksum(self, dsa):
        a1 = bytearray(dsa)
        a3 = a1[3]
        for i in range(4, len(a1)):
            a3 = a3 ^ a1[i]
        a2 = bytes(a1)

        a3 = int(a3) & 127
        a4 = str(a3)
        if len(str(a3)) == 1:
            a4 = '0' + str(a3)
        a4 = int(a4)
        a4 = hex(a4)
        a4 = str(a4)
        a4 = a4[2:4]
        if len(str(a4))== 1:
            a4 = '0' + str(a4)
        return a4

    def programiranje_kartice(self,id_kartice,id_sobe, lokacija_kartice):
        print('stigo')
        #buffer = self.broj_kartice_usb()
        buffer = self.env['hotel.room.card'].browse(id_kartice)
        buffer = buffer.broj_kartice
        buffer = str(buffer)
        print('nastavi')

        b0 = str(30 + int(buffer[0]))
        b1 = str(30 + int(buffer[1]))
        b2 = str(30 + int(buffer[2]))
        b3 = str(30 + int(buffer[3]))
        b4 = str(30 + int(buffer[4]))

        lokacija_kartice = str(lokacija_kartice)
        lokacija_kartice = int(lokacija_kartice)
        lokacija_kartice = hex(lokacija_kartice)
        lokacija_kartice = str(lokacija_kartice)
        lokacija_kartice = lokacija_kartice[2:4]
        #
        id_sobe = str(id_sobe)

        if (len(id_sobe)) == 1:
            id_sobe = '0' + id_sobe

        if(len(lokacija_kartice))==1:
            lokacija_kartice = '0' + lokacija_kartice

        dsa = binascii.unhexlify('DDDDDD0101')
        print(str(id_sobe))

        dsa += binascii.unhexlify(id_sobe)
        dsa += binascii.unhexlify('650000')
        print(lokacija_kartice)
        #dsa += binascii.unhexlify(id_kartice)
        dsa += binascii.unhexlify('0a')
        dsa += binascii.unhexlify(b0)
        dsa += binascii.unhexlify(b1)
        dsa += binascii.unhexlify(b2)
        dsa += binascii.unhexlify(b3)
        dsa += binascii.unhexlify(b4)
        dsa += binascii.unhexlify('0000000000000000000000000000000000000000000000000000000000000000')
        dsa += binascii.unhexlify(self.chksum(dsa))
        print('stigo2')
        dsa += binascii.unhexlify('BB')

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print('stigo')
        print(dsa)
        print(len(dsa))
        #na serverskoj strani salje se na .171

        server_address = ('192.168.1.116', 80)
        sent = sock.sendto(dsa, server_address)
        print('proso')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.bind(('0.0.0.0', 80))
        data, address = sock.recvfrom(512)
        if data[0] == 1:
            print('proso uspesno')
        else:
            print('neuspesno')
        sock.close()

    def brisanje_kartice(self,id_kartice,id_sobe):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        id_kartice = str(id_kartice)
        id_kartice = int(id_kartice)
        id_kartice = hex(id_kartice)
        id_kartice = str(id_kartice)
        id_kartice = id_kartice[2:4]
        id_sobe = str(id_sobe)



        if (len(id_sobe)) == 1:
            id_sobe = '0' + id_sobe

        if (len(id_kartice)) == 1:
            id_kartice = '0' + id_kartice
        dsa = binascii.unhexlify('DDDDDD0101')
        dsa += binascii.unhexlify(id_sobe)    #==============================================>                  Todo ovde treba da vrati samo jedan broj sobe koja je izbacena
        dsa += binascii.unhexlify('650000')
        dsa += binascii.unhexlify(id_kartice)
        #dsa += binascii.unhexlify('01')
        asd = bytes(dsa)
        dsa += binascii.unhexlify('ff')
        dsa += binascii.unhexlify('ff')
        dsa += binascii.unhexlify('ff')
        dsa += binascii.unhexlify('ff')
        dsa += binascii.unhexlify('ff')

        dsa += binascii.unhexlify('0000000000000000000000000000000000000000000000000000000000000000')
        dsa += binascii.unhexlify(self.chksum(dsa))
        dsa += binascii.unhexlify('BB')
        print(dsa)

        # na serverskoj strani salje se na .171
        server_address = ('192.168.1.116', 80)
        sent = sock.sendto(dsa, server_address)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.bind(('0.0.0.0', 80))
        data, address = sock.recvfrom(512)
        if data[0] == 1:
            print('proso uspesno')
        else:
            print('neuspesno')
        sock.close()



    def paket_za_odazivanje(self):
        dsa = binascii.unhexlify('DDDDDD0100')
        asd = bytes(dsa)

        time_now = datetime.datetime.now()
        timee = time_now.timetuple()
        dsa += bytes([timee.tm_mday]) + bytes([timee.tm_mon]) + bytes([18]) + bytes([timee.tm_hour]) + bytes(
            [timee.tm_min]) + bytes([20])

        dsa += binascii.unhexlify('000000000000000000000000000000000000000000000000000000000000000000000000')
        dsa += binascii.unhexlify(self.chksum(dsa))
        dsa += binascii.unhexlify('BB')
        return dsa


    @api.one
    def auto_refresh(self):
        model = self.env['hotel.room']
        model.env['bus.bus'].sendone('auto_refresh', model._name)

    @api.multi
    def lista_brojeva_soba(self):
        brojevi = []
        for soba in self:
            brojevi.append(soba.broj_sobe)
        print(brojevi)

        return brojevi




    @api.constrains('capacity')
    def check_capacity(self):
        for room in self:
            if room.capacity <= 0:
                raise ValidationError(_('Room capacity must be more than 0'))



   # @api.onchange('sos')
   # def sos_change(self):
    #    if self.sos is True:
     #       self.sos_status = 'true'
      #  if self.sos is False:
       #     self.sos_status = 'false'

    @api.onchange('isroom')
    def isroom_change(self):
        '''
        Based on isroom, status will be updated.
        ----------------------------------------
        @param self: object pointer
        '''
        if self.isroom is False:
            self.status = 'occupied'
        if self.isroom is True:
            self.status = 'available'

    # @api.multi
    # def write(self, vals):
    #     """
    #     Overrides orm write method.
    #     @param self: The object pointer
    #     @param vals: dictionary of fields value.
    #     """
    #     if 'isroom' in vals and vals['isroom'] is False:
    #         vals.update({'color': 2, 'status': 'occupied'})
    #     if 'isroom'in vals and vals['isroom'] is True:
    #         vals.update({'color': 5, 'status': 'available'})
    #     ret_val = super(HotelRoom, self).write(vals)
    #     return ret_val
    #
    # @api.multi
    # def set_room_status_occupied(self):
    #     """
    #     This method is used to change the state
    #     to occupied of the hotel room.
    #     ---------------------------------------
    #     @param self: object pointer
    #     """
    #     return self.write({'isroom': False, 'color': 2})
    #
    # @api.multi
    # def set_room_status_available(self):
    #     """
    #     This method is used to change the state
    #     to available of the hotel room.
    #     ---------------------------------------
    #     @param self: object pointer
    #     """
    #     return self.write({'isroom': True, 'color': 5})

    # def __init__(self, cr ,ir):
    #
    #     thread = threading.Thread(target=self.run, args=())
    #     thread.daemon = True  # Daemonize thread
    #     thread.start()  # Start the execution
    # @api.multi
    # def run(self):
    #     """ Method that runs forever """
    #     while True:
    #         self.status_soba()
    #         print('doso')
    #         print('proso')
    #         print('Doing something imporant in the background')
    #
    #         time.sleep(self.interval)

# example = HotelRoom()
# time.sleep(7)
# print('Checkpoint')
# time.sleep(7)
# print('Bye')



class HotelFolio(models.Model):

    @api.multi
    def name_get(self):
        res = []
        disp = ''
        for rec in self:
            if rec.order_id:
                disp = str(rec.name)
                res.append((rec.id, disp))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        args += ([('name', operator, name)])
        mids = self.search(args, limit=100)
        return mids.name_get()

    @api.model
    def _needaction_count(self, domain=None):
        """
         Show a count of draft state folio on the menu badge.
         @param self: object pointer
        """
        return self.search_count([('state', '=', 'draft')])

    @api.model
    def _get_checkin_date(self):
        if self._context.get('tz'):
            to_zone = self._context.get('tz')
        else:
            to_zone = 'UTC'
        return _offset_format_timestamp1(time.strftime("%Y-%m-%d 12:00:00"),
                                         DEFAULT_SERVER_DATETIME_FORMAT,
                                         DEFAULT_SERVER_DATETIME_FORMAT,
                                         ignore_unparsable_time=True,
                                         context={'tz': to_zone})

    @api.model
    def _get_checkout_date(self):
        if self._context.get('tz'):
            to_zone = self._context.get('tz')
        else:
            to_zone = 'UTC'
        tm_delta = datetime.timedelta(days=1)
        return datetime.datetime.strptime(_offset_format_timestamp1
                                          (time.strftime("%Y-%m-%d 12:00:00"),
                                           DEFAULT_SERVER_DATETIME_FORMAT,
                                           DEFAULT_SERVER_DATETIME_FORMAT,
                                           ignore_unparsable_time=True,
                                           context={'tz': to_zone}),
                                          '%Y-%m-%d %H:%M:%S') + tm_delta

    @api.multi
    def copy(self, default=None):
        '''
        @param self: object pointer
        @param default: dict of default values to be set
        '''
        return super(HotelFolio, self).copy(default=default)

    _name = 'hotel.folio'
    _description = 'hotel folio new'
    _rec_name = 'order_id'
    _order = 'id'

    name = fields.Char('Folio Number', readonly=True, index=True,
                       default='New')
    order_id = fields.Many2one('sale.order', 'Order', delegate=True,
                               required=True, ondelete='cascade')
    checkin_date = fields.Datetime('Check In', required=True, readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   default=_get_checkin_date)
    checkout_date = fields.Datetime('Check Out', required=True, readonly=True,
                                    states={'draft': [('readonly', False)]},
                                    default=_get_checkout_date)
    room_lines = fields.One2many('hotel.folio.line', 'folio_id',
                                 readonly=True,
                                 states={'draft': [('readonly', False)],
                                         'sent': [('readonly', False)]},
                                 help="Hotel room reservation detail.")
    service_lines = fields.One2many('hotel.service.line', 'folio_id',
                                    readonly=True,
                                    states={'draft': [('readonly', False)],
                                            'sent': [('readonly', False)]},
                                    help="Hotel services details provided to"
                                    "Customer and it will included in "
                                    "the main Invoice.")
    hotel_policy = fields.Selection([('prepaid', 'On Booking'),
                                     ('manual', 'On Check In'),
                                     ('picking', 'On Checkout')],
                                    'Hotel Policy', default='manual',
                                    help="Hotel policy for payment that "
                                    "either the guest has to payment at "
                                    "booking time or check-in "
                                    "check-out time.")
    duration = fields.Float('Duration in Days',
                            help="Number of days which will automatically "
                            "count from the check-in and check-out date. ")
    hotel_invoice_id = fields.Many2one('account.invoice', 'Invoice',
                                       copy=False)
    duration_dummy = fields.Float('Duration Dummy')

    @api.constrains('room_lines')
    def folio_room_lines(self):
        '''
        This method is used to validate the room_lines.
        ------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        folio_rooms = []
        for room in self[0].room_lines:
            if room.product_id.id in folio_rooms:
                raise ValidationError(_('You Cannot Take Same Room Twice'))
            folio_rooms.append(room.product_id.id)

    @api.onchange('checkout_date', 'checkin_date')
    def onchange_dates(self):
        '''
        This method gives the duration between check in and checkout
        if customer will leave only for some hour it would be considers
        as a whole day.If customer will check in checkout for more or equal
        hours, which configured in company as additional hours than it would
        be consider as full days
        --------------------------------------------------------------------
        @param self: object pointer
        @return: Duration and checkout_date
        '''
        configured_addition_hours = 0
        wid = self.warehouse_id
        whouse_com_id = wid or wid.company_id
        if whouse_com_id:
            configured_addition_hours = wid.company_id.additional_hours
        myduration = 0
        chckin = self.checkin_date
        chckout = self.checkout_date
        if chckin and chckout:
            server_dt = DEFAULT_SERVER_DATETIME_FORMAT
            chkin_dt = datetime.datetime.strptime(chckin, server_dt)
            chkout_dt = datetime.datetime.strptime(chckout, server_dt)
            dur = chkout_dt - chkin_dt
            sec_dur = dur.seconds
            if (not dur.days and not sec_dur) or (dur.days and not sec_dur):
                myduration = dur.days
            else:
                myduration = dur.days + 1
            # To calculate additional hours in hotel room as per minutes
            if configured_addition_hours > 0:
                additional_hours = abs((dur.seconds / 60) / 60)
                if additional_hours >= configured_addition_hours:
                    myduration += 1
        self.duration = myduration
        self.duration_dummy = self.duration

    @api.model
    def create(self, vals, check=True):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        @return: new record set for hotel folio.
        """
        if not 'service_lines' and 'folio_id' in vals:
            tmp_room_lines = vals.get('room_lines', [])
            vals['order_policy'] = vals.get('hotel_policy', 'manual')
            vals.update({'room_lines': []})
            folio_id = super(HotelFolio, self).create(vals)
            for line in (tmp_room_lines):
                line[2].update({'folio_id': folio_id})
            vals.update({'room_lines': tmp_room_lines})
            folio_id.write(vals)
        else:
            if not vals:
                vals = {}
            vals['name'] = self.env['ir.sequence'].next_by_code('hotel.folio')
            vals['duration'] = vals.get('duration',
                                        0.0) or vals.get('duration_dummy',
                                                         0.0)
            folio_id = super(HotelFolio, self).create(vals)
            folio_room_line_obj = self.env['folio.room.line']
            h_room_obj = self.env['hotel.room']
            try:
                for rec in folio_id:
                    if not rec.reservation_id:
                        for room_rec in rec.room_lines:
                            prod = room_rec.product_id.name
                            room_obj = h_room_obj.search([('name', '=',
                                                           prod)])
                            room_obj.write({'isroom': False})
                            vals = {'room_id': room_obj.id,
                                    'check_in': rec.checkin_date,
                                    'check_out': rec.checkout_date,
                                    'folio_id': rec.id,
                                    }
                            folio_room_line_obj.create(vals)
            except:
                for rec in folio_id:
                    for room_rec in rec.room_lines:
                        prod = room_rec.product_id.name
                        room_obj = h_room_obj.search([('name', '=', prod)])
                        room_obj.write({'isroom': False})
                        vals = {'room_id': room_obj.id,
                                'check_in': rec.checkin_date,
                                'check_out': rec.checkout_date,
                                'folio_id': rec.id,
                                }
                        folio_room_line_obj.create(vals)
        return folio_id

    @api.multi
    def write(self, vals):
        """
        Overrides orm write method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        """
        product_obj = self.env['product.product']
        h_room_obj = self.env['hotel.room']
        folio_room_line_obj = self.env['folio.room.line']
        room_lst = []
        room_lst1 = []
        for rec in self:
            for res in rec.room_lines:
                room_lst1.append(res.product_id.id)
            if vals and vals.get('duration_dummy', False):
                vals['duration'] = vals.get('duration_dummy', 0.0)
            else:
                vals['duration'] = rec.duration
            for folio_rec in rec.room_lines:
                room_lst.append(folio_rec.product_id.id)
            new_rooms = set(room_lst).difference(set(room_lst1))
            if len(list(new_rooms)) != 0:
                room_list = product_obj.browse(list(new_rooms))
                for rm in room_list:
                    room_obj = h_room_obj.search([('name', '=', rm.name)])
                    room_obj.write({'isroom': False})
                    vals = {'room_id': room_obj.id,
                            'check_in': rec.checkin_date,
                            'check_out': rec.checkout_date,
                            'folio_id': rec.id,
                            }
                    folio_room_line_obj.create(vals)
            if len(list(new_rooms)) == 0:
                room_list_obj = product_obj.browse(room_lst1)
                for rom in room_list_obj:
                    room_obj = h_room_obj.search([('name', '=', rom.name)])
                    room_obj.write({'isroom': False})
                    room_vals = {'room_id': room_obj.id,
                                 'check_in': rec.checkin_date,
                                 'check_out': rec.checkout_date,
                                 'folio_id': rec.id,
                                 }
                    folio_romline_rec = (folio_room_line_obj.search
                                         ([('folio_id', '=', rec.id)]))
                    folio_romline_rec.write(room_vals)
        return super(HotelFolio, self).write(vals)

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        '''
        When you change warehouse it will update the warehouse of
        the hotel folio as well
        ----------------------------------------------------------
        @param self: object pointer
        '''
        return self.order_id._onchange_warehouse_id()

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        '''
        When you change partner_id it will update the partner_invoice_id,
        partner_shipping_id and pricelist_id of the hotel folio as well
        ---------------------------------------------------------------
        @param self: object pointer
        '''
        if self.partner_id:
            partner_rec = self.env['res.partner'].browse(self.partner_id.id)
            order_ids = [folio.order_id.id for folio in self]
            if not order_ids:
                self.partner_invoice_id = partner_rec.id
                self.partner_shipping_id = partner_rec.id
                self.pricelist_id = partner_rec.property_product_pricelist.id
                raise _('Not Any Order For  %s ' % (partner_rec.name))
            else:
                self.partner_invoice_id = partner_rec.id
                self.partner_shipping_id = partner_rec.id
                self.pricelist_id = partner_rec.property_product_pricelist.id

    @api.multi
    def action_done(self):
        self.state = 'done'

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        '''
        @param self: object pointer
        '''
        room_lst = []
        invoice_id = (self.order_id.action_invoice_create(grouped=False,
                                                          final=False))
        for line in self:
            values = {'invoiced': True,
                      'hotel_invoice_id': invoice_id
                      }
            line.write(values)
            for rec in line.room_lines:
                room_lst.append(rec.product_id)
            for room in room_lst:
                room_rec = self.env['hotel.room'].\
                    search([('name', '=', room.name)])
                room_rec.write({'isroom': True})
        return invoice_id

    @api.multi
    def action_invoice_cancel(self):
        '''
        @param self: object pointer
        '''
        if not self.order_id:
            raise UserError(_('Order id is not available'))
        for sale in self:
            for line in sale.order_line:
                line.write({'invoiced': 'invoiced'})
        self.state = 'invoice_except'
        return self.order_id.action_invoice_cancel

    @api.multi
    def action_cancel(self):
        '''
        @param self: object pointer
        '''
        if not self.order_id:
            raise UserError(_('Order id is not available'))
        for sale in self:
            for invoice in sale.invoice_ids:
                invoice.state = 'cancel'
        return self.order_id.action_cancel()

    @api.multi
    def action_confirm(self):
        for order in self.order_id:
            order.state = 'sale'
            if not order.analytic_account_id:
                for line in order.order_line:
                    if line.product_id.invoice_policy == 'cost':
                        order._create_analytic_account()
                        break
        config_parameter_obj = self.env['ir.config_parameter']
        if config_parameter_obj.sudo().get_param('sale.auto_done_setting'):
            self.order_id.action_done()

    @api.multi
    def test_state(self, mode):
        '''
        @param self: object pointer
        @param mode: state of workflow
        '''
        write_done_ids = []
        write_cancel_ids = []
        if write_done_ids:
            test_obj = self.env['sale.order.line'].browse(write_done_ids)
            test_obj.write({'state': 'done'})
        if write_cancel_ids:
            test_obj = self.env['sale.order.line'].browse(write_cancel_ids)
            test_obj.write({'state': 'cancel'})

    @api.multi
    def action_cancel_draft(self):
        '''
        @param self: object pointer
        '''
        if not len(self._ids):
            return False
        query = "select id from sale_order_line \
        where order_id IN %s and state=%s"
        self._cr.execute(query, (tuple(self._ids), 'cancel'))
        cr1 = self._cr
        line_ids = map(lambda x: x[0], cr1.fetchall())
        self.write({'state': 'draft', 'invoice_ids': [], 'shipped': 0})
        sale_line_obj = self.env['sale.order.line'].browse(line_ids)
        sale_line_obj.write({'invoiced': False, 'state': 'draft',
                             'invoice_lines': [(6, 0, [])]})
        return True


class HotelFolioLine(models.Model):

    @api.multi
    def copy(self, default=None):
        '''
        @param self: object pointer
        @param default: dict of default values to be set
        '''
        return super(HotelFolioLine, self).copy(default=default)

    @api.model
    def _get_checkin_date(self):
        if 'checkin' in self._context:
            return self._context['checkin']
        return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    @api.model
    def _get_checkout_date(self):
        if 'checkout' in self._context:
            return self._context['checkout']
        return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    _name = 'hotel.folio.line'
    _description = 'hotel folio1 room line'

    order_line_id = fields.Many2one('sale.order.line', string='Order Line',
                                    required=True, delegate=True,
                                    ondelete='cascade')
    folio_id = fields.Many2one('hotel.folio', string='Folio',
                               ondelete='cascade')
    checkin_date = fields.Datetime('Check In', required=True,
                                   default=_get_checkin_date)
    checkout_date = fields.Datetime('Check Out', required=True,
                                    default=_get_checkout_date)
    is_reserved = fields.Boolean('Is Reserved',
                                 help='True when folio line created from \
                                 Reservation')

    @api.model
    def create(self, vals, check=True):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        @return: new record set for hotel folio line.
        """
        if 'folio_id' in vals:
            folio = self.env["hotel.folio"].browse(vals['folio_id'])
            vals.update({'order_id': folio.order_id.id})
        return super(HotelFolioLine, self).create(vals)

    @api.constrains('checkin_date', 'checkout_date')
    def check_dates(self):
        '''
        This method is used to validate the checkin_date and checkout_date.
        -------------------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        if self.checkin_date >= self.checkout_date:
                raise ValidationError(_('Room line Check In Date Should be \
                less than the Check Out Date!'))
        if self.folio_id.date_order and self.checkin_date:
            if self.checkin_date <= self.folio_id.date_order:
                raise ValidationError(_('Room line check in date should be \
                greater than the current date.'))

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        sale_line_obj = self.env['sale.order.line']
        fr_obj = self.env['folio.room.line']
        for line in self:
            if line.order_line_id:
                sale_unlink_obj = (sale_line_obj.browse
                                   ([line.order_line_id.id]))
                for rec in sale_unlink_obj:
                    room_obj = self.env['hotel.room'
                                        ].search([('name', '=', rec.name)])
                    if room_obj.id:
                        folio_arg = [('folio_id', '=', line.folio_id.id),
                                     ('room_id', '=', room_obj.id)]
                        folio_room_line_myobj = fr_obj.search(folio_arg)
                        if folio_room_line_myobj.id:
                            folio_room_line_myobj.unlink()
                            room_obj.write({'isroom': True,
                                            'status': 'available'})
                sale_unlink_obj.unlink()
        return super(HotelFolioLine, self).unlink()

    @api.onchange('product_id')
    def product_id_change(self):
        '''
 -        @param self: object pointer
 -        '''
        context = dict(self._context)
        if not context:
            context = {}
        if context.get('folio', False):
            if self.product_id and self.folio_id.partner_id:
                self.name = self.product_id.name
                self.price_unit = self.product_id.list_price
                self.product_uom = self.product_id.uom_id
                tax_obj = self.env['account.tax']
                pr = self.product_id
                self.price_unit = tax_obj._fix_tax_included_price(pr.price,
                                                                  pr.taxes_id,
                                                                  self.tax_id)
        else:
            if not self.product_id:
                return {'domain': {'product_uom': []}}
            val = {}
            pr = self.product_id.with_context(
                lang=self.folio_id.partner_id.lang,
                partner=self.folio_id.partner_id.id,
                quantity=val.get('product_uom_qty') or self.product_uom_qty,
                date=self.folio_id.date_order,
                pricelist=self.folio_id.pricelist_id.id,
                uom=self.product_uom.id
            )
            p = pr.with_context(pricelist=self.order_id.pricelist_id.id).price
            if self.folio_id.pricelist_id and self.folio_id.partner_id:
                obj = self.env['account.tax']
                val['price_unit'] = obj._fix_tax_included_price(p,
                                                                pr.taxes_id,
                                                                self.tax_id)

    @api.onchange('checkin_date', 'checkout_date')
    def on_change_checkout(self):
        '''
        When you change checkin_date or checkout_date it will checked it
        and update the qty of hotel folio line
        -----------------------------------------------------------------
        @param self: object pointer
        '''
        configured_addition_hours = 0
        fwhouse_id = self.folio_id.warehouse_id
        fwc_id = fwhouse_id or fwhouse_id.company_id
        if fwc_id:
            configured_addition_hours = fwhouse_id.company_id.additional_hours
        myduration = 0
        if not self.checkin_date:
            self.checkin_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if not self.checkout_date:
            self.checkout_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        chckin = self.checkin_date
        chckout = self.checkout_date
        if chckin and chckout:
            server_dt = DEFAULT_SERVER_DATETIME_FORMAT
            chkin_dt = datetime.datetime.strptime(chckin, server_dt)
            chkout_dt = datetime.datetime.strptime(chckout, server_dt)
            dur = chkout_dt - chkin_dt
            sec_dur = dur.seconds
            if (not dur.days and not sec_dur) or (dur.days and not sec_dur):
                myduration = dur.days
            else:
                myduration = dur.days + 1
#            To calculate additional hours in hotel room as per minutes
            if configured_addition_hours > 0:
                additional_hours = abs((dur.seconds / 60) / 60)
                if additional_hours >= configured_addition_hours:
                    myduration += 1
        self.product_uom_qty = myduration
        hotel_room_obj = self.env['hotel.room']
        hotel_room_ids = hotel_room_obj.search([])
        avail_prod_ids = []
        for room in hotel_room_ids:
            assigned = False
            for rm_line in room.room_line_ids:
                if rm_line.status != 'cancel':
                    if(self.checkin_date <= rm_line.check_in <=
                       self.checkout_date) or (self.checkin_date <=
                                               rm_line.check_out <=
                                               self.checkout_date):
                        assigned = True
                    elif (rm_line.check_in <= self.checkin_date <=
                          rm_line.check_out) or (rm_line.check_in <=
                                                 self.checkout_date <=
                                                 rm_line.check_out):
                        assigned = True
            if not assigned:
                avail_prod_ids.append(room.product_id.id)
        domain = {'product_id': [('id', 'in', avail_prod_ids)]}
        return {'domain': domain}

    @api.multi
    def button_confirm(self):
        '''
        @param self: object pointer
        '''
        for folio in self:
            line = folio.order_line_id
            line.button_confirm()
        return True

    @api.multi
    def button_done(self):
        '''
        @param self: object pointer
        '''
        lines = [folio_line.order_line_id for folio_line in self]
        lines.button_done()
        self.state = 'done'
        return True

    @api.multi
    def copy_data(self, default=None):
        '''
        @param self: object pointer
        @param default: dict of default values to be set
        '''
        line_id = self.order_line_id.id
        sale_line_obj = self.env['sale.order.line'].browse(line_id)
        return sale_line_obj.copy_data(default=default)


class HotelServiceLine(models.Model):

    @api.multi
    def copy(self, default=None):
        '''
        @param self: object pointer
        @param default: dict of default values to be set
        '''
        return super(HotelServiceLine, self).copy(default=default)

    @api.model
    def _service_checkin_date(self):
        if 'checkin' in self._context:
            return self._context['checkin']
        return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    @api.model
    def _service_checkout_date(self):
        if 'checkout' in self._context:
            return self._context['checkout']
        return time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    _name = 'hotel.service.line'
    _description = 'hotel Service line'

    service_line_id = fields.Many2one('sale.order.line', 'Service Line',
                                      required=True, delegate=True,
                                      ondelete='cascade')
    folio_id = fields.Many2one('hotel.folio', 'Folio', ondelete='cascade')
    ser_checkin_date = fields.Datetime('From Date', required=True,
                                       default=_service_checkin_date)
    ser_checkout_date = fields.Datetime('To Date', required=True,
                                        default=_service_checkout_date)

    @api.model
    def create(self, vals, check=True):
        """
        Overrides orm create method.
        @param self: The object pointer
        @param vals: dictionary of fields value.
        @return: new record set for hotel service line.
        """
        if 'folio_id' in vals:
            folio = self.env['hotel.folio'].browse(vals['folio_id'])
            vals.update({'order_id': folio.order_id.id})
        return super(HotelServiceLine, self).create(vals)

    @api.multi
    def unlink(self):
        """
        Overrides orm unlink method.
        @param self: The object pointer
        @return: True/False.
        """
        s_line_obj = self.env['sale.order.line']
        for line in self:
            if line.service_line_id:
                sale_unlink_obj = s_line_obj.browse([line.service_line_id.id])
                sale_unlink_obj.unlink()
        return super(HotelServiceLine, self).unlink()

    @api.onchange('product_id')
    def product_id_change(self):
        '''
        @param self: object pointer
        '''
        if self.product_id and self.folio_id.partner_id:
            self.name = self.product_id.name
            self.price_unit = self.product_id.list_price
            self.product_uom = self.product_id.uom_id
            tax_obj = self.env['account.tax']
            prod = self.product_id
            self.price_unit = tax_obj._fix_tax_included_price(prod.price,
                                                              prod.taxes_id,
                                                              self.tax_id)

    @api.onchange('ser_checkin_date', 'ser_checkout_date')
    def on_change_checkout(self):
        '''
        When you change checkin_date or checkout_date it will checked it
        and update the qty of hotel service line
        -----------------------------------------------------------------
        @param self: object pointer
        '''
        if not self.ser_checkin_date:
            time_a = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            self.ser_checkin_date = time_a
        if not self.ser_checkout_date:
            self.ser_checkout_date = time_a
        if self.ser_checkout_date < self.ser_checkin_date:
            raise _('Checkout must be greater or equal checkin date')
        if self.ser_checkin_date and self.ser_checkout_date:
            date_a = time.strptime(self.ser_checkout_date,
                                   DEFAULT_SERVER_DATETIME_FORMAT)[:5]
            date_b = time.strptime(self.ser_checkin_date,
                                   DEFAULT_SERVER_DATETIME_FORMAT)[:5]
            diffDate = datetime.datetime(*date_a) - datetime.datetime(*date_b)
            qty = diffDate.days + 1
            self.product_uom_qty = qty

    @api.multi
    def button_confirm(self):
        '''
        @param self: object pointer
        '''
        for folio in self:
            line = folio.service_line_id
            x = line.button_confirm()
        return x

    @api.multi
    def button_done(self):
        '''
        @param self: object pointer
        '''
        for folio in self:
            line = folio.service_line_id
            x = line.button_done()
        return x

    @api.multi
    def copy_data(self, default=None):
        '''
        @param self: object pointer
        @param default: dict of default values to be set
        '''
        sale_line_obj = self.env['sale.order.line'
                                 ].browse(self.service_line_id.id)
        return sale_line_obj.copy_data(default=default)


class HotelServiceType(models.Model):

    _name = "hotel.service.type"
    _description = "Service Type"

    name = fields.Char('Service Name', size=64, required=True)
    service_id = fields.Many2one('hotel.service.type', 'Service Category')
    child_ids = fields.One2many('hotel.service.type', 'service_id',
                               'Child Categories')

    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.service_id.name, ...] """
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.service_id
            return res
        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            # Be sure name_search is symetric to name_get
            category_names = name.split(' / ')
            parents = list(category_names)
            child = parents.pop()
            domain = [('name', operator, child)]
            if parents:
                names_ids = self.name_search(' / '.join(parents), args=args,
                                             operator='ilike', limit=limit)
                category_ids = [name_id[0] for name_id in names_ids]
                if operator in expression.NEGATIVE_TERM_OPERATORS:
                    categories = self.search([('id', 'not in', category_ids)])
                    domain = expression.OR([[('service_id', 'in',
                                              categories.ids)], domain])
                else:
                    domain = expression.AND([[('service_id', 'in',
                                               category_ids)], domain])
                for i in range(1, len(category_names)):
                    domain = [[('name', operator,
                                ' / '.join(category_names[-1 - i:]))], domain]
                    if operator in expression.NEGATIVE_TERM_OPERATORS:
                        domain = expression.AND(domain)
                    else:
                        domain = expression.OR(domain)
            categories = self.search(expression.AND([domain, args]),
                                     limit=limit)
        else:
            categories = self.search(args, limit=limit)
        return categories.name_get()


class HotelServices(models.Model):

    _name = 'hotel.services'
    _description = 'Hotel Services and its charges'

    product_id = fields.Many2one('product.product', 'Service_id',
                                 required=True, ondelete='cascade',
                                 delegate=True)
    categ_id = fields.Many2one('hotel.service.type', string='Service Category',
                               required=True)
    product_manager = fields.Many2one('res.users', string='Product Manager')


class ResCompany(models.Model):

    _inherit = 'res.company'

    additional_hours = fields.Integer('Additional Hours',
                                      help="Provide the min hours value for \
                                      check in, checkout days, whatever the \
                                      hours will be provided here based on \
                                      that extra days will be calculated.")


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    @api.model
    def create(self, vals):
        res = super(AccountInvoice, self).create(vals)
        if self._context.get('folio_id'):
            folio = self.env['hotel.folio'].browse(self._context['folio_id'])
            folio.write({'hotel_invoice_id': res.id,
                         'invoice_status': 'invoiced'})
        return res
class RoomStatus(models.Model):
    _name = 'room.status'

    do_not_disturb = fields.Boolean('Do Not disturb')
    sos_status = fields.Selection([('true', 'Ukljucen'), ('false', 'Iskljucen')], 'Sos Status', default='false')
    poziv_osoblju = fields.Selection([('true', 'gost je pozvao osoblje'), ('false', '')])
    gost_status = fields.Selection([('true', 'gost je u sobi'), ('false', 'soba je prazna')])
    broj_sobe = fields.Integer('Broj Sobe')