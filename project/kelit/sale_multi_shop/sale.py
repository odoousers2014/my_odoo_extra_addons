# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2011 Zikzakmedia S.L. (http://zikzakmedia.com)
#        All Rights Reserved, Jesús Martín <jmartin@zikzakmedia.com>
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from openerp.osv import osv, fields
from TYPES import major

class sale_shop(osv.osv):
    _inherit = "sale.shop"
    _columns = {
        'user_ids': fields.many2many('res.users', 'shop_user_rel',
                                        'user_id', 'shop_id', "Users"),
        'sequence_id': fields.many2one('ir.sequence', "Sale Order Sequence",
                        domain="[('company_id','=',company_id)]",
                        help="The sequence used for sale order numbers."),
        'journal_id': fields.many2one('account.journal', "Account Journal",
                        domain="[('company_id','=',company_id)]",
                        help="The journal used for this shop."),
        'exclude_lines_notes': fields.boolean('Exclude Order Line Notes',
                        help='Exclude copy sale description to sale order line'),
    }

sale_shop()

class sale_order(osv.osv):
    _inherit = "sale.order"
    
    def _shop_get(self, cr, uid, context=None):
        """ To get  Shop  for this order
        @return: Shop id """
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

    def _make_invoice(self, cr, uid, order, lines, context=None):
        """ To make invoice for this shop
        @input: order
        @input: lines
        @return: invoice id  """
        if context is None:
            context = {}
        invoice = self.pool.get('account.invoice')
        invoice_id = super(sale_order, self)._make_invoice(cr, uid, order,
                                                                lines, context)
        res = self._shop_get(cr, uid, context=context)
        if res:
            shop = self.pool.get('sale.shop').browse(cr, uid, res,
                                                                context=context)
            if shop.journal_id:
                invoice.write(cr, uid, invoice_id, {'journal_id': shop.journal_id.id}, context)
        return invoice_id
    
    def _get_order_name_bye_shop(self,cr,uid,shop_id,context=None):
        
        sequence_obj = self.pool.get('ir.sequence')
        shop_obj=self.pool.get('sale.shop')
        
        order_name='/'
        if shop_id: 
            shop=shop_obj.browse(cr,uid,shop_id)
            if shop.sequence_id:
                order_name = sequence_obj.next_by_id(cr, uid, shop.sequence_id.id, context=context)
            else: 
                order_name = sequence_obj.next_by_code(cr, uid,'sale.order', context=context)
        else:
            order_name = sequence_obj.next_by_code(cr, uid,'sale.order', context=context)
            
        return order_name

    _defaults = {
        'shop_id': _shop_get,
        'name': lambda *a: '/',
    }
    
    def create(self, cr, uid, vals, context=None):
        """Rewrite Create method.
        This method spend new sequence when create (not default value)
        :param vals: dicc
        :return order_id
        """
        if context is None:
            context = {}
            
        date_order = vals.get('date_order',False)
        fy_obj=self.pool.get('account.fiscalyear')
        if date_order:
            fy_ids = fy_obj.search(cr, uid, [('date_start', '<=', date_order), ('date_stop', '>=', date_order)], context=context)
            fy_id=fy_ids and fy_ids[0] or False
            context.update({'fiscalyear_id':fy_id} )

        vals.update( {'name': self._get_order_name_bye_shop(cr,uid,vals.get('shop_id',False),) })
        
        return  super(sale_order, self).create(cr, uid, vals,context=context)


    def _make_invoice(self, cr, uid, order, lines, context=None):
        if context is None:
            context = {}
        invoice_id = super(sale_order, self)._make_invoice(cr, uid, order, lines, context)
        if order and order.shop_id and order.shop_id.journal_id:
            journal_id = order.shop_id.journal_id.id
            self.pool.get('account.invoice').write(cr, uid, invoice_id, {'journal_id': journal_id}, context)
        return invoice_id
    
    #delivery order shop_id come from SO shop_id  jon.chow<@>elico-corp.com    Jun 13, 2013
    def _prepare_order_picking(self, cr, uid, order, context=None):
        res= super(sale_order, self)._prepare_order_picking(cr,uid,order,context=context)
        shop_id=order.shop_id and order.shop_id.id or False
        res.update({'shop_id': shop_id})
        return res

sale_order()

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):

        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)

        if product:
            sale_shop_obj = self.pool.get('sale.shop')
            user = self.pool.get('res.users').browse(cr, uid, uid)
            if user.shop_id.exclude_lines_notes and 'value' in res:
                if 'notes' in res['value']:
                    del res['value']['notes']
        return res
    
sale_order_line()













