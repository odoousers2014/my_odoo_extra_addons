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

import time
from openerp.osv import osv, fields
from openerp import netsvc
from openerp.tools.translate import _


class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _name    = "account.invoice"
    
    def _need_to_create_intercompany_object(self, cr, uid, id, parent_check=True, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        invoice = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(invoice.partner_id.id,))
        company_to = cr.fetchone()
        if company_to:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, uid, uid).company_ids):
                if not invoice.invoice_ic_id or not parent_check:
                    if invoice.type in ['out_invoice','out_refund']:
                        invoice_rel = context.get('sale_id_for_ic', [])
                        if not invoice_rel:
                            cr.execute("SELECT * FROM sale_order_invoice_rel WHERE invoice_id=%s",(invoice.id,))
                            invoice_rel = cr.fetchone()
                    else: #invoice.type in ['in_invoice','in_refund']
                        cr.execute("SELECT * FROM purchase_invoice_rel WHERE invoice_id=%s",(invoice.id,))
                        invoice_rel = cr.fetchone()
                    
                    if not invoice_rel or not parent_check:
                        if invoice.type in ['out_invoice','out_refund']:
                            cr.execute("SELECT ci2si FROM res_intercompany WHERE company_from=%s AND company_to=%s",(invoice.company_id.id,company_to,))
                        else: #invoice.type in ['in_invoice','in_refund']
                            cr.execute("SELECT si2ci FROM res_intercompany WHERE company_from=%s AND company_to=%s",(invoice.company_id.id,company_to,))
                        ic_config = cr.fetchone()
                        if ic_config:
                            ic_config = ic_config[0]
                            if ic_config=='draft' and (invoice.state=='draft' or not parent_check):
                                return company_to
                            elif ic_config=='confirm' and (invoice.state=='open' or not parent_check):
                                return company_to
        return False
    
    
    def _need_to_update_intercompany_object(self, cr, uid, id, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        invoice = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(invoice.partner_id.id,))
        company_to = cr.fetchone()
        if company_to and invoice.invoice_ic_id:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, uid, uid).company_ids):
                if invoice.type in ['out_invoice','out_refund']:
                    cr.execute("SELECT ci2si FROM res_intercompany WHERE company_from=%s AND company_to=%s",(invoice.company_id.id,company_to,))
                else: #invoice.type in ['in_invoice','in_refund']
                    cr.execute("SELECT si2ci FROM res_intercompany WHERE company_from=%s AND company_to=%s",(invoice.company_id.id,company_to,))
                ic_config = cr.fetchone()
                if ic_config:
                    ic_config = ic_config[0]
                    if ic_config=='draft':
                        return ic_config
        return False
    
    
    def _generate_invoice_from_invoice(self, cr, uid, invoice, company_id, context=None):
        #print ">>>>>>>> Create Invoice"
        line_pool    = self.pool.get('account.invoice.line')
        journal_pool = self.pool.get('account.journal')
        period_pool  = self.pool.get('account.period')
        #prop_pool    = self.pool.get('ir.property')
        part = invoice.company_id.partner_id
        
        #Invoice Type
        if 'out_' in invoice.type:
            invoice_type = invoice.type.replace('out_','in_')
            acc_id = part.property_account_receivable.id
            cr.execute("SELECT value_reference FROM ir_property WHERE name='property_account_receivable' AND res_id='res.partner,%s' AND company_id=%s",(part.id,company_id))
            prop = cr.fetchone()
            if prop and prop[0]:
                acc_id = prop[0].split('account.account,')[1]
        else:
            invoice_type = invoice.type.replace('in_','out_')
            acc_id = part.property_account_payable.id
            cr.execute("SELECT value_reference FROM ir_property WHERE name='property_account_payable' AND res_id='res.partner,%s' AND company_id=%s",(part.id,company_id))
            prop = cr.fetchone()
            if prop and prop[0]:
                acc_id = prop[0].split('account.account,')[1]
        
        #Invoice Journal
        type2journal = {'out_invoice': 'sale', 'in_invoice': 'purchase', 'out_refund': 'sale_refund', 'in_refund': 'purchase_refund'}        
        res = journal_pool.search(cr, uid, [('type', '=', type2journal.get(invoice_type, 'sale')), ('company_id', '=', company_id)], limit=1)
        journal_id = res and res[0] or False
        # We assume periods in Inter-companies have the same code. 
        period_ids = period_pool.search(cr, uid, [('code', '=', invoice.period_id.code), ('company_id', '=', company_id)], limit=1)
        period_id  = period_ids and period_ids[0] or False

        origin = invoice.name and 'IC:' + str(invoice.name) or ''
        ic_id = self.create(cr, uid, {
            'invoice_ic_id': invoice.id,
            'is_locked': True,
            'ic_create': True,
            'name': invoice.name,
            'origin': origin,
            'supplier_invoice_number': invoice.supplier_invoice_number,
            'type': invoice_type,
            'reference': invoice.reference,
            'reference_type': invoice.reference_type,
            'comment': invoice.comment,
            'date_invoice': invoice.date_invoice,
            'date_due': invoice.date_due,
            'partner_id': part.id,
            'payment_term': invoice.payment_term and invoice.payment_term.id or False,
            'period_id':period_id,
            'account_id':acc_id,
            'journal_id': journal_id,
            #'currency_id': invoice.currency_id and invoice.currency_id.id or False,
            'company_id': company_id
        }, context={'force_ic_checking':False})
        
        
        #prop = prop_pool.get(cr, uid, 'property_account_income_categ', 'product.category', context=context)
        #account_id = prop and prop.id or False
        
        for invoice_line in invoice.invoice_line:
            line_pool.create(cr, uid, {
                'name': invoice_line.name,
                'origin': invoice_line.origin,
                'sequence': invoice_line.sequence,
                'invoice_id': ic_id,
                'uos_id': invoice_line.uos_id and invoice_line.uos_id.id or False,
                'product_id': invoice_line.product_id and invoice_line.product_id.id or False,
                'account_id': acc_id, #account_id,
                'price_unit': invoice_line.price_unit,
                'quantity': invoice_line.quantity,
                'discount': invoice_line.discount,
                'company_id': company_id
            })
        return ic_id
    
    
    def create(self, cr, uid, vals, context=None):
        new_id = super(account_invoice, self).create(cr, uid, vals, context=context)
        context = context or {}
        if context.get('force_ic_checking',True):
            new_invoice = self.browse(cr, uid, new_id, context=context)
            res = self._need_to_create_intercompany_object(cr, uid, new_id, context=context)
            if res:
                ic_id = self._generate_invoice_from_invoice(cr, uid, new_invoice, res, context=context)
                self.write(cr, uid, new_id, {'invoice_ic_id':ic_id,}, context={'force_ic_checking':False})
                
            elif self._need_to_create_intercompany_object(cr, uid, new_id, parent_check=False, context=context):
                # A linked object may have been created by standard OpenERP
                new_invoice_vals = {}
                ic_invoice_vals  = {}
                ic_id            = False
                order            = False
                
                if new_invoice.type in ['out_invoice','out_refund']:
                    order_ids = context.get('sale_id_for_ic', [])
                    if not order_ids:
                        cr.execute("SELECT order_id FROM sale_order_invoice_rel WHERE invoice_id=%s",(new_invoice.id,))
                        order_ids = map(lambda x: x[0], cr.fetchall())
                    if order_ids:
                        order = self.pool.get('sale.order').browse(cr, uid, order_ids[0])
                else: #new_invoice.type in ['in_invoice','in_refund']
                    cr.execute("SELECT order_id FROM purchase_invoice_rel WHERE invoice_id=%s",(new_invoice.id,))
                    order_ids = map(lambda x: x[0], cr.fetchall())
                    if order_ids:
                        order = self.pool.get('purchase.order').browse(cr, uid, order_ids[0])
                
                if order:
                    if order.ic_create:
                        new_invoice_vals.update({'ic_create': True,})
                    if order.is_locked:
                        new_invoice_vals.update({'is_locked': True,})
                    
                    if new_invoice.type in ['out_invoice','out_refund']:
                        if order.purchase_id:
                            cr.execute("SELECT invoice_id FROM purchase_invoice_rel WHERE purchase_id=%s",(order.purchase_id.id,))
                            ic_id = map(lambda x: x[0], cr.fetchall())
                            ic_id = ic_id and ic_id[0] or False
                    else: #new_invoice.type in ['in_invoice','in_refund']
                        if order.sale_id:
                            cr.execute("SELECT invoice_id FROM sale_invoice_rel WHERE sale_id=%s",(order.sale_id.id,))
                            ic_id = map(lambda x: x[0], cr.fetchall())
                            ic_id = ic_id and ic_id[0] or False
                    
                    if ic_id:
                        new_invoice_vals.update({'invoice_ic_id': ic_id,})
                        
                        ic_invoice_vals.update({'invoice_ic_id': new_id,})
                        if new_invoice.type in ['out_invoice','out_refund']:
                            if order.purchase_id.ic_create:
                                ic_invoice_vals.update({'ic_create': True,})
                            if order.purchase_id.is_locked:
                                ic_invoice_vals.update({'is_locked': True,})
                        else: #new_invoice.type in ['in_invoice','in_refund']
                            if order.sale_id.ic_create:
                                ic_invoice_vals.update({'ic_create': True,})
                            if order.sale_id.is_locked:
                                ic_invoice_vals.update({'is_locked': True,})
                    
                    if new_invoice_vals:
                        self.write(cr, uid, new_id, new_invoice_vals, context={'force_ic_checking':False})
                    if ic_invoice_vals and ic_id:
                        self.write(cr, uid, ic_id, ic_invoice_vals, context={'force_ic_checking':False})
        return new_id
    
    
    def write(self, cr, uid, ids, vals, context=None):
        #print '----------INVOICE-------------'
        #print vals, context
        context = context or {}
        if type(ids)!=type([]):
            ids = [ids]

        if not context:
            wf_service = netsvc.LocalService("workflow")
            new_vals = vals
            for invoice in self.browse(cr, uid, ids, context=context):
                if not invoice.ic_create:
                    if invoice.invoice_ic_id:
                        if 'state' in vals:
                            if vals['state'] == 'cancel':
                                wf_service.trg_validate(uid, 'account.invoice', invoice.invoice_ic_id.id, 'invoice_cancel', cr)
                            elif vals['state'] == 'open' and self._need_to_update_intercompany_object(cr, uid, invoice.id, context=context):
                                wf_service.trg_validate(uid, 'account.invoice', invoice.invoice_ic_id.id, 'invoice_open', cr)
                    else:
                        res = self._need_to_create_intercompany_object(cr, uid, invoice.id, context=context)
                        if res:
                            ic_id = self._generate_invoice_from_invoice(cr, uid, invoice, res, context=context)
                            wf_service.trg_validate(uid, 'account.invoice', ic_id, 'invoice_open', cr)
                            new_vals.update({'invoice_ic_id':ic_id,})
                super(account_invoice, self).write(cr, uid, [invoice.id], new_vals, context=context)
                
        elif len(vals)<=1 and ('date_invoice' in vals or 'message_follower_ids' in vals):
            super(account_invoice, self).write(cr, uid, ids, vals, context=context)
            
        elif context.get('force_ic_checking',True):
            wf_service = netsvc.LocalService("workflow")
            for invoice in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if 'is_locked' in new_vals:
                    if invoice.invoice_ic_id:
                        self.write(cr, uid, [invoice.invoice_ic_id.id], {'invoice_ic_id':False,}, context={'force_ic_checking':False})
                    new_vals.update({'invoice_ic_id':False,})
                    super(account_invoice, self).write(cr, uid, [invoice.id], new_vals, context=context)
                    
                elif not invoice.is_locked:
                    if not invoice.ic_create:
                        if invoice.invoice_ic_id:
                            if 'state' in vals:
                                if vals['state'] == 'cancel':
                                    wf_service.trg_validate(uid, 'account.invoice', invoice.invoice_ic_id.id, 'invoice_cancel', cr)
                                elif vals['state'] == 'open' and self._need_to_update_intercompany_object(cr, uid, invoice.id, context=context):
                                    wf_service.trg_validate(uid, 'account.invoice', invoice.invoice_ic_id.id, 'invoice_open', cr)
                                
                            else:
                                #print ">>>>>>>> CANCEL Invoice"
                                super(account_invoice, self).write(cr, uid, [invoice.id], vals, context=context)
                                wf_service.trg_validate(uid, 'account.invoice', invoice.invoice_ic_id.id, 'invoice_cancel', cr)
                                cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(invoice.partner_id.id,))
                                company_to = cr.fetchone()[0]
                                ic_id = self._generate_invoice_from_invoice(cr, uid, invoice, company_to, context=context)
                                new_vals = {}
                                new_vals.update({'invoice_ic_id':ic_id,})
                        else:
                            res = self._need_to_create_intercompany_object(cr, uid, invoice.id, context=context)
                            if res:
                                ic_id = self._generate_invoice_from_invoice(cr, uid, invoice, res, context=context)
                                wf_service.trg_validate(uid, 'account.invoice', ic_id, 'invoice_open', cr)
                                new_vals.update({'invoice_ic_id':ic_id,})
                    super(account_invoice, self).write(cr, uid, [invoice.id], new_vals, context=context)
                else:
                    raise osv.except_osv(_('Invalid Action!'), _('You can not update this Invoice, because it is Locked by Inter-Company process.'))
        else:
            super(account_invoice, self).write(cr, uid, ids, vals, context=context)     
        return True
    
    
    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default.update({'is_locked':False,'ic_create':False,'invoice_ic_id':False,})
        return super(account_invoice, self).copy(cr, uid, id, default=default, context=context)
    

    _columns = {
        'is_locked':     fields.boolean('Locked for Intercompany'),
        'ic_create':     fields.boolean('Intercompany Invoice generated'),
        'invoice_ic_id': fields.many2one('account.invoice', 'Invoice'),
    }
account_invoice()


class account_move(osv.osv):
    _inherit = "account.move"
    _name    = "account.move"
    
    def create(self, cr, uid, vals, context=None):
        context = context or {}
        context.update({'force_ic_checking':False})
        if not vals.get('company_id', False):
            vals['company_id'] = context.get('company_id', False)
        return super(account_move, self).create(cr, uid, vals, context=context)

account_move()


class account_move_line(osv.osv):
    _inherit = "account.move.line"
    _name    = "account.move.line"

    def create(self, cr, uid, vals, context=None, check=True):
        context = context or {}
        context.update({'force_ic_checking':False})
        if not vals.get('company_id', False):
            vals['company_id'] = context.get('company_id', False)
        return super(account_move_line, self).create(cr, uid, vals, context=context, check=check)

account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: