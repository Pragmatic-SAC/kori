# -*- coding: utf-8 -*-
import datetime
import calendar
import io
import json
import base64
import xlsxwriter
from . import utils
import threading, queue
from odoo import models, fields, api, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round, float_is_zero
from odoo.tools import config, date_utils, get_lang

q = queue.Queue()

TYPEKARDEX = [('units', _('Units')), ('valued', _('Valued'))]
STATES = [('0', _('Not realized')), ('1', _('Realized'))]


class KardexMove(models.Model):
    _name = 'kardex'
    _description = "Kardex Inventory"

    @api.model
    def _get_from_date(self):
        date = datetime.date.today()
        start_date = datetime.datetime(date.year, date.month, 1)
        return start_date.date()

    @api.model
    def _get_name_report(self):
        date = datetime.date.today()
        name_ = "%s%s%s" % (_("Month"), " ", date.strftime('%B'))
        return name_

    @api.model
    def _get_date_to(self):
        date = datetime.date.today()
        end_date = datetime.datetime(date.year, date.month, calendar.mdays[date.month])
        return end_date.date()

    name = fields.Char(string="Name", required=True, default=_get_name_report)
    date_from = fields.Date(string='Date from', default=_get_from_date)
    date_to = fields.Date(string='Date to', default=_get_date_to, required=True, )
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.user.company_id,
                                 string='Company')
    establishment = fields.Many2one(comodel_name="pragmatic.establishment", string="Establishment", required=True, )
    type_kardex = fields.Selection(TYPEKARDEX, default='units', required=True)
    progress_state = fields.Integer(default=0)

    @api.model
    def get_states(self):
        return self.env['kardex.status'].sudo().search([('code', '=', 'NINGUNO')]).ids

    state_ids = fields.Many2many('kardex.status', default=get_states)
    kardex_lines = fields.One2many(comodel_name='kardex.line', inverse_name='kardex_line')

    def worker(self):
        while True:
            item = q.get()
            print(f'Finished {item}')
            q.task_done()

    def execute_kardex(self):
        if self.date_from > self.date_to:
            raise UserError(_("The Start date cannot be less than the end date "))
        else:
            pass
            self.env['kardex'].sudo().kardex_plan(self.id)

    def kardex_plan(self, kardex):
        envs = self.env['kardex'].sudo().browse(kardex)
        for kardex in envs:
            kardex.write({'progress_state': 0})
            kardex.write({'state_ids': [(6, 0, [])]})
            kardex.kardex_lines.filtered(lambda r: r.type_kardex == kardex.type_kardex).unlink()
            self.env.cr.commit()
        for kard in envs:
            threading.Thread(target=self.worker, daemon=True).start()
            date_from_str = kard.date_from.strftime("%Y %m %d %H:%M:%S")
            dete_to_str = kard.date_to.strftime("%Y %m %d %H:%M:%S")
            date_from = datetime.datetime.strptime(date_from_str, "%Y %m %d %H:%M:%S")
            date_to = datetime.datetime.strptime(dete_to_str, "%Y %m %d %H:%M:%S") + datetime.timedelta(hours=23,
                                                                                                        minutes=59,
                                                                                                        seconds=59)
            query_total = kard._moviento_completo()
            query_movimiento = """
                                        select * from (
                                          """ + query_total + """

                                        ) as mov where create_date::date >=%s and create_date::date <=%s

                                        """
            establishment = kard.establishment.id
            query_movimiento_param = ''
            if kard.establishment:
                query_movimiento_param = (
                    establishment, establishment, establishment, establishment, date_from, date_to)
            self.env.cr.execute(query_movimiento, query_movimiento_param)
            movs = self.env.cr.dictfetchall()
            saldo_ = 0.0
            cant_total = 0.0
            cost_total = 0.00
            product_eq = 0
            cont = 0
            costo_unit_s = 0.00
            # type_transaction = self.env['it.lztn.resource.sunat.pe']
            precision_value = self.env.user.company_id.currency_id.decimal_places or 2
            precision_cost = self.env['decimal.precision'].sudo().search([('name', '=', 'Product Price')], limit=1)
            lines_total = len(movs)
            if len(movs) > 0:
                try:
                    for mov in movs:
                        q.put(mov)
                        type_doc = '00'
                        serie_doc = '0'
                        number_doc = '0'
                        # if mov['picking_id'] != None:
                        #     picking_sale = kard.get_picking_doc(mov['picking_id'])
                        #     type_doc = picking_sale['type_doc']
                        #     serie_doc = picking_sale['serie_doc']
                        #     number_doc = picking_sale['number_doc']

                        # type_transaction_id = None
                        # if mov['loc_ori'] == 'production' and mov['loc_des'] == 'internal':
                        #     type_transaction_id = kard.get_type_document_excel('19')
                        # elif mov['loc_ori'] == 'internal' and mov['loc_des'] == 'production':
                        #     type_transaction_id = kard.get_type_document_excel('10')
                        # elif mov['picking_id'] == None:
                        #     if mov['loc_ori'] == 'internal' and mov['loc_des'] == 'customer':
                        #         type_transaction_id = kard.get_type_document_excel('01')

                        # Saldo iniciales
                        if saldo_ == 0 and product_eq == 0:
                            query_total = kard._moviento_completo_producto()
                            query_saldo_anterior = """
                                                                  select *  from (
                                                            """ + query_total + """


                                                            )as saldo_ante where create_date::date < %s order by product, date_order desc  limit 1--) estes espara obteber el saldo anterior

                                                                    """
                            product_eq = mov['product']
                            query_saldo_anterior_param = (
                                product_eq, establishment, product_eq, establishment, product_eq, establishment,
                                product_eq,
                                establishment, product_eq, kard.date_from,)
                            self.env.cr.execute(query_saldo_anterior, query_saldo_anterior_param)

                            saldo_anterior = self.env.cr.dictfetchall()
                            # type_operation_init = type_transaction.sudo().search(
                            #     [('code', '=', '16'), ('resource_code', '=', 'TABLA_12')], limit=1)
                            if saldo_anterior:
                                for sal_ini in saldo_anterior:
                                    for kardex in kard:
                                        costo_unit = sal_ini[
                                            'costo_unit']  # prod.get_history_price(kard.env.user.company_id.id,date=sal_ini['date_order'])
                                        cant_total = sal_ini['u_saldo'] or 0.00
                                        if costo_unit is None:
                                            prod = self.env['product.product'].sudo().browse(sal_ini['product'])
                                            costo_unit = prod.get_price_transfer(kard.env.user.company_id.id,
                                                                                 date=sal_ini['date_order'])
                                        costo_unit_s = costo_unit
                                        if cant_total > 0:
                                            saldo_ = sal_ini['u_saldo'] * costo_unit or 0.00  # sal_ini['v_saldo'] or 00
                                            cost_total = costo_unit or 0.00
                                            line = ({
                                                'account_period': kardex.date_from, 'account_correlative': None,
                                                'stock_move': sal_ini['stock'],
                                                'account_move': sal_ini['account'],
                                                'establishment': kard.establishment.id,
                                                'date_emision': sal_ini['create_date'],
                                                'type_document_move': str(type_doc),
                                                'series_document_move': str(serie_doc),
                                                'number_document_move': str(number_doc),
                                                'type_operation': '',
                                                'cost_method': '', 'company_id': sal_ini['company_id'],
                                                'origin': sal_ini['origin'],
                                                'picking_id': sal_ini['picking_id'],
                                                'inventory_id': sal_ini['inventory_id'],
                                                'product_id': sal_ini['product'],
                                                # 'type_transaction_id': type_operation_init.id,
                                                'scrap_id': None,
                                                'reference': sal_ini['reference'],
                                                'cant_input': cant_total, 'cost_unit_input': cost_total,
                                                'cost_total_input': saldo_,
                                                'cant_ouput': 0.00,
                                                'cost_unit_ouput': 0.00, 'cost_total_ouput': 0.00,
                                                'cant_saldo_final': cant_total, 'cost_unit_saldo_final': cost_total,
                                                'cost_saldo_final': saldo_, 'state_operation': sal_ini['state'],
                                                'level': 1,
                                                'type_kardex': kard.type_kardex,
                                                'type': sal_ini['tipo']
                                            })
                                            lines = [(0, 0, line)]
                                            kardex.write({'kardex_lines': lines})
                                            self.env.cr.commit()
                                        else:
                                            saldo_ = 0.00
                                            cant_total = 0.00
                                            cost_total = 0.00
                            else:
                                saldo_ = 0.00
                                cant_total = 0.00
                                cost_total = 0.00
                        else:
                            if product_eq == mov['product']:
                                pass
                            else:
                                query_total = kard._moviento_completo_producto()
                                query_saldo_anterior = """
                                                                                      select *  from (
                                                                                """ + query_total + """


                                                                                )as saldo_ante where create_date::date < %s order by product, date_order desc  limit 1 --) estes espara obteber el saldo anterior

                                                                                        """
                                product_eq = mov['product']
                                query_saldo_anterior_param = (
                                    product_eq, establishment, product_eq, establishment, product_eq, establishment,
                                    product_eq, establishment, product_eq, date_from,)
                                self.env.cr.execute(query_saldo_anterior, query_saldo_anterior_param)

                                saldo_anterior = self.env.cr.dictfetchall()
                                # type_operation_init = type_transaction.sudo().search(
                                #     [('code', '=', '16'), ('resource_code', '=', 'TABLA_12')], limit=1)
                                if saldo_anterior:
                                    for sal_ini in saldo_anterior:
                                        for kardex in kard:
                                            costo_unit = sal_ini[
                                                'costo_unit']  # prod.get_history_price(kard.env.user.company_id.id,date=sal_ini['date_order'])
                                            cant_total = sal_ini['u_saldo'] or 0.00
                                            if cant_total > 0:
                                                if costo_unit is None:
                                                    prod = self.env['product.product'].sudo().browse(sal_ini['product'])
                                                    costo_unit = prod.get_price_transfer(kard.env.user.company_id.id,
                                                                                         date=sal_ini['date_order'])
                                                saldo_ = sal_ini[
                                                             'u_saldo'] * costo_unit or 0.00  # sal_ini['v_saldo'] or 0.00
                                                cost_total = costo_unit or 0.00
                                                costo_unit_s = costo_unit
                                                line = ({
                                                    'account_period': kardex.date_from,
                                                    'account_correlative': None,
                                                    'stock_move': sal_ini['stock'],
                                                    'account_move': sal_ini['account'],
                                                    'establishment': kard.establishment.id,
                                                    'date_emision': sal_ini['create_date'],
                                                    'type_document_move': str(type_doc),
                                                    'series_document_move': str(serie_doc),
                                                    'number_document_move': str(number_doc),
                                                    'type_operation': '',
                                                    'cost_method': '', 'company_id': sal_ini['company_id'],
                                                    'origin': sal_ini['origin'],
                                                    'picking_id': sal_ini['picking_id'],
                                                    'inventory_id': sal_ini['inventory_id'],
                                                    'product_id': sal_ini['product'],
                                                    # 'type_transaction_id': type_operation_init.id,
                                                    'scrap_id': None,
                                                    'reference': sal_ini['reference'],
                                                    'cant_input': cant_total, 'cost_unit_input': cost_total,
                                                    'cost_total_input': saldo_,
                                                    'cant_ouput': 0.00,
                                                    'cost_unit_ouput': 0.00, 'cost_total_ouput': 0.00,
                                                    'cant_saldo_final': cant_total, 'cost_unit_saldo_final': cost_total,
                                                    'cost_saldo_final': saldo_, 'state_operation': sal_ini['state'],
                                                    'level': 1,
                                                    'type_kardex': kard.type_kardex,
                                                    'type': sal_ini['tipo']
                                                })
                                                lines = [(0, 0, line)]
                                                kardex.write({'kardex_lines': lines})
                                                self.env.cr.commit()

                                            else:
                                                saldo_ = 0.00
                                                cant_total = 0.00
                                                cost_total = 0.00
                                else:
                                    saldo_ = 0.00
                                    cant_total = 0.00
                                    cost_total = 0.00

                        # Movimientos
                        print('mov====', mov)
                        if mov['tipo'] == 'IN':
                            # if mov['picking_id'] is None and mov['u_entrada'] == 0:
                            #     type_transaction_id = type_transaction.search(
                            #         [('it_cost_adjustment', '=', True), ('resource_code', '=', 'TABLA_12')], limit=1)
                            costo_unit_final = mov['costo_unit']
                            costo_unit_s = mov['costo_unit']
                            costo_unit = float_round(mov['costo_unit'], precision_digits=precision_cost.digits or 2)
                            entrada = float_round(mov['v_entrada'], precision_digits=precision_value)
                            salida = 0.00
                            cant_entrada = mov['u_entrada']
                            cant_salida = 0.00
                            cost_entrada = costo_unit
                            cost_salida = 0.00
                            cant_total = cant_total + cant_entrada
                            if round(cant_total, 2) > 0:
                                saldo_ = saldo_ + entrada
                                # saldo_ = mov['v_saldo']  # cant_total * costo_unit_final
                                cost_total = costo_unit_final
                            else:
                                saldo_ = 0.00
                                cant_total = 0.00
                                cost_total = 0.00
                        if mov['tipo'] == 'IN_INT':
                            costo_unit = float_round(costo_unit_s, precision_digits=precision_cost.digits or 2)
                            costo_unit_final = costo_unit_s
                            entrada = float_round(mov['u_entrada'] * costo_unit, precision_digits=precision_value)
                            salida = 0.00
                            cant_entrada = mov['u_entrada']
                            cant_salida = 0.00
                            cost_entrada = costo_unit
                            cost_salida = 0.00
                            cant_total = cant_total + cant_entrada
                            if round(cant_total, 2) > 0:
                                saldo_ = saldo_ + abs(entrada)
                                # saldo_ = mov['v_saldo']  # cant_total * costo_unit_final
                                cost_total = costo_unit_final
                            else:
                                saldo_ = 0.00
                                cant_total = 0.00
                                cost_total = 0.00
                        if mov['tipo'] == 'OUT':
                            costo_unit_final = mov['costo_unit']
                            costo_unit_s = mov['costo_unit']
                            costo_unit = float_round(mov['costo_unit'], precision_digits=precision_cost.digits or 2)
                            entrada = 0.00
                            salida = float_round(mov['v_salida'], precision_digits=precision_value)
                            cant_entrada = 0.00
                            cant_salida = mov['u_salida']
                            cost_entrada = 0.00
                            cost_salida = costo_unit
                            cant_total = cant_total - abs(cant_salida)
                            if round(cant_total, 2) > 0:
                                saldo_ = saldo_ - salida
                                # saldo_ = mov['v_saldo']  # cant_total * costo_unit_final
                                cost_total = costo_unit_final
                            else:
                                saldo_ = 0.00
                                cant_total = 0.00
                                cost_total = 0.00
                        if mov['tipo'] == 'OUT_INT':
                            costo_unit_final = costo_unit_s
                            costo_unit = float_round(costo_unit_s, precision_digits=precision_cost.digits or 2)
                            entrada = 0.00
                            salida = float_round(mov['u_salida'] * costo_unit_s, precision_digits=precision_value)
                            cant_entrada = 0.00
                            cant_salida = mov['u_salida']
                            cost_entrada = 0.00
                            cost_salida = costo_unit
                            cant_total = cant_total - abs(cant_salida)
                            if round(cant_total, 2) > 0:
                                saldo_ = saldo_ - abs(salida)
                                # saldo_ = mov['v_saldo']  # cant_total * costo_unit_final
                                cost_total = costo_unit_final
                            else:
                                saldo_ = 0.00
                                cant_total = 0.00
                                cost_total = 0.00
                        if mov['tipo'] == 'AJUST':
                            query_total = kard._mov_all_multiestablisment()
                            all_quantity = """
                                                                                    select *  from (
                                                                            """ + query_total + """


                                                                            )as saldo_ante where create_date::date < %s order by product, date_order desc  limit 1 --) estes espara obteber el saldo anterior

                                                                                    """
                            product_eq = mov['product']
                            all_quantity_param = (
                                product_eq, product_eq, product_eq, product_eq, date_from,)
                            self.env.cr.execute(all_quantity, all_quantity_param)

                            all_quantity_movs = self.env.cr.dictfetchall()
                            total_cant_stablishment = 0
                            for tot in all_quantity_movs:
                                total_cant_stablishment = tot['u_saldo'] or 0.00
                            if mov['v_entrada'] > 0:
                                salida = 0.00
                                cant_entrada = 0.00
                                cant_salida = 0.00
                                cost_entrada = 0.00
                                cost_salida = 0.00
                                entrada = float_round(mov['v_entrada'],
                                                      precision_digits=precision_value)  # mov['v_entrada']
                                cant_total = cant_total + cant_entrada
                                if total_cant_stablishment > 0:
                                    entrada = float_round((entrada / total_cant_stablishment) * cant_total,
                                                          precision_digits=precision_value)
                                saldo_ = saldo_ + entrada
                                cost_total = saldo_ / cant_total if cant_total > 0 else 0.00
                                costo_unit_s = cost_total
                                if round(cant_total, 2) <= 0:
                                    saldo_ = 0.00
                                    cant_total = 0.00
                                    cost_total = 0.00
                            else:
                                entrada = 0.00
                                cant_entrada = 0.00
                                cant_salida = 0.00
                                cost_entrada = 0.00
                                cost_salida = 0.00
                                salida = float_round(mov['v_salida'],
                                                     precision_digits=precision_value)  # mov['v_salida']
                                cant_total = cant_total - cant_salida
                                if total_cant_stablishment > 0:
                                    salida = float_round((salida / total_cant_stablishment) * cant_total,
                                                         precision_digits=precision_value)
                                saldo_ = saldo_ - salida
                                cost_total = saldo_ / cant_total if cant_total > 0 else 0.00
                                costo_unit_s = cost_total
                                if round(cant_total, 2) <= 0:
                                    saldo_ = 0.00
                                    cant_total = 0.00
                                    cost_total = 0.00
                        line = ({'account_period': mov['create_date'], 'account_correlative': None,
                                 'stock_move': mov['stock'],
                                 'account_move': mov['account'],
                                 'establishment': kard.establishment.id, 'date_emision': mov['create_date'],
                                 'type_document_move': str(type_doc),
                                 'series_document_move': str(serie_doc), 'number_document_move': str(number_doc),
                                 'type_operation': '',
                                 'cost_method': '', 'company_id': mov['company_id'], 'origin': mov['origin'],
                                 'picking_id': mov['picking_id'], 'inventory_id': mov['inventory_id'],
                                 'product_id': mov['product'],
                                 # 'type_transaction_id': type_transaction_id.id if type_transaction_id else None,
                                 'scrap_id': mov['scrap_id'],
                                 'reference': mov['reference'],
                                 'cant_input': cant_entrada, 'cost_unit_input': cost_entrada,
                                 'cost_total_input': entrada,
                                 'cant_ouput': cant_salida,
                                 'cost_unit_ouput': cost_salida, 'cost_total_ouput': salida,
                                 'cant_saldo_final': cant_total, 'cost_unit_saldo_final': cost_total,
                                 'cost_saldo_final': saldo_, 'state_operation': mov['state'],
                                 'level': 2,
                                 'type_kardex': kard.type_kardex,
                                 'type': mov['tipo']
                                 })
                        lines = [(0, 0, line)]
                        type_transaction_id = None
                        for kardex in kard:
                            cont += 1
                            percent = (cont * 100) / lines_total
                            kardex.write({'progress_state': percent, 'kardex_lines': lines})
                            self.env.cr.commit()
                    # SALDO INICIAL DE PRODUCTO QUE TIENEN STOCK
                    query_total = kard._moviento_completo()
                    query_movimiento = """
                                            select distinct(product) from (
                                            """ + query_total + """

                                            ) as mov where product NOT IN (select distinct(product) from (""" + query_total + """) as det
                                            where create_date::date >=%s and create_date::date <=%s ) and create_date::date <%s

                                            """
                    establishment = kard.establishment.id
                    date_from = kard.date_from
                    date_to = kard.date_to
                    query_movimiento_param = ''
                    if kard.establishment:
                        query_movimiento_param = (
                            establishment, establishment, establishment, establishment, establishment, establishment,
                            establishment, establishment, date_from, date_to, date_from)
                    self.env.cr.execute(query_movimiento, query_movimiento_param)

                    stocks = self.env.cr.dictfetchall()
                    for sto in stocks:
                        query_total = kard._moviento_completo_producto()
                        query_saldo_anterior = """
                                                            select *  from (
                                                        """ + query_total + """


                                                        )as saldo_ante where date_order < %s order by product, date_order desc  limit 1--) estes espara obteber el saldo anterior

                                                                """
                        establishment = kard.establishment.id
                        date_from = kard.date_from
                        product_eq = sto['product']
                        query_saldo_anterior_param = (
                            product_eq, establishment, product_eq, establishment, product_eq, establishment, product_eq,
                            establishment, product_eq, date_from,)
                        self.env.cr.execute(query_saldo_anterior, query_saldo_anterior_param)

                        saldo_anterior = self.env.cr.dictfetchall()
                        for sal_ in saldo_anterior:
                            q.put(sal_)
                            # type_operation_init_stock = type_transaction.sudo().search(
                            #     [('code', '=', '16'), ('resource_code', '=', 'TABLA_12')], limit=1)
                            type_doc_stock = '00'
                            serie_doc_stock = '0'
                            number_doc_stock = '0'
                            if sal_['picking_id'] != None:
                                picking_sale = kard.get_picking_doc(sal_['picking_id'])
                                type_doc_stock = picking_sale['type_doc']
                                serie_doc_stock = picking_sale['serie_doc']
                                number_doc_stock = picking_sale['number_doc']

                            for kardex in kard:
                                precision = kard.env.user.company_id.currency_id.decimal_places or 2
                                cant_total_stock = float_round(abs(sal_['u_saldo']), precision_digits=precision) or 0.00
                                if cant_total_stock > 0:
                                    costo_unit = sal_ini['costo_unit']
                                    if costo_unit is None:
                                        prod = self.env['product.product'].sudo().browse(sal_ini['product'])
                                        costo_unit = prod.get_price_transfer(kard.env.user.company_id.id,
                                                                             date=sal_ini['date_order'])
                                    saldo_stock = sal_['u_saldo'] * costo_unit or 0.00
                                    cost_total_stock = costo_unit or 0.00
                                    line = ({
                                        'account_period': kardex.date_from,
                                        'account_correlative': None,
                                        'stock_move': sal_['stock'],
                                        'account_move': sal_['account'],
                                        'establishment': kard.establishment.id,
                                        'date_emision': sal_['create_date'],
                                        'type_document_move': str(type_doc_stock),
                                        'series_document_move': str(serie_doc_stock),
                                        'number_document_move': str(number_doc_stock),
                                        'type_operation': '',
                                        'cost_method': '', 'company_id': sal_ini['company_id'],
                                        'origin': sal_ini['origin'],
                                        'picking_id': sal_ini['picking_id'],
                                        'inventory_id': sal_ini['inventory_id'],
                                        'product_id': sal_ini['product'],
                                        # 'type_transaction_id': type_operation_init_stock.id,
                                        'scrap_id': None,
                                        'reference': sal_ini['reference'],
                                        'cant_input': cant_total_stock, 'cost_unit_input': cost_total_stock,
                                        'cost_total_input': saldo_stock,
                                        'cant_ouput': 0.00,
                                        'cost_unit_ouput': 0.00, 'cost_total_ouput': 0.00,
                                        'cant_saldo_final': cant_total_stock, 'cost_unit_saldo_final': cost_total_stock,
                                        'cost_saldo_final': saldo_stock, 'state_operation': sal_ini['state'],
                                        'level': 1,
                                        'type_kardex': kard.type_kardex,
                                        'type': sal_ini['tipo']
                                    })
                                    lines = [(0, 0, line)]
                                    kardex.write({'kardex_lines': lines})
                                    self.env.cr.commit()

                    states = []
                    del_state = self.env['kardex.status'].sudo().search([('code', 'in', ['NINGUNO', 'error'])],
                                                                           limit=1)
                    kardex.write({'state_ids': [(2, del_state.id)]})
                    type_print_id = self.env['kardex.status'].sudo().search([('code', '=', kardex.type_kardex)],
                                                                               limit=1)
                    states.append(type_print_id.id)
                    for x in kardex.state_ids:
                        states.append(x.id)
                    kardex.write({'state_ids': [(6, 0, states)]})
                    self.env.cr.commit()
                except Exception as e:
                    states = []
                    type_print_id = self.env['kardex.status'].sudo().search([('code', '=', 'error')],
                                                                               limit=1)
                    states.append(type_print_id.id)
                    for x in kardex.state_ids:
                        states.append(x.id)
                    kardex.write({'state_ids': [(6, 0, states)]})
                    self.env.cr.commit()
                    raise ValidationError(str(e))
            else:
                states = []
                del_state = self.env['kardex.status'].sudo().search([('code', 'in', ['NINGUNO', 'error'])], limit=1)
                kardex.write({'state_ids': [(2, del_state.id)]})
                type_print_id = self.env['kardex.status'].sudo().search([('code', '=', kardex.type_kardex)], limit=1)
                states.append(type_print_id.id)
                for x in kardex.state_ids:
                    states.append(x.id)
                kardex.write({'progress_state': 100, 'state_ids': [(6, 0, states)]})
                self.env.cr.commit()
        q.join()
        print('All work completed')

    def _moviento_completo(self):
        local_des = ""
        location_id = ""
        ajustes = ""
        if self.establishment:
            local_des = "sm.location_dest_id in (select sl.id from stock_location sl where sl.usage = 'internal' and sl.active is true and sl.establishment =%s)"
            location_id = "sm.location_id in (select sl.id from stock_location sl where sl.usage = 'internal' and sl.active is true and sl.establishment =%s)"
        if self.type_kardex == 'units':
            ajustes = "svl.quantity > 0"
        else:
            ajustes = "svl.quantity=0"

        # 665, 671, 672, 674,
        # productos = "sm.product_id in (3172)"
        # productos_ajus = "svl.product_id in (3172)"
        productos = "sm.product_id > 0"
        productos_ajus = "svl.product_id > 0"
        query_movimiento = """
             select id,create_date,company_id, product,nombre,u_entrada,
             u_salida,u_saldo,costo_unit,v_entrada,v_salida,
            v_saldo,state,origin,reference,loc_ori,loc_des,usage,loc_des_scrap,complete_name,ubicacion,inventory_id ,picking_id,tipo,account,stock,date_order,scrap_id  
            from (
            -------------3)Comienza el segundo select
                select id,create_date,company_id ,product_id as product,
              name as nombre,u_entrada,u_salida,
                     SUM(u_entrada-u_salida)over (order by create_date asc)as u_saldo,
                     costo_unit,v_entrada,v_salida,
                SUM(v_entrada-v_salida)over (order by create_date asc)as  v_saldo,state
              ,origin,reference,loc_ori,loc_des,usage,loc_des_scrap,
                    complete_name,ubicacion,inventory_id ,picking_id,tipo,account,stock,date_order,scrap_id  
                  from (
            --------------- EMPIEZA LA UNION
                    --- unimos entradas
                    select id,create_date,product_id,name,company_id, u_entrada,u_salida,  
                costo_unit
                    , v_entrada,v_salida,v_saldo,state,origin,reference,loc_ori,loc_des,
                    usage,loc_des_scrap,complete_name,ubicacion,create_uid,inventory_id,picking_id,tipo,account,stock,date_order,scrap_id   
                    from 
                    (
                        select sm.id,svl.create_date,sm.product_id,sm.name,sm.company_id,case when svl.stock_landed_cost_id is null then sm.product_qty else 0 end as u_entrada,(sm.product_qty * 0) as u_salida,
                        svl.unit_cost as costo_unit,svl.value as v_entrada,(-1 * 0) as v_salida,(1 *0) as v_saldo,sm.state,sm.origin,sm.reference,
                        sl2.usage as loc_ori,sl.usage as loc_des,sl.usage,sl.scrap_location as loc_des_scrap,sl.complete_name,(sm.location_dest_id)as ubicacion,sm.create_uid,cast(null as int) as inventory_id,case when svl.stock_landed_cost_id is null then sm.picking_id else cast(null as int) end as picking_id,
                        'IN'::text as tipo,am.id as account,sm.id as stock,sm.date as date_order,ss.id as scrap_id
                          from stock_valuation_layer svl
                          inner join stock_move sm on svl.stock_move_id = sm.id
                          inner join stock_location sl on sm.location_dest_id=sl.id
                          inner join stock_location sl2 on sm.location_id=sl2.id
                          inner join product_product pp on sm.product_id = pp.id
                          inner join product_template pt on pp.product_tmpl_id = pt.id
                          inner join account_move am on sm.id = am.stock_move_id 
                          left join stock_scrap ss on sm.id=ss.move_id
                          where """ + productos + """ and sm.state='done' and """ + local_des + """ and pt.valuation_kardex='real_time'
                        order by product_id,create_date asc 
                    )as    sl   
                    UNION
                    ----Transferencia interna
                     select id,create_date,product_id,name,company_id,u_entrada,u_salida,costo_unit,v_entrada,v_salida,
                     v_saldo,state,origin,reference,loc_ori,loc_des,usage,loc_des_scrap,complete_name,ubicacion,create_uid,
                     inventory_id,picking_id,tipo,account,stock,date_order,scrap_id 
                     from (select sm.id,sm.date as create_date ,sm.product_id,sm.name,sm.company_id,sm.product_qty as u_entrada,(sm.product_qty * 0) as u_salida,
                     sm.price_unit as costo_unit,(sm.product_qty*sm.price_unit) as v_entrada,(-1 * 0) as v_salida,(1 *0) as v_saldo,sm.state,sm.origin,sm.reference,
                        sl2.usage as loc_ori,sl.usage as loc_des,sl.usage,sl.scrap_location as loc_des_scrap,sl.complete_name,(sm.location_dest_id)as ubicacion,sm.create_uid,cast(null as int) as inventory_id,sm.picking_id,
                        'IN_INT'::text as tipo,cast(null as int) as account,sm.id as stock,sm.date as date_order,ss.id as scrap_id
                          from  stock_move sm
                          inner join stock_location sl on sm.location_dest_id=sl.id
                          inner join stock_location sl2 on sm.location_id=sl2.id
                          inner join product_product pp on sm.product_id = pp.id
                          inner join product_template pt on pp.product_tmpl_id = pt.id
                          left join stock_scrap ss on sm.id=ss.move_id
                          where """ + productos + """ and sm.state='done' and sl.usage='internal' and sl2.usage='internal'  and """ + local_des + """ and pt.valuation_kardex='real_time'
                          order by product_id,create_date asc)as sl
                    ---- para las entrada
                    UNION 
                     -------------unimos salidas
                    select id,create_date,product_id,name,company_id, u_entrada,u_salida,costo_unit
                    ,v_entrada,v_salida,v_saldo,state,origin,reference,loc_ori,loc_des,
                    usage,loc_des_scrap,complete_name,ubicacion,create_uid,inventory_id,picking_id,tipo,account,stock,date_order,scrap_id  
                    from
                       (
                       select sm.id,svl.create_date,sm.product_id,sm.name,sm.company_id,(sm.product_qty * 0) as u_entrada, (sm.product_qty*-1) as u_salida,
                       svl.unit_cost as costo_unit,(1 * 0)as v_entrada,(svl.value*-1) as v_salida,(-1 *0) as v_saldo,sm.state,sm.origin,sm.reference,
                       sl.usage as loc_ori,sl2.usage as loc_des,sl.usage,sl2.scrap_location as loc_des_scrap,sl.complete_name,(sm.location_id)as ubicacion,sm.create_uid,cast(null as int) as inventory_id,sm.picking_id,
                            'OUT'::text as tipo,am.id as account,sm.id as stock,sm.date as date_order,ss.id as scrap_id 
                              from stock_valuation_layer svl
                              inner join stock_move sm on svl.stock_move_id = sm.id
                              inner join stock_location sl on sm.location_id=sl.id
                              inner join stock_location sl2 on sm.location_dest_id=sl2.id 
                              inner join product_product pp on sm.product_id = pp.id
                              inner join product_template pt on pp.product_tmpl_id = pt.id
                              inner join account_move am on sm.id = am.stock_move_id 
                              left join stock_scrap ss on sm.id=ss.move_id
                              where """ + productos + """ and sm.state='done' and """ + location_id + """ and pt.valuation_kardex='real_time'
                            order by product_id,create_date asc
                      )sl
            UNION
          select id,create_date,product_id,name,company_id,u_entrada,u_salida,costo_unit,v_entrada,v_salida,v_saldo,state,origin,
          reference,loc_ori,loc_des,usage,loc_des_scrap,complete_name,ubicacion,create_uid,inventory_id,picking_id,tipo,
          account,stock,date_order,scrap_id
          from(
    select
        sm.id,
        sm.date as create_date,
        sm.product_id,
        sm.name,
        sm.company_id,
        (sm.product_qty * 0) as u_entrada,
        (sm.product_qty *-1) as u_salida,
        sm.price_unit as costo_unit,
        (1 * 0)as v_entrada,
        (sm.product_qty*sm.price_unit) *-1 as v_salida,
        (-1 * 0) as v_saldo,
        sm.state,
        sm.origin,
        sm.reference,
        sl.usage as loc_ori,
        sl2.usage as loc_des,
        sl.usage,
        sl2.scrap_location as loc_des_scrap,
        sl.complete_name,
        (sm.location_id)as ubicacion,
        sm.create_uid,
        cast(null as int) as inventory_id,
        sm.picking_id,
        'OUT_INT'::text as tipo,
        cast(null as int) as account,
        sm.id as stock,
        sm.date as date_order,
        ss.id as scrap_id
    from  stock_move sm
    inner join stock_location sl on sm.location_dest_id=sl.id
                          inner join stock_location sl2 on sm.location_id=sl2.id
                          inner join product_product pp on sm.product_id = pp.id
                          inner join product_template pt on pp.product_tmpl_id = pt.id
                          left join stock_scrap ss on sm.id=ss.move_id
                          where """ + productos + """ and sm.state='done' and sl.usage='internal' and sl2.usage='internal'  and """ + location_id + """ and pt.valuation_kardex='real_time'
        order by product_id,create_date asc)sl
                      -------------- para ajustes de costos
        UNION

          select id,create_date,product_id,name,company_id,u_entrada,u_salida,costo_unit,v_entrada,v_salida,v_saldo,state,origin,reference,
          loc_ori,loc_des,usage,loc_des_scrap,complete_name,
          ubicacion,create_uid,inventory_id,picking_id,tipo,account,stock,date_order,scrap_id
          from (
          select am.id,svl.create_date ,svl.product_id,svl.description as name,am.company_id,(1*0)as u_entrada,(-1*0)as u_salida,
          (1*0) costo_unit,case when svl.value > 0 then svl.value else 0 end as v_entrada,case when svl.value < 0 then (svl.value*-1) else 0 end as v_salida,
          case when svl.value < 0 then (-1 *0) else (1*0) end as v_saldo,am.state,cast(null as varchar(255))as origin,svl.description reference,
          null as loc_ori,null as loc_des,cast(null as varchar(255)) as usage,null::boolean as loc_des_scrap,cast(null as varchar(255)) as complete_name,
          cast(null as int) as ubicacion, am.create_uid,cast(null as int) as inventory_id, cast(null as int) as picking_id,
          'AJUST'::text as tipo, am.id as account,cast(null as int) as stock,am.create_date as date_order,cast(null as int) as scrap_id
          from stock_valuation_layer svl inner join account_move am on svl.account_move_id = am.id
          where am.state ='posted' and """ + productos_ajus + """ and """ + ajustes + """ and svl.stock_move_id is null
          order by svl.product_id,svl.create_date asc
          )sl
                ) as kardex order by product, create_date asc -------2)TERMINA EL 2DO SELECT
            )as kardex2   ------1)TERMINA EL PRIMER SELECT
                    """
        return query_movimiento

    def _moviento_completo_producto(self):
        local_des = ""
        location_id = ""
        ajustes = ""
        if self.establishment:
            local_des = "sm.location_dest_id in (select sl.id from stock_location sl where sl.usage = 'internal' and sl.active is true and sl.establishment =%s)"
            location_id = "sm.location_id in (select sl.id from stock_location sl where sl.usage = 'internal' and sl.active is true and sl.establishment =%s)"

        productos = "sm.product_id = %s"
        productos_ajus = "svl.product_id = %s"
        # search_change_price = "Precio estándar cambiado:%s"
        if self.type_kardex == 'units':
            ajustes = "svl.quantity > 0"
        else:
            ajustes = "svl.quantity=0"

        query_movimiento = """
     select id,create_date,company_id, product,nombre,u_entrada,
     u_salida,u_saldo,costo_unit,v_entrada,v_salida,
    v_saldo,state,origin,reference,loc_ori,loc_des,usage,loc_des_scrap,complete_name,ubicacion,inventory_id ,picking_id,tipo,account,stock,date_order,scrap_id  
    from (
    -------------3)Comienza el segundo select
        select id,create_date,company_id ,product_id as product,
      name as nombre,u_entrada,u_salida,
             SUM(u_entrada-u_salida)over (order by create_date asc)as u_saldo,
             costo_unit,v_entrada,v_salida,
        SUM(v_entrada-v_salida)over (order by create_date asc)as  v_saldo,state
      ,origin,reference,loc_ori,loc_des,usage,loc_des_scrap,
            complete_name,ubicacion,inventory_id ,picking_id,tipo,account,stock,date_order,scrap_id  
          from (

    --------------- EMPIEZA LA UNION 

            --- unimos entradas
            select id,create_date,product_id,name,company_id, u_entrada,u_salida,  
        costo_unit
            , v_entrada,v_salida,v_saldo,state,origin,reference,loc_ori,loc_des,
            usage,loc_des_scrap,complete_name,ubicacion,create_uid,inventory_id,picking_id,tipo,account,stock, date_order,scrap_id   
            from 
            (
                select sm.id,svl.create_date,sm.product_id,sm.name,sm.company_id,case when svl.stock_landed_cost_id is null then sm.product_qty else 0 end as u_entrada,(sm.product_qty * 0)u_salida,
               svl.unit_cost as costo_unit,svl.value as v_entrada,(-1 * 0) as v_salida,(1 *0) as v_saldo,sm.state,sm.origin,sm.reference,
                sl2.usage as loc_ori,sl.usage as loc_des,sl.usage,sl.scrap_location as loc_des_scrap,sl.complete_name,(sm.location_dest_id)as ubicacion,sm.create_uid,cast(null as int) as inventory_id,case when svl.stock_landed_cost_id is null then sm.picking_id else cast(null as int) end as picking_id,
                'IN'::text as tipo,am.id as account,sm.id as stock, sm.date as date_order,ss.id as scrap_id
                  from stock_move sm  
                  inner join stock_valuation_layer svl on svl.stock_move_id = sm.id
                  inner join stock_location sl on sm.location_dest_id=sl.id 
                  inner join stock_location sl2 on sm.location_id=sl2.id 
                  inner join product_product pp on sm.product_id = pp.id
                  inner join product_template pt on pp.product_tmpl_id = pt.id
                  inner join account_move am on sm.id = am.stock_move_id 
                  left join stock_scrap ss on sm.id=ss.move_id
                  where """ + productos + """ and sm.state='done' and """ + local_des + """ and pt.valuation_kardex='real_time'

                order by product_id,create_date asc 
            )as    sl   
            UNION
                    ----Transferencia interna
                     select id,create_date,product_id,name,company_id,u_entrada,u_salida,costo_unit,v_entrada,v_salida,
                     v_saldo,state,origin,reference,loc_ori,loc_des,usage,loc_des_scrap,complete_name,ubicacion,create_uid,
                     inventory_id,picking_id,tipo,account,stock,date_order,scrap_id 
                     from (select sm.id,sm.date as create_date ,sm.product_id,sm.name,sm.company_id,sm.product_qty as u_entrada,(sm.product_qty * 0) as u_salida,
    sm.price_unit as costo_unit,(sm.product_qty*sm.price_unit) as v_entrada,(-1 * 0) as v_salida,(1 *0) as v_saldo,sm.state,sm.origin,sm.reference,
                        sl2.usage as loc_ori,sl.usage as loc_des,sl.usage,sl.scrap_location as loc_des_scrap,sl.complete_name,(sm.location_dest_id)as ubicacion,sm.create_uid,cast(null as int) as inventory_id,sm.picking_id,
                        'IN_INT'::text as tipo,cast(null as int) as account,sm.id as stock,sm.date as date_order,ss.id as scrap_id
                          from  stock_move sm
                          inner join stock_location sl on sm.location_dest_id=sl.id
                          inner join stock_location sl2 on sm.location_id=sl2.id
                          inner join product_product pp on sm.product_id = pp.id
                          inner join product_template pt on pp.product_tmpl_id = pt.id
                          left join stock_scrap ss on sm.id=ss.move_id
                          where """ + productos + """ and sm.state='done' and sl.usage='internal' and sl2.usage='internal'  and """ + local_des + """ and pt.valuation_kardex='real_time'
                          order by product_id,create_date asc)as sl

            ---- para las entrada

            UNION

             -------------unimos salidas
            select id,create_date,product_id,name,company_id, u_entrada,u_salida,costo_unit
            ,v_entrada,v_salida,v_saldo,state,origin,reference,loc_ori,loc_des,
            usage,loc_des_scrap,complete_name,ubicacion,create_uid,inventory_id,picking_id,tipo,account,stock,date_order,scrap_id  
            from
               (
                    select sm.id,svl.create_date,sm.product_id,sm.name,sm.company_id,(sm.product_qty * 0) as u_entrada,sm.product_qty as u_salida,
                    svl.unit_cost as costo_unit,(-1 * 0)as v_entrada,(svl.value*-1) as v_salida,(-1 *0) as v_saldo,sm.state,sm.origin,sm.reference,
                    sl.usage as loc_ori,sl2.usage as loc_des,sl.usage,sl2.scrap_location as loc_des_scrap,sl.complete_name,(sm.location_id)as ubicacion,sm.create_uid,cast(null as int) as inventory_id,sm.picking_id,
                    'OUT'::text as tipo,am.id as account,sm.id as stock,sm.date as date_order,ss.id as scrap_id 
                      from stock_move sm  
                      inner join stock_valuation_layer svl on svl.stock_move_id = sm.id
                      inner join stock_location sl on sm.location_id=sl.id
                      inner join stock_location sl2 on sm.location_dest_id=sl2.id 
                      inner join product_product pp on sm.product_id = pp.id
                      inner join product_template pt on pp.product_tmpl_id = pt.id
                      inner join account_move am on sm.id = am.stock_move_id 
                      left join stock_scrap ss on sm.id=ss.move_id
                      where """ + productos + """ and sm.state='done' and """ + location_id + """ and pt.valuation_kardex='real_time'
                    order by product_id,create_date asc
              )sl
              UNION
          select id,create_date,product_id,name,company_id,u_entrada,u_salida,costo_unit,v_entrada,v_salida,v_saldo,state,origin,
          reference,loc_ori,loc_des,usage,loc_des_scrap,complete_name,ubicacion,create_uid,inventory_id,picking_id,tipo,
          account,stock,date_order,scrap_id
          from(
    select
        sm.id,
        sm.date as create_date,
        sm.product_id,
        sm.name,
        sm.company_id,
        (sm.product_qty * 0) as u_entrada,
        (sm.product_qty) as u_salida,
        sm.price_unit as costo_unit,
        (-1 * 0)as v_entrada,
        (sm.product_qty*sm.price_unit)*-1 as v_salida,
        (-1 * 0) as v_saldo,
        sm.state,
        sm.origin,
        sm.reference,
        sl.usage as loc_ori,
        sl2.usage as loc_des,
        sl.usage,
        sl2.scrap_location as loc_des_scrap,
        sl.complete_name,
        (sm.location_id)as ubicacion,
        sm.create_uid,
        cast(null as int) as inventory_id,
        sm.picking_id,
        'OUT_INT'::text as tipo,
        cast(null as int) as account,
        sm.id as stock,
        sm.date as date_order,
        ss.id as scrap_id
    from  stock_move sm
    inner join stock_location sl on sm.location_dest_id=sl.id
                          inner join stock_location sl2 on sm.location_id=sl2.id
                          inner join product_product pp on sm.product_id = pp.id
                          inner join product_template pt on pp.product_tmpl_id = pt.id
                          left join stock_scrap ss on sm.id=ss.move_id
                          where """ + productos + """ and sm.state='done' and sl.usage='internal' and sl2.usage='internal'  and """ + location_id + """ and pt.valuation_kardex='real_time'
        order by product_id,create_date asc)sl
              -------------- para ajustes de costos
            UNION

          select id,create_date,product_id,name,company_id,u_entrada,u_salida,costo_unit,v_entrada,v_salida,v_saldo,state,origin,reference,
          loc_ori,loc_des,usage,loc_des_scrap,complete_name,
          ubicacion,create_uid,inventory_id,picking_id,tipo,account,stock,date_order,scrap_id
          from (
          select am.id as id,svl.create_date ,svl.product_id,svl.description as name,am.company_id,(1*0)as u_entrada,(1*0)as u_salida,
          (1*0) costo_unit,case when svl.value > 0 then svl.value else 0 end as v_entrada,case when svl.value < 0 then (svl.value*-1) else 0 end as v_salida,
          case when svl.value < 0 then (-1 *0) else (1*0) end as v_saldo,am.state,cast(null as varchar(255))as origin,svl.description reference,
          null as loc_ori,null as loc_des,cast(null as varchar(255)) as usage,null::boolean as loc_des_scrap,cast(null as varchar(255)) as complete_name,
          cast(null as int) as ubicacion, am.create_uid,cast(null as int) as inventory_id, cast(null as int) as picking_id,
          'AJUST'::text as tipo, am.id as account,cast(null as int) as stock,am.create_date as date_order,cast(null as int) as scrap_id
          from stock_valuation_layer svl inner join account_move am on svl.account_move_id = am.id
          where am.state ='posted' and """ + productos_ajus + """ and """ + ajustes + """ and svl.stock_move_id is null
          order by svl.product_id,svl.create_date asc
          )sl

        ) as kardex order by product, create_date asc -------2)TERMINA EL 2DO SELECT
    )as kardex2   ------1)TERMINA EL PRIMER SELECT
            """
        return query_movimiento

    def _mov_all_multiestablisment(self):
        local_des = ""
        location_id = ""
        if self.establishment:
            local_des = "sm.location_dest_id in (select sl.id from stock_location sl where sl.usage = 'internal' and sl.active is true)"
            location_id = "sm.location_id in (select sl.id from stock_location sl where sl.usage = 'internal' and sl.active is true)"

        productos = "sm.product_id = %s"
        query_movimiento = """
     select id,create_date,company_id, product,nombre,u_entrada,
     u_salida,u_saldo,costo_unit,v_entrada,v_salida,
    v_saldo,state,origin,reference,loc_ori,loc_des,usage,loc_des_scrap,complete_name,ubicacion,inventory_id ,picking_id,tipo,account,stock,date_order,scrap_id  
    from (
    -------------3)Comienza el segundo select
        select id,create_date,company_id ,product_id as product,
      name as nombre,u_entrada,u_salida,
             SUM(u_entrada-u_salida)over (order by create_date asc)as u_saldo,
             costo_unit,v_entrada,v_salida,
        SUM(v_entrada-v_salida)over (order by create_date asc)as  v_saldo,state
      ,origin,reference,loc_ori,loc_des,usage,loc_des_scrap,
            complete_name,ubicacion,inventory_id ,picking_id,tipo,account,stock,date_order,scrap_id  
          from (

    --------------- EMPIEZA LA UNION 

            --- unimos entradas
            select id,create_date,product_id,name,company_id, u_entrada,u_salida,  
        costo_unit
            , v_entrada,v_salida,v_saldo,state,origin,reference,loc_ori,loc_des,
            usage,loc_des_scrap,complete_name,ubicacion,create_uid,inventory_id,picking_id,tipo,account,stock, date_order,scrap_id   
            from 
            (
                select sm.id,svl.create_date,sm.product_id,sm.name,sm.company_id,case when svl.stock_landed_cost_id is null then sm.product_qty else 0 end as u_entrada,(sm.product_qty * 0)u_salida,
               svl.unit_cost as costo_unit,svl.value as v_entrada,(-1 * 0) as v_salida,(1 *0) as v_saldo,sm.state,sm.origin,sm.reference,
                sl2.usage as loc_ori,sl.usage as loc_des,sl.usage,sl.scrap_location as loc_des_scrap,sl.complete_name,(sm.location_dest_id)as ubicacion,sm.create_uid,cast(null as int) as inventory_id,case when svl.stock_landed_cost_id is null then sm.picking_id else cast(null as int) end as picking_id,
                'IN'::text as tipo,am.id as account,sm.id as stock, sm.date as date_order,ss.id as scrap_id
                  from stock_move sm  
                  inner join stock_valuation_layer svl on svl.stock_move_id = sm.id
                  inner join stock_location sl on sm.location_dest_id=sl.id 
                  inner join stock_location sl2 on sm.location_id=sl2.id 
                  inner join product_product pp on sm.product_id = pp.id
                  inner join product_template pt on pp.product_tmpl_id = pt.id
                  inner join account_move am on sm.id = am.stock_move_id 
                  left join stock_scrap ss on sm.id=ss.move_id
                  where """ + productos + """ and sm.state='done' and """ + local_des + """ and pt.valuation_kardex='real_time'

                order by product_id,create_date asc 
            )as    sl   
            UNION
                    ----Transferencia interna
                     select id,create_date,product_id,name,company_id,u_entrada,u_salida,costo_unit,v_entrada,v_salida,
                     v_saldo,state,origin,reference,loc_ori,loc_des,usage,loc_des_scrap,complete_name,ubicacion,create_uid,
                     inventory_id,picking_id,tipo,account,stock,date_order,scrap_id 
                     from (select sm.id,sm.date as create_date ,sm.product_id,sm.name,sm.company_id,sm.product_qty as u_entrada,(sm.product_qty * 0) as u_salida,
    sm.price_unit as costo_unit,(sm.product_qty*sm.price_unit)as v_entrada,(-1 * 0) as v_salida,(1 *0) as v_saldo,sm.state,sm.origin,sm.reference,
                        sl2.usage as loc_ori,sl.usage as loc_des,sl.usage,sl.scrap_location as loc_des_scrap,sl.complete_name,(sm.location_dest_id)as ubicacion,sm.create_uid,cast(null as int) as inventory_id,sm.picking_id,
                        'IN_INT'::text as tipo,cast(null as int) as account,sm.id as stock,sm.date as date_order,ss.id as scrap_id
                          from  stock_move sm
                          inner join stock_location sl on sm.location_dest_id=sl.id
                          inner join stock_location sl2 on sm.location_id=sl2.id
                          inner join product_product pp on sm.product_id = pp.id
                          inner join product_template pt on pp.product_tmpl_id = pt.id
                          left join stock_scrap ss on sm.id=ss.move_id
                          where """ + productos + """ and sm.state='done' and sl.usage='internal' and sl2.usage='internal'  and """ + local_des + """ and pt.valuation_kardex='real_time'
                          order by product_id,create_date asc)as sl

            ---- para las entrada

            UNION

             -------------unimos salidas
            select id,create_date,product_id,name,company_id, u_entrada,u_salida,costo_unit
            ,v_entrada,v_salida,v_saldo,state,origin,reference,loc_ori,loc_des,
            usage,loc_des_scrap,complete_name,ubicacion,create_uid,inventory_id,picking_id,tipo,account,stock,date_order,scrap_id  
            from
               (
                    select sm.id,svl.create_date,sm.product_id,sm.name,sm.company_id,(sm.product_qty * 0) as u_entrada,sm.product_qty as u_salida,
                    svl.unit_cost as costo_unit,(-1 * 0)as v_entrada,(svl.value*-1) as v_salida,(-1 *0) as v_saldo,sm.state,sm.origin,sm.reference,
                    sl.usage as loc_ori,sl2.usage as loc_des,sl.usage,sl2.scrap_location as loc_des_scrap,sl.complete_name,(sm.location_id)as ubicacion,sm.create_uid,cast(null as int) as inventory_id,sm.picking_id,
                    'OUT'::text as tipo,am.id as account,sm.id as stock,sm.date as date_order,ss.id as scrap_id 
                      from stock_move sm  
                      inner join stock_valuation_layer svl on svl.stock_move_id = sm.id
                      inner join stock_location sl on sm.location_id=sl.id
                      inner join stock_location sl2 on sm.location_dest_id=sl2.id 
                      inner join product_product pp on sm.product_id = pp.id
                      inner join product_template pt on pp.product_tmpl_id = pt.id
                      inner join account_move am on sm.id = am.stock_move_id 
                      left join stock_scrap ss on sm.id=ss.move_id
                      where """ + productos + """ and sm.state='done' and """ + location_id + """ and pt.valuation_kardex='real_time'
                    order by product_id,create_date asc
              )sl
              UNION
          select id,create_date,product_id,name,company_id,u_entrada,u_salida,costo_unit,v_entrada,v_salida,v_saldo,state,origin,
          reference,loc_ori,loc_des,usage,loc_des_scrap,complete_name,ubicacion,create_uid,inventory_id,picking_id,tipo,
          account,stock,date_order,scrap_id
          from(
    select
        sm.id,
        sm.date as create_date,
        sm.product_id,
        sm.name,
        sm.company_id,
        (sm.product_qty * 0) as u_entrada,
        (sm.product_qty) as u_salida,
        sm.price_unit as costo_unit,
        (-1 * 0)as v_entrada,
        (sm.product_qty*sm.price_unit)*-1 as v_salida,
        (-1 * 0) as v_saldo,
        sm.state,
        sm.origin,
        sm.reference,
        sl.usage as loc_ori,
        sl2.usage as loc_des,
        sl.usage,
        sl2.scrap_location as loc_des_scrap,
        sl.complete_name,
        (sm.location_id)as ubicacion,
        sm.create_uid,
        cast(null as int) as inventory_id,
        sm.picking_id,
        'OUT_INT'::text as tipo,
        cast(null as int) as account,
        sm.id as stock,
        sm.date as date_order,
        ss.id as scrap_id
    from  stock_move sm
    inner join stock_location sl on sm.location_dest_id=sl.id
                          inner join stock_location sl2 on sm.location_id=sl2.id
                          inner join product_product pp on sm.product_id = pp.id
                          inner join product_template pt on pp.product_tmpl_id = pt.id
                          left join stock_scrap ss on sm.id=ss.move_id
                          where """ + productos + """ and sm.state='done' and sl.usage='internal' and sl2.usage='internal'  and """ + location_id + """ and pt.valuation_kardex='real_time'
        order by product_id,create_date asc)sl
        ) as kardex order by product, create_date asc -------2)TERMINA EL 2DO SELECT
    )as kardex2   ------1)TERMINA EL PRIMER SELECT
            """
        return query_movimiento

    @api.model
    def get_name_txt(self, options):
        account_period = datetime.datetime.strptime(options["date_to"], "%Y-%m-%d")
        company = self.env["res.company"].browse(options["company_id"])
        data = {"company_ruc": company.vat, "account_period": account_period}
        if options["type_kardex"] == 'units':
            txt_name = utils.get_name_units(data)
        else:
            txt_name = utils.get_name_valued(data)

        return txt_name

    @api.model
    def get_name_xlsx(self, options):
        account_period = datetime.datetime.strptime(options['date_to'], "%Y-%m-%d")
        if options['type_kardex'] == 'units':
            xlsx_name = "%s%s%s%s%s" % (
                _("PHYSICAL KARDEX "), ' ', str(_(account_period.strftime('%B'))).upper(), ' ', account_period.year)
        else:
            xlsx_name = "%s%s%s%s%s" % (
                _("VALORIZED KARDEX "), ' ', str(_(account_period.strftime('%B'))).upper(), ' ', account_period.year)

        return xlsx_name

    def get_report_filename(self, options):
        if 'txt' in options:
            report_name = self.get_name_txt(options)
        elif 'excel' in options:
            report_name = self.get_name_xlsx(options)
        return report_name

    @api.model
    def _get_report_name(self, options):
        if options['type_kardex'] == 'units':
            name_sheet = _('PHYSICAL KARDEX')
        else:
            name_sheet = _('VALORIZED KARDEX')
        return name_sheet

    def get_header(self, options):
        columns = self._get_columns_name(options)
        return [columns]

    def _get_columns_name(self, options):
        if options['type_kardex'] == 'units':
            return utils.column_excel_unit()
        else:
            return utils.column_excel_val()

    def get_xlsx(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self._get_report_name(data)[:31])

        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'align': 'center', })
        detail_general = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 10, 'font_color': '#666666', 'align': 'center'})
        line_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'align': 'start', })
        name_bold = workbook.add_format({'font_name': 'Arial', 'bold': True})
        format_date = workbook.add_format({'num_format': 'dd/mm/yy'})
        format_date_init = workbook.add_format(
            {'num_format': 'dd/mm/yy', 'font_name': 'Arial', 'bold': True, 'bottom': 2})
        format_saldo_init = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})

        # Set the first column width to 50
        # sheet.set_column(0, 0, 5)
        sheet.merge_range('E2:H2' if data['type_kardex'] == 'units' else 'H2:K2',
                          _('PHYSICAL KARDEX') if data['type_kardex'] == 'units' else _('VALORIZED KARDEX'),
                          title_style)
        sheet.merge_range('E3:H3' if data['type_kardex'] == 'units' else 'H3:K3', _('General detail'), detail_general)

        company = self.env.user.company_id
        image_data = io.BytesIO(base64.b64decode(company.logo))  # to convert it to base64 file
        sheet.insert_image('A3', 'logo', {'image_data': image_data, 'x_scale': 0.2, 'y_scale': 0.2})
        sheet.merge_range('D4:E4', _('Ruc:'), name_bold)
        sheet.merge_range('F4:G4', company.vat)
        sheet.merge_range('D5:E5', _('Address:'), name_bold)
        sheet.merge_range('F5:K5', company.street)
        sheet.merge_range('D6:E6', _('Mail:'), name_bold)
        sheet.merge_range('F6:G6', company.email)
        sheet.merge_range('H4:I4', _('Business name:'), name_bold)
        sheet.merge_range('J4:K4', company.name)
        sheet.merge_range('H6:I6', _('Phone:'), name_bold)
        sheet.merge_range('J6:K6', company.phone)
        sheet.merge_range('A8:K8' if data['type_kardex'] == 'units' else 'A8:P8',
                          _('INVENTORY RECORD IN PHYSICAL UNITS') if data[
                                                                         'type_kardex'] == 'units' else _(
                              'RECORD OF PERMANENT INVENTORY VALUED'),
                          line_style)
        sheet.merge_range('A9:C9', _('PERIOD:'), name_bold)
        sheet.merge_range('D9:F9',
                          _("from:") + " " + data['date_from'] + " " + _("to:") + " " + data['date_to'])
        sheet.merge_range('A10:C10', _('RUC:'), name_bold)
        sheet.merge_range('D10:F10', company.vat)
        sheet.merge_range('A11:C11', _('BUSINESS NAME:'), name_bold)
        sheet.merge_range('D11:F11', company.name)
        sheet.merge_range('A12:C12', _('ESTABLISHMENT:'), name_bold)
        sheet.merge_range('D12:F12', str(data['establishment']['name']).upper())
        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 15)
        sheet.set_column('L:L', 15)
        sheet.set_column('M:M', 15)
        sheet.set_column('N:N', 15)
        sheet.set_column('O:O', 15)
        sheet.set_column('P:P', 15)

        y_offset = 13

        for row in self.get_header(data):
            x = 0
            for column in row:
                colspan = column.get('colspan', 1)
                header_label = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                if colspan == 1:
                    sheet.write(y_offset, x, header_label, title_style)
                else:
                    sheet.merge_range(y_offset, x, y_offset, x + colspan - 1, header_label, title_style)
                x += colspan
            y_offset += 1

        # lines = self._get_lines(data)
        precision = self.env.user.company_id.currency_id.decimal_places or 2
        precision_cost = self.env['decimal.precision'].sudo().search([('name', '=', 'Product Price')], limit=1)
        units_cost = self.env['decimal.precision'].sudo().search([('name', '=', 'Product Unit of Measure')], limit=1)

        todo_reporte = self.env['kardex.line'].sudo().search(
            [('kardex_line', '=', data['kardex_id']), ('type_kardex', '=', data['type_kardex'])])

        tf = 0
        for todfact in todo_reporte:
            ini = 14
            if data['type_kardex'] == 'units':
                type_operation_move = ''
                # if todfact.inventory_id:
                #     if todfact.inventory_id.it_type_operation:
                #         type_operation_move = todfact.inventory_id.it_type_operation.code + '-' + todfact.inventory_id.it_type_operation.name
                # if todfact.picking_id:
                #     if todfact.picking_id.it_type_operation:
                #         type_operation_move = todfact.picking_id.it_type_operation.code + '-' + todfact.picking_id.it_type_operation.name
                # if todfact.scrap_id:
                #     if todfact.scrap_id.it_type_operation:
                #         type_operation_move = todfact.scrap_id.it_type_operation.code + '-' + todfact.scrap_id.it_type_operation.name
                # if todfact.type_transaction_id:
                #     type_operation_move = todfact.type_transaction_id.code + '-' + todfact.type_transaction_id.name
                reference_code = ''
                # if todfact.type_document_move:
                #     reference_code += todfact.type_document_move + '-'
                # if todfact.series_document_move:
                #     reference_code += todfact.series_document_move + '-'
                # if todfact.number_document_move:
                #     reference_code += todfact.number_document_move

                sheet.write(tf + ini, 0, todfact.account_period,
                            format_date_init if todfact.level == 1 else format_date)
                # sheet.write(tf + ini, 1, todfact.stock_move.id if todfact.stock_move else todfact.account_move.id)
                sheet.write(tf + ini, 1, todfact.account_move.id if todfact.account_move else str(
                    "M-%s" % str(todfact.stock_move.id)), format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 2, todfact.reference, format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 3, data['establishment']['name'], format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 4, todfact.product_id.display_name,
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 5, todfact.product_id.uom_id.name,
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 6, reference_code, format_saldo_init if todfact.level == 1 else '')
                # sheet.write(tf + ini, 7, todfact.series_document_move, format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 7, type_operation_move, format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 8, float_round(abs(todfact.cant_input), precision_digits=units_cost.digits),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 9, float_round(abs(todfact.cant_ouput), precision_digits=units_cost.digits),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 10,
                            float_round(abs(todfact.cant_saldo_final), precision_digits=units_cost.digits),
                            format_saldo_init if todfact.level == 1 else '')
            else:
                type_operation_move = ''
                # if todfact.inventory_id:
                #     if todfact.inventory_id.it_type_operation:
                #         type_operation_move = todfact.inventory_id.it_type_operation.code + '-' + todfact.inventory_id.it_type_operation.name
                # if todfact.picking_id:
                #     if todfact.picking_id.it_type_operation:
                #         type_operation_move = todfact.picking_id.it_type_operation.code + '-' + todfact.picking_id.it_type_operation.name
                # if todfact.scrap_id:
                #     if todfact.scrap_id.it_type_operation:
                #         type_operation_move = todfact.scrap_id.it_type_operation.code + '-' + todfact.scrap_id.it_type_operation.name
                # if todfact.type_transaction_id:
                #     type_operation_move = todfact.type_transaction_id.code + '-' + todfact.type_transaction_id.name
                reference_code = ''
                # if todfact.type_document_move:
                #     reference_code += todfact.type_document_move + '-'
                # if todfact.series_document_move:
                #     reference_code += todfact.series_document_move + '-'
                # if todfact.number_document_move:
                #     reference_code += todfact.number_document_move
                sheet.write(tf + ini, 0, todfact.account_period,
                            format_date_init if todfact.level == 1 else format_date)
                # sheet.write(tf + ini, 1, todfact.stock_move.id if todfact.stock_move else todfact.account_move.id)
                sheet.write(tf + ini, 1, todfact.account_move.id if todfact.account_move else str(
                    "M-%s" % str(todfact.stock_move.id)), format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 2, todfact.reference, format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 3, data['establishment']['name'], format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 4, todfact.product_id.display_name,
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 5, todfact.product_id.uom_id.name,
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 6, reference_code, format_saldo_init if todfact.level == 1 else '')
                # sheet.write(tf + ini, 7, todfact.series_document_move, format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 7, type_operation_move, format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 8, float_round(abs(todfact.cant_input), precision_digits=precision),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 9,
                            float_round(abs(todfact.cost_unit_input), precision_digits=precision_cost.digits or 2),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 10, float_round(abs(todfact.cost_total_input), precision_digits=precision),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 11, float_round(abs(todfact.cant_ouput), precision_digits=precision),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 12,
                            float_round(abs(todfact.cost_unit_ouput), precision_digits=precision_cost.digits or 2),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 13, float_round(abs(todfact.cost_total_ouput), precision_digits=precision),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 14, float_round(abs(todfact.cant_saldo_final), precision_digits=precision),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 15, float_round(abs(todfact.cost_unit_saldo_final),
                                                      precision_digits=precision_cost.digits or 2),
                            format_saldo_init if todfact.level == 1 else '')
                sheet.write(tf + ini, 16, float_round(abs(todfact.cost_saldo_final), precision_digits=precision),
                            format_saldo_init if todfact.level == 1 else '')
                # sheet.write(tf + ini, 17, todfact.cost_saldo_final)
            tf += 1

        # write all data rows

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def export_excel(self):
        if self.date_from > self.date_to:
            raise UserError(_("The Start date cannot be less than the end date "))
        else:
            data = {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'establishment': {'id': self.establishment.id, 'name': self.establishment.name},
                'type_kardex': self.type_kardex,
                'kardex_id': self.id,
                'excel': 'excel'
            }
            return {
                'type': 'kardex_xlsx_txt',
                'report_type': 'kardex_xlsx_txt',
                'data': {
                    'model': 'kardex',
                    'options': json.dumps(data, default=date_utils.json_default),
                    'output_format': 'xlsx',
                    'report_name': 'Excel Report',
                }
            }

    def get_txt(self, options):
        content = ""
        moves_json = self.get_moves_json(options)
        if options['type_kardex'] == 'units':
            for move in moves_json:
                content += utils.data_txt_units(move)
        else:
            for move in moves_json:
                content += utils.data_txt_valued(move)
        return content

    @api.model
    def get_moves_json(self, options):
        moves_json = []
        return moves_json

    def export_txt(self):
        if self.date_from > self.date_to:
            raise UserError(_("The Start date cannot be less than the end date "))
        else:
            data = {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'establishment': {'id': self.establishment.id, 'name': self.establishment.name},
                'type_kardex': self.type_kardex,
                'kardex_id': self.id,
                'excel': 'excel'
            }
            return {
                'type': 'kardex_xlsx_txt',
                'report_type': 'kardex_xlsx_txt',
                'data': {
                    'model': 'kardex',
                    'options': json.dumps(data, default=date_utils.json_default),
                    'output_format': 'txt',
                    'report_name': 'txt report',
                }
            }

