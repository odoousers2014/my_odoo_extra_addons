# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import netsvc
from openerp.tools.float_utils import float_compare
import copy
import time

    
class okgj_stock_warehouse(osv.osv):
    _inherit = "stock.warehouse"
    _columns = {
        'okgj_warehouse_id':fields.integer(u'商城维护ID'), 
    }


class okgj_stock_location(osv.osv):
    _inherit = "stock.location"
    _columns = {
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心'),
        'is_presale':fields.boolean(u'预售库'),
    }
okgj_stock_location()

class okgj_stock_inventory(osv.osv):
    _inherit = "stock.inventory"
    _order = "date desc"
    _columns = {
        'note':fields.text(u'备注'),
    }
    
    def process_error_message(self, error_type, product_code = ''):
        """error 消息处理
        """
        message_body = u''  
        if error_type == 'no_datas' :
            message_body = u'错误:盘点的数据不能 为空!' 
        if error_type == 'format_error' :
            message_body = u'盘点数据格式错误,格式必须为 :[{...}, {...}] 列表类型!'
        if error_type == 'line_format' :
            message_body = u'盘点明细数据 格式错误,格式必须为: {...} 字典类型!'
        if error_type == 'no_exist' :
            message_body = u'商品 %s:不存在!' % (product_code)
        if error_type == 'non_null' :
            message_body = u'商品%s:仓库不能为空!' % (product_code)
        if error_type == 'no_location' :
            message_body = u'商品:%s 仓库不存在,请确认!' % (product_code)
        if error_type == 'no_rack' :
            message_body = u'商品 :%s的货位不存在!' % (product_code)
        if error_type == 'create_error' :
            message_body = u'盘点数据创建失败:请重新创建!'
        if error_type == 'non_rack' :
            message_body = u'盘点商品的货位不能为空!'
        if error_type == 'non_warehouse' :
            message_body = u'盘点商品的物流中心不能为空!'
        if error_type == 'no_warehouse' :
            message_body = u'该商品的物流中心不存在, 请确认!'
        if error_type == 'prdlot_error':
            message_body = u'商品%s:批次号格式错误,批次号格式为6位年月日' % (product_code)
        if error_type == 'warehouse_error':
            message_body = u'类型错误:发现无效字符串,参数物流中心的类型必须为:int or long or list!'
        if error_type == 'non_prodlot':
            message_body = u'商品%s:批次号不能为空!' % (product_code)
        return message_body
    
    def update_product_rack(self, cr, uid, rack_data, context=None):
        """商品的货位有修改时，更新货位！
            @param rack_data: {
                'product_id':{'rack_id':False, 'warehouse_id':False,
                'usage':False, 'origin_rack_ids':False},...{  }
                }
        """
        if context is None:
            context = {}
        rack_usage_obj = self.pool.get('okgj.product.rack.usage')
        product_obj = self.pool.get('product.product')

        for product_id in rack_data:
            rack_id, rack_usage = rack_data[product_id]['rack_id'], rack_data[product_id]['usage']
            warehouse_id, rack_usage_data = rack_data[product_id]['warehouse_id'], rack_data[product_id]
            product_rack_field = rack_data[product_id].pop('product_rack_field')
            origin_rack_ids = rack_data[product_id].pop('origin_rack_ids')  
            rack_usage_ids = False
            
            if origin_rack_ids and (rack_id != origin_rack_ids[0]):
                product_obj.write(cr, uid, product_id, {
                    product_rack_field: [(6, 0, [rack_id])]
                    }, context=context)
                rack_usage_ids = rack_usage_obj.search(cr, uid,[
                    ('product_id', '=', product_id), 
                    ('warehouse_id', '=', warehouse_id),
                    ('rack_id', '=', origin_rack_ids[0]),
                    ('usage', '=', rack_usage)], context=context)
            elif (not origin_rack_ids):
                product_obj.write(cr, uid, product_id, {product_rack_field: [(4, rack_id)]}, context=context)
            
            if rack_usage_ids:
                rack_usage_obj.write(cr, uid, rack_usage_ids, {'rack_id' : rack_id}, context=context)
            else:
                rack_usage_obj.create(cr, uid, rack_usage_data, context=context)
        return True
    
    ##手机盘点接口
    def action_mobile_inventory(self, cr, uid, datas, context=None):
        '''@param datas: [{'picking_id': False, 'product_id': False,
                           'product_qty': 0, 'prdlot_id': '',   
                           'location_id': '', 'warehouse_id': False}, {...}, {...}]
        '''
        if not datas:
            return self.process_error_message('no_datas')
        if not isinstance(datas, list):
            return self.process_error_message('format_error')
        if context is None:
            context = {}
        
        inventory_obj = self.pool.get('stock.inventory')
        product_obj = self.pool.get('product.product')
        stock_obj = self.pool.get('stock.location')
        rack_obj = self.pool.get('okgj.product.rack')
        rack_usage_obj = self.pool.get('okgj.product.rack.usage')
        lot_obj = self.pool.get('stock.production.lot')
        warehouse_obj = self.pool.get('stock.warehouse')
        user_name = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.name
        
        inventory_line_data = []
        product_rack_data = {}
        inventory_note = u'创建人:%s' % (user_name) 
        usage_dict = {'pick': 'product_pick_rack_ids', 'store': 'product_store_rack_ids'}
        for one_inventory_data in datas:
            if not isinstance(one_inventory_data, dict):
                return self.process_error_message('line_format')
            default_code = one_inventory_data.get('product_id', False)
            product_qty = one_inventory_data.get('product_qty', 0)
            prodlot_name = one_inventory_data.get('prodlot_id', False)
            stock_name = one_inventory_data.get('stock_id', False)
            rack_name = one_inventory_data.get('rack_id', False)
            rack_usage = one_inventory_data.get('rack_usage', False)
            product_rack_field = usage_dict[rack_usage]
            warehouse_name = one_inventory_data.get('warehouse_id', False)
            
            if not warehouse_name:
                return self.process_error_message('non_warehouse')
            warehouse_ids = warehouse_obj.search(cr, uid, [('name', '=', warehouse_name)], context=context)
            if not stock_name:
                return self.process_error_message('non_null', default_code)
            
            product_ids = product_obj.search(cr, uid, [('default_code', '=', default_code)], context=context)
            if not product_ids:
                return self.process_error_message('no_exist', default_code)
            uom_id = product_obj.read(cr, uid, product_ids[0], ['uom_id'], load='_classic_write', context=context)['uom_id']
            
            stock_location_ids = stock_obj.search(cr, uid, [('complete_name', '=', stock_name), ('usage', '=', 'internal')], context=context)
            if not stock_location_ids:
                return self.process_error_message('no_location', default_code)
            #处理生产日期
            prodlot_id = False
            track_incoming = product_obj.read(cr, uid, product_ids[0], ['track_incoming'])['track_incoming']
            if prodlot_name:
                if len(str(prodlot_name)) != 6:
                    return self.process_error_message('prodlot_error', default_code)
                prefix_prodlot_name = '20' + str(prodlot_name)  
                prodlot_ids = lot_obj.search(cr, uid, [('name', '=', prefix_prodlot_name), ('product_id', '=', product_ids[0])], context=context)
                if prodlot_ids:
                    prodlot_id = prodlot_ids[0]
                else:
                    prodlot_id = lot_obj.create(cr, uid, {'name':prodlot_name, 'product_id':product_ids[0], }, context=context)
            else:
                if track_incoming:
                    return self.process_error_message('non_prodlot', default_code)
            #处理货位
            origin_rack_ids = product_obj.read(cr, uid, product_ids[0], [product_rack_field], context=context)[product_rack_field]
            if rack_name:
                rack_ids = rack_obj.search(cr, uid, [('name', '=', rack_name), ('warehouse_id', '=', warehouse_ids[0])], context=context)
                if rack_ids:
                    if product_ids[0] not in product_rack_data:
                        product_rack_data[product_ids[0]] = {
                            'product_id': product_ids[0],
                            'warehouse_id': warehouse_ids[0],
                            'rack_id': rack_ids[0],
                            'usage': rack_usage,
                            'origin_rack_ids': origin_rack_ids,
                            'product_rack_field': product_rack_field,}
                else:
                    return self.process_error_message('no_rack', default_code)
            inventory_line_data.append((0, 0,{
                'location_id': stock_location_ids[0],
                'product_id': product_ids[0],
                'product_qty': product_qty,
                'product_uom':  uom_id,
                'prod_lot_id': prodlot_id,}))
        
        flg = True
        try:
            inventory_id = inventory_obj.create(cr, uid, {
                'name': '_'.join([time.strftime("%Y%m%d%H%M%S"), user_name]),
                'note': inventory_note,
                'inventory_line_id': inventory_line_data,}, context=context)
        except:
            flg = False
            return self.process_error_message('create_error')
        #修改货位:
        if flg:
            self.update_product_rack(cr, uid, product_rack_data, context=context)
        return '1'
    
    def get_product_info(self, cr, uid, product_filter, context=None):
        '''
            @param: product_filter: [[...]]
            example: [['is_group_product','=','True'], ['default_code','=',"'123'"],] 
        '''
        sql_str ="""
            SELECT p.default_code, p.name_template, p.variants, p.track_incoming, r.name, ru.usage
            FROM product_product as p
            LEFT JOIN okgj_product_rack_usage as ru on ru.product_id=p.id 
            LEFT JOIN okgj_product_rack r on ru.rack_id = r.id
            LEFT JOIN stock_warehouse w on ru.warehouse_id = w.id
            """
        if not isinstance(product_filter, list):
            return u'查询数据格式错误 ,格式 必须为 [[...]]'
        
        filter_str = ''
        for s in product_filter:
            filter_str += ' AND '
            blank_str = ''
            filter_str += blank_str.join(s)
        filter_str = " where p.is_group_product='f' " + filter_str
        sql_str += filter_str
        
        cr.execute(sql_str)
        result = []
        for i in cr.fetchall():
            #处理None值
            res = map(lambda x: '' if x is None else x, i)
            result.append(res)
        return result
    
    def get_logistics_info(self, cr, uid, context=None):
        """获取所有物流中心信息"""
        sql_str = """
                    SELECT name, id FROM stock_warehouse
                  """
        cr.execute(sql_str)
        return cr.fetchall()
    
    def get_warehouse_info(self, cr, uid, warehouse_id=None, context=None):
        """获取物流中心仓库信息"""
        sql_str = """
                    SELECT complete_name, id, warehouse_id
                    FROM stock_location
                    WHERE usage='internal'
                  """
        if warehouse_id:
            if isinstance(warehouse_id, (int, long)):
                warehouse_id = [warehouse_id]
            elif isinstance(warehouse_id, basestring):
                return self.process_error_message('warehouse_error')
            warehouse_id = tuple(warehouse_id)
            where_str = " and warehouse_id in %s" 
            sql_str += where_str
            cr.execute(sql_str, (warehouse_id,))
        else:
            cr.execute(sql_str)
        return cr.fetchall()

