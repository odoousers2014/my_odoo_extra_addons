#-*- coding:utf-8 -*-
import logging
from osv import osv, fields
from ..sync_api import Wait_Send_Status
_logger = logging.getLogger(__name__)


class express_batch__sync(osv.osv_memory):
    _name = 'express.batch.sync'
    _columns = {
        'name': fields.char(u'Name', size=10),
    }
express_batch__sync()


class express_batch_sync_line(osv.osv_memory):
    _name = 'express.batch.sync.line'
    _columns = {
        'name': fields.char('Name', size=10),
        'api_id': fields.many2one('sync.api', 'API'),
        'wizard_id': fields.many2one('express.batch.sync', 'Wizard'),
    }
express_batch_sync_line()


class express_batch_sync(osv.osv_memory):
    _inherit = 'express.batch.sync'
    
    def _default_lines(self, cr, uid, context=None):
        api_ids = self.pool.get('sync.api').search(cr, uid, [('user_id', '=', uid)])
        return [(0, 0, {'api_id': x}) for x in api_ids]
    
    _columns = {
        'lines': fields.one2many('express.batch.sync.line', 'wizard_id', u'帐号'),
        'type': fields.selection([('printed', u'出库单已录入快递'), ('shipped', u'出库单已经发货')], u'条件'),
    }
    _defaults = {
        'type': 'shipped',
        'lines': lambda self, cr, uid, c: self._default_lines(cr, uid, context=c)
    }
    
    def apply(self, cr, uid, ids, context=None):
        _logger.info('express_batch_sync start')
        
        api_obj = self.pool.get('sync.api')
        pick_obj = self.pool.get('stock.picking')
        wizard = self.browse(cr, uid, ids[0], context=context)
        if not wizard.lines:
            raise osv.except_osv((u"Error"), (u"请至少选择一个帐号"))
        
        #test connect
        apis = [x.api_id for x in wizard.lines]
        api_ids = [x.id for x in apis]
        for api in apis:
            if not api_obj.connection_test(cr, uid, api.id, context=context, popup=False):
                raise osv.except_osv((u"Error"), (u"帐号连接失败，请确认 %s" % api.name))

        #search picking.out
        domain = [('platform_so_state', 'in', Wait_Send_Status), ('express_id', '!=', False),
                  ('api_id', 'in', api_ids), ('type', '=', 'out')]
        if wizard.type == 'shipped':
            domain.append(('state', '=', 'done'))
        pick_ids = pick_obj.search(cr, uid, domain, context=context)
        if not pick_ids:
            raise osv.except_osv((u"Error"), (u"没有找到符合条件的出库单"))
        
        #sync express
        _logger.info('wizardpicking todo %s' % pick_ids)
        so_ids = pick_obj.express_post_to_platform(cr, uid, pick_ids, context=context)
        
        _logger.info('express_batch_sync End')
        return {
            'name': ('Sales Orders'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'sale.order',
            "domain": [('id', 'in', so_ids)],
            'type': 'ir.actions.act_window',
        }
    

express_batch_sync()


####################################################################
