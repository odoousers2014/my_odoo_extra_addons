# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

#拣货物流中心设置，如何取物流中心默认值？

#汇拣单打印
class okgj_multi_order_print(osv.osv):
    _name = "okgj.multi.order.print"
okgj_multi_order_print()

class okgj_multi_order_print_line(osv.osv):
    _name = "okgj.multi.order.print.line"
okgj_multi_order_print_line()

class okgj_stock_picking_collect(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        #复核单字段
        'collect_state':fields.selection([('not', 'NOT'), ('yes', 'YES')], 'Collect Print State', required=True),
        'collect_id':fields.many2one('okgj.multi.order.print', 'Print'),
        'collect_line_id':fields.many2one('okgj.multi.order.print.line', 'Print'),
    }
    _defaults = {
        'collect_state': lambda *args: 'not',
    }

class okgj_multi_order_print_line(osv.osv):
    _inherit = "okgj.multi.order.print.line"
    _columns = {
        'print_id':fields.many2one('okgj.multi.order.print', 'Print'),
        'product_id':fields.many2one('product.product', u'商品'),
        'product_qty': fields.float(u'数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_uom': fields.many2one('product.uom', u'计量单位'),
        'rack':fields.char(u'货架', size=64),
        'orders':fields.text(u'发货单'),
    }
okgj_multi_order_print_line()

class okgj_multi_order_print(osv.osv):
    _inherit = "okgj.multi.order.print"
    _columns = {
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True),
        'picking_ids':fields.one2many('stock.picking', 'collect_id', u'发货单', domain=[('type', '=', 'out')], required=True),
        'line_ids':fields.one2many('okgj.multi.order.print.line', 'print_id', 'Lines', required=True),
    }

    def create(self, cr, uid, vals, context=None):
        picking_ids = vals.get('picking_ids', False)
        self.pool.get('stock.picking').write(cr, uid, picking_ids[0][2], {'collect_state':'yes'}, context=context)
        return super(okgj_multi_order_print, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        raise osv.except_osv(_('Error!'), _(u'汇拣单不允许修改!'))

    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Error!'), _(u'汇拣单不允许删除!'))

    def onchange_picking_ids(self, cr, uid, ids, warehouse_id=False, picking_ids=False, context=None):
        """ On change of warehouse_id, picking_ids
        @return: Dictionary of values
        """
        if (not warehouse_id) or (not picking_ids):
            return {}
        picking_ids = picking_ids[0][2]
        picking_data = self.pool.get('stock.picking').browse(cr, uid, picking_ids, context=context)
        print_product = {} #以商品ID为key
        uom_obj = self.pool.get('product.uom')
        for one_picking in picking_data:
            picking_name = one_picking.name
            collect_state = one_picking.collect_state
#            if collect_state == 'yes':
#                raise osv.except_osv(_('Invalid Action!'), _(u"单据'%s'已生成汇拣单!") % (picking_name))
            move_lines = one_picking.move_lines
            for one_move in move_lines:
                product_id = one_move.product_id.id
                product_base_uom = one_move.product_id.uom_id.id
                move_uom = one_move.product_uom.id
                product_real_qty = one_move.product_qty
                if product_base_uom != move_uom:
                    product_real_qty = uom_obj._compute_qty(cr, uid, move_uom, one_move.product_qty, product_base_uom)
                if print_product.get(product_id, False):
                    print_product[product_id]['product_qty'] += product_real_qty
                    print_product[product_id]['orders'] =  print_product[product_id]['orders'] + ', ' + picking_name
                else:
                    product_rack = ''
                    product_racks = one_move.product_id.product_rack_ids
                    for one_rack in product_racks:
                        if one_rack.warehouse_id.id == warehouse_id:
                            product_rack = one_rack.name
                            break
                    print_product[product_id] = {
                        'product_id':product_id,
                        'product_qty':product_real_qty,
                        'product_uom':product_base_uom,
                        'rack':product_rack,
                        'orders':picking_name,
                    }
        values = [print_product[product_key] for product_key in print_product.keys()]
        #注意one2many返回格式
        return {'value': {'line_ids' : values}}

    def do_print(self, cr, uid, ids, context=None):
        '''打印汇拣单'''

        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        line_data_obj = self.browse(cr, uid, ids[0], context=context)
        datas = {}
        datas['form'] = []        
        for line_data in line_data_obj.line_ids: 
            datas['form'].append({
                                 'product_id': line_data.product_id.name,      
                                 'product_qty': line_data.product_qty,  
                                 'product_uom': line_data.product_uom.name,    
                                 'rack': line_data.rack,         
                                 'orders': line_data.orders,                                                                                                                                                     
                       }) 
        datas['model'] = 'okgj.multi.order.print'
        datas['ids'] = ids             
        return {'type': 'ir.actions.report.xml', 'report_name': 'okgj.multi.order.print', 'datas': datas, 'nodestroy': True}

okgj_multi_order_print()

