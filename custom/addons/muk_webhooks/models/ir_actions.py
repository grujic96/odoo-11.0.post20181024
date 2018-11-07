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

import json
import logging
import textwrap

from requests import Request, Session
from requests.auth import HTTPBasicAuth
from requests.auth import HTTPDigestAuth
from requests.exceptions import RequestException

from odoo import api, models, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.safe_eval import safe_eval, test_python_expr
from odoo.exceptions import UserError, ValidationError, AccessError
#from odoo.addons.muk_utils.tools.json import RecordEncoder


import json
import logging
import datetime

from odoo import models, tools

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------
# JSON Encoder
# ----------------------------------------------------------

class ResponseEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        if isinstance(obj, datetime.datetime):
            return obj.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        if isinstance(obj, (bytes, bytearray)):
            return obj.decode()
        return json.JSONEncoder.default(self, obj)


class RecordEncoder(ResponseEncoder):

    def default(self, obj):
        if isinstance(obj, models.BaseModel):
            return obj.name_get()
        return ResponseEncoder.default(self, obj)
_logger = logging.getLogger(__name__)

try:
    from oauthlib.oauth2 import LegacyApplicationClient
    from oauthlib.oauth2 import BackendApplicationClient
    from requests_oauthlib import OAuth1, OAuth2Session
except ImportError:
    _logger.warning("The Python library requests_oauthlib is not installed, OAuth settings are disabled.")
    oauth_authentication = False
else:
    oauth_authentication = True

DEFAULT_WEBHOOK_PAYLOAD = textwrap.dedent("""\
    # Available variables:
    #  - env: Odoo Environment on which the action is triggered
    #  - user: User who triggered the action
    #  - model: Odoo Model of the record on which the action is triggered; is a void recordset
    #  - record: record on which the action is triggered; may be be void
    #  - records: recordset of all records on which the action is triggered in multi-mode; may be void
    #  - time, datetime, dateutil, timezone: useful Python libraries
    #  - date_format, datetime_format: server date and time formats
    #  - log: log(message, level='info'): logging function to record debug information in ir.logging table
    #  - dump: dump(content): dumps content into a json string and takes care of converting dates and records
    #  - Warning: Warning Exception to use with raise
    # To extend the playload, assign: content = {...}\n\n\n\n""")

DEFAULT_WEBHOOK_PROCESS = textwrap.dedent("""\
    # Available variables:
    #  - env: Odoo Environment on which the action is triggered
    #  - user: User who triggered the action
    #  - request: Request send by the action
    #  - response: Response received when the request was sent
    #  - model: Odoo Model of the record on which the action is triggered; is a void recordset
    #  - record: record on which the action is triggered; may be be void
    #  - records: recordset of all records on which the action is triggered in multi-mode; may be void
    #  - time, datetime, dateutil, timezone: useful Python libraries
    #  - date_format, datetime_format: server date and time formats
    #  - log: log(message, level='info'): logging function to record debug information in ir.logging table
    #  - dump: dump(content): dumps content into a json string and takes care of converting dates and records
    #  - Warning: Warning Exception to use with raise\n\n\n\n""")

