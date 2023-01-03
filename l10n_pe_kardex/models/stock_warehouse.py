# -*- coding: utf-8 -*-
from odoo import api, models, fields, _


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    establishment = fields.Many2one(comodel_name="pragmatic.establishment",
                                    string="Establishment")

    show_field = fields.Boolean(string="Show field", default=True, compute='_compute_installed_l10n_pe_conf')

    def _compute_installed_l10n_pe_conf(self):
        installed = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'l10n_pe_conf'), ('state', '=', 'installed')], limit=1)
        if installed:
            self.show_field = False
        else:
            self.show_field = True
