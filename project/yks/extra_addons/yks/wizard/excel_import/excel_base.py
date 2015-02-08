#-*-coding:utf-8 -*-

import xlrd

from openerp.osv import  osv, fields
import logging
_logger = logging.getLogger(__name__)


class excel_base(osv.osv_memory):
    _name = "excel.base"

    Excel_model = {
        'collection_voucher': {'title': ['name', 'platform_so_id', 'amount_in', 'amount_out', 'trans_time', 'note', 'payer_account'], 'string': u"收款记录"},
        'complex_product': {'title': ['name', 'complex_sku', 'sub_sku', 'qty'], 'string': u'组合品'},
        'product': {'title': ['name', 'sku'], 'string': u'产品'},
        'orderpoint': {'title': ['sku', 'name', 'product_min_qty'], 'string': u'库存预警'},
        'beibeiwang': {'title': ['platform_so_id', 'buyer_note', 'platform_seller_id', 'province', 'city', 'county', 'receive_user',
                                 'receive_phone', 'receive_address', 'seller_note', 'product_qty_total',
                                 'sku', 'price_unit', 'total', 'all_total', 'product_qty'], 'string': u'贝贝网销售订单'},
        'yangmatou': {'title': ['platform_so_id', 'sku', 'product_qty', 'price_unit', 'total', 'platform_create_time',
                                'platform_pay_time', 'buyer_note', 'platform_user_id', 'receive_user', 'receive_phone',
                                'receive_address', 'receive_zip', 'seller_note', 'sale_model'], 'string': u'洋码头销售订单'},
    }
    _columns = {
        'name': fields.char('Name', size=20,),
        'file': fields.binary(u'Excel文件', filters='*.xls'),
        'replace': fields.selection([('update', u'更新'), ('create', u'新建')], u'导入类型'),
        'model': fields.selection([(k, Excel_model[k]['string']) for k in Excel_model], u'导入内容'),
    }

    def parse_title_data(self, filename=None, file_contents=None):
        """
        parse excel, first line is title
        @return,  {'title':[],'data': [t1:v1, t2:v2])
        """
        res = {}
        try:
            book = xlrd.open_workbook(filename=filename, file_contents=file_contents)
            sheet = book.sheet_by_index(0)
            titles = sheet.row_values(1)
            datas = []
            for i in range(2, sheet.nrows):
                dic = dict(zip(titles, sheet.row_values(i)))
                dic.update({'row_nu': i + 1})
                datas.append(dic)
            res.update({'title': titles, 'data': datas})
        except Exception, e:
            _logger.info('Error,excel parse %s' % e)
        return res

    def apply(self, cr, uid, ids, context=None):
        return {}

excel_base()

##################################################################