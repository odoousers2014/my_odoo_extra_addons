# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp import netsvc
from openerp.tools.translate import _

#其它出入库单
class okgj_order_picking_internal(osv.osv):
    _name = "okgj.order.picking.internal"
    _description = 'Picking internal'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
okgj_order_picking_internal()

class okgj_order_picking_internal_line(osv.osv):
    
    def _amount_line(self, cr, uid, ids, field_names, arg, context=None):
        """ 
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        result = {}.fromkeys(ids, 0.0)
        for one_line in self.browse(cr, uid, ids, context=context):
            result[one_line.id] = one_line.price_unit * one_line.product_qty
        return result

    _name = "okgj.order.picking.internal.line"
    _description = 'Picking internal Line'
    _columns = {
        'product_id':fields.many2one('product.product', u'商品', required=True, domain=[('is_group_product', '=', False)]),
        'prodlot_id':fields.many2one('stock.production.lot', u'生产日期'),
        'product_qty':fields.float(u'数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'price_unit': fields.float(u'单价', required=True, digits_compute= dp.get_precision('Product Price')),
        ## 'price_subtotal': fields.float('金额', digits_compute= dp.get_precision('Product Price')),
        'price_subtotal': fields.function(_amount_line, string=u'金额', digits_compute= dp.get_precision('Account')), 
        'product_uom': fields.many2one('product.uom', u'计量单位', required=True),
        'internal_order_id': fields.many2one('okgj.order.picking.internal', 'Order Reference', select=True, required=True, ondelete='cascade'),
    }
    
    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id,
                            product_qty, product_uom, price_unit=False, context=None):
        """
        onchange handler of product_id.
        """
        if context is None:
            context = {}
        res = {'value': {'price_unit': price_unit or 0.0, 'product_uom' : product_uom or False}}
        if not product_id:
            return res
        product_product_obj = self.pool.get('product.product')
        product_pricelist_obj = self.pool.get('product.pricelist')
        product = product_product_obj.browse(cr, uid, product_id, context=context)
        # - set a domain on product_uom
        res['domain'] = {'product_uom': [('category_id','=',product.uom_id.category_id.id)]}
        if not product_uom:
            product_uom_id = product.uom_id.id
            res['value'].update({'product_uom': product_uom_id})
        price = product.standard_price
        #取商品物流中心成本价
        warehouse_id = context.get('warehouse_id', False)
        if warehouse_id:
            price = product_product_obj.get_okgj_product_warehouse_cost(cr, uid, warehouse_id, [product_id]).get(product_id, 0.0)
        res['value'].update({'price_unit': price})
        return res

    ## def onchange_product_qty_price(self, cr, uid, ids, product_qty=False, price_unit=False, context=None):
    ##     """ On change of product id, finds UoM
    ##     @param prod_id: Changed Product id
    ##     @return: Dictionary of values
    ##     """
    ##     if not product_qty or not price_unit:
    ##         return {}
    ##     result = {
    ##         'price_subtotal': product_qty * price_unit,
    ##     }
    ##     return {'value': result}

okgj_order_picking_internal_line()

