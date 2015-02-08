# -*- coding: utf-8 -*-
##############################################################################

from openerp import tools
from osv import fields, osv
import openerp.addons.decimal_precision as dp
import re
from openerp.tools.translate import _

#仓库，商品分类，品牌，条码，品名

class okgj_report_jitinventory_wizard(osv.osv_memory):
    _name = "okgj.report.jitinventory.wizard"
    _columns = {
        'logiscenter_id':fields.many2one('stock.warehouse', u'物流中心',required=True),
	'warehouse_id':fields.many2one('stock.location', u'仓库',required=True, domain=[('usage','=','internal')]),
        'category_id':fields.many2one('product.category', u'类别'),
        #'supplier_id':fields.many2one('res.partner', u'供应商'),
        'brand_id':fields.many2one('okgj.product.brand', u'品牌'),
        'product_id':fields.many2one('product.product', u'商品'),
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
        report_data = self.browse(cr, uid, ids[0], context=context)
	
	search_domain = []

	if report_data.category_id:
	    search_domain.append(('categ_id','in',self._get_final_categ(cr,uid,report_data.category_id.id)))
	if report_data.brand_id:
	    search_domain.append(('brand_id','=',report_data.brand_id.id))
	if report_data.product_id:
	    search_domain.append(('id','=',report_data.product_id.id))
	domain_ids=self.pool.get('product.product').search(cr,uid,search_domain)
	domain=[('id','in',domain_ids)]

	if report_data.logiscenter_id:
	    context.update({'logiscenter_id':report_data.logiscenter_id.id})
        if report_data.warehouse_id:
	    context.update({'warehouse_id':report_data.warehouse_id.id})
        
	view_ref = self.pool.get('ir.model.data').get_object_reference(cr,uid,'okgj','view_okgj_report_jitinventory_tree')
	view_id = view_ref and view_ref[1] or False

	return {
            'name': _('即时库存'),
            'context': context,
            'view_type': 'form',
            "view_mode": 'tree',
            'res_model':'product.product',
            'type': 'ir.actions.act_window',
            'view_id': view_id,
            'domain':domain,
        }
okgj_report_jitinventory_wizard()

class okgj_report_jitinventory(osv.osv):

    def _get_pick_rack(self, cr, uid, ids, field_names, arg, context=None):
        """ Read the 'rack' functional fields. """
        res = {}
        warehouse_id = context.get('warehouse_id', False)
        product_obj = self.pool.get('product.product')
        for one_record in ids:
            pick_rack_data = product_obj.browse(cr, uid, one_record, context=context).product_pick_rack_ids
            has_rack = False
            for one_rack in pick_rack_data:
                if one_rack.warehouse_id.id == warehouse_id:
                    has_rack = True
                    res[one_record] = one_rack.id
                    break
            if not has_rack:
                res[one_record] = False
        return res

    def _get_store_rack(self, cr, uid, ids, field_names, arg, context=None):
	""" Read the 'rack' functional fields. """
	res ={}
	warehouse_id = context.get('warehouse_id', False)
	product_obj = self.pool.get('product.product')
	for one_record in ids:
	    store_rack_data = product_obj.browse(cr, uid, one_record, context=context).product_store_rack_ids
	    has_rack = False
	    for one_rack in store_rack_data:
		if one_rack.warehouse_id.id == warehouse_id:
		    has_rack = True
		    res[one_record] = one_rack.id
		    break
	    if not has_rack:
		res[one_record] = False
	return res

    def _get_jitdata(self, cr, uid, ids, field_names, arg, context=None):
	res = {}
		
	if context is None:
		context = {}
	
	logiscenter_id=context.get('logiscenter_id',False)
	warehouse_id=context.get('warehouse_id',False)

        strWhere=' 1=1'               
        if logiscenter_id !=0:
           context.update({'warehouse_id':logiscenter_id})
       
        if len(ids) == 1:
            strWhere=strWhere +'  AND orderproduct.id = ' +  str(ids[0])
        else:
            strWhere=strWhere +'  AND orderproduct.id in ' + str(tuple(ids))

    
        sqlstr=""" 
            --最终查询
            select
            okgjlocation.complete_name as stockname,
            productinqty.invqty as invqty
            
            from product_product orderproduct 
            left join 
                (select temgroupinqty.id,temgroupinqty.location_id,(coalesce(temgroupinqty.inqty,0)-coalesce(temgroupoutqty.outqty,0))invqty from( 
					select product.id,tempinqty.location_id,
					sum(coalesce(tempinqty.inqty,0))inqty
					from product_product product
					left join
						(--获取入库数量
						select product_id,location_id,sum(inqty) as inqty from 
							(select 
							stockmove.product_id,stockmove.location_dest_id as location_id,stockmove.product_uom,
							(sum(coalesce(stockmove.product_qty,0))/coalesce(stockpuom.factor,0))*puom.factor as inqty
							from stock_move stockmove
							left join 
								(select  product1.id,producttemp1.uom_id,puom1.factor 
									from 
									product_product product1
									inner join product_template producttemp1 on product1.product_tmpl_id=producttemp1.id
									left join product_uom puom1 on producttemp1.uom_id=puom1.id) puom 
									on stockmove.product_id=puom.id
							
							left join product_uom stockpuom on stockpuom.id=stockmove.product_uom 
								where stockmove.location_id not in("""+str(warehouse_id)+""")
								and stockmove.location_dest_id  in("""+str(warehouse_id)+""")
								and stockmove.state in ('done')
								group by stockmove.product_id,stockmove.location_dest_id,
								stockmove.product_uom,stockpuom.factor,puom.factor) temp_totalinqty 
						group by product_id,location_id) tempinqty 
						on product.id=tempinqty.product_id
					group by product.id,tempinqty.location_id) temgroupinqty
			left join
					(select product.id,tempoutqty.location_id,
					sum(coalesce(tempoutqty.outqty,0))outqty
					  from product_product product
							left join (--出库
						select product_id,location_id,sum(outqty) as outqty from 
							(select stockmove.product_id,stockmove.location_id as location_id ,stockmove.product_uom,
							(sum(coalesce(stockmove.product_qty,0))/coalesce(stockpuom.factor,0))*puom.factor as outqty
							from stock_move stockmove
							left join 
								(select  productout.id,producttempout.uom_id,puomout.factor 
								from 
								product_product productout
								inner join product_template producttempout on productout.product_tmpl_id=producttempout.id
								left join product_uom puomout on producttempout.uom_id=puomout.id) puom on stockmove.product_id=puom.id
				
							
							left join product_uom stockpuom on stockpuom.id=stockmove.product_uom 
							where 
							stockmove.location_id in("""+str(warehouse_id)+""")
							and stockmove.location_dest_id not in("""+str(warehouse_id)+""")
							and stockmove.state in ('done')
							group by stockmove.product_id,stockmove.location_id,stockmove.product_uom,stockpuom.factor,puom.factor)temp_outqty 
							group by product_id,location_id) tempoutqty 
							on product.id=tempoutqty.product_id 
							group by product.id,tempoutqty.location_id) temgroupoutqty 
								on temgroupinqty.id=temgroupoutqty.id and temgroupinqty.location_id=temgroupoutqty.location_id 
						) productinqty 
                on orderproduct.id=productinqty.id
            left join stock_location okgjlocation on productinqty.location_id=okgjlocation.id

            where 1=1 AND  """+strWhere+"""         
        """

	cr.execute(sqlstr)
        result = cr.fetchall()
        i = 0
        for one_id in sorted(ids):
            res[one_id] = {
                'stockname' : result[i][0] and result[i][0] or '',
                'invqty' : result[i][1] and result[i][1] or 0.0,
            }
            i += 1
        return res

    _inherit = "product.product"
    _description = "即时库存报表"
    _columns = {
        ##'productcaterotyname': fields.char(u'分类', readonly=True),
        ##'productnumber': fields.char(u'对应商品条码',readonly=True),
        ##'productname': fields.char(u'对应商品名称',readonly=True),
        ##'variants': fields.char(u'规格',readonly=True),
        ##'brandname': fields.char(u'品牌',readonly=True),
        'pickrack': fields.function(_get_pick_rack, type='many2one', relation='okgj.product.rack', string=u'拣货货位'),
        'storerack': fields.function(_get_store_rack, type='many2one', relation='okgj.product.rack', string=u'存货货位'),
        'stockname': fields.function(_get_jitdata,type='char',string=u'仓库',multi='get_jitdata'),##.char(u'仓库',readonly=True),
        'invqty': fields.function(_get_jitdata,type='char',string=u'库存数量',multi='get_jitdata'),##float(u'库存数量', readonly=True),
        }
okgj_report_jitinventory()
