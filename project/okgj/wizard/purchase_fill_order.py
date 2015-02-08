# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

class okgj_purchase_fill_order(osv.osv_memory):
    _name = "okgj.purchase.fill.order"
okgj_purchase_fill_order()

class okgj_purchase_fill_order_lines(osv.osv_memory):
    _name = "okgj.purchase.fill.order.lines"
    _order = 'last_month desc'
    _columns = {               
        'wizard_id': fields.many2one('okgj.purchase.fill.order','Parent Wizard'), 
        'product_id': fields.many2one('product.product', u'商品', required=True),
        'product_qty': fields.float(u'待购数量', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'min_qty': fields.integer(u'最小包装数', readonly=True),
        'uom_id':fields.many2one('product.uom', string=u'计量单位', readonly=True),
        'qty_avail': fields.float(u'可用数量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'last_week': fields.float(u'前7天出货量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'last_month': fields.float(u'前30天出货量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
    }
    _defaults = {
        'product_qty': lambda *a: 0.0,
    }
    
    def onchange_product_qty(self, cr, uid, ids, product_id, product_qty=0,context=None):
        """ On change of product_qty
        @return: warning
        """
        if (not product_id) or (product_qty == 0):
            return {}
        product_data = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        min_qty = product_data.min_qty
        if (min_qty != 0) and (product_qty % min_qty != 0):
            warning = {
                'title': _('最小包装量错误'),
                'message': product_data.name,
            }
            return {'warning':warning, 'value':{}}
        return {}

okgj_purchase_fill_order_lines()    

class okgj_purchase_fill_order(osv.osv_memory):
    _inherit = "okgj.purchase.fill.order"
    _columns = { 
        'line_ids': fields.one2many('okgj.purchase.fill.order.lines', 'wizard_id','Lines'),    
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
        partner_id = context.get('active_partner_id', [])
        warehouse_id = context.get('active_warehouse_id', [])
        order_id = context.get('active_ids',[])
        if (not partner_id) or (not warehouse_id):
            raise osv.except_osv(_('Invalid Action!'), _(u'请先填写供应商与物流中心.'))
        res = super(okgj_purchase_fill_order, self).default_get(cr, uid, fields, context=context)
        context.update({'warehouse_id':warehouse_id})
        product_obj = self.pool.get('product.product')
        supplierinfo_obj = self.pool.get('product.supplierinfo')
        purchase_obj = self.pool.get('purchase.order')
        supplierinfo_ids = supplierinfo_obj.search(cr, uid, [('name', '=', partner_id)], context=context)
        product_tmpl_ids = [i['product_id'][0] for i in supplierinfo_obj.read(cr, uid, supplierinfo_ids, ['product_id'], context=context)]
        product_ids = []
        for one_tmpl_id in product_tmpl_ids:
            product_ids += product_obj.search(cr, uid, [('product_tmpl_id', '=', one_tmpl_id), ('purchase_ok', '=', True)], context=context)
        line_ids = []
        product_ids=list(set(product_ids))
        qty_dict = {}
        if order_id:
            for one_line in purchase_obj.browse(cr, uid, order_id[0], context=context).order_line:
                qty_dict.update({one_line.product_id.id : one_line.product_qty or 0})
        product_out_data = product_obj.get_last_sell(cr, uid, product_ids, context=context)
        for one_product in product_obj.browse(cr, uid, product_ids, context=context):
            line_ids.append((0, 0,  {
                'product_id':one_product.id,
                'product_qty':qty_dict.get(one_product.id) or 0,
                'min_qty':one_product.min_qty or 0,
                'uom_id':product_out_data[one_product.id]['uom_id'],
                'qty_avail':one_product.qty_available,
                'last_week':product_out_data[one_product.id]['last_week'],
                'last_month':product_out_data[one_product.id]['last_month']}))
        line_ids.sort(lambda x,y: -cmp(x[2]['last_week'], y[2]['last_week']))
        if 'line_ids' in fields:
            res.update({'line_ids': line_ids})
        return res


    def do_import(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}
        today = fields.date.context_today(cr, uid, ids, context=context)
        purchase_obj = self.pool.get('purchase.order')
        purchase_line_obj = self.pool.get('purchase.order.line')
        form_data = self.browse(cr, uid, ids[0], context=context).line_ids
        partner_id = context.get('active_partner_id', [])
        order_id = context.get('active_ids',[])
        pricelist_id = context.get('pricelist_id', [])
        fiscal_position_id = context.get('fiscal_position_id', False)
        product_pricelist_obj = self.pool.get('product.pricelist')
        account_tax_obj = self.pool.get('account.tax')
        account_fiscal_position_obj = self.pool.get('account.fiscal.position')
        data = []
        for one_line  in form_data:
            #TODO:处理税
            if pricelist_id:
                price = product_pricelist_obj.price_get(cr, uid, [pricelist_id], one_line.product_id.id, one_line.product_qty or 1.0, partner_id or False, {'uom': one_line.product_id.uom_id.id})[pricelist_id]
            else:
                price = one_line.product_id.standard_price
            taxes = account_tax_obj.browse(cr, uid, map(lambda x: x.id, one_line.product_id.supplier_taxes_id))
            fpos = fiscal_position_id and account_fiscal_position_obj.browse(cr, uid, fiscal_position_id, context=context) or False
            taxes_ids = account_fiscal_position_obj.map_tax(cr, uid, fpos, taxes)
            if one_line.product_qty > 0:
                data.append((0, 0, {
                    'name':one_line.product_id.name,
                    'product_id':one_line.product_id.id,
                    'price_unit': price,
                    'product_qty':one_line.product_qty,
                    'product_uom':one_line.product_id.uom_id.id,
                    'date_planned':today,
                    'taxes_id':taxes_ids,
                    'order_id':order_id,
                    'state':'draft',
                }))
        line_ids = purchase_line_obj.search(cr, uid, [('order_id', '=', order_id[0])], context=context)
        purchase_line_obj.unlink(cr, uid, line_ids, context=context)
        purchase_obj.write(cr, uid, order_id, {'order_line':data}, context=context)
        return {'type': 'ir.actions.act_window_close'}            

okgj_purchase_fill_order()
