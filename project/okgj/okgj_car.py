﻿# -*- coding: utf-8 -*-

from osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import re
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

OKGJ_ORDER_TYPE=[
    ('erp', u'ERP'),
    ('okshop', u'商城'),
    ('okkg', u'快购'),
    ('okapp', u'手机终端'),
    ('okwd', u'微店'),
    ('oktg', u'团购'),#'商城后台'(管理员添加)
    ('offline', u'线下'),
    ('others', u'其它'),
]

#车辆信息登记
class okgj_logistics_car(osv.osv):
    _name = 'okgj.logistics.car'
    _description = 'Logistics Car'
    _columns = {
        'name':fields.char(u'编号', size=16, required=True),
        'car_code':fields.char(u'车牌号', size=32, required=True),
        'driver':fields.char(u'司机姓名', size=16, required=True),
        'driver_phone':fields.char(u'电话号码', size=16, required=True),
        'start_time': fields.date(u'合作日期'),
        'active': fields.boolean(u'启用'),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心',),
    }
    
    _defaults = {
        'active': lambda *a: True,
    }

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['car_code','driver'], context=context)
        res = []
        for record in reads:
            if record['car_code']:
                newname = record['car_code'] +' / '+ record['driver']
            else:
                newname = record['driver']
            res.append((record['id'], newname))
        return res

okgj_logistics_car()


class okgj_logistics(osv.osv):
    _name = "okgj.logistics"
    _description = 'Logistics'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
okgj_logistics()

