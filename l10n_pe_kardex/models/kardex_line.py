import threading, queue
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError


class KardexLine(models.Model):
    _name = 'kardex.line'
    _description = "kardex detail"

    kardex_line = fields.Many2one('kardex')
    account_period = fields.Date(string="Account period")
    type_kardex = fields.Char(string="Type Kardex")
    account_correlative = fields.Many2one('stock.move')
    stock_move = fields.Many2one('stock.move')
    account_move = fields.Many2one('account.move')
    establishment = fields.Many2one('pragmatic.establishment')
    date_emision = fields.Date(string='Date Emission')
    type_document_move = fields.Char('Type Doc Move')
    series_document_move = fields.Char('Serie Doc Move')
    number_document_move = fields.Char('Number Doc Move')
    type_operation = fields.Char('Type Operation')
    cost_method = fields.Char('Cost Method')
    reference = fields.Char('Reference')
    company_id = fields.Many2one('res.company', string='Company')
    origin = fields.Char(string='Origin')
    picking_id = fields.Many2one('stock.picking', string='Picking')
    account_move = fields.Many2one('account.move', string='Invoice')
    inventory_id = fields.Many2one('stock.inventory', string='Inventory')
    product_id = fields.Many2one('product.product', string='Product')
    # type_transaction_id = fields.Many2one('it.lztn.resource.sunat.pe', string="Type transaction")
    scrap_id = fields.Many2one('stock.scrap', string="Scrap")
    cant_input = fields.Float()
    cost_unit_input = fields.Float()
    cost_total_input = fields.Float()
    cant_ouput = fields.Float()
    cost_unit_ouput = fields.Float()
    cost_total_ouput = fields.Float()
    cant_saldo_final = fields.Float()
    cost_unit_saldo_final = fields.Float()
    cost_saldo_final = fields.Float()
    state_operation = fields.Char()
    level = fields.Integer()
    type = fields.Char()