class okgj_order_picking_internal(osv.osv):
    _inherit = "okgj.order.picking.internal"
    _order ="name desc"
    _columns = {
        'create_uid':fields.many2one('res.users', u'创建人', readonly='True'),
        'create_date':fields.datetime(u'创建时间', readonly='True'),
        'name': fields.char(u'其它出入库单号', size=64, required=True, select=True, states={'draft':[('readonly', False)]}, readonly=True),
        'date_planned': fields.date(u'出入库日期', required=True, select=True, states={'draft':[('readonly', False)]}, readonly=True),
        'line_ids':fields.one2many('okgj.order.picking.internal.line', 'internal_order_id', u'商品明细', states={'draft':[('readonly', False)]}, readonly=True),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True,states={'draft':[('readonly', False)]}, readonly=True),
        'dest_warehouse_id':fields.many2one('stock.warehouse', u'目的物流中心', required=True,states={'draft':[('readonly', False)]}, readonly=True),
        'in_location_id':fields.many2one('stock.location', u'发货仓', states={'draft':[('readonly', False)]}, readonly=True),
        'out_location_id':fields.many2one('stock.location', u'收货仓', states={'draft':[('readonly', False)]}, readonly=True),
        'journal_id':fields.many2one('stock.journal', u'业务类型', states={'draft':[('readonly', False)]}, readonly=True),
        'state': fields.selection([('draft', u'草稿'), ('confirmed', u'确认'), ('done', u'完成'), ('cancel', u'取消')], u'状态', required=True, readonly=True),
        'invoice_state': fields.selection([('2binvoiced', u'开票'), ('none', u'不开票')], u'发票', required=True, states={'draft':[('readonly', False)]}, readonly=True),
        'pricelist_id':fields.many2one('product.pricelist', u'价格表', readonly=True, states={'draft':[('readonly',False)]}),
        'type': fields.selection([('in', 'IN'), ('out', 'OUT'), ('internal', 'INTERNAL')], u'类型', required=True, states={'draft':[('readonly', False)]}, readonly=True),
        'note':fields.text(u'备注')
    }
    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'okgj.picking.internal'),
        'date_planned': fields.date.context_today,
        'state': lambda *args: 'draft',
        'invoice_state': lambda *a: 'none',
    }

    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
        """
        onchange handler of warehouse
        """
        if context is None:
            context = {}
        if warehouse_id:
            location_id = self.pool.get('stock.warehouse').read(cr, uid, warehouse_id, ['lot_stock_id'], context=context)['lot_stock_id'][0]  
            return {'value':{'in_location_id':location_id}}
        else:
            return {}

    def onchange_dest_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
        """
        onchange handler of warehouse
        """
        if context is None:
            context = {}
        if warehouse_id:
            location_id = self.pool.get('stock.warehouse').read(cr, uid, warehouse_id, ['lot_stock_id'], context=context)['lot_stock_id'][0]  
            return {'value':{'out_location_id':location_id}}
        else:
            return {}

    def action_confirm(self, cr, uid, ids, context=None):
        """ 确认并创建picking，应该需要审核
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids selected
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        ## picking_in_obj = self.pool.get('stock.picking.in')
        ## picking_out_obj = self.pool.get('stock.picking.out')
        seq_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        for one_order in self.browse(cr, uid, ids, context=context):
            out_location_id = one_order.out_location_id
            in_location_id = one_order.in_location_id
            journal_id = one_order.journal_id.id or False
            if one_order.dest_warehouse_id:
                location_obj = self.pool.get('stock.location')
                trans_location_id = location_obj.search(cr, uid, [('usage', '=', 'transit')], context=context)
                if not trans_location_id:
                    raise osv.except_osv(_('配置错误!'), _('无公司间中转仓库'))
                okgj_type = 'okgj_internal_out'
                ttype = 'out'
                picking_obj = self.pool.get('stock.picking.out')
                move_lines = []
                for line in one_order.line_ids:
                    move_lines.append((0, 0, {
                        'name':one_order.name,
                        'date':one_order.date_planned,
                        'date_expected':one_order.date_planned,
                        'product_id':line.product_id.id,
                        #alter:09-13 16:32
                        'price_unit':line.price_unit,
                        #'price_unit':line.product_id.standard_price or 0.0,
                        'prodlot_id':line.prodlot_id.id,
                        'product_qty':line.product_qty,
                        'order_internal_line_id':line.id,
                        'product_uom':line.product_uom.id,
                        'location_id':in_location_id.id,
                        'location_dest_id':trans_location_id[0]}))
                out_picking_id = picking_obj.create(cr, uid, {
                    'name': seq_obj.get(cr, uid, 'okgj.picking.internal'),
                    'stock_journal_id':journal_id,
                    'move_lines': move_lines, 
                    'state':'draft', 
                    'type': ttype,
                    'date':one_order.date_planned,
                    'invoice_state': one_order.invoice_state,
                    'move_type':'one',
                    'okgj_type':okgj_type,
                    'internal_order_id':one_order.id,
                    }, context=context)
                wf_service.trg_validate(uid, 'stock.picking', out_picking_id, 'button_confirm', cr)
                okgj_type = 'okgj_internal_in'
                ttype = 'in'
                picking_obj = self.pool.get('stock.picking.in')
                move_lines = []
                for line in one_order.line_ids:
                    move_lines.append((0, 0, {
                        'name':one_order.name,
                        'date':one_order.date_planned,
                        'date_expected':one_order.date_planned,
                        'product_id':line.product_id.id,
                        'prodlot_id':line.prodlot_id.id,
                        #alter:09-13 16:32
                        'price_unit':line.price_unit,
                        #'price_unit':line.product_id.standard_price or 0.0,
                        'product_qty':line.product_qty,
                        'order_internal_line_id':line.id,
                        'product_uom':line.product_uom.id,
                        'location_id':trans_location_id[0],
                        'location_dest_id':out_location_id.id}))
                in_picking_id = picking_obj.create(cr, uid, {
                    'name': seq_obj.get(cr, uid, 'okgj.picking.internal'),
                    'stock_journal_id':journal_id,
                    'move_lines': move_lines, 
                    'state':'draft', 
                    'type': ttype,
                    'date':one_order.date_planned,
                    'invoice_state': one_order.invoice_state,
                    'move_type':'one',
                    'okgj_type':okgj_type,
                    'internal_order_id':one_order.id,
                    }, context=context)
                wf_service.trg_validate(uid, 'stock.picking', in_picking_id, 'button_confirm', cr)
            else:
                need_finish = False
                if (in_location_id.usage in ['internal']) and (out_location_id.usage in ['internal']):
                    okgj_type = 'okgj_internal_internal'
                    ttype = 'internal'
                    picking_obj = self.pool.get('stock.picking')
                    need_finish = True
                elif  (in_location_id.usage in ['internal']) and (out_location_id.usage in ['customer', 'supplier', 'inventory']):
                    okgj_type = 'okgj_internal_out'
                    ttype = 'out'
                    picking_obj = self.pool.get('stock.picking.out')
                elif (in_location_id.usage in ['customer', 'supplier', 'inventory']) and (out_location_id.usage in ['internal']):
                    okgj_type = 'okgj_internal_in'
                    ttype = 'in'
                    picking_obj = self.pool.get('stock.picking.in')
                else:
                    raise osv.except_osv(_('配置错误!'), _('系统无法确认出入库类型'))
                move_lines = []
                for line in one_order.line_ids:
                    move_lines.append((0, 0, {
                        'name':one_order.name,
                        'date':one_order.date_planned,
                        'date_expected':one_order.date_planned,
                        'product_id':line.product_id.id,
                        'prodlot_id':line.prodlot_id.id,
                        #alter:09-13 16:32
                        'price_unit':line.price_unit,
                        #'price_unit':line.product_id.standard_price or 0.0,
                        'product_qty':line.product_qty,
                        'order_internal_line_id':line.id,
                        'product_uom':line.product_uom.id,
                        'location_id':in_location_id.id,
                        'location_dest_id':out_location_id.id}))
                picking_id = picking_obj.create(cr, uid, {
                    'name': seq_obj.get(cr, uid, 'okgj.picking.internal'),
                    'stock_journal_id':journal_id,
                    'move_lines': move_lines, 
                    'state':'draft', 
                    'type': ttype,
                    'date':one_order.date_planned,
                    'invoice_state': one_order.invoice_state,
                    'move_type':'one',
                    'okgj_type':okgj_type,
                    'internal_order_id':one_order.id,
                    }, context=context)
                #picking_obj.action_confirm(cr, uid, picking_id, context=context)
                wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
                if need_finish:
                    picking_obj.force_assign(cr, uid, [picking_id])
                    wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_done', cr)
        #picking_obj.force_assign(cr, uid, [picking_id], context)
        self.write(cr, uid, ids, {'state':'confirmed'}, context=context)
        return True

    #为什么需要取消
    def action_cancel(self, cr, uid, ids, context=None):
        pass

okgj_order_picking_internal()

