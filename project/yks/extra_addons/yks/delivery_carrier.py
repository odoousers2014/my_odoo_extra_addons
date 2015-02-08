# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import  osv, fields
#from openerp.tools.translate import _


class delivery_carrier(osv.osv):
    _inherit = 'delivery.carrier'
    _columns = {
        'name_pinyin': fields.char('PinYin', size=30),
        'code_taobao': fields.char(u'编码：淘宝', size=20),
        'code_yhd': fields.char(u'编码：一号店', size=20),
        'code_suning': fields.char(u'编码：苏宁', size=20),
        'code_alibaba': fields.char(u'编码：阿里巴巴', size=20),
        'code_36wu': fields.char(u'编码：36wu', size=20),
        'code_100': fields.char(u'编码：快递100', zise=20),
        'rule': fields.text(u'单号规则',)
    }
    _sql_constraints = [
        ('name_unique', 'unique (name)', 'The name of the delivery_carrier must unique !'),
    ]
delivery_carrier()
##############################################################################
