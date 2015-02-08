# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Jon.Chow <jon.chow@elico-corp.com>
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
import time
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

from openerp.addons.sale.sale  import sale_order as SALE_ORDER
#SALE_ORDER._columns['date_order']=fields.datetime('Date', required=True, readonly=True, select=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    # jon fied readonly by some groups, 
    #  may be at the time of approve  SO ,do some check is better.
    # test   write=['base.group_admin'],read=['base.group_admin']  is not work
    # https://answers.launchpad.net/openobject-server/+question/178779 
    def _check_field_permissions(self, cr, uid, ids, field_name, arg, context):
        res = {}
        user=self.pool.get('res.users').browse(cr,uid,uid)
        flage=False
        for gp in user.groups_id:
            categ= gp.category_id and gp.category_id.name or False
            if gp.name=='Manager' and  categ=='Sales':
                flage=True
                break
        for i in ids:
            if not i:
                continue
            if flage:
                res[i]=True
            else:
                res[i]=True   # temp not user this function, so return True
        
        return  res
    
    def _def_unit_price_permission(self,cr,uid,context=None):
        user=self.pool.get('res.users').browse(cr,uid,uid)
        flage=False
        for gp in user.groups_id:
            categ= gp.category_id and gp.category_id.name or False
            if gp.name=='Manager' and  categ=='Sales':
                flage=True
                break
        # jon if default is False, the price can not be write into db , may oncchange replace readonly is better

        return flage
    _columns={
        'unit_price_permission':fields.function(_check_field_permissions,arg='123', type='boolean', method=True, string="Permissions price_unit"),
        'is_sample':fields.boolean('Sample ?',help='If set to True,This SOL only a sample,not really SOL.'),

    }
    _defaults={
        'unit_price_permission':lambda self,cr,uid,c:  True,

    }
    
    def on_discount_change(self, cr, uid, ids, discount, context=None):
        is_manager = False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        for group in user.groups_id:
            if group.name == "Manager" and group.category_id and group.category_id.name == "Sales":
                is_manager = True
        # jon ,   max_sale_discount  come from config.settings 
        config_parameter_obj = self.pool.get("sale.config.settings")
        max_sale_discount = config_parameter_obj.get_default_max_sale_discount(cr, uid, [], context=context)['max_sale_discount']

        if not is_manager and  discount > max_sale_discount:
            warning = {
                'title': _('Error!'),
                'message' : _('You can not set a discount greater than %s%%!'  %  max_sale_discount )
            }
            return {'warning': warning, 'value': {'discount':0}}
        return {}
    
    
    #TODO: product_id_change  add  arg  is_sample    
    
     
    def on_change_is_sample(self, cr, uid, ids, is_sample, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        """
        select is_sample, return price_unit:0, name:name + FREE OF CHARGE
        unselect , return  product_id_change
        """
        if not product:
            return True
        
        if is_sample == False:
            res=self.product_id_change(cr, uid, ids, pricelist, product, qty=qty,
                                              uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
                                              lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, 
                                              fiscal_position=fiscal_position, flag=flag, context=context)
            return res
        else:
            return {'value':{'price_unit':0}}
#            return {'value':{'price_unit':0, 'name':name + " - SAMPLE FREE OF CHARGE - 免费样品 " }}
        
    
sale_order_line()

#===============================================================================
# from openerp.addons.sale_stock.sale_stock import sale_order as SO
# 
# def new_prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
#     location_id = order.shop_id.warehouse_id.lot_stock_id.id
#     output_id = order.shop_id.warehouse_id.lot_output_id.id
#     return {
#         'name': line.name,
#         'picking_id': picking_id,
#         'product_id': line.product_id.id,
#         'date': date_planned,
#         'date_expected': date_planned,
#         'product_qty': line.product_uom_qty,
#         'product_uom': line.product_uom.id,
#         'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
#         'product_uos': (line.product_uos and line.product_uos.id)\
#                 or line.product_uom.id,
#         'product_packaging': line.product_packaging.id,
#         'partner_id': line.address_allotment_id.id or order.partner_shipping_id.id,
#         'location_id': location_id,
#         'location_dest_id': output_id,
#         'sale_line_id': line.id,
#         'tracking_id': False,
#         'state': 'draft',
#         #'state': 'waiting',
#         'company_id': order.company_id.id,
#         'price_unit': line.product_id.standard_price or 0.0,
#         'is_sample':line.is_sample,
# }
# SO._prepare_order_line_move=new_prepare_order_line_move
#===============================================================================




class sale_order(osv.osv):
    _inherit='sale.order'
    def _get_date_order_time(self,cr,uid,ids,field_name,arg=None,context=None):
        res={}
        return res
    
    _columns={
        #change date_order type  date->datetime   !! not change
        'date_order': fields.date('Date', required=True, readonly=True, select=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}),
    }
    _defaults = {
        'date_order': lambda *a: time.strftime('%Y-%m-%d'),
    }
    
    #Jon fix bug :  context_lang = context.copy()  AttributeError: 'NoneType' object has no attribute 'copy
    def get_salenote(self, cr, uid, ids, partner_id, context=None):
        if not context:
            context={} 
        
        context_lang = context.copy() 
        if partner_id:
            partner_lang = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context).lang
            context_lang.update({'lang': partner_lang})
        return self.pool.get('res.users').browse(cr, uid, uid, context=context_lang).company_id.sale_note
    
    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        res = super(sale_order, self)._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=None)
        res.update({'is_sample': line.is_sample})
        return res
    
