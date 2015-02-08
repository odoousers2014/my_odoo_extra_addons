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


class old_stock_express_print(report_sxw.rml_parse,):
    def __init__(self, cr, uid, name, context):
        super(old_stock_express_print, self).__init__(cr, uid, name, context=context)
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

    def _print_num(self, picking_out_obj):
        self.num = self.num + 1
        number = self.num
        if self.num == picking_out_obj.need_express_count:
            self.num = 0
        if not picking_out_obj.need_express_count:
            res = '1/1'
        else:
            res = '%s/%s' % (number, picking_out_obj.need_express_count)
        return res
    
    def _get_new_objects(self, ids):
        uid = SUPERUSER_ID
        cr = self.cr
        new_object = []
        pick_obj = self.pool.get('stock.picking.out')
        pick_obj.write(cr, uid, ids, {'express_printed': True})
        for pick in pick_obj.browse(cr, uid, ids):
            count = pick.need_express_count or 1
            new_object += [pick] * count

        return new_object
        
    def _get_user_name(self, picking_out_obj):
        return picking_out_obj.sale_id.deliver_name or ''
    
    def _get_user_address(self, picking_out_obj):
        return picking_out_obj.sale_id.deliver_address or ''
    
    def _get_user_company(self, picking_out_obj):
        return picking_out_obj.sale_id.deliver_company_name or ''
    
    def _get_user_phone(self, picking_out_obj):
        return picking_out_obj.sale_id.deliver_tel or ''
    
    def _get_user_signature(self, picking_out_obj):
        return picking_out_obj.sale_id.deliver_name or ''
    
    def _get_receive_name(self, picking_out_obj):
        return picking_out_obj.sale_id.receive_user or ''
    
    def _get_receive_address(self, picking_out_obj):
        return picking_out_obj.sale_id.receive_address or ''
    
    def _get_receive_phone(self, picking_out_obj):
        return picking_out_obj.sale_id.receive_phone or ''
    
    def _get_receive_zip(self, picking_out_obj):
        return picking_out_obj.sale_id.receiver_zip or ''


report_sxw.report_sxw('report.old_stock_express_zto_continuously', 'stock.picking.out',
    'addons/yks/report/express_zto_continuously.rml', parser=old_stock_express_print, header="Express")

report_sxw.report_sxw('report.old_stock_express_yunda_continuously', 'stock.picking.out',
    'addons/yks/report/express_yunda_continuously.rml', parser=old_stock_express_print, header="Express")




##############################################################
