# -*- coding: utf-8 -*-
##############################################################################
#from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
from openerp.osv import  osv, fields
from openerp import netsvc
import time
from ..sale_back import Picking_Out_status
#from openerp.tools.translate import _


class picking_scan_done_(osv.osv_memory):
    _name = 'picking.scan.done'
    _order = 'id'
    _columns = {
        'name': fields.char('Name', size=10),
    }
    _defaults = {
        'name': lambda self, cr, uid, c: time.strftime('%H:%M:%S'),
    }
    
picking_scan_done_()


class picking_scan_done_line(osv.osv_memory):
    _name = 'picking.scan.done.line'
    _columns = {
        'name': fields.char('Name', size=10),
        'wizard_id': fields.many2one('picking.scan.done', 'Wizard'),
        'picking_id': fields.many2one('stock.picking.out', u'出库单'),
        'location_id': fields.related('picking_id', 'location_id', type="many2one", relation="stock.location", string='库位', readonly=True),
        'state': fields.related('picking_id', 'state', type="selection", selection=Picking_Out_status, string=u'状态', readonly=True),
        'platform_so_id': fields.related('picking_id', 'platform_so_id', type="char", string=u'交易编号', size=50, readonly=True),
        'receive_user': fields.related('picking_id', 'receive_user', type="char", string=u'收件人', size=20, readonly=True),
       'receive_address': fields.related('picking_id', 'receive_address', type="char", string=u'收货地址', size=80, readonly=True),
        
    }
picking_scan_done_line()


class picking_scan_done(osv.osv_memory):
    _inherit = 'picking.scan.done'
    _columns = {
        'scan_input': fields.char(u'快递条码', size=40),
        'lines': fields.one2many('picking.scan.done.line', 'wizard_id', 'Lines'),
        'manner': fields.selection([('1', u'立即发货'), ('2', u'扫入后确认')], u'方式')
    }
    _defaults = {
        'manner': '2',
    }

    def onchange_scan_input(self, cr, uid, ids, scan_input, lines, context=None):
        #print ids
        #print scan_input
        #print "lines", lines
        pick_obj = self.pool.get('stock.picking')
        
        picking_ids = []
        for i in lines:
            if i[0] == 0:
                picking_ids.append(i[2]['picking_id'])
            if i[0] == 4:
                picking_ids.append(i[1])
                
        if scan_input:
            if 'stock.picking:' in scan_input:
                pick_id = int(scan_input.split(':')[-1])
                pick = pick_obj.browse(cr, uid, pick_id, context=context)
                
                if pick_id not in picking_ids:
                    lines.append((0, 0, {
                        'picking_id': pick_id,
                        'state': pick.state,
                        'location_id': pick.location_id and pick.location_id.id,
                        'platform_so_id': pick.platform_so_id,
                        'receive_user': pick.receive_user,
                        'receive_address': pick.receive_address,
                    }))
            
        return {'value': {'scan_input': False, 'lines': lines}}
    
    def apply(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=context)
        wf_service = netsvc.LocalService("workflow")
        picks = [x.picking_id for x in wizard.lines]
        todo_ids = [p.id for p in picks if p.state == 'assigned']
        for pid in todo_ids:
            wf_service.trg_validate(uid, 'stock.picking', pid, 'button_done', cr)
        return True

picking_scan_done()
############################################
