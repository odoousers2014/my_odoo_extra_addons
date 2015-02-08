# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp import SUPERUSER_ID
from openerp import netsvc
from openerp.osv.orm import browse_record, browse_null
from openerp import pooler
import datetime
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from openerp.tools.translate import _

class okgj_purchase_order(osv.osv):

    def _test_repeat(self, cr, uid, ids, field_names, arg, context=None):
        """ 验证订单是否有重复行
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        result = {}.fromkeys(ids, {})
        all_orders = self.browse(cr, uid, ids, context=context)
        promotion_price_obj = self.pool.get('okgj.purchase.price.management')
        purchase_time = time.strftime("%Y-%m-%d")
        for one_order in all_orders:
            result[one_order.id]['has_promotion_price'] = False
            product_ids = [i.product_id.id for i in one_order.order_line]
            promotion_price = promotion_price_obj.get_price_management(cr, uid, product_ids, purchase_time, one_order.partner_id.id, one_order.warehouse_id.id)
            if promotion_price:
                for line in one_order.order_line:
                    if (line.product_id.id in promotion_price) and (line.price_unit > promotion_price[line.product_id.id]):
                        result[one_order.id]['has_promotion_price'] = True
                        break
            line_count = len(one_order.order_line)
            product_count = len(set([one_line.product_id  for one_line in one_order.order_line]))
            if product_count < line_count:
                result[one_order.id]['has_repeat'] = True
            else:
                result[one_order.id]['has_repeat'] = False
        return result

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        for po in self.browse(cr, uid, ids, context=context):
            if po.has_promotion_price:
                raise osv.except_osv(_('错误!'),_('订单中有商品有促销价，请更新.'))
        super(okgj_purchase_order, self).wkf_confirm_order(cr, uid, ids, context=context)
        return True

    _inherit = 'purchase.order'
    _columns = {
        'create_date':fields.datetime(u'创建时间', readonly='True'),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'create_uid':fields.many2one('res.users', u'创建人', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'has_repeat': fields.function(_test_repeat, type='boolean', string=u'有重复行', multi="check"),
        'has_promotion_price': fields.function(_test_repeat, type='boolean', string=u'有促销进价', multi="check"),
        'origin_type':fields.selection([('make_to_order', u'订单'), ('make_to_stock', u'备货')], u'补货依据'),
        #'payment_term_id': fields.related('partner_id', 'payment_term_id', type='many2one', relation='account.payment.term', string=u'付款条款', store=True, readonly=True),
    }


    def action_show_repeat(self, cr, uid, ids, context=None):
        if isinstance(ids, list):
            ids = ids[0]
        product_ids = {}
        for one_line in self.browse(cr, uid, ids, context=context).order_line:
            one_product_id = one_line.product_id.id
            line_no = one_line.line_no
            if one_product_id in product_ids:
                raise osv.except_osv(_(u'Warn!'), _(u'第%s行与%s行商品重复!') % (product_ids[one_product_id],line_no))
            else:
                product_ids.update({one_product_id:line_no})
        return True

    def action_import_product(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context)[0]
        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False,
            'active_partner_id':data.partner_id.id,
            'active_warehouse_id':data.warehouse_id.id,
            'pricelist_id':data.pricelist_id.id,
            'fiscal_position_id':data.fiscal_position.id or False,
        })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'okgj.purchase.fill.order',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    ## def action_import_product(self, cr, uid, ids, context=None):
    ##     #self.write(cr, uid, ids, {'state':'cancel'})
    ##     self.okgj_do_merge_cron(cr, uid, use_new_cursor='okgj0617nie2', context=context)
    ##     return True
    
    ## def _check_repeat(self, cr, uid, ids, context=None):
    ##     ## return True
    ##     for one_order in self.browse(cr, uid, ids, context):
    ##         product_ids = []
    ##         for one_line in one_order.order_line:
    ##             if one_line.product_id.id not in product_ids:
    ##                 product_ids.append(one_line.product_id.id)
    ##             else:
    ##                 return False
    ##         return True
     
    ## _constraints = [
    ##     (_check_repeat, '错误，有重复行.', ['order_line']),
    ## ]   

    def okgj_do_merge_cron(self, cr, uid, use_new_cursor=False, context=None):
        """
        Auto merge simialar type of purchase orders.
        Orders will only be merged if:
        * Purchase Orders are in draft
        * Purchase Orders belong to the same partner
        * Purchase Orders are have same stock location, same pricelist
        Lines will only be merged if:
        * Order lines are exactly the same except for the quantity and unit

         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: the ID or list of IDs
         @param context: A standard dictionary

         @return: new purchase order id

        """
        #TOFIX: merged order line should be unlink
        if context is None:
            context = {}
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        to_merge_ids = self.search(cr, uid, [('state', 'in', ['draft']), ('create_uid', '=', SUPERUSER_ID)], context=context)
        wf_service = netsvc.LocalService("workflow")
        def make_key(br, fields):
            list_key = []
            for field in fields:
                field_val = getattr(br, field)
                if field in ('product_id', 'move_dest_id', 'account_analytic_id', 'warehouse_id'):
                    if not field_val:
                        field_val = False
                if isinstance(field_val, browse_record):
                    field_val = field_val.id
                elif isinstance(field_val, browse_null):
                    field_val = False
                elif isinstance(field_val, list):
                    field_val = ((6, 0, tuple([v.id for v in field_val])),)
                list_key.append((field, field_val))
            list_key.sort()
            return tuple(list_key)

        # Compute what the new orders should contain
        new_orders = {}
        for porder in [order for order in self.browse(cr, uid, to_merge_ids, context=context) if order.state == 'draft']:
            order_key = make_key(porder, ('partner_id', 'location_id', 'pricelist_id', 'warehouse_id', 'origin_type'))
            new_order = new_orders.setdefault(order_key, ({}, []))
            new_order[1].append(porder.id)
            order_infos = new_order[0]
            if not order_infos:
                order_infos.update({
                    'origin': porder.origin,
                    'date_order': porder.date_order,
                    'origin_type':porder.origin_type,
                    'partner_id': porder.partner_id.id,
                    'dest_address_id': porder.dest_address_id.id,
                    'warehouse_id': porder.warehouse_id.id,
                    'location_id': porder.location_id.id,
                    'pricelist_id': porder.pricelist_id.id,
                    'state': 'draft',
                    'order_line': {},
                    'notes': '%s' % (porder.notes or '',),
                    'fiscal_position': porder.fiscal_position and porder.fiscal_position.id or False,
                })
            else:
                if porder.date_order < order_infos['date_order']:
                    order_infos['date_order'] = porder.date_order
                if porder.notes:
                    order_infos['notes'] = (order_infos['notes'] or '') + ('\n%s' % (porder.notes,))
                if porder.origin:
                    order_infos['origin'] = (order_infos['origin'] or '') + ' ' + porder.origin

            for order_line in porder.order_line:
                line_key = make_key(order_line, ('name', 'date_planned', 'taxes_id', 'price_unit', 'product_id', 'move_dest_id', 'account_analytic_id'))
                o_line = order_infos['order_line'].setdefault(line_key, {})
                if o_line:
                    # merge the line with an existing line
                    o_line['product_qty'] += order_line.product_qty
                else:
                    # append a new "standalone" line
                    for field in ('product_qty', 'product_uom'):
                        field_val = getattr(order_line, field)
                        if isinstance(field_val, browse_record):
                            field_val = field_val.id
                        o_line[field] = field_val

        allorders = [] #存储新生成订单ID
        orders_info_temp = {} #存储新旧订单关联ID
        count = 50
        for order_key, (order_data, old_ids) in new_orders.iteritems():
            count -= 1
            # skip merges with only one order
            if len(old_ids) < 2:
                allorders += (old_ids or [])
                continue

            # cleanup order line data
            for key, value in order_data['order_line'].iteritems():
                value.update(dict(key))
            order_data['order_line'] = [(0, 0, value) for value in order_data['order_line'].itervalues()]

            neworder_id = self.create(cr, uid, order_data)
            orders_info_temp.update({neworder_id: old_ids})
            allorders.append(neworder_id)
            
            # make triggers pointing to the old orders point to the new order
            for old_id in old_ids:
                wf_service.trg_redirect(uid, 'purchase.order', old_id, neworder_id, cr)
                wf_service.trg_validate(uid, 'purchase.order', old_id, 'purchase_cancel', cr)
            if count < 0:
                cr.commit()
        proc_obj = self.pool.get('procurement.order')
        for new_order in orders_info_temp:
            proc_ids = proc_obj.search(cr, uid, [('purchase_id', 'in', orders_info_temp[new_order])], context=context)
            for proc in proc_obj.browse(cr, uid, proc_ids, context=context):
                if proc.purchase_id:
                    proc_obj.write(cr, uid, [proc.id], {'purchase_id': new_order}, context)
        cr.commit()

        if use_new_cursor:
            cr.close()
        return {}
    
    def format_datetime(self, line_date):
        current_time = time.strftime('%Y-%m-%d')
        if line_date:
            format_time = datetime.datetime.strptime(line_date, '%Y-%m-%d %H:%M:%S')
            order_line_time = datetime.datetime.strftime(format_time, '%Y-%m-%d')
            return order_line_time
        return current_time
    
    ## def onchange_stock_warehouse_id(self, cr, uid, ids, warehouse_id, partner_id, order_line):
    ##     if not warehouse_id:
    ##          raise osv.except_osv(_(u'警告!'), _(u'物流中心不能为空!'))
    ##     res = super(okgj_purchase_order, self).onchange_warehouse_id(cr, uid, ids, warehouse_id)
    ##     line_obj = self.pool.get('purchase.order.line')
    ##     pur_mag_obj =self.pool.get('okgj.purchase.price.management')
    ##     product_obj = self.pool.get('product.product')
    ##     datas=[]
    ##     for one_line in order_line:
    ##         ##one_line:(0, 0, {})
    ##         product_id, order_line_time = None, None
    ##         if (one_line[0] == 2) or (one_line[0] == 4 and not one_line[1]):
    ##             continue
    ##         if  one_line[1] and one_line[2]:
    ##             product_id = one_line[2]['product_id']
    ##             line_date = line_obj.perm_read(cr, uid, one_line[1]).get('create_date').split('.')[0]
    ##             order_line_time = self.format_datetime(line_date)
    ##         else:
    ##             if one_line[0] == 0 and one_line[2]:
    ##                 product_id = one_line[2]['product_id']
    ##                 line_date = one_line[2].get('create_date', False)
    ##                 order_line_time = self.format_datetime(line_date)
    ##         # 先根据供应商物流中心查询相应单价
    ##         product_list, purchase_time = [product_id], order_line_time
    ##         supplier_price = product_obj.get_supplier_warehouse_price(cr, uid, product_list[0], warehouse_id, partner_id)
    ##         new_price= supplier_price and supplier_price[str(product_list[0])] or 0
            
    ##         #促销价
    ##         result = pur_mag_obj.get_price_management(cr, uid, product_list, purchase_time, partner_id, warehouse_id)
    ##         if result and result[product_list[0]]:
    ##             new_price = result[product_list[0]]
    ##         if one_line[2]:
    ##             one_line[2].update(price_unit=new_price)
    ##         datas.append(one_line)
    ##     if datas:
    ##         res['value']['order_line'] = datas
    ##     return res
    
    def update_purchase_price(self, cr, uid, ids, context=None):
        """
        更新促销价
        """
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        line_obj = self.pool.get('purchase.order.line')
        pur_mag_obj = self.pool.get('okgj.purchase.price.management')
        product_obj = self.pool.get('product.product')
        for order_data in self.browse (cr, uid, ids, context=context): 
            line_data = order_data.order_line
            product_list = [rec.product_id.id for rec in line_data]
            warehouse_id = order_data.warehouse_id.id
            partner_id = order_data.partner_id.id
            purchase_time = order_data.write_date or order_data.create_date
            origin_price_result = product_obj.get_supplier_warehouse_price(cr, uid, partner_id, product_list, warehouse_id, context=context)
            for one_line in line_data:
                product_id = one_line.product_id.id
                if product_id in origin_price_result:
                    new_origin_price = origin_price_result[product_id]
                else:
                    new_origin_price = 0.0
                line_obj.write(cr, uid, one_line.id, {'price_unit':new_origin_price}, context=context)
            result = pur_mag_obj.get_price_management(cr, uid, product_list, purchase_time, partner_id, warehouse_id)
            for one_line in line_data:
                product_id = one_line.product_id.id
                if product_id in result:
                    new_price = result[product_id]
                    line_obj.write(cr, uid, one_line.id, {'price_unit':new_price}, context=context)
        return True
        
okgj_purchase_order()

class okgj_purchase_order_line(osv.osv):

    def _get_line_no(self, cr, uid, ids, field_names, arg, context=None):
        """ 获取订单行号，效率以后有空更改
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        result = {}.fromkeys(ids, 0)
        line_no = 0
        for one_id in sorted(ids):
            line_no += 1
            result[one_id] = line_no
        return result

    def _get_last_sell(self, cr, uid, ids, field_names, arg, context=None):
        """ 获取7天与30天销量
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        result = {}.fromkeys(ids, 0)
        product_ids = []
        form = self.browse(cr, uid, ids, context=context)
        context.update({'active_warehouse_id':form[0].order_id.warehouse_id.id})
        product_ids = [one_line.product_id.id for one_line in form]
        product_out_data = self.pool.get('product.product').get_last_sell(cr, uid, product_ids, context=context)
        for one_line in form:
            result[one_line.id] = {
                'last_week':product_out_data[one_line.product_id.id]['last_week'],
                'last_month':product_out_data[one_line.product_id.id]['last_month'],
            }
        return result

    def _get_product_qty(self, cr, uid, ids, field_names, arg, context=None):
        """ 
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        result = {}.fromkeys(ids, 0)
        for one_id in ids:
            warehouse_id = self.browse(cr, uid, one_id, context=context).order_id.warehouse_id.id
            context.update({'warehouse_id':warehouse_id})
            one_line = self.browse(cr, uid, one_id, context=context)
            result[one_id] = {
                'qty_available':one_line.product_id.qty_available,
                'outgoing_qty':one_line.product_id.outgoing_qty,
                'incoming_qty':one_line.product_id.incoming_qty,
            }
        return result
    
    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty, uom_id, partner_id, date_order=False, fiscal_position_id=False, date_planned=False,
            name=False, price_unit=False, context=None):
        res = super(okgj_purchase_order_line, self).onchange_product_id(cr, uid, ids, pricelist_id=pricelist_id, product_id=product_id, qty=qty, uom_id=uom_id,
            partner_id=partner_id, date_order=date_order, fiscal_position_id=fiscal_position_id, date_planned=date_planned,
            name=name, price_unit=price_unit, context=context)

        supp_obj = self.pool.get('product.supplierinfo')
        pur_mag_obj = self.pool.get('okgj.purchase.price.management')
        product_obj = self.pool.get('product.product')
        
        warehouse_id = context.get('warehouse_id', False)
        purchase_time = time.strftime('%Y-%m-%d')
        ## 多物流中心价格处理
        product_price = product_obj.get_supplier_warehouse_price(cr, uid, partner_id, product_id, warehouse_id, context=context)
        if product_price:
            res['value']['price_unit'] = product_price[product_id]
        ## 促销价处理
        #result = pur_mag_obj.get_price_management(cr, uid, product_id, purchase_time, partner_id, warehouse_id)
        #if product_id in result:
        #    res['value']['price_unit'] = result[product_id]
        ## 修正日期bug
        if not res['value']['date_planned']:
            supplierinfo = supp_obj.search(cr, uid, [('name', '=', partner_id)])
            dt_planed = self._get_date_planned(cr, uid, supplierinfo, purchase_time, context=context)
        ## res['value']['date_planned'] = purchase_time
        return res
    
    _inherit = 'purchase.order.line'
    _columns = {
        'create_date':fields.datetime(u'创建时间', readonly='True'),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'create_uid':fields.many2one('res.users', u'创建人', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'line_no': fields.function(_get_line_no, type='integer', string=u'行号'),    
        'variant':fields.related('product_id', 'variants', type='char', string=u'规格', readonly=True),
        'min_qty':fields.related('product_id', 'min_qty', type='integer', string=u'最小包装数', readonly=True),
        ## 'qty_available':fields.related('product_id', 'qty_available', type='float', string=u'在库数量', readonly=True),
        ## 'outgoing_qty':fields.related('product_id', 'outgoing_qty', type='float', string=u'待出库数量', readonly=True),
        ## 'incoming_qty':fields.related('product_id', 'incoming_qty', type='float', string=u'待入库数量', readonly=True),
        'qty_available':fields.function(_get_product_qty, type='float', string=u'在库数量', readonly=True, multi='get_product_qty', digits_compute=dp.get_precision('Product Unit of Measure')),
        'outgoing_qty':fields.function(_get_product_qty,  type='float', string=u'待出库数量', readonly=True, multi='get_product_qty', digits_compute=dp.get_precision('Product Unit of Measure')),
        'incoming_qty':fields.function(_get_product_qty, type='float', string=u'待入库数量', readonly=True, multi='get_product_qty', digits_compute=dp.get_precision('Product Unit of Measure')),
        'last_week': fields.function(_get_last_sell, type='float', string=u'前7天出货量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True, multi='get_last_sell'),
        'last_month': fields.function(_get_last_sell, type='float', string=u'前30天出货量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True, multi='get_last_sell'),
        'okgj_note':fields.text(u'备注'),
    }


    ## def _check_min_qty(self, cr, uid, ids, context=None):
    ##     for one_line in self.browse(cr, uid, ids, context):
    ##         if (one_line.product_id.min_qty) and (one_line.product_id.min_qty != 0) and (one_line.product_qty % one_line.product_id.min_qty != 0):
    ##             return False
    ##     return True

    ## _constraints = [
    ##     (_check_min_qty, 'Min Qty Needed', ['product_qty']),
    ## ]
    

class product_product(osv.osv):
    _name = "product.product"
    _inherit = "product.product"
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        """
        when select product at pol, if the Partner.product_limit is True, domian product by supplier..
        """
        if context and context.get('supplier_id', False):
            product_limit = self.pool.get('res.partner').read(cr,uid,context['supplier_id'],['supplier_product_limit'])['supplier_product_limit']
            if product_limit:
                #    ids = []
                cr.execute("SELECT distinct(product_id) FROM product_supplierinfo where name = %s" % (context.get('supplier_id')))
                ids = [x[0] for x in cr.fetchall()]
                args.append(('id', 'in', ids))
                order = 'default_code'
        return super(product_product, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

product_product()

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _columns = {
        'supplier_product_limit':fields.boolean(u"采购产品控制",),
    }
    _defaults = {
        'supplier_product_limit': True,
    }
res_partner()
    

