# -*- coding: utf-8 -*-
import time
from openerp.report import report_sxw

class okgj_picking_collect_report(report_sxw.rml_parse):
    _name = 'report.okgj.picking.collect'

    def __init__(self, cr, uid, name, context=None):
        super(okgj_picking_collect_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            ## 'get_codes': self._get_codes,
        })

report_sxw.report_sxw('report.okgj.multi.order.print', 'okgj.multi.order.print',
    'addons/okgj/report/multi_order_print.rml', parser=okgj_picking_collect_report, header=False)
