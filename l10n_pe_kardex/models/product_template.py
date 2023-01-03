# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _

valuation = [('manual_periodic', _('Manual')), ('real_time', _('Automatizado'))]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # valuation_kardex = fields.Selection(valuation, readonly=True, store=True, compute="_compute_valuation")
    valuation_kardex = fields.Selection(related="categ_id.property_valuation", readonly=True, store=True)
    comodel_name = "it.lztn.resource.sunat.pe"

    # def _compute_valuation(self):
    #     for prod in self:
    #         prod.valuation_kardex = prod.categ_id.property_valuation
    #         print('vallll=>',prod.valuation_kardex)


class ProductTemplate(models.Model):
    _inherit = 'product.product'

    def get_price_transfer(self, company_id, date=None):
        history = self.env['stock.valuation.layer'].search([
            ('company_id', '=', company_id),
            ('product_id', 'in', self.ids),
            ('create_date', '<=', date or fields.Datetime.now())], order='create_date desc,id desc', limit=1)
        return history.unit_cost or 0.0
