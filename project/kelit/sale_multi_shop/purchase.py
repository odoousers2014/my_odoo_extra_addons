# -*- encoding: utf-8 -*-

from openerp.osv import osv, fields

#jon.chow<@>elico-corp.com    Apr 27, 2013
# kelit need  limit  invoice,partner,PO by shop.
# So, maybe  those object also add field  shop_id, related form SO
class purchase_order(osv.osv):
    _inherit='purchase.order'
    
    #Jon: set default shop_id 
    def _get_default_shop(self,cr,uid,context=None):
        if context is None:
            context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        if user.shop_id:
            shop_id = user.shop_id.id
        elif user.shop_ids:
            shop_id = user.shop_ids[0].id
        else:
            res = self.pool.get('sale.shop').search(cr, uid, [])
            shop_id = res and res[0] or False
        return shop_id
        
    _columns={
        'shop_id': fields.many2one('sale.shop','Shop',required=True),
    }
    _defaults={
        'shop_id': lambda self,cr,uid,context:self._get_default_shop(cr,uid,context=context),
    }
purchase_order()
