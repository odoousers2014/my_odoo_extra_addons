# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from datetime import datetime
import openerp.addons.decimal_precision as dp
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _

#销售调价单
class okgj_adjust_price(osv.osv):
    _name = "okgj.adjust.price"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _columns = {
        'name': fields.char(u'单据编号', required=True, select=True, readonly=True,states={'draft': [('readonly', False)]}),
        'date_apply': fields.datetime(u'生效日期', required=True, select=True ,readonly=True,states={'draft': [('readonly', False)]}),
        'date_now': fields.datetime(u'制单时间', required=True, readonly=True),   
        'date_approval': fields.datetime(u'审核时间', readonly=True),             
        'line_ids':fields.one2many('okgj.adjust.price.line', 'adjust_order_id', u'商品明细',readonly=True,states={'draft': [('readonly', False)]}),
        'user_id':fields.many2one('res.users', u'制单人', readonly=True),
        'supplier_id':fields.many2one('res.partner', u'供应商', domain=[('supplier', '=', True)]),
        'type': fields.selection(
            [('sale', u'销售调价'),
             ('purchase', u'采购调价'),
             ('other', u'市场调价')
            ], u'类型', required=True),
        'validate_type': fields.selection(
            [('now', u'即时生效'),
             ('clock', u'定时生效'),
            ], u'生效类型', required=True),
        'next_user_id':fields.many2one('res.users', u'审核人', readonly=True),
        'state': fields.selection([('draft', u'草稿'), ('topurchase', u'采购待审'),('tofinance', u'财务待审'), ('wait', u'待生效'),('done', u'已生效'), ('cancel', u'已作废')], u'状态',track_visibility='onchange', required=True, readonly=True),
    }
    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'adjust.sale.price'),
        'type':lambda *args: 'sale',
        'validate_type':lambda *args: 'clock',
        'state': lambda *args: 'draft',
        'date_now': lambda *a: fields.datetime.now(),
        'user_id': lambda self, cr, uid, ctx: uid,
    }
    
    def scheduler_cron(self, cr, uid, context=None):
        present = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_ids = self.search(cr, uid, [('state','=','wait')],context=context)        
        for date_id in date_ids:
            date_apply = self.browse(cr, uid, date_id, context=context).date_apply[0:10]
            if (present >= date_apply):
                self.action_done(cr, uid, date_id, context=context)
                 
    def _save_data(self,cr,uid,ids,context=None):
        if isinstance(ids, (int, long)):
                      ids = [ids]
        form = self.browse(cr, uid, ids[0], context=context)
        product_obj = self.pool.get('product.product')
        product_temp_obj = self.pool.get('product.template')
        line_datas = form.line_ids
        if form.type == 'sale':
            for one_data in line_datas: 
                product_id = one_data.product_id.id
                new_list_price = one_data.new_list_price
                #product_data = product_obj.browse(cr, uid, product_id, context=context)
                #product_tmpl_id = product_data.product_tmpl_id
                list_price = one_data.product_id.list_price   
                if list_price != new_list_price:
                    #lst_price只是个函数字段，无法执行写入
                    product_obj.write(cr, uid, product_id, {'list_price': new_list_price,}, context=context)
                    #product_temp_obj.write(cr, uid, product_tmpl_id.id, {'list_price': new_list_price,}, context=context)

        elif form.type == 'purchase':
            supplierinfo_obj = self.pool.get('product.supplierinfo')
            pricelistinfo_obj = self.pool.get('pricelist.partnerinfo')
            supplier_id = form.supplier_id.id
            for one_data in line_datas: 
                product_id = one_data.product_id.id
                product_tmpl_id = one_data.product_id.product_tmpl_id.id
                new_purchase_price = one_data.new_purchase_price
                seller_info_id = one_data.product_id.seller_info_id.id
                
                supplierinfo_id = supplierinfo_obj.search(cr, uid, [('name', '=',supplier_id), ('product_id', '=', product_tmpl_id)], context=context)
                
                if supplierinfo_id:
                    pricelist_ids = pricelistinfo_obj.search(cr, uid, [('suppinfo_id', '=', supplierinfo_id[0])], context=context)
                    if pricelist_ids:
                        pricelistinfo_obj.write(cr, uid, pricelist_ids[0], {'price':new_purchase_price}, context=context)
                    else:
                        pricelistinfo_obj.create(cr, uid, {
                            'suppinfo_id':supplierinfo_id[0],
                            'min_quantity':0,
                            'price':new_purchase_price}, context=context)
                else:
                    supplierinfo_obj.create(cr, uid, {
                        'name':supplier_id,
                        'min_qty':0,
                        'product_id':product_tmpl_id,
                        'delay':1,
                        'pricelist_ids':[(0, 0, {'min_quantity':0, 'price':new_purchase_price})]}, context=context)
               
    def action_topurchase(self, cr, uid, ids, context=None):       
        self.write(cr, uid, ids, {'state': 'topurchase','next_user_id':uid, 'date_approval': time.strftime('%Y-%m-%d')}, context=context)
        return True

    def action_tofinance(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'tofinance','next_user_id':uid, 'date_approval': time.strftime('%Y-%m-%d')}, context=context)
        return True

    def action_cancel(self, cr, uid, ids, context=None):        
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True
    
    def action_wait(self, cr, uid, ids, context=None):
        validate_type = self.browse(cr, uid, ids[0], context=context).validate_type
        if validate_type == 'now':
            self.action_done(cr, uid, ids, context=context)
        else:
            self.write(cr, uid, ids, {'state': 'wait'}, context=context)
            self.scheduler_cron(cr, uid, context=context)
            return True

    def action_done(self, cr, uid, ids, context=None):        
        self._save_data(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        adjust_price_orders = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in adjust_price_orders:
            if s['state'] not in ['done']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('Invalid Action!'), _('不允许删除已生效调价单!'))
        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
