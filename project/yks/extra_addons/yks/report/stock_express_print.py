#-*- coding:utf-8 -*-
#===============================================================================
# 日期：2014-11-3
# 作者：cloudy
# 描述：统一快递功能，便于维护
#===============================================================================

import time
from openerp.report import report_sxw
from openerp import SUPERUSER_ID
#from openerp.tools.translate import _


class stock_express_print(report_sxw.rml_parse,):
    def __init__(self, cr, uid, name, context):
        super(stock_express_print, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_user_name': self._get_user_name,
            'get_user_address': self._get_user_address,
            'get_user_company': self._get_user_company,
            'get_user_phone': self._get_user_phone,
            'get_user_signature': self._get_user_signature,
            'get_receive_name': self._get_receive_name,
            'get_receive_address': self._get_receive_address,
            'get_receive_phone': self._get_receive_phone,
            'get_receive_zip': self._get_receive_zip,
            'get_new_objects': self._get_new_objects,
            'print_num': self._print_num,
            'get_province': self._get_province,
            'get_city': self._get_city,
            'get_district': self._get_district,
        })
    num = 0

    def _print_num(self, pick):
        self.num = self.num + 1
        number = self.num
        if self.num == pick.need_express_count:
            self.num = 0
        if not pick.need_express_count:
            res = '1/1'
        else:
            res = '%s/%s' % (number, pick.need_express_count)
        return res
    
    def _get_new_objects(self, ids):
        uid = SUPERUSER_ID
        cr = self.cr
        new_object = []
        pick_obj = self.pool.get('stock.picking.out')

        for pick in pick_obj.browse(cr, uid, ids):
            count = pick.need_express_count or 1
            new_object += [pick] * count
            if not pick.express_printed:
                pick_obj.write(cr, uid, pick.id, {'express_printed': True})
                
        return new_object
        
    def _get_user_name(self, pick):
        return pick.deliver_name or ''
    
    def _get_user_address(self, pick):
        return pick.deliver_address or ''
    
    def _get_user_company(self, pick):
        return pick.deliver_company_name or ''
    
    def _get_user_phone(self, pick):
        return pick.deliver_tel or ''
    
    def _get_user_signature(self, pick):
        return pick.deliver_name or ''
    
    def _get_receive_name(self, pick):
        return pick.receive_user or ''
    
    def _get_receive_address(self, pick):
        address_format = pick.api_id and pick.api_id.address_format or '%(state)s %(city)s %(district)s %(address)s'
        state = pick.receiver_state_id and pick.receiver_state_id.name or ''
        city = pick.receiver_city_id and pick.receiver_city_id.name or ''
        district = pick.receiver_district or ''
        address = pick.receive_address or ''
        
        return address_format % {'state': state, 'city': city, 'district': district, 'address': address}
    
    def _get_receive_phone(self, pick):
        return pick.receive_phone or ''
    
    def _get_receive_zip(self, pick):
        return pick.receiver_zip or ''
    
    def _get_province(self, pick):
        return pick.receiver_state_id and pick.receiver_state_id.name or ''
    
    def _get_city(self, pick):
        return pick.receiver_city_id and pick.receiver_city_id.name or ''
    
    def _get_district(self, pick):
        return pick.receiver_district or ''

#连续打印
report_sxw.report_sxw('report.stock_express_qf_continuously', 'stock.picking.out',
    'addons/yks/report/express_qf_continuously.rml', parser=stock_express_print, header="Express")

report_sxw.report_sxw('report.stock_express_zto_continuously', 'stock.picking.out',
    'addons/yks/report/express_zto_continuously.rml', parser=stock_express_print, header="Express")

report_sxw.report_sxw('report.stock_express_yunda_continuously', 'stock.picking.out',
    'addons/yks/report/express_yunda_continuously.rml', parser=stock_express_print, header="Express")

report_sxw.report_sxw('report.stock_express_ane_continuously', 'stock.picking.out',
    'addons/yks/report/stock_express_ane_continuously.rml', parser=stock_express_print, header="Express")

# 单页打印
report_sxw.report_sxw('report.stock_express_qf', 'stock.picking.out',
    'addons/yks/report/express_qf.mako', parser=stock_express_print, header="Express")

report_sxw.report_sxw('report.stock_express_zto', 'stock.picking.out',
    'addons/yks/report/express_zto.mako', parser=stock_express_print, header="Express")

report_sxw.report_sxw('report.stock_express_yunda', 'stock.picking.out',
    'addons/yks/report/express_yunda.mako', parser=stock_express_print, header="Express")

report_sxw.report_sxw('report.stock_express_ane', 'stock.picking.out',
    'addons/yks/report/stock_express_ane.mako', parser=stock_express_print, header="Express")

##############################################################
