# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from datetime import datetime, date
import openerp.addons.decimal_precision as dp
import time
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _
import sys
from openerp import SUPERUSER_ID

class product_supplierinfo_add_warehouse(osv.osv):
    _inherit = 'product.supplierinfo'
    _columns = {
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心'),
    }
product_supplierinfo_add_warehouse()

class procurement_order(osv.osv):
    _inherit = 'procurement.order'

    _columns = {
        'need_purchase':fields.boolean(u'需采购'),
    }

    _defaults = {
        'need_purchase': False,
    }

    def _get_warehouse_and_supplier(self, cr, uid, form, context=None):
        """
        Get Location ID and Return , Warehouse ID and Supplier ID
        如果product.supplierinfo存在该物流中心相应供应商，取出，如果没有，按正常程序取
        
        """
        location_id = form.location_id.id
        prod_tmpl_id = form.product_id.product_tmpl_id.id
        warehouse_obj = self.pool.get('stock.warehouse')
        warehouse_id = warehouse_obj.search(cr, uid, [
            ('lot_stock_id', '=', location_id)
            ], context=context)
        if warehouse_id:
            suppinfo_obj = self.pool.get("product.supplierinfo")
            suppinfo_id = suppinfo_obj.search(cr, uid, [
                ('product_id', '=', prod_tmpl_id),
                ('warehouse_id', '=', warehouse_id[0]),
                ('sequence', '=', 1)
                ], context=context)
            if not suppinfo_id:
                suppinfo_id = suppinfo_obj.search(cr, uid, [
                    ('product_id', '=', prod_tmpl_id),
                    ('warehouse_id', '=', warehouse_id[0]),
                ], context=context)
            if not suppinfo_id:
                suppinfo_id = suppinfo_obj.search(cr, uid, [
                    ('product_id', '=', prod_tmpl_id),
                    ('sequence', '=', 1),
                ], context=context)
            if suppinfo_id:
                seller_id =  suppinfo_obj.browse(cr, uid, suppinfo_id[0], context=context).name
                return (warehouse_id[0], seller_id)
            else:
                return (warehouse_id[0], form.product_id.seller_id)
        else:
            warehouse_id = warehouse_obj.search(cr, uid, [], context=context)
            return (warehouse_id[0], form.product_id.seller_id)


    def create_automatic_op(self, cr, uid, context=None):
        """
        Create procurement of  virtual stock < 0

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        proc_obj = self.pool.get('procurement.order')
        warehouse_obj = self.pool.get('stock.warehouse')
        wf_service = netsvc.LocalService("workflow")

        warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)
        products_ids = product_obj.search(cr, uid, [], order='id', context=context)

        for warehouse in warehouse_obj.browse(cr, uid, warehouse_ids, context=context):
            context['warehouse'] = warehouse
            # Here we check products availability.
            # We use the method 'read' for performance reasons, because using the method 'browse' may crash the server.
            for product_read in product_obj.read(cr, uid, products_ids, ['virtual_available', 'is_group_product'], context=context):
                if product_read['is_group_product']:
                    continue
                
                if product_read['virtual_available'] >= 0.0:
                    continue

                product = product_obj.browse(cr, uid, [product_read['id']], context=context)[0]
                if product.supply_method == 'buy':
                    location_id = warehouse.lot_input_id.id
                elif product.supply_method == 'produce':
                    location_id = warehouse.lot_stock_id.id
                else:
                    continue
                proc_id = proc_obj.create(cr, uid,
                            self._prepare_automatic_op_procurement(cr, uid, product, warehouse, location_id, context=context),
                            context=context)
                wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)
                wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_check', cr)
        return True


    def make_to_order_cron(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        ''' 
        @预售商品处理
        '''
        self._make_to_order_confirm(cr, uid, use_new_cursor=use_new_cursor, context=context)
    
    def _make_to_order_confirm(self, cr, uid, ids=None, use_new_cursor=False, context=None):
        '''
        Call the scheduler to check the procurement order

        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param use_new_cursor: False or the dbname
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        '''
        if context is None:
            context = {}
        try:
            if use_new_cursor:
                cr = pooler.get_db(use_new_cursor).cursor()
            wf_service = netsvc.LocalService("workflow")

            procurement_obj = self.pool.get('procurement.order')
            if not ids:
                ## 仅处理预售商品处于except状态
                ids = procurement_obj.search(cr, uid, [
                    ('state', '=', 'exception'),
                    ('procure_method', '=', 'make_to_order'),
                    ## ('need_purchase', '=', True),
                    ], order="date_planned")
            for id in ids:
                wf_service.trg_validate(uid, 'procurement.order', id, 'button_restart', cr)
            if use_new_cursor:
                cr.commit()
            offset = 0
            while True:
                ids = procurement_obj.search(cr, uid, [
                    ('state', '=', 'confirmed'),
                    ('procure_method', '=', 'make_to_order')
                    ## ('need_purchase', '=', True),
                    ], offset=offset, limit=500, order='priority, date_planned', context=context)
                for proc_id in ids:
                    ## 全部立即处理
                    wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_check', cr)
                if use_new_cursor:
                    cr.commit()
                if not ids:
                    break
            if use_new_cursor:
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
        return {}


    def make_po(self, cr, uid, ids, context=None):
        """ Make purchase order from procurement
        @return: New created Purchase Orders procurement wise
        """
        res = {}
        if context is None:
            context = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        partner_obj = self.pool.get('res.partner')
        uom_obj = self.pool.get('product.uom')
        pricelist_obj = self.pool.get('product.pricelist')
        prod_obj = self.pool.get('product.product')
        acc_pos_obj = self.pool.get('account.fiscal.position')
        seq_obj = self.pool.get('ir.sequence')
        warehouse_obj = self.pool.get('stock.warehouse')
        for procurement in self.browse(cr, uid, ids, context=context):
            res_id = procurement.move_id.id
            ##按物流中心获取主供应商
            (warehouse_id, partner) = self._get_warehouse_and_supplier(cr, uid, procurement, context=context)
            
            seller_qty = procurement.product_id.seller_qty
            partner_id = partner.id
            address_id = partner_obj.address_get(cr, uid, [partner_id], ['delivery'])['delivery']
            pricelist_id = partner.property_product_pricelist_purchase.id
            uom_id = procurement.product_id.uom_po_id.id
            qty = uom_obj._compute_qty(cr, uid, procurement.product_uom.id, procurement.product_qty, uom_id)
            if seller_qty:
                qty = max(qty,seller_qty)

            price = pricelist_obj.price_get(cr, uid, [pricelist_id], procurement.product_id.id, qty, partner_id, {'uom': uom_id})[pricelist_id]

            schedule_date = self._get_purchase_schedule_date(cr, uid, procurement, company, context=context)
            purchase_date = self._get_purchase_order_date(cr, uid, procurement, company, schedule_date, context=context)

            #Passing partner_id to context for purchase order line integrity of Line name
            new_context = context.copy()
            new_context.update({'lang': partner.lang, 'partner_id': partner_id})

            product = prod_obj.browse(cr, uid, procurement.product_id.id, context=new_context)
            taxes_ids = procurement.product_id.supplier_taxes_id
            taxes = acc_pos_obj.map_tax(cr, uid, partner.property_account_position, taxes_ids)

            name = product.partner_ref
            if product.description_purchase:
                name += '\n'+ product.description_purchase
            line_vals = {
                'name': name,
                'product_qty': qty,
                'product_id': procurement.product_id.id,
                'product_uom': uom_id,
                'price_unit': price or 0.0,
                'date_planned': schedule_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'move_dest_id': res_id,
                'taxes_id': [(6,0,taxes)],
            }
            name = seq_obj.get(cr, uid, 'purchase.order') or _('PO: %s') % procurement.name
            if procurement.need_purchase:
                origin_type = 'make_to_order'
            else:
                origin_type = 'make_to_stock'
            po_vals = {
                'name': name,
                'origin': procurement.origin,
                'partner_id': partner_id,
                'location_id': procurement.location_id.id,
                'warehouse_id': warehouse_id or False,
                'pricelist_id': pricelist_id,
                'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'company_id': procurement.company_id.id,
                'fiscal_position': partner.property_account_position and partner.property_account_position.id or False,
                'payment_term_id': partner.property_supplier_payment_term.id or False,
                ## 区分mts与mto
                ## 'origin_type':procurement.product_id.product_tmpl_id.procure_method,
                'origin_type':origin_type,
            }
            res[procurement.id] = self.create_procurement_purchase_order(cr, uid, procurement, po_vals, line_vals, context=new_context)
            self.write(cr, uid, [procurement.id], {'state': 'running', 'purchase_id': res[procurement.id]})
        self.message_post(cr, uid, ids, body=_("Draft Purchase Order created"), context=context)
        return res
    
class okgj_orderpoint(osv.osv):
    _inherit = "stock.warehouse.orderpoint"
    
    def delorderpoint_cron(self, cr, uid, context=None):
        if context is None:
            context = {}        
        warehouse_obj = self.pool.get('stock.warehouse')
        warehouse_ids = warehouse_obj.search(cr, uid,[])        
        unlink_ids = []
        for one_id in warehouse_ids:
            sql_str = """
            select op.id
            from product_product pp
            left join product_template pt on pt.id = pp.product_tmpl_id
            left join stock_warehouse_orderpoint op on pp.id=op.product_id
            where pp.is_group_product = 'f'
            and (pt.purchase_ok = 'f'
            or pp.active = 'f')
    	    and op.warehouse_id = %s
            """
            cr.execute(sql_str, (one_id,))
            unlink_ids += [one[0] for one in cr.fetchall()]
        self.unlink(cr, SUPERUSER_ID, unlink_ids,)
        return {}


    def orderpoint_cron(self, cr, uid, context=None):
        if context is None:
            context = {}        
        product_obj = self.pool.get('product.product')
        warehouse_obj = self.pool.get('stock.warehouse')
        warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)        
        warehouse_data = warehouse_obj.browse(cr, uid, warehouse_ids, context=context)
        
        for one_warehouse in warehouse_data:
            sql_str = """
            select pro.id,product.name_template,ptemp.uom_id 
            from (
            select pp.id
            from product_product pp
            left join product_template pt on pt.id = pp.product_tmpl_id
            where pp.is_group_product = 'f'
            and pt.purchase_ok = 't'
            and pp.active = 't'
            except
            select op.product_id
            from stock_warehouse_orderpoint op
            where warehouse_id = %s
            ) pro
            left join product_product product on product.id = pro.id
            left join product_template ptemp on ptemp.id = product.product_tmpl_id
            """
            cr.execute(sql_str, (one_warehouse.id,))
            count = 200
            for one_product in cr.fetchall():
                if count < 0: count = 200
                count -= 1
                local_res = {
                    'name':one_product[1] + ' / ' + one_warehouse.name,
                    'warehouse_id' : one_warehouse.id,
                    'product_id' : one_product[0],
                    'product_uom' : one_product[2],
                    'qty_multiple':1, 
                    'location_id' : one_warehouse.lot_stock_id.id}
                self.create(cr, uid, local_res, context=context)
                if count < 0:
                    cr.commit()
        return {}

okgj_orderpoint()

class okgj_product_product_procurement(osv.osv):
    _inherit = "product.product"

    def get_last_sell_days_for_procurement(self, cr, uid, product_id, days=[], context=None):
        '''
        计算商品出库数量，
        days=[3,5,7], int类型
        参数字典，商品，物流中心
        返回,{3:10, 5:20, 7:21},计量单位为商品uom_id
        '''
        if context is None:
            context = {}
        warehouse_id = context.get('active_warehouse_id', [])
        if not warehouse_id:
            raise osv.except_osv(_('Invalid Action!'), _(u'No Warehouse!'))
        warehouse_obj = self.pool.get('stock.warehouse')
        mov_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        warehouse_data = warehouse_obj.browse(cr, uid, warehouse_id, context)
        lot_stock_id = warehouse_data.lot_stock_id.id
        product_uom = self.read(cr, uid, [product_id], ['uom_id'], context)[0]['uom_id'][0]
        today = datetime.utcnow()
        today_str = date.fromtimestamp(time.time()).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        res = {}
        for iday in days:
            last_iday_str = (today - relativedelta(days=iday)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            #yesterday = (today - relativedelta(days=iday)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            #last_iday_move_lines_ids = mov_obj.search(cr, uid, [('product_id','=',product_id), ('location_id','=',lot_stock_id), ('date','>', last_iday), ('state','=', 'done'), ('sale_line_id', '!=', False), ('type', '=', 'out')], context=context)
            last_iday_move_lines_ids = mov_obj.search(cr, uid, [('product_id','=',product_id), ('location_id','=',lot_stock_id), ('date','>', last_iday_str), ('date','<', today_str), ('sale_line_id', '!=', False), ('type', '=', 'out')], order='date asc', context=context)
            last_iday_move_lines_data = mov_obj.browse(cr, uid, last_iday_move_lines_ids, context=context)
            iday_qty = 0
            move_date = []
            for one_move in last_iday_move_lines_data:
                move_date.append(one_move.date)
                if product_uom != one_move.product_uom.id:
                    product_qty = uom_obj._compute_qty(cr, uid, one_move.product_uom.id, one_move.product_qty, product_uom)
                else:
                    product_qty = one_move.product_qty
                iday_qty = iday_qty + product_qty
            if move_date:
                #方法一:以实际出库天数算
                #total_days = (datetime.datetime.strptime(move_date[-1], DEFAULT_SERVER_DATETIME_FORMAT) - datetime.datetime.strptime(move_date[0], DEFAULT_SERVER_DATETIME_FORMAT)).days + 1
                #方法二:以昨天算
                total_days = (today - datetime.strptime(move_date[0], DEFAULT_SERVER_DATETIME_FORMAT)).days + 1
                #注意时间差，不足24小时不算一天
                ## days =  (datetime.datetime.strptime("13-05-28 05:05:05", "%y-%m-%d %H:%M:%S") - datetime.datetime.strptime("13-05-27 05:05:06", "%y-%m-%d %H:%M:%S")).days
                ## print days

                res[iday] = iday_qty / total_days
            else:
                res[iday] = 0
        return res

class okgj_stock_warehouse_orderpoint(osv.osv):
    """
    自动计算最小最大订货规则
    """

    ## def _get_min(self, cr, uid, ids, field_names, arg, context=None):
    ##     """ 获取最小销售数量
    ##     @param prop: Name of field.
    ##     @param unknow_none:
    ##     @return: Dictionary of values.
    ##     """
    ##     if context is None:
    ##         context = {}
    ##     local_context = context
    ##     result = {}.fromkeys(ids, 0.0)
    ##     product_obj = self.pool.get('product.product')
    ##     for one_line in self.browse(cr, uid, ids, context=context):
    ##         product_id = one_line.product_id.id
    ##         warehouse_id = one_line.warehouse_id.id
    ##         local_context.update({'active_warehouse_id': warehouse_id})
    ##         result[one_line.id] = product_obj.get_last_sell_days(cr, uid, product_id, days=[14], context=local_context)[14]
    ##     return result

    ## def _get_max(self, cr, uid, ids, field_names, arg, context=None):
    ##     """ 获取最大销售数量
    ##     @param prop: Name of field.
    ##     @param unknow_none:
    ##     @return: Dictionary of values.
    ##     """
    ##     if context is None:
    ##         context = {}
    ##     local_context = context
    ##     result = {}.fromkeys(ids, 0.0)
    ##     product_obj = self.pool.get('product.product')
    ##     for one_line in self.browse(cr, uid, ids, context=context):
    ##         product_id = one_line.product_id.id
    ##         warehouse_id = one_line.warehouse_id.id
    ##         local_context.update({'active_warehouse_id': warehouse_id})
    ##         result[one_line.id] = product_obj.get_last_sell_days(cr, uid, product_id, days=[30], context=local_context)[30]
    ##     return result

    def _get_count(self, cr, uid, ids, field_names, arg, context=None):
        if context is None:
            context = {}
        local_context = context
        result = {}.fromkeys(ids, 0.0)
        product_obj = self.pool.get('product.product')
        for one_line in self.browse(cr, uid, ids, context=context):
            product_id = one_line.product_id.id
            warehouse_id = one_line.warehouse_id.id
            local_context.update({'active_warehouse_id': warehouse_id})
            last_sell = product_obj.get_last_sell_days_for_procurement(cr, uid, product_id, days=[120], context=local_context)[120]
            result[one_line.id] = {
                'product_min_qty':round(last_sell * 7), #随时调整，旧数据14
                'product_max_qty':round(last_sell * 14), #旧数据30
            }
        return result

    _inherit = "stock.warehouse.orderpoint"
    _columns = {
        'product_min_qty': fields.function(_get_count, type='float', digits_compute=dp.get_precision('Product Unit of Measure'), string="Minimum Quantity", multi='get_count'),
        'product_max_qty': fields.function(_get_count, type='float', digits_compute=dp.get_precision('Product Unit of Measure'), string="Maximum Quantity", multi='get_count'),
    }
okgj_stock_warehouse_orderpoint()
