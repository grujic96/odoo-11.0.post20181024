###################################################################################
# 
#    Copyright (C) 2018 MuK IT GmbH
#
#    Odoo Proprietary License v1.0
#    
#    This software and associated files (the "Software") may only be used 
#    (executed, modified, executed after modifications) if you have
#    purchased a valid license from the authors, typically via Odoo Apps,
#    or if you have received a written agreement from the authors of the
#    Software (see the COPYRIGHT file).
#    
#    You may develop Odoo modules that use the Software as a library 
#    (typically by depending on it, importing it and using its resources),
#    but without copying any source code or material from the Software.
#    You may distribute those modules under the license of your choice,
#    provided that this license is compatible with the terms of the Odoo
#    Proprietary License (For example: LGPL, MIT, or proprietary licenses
#    similar to this one).
#    
#    It is forbidden to publish, distribute, sublicense, or sell copies of
#    the Software or modified copies of the Software.
#    
#    The above copyright notice and this permission notice must be included
#    in all copies or substantial portions of the Software.
#    
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
###################################################################################

import os
import json
import logging
import requests

from odoo import _, http, tools, SUPERUSER_ID
from odoo.tests.common import TransactionCase

from odoo.addons.muk_utils.tools.json import RecordEncoder 

_path = os.path.dirname(os.path.dirname(__file__))
_logger = logging.getLogger(__name__)

WEBTESTER_TOKEN_URL = "https://webhook.site/token"
WEBTESTER_WEBHOOK_URL = "https://webhook.site/%s"
WEBTESTER_REQUESTS_URL = "https://webhook.site/token/%s/requests"

class WebhookTestCase(TransactionCase):
    
    def setUp(self):
        super(WebhookTestCase, self).setUp()
        self.model_model = self.env['ir.model']
        self.model_fields = self.env['ir.model.fields']
        self.action = self.env['ir.actions.server']
        self.model_partner = self.model_model.search([('model', '=', 'res.partner')], limit=1)
        field_domain = [('model_id', '=', self.model_partner.id), ('name', '=', 'name')]
        self.field_partner_name = self.model_fields.search(field_domain, limit=1)
        self.uuid = requests.post(WEBTESTER_TOKEN_URL).json().get('uuid')
    
    def get_requests(self, uuid):
        return requests.get(WEBTESTER_REQUESTS_URL % uuid).json()

    def test_webhook_simple(self):
        webhook = self.action.create({
            'name': "Webhook Test Simple",
            'state': 'webhook',
            'model_id': self.model_partner.id,
            'webhook_fields': [(6, 0, [self.field_partner_name.id])],
            'webhook_address': WEBTESTER_WEBHOOK_URL % self.uuid})
        webhook.run()
        webhook_requests = self.get_requests(self.uuid)
        self.assertTrue(webhook_requests.get('total') == 1)
        webhook_payload = webhook_requests.get('data')[0]['request']
        self.assertEquals(webhook_requests.get('data')[0]['method'], 'POST')
        self.assertEquals(webhook_payload.get('name'), "Webhook Test Simple")
        self.assertEquals(webhook_payload.get('model'), 'res.partner')
        self.assertEquals(webhook_payload.get('records'), '[]')
        
    def test_webhook_method(self):
        webhook = self.action.create({
            'name': "Webhook Test Method",
            'state': 'webhook',
            'model_id': self.model_partner.id,
            'webhook_method': 'GET',
            'webhook_fields': [(6, 0, [self.field_partner_name.id])],
            'webhook_address': WEBTESTER_WEBHOOK_URL % self.uuid})
        webhook.run()
        webhook_requests = self.get_requests(self.uuid)
        self.assertTrue(webhook_requests.get('total') == 1)
        self.assertEquals(webhook_requests.get('data')[0]['method'], 'GET')
        
    def test_webhook_payload(self):
        webhook = self.action.create({
            'name': "Webhook Test Payload",
            'state': 'webhook',
            'model_id': self.model_partner.id,
            'webhook_fields': [(6, 0, [self.field_partner_name.id])],
            'webhook_address': WEBTESTER_WEBHOOK_URL % self.uuid,
            'webhook_payload': "content = dump(model.search([], limit=1).read(fields=['display_name']))"})
        records = self.env['res.partner'].search([], limit=1).read(fields=['display_name'])
        tester = json.dumps(records, sort_keys=True, indent=4, cls=RecordEncoder)
        webhook.run()
        webhook_requests = self.get_requests(self.uuid)
        self.assertTrue(webhook_requests.get('total') == 1)
        webhook_payload = webhook_requests.get('data')[0]['request']
        self.assertEquals(webhook_payload.get('content'), tester)
        
    def test_webhook_process(self):
        webhook = self.action.create({
            'name': "Webhook Test Process",
            'state': 'webhook',
            'model_id': self.model_partner.id,
            'webhook_fields': [(6, 0, [self.field_partner_name.id])],
            'webhook_address': WEBTESTER_WEBHOOK_URL % self.uuid,
            'webhook_process': "log('%s' + '-' + str(response.status_code))" % self.uuid})
        webhook.run()
        webhook_requests = self.get_requests(self.uuid)
        self.assertTrue(webhook_requests.get('total') == 1)
        
    def test_webhook_authentication(self):
        webhook = self.action.create({
            'name': "Webhook Test Basic",
            'state': 'webhook',
            'model_id': self.model_partner.id,
            'webhook_fields': [(6, 0, [self.field_partner_name.id])],
            'webhook_address': WEBTESTER_WEBHOOK_URL % self.uuid,
            'webhook_authentication': 'base',
            'webhook_user': 'base',
            'webhook_password': 'base'})
        webhook.run()
        webhook_requests = self.get_requests(self.uuid)
        self.assertTrue(webhook_requests.get('total') == 1)
        webhook_headers = webhook_requests.get('data')[0]['headers']
        self.assertTrue(webhook_headers.get('authorization')[0].startswith('Basic'))
