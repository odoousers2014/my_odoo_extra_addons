# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import osv, fields
#from openerp.tools.translate import _

Monkey_sale_type = [('1', u'德国直邮区'), ('2', u'国内现货区'), ('3', u'现货+直邮')]
Monkey_shop_type = [('1', u'淘宝C店'), ('2', u'天猫'), ('3', u'天猫国际')]


class crm_lead(osv.osv):
    _inherit = 'crm.lead'
    _columns = {
        'brand_ids': fields.many2many('product.brand', 'brand_partner_ref', 'brand_id', 'partner_id', string=u'品牌'),
        'industry': fields.char(u'行业', size=50),
        'shop_type': fields.selection(Monkey_shop_type, u'店铺类型'),
        'sale_type': fields.selection(Monkey_sale_type, u'销售类型'),
        'annual_sale': fields.char(u'年销售额', size=20),
        'month_sale': fields.integer(u'月销售额'),
        'sku_month_sale': fields.integer(u'单品月销售'),
        'taobao_rate': fields.integer(u'淘宝等级'),
        'business_content': fields.char(u'主营业务', size=100),
        'count_of_employees': fields.char(u'人工人数', size=50),
        'qq': fields.char(u'QQ', size=20,),
        'wechat': fields.char(u'微信', size=50,),
        'wangwang': fields.char(u'旺旺', size=50,),
        'gender': fields.selection([('male', u'男'), ('female', u'女')], u'性别'),
        'is_contact': fields.boolean(u'悟空联系人'),
    }
crm_lead()

##################################################################################