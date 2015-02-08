# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

#货位更新
class okgj_product_rack_change(osv.osv):
    _name = "okgj.product.rack.change"
okgj_product_rack_change()

class okgj_product_rack_change_line(osv.osv):
    _name = "okgj.product.rack.change.line"
    _columns = {
        'product_id':fields.many2one('product.product', u'商品', required=True),
        'pick_rack_id':fields.many2one('okgj.product.rack', u'拣货货位'),
        'store_rack_id':fields.many2one('okgj.product.rack', u'存货货位'),
        'change_id':fields.many2one('okgj.product.rack.change', 'Change'), 
    }
okgj_product_rack_change_line()

class okgj_product_rack_change(osv.osv):
    _inherit = "okgj.product.rack.change"
    _columns = {
        #复核单字段
        'name':fields.char(u'单号', size=16),
        'state':fields.selection([('draft', 'Draft'), ('done', 'Done')], 'Collect Print State', required=True),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True),
        'line_ids':fields.one2many('okgj.product.rack.change.line', 'change_id', u'明细行'),
    }
    _defaults = {
        'state': lambda *args: 'draft',
    }

    def action_done(self, cr, uid, ids, context=None):
        for one_form in self.browse(cr, uid, ids, context=context):
            warehouse_id = one_form.warehouse_id.id
            product_obj = self.pool.get('product.product')
            rack_obj = self.pool.get('okgj.product.rack')
            for one_line in one_form.line_ids:
                if (one_line.pick_rack_id.warehouse_id.id != warehouse_id) or (one_line.store_rack_id.warehouse_id.id != warehouse_id):
                    raise osv.except_osv(_('Error!'),_("物流中心不符，无法完成更新"))
                product_id = one_line.product_id.id
                pick_rack_id = one_line.pick_rack_id.id
                store_rack_id = one_line.store_rack_id.id
                product_data = product_obj.read(cr, uid, product_id, ['product_pick_rack_ids', 'product_store_rack_ids'], context=context)
                product_pick_rack_ids = product_data['product_pick_rack_ids']
                if pick_rack_id:
                    if not product_pick_rack_ids:
                        product_obj.write(cr, uid, product_id, {'product_pick_rack_ids':[(4, pick_rack_id)]}, context=context)
                    else:
                        change_state = True
                        for one_rack in rack_obj.browse(cr, uid, product_pick_rack_ids, context):
                            if one_rack.warehouse_id.id == warehouse_id:
                                product_obj.write(cr, uid, product_id, {'product_pick_rack_ids':[(3, one_rack.id)]}, context=context)
                                product_obj.write(cr, uid, product_id, {'product_pick_rack_ids':[(4, pick_rack_id)]}, context=context)
                                change_state = False
                                break
                        if change_state:
                            product_obj.write(cr, uid, product_id, {'product_pick_rack_ids':[(4, pick_rack_id)]}, context=context)
                if store_rack_id:
                    product_store_rack_ids = product_data['product_store_rack_ids']
                    if not product_store_rack_ids:
                        product_obj.write(cr, uid, product_id, {'product_store_rack_ids':[(4, store_rack_id)]}, context=context)
                    else:
                        change_state = True
                        for one_rack in rack_obj.browse(cr, uid, product_store_rack_ids, context):
                            if one_rack.warehouse_id.id == warehouse_id:
                                product_obj.write(cr, uid, product_id, {'product_store_rack_ids':[(3, one_rack.id)]}, context=context)
                                product_obj.write(cr, uid, product_id, {'product_store_rack_ids':[(4, pick_rack_id)]}, context=context)
                                change_state = False
                                break
                        if change_state:
                            product_obj.write(cr, uid, product_id, {'product_store_rack_ids':[(4, store_rack_id)]}, context=context)
        return self.write(cr, uid, ids, {'state':'done'}, context=context)

okgj_product_rack_change()