okgj_stock_inventory()
    
class okgj_stock_picking(osv.osv):
    _inherit = "stock.picking"
    _order = "create_date desc"

    #处理手机收货
    def action_mobile_stock_in(self, cr, uid, ids, partial_datas, new_picking=None, context=None):
        """ Makes partial picking and moves done from mobile phone.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, partner_id, delivery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        #增加以便取多物流中心成本数据
        warehouse_sprice_obj = self.pool.get("okgj.warehouse.sprice")
        for pick in self.browse(cr, uid, ids, context=context):
            #传入已收货new_picking,避免处理同一商品多个生产日期时,生成新的收货单
            new_picking = new_picking
            #new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s'%(move.id), {})
                product_qty = partial_data.get('product_qty',0.0)
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom',False)
                product_price = partial_data.get('product_price',0.0)
                product_currency = partial_data.get('product_currency',False)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    too_many.append(move)

                # Average price computation
                if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                    product = product_obj.browse(cr, uid, move.product_id.id)
                    move_currency_id = move.company_id.currency_id.id
                    context['currency_id'] = move_currency_id
                    qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)

                    if product.id in product_avail:
                        product_avail[product.id] += qty
                    else:
                        product_avail[product.id] = product.qty_available

                    if qty > 0:
                        new_price = currency_obj.compute(cr, uid, product_currency,
                                move_currency_id, product_price)
                        new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                                product.uom_id.id)
                        if product.qty_available <= 0:
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get('standard_price', context=context)[product.id]
                            new_std_price = ((amount_unit * product_avail[product.id])\
                                + (new_price * qty))/(product_avail[product.id] + qty)
                        # Write the field according to price type field
                        product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})

                        # Record the values that were chosen in the wizard, so they can be
                        # used for inventory valuation if real-time valuation is enabled.
                        move_obj.write(cr, uid, [move.id],
                                {'price_unit': product_price,
                                 'price_currency_id': product_currency})

                        ##更改多物流中心的成本价
                        warehouse_id = pick.warehouse_id.id
                        warehouse_context = copy.deepcopy(context)
                        warehouse_context.update({'warehouse':warehouse_id})
                        warehouse_product_data = product_obj.browse(cr, uid, product.id, context=warehouse_context)
                        #获取是否有该物流中心成本数据
                        warehouse_sprice_line_id = warehouse_sprice_obj.search(cr, uid, [
                            ('warehouse_id', '=', warehouse_id),
                            ('product_id', '=', product.id)
                            ], context=context)
                        if warehouse_sprice_line_id:
                            old_warehouse_sprice = warehouse_sprice_obj.browse(cr, uid, warehouse_sprice_line_id[0], context=warehouse_context).standard_price
                        else:
                            old_warehouse_sprice = 0
                        if warehouse_product_data.qty_available <=0:
                            new_warehouse_std_price = new_price
                        else:
                            new_warehouse_std_price = ((old_warehouse_sprice * warehouse_product_data.qty_available)\
                                                       + (new_price * qty))/(warehouse_product_data.qty_available + qty)
                        if warehouse_sprice_line_id:
                            warehouse_sprice_obj.write(cr, uid, warehouse_sprice_line_id[0], {'standard_price':new_warehouse_std_price}, context=warehouse_context)
                        else:
                            warehouse_sprice_obj.create(cr, uid, {
                                'product_id':product.id,
                                'standard_price':new_warehouse_std_price,
                                'warehouse_id':warehouse_id
                                }, context=warehouse_context)
                        #Added by ouke 1 above
            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    new_picking_name = pick.name
                    self.write(cr, uid, [pick.id], 
                               {'name': sequence_obj.get(cr, uid,
                                            'stock.picking.%s'%(pick.type)),
                               })
                    new_picking = self.copy(cr, uid, pick.id,
                            {
                                'name': new_picking_name,
                                'move_lines' : [],
                                'state':'draft',
                            })
                if product_qty != 0:
                    defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty, #TODO: put correct uos_qty
                            'picking_id' : new_picking,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': move.price_unit,
                            'product_uom': product_uoms[move.id]
                    }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(cr, uid, move.id, defaults)
                move_obj.write(cr, uid, [move.id],
                        {
                            'product_qty': move.product_qty - partial_qty[move.id],
                            'product_uos_qty': move.product_qty - partial_qty[move.id], #TODO: put correct uos_qty
                            'prodlot_id': False,
                            'tracking_id': False,
                        })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[move.id], 'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty' : product_qty,
                    'product_uos_qty': product_qty, #TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking], context=context)
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_done', cr)
                wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
                delivered_pack_id = new_picking
                back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                self.message_post(cr, uid, ids, body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name), context=context)
            else:
                self.action_move(cr, uid, [pick.id], context=context)
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}

        return res

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial picking and moves done.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, partner_id, delivery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        #增加以便取多物流中心成本数据
        warehouse_sprice_obj = self.pool.get("okgj.warehouse.sprice")
        for pick in self.browse(cr, uid, ids, context=context):
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            product_warehouse_avail = {}
            last_qty = {}
            last_warehouse_qty = {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s'%(move.id), {})
                product_qty = partial_data.get('product_qty',0.0)
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom',False)
                product_price = partial_data.get('product_price',0.0)
                product_currency = partial_data.get('product_currency',False)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    too_many.append(move)

                # Average price computation
                if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                    ##位置不传入
                    context.update({'shop':False,'warehouse':False, 'location':False})
                    product = product_obj.browse(cr, uid, move.product_id.id, context=context)
                    move_currency_id = move.company_id.currency_id.id
                    context['currency_id'] = move_currency_id
                    qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)

                    warehouse_id = pick.warehouse_id.id
                    ## bug repaired by ouke 1 多批次入库成本问题
                    if product.id in last_qty:
                        add_qty = last_qty[product.id]
                    else:
                        add_qty = 0

                    if product.id in product_avail:
                        product_avail[product.id] += add_qty
                    else:
                        product_avail[product.id] = product.qty_available


                    if qty > 0:
                        new_price = currency_obj.compute(cr, uid, product_currency,
                                move_currency_id, product_price)
                        new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                                product.uom_id.id)
                        if product.qty_available <= 0:
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get('standard_price', context=context)[product.id]
                            new_std_price = ((amount_unit * product_avail[product.id])\
                                + (new_price * qty))/(product_avail[product.id] + qty)
                        # Write the field according to price type field
                        product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})

                        # Record the values that were chosen in the wizard, so they can be
                        # used for inventory valuation if real-time valuation is enabled.
                        move_obj.write(cr, uid, [move.id],
                                {'price_unit': product_price,
                                 'price_currency_id': product_currency})

                        ##更改多物流中心的成本价
                        if warehouse_id not in product_warehouse_avail:
                            product_warehouse_avail[warehouse_id] = {}
                        if warehouse_id not in last_warehouse_qty:
                            last_warehouse_qty[warehouse_id] = {}
                        ## 上个周期数量
                        if product.id in last_warehouse_qty[warehouse_id]:
                            add_warehouse_qty = last_warehouse_qty[warehouse_id][product.id]
                        else:
                            add_warehouse_qty = 0
                        if product.id in product_warehouse_avail[warehouse_id]:
                            product_warehouse_avail[warehouse_id][product.id] += add_warehouse_qty
                        else:
                            warehouse_context = copy.deepcopy(context)
                            warehouse_context.update({'warehouse':warehouse_id})
                            warehouse_product_data = product_obj.browse(cr, uid, product.id, context=warehouse_context)
                            product_warehouse_avail[warehouse_id][product.id] = warehouse_product_data.qty_available
                            
                        #获取是否有该物流中心成本数据
                        warehouse_sprice_line_id = warehouse_sprice_obj.search(cr, uid, [
                            ('warehouse_id', '=', warehouse_id),
                            ('product_id', '=', product.id)
                            ], context=context)
                        if warehouse_sprice_line_id:
                            old_warehouse_sprice = warehouse_sprice_obj.browse(cr, uid, warehouse_sprice_line_id[0], context=warehouse_context).standard_price
                        else:
                            old_warehouse_sprice = 0

                        if product_warehouse_avail[warehouse_id][product.id] <=0:
                            new_warehouse_std_price = new_price
                        else:
                            new_warehouse_std_price = ((old_warehouse_sprice * product_warehouse_avail[warehouse_id][product.id])\
                                                       + (new_price * qty))/(product_warehouse_avail[warehouse_id][product.id] + qty)

                        if warehouse_sprice_line_id:
                            warehouse_sprice_obj.write(cr, uid, warehouse_sprice_line_id[0], {'standard_price':new_warehouse_std_price}, context=warehouse_context)
                        else:
                            warehouse_sprice_obj.create(cr, uid, {
                                'product_id':product.id,
                                'standard_price':new_warehouse_std_price,
                                'warehouse_id':warehouse_id
                                }, context=warehouse_context)
                        last_qty[product.id] = qty
                        last_warehouse_qty[warehouse_id][product.id] = qty
                    #Added by ouke 1 above
            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    new_picking_name = pick.name
                    self.write(cr, uid, [pick.id], 
                               {'name': sequence_obj.get(cr, uid,
                                            'stock.picking.%s'%(pick.type)),
                               })
                    new_picking = self.copy(cr, uid, pick.id,
                            {
                                'name': new_picking_name,
                                'move_lines' : [],
                                'state':'draft',
                            })
                if product_qty != 0:
                    defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty, #TODO: put correct uos_qty
                            'picking_id' : new_picking,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': move.price_unit,
                            'product_uom': product_uoms[move.id]
                    }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(cr, uid, move.id, defaults)
                move_obj.write(cr, uid, [move.id],
                        {
                            'product_qty': move.product_qty - partial_qty[move.id],
                            'product_uos_qty': move.product_qty - partial_qty[move.id], #TODO: put correct uos_qty
                            'prodlot_id': False,
                            'tracking_id': False,
                        })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[move.id], 'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty' : product_qty,
                    'product_uos_qty': product_qty, #TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking], context=context)
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_done', cr)
                wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
                delivered_pack_id = new_picking
                back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                self.message_post(cr, uid, ids, body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name), context=context)
            else:
                self.action_move(cr, uid, [pick.id], context=context)
                wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}

        return res

    def _get_warehouse(self, cr, uid, ids, field_names, arg, context=None):
        """ Read the 'warehouse' functional fields. """
        res = {}.fromkeys(ids, 0.0)
        for one_picking in self.browse(cr, uid, ids, context=context):
            warehouse_id = ((one_picking.purchase_id  and one_picking.purchase_id.warehouse_id.id) or 
                            (one_picking.sale_id  and one_picking.sale_id.shop_id.warehouse_id.id) or 
                            (one_picking.purchase_return_id  and one_picking.purchase_return_id.warehouse_id.id) or 
                            (one_picking.sale_return_id  and one_picking.sale_return_id.warehouse_id.id) or
                            False)
            if not warehouse_id:
                if one_picking.internal_order_id:
                    if one_picking.internal_order_id.dest_warehouse_id:
                        if one_picking.type == 'in':
                            warehouse_id = one_picking.internal_order_id.dest_warehouse_id.id
                        elif one_picking.type == 'out':
                            warehouse_id = one_picking.internal_order_id.warehouse_id.id
                    else:
                        warehouse_id = one_picking.internal_order_id.warehouse_id.id
            res[one_picking.id] = warehouse_id
        return res

    _columns = {
        'okgj_type':fields.selection([
            ('okgj_internal_in', u'其它入库单'),
            ('okgj_internal_out', u'其它出库单'),
            ('okgj_internal_internal', u'其它调拨单'),
            ('okgj_others', u'其它单据'),
            ('okgj_sale_in', u'销售退货入库单'),
            ('okgj_internal_in', u'其它入库单'),
            ('okgj_purchase_out', u'采购退货出库单'),
            ('okgj_sale_out', u'销售退货出库单'),
            ], string=u'单据类型'),
        'internal_order_id':fields.many2one('okgj.order.picking.internal', u'源出入库申请单'),
        'sale_return_id':fields.many2one('okgj.sale.return', u'源销售退货单'),
        'sale_return_sale':fields.related('sale_return_id', 'sale_order_id', type='many2one', relation='sale.order', store=True, string=u'源销售单'),
        'okgj_sale_return_city':fields.related('sale_return_id', 'sale_order_id', 'okgj_city', type='char', string=u'收货城市', readonly=True, store=True),
        'sale_return_consignee':fields.related('sale_return_id', 'consignee', type='char', store=True, string=u'收货人'),
        'sale_return_tel':fields.related('sale_return_id', 'okgj_tel', type='char', store=True, string=u'联系电话'),
        'purchase_return_id':fields.many2one('okgj.purchase.return', u'源退货单'),
        'print_state':fields.selection([('not', 'NOT'), ('yes', 'YES')], 'Print State'),
        'collect_state':fields.selection([('not', 'NOT'), ('yes', 'YES')], 'Collect Print State'),
        'pay_id':fields.related('sale_id', 'pay_name', type='char', string='支付方式', readonly=True),
        'send_time':fields.related('sale_id', 'send_time', type='char', string=u'要求送货时间', readonly=True, store=True),
        'inv_payee':fields.related('sale_id', 'inv_payee', type='text', string=u'发票抬头', readonly=True),
        'inv_content':fields.related('sale_id', 'inv_content', type='text', string=u'发票内容', readonly=True),
        'inv_amount':fields.related('sale_id', 'inv_amount', type='float', string=u'发票金额', readonly=True),
        'okgj_city':fields.related('sale_id', 'okgj_city', type='char', string=u'收货城市', readonly=True),
        'region_name':fields.related('sale_id', 'region_name', type='char', string=u'收货区域', readonly=True),
        'okgj_address':fields.related('sale_id', 'okgj_address', type='char', string=u'收货地址', readonly=True),
        'consignee':fields.related('sale_id', 'consignee', type='char', string=u'收货人', readonly=True,),
        'create_date': fields.datetime(u'创建时间', readonly=True),
        'create_uid': fields.many2one('res.users', u'创建人', readonly=True),
        'write_date': fields.datetime(u'修改时间', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'warehouse_id':fields.function(_get_warehouse, type='many2one', relation='stock.warehouse', string=u'物流中心', store=True),
    }
    _defaults = {
        'collect_state': lambda *args: 'not',
        'print_state': lambda *args: 'not',
    }
okgj_stock_picking()

class okgj_stock_picking_in(osv.osv):
    _inherit = "stock.picking.in"
    _order = "create_date desc"
    _columns = {
        'warehouse_id':fields.many2one('stock.warehouse', string=u'物流中心', readonly=True),
        'sale_return_id':fields.many2one('okgj.sale.return', u'源销售退货单'),
        'sale_return_sale':fields.related('sale_return_id', 'sale_order_id', type='many2one', relation='sale.order', store=True, string=u'源销售单'),
        'okgj_sale_return_city':fields.related('sale_return_id', 'sale_order_id', 'okgj_city', type='char', string=u'收货城市', readonly=True, store=True),
        'sale_return_consignee':fields.related('sale_return_id', 'consignee', type='char', store=True, string=u'收货人'),
        'sale_return_tel':fields.related('sale_return_id', 'okgj_tel', type='char', store=True, string=u'联系电话'),
        'okgj_type':fields.selection([
            ('okgj_sale_in', u'销售退货入库单'),
            ('okgj_internal_in', u'其它入库单'),
            ], string=u'单据类型'),
        'internal_order_id':fields.many2one('okgj.order.picking.internal', u'源出入库申请单'),
        'create_date': fields.datetime(u'创建时间', readonly=True),
        'create_uid': fields.many2one('res.users', u'创建人', readonly=True),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True), 
    }

    ##一次收货后自动定时关闭采购订单，未出货的出库单
    def okgj_close_partial_picking_cron(self, cr, uid, context=None):
        if context is None:
            context = {}
        wf_service = netsvc.LocalService("workflow")
        to_close_ids = self.search(cr, uid, [('state', 'in', ['draft', 'auto', 'confirmed', 'assigned']), ('type', '=', 'in'), ('purchase_id', '!=', False)], context=context)
        for one in self.browse(cr, uid, to_close_ids, context=context):
            if one.backorder_id:
                wf_service.trg_validate(uid, "stock.picking", one.id, 'button_cancel', cr)
        #未出货的出库单
        to_close_return_ids = self.search(cr, uid, [('state', 'in', ['draft', 'auto', 'confirmed', 'assigned']), ('type', '=', 'out'), ('purchase_return_id', '!=', False)], context=context)
        for one in self.browse(cr, uid, to_close_return_ids, context=context):
            if one.backorder_id:
                wf_service.trg_validate(uid, "stock.picking", one.id, 'button_cancel', cr)
okgj_stock_picking_in()

class okgj_stock_picking_out(osv.osv):
    _inherit = "stock.picking.out"
    _order = "create_date desc"
    _columns = {
        'warehouse_id':fields.many2one('stock.warehouse', string=u'物流中心', readonly=True),
        'okgj_type':fields.selection([
            ('okgj_purchase_out', u'采购退货出库单'),
            ('okgj_sale_out', u'销售退货出库单'),
            ('okgj_internal_out', u'其它出库单'),
            ], string=u'单据类型'),
        'internal_order_id':fields.many2one('okgj.order.picking.internal', u'源出入库申请单'),
        'collect_state':fields.selection([('not', 'NOT'), ('yes', 'YES')], 'Collect Print State'),
        'print_state':fields.selection([('not', 'NOT'), ('yes', 'YES')], 'Print State'),
        'purchase_return_id':fields.many2one('okgj.purchase.return', u'源退货单'),
        'sale_return_id':fields.many2one('okgj.sale.return', u'源销售单'),
        'sale_return_sale':fields.related('sale_return_id', 'sale_order_id', type='many2one', relation='sale.order', store=True, string=u'源销售单'),
        'okgj_sale_return_city':fields.related('sale_return_id', 'sale_order_id', 'okgj_city', type='char', string=u'收货城市', readonly=True, store=True),
        'sale_return_consignee':fields.related('sale_return_id', 'consignee', type='char', store=True, string=u'收货人'),
        'sale_return_tel':fields.related('sale_return_id', 'okgj_tel', type='char', store=True, string=u'联系电话'),
        'pay_id':fields.related('sale_id', 'pay_name', type='char', string=u'支付方式', readonly=True),
        'send_time':fields.related('sale_id', 'send_time', type='char', string=u'要求送货时间', readonly=True, store=True),
        'inv_payee':fields.related('sale_id', 'inv_payee', type='text', string=u'发票抬头', readonly=True),
        'inv_content':fields.related('sale_id', 'inv_content', type='text', string=u'发票内容', readonly=True),
        'inv_amount':fields.related('sale_id', 'inv_amount', type='float', string=u'发票金额', readonly=True),
        'okgj_city':fields.related('sale_id', 'okgj_city', type='char', string=u'收货城市', readonly=True),
        'region_name':fields.related('sale_id', 'region_name', type='char', string=u'收货区域', readonly=True),
        'okgj_address':fields.related('sale_id', 'okgj_address', type='char', string=u'收货地址', readonly=True),
        'consignee':fields.related('sale_id', 'consignee', type='char', string=u'收货人', readonly=True,),
        'create_date': fields.datetime(u'创建时间', readonly=True),
        'create_uid': fields.many2one('res.users', u'创建人', readonly=True),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True), 
        
    }
    _defaults = {
        'collect_state': lambda *args: 'not',
        'print_state': lambda *args: 'not',
    }
okgj_stock_picking_out()

#理货上架，添加货位字段
class okgj_stock_move(osv.osv):
    _inherit = "stock.move"

    def _action_explode(self, cr, uid, move, context=None):
        """ Explodes pickings.
        @param move: Stock moves
        @return: True
        """
        bom_obj = self.pool.get('mrp.bom')
        move_obj = self.pool.get('stock.move')
        procurement_obj = self.pool.get('procurement.order')
        product_obj = self.pool.get('product.product')
        wf_service = netsvc.LocalService("workflow")
        processed_ids = [move.id]
        if move.product_id.supply_method == 'produce':
            bis = bom_obj.search(cr, uid, [
                ('product_id','=',move.product_id.id),
                ('bom_id','=',False),
                ('type','=','phantom')])
            if bis:
                factor = move.product_qty
                bom_point = bom_obj.browse(cr, uid, bis[0], context=context)
                res = bom_obj._bom_explode(cr, uid, bom_point, factor, [])
                state = 'confirmed'
                if move.state == 'assigned':
                    state = 'assigned'
                for line in res[0]: 
                    valdef = {
                        'picking_id': move.picking_id.id,
                        'product_id': line['product_id'],
                        'price_unit': product_obj.read(cr, uid, line['product_id'], ['standard_price'], context=context)['standard_price'],
                        'product_uom': line['product_uom'],
                        'product_qty': line['product_qty'],
                        'product_uos': line['product_uos'],
                        'product_uos_qty': line['product_uos_qty'],
                        'move_dest_id': move.id,
                        'state': state,
                        'name': line['name'],
                        'move_history_ids': [(6,0,[move.id])],
                        'move_history_ids2': [(6,0,[])],
                        'procurements': [],
                    }
                    mid = move_obj.copy(cr, uid, move.id, default=valdef)
                    #查找
                    more_ids = move_obj.search(cr, uid, [('picking_id','=',move.picking_id.id), ('product_id', '=', line['product_id'])], context=context)
                    processed_ids.extend(more_ids)
                    prodobj = product_obj.browse(cr, uid, line['product_id'], context=context)
                    #循环
                    for one_mov_id in more_ids:
                        proc_id = procurement_obj.create(cr, uid, {
                            'name': (move.picking_id.origin or ''),
                            'origin': (move.picking_id.origin or ''),
                            'date_planned': move.date,
                            'product_id': line['product_id'],
                            'product_qty': line['product_qty'],
                            'product_uom': line['product_uom'],
                            'product_uos_qty': line['product_uos'] and line['product_uos_qty'] or False,
                            'product_uos':  line['product_uos'],
                            'location_id': move.location_id.id,
                            ##支持组合品预售功能
                            ## 'procure_method': prodobj.procure_method, 
                            'procure_method': (move.procurements and move.procurements[0].procure_method) or prodobj.procure_method,
                            'need_purchase':(move.procurements and move.procurements[0].need_purchase),
                            'move_id': one_mov_id,
                        })
                        wf_service.trg_validate(uid, 'procurement.order', proc_id, 'button_confirm', cr)
                move_obj.write(cr, uid, [move.id], {
                    'location_dest_id': move.location_id.id, # dummy move for the kit
                    'auto_validate': True,
                    'picking_id': False,
                    'state': 'confirmed'
                })
                for m in procurement_obj.search(cr, uid, [('move_id','=',move.id)], context):
                    wf_service.trg_validate(uid, 'procurement.order', m, 'button_confirm', cr)
                    wf_service.trg_validate(uid, 'procurement.order', m, 'button_wait_done', cr)
        return processed_ids
    
    #重载以实现更多批次检验
    def _check_tracking(self, cr, uid, ids, context=None):
        """ Checks if serial number is assigned to stock move or not.
        @return: True or False
        """
        for move in self.browse(cr, uid, ids, context=context):
            if not move.prodlot_id and \
                   (move.state == 'done' and \
                    ( \
                        (move.product_id.track_production and move.location_id.usage == 'production') or \
                        (move.product_id.track_production and move.location_dest_id.usage == 'production') or \
                        (move.product_id.track_incoming and move.location_id.usage == 'supplier') or \
                        (move.product_id.track_outgoing and move.location_dest_id.usage == 'customer') or \
                        (move.product_id.track_incoming and move.location_id.usage == 'customer') or \
                        (move.product_id.track_outgoing and move.location_dest_id.usage == 'supplier') or \
                        (move.product_id.track_incoming and move.location_id.usage == 'inventory') \
                        )):
                 #采购退货出库
                 #销售退货入库
                return False
        return True

    _constraints = [
        (_check_tracking,
         'You must assign a serial number for this product.',
         ['prodlot_id'])]

    def _get_pick_rack(self, cr, uid, ids, field_names, arg, context=None):
        """ Read the 'rack' functional fields. """
        res = {}
        for one_move in self.browse(cr, uid, ids, context=context):
            picking = one_move.picking_id or False
            if not picking:
                res[one_move.id] = False
                continue
            warehouse_id = False
            #采购单
            purchase = picking.purchase_id  or False
            if purchase:
                warehouse_id = purchase.warehouse_id.id
            #销售单
            sale = picking.sale_id  or False
            if sale:
                warehouse_id = sale.shop_id.warehouse_id.id
            #采购退货单
            purchase_return = picking.purchase_return_id  or False
            if purchase_return:
                warehouse_id = purchase_return.warehouse_id.id
            #销售退货单
            sale_return = picking.sale_return_id  or False
            if sale_return:
                warehouse_id = sale_return.warehouse_id.id
            #内部调拨与其它出入库
            internal_return = picking.internal_order_id  or False
            if internal_return:
                warehouse_id = internal_return.warehouse_id.id
            if not warehouse_id:
                res[one_move.id] = False
                continue
            pick_rack_data = one_move.product_id.product_pick_rack_ids
            has_rack = False
            for one_rack in pick_rack_data:
                if one_rack.warehouse_id.id == warehouse_id:
                    has_rack = True
                    res[one_move.id] = one_rack.id
                    break
            if not has_rack:
                res[one_move.id] = False
        return res

    ## def _set_pick_rack(self, cr, uid, id, pick_rack_id, value, arg, context=None):
    ##     pass
    ##     """ Write the 'rack' functional fields. """
    ##     assert pick_rack_id == 'pick_rack_id'
    ##     warehouse_obj = self.pool.get('stock.warehouse')
    ##     users_obj = self.pool.get('res.users')
    ##     product_obj = self.pool.get('product.product')

    ##     picking = one_move.picking_id or False
    ##     if not picking:
    ##         warehouse_id = False
    ##     #采购单
    ##     purchase = picking.purchase_id  or False
    ##     if purchase:
    ##         warehouse_id = purchase.warehouse_id.id
    ##     #销售单
    ##     sale = picking.sale_id  or False
    ##     if sale:
    ##         warehouse_id = sale.warehouse_id.id
    ##     #采购退货单
    ##     purchase_return = picking.purchase_return_id  or False
    ##     if purchase_return:
    ##         warehouse_id = purchase_return.warehouse_id.id
    ##     #销售退货入库单
    ##     sale_return_in = picking.sale_return_in_id  or False
    ##     if sale_return_in:
    ##         warehouse_id = sale_return_in.warehouse_id.id
    ##     #销售退货出库单
    ##     sale_return_out = picking.sale_return_out_id  or False
    ##     if sale_return_out:
    ##         warehouse_id = sale_return_out.warehouse_id.id
    ##     if not warehouse_id:
    ##         res[one_move.id] == False
    ##         continue
    ##     rack_obj = self.pool.get('okgj.product.rack')
    ##     rack_data = rack_obj.browse(cr, uid, value, context=context)
    ##     if rack_data.warehouse_id.id = warehouse_id:

    ##         product_data = product_obj.read(cr, uid, product_id, ['product_pick_rack_ids'], context=context)
    ##     product_pick_rack_ids = product_data['product_pick_rack_ids']
    ##     if not product_pick_rack_ids:
    ##         product_obj.write(cr, uid, product_id, {'product_pick_rack_ids':[(4, pick_rack_id)]}, context=context)
    ##     else:
    ##         change_state = True
    ##         for one_rack in rack_obj.browse(cr, uid, product_pick_rack_ids, context):
    ##             if one_rack.warehouse_id.id == warehouse_id[0]:
    ##                 product_obj.write(cr, uid, product_id, {'product_pick_rack_ids':[(3, one_rack.id)]}, context=context)
    ##                 product_obj.write(cr, uid, product_id, {'product_pick_rack_ids':[(4, pick_rack_id)]}, context=context)
    ##                 change_state = False
    ##                 break
    ##         if change_state:
    ##             product_obj.write(cr, uid, product_id, {'product_pick_rack_ids':[(4, pick_rack_id)]}, context=context)
    ##     return True

    def _get_store_rack(self, cr, uid, ids, field_names, arg, context=None):
        """ Read the 'rack' functional fields. """
        res ={}
        for one_move in self.browse(cr, uid, ids, context=context):
            picking = one_move.picking_id or False
            if not picking:
                res[one_move.id] = False
                continue
            warehouse_id = False
            #采购单
            purchase = picking.purchase_id  or False
            if purchase:
                warehouse_id = purchase.warehouse_id.id
            #销售单
            sale = picking.sale_id  or False
            if sale:
                warehouse_id = sale.shop_id.warehouse_id.id
            #采购退货单
            purchase_return = picking.purchase_return_id  or False
            if purchase_return:
                warehouse_id = purchase_return.warehouse_id.id
            #销售退货入库单
            sale_return = picking.sale_return_id  or False
            if sale_return:
                warehouse_id = sale_return.warehouse_id.id
            #内部调拨与其它出入库
            internal_return = picking.internal_order_id  or False
            if internal_return:
                warehouse_id = internal_return.warehouse_id.id
            if not warehouse_id:
                res[one_move.id] = False
                continue
            store_rack_data = one_move.product_id.product_store_rack_ids
            has_rack = False
            for one_rack in store_rack_data:
                if one_rack.warehouse_id.id == warehouse_id:
                    has_rack = True
                    res[one_move.id] = one_rack.id
                    break
            if not has_rack:
                res[one_move.id] = False
        return res

    _columns = {
        'pick_rack_id': fields.function(_get_pick_rack, type='many2one', relation='okgj.product.rack', string=u'拣货货位'),
        'store_rack_id': fields.function(_get_store_rack, type='many2one', relation='okgj.product.rack', string=u'存货货位'),
        'variant':fields.related('product_id', 'variants', type='char', string=u'规格', readonly=True),
        'purchase_return_line_id': fields.many2one('okgj.purchase.return.line', 'Purchase Return Order Line', ondelete='set null', select=True, readonly=True),
        'sale_return_old_line_id': fields.many2one('okgj.sale.return.old.line', 'Sales Return Order OLD Line', ondelete='set null', select=True, readonly=True),
        'sale_return_new_line_id': fields.many2one('okgj.sale.return.new.line', 'Sales Return Order NEW Line', ondelete='set null', select=True, readonly=True),
        'order_internal_line_id': fields.many2one('okgj.order.picking.internal.line', 'Order Internal Line', ondelete='set null', select=True, readonly=True),
        'okgj_purchase_note':fields.related('purchase_line_id', 'okgj_note', type='char', string=u'采购备注', store=True, readonly=True),
    }

    def create(self, cr, uid, vals, context=None):
        #先创建，再拆分？
        mov_id = super(okgj_stock_move,self).create(cr, uid, vals, context=context)
        if (not vals.get('prodlot_id', False) and vals.get('sale_line_id', False)) or (not vals.get('prodlot_id', False) and vals.get('sale_return_new_line_id', False)):
            warehouse_obj = self.pool.get('stock.warehouse')
            product_obj = self.pool.get('product.product')
            mov_obj = self.pool.get('stock.move')
            warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)
            warehouse_data = warehouse_obj.browse(cr, uid, warehouse_ids, context=context)
            lot_stock_ids={}
            for one_warehouse in warehouse_data:
                lot_stock_ids[one_warehouse.lot_stock_id.id] = one_warehouse.id
            location_id = vals.get('location_id')
            if location_id in lot_stock_ids.keys():
                product_id = vals.get('product_id')
                product_qty = vals.get('product_qty')
                warehouse_id = lot_stock_ids[location_id]
                prodlot_dict = product_obj.get_out_lot(cr, uid, product_id, product_qty, warehouse_id, context=None)
                if prodlot_dict:                #先处理不足数量
                    all_lot_qty = 0
                    for one_lot_qty in [prodlot_dict[i] for i in prodlot_dict]:
                        all_lot_qty += one_lot_qty
                    if product_qty > all_lot_qty:
                        defaults = None
                        new_vals = mov_obj.copy_data(cr, uid, mov_id, defaults, context=context)
                        new_vals.update({'product_uos_qty':False, 'prodlot_id':False, 'product_qty':(product_qty-all_lot_qty)})
                        #UOS复制有无BUG？如何转换?
                        super(okgj_stock_move,self).create(cr, uid, new_vals, context=context)
                    new_state = False
                    for one_lot in prodlot_dict:
                        if new_state:
                            defaults = None
                            new_vals = mov_obj.copy_data(cr, uid, mov_id, defaults, context=None)
                            if prodlot_dict[one_lot] != 0:
                                new_vals.update({'product_uos_qty':False, 'prodlot_id':one_lot, 'product_qty':prodlot_dict[one_lot]})
                                mov_obj.create(cr, uid, new_vals, context=context)
                                #UOS复制有无BUG？如何转换?
                                #super(okgj_stock_move,self).create(cr, uid, new_vals, context=context)
                        else:
                            mov_obj.write(cr, uid, mov_id, {'prodlot_id':one_lot, 'product_qty':prodlot_dict[one_lot]}, context=context)
                            new_state = True
        return mov_id


    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial pickings and moves done.
        @param partial_datas: Dictionary containing details of partial picking
                          like partner_id, delivery_date, delivery
                          moves with product_id, product_qty, uom
        """
        res = {}
        picking_obj = self.pool.get('stock.picking')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        #增加以便取多物流中心成本数据
        warehouse_sprice_obj = self.pool.get("okgj.warehouse.sprice")
        wf_service = netsvc.LocalService("workflow")

        if context is None:
            context = {}

        complete, too_many, too_few = [], [], []
        move_product_qty = {}
        prodlot_ids = {}
        for move in self.browse(cr, uid, ids, context=context):
            if move.state in ('done', 'cancel'):
                continue
            partial_data = partial_datas.get('move%s'%(move.id), False)
            assert partial_data, _('Missing partial picking data for move #%s.') % (move.id)
            product_qty = partial_data.get('product_qty',0.0)
            move_product_qty[move.id] = product_qty
            product_uom = partial_data.get('product_uom',False)
            product_price = partial_data.get('product_price',0.0)
            product_currency = partial_data.get('product_currency',False)
            prodlot_ids[move.id] = partial_data.get('prodlot_id')
            if move.product_qty == product_qty:
                complete.append(move)
            elif move.product_qty > product_qty:
                too_few.append(move)
            else:
                too_many.append(move)

            # Average price computation
            if (move.picking_id.type == 'in') and (move.product_id.cost_method == 'average'):
                ##位置不传入
                context.update({'shop':False,'warehouse':False, 'location':False})
                product = product_obj.browse(cr, uid, move.product_id.id, context=context)
                move_currency_id = move.company_id.currency_id.id
                context['currency_id'] = move_currency_id
                qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)


                if qty > 0:
                    new_price = currency_obj.compute(cr, uid, product_currency,
                            move_currency_id, product_price)
                    new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                            product.uom_id.id)
                    if product.qty_available <= 0:
                        new_std_price = new_price
                    else:
                        # Get the standard price
                        amount_unit = product.price_get('standard_price', context=context)[product.id]
                        new_std_price = ((amount_unit * product.qty_available)\
                            + (new_price * qty))/(product.qty_available + qty)

                    product_obj.write(cr, uid, [product.id],{'standard_price': new_std_price})

                    # Record the values that were chosen in the wizard, so they can be
                    # used for inventory valuation if real-time valuation is enabled.
                    self.write(cr, uid, [move.id],
                                {'price_unit': product_price,
                                 'price_currency_id': product_currency,
                                })
                    ##更改多物流中心的成本价
                    warehouse_id = move.picking_id.warehouse_id.id
                    warehouse_context = copy.deepcopy(context)
                    warehouse_context.update({'warehouse':warehouse_id})
                    warehouse_product_data = product_obj.browse(cr, uid, product.id, context=warehouse_context)
                    #获取是否有该物流中心成本数据
                    warehouse_sprice_line_id = warehouse_sprice_obj.search(cr, uid, [
                        ('warehouse_id', '=', warehouse_id),
                        ('product_id', '=', product.id)
                        ], context=context)
                    if warehouse_sprice_line_id:
                        old_warehouse_sprice = warehouse_sprice_obj.browse(cr, uid, warehouse_sprice_line_id[0], context=warehouse_context).standard_price
                    else:
                        old_warehouse_sprice = 0
                    if warehouse_product_data.qty_available <=0:
                        new_warehouse_std_price = new_price
                    else:
                        new_warehouse_std_price = ((old_warehouse_sprice * warehouse_product_data.qty_available)\
                                                   + (new_price * qty))/(warehouse_product_data.qty_available + qty)
                    if warehouse_sprice_line_id:
                        warehouse_sprice_obj.write(cr, uid, warehouse_sprice_line_id[0], {'standard_price':new_warehouse_std_price}, context=warehouse_context)
                    else:
                        warehouse_sprice_obj.create(cr, uid, {
                            'product_id':product.id,
                            'standard_price':new_warehouse_std_price,
                            'warehouse_id':warehouse_id
                        }, context=warehouse_context)
                    #Added by ouke 1 above

        for move in too_few:
            product_qty = move_product_qty[move.id]
            if product_qty != 0:
                defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty,
                            'picking_id' : move.picking_id.id,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': move.price_unit,
                            }
                prodlot_id = prodlot_ids[move.id]
                if prodlot_id:
                    defaults.update(prodlot_id=prodlot_id)
                new_move = self.copy(cr, uid, move.id, defaults)
                complete.append(self.browse(cr, uid, new_move))
            self.write(cr, uid, [move.id],
                    {
                        'product_qty': move.product_qty - product_qty,
                        'product_uos_qty': move.product_qty - product_qty,
                        'prodlot_id': False,
                        'tracking_id': False,
                    })


        for move in too_many:
            self.write(cr, uid, [move.id],
                    {
                        'product_qty': move.product_qty,
                        'product_uos_qty': move.product_qty,
                    })
            complete.append(move)

        for move in complete:
            if prodlot_ids.get(move.id):
                self.write(cr, uid, [move.id],{'prodlot_id': prodlot_ids.get(move.id)})
            self.action_done(cr, uid, [move.id], context=context)
            if  move.picking_id.id :
                # TOCHECK : Done picking if all moves are done
                cr.execute("""
                    SELECT move.id FROM stock_picking pick
                    RIGHT JOIN stock_move move ON move.picking_id = pick.id AND move.state = %s
                    WHERE pick.id = %s""",
                            ('done', move.picking_id.id))
                res = cr.fetchall()
                if len(res) == len(move.picking_id.move_lines):
                    picking_obj.action_move(cr, uid, [move.picking_id.id])
                    wf_service.trg_validate(uid, 'stock.picking', move.picking_id.id, 'button_done', cr)

        return [move.id for move in complete]