class ServerActions(models.Model):
    
    _inherit = 'ir.actions.server'

    #----------------------------------------------------------
    # Selections
    #----------------------------------------------------------

    def _webhook_authentication_selection(self):
        selection = [
            ('none', 'Public'),
            ('base', 'Basic'),
            ('digest', 'Digest'),
            ('token', 'Token'),
        ]
        if oauth_authentication:
            selection.extend([
                ('oauth1', 'OAuth1'),
                ('oauth2', 'OAuth2')
            ])
        return selection

    #----------------------------------------------------------
    # Database
    #----------------------------------------------------------
    
    state = fields.Selection(
        selection_add=[('webhook', 'Webhook')])
    
    webhook_address = fields.Char(
        string="Address",
        states={'webhook': [('required', True)]})
    
    webhook_method = fields.Selection(
        selection=[
            ("GET", "GET"),
            ("POST", "POST"),
            ("PUT", "PUT"),
            ("DELETE", "DELETE")],
        string="Method",
        states={'webhook': [('required', True)]},
        default='POST')
    
    webhook_payload = fields.Text(
        string="Payload",
        default=DEFAULT_WEBHOOK_PAYLOAD)
    
    webhook_process = fields.Text(
        string="Process",
        default=DEFAULT_WEBHOOK_PROCESS)
    
    webhook_timeout = fields.Integer(
        string="Timeout",
        states={'webhook': [('required', True)]},
        default=25)
    
    webhook_authentication = fields.Selection(
        selection=_webhook_authentication_selection,
        string="Authentication",
        states={'webhook': [('required', True)]},
        default='none')
    
    webhook_user = fields.Char(
        string="User")
    
    webhook_password = fields.Char(
        string="Password")
    
    webhook_token = fields.Char(
        string="Access Token")
    
    webhook_client_key = fields.Char(
        string="Client Key")
    
    webhook_client_secret = fields.Char(
        string="Client Secret")
    
    webhook_resource_owner_key = fields.Char(
        string="Resource Key")
    
    webhook_resource_owner_secret = fields.Char(
        string="Resource Secret")
    
    webhook_token_url = fields.Char(
        string="Token URL")
    
    webhook_grant = fields.Selection(
        selection=[
            ('password', 'Password Credentials'),
            ('client_credentials', ' Client Credentials')],
        string="Grant Type",
        default='password')
    
    webhook_fields = fields.Many2many(
        comodel_name='ir.model.fields',
        domain="[('model_id', '=', model_id)]", 
        string="Fields")
    
    webhook_secure = fields.Boolean(
        compute='_compute_webhook_secure',
        string="Secure")
    
    webhook_verify = fields.Boolean(
        string="Verify",
        default=True)
    
    webhook_path = fields.Char(
        string="Path to Certificate")
    
    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------
    
    @api.model
    def _get_eval_context(self, action=None):
        def dump(content):
            return json.dumps(content, sort_keys=True, indent=4, cls=RecordEncoder)
        eval_context = super(ServerActions, self)._get_eval_context(action=action)
        eval_context.update({
            'dump': dump,
            'date_format': DEFAULT_SERVER_DATE_FORMAT,
            'datetime_format': DEFAULT_SERVER_DATETIME_FORMAT,
        })
        return eval_context
        
    @api.model
    def run_action_webhook_multi(self, action, eval_context={}):
        user = eval_context.get('user')
        fields = action.webhook_fields.mapped('name')
        records = eval_context.get('records') or self.env[action.model_name]
        payload = {
            'name': action.name,
            'uid': eval_context.get('uid'),
            'user': user and user.name,
            'model': action.model_name,
            'records': json.dumps(records.read(fields=fields), cls=RecordEncoder)
        }
        auth = None
        session = Session()
        if action.webhook_authentication == 'base':
            auth = HTTPBasicAuth(action.webhook_user, action.webhook_password)
        elif action.webhook_authentication == 'digest':
            auth = HTTPDigestAuth(action.webhook_user, action.webhook_password)
        elif action.webhook_authentication == 'oauth1':
            auth = OAuth1(action.webhook_client_key, client_secret=action.webhook_client_secret,
                   resource_owner_key=action.webhook_resource_owner_key,
                   resource_owner_secret=action.webhook_resource_owner_secret)
        elif action.webhook_authentication == 'oauth2' and action.webhook_grant == 'password':
            session = OAuth2Session(client=LegacyApplicationClient(client_id=action.webhook_client_key))
            session.fetch_token(token_url=action.webhook_token_url, username=action.webhook_user,
                password=action.webhook_password, client_id=action.webhook_client_key, 
                client_secret=action.webhook_client_secret)
        elif action.webhook_authentication == 'oauth2' and action.webhook_grant == 'client_credentials':
            session = OAuth2Session(client=BackendApplicationClient(client_id=client_id))
            session.fetch_token(token_url=action.webhook_token_url, client_id=action.webhook_client_key, 
                client_secret=action.webhook_client_secret)
        elif action.webhook_authentication == 'token':
            payload.update({'access_token': action.webhook_token})
        if action.webhook_payload:
            safe_eval(action.webhook_payload.strip(), eval_context, mode="exec", nocopy=True)
            if 'content' in eval_context:
                payload.update({'content': eval_context['content']})
        request = Request(action.webhook_method,  action.webhook_address, data=json.dumps(payload), auth=auth)
        prepared_request = session.prepare_request(request)
        logger_message = "Webhook: [%s] %s" % (action.webhook_method, action.webhook_address)
        try:
            webhook_path = action.webhook_path
            webhook_verify = action.webhook_verify
            verify = webhook_path if webhook_verify and webhook_path else webhook_verify
            response = session.send(prepared_request,
                                    timeout=action.webhook_timeout, verify=verify)
            _logger.info("%s - %s" % (logger_message, response.status_code))
            if action.webhook_process:
                eval_context.update({'request': prepared_request, 'response': response})
                safe_eval(action.webhook_process.strip(), eval_context, mode="exec")
        except RequestException:
            _logger.exception(logger_message)
        finally:
            session.close()
          
    #----------------------------------------------------------
    # Read
    #----------------------------------------------------------
    
    @api.depends('webhook_address')
    def _compute_webhook_secure(self):
        for record in self:
            record.webhook_secure = record.webhook_address and record.webhook_address.startswith("https")
      
    #----------------------------------------------------------
    # Create, Update, Delete
    #----------------------------------------------------------
    
    @api.constrains('webhook_payload')
    def _check_webhook_payload(self):
        for record in self.sudo().filtered('webhook_payload'):
            message = test_python_expr(expr=record.webhook_payload.strip(), mode="exec")
            if message:
                raise ValidationError(message)
    
    @api.constrains('webhook_process')
    def _check_webhook_process(self):
        for record in self.sudo().filtered('webhook_process'):
            message = test_python_expr(expr=record.webhook_process.strip(), mode="exec")
            if message:
                raise ValidationError(message)
    
    @api.constrains('webhook_authentication')
    def _validate_webhook_authentication(self):
        validators = {
            'base': lambda rec: rec.webhook_user and rec.webhook_password,
            'digest': lambda rec: rec.webhook_user and rec.webhook_password,
            'token': lambda rec: rec.webhook_token,
            'oauth1': lambda rec: rec.webhook_client_key and rec.webhook_client_secret and \
                rec.webhook_resource_owner_key and rec.webhook_resource_owner_secret,
            'oauth2': lambda rec: rec.webhook_token_url and (
                    rec.webhook_grant == 'password' and 
                    rec.webhook_user and rec.webhook_password and
                    rec.webhook_client_key and rec.webhook_client_secret
                ) or (
                    rec.webhook_grant == 'client_credentials' and 
                    rec.webhook_client_key and rec.webhook_client_secret),
        }
        for record in self:
            if record.webhook_authentication in validators and not validators[record.webhook_authentication](record):
                raise ValidationError(("Webhook validation has failed!"))