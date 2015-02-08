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

from openerp.osv import fields,osv

class stock_picking(osv.osv):
    _inherit='stock.picking'
    _table='stock_picking'
    _columns={
        'shop_id': fields.many2one('sale.shop', 'Shop', help='The current shop related to the user'),
    }
    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        res = super(stock_picking, self)._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
        if  picking.shop_id:
            res.update({'shop_id': picking.shop_id.id})
        return res
stock_picking()

class stock_picking_out(osv.osv):
    _inherit='stock.picking.out'
    _table='stock_picking'
    _columns={
        'shop_id': fields.many2one('sale.shop', 'Shop', help='The current shop related to the user'),
    }
stock_picking_out()


class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'shop_id': fields.many2one('sale.shop' ,'Shop'),                    
    }
account_invoice()



        


