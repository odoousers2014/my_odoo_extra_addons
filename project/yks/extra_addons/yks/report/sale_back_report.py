#-*-coding:utf-8 -*-
import time
from openerp.report import report_sxw
from ..sale_back import Sale_Back_Trade_Status, Picking_Out_status, Back_Type
from ..sync_api import Platform_List


class sale_back_report(report_sxw.rml_parse,):
    def __init__(self, cr, uid, name, context):
        super(sale_back_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_deal_info': self._get_deal_info,
            'get_pay_info': self._get_pay_info,
            'get_product': self._get_product,
            'get_date': self._get_date,

        })
    def _get_product(self, product):        
        return '[%s] %s' % (product.default_code, product.name_template)
    
    def _get_date(self):
        return time.strftime('%Y-%m-%d %H:%M:%S')
        
    def _get_deal_info(self, obj):
        """交易信息"""
        NL = '\n'
        NUL = ''
        sale_num = u'销售单号：' + obj.so_id.name
        deal_num = obj.platform_so_id and u'交易编号：' + obj.platform_so_id or NUL
        api_info = obj.api_id and  u'卖家：' + dict(Platform_List)[obj.api_id.type] + ':' + obj.api_id.name or u'卖家：-'
        buyer = obj.platform_user_id and u'买家：' + obj.platform_user_id or u'买家：-'
        create_date = u'创建时间：' + obj.create_date
        user = u'业务员:' + obj.create_uid.name
        deal_info = NL.join([sale_num, deal_num, api_info, buyer, create_date, user])
        return deal_info

    def _get_pay_info(self, obj):
        """支付信息"""
        NL = '\n'
        HX = '-'
        trade_state = u'交易状态：' + dict(Sale_Back_Trade_Status)[obj.trade_state]
        amount = u'退款金额：' + str(obj.amount or HX)
        alipay_name = u'支付宝姓名：' + (obj.alipay_name or HX)
        alipay_nick = u'支付宝账号：' + (obj.alipay_nick or HX)
        alipay_phone = u'客户电话:' + (obj.alipay_phone or HX)
        carrier = u'快递方式:' + (obj.carrier_id and obj.carrier_id.name or HX)
        carrier_tracking = u'快递号码:' + (obj.carrier_tracking or HX)
        
        pay_info = NL.join([trade_state, amount, alipay_nick, alipay_name, alipay_phone, carrier, carrier_tracking])
        return pay_info



report_sxw.report_sxw('report.sale_back_report', 'sale.back',
    'addons/yks/report/sale_back_report.rml', parser=sale_back_report, header="Report")

# report_sxw.report_sxw('report.sale_back_report', 'sale.back',
#                       'addons/yks/report/sale_back_report.mako', parser=sale_back_report, header='Report')