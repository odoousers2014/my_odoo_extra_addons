# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import  osv, fields
from openerp import netsvc
from ..sale_back import Picking_Out_status


class picking_batch_done_(osv.osv_memory):
    _name = 'picking.batch.done'
    _columns = {
        'name': fields.char('Name', size=10),
    }
picking_batch_done_()


class picking_batch_done_line(osv.osv_memory):
    _name = 'picking.batch.done.line'
    _columns = {
        'name': fields.char('Name', size=10),
        'wizard_id': fields.many2one('picking.batch.done'),
        'pick_id': fields.many2one('stock.picking.out', u'出库单'),
        'state': fields.selection(Picking_Out_status, u'状态'),
        'so_id': fields.many2one('sale.order', u'销售订单'),
        'platform_so_id': fields.char(u'交易编号', size=50, help=u"例如淘宝TID",),
        'receive_user': fields.char(u'收件人', size=20),
        'receive_address': fields.char(u'收货地址', size=80),
        
    }
    

class picking_batch_done(osv.osv_memory):
    _inherit = 'picking.batch.done'
    
    def _default_lines(self, cr, uid, context=None):
        pick_ids = context.get('active_ids', [])
        lines = []
        for p in self.pool.get('stock.picking.out').browse(cr, uid, pick_ids, context=context):
            if p.state not in ['confirmed', 'assigned']:
                continue
            lines.append((0, 0, {
                'pick_id': p.id,
                'so_id': p.sale_id and p.sale_id.id or False,
                'platform_so_id': p.platform_so_id,
                'receive_user': p.receive_user,
                'receive_address': p.receive_address,
                'state': p.state,
            }))
                         
        return lines

    _columns = {
        'lines': fields.one2many('picking.batch.done.line', 'wizard_id', 'Line'),
    }
    
    _defaults = {
        'lines': lambda self, cr, uid, c: self._default_lines(cr, uid, context=c)
    }
    
    def apply(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        pick_mod = 'stock.picking'
        pick_obj = self.pool.get(pick_mod)
        pick_ids = context.get('active_ids', [])
        #check
        picks = pick_obj.browse(cr, uid, pick_ids, context=context)
        to_check_ids = [p.id for p in picks if p.state == 'confirmed']
        pick_obj.action_assign(cr, uid, to_check_ids)
        #done
        picks_2 = pick_obj.browse(cr, uid, pick_ids, context=context)
        to_done_ids = [p.id for p in picks_2 if p.state == 'assigned']
        for to_done_id in to_done_ids:
            wf_service.trg_validate(uid, pick_mod, to_done_id, 'button_done', cr)
        
        return {
            'name': u'批量出库',
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'stock.picking.out',
            "domain": [('id', 'in', pick_ids)],
            'type': 'ir.actions.act_window',
        }

picking_batch_done()
##########################################