# -*- coding: utf-8 -*-
##############################################################################
from openerp.osv import osv


class product_pricelist_version(osv.osv):
    
    def _default_pricelist(self, cr, uid, context=None):
        return self.pool.get('ir.model.data').get_object_reference(cr, uid, 'yks', 'product_pricelist_wholesale')[1]
        
    _inherit = 'product.pricelist.version'
    _defaults = {
        'pricelist_id': lambda self, cr, uid, c: self._default_pricelist(cr, uid, context=c),
    }

product_pricelist_version()
##############################################################################
