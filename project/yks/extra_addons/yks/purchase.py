# -*- coding: utf-8 -*-
##############################################################################
from openerp.osv import  osv, fields
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import  time


class  wizard_pol_fill_(osv.osv_memory):
    _name = "wizard.pol.fill"
wizard_pol_fill_()


class wizard_pol_fill_line(osv.osv_memory):
    _name = "pol.fill.line"
    _columns = {
        'wizard_id': fields.many2one('wizard.pol.fill', 'Parent Wizard'),
        'product_id': fields.many2one('product.product', u'商品', required=True),
        'qty': fields.float(u'待购数量', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'price': fields.float(u'价格', digits=(4, 3)),
    }
wizard_pol_fill_line()


class  wizard_pol_fill(osv.osv_memory):
    _inherit = "wizard.pol.fill"
    _columns = {
        'line_ids': fields.one2many('pol.fill.line', 'wizard_id', string='Products'),
        'product_ids': fields.many2many('product.product', 'polfill_product_rel', 'product_id', 'polfill_id', 'Products'),
    }

    def do_fill(self, cr, uid, ids, context=None):
        po_obj = self.pool.get('purchase.order')
        po_id = context.get('active_id', )
        wizard = self.browse(cr, uid, ids[0], context=context)

        date_planned = time.strftime('%Y-%m-%d')
        line = [(5,), ]
        for p in wizard.product_ids:
            line.append((0, 0, {
                    'product_id': p.id,
                    'product_qty': 1,
                    'price_unit': 0.0,
                    'name': p.name,
                    'date_planned': date_planned}))
        po_obj.write(cr, uid, po_id, {'order_line': line})

        return True
wizard_pol_fill()


class purcahse_order(osv.osv):
    _inherit = 'purchase.order'

    def onchange_partner_id(self, cr, uid, ids, partner_id, ):
        res = super(purcahse_order, self).onchange_partner_id(cr, uid, ids, partner_id,)
        note = None
        if partner_id:
            partner_pool = self.pool.get('res.partner')
            note = partner_pool.read(cr, uid, partner_id, ['comment'])['comment']
        res['value'].update({'notes': note})
        return res

    def action_pol_fill(self, cr, uid, ids, context=None):
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': "wizard.pol.fill",
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }
        
    def _prepare_order_picking(self, cr, uid, order, context=None):
        res = super(purcahse_order, self)._prepare_order_picking(cr, uid, order, context=context)
        res.update({'location_dest_id': order.warehouse_id.lot_stock_id.id})
        return res
        
    
purcahse_order()


class purcahse_order_line(osv.osv):
    _inherit = 'purchase.order.line'
    _columns = {
        'create_uid': fields.many2one('res.users', u'创建人'),
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ['draft', 'cancel']:
                raise osv.except_osv(_('Invalid Action!'), _('Cannot delete a purchase order line which is in state \'%s\'.') % rec.state)
        return super(purcahse_order_line, self).unlink(cr, uid, ids, context=context)

purcahse_order_line()

##############################################################################
