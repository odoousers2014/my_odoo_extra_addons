# -*- coding: utf-8 -*-
##############################################################################
from osv import osv, fields


class quickly_shop_establish(osv.osv_memory):
    _name = 'quickly.shop.establish'
    _columns = {
        'name': fields.char(u'Shop Name', size=100,),
    }

    def apply(self, cr, uid, ids, context=None):
        warehouse_obj = self.pool.get('stock.warehouse')
        location_obj = self.pool.get('stock.location')
        shop_obj = self.pool.get('sale.shop')
        mod_obj = self.pool.get('ir.model.data')
        wizard = self.browse(cr, uid, ids[0], context=context)
        name = wizard.name

        #create view location
        view_location_id = location_obj.create(cr, uid, {
            'name': name,
            'usage': 'view',
            'active': True,
            'location_id': mod_obj.get_object_reference(cr, uid, 'stock', 'stock_location_locations')[1],
        }, context=context)
        
        # create internal location
        lot_out_id = location_obj.create(cr, uid, {
            'name': name + u'出库',
            'usage': 'internal',
            'active': True,
            'location_id': view_location_id,
            'chained_location_type': 'customer',
            'chained_auto_packing': 'transparent',
            'chained_picking_type': 'out',
            'chained_journal_id': mod_obj.get_object_reference(cr, uid, 'stock', 'journal_delivery')[1],
        }, context=context)
        lot_stock_id = location_obj.create(cr, uid, {
            'name': name + u'库存',
            'usage': 'internal',
            'active': True,
            'location_id': view_location_id,
        }, context=context)
        
        #create warhouse
        warehouse_id = warehouse_obj.create(cr, uid, {
            'name': name,
            'lot_input_id': lot_stock_id,
            'lot_stock_id': lot_stock_id,
            'lot_output_id': lot_out_id,
        }, context=context)
        
        #create shop
        payment_default_id = mod_obj.get_object_reference(cr, uid, 'account', 'account_payment_term_net')[1]
        pricelist_id = mod_obj.get_object_reference(cr, uid, 'product', 'list0')[1]

        shop_id = shop_obj.create(cr, uid, {
            'name': name,
            'warehouse_id': warehouse_id,
            'payment_default_id': payment_default_id,
            'pricelist_id': pricelist_id,
        }, context=context)
        
        return shop_id
    

quickly_shop_establish()

################################