okgj_stock_move()


# 手机收货
class okgj_stock_in_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"
    
    def stock_in_do_partial(self, cr, uid, ids, context=None):
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
    
    def get_move_line_data(self, cr, uid, value=None, context=None):
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
    
    def do_parse_datas(self, cr, uid, datas=None, context=None):
        print datas,'datas'
        process_info = {
                        '0':u'数据不能为空',
                        '1':u'1', #数据处理成功
                        '2':u'收货单号不存在,请确认!',
                        '3':u'数据处理失败,请检查相关数据信息  或网络连接!',
                        '5':u'数据元素长度错误!', 
                        '6':u'数据格式错误,数据格式必须为:[{"picking_id":'',"datas":[{"product_id":[], "stockin_qty":0, "product_lot_id":''}] }]',
                        '7':u'ERP的采购收货单里,商品%s有重复.',
                        '8':u'商品编码不能为空',
                        '9':u'商品%s:批次号格式错误,批次号格式为6位年月日',
                        '10':u'输入有误:收货单明细里没有商品%s!',
                        '11':u'收货单号 %s,请确认!',
                        '12':u'商品%s:批次号不能为空!'}
        picking_state_dict ={'assigned':u'待接收','done':u'已接收','cancel':u'已取消'}
        if context is None: context = {}
        datas_dict = None
        picking_obj = self.pool.get('stock.picking.in')
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
                move_lines = self.get_move_line_data(cr, uid, value=value)
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
                flg = self.stock_in_do_partial(cr, uid, [partial_picking_id])
            except:
                return process_info['3']
            if flg:
                return process_info['1']
            else:
                return process_info['3']
