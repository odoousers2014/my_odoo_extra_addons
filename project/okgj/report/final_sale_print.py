# -*- coding: utf-8 -*-
import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler

class okgj_final_sale_report(report_sxw.rml_parse):
    _name = 'report.okgj.final.sale.print'

    def __init__(self, cr, uid, name, context=None):
        super(okgj_final_sale_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            ## 'get_codes': self._get_codes,
        })

report_sxw.report_sxw('report.okgj.final.sale.print', 'sale.order', 'addons/okgj/report/final_sale_print.rml', parser=okgj_final_sale_report, header=None)


