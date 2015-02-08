# -*- coding: utf-8 -*-

from openerp import tools
from osv import fields, osv
import openerp.addons.decimal_precision as dp
import re
import datetime
from openerp.tools.translate import _

#物流中心，商品分类，供应商，品牌，条码，品名，上周日期，本周日期
class okgj_report_sales_comp_wizard(osv.osv_memory):
    _name = "okgj.report.sales.comp.wizard"
    _columns = {
        'category_id':fields.many2one('product.category', u'类别'),
        'supplier_id':fields.many2one('res.partner', u'供应商'),
        'brand_id':fields.many2one('okgj.product.brand', u'品牌'),
        'product_id':fields.many2one('product.product', u'商品'),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True),
        'first_start_date':fields.date(u'上期开始日期', required=True),
        'first_end_date':fields.date(u'上期结束日期', required=True),
        'second_start_date':fields.date(u'本期开始日期', required=True),
        'second_end_date':fields.date(u'本期结束日期', required=True),
    }

    def _default_warehouse_id(self, cr, uid, context=None):
        user_data = self.pool.get('res.users').browse(cr,uid, uid, context=context)
        warehouse_id = False
        for one_warehouse in user_data.warehouse_ids:
            warehouse_id = one_warehouse.id
            if warehouse_id:
                break
        return warehouse_id

    _defaults = {
        'warehouse_id': _default_warehouse_id,
	'first_start_date':lambda *a: (datetime.date.today()-datetime.timedelta(days=6)).strftime('%Y-%m-%d'),	
	'first_end_date':lambda *a: datetime.date.today().strftime('%Y-%m-%d'),
	'second_start_date':lambda *a: datetime.date.today().strftime('%Y-%m-%d'),
	'second_end_date':lambda *a: datetime.date.today().strftime('%Y-%m-%d'),
    }

    def _get_final_categ(self, cr, uid, cate_id, context=None):
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

    def _get_supplier_product(self, cr, uid, supplier_id, context=None):
        """
        @param supplier_id: supplier id
        @return: product_ids
        """
        supplierinfo_obj = self.pool.get("product.supplierinfo")
        product_obj = self.pool.get("product.product")
        supplierinfo_ids = supplierinfo_obj.search(cr, uid, [('name', '=', supplier_id)], context=context)
        product_tmpl_ids = [i['product_id'][0] for i in supplierinfo_obj.read(cr, uid, supplierinfo_ids, ['product_id'], context=context)]
        product_ids = []
        for one_tmpl_id in product_tmpl_ids:
            product_ids += product_obj.search(cr, uid, [('product_tmpl_id', '=', one_tmpl_id)], context=context)
        return product_ids

    def action_open_window(self, cr, uid, ids, context=None):
        """
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param ids: the ID or list of IDs if we want more than one
            @return:
        """
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids[0], context=context)
        search_domain = []
        if data.category_id:
            search_domain.append(('categ_id', 'in', self._get_final_categ(cr, uid, data.category_id.id)))
        if data.supplier_id:
            search_domain.append(('id', 'in', self._get_supplier_product(cr, uid, data.supplier_id.id)))
        if data.brand_id:
            search_domain.append(('brand_id', '=', data.brand_id.id))
        if data.product_id:
            search_domain.append(('id', '=', data.product_id.id))
        domain_ids = self.pool.get('product.product').search(cr, uid, search_domain)
        #context.update({'domain_ids':domain_ids})
        domain = [('id', 'in', domain_ids)]
        
        if data.warehouse_id:
            context.update({'warehouse_id':data.warehouse_id.id})
        if data.first_start_date:
            context.update({'first_start_date':data.first_start_date})
        if data.first_end_date:
            context.update({'first_end_date':data.first_end_date})
        if data.second_start_date:
            context.update({'second_start_date':data.second_start_date})
        if data.second_end_date:
            context.update({'second_end_date':data.second_end_date})
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'okgj', 'view_okgj_report_sales_comp_tree')
        view_id = view_ref and view_ref[1] or False,
        
        return {
            'name': _('销售环比报表'),
            'context': context,
            'view_type': 'form',
            "view_mode": 'tree',
            'res_model':'product.product',
            'type': 'ir.actions.act_window',
            'view_id':view_id,
            'domain' : domain,
        }
okgj_report_sales_comp_wizard()

class report_sales_comp(osv.osv):

    def _get_invamount(self, cr, uid, ids, field_names, arg, context=None):
        """ 获取库存金额
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        result = {}.fromkeys(ids, 0.0)
        for one_product in self.browse(cr, uid, ids, context=context):
            result[one_product.id] = one_product.qty_available * one_product.okgj_cost_price
        return result

    def _get_comp(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        if context is None:
            context = {}
        #domain_ids = context.get('domain_ids', False)
        first_start_date = context.get('first_start_date', False)
        first_end_date = context.get('first_end_date', False)
        second_start_date = context.get('second_start_date', False)
        second_end_date = context.get('second_end_date', False)
        strWhere=' 1=1'               
        if len(ids) ==1:
            strWhere=strWhere +'  AND orderproduct.id = ' + str(ids[0])
        else:
            strWhere=strWhere +'  AND orderproduct.id in ' +str(tuple(ids))
   
        sqlstr = """
            --最终查询
            select 
            partner.ref as suppliernumber,
            partner.name as suppliername,
            --销售成本
            lastweekdata.salecostprice as lastsalecostprice,
            curweekdata.salecostprice as cursalecostprice,
            lastweekdata.saleqty as lastweekdataqty,
            curweekdata.saleqty as curweekdataqty,
            lastweekdata.saleamount as lastweekdataamount,
            curweekdata.saleamount as curweekdataamount,
            --销售环比
            case curweekdata.saleamount when 0 then 0 else
               (curweekdata.saleamount-lastweekdata.saleamount)/lastweekdata.saleamount end *100 as salescomp,
            --上期毛利率
            case lastweekdata.saleamount when 0 then 0 else 
               (lastweekdata.saleamount-lastweekdata.salecostprice)/lastweekdata.saleamount end *100 as lastmargin,
            --本期毛利率
            case curweekdata.saleamount when 0 then 0 else 
               (curweekdata.saleamount-curweekdata.salecostprice)/curweekdata.saleamount end *100 as curmargin,
            --毛利环比
            case (lastweekdata.saleamount-lastweekdata.salecostprice) when 0 then 0 else
               ((curweekdata.saleamount-curweekdata.salecostprice)-(lastweekdata.saleamount-lastweekdata.salecostprice))
               /(lastweekdata.saleamount-lastweekdata.salecostprice) end *100 as margincomp
            --库存量
            --case orderproduct.is_group_product when 'f' then productinqty.invqty else
              --parentproduct.parentinvqty end as invqty,
            --库存成本
           -- case orderproduct.is_group_product when 'f' then productinqty.invqty * coalesce(producttemp.standard_price,0) else
            --   parentproduct.parentinvqty*parentproduct.parentcost end as invamount
            --保质期
            --orderproduct.use_time as usetime,
            --orderproduct.create_date as createdate
            ,orderproduct.id
            from product_product orderproduct 
            inner join product_template producttemp on orderproduct.product_tmpl_id=producttemp.id
            left join 
                (select saleorderline.product_id, 
                sum(coalesce(saleorderline.purchase_price,0)*coalesce(saleorderline.product_uom_qty,0))as salecostprice,
                sum(coalesce(saleorderline.product_uom_qty,0))as saleqty,
                sum(coalesce(saleorderline.price_unit,0)*coalesce(saleorderline.product_uom_qty,0))as saleamount
                from sale_order saleorder 
                inner join sale_order_line saleorderline on saleorder.id=saleorderline.order_id
    
                where  saleorder.state not  in('cancel')  and 
                to_char(saleorder.create_date,'YYYY-MM-DD')>=%s and  to_char(saleorder.create_date,'YYYY-MM-DD')<=%s
                
                group by saleorderline.product_id) curweekdata on orderproduct.id=curweekdata.product_id
            left join 
                (select saleorderline.product_id, 
                sum(coalesce(saleorderline.purchase_price,0)*coalesce(saleorderline.product_uom_qty,0))as salecostprice,
                sum(coalesce(saleorderline.product_uom_qty,0))as saleqty,
                sum(coalesce(saleorderline.price_unit,0)*coalesce(saleorderline.product_uom_qty,0))as saleamount
                from sale_order saleorder 
                inner join sale_order_line saleorderline on saleorder.id=saleorderline.order_id
                where  saleorder.state not  in('cancel') and 
                to_char(saleorder.create_date,'YYYY-MM-DD')>=%s and  to_char(saleorder.create_date,'YYYY-MM-DD')<=%s
                
                group by saleorderline.product_id) lastweekdata on orderproduct.id=lastweekdata.product_id
            left join product_category productcategory on producttemp.categ_id=productcategory.id
            left join product_uom puom on producttemp.uom_id=puom.id
            left join product_supplierinfo supplier on producttemp.id=supplier.product_id and supplier.sequence=1
            left join res_partner partner on supplier.name=partner.id
            left join pricelist_partnerinfo pricelistpartnerinfo on pricelistpartnerinfo.suppinfo_id=supplier.id
            where 1=1 AND  """+strWhere+""" order by orderproduct.id asc
            """
        cr.execute(sqlstr, (second_start_date,second_end_date,first_start_date,first_end_date))
        result = cr.fetchall()
        i = 0
        for one_id in sorted(ids):
            res[one_id] = {
                'okgj_comp_suppliernumber': result[i][0] and result[i][0] or '',
                'okgj_comp_suppliername' : result[i][1] and result[i][1] or '',
                'okgj_comp_lastsalecostprice' : result[i][2] and result[i][2] or 0.0,
                'okgj_comp_cursalecostprice' : result[i][3] and result[i][3] or 0.0,
                'okgj_comp_lastweekdataqty' : result[i][4] and result[i][4] or 0.0,
                'okgj_comp_curweekdataqty' : result[i][5] and result[i][5] or 0.0,
                'okgj_comp_lastweekdataamount': result[i][6] and result[i][6] or 0.0,
                'okgj_comp_curweekdataamount' : result[i][7] and result[i][7] or 0.0,
                'okgj_comp_salescomp' : result[i][8] and result[i][8] or 0.0,
                'okgj_comp_lastmargin' : result[i][9] and result[i][9] or 0.0,
                'okgj_comp_curmargin' : result[i][10] and result[i][10] or 0.0,
                'okgj_comp_margincomp': result[i][11] and result[i][11] or 0.0,
            }
            i += 1
        return res
    
    _inherit = "product.product"
    _description = "销售环比报表"
    _columns = {
        'okgj_comp_suppliernumber':fields.function(_get_comp, type='char', string=u'供应商编码', multi='get_comp'),
        'okgj_comp_suppliername':fields.function(_get_comp, type='char', string=u'供应商名称', multi='get_comp'),
        'okgj_comp_lastsalecostprice': fields.function(_get_comp, type='float', string=u'上期销售成本', multi='get_comp'),
        'okgj_comp_cursalecostprice': fields.function(_get_comp, type='float', string=u'本期销售成本', multi='get_comp'),
        'okgj_comp_lastweekdataqty': fields.function(_get_comp, type='float', string=u'上期销售数量', multi='get_comp'),
        'okgj_comp_curweekdataqty': fields.function(_get_comp, type='float', string=u'本期销售数量', multi='get_comp'),
        'okgj_comp_lastweekdataamount': fields.function(_get_comp, type='float', string=u'上期销售金额', multi='get_comp'),
        'okgj_comp_curweekdataamount': fields.function(_get_comp, type='float', string=u'本期销售金额', multi='get_comp'),
        'okgj_comp_salescomp': fields.function(_get_comp, type='float', string=u'销售环比', multi='get_comp'),
        'okgj_comp_margincomp': fields.function(_get_comp, type='float', string=u'毛利环比%', multi='get_comp'),
        'okgj_comp_lastmargin': fields.function(_get_comp, type='float', string=u'上期毛利率%', multi='get_comp'),
        'okgj_comp_curmargin': fields.function(_get_comp, type='float', string=u'本期毛利率%', multi='get_comp'),
        #'okgj_comp_invqty': fields.function(_get_comp, type='float', string=u'库存数量', multi='get_comp'),
        'okgj_comp_invamount': fields.function(_get_invamount, type='float', string=u'库存金额'),
        }
report_sales_comp()

        ## 'productnumber': fields.char(u'对应商品条码',readonly=True),
        ## 'productname': fields.char(u'对应商品名称',readonly=True),
        ## 'isgroupproduct': fields.char(u'是否组合品',readonly=True),
        ## 'uomname': fields.char(u'单位',readonly=True),
        ## 'min_qty': fields.integer(u'箱装数量',readonly=True),
        ## 'variants': fields.char(u'规格',readonly=True),
        ## 'marketprice': fields.float(u'市场价', readonly=True),
        ## 'purchaseprice': fields.float(u'进价', readonly=True),
        ## 'okprice': fields.float(u'OK价', readonly=True),
        ## 'okgjcostprice': fields.float(u'成本价', readonly=True),
        ## 'productcaterotyname': fields.char(u'分类', readonly=True),
        ## 'usetime': fields.integer(u'保质期',readonly=True),
        ## 'createdate': fields.date(u'商品创建时间',readonly=True),
        ## 'suppliernumber': fields.char(u'供应商编码',readonly=True),
        ## 'suppliername': fields.char(u'供应商名称',readonly=True),
        ## 'lastsalecostprice': fields.float(u'上期销售成本', readonly=True),
        ## 'cursalecostprice': fields.float(u'本期销售成本', readonly=True),
        ## 'lastweekdataqty': fields.float(u'上期销售数量', readonly=True),
        ## 'curweekdataqty': fields.float(u'本期销售数量', readonly=True),
        ## 'lastweekdataamount': fields.float(u'上期销售金额', readonly=True),
        ## 'curweekdataamount': fields.float(u'本期销售金额', readonly=True),
        ## 'salescomp': fields.float(u'销售环比%', readonly=True),
        ## 'margincomp': fields.float(u'毛利环比%', readonly=True),
        ## 'lastmargin': fields.float(u'上期毛利率%', readonly=True),
        ## 'curmargin': fields.float(u'本期毛利率%', readonly=True),
        ## 'invqty': fields.float(u'库存数量', readonly=True),
        ## 'invamount': fields.float(u'库存金额', readonly=True),


    ## def init(self, cr):
    ##     #tools.drop_view_if_exists(cr, 'report_sales_comp')
    ##     #总的结果查询
    ##     cr.execute("""
    ##     CREATE or replace VIEW report_sales_comp AS (      
    ##     select 
    ##         id as id,
    ##         productcaterotyname as productcaterotyname,
    ##         suppliernumber as suppliernumber,suppliername as suppliername,
    ##         productnumber as productnumber,productname as productname,
    ##         isgroupproduct as isgroupproduct,
    ##         uomname as uomname,
    ##         min_qty as min_qty,variants as variants,
    ##         marketprice as marketprice,
    ##         purchaseprice as purchaseprice,
    ##        okprice as okprice, 
    ##         okgjcostprice as okgjcostprice,
    ##         --销售成本
    ##          lastsalecostprice as lastsalecostprice,cursalecostprice as cursalecostprice,
    ##         lastweekdataqty as lastweekdataqty,curweekdataqty as curweekdataqty,
    ##         lastweekdataamount as lastweekdataamount,curweekdataamount as curweekdataamount,

    ##         --销售环比
    ##         salescomp as salescomp,
    ##         --上期毛利率
    ##         lastmargin as lastmargin,
    ##         --本期毛利率
    ##         curmargin as curmargin,
    ##         --毛利环比
    ##        margincomp as margincomp,
    ##         --库存量
    ##         invqty as invqty,
    ##         --库存成本
    ##         invamount as invamount,
    ##         --保质期
    ##         usetime as usetime,
    ##         createdate as createdate
            
        
    ##        from report_sales_comp_data
    ##     )
    ##     """
    ## )
    
    
##     def init(self, cr):
##                 tools.drop_view_if_exists(cr, 'report_sales_comp')
 
##                 #总的结果查询
               
##                 cr.execute(""" 
##                     CREATE or replace VIEW report_sales_comp AS (      
##   --最终查询
## select 
## orderproduct.id as id,
## substring(getparentcategory(productcategory.id),2,char_length(getparentcategory(productcategory.id))-1) as productcaterotyname,
## partner.ref as suppliernumber,partner.name as suppliername,
## orderproduct.default_code as productnumber,orderproduct.name_template as productname,
## case orderproduct.is_group_product when 't' then '是' else '否' end as isgroupproduct,
## puom.name as uomname,
## orderproduct.min_qty as min_qty,orderproduct.variants as variants,
## orderproduct.other_price as marketprice,pricelistpartnerinfo.price as purchaseprice,
## producttemp.list_price as okprice, 
## case orderproduct.is_group_product when 'f' then producttemp.standard_price else
## parentproduct.parentcost end as okgjcostprice,
## --销售成本
## lastweekdata.salecostprice as lastsalecostprice,curweekdata.salecostprice as cursalecostprice,
## lastweekdata.saleqty as lastweekdataqty,curweekdata.saleqty as curweekdataqty,
## lastweekdata.saleamount as lastweekdataamount,curweekdata.saleamount as curweekdataamount,
## --销售环比
## case curweekdata.saleamount when 0 then 0 else
## (curweekdata.saleamount-lastweekdata.saleamount)/lastweekdata.saleamount end *100 as salescomp,
## --上期毛利率
## case lastweekdata.saleamount when 0 then 0 else 
## (lastweekdata.saleamount-lastweekdata.salecostprice)/lastweekdata.saleamount end *100 as lastmargin,
## --本期毛利率
## case curweekdata.saleamount when 0 then 0 else 
## (curweekdata.saleamount-curweekdata.salecostprice)/curweekdata.saleamount end *100 as curmargin,
## --毛利环比
## case (lastweekdata.saleamount-lastweekdata.salecostprice) when 0 then 0 else
## ((curweekdata.saleamount-curweekdata.salecostprice)-(lastweekdata.saleamount-lastweekdata.salecostprice))
## /(lastweekdata.saleamount-lastweekdata.salecostprice) end *100 as margincomp,
## --库存量
## case orderproduct.is_group_product when 'f' then productinqty.invqty else
## parentproduct.parentinvqty end as invqty,
## --库存成本
## case orderproduct.is_group_product when 'f' then productinqty.invqty * coalesce(producttemp.standard_price,0) else
## parentproduct.parentinvqty*parentproduct.parentcost end as invamount,
## --保质期
## orderproduct.use_time as usetime,
## orderproduct.create_date as createdate

## from product_product orderproduct 
## inner join product_template producttemp on orderproduct.product_tmpl_id=producttemp.id
## left join 
##     (select saleorderline.product_id, 
##     sum(coalesce(saleorderline.purchase_price,0)*coalesce(saleorderline.product_uom_qty,0))as salecostprice,
##     sum(coalesce(saleorderline.product_uom_qty,0))as saleqty,
##     sum(coalesce(saleorderline.price_unit,0)*coalesce(saleorderline.product_uom_qty,0))as saleamount
##     from sale_order saleorder 
##     inner join sale_order_line saleorderline on saleorder.id=saleorderline.order_id
##     --where
##     group by saleorderline.product_id) curweekdata on orderproduct.id=curweekdata.product_id
## left join 
##     (select saleorderline.product_id, 
##     sum(coalesce(saleorderline.purchase_price,0)*coalesce(saleorderline.product_uom_qty,0))as salecostprice,
##     sum(coalesce(saleorderline.product_uom_qty,0))as saleqty,
##     sum(coalesce(saleorderline.price_unit,0)*coalesce(saleorderline.product_uom_qty,0))as saleamount
##     from sale_order saleorder 
##     inner join sale_order_line saleorderline on saleorder.id=saleorderline.order_id
##     --where
##     group by saleorderline.product_id) lastweekdata on orderproduct.id=lastweekdata.product_id
## left join product_category productcategory on producttemp.categ_id=productcategory.id
## left join product_uom puom on producttemp.uom_id=puom.id
## left join product_supplierinfo supplier on producttemp.id=supplier.product_id
## left join res_partner partner on supplier.name=partner.id
## left join pricelist_partnerinfo pricelistpartnerinfo on pricelistpartnerinfo.suppinfo_id=partner.id
## left join 
##     (select product.id,(coalesce(tempinqty.inqty,0)-coalesce(tempoutqty.outqty,0)) as invqty 
##     from 
##         (select  product.id,producttemp.uom_id,puom.factor 
##         from 
##         product_product product
##         inner join product_template producttemp on product.product_tmpl_id=producttemp.id
##         left join product_uom puom on producttemp.uom_id=puom.id) product
##     left join (--获取入库数量
##         select product_id,sum(inqty) as inqty from 
##             (select 
##                 stockmove.product_id,stockmove.product_uom,
##                 (sum(coalesce(stockmove.product_qty,0))/coalesce(stockpuom.factor,0))*puom.factor as inqty
##                 from stock_move stockmove
##             left join 
##                 (select  product1.id,producttemp1.uom_id,puom1.factor 
##                 from 
##                 product_product product1
##                 inner join product_template producttemp1 on product1.product_tmpl_id=producttemp1.id
##                 left join product_uom puom1 on producttemp1.uom_id=puom1.id) puom 
##                 on stockmove.product_id=puom.id
##             left join product_uom stockpuom on stockpuom.id=stockmove.product_uom 
##             where stockmove.location_id not in(12)
##             and stockmove.location_dest_id  in(12)
##             and stockmove.state in ('done')
##             group by stockmove.product_id,stockmove.product_uom,stockpuom.factor,puom.factor) temp_totalinqty 
##         group by product_id) tempinqty 
##     on product.id=tempinqty.product_id
##     left join (--出库
##         select product_id,sum(outqty) as outqty from 
##             (select stockmove.product_id,stockmove.product_uom,
##                 (sum(coalesce(stockmove.product_qty,0))/coalesce(stockpuom.factor,0))*puom.factor as outqty
##                 from stock_move stockmove
##                 left join 
##                     (select  productout.id,producttempout.uom_id,puomout.factor 
##                     from 
##                     product_product productout
##                     inner join product_template producttempout on productout.product_tmpl_id=producttempout.id
##                     left join product_uom puomout on producttempout.uom_id=puomout.id) puom on stockmove.product_id=puom.id
##                 left join product_uom stockpuom on stockpuom.id=stockmove.product_uom 
##                 where 
##                 stockmove.location_id in(12)
##                 and stockmove.location_dest_id not in(12)
##                 and stockmove.state in ('done')
##             --and stockmove.product_id=5981
##                 group by stockmove.product_id,stockmove.product_uom,stockpuom.factor,puom.factor)temp_outqty 
##             group by product_id) tempoutqty 
##     on product.id=tempoutqty.product_id) productinqty on orderproduct.id=productinqty.id

## left join (select parentbom.product_id,
## min(coalesce(tempinvqty.invqty ,0)/coalesce(childbom.product_qty,0))as parentinvqty,--end
## sum(coalesce(childproducttemp.standard_price,0)*coalesce(childbom.product_qty,0)) as parentcost
## from mrp_bom childbom 
## left join mrp_bom parentbom on childbom.bom_id=parentbom.id 
## left join (--即时库存量
## select product.id,(coalesce(tempinqty.inqty,0)-coalesce(tempoutqty.outqty,0)) as invqty 
## from (select  product.id,producttemp.uom_id,puom.factor 
## from 
## product_product product
## inner join product_template producttemp on product.product_tmpl_id=producttemp.id
## left join product_uom puom on producttemp.uom_id=puom.id) product
##     left join (--获取入库数量
##         select product_id,sum(inqty) as inqty from 
##             (select 
##                 stockmove.product_id,stockmove.product_uom,
##                 (sum(coalesce(stockmove.product_qty,0))/coalesce(stockpuom.factor,0))*puom.factor as inqty
##                 from stock_move stockmove
##             left join 
##                 (select  product1.id,producttemp1.uom_id,puom1.factor 
##                 from 
##                 product_product product1
##                 inner join product_template producttemp1 on product1.product_tmpl_id=producttemp1.id
##                 left join product_uom puom1 on producttemp1.uom_id=puom1.id) puom 
##                 on stockmove.product_id=puom.id
##             left join product_uom stockpuom on stockpuom.id=stockmove.product_uom 
##             where stockmove.location_id not in(12)
##             and stockmove.location_dest_id  in(12)
##             and stockmove.state in ('done')
##             group by stockmove.product_id,stockmove.product_uom,stockpuom.factor,puom.factor) temp_totalinqty 
##         group by product_id) tempinqty 
## on product.id=tempinqty.product_id
## left join 
##     (--出库
##         select product_id,sum(outqty) as outqty from 
##             (select stockmove.product_id,stockmove.product_uom,
##                 (sum(coalesce(stockmove.product_qty,0))/coalesce(stockpuom.factor,0))*coalesce(puom.factor,0) as outqty
##                 from stock_move stockmove
##                 left join 
##                     (select  productout.id,producttempout.uom_id,puomout.factor 
##                     from 
##                     product_product productout
##                     inner join product_template producttempout on productout.product_tmpl_id=producttempout.id
##                     left join product_uom puomout on producttempout.uom_id=puomout.id) puom on stockmove.product_id=puom.id
##                 left join product_uom stockpuom on stockpuom.id=stockmove.product_uom 
##                 where 
##                 stockmove.location_id in(12)
##                 and stockmove.location_dest_id not in(12)
##                 and stockmove.state in ('done')
##             --and stockmove.product_id=5981
##                 group by stockmove.product_id,stockmove.product_uom,stockpuom.factor,puom.factor)temp_outqty 
##             group by product_id) tempoutqty 
## on product.id=tempoutqty.product_id) tempinvqty on childbom.product_id=tempinvqty.id
## left join product_product productdata on productdata.id=parentbom.product_id
## left join product_product childproduct on childbom.product_id=childproduct.id
## inner join product_template childproducttemp on childproduct.product_tmpl_id=childproducttemp.id
## where childbom.type='normal' 
## group by parentbom.product_id) parentproduct on orderproduct.id=parentproduct.product_id
## --where orderproduct.productid=

##   )
##      """)
