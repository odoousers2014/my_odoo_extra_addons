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


class stock_change_product_qty(osv.osv_memory):
    _inherit = "stock.change.product.qty"

    def default_get(self, cr, uid, fields, context):
        res = super(stock_change_product_qty, self).default_get(
            cr, uid, fields, context)

        location_pool = self.pool.get('stock.location')
        company_id = self.pool.get('res.users').browse(
            cr, uid, uid,).company_id.id

        location_id = location_pool.search(
            cr, uid, [('company_id', '=', company_id),
                      ('usage', '=', 'internal'),
                      ('name', 'ilike', 'stock')])
        location_id = location_id and location_id[0] or False
        res.update({'location_id': location_id})
        return res

stock_change_product_qty()
