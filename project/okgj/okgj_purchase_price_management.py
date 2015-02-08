# -*-coding:utf-8 -*-
import time
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import datetime

class purchase_price_order_management(osv.osv):
    _name = 'okgj.purchase.price.order.management'
    _order = 'create_date desc'
    
    def _get_warehouse_id(self, cr, uid, context=None):
        """
        依用户ID返回用户的第一个物流中心
        """
        user_data = self.pool.get('res.users').browse(cr,uid, uid, context=context)
        warehouse_id = False
        for one_warehouse in user_data.warehouse_ids:
            warehouse_id = one_warehouse.id
            if warehouse_id:
                break
        return warehouse_id

    _columns = {
        'name':fields.char('促销单号', size=64, select=True, states={'draft':[('readonly', False)]}, readonly=True),
        'create_uid':fields.many2one('res.users', u'创建人', readonly=True),
        'create_date':fields.datetime(u'创建日期', readonly=True),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True, states={'draft':[('readonly', False)]}, readonly=True),
        'partner_id':fields.many2one('res.partner', u'供应商', domain=[('supplier','=',True)], select=True, required=True, states={'draft':[('readonly', False)]}, readonly=True),
        'price_management_ids':fields.one2many('okgj.purchase.price.management', 'order_management_id', u'促销进价明细'),
        'state': fields.selection([
            ('draft', u'草稿'),
            ('confirmed', u'确认'),
            ('need_reedit', u'驳回'),
            ], u'状态', required=True, readonly=True),
    }
    
    _defaults = {
        'warehouse_id':_get_warehouse_id,
        'state':lambda *a:'draft',
        'name':lambda self, cr, uid, context: self.pool.get('ir.sequence').get(cr, uid, 'okgj.purchase.price.change'),
    }
        
    def do_need_reedit(self, cr, uid, ids, context=None):
        """
            驳回
        """
        if isinstance(ids, (int,long)):
            ids = [ids]
        if context is None: context={}
        management_line_obj =  self.pool.get("okgj.purchase.price.management")
        for one_order in self.browse(cr, uid, ids, context=context):
            for one_line in one_order.price_management_ids:
                management_line_obj.do_need_reedit(cr, uid, one_line.id, context=context)
        self.write(cr, uid, ids, {'state':'need_reedit'}, context=context)
        return True
    
    def do_draft(self, cr, uid, ids, context=None):
        """
            设为草稿
        """
        if isinstance(ids, (int,long)):
            ids = [ids]
        if context is None: context={}
        management_line_obj =  self.pool.get("okgj.purchase.price.management")
        for one_order in self.browse(cr, uid, ids, context=context):
            for one_line in one_order.price_management_ids:
                management_line_obj.do_draft(cr, uid, one_line.id, context=context)
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        return True
    
    def do_confirm(self, cr, uid, ids, context=None):
        """
        审核
        """
        if isinstance(ids, (int,long)):
            ids = [ids]
        if context is None: context={}
        management_line_obj =  self.pool.get("okgj.purchase.price.management")
        for one_order in self.browse(cr, uid, ids, context=context):
            for one_line in one_order.price_management_ids:
                management_line_obj.do_confirm(cr, uid, one_line.id, context=context)
        self.write(cr, uid, ids, {'state':'confirmed'}, context=context)
        return True

purchase_price_order_management() 
    