sale_order()

#===============================================================================
# ##############################   date_order  field type change to  datetime 
# # those code because of date_order type change to datetime,
# # so where the code used this filed must be fix
# 
# from datetime import datetime, timedelta
# from dateutil.relativedelta import relativedelta
# from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
# def _get_date_planned(self, cr, uid, order, line, start_date, context=None):
#     # date_order type change to datetime,so the start_date need to cut the date
#     start_date=start_date[:10]
#     
#     start_date = self.date_to_datetime(cr, uid, start_date, context)
#     date_planned = datetime.strptime(start_date, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=line.delay or 0.0)
#     date_planned = (date_planned - timedelta(days=order.company_id.security_lead)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
#     return date_planned
# def _prepare_order_picking(self, cr, uid, order, context=None):
#     pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
#     return {
#         'name': pick_name,
#         'origin': order.name,
#         # order.date_order-> order.date_order[:10] date_order type change to datetime,so the start_date need to cut the date
#         'date': self.date_to_datetime(cr, uid, order.date_order[:10], context),
#         'type': 'out',
#         'state': 'auto',
#         'move_type': order.picking_policy,
#         'sale_id': order.id,
#         'partner_id': order.partner_shipping_id.id,
#         'note': order.note,
#         'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
#         'company_id': order.company_id.id,
#     }
# 
# from openerp.addons.sale_stock.sale_stock import sale_order as  SO
# setattr(SO, '_get_date_planned' , _get_date_planned)
# setattr(SO, '_prepare_order_picking' , _prepare_order_picking)
# ####################################  date_order  field type change to  datetime 
#===============================================================================


# Jon , set max_sale_discount  at  menu  SET/Generation/Sale
class sale_config_settings(osv.osv_memory):
    _inherit = 'sale.config.settings'
    _columns = {
       'max_sale_discount': fields.float('Set the max sale discount',  digits=(2,2)),
     }
    def get_default_max_sale_discount(self, cr, uid, ids, context=None):
        config_parameter_obj = self.pool.get("ir.config_parameter")
        max_sale_discount = config_parameter_obj.get_param(cr, uid, "max_sale_discount", context=context)
        return {'max_sale_discount' : float(max_sale_discount), }
    
    def set_max_sale_discount(self,cr,uid,ids,context=None):
        config_parameter_obj = self.pool.get("ir.config_parameter")
        for record in self.browse(cr, uid, ids, context=context):
            config_parameter_obj.set_param(cr, uid, "max_sale_discount", str(record.max_sale_discount) )



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: