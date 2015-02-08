# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Yannick Gouin <yannick.gouin@elico-corp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields
from openerp import netsvc
from openerp.tools.translate import _
from datetime import datetime


class sale_order(osv.osv):
    _inherit = "sale.order"
    _name    = "sale.order"
    
    def _need_to_create_intercompany_object(self, cr, uid, id, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        order = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(order.partner_id.id,))
        company_to = cr.fetchone()
        if company_to:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, 1, uid).company_ids):
                cr.execute("SELECT so2po FROM res_intercompany WHERE company_from=%s AND company_to=%s",(order.company_id.id,company_to,))
                ic_config = cr.fetchone()
                if ic_config:
                    ic_config = ic_config[0]
                    if ic_config=='draft' and order.state=='draft':
                        return company_to
                    elif ic_config=='confirm' and order.state in ['progress','manual']: #order.state=='manual'
                        return company_to
        return False
    
    
    def _need_to_update_intercompany_object(self, cr, uid,id, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        order = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(order.partner_id.id,))
        company_to = cr.fetchone()
        if company_to and order.purchase_id:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, 1, uid).company_ids):
                cr.execute("SELECT po2so FROM res_intercompany WHERE company_from=%s AND company_to=%s",(order.company_id.id,company_to,))
                ic_config = cr.fetchone()
                if ic_config:
                    ic_config = ic_config[0]
                    if ic_config=='confirm' or ic_config=='draft':
                        return ic_config
        return False
    
    
    def _generate_po_from_so(self, cr, uid, order, company_id, context=None):
        #print ">>>>>>>> Create PO"
        po_pool  = self.pool.get('purchase.order')
        pol_pool = self.pool.get('purchase.order.line')
        
        part = order.company_id.partner_id
        res = po_pool.onchange_partner_id(cr, uid, [order.id], part.id)['value']
        pricelist = 'pricelist_id' in res and res['pricelist_id'] or False
        payment_term = res['payment_term_id']
        fiscal_position = res['fiscal_position']
        
        location_id = part.property_stock_supplier and part.property_stock_supplier.id or False
        cr.execute("SELECT id FROM stock_location WHERE company_id=%s AND name = 'Stock'",(company_id,))
        location = cr.fetchone()
        if location and location[0]:
            location_id = location[0]
        
        ic_id = po_pool.create(cr, uid, {
            'partner_id': part.id,
            'pricelist_id': pricelist,
            'payment_term_id': payment_term,
            'fiscal_position': fiscal_position,
            'sale_id': order.id,
            'is_locked': True,
            'ic_create': True,
            'company_id': company_id,
            'location_id': location_id,
            'origin': 'IC:' + str(order.name),
        }, context={'force_ic_checking':False})
        
        for so_line in order.order_line:
            date_planned = self._get_date_planned(cr, uid, order, so_line, order.date_order, context=context)
            pol_pool.create(cr, uid, {
                'order_id': ic_id,
                'name': so_line.name,
                'product_qty': so_line.product_uom_qty,
                'product_id': so_line.product_id and so_line.product_id.id or False,
                'product_uom': so_line.product_uom.id,
                'price_unit': so_line.price_unit,
                'date_planned': date_planned, #datetime.now().strftime('%Y-%m-%d')
            })
        return ic_id
    
    
    def create(self, cr, uid, vals, context=None):
        new_id = super(sale_order, self).create(cr, uid, vals, context=context)
        context = context or {}
        if context.get('force_ic_checking',True):
            res = self._need_to_create_intercompany_object(cr, uid, new_id, context=context)
            if res:
                so = self.browse(cr, uid, new_id, context=context)
                ic_id = self._generate_po_from_so(cr, 1, so, res, context=context)
                self.write(cr, uid, new_id, {'purchase_id':ic_id,}, context={'force_ic_checking':False})
        return new_id
    
    
    def write(self, cr, uid, ids, vals, context=None):
        #print '----------SO-------------------'
        #print vals, context
        context = context or {}
        if type(ids)!=type([]):
            ids = [ids]
        
        if not context:
            wf_service = netsvc.LocalService("workflow")
            for order in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if not order.ic_create:
                    if order.purchase_id:
                        if 'state' in vals:
                            if vals['state'] == 'cancel':
                                wf_service.trg_validate(1, 'purchase.order', order.purchase_id.id, 'purchase_cancel', cr)
                            elif vals['state'] in ['progress','manual'] and self._need_to_update_intercompany_object(cr, uid, order.id, context=context):
                                wf_service.trg_validate(1, 'purchase.order', order.purchase_id.id, 'purchase_confirm', cr)
                    else:
                        res = self._need_to_create_intercompany_object(cr, uid, order.id, context=context)
                        if res:
                            ic_id = self._generate_po_from_so(cr, 1, order, res, context=context)
                            wf_service.trg_validate(1, 'purchase.order', ic_id, 'purchase_confirm', cr)
                            new_vals.update({'purchase_id':ic_id,})
                super(sale_order, self).write(cr, uid, [order.id], new_vals, context=context)
        
        elif len(vals)<=1 and ('message_follower_ids' in vals):
            super(sale_order, self).write(cr, uid, ids, vals, context=context)
        
        elif context.get('force_ic_checking',True):
            po_pool    = self.pool.get('purchase.order')
            wf_service = netsvc.LocalService("workflow")
            for order in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if 'is_locked' in new_vals:
                    if order.purchase_id:
                        po_pool.write(cr, uid, [order.purchase_id.id], {'sale_id':False,}, context={'force_ic_checking':False})
                    new_vals.update({'purchase_id':False,})
                    super(sale_order, self).write(cr, uid, [order.id], new_vals, context=context)
                elif not order.is_locked:
                    if not order.ic_create:
                        if order.purchase_id:
                            if 'state' in vals:
                                if vals['state'] == 'cancel':
                                    wf_service.trg_validate(uid, 'purchase.order', order.purchase_id.id, 'purchase_cancel', cr)
                                elif vals['state'] in ['progress','manual'] and self._need_to_update_intercompany_object(cr, uid, order.id, context=context):
                                    wf_service.trg_validate(uid, 'purchase.order', order.purchase_id.id, 'purchase_confirm', cr)
                                
                            else:
                                #print ">>>>>>>> CANCEL PO"
                                super(sale_order, self).write(cr, 1, [order.id], vals, context=context)
                                wf_service.trg_validate(1, 'purchase.order', order.purchase_id.id, 'purchase_cancel', cr)
                                cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(order.partner_id.id,))
                                company_to = cr.fetchone()[0]
                                ic_id = self._generate_po_from_so(cr, 1, order, company_to, context=context)
                                new_vals = {}
                                new_vals.update({'purchase_id':ic_id,})
                        else:
                            res = self._need_to_create_intercompany_object(cr, uid, order.id, context=context)
                            if res:
                                ic_id = self._generate_po_from_so(cr, 1, order, res, context=context)
                                wf_service.trg_validate(1, 'purchase.order', ic_id, 'purchase_confirm', cr)
                                new_vals.update({'purchase_id':ic_id,})
                    super(sale_order, self).write(cr, uid, [order.id], new_vals, context=context)
                else:
                    raise osv.except_osv(_('Invalid Action!'), _('You can not update this Sales Order, because it is Locked by Inter-Company process.'))
        else:
            super(sale_order, self).write(cr, uid, ids, vals, context=context)
        return True
    
    
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({'is_locked':False,'ic_create':False,'purchase_id':False,})
        return super(sale_order, self).copy(cr, uid, id, default=default, context=context)
    
    
    def _make_invoice(self, cr, uid, order, lines, context=None):
        context = context or {}
        if order:
            context.update({'sale_id_for_ic': [order.id]})
        return super(sale_order, self)._make_invoice(cr, uid, order, lines, context=context)
    
    
    _columns = {
        'is_locked':   fields.boolean('Locked for Intercompany'),
        'ic_create':   fields.boolean('Intercompany SO generated'),
        'purchase_id': fields.many2one('purchase.order', 'Purchase Order'),
    }
