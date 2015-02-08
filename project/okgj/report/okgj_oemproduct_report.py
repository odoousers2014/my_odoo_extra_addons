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
from lxml import etree

class okgj_report_oemproduct(osv.osv_memory):
    _name = "okgj.report.oemproduct"
okgj_report_oemproduct()

#仓库，商品分类，品牌，条码，品名
class okgj_report_oemproduct_lines(osv.osv_memory):
    _name = "okgj.report.oemproduct.lines"
    _description = u"OEM商品统计"
    _columns = {
        'okgjcity':fields.char(u'城市',readonly=True),
        'okgjproductnumber':fields.char(u'商品编码',readonly=True),
        'okgjproductname':fields.char(u'商品名称',readonly=True),
        'amount': fields.float(u'商品总金额', readonly=True),
        'billcount': fields.float(u'商品总数量', readonly=True),
        'price': fields.float(u'单价', readonly=True),
        'orderSN':fields.integer(u'序号',readonly=True),
        'grossprofit':fields.float(u'毛利',readonly=True),
        'costprice':fields.float(u'单位成本',readonly=True),
        'totalcost':fields.float(u'总成本',readonly=True),
        'profitrate':fields.float(u'毛利率(%)',readonly=True),
        'report_oemproduct_id':fields.many2one('okgj.report.oemproduct',u'商品统计单号',readonly=True),
    }
okgj_report_oemproduct_lines()

class okgj_report_oemproduct(osv.osv_memory):
    _inherit = "okgj.report.oemproduct"
    _columns = {
        'okgj_iswholeday':fields.boolean(u'当天订单'),
        'first_start_date':fields.datetime(u'开始日期/时间'),
        'first_end_date':fields.datetime(u'结束日期/时间'),
        'okgj_productnumber':fields.char(u'商品编码/名称'),
        'okgj_includeproduct':fields.boolean(u'只含单品'),
        'okgj_brand':fields.char(u'商品品牌'),
        'line_ids':fields.one2many('okgj.report.oemproduct.lines', 'report_oemproduct_id', u'明细行', readonly=True),
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
        product_number=form.okgj_productnumber
        isincludeproduct=form.okgj_includeproduct
        #品牌
        okgj_brand = form.okgj_brand
        ##删除历史数据
        line_ids = [one_line.id for one_line in form.line_ids]
        if line_ids:
            self.pool.get('okgj.report.oemproduct.lines').unlink(cr, SUPERUSER_ID, line_ids,)
        
        strWhere=' 1=1 '        
        if not (product_number or okgj_brand):
            raise osv.except_osv((u'无效动作:'), (u'请输入要查询的商品或者品牌!'))
        if product_number:
            strWhere=strWhere+" And (p.name_template like '%"+product_number.encode('utf-8')+"%' or p.default_code='"+product_number.encode('utf-8')+"') "
        if okgj_brand:
            brand_ids = self.pool.get('okgj.product.brand').search(cr, uid, [('name', '=', okgj_brand)], context=context)
            if brand_ids:
                strWhere=strWhere+" And (p.brand_id ="+str(brand_ids[0])+") "
            else:
                return False
        if start_date_data:
            strWhere=strWhere+" And (so.date_order2)>= '"+str(start_date_data)+"'"
        if end_date_data:
            strWhere=strWhere+" And (so.date_order2) <= '"+str(end_date_data)+"'"
        if isincludeproduct:
            sqlstr=self.getProductSQL(cr, uid, curid,strWhere,context=context)
        else:
            sqlstr=self.getGroupProductSQL(cr, uid, curid,strWhere,context=context)
        
        cr.execute(sqlstr)
        results = cr.fetchall()

        data = []

        for result  in results:
            data.append((0, 0, {
                'orderSN' : result[0] and result[0] or 0.0,
                'okgjcity' : result[1] and result[1] or '',
                'okgjproductnumber' : result[2] and result[2] or '',
                'okgjproductname':result[3] and result[3] or '',
                'billcount' : result[4] and result[4] or 0.0,
                'price' : result[5] and result[5] or 0.0,
                'costprice' : result[6] and result[6] or 0,
                'amount' : result[7] and result[7] or 0,
                'grossprofit' : result[8] and result[8] or 0,
                'profitrate' : result[9] and result[9] or 0,
                'totalcost' : result[10] and result[10] or 0,

            }))
            
        self.write(cr, uid, curid, {'line_ids':data}, context=context)
        return True

    def getProductSQL(self, cr, uid, ids, strWhere=False,context=None):

        strSQL=""" 
            select row_number() over(order by indexs) indexs,
            okgjcity,default_code,pname,qty,saleprice,costprice,
            amount,diff,diffrate,costtotal
             from (
            select row_number() over(order by okgjcity,indexs,qty desc) indexs,
            okgjcity,default_code,pname,qty,saleprice,costprice,
            amount,diff,diffrate,costtotal  from
            (select 
            1 as indexs,
            oemdetail.okgjcity,oemdetail.default_code,oemdetail.pname,oemdetail.qty,oemdetail.saleprice,oemdetail.costprice,
            oemdetail.amount,oemdetail.diff,oemdetail.diffrate,costtotal from (
            select 
            COALESCE(so.okgj_city,'深圳') as okgjcity,p.default_code,p.name_template as pname,
            sum(COALESCE(s.product_uom_qty,0))qty
            ,COALESCE(s.price_unit,0) as saleprice,COALESCE(s.purchase_price,0) as costprice,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.price_unit,0) as amount
            ,(COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))* sum(COALESCE(s.product_uom_qty,0)) as diff,
            case COALESCE(s.price_unit,0) when 0 then 0 
            else ((COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))/COALESCE(s.price_unit,0))*100 end as diffrate,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.purchase_price,0) as costtotal
            from stock_move v 
            left join product_product p on v.product_id=p.id
            left join sale_order_line s on v.sale_line_id=s.id
            left join sale_order so on s.order_id=so.id
            where v.sale_line_id is not null and so.state not in('cancel') and so.okgj_shop_cancel<>'t' and p.is_group_product='f'
            and """+strWhere+"""
            group by COALESCE(so.okgj_city,'深圳'),p.default_code,p.name_template,s.price_unit,s.purchase_price)oemdetail
            union
            select 
            2 as indexs,
            oemcount.okgjcity,'合计' default_code,'' as pname,sum(oemcount.qty),0 as saleprice,0 as costprice,
            sum(oemcount.amount),sum(diff) as diff,
            case sum(oemcount.amount) when 0 then 0 else 
            ((sum(oemcount.amount)-sum(oemcount.costtotal))/sum(oemcount.amount))*100 end diffrate,
            sum(oemcount.costtotal) as costtotal  from (
            select 
            COALESCE(so.okgj_city,'深圳') as okgjcity,p.default_code,p.name_template as pname,
            sum(COALESCE(s.product_uom_qty,0))qty
            ,COALESCE(s.price_unit,0) as saleprice,COALESCE(s.purchase_price,0) as costprice,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.price_unit,0) as amount
            ,(COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))* sum(COALESCE(s.product_uom_qty,0)) as diff,
            case COALESCE(s.price_unit,0) when 0 then 0 
            else ((COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))/COALESCE(s.price_unit,0))*100 end as diffrate,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.purchase_price,0) as costtotal
            from stock_move v 
            left join product_product p on v.product_id=p.id
            left join sale_order_line s on v.sale_line_id=s.id
            left join sale_order so on s.order_id=so.id
            where v.sale_line_id is not null and so.state not in('cancel') and so.okgj_shop_cancel<>'t' and p.is_group_product='f'
            and """+strWhere+"""
            group by COALESCE(so.okgj_city,'深圳'),p.default_code,p.name_template,s.price_unit,s.purchase_price)oemcount
            group by oemcount.okgjcity
            )tt
            union
            select 
            99999999 as indexs,
            '总计' as okgjcity,'' default_code,'' as pname,sum(oemtotal.qty),0 as saleprice,0 as costprice,
            sum(oemtotal.amount),sum(diff) as diff,
            case sum(oemtotal.amount) when 0 then 0 else 
            ((sum(oemtotal.amount)-sum(oemtotal.costtotal))/sum(oemtotal.amount))*100 end diffrate,
            sum(oemtotal.costtotal) as costtotal  from (
            select 
            COALESCE(so.okgj_city,'深圳') as okgjcity,p.default_code,p.name_template as pname,
            sum(COALESCE(s.product_uom_qty,0))qty
            ,COALESCE(s.price_unit,0) as saleprice,COALESCE(s.purchase_price,0) as costprice,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.price_unit,0) as amount
            ,(COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))* sum(COALESCE(s.product_uom_qty,0)) as diff,
            case COALESCE(s.price_unit,0) when 0 then 0 
            else ((COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))/COALESCE(s.price_unit,0))*100 end as diffrate,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.purchase_price,0) as costtotal
            from stock_move v 
            left join product_product p on v.product_id=p.id
            left join sale_order_line s on v.sale_line_id=s.id
            left join sale_order so on s.order_id=so.id
            where v.sale_line_id is not null and so.state not in('cancel') and so.okgj_shop_cancel<>'t' and p.is_group_product='f'
            and """+strWhere+"""
            group by COALESCE(so.okgj_city,'深圳'),p.default_code,p.name_template,s.price_unit,s.purchase_price)oemtotal
            )ttt
        """
        return strSQL

    def getGroupProductSQL(self, cr, uid, ids, strWhere=False,context=None):
        strSQL="""
            select row_number() over(order by indexs) indexs,
            okgjcity,default_code,pname,qty,saleprice,costprice,
            amount,diff,diffrate ,costtotal
             from (
            select row_number() over(order by okgjcity,indexs,qty desc) indexs,
            okgjcity,default_code,pname,qty,saleprice,costprice,
            amount,diff,diffrate, costtotal  from
            (select 
            1 as indexs,
            oemdetail.okgjcity,oemdetail.default_code,oemdetail.pname,oemdetail.qty,oemdetail.saleprice,oemdetail.costprice,
            oemdetail.amount,oemdetail.diff,oemdetail.diffrate,costtotal from (
            select 
            COALESCE(so.okgj_city,'深圳') as okgjcity,p.default_code,p.name_template as pname,
            sum(COALESCE(s.product_uom_qty,0))qty
            ,COALESCE(s.price_unit,0) as saleprice,COALESCE(s.purchase_price,0) as costprice,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.price_unit,0) as amount
           ,(COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))* sum(COALESCE(s.product_uom_qty,0)) as diff,
            case COALESCE(s.price_unit,0) when 0 then 0 
            else ((COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))/COALESCE(s.price_unit,0))*100 end as diffrate
            ,sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.purchase_price,0) as costtotal
            from sale_order_line s 
            left join product_product p on s.product_id=p.id
            --left join sale_order_line s on v.id=s.id
            left join sale_order so on s.order_id=so.id
            where  so.state not in('cancel') and so.okgj_shop_cancel<>'t'
            and """+strWhere+"""
            group by COALESCE(so.okgj_city,'深圳'),p.default_code,p.name_template,s.price_unit,s.purchase_price)oemdetail
            union
            select 
            2 as indexs,
            oemcount.okgjcity,'合计' default_code,'' as pname,sum(oemcount.qty),0 as saleprice,0 as costprice,
            sum(oemcount.amount),sum(diff) as diff,
            case sum(oemcount.amount) when 0 then 0 else 
            ((sum(oemcount.amount)-sum(oemcount.costtotal))/sum(oemcount.amount))*100 end diffrate,
            sum(oemcount.costtotal) as costtotal from (
            select 
            COALESCE(so.okgj_city,'深圳') as okgjcity,p.default_code,p.name_template as pname,
            sum(COALESCE(s.product_uom_qty,0))qty
            ,COALESCE(s.price_unit,0) as saleprice,COALESCE(s.purchase_price,0) as costprice,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.price_unit,0) as amount
            ,(COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))* sum(COALESCE(s.product_uom_qty,0)) diff,
            case COALESCE(s.price_unit,0) when 0 then 0 
            else ((COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))/COALESCE(s.price_unit,0))*100 end as diffrate,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.purchase_price,0) as costtotal
            from sale_order_line s 
            left join product_product p on s.product_id=p.id
            --left join sale_order_line s on v.id=s.id
            left join sale_order so on s.order_id=so.id
            where so.state not in('cancel') and so.okgj_shop_cancel<>'t'
            and """+strWhere+"""
            group by COALESCE(so.okgj_city,'深圳'),p.default_code,p.name_template,s.price_unit,s.purchase_price)oemcount
            group by oemcount.okgjcity
            )tt
            union
            select 
            99999999 as indexs,
            '总计' as okgjcity,'' default_code,'' as pname,sum(oemtotal.qty),0 as saleprice,0 as costprice,
            sum(oemtotal.amount),sum(diff) as diff,
            case sum(oemtotal.amount) when 0 then 0 else 
            ((sum(oemtotal.amount)-sum(oemtotal.costtotal))/sum(oemtotal.amount))*100 end diffrate
            , sum(oemtotal.costtotal) as costtotal from (
            select 
            COALESCE(so.okgj_city,'深圳') as okgjcity,p.default_code,p.name_template as pname,
            sum(COALESCE(s.product_uom_qty,0))qty
            ,COALESCE(s.price_unit,0) as saleprice,COALESCE(s.purchase_price,0) as costprice,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.price_unit,0) as amount
            ,(COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))* sum(COALESCE(s.product_uom_qty,0)) as diff,
            case COALESCE(s.price_unit,0) when 0 then 0 
            else ((COALESCE(s.price_unit,0)-COALESCE(s.purchase_price,0))/COALESCE(s.price_unit,0))*100 end as diffrate,
            sum(COALESCE(s.product_uom_qty,0))*COALESCE(s.purchase_price,0) as costtotal
            from sale_order_line s 
            left join product_product p on s.product_id=p.id
            --left join sale_order_line s on v.id=s.id
            left join sale_order so on s.order_id=so.id
            where   so.state not in('cancel') and so.okgj_shop_cancel<>'t'
            and """+strWhere+"""
            group by COALESCE(so.okgj_city,'深圳'),p.default_code,p.name_template,s.price_unit,s.purchase_price)oemtotal
            )ttt
        """

        return strSQL
    
okgj_report_oemproduct()
