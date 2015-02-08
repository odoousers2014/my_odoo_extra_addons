# -*- coding: utf-8 -*-
#===============================================================================
# auther：cloudy
# date：2014/10/31
# description：退货单
#===============================================================================

#import time
from openerp.osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import time
#from openerp.tools.translate import _
RDO_Status = [('draft', u'草稿'), ('confirmed', u'已确认'), ('purchased', '已申请采购'), ('done', u'完成'), ('cancel', u'取消')]


class requirement_distribution_order__(osv.osv):
    _name = 'requirement.distribution.order'
    
    def _default_name(self, cr, uid, ids, field_name, arg=None, context=None):
        res = {}
        for do in self.browse(cr, uid, ids, context=context):
            res[do.id] = 'RDO%s' % do.sale_id.name
        return res

    _columns = {
        'name': fields.function(_default_name, type="char", string='需求分配单', size=40, store=True),
    }
requirement_distribution_order__()


class requirement_distribution_line(osv.osv):
    _name = 'requirement.distribution.line'
    _columns = {
        'name': fields.char('Name', size=10),
        'order_id': fields.many2one('requirement.distribution.order', 'Distribution Order'),
        'sol_id': fields.many2one('sale.order.line', 'SOL', required=True),
        'product_id': fields.many2one('product.product', 'SKU'),
        'qty': fields.float(u'需求数量'),
        'purchase_qty': fields.float(u'采购数量'),
        'move_qty': fields.float(u'调货数量'),
    }
    
    _sql_constraints = [
        ('sale_uniq', 'unique(sale_id)', u'一个销售订单只能分配一次'),
        ('qty_check', 'check(qty-purchase_qty-move_qty=0)', u'采购数量+掉货数 ！= 需求数量'),
    ]
    
    def onchange_qty(self, cr, uid, ids, purchase_qty, move_qty, qty, fn, context=None):
        """
        @fn P:purchase_qty  M:move_qty
        """
        if fn == 'M':
            value = {'purchase_qty': qty - move_qty}
        else:
            value = {'move_qty': qty - purchase_qty}
        return {'value': value}
    
requirement_distribution_line()


