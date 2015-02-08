# -*- coding: utf-8 -*-
#===============================================================================
# auther：cloudy
# date：2014/10/31
# description：退货单
#===============================================================================

#import time
from openerp.osv import  osv, fields
from openerp.tools.translate import _
#from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
import time
from sale import Sale_Status
from openerp import netsvc
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT


Picking_In_Status = [
    ('draft', u'草稿'),
    ('cancel', u'取消'),
    ('auto', u'等待其他操作'),
    ('confirmed', u'等待可用'),
    ('assigned', u'准备收货'),
    ('done', u'已入库'),
]
Picking_Out_status = [
    ('draft', u'草稿'),
    ('cancel', u'取消'),
    ('auto', u'等待其他操作'),
    ('confirmed', u'等待可用'),
    ('assigned', u'准备发运'),
    ('done', u'已出库'),
]
Sale_Back_Trade_Status = [('done', u'交易完成'), ('undone', u'交易未完成')]
Back_Type = [
    ('refund', u'退款：未发货,退款，取消出库'),
    ('back', u'退款退货：已发货，退款，SKU退入仓库'),
    ('exchange', u'换货：SKU入库，SKU出库'),
    ('back_money', u'退款：补差价,退款不退货,报价单退款'),
    ]


class sale_back_(osv.osv):
    _name = 'sale.back'
    _description = u"退货单"
    _columns = {
        'name': fields.char(string=u'退货单信息', size=50),
    }
sale_back_()


class sale_exchange_line(osv.osv):
    _name = 'sale.exchange.line'
    _description = u"出库明细"
    _columns = {
        'name': fields.char(u'产品', size=10),
        'back_id': fields.many2one('sale.back', u'换货单', required=True, ondelete='cascade', ),
        'product_id': fields.many2one('product.product', u"产品", required=True),
        'product_qty': fields.float(u"数量"),
        #'price_unit':fields.float(string=u'单价'),
        #'price_subtotal':fields.float(string=u'小计'),

    }
sale_exchange_line()


class sale_refund_line(osv.osv):
    _name = 'sale.refund.line'
    _description = u"退款明细"
    _columns = {
        'name': fields.char(u'产品', size=10),
        'back_id': fields.many2one('sale.back', u'换货单', required=True, ondelete='cascade', ),
        'product_id': fields.many2one('product.product', u"产品", required=True),
        'product_qty': fields.float(u"数量"),
    }
sale_refund_line()


class sale_back_picking_out_line(osv.osv):
    _name = "sale.back.picking.out.line"


class sale_back_line(osv.osv):
    _name = 'sale.back.line'
    _description = u"入库明细"
    _columns = {
       'name': fields.char(u'产品', size=10),
       'back_id': fields.many2one('sale.back', u'退货单', required=True, ondelete='cascade', ),
       'product_id': fields.many2one('product.product', u"产品", required=True),
       'product_qty': fields.float(u"数量"),
       #'price_unit':fields.float(string=u'单价'),
       #'price_subtotal':fields.float(string=u'小计'),
    }
sale_back_line()


