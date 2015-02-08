# -*- coding: utf-8 -*-

##############################################################################
from openerp import tools
from osv import fields, osv
import openerp.addons.decimal_precision as dp
import re
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

#仓库，商品分类，品牌，条码，品名
class okgj_report_adventinv_wizard(osv.osv_memory):
    _name = "okgj.report.adventinv.wizard"
    _columns = {
        'logiscenter_id':fields.many2one('stock.warehouse', u'物流中心',required=True),
        'warehouse_id':fields.many2one('stock.location', u'仓库',required=True, domain=[('usage','=','internal')]),
        'category_id':fields.many2one('product.category', u'类别'),
        'brand_id':fields.many2one('okgj.product.brand', u'品牌'),
        'product_id':fields.many2one('product.product', u'商品'),
        'adventdays':fields.integer( u'临期天数'),
        'has_zero':fields.boolean(u'显示零库存'),
    }

    def _default_warehouse_id(self, cr, uid, context=None):
        user_data = self.pool.get('res.users').browse(cr,uid, uid, context=context)
        warehouse_id = False
        for one_warehouse in user_data.warehouse_ids:
            warehouse_id = one_warehouse.id
            if warehouse_id:
		    break
        return warehouse_id

    def _default_location_id(self,cr,uid,context=None):
	user_data = self.pool.get('res.users').browse(cr,uid, uid, context=context)
        warehouse_id = False
        location_id = False
        for one_warehouse in user_data.warehouse_ids:
            location_id = one_warehouse.lot_stock_id.id
	    if location_id:
		    break
   	return location_id

    _defaults = {
        'logiscenter_id': _default_warehouse_id,
	'warehouse_id': _default_location_id,
    }
    
    def onchangelocation_id(self,cr,uid,ids,logiscenter_id=False,context=None):
	if(not logiscenter_id):
		return {}
        warehouse_id = self.pool.get('stock.warehouse').browse(cr, uid, logiscenter_id, context=context).lot_stock_id.id
	return {'value':{'warehouse_id':warehouse_id}}
    
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
        product_ids = self.pool.get('product.product').search(cr, uid, [('categ_id', 'in', child_ids)], context=context)
        return product_ids
    
    def _get_brand_products(self, cr, uid, brand_id, context=None):
        """
        @param cate_id: product category id
        @return: the lowest category id
        """
        product_ids = self.pool.get('product.product').search(cr, uid, [('brand_id', '=', brand_id)], context=context)
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
            search_domain.append(('product_id', 'in', self._get_final_categ_products(cr, uid, data.category_id.id)))
        if data.brand_id:
            search_domain.append(('product_id', 'in', self._get_brand_products(cr, uid, data.brand_id.id)))
        if data.product_id:
            search_domain.append(('product_id', '=', data.product_id.id))
        if not data.has_zero:
            ## search_domain.append(('|'))
            search_domain.append(('stock_available', '>', 0))
            ## search_domain.append(('stock_available', '<', 0.00000000000))
        if data.logiscenter_id:
            context.update({'warehouse_id':data.logiscenter_id.id})
        if data.warehouse_id:
            context.update({'location_id':data.warehouse_id.id})
        if data.adventdays:
            context.update({'adventdays':data.adventdays or False})
            adventday_str = (datetime.now() + relativedelta(days=data.adventdays)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            search_domain.append(('use_date', '<', adventday_str))
        domain_ids = self.pool.get('stock.production.lot').search(cr, uid, search_domain, context=context)
        domain = [('id', 'in', domain_ids)]
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'okgj', 'view_okgj_report_adventinv_tree')
        view_id = view_ref and view_ref[1] or False,
        return {
            'name': _('临期商品统计表'),
            'context': context,
            'view_type': 'form',
            "view_mode": 'tree',
            'res_model':'stock.production.lot',
            'type': 'ir.actions.act_window',
            'view_id': view_id,
            'domain' : domain,
        }
okgj_report_adventinv_wizard()

class okgj_report_adventinv(osv.osv):

    def _get_pick_rack(self, cr, uid, ids, field_names, arg, context=None):
        """ Read the 'rack' functional fields. """
        res = {}
        warehouse_id = context.get('warehouse_id', False)
        product_obj = self.pool.get('product.product')
        for one_record in self.browse(cr, uid, ids, context=context):
            pick_rack_data = product_obj.browse(cr, uid, one_record.product_id, context=context).product_pick_rack_ids
            has_rack = False
            if pick_rack_data is None: pick_rack_data = []
            for one_rack in pick_rack_data:
                if one_rack.warehouse_id.id == warehouse_id:
                    has_rack = True
                    res[one_record.id] = one_rack.id
                    break
            if not has_rack:
                res[one_record.id] = False
        return res

    def _get_store_rack(self, cr, uid, ids, field_names, arg, context=None):
        """ Read the 'rack' functional fields. """
        res ={} 
        warehouse_id = context.get('warehouse_id', False)
        product_obj = self.pool.get('product.product')
        for one_record in self.browse(cr, uid, ids, context=context):
            store_rack_data = product_obj.browse(cr, uid, one_record.product_id, context=context).product_store_rack_ids
            has_rack = False
            if store_rack_data is None: store_rack_data = []
            for one_rack in store_rack_data:
                if one_rack.warehouse_id.id == warehouse_id:
                    has_rack = True
                    res[one_record.id] = one_rack.id
                    break
            if not has_rack:
                res[one_record.id] = False
        return res

    def _get_adventinv(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        if context is None:
            context = {}
        warehouse_id = context.get('location_id', False)
        adventdays = context.get('adventdays', False)
        strWhere=' 1=1'               
        if  adventdays != 0:
           strWhere=strWhere + ' AND  extract(day from stockprodlot.use_date-current_date)<='+str(adventdays)+''
        if len(ids) ==1:
            strWhere=strWhere +'  AND stockprodlot.id = ' + str(ids[0])
        else:
            strWhere=strWhere +'  AND stockprodlot.id in ' +str(tuple(ids))
        sqlstr = """ 
            --最终查询
            select 
            --stockprodlot.id,
            coalesce(okgjlocation.complete_name,'') as stockname,
            extract(day from stockprodlot.use_date-current_date) as adventday,
            coalesce(productinqty.invqty,0) as invqty
            
            from product_product orderproduct 
            left join 
		(
     		select temgroupinqty.id,temgroupinqty.location_id,temgroupinqty.lotid,(coalesce(temgroupinqty.inqty,0)-coalesce(temgroupoutqty.outqty,0))invqty
		from product_product orderproducts 
		left join stock_production_lot stockprodlot on orderproducts.id=stockprodlot.product_id
		left join ( 
			select product.id,tempinqty.location_id,tempinqty.lotid,
			sum(coalesce(tempinqty.inqty,0))inqty
			from product_product product
			left join
				(--获取入库数量
				select product_id,location_id,lotid,sum(inqty) as inqty from 
			    		(select 
					stockmove.product_id,stockmove.location_dest_id as location_id,stocklot.id as lotid,stockmove.product_uom,
					(sum(coalesce(stockmove.product_qty,0))/coalesce(stockpuom.factor,0))*puom.factor as inqty
					from stock_move stockmove
					left join 
						(select  product1.id,producttemp1.uom_id,puom1.factor 
							from 
							product_product product1
							inner join product_template producttemp1 on product1.product_tmpl_id=producttemp1.id
							left join product_uom puom1 on producttemp1.uom_id=puom1.id) puom 
							on stockmove.product_id=puom.id
					left join stock_production_lot stocklot on stockmove.prodlot_id=stocklot.id --and stockmove.product_id=stocklot.product_id
				
					left join product_uom stockpuom on stockpuom.id=stockmove.product_uom 
				    	where stockmove.location_id not in("""+str(warehouse_id)+""")
				    and stockmove.location_dest_id  in("""+str(warehouse_id)+""")
				    and stockmove.state in ('done')
				    group by stockmove.product_id,stockmove.location_dest_id,stocklot.id,
				    stockmove.product_uom,stockpuom.factor,puom.factor) temp_totalinqty 
			group by product_id,location_id,lotid) tempinqty 
			on product.id=tempinqty.product_id
			group by product.id,tempinqty.location_id,tempinqty.lotid) temgroupinqty
			on orderproducts.id=temgroupinqty.id and stockprodlot.id=temgroupinqty.lotid
		left join
			(select product.id,tempoutqty.location_id,tempoutqty.lotid,
			sum(coalesce(tempoutqty.outqty,0))outqty
			  from product_product product
					left join (--出库
				select product_id,location_id,lotid,sum(outqty) as outqty from 
				    (select stockmove.product_id,stockmove.location_id as location_id ,stocklot.id as lotid,stockmove.product_uom,
					(sum(coalesce(stockmove.product_qty,0))/coalesce(stockpuom.factor,0))*puom.factor as outqty
					from stock_move stockmove
					left join 
					    (select  productout.id,producttempout.uom_id,puomout.factor 
					    from 
					    product_product productout
					    inner join product_template producttempout on productout.product_tmpl_id=producttempout.id
					    left join product_uom puomout on producttempout.uom_id=puomout.id) puom on stockmove.product_id=puom.id

					left join stock_production_lot stocklot on stockmove.prodlot_id=stocklot.id --and stockmove.product_id=stocklot.product_id
					
					left join product_uom stockpuom on stockpuom.id=stockmove.product_uom 
					where 
					stockmove.location_id in("""+str(warehouse_id)+""")
					and stockmove.location_dest_id not in("""+str(warehouse_id)+""")
					and stockmove.state in ('done')
					group by stockmove.product_id,stockmove.location_id,stocklot.id,stockmove.product_uom,stockpuom.factor,puom.factor)temp_outqty 
					group by product_id,location_id,lotid) tempoutqty 
					on product.id=tempoutqty.product_id group by product.id,tempoutqty.location_id,tempoutqty.lotid) temgroupoutqty 
				on orderproducts.id=temgroupoutqty.id and stockprodlot.id=temgroupoutqty.lotid 
			) productinqty 
		on orderproduct.id=productinqty.id                
            left join stock_location okgjlocation on productinqty.location_id=okgjlocation.id
            right join stock_production_lot stockprodlot on stockprodlot.id=productinqty.lotid and orderproduct.id=stockprodlot.product_id
            where 1=1 AND  """+strWhere+"""  order by stockprodlot.id asc       
       
        """
        cr.execute(sqlstr)
        result = cr.fetchall()
        i = 0
        for one_id in sorted(ids):
            res[one_id] = {
                'okgj_comp_stock_name': result[i] and result[i][0] or '',
                'okgj_comp_adventday' : result[i] and result[i][1] or 0,
                'okgj_comp_invqty' : result[i] and result[i][2] or 0,
            }
            i += 1
        return res

    _inherit = "stock.production.lot"
    _description = "临期商品统计表"
    _columns = {
        'caterotyname': fields.related('product_id', 'categ_id', type='many2one', relation='product.category', string=u'分类', store=True, readonly=True),
        'productnumber': fields.related('product_id', 'default_code', type='char', string=u'对应商品条码', store=True, readonly=True),
        'variants': fields.related('product_id', 'variants', type='char', string=u'规格', store=True, readonly=True),
        'brandname': fields.related('product_id', 'brand_id', type='many2one', relation='okgj.product.brand', string=u'品牌', store=True, readonly=True),
        'pickrack': fields.function(_get_pick_rack, type='many2one', relation='okgj.product.rack', string=u'拣货货位'),
        'storerack': fields.function(_get_store_rack, type='many2one', relation='okgj.product.rack', string=u'存货货位'),
        'okgj_comp_stock_name':fields.function(_get_adventinv, type='char', string=u'仓库', multi='get_adventinv'),
        #'okgj_comp_stock_name':fields.text(u'仓库'),
        'okgj_comp_adventday':fields.function(_get_adventinv, type='integer', string=u'临期天数', multi='get_adventinv'),
        'okgj_comp_invqty':fields.function(_get_adventinv, type='integer', string=u'库存数量', multi='get_adventinv'),
        }
okgj_report_adventinv()


## 'stockname': fields.char(u'仓库',readonly=True),
## 'adventday': fields.float(u'临期天数',readonly=True),
## 'invqty': fields.float(u'库存数量', readonly=True),

    ## def init(self, cr):
    ##     #tools.drop_view_if_exists(cr, 'report_sales_comp')
    ##     #总的结果查询
    ##     cr.execute("""
    ##     CREATE or replace VIEW okgj_report_adventinv AS (      
    ##     select 
    ##         id as id,
    ##         productid as productid,
    ##         productnumber as productnumber,
    ##         productname as productname,
    ##         variants as variants,
    ##         productcaterotyname as productcaterotyname,    
    ##         brandname as brandname,
    ##        -- pickrack as pickrack,
    ##        -- storerack as storerack,
    ##         stockname as stockname,
    ##         prodlot as prodlot,
    ##         adventday as adventday,
    ##         invqty as invqty
            
        
    ##        from okgj_report_adventinv_data
    ##     )
    ##     """
    ## )
            
        
       ## cr.execute(""" select *  into okgj_report_adventinv_data_table from  okgj_report_adventinv_data""")

