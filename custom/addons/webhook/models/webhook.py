# -*- coding: utf-8 -*-
# Copyright 2016 Vauxoo - https://www.vauxoo.com/
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.http import request
import traceback
import logging
_logger = logging.getLogger(__name__)
from odoo import api, exceptions, fields, models, tools
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import _
import json
import requests



_logger = logging.getLogger(__name__)

try:
    import ipaddress
except ImportError as err:
    _logger.debug(err)


class WebhookAddress(models.Model):
    _name = 'webhook.address'

    name = fields.Char(
        'IP or Network Address',
        required=True,
        help='IP or network address of your consumer webhook:\n'
        'ip address e.g.: 10.10.0.8\n'
        'network address e.g. of: 10.10.0.8/24',
    )
    webhook_id = fields.Many2one(
        'webhook', 'Webhook', required=True, ondelete='cascade')


class Webhook(models.Model):
    _name = 'webhook'

    name = fields.Char(
        'Consumer name',
        required=True,
        help='Name of your consumer webhook. '
             'This name will be used in named of event methods')
    address_ids = fields.One2many(
        'webhook.address', 'webhook_id', 'IP or Network Address',
        required=True,
        help='This address will be filter to know who is '
             'consumer webhook')
    python_code_get_event = fields.Text(
        'Get event',
        required=True,
        help='Python code to get event from request data.\n'
             'You have object.env.request variable with full '
             'webhook request.',
        default='# You can use object.env.request variable '
                'to get full data of webhook request.\n'
                '# Example:\n#request.httprequest.'
                'headers.get("X-Github-Event")',
    )
    python_code_get_ip = fields.Text(
        'Get IP',
        required=True,
        help='Python code to get remote IP address '
             'from request data.\n'
             'You have object.env.request variable with full '
             'webhook request.',
        default='# You can use object.env.request variable '
                'to get full data of webhook request.\n'
                '# Example:\n'
                '#object.env.request.httprequest.remote_addr'
                '\nrequest.httprequest.remote_addr',

    )
    active = fields.Boolean(default=True)

    @api.multi
    def process_python_code(self, python_code, request=None):
        """
        Execute a python code with eval.
        :param string python_code: Python code to process
        :param object request: Request object with data of json
                               and http request
        :return: Result of process python code.
        """
        self.ensure_one()
        res = None
        eval_dict = {
            'user': self.env.user,
            'object': self,
            'request': request,
            # copy context to prevent side-effects of eval
            'context': dict(self.env.context),
        }
        try:
            res = safe_eval(python_code, eval_dict)
        except BaseException:
            error = tools.ustr(traceback.format_exc())
            _logger.debug(
                'python_code "%s" with dict [%s] error [%s]',
                python_code, eval_dict, error)
        if isinstance(res, str):
            res = tools.ustr(res)
        return res

    @api.model
    def search_with_request(self, request):
        """
        Method to search of all webhook
        and return only one that match with remote address
        and range of address.
        :param object request: Request object with data of json
                               and http request
        :return: object of webhook found or
                 if not found then return False
        """
        for webhook in self.search([]):
            remote_address = webhook.process_python_code(
                webhook.python_code_get_ip, request)
            if not remote_address:
                continue
            if webhook.is_address_range(remote_address):
                return webhook
        return False

    @api.multi
    def is_address_range(self, remote_address):
        """
        Check if a remote IP address is in range of one
        IP or network address of current object data.
        :param string remote_address: Remote IP address
        :return: if remote address match then return True
                 else then return False
        """
        self.ensure_one()
        for address in self.address_ids:
            ipn = ipaddress.ip_network(u'' + address.name)
            hosts = [host.exploded for host in ipn.hosts()]
            hosts.append(address.name)
            if remote_address in hosts:
                return True
        return False

    @api.model
    def get_event_methods(self, event_method_base):
        """
        List all methods of current object that start with base name.
        e.g. if exists methods called 'x1', 'x2'
        and other ones called 'y1', 'y2'
        if you have event_method_base='x'
        Then will return ['x1', 'x2']
        :param string event_method_base: Name of method event base
        returns: List of methods with that start wtih method base
        """
        # TODO: Filter just callable attributes
        return sorted(
            attr for attr in dir(self) if attr.startswith(
                event_method_base)
        )
    def run_github_gollum1(self):
        pass

    @api.model
    def get_ping_events(self):
        """
        List all name of event type ping.
        This event is a dummy event just to
        know if a provider is working.
        :return: List with names of ping events
        """
        return ['ping']

    @api.multi
    def run_webhook(self, request):
        """
        Run methods to process a webhook event.
        Get all methods with base name
        'run_CONSUMER_EVENT*'
        Invoke all methods found.
        :param object request: Request object with data of json
                               and http request
        :return: True
        """
        _logger.warning('request je %s', request.httprequest.headers)
        self.ensure_one()
        #event = self.process_python_code(
         #  self.python_code_get_event, request)
        event ="X-GetEvent"
        _logger.warning('event je %s', event)
        if not event:
            raise exceptions.ValidationError(_(
                'event is not defined'))
        method_event_name_base = \
            'run_' + self.name + \
            '_' + event
        _logger.warning('Primio zahtev1 %s', method_event_name_base)
        methods_event_name = self.get_event_methods(method_event_name_base)
        self.run_github_push_task(request)
        _logger.warning('Primio zahtev2 %s', methods_event_name)
        # if not methods_event_name:
        #     # if is a 'ping' event then return True
        #     # because the request is received fine.
        #     if event in self.get_ping_events():
        #         _logger.warning('Stigo do kraja ')
        #         self.run_github_push_task()
        #         return True
        #
        #     raise exceptions.ValidationError(_(
        #         'Not defined methods "%s" yet' % (
        #             method_event_name_base)))
        # self.env.request = request

        for method_event_name in methods_event_name:
            method = getattr(self, method_event_name)
            res_method = method(request)
            if isinstance(res_method, list) and len(res_method) == 1:
                if res_method[0] is NotImplemented:
                    _logger.debug(
                        'Not implemented method "%s" yet', method_event_name)
        _logger.warning('Stigo do kraja ')
        self.run_github_push_task(request)
        return True


    #dodato
    @api.one
    def run_github_push_task(self, request):

        _logger.warning('stigo')
        headers = request.httprequest.headers.get("X-GetEvent")
        # TODO: Probaj bez json.loads
        data = json.loads(headers)
        print(data)
        data_record = data['records']
        data_record = data_record[1:-1]
        data_record = json.loads(data_record)
        hotel_room = self.env['hotel.room'].search([("broj_sobe", '=', data_record['broj_sobe'])])
        print(data_record['do_not_disturb'])
        print(data_record['gost_status'])
        print(data_record['poziv_osoblju'])
        data_recordd = [('true', 'true'), (False, 'false')]
        if hotel_room.do_not_disturb != data_record['do_not_disturb']:
            if hotel_room.do_not_disturb:
                hotel_room.do_not_disturb_change("Iskljucen")
                hotel_room.do_not_disturb = False
            else:
                hotel_room.do_not_disturb_change("Ukljucen")
                hotel_room.do_not_disturb = True

        if hotel_room.sos_status != data_record['sos_status']:
            if hotel_room.sos_status == True:
                hotel_room.sos_status_change("Iskljucen")
                hotel_room.sos_status = data_record['sos_status']
            else:
                hotel_room.sos_status_change("Ukljucen")
                hotel_room.sos_status = True

        if hotel_room.gost_status != data_record['gost_status']:
            if hotel_room.gost_status == True:
                hotel_room.gost_status_change("Iskljucen")
                hotel_room.gost_status =False
            else:
                hotel_room.gost_status_change("Ukljucen")
                hotel_room.gost_status = True
        if hotel_room.poziv_osoblju != data_record['poziv_osoblju']:
            if hotel_room.poziv_osoblju == True:
                hotel_room.poziv_osoblju_change("Iskljucen")
                hotel_room.poziv_osoblju = False
            else:
                hotel_room.poziv_osoblju_change("Ukljucen")
                hotel_room.poziv_osoblju = True



        print('dosoo11111')
        model = self.env['hotel.room']
        model.env['bus.bus'].sendone('auto_refresh', model._name)

        # hotel_room_prikaz = self.env['hotel.room.prikaz'].search([("id", '=', 1)])
        # hotel_room_prikaz.sos_status1 = data_record['sos_status']
        # hotel_room_prikaz.poziv_osoblju1 = data_record['poziv_osoblju']
        # hotel_room_prikaz.gost_status1 = data_record['gost_status']
        # hotel_room_prikaz.do_not_disturb1 = data_record['do_not_disturb']
        #
        # model = self.env['hotel.room.prikaz']
        # model.env['bus.bus'].sendone('auto_refresh', model._name)
        print(json.loads(headers))
        print('dosoooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooooo')

