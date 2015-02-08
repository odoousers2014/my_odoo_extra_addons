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
from openerp.osv import osv
from openerp.report import report_sxw
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
from openerp.addons.yks.sync_api import Platform_List
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
#from ..sale_back import Picking_Out_status


class yks_stock_out_order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        pick_ids = context.get('active_ids')
        domain = ','.join([str(i) for i in pick_ids])
        cr.execute("""select state from stock_picking where id in (%s)""" % domain)
        
        #改为由仓库拆单，打印前不做状态检测
        #for i in cr.fetchall():
        #    if i[0] not in ['assigned', 'done']:
        #        raise osv.except_osv((u"Error"), (u"选择打印的出库单状态不可用，请先检查可用后，再打印，或者拆分出库单后检查可用"))
        
        super(yks_stock_out_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'int': int,
            'show_discount': self._show_discount,
            'get_platform_so_info': self.get_platform_so_info,
            'get_user_info': self.get_user_info,
            'get_product_desc': self.get_product_desc,
            'mark_printed': self._mark_printed,
        })
    
    def _mark_printed(self, pick, user):
        group_id = self.pool.get('ir.model.data').get_object_reference(self.cr, SUPERUSER_ID, 'stock', 'group_stock_manager')[1]
        if group_id in [g.id for g in  user.groups_id]:
            self.pool.get('stock.picking.out').write(self.cr, user.id, pick.id, {'printed': True})
        return ''

    def _show_discount(self, uid, context=None):
        cr = self.cr
        try:
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'group_discount_per_so_line')[1]
        except:
            return False
        return group_id in [x.id for x in self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id]
    
    def get_product_desc(self, move_line):
        desc = move_line.product_id.name
        if move_line.product_id.default_code:
            desc = '[' + move_line.product_id.default_code + ']' + ' ' + desc
        return desc
    
    def get_express_info(self, expresses):
        return ''
    
    def get_platform_so_info(self, pick):
        NL = '\n'
        NUL = ''
        platform_user_id = pick.sale_id.platform_user_id and u'买家昵称：' + pick.sale_id.platform_user_id or NUL
        platform_so_id = pick.platform_so_id and u'交易编号：' + pick.platform_so_id  or NUL
        receive_user = pick.receive_user and u'收货人：' + pick.receive_user or NUL
        receive_address = pick.receive_address and u'收货地址：' + pick.receive_address or NUL
        receive_phone = pick.receive_phone and u'收货电话：' + pick.receive_phone or NUL
        res = NL.join([platform_user_id, platform_so_id, receive_user, receive_phone, receive_address])

        return res
 
    def get_user_info(self, pick, user):
        NL = '\n'
        NUL = ''
        platform_type = pick.api_id and dict(Platform_List).get(pick.api_id.type) + '-' or NUL
        sale_man = pick.deliver_name and u'业务员：' + pick.deliver_name or ''
        platform_seller_id = pick.sale_id.platform_seller_id and u'卖家昵称：' + platform_type + pick.sale_id.platform_seller_id or NUL
        print_user = user.name and u'打印人：' + user.name or NUL
        print_time = u'打印时间：' + (datetime.now() + timedelta(hours=8)).strftime(DF)
        origin = pick.origin and u'源单据：' + pick.origin  or NUL
        create_time = u'订单创建时间：' + pick.sale_id.platform_create_time
        #state = u'状态：' + dict(Picking_Out_status).get(pick.state)
        res = NL.join([sale_man, platform_seller_id, origin, create_time, print_user, print_time])
        return res
    
report_sxw.report_sxw('report.yks_stock_out_order', 'stock.picking.out', 'addons/yks/report/yks_stock_out_order.rml', parser=yks_stock_out_order, header="external")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: