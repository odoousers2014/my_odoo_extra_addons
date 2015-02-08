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
from openerp.osv import osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
from openerp.addons.yks.sync_api import Platform_List
from datetime import datetime, timedelta


class yks_sale_order(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        #jon  cancel draft sent cant not be preint
        so_ids = context.get('active_ids')
        domain = ','.join([str(i) for  i in so_ids])
        cr.execute("""select state from sale_order where id in (%s)""" % domain)
        for i in cr.fetchall():
            if i[0] in ['draft', 'sent', 'cancel']:
                raise osv.except_osv((u"Error"), ("禁止打印报价单，请确认为销售单后再打印"))
        
        super(yks_sale_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'show_discount': self._show_discount,
            'get_platform_so_info': self.get_platform_so_info,
            'get_user_info': self.get_user_info,
        })

    def _show_discount(self, uid, context=None):
        cr = self.cr
        try:
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'group_discount_per_so_line')[1]
        except:
            return False
        return group_id in [x.id for x in self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id]
    
    def get_platform_so_info(self, so):
        
        NL = '\n'
        NUL = ''
        platform_type = so.api_id and u'销售平台：' + dict(Platform_List).get(so.api_id.type) or NUL
        platform_seller_id = so.platform_seller_id and u"卖家昵称：" + so.platform_seller_id or NUL
        platform_user_id = so.platform_user_id and u'买家昵称：' + so.platform_user_id or NUL
        platform_so_id = so.platform_so_id and u'交易编号：' + so.platform_so_id  or NUL
        receive_user = so.receive_user and u'收货人：' + so.receive_user or NUL
        receive_address = so.receive_address and u'收货地址：' + so.receive_address or NUL
        receive_phone = so.receive_phone and u'收货电话：' + so.receive_phone or NUL
        res = NL.join([platform_type, platform_seller_id, platform_user_id, platform_so_id, receive_user, receive_address, receive_phone])

        return res
    
    def get_user_info(self, so, user):
        NL = '\n'
        sale_man = so.user_id and u'业务员：' + so.user_id.name or ''
        print_user = user.name and u'打印人：' + user.name or ''
        print_time = u'打印时间：' + (datetime.now() + timedelta(hours=8)).strftime(DF)
        create_time = u'订单创建时间：' + so.platform_create_time
        res = NL.join([sale_man, print_user, create_time, print_time])
     
        return res
report_sxw.report_sxw('report.yks_sale_order', 'sale.order', 'addons/yks/report/yks_sale_order.rml', parser=yks_sale_order, header="external")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: