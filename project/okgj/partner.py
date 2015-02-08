# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

class okgj_res_partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
        'product_ids':fields.many2many('product.product', id1='partner_id', id2='product_id', string='Products', readonly=True),
        'is_ok':fields.boolean(u'OKGJ客户'),
        'qq':fields.char(u'QQ', size=32),
        'okgj_comment2':fields.text(u'供应范围'),
        'coop_way':fields.selection([
            ('proxy_sale',    u'代销'     ),
            ('purchase_sale', u'购销'     ),
            ('use_platform', u'使用平台' ),
            ('other',         u'其他'     ),
        ],string=u'合作方式'),   
    }
    
    def unlink(self, cr, uid, ids, context=None):
        for one_partner in self.browse(cr, uid, ids, context=context):
            if one_partner.is_ok:
                raise osv.except_osv(_('Error!'), _('不允许删除默认客户，即使您建了多个!'))
        return super(okgj_res_partner, self).unlink(cr, uid, ids, context=context)
    
okgj_res_partner()

class okgj_res_users(osv.osv):
    _inherit = "res.users"
    _columns = {
        'warehouse_ids':fields.many2many('stock.warehouse', id1='warehouse_id', id2='user_id', string=u'物流中心'),
        'shop_ids':fields.many2many('sale.shop', id1='shop_id', id2='user_id', string=u'商店'),
    }
    
class okgj_stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
        'user_ids':fields.many2many('res.users', id1='user_id', id2='warehouse_id', string=u'员工'),
        'okgj_warehouse_id':fields.char(u'商城维护ID', size=16), 
    }

class okgj_sale_shop(osv.osv):
    _inherit = "sale.shop"
    _columns = {
        'user_ids':fields.many2many('res.users', id1='user_id', id2='shop_id', string=u'员工'), 
    }


    ## def create(self, cr, uid, vals, context=None):
    ##     partner_id = super(okgj_res_partner,self).create(cr, uid, vals, context=context)
    ##     products = vals.get('product_ids', [])
    ##     if products:
    ##         products = products[0][2]
    ##         product_obj = self.pool.get('product.product')
    ##     for one_product in products:
    ##         product_obj.write(cr, uid, one_product, {'seller_ids':[(0, 0, {'name':partner_id, 'min_qty':0, 'product_id':one_product, 'delay':0})]})
    ##     return partner_id
    
    ## def write(self, cr, uid, ids, vals, context=None):
    ##     products = vals.get('product_ids', [])
    ##     if products:
    ##         product_ids = products[0][2]
    ##         product_obj = self.pool.get('product.product')
    ##     partner_id = ids
    ##     if isinstance(partner_id, list):
    ##         partner_id = partner_id[0]
    ##     if products[0][0] == 0:
    ##         for one_product_id in product_ids:
    ##             product_obj.write(cr, uid, one_product, {'seller_ids':[(0, 0, {'name':partner_id, 'min_qty':0, 'product_id':one_product, 'delay':0})]})
    ##     return  super(okgj_res_partner, self).write(cr, uid, ids, vals, context=context)

#如何实现反写到product.product
## class okgj_product_supplierinfo(osv.osv):
##     _inherit = "product.supplierinfo"

##     def create(self, cr, uid, vals, context=None):
##         partner_id = vals.get('name', False)
##         product_id = vals.get('product_id', False)
##         if partner_id and product_id:
                    
##             import sys
##             sys.stdout=open('log.txt','a')
##             print product_id
##             sys.stdout.close()
##             sys.stdout = sys.__stdout__

##             self.pool.get('res.partner').write(cr, uid, partner_id, {'product_ids':[(4, 0, product_id)]}, context=context)
##         return super(okgj_product_supplierinfo, self).create(cr, uid, vals, context=context)
    
##     def write(self, cr, uid, ids, vals, context=None):
##         super(okgj_product_supplierinfo, self).write(cr, uid, ids, vals, context=context)
##         if vals.get('name', False) or vals.get('product_id', False):
##             partner_obj = self.pool.get('res.partner')
##             for one_record in self.browse(cr, uid, ids, context=context):
##                 partner_id = one_record.partner_id.id
##                 product_id = one_record.name.id
##                 partner_obj.write(cr, uid, partner_id, {'product_ids':(4, product_id)}, context=context)
##         return True
