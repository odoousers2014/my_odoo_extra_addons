# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import  osv, fields
#from openerp.tools.translate import _


class picking_cancel_check(osv.osv_memory):
    _name = 'picking.cancel.check'
    
    def _default_shop(self, cr, uid, context=None):
        return self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'sale_shop_1')[1]

    _columns = {
        'name': fields.char(u'Name', size=128, ),
        'shop_id': fields.many2one('sale.shop', u'订单的发货商店'),
    }
    
    _defaults = {
        'shop_id': lambda self, cr, uid, c: self._default_shop(cr, uid, context=c),
    }
    
    def apply(self, cr, uid, ids, context=None):
        pick_obj = self.pool.get('stock.picking.out')
        wizard = self.browse(cr, uid, ids[0], context=context)
        shop_id = wizard.shop_id.id
        pick_ids = pick_obj.search(cr, uid, [('state', '=', 'assigned'), ('shop_id', '=', shop_id), ('type', '=', 'out')])
        
        if pick_ids:
            pick_obj.relieve_assign(cr, uid, pick_ids)
            return {
                'name': u'被取消检查可用的出库单',
                'view_type': 'form',
                "view_mode": 'tree,form,graph',
                'res_model': 'stock.picking.out',
                "domain": [('id', 'in', pick_ids)],
                'type': 'ir.actions.act_window',
            }
        else:
            raise osv.except_osv(u'无效操作！', u'没有发现需要取消检查可用的出库单据')

picking_cancel_check()


class picking_auot_check(osv.osv_memory):
    _name = 'picking.auot.check'
    
    _columns = {
        'name': fields.char(u'Name', size=128, ),
        'location_id': fields.many2one('stock.location', u'库位'),
    }
    
    _defaults = {
        'location_id': 12,
    }
    
    def apply(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        location_id = wizard.location_id.id
        self.pool.get('stock.picking').auto_aciotn_assign(cr, uid, location=location_id, context=context)
        return True

picking_auot_check()


##############################################################################
