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


class express_print(report_sxw.rml_parse,):
    def __init__(self, cr, uid, name, context):
        super(express_print, self).__init__(cr, uid, name, context=context)
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
        })
    num = 0
    
    def _print_num(self, so):
        self.num = self.num + 1
        number = self.num
        if self.num == so.need_express_count:
            self.num = 0
        return '%s/%s' % (number, so.need_express_count)
    
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
        
    def _get_user_name(self, so):
        return so.deliver_name or ''
    
    def _get_user_address(self, so):
        return so.deliver_address or ''
    
    def _get_user_company(self, so):
        return so.deliver_company_name or ''
    
    def _get_user_phone(self, so):
        return so.deliver_tel or ''
    
    def _get_user_signature(self, so):
        return so.deliver_name or ''
    
    def _get_receive_name(self, so):
        return so.receive_user or ''
    
    def _get_receive_address(self, so):
        return so.receive_address or ''
    
    def _get_receive_phone(self, so):
        return so.receive_phone or ''
    
    def _get_receive_zip(self, so):
        return so.receiver_zip or ''
    
#连续打印
report_sxw.report_sxw('report.express_qf_continuously', 'sale.order',
    'addons/yks/report/express_qf_continuously.rml', parser=express_print, header="Express")

report_sxw.report_sxw('report.express_zto_continuously', 'sale.order',
    'addons/yks/report/express_zto_continuously.rml', parser=express_print, header="Express")

report_sxw.report_sxw('report.express_yunda_continuously', 'sale.order',
    'addons/yks/report/express_yunda_continuously.rml', parser=express_print, header="Express")


# 单页打印
report_sxw.report_sxw('report.express_qf', 'sale.order',
    'addons/yks/report/express_qf.mako', parser=express_print, header="Express")

report_sxw.report_sxw('report.express_zto', 'sale.order',
    'addons/yks/report/express_zto.mako', parser=express_print, header="Express")

report_sxw.report_sxw('report.express_yunda', 'sale.order',
    'addons/yks/report/express_yunda.mako', parser=express_print, header="Express")

##############################################################
