# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

## 打单
class okgj_multi_order_print_log(osv.osv):
    _inherit = "okgj.multi.order.print"

    def create(self, cr, uid, vals, context=None):
        new_multi_id = super(okgj_multi_order_print_log,self).create(cr, uid, vals, context=context)
        log_message = u"""<div><b>订单处理</b>:  ===> 已打单，拣货单号： """ + unicode(vals.get('name'))
        picking_ids = vals.get('picking_ids')
        if picking_ids:
            picking_data = self.pool.get('stock.picking.out').browse(cr, uid, picking_ids[0][2], context=context)
            sale_obj = self.pool.get('sale.order')
            for one_pick in picking_data:
                sale_order_id = one_pick.sale_id and one_pick.sale_id.id or False
                if sale_order_id:
                    sale_obj.message_post(cr, uid, sale_order_id, log_message, context=context)
        return new_multi_id

## 装车
class okgj_logistics_log(osv.osv):
    _inherit = "okgj.logistics"

    def action_start(self, cr, uid, ids, context=None):
        super(okgj_logistics_log,self).action_start(cr, uid, ids, context=context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        sale_obj = self.pool.get('sale.order')
        for one_logistics in self.browse(cr, uid, ids, context=context):
            logistics_name = one_logistics.name
            logistics_type = one_logistics.type
            car_driver = one_logistics.car_id.driver
            car_phone = one_logistics.car_id.driver_phone
            shop_name = one_logistics.dest_shop and one_logistics.dest_shop.name or False
            for one_line in one_logistics.line_ids:
                sale_order_id = (one_line.picking_id and
                                 one_line.picking_id.sale_id and
                                 one_line.picking_id.sale_id.id or False)
                sale_return_orgin_order_id = (one_line.sale_return_id and
                                 one_line.sale_return_id.sale_order_id and
                                 one_line.sale_return_id.sale_order_id.id or False)
                if sale_order_id:
                    if logistics_type == 'local':
                        log_message = u"""<div><b>订单处理</b>:  ===> 已装车,将发送至客户，装车单号：""" + unicode(logistics_name) + u", 司机姓名:" + unicode(car_driver) + u"电话" +  unicode(car_phone)
                    else:
                        log_message = u"""<div><b>订单处理</b>:  ===> 已装车,将发送至分站:""" + unicode(shop_name) + u" 装车单号: " + unicode(logistics_name) + u", 司机姓名:" + unicode(car_driver) + u"电话" +  unicode(car_phone)
                    sale_obj.message_post(cr, uid, sale_order_id, log_message, context=context)
                if sale_return_orgin_order_id:
                    if logistics_type == 'local':
                        log_message = u"""<div><b>退换货单处理</b>:  ===> 已装车,将发送至客户，装车单号：""" + unicode(logistics_name)  + u", 司机姓名:" + unicode(car_driver) + u"电话" +  unicode(car_phone)
                    else:
                        log_message = u"""<div><b>退换货单处理</b>:  ===> 已装车,将发送至分站:""" + unicode(shop_name) + u" 装车单号: " + unicode(logistics_name)  + u", 司机姓名:" + unicode(car_driver) + u"电话" +  unicode(car_phone)
                    sale_obj.message_post(cr, uid, sale_return_orgin_order_id, log_message, context=context)
        return True

## 送达与未送达
class okgj_logistics_line_log(osv.osv):
    _inherit = "okgj.logistics.line"

    def write(self, cr, uid, ids, vals, context=None):
        super(okgj_logistics_line_log, self).write(cr, uid, ids, vals, context=context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        sale_obj = self.pool.get('sale.order')
        line = self.browse(cr, uid, ids[0], context=context)
        logistics_name = line.logistics_id.name
        if line.sale_return_id :
            sale_return_orgin_order_id = line.sale_return_id and \
                                         line.sale_return_id.sale_order_id and \
                                         line.sale_return_id.sale_order_id.id
            log_message = ''
            if (vals.get('state') == 'cancel'):
                log_cause = vals.get('cause', u'无')
                log_message = u"""<div><b>退换货单处理</b>:  ===> 未送达,原因:""" + unicode(log_cause)  + u" 装车单号: " + unicode(logistics_name)
            elif (vals.get('state') == 'done'):
                log_message = u"""<div><b>退换货单处理</b>:  ===> 已送达, """ + u" 装车单号: " + unicode(logistics_name)
            elif (vals.get('state') == 'todo'):
                log_message = u"""<div><b>退换货单处理</b>:  ===> 待送, """ + u" 装车单号: " + unicode(logistics_name)
            if log_message:    
                sale_obj.message_post(cr, uid, sale_return_orgin_order_id, log_message, context=context)
            if (vals.get('money_state') == 'done'):
                money_log_message = u"""<div><b>退换货单处理</b>:  ===> 已结款""" + u" 装车单号: " + unicode(logistics_name)
                sale_obj.message_post(cr, uid, sale_return_orgin_order_id, money_log_message, context=context)
        if line.picking_id:
            sale_order_id = line.picking_id and \
                            line.picking_id.sale_id and \
                            line.picking_id.sale_id.id or False
            log_message = ''
            if (vals.get('state') == 'cancel'):
                log_cause = vals.get('cause', u'无')
                log_message = u"""<div><b>订单处理</b>:  ===> 未送达,原因:""" + unicode(log_cause) + u" 装车单号: " + unicode(logistics_name)
            elif (vals.get('state') == 'done'):
                log_message = u"""<div><b>订单处理</b>:  ===> 已送达,""" + u" 装车单号: " + unicode(logistics_name)
            elif (vals.get('state') == 'done'):
                log_message = u"""<div><b>订单处理</b>:  ===> 待送,""" + u" 装车单号: " + unicode(logistics_name)
            if log_message:
                sale_obj.message_post(cr, uid, sale_order_id, log_message, context=context)
            if (vals.get('money_state') == 'done'):
                money_log_message = u"""<div><b>订单处理</b>:  ===> 已结款, """ + u" 装车单号: " + unicode(logistics_name)
                sale_obj.message_post(cr, uid, sale_order_id, money_log_message, context=context)
        return True

## 退换货创建、复核
class okgj_sale_return_log(osv.osv):
    _inherit = "okgj.sale.return"

    def create(self, cr, uid, vals, context=None):
        new_return_id = super(okgj_sale_return_log,self).create(cr, uid, vals, context=context)
        log_message = u"""<div><b>退换货单</b>:  ===> 已创建，单号:""" + unicode(vals.get('name'))
        sale_order_id = vals.get('sale_order_id')
        if sale_order_id:
            self.pool.get('sale.order').message_post(cr, uid, sale_order_id, log_message, context=context)
        return new_return_id

    def action_validate(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        super(okgj_sale_return_log, self).action_validate(cr, uid, ids, context=context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        sale_obj = self.pool.get("sale.order")
        for one_order in self.browse(cr, uid, ids, context=context):
            sale_order_id = one_order.sale_order_id.id
            order_name = one_order.name
            log_message = u"""<div><b>退换货单</b>:  ===> 已审核,""" + u" 单号:" + unicode(order_name)
            sale_obj.message_post(cr, uid, sale_order_id, log_message, context=context)
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        super(okgj_sale_return_log, self).action_cancel(cr, uid, ids, context=context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        sale_obj = self.pool.get("sale.order")
        for one_order in self.browse(cr, uid, ids, context=context):
            sale_order_id = one_order.sale_order_id.id
            order_name = one_order.name
            log_message = u"""<div><b>退换货单</b>:  ===> 已取消, """ + u" 单号:" + unicode(order_name)
            sale_obj.message_post(cr, uid, sale_order_id, log_message, context=context)
        return True

    def write(self, cr, uid, ids, vals, context=None):
        super(okgj_sale_return_log, self).write(cr, uid, ids, vals, context=context)
        if vals.get('has_print') is True:
            if isinstance(ids, (int, long)):
                ids = [ids]
            sale_obj = self.pool.get('sale.order')
            for one_order in self.browse(cr, uid, ids, context=context):
                order_name = one_order.name
                sale_order_id = one_order.sale_order_id and one_order.sale_order_id.id or False
                if sale_order_id:
                    log_message = u"""<div><b>退换货单处理</b>:  ===> 已打单, """ + u" 单号:" + unicode(order_name)
                    sale_obj.message_post(cr, uid, sale_order_id, log_message, context=context)
        return True

class okgj_stock_picking_log(osv.osv):
    _inherit = "stock.picking"

    def write(self, cr, uid, ids, vals, context=None):
        super(okgj_stock_picking_log, self).write(cr, uid, ids, vals, context=context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        all_data = self.browse(cr, uid, ids, context=context)
        ## 订单复核
        if vals.get('verify_uid') and vals.get('verify_date'):
            log_message = u"""<div><b>订单处理</b>:  ===> 已复核"""
            sale_obj = self.pool.get('sale.order')
            for one_verify in all_data:
                sale_order_id = one_verify.sale_id and one_verify.sale_id.id or False
                if sale_order_id:
                    sale_obj.message_post(cr, uid, sale_order_id, log_message, context=context)
        if vals.get('state') == 'done':
            sale_obj = self.pool.get('sale.order')
            for one_pick in all_data:
                ## 换货商品出库
                if one_pick.okgj_type == 'okgj_sale_out': 
                    sale_order_id = one_pick.sale_return_id and one_pick.sale_return_id.sale_order_id and one_pick.sale_return_id.sale_order_id.id or False
                    return_order_name = one_pick.sale_return_id and one_pick.sale_return_id.sale_order_id and one_pick.sale_return_id.name or False
                    if sale_order_id and return_order_name:
                        log_message = u"""<div><b>退换货单处理</b>:  ===> 已出库, """ + u" 单号:" + unicode(return_order_name)
                        sale_obj.message_post(cr, uid, sale_order_id, log_message, context=context)
                ## 换货商品入库
                elif one_pick.okgj_type == 'okgj_sale_in':
                    sale_order_id = one_pick.sale_return_id and one_pick.sale_return_id.sale_order_id and one_pick.sale_return_id.sale_order_id.id or False
                    return_order_name = one_pick.sale_return_id and one_pick.sale_return_id.sale_order_id and one_pick.sale_return_id.name or False
                    if sale_order_id and return_order_name:
                        log_message = u"""<div><b>退换货单处理</b>:  ===> 已入库, """ + u" 单号:" + unicode(return_order_name)
                        sale_obj.message_post(cr, uid, sale_order_id, log_message, context=context)
        return True
