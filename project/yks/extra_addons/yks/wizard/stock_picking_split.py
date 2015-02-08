# -*- coding: utf-8 -*-
##############################################################################
from lxml import etree
from openerp.osv import osv, fields


class stock_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"
    
    def _default_carrier(self, cr, uid, context=None):
        pick_id = context.get('active_id')
        return False
        carrier_id = self.pool.get('stock.picking.out').read(cr, uid, pick_id, ['carrier_id'])['carrier_id']
        return carrier_id
    
    _columns = {
        'carrier_id': fields.many2one('delivery.carrier', u'快递方式'),
        'need_express_count': fields.integer(u'拆分后需要快递单数量'),
    }
    
    _defaults = {
        #'carrier_id': lambda self, cr, uid, c: self._default_carrier(cr, uid, context=c),
        #'need_express_count': 1,
    }

    def do_partial(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        if context.get('split'):
            self._split_check(cr, uid, ids, context=context)
            #split express info pass by context
            context.update({
                'carrier_id': wizard.carrier_id.id,
                'need_express_count': wizard.need_express_count,
            })
        return super(stock_partial_picking, self).do_partial(cr, uid, ids, context=context)
    
    def _split_check(self, cr, uid, ids, context):
        wrsa_obj = self.pool.get('wms.report.stock.available')
        wizard = self.browse(cr, uid, ids[0], context=context)
        location_id = wizard.picking_id.location_id.id
        for line in wizard.move_ids:
            if line.quantity <= 0 or line.quantity > line.move_id.product_qty:
                raise osv.except_osv(u'Error', u'拆分数量必须大于0，且不大于出库数量')
            info_qty = wrsa_obj.get_qty(cr, uid, line.product_id.id, location_id, context=context)
            if line.quantity > info_qty['product_qty_a']:
                raise osv.except_osv(u'Error', u'拆分数量大于库存可用数量，请减少拆分数量')
        return True
    
    def default_get(self, cr, uid, fields, context=None):
        wrsa_obj = self.pool.get('wms.report.stock.available')
        move_obj = self.pool.get('stock.move')
        
        res = super(stock_partial_picking, self).default_get(cr, uid, fields, context=context)
        if context.get('split'):
            moves = res.get('move_ids')
            if moves:
                for line in res['move_ids']:
                    #info_qty = wrsa_obj.get_qty(cr, uid, line['product_id'], line['location_id'], context=context)
                    #move_qty = move_obj.read(cr, uid, line['move_id'], ['product_qty'],)['product_qty']
                    #qty = move_qty <= info_qty['product_qty_a'] and move_qty or info_qty['product_qty_a']
                    line.update({'quantity': 0})
        return res
    
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(stock_partial_picking, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if context.get('split') and view_type == 'form':
            doc = etree.XML(res['arch'])
            doc.xpath("//button[@name='do_partial']")[0].set('string', u'拆单')
            res['arch'] = etree.tostring(doc)
        return res
    
stock_partial_picking()

############################