# -*- coding: utf-8 -*-
##############################################################################
from osv import osv, fields


class sync_single_so(osv.osv_memory):
    _name = 'sync.single.so'
    _columns = {
        'name': fields.char(u'交易编号', size=50),
        'api_id': fields.many2one('sync.api', u'帐号'),
    }
    
    def apply(self, cr, uid, ids, context=None):
        so_obj = self.pool.get('sale.order')
        api_obj = self.pool.get('sync.api')
        wizard = self.browse(cr, uid, ids[0], context=context)
        data = api_obj.reget_order(cr, uid, wizard.api_id, wizard.name, context=context)
        if data and not data.get('user_id'):
            data['user_id'] = uid
        if data:
            so_id = so_obj.create(cr, uid, data, context=context)
            return {
                'name': 'Sales Orders',
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'sale.order',
                'res_id': so_id,
                'type': 'ir.actions.act_window',
            }
            
        return True
sync_single_so()


#################################################