class okgj_logistics_line_cause(osv.osv_memory):
    _name = "okgj.logistics.line.cause"
    _columns = {
        'cause':fields.text(u'原因', required=True),
    }

    def action_cancel(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        line_ids = context and context.get('active_ids', False) or False
        if not line_ids:
            raise osv.except_osv(_('Invalid Action!'), _('请先选择订单'))
        if_refuse = context and context.get('if_refuse', False)
        field_cause = if_refuse and 'refuse_cause' or 'cause'
        state = if_refuse and 'refuse' or 'cancel'
        cause = self.browse(cr, uid, ids[0], context=context).cause
        line_obj = self.pool.get('okgj.logistics.line')
        line_obj.write(cr, uid, line_ids[0], {
            field_cause:cause,
            'state':state,
            #'state':'cancel',
            #'cause':cause,
            'money_act':0,
            'pos_act':0,
            }, context=context)
        return {'type': 'ir.actions.act_window_close'}
    
okgj_logistics_line_cause()

class okgj_logistics_line_money(osv.osv_memory):
    _name = "okgj.logistics.line.money"
    _columns = {
        'order_id':fields.many2one('sale.order', u'订单', readonly=True),
        'money_act': fields.float(u'实收金额', digits_compute=dp.get_precision('Product Price')),
        'pos_act': fields.float(u'刷卡金额', digits_compute=dp.get_precision('Product Price')),
        'notes':fields.text(u'备注'),
    }

    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        if context is None:
            context = {}
        res = super(okgj_logistics_line_money, self).default_get(cr, uid, fields, context=context)
        logistics_line_ids = context and context.get('active_ids', False) or False
        if isinstance(logistics_line_ids, (int, long)):
            logistics_line_ids = [logistics_line_ids]
        form = self.pool.get('okgj.logistics.line').browse(cr, uid, logistics_line_ids[0], context=context)
        res.update({'order_id':form.sale_order_id.id, 'money_act':form.money_act, 'pos_act':form.pos_act, 'notes':form.notes}) 
        return res

    def action_money(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        line_ids = context and context.get('active_ids', False) or False
        if not line_ids:
            raise osv.except_osv(_('Invalid Action!'), _('请先选择发货单'))
        form = self.browse(cr, uid, ids[0], context=context)
        money_act = form.money_act
        pos_act = form.pos_act
        notes = form.notes
        line_obj = self.pool.get('okgj.logistics.line')
        line_obj.write(cr, uid, line_ids, {'money_act':money_act, 'pos_act':pos_act, 'notes':notes}, context=context)
        return {'type': 'ir.actions.act_window_close'}
    
okgj_logistics_line_money()

class okgj_logistics_line(osv.osv):

    def _get_pay_way(self, name):
        """ 依支付名称判断支付方式
        @param prop: 支付名称
        @return: 1:现金支付，2:POS刷卡，其它为0
        """
        ## 现有支付方式
        ## pay_id:pay_name
        ## 1:余额支付
        ## 3:货到付款 - POS刷卡
        ## 5:环迅网银支付
        ## 6:货到付款 - 现金支付
        ## 7:支付宝支付
        ## 8:快钱支付
        ## 9:快钱网银支付
        ## 10:环迅支付
        ## 11:手机网银支付
        ## 暂枚举而不用正则表达式处理
        if name == u'货到付款':
            return 2
        elif name == u'货到付款(现金支付)':
            return 1
        else:
            return 0

    def _get_line_no(self, cr, uid, ids, field_names, arg, context=None):
        """ 获取订单行号，效率以后有空更改
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        result = {}.fromkeys(ids, 0)
        line_no = 0
        for one_id in sorted(ids):
            line_no += 1
            result[one_id] = line_no
        return result

    def _get_order_info(self, cr, uid, ids, field_names, arg, context=None):
        if context is None:
            context = {}
        result = {}.fromkeys(ids, 0)
        for one_line in self.browse(cr, uid, ids, context=context):
            if one_line.picking_id.sale_id:
                so=one_line.picking_id.sale_id
                #pcs order diff other okgj_order_type
                if so.is_cps_order:
                    rebate=one_line.picking_id.move_lines[0].product_id.rebate
                    money_owned = one_line.picking_id.sale_id.goods_amount
                    rebate_amount = money_owned * rebate / 100
                else:
                    rebate=0.0
                    money_owned = one_line.picking_id.sale_id.order_amount
                    rebate_amount=0.0
                
                result[one_line.id] = {
                    'order_type':u'销售出库',
                    'sale_order_id':one_line.picking_id.sale_id.id or False,
                    'sale_okgj_city':one_line.picking_id.sale_id.okgj_city,
                    'sale_region_name':one_line.picking_id.sale_id.region_name,
                    'sale_consignee':one_line.picking_id.sale_id.consignee,
                    'sale_okgj_tel':one_line.picking_id.sale_id.okgj_tel,
                    'sale_okgj_address':one_line.picking_id.sale_id.okgj_address,
                    'sale_pay_id':one_line.picking_id.sale_id.pay_name,
                    'sale_date_order2':one_line.picking_id.sale_id.date_order2,
                    'sale_create_date':one_line.picking_id.sale_id.create_date,
                    'sale_best_time':one_line.picking_id.sale_id.send_time,
                    'sale_inv_payee':one_line.picking_id.sale_id.inv_payee,
                    'sale_inv_content':one_line.picking_id.sale_id.inv_content,
                    'sale_inv_amount':one_line.picking_id.sale_id.inv_amount,
                    'send_time_content':one_line.picking_id.sale_id.send_time_content,
                    'money_owned':money_owned,
                    'rebate': rebate,
                    'rebate_amount': rebate_amount,
                    'partner_id':so.partner_id.id,
                    }
            elif one_line.sale_return_id:
                result[one_line.id] = {
                    'order_type':u'退换货出入库',
                    'sale_order_id':one_line.sale_return_id.sale_order_id.id or False,
                    'sale_okgj_city': '', #one_line.picking_id.sale_return_id.okgj_city,
                    'sale_region_name':one_line.sale_return_id.region_name,
                    'sale_consignee':one_line.sale_return_id.consignee,
                    'sale_okgj_tel':one_line.sale_return_id.okgj_tel,
                    'sale_okgj_address':one_line.sale_return_id.address,
                    'sale_pay_id':False,
                    'sale_date_order2':False,
                    'sale_create_date':one_line.sale_return_id.create_date,
                    'sale_best_time':one_line.sale_return_id.best_time,
                    'sale_inv_payee':'',
                    'sale_inv_content':'',
                    'sale_inv_amount':'',
                    'send_time_content':one_line.sale_return_id.action_note,
                    'money_owned':one_line.sale_return_id.money_get,
                    #'rebate': rebate,
                    #'rebate_amount': rebate_amount,
                    'partner_id':one_line.sale_return_id.sale_order_id.partner_id.id,
                    }
            else:
                result[one_line.id] = {
                    'order_type':'',
                    'sale_order_id':'',
                    'sale_okgj_city':'',
                    'sale_region_name':'',
                    'sale_consignee':'',
                    'sale_okgj_tel':'',
                    'sale_okgj_address':'',
                    'sale_pay_id':'',
                    'sale_date_order2':'',
                    'sale_create_date':'',
                    'sale_best_time':'',
                    'sale_inv_payee':'',
                    'sale_inv_content':'',
                    'sale_inv_amount':'',
                    'send_time_content':'',
                    'money_owned':'',
                    'rebate': 0.0,
                    'rebate_amount': 0.0,
                    'partner_id':False,
                }
        return result

    def _get_diff(self, cr, uid, ids, field_names, arg, context=None):
        """ 获取差异额
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        result = {}.fromkeys(ids, 0.0)
        for one_line in self.browse(cr, uid, ids, context=context):
            result[one_line.id] = one_line.money_owned - one_line.money_act - one_line.pos_act - one_line.rebate_amount
        return result

    _name = "okgj.logistics.line"
    _rec_name = "create_date"
    _description = 'Logistics Line'
    _order = 'id'
    _columns = {
        'line_no': fields.function(_get_line_no, type='integer', string=u'行号'),
        'sale_order_id':fields.function(_get_order_info, type='many2one', relation='sale.order', string=u"订单", readonly=True, store=True, multi='get_order_info'),
        'order_type':fields.function(_get_order_info, type="char", string=u'类别', readonly=True, store=True, multi='get_order_info'),
        'picking_id':fields.many2one('stock.picking.out', u'出库单号'), #TODO:加入domain限制
        'sale_return_id':fields.many2one('okgj.sale.return', u'退换货单号'), #TODO:加入domain限制
        'sale_okgj_city':fields.function(_get_order_info, type="char", string=u'收货城市', readonly=True, store=True, multi='get_order_info'),
        'sale_region_name':fields.function(_get_order_info, type="char", string=u'区域', readonly=True, store=True, multi='get_order_info'),
        'sale_consignee':fields.function(_get_order_info, type="char", string=u'收货人', readonly=True, store=True, multi='get_order_info'),
        'sale_okgj_tel':fields.function(_get_order_info, type="char", string=u'联系电话', readonly=True, store=True, multi='get_order_info'),
        'sale_okgj_address':fields.function(_get_order_info, type="char", string=u'收货地址', readonly=True, store=True, multi='get_order_info'),
        'sale_pay_id':fields.function(_get_order_info, type="char", string=u'付款方式', readonly=True, store=True, multi='get_order_info'),
        'sale_date_order2':fields.function(_get_order_info, type="datetime", string=u'商城下单时间', readonly=True, store=True, multi='get_order_info'),
        'sale_create_date':fields.function(_get_order_info, type="datetime", string=u'ERP创建时间', readonly=True, store=True, multi='get_order_info'),
        'sale_best_time':fields.function(_get_order_info, type="char", string=u'送货时间', readonly=True, store=True, multi='get_order_info'),

        #'collect_ids':fields.related('picking_id', 'collect_ids', type='one2many', relation='okgj.multi.order.print', string=u'拣货单号', readonly=True, store=True),
        'reg_operate_id':fields.related('picking_id', 'reg_id', 'operator_id', type='many2one', relation='res.users', string=u'拣货人', readonly=True, store=True),
        'reg_date':fields.related('picking_id', 'reg_date', type='datetime', string=u'拣货登记时间', readonly=True, store=True),
        'reg_verify_id':fields.related('picking_id', 'verify_uid', type='many2one', relation='res.users', string=u'复核人', readonly=True, store=True),
        'reg_verify_date':fields.related('picking_id', 'verify_date', type='datetime', string=u'复核时间', readonly=True, store=True),
        
        ## 'collect_create_uid':fields.related('picking_id', 'collect_ids', 'create_uid', type="many2many", string=u'打单人', readonly=True, store=True),
        ## 'collect_create_date':fields.related('picking_id', 'collect_ids', 'create_date', type="datetime", string=u'打单时间', readonly=True, store=True),
        'logistics_id':fields.many2one('okgj.logistics', u'装车单号'),
        'create_uid':fields.many2one('res.users', u'装车登记人', readonly=True),
        'create_date':fields.datetime(u'装车时间', readonly=True),        
        'logistics_car_name':fields.related('logistics_id', 'car_name', type="char", string=u'管家编号', readonly=True, store=True),
        'logistics_car_id':fields.related('logistics_id', 'car_id', type="many2one", relation="okgj.logistics.car", string=u"车辆", readonly=True, store=True),
        'logistics_car_tel':fields.related('logistics_id', 'car_id', 'driver_phone', type="char", string=u"司机电话", readonly=True, store=True),
        'logistics_car_name':fields.related('logistics_id', 'car_name', type="char", string=u'管家编号', readonly=True, store=True),
        'sale_inv_payee':fields.function(_get_order_info, type="char", string=u'发票抬头', readonly=True, store=True, multi='get_order_info'),
        'sale_inv_content':fields.function(_get_order_info, type="char", string=u'发票内容', readonly=True, store=True, multi='get_order_info'),
        'sale_inv_amount':fields.function(_get_order_info, type="float", string=u'发票金额', readonly=True, store=True, multi='get_order_info'),
        'send_time_content':fields.function(_get_order_info, type="char", string=u'送货备注', readonly=True, store=True, multi='get_order_info'),
        'money_owned':fields.function(_get_order_info, type="float", string=u'货到付款金额', readonly=True, store=True, multi='get_order_info'),
        'money_act': fields.float(u'现金', digits_compute=dp.get_precision('Product Price')),
        'pos_act': fields.float(u'POS', digits_compute=dp.get_precision('Product Price')),
        'money_diff': fields.function(_get_diff, type='float', string=u'差异'),
        'box':fields.related('picking_id', 'okgj_box', type="char", string=u'箱号', readonly=True),
        'container':fields.related('picking_id', 'okgj_container', type="text", string=u'外挂', readonly=True),
        'state':fields.selection([
            ('todo', u'待送'),
            ('cancel', u'未送达'),
            ('refuse', u'拒收'),
            ('done', u'已送达'),
        ], string=u'状态', readonly=True),
        'money_state':fields.selection([
            ('todo', u'待审'),
            ('done', u'已回款'),
        ], string=u'回款状态', readonly=True),
        'notes':fields.text(u'备注'),
        'cause':fields.text(u'未送达原因'),
        'refuse_cause':fields.text(u'拒收原因'),
        'okgj_pay_car':fields.boolean(u'需结款'),
        'three_side_picking':fields.char(u'第三方物流单号', size=64, readonly=True, states={'todo':[('readonly',False)]}),
        #'rebate':fields.float(u'返点%',digits_compute=dp.get_precision('Account')),
        'rebate':fields.function(_get_order_info, type="float", readonly=True, store=True, multi='get_order_info',string=u'返点%',digits_compute=dp.get_precision('Account')),
        'rebate_amount':fields.function(_get_order_info, type="float", readonly=True, store=True, multi='get_order_info',string=u'返点金额',digits_compute=dp.get_precision('Account')),
        'partner_id': fields.function(_get_order_info, type="many2one", relation='res.partner',  readonly=True, store=True, multi='get_order_info',string=u'客户',),
    }
    
    _defaults = {
        'state': lambda *a: 'todo',
        'money_state':lambda *a: 'todo',
        'okgj_pay_car': lambda *a: True,
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        new_id = super(okgj_logistics_line, self).create(cr, uid, vals, context)
        form = self.browse(cr, uid, new_id, context=context)
        if form.sale_return_id:
            money_owned = form.sale_return_id.money_get
            sale_pay_id = False
        else:
            money_owned = form.picking_id.sale_id.order_amount
            sale_pay_id = form.picking_id.sale_id.pay_name
      
        if money_owned:
            if sale_pay_id:
                if self._get_pay_way(sale_pay_id) == 1:
                    self.write(cr, uid, new_id, {'money_act':money_owned}, context=context)
                elif self._get_pay_way(sale_pay_id) == 2:
                    self.write(cr, uid, new_id, {'pos_act':money_owned}, context=context)
            else:
                self.write(cr, uid, new_id, {'money_act':money_owned}, context=context)
        return new_id

    #防止误操作
    def action_todo(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'state':'todo'}, context=context)

    def action_done(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'state':'done'}, context=context)

    def action_cancel_in_mobile(self, cr, uid, ids, cause='', context=None):
        if context is None:
            context = {}
        self.write(cr, uid, ids, {
            'state':'cancel',
            'cause':cause,
            'money_act':0,
            'pos_act':0,
            }, context=context)
        return True

okgj_logistics_line()

#装车
class okgj_logistics(osv.osv):
    


    def _get_done_line(self, cr, uid, ids, field_names, arg=None, context=None):
        if context is None:
            context = {}
        result = {}.fromkeys(ids, 0.0)
        for one in self.browse(cr, uid, ids, context=context):
            one_line_ids = []
            for one_line in one.line_ids:
                if one_line.state == 'done':
                    one_line_ids.append(one_line.id)
            result[one.id] = one_line_ids
        return result
    
    def _get_partner(self, cr, uid, ids, field_name, arg=None, context=None):
        """
        if one logistics related to multi-orders. maybe they order not one parter, so return None.
        """
        res = {}.fromkeys(ids, None)
        for one in self.browse(cr, uid, ids, context=context):
            if len(one.line_ids) == 1 and not one.is_sale_return:
                if one.line_ids[0].picking_id and one.line_ids[0].picking_id.sale_id and one.line_ids[0].picking_id.sale_id.partner_id:
                    res[one.id] = one.line_ids[0].picking_id.sale_id.partner_id.id
        return res
    
    def _get_okgj_order_type(self, cr, uid, ids, field_name, arg=None, context=None):
        """
        """
        res = {}.fromkeys(ids, '')
        for one in self.browse(cr, uid, ids, context=context):
            if len(one.line_ids) == 1 and not one.is_sale_return:
                if one.line_ids[0].picking_id and one.line_ids[0].picking_id.sale_id:
                    res[one.id] = one.line_ids[0].picking_id.sale_id.okgj_order_type
        return res
    
    def partner_id_recount(self, cr, uid, context=None):
        """
        This function is used to init the old record, 
        """
        ids = self.search(cr, uid, [], context=None)
        id_value = self._get_partner(cr, uid, ids, 'partner_id', context=context)

        for one_id in id_value:
            self.write(cr, uid, one_id, {'partner_id':id_value[one_id]} )
        return True

    _inherit = "okgj.logistics"
    _order ="create_date desc"
    _columns = {
        'type':fields.selection([
            ('local', u'本地物流'),
            ('route', u'干线物流'),
            ('three_side', u'第三方物流'),
        ], string=u'类别', readonly=True, states={'draft':[('readonly',False)]}, required=True),
        'is_sale_return':fields.boolean(u'退换货单'),
        'dest_shop':fields.many2one('sale.shop', u'商店', readonly=True, states={'draft':[('readonly',False)]}),
        'create_uid':fields.many2one('res.users', u'装车登记人', readonly=True),
        'create_date':fields.datetime(u'装车登记时间', readonly=True),
        'back_uid':fields.many2one('res.users', u'返程登记人', readonly=True),
        'back_date':fields.datetime(u'返程登记时间', readonly=True),
        'money_uid':fields.many2one('res.users', u'回款登记人', readonly=True),
        'money_date':fields.datetime(u'回款登记时间', readonly=True),
        'name': fields.char(u'装车单号', size=64, required=True, select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'car_id':fields.many2one('okgj.logistics.car', u'车辆', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'car_name':fields.related('car_id', 'name', type='char', string=u'管家编号', readonly=True, store=True),
        'okgj_tel':fields.related('car_id', 'driver_phone', type='char', string=u"联系电话", readonly=True),
        'picking':fields.char(u'单号', size=32, readonly=True, states={'draft':[('readonly',False)]}),
        'okgj_box':fields.text(u'箱号', help=u'物流箱号，每行一个', readonly=True, states={'draft':[('readonly',False)]}),
        'okgj_box_qty': fields.integer(u'箱数', readonly=True, states={'draft':[('readonly',False)]}),
        'okgj_box_return_qty': fields.integer(u'返回箱数', readonly=True, states={'start':[('readonly',False)]}),
        'state':fields.selection([
            ('draft', u'草稿'),
            ('start', u'已出发'),
            ('end', u'已返程'),
            ('done', u'完成'),
        ], string=u'状态', readonly=True),
        'start_miles':fields.float(u'出发里程', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True, states={'draft':[('readonly',False)]}),
        'end_miles':fields.float(u'返回里程', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True,  states={'start':[('readonly', False)]}),
        'line_ids':fields.one2many('okgj.logistics.line', 'logistics_id', u'明细行', readonly=True, states={'draft':[('readonly',False)],'end':[('readonly',False)]}, required=True),
        'line_done_ids':fields.function(_get_done_line, type='one2many', relation='okgj.logistics.line', string=u'已完成明细行', readonly=True),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心'),
        'three_side_picking':fields.char(u'第三方物流单号', size=64, readonly=True, states={'draft':[('readonly',False)]}),
        #'partner_id': fields.function(_get_partner,type='many2one', readonly=True, store=True, relation='res.partner',string=u'客户'),
        'okgj_order_type':fields.function(_get_okgj_order_type,type='selection',selection=OKGJ_ORDER_TYPE , readonly=True, store=True, string=u'来源'),
    }
    def _default_warehouse_id(self, cr, uid, context=None):
        if context is None: context = {}
        user_data = self.pool.get('res.users').browse(cr,uid, uid, context=context)
        warehouse_id = False
        for one_warehouse in user_data.warehouse_ids:
            warehouse_id = one_warehouse.id
            if warehouse_id:
                break
        return warehouse_id
    
    _defaults = {
        'warehouse_id': _default_warehouse_id,
        'state': lambda *a: 'draft',
        'type': lambda *a: 'local',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'okgj.logistics'),
    }

    def _check_repeat(self, cr, uid, ids, context=None):
        for one_order in self.browse(cr, uid, ids, context):
            picking_ids = []
            sale_return_ids = []
            for one_line in one_order.line_ids:
                if one_line.picking_id :
                    if one_line.picking_id.id not in picking_ids:
                        picking_ids.append(one_line.picking_id.id)
                    else:
                        return False
                
                if one_line.sale_return_id:
                    if one_line.sale_return_id.id not in sale_return_ids:
                        sale_return_ids.append(one_line.sale_return_id.id)
                    else:
                        return False
            return True
     
    _constraints = [
        (_check_repeat, '错误，有重复订单行.', ['line_ids']),
    ]   
    
    #写入箱数
    ## def create(self, cr, user, vals, context=None):
    ##     if vals.get('okgj_box', False):
    ##         vals.update({'okgj_box_qty' : len(re.split('\n', vals.get('okgj_box')))})
    ##     return super(okgj_logistics, self).create(cr, user, vals, context)

    #写入箱数
    ## def write(self, cr, uid, ids, vals, context=None):
    ##     if vals.get('okgj_box', False):
    ##         vals.update({'okgj_box_qty' : len(re.split('\n', vals.get('okgj_box')))})
    ##     return  super(okgj_logistics, self).write(cr, uid, ids, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'name': self.pool.get('ir.sequence').get(cr, uid, 'okgj.logistics'),
        })
        return super(okgj_logistics, self).copy(cr, uid, id, default, context=context)   

    def action_start_three(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        objs = self.read(cr, uid, ids, context=context)
        for obj in objs:
            line_ids = obj.get('line_ids',[])
            if len(line_ids) == 0:
                raise osv.except_osv(u'错误',u'无第三方装车明细')
            elif len(line_ids) > 1:
                #如果有多个第三方装车明细,需要拆分每一条明细为一条独立的装车单.
                #current_line = line_ids[0]
                #other_lines = line_ids[1:]
                count = 0
                for line in line_ids:
                    if count == 0:
                        new_obj_id = obj.get('id')
                    else:
                        new_obj_id = self.copy(cr, uid, obj.get('id'), default={'line_ids':[]}, context=context)
                    #改变每一个装车单状态
                    self.write(cr, uid, new_obj_id, {'state':'start'}, context=context)
                    #将每个明细的logistics_id更新为new_obj_id
                    for line_obj in self.pool.get('okgj.logistics.line').browse(cr, uid, [line], context=context):
                        line_obj.write({'logistics_id':new_obj_id})
                    
                    count += 1
            else:# 仅一条
                self.write(cr, uid, ids, {'state':'start'}, context=context)
                
        return True    

    def action_start(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state':'start'}, context=context)
        return True

    def action_end(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for one in self.browse(cr, uid, ids, context=context):
            for one_picking_line in one.line_ids:
                if one_picking_line.state == 'todo':
                    if one_picking_line.sale_return_id:
                        raise osv.except_osv(_('Invalid Action!'), _('请先确认 %s 是否送达') % (one_picking_line.sale_return_id.name))                
                    else:
                        raise osv.except_osv(_('Invalid Action!'), _('请先确认 %s 是否送达') % (one_picking_line.picking_id.sale_id.name))                
        self.write(cr, uid, ids, {
            'state':'end',
            'back_uid':uid,
            'back_date':time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }, context=context)
        return True

    def action_done(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        line_obj = self.pool.get('okgj.logistics.line')
        for one in self.browse(cr, uid, ids, context=context):
            for one_picking_line in one.line_done_ids:
                if one_picking_line.money_state == 'todo':
                    line_obj.write(cr, uid, one_picking_line.id, {'money_state':'done'}, context=context)
        self.write(cr, uid, ids, {
            'state':'done',
            'money_uid':uid,
            'money_date':time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            }, context=context)
        return True

    def action_route_done(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state':'done'}, context=context)
        return True
    
    def _check_sale_return(self, cr, uid, name, context=None):
        sale_return_obj = self.pool.get("okgj.sale.return")
        message = ''
        sale_return_ids = sale_return_obj.search(cr, uid, [('name', '=', name), ('state', 'in', ['confirmed', 'validate'])], context=context)
        if not sale_return_ids:
            message = u'未找到匹配的退换货单'
            return (sale_return_ids, message)
        if isinstance(sale_return_ids, list):
            if len(sale_return_ids) != 1:
                message = u'找到多个匹配的退换货单, 无法识别'
                return (sale_return_ids, message)
        return (sale_return_ids, message)

    def _check_picking(self, cr, uid, name, context=None):
        message = ''
        #从全部出入库单中查找
        picking_obj = self.pool.get('stock.picking.out')
        picking_ids = picking_obj.search(cr, uid, [('name', '=', name), ('state', '=', 'done')], context=context)
        if not picking_ids:
            message =  u'未找到匹配的出入库单'
            return (picking_ids, message)
        if isinstance(picking_ids, list):
            if len(picking_ids) != 1:
                message = u'找到多个匹配的送货单, 无法识别'
                return (picking_ids, message)
        sale_data = picking_obj.browse(cr, uid, picking_ids[0], context=context).sale_id
        if sale_data and sale_data.okgj_shop_cancel:
            message = u'该订单在拣货复核后已由商城取消，请确认!'
            return (picking_ids, message)
        return (picking_ids, message)

    def _verify_sale_return_repeat(self, cr, uid, ttype, sale_return_ids=False, context=None):
        message = ''
        logistics_line_obj = self.pool.get('okgj.logistics.line')
        if ttype == 'route':
            has_in_lines = logistics_line_obj.search(cr, uid, [('sale_return_id', '=', sale_return_ids[0]), ('state', 'in', ['todo'])], context=context)
            for one_line in logistics_line_obj.browse(cr, uid, has_in_lines, context=context):
                if one_line.logistics_id.type == 'route':
                    message = u'该单上次干线物流过程未完成，不应装车'
                    return message
        if ttype == 'local':
            has_in_lines = logistics_line_obj.search(cr, uid, [('sale_return_id', '=', sale_return_ids[0]), ('state', 'in', ['todo', 'done'])], context=context)
            for one_line in logistics_line_obj.browse(cr, uid, has_in_lines, context=context):
                if one_line.logistics_id.type == 'local':
                    message = u'该单已出发或已送达至客户'
                    return message
        return message

    def _verify_picking_repeat(self, cr, uid, ttype, picking_ids=False, context=None):
        message = ''
        logistics_line_obj = self.pool.get('okgj.logistics.line')
        if ttype == 'route':
            has_in_lines = logistics_line_obj.search(cr, uid, [('picking_id', '=', picking_ids[0]), ('state', 'in', ['todo'])], context=context)
            for one_line in logistics_line_obj.browse(cr, uid, has_in_lines, context=context):
                if one_line.logistics_id.type == 'route':
                    message = u'该单上次干线物流过程未完成，不应装车'
                    return message
        if ttype in ['local', 'three_side']:
            has_in_lines = logistics_line_obj.search(cr, uid, [('picking_id', '=', picking_ids[0]), ('state', 'in', ['todo', 'done'])], context=context)
            for one_line in logistics_line_obj.browse(cr, uid, has_in_lines, context=context):
                if one_line.logistics_id.type in ['local', 'three_side']:
                    message = u'该单已出发或已送达至客户'
                    return message
        return message

    def _check_repeat_address(self, cr, uid, sale_return_ids=[], picking_ids=[], line_ids=[], context=None): 
        #重复地址检查
        message = ''
        sale_address = []
        picking_obj = self.pool.get('stock.picking.out')
        sale_return_obj = self.pool.get("okgj.sale.return")
        if not line_ids:
            line_ids = []
        all_picking_line_ids = [one_line[2]['picking_id'] for one_line  in line_ids if one_line and one_line[2] and one_line[2].get('picking_id', False)]
        all_picking_data = picking_obj.browse(cr, uid, all_picking_line_ids, context=context)
        for one_picking_line in all_picking_data:
            if one_picking_line.sale_id:
                sale_address.append(one_picking_line.sale_id.okgj_address)

        all_sale_return_ids = [one_line[2]['sale_return_id'] for one_line  in line_ids if one_line and one_line[2] and one_line[2].get('sale_return_id', False)]
        all_return_data = sale_return_obj.browse(cr, uid, all_sale_return_ids, context=context)
        for one_return_line in all_return_data:
            sale_address.append(one_return_line.address)

        if picking_ids:
            now_picking_data = picking_obj.browse(cr, uid, picking_ids[0], context=context)
            if now_picking_data.sale_id.okgj_address in sale_address:
                message = u'该单地址已存在前述单中'
                return message
        if sale_return_ids:
            now_return_data = sale_return_obj.browse(cr, uid, sale_return_ids[0], context=context)     
            if now_return_data.address in sale_address:
                message = u'该单地址已存在前述单中'
                return message
        return message

    def onchange_picking(self, cr, uid, ids, ttype='local', is_sale_return=False, picking=False, line_ids=False, three_side_picking=False, context=None):
        """ On change of Picking and will add line_ids
        #同一送货地址需提示
        @return: Dictionary of values
        """
        if (not picking):
            return {}
        sale_return_ids = False
        picking_ids = False
        if is_sale_return:
            (sale_return_ids, message) = self._check_sale_return(cr, uid, picking)
        else:
            (picking_ids, message) = self._check_picking(cr, uid, picking)
        if message:
            return {'warning':{
                'title': picking,
                'message': message,
                }}
        if is_sale_return:
            message = self._verify_sale_return_repeat(cr, uid, ttype, sale_return_ids, context=context)
        else:
            message = self._verify_picking_repeat(cr, uid, ttype, picking_ids, context=context)
        if message:
            return {'warning':{
                'title': picking,
                'message': message,
                }}
        #处理第三方物流
        if ttype == 'three_side':
            temp_message = ''
            if not three_side_picking:
                temp_message += u'第三方物流单号不能为空! \n'
            #if picking_ids: 
            #    temp_message += self._check_three_side_picking(cr, uid, picking_ids, ttype, three_side_picking) 
            if temp_message:
                return {'warning':{
                        'title': picking,
                        'message': temp_message,
                        }}
               
        message = self._check_repeat_address(cr, uid, sale_return_ids, picking_ids, line_ids, context=context)
        warning = {}
        if message:
            warning = {
                'title': picking,
                'message': message,
            }
        if is_sale_return:
            line_ids.append((0, 0, {'sale_return_id':sale_return_ids[0], 'three_side_picking':three_side_picking}))
        else:
            line_ids.append((0, 0, {'picking_id':picking_ids[0], 'three_side_picking':three_side_picking}))
        #正常完成
        if warning:
            return {'value':{'line_ids':line_ids, 'picking':False, 'three_side_picking':False}, 'warning':warning}
        else:
            return {'value':{'line_ids':line_ids, 'picking':False, 'three_side_picking':False}}
        return {}
    
    def _check_three_side_picking(self, cr, uid, picking_ids, ttype=None, three_side_picking=None, context=None):
        """
                检测第三方物流单号是否填写
                检测第三方物流出库单的付款方式是否为余额支付
        """
        if context is None:
            context = {}
        sale_data = self.pool.get('stock.picking').browse(cr, uid, picking_ids[0], context=context).sale_id
        message = ''
        
        if sale_data and sale_data.pay_name in [u'货到付款(现金支付)', u'货到付款']:
            message += (u'错误: 第三方物流配送的付款方式不支持:%s!' % sale_data.pay_name)
        return message
    
okgj_logistics()

#省份城市字段
class okgj_res_country_state(osv.osv):
    _inherit='res.country.state'
    _columns={
        'city_line_ids':fields.one2many('okgj.logistics.city.line', 'province_id', u'城市明细'),
    }
okgj_res_country_state()

class okgj_logistics_city_line(osv.osv):
    _name='okgj.logistics.city.line'
    _description='Logistics city.line'
    _order='name'
    _columns={
        'name':fields.char(u'城市名称', size=32, required=True),
        'code':fields.char(u'城市编码', size=16),
        'okgj_city_id':fields.char(u'城市ID(商城)', size=32),
        'province_id':fields.many2one('res.country.state', u'省份', required=True),
        'country_id':fields.related('province_id', 'country_id', type="many2one", relation='res.country', string=u'国家'),
        'create_date':fields.datetime(u'创建时间', readonly=True),
        'create_uid':fields.many2one('res.users', u'创建人', readonly=True),
    }
okgj_logistics_city_line()

class okgj_logistics_region(osv.osv):
    _name='okgj.logistics.region'
    _description='Logistics region'
    _order='create_date'
    _columns={
        'name':fields.char(u'区域名称', size=32, required=True),
        'code':fields.char(u'区域编码', size=16, required=True),
        'okgj_region_id':fields.char(u'区域ID(商城)', size=32),
        'city_line_id':fields.many2one('okgj.logistics.city.line', u'所属城市', required=True),
        'province_id':fields.related('city_line_id', 'province_id', type="many2one", relation="res.country.state", string=u'省份'),
        'country_id':fields.related('city_line_id', 'country_id', type="many2one", relation="res.country", string=u"国家"),
        'region_line_ids':fields.one2many('okgj.logistics.region.line', 'region_id', u'区域明细'),
        'create_date':fields.datetime(u'创建时间', readonly=True),
        'create_uid':fields.many2one('res.users', u'创建人', readonly=True),
    }
okgj_logistics_region()

class okgj_logistics_region_line(osv.osv):
    _name='okgj.logistics.region.line'
    _columns={
        'name':fields.char(u'街道名称(或路线名称)', size=32),
        'code':fields.char(u'名称编码'),
        'region_id':fields.many2one('okgj.logistics.region', u'区域'),
        'city_line_id':fields.related('region_id', 'city_line_id', type='many2one', relation='okgj.logistics.city.line', string=u'城市'),
    }
okgj_logistics_region_line()