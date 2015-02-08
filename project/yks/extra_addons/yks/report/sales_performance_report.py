# -*- coding: utf-8 -*-


from openerp import tools
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
from ..sync_api import strp_time
import time
import calendar

Month_Selection = [(str(i).rjust(2, '0'), str(i).rjust(2, '0') + u'月') for i in range(1, 13)]
Year_Selection = [(str(i), str(i) + u'年') for i in range(2014, 2020)]


class wizard_sales_performance(osv.osv_memory):
    _name = 'wizard.sales.performance'
    
    def _default_year(self):
        year, month = time.gmtime()[0:2]
        if month == 1:
            year -= 1
        return str(year)
    
    def _default_month(self):
        month = time.gmtime()[1]
        if month == 1:
            month = 12
        return str(month).rjust(2, '0')

    _columns = {
        'name': fields.char('Name', size=10),
        'user_id': fields.many2one('res.users', string=u'业务员',),
        'product_id': fields.many2one('product.product', string='产品', hlep=u"产品，不选择，表示所有"),
        'start_date': fields.datetime(u'开始时间', required=True),
        'end_date': fields.datetime(u'截止时间', required=True),
        'year': fields.selection(Year_Selection, u'年', ),
        'month': fields.selection(Month_Selection, u'月',),
        'location_id': fields.many2one('stock.location', u'库位')
    }

    _defaults = {
        'year': lambda self, cr, uid, c: self._default_year(),
        'month': lambda self, cr, uid, c: self._default_month(),
    }
    
    def onchange_month(self, cr, uid, ids, month, year, context=None):
        value = {}
        if month and  year:
            last_day = calendar.monthrange(int(year), int(month))[1]
            start_date = strp_time('%s-%s-01 00:00:00' % (year, month))
            end_date = strp_time('%s-%s-%s 23:59:59' % (year, month, str(last_day)))
            value = {'start_date': start_date, 'end_date': end_date}
        return {'value': value}

    def apply(self, cr, uid, ids, context=None):
        """
        """
        wizard = self.browse(cr, uid, ids[0], context)
        domain = [('date_done', '>=', wizard.start_date), ('date_done', '<=', wizard.end_date)]
        if wizard.product_id:
            domain.append(('product_id', '=', wizard.product_id.id))
        if wizard.user_id:
            domain.append(('sale_uid', '=', wizard.user_id.id))

        return {
            'name': (u'销售业绩报告'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sales.performance.report',
            'domain': domain,
            'type': 'ir.actions.act_window',
        }

wizard_sales_performance()


class sales_performance_report(osv.osv):
    _name = "sales.performance.report"
    _order = "sale_uid desc"
    _auto = False

    _columns = {
        'product_id': fields.many2one('product.product', string='产品', readonly=True),
        'product_qty': fields.float(string=u'数量', readonly=True),
        'type': fields.selection([('in', u'入'), ('out', u'出')], string=u'出入', readonly=True),
        'price_unit': fields.float(string='单价', readonly=True),
        'total': fields.float(string='小计', readonly=True),
        'picking_id': fields.many2one('stock.picking', string=u'调拨', readonly=True),
        'sale_id': fields.many2one('sale.order', string=u'销售单', readonly=True),
        'sale_uid': fields.many2one('res.users', string=u'业务员', readonly=True),
        'buyer_name': fields.char(u'卖家'),
        'seller_name': fields.char(u'买家'),
        'section_id': fields.many2one('crm.case.section', string=u"销售团队"),
        'location_id': fields.many2one('stock.location', string=u'源库位', readonly=True),
        'location_dest_id': fields.many2one('stock.location', string=u'目的库位', readonly=True),
        'date_done': fields.datetime(string=u'完成时间', readonly=True),
        'year': fields.char(u'年', size=8, readonly=True),
        'month': fields.selection(Month_Selection, u'月', readonly=True),
        'day': fields.char(u'天', size=8, readonly=True),
    }

    def init(self, cr):
        """"""
        tools.drop_view_if_exists(cr, 'sales_performance_report')
        cr.execute("""
            create or replace view sales_performance_report as (
                select
                    m.id as id,
                    pick.type as type,
                    pick.date_done as date_done,
                    sale.id as sale_id,
                    pick.id as picking_id,
                    sale.user_id as sale_uid,
                    sale.section_id as section_id,
                    sale.platform_user_id as seller_name,
                    sale.platform_seller_id as buyer_name,
                    case pick.type
                        when 'in' then  -m.product_qty
                        when 'out' then   m.product_qty
                    end as product_qty,
                    product.id as product_id,
                    m.location_id as location_id,
                    sl.price_unit as price_unit,
                    (sl.price_unit * product_qty) as total,
                    m.location_dest_id as location_dest_id,
                    to_char(pick.date_done, 'YYYY') as year,
                    to_char(pick.date_done, 'MM') as month,
                    to_char(pick.date_done, 'YYYY-MM-DD') as day
                from
                    stock_picking as pick
                    left join  sale_order sale on (sale.id = pick.sale_id)
                    left join stock_move m on (m.picking_id = pick.id)
                    left join product_product product on (product.id = m.product_id)
                    left join sale_order_line sl on (sl.id =m.sale_line_id)
                where
                    pick.state ='done' and pick.sale_id is not NULL
            )
        """)

sales_performance_report()


#########
