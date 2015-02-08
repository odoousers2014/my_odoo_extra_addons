# -*- coding: utf-8 -*-

import time
from openerp.report import report_sxw
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
import math 
States = [
    ('draft', u'草稿'),
    ('cancel', u'已取消'),
    ('waiting', u'等待其他操作'),
    ('confirmed', u'等待可用'),
    ('assigned', u'准备收货'),
    ('done', u'已收货'),
]


class yks_stock_in_order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(yks_stock_in_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'int': int,
            'get_purchase_info': self._get_purchase_info,
            'get_create_info': self._get_create_info,
            'get_product_desc': self._get_product_desc,
            'get_state': self._get_state,
        })

    def _get_product_desc(self, move_line):
        desc = move_line.product_id.name
        if move_line.product_id.default_code:
            desc = '[' + move_line.product_id.default_code + ']' + ' ' + desc
        return desc

    def _get_state(self, move_line):
        ''''''
        res = dict(States)[move_line.state]
        return res

    def _get_purchase_info(self, obj, user):
        '''获得供应信息'''

        NL = '\n'
        NUL = ''
        partner_name = '%s%s' % (obj.partner_id and u'供应商：', obj.partner_id and obj.partner_id.name or NUL)
        origin = obj.origin and u'源单据：' + obj.origin or NUL
        create_time = obj.date and u'创建时间：' + obj.date

        print_user = user.name and u'打印人：' + user.name or NUL
        print_time = u'打印时间：' + (datetime.now() + timedelta(hours=8)).strftime(DF)
        purchase_info = NL.join([partner_name, origin, create_time, print_user, print_time])
        return purchase_info

    def _get_create_info(self, obj):
        ''''''
        NL = '\n'
        NUL = ''
        move_type = {'direct': u'部分', 'one': u'全部一次性'}
        purchase_order = '%s%s' % (obj.purchase_id and u'采购订单：', obj.purchase_id and obj.purchase_id.name or NUL)
        create_user = '%s%s' % (obj.create_uid and u'创建人：', obj.create_uid and obj.create_uid.name or NUL)
        receive_date = obj.date_done and u'接收日期：' + obj.date_done or NUL
        move_type = obj.move_type and u'送货方式：' + move_type.get(obj.move_type, '')
        create_info = NL.join([purchase_order, create_user, receive_date, move_type])
        return create_info

report_sxw.report_sxw('report.yks_stock_in_order', 'stock.picking.in',
    'addons/yks/report/yks_stock_in_order.rml', parser=yks_stock_in_order, header="Report")
