# -*- coding: utf-8 -*-

from odoo import models, fields, api
# class academy(models.Model):
#     _name = 'academy.academy'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100

class HotelRoom1(models.Model) :

    _name = 'academy.academy'
    _description = 'Hotel Room1'
    name = fields.Char()



