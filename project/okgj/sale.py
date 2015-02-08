# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class okgj_sale_order_more(osv.osv):

    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        result = {}.fromkeys(ids, 0.0)        
        for sale in self.browse(cr, uid, ids, context=context):
            sale_total = sale.goods_amount - sale.coupon_pay - sale.discount
            purchase_total = 0.0
            for line in sale.order_line:
                purchase_total += (line.purchase_price * line.product_uom_qty)
            result[sale.id] = (sale_total - purchase_total)
        return result

    def _get_profit_pct(self, cr, uid, ids, field_name, arg, context=None):
        result = {}.fromkeys(ids, 0.0)        
        for sale in self.browse(cr, uid, ids, context=context):
            sale_total = sale.goods_amount - sale.coupon_pay - sale.discount + sale.shipping_fee
            purchase_total = sale.shipping_fee
            for line in sale.order_line:
                purchase_total += (line.purchase_price * line.product_uom_qty)
            try:
                result[sale.id] = (sale_total - purchase_total) * 100/ float(sale_total)
            except:
                result[sale.id] = 0
        return result

    ## 更改价格与处理预售
    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        results = super(okgj_sale_order_more, self)._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context)
        warehouse_id = order.shop_id.warehouse_id.id
        ## #取商品物流中心的成本价
        ## product_id = line.product_id.id
        ## warehouse_cost_price = self.pool.get('product.product').get_okgj_product_warehouse_cost(cr, uid, warehouse_id, product_id)
        ## if warehouse_cost_price:
        ##     results.update({'price_unit':warehouse_cost_price.get(product_id, 0.0)})
        ## 处理预售
        if line.need_purchase:
            presale_location_ids = self.pool.get('stock.location').search(cr, uid, [
                ('warehouse_id', '=', warehouse_id),
                ('is_presale', '=', True)
                ], context=context)
            if presale_location_ids:
                results.update({'location_id': presale_location_ids[0]})
        return results

    def _prepare_order_line_procurement(self, cr, uid, order, line, move_id, date_planned, context=None):
        results = super(okgj_sale_order_more, self)._prepare_order_line_procurement(cr, uid, order, line, move_id, date_planned, context=context)
        if line.need_purchase:
            results.update({'procure_method': 'make_to_order', 'need_purchase':True})
            warehouse_id = order.shop_id.warehouse_id.id
            presale_location_ids = self.pool.get('stock.location').search(cr, uid, [
                ('warehouse_id', '=', warehouse_id),
                ('is_presale', '=', True)
                ], context=context)
            if presale_location_ids:
                results.update({'location_id': presale_location_ids[0]})
        return results

    ## 按箱号打印OKKG出库单
    def print_okkg_stock_box(self, cr, uid, ids, context=None):
        """
        按箱号打印OKKG出库单
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        print_ids = []
        picking_obj = self.pool.get("stock.picking")
        box_info_obj = self.pool.get("okgj.stock.picking.box.info")
        picking_ids = picking_obj.search(cr, uid, [
            ('sale_id', 'in', ids),
            ], context=context)
        if not picking_ids:
            raise osv.except_osv(_('错误操作!'), _('未找到出库单'))
        box_info_ids = box_info_obj.search(cr, uid, [
            ('picking_out_id', 'in', picking_ids),
            ], context=context)
        if not box_info_ids:
            raise osv.except_osv(_('错误操作!'), _('未找到装箱信息'))
        datas = {
            'model': 'okgj.stock.picking.box.info',
            'ids': box_info_ids,
            'form': box_info_obj.read(cr, uid, box_info_ids, context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'okgj.okkg.sale.report', 'datas': datas, 'nodestroy': True}

    _inherit = "sale.order"
    _columns = {
        'margin': fields.function(_product_margin, type='float', string=u'毛利', digits_compute=dp.get_precision('Account'),),
        'profit_pct': fields.function(_get_profit_pct, type='float', string=u'毛利率(%)', digits_compute=dp.get_precision('Account'),),
    }


class okgj_sale_order_line(osv.osv):

    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        res = {}.fromkeys(ids, 0.0)        
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = 0
            if line.product_id:
                if line.purchase_price:
                    res[line.id] = round((line.price_unit*line.product_uom_qty*(100.0-line.discount)/100.0) -(line.purchase_price*line.product_uom_qty), 2)
                else:
                    res[line.id] = round((line.price_unit*line.product_uom_qty*(100.0-line.discount)/100.0) -(line.product_id.standard_price*line.product_uom_qty), 2)
        return res

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

    def _get_diff(self, cr, uid, ids, field_names, arg, context=None):
        """ 获取订单行号，效率以后有空更改
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        result = {}.fromkeys(ids, {})
        for one_line in self.browse(cr, uid, ids, context=context):
            diff = (one_line.price_unit - one_line.purchase_price) * one_line.product_uom_qty or 0.0
            try:
                diff_pct = ((one_line.price_unit - one_line.purchase_price)*100) / one_line.price_unit
            except:
                diff_pct = 0.0
            result[one_line.id] = {'diff':diff, 'diff_pct':diff_pct}
        return result

    _inherit = 'sale.order.line'
    _columns = {
        'line_no': fields.function(_get_line_no, type='integer', string=u'行号'),    
        'variant':fields.related('product_id', 'variants', type='char', string=u'规格', readonly=True, store=True),
        'okgj_discount': fields.float(u'折扣金额', digits_compute=dp.get_precision('Product Price')),
        'date_order2':fields.related('order_id', 'date_order2', type='datetime', string=u'商城下单时间', store=True),
        'diff': fields.function(_get_diff, type='float', string=u'毛利', digits_compute=dp.get_precision('Account'), multi='diff'),
        'diff_pct': fields.function(_get_diff, type='float', string=u'毛利率(%)', digits_compute=dp.get_precision('Account'), multi='diff'),    
#        'proxy_invoiced':fields.boolean(u'代销发票'),
        'need_purchase':fields.boolean(u'需采购', readonly=True),
        'okgj_city':fields.related('order_id', 'okgj_city', type='char', size=32, string=u'收货城市', stroe=True),
        'name_template': fields.related('product_id', 'name_template', type='char', size=128, string="Template Name", store=True, select=True),
        'default_code': fields.related('product_id', 'default_code', type='char', size=128, string="Product", store=True),
        'link_code':fields.char(u'串码',size=32),
        'rebate':fields.float(u'返点%',digits_compute=dp.get_precision('Account')),
    }
    
    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):

        res = super(okgj_sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, 
            fiscal_position=fiscal_position, flag=flag, context=context)

        if product:
            p=self.pool.get('product.product').browse(cr, uid, product)
            res['value'].update({'rebate':p.rebate})

        return res

    

