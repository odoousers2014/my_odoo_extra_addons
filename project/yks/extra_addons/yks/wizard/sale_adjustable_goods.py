# -*- coding: utf-8 -*-
##############################################################################
from openerp.osv import  osv, fields


class sale_adjustable_goods_line(osv.osv_memory):
    _name = 'sale.adjustable.goods.line'

    _columns = {
        'name': fields.char(u'Name', size=30),
        'wizard_id': fields.many2one('sale.adjustable.goods', string=u'Wizard'),
        'sol_id': fields.many2one('sale.order.line', string="SOL"),
        'product_id': fields.many2one('product.product', string=u'产品', required=True),
        'product_qty': fields.float(string=u'总数量'),
        'move_qty': fields.float(string=u'调拨数量'),
    }

sale_adjustable_goods_line()


class sale_adjustable_goods(osv.osv_memory):
    _name = 'sale.adjustable.goods'
    
    def _default_lines(self, cr, uid, context=None):
        so_id = context.get('active_id')
        so = self.pool.get('sale.order').browse(cr, uid, so_id, context=context)
        res = []
        for sol in so.order_line:
            if sol.product_id.type == 'product':
                res.append((0, 0, {
                   'sol_id': sol.id,
                   'product_id': sol.product_id.id,
                   'product_qty': sol.product_uom_qty,
                   'move_qty': 0,
                }))
        return res
    
    _columns = {
        'name': fields.char('Name', size=20),
        'location_id': fields.many2one('stock.location', string=u'调货库位', required=True,),
        'location_dest_id': fields.many2one('stock.location', string=u'目标库位', required=False),
        'lines': fields.one2many('sale.adjustable.goods.line', 'wizard_id', string='明细'),
        'sale_id': fields.many2one('sale.order', u'销售订单'),
        'carrier_id': fields.many2one('delivery.carrier', u'快递方式'),
        'need_express_count': fields.integer(u'需要快递单数量'),
    }
    
    _defaults = {
        'location_id': lambda self, cr, uid, c: self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')[1],
        'lines': lambda self, cr, uid, c: self._default_lines(cr, uid, context=c),
        'need_express_count': 1,
    }
    
    def apply_check(self, wizard, context=None):
        
        if wizard.location_id == wizard.location_dest_id:
            raise osv.except_osv(u'错误', u'调拨库位和目标库位必须不同')
             
        for l in wizard.lines:
            if (l.move_qty <= 0 or l.move_qty > l.product_qty):
                raise osv.except_osv(u'错误', u'调拨数量不能大于订单数量或者小于1')
        return True

    def apply(self, cr, uid, ids, context=None):

        pick_obj = self.pool.get('stock.picking.out')

        wizard = self.browse(cr, uid, ids[0], context=context)
        so = wizard.sale_id
        
        self.apply_check(wizard, context=context)
        
        move_lines = []
        for l in wizard.lines:
            move_lines.append((0, 0, {
                    'product_id': l.product_id.id,
                    'product_qty': l.move_qty,
                    'product_uom': l.product_id.uom_id.id,
                    'name': l.product_id.name,
                    'location_id': wizard.location_id.id,
                    'location_dest_id': wizard.location_dest_id.id,
            }))
        pick_data = {
            'name': self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out'),
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
            'partner_id': so.partner_id.id,
            'origin': so.name,
            'sale_id': so.id,
            'move_lines': move_lines,
            'location_id': wizard.location_id.id,
            'carrier_id': wizard.carrier_id  and  wizard.carrier_id.id,
            'need_express_count': wizard.need_express_count,
        }
        
        pick_id = pick_obj.create(cr, uid, pick_data, context=context)
        return {
            'name': u'调拨出库单',
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'stock.picking.out',
            'res_id': pick_id,
            "domain": [('id', 'in', [pick_id])],
            'type': 'ir.actions.act_window',
        }
        
        
sale_adjustable_goods()

###############################