sale_order()



class sale_advance_payment_inv(osv.osv_memory):
    _inherit = "sale.advance.payment.inv"
    _name    = "sale.advance.payment.inv"

    def _create_invoices(self, cr, uid, inv_values, sale_id, context=None):
        context = context or {}
        context.update({'sale_id_for_ic':[sale_id]})
        inv_obj = self.pool.get('account.invoice')
        sale_obj = self.pool.get('sale.order')
        inv_id = inv_obj.create(cr, uid, inv_values, context=context)
        inv_obj.button_reset_taxes(cr, uid, [inv_id], context=context)
        # add the invoice to the sales order's invoices
        sale_obj.write(cr, uid, sale_id, {'invoice_ids': [(4, inv_id)]}, context=context)
        return inv_id

sale_advance_payment_inv()



class purchase_order(osv.osv):
    _inherit = "purchase.order"
    _name    = "purchase.order"
    
    def _need_to_create_intercompany_object(self, cr, uid, id, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        order = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(order.partner_id.id,))
        company_to = cr.fetchone()
        if company_to:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, 1, uid).company_ids):
                cr.execute("SELECT po2so FROM res_intercompany WHERE company_from=%s AND company_to=%s",(order.company_id.id,company_to,))
                ic_config = cr.fetchone()
                if ic_config:
                    ic_config = ic_config[0]
                    if ic_config=='draft' and order.state=='draft':
                        return company_to
                    elif ic_config=='confirm' and order.state=='confirmed':
                        return company_to
        return False
    
    
    def _need_to_update_intercompany_object(self, cr, uid,id, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        order = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(order.partner_id.id,))
        company_to = cr.fetchone()
        if company_to and order.sale_id:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, 1, uid).company_ids):
                cr.execute("SELECT po2so FROM res_intercompany WHERE company_from=%s AND company_to=%s",(order.company_id.id,company_to,))
                ic_config = cr.fetchone()
                if ic_config:
                    ic_config = ic_config[0]
                    if ic_config=='draft':
                        return ic_config
        return False
    
    
    def _generate_so_from_po(self, cr, uid, order, company_id, context=None):
        #print ">>>>>>>> Create SO"
        so_pool  = self.pool.get('sale.order')
        sol_pool = self.pool.get('sale.order.line')
            
        part = order.company_id.partner_id
        addr = self.pool.get('res.partner').address_get(cr, uid, [part.id], ['delivery', 'invoice', 'contact'])
        pricelist = part.property_product_pricelist and part.property_product_pricelist.id or False
        payment_term = part.property_payment_term and part.property_payment_term.id or False
        fiscal_position = part.property_account_position and part.property_account_position.id or False
        dedicated_salesman = part.user_id and part.user_id.id or uid
        
        shop_ids = self.pool.get('sale.shop').search(cr, uid, [('company_id','=',company_id)], context=context)
        if not shop_ids:
            raise osv.except_osv(_('Error!'), _('There is no default shop for the destination company!'))
        
        ic_id = so_pool.create(cr, uid, {
            'partner_id': part.id,
            'pricelist_id': pricelist,
            'partner_invoice_id': addr['invoice'],
            'partner_order_id': addr['contact'],
            'partner_shipping_id': addr['delivery'],
            'payment_term': payment_term,
            'fiscal_position': fiscal_position,
            'user_id': dedicated_salesman,
            'purchase_id': order.id,
            'is_locked': True,
            'ic_create': True,
            'shop_id': shop_ids[0],
            #'company_id': company_id,
        }, context={'force_ic_checking':False})
        
        for po_line in order.order_line:
            sol_pool.create(cr, uid, {
                'order_id': ic_id,
                'name': po_line.name,
                'product_uom_qty': po_line.product_qty,
                'product_id': po_line.product_id and po_line.product_id.id or False,
                'product_uom': po_line.product_uom.id,
                'price_unit': po_line.price_unit,
            })
        return ic_id
    
        
    def create(self, cr, uid, vals, context=None):
        new_id = super(purchase_order, self).create(cr, uid, vals, context=context)
        context = context or {}
        if context.get('force_ic_checking',True):
            res = self._need_to_create_intercompany_object(cr, uid, new_id, context=context)
            if res:
                po = self.browse(cr, uid, new_id, context=context)
                ic_id = self._generate_so_from_po(cr, 1, po, res, context=context)
                self.write(cr, uid, new_id, {'sale_id':ic_id,}, context={'force_ic_checking':False})
        return new_id
    
    
    def write(self, cr, uid, ids, vals, context=None):
        #print '----------PO-------------------'
        #print vals, context
        context = context or {}
        if type(ids)!=type([]):
            ids = [ids]
        
        if not context:
            wf_service = netsvc.LocalService("workflow")
            for order in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if not order.ic_create:
                    if order.sale_id:
                        if 'state' in vals:
                            if vals['state'] == 'cancel':
                                wf_service.trg_validate(1, 'sale.order', order.sale_id.id, 'cancel', cr)
                            elif vals['state'] == 'approved' and self._need_to_update_intercompany_object(cr, uid, order.id, context=context):
                                wf_service.trg_validate(1, 'sale.order', order.sale_id.id, 'order_confirm', cr)
                    else:
                        res = self._need_to_create_intercompany_object(cr, uid, order.id, context=context)
                        if res:
                            ic_id = self._generate_so_from_po(cr, 1, order, res, context=context)
                            wf_service.trg_validate(1, 'sale.order', ic_id, 'order_confirm', cr)
                            new_vals.update({'sale_id':ic_id,})
                super(purchase_order, self).write(cr, uid, [order.id], new_vals, context=context)
        
        elif len(vals)<=1 and ('message_follower_ids' in vals):
            super(purchase_order, self).write(cr, uid, ids, vals, context=context)
        
        elif context.get('force_ic_checking',True):
            so_pool    = self.pool.get('sale.order')
            wf_service = netsvc.LocalService("workflow")
            for order in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if 'is_locked' in new_vals:#if unlocked object need to break the IC links
                    if order.sale_id:
                        so_pool.write(cr, uid, [order.sale_id.id], {'purchase_id':False,}, context={'force_ic_checking':False})
                    new_vals.update({'sale_id':False,})
                    super(purchase_order, self).write(cr, uid, [order.id], new_vals, context=context)
                    
                elif not order.is_locked:# when locked, warning
                    if not order.ic_create:# if the PO has not been generated from a SO through IC process
                        if order.sale_id:# already have a SO linked
                            if 'state' in vals:# update linked SO state
                                if vals['state'] == 'cancel':
                                    wf_service.trg_validate(1, 'sale.order', order.sale_id.id, 'cancel', cr)
                                elif vals['state'] == 'approved' and self._need_to_update_intercompany_object(cr, uid, order.id, context=context):
                                    wf_service.trg_validate(1, 'sale.order', order.sale_id.id, 'order_confirm', cr)
                                
                            else:# cancel and re-create linked SO
                                #print ">>>>>>>> CANCEL SO"
                                super(purchase_order, self).write(cr, uid, [order.id], vals, context=context)
                                wf_service.trg_validate(1, 'sale.order', order.sale_id.id, 'cancel', cr)
                                cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(order.partner_id.id,))
                                company_to = cr.fetchone()[0]
                                ic_id = self._generate_so_from_po(cr, 1, order, company_to, context=context)
                                new_vals = {}
                                new_vals.update({'sale_id':ic_id,})
                        else:
                            res = self._need_to_create_intercompany_object(cr, uid, order.id, context=context)
                            if res:# if must create linked SO when confirmed
                                ic_id = self._generate_so_from_po(cr, 1, order, res, context=context)
                                wf_service.trg_validate(1, 'sale.order', ic_id, 'order_confirm', cr)
                                new_vals.update({'sale_id':ic_id,})
                    super(purchase_order, self).write(cr, uid, [order.id], new_vals, context=context)
                else:
                    raise osv.except_osv(_('Invalid Action!'), _('You can not update this Purchase Order, because it is Locked by Inter-Company process.'))
        else:
            super(purchase_order, self).write(cr, uid, ids, vals, context=context)
        return True
        
    
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({'is_locked':False,'ic_create':False,'sale_id':False,})
        return super(purchase_order, self).copy(cr, uid, id, default=default, context=context)
    
    
    _columns = {
        'is_locked': fields.boolean('Locked for Intercompany'),
        'ic_create': fields.boolean('Intercompany PO generated'),
        'sale_id':   fields.many2one('sale.order', 'Sales Order'),
    }
purchase_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: