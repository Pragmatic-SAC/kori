# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PragmaticEstablishment(models.Model):
    _name = "pragmatic.establishment"
    _description = "Pragmatic Sunat Resources."

    name = fields.Char(string="Name", index=True, required=True)
    code = fields.Char(string="Code", index=True, required=True)
    active = fields.Boolean(string="Active", default=True)
    sunat_code = fields.Char(string="Sunat Code", index=True, required=True)
    address = fields.Char(string="Address")
    company_id = fields.Many2one(comodel_name="res.company", string="Company", required=True)

    def name_get(self):
        result = []
        for table in self:
            l_name = "%s - %s" % (table.code, table.name)
            result.append((table.id, l_name))
        return result
