# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

class okgj_purchase_return_fill_order(osv.osv_memory):
    _name = "okgj.purchase.return.fill.order"
okgj_purchase_return_fill_order()

class okgj_purchase_return_fill_order_lines(osv.osv_memory):

    _name = "okgj.purchase.return.fill.order.lines"
    _columns = {               
        'wizard_id': fields.many2one('okgj.purchase.return.fill.order','Parent Wizard'), 
        'product_id': fields.many2one('product.product', u'商品', required=True),
        'product_qty': fields.float(u'待退数量', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'price_unit': fields.float(u'单价', digits_compute= dp.get_precision('Product Price'), readonly=True),
        'min_qty': fields.integer(u'最小包装数', readonly=True),
        'uom_id':fields.many2one('product.uom', string=u'计量单位', readonly=True),
        'qty_avail': fields.float(u'可用数量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'last_week': fields.float(u'前7天出货量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'last_month': fields.float(u'前30天出货量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
    }
    _defaults = {
        'product_qty': lambda *a: 0.0,
    }

okgj_purchase_return_fill_order_lines()    

class okgj_purchase_return_fill_order(osv.osv_memory):
    _inherit = "okgj.purchase.return.fill.order"
    _columns = { 
        'line_ids': fields.one2many('okgj.purchase.return.fill.order.lines', 'wizard_id','Lines'),    
    }
    
    def default_get(self, cr, uid, fields, context=None):
        """ To get default values for the object.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param fields: List of fields for which we want default values 
        @param context: A standard dictionary 
        @return: A dictionary which of fields with values. 
        """ 
        if not context:
            context = {}
        partner_id = context.get('active_supplier_id', [])
        warehouse_id = context.get('active_warehouse_id', [])
        pricelist_id = context.get('active_pricelist_id', [])
        if (not partner_id) or (not warehouse_id):
            raise osv.except_osv(_('Invalid Action!'), _(u'请先填写供应商与物流中心.'))
        res = super(okgj_purchase_return_fill_order, self).default_get(cr, uid, fields, context=context)
        product_obj = self.pool.get('product.product')
        product_pricelist_obj = self.pool.get('product.pricelist')
        supplierinfo_obj = self.pool.get('product.supplierinfo')
        supplierinfo_ids = supplierinfo_obj.search(cr, uid, [('name', '=', partner_id)], context=context)
        product_tmpl_ids = [i['product_id'][0] for i in supplierinfo_obj.read(cr, uid, supplierinfo_ids, ['product_id'], context=context)]
        product_ids = []
        for one_tmpl_id in product_tmpl_ids:
            product_ids += product_obj.search(cr, uid, [('product_tmpl_id', '=', one_tmpl_id)], context=context)
        line_ids = []
        context.update({'warehouse_id':warehouse_id})
        product_ids=list(set(product_ids))
        product_out_data = product_obj.get_last_sell(cr, uid, product_ids, context=context)
        for one_product in product_obj.browse(cr, uid, product_ids, context=context):
            if pricelist_id:
                price_unit = product_pricelist_obj.price_get(
                    cr, uid, [pricelist_id], one_product.id,
                    1.0, partner_id or False)[pricelist_id]
            else:
                price_unit = product_out_data.standard_price

            line_ids.append((0, 0,  {
                'product_id':one_product.id,
                'product_qty':0,
                'min_qty':one_product.min_qty or 0,
                'price_unit':price_unit,
                'uom_id':product_out_data[one_product.id]['uom_id'],
                'qty_avail':one_product.qty_available,
                'last_week':product_out_data[one_product.id]['last_week'],
                'last_month':product_out_data[one_product.id]['last_month']}))
        if 'line_ids' in fields:
            res.update({'line_ids': line_ids})
        return res
        ## for one_product in partner_products:
        ## partner_products = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context).product_ids
        ## product_obj = self.pool.get('product.product')


    def do_import(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}
        today = fields.date.context_today(cr, uid, ids, context=context)
        purchase_return_obj = self.pool.get('okgj.purchase.return') 
        form_data = self.browse(cr, uid, ids[0], context=context).line_ids
        partner_id = context.get('active_supplier_id', [])
        order_id = context.get('active_ids',[])
        warehouse_id = context.get('active_warehouse_id',[])
        data = []
        context.update({'warehouse_id':warehouse_id})
        for one_line  in form_data:
            #TODO:处理税
            if one_line.product_qty > 0:
                data.append((0, 0, {
                    'product_id':one_line.product_id.id,
                    'price_unit': one_line.price_unit,
                    'product_qty':one_line.product_qty,
                    'product_uom':one_line.product_id.uom_id.id,
                    'return_order_id':order_id,
                }))
        purchase_return_obj.write(cr, uid, order_id, {'line_ids':data}, context=context)
        return {'type': 'ir.actions.act_window_close'}            

okgj_purchase_return_fill_order()
