# -*- coding: utf-8 -*-
##############################################################################
import logging
import time
from openerp.osv import osv, fields
from openerp import netsvc
from openerp import pooler
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
from sync_api import Wait_Send_Status, ALL_Platform_SO_State

_logger = logging.getLogger(__name__)


class stock_location(osv.osv):
    _inherit = "stock.location"
    _columns = {
        "code": fields.char('Code', size=12),
    }
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Code must be unique per location'),
    ]
stock_location()


class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def _default_express(self, cr, uid, ids, field_name, arg=None, context=None):
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            res[pick.id] = pick.express_ids and pick.express_ids[0].id or None
        return res
        
    _columns = {
        "platform_so_id": fields.related('sale_id', 'platform_so_id', type='char', string=u'交易编号', readonly=True),
        "platform_so_state": fields.related('sale_id', 'platform_so_state', type='char', string=u'订单平台状态', readonly=True),
        
        "receive_user": fields.char(u'收件人', size=20),
        "receiver_city_id": fields.many2one('res.city', u'城市',),
        "receiver_state_id": fields.many2one('res.country.state', u'省'),
        "receiver_district": fields.char(u'区域', size=30),
        'receive_address': fields.char(u'收货地址', size=80),
        'receive_phone': fields.char(u'收货电话', size=20),
        'receiver_zip': fields.char(u'邮编', size=20),
         ##送货人信息
        'deliver_name': fields.char(u'发货人', size=20),
        'deliver_city_id': fields.many2one('res.city', u'发货城市'),
        'deliver_company_name': fields.char(u'发货单位', size=50),
        'deliver_tel': fields.char(u'发货电话', size=20),
        'deliver_address': fields.char(u'发货地址', size=80),
        'receiver_zip': fields.char(u'邮编', size=20),
        
        'unneed_express': fields.boolean(u'无需快递'),
        'carrier_id': fields.many2one('delivery.carrier', u'快递方式'),
        'need_express_count': fields.integer(u'需要快递单数量'),
        'printed': fields.boolean(u'已打单'),
        'express_printed': fields.boolean(u'已打快递'),
        
        'create_uid': fields.many2one('res.users', u'创建人', readonly=True),
        'create_date': fields.datetime(u'创建日期', readonly=True),
        'had_sync': fields.boolean(u'发货已同步到商城'),
        'express_url': fields.char('express url', size=30),
        'shop_id': fields.related('sale_id', 'shop_id', type="many2one", relation="sale.shop", string=u"订单仓库", readonly=1),
        'express_ids': fields.many2many('express.express', 'res_express_picking', 'picking_id', 'express_id', string=u'快递单号'),
        'express_id': fields.function(_default_express, arg=None, type='many2one', relation='express.express', string="快递单", store=True),
        'scan_input': fields.char(u'快递扫描', size=30),
        'sale_uid': fields.related('sale_id', 'user_id', type="many2one", relation="res.users", string=u'业务员', readonly=True),
        'api_id': fields.related('sale_id', 'api_id', type='many2one', relation="sync.api", string="API", readonly=True,),
        'back_id': fields.many2one('sale.back', u'退货单'),

    }
        
    def create(self, cr, uid, value, context=None):
        if context is None:
            context = {}
        express_ids = context.get('express_ids')
        if express_ids:
            value.update({'express_ids': [(6, 0, express_ids)]})
        return super(stock_picking, self).create(cr, uid, value, context=context)
    
    def action_move(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        express_ids = context.get('express_ids')
        if express_ids:
            self.write(cr, uid, ids, {'express_ids': [(6, 0, express_ids)]})
        return super(stock_picking, self).action_move(cr, uid, ids, context=context)
    
    def action_done(self, cr, uid, ids, context=None):
        #to open or close "auto express_post_to_platform"
        auto = False
        if auto:
            for pick in self.browse(cr, uid, ids, context=context):
                if pick.type == 'out':
                    try:
                        self.express_post_to_platform(cr, uid, ids, context=context)
                    except Exception, e:
                        _logger.info("action_done Error,%s" % e)

        return super(stock_picking, self).action_done(cr, uid, ids, context=context)
    
    def relieve_assign(self, cr, uid, ids, *args):
        move_obj = self.pool.get('stock.move')
        for pick in self.browse(cr, uid, ids,):
            move_ids = [i.id for i in pick.move_lines]
            move_obj.cancel_assign(cr, uid, move_ids)
        return True

    def express_post_to_platform(self, cr, uid, ids, context=None):
        """
        return@ so_id   the ids of SO thant Express sync success
        """
        _logger.info("express_post_to_platform Start")
        if context is None:
            context = {}
        api_obj = self.pool.get('sync.api')
        so_obj = self.pool.get('sale.order')
        so_ids = []
        for pick in self.browse(cr, uid, ids, context=context):
            so = pick.sale_id
            if pick.type == 'out' and  so:
                if all([so.platform_so_id, pick.express_id, so.api_id]):
                    express = pick.express_id
                    api = so.api_id
                    company_code = None
                    platform_sol_id = None
                    company_name = express.delivery_carrier_id.name_pinyin or 'ID:%s' % express.delivery_carrier_id.id
                    
                    if api.type in ['taobao', 'tmall']:
                        company_code = express.delivery_carrier_id.code_taobao or express.delivery_carrier_id.name_pinyin
                    elif api.type == 'suning':
                        company_code = express.delivery_carrier_id.code_suning
                        platform_sol_id = [str(line.platform_sol_id) for line in so.order_line]
                    elif api.type == 'yhd':
                        company_code = express.delivery_carrier_id.code_yhd
                    elif api.type == 'alibaba':
                        company_code = express.delivery_carrier_id.code_alibaba or '8'
                        platform_sol_id = ','.join([i.platform_sol_id for i in so.order_line if i.platform_sol_id])
                    else:
                        pass

                    if company_code:
                        arg = {
                            'platform_so_id': so.platform_so_id,
                            'tracking': express.name,
                            'company_code': company_code,
                            'platform_sol_id': platform_sol_id,
                            'company_name': company_name,
                        }
                        _logger.info("express_post_to_platform arg:%s-type:%s-account:%s-pick:%s" % (arg, api.type, api.name, pick.name))
                        new_state = api_obj.action_delivery(cr, uid, api, arg, context=context)
                        if new_state and new_state != so.platform_so_state:
                            so_obj.write(cr, uid, so.id, {'platform_so_state': new_state})
                            so_ids.append(so.id)
                    else:
                        _logger.info("express_post_to_platform Error,not deliver_company code:%s" % pick.name)
                else:
                    _logger.info("express_post_to_platform Error, not all( platform_so_id, express, api) for %s" % pick.name)
            else:
                _logger.info("express_post_to_platform Error,type is not out not SO %s" % pick.name)

        _logger.info("express_post_to_platform End")
        return so_ids
    
    def scheduler_express_sync(self, cr, uid, use_new_cursor=True, context=None):
        _logger.info("scheduler_express_sync Start")
        context = context or {}
        try:
            if use_new_cursor:
                cr = pooler.get_db(cr.dbname).cursor()
                self._sync_express(cr, uid, context=context)
            if use_new_cursor:
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
        _logger.info("scheduler_express_sync End")
        return True
    
    def _sync_express(self, cr, uid, context=None):
        _logger.info("_sync_express Start")
        
        api_obj = self.pool.get('sync.api')
        ok_api_ids = api_obj.get_connection_ok_api(cr, uid, None, context=context)
        domain = [('platform_so_state', 'in', Wait_Send_Status),
                  ('state', '=', 'done'),
                  ('type', '=', 'out'),
                  ('api_id', 'in', ok_api_ids),
                  ('express_id', '!=', False)]
        todo_ids = self.search(cr, uid, domain, order="id desc", limit=100, context=context)
        _logger.info("_sync_express todo_ids" % todo_ids)
        if todo_ids:
            self.express_post_to_platform(cr, uid, todo_ids, context=context)

        _logger.info("_sync_express End")
        return True
    
    def copy_new(self, cr, uid, ids, context=None):
        """"""
        old_obj = self.browse(cr, uid, ids[0], context)
        sequence_obj = self.pool.get('ir.sequence')
        now = time.strftime(DF)
        
        move_lines = []
        for move_line in old_obj.move_lines:
            move_lines.append((0, 0, {
                'name': move_line.name,
                'product_id': move_line.product_id.id,
                'product_qty': move_line.product_qty,
                'product_uom': move_line.product_uom.id,
                'date': now,
                'date_excepted': now,
                'location_id': move_line.location_id.id,
                'location_dest_id': move_line.location_dest_id.id,
            }))
        vals = {
            'partner_id': old_obj.partner_id.id,
            'stock_journal_id': old_obj.stock_journal_id.id,
            'date': now,
            'min-date': now,
            'origin': old_obj.origin,
            'name': sequence_obj.get(cr, uid, 'stock.picking.in'),
            'move_lines': move_lines,
        }
        picking_id = self.create(cr, uid, vals, context=context)
        return {
            'name': 'Internal Moves',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': picking_id,
            'type': 'ir.actions.act_window',
        }
        
    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        if context is None:
            context = {}
            
        if context.get('split'):
            return self.split_picking(cr, uid, ids, partial_datas, context=context)
        else:
            return super(stock_picking, self).do_partial(cr, uid, ids, partial_datas, context=context)
            
    def split_picking(self, cr, uid, ids, partial_datas, context=None):
        if context is None:
            context = {}

        res = {}
        move_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        for pick in self.browse(cr, uid, ids, context=context):
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s' % (move.id), {})
                product_qty = partial_data.get('product_qty', 0.0)
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom', False)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id],
                                                            product_qty, move.product_uom.id)
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    too_many.append(move)
            # We remove section of code that manage incoming picking
            # please refere to original code if needed
            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    new_picking_name = pick.name
                    self.write(cr, uid, [pick.id], {
                        'name': sequence_obj.get(cr, uid, 'stock.picking.%s' % pick.type),
                        #'carrier_id': pick.carrier_id and pick.carrier_id.id,
                        #'need_express_count': pick.need_express_count,
                    })
                    ##
                    new_picking = self.copy(cr, uid, pick.id, {
                        'name': new_picking_name,
                        'move_lines': [],
                        'state': 'draft',
                        #split express info pass from stock.partial.picking's context
                        'carrier_id': context.get('carrier_id'),
                        'need_express_count': context.get('need_express_count', 0),
                    })
                if product_qty != 0:
                    defaults = {
                            'product_qty': product_qty,
                            'product_uos_qty': product_qty,  # TODO: put correct uos_qty
                            'picking_id': new_picking,
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
                            'product_uos_qty': move.product_qty - partial_qty[move.id],
                            'prodlot_id': False,
                            'tracking_id': False,
                        })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[move.id],
                            'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty': product_qty,
                    'product_uos_qty': product_qty,  # TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            if new_picking:
                wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                delivered_pack_id = new_picking
            else:
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}

        return res

    def schedule_action_assign(self, cr, uid, use_new_cursor=True, location=None, context=None):
        _logger.info("schedule_action_assign Start")
        context = context or {}
        try:
            if use_new_cursor:
                cr = pooler.get_db(cr.dbname).cursor()
                self.auto_aciotn_assign(cr, uid, location=location, context=context)
            if use_new_cursor:
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
        _logger.info("schedule_action_assign End")
        return True
    
    def auto_aciotn_assign(self, cr, uid, location=None, context=None):

        domian = [('type', '=', 'out'), ('state', '=', 'confirmed')]
        if location:
            domian.append(('location_id', '=', location))
        todo_ids = self.search(cr, uid, domian)
        if todo_ids:
            _logger.info("_auto_aciotn_assign %s" % todo_ids)
            self.action_assign(cr, uid, todo_ids)
        return True
    
    def test_assigned(self, cr, uid, ids):
        ok = super(stock_picking, self).test_assigned(cr, uid, ids)
        for pick in self.browse(cr, uid, ids):
            #when out picking, if want to assigned, must sure all move state is assigned
            if pick.type == 'out':
                for move in pick.move_lines:
                    if move.state not in ['assigned', 'done']:
                        ok = False
                        break
        return ok
    
    def action_cancel(self, cr, uid, ids, context=None):
        """
        can not cancel the printed picking.out
        """
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.printed:
                raise osv.except_osv('Error', u"已经打印的发货单据，必须先通知仓库人员取消打印")
        return super(stock_picking, self).action_cancel(cr, uid, ids, context=context)


stock_picking()


class stock_picking_out(osv.osv):
    _inherit = 'stock.picking.out'

    def _auto_init(self, cr, context=None):
        uid = SUPERUSER_ID
        ids = self.search(cr, uid, [('receive_user', '=', False), ('receive_phone', '=', False), ('receive_address', '=', False)])
        for picking in self.browse(cr, uid, ids):
            so = picking.sale_id
            if so:
                self.write(cr, uid, picking.id, {
                    'receive_user': so.receive_user,
                    'receive_phone': so.receive_phone,
                    'receive_address': so.receive_address,
                    'receiver_city_id': so.receiver_city_id and so.receiver_city_id.id,
                    'receiver_state_id': so.receiver_state_id and so.receiver_state_id.id,
                })
        return super(stock_picking_out, self)._auto_init(cr, context=context)

    def _default_express(self, cr, uid, ids, field_name, arg=None, context=None):
        res = {}
        for pick in self.browse(cr, uid, ids, context=context):
            res[pick.id] = pick.express_ids and pick.express_ids[0].id or None
        return res

    _columns = {
        "platform_so_id": fields.related('sale_id', 'platform_so_id', type='char', string=u'交易编号', readonly=True),
        "platform_so_state": fields.related('sale_id', 'platform_so_state', type='selection', selection=ALL_Platform_SO_State, string=u'订单平台状态', readonly=True),
        "receive_user": fields.char(u'收件人', size=20),
        "receiver_city_id": fields.many2one('res.city', u'城市'),
        "receiver_state_id": fields.many2one('res.country.state', u'省'),
        "receiver_district": fields.char(u'区域', size=30),
        'receive_address': fields.char(u'收货地址', size=80),
        'receive_phone': fields.char(u'收货电话', size=20),
        'receiver_zip': fields.char(u'邮编', size=20),
         ##送货人信息
        'deliver_name': fields.char(u'发货人', size=20),
        'deliver_city_id': fields.many2one('res.city', u'发货城市'),
        'deliver_company_name': fields.char(u'发货单位', size=50),
        'deliver_tel': fields.char(u'发货电话', size=20),
        'deliver_address': fields.char(u'发货地址', size=80),
        'receiver_zip': fields.char(u'邮编', size=20),

        'unneed_express': fields.boolean(u'无需快递'),
        'carrier_id': fields.many2one('delivery.carrier', u'快递方式'),
        'need_express_count': fields.integer(u'需要快递单数量'),
        'printed': fields.boolean(u'打单'),
        'express_printed': fields.boolean(u'打快递'),

        'create_uid': fields.many2one('res.users', u'创建人', readonly=True),
        'create_date': fields.datetime(u'创建日期', readonly=True),
        'had_sync': fields.boolean(u'发货已同步到商城'),
        'express_url': fields.char('express url', size=30),
        'shop_id': fields.related('sale_id', 'shop_id', type="many2one", relation="sale.shop", string=u"订单仓库", readonly=1),
        'express_ids': fields.many2many('express.express', 'res_express_picking', 'picking_id', 'express_id', string=u'快递单号'),
        'express_id': fields.function(_default_express, arg=None, type='many2one', relation='express.express', string="快递单", store=True),
        'scan_input': fields.char(u'快递扫描', size=30),
        'sale_uid': fields.related('sale_id', 'user_id', type="many2one", relation="res.users", string=u'业务员', readonly=True),
        'api_id': fields.related('sale_id', 'api_id', type='many2one', relation="sync.api", string="API", readonly=True,),
        'cancel_picking_ids': fields.many2many('sale.back', 'cancel_stock_picking', 'stock_ids', 'back_ids', string=u'退货单'),
    }
    
    def cancel_print(self, cr, uid, ids, context=None):
        '''取消打印'''
        return self.write(cr, uid, ids, {'printed': False}, context=context)

    def onchange_scan_input(self, cr, uid, ids, scan_input, carrier_id, express_ids, context=None):
        
        express_obj = self.pool.get('express.express')
        if not carrier_id or not scan_input or not ids:
            return False

        search_ids = express_obj.search(cr, uid, [('name', '=', scan_input)], limit=1)
        express_id = search_ids and search_ids[0]
        if not express_id:
            express_id = express_obj.create(cr, uid, {
                'name': scan_input,
                'delivery_carrier_id': carrier_id,
                'state': '0',
                'picking_ids': [(4, ids[0])]
            }, context=context)

        if express_ids is None:
            express_ids = [(6, 0, [express_id])]
        else:
            express_ids[0][2].append(express_id)
        return {'value': {'scan_input': '', 'express_ids': express_ids}}
    
    def relieve_assign(self, cr, uid, ids, *args):
        move_obj = self.pool.get('stock.move')
        for pick in self.browse(cr, uid, ids,):
            move_ids = [i.id for i in pick.move_lines]
            move_obj.cancel_assign(cr, uid, move_ids)
        return True
    
    def action_assign(self, cr, uid, ids, *args):
        """
        If action_assing not passed, cancel the move assigned
        """
        res = super(stock_picking_out, self).action_assign(cr, uid, ids, *args)
        picks = self.browse(cr, uid, ids, context={})
        to_relieve_ids = [p.id for p in picks if p.type == 'out' and p.state == 'confirmed']
        self.relieve_assign(cr, uid, to_relieve_ids, *args)
        return res
    
    def express_post_to_platform(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking').express_post_to_platform(cr, uid, ids, context=context)
    
    def split_picking_out(self, cr, uid, ids, context=None):
        """
        """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': ids and ids[0] or False,
            'split': True,
        })
        return {
            'name': u'拆分出库',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.partial.picking',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
            'nodestroy': True,
        }
        
