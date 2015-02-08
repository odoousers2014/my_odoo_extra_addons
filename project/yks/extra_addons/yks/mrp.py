# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import osv, fields


class mrp_bom(osv.osv):
    _inherit = 'mrp.bom'

    def _check_bom_product(self, cr, uid, ids, context=None):
        for bom in self.browse(cr, uid, ids, context=context):
            same_ids = self.search(cr, uid, [('bom_id', '=', False), ('product_id', '=', bom.product_id.id)])
            if same_ids and len(same_ids) > 1:
                return False
            if not bom.bom_id and bom.product_id.supply_method != 'produce':
                return False

        return True

    _defaults = {
        'type': lambda *a: 'phantom',
    }

    _constraints = [
        (_check_bom_product, u'不能为一个组合品创建多个BOM, 也不能为非组合品创建BOM', ['product_id', 'bom_id']),
    ]

mrp_bom()










##########################################