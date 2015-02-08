# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import  osv, fields
import openerp.addons.decimal_precision as dp
#from openerp.tools.translate import _


class product_brand(osv.osv):
    _name = 'product.brand'
    _columns = {
        'create_uid': fields.many2one('res.users', u'创建人'),
        'name': fields.char(u'品牌名称', size=128, select=True, required=True,),
    }
    _sql_constraints = [
        ('name_unique', 'unique (name)', 'The code of the brand #must be unique !'),
    ]
product_brand()


class product_category(osv.osv):
    _inherit = 'product.category'
    _columns = {
        'create_uid': fields.many2one('res.users', u'创建人'),
    }
product_category()


class product_product(osv.osv):
    _inherit = 'product.product'

    def _check_default_code(self, cr, uid, ids, context=None):
        for pdt in self.browse(cr, uid, ids, context=context):
            if pdt.default_code and ' ' in pdt.default_code:
                return False
        return True

    _columns = {
        'create_uid': fields.many2one('res.users', u'创建人', ),
        'brand_id': fields.many2one('product.brand', u'品牌', ondelete='restrict'),
        'formula': fields.char(u'配方', size=40),
        'place_production': fields.many2one('res.country', u'原产地'),
        'suitable_crowd': fields.char(u'适用人群', size=25),
        'old_id': fields.char(u'Old  ID', size=16),
        'default_code': fields.char('Internal Reference', size=64, select=True, required=True),
        'hs_code': fields.char(u'海关编码', size=20,),
        'en_name': fields.char(u'英文名称', size=100,),
        'hs_tax_id': fields.many2one('account.tax', u'海关税'),
        'pp_tax_id': fields.many2one('account.tax', u'行邮税'),
        'price_wholesale': fields.float(u'批发价', digits_compute=dp.get_precision('Product Price')),
        'goods_item': fields.char(u'商品货号', size=30),
    }
    _sql_constraints = [
        ('default_code_unique', 'unique (default_code)', 'The code of the SKU must be unique !'),
    ]
    _constraints = [
        (_check_default_code, u'SKU编码中有空格,请检查', ['default_code', ]),
    ]
    _defaults = {
        'type': 'product',
    }
product_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: