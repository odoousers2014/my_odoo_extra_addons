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
from openerp.tools.float_utils import float_compare

class okgj_mobilesign(osv.osv_memory):
    _name = "okgj.mobilesign"
    _columns = {
        'okgj_sign_carNo':fields.char(u'装车单号'),
        'okgj_sign_driver':fields.char(u'司机编号'),
        'okgj_sign_billcount':fields.integer(u'单数'),
        'okgj_sign_delivedcount':fields.integer(u'已送达'),
        'okgj_sign_undelivedcount':fields.integer(u'未送达'),
        'okgj_sign_pendingcount':fields.integer(u'待处理'),
    }
    def do_carsearch(self, cr, uid, filters, context=None):
        if context is None:
            context = {}
        data = {}
       
        okgjfilter=''.join(filters[0])
        strwhere="where 1=1 and "
        strwhere=strwhere+okgjfilter

        sqlstr="""
            select COALESCE(carinfo.name,'') as name,
            carinfo.okgj_sign_driver,COALESCE(carinfo.carcount,0) as billcount,COALESCE(billdone.carcount,0) as billdonecount,
            COALESCE(billcancel.carcount,0) as billcancelcount,COALESCE(billtodo.carcount,0) as billtodocount,carinfo.id as car_id,carinfo.state from (
            select v2.id,v2.name,v3.driver_phone as okgj_sign_driver,
            count(COALESCE(sale_order_id,0))carcount,v2.state from okgj_logistics_line v1
            left join okgj_logistics v2 on v1.logistics_id=v2.id
            left join okgj_logistics_car v3 on v2.car_id=v3.id
            where v2.state in('start')
            group by v2.id,v2.name,v3.driver_phone
                )carinfo
                left join(
            select v1.state,v2.name,
            count(COALESCE(sale_order_id,0))carcount from okgj_logistics_line v1
            left join okgj_logistics v2 on v1.logistics_id=v2.id
            where v1.state='done'
            group by v2.name,v1.state
                )billdone on carinfo.name=billdone.name
                left join(
            select v1.state,v2.name,
            count(COALESCE(sale_order_id,0))carcount from okgj_logistics_line v1
            left join okgj_logistics v2 on v1.logistics_id=v2.id
            where v1.state='cancel'
            group by v2.name,v1.state
                )billcancel on carinfo.name=billcancel.name
                left join(
            select v1.state,v2.name,
            count(COALESCE(sale_order_id,0))carcount from okgj_logistics_line v1
            left join okgj_logistics v2 on v1.logistics_id=v2.id
            where v1.state='todo'
            group by v2.name,v1.state
                )billtodo on carinfo.name=billtodo.name
            """+strwhere+"""
        """
        #import sys
        #sys.stdout=open('/home/ouke/yangyang/OKYUN/OKYUN/test.txt','a')
        #print sqlstr
        #sys.stdout.close()
        #sys.stdout = sys.__stdout__
        
        cr.execute(sqlstr)
        results = cr.fetchall()

        return results
    
    def do_cardetailsearch(self, cr, uid, filters, context=None):
        if context is None:
            context = {}
        data = {}
       
        okgjfilter=''.join(filters[0])
        strwhere="where 1=1 and "
        strwhere=strwhere+okgjfilter

        sqlstr="""
            select v1.logistics_id, COALESCE(v3.name,'') as name, COALESCE(v2.name,'') as okgj_orderno,
            case pickout.name is null when true then  COALESCE(salereturn.name,'') else  COALESCE(pickout.name,'') end as okgj_saleourno,
             COALESCE(v1.sale_consignee,'') as sale_consignee, COALESCE(v1.sale_okgj_tel,'') as sale_okgj_tel,
             COALESCE(v1.sale_region_name||v1.sale_okgj_address,'') as okgj_address,
             COALESCE(pickout.okgj_box,'') as okgj_box,
            case v1.state when 'todo' then '待送达' when 'done' then '已送达' when 'cancel' then '未送达' end as state,v1.id
            from okgj_logistics_line v1
            left join  okgj_logistics v3 on v1.logistics_id=v3.id
            left join sale_order v2 on v1.sale_order_id = v2.id
            left join stock_picking pickout on v1.picking_id=pickout.id
            left join okgj_sale_return salereturn on v1.sale_return_id=salereturn.id

            """+strwhere+"""

            order by v1.state desc
        """
        cr.execute(sqlstr)
        results = cr.fetchall()

        return results

    ##采购收货入库
    def do_stockinsearch(self, cr, uid, filters, context=None):
        if context is None:
            context = {}
        data = {}
       
        okgjfilter=''.join(filters[0])
        strwhere=" and "
        strwhere=strwhere+okgjfilter

        sqlstr="""
            select COALESCE(porder.name,'') as pordernumber,COALESCE(stockpick.name,'') as stockpicknumber,
            COALESCE(product.default_code,'') as productnumber,COALESCE(product.track_incoming,False) as isqgp,
            COALESCE(stocklot.name,'') as productlot,COALESCE(stockmove.product_qty,0) as qty,COALESCE(stockmove.price_unit,0) as price
            from stock_move stockmove
            left join stock_picking stockpick on stockmove.picking_id=stockpick.id
            left join purchase_order porder on stockpick.purchase_id = porder.id
            left join product_product product on stockmove.product_id=product.id
            left join stock_production_lot stocklot on stockmove.prodlot_id=stocklot.id
            where stockpick.purchase_id is not null and stockpick.state='assigned'
           
            """+strwhere+"""
        """
        cr.execute(sqlstr)
        results = cr.fetchall()

        return results
    
    ##采购退货出库
    def do_purchaseturnsearch(self, cr, uid, filters, context=None):
        if context is None:
            context = {}
        data = {}
       
        okgjfilter=''.join(filters[0])
        strwhere=" and "
        strwhere=strwhere+okgjfilter

        sqlstr="""
            select COALESCE(porderrturn.name,'') as purreturnnumber,COALESCE(stockpick.name,'') as stockpicknumber,
            COALESCE(product.default_code,'') as productnumber,COALESCE(product.track_incoming,False) as isqgp,
            COALESCE(stocklot.name,'') as productlot,COALESCE(stockmove.product_qty,0) as qty,COALESCE(stockmove.price_unit,0) as price
            from stock_move stockmove
            left join stock_picking stockpick on stockmove.picking_id=stockpick.id
	        left join okgj_purchase_return porderrturn on stockpick.purchase_return_id = porderrturn.id
            left join product_product product on stockmove.product_id=product.id
            left join stock_production_lot stocklot on stockmove.prodlot_id=stocklot.id
            where stockpick.purchase_return_id is not null and stockpick.state='confirmed'
           
            """+strwhere+"""
        """
        cr.execute(sqlstr)
        results = cr.fetchall()

        return results

    ##商店
    def do_shopsearch(self,cr,uid,filters,context=None):
        if context is None:
            context = {}

        okgjfilter=''.join(filters[0])
        strwhere=" and "
        strwhere=strwhere+okgjfilter

        sqlstr=""" 
            select id,name,warehouse_id from sale_shop
            where 1=1

            """+strwhere+"""
        """
        cr.execute(sqlstr)
        results = cr.fetchall()

        return results
    
    ##装车单接口=================开始==============================
    def do_carstockoutseach(self,cr,uid,filters,is_sale_return=False,context=None):
        if context is None:
            context ={}

        okgjfilter=''.join(filters[0])
        strwhere=" and "
        strwhere=strwhere+okgjfilter

        if not is_sale_return:
            sqlstr="""
                select COALESCE(saleorder.name,'') as saleordernumber,COALESCE(stockpick.name,'') as stockpicknumber,
                saleorder.id as saleorderid,stockpick.id as stockpickid
                from  stock_picking stockpick 
                left join sale_order saleorder on stockpick.sale_id=saleorder.id
                where stockpick.sale_id is not null and stockpick.state='done'

                """+strwhere+"""
            """
        else:
            sqlstr="""
                select COALESCE(saleorderreturn.name,'') as saleorderreturnnumber,COALESCE(stockpick.name,'') as stockpicknumber
                saleorderreturn.id as saleorderid,stockpick.id as stockpickid
                from stock_picking stockpick 
                left join okgj_sale_return saleorderreturn on stockpick.sale_return_id=saleorderreturn.id
                where saleorderreturn.state in('confirmed', 'validate')

                """+strwhere+"""
            """
        cr.execute(sqlstr)
        results = cr.fetchall()

        return results

    def do_carloadcreate(self,cr,uid,datas,context=None):
        if context is None:
            context={}
        if not datas:
            return u'装车单数据不能为空'
        if not isinstance(datas,list):
            return u'装车单格式不正确,应为列表'
        
        car_datas=self.pool.get('okgj.logistics')
        drivers_datas=self.pool.get('okgj.logistics.car')
        warehouse_datas=self.pool.get('stock.warehouse')
        user_name = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.name

        final_line_datas=[]
        for one_data in datas:
            if not isinstance(one_data,dict):
                return u'装车单格式不正确,应为字典'
            
            warehouse_name=one_data.get('warehouse_name',False)
            if not warehouse_name:
                return u'物流中心不能为空'
            warehouse_ids=warehouse_datas.search(cr,uid,[('name','=',warehouse_name)],context=context)
            
            drivers_number=one_data.get('drivers_number',False)
            if not drivers_number:
                return u'送货管家不能为空'
            drivers_ids=drivers_datas.search(cr,uid,[('name','=',drivers_number)],context=context)
            
            okgj_isreturn=one_data.get('isreturn',False)
            okgj_type=one_data.get('okgjtype',False)
            okgj_boxnumber=one_data.get('okgjboxnumber',False)
            okgj_boxqty=one_data.get('okgjboxqty',False)
            okgj_startmiles=one_data.get('okgjstartmiles',False)
            
            line_datas=one_data.get('line_ids',False)
            if not line_datas:
                return u'装车单明细不能为空'
            if not isinstance(line_datas,list):
                return u'明细格式不正确'

            if not okgj_isreturn: ##正常出库
                for one_line_data in line_datas:
                    stockoutid=one_line_data.get('stockoutid',False)
                
                    final_line_datas.append((0,0,{
                        'picking_id':stockoutid,
                        }))
            else:##退换货
                for one_line_data in line_datas:
                    salereturn_id=one_line_data.get('stockoutid',False)
                     
                    final_line_datas.append((0,0,{
                        'sale_return_id':stockoutid,
                        }))
            try:
                new_id = car_datas.create(cr,uid,{
                    'type':okgj_type,
                    'name':'_'.join([time.strftime("%Y%m%d%H%M%S"), "PDA"]),
                    'is_sale_return':okgj_isreturn,
                    'car_id':drivers_ids[0],
                    'okgj_box':okgj_boxnumber,
                    'okgj_box_qty':okgj_boxqty,
                    'start_miles':okgj_startmiles,
                    'warehouse_id':warehouse_ids[0],
                    'line_ids':final_line_datas,
                    },context=context)
            except:
                return u'装车单创建失败!'
            return "1"
    
    ##修改货位      
    def modify_product_rack(self, cr, uid, rack_datas, context=None):
        """商品的货位有修改时，更新货位！
            @param rack_data: {
                'product_id':{'rack_id':False, 'warehouse_id':False,
                'usage':False,},...{  }
                }
        """
        if context is None:
            context = {}
        rack_obj = self.pool.get('okgj.product.rack')
        rack_usage_obj = self.pool.get('okgj.product.rack.usage')
        product_obj = self.pool.get('product.product')
        usage_dict = {'pick': 'product_pick_rack_ids', 'store': 'product_store_rack_ids'}
        

        for rack_data in rack_datas:
            rack_number=rack_data.get('rack_number',False)
            rack_usage =rack_data.get('usage',False)
            warehouse_id=rack_data.get('warehouse_id',False)
            product_number=rack_data.get('productid',False)
            warehouse_id=int(warehouse_id)
            product_rack_field = usage_dict[rack_usage]
            
            ##product_rack_field = rack_data[product_number].pop('product_rack_field')
            rack_usage_ids = False
            
            product_ids = product_obj.search(cr, uid, [('default_code', '=', product_number)], context=context)
            if not product_ids:
                return u"当前商品不存在"
            
            product_id=product_ids[0]
            rack_ids = rack_obj.search(cr, uid, [('name', '=', rack_number), ('warehouse_id', '=', int(warehouse_id))], context=context)
            
            if rack_ids:
                rack_id=rack_ids[0]

                rack_usage_data = {'rack_id':rack_id, 'warehouse_id':warehouse_id,'usage':rack_usage,'product_id':product_id,}
                try: 
                    if rack_id:
                        product_obj.write(cr, uid, product_id, {
                            product_rack_field: [(6, 0, [rack_id])]
                            }, context=context)
                        rack_usage_ids = rack_usage_obj.search(cr, uid,[
                            ('product_id', '=', product_id), 
                            ('warehouse_id', '=', warehouse_id),
                            #('rack_id', '=', rack_id),
                            ('usage', '=', rack_usage)], context=context)
                    if rack_usage_ids:
                        rack_usage_obj.write(cr, uid, rack_usage_ids, {'rack_id' : rack_id}, context=context)
                    else:
                        rack_usage_obj.create(cr, uid, rack_usage_data, context=context)
                except Exception,e:
                    return e
            else:
                return u'货位不存在'
        return "1"
okgj_mobilesign()

# 采购退货出库
class okgj_purreturn_stock_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"
    
    def purreturn_stock_out_do_partial(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'Partial picking processing may only be done one at a time.'
        stock_picking = self.pool.get('stock.picking')
        stock_move = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        partial = self.browse(cr, uid, ids[0], context=context)
        partial_data = {
            'delivery_date' : partial.date
        }
        #存储同一商品不同生产日期数据
        unlike_date_datas = {}
        move_product_ids = {}
        for wizard_line in partial.move_ids:
            move_product_ids['move%s' % (wizard_line.move_id.id)] = [wizard_line.move_id.product_id.id]
        picking_type = partial.picking_id.type
        for wizard_line in partial.move_ids:
            line_uom = wizard_line.product_uom
            move_id = wizard_line.move_id.id
            #Quantiny must be Positive
            if wizard_line.quantity < 0:
                raise osv.except_osv(_('Warning!'), _('Please provide proper Quantity.'))

            #Compute the quantity for respective wizard_line in the line uom (this jsut do the rounding if necessary)
            qty_in_line_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, line_uom.id)

            if line_uom.factor and line_uom.factor <> 0:
                if float_compare(qty_in_line_uom, wizard_line.quantity, precision_rounding=line_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _('The unit of measure rounding does not allow you to ship "%s %s", only roundings of "%s %s" is accepted by the Unit of Measure.') % (wizard_line.quantity, line_uom.name, line_uom.rounding, line_uom.name))
            if move_id:
                #Check rounding Quantity.ex.
                #picking: 1kg, uom kg rounding = 0.01 (rounding to 10g),
                #partial delivery: 253g
                #=> result= refused, as the qty left on picking would be 0.747kg and only 0.75 is accepted by the uom.
                initial_uom = wizard_line.move_id.product_uom
                #Compute the quantity for respective wizard_line in the initial uom
                qty_in_initial_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, initial_uom.id)
                without_rounding_qty = (wizard_line.quantity / line_uom.factor) * initial_uom.factor
                if float_compare(qty_in_initial_uom, without_rounding_qty, precision_rounding=initial_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _('The rounding of the initial uom does not allow you to ship "%s %s", as it would let a quantity of "%s %s" to ship and only roundings of "%s %s" is accepted by the uom.') % (wizard_line.quantity, line_uom.name, wizard_line.move_id.product_qty - without_rounding_qty, initial_uom.name, initial_uom.rounding, initial_uom.name))
            else:
                seq_obj_name =  'stock.picking.' + picking_type
                move_id = stock_move.create(cr,uid,{'name' : self.pool.get('ir.sequence').get(cr, uid, seq_obj_name),
                                                    'product_id': wizard_line.product_id.id,
                                                    'product_qty': wizard_line.quantity,
                                                    'product_uom': wizard_line.product_uom.id,
                                                    'prodlot_id': wizard_line.prodlot_id.id,
                                                    'location_id' : wizard_line.location_id.id,
                                                    'location_dest_id' : wizard_line.location_dest_id.id,
                                                    'picking_id': partial.picking_id.id
                                                    },context=context)
                stock_move.action_confirm(cr, uid, [move_id], context)
            #收集同一商品不同生产日期数据
            line_prodlot_id = wizard_line.prodlot_id.id
            line_product_id = wizard_line.product_id.id
            line_qty = wizard_line.quantity
            if 'move%s' % (wizard_line.move_id.id) not in partial_data:
                partial_data['move%s' % (wizard_line.move_id.id)] = {
                    'product_id': wizard_line.product_id.id,
                    'product_qty': wizard_line.quantity,
                    'product_uom': wizard_line.product_uom.id,
                    'prodlot_id': wizard_line.prodlot_id.id,
                }
            elif 'move%s' % (wizard_line.move_id.id) in partial_data:
                current_data = [wizard_line.product_id.id, wizard_line.prodlot_id.id]
                origin_data = [partial_data['move%s' % (wizard_line.move_id.id)].get('product_id', False), partial_data['move%s' % (wizard_line.move_id.id)].get('prodlot_id', False)]
                if current_data != origin_data:
                    if 'move%s'% (wizard_line.move_id.id) in unlike_date_datas.keys():
                        if line_prodlot_id in unlike_date_datas['move%s' % (wizard_line.move_id.id)]:
                            unlike_qty = unlike_date_datas['move%s' % (wizard_line.move_id.id)][line_prodlot_id].get('product_qty', False) + line_qty
                            unlike_date_datas['move%s' % (wizard_line.move_id.id)][line_prodlot_id].update(product_qty=unlike_qty)
                        else:
                            unlike_date_datas['move%s' % (wizard_line.move_id.id)].update({
                                                        line_prodlot_id: {
                                                         'product_id': wizard_line.product_id.id,
                                                         'product_qty': wizard_line.quantity,
                                                         'product_uom': wizard_line.product_uom.id,
                                                         'prodlot_id': wizard_line.prodlot_id.id,
                                                                }})
                        
                    elif 'move%s' % (wizard_line.move_id.id) not in unlike_date_datas.keys():
                            unlike_date_datas['move%s' % (wizard_line.move_id.id)] = {line_prodlot_id: {
                                                                     'product_id': wizard_line.product_id.id,
                                                                     'product_qty': wizard_line.quantity,
                                                                     'product_uom': wizard_line.product_uom.id,
                                                                     'prodlot_id': wizard_line.prodlot_id.id,
                                                                                        }}
                        
                elif current_data == origin_data:
                    origin_quantity = partial_data['move%s' % (wizard_line.move_id.id)].get('product_qty', False)
                    quantity = origin_quantity + wizard_line.quantity
                    partial_data['move%s' % (wizard_line.move_id.id)].update(product_qty=quantity)
                    
            if (picking_type == 'in') and (wizard_line.product_id.cost_method == 'average'):
                partial_data['move%s' % (wizard_line.move_id.id)].update(product_price=wizard_line.cost,
                                                                    product_currency=wizard_line.currency.id)
        res = stock_picking.action_mobile_stock_in(cr, uid, [partial.picking_id.id], partial_data, context=context)
        #处理商品不同生产日期数据
        #已收货new_picking
        #注意商品的平均价格计算是否准确(standard_price:成本价)
        new_picking = res[partial.picking_id.id].get('delivered_picking', False)
        print unlike_date_datas,'unlike_date_datas'
        unlike_datas_list = [(unlike_move_id, unlike_date_datas[unlike_move_id].values()) for unlike_move_id in unlike_date_datas]
        for unlike_move_id, unlike_date_data in unlike_datas_list:
            for one_date_data in unlike_date_data:
                one_date_data['delivery_date'] = partial.date
                unlike_datas = dict([(unlike_move_id, one_date_data)])
                stock_picking.action_mobile_stock_in(cr, uid, [partial.picking_id.id], unlike_datas, new_picking, context=context)
        return True
    
    def get_purreturn_move_line_data(self, cr, uid, value=None, context=None):
        '''
            @params:value: [(picking_id, '=',False), (product_id, '=', False), (prodlot_id, '=', False)]
        '''
        if value is None:
            return u'过滤条件value错误'
        move_obj = self.pool.get('stock.move')
        move_lines = [] 
        # 搜索move_id
        move_ids = move_obj.search(cr, uid, value)
        if not move_ids:
            move_ids = move_obj.search(cr, uid, value[0:2])
        for one_move_data in move_obj.browse(cr, uid, move_ids):
            data = {
                    'product_id' : one_move_data.product_id.id,
                    'quantity' : one_move_data.product_qty if one_move_data.state in ('assigned','draft','confirmed') else 0,
                    'product_uom' : one_move_data.product_uom.id,
                    #'prodlot_id' : one_move_data.prodlot_id.id,
                    'move_id' : one_move_data.id,
                    'location_id' : one_move_data.location_id.id,
                    'location_dest_id' : one_move_data.location_dest_id.id,
                    
                    }
            if one_move_data.picking_id.type == 'in' and one_move_data.product_id.cost_method == 'average':
                data.update(update_cost=True, **self._product_cost_for_average_update(cr, uid, one_move_data))
            move_lines.append(data)
        return move_lines
    
    def do_purreturn_parse_datas(self, cr, uid, datas=None, context=None):
        print datas,'datas'
        process_info = {
                        '0':u'数据不能为空',
                        '1':u'1', #数据处理成功
                        '2':u'采购退货单不存在,请确认!',
                        '3':u'数据处理失败,请检查相关数据信息  或网络连接!',
                        '5':u'数据元素长度错误!', 
                        '6':u'数据格式错误,数据格式必须为:[{"picking_id":'',"datas":[{"product_id":[], "stockin_qty":0, "product_lot_id":''}] }]',
                        '7':u'ERP的采购收货单里,商品%s有重复.',
                        '8':u'商品编码不能为空',
                        '9':u'商品%s:批次号格式错误,批次号格式为6位年月日',
                        '10':u'输入有误:收货单明细里没有商品%s!',
                        '11':u'采购退货单号 %s,请确认!',
                        '12':u'商品%s:批次号不能为空!'}
        picking_state_dict ={'assigned':u'待接收','done':u'已接收','cancel':u'已取消'}
        if context is None: context = {}
        datas_dict = None
        picking_obj = self.pool.get('stock.picking.out')
        lot_obj = self.pool.get('stock.production.lot')
        product_obj = self.pool.get('product.product')
        if not datas:
            return process_info['0']
        if isinstance(datas, list):
            if len(datas) >1:
                return process_info['5']
            elif len(datas) == 1:
                datas_dict = datas[0]
        elif isinstance(datas, dict):
            datas_dict = datas.copy()
        else:
            return process_info['6']
        if datas_dict:
            picking_name = datas_dict.get('picking_id', '')
            picking_datas = datas_dict.get('datas', [])
            if not picking_name:
                return process_info['2']
            if not picking_datas:
                return process_info['0']
            picking_ids = picking_obj.search(cr, uid, [('name', '=', picking_name)])
            if not picking_ids:
                return process_info['2']
            if picking_ids:
                picking_state = picking_obj.read(cr, uid, picking_ids[0], ['state'])['state']
                if picking_state in picking_state_dict and picking_state not in ['assigned']:
                    state_info = process_info['11'] % (picking_state_dict[picking_state])
                    return state_info
            # stockin_qty:数量 , product_lot_id:批次号, product_id:商品编码
            # 创建stock.partial.picking
            partial_picking_id = self.create(cr, uid, {'picking_id':picking_ids[0], 'date':time.strftime('%Y-%m-%d %H:%M:%S')})
            move_datas = []
            for one_datas in picking_datas:
                #商品批次(生产日期)
                prodlot_id = False
                have_origin_prodlot = False
                #商品数量
                quantity = one_datas.get('stockin_qty', False)
                #商品id
                product_default_code = one_datas.get('product_id', False)
                if not product_default_code:
                    return process_info['8']
                product_ids = product_obj.search(cr, uid, [('default_code', '=', product_default_code)])
                track_incoming = product_obj.read(cr, uid, product_ids[0], ['track_incoming'])['track_incoming']
                prodlot_name = one_datas.get('product_lot_id', False)
                value = [('picking_id', '=', picking_ids[0]), ('product_id', '=', product_ids[0])]
                if prodlot_name:
                    if len(str(prodlot_name)) != 6:
                        prodlot_info = process_info['9'] % (product_default_code)
                        return prodlot_info
                    prefix_prodlot_name = '20' + str(prodlot_name)  
                    prodlot_ids = lot_obj.search(cr, uid, [('name', '=', prefix_prodlot_name), ('product_id', '=', product_ids[0])])
                    if prodlot_ids:
                        prodlot_id = prodlot_ids[0]
                        have_origin_prodlot = True
                    else:
                        prodlot_id = lot_obj.create(cr, uid, {'name':prodlot_name, 'product_id':product_ids[0], })
                if track_incoming:
                    if not prodlot_id:
                        msg = process_info['12'] % (product_default_code)
                        return msg
                    else:
                        if have_origin_prodlot:
                            value.append(('prodlot_id', '=', prodlot_id))
                else:
                    if prodlot_id and have_origin_prodlot:
                        value.append(('prodlot_id', '=', prodlot_id))
                #收集商品移库信息
                move_lines = self.get_purreturn_move_line_data(cr, uid, value=value)
                if move_lines:
                    if len(move_lines) == 1:
                        move_lines[0]['quantity'] = quantity
                        move_lines[0]['prodlot_id'] = prodlot_id
                        move_lines[0]['wizard_id'] = partial_picking_id
                        move_lines[0]['prodlot_id'] = prodlot_id or False
                        move_datas.append((0, 0, move_lines[0]))
                    else:
                        line_info = process_info['7'] % (product_default_code)
                        return line_info
                else:
                    message = process_info['10'] % (product_default_code)
                    return message
            print move_datas,'move_datas'
            self.write(cr, uid, partial_picking_id, {'move_ids':move_datas})
            # 调用stock_in_do_partial方法:处理商品移库
            try:
                flg = self.purreturn_stock_out_do_partial(cr, uid, [partial_picking_id])
            except:
                return process_info['3']
            if flg:
                return process_info['1']
            else:
                return process_info['3']

okgj_purreturn_stock_picking() 