stock_picking_out()


class stock_picking_in(osv.osv):
    _inherit = 'stock.picking.in'
    _columns = {
        'create_uid': fields.many2one('res.users', u'创建人', readonly=True),
        'create_date': fields.datetime(u'创建日期', readonly=True),
        "sale_id": fields.many2one('sale.order', string=u"销售单号", required=True),
        'sale_uid': fields.related('sale_id', 'user_id', type="many2one", relation="res.users", string=u'业务员', readonly=True),
    }
stock_picking_in()


class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'purchase_price': fields.related('purchase_line_id', 'price_unit', type="float", digits_compute=dp.get_precision('Account'), string=u"采购价", readonly=True),
        "platform_so_id": fields.related('picking_id', 'platform_so_id', type='char', string=u'交易编号', readonly=True),
    }

    def show_product_pictrue(self, cr, uid, ids, context=None):
        line = self.browse(cr, uid, ids[0])
        mod_obj = self.pool.get('ir.model.data')
        view_id = mod_obj.get_object_reference(cr, uid, 'yks', 'yks_view_product_big_picture')[1]
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.product',
            'res_id': line.product_id.id,
            'view_id': view_id,
            'target': 'new',
        }
        
    def quick_product_change(self, cr, uid, ids, product, location_id, location_dest_id, date_expected, context=None):
        context = context or {}
        res = {}
        product = self.pool.get('product.product').browse(cr, uid, product, context=context)
        if product:
            res.update({
                'product_uom': product.uom_id.id,
                'name': product.name,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'date_expected': date_expected,
            })
        return {'value': res}

stock_move()


class delivery_carrier(osv.osv):
    _inherit = "delivery.carrier"
    _order = "sequence"
    _columns = {
        'sequence': fields.integer(u'序号',),
    }

    _defaults = {
        'sequence': 50,
    }

delivery_carrier()


class stock_inventory(osv.osv):
    _inherit = 'stock.inventory'
    _columns = {
        'create_uid': fields.many2one('res.users', u'创建人'),
        'done_uid': fields.many2one('res.users', u'确认人'),
    }
    
    def action_done(self, cr, uid, ids, context=None):
        res = super(stock_inventory, self).action_done(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'done_uid': uid}, context=context)
        return res

stock_inventory()


##############################################################################