okgj_adjust_price()

#调价单行
class okgj_adjust_price_line(osv.osv):
    _name = "okgj.adjust.price.line"
    _columns = {              
        'product_id':fields.many2one('product.product', u'商品名称', required=True),
        'variants': fields.related('product_id', 'variants', type='char', string='规格', readonly=True),
        'purchase_price': fields.float(u'原主供应商采购价', digits_compute=dp.get_precision('Product Price')),
        'list_price': fields.float(u'原销售价', digits_compute=dp.get_precision('Product Price')),
        'other_price': fields.float(u'原市场价', digits_compute=dp.get_precision('Product Price')),
        'new_list_price': fields.float(u'新销售价格', digits_compute=dp.get_precision('Product Price')),
        'new_purchase_price': fields.float(u'新主供应商采购价', digits_compute=dp.get_precision('Product Price')),   
        'adjust_order_id': fields.many2one('okgj.adjust.price', 'Order Reference', select=True, required=True, ondelete='cascade'),
        #'line_state': fields.selection([('gross', u'毛利'),('ungross', u'负毛利'),('fair', u'持平')], u'状态'),
    }

    ## def create(self, cr, uid, vals, context=None):
    ##     return super(okgj_adjust_price_line,self).create(cr, uid, vals, context=context)

    ## def write(self, cr, uid, ids, vals, context=None):
    ##     return super(okgj_adjust_price_line, self).write(cr, uid, ids, vals, context=context)

    def onchange_product_id(self, cr, uid, ids,product_id = False, context=None):
        if context is None:
            context = {}
        res = {'value': {}}
        if not product_id:
            return res
        product_data = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        list_price = product_data.list_price
        supplierinfo_id = product_data.seller_info_id.id
        has_price_data = self.pool.get('product.supplierinfo').browse(cr, uid, supplierinfo_id, context=context).pricelist_ids
        if has_price_data:
            purchase_price = has_price_data[0].price 
        else:
            purchase_price = False
        res['value'].update({
            'list_price': list_price,
            'purchase_price':purchase_price}) 
        return res    
         
okgj_adjust_price_line()


class product_product(osv.osv):
    _inherit='product.product'
    _columns={
        'promotion_price': fields.float( u'最近销售价', help=u"产品最近对销售价格"), 
        'promotion_start_time': fields.datetime(u'促销开始时间'),
        'promotion_end_time': fields.datetime(u'促销结束时间'),  
    }
    
    def update_product_by_code(self, cr, uid, default_code, values, context=None ):
        """
        update product info according the product.default_code 
        """
        if (not default_code) or (not values):
            raise osv.except_osv(_('Error'), _('参数错误'))
        
        product_ids=self.search(cr,uid,[('default_code','=',default_code)])
        product_id= product_ids and product_ids[0] or False
        
        if product_id:
            return self.write(cr, uid, product_id, values, context=context)
        else:
            raise osv.except_osv(_('Error'), _(u'找不到对应对产品编码'))
            
product_product()