class sale_back(osv.osv):
    _inherit = 'sale.back'
    _order = 'id desc'
    _sale_back_state = [('draft', u'草稿'), ('approval', u"待主管"), ('wait_account', u'待财务'), ('wait_house', u'待仓库'), ('confirmed', u"待复核"),
                        ('done', u'完成'), ('cancel', u'取消')]

    def default_get(self, cr, uid, fields, context=None):

        res = super(sale_back, self).default_get(cr, uid, fields, context)
        try:
            so_id = context.get('active_ids')
            res.update({'so_id': so_id[0]})
        except:
            pass
        return res

    def _constraint_flag(self, cr, uid, ids, context=None):
        ''''''
        for line in self.browse(cr, uid, ids, context=context):
            if line.out_cancel_flag:
                if not line.new_cancel_picking_ids:
                    raise osv.except_osv(u'错误', u'没有需要取消的出库单，不用勾选‘需要取消出库’')
            if line.in_flag:
                if not line.back_line:
                    raise osv.except_osv(u'错误', u'没有入库库明细，不用勾选‘需要入库’')
            if line.out_flag:
                if not line.exchange_line:
                    raise osv.except_osv(u'错误', u'没有出库明细，不用勾选‘需要出库’')
        return True

    def _get_default_warehouse(self, cr, uid, context=None):
        mod_obj = self.pool.get('ir.model.data')
        return mod_obj.get_object_reference(cr, uid, 'stock', 'warehouse0')[1],
    _columns = {
        "name": fields.char(u'退货单号', size=30),
        'type': fields.selection(Back_Type, string=u"退/换货", required=False),
        "so_id": fields.many2one('sale.order', string=u"销售单号", required=True),
        'amount': fields.float(u'退款金额', ),
        'alipay_nick': fields.char(u'支付宝：帐号', size=50),
        'alipay_name': fields.char(u'支付宝：姓名', size=50),
        'alipay_phone': fields.char(u'客户电话', size=20),
        'trade_state': fields.selection(Sale_Back_Trade_Status, string=u'交易状态', required=True),

        "refund_line": fields.one2many('sale.refund.line', 'back_id', string=u'退款明细'),
        "back_line": fields.one2many('sale.back.line', 'back_id', string=u'入库明细'),
        "exchange_line": fields.one2many('sale.exchange.line', 'back_id', string=u'出库明细'),

        "state": fields.selection(_sale_back_state, string=u"审核状态"),
        'note': fields.text(u"备注"),
        'reason': fields.text(u'原因'),
        'create_uid': fields.many2one('res.users', string=u'申请人', readonly=True),
        'create_date': fields.datetime(u'创建时间', readonly=True),
        'carrier_id': fields.many2one('delivery.carrier', string=u'快递方式', required=False),
        'carrier_tracking': fields.char(u'快递单号', size=50, required=False),
        'return_location_id': fields.many2one('stock.location', required=False, string=u'退入仓库'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Ware House'),
        'picking_id': fields.many2one('stock.picking.in', string=u'入库单号'),
        'in_pick_state': fields.related('picking_id', 'state', type='selection', selection=Picking_In_Status, string=u'入库状态', readonly=True),
        'platform_so_id': fields.related('so_id', 'platform_so_id', type='char', string=u"交易编号", readonly=True),
        'platform_user_id': fields.related('so_id', 'platform_user_id', type='char', string=u"买家ID", readonly=True),
        'platform_seller_id': fields.related('so_id', 'platform_seller_id', type='char', string=u"卖家ID:店铺", readonly=True),
        'api_id': fields.related('so_id', 'api_id', type='many2one', relation='sync.api', string=u"卖家ID:店铺", readonly=True),
        'receiver_phone': fields.related('so_id', 'receiver_phone', type='char', string=u"收货电话", readonly=True),
        'receive_user': fields.related('so_id', 'receive_user', type='char', string=u'收件人', readonly=True),

        'need_cancel_picking_id': fields.many2one('stock.picking.out', string=u'出库单'),
        'cancel_picking_ids': fields.many2many('stock.picking.out', 'cancel_stock_picking', 'back_ids', 'stock_ids', string=u'所有出库单'),
        'need_cancel_picking_state': fields.related('need_cancel_picking_id', 'state', type='selection', selection=Picking_Out_status, string=u'要取消的出库单状态', readonly=True),

        'out_picking_id': fields.many2one('stock.picking.out', string=u'出库单号'),
        'out_pick_state': fields.related('out_picking_id', 'state', type='selection', selection=Picking_Out_status, string=u'出库状态', readonly=True),

        'new_receive_info_flag': fields.boolean(u'收货人使用新地址'),
        'out_receive_user': fields.char(u'收件人', size=20),
        "out_receiver_city_id": fields.many2one('res.city', u'城市',),
        "out_receiver_district": fields.char(u'区域', size=30),
        "out_receiver_state_id": fields.many2one('res.country.state', u'省份'),
        'out_receive_address': fields.char(u'收货地址', size=80),
        'out_receive_phone': fields.char(u'收货电话', size=20),

        'new_send_info_flag': fields.boolean(u'发货使用新地址'),
        'new_deliver_name': fields.char(u'发货人', size=20),
        'new_deliver_city_id': fields.many2one('res.city', u'发货城市'),
        'new_deliver_company_name': fields.char(u'发货单位', size=50),
        'new_deliver_tel': fields.char(u'发货电话', size=20),
        'new_deliver_address': fields.char(u'发货地址', size=80),
        'in_flag': fields.boolean(u'需要入库'),
        'out_flag': fields.boolean(u'需要出库'),
        'out_cancel_flag': fields.boolean(u'需要取消出库'),
        'so_state': fields.related('so_id', 'state', type='selection', selection=Sale_Status, string=u'订单状态', readonly=True),
        'new_cancel_picking_ids': fields.many2many('stock.picking.out', 'new_cancel_stock_picking', 'back_ids', 'stock_ids', string=u'需要取消的出库单'),
        'shop_id': fields.related('so_id', 'shop_id', type='many2one', relation='sale.shop', string=u'商店', readonly=True),

    }
    _defaults = {
        'state': 'draft',
    }
    _constraints = [
        (_constraint_flag, u"修改信息失败,请联系开发人员", ['in_flag', 'out_flag', 'out_cancel_flag', 'type', 'state'])
    ]

    def create(self, cr, uid, value, context=None):
        value.update({'name': 'SR' + time.strftime('%Y%m%d%H%M%S')})
        return super(sale_back, self).create(cr, uid, value, context=context)

    def unlink(self, cr, uid, ids, context=None):
        '''
        删除退货单申请
        '''
        backs_info = self.read(cr, uid, ids, ['state', ], context=context)
        for info in backs_info:
            if info['state'] != 'draft':
                raise osv.except_osv(_(u'无效操作！'), _(u'只能删除草稿状态的退货申请单！'))
        return super(sale_back, self).unlink(cr, uid, ids, context=context)

    def onchange_picking_out_id(self, cr, uid, ids, need_cancel_picking_id):
        """出库单单号改变时，获得出库单的状态"""
        value = {}
        if need_cancel_picking_id:
            picking_obj = self.pool.get('stock.picking.out').browse(cr, uid, need_cancel_picking_id)
            value.update({'need_cancel_picking_state': picking_obj.state})
        return {'value': value}

    def onchange_so_id_new(self, cr, uid, ids, so_id, in_flag, out_flag, out_cancel_flag):
        """
        选择销售订单时，自动更新退换货明细
        """
        value = {}
        cancel_picking_ids = []
        new_cancel_picking_ids = []

        refund_line = [(5, )]
        back_line = [(5, )]
        exchange_line = [(5, )]
        so_id = so_id
        so_obj = self.pool.get('sale.order')
        picking_out_obj = self.pool.get('stock.picking.out')
        if so_id:
            cancel_picking_ids = picking_out_obj.search(cr, uid, [('sale_id', '=', so_id), ('type', '=', 'out')])
            if out_cancel_flag:
                new_cancel_picking_ids = picking_out_obj.search(cr, uid, [('sale_id', '=', so_id), ('type', '=', 'out'), ('state', 'not in', ['done', 'cancel'])])
            so = so_obj.browse(cr, uid, so_id)
            #退款， 退货，换货
            for line in so.order_line:
                if line.product_id.type != 'product':
                    continue
                #入库明细
                if in_flag:
                    back_line.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                    }))
                #出库明细
                if out_flag:
                    exchange_line.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                    }))
                    value.update({
                        'out_receive_user': so.receive_user or '',
                        "out_receiver_city_id": so.receiver_city_id and so.receiver_city_id.id or None,
                        "out_receiver_district": so.receiver_district or '',
                        "out_receiver_state_id": so.receiver_state_id and so.receiver_state_id.id or None,
                        'out_receive_address': so.receive_address or '',
                        'out_receive_phone': so.receive_phone or '',
                        'new_deliver_name': so.deliver_name or '',
                        'new_deliver_city_id': so.deliver_city_id and so.deliver_city_id.id or None,
                        'new_deliver_company_name': so.deliver_company_name or '',
                        'new_deliver_tel': so.deliver_tel or '',
                        'new_deliver_address': so.deliver_address or'',
                    })
        value.update({
            'back_line': back_line,
            'exchange_line': exchange_line,
            'refund_line': refund_line,
            'so_id': so_id,
            'cancel_picking_ids': cancel_picking_ids,
            'new_cancel_picking_ids': new_cancel_picking_ids,
        })
        return {'value': value}

    def onchange_so_id(self, cr, uid, ids, so_id, back_type):
        """
        选择销售订单时，自动更新退换货明细
        """
        
        value = {}
        cancel_picking_ids = []

        refund_line = [(5, )]
        back_line = [(5, )]
        exchange_line = [(5, )]
        so_id = so_id
        so_obj = self.pool.get('sale.order')
        picking_out_obj = self.pool.get('stock.picking.out')

        if so_id:
            cancel_picking_ids = picking_out_obj.search(cr, uid, [('sale_id', '=', so_id), ('type', '=', 'out')])
            so = so_obj.browse(cr, uid, so_id)
            #退款， 退货，换货
            for line in so.order_line:
                if line.product_id.type != 'product':
                    continue
                #退款明细
                if back_type in ['refund', 'back']:
                    refund_line.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                    }))
                #入库明细
                if back_type in ['back', 'exchange']:
                    back_line.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                    }))
                #出库明细
                if back_type == 'exchange':
                    exchange_line.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                    }))
                    value.update({
                        'out_receive_user': so.receive_user or '',
                        "out_receiver_city_id": so.receiver_city_id and so.receiver_city_id.id or None,
                        "out_receiver_district": so.receiver_district or '',
                        "out_receiver_state_id": so.receiver_state_id and so.receiver_state_id.id or None,
                        'out_receive_address': so.receive_address or '',
                        'out_receive_phone': so.receive_phone or '',
                        'new_deliver_name': so.deliver_name or '',
                        'new_deliver_city_id': so.deliver_city_id and so.deliver_city_id.id or None,
                        'new_deliver_company_name': so.deliver_company_name or '',
                        'new_deliver_tel': so.deliver_tel or '',
                        'new_deliver_address': so.deliver_address or '',
                    })
                #判断明细是否错误，
                if back_type == 'refund':
                    if exchange_line != [(5, )] or back_line != [(5, )]:
                        raise osv.except_osv(u'错误', u'出库明细和入库明细应为空，请联系开发人员')
                if back_type == 'back':
                    if exchange_line != [(5, )]:
                        raise osv.except_osv(u'错误', u'出库明细应为空，请联系开发人员')
                if back_type == 'exchange':
                    if refund_line != [(5, )]:
                        raise osv.except_osv(u'错误', u'出库明细应为空，请联系开发人员')
        value.update({
            'back_line': back_line,
            'exchange_line': exchange_line,
            'refund_line': refund_line,
            'so_id': so_id,
            'cancel_picking_ids': cancel_picking_ids,
        })
        return {'value': value}

    def action_button_pass(self, cr, uid, ids, context=None):
        '''主管审核'''

        assert len(ids) == 1
        return self.write(cr, uid, ids, {'state': "wait_account"}, context=context)

    def action_wait_house(self, cr, uid, ids, context=None):
        '''仓库审核'''
        assert len(ids) == 1
        flag = False
        sale_back_obj = self.browse(cr, uid, ids[0], context)
        if sale_back_obj.out_cancel_flag:
            for line in sale_back_obj.new_cancel_picking_ids:
                if line.state != 'cancel':
                    flag = True
        if flag:
            raise osv.except_osv(u'错误', u'有需要取消的出库单未取消')
        if  sale_back_obj.picking_id:
            if sale_back_obj.picking_id.state != 'done':
                move_obj = self.pool.get('stock.move')
                line_ids = [line.id for line in sale_back_obj.picking_id.move_lines]
                picking_ids = []
                move_ids = []
                wf_service = netsvc.LocalService("workflow")
                if context is None:
                    context = {}

                todo = []
                for move in move_obj.browse(cr, uid, line_ids, context=context):
                    if move.state == "draft":
                        todo.append(move.id)
                if todo:
                    move_obj.action_confirm(cr, uid, todo, context=context)
                    todo = []

                for move in move_obj.browse(cr, uid, line_ids, context=context):
                    if move.state in ['done', 'cancel']:
                        continue
                    move_ids.append(move.id)

                    if move.picking_id:
                        picking_ids.append(move.picking_id.id)
                    if move.move_dest_id.id and (move.state != 'done'):
                        # Downstream move should only be triggered if this move is the last pending upstream move
                        other_upstream_move_ids = move_obj.search(cr, uid, [('id', '!=', move.id), ('state', 'not in', ['done', 'cancel']),
                                                    ('move_dest_id', '=', move.move_dest_id.id)], context=context)
                        if not other_upstream_move_ids:
                            move_obj.write(cr, uid, [move.id], {'move_history_ids': [(4, move.move_dest_id.id)]})
                            if move.move_dest_id.state in ('waiting', 'confirmed'):
                                move_obj.force_assign(cr, uid, [move.move_dest_id.id], context=context)
                                if move.move_dest_id.picking_id:
                                    wf_service.trg_write(uid, 'stock.picking', move.move_dest_id.picking_id.id, cr)
                                if move.move_dest_id.auto_validate:
                                    move_obj.action_done(cr, uid, [move.move_dest_id.id], context=context)
                    move_obj._create_product_valuation_moves(cr, uid, move, context=context)
                    if move.state not in ('confirmed', 'done', 'assigned'):
                        todo.append(move.id)
                if todo:
                    move_obj.action_confirm(cr, uid, todo, context=context)
                move_obj.write(cr, uid, move_ids, {'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
                for move_id in move_ids:
                    wf_service.trg_trigger(uid, 'stock.move', move_id, cr)

                for pick_id in picking_ids:
                    wf_service.trg_write(uid, 'stock.picking', pick_id, cr)
                    self.pool.get('stock.picking.in').write(cr, uid, pick_id, {'state': 'done'},context=context)
        return self.write(cr, uid, ids, {'state': "confirmed"}, context=context)

    def action_confirmed(self, cr, uid, ids, context=None):
        '''财务复核'''
        assert len(ids) == 1
        sale_back_obj = self.browse(cr, uid, ids[0], context)
        if  sale_back_obj.picking_id:
            if sale_back_obj.picking_id.state != 'done':
                raise osv.except_osv(u'错误', u'请先联系仓库入库')
        return self.write(cr, uid, ids, {'state': "done"}, context=context)

    def action_wait_account(self, cr, uid, ids, context=None):
        '''
         财务审核
        '''
        mod_obj = self.pool.get('ir.model.data')
        picking_in_obj = self.pool.get('stock.picking.in')
        picking_out_obj = self.pool.get('stock.picking.out')
        sequence_obj = self.pool.get('ir.sequence')
        flag = False
        location_customers = mod_obj.get_object_reference(cr, uid, 'stock', 'stock_location_customers')[1]
        location_stock = mod_obj.get_object_reference(cr, uid, 'stock', 'stock_location_stock')[1]
        back_order = self.browse(cr, uid, ids[0], context=context)
        if back_order.state != 'wait_account':
            raise osv.except_osv(u'错误', u'需要主管审核通过之后才能由财务审核')
        so = back_order.so_id

        picking_in_id = out_picking_id = False
        #退货、换货.生成入库单
        if back_order.type in ['back', 'exchange'] or back_order.in_flag:
            in_move_lines = []
            for l in back_order.back_line:
                in_move_lines.append((0, 0, {
                    'product_id': l.product_id.id,
                    'product_qty': l.product_qty,
                    'product_uom': l.product_id.uom_id.id,
                    'name': l.product_id.name,
                    'location_id': location_customers,
                    'location_dest_id': back_order.return_location_id.id,
                }))
            if in_move_lines:
                flag = True
            vals = {
                'origin': so.name,
                'name': sequence_obj.get(cr, uid, 'stock.picking.in') + '-' + so.name + '-Return',
                'move_lines': in_move_lines,
                'sale_id': so.id,
                'location_dest_id': back_order.return_location_id.id,
            }
            picking_in_id = picking_in_obj.create(cr, uid, vals, context=context)
        #换货，生成出库单据
        if back_order.type == 'exchange' or back_order.out_flag:
            out_move_lines = []
            for l in back_order.exchange_line:
                out_move_lines.append((0, 0, {
                    'product_id': l.product_id.id,
                    'product_qty': l.product_qty,
                    'product_uom': l.product_id.uom_id.id,
                    'name': l.product_id.name,
                    'location_id': location_stock,
                    'location_dest_id': location_customers,
                }))
            if out_move_lines:
                flag = True
            args = {
                'receive_user': back_order.out_receive_user,
                'receiver_city_id': back_order.out_receiver_city_id and back_order.out_receiver_city_id.id or None,
                'receiver_state_id': back_order.out_receiver_state_id and back_order.out_receiver_state_id.id or None,
                'receive_address': back_order.out_receive_address,
                'receive_phone': back_order.out_receive_phone,
                'deliver_name': back_order.new_deliver_name,
                'deliver_city_id': back_order.new_deliver_city_id and back_order.new_deliver_city_id.id or None,
                'deliver_company_name': back_order.new_deliver_company_name,
                'deliver_tel': back_order.new_deliver_tel,
                'deliver_address': back_order.new_deliver_address,
                'partner_id': back_order.so_id.partner_id and back_order.so_id.partner_id.id or None,
                'origin': so.name,
                'sale_id': so.id,
                'name': sequence_obj.get(cr, uid, 'stock.picking.out') + '-' + so.name + '-Exchange',
                'move_lines': out_move_lines,
                'location_id': location_stock,
            }
            out_picking_id = picking_out_obj.create(cr, uid, args, context)
        vals = {
            'picking_id': picking_in_id,
            'out_picking_id': out_picking_id,
        }
        if flag:
            vals.update({'state': 'wait_house'})
        else:
            vals.update({'state': 'done'})
        record_id = self.write(cr, uid, ids, vals, context=context)

        #self.auto_action_done(cr, uid, context=context)
        return record_id

    def action_button_submit(self, cr, uid, ids, context=None):
        '''
        业务员将退货申请单提交给业务主管审批
        '''
        assert len(ids) == 1
        return self.write(cr, uid, ids, {'state': "approval"}, context=context)

    def action_button_notpass(self, cr, uid, ids, context=None):
        '''platform_so_id
         业务主管审核不通过业务员提交的退货申请单，打回给业务员，并在备注中说明理由或者需要补充、更改的信息

        '''
        assert len(ids) == 1
        value = {}
        picking_in_obj = self.pool.get('stock.picking.in')
        picking_out_obj = self.pool.get('stock.picking.out')
        back_order = self.browse(cr, uid, ids[0], context=context)
        if back_order.picking_id and back_order.picking_id.state == 'done':
            raise osv.except_osv(u'错误', u'入库单%s入库完成,不能返回草稿' % back_order.picking_id.name)
        else:
            cancel_id = back_order.picking_id.id
            if cancel_id:
                picking_in_obj.unlink(cr, uid, [cancel_id])
        if back_order.out_picking_id and back_order.out_picking_id.state == 'done':
            raise osv.except_osv(u'错误', u'出库单%s出库完成,不能返回草稿' % back_order.out_picking_id.name)
        else:
            cancel_id = back_order.out_picking_id.id
            if cancel_id:
                picking_out_obj.unlink(cr, uid, [cancel_id])
        value.update({
            'state': "draft",
            'picking_id': [],
            'out_picking_id': [],
            'carrier_id': [],
            'carrier_tracking': '',
            'return_location_id': [],
        })

        return self.write(cr, uid, ids, value, context=context)

    def action_button_cancel(self, cr, uid, ids, context=None):
        '''
        取消退换货申请单
        '''
        assert len(ids) == 1
        bo = self.browse(cr, uid, ids[0], context=context)
        if ((bo.out_pick_state and bo.out_pick_state != 'cancel') or (bo.in_pick_state and bo.in_pick_state != 'cancel')):
            raise osv.except_osv(u'警告!', u'要取消退货单，请先取消相关的出库单和入库单')
        return self.write(cr, uid, ids, {'state': "cancel"}, context=context)

    def action_done(self, cr, uid, ids, context=None):
        #可以完成的条件 出库单完成  入库单完成   应该取消的出库单取消
        for sale_back in self.browse(cr, uid, ids, context=context):
            if (sale_back.state != 'confirmed'
                or(sale_back.picking_id and sale_back.picking_id.state != 'done')
                or (sale_back.out_picking_id and sale_back.out_picking_id.state != 'done')):
                continue
            else:
                self.write(cr, uid, sale_back.id, {'state': 'done'})
        return True

    def auto_action_done(self, cr, uid, ids=None, context=None):
        uid = 1
        todo_ids = self.search(cr, uid, [('state', '=', 'confirmed'), ('picking_id.state', '=', 'done')])
        self.action_done(cr, uid, todo_ids, context=context)
        return True
sale_back()
