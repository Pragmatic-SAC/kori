# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _


def column_excel_unit():
    return [
        {'name': _("Date")},
        {'name': _("CUO")},
        {'name': _("Movement")},
        {'name': _("Establishment")},
        {'name': _("Product")},
        {'name': _("Udm")},
        {'name': _("Reference")},
        # {'name': _("Series")},
        {'name': _("Operation type")},
        {'name': _("Inputs")},
        {'name': _("Outputs")},
        {'name': _("Final Balance")},
    ]


def column_excel_val():
    return [
        {'name': _("Date")},
        {'name': _("CUO")},
        {'name': _("Movement")},
        {'name': _("Establishment")},
        {'name': _("Product")},
        {'name': _("Udm")},
        {'name': _("Reference")},
        {'name': _("Operation type")},
        {'name': _("Input Cant.")},
        {'name': _("Input Cost Unit.")},
        {'name': _("Input Cost Total")},
        {'name': _("Output Cant.")},
        {'name': _("Output Cost Unit.")},
        {'name': _("Output Cost Total")},
        {'name': _("Final Cant.")},
        {'name': _("Final Cost Unit.")},
        {'name': _("Final Cost Total")}
    ]


def get_name_units(obj):
    return "%s%s%s%s%s%s%s%s%s%s%s" % (
        "LE",
        obj["company_ruc"],
        obj["account_period"].year,
        "%02d" % (obj["account_period"].month),
        "00",
        "120100",
        "00",
        "1",
        "1",  # Con informacion,
        "1",  # Moneda Validar,
        1
    )


def get_name_valued(obj):
    return "%s%s%s%s%s%s%s%s%s%s%s" % (
        "LE",
        obj["company_ruc"],
        obj["account_period"].year,
        "%02d" % (obj["account_period"].month),
        "00",
        "130100",
        "00",
        "1",
        "1",  # Con informacion,
        "1",  # Moneda Validar,
        1
    )


def data_txt_units(obj):
    return "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\r\n" % (
        obj["period"],
        obj["cuo"],
        obj["account_correlative"],
        obj["code_establishment"],
        obj["code_catalog"],
        obj["type_existence"],
        obj["code_existence"],
        obj["code_existence_catalog"],
        obj["date_emision"],
        obj["type_document_move"],
        obj["series_document_move"],
        obj["number_document_move"],
        obj["type_operation"],
        obj["description_existence"],
        obj["code_uom"],
        obj["entry_input_phisical"],
        obj["entry_ouput_phisical"],
        obj["state_operation"]
    )


def data_txt_valued(obj):
    return "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|\r\n" % (
        obj["period"],
        obj["cuo"],
        obj["account_correlative"],
        obj["code_establishment"],
        obj["code_catalog"],
        obj["type_existence"],
        obj["code_existence"],
        obj["code_existence_catalog"],
        obj["date_emision"],
        obj["type_document_move"],
        obj["series_document_move"],
        obj["number_document_move"],
        obj["type_operation"],
        obj["description_existence"],
        obj["code_uom"],
        obj["cost_method"],
        obj["cant_input"],
        obj["cost_unit_input"],
        obj["cost_total_input"],
        obj["cant_ouput"],
        obj["cost_unit_ouput"],
        obj["cost_total_ouput"],
        obj["cant_saldo_final"],
        obj["cost_unit_saldo_final"],
        obj["cost_saldo_final"],
        obj["state_operation"]
    )
