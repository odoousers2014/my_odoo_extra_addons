# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Camptocamp 2012
#    Author : Joel Grand-Guillaume
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
from datetime import datetime
from osv import osv, fields
from tools.translate import _
import netsvc
import time
import tools
from tools.safe_eval import safe_eval


class sale_order(osv.osv):
    _inherit = "sale.order"

    _columns = {
        'delivery_type': fields.selection([
            ('standard', 'Standard'),
            ('consignment', 'Consignment'),
        ], 'Delivery Type', required=True, readonly=True, states={'draft': [('readonly', False)]},
        help="Select consignment if you want this SO to be delivered in the consignment location of the selected partner. Leave standard to deliver to the customer as usual. "),
    }

    _defaults = {
        'delivery_type': 'standard',
    }
    
    
    # def _find_so_base_action_rule_id(self, cr,uid,context=None):
    #     rule_id = None
    #     model_data_obj = self.pool.get('ir.model.data')
    #     # Find the rule created in the data.xml
    #     model_res_id = model_data_obj.search(cr, uid, [('model','=','base.action.rule'),('name','=',BASE_ACTION_RULE_SO)], context)
    #     model_res = model_data_obj.browse(cr,uid,model_res_id, context)
    #     if model_res and len(model_res) == 1:
    #         rule_id = int(model_res[0].res_id)
    #     return rule_id
    
    
    # def action_wait(self, cr, uid, ids, *args):
    #     """Send a mail using the action. Cannot use the do_action method cause mail
    #     was send multiple time wihtou explaination. I use directly email_send one instaed.
    #     Pay attention I had to recode part of the email_to, email_from algo here."""
        
        
    #     user = self.pool.get('res.users').browse(cr, uid, uid)
    #     res = super(sale_order, self).action_wait(cr, uid, ids, *args)
    #     act_rule_obj = self.pool.get('base.action.rule')
    #     so_obj = self.pool.get('sale.order')
    #     rule_id = self._find_so_base_action_rule_id(cr, uid)
    #     if not rule_id:
    #         raise osv.except_osv(_('Warning !'), _('Cannot find the related rule to send email on order confirmation. !'))
    #     rule_action = act_rule_obj.browse(cr,uid,rule_id)
    #     for obj in self.browse(cr, uid, ids):
    #         locals_for_emails = {
    #             'user' : user,
    #             'obj' : obj,
    #         }
    #         email_to = tools.ustr(rule_action.act_email_to)
    #         from_email= tools.ustr(rule_action.act_email_from)
    #         # Taken from send_mail in base_action_rule
    #         try:
    #             from_email= safe_eval(from_email, {}, locals_for_emails)
    #         except:
    #             pass
    #         try:
    #             email_to = safe_eval(email_to, {}, locals_for_emails)
    #         except:
    #             pass
    #         print "MERDEEEEEEEEE !!!!!!!!!!!!!!!!!!!!!!!!!!"
    #         act_rule_obj.email_send(cr, uid, obj, email_to, rule_action.act_mail_body, emailfrom=from_email)
    #     return res
    
    def _prepare_order_picking(self, cr, uid, order, context=None):
        res = res = super(sale_order, self)._prepare_order_picking(cr, uid, order, context=context)
   
        if  order.delivery_type == 'consignment':
            if order.partner_id.consignment_location_id:
                res.update({'invoice_state':'none'})
            else:
                raise osv.except_osv(_('Warning !'), _('You need to setup the Consignment Location on the selected partner !'))
                
        return res
    
        
    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        res = super(sale_order, self)._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context)
        
        if order.delivery_type == 'consignment':
            if order.partner_id.consignment_location_id:
                dest_id = order.partner_id.consignment_location_id.id
                res.update({'location_dest_id': dest_id})
            else:
                raise osv.except_osv(_('Warning !'), _('You need to setup the Consignment Location on the selected partner !'))
                
        return res

    
#===============================================================================
#     def action_ship_create(self, cr, uid, ids, context=None):
#         """Override the method to write back on all related moves the destination location
#         in case the user selected 'Consignment' as delivery type
#         """
#         res = super (sale_order, self).action_ship_create(cr, uid, ids , context=context)
#         picking_obj = self.pool.get('stock.picking')
#         move_obj = self.pool.get('stock.move')
# #        procurement_obj = self.pool.get('procurement.order')
#         for order in self.browse(cr, uid, ids, context={}):
#             
#             if order.delivery_type != 'standard':
#                 if order.partner_id.consignment_location_id:
#                     dest_location_id = order.partner_id.consignment_location_id.id
#                 else:
#                     raise osv.except_osv(_('Warning !'), _('You need to setup the Consignment Location on the selected partner !'))
#                 pick_ids = picking_obj.search(cr,uid,[('sale_id','=',order.id),('state','!=','cancel')])
#                 for pick in picking_obj.browse(cr,uid,pick_ids):
#                     # In each picking not in state cancel, change dest. of move if 
#                     # consignment was chosen in the SO
#                     #import pdb;
#                     #pdb.set_trace()
#                     for move in pick.move_lines:
#                         move_obj.write(cr,uid,move.id,{'location_dest_id':dest_location_id})
#         return res
#===============================================================================

        
sale_order()


class stock_move(osv.osv):
    _inherit = 'stock.move'
    def _prepare_chained_picking(self, cr, uid, picking_name, picking, picking_type, moves_todo, context=None):
        res = super(stock_move, self)._prepare_chained_picking( cr, uid, picking_name, picking, picking_type, moves_todo, context=context)
        res.update({'shop_id':picking.shop_id and picking.shop_id.id or False })

        so = picking.sale_id or False
        if so and so.delivery_type == 'consignment':
            name =  self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.' + 'out')
            origin =  so.name +  r':' + picking.name
            res.update({'invoice_state':'2binvoiced', 'origin':origin, 'name':name})
        return res
        
stock_move()