class requirement_distribution_order(osv.osv):
    _inherit = 'requirement.distribution.order'
    
    _columns = {
        'state': fields.selection(RDO_Status, u'状态', required=True),
        'sale_id': fields.many2one('sale.order', u'销售单', required=True),
        'shop_id': fields.related('sale_id', 'shop_id', type='many2one', relation='sale.shop', string=u'需求仓库', readonly=True),
        'platform_so_id': fields.related('sale_id', 'platform_so_id', type="char", string="平台交易号", readonly=True),
        'partner_id': fields.many2one('res.partner', u'供应商'),
        'po_id': fields.many2one('purchase.order', u"采购单"),
        'location_id': fields.many2one('stock.location', u'调货库位'),
        'picking_id': fields.many2one('stock.picking.out', u"调货单"),
        'lines': fields.one2many('requirement.distribution.line', 'order_id', u'需求分配明细'),
        'create_uid': fields.many2one('res.users', u'业务员'),
        'purchase_uid': fields.many2one('res.users', u'采购员'),
        
        'carrier_id': fields.many2one('delivery.carrier', u'快递方式'),
        'need_express_count': fields.integer(u'需要快递单数量'),
    }
    
    _sql_constraints = [
        ('sale_uniq', 'unique(sale_id)', u'一个销售订单只能分配一次'),
    ]
    
    _defaults = {
        'state': 'draft',
        'location_id': 12,
        'need_express_count': 1,
    }

    def distribution_purchase(self, cr, uid, ids, context=None):
        po_obj = self.pool.get('purchase.order')
        sequence_obj = self.pool.get('ir.sequence')
        do = self.browse(cr, uid, ids[0], context=context)
        date_planned = time.strftime(DF)
        
        if do.state == 'confirmed':
            order_line = []
            for line in do.lines:
                if  line.product_id.type == 'product' and line.purchase_qty > 0:
                    order_line.append((0, 0, {
                        'product_id': line.product_id.id,
                        'product_qty': line.purchase_qty,
                        'name': line.product_id.name,
                        'price_unit': 0,
                        'date_planned': date_planned,
                    }))
            
            if not order_line:
                return True
                
            po_data = {
                'name': sequence_obj.get(cr, uid, 'purchase.order'),
                'partner_id': do.partner_id and do.partner_id.id or 1,
                'warehouse_id': do.shop_id.warehouse_id.id,
                'location_id': do.shop_id.warehouse_id.lot_stock_id.id,
                'pricelist_id': 1,
                'date_planned': date_planned,
                'order_line': order_line,
                'notes': 'SO: %s' % do.sale_id.name,
            }
            po_id = po_obj.create(cr, uid, po_data, context=context)
            self.write(cr, uid, do.id, {'po_id': po_id, 'state': 'purchased'}, context=context)
        
        return True
    
    def action_confirm(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        do = self.browse(cr, uid, ids[0], context=context)
        if do.state == 'draft':
            self.distribution_picking(cr, uid, ids, context=context)
            self.write(cr, uid, ids, {'state': 'confirmed'}, context=context)
        return True
    
    def aciont_draft(self, cr, uid, ids, context=None):
        do = self.browse(cr, uid, ids[0], context=context)
        
        if do.picking_id and do.picking_id.state != 'cancel':
            raise osv.except_osv(u'Error', u'要返回草稿，必须先取消 调货单')
        if do.po_id and do.po_id.state != 'cancel':
            raise osv.except_osv(u'Error', u'要返回草稿，必须先取消 采购单')
        self.write(cr, uid, do.id, {
            'state': 'draft',
            'picking_id': False,
            'po_id': False}, context=context)
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        do = self.browse(cr, uid, ids[0], context=context)
        if do.picking_id and do.picking_id.state != 'cancel':
            raise osv.except_osv(u'Error', u'要设为取消状态，必须先取消 调货单')
        if do.po_id and do.po_id.state != 'cancel':
            raise osv.except_osv(u'Error', u'要设为取消状态，必须先取消 采购单')
        self.write(cr, uid, do.id, {'state': 'cancel'}, context=context)
    
    def action_done(self, cr, uid, ids, context=None):
        do = self.browse(cr, uid, ids[0], context=context)
        if do.picking_id and do.picking_id.state != 'done':
            raise osv.except_osv(u'Error', u'调货单未完成')
        if do.sale_id.state not in ['done', 'shipped']:
            raise osv.except_osv(u'Error', u'销售订单必须 已发货')
        self.write(cr, uid, do.id, {'state': 'done'}, context=context)
        return True
    
    def distribution_picking(self, cr, uid, ids, context=None):
        pick_obj = self.pool.get('stock.picking.out')
        sequence_obj = self.pool.get('ir.sequence')
        do = self.browse(cr, uid, ids[0], context=context)
        so = do.sale_id
         
        #TODO check locaiton not same as dest location
        location_id = do.location_id.id
        location_dest_id = do.shop_id.warehouse_id.lot_stock_id.id
        
        if location_id == location_dest_id:
            raise osv.except_osv(u'Error', u'调货仓库和 销售发货仓库不能为同一个库位')
        
        move_lines = []
        for line in do.lines:
            if  line.product_id.type == 'product' and line.move_qty > 0:
                move_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.move_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'name': line.product_id.name,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
            }))
        if not move_lines:
            return True
        
        pick_data = {
            'name': sequence_obj.get(cr, uid, 'stock.picking.out'),
            'partner_id': do.partner_id and do.partner_id.id or 1,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'receive_user': so.receive_user,
            'receiver_city_id': so.receiver_city_id and so.receiver_city_id.id,
            'receiver_state_id': so.receiver_state_id and so.receiver_state_id.id,
            'receive_address': so.receive_address,
            'receive_phone': so.receive_phone,
            'deliver_name': so.deliver_name,
            'deliver_city_id': so.deliver_city_id and so.deliver_city_id.id,
            'deliver_company_name': so.deliver_company_name,
            'deliver_tel': so.deliver_tel,
            'deliver_address': so.deliver_address,
            'origin': so.name,
            'sale_id': so.id,
            'carrier_id': do.carrier_id and do.carrier_id.id,
            'need_express_count': do.need_express_count,
            'move_lines': move_lines,
            'note': do.name,
        }
        picking_id = pick_obj.create(cr, uid, pick_data, context=context)
        self.write(cr, uid, do.id, {'picking_id': picking_id}, context=context)
        
        return True
    
    def create(self, cr, uid, value, context=None):
        so_obj = self.pool.get('sale.order')
        sale_id = value.get('sale_id')
        lines = value.get('lines', [])
        if sale_id and not lines:
            so = so_obj.browse(cr, uid, sale_id, context=context)
            for sol in so.order_line:
                if sol.product_id.type == 'product':
                    lines.append((0, 0, {
                        'sol_id': sol.id,
                        'product_id': sol.product_id.id,
                        'qty': sol.product_uom_qty,
                        'purchase_qty': sol.product_uom_qty,
                        'move_qty': 0,
                    }))
            value.update({'lines': lines})
        return super(requirement_distribution_order, self).create(cr, uid, value, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        for do in self.browse(cr, uid, ids, context=context):
            if do.state not in ['draft', 'cancel']:
                raise osv.except_osv(u'Error', u'只能删除 草稿 取消 状态的 需求申请')
        return super(requirement_distribution_order, self).unlink(cr, uid, ids, context=context)
    

requirement_distribution_order()

####################################################################