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

class okgj_report_guestfolio(osv.osv_memory):
    _name = "okgj.report.guestfolio"
okgj_report_guestfolio()

#仓库，商品分类，品牌，条码，品名
class okgj_report_guestfolio_lines(osv.osv_memory):
    _name = "okgj.report.guestfolio.lines"
    _description = u"订单统计"
    _columns = {
        'ordertotalamount': fields.float(u'订单总金额', readonly=True),
        'totalamount': fields.float(u'商品总金额', readonly=True),
        'totalcount': fields.float(u'总单量', readonly=True),
        'price': fields.float(u'客单价', readonly=True),
        'shippingfee':fields.float(u'物流费',readonly=True),
        'shippingfeerate':fields.float(u'物流费占比(%)',readonly=True),
        'shipfee':fields.float(u'基本物流费',readonly=True),
        'shipfeerate':fields.float(u'基本物流费占比(%)',readonly=True),
        'weightfee':fields.float(u'超重费',readonly=True),
        'weightfeerate':fields.float(u'超重费占比(%)',readonly=True),
        'okgjformulatefee':fields.float(u'预约物流费',readonly=True),
        'okgjformulatefeerate':fields.float(u'预约物流费占比(%)',readonly=True),
        'carcount':fields.float(u'装车单数',readonly=True),
        'okgjcity':fields.char(u'城市',readonly=True),
        'orderSN':fields.integer(u'序号',readonly=True),
        'report_guestfolio_id':fields.many2one('okgj.report.guestfolio',u'订单统计单号',readonly=True),
    }
okgj_report_guestfolio_lines()

class okgj_report_guestfolio(osv.osv_memory):
    _inherit = "okgj.report.guestfolio"
    _columns = {
        'okgj_iswholeday':fields.boolean(u'当天订单'),
        'first_start_date':fields.datetime(u'开始日期/时间'),
        'first_end_date':fields.datetime(u'结束日期/时间'),
        'line_ids':fields.one2many('okgj.report.guestfolio.lines', 'report_guestfolio_id', u'明细行', readonly=True),
    }

    _defaults = {
        'okgj_iswholeday': False,
        ## 'first_start_date': (datetime.datetime.strptime(datetime.date.today().strftime("%Y-%m-%d 00:00:00"), "%Y-%m-%d %H:%M:%S")-datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
        ## 'first_end_date' : (datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")).strftime("%Y-%m-%d %H:%M:%S")
    }

    def onchange_wholeday(self, cr, uid, ids, wholeday=False, context=None):
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
        okgj_iswholeday=form.okgj_iswholeday
        
        ##删除历史数据
        line_ids = [one_line.id for one_line in form.line_ids]
        if line_ids:
            self.pool.get('okgj.report.guestfolio.lines').unlink(cr, SUPERUSER_ID, line_ids,)
        
        strWhere=' AND 1=1 '               
        strWherelogis=' AND 1=1 '
        if okgj_iswholeday:

            start_date_data=(datetime.datetime.strptime(datetime.date.today().strftime("%Y-%m-%d 00:00:00"),  "%Y-%m-%d %H:%M:%S")-datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S") 
            end_date_data=time.strftime('%Y-%m-%d 15:59:59')

        if start_date_data:
            strWhere=strWhere+" And (saleorder.date_order2)>= '"+str(start_date_data)+"'"
            strWherelogis=strWherelogis+" And create_date>= '"+str(start_date_data)+"'"
        if end_date_data:
            strWhere=strWhere+" And (saleorder.date_order2) <= '"+str(end_date_data)+"'"
            strWherelogis=strWherelogis+" And create_date<= '"+str(end_date_data)+"'"
        
        sqlstr="""
            select totalamount,totalcount,price,shipfee,shippingfee,weightfee,carcount
            ,shippingfeerate,ordertotalamount,
            shipfeerate,weightfeerate,okgjcity,row_number() over(order by indexs,totalamount desc) as orderSN,
            indexs,okgjformulatefee,okgjformulatefeerate
            from (
                select totalamount,totalcount,price,shipfee,shippingfee,weightfee,COALESCE(carcount,0)carcount
                ,shippingfeerate,ordertotalamount,
                shipfeerate,weightfeerate,ordercount.okgjcity,2 as indexs,okgjformulatefee,okgjformulatefeerate
                from( 
                    select COALESCE(okgj_city,'深圳') as okgjcity, sum(goods_amount)-sum(discount)  as totalamount,count(*) as totalcount,
                    case coalesce(count(*),0) when 0 then 0 else (sum(goods_amount)-sum(discount))/count(*) end as price,
                    sum(ship_fee) as shipfee,sum(shipping_fee) as shippingfee,sum(weight_fee) as weightfee,
                    sum(goods_amount)-sum(discount)+sum(shipping_fee) as ordertotalamount,
                    case (sum(goods_amount)-sum(discount)+sum(shipping_fee)) when 0 then 0
                    else (sum(shipping_fee)/(sum(goods_amount)-sum(discount)+sum(shipping_fee)))*100 end as shippingfeerate,
                    case (sum(goods_amount)-sum(discount)+sum(shipping_fee)) when 0 then 0
                    else (sum(ship_fee)/(sum(goods_amount)-sum(discount)+sum(shipping_fee)))*100 end as shipfeerate,
                    case (sum(goods_amount)-sum(discount)+sum(shipping_fee)) when 0 then 0
                    else (sum(weight_fee)/(sum(goods_amount)-sum(discount)+sum(shipping_fee)))*100 end as weightfeerate,
                    sum(okgj_formulate_fee) as okgjformulatefee,
                    case (sum(goods_amount)-sum(discount)+sum(shipping_fee)) when 0 then 0
                    else (sum(okgj_formulate_fee)/(sum(goods_amount)-sum(discount)+sum(shipping_fee)))*100 end as okgjformulatefeerate
                    from sale_order saleorder 
                    where  saleorder.state not in('cancel') """+strWhere+"""
                    group by COALESCE(okgj_city,'深圳') order by sum(goods_amount) desc
                    --AND  (saleorder.date_order2)>=%s and  (saleorder.date_order2) <=%s
                    )ordercount
                    left join
                    (select COALESCE(sale_okgj_city,'深圳')  as okgjcity,count(COALESCE(sale_order_id,0))carcount from okgj_logistics_line
                     where 1=1 """+strWherelogis+"""
                     group by COALESCE(sale_okgj_city,'深圳') 
                    -- create_date>=%s and create_date<=%s
                    )carcount on ordercount.okgjcity=carcount.okgjcity
            union 
                select totalamount,totalcount,price,shipfee,shippingfee,weightfee,COALESCE(carcount,0)carcount
                ,shippingfeerate,ordertotalamount,
                shipfeerate,weightfeerate,'合计' as okgjcity,999999999 as indexs,okgjformulatefee,okgjformulatefeerate
                from( 
                    select 1 as okgjcity, sum(goods_amount)-sum(discount)  as totalamount,count(*) as totalcount,
                    case coalesce(count(*),0) when 0 then 0 else (sum(goods_amount)-sum(discount))/count(*) end as price,
                    sum(ship_fee) as shipfee,sum(shipping_fee) as shippingfee,sum(weight_fee) as weightfee,
                    sum(goods_amount)-sum(discount)+sum(shipping_fee) as ordertotalamount,
                    case (sum(goods_amount)-sum(discount)+sum(shipping_fee)) when 0 then 0
                    else (sum(shipping_fee)/(sum(goods_amount)-sum(discount)+sum(shipping_fee)))*100 end as shippingfeerate,
                    case (sum(goods_amount)-sum(discount)+sum(shipping_fee)) when 0 then 0
                    else (sum(ship_fee)/(sum(goods_amount)-sum(discount)+sum(shipping_fee)))*100 end as shipfeerate,
                    case (sum(goods_amount)-sum(discount)+sum(shipping_fee)) when 0 then 0
                    else (sum(weight_fee)/(sum(goods_amount)-sum(discount)+sum(shipping_fee)))*100 end as weightfeerate,
                    sum(okgj_formulate_fee) as okgjformulatefee,
                    case (sum(goods_amount)-sum(discount)+sum(shipping_fee)) when 0 then 0
                    else (sum(okgj_formulate_fee)/(sum(goods_amount)-sum(discount)+sum(shipping_fee)))*100 end as okgjformulatefeerate
                    from sale_order saleorder 
                    where  saleorder.state not  in('cancel') """+strWhere+"""
                    --AND  (saleorder.date_order2)>=%s and  (saleorder.date_order2) <=%s
                    )ordercount
                    left join
                    (select 1 as okgjcity,count(COALESCE(sale_order_id,0))carcount from okgj_logistics_line
                     where 1=1 """+strWherelogis+"""
                    -- create_date>=%s and create_date<=%s
                    )carcount on ordercount.okgjcity=carcount.okgjcity)total
        """
        cr.execute(sqlstr)
        results = cr.fetchall()

        data = []

        for result  in results:
            data.append((0, 0, {
                'totalamount' : result[0] and result[0] or 0.0,
                'totalcount' : result[1] and result[1] or 0.0,
                'price' : result[2] and result[2] or 0.0,
                'shipfee':result[3] and result[3] or 0.0,
                'shippingfee' : result[4] and result[4] or 0.0,
                'weightfee' : result[5] and result[5] or 0.0,
                'carcount' : result[6] and result[6] or 0,
                'shippingfeerate' : result[7] and result[7] or 0.0,
                'ordertotalamount' : result[8] and result[8] or 0.0,
                'shipfeerate' : result[9] and result[9] or 0.0,
                'weightfeerate' : result[10] and result[10] or 0.0,
                'okgjcity' : result[11] and result[11] or 0.0,
                'orderSN' : result[12] and result[12] or 0.0,
                'okgjformulatefee': result[14] and result[14] or 0.0,
                'okgjformulatefeerate': result[15] and result[15] or 0.0,
            }))
            
        self.write(cr, uid, curid, {'line_ids':data}, context=context)
        return True
    
okgj_report_guestfolio()
