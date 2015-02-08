# -*- coding: utf-8 -*-
##############################################################################
from osv import osv, fields
from openerp.tools.translate import _


class so_batch_confirm(osv.osv_memory):
    _name = 'so.batch.confirm'
    _columns = {
        'name': fields.char(u'Name', size=32,),
        'select_count': fields.integer(u'选中记录数量'),
    }
    _defaults = {
        "select_count": lambda self, cr, uid, c: len(c.get('active_ids', [])),
    }
    
    def check(self, cr, uid, sale_orders, context=None):
        for so in sale_orders:
            if so.state not in ['draft', 'sent']:
                raise osv.except_osv(_('Error!'), _(u'只有询价单可以确认为销售订单，请检查'))
        return True
        
    def apply(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        so_ids = context.get('active_ids')
        so_obj = self.pool.get('sale.order')
        
        for so_id in so_ids:
            #SO action_button_confirm len(ids) must == 1
            so_obj.sale_charge_approve(cr, uid, [so_id, ], context=context)
        
        return {
            'name': _('Sales Orders'),
            'view_type': 'form',
            "view_mode": 'tree,form,graph',
            'res_model': 'sale.order',
            "domain": [('id', 'in', so_ids)],
            'type': 'ir.actions.act_window',
            'search_view_id': mod_obj.get_object_reference(cr, uid, 'sale', 'view_order_tree')[1],
        }

so_batch_confirm()

##############################################################