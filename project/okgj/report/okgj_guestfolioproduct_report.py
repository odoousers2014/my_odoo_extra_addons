# -*- coding: utf-8 -*-

from openerp import tools
from osv import fields, osv
import openerp.addons.decimal_precision as dp
import re
import time
import datetime
from dateutil import relativedelta
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

class okgj_report_guestfolioproduct(osv.osv_memory):
    _name = "okgj.report.guestfolioproduct"
okgj_report_guestfolioproduct()

#仓库，商品分类，品牌，条码，品名
class okgj_report_guestfolioproduct_lines(osv.osv_memory):
    _name = "okgj.report.guestfolioproduct.lines"
    _description = u"商品统计"
    _columns = {
        'amount': fields.float(u'商品总金额', readonly=True),
        'billcount': fields.float(u'总单量', readonly=True),
        'price': fields.float(u'客单价', readonly=True),
        'okgjcity':fields.char(u'城市',readonly=True),
        'catename':fields.char(u'商品分类',readonly=True),
        'orderSN':fields.integer(u'序号',readonly=True),
        'grossprofit':fields.float(u'毛利',readonly=True),
        'totalcost':fields.float(u'总成本',readonly=True),
        'profitrate':fields.float(u'毛利率(%)',readonly=True),
        'report_guestfolioproduct_id':fields.many2one('okgj.report.guestfolioproduct',u'商品统计单号',readonly=True),
    }
okgj_report_guestfolioproduct_lines()

class okgj_report_guestfolioproduct(osv.osv_memory):
    _inherit = "okgj.report.guestfolioproduct"
    _columns = {
        'okgj_iswholeday':fields.boolean(u'当天订单'),
        'first_start_date':fields.datetime(u'开始日期/时间'),
        'first_end_date':fields.datetime(u'结束日期/时间'),
		'category_id':fields.many2one('product.category', u'商品分类',required=True),
        'line_ids':fields.one2many('okgj.report.guestfolioproduct.lines', 'report_guestfolioproduct_id', u'明细行', readonly=True),
    }
    _defaults = {
        'okgj_iswholeday': False,
    }


    def onchange_wholeday(self, cr, uid, ids,wholeday=False, context=None):
	if (wholeday):
            results = {
                'first_start_date':False, 
                'first_end_date': False
            }
        else:
            if datetime.datetime.now().hour < 16:
                first_start_date = (datetime.datetime.strptime(datetime.date.today().strftime("%Y-%m-%d 00:00:00"), "%Y-%m-%d %H:%M:%S")-datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                first_start_date = (datetime.datetime.strptime(datetime.date.today().strftime("%Y-%m-%d 00:00:00"), "%Y-%m-%d %H:%M:%S")+datetime.timedelta(hours=16)).strftime("%Y-%m-%d %H:%M:%S")
            first_end_date = (datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S")
            results = {
                'first_start_date':first_start_date, 
                'first_end_date': first_end_date
            }
        return {'value':results}


    def _get_final_categ_products(self, cr, uid, cate_id, context=None):
        """
        @param cate_id: product category id
        @return: the lowest category id
        """
        cate_obj = self.pool.get('product.category')
        child_ids = []
        def get_child_child(cr, uid, cate_id, context=None):
            childs = cate_obj.browse(cr, uid, cate_id, context=context).child_id
            for one_children in childs:
                if one_children.child_id:
                    get_child_child(cr, uid, one_children.id, context=context)
                else:
                    child_ids.append(one_children.id)
        get_child_child(cr, uid, cate_id, context=context)
        if not child_ids:
             child_ids = [cate_id]
        return child_ids

    def do_import(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}
        today = fields.date.context_today(cr, uid, ids, context=context)
        if isinstance(ids, (int, long)):
            curid=ids
        else:
            curid=ids[0]

        form = self.browse(cr, uid, curid, context=context)
        start_date_data = form.first_start_date
        end_date_data = form.first_end_date
        okgj_category= form.category_id.id
        
        ##删除历史数据
        line_ids = [one_line.id for one_line in form.line_ids]
        if line_ids:
            self.pool.get('okgj.report.guestfolioproduct.lines').unlink(cr, SUPERUSER_ID, line_ids,)
        
        strWhere=' AND 1=1 '        

        categ_ids = self._get_final_categ_products(cr, uid, okgj_category)
        if len(categ_ids) == 1:
            categ_ids_str = "(" + str(categ_ids[0]) + ")"
        else:
            categ_ids_str = str(tuple(categ_ids))

        if okgj_category:
            strWhere=strWhere+" And productcategory.id in "+ categ_ids_str
        if start_date_data:
            strWhere=strWhere+" And (saleorder.date_order2)>= '"+str(start_date_data)+"'"
        if end_date_data:
            strWhere=strWhere+" And (saleorder.date_order2) <= '"+str(end_date_data)+"'"
        
        sqlstr="""
            select row_number() over(order by indexs,amount desc) as orderSN,catename,okgj_city,billcount,amount,price,grossprofit,totalcost,profitrate
            from (
            select row_number() over(order by catename,indexs,amount desc) indexs,catename,okgj_city,billcount,amount,price,grossprofit,totalcost,profitrate from (
			select 1 as indexs,t.catename,t.okgj_city,sum(t.billcount)billcount,sum(t.amount)amount,
            case sum(t.billcount) when 0 then 0 else sum(t.amount)/sum(t.billcount) end as price,
            sum(t.grossprofit)grossprofit,sum(totalcost)totalcost,
            case sum(t.amount) when 0 then 0 else ((sum(t.amount-t.totalcost))/sum(t.amount))*100 end profitrate
			from (
			select COALESCE(okgj_city,'深圳')okgj_city,COALESCE(productcategory.name,'')catename,
			count(distinct saleorder.name) as billcount,
			sum(COALESCE(price_unit,0)*COALESCE(product_uom_qty,0)) as amount,
            (sum((COALESCE(price_unit,0)-COALESCE(purchase_price,0))*COALESCE(product_uom_qty,0))) as grossprofit,
            sum(COALESCE(purchase_price,0)*COALESCE(product_uom_qty,0)) totalcost
			from sale_order saleorder 
			left join sale_order_line saleorderline on saleorder.id=saleorderline.order_id
			left join product_product orderproduct on saleorderline.product_id=orderproduct.id
			inner join product_template producttemp on orderproduct.product_tmpl_id=producttemp.id
			left join product_category productcategory on producttemp.categ_id=productcategory.id
			left join okgj_product_brand okgjbrand on orderproduct.brand_id=okgjbrand.id
			where  saleorder.state not in('cancel') """+strWhere+"""
			group by COALESCE(okgj_city,'深圳') ,COALESCE(productcategory.name,'')
			)t group by t.okgj_city,t.catename
			union
			select 2 as indexs,t.catename,'合计' as okgj_city,sum(t.billcount)billcount,sum(t.amount)amount,
            case sum(t.billcount) when 0 then 0 else sum(t.amount)/sum(t.billcount) end as price
			,sum(t.grossprofit)grossprofit,sum(totalcost)totalcost,
            case sum(t.amount) when 0 then 0 else ((sum(t.amount-t.totalcost))/sum(t.amount))*100 end profitrate
			from (
			select COALESCE(productcategory.name,'')catename,
			count(distinct saleorder.name) as billcount,
			sum(COALESCE(price_unit,0)*COALESCE(product_uom_qty,0)) as amount,
            (sum((COALESCE(price_unit,0)-COALESCE(purchase_price,0))*COALESCE(product_uom_qty,0))) as grossprofit,
            sum(COALESCE(purchase_price,0)*COALESCE(product_uom_qty,0)) totalcost
			from sale_order saleorder 
			left join sale_order_line saleorderline on saleorder.id=saleorderline.order_id
			left join product_product orderproduct on saleorderline.product_id=orderproduct.id
			inner join product_template producttemp on orderproduct.product_tmpl_id=producttemp.id
			left join product_category productcategory on producttemp.categ_id=productcategory.id
			left join okgj_product_brand okgjbrand on orderproduct.brand_id=okgjbrand.id
			where  saleorder.state not in('cancel') """+strWhere+"""
			group by COALESCE(productcategory.name,'')
			)t group by t.catename)tt
            union
            select 999999999 as indexs,'' as catename,'总计' as okgj_city,sum(t.billcount)billcount,
            sum(t.amount)amount,
            case sum(t.billcount) when 0 then 0 else sum(t.amount)/sum(t.billcount) end as price,
            sum(t.grossprofit)grossprofit,sum(t.totalcost)totalcost,
            case sum(t.amount) when 0 then 0 else ((sum(t.amount-t.totalcost))/sum(t.amount))*100 end profitrate
            from (
            select count(distinct saleorder.name) as billcount,
            sum(COALESCE(price_unit,0)*COALESCE(product_uom_qty,0)) as amount,
            (sum((COALESCE(price_unit,0)-COALESCE(purchase_price,0))*COALESCE(product_uom_qty,0))) as grossprofit,
            sum(COALESCE(purchase_price,0)*COALESCE(product_uom_qty,0)) totalcost
            from sale_order saleorder 
            left join sale_order_line saleorderline on saleorder.id=saleorderline.order_id
            left join product_product orderproduct on saleorderline.product_id=orderproduct.id
            inner join product_template producttemp on orderproduct.product_tmpl_id=producttemp.id
            left join product_category productcategory on producttemp.categ_id=productcategory.id
            left join okgj_product_brand okgjbrand on orderproduct.brand_id=okgjbrand.id
            where  saleorder.state not in('cancel') """+strWhere+"""
            )t)ttt2
            
        """
        cr.execute(sqlstr)
        results = cr.fetchall()

        data = []

        for result  in results:
            data.append((0, 0, {
                'orderSN' : result[0] and result[0] or 0.0,
                'catename' : result[1] and result[1] or '',
                'okgjcity' : result[2] and result[2] or '',
                'billcount':result[3] and result[3] or 0.0,
                'amount' : result[4] and result[4] or 0.0,
                'price' : result[5] and result[5] or 0.0,
                'grossprofit' : result[6] and result[6] or 0,
                'totalcost' : result[7] and result[7] or 0,
                'profitrate' : result[8] and result[8] or 0,
            }))
            
        self.write(cr, uid, curid, {'line_ids':data}, context=context)
        return True
    
okgj_report_guestfolioproduct()
