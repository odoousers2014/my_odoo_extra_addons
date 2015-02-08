# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp.report import report_sxw
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF


class yks_sale_shipping(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(yks_sale_shipping, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_product_desc': self.get_product_desc,
            'get_platform_so_info': self.get_platform_so_info,
            'get_user_info': self.get_user_info,
        })
    
    def get_product_desc(self, move_line):
        desc = move_line.product_id.name
        if move_line.product_id.default_code:
            desc = '[' + move_line.product_id.default_code + ']' + ' ' + desc
        return desc
    
    def get_platform_so_info(self, picking):
        if picking.type != 'out':
            return ''
        
        NL = '\n'
        so = picking.sale_id
        platform_user_id = so and so.platform_user_id and u'买家昵称：' + so.platform_user_id or ''
        platform_so_id = picking.platform_so_id and u'交易编号：' + picking.platform_so_id  or ''
        receive_user = picking.receive_user and u'收货人：' + picking.receive_user or ''
        receive_address = picking.receive_address and u'收货地址：' + picking.receive_address or ''
        receive_phone = picking.receive_phone and u'收货电话：' + picking.receive_phone or ''
        res = NL.join([platform_user_id, platform_so_id, receive_user, receive_address, receive_phone])
        
        return res
    
    def get_user_info(self, picking, user):
        if picking.type != 'out':
            return ''
        
        NL = '\n'
        so = picking.sale_id
        sale_man = so and so.user_id and u'业务员：' + so.user_id.name or ''
        print_user = user.name and u'打印人：' + user.name or ''
        print_time = u'打印时间：' + time.strftime(DF)
        res = NL.join([sale_man, print_user, print_time])
        return res

report_sxw.report_sxw('report.yks_sale_shipping', 'stock.picking.out', 'addons/delivery/report/yks_sale_shipping.rml', parser=yks_sale_shipping)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: