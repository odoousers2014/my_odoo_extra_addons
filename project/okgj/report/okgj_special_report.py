# -*- coding: utf-8 -*-
import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from openerp import pooler

class okgj_purchase_order_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_purchase_order_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'user': self.pool.get('res.users').browse(cr, uid, uid, context)
        })
report_sxw.report_sxw('report.okgj.purchase.order','purchase.order','addons/okgj/report/okgj_purchase_order.rml',parser=okgj_purchase_order_report, header=None)

class okgj_purchase_stock_picking_in(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_purchase_stock_picking_in, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })
report_sxw.report_sxw('report.okgj.purchase.stock.picking.in','stock.picking.in','addons/okgj/report/okgj_special_purchase_stock_in_report.rml',parser=okgj_purchase_stock_picking_in, header=None)

class okgj_purchase_return_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_purchase_return_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })

report_sxw.report_sxw('report.okgj.purchase.return.report','okgj.purchase.return','addons/okgj/report/okgj_purchase_return.rml',parser=okgj_purchase_return_report, header=None)


class okgj_purchase_stock_picking_out(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_purchase_stock_picking_out, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })

report_sxw.report_sxw('report.okgj.purchase.stock.picking.out','stock.picking.out','addons/okgj/report/okgj_special_purchase_stock_out_report.rml',parser=okgj_purchase_stock_picking_out, header=None)

##汇拣单与发货单
## class okgj_picking_multi_report(report_sxw.rml_parse):
##     def __init__(self, cr, uid, name, context=None):
##         #创建汇拣单
##         picking_ids = context.get('active_ids', False)
##         if picking_ids:
##             multi_obj = pooler.get_pool(cr.dbname).get('okgj.multi.order.print')
##             self.collect_id = multi_obj.create(cr, uid, {'picking_ids':[(6, 0, picking_ids)]}, context=context)
##         else:
##             raise osv.except_osv(_('Invalid Action!'), _(u"请选择发货单据!"))
##         context.update({
##             'active_ids':[self.collect_id],
##             'active_id':self.collect_id,
##             'active_model':'okgj.multi.order.print',
##             'multi_picking_ids': [self.collect_id]
##         })
##         super(okgj_picking_multi_report, self).__init__(cr, uid, name, context=context)
##         self.localcontext.update({
##             'time': time,
##         })

##     def set_context(self, objects, data, ids, report_type=None):
##         ids = [self.collect_id]
##         super(okgj_picking_multi_report, self).set_context(objects, data, ids, report_type=report_type)
    
## report_sxw.report_sxw('report.okgj.picking.multi.print', 'okgj.multi.order.print', 'addons/okgj/report/okgj_all_multi_order_print.rml', parser=okgj_picking_multi_report, header=False)


class okgj_picking_multi_report_collect(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_picking_multi_report_collect, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })
report_sxw.report_sxw('report.okgj.picking.multi.print.collect','okgj.multi.order.print','addons/okgj/report/okgj_all_multi_order_print_collect.rml',parser=okgj_picking_multi_report_collect, header=None)

class okgj_picking_multi_report_sale(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_picking_multi_report_sale, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })
report_sxw.report_sxw('report.okgj.picking.multi.print.sale','okgj.multi.order.print','addons/okgj/report/okgj_all_multi_order_print_sale.rml',parser=okgj_picking_multi_report_sale, header=None)

class okgj_sale_return_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_sale_return_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })

report_sxw.report_sxw('report.okgj.sale.return.report','okgj.sale.return','addons/okgj/report/okgj_sale_return.rml',parser=okgj_sale_return_report, header=None)

#装车单
class okgj_logistics_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_logistics_print, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'user': self.pool.get('res.users').browse(cr, uid, uid, context)
        })
report_sxw.report_sxw('report.okgj.logistics.print','okgj.logistics','addons/okgj/report/okgj_logistics.rml',parser=okgj_logistics_print, header="internal landscape")


#其它入库单
class okgj_order_picking_internal_in(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_order_picking_internal_in, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'user': self.pool.get('res.users').browse(cr, uid, uid, context)
        })
report_sxw.report_sxw('report.okgj.order.picking.internal.in','okgj.order.picking.internal','addons/okgj/report/okgj_order_picking_internal_in.rml',parser=okgj_order_picking_internal_in, header="internal")

#其它出库单
class okgj_order_picking_internal_out(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_order_picking_internal_out, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'user': self.pool.get('res.users').browse(cr, uid, uid, context)
        })
report_sxw.report_sxw('report.okgj.order.picking.internal.out','okgj.order.picking.internal','addons/okgj/report/okgj_order_picking_internal_out.rml',parser=okgj_order_picking_internal_out, header="internal")


## 快购装箱单
class okgj_okkg_sale_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_okkg_sale_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })

report_sxw.report_sxw('report.okgj.okkg.sale.report','okgj.stock.picking.box.info','addons/okgj/report/okgj_okkg_sale.rml',parser=okgj_okkg_sale_report, header=None)

##其它入库打印
class okgj_stock_picking_in_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_stock_picking_in_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'user': self.pool.get('res.users').browse(cr, uid, uid, context),
        })

report_sxw.report_sxw('report.okgj.stock.picking.in.report','stock.picking.in','addons/okgj/report/okgj_stock_picking_in_report.rml',parser=okgj_stock_picking_in_report, header=None)

##其它出库打印
class okgj_stock_picking_out_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_stock_picking_out_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'user': self.pool.get('res.users').browse(cr, uid, uid, context),
        })

report_sxw.report_sxw('report.okgj.stock.picking.out.report','stock.picking.out','addons/okgj/report/okgj_stock_picking_out_report.rml',parser=okgj_stock_picking_out_report, header=None)
