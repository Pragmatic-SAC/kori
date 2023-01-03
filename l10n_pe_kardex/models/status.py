import threading, queue
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError


class KardexStatus(models.Model):
    _name = 'kardex.status'
    _description = "Kardex Status"

    name = fields.Char(string="Name")
    code = fields.Char(string="Code")
    color = fields.Integer(string="Color")