class purchase_price_management(osv.osv):

    def _get_org_price(self, cr, uid, ids, fields_name, arg, context=None):
        res = {}
        supinfo_obj = self.pool.get('product.supplierinfo')
        pricelist_obj = self.pool.get('pricelist.partnerinfo')
        res = {}.fromkeys(ids, 0.0)
        for record in self.browse(cr, uid, ids):
            if record.product_id and record.partner_id and record.warehouse_id:
                supp_ids = supinfo_obj.search(cr, uid, [
                    ('product_id', '=', record.product_id.id),
                    ('name', '=', record.partner_id.id),
                    ('warehouse_id', '=', record.warehouse_id.id),
                    ], context=context)
                if supp_ids:
                    pricelist_ids = pricelist_obj.search(cr, uid, [('suppinfo_id', '=', supp_ids[0]),], context=context)
                    if pricelist_ids:
                        res[record.id] = pricelist_obj.read(cr, uid, pricelist_ids[0], ['price'])['price']
        return res
                        
    _name = 'okgj.purchase.price.management'
    _order = 'create_date desc'
    _columns = {
        'order_management_id':fields.many2one('okgj.purchase.price.order.management', u'促销进价单', ondelete='cascade'),
        'user_id':fields.many2one('res.users', u'创建人', readonly=True),
        'create_date':fields.datetime(u'创建日期', readonly=True),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True, states={'draft':[('readonly', False)]}, readonly=True),
        'product_id':fields.many2one('product.product', u'商品', required=True, select=True, states={'draft':[('readonly', False)]}, readonly=True),
        'start_time':fields.date(u'开始时间', required=True, states={'draft':[('readonly', False)]}, readonly=True),
        'end_time':fields.date(u'结束时间', required=True, states={'draft':[('readonly', False)]}, readonly=True),
        'org_price':fields.function(_get_org_price, type='float',
                                    digits_compute=dp.get_precision('Product Price'),
                                    string=u'非促销进价'),
        'new_price':fields.float(u'促销进价', digits_compute=dp.get_precision('Product Price'), required=True, states={'draft':[('readonly', False)]}, readonly=True),
        'partner_id':fields.many2one('res.partner', u'供应商', domain=[('supplier','=',True)], select=True, states={'draft':[('readonly', False)]}, readonly=True),
        'active': fields.boolean(u'启用'),
        'state': fields.selection([
            ('draft', u'草稿'),
            ('confirmed', u'确认'),
            ('need_reedit', u'驳回'),
            ], u'状态', required=True, readonly=True),
    }
    _defaults = {
        'user_id':lambda self,cr,uid,context:uid,
        'active':lambda *a: True,
        'state':lambda *a:'draft',
    }
    
    def create(self, cr, uid, vals, context=None):
        order_management_id = vals.get('order_management_id', False)
        if order_management_id:
            order_management_obj = self.pool.get('okgj.purchase.price.order.management')
            order_data = order_management_obj.browse(cr, uid, order_management_id, context=context)
            vals.update({
                'partner_id':order_data.partner_id.id, 
                'warehouse_id':order_data.warehouse_id.id
                })
        return super(purchase_price_management, self).create(cr, uid, vals, context=context)
    
    def do_draft(self, cr, uid, ids, context=None):
        """
        设为草稿
        """
        if isinstance(ids, (int,long)):
            ids = [ids]
        if context is None: context={}
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        return True

    def do_need_reedit(self, cr, uid, ids, context=None):
        """
        审核
        """
        if isinstance(ids, (int,long)):
            ids = [ids]
        if context is None: context={}
        self.write(cr, uid, ids, {'state':'need_reedit'}, context=context)
        return True

    def do_confirm(self, cr, uid, ids, context=None):
        """
        审核
        """
        if isinstance(ids, (int,long)):
            ids = [ids]
        if context is None: context={}
        self.write(cr, uid, ids, {'state':'confirmed'}, context=context)
        return True
            
    def check_repeat_time(self, cr, uid, ids, context=None):
        """
        校验时间是否有冲突
        """
        for line in self.browse(cr, uid, ids, context=context):
            l_stime = datetime.datetime.strptime(line.start_time, '%Y-%m-%d')
            l_etime = datetime.datetime.strptime(line.end_time, '%Y-%m-%d')
            if l_stime > l_etime:
                return False
        return True
    
    def check_product_supplier(self, cr, uid, ids, context=None):
        """
        校验供应商是否供应该商品
        """
        sup_obj = self.pool.get('product.supplierinfo')
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.order_management_id:
                partner_id = rec.order_management_id.partner_id.id
                ##warehouse_id = rec.order_management_id.warehouse_id.id ##多物流中心
                sup_ids = sup_obj.search(cr, uid, [
                    ('product_id', '=', rec.product_id.id),
                    ## ('warehouse_id', '=', warehouse_id.id), ## 多物流中心适用
                    ('name', '=', partner_id)], context=context)
                if not sup_ids:
                    return False
        return True
            
    def check_new_price(self, cr, uid, ids, context=None):
        """
        校验促销进价格是否低于正常采购价
        """
        pricelist_obj = self.pool.get('pricelist.partnerinfo')
        sup_obj = self.pool.get('product.supplierinfo')
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.order_management_id:
                partner_id = rec.order_management_id.partner_id.id
                ##warehouse_id = rec.order_management_id.warehouse_id.id ##多物流中心
                sup_ids = sup_obj.search(cr, uid, [
                    ('product_id', '=', rec.product_id.id),
                    ## ('warehouse_id', '=', warehouse_id), ## 多物流中心适用
                    ('name', '=', partner_id)], context=context)
                if sup_ids:
                    pricelist_ids = pricelist_obj.search(cr, uid, [
                        ('suppinfo_id', '=', sup_ids[0]),
                        ], context=context)
                    if pricelist_ids:
                        org_price = pricelist_obj.read(cr, uid, pricelist_ids[0], ['price'])['price']
                        if rec.new_price > org_price:
                            return False
        return True
                
    _constraints = [
        (check_repeat_time, u'促销明细开始时间必须小于结束时间', ['start_time','end_time']),
        (check_product_supplier, u'促销明细商品不在该供应商里', ['product_id']),
        (check_new_price, u'促销明细的进价高于正常采购价', ['new_price']),
    ]


    def get_price_management(self, cr, uid, product_list, purchase_time, partner_id, warehouse_id=None, context=None):
        """ 取得商品促销进价.
        @param product_list:product_id or [product_id]
        @return line_dic: {product_id:values}. 
        """
        if context is None:
            context={}
        if isinstance(product_list, (int, long)):
            product_list = [product_list]
        res = {}
        for one_product in product_list:
            management_ids = self.search(cr, uid, [ 
                ('start_time', '<=', purchase_time),
                ('end_time', '>=', purchase_time),
                ('product_id', '=', one_product),
                ('warehouse_id', '=', warehouse_id),
                ('partner_id', '=', partner_id),
                ('state', '=', 'confirmed'),
                ], order='id desc', context=context)
            if management_ids:
                res[one_product] = self.read(cr, uid, management_ids[0], ['new_price'])['new_price']
        return res
purchase_price_management()

class okgj_purchase_price_management_confirm(osv.osv_memory):
    """
    采购促销进价审核
    """
    _name = "okgj.purchase.price.management.confirm"

    def do_confirm(self, cr, uid, ids, context=None):
        '''审核'''
        line_obj = self.pool.get('okgj.purchase.price.management')
        line_ids = context.get('active_ids', False)
        if line_ids:
            line_obj.do_confirm(cr, uid, line_ids, context=context)
        return {'type':'ir.actions.act_window_close'}

okgj_purchase_price_management_confirm()

