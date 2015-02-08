# -*- coding: utf-8 -*-
#===============================================================================
# auther：cloudy
# date：2014/12/20
# description：客户负责人批量更改
#===============================================================================
from osv import osv, fields


class partner_change_charge(osv.osv_memory):
    """ 客户负责人批量更改"""
    _name = "partner.change.charge"
    _columns = {
        'name': fields.char(u'name', size=32),
        'res_partner': fields.many2one('res.partner', u'客户'),
        'user_id': fields.many2one('res.users', u'负责人'),
    }

    def batch_change(self, cr, uid, ids, context=None):
        """
        """
        partner_obj = self.pool.get('res.partner')
        need_ids = context.get('active_ids',)
        info = self.browse(cr, uid, ids[0], context=context)
        partner_obj.write(cr, uid, need_ids, {'user_id': info.user_id.id})
        #修改联系人的负责人
        line_ids = partner_obj.search(cr, uid, [('parent_id', 'in', need_ids)])
        partner_obj.write(cr, uid, line_ids, {'user_id': info.user_id.id})
        return True

partner_change_charge()


##############################################################################