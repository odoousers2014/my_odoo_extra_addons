# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#     Jon Chow <jon.chow@elico-corp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#     Jon Chow <jon.chow@elico-corp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv
from openerp.addons.purchase.purchase import purchase_order as PURCHASE_ORDER


def new_prepare_order_line_move(self, cr, uid, order, order_line,
                                picking_id, context=None):
    return {
        'name': order_line.name or '',
        'product_id': order_line.product_id.id,
        'product_qty': order_line.product_qty,
        'product_uos_qty': order_line.product_qty,
        'product_uom': order_line.product_uom.id,
        'product_uos': order_line.product_uom.id,
        'date': self.date_to_datetime(cr, uid, order.date_order, context),
        # order.date_orde --> order_line.date_planned,
        'date_expected': self.date_to_datetime(cr, uid,
                                               order_line.date_planned,
                                               context),
        'location_id': order.partner_id.property_stock_supplier.id,
        'location_dest_id': order.location_id.id,
        'picking_id': picking_id,
        'partner_id': order.dest_address_id.id or order.partner_id.id,
        'move_dest_id': order_line.move_dest_id.id,
        'state': 'draft',
        'type': 'in',
        'purchase_line_id': order_line.id,
        'company_id': order.company_id.id,
        'price_unit': order_line.price_unit
    }
PURCHASE_ORDER._prepare_order_line_move = new_prepare_order_line_move


class purchase_order(osv.osv):
    _inherit = 'purchase.order'

    def action_picking_create(self, cr, uid, ids, context=None):
        """
        when confirm purchase order, create picking,
        picking min_date is the min stock.move date_expected
        """
        pick_id = super(purchase_order, self).action_picking_create(
            cr, uid, ids, context=context)
        picking_pool = self.pool.get('stock.picking')

        if pick_id:
            min_date = None
            for line in picking_pool.browse(cr, uid, pick_id).move_lines:
                if min_date is None:
                    min_date = line.date_expected
                else:
                    min_date = (line.date_expected < min_date
                                and line.date_expected
                                or min_date)

            picking_pool.write(cr, uid, pick_id, {'min_date': min_date})

        return pick_id

purchase_order()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
