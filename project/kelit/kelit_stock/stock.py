# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Yannick Gouin <yannick.gouin@elico-corp.com>
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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class stock_picking(osv.osv):
    _inherit='stock.picking'
    _table='stock_picking'
    _columns={
        'salesman_id':fields.many2one('res.users','Salesman'),
    }
stock_picking()

class stock_picking_in(osv.osv):
    _inherit='stock.picking.in'
    _table='stock_picking'
    _columns={
        'shop_id': fields.many2one('sale.shop', 'Shop'),      
    }
stock_picking_in()

class stock_picking_out(osv.osv):
    _inherit='stock.picking.out'
    _table='stock_picking'
    
    def _get_salesman(self,cr,uid,ids,fields,arg=None,context=None):
        res={}
        for picking in self.browse(cr,uid,ids):
            salesman_id=False
            if picking.sale_id:
                if picking.sale_id.user_id:
                    salesman_id=picking.sale_id.user_id.id
            res[picking.id]=salesman_id
                    
        return res
    def _get_picking_by_so(self,cr,uid,ids,context=None):
        return self.pool.get('stock.picking.out').search(cr,uid,[('sale_id','in',ids)])
        
    _columns={
        'salesman_id':fields.function(_get_salesman,type='many2one',relation='res.users',string='Salesman',
                                      store={'sale.order':(_get_picking_by_so,['user_id'],20)}
                                      ),            
    }
    
    def _auto_init(self, cr,context=None):
        super(stock_picking_out, self)._auto_init(cr, context=context)
        
        # update stock_picking(old record) that salesman_id  is Null.
        cr.execute(""" 
        SELECT 
            so.user_id, sp.id
        FROM 
            stock_picking AS sp
            LEFT JOIN sale_order AS so ON (sp.sale_id = so.id)
        WHERE 
            sp.sale_id IS NOT Null   
        """)
        for user_picking in  cr.fetchall():
            if user_picking[0] and user_picking[1]:
                cr.execute("""   update stock_picking set (salesman_id) = (%d) where id = %d """  % (user_picking[0], user_picking[1]  ))
            
        
stock_picking_out()


class stock_move(osv.osv):
    _inherit = 'stock.move'
    
    def _default_location_destination(self, cr, uid, context=None):
        """ Gets default address of partner for destination location
        @return: Address id or False
        """
        location_id = False
        if context is None:
            context = {}
        if context.get('move_line', []):
            if context['move_line'][0]:
                if isinstance(context['move_line'][0], (tuple, list)):
                    location_id = context['move_line'][0][2] and context['move_line'][0][2].get('location_dest_id',False)
                else:
                    move_list = self.pool.get('stock.move').read(cr, uid, context['move_line'][0], ['location_dest_id'])
                    location_id = move_list and move_list['location_dest_id'][0] or False
        elif context.get('address_out_id', False):
            property_out = self.pool.get('res.partner').browse(cr, uid, context['address_out_id'], context).property_stock_customer
            location_id = property_out and property_out.id or False
 
        return location_id
 
 
    def _default_location_source(self, cr, uid, context=None):
        """ Gets default address of partner for source location
        @return: Address id or False
        """
        location_id = False
 
        if context is None:
            context = {}
        if context.get('move_line', []):
            try:
                location_id = context['move_line'][0][2]['location_id']
            except:
                pass
        elif context.get('address_in_id', False):
            part_obj_add = self.pool.get('res.partner').browse(cr, uid, context['address_in_id'], context=context)
            if part_obj_add:
                location_id = part_obj_add.property_stock_supplier.id
 
        return location_id
    _columns={
        #string  Source location ->  From location
        'location_id': fields.many2one('stock.location', 'From Location', required=True, select=True,states={'done': [('readonly', True)]}, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),      
    }

    _defaults = {
        'location_id': False,
        'location_dest_id': False,
    }

    def onchange_move_type(self, cr, uid, ids, type, context=None):
        return {}
    
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False,
                            loc_dest_id=False, partner_id=False):
        """
        Let the stock.move name is same as Product name_get, product.product name_get modify at module keit_fields
        """
        res = super(stock_move, self).onchange_product_id( cr, uid, ids, prod_id=prod_id, loc_id=loc_id,
                            loc_dest_id=loc_dest_id, partner_id=partner_id)
        product_pool = self.pool.get('product.product')
        name = product_pool.name_get(cr, uid, prod_id)[0][1]
        if name and res['value'].get('name'):
            res['value'].update({'name':name})        
        return res
    
class sale_order(osv.osv):
    _inherit='sale.order'
    def cancel_order_and_picking(self,cr,uid,ids,context=None):
        sale_id=ids[0]
        
        pick_obj=self.pool.get('stock.picking.out')
        pick_ids=pick_obj.search(cr,uid, [('sale_id','=',sale_id)] )
        picks=pick_obj.browse(cr,uid,pick_ids)
        
        if 'done' in [p.state for p in picks]:
            raise osv.except_osv(_('Warning!'),_('Can not cacel the delivery order state is done'))
        
        else:
            res = pick_obj.action_cancel(cr,uid,pick_ids,)
            if res:
                return self.action_cancel(cr,uid,ids,context=context)

sale_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: