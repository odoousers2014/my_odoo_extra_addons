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
from openerp.tools import float_compare


class stock_picking_in(osv.osv):
    _inherit = "stock.picking.in"
    _name    = "stock.picking.in"
    
    def _need_to_create_intercompany_object(self, cr, uid, id, parent_check=True, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        picking = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(picking.partner_id.id,))
        company_to = cr.fetchone()
        if company_to:
            company_to = company_to[0]
            
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, 1, uid).company_ids):
                if not picking.purchase_id or not picking.purchase_id.sale_id or not parent_check:
                    cr.execute("SELECT is2do FROM res_intercompany WHERE company_from=%s AND company_to=%s",(picking.company_id.id,company_to,))
                    ic_config = cr.fetchone()
                    if ic_config:
                        ic_config = ic_config[0]
                        if ic_config=='draft' and (picking.state=='draft' or not parent_check):
                            return company_to
                        elif ic_config=='confirm' and (picking.state=='confirmed' or not parent_check):
                            return company_to
        return False
    
    
    def _need_to_update_intercompany_object(self, cr, uid, id, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        picking = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(picking.partner_id.id,))
        company_to = cr.fetchone()
        if company_to:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, 1, uid).company_ids):
                if picking.picking_ic_id:
                    cr.execute("SELECT is2do FROM res_intercompany WHERE company_from=%s AND company_to=%s",(picking.company_id.id,company_to,))
                    ic_config = cr.fetchone()
                    if ic_config:
                        ic_config = ic_config[0]
                        if ic_config=='draft':
                            return ic_config
        return False
    
    
    def _generate_do_from_is(self, cr, uid, pick, company_id, context=None):
        #print ">>>>>>>> Create DO"
        context.update({'picking_type':'out'})
        pick_pool = self.pool.get('stock.picking.out')
        move_pool = self.pool.get('stock.move')
        part = pick.company_id.partner_id
        
        location_id      = move_pool._default_location_source(cr, uid, context=context) or part.property_stock_supplier.id
        #location_dest_id = move_pool._default_location_destination(cr, uid, context=context)
        location_dest_id = part.property_stock_supplier.id
        cr.execute("SELECT id FROM stock_location WHERE company_id=%s AND name = 'Stock'",(company_id,))
        location = cr.fetchone()
        if location and location[0]:
            location_id = location[0]
        
        ic_id = pick_pool.create(cr, uid, {
            'partner_id': part.id,
            'picking_ic_id': pick.id,
            'is_locked': True,
            'ic_create': True,
            'company_id': company_id,
            'type':'out',
        }, context={'force_ic_checking':False})
        
        for move_line in pick.move_lines:
            move_pool.create(cr, uid, {
                'picking_id': ic_id,
                'name': move_line.name,
                'product_qty': move_line.product_qty,
                'product_id': move_line.product_id and move_line.product_id.id or False,
                'product_uom': move_line.product_uom.id,
                'price_unit': move_line.price_unit,
                'price_currency_id': move_line.price_currency_id and move_line.price_currency_id.id or False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': company_id,
            })
        return ic_id
    
    
    def create(self, cr, uid, vals, context=None):
        #print '----------IS-------------------'
        #print vals, context
        new_id = super(stock_picking_in, self).create(cr, uid, vals, context=context)
        context = context or {}
        if context.get('force_ic_checking',True):
            res = self._need_to_create_intercompany_object(cr, uid, new_id, context=context)
            if res:
                # We automatically create the linked object
                pick = self.browse(cr, uid, new_id, context=context)
                ic_id = self._generate_do_from_is(cr, 1, pick, res, context=context)
                self.write(cr, uid, new_id, {'picking_ic_id':ic_id,}, context={'force_ic_checking':False})
            
            elif self._need_to_create_intercompany_object(cr, uid, new_id, parent_check=False, context=context):
                # A linked object may have been created by standard OpenERP (Eg: Incoming Shipment created by PO confirmation)
                new_pick = self.browse(cr, uid, new_id, context=context)
                new_pick_vals = {}
                ic_pick_vals  = {}
                ic_id         = False
                
                if new_pick.purchase_id:
                    if new_pick.purchase_id.ic_create:
                        new_pick_vals.update({'ic_create': True,})
                    if new_pick.purchase_id.is_locked:
                        new_pick_vals.update({'is_locked': True,})
                    
                    if new_pick.purchase_id.sale_id and new_pick.purchase_id.sale_id:
                        ic_id = self.pool.get('stock.picking.out').search(cr, uid, [('sale_id','=',new_pick.purchase_id.sale_id.id)], context=context)
                        ic_id = ic_id and ic_id[0] or False
                        
                        if ic_id:
                            new_pick_vals.update({'picking_ic_id': ic_id,})
                            
                            ic_pick_vals.update({'picking_ic_id': new_id,})
                            if new_pick.purchase_id.sale_id.ic_create:
                                ic_pick_vals.update({'ic_create': True,})
                            if new_pick.purchase_id.sale_id.is_locked:
                                ic_pick_vals.update({'is_locked': True,})
                    
                    if new_pick_vals:
                        self.write(cr, uid, new_id, new_pick_vals, context={'force_ic_checking':False})
                    if ic_pick_vals and ic_id:
                        self.write(cr, uid, ic_id, ic_pick_vals, context={'force_ic_checking':False})
        return new_id
    
    
    def write(self, cr, uid, ids, vals, context=None):
        #print '----------IS-------------------'
        #print vals, context
        context = context or {}
        if type(ids)!=type([]):
            ids = [ids]
        
        if not context:
            wf_service = netsvc.LocalService("workflow")
            for pick in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if not pick.ic_create:
                    if pick.picking_ic_id:
                        if 'state' in vals:
                            if vals['state'] == 'cancel':
                                wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_cancel', cr)
                            elif vals['state'] in ['confirmed'] and self._need_to_update_intercompany_object(cr, uid, pick.id, context=context):
                                wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_confirm', cr)
                    else:
                        res = self._need_to_create_intercompany_object(cr, uid, pick.id, context=context)
                        if res:
                            ic_id = self._generate_do_from_is(cr, 1, pick, res, context=context)
                            wf_service.trg_validate(1, 'stock.picking', ic_id, 'button_confirm', cr)
                            new_vals.update({'picking_ic_id':ic_id,})
                super(stock_picking_in, self).write(cr, uid, [pick.id], new_vals, context=context)
            
        elif (len(vals)<=1 and ('message_follower_ids' in vals)):
            super(stock_picking_in, self).write(cr, uid, ids, vals, context=context)
        
        elif context.get('force_ic_checking',True):
            picking_pool = self.pool.get('stock.picking.out')
            wf_service   = netsvc.LocalService("workflow")
            for pick in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if 'is_locked' in new_vals:
                    if pick.picking_ic_id:
                        picking_pool.write(cr, uid, [pick.picking_ic_id.id], {'picking_ic_id':False,}, context={'force_ic_checking':False})
                    new_vals.update({'picking_ic_id':False,})
                    super(stock_picking_in, self).write(cr, uid, [pick.id], new_vals, context=context)
                    
                elif not pick.is_locked:
                    if not pick.ic_create:
                        if pick.picking_ic_id:
                            if 'state' in vals:
                                if vals['state'] == 'cancel':
                                    wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_cancel', cr)
                                elif vals['state'] in ['confirmed'] and self._need_to_update_intercompany_object(cr, uid, pick.id, context=context):
                                    wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_confirm', cr)
                                
                            else:
                                #print ">>>>>>>> CANCEL Delivery Order"
                                super(stock_picking_in, self).write(cr, uid, [pick.id], vals, context=context)
                                wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_cancel', cr)
                                cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(pick.partner_id.id,))
                                company_to = cr.fetchone()[0]
                                ic_id = self._generate_do_from_is(cr, 1, pick, company_to, context=context)
                                new_vals = {}
                                new_vals.update({'picking_ic_id':ic_id,})
                        else:
                            res = self._need_to_create_intercompany_object(cr, uid, pick.id, context=context)
                            if res:
                                ic_id = self._generate_do_from_is(cr, 1, pick, res, context=context)
                                wf_service.trg_validate(1, 'stock.picking', ic_id, 'button_confirm', cr)
                                new_vals.update({'picking_ic_id':ic_id,})
                    super(stock_picking_in, self).write(cr, uid, [pick.id], new_vals, context=context)
                else:
                    raise osv.except_osv(_('Invalid Action!'), _('You can not update this Incoming Shipment, because it is Locked by Inter-Company process.'))
        else:
            super(stock_picking_in, self).write(cr, uid, ids, vals, context=context)
        return True
    
    
    _columns = {
        'is_locked':     fields.boolean('Locked for Intercompany'),
        'ic_create':     fields.boolean('Intercompany Picking generated'),
        'picking_ic_id': fields.many2one('stock.picking.out', 'Delivery Order'),
    }
stock_picking_in()



class stock_picking_out(osv.osv):
    _inherit = "stock.picking.out"
    _name    = "stock.picking.out"
    
    def _need_to_create_intercompany_object(self, cr, uid, id, parent_check=True, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        picking = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(picking.partner_id.id,))
        company_to = cr.fetchone()
        if company_to:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, 1, uid).company_ids):
                if not picking.sale_id or not picking.sale_id.purchase_id or not parent_check:
                    cr.execute("SELECT do2is FROM res_intercompany WHERE company_from=%s AND company_to=%s",(picking.company_id.id,company_to,))
                    ic_config = cr.fetchone()
                    if ic_config:
                        ic_config = ic_config[0]
                        if ic_config=='draft' and (picking.state=='draft' or not parent_check):
                            return company_to
                        elif ic_config=='confirm' and (picking.state=='confirmed' or not parent_check):
                            return company_to
        return False
    
    
    def _need_to_update_intercompany_object(self, cr, uid, id, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        picking = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(picking.partner_id.id,))
        company_to = cr.fetchone()
        if company_to:
            company_to = company_to[0]
            if picking.picking_ic_id:
                cr.execute("SELECT do2is FROM res_intercompany WHERE company_from=%s AND company_to=%s",(picking.company_id.id,company_to,))
                ic_config = cr.fetchone()
                if ic_config:
                    ic_config = ic_config[0]
                    if ic_config=='draft':
                        return ic_config
        return False
    
    
    def _generate_is_from_do(self, cr, uid, pick, company_id, context=None):
        #print ">>>>>>>> Create IS"
        context = context or {}
        context.update({'picking_type':'in'})
        pick_pool = self.pool.get('stock.picking.in')
        move_pool = self.pool.get('stock.move')
        part = pick.company_id.partner_id
        
        location_id      = move_pool._default_location_source(cr, uid, context=context)
        location_dest_id = part.property_stock_supplier.id or move_pool._default_location_destination(cr, uid, context=context)
        
        cr.execute("SELECT id FROM stock_location WHERE company_id=%s AND name = 'Stock'",(company_id,))
        location = cr.fetchone()
        if location and location[0]:
            location_dest_id = location[0]
        
        ic_id = pick_pool.create(cr, uid, {
            'partner_id': part.id,
            'picking_ic_id': pick.id,
            'is_locked': True,
            'ic_create': True,
            'company_id': company_id,
            'type':'in',
        }, context={'force_ic_checking':False})
        
        for move_line in pick.move_lines:
            move_pool.create(cr, uid, {
                'picking_id': ic_id,
                'name': move_line.name,
                'product_qty': move_line.product_qty,
                'product_id': move_line.product_id and move_line.product_id.id or False,
                'product_uom': move_line.product_uom.id,
                'price_unit': move_line.price_unit,
                'price_currency_id': move_line.price_currency_id and move_line.price_currency_id.id or False,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'partner_id': res,
                'company_id': company_id
            })
        return ic_id
    
    
    def create(self, cr, uid, vals, context=None):
        #print '----------DO-------------------'
        #print vals, context
        new_id = super(stock_picking_out, self).create(cr, uid, vals, context=context)
        context = context or {}
        if context.get('force_ic_checking',True):
            res = self._need_to_create_intercompany_object(cr, uid, new_id, context=context)
            if res:
                # We automatically create the linked object
                pick = self.browse(cr, uid, new_id, context=context)
                ic_id = self._generate_is_from_do(cr, 1, pick, res, context=context)
                self.write(cr, uid, new_id, {'picking_ic_id':ic_id,}, context={'force_ic_checking':False})
            
            elif self._need_to_create_intercompany_object(cr, uid, new_id, parent_check=False, context=context):
                # A linked object may have been created by standard OpenERP (Eg: Delivery Order created by SO confirmation)
                new_pick = self.browse(cr, uid, new_id, context=context)
                new_pick_vals = {}
                ic_pick_vals  = {}
                ic_id         = False
                
                if new_pick.sale_id:
                    if new_pick.sale_id.ic_create:
                        new_pick_vals.update({'ic_create': True,})
                    if new_pick.sale_id.is_locked:
                        new_pick_vals.update({'is_locked': True,})
                    
                    if new_pick.sale_id.purchase_id and new_pick.sale_id.purchase_id:
                        ic_id = self.pool.get('stock.picking.in').search(cr, uid, [('purchase_id','=',new_pick.sale_id.purchase_id.id)], context=context)
                        ic_id = ic_id and ic_id[0] or False
                        
                        if ic_id:
                            new_pick_vals.update({'picking_ic_id': ic_id,})
                            
                            ic_pick_vals.update({'picking_ic_id': new_id,})
                            if new_pick.sale_id.purchase_id.ic_create:
                                ic_pick_vals.update({'ic_create': True,})
                            if new_pick.sale_id.purchase_id.is_locked:
                                ic_pick_vals.update({'is_locked': True,})
                    
                    if new_pick_vals:
                        self.write(cr, uid, new_id, new_pick_vals, context={'force_ic_checking':False})
                    if ic_pick_vals and ic_id:
                        self.write(cr, uid, ic_id, ic_pick_vals, context={'force_ic_checking':False})
        return new_id
    
    
    def write(self, cr, uid, ids, vals, context=None):
        #print '----------DO-------------------'
        #print vals, context
        context = context or {}
        if type(ids)!=type([]):
            ids = [ids]
        
        if not context:
            wf_service = netsvc.LocalService("workflow")
            for pick in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if not pick.ic_create:
                    if pick.picking_ic_id:
                        if 'state' in vals:
                            if vals['state'] == 'cancel':
                                wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_cancel', cr)
                            elif vals['state'] in ['confirmed'] and self._need_to_update_intercompany_object(cr, uid, pick.id, context=context):
                                wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_confirm', cr)
                    else:
                        res = self._need_to_create_intercompany_object(cr, uid, pick.id, context=context)
                        if res:
                            ic_id = self._generate_is_from_do(cr, 1, pick, res, context=context)
                            wf_service.trg_validate(1, 'stock.picking', ic_id, 'button_confirm', cr)
                            new_vals.update({'picking_ic_id':ic_id,})
                super(stock_picking_out, self).write(cr, uid, [pick.id], new_vals, context=context)
        
        elif len(vals)<=1 and ('message_follower_ids' in vals):
            super(stock_picking_out, self).write(cr, uid, ids, vals, context=context)
        
        elif context.get('force_ic_checking',True):
            picking_pool = self.pool.get('stock.picking.in')
            wf_service   = netsvc.LocalService("workflow")
            for pick in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if 'is_locked' in new_vals:
                    if pick.picking_ic_id:
                        picking_pool.write(cr, uid, [pick.picking_ic_id.id], {'picking_ic_id':False,}, context={'force_ic_checking':False})
                    new_vals.update({'picking_ic_id':False,})
                    super(stock_picking_out, self).write(cr, uid, [pick.id], new_vals, context=context)
                    
                elif not pick.is_locked:
                    if not pick.ic_create:
                        if pick.picking_ic_id:
                            if 'state' in vals:
                                if vals['state'] == 'cancel':
                                    wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_cancel', cr)
                                elif vals['state'] in ['confirmed'] and self._need_to_update_intercompany_object(cr, uid, pick.id, context=context):
                                    wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_confirm', cr)
                                
                            else:
                                #print ">>>>>>>> CANCEL Incoming Shipment"
                                super(stock_picking_out, self).write(cr, uid, [pick.id], vals, context=context)
                                wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_cancel', cr)
                                cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(pick.partner_id.id,))
                                company_to = cr.fetchone()[0]
                                ic_id = self._generate_is_from_do(cr, 1, pick, company_to, context=context)
                                new_vals = {}
                                new_vals.update({'picking_ic_id':ic_id,})
                        else:
                            res = self._need_to_create_intercompany_object(cr, uid, pick.id, context=context)
                            if res:
                                ic_id = self._generate_is_from_do(cr, 1, pick, res, context=context)
                                wf_service.trg_validate(1, 'stock.picking', ic_id, 'button_confirm', cr)
                                new_vals.update({'picking_ic_id':ic_id,})
                    super(stock_picking_out, self).write(cr, uid, [pick.id], new_vals, context=context)
                else:
                    raise osv.except_osv(_('Invalid Action!'), _('You can not update this Delivery Order, because it is Locked by Inter-Company process.'))
        else:
            super(stock_picking_out, self).write(cr, uid, ids, vals, context=context)
        return True
    
    
    _columns = {
        'is_locked':     fields.boolean('Locked for Intercompany'),
        'ic_create':     fields.boolean('Intercompany Picking generated'),
        'picking_ic_id': fields.many2one('stock.picking.in', 'Incoming Shipment'),
    }
stock_picking_out()



class stock_picking(osv.osv):
    _inherit = "stock.picking"
    _name    = "stock.picking"
    
    def _need_to_create_intercompany_object(self, cr, uid, id, parent_check=True, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        picking = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(picking.partner_id.id,))
        company_to = cr.fetchone()
        if company_to:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, 1, uid).company_ids):
                if picking.type=='in':
                    if not picking.sale_id or not picking.sale_id.purchase_id or not parent_check:
                        cr.execute("SELECT is2do FROM res_intercompany WHERE company_from=%s AND company_to=%s",(picking.company_id.id,company_to,))
                        ic_config = cr.fetchone()
                        if ic_config:
                            ic_config = ic_config[0]
                            if ic_config=='draft' and (picking.state=='draft' or not parent_check):
                                return company_to
                            elif ic_config=='confirm' and (picking.state=='confirmed' or not parent_check):
                                return company_to
                elif picking.type=='out':
                    if not picking.sale_id or not picking.sale_id.purchase_id or not parent_check:
                        cr.execute("SELECT do2is FROM res_intercompany WHERE company_from=%s AND company_to=%s",(picking.company_id.id,company_to,))
                        ic_config = cr.fetchone()
                        if ic_config:
                            ic_config = ic_config[0]
                            if ic_config=='draft' and (picking.state=='draft' or not parent_check):
                                return company_to
                            elif ic_config=='confirm' and (picking.state=='draft' or not parent_check):
                                return company_to
        return False
    
    
    def _need_to_update_intercompany_object(self, cr, uid, id, context=None):
        context = context or {}
        if type(id)==type([]):
            raise osv.except_osv(_('Invalid Action!'), _('You must use this function for one object, not a list.'))
        
        picking = self.browse(cr, uid, id, context=context)
        cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(picking.partner_id.id,))
        company_to = cr.fetchone()
        if company_to:
            company_to = company_to[0]
            if company_to in map(lambda x: x.id, self.pool.get('res.users').browse(cr, 1, uid).company_ids):
                if picking.picking_ic_id:
                    if picking.type=='in':
                        cr.execute("SELECT is2do FROM res_intercompany WHERE company_from=%s AND company_to=%s",(picking.company_id.id,company_to,))
                    else:
                        cr.execute("SELECT do2is FROM res_intercompany WHERE company_from=%s AND company_to=%s",(picking.company_id.id,company_to,))
                    ic_config = cr.fetchone()
                    if ic_config:
                        ic_config = ic_config[0]
                        if ic_config=='draft':
                            return ic_config
        return False
    
    
    def create(self, cr, uid, vals, context=None):
        if vals and 'type' in vals:
            if vals['type'] == 'in':
                return self.pool.get('stock.picking.in').create(cr, uid, vals, context=context)
            elif vals['type'] == 'out':
                return self.pool.get('stock.picking.out').create(cr, uid, vals, context=context)
        return super(stock_picking, self).create(cr, uid, vals, context=context)
    
    
    def write(self, cr, uid, ids, vals, context=None):
        #print '----------PICK-------------------'
        #print vals, context
        context = context or {}
        if type(ids)!=type([]):
            ids = [ids]
        
        if not context:
            wf_service = netsvc.LocalService("workflow")
            for pick in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if pick.type in ['out','in']:
                    if not pick.ic_create:
                        if pick.picking_ic_id:
                            if 'state' in vals:
                                if vals['state'] == 'cancel':
                                    wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_cancel', cr)
                                elif vals['state'] in ['confirmed'] and self._need_to_update_intercompany_object(cr, uid, pick.id, context=context):
                                    wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_confirm', cr)
                        else:
                            res = self._need_to_create_intercompany_object(cr, uid, pick.id, context=context)
                            if res:
                                if pick.type=='out':
                                    ic_id = self.pool.get('stock.picking.out')._generate_is_from_do(cr, 1, pick, res, context=context)
                                else:
                                    ic_id = self.pool.get('stock.picking.in')._generate_do_from_is(cr, 1, pick, res, context)
                                wf_service.trg_validate(1, 'stock.picking', ic_id, 'button_confirm', cr)
                                new_vals.update({'picking_ic_id':ic_id,})
                super(stock_picking, self).write(cr, uid, [pick.id], new_vals, context=context)
        
        elif len(vals)<=1 and ('message_follower_ids' in vals):
            super(stock_picking, self).write(cr, uid, ids, vals, context=context)
        
        elif context.get('force_ic_checking',True):
            picking_pool = self.pool.get('stock.picking')
            wf_service   = netsvc.LocalService("workflow")
            for pick in self.browse(cr, uid, ids, context=context):
                new_vals = vals
                if pick.type in ['out','in']:
                    if 'is_locked' in new_vals:
                        if pick.picking_ic_id:
                            picking_pool.write(cr, uid, [pick.picking_ic_id.id], {'picking_ic_id':False,}, context={'force_ic_checking':False})
                        new_vals.update({'picking_ic_id':False,})
                        super(stock_picking, self).write(cr, uid, [pick.id], new_vals, context=context)
                        
                    elif not pick.is_locked:
                        if not pick.ic_create:
                            if pick.picking_ic_id:
                                if 'state' in vals:
                                    if vals['state'] == 'cancel':
                                        wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_cancel', cr)
                                    elif vals['state'] in ['confirmed'] and self._need_to_update_intercompany_object(cr, uid, pick.id, context=context):
                                        wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_confirm', cr)
                                    
                                else:
                                    super(stock_picking, self).write(cr, uid, [pick.id], vals, context=context)
                                    wf_service.trg_validate(1, 'stock.picking', pick.picking_ic_id.id, 'button_cancel', cr)
                                    cr.execute("SELECT id FROM res_company WHERE partner_id=%s",(pick.partner_id.id,))
                                    company_to = cr.fetchone()[0]
                                    if pick.type=='out':
                                        ic_id = self.pool.get('stock.picking.out')._generate_is_from_do(cr, 1, pick, res, context=context)
                                    else:
                                        ic_id = self.pool.get('stock.picking.in')._generate_do_from_is(cr, 1, pick, res, context=context)
                                    new_vals = {}
                                    new_vals.update({'picking_ic_id':ic_id,})
                            else:
                                res = self._need_to_create_intercompany_object(cr, uid, pick.id, context=context)
                                if res:
                                    if pick.type=='out':
                                        ic_id = self.pool.get('stock.picking.out')._generate_is_from_do(cr, 1, pick, res, context=context)
                                    else:
                                        ic_id = self.pool.get('stock.picking.in')._generate_do_from_is(cr, 1, pick, res, context=context)
                                    wf_service.trg_validate(1, 'stock.picking', ic_id, 'button_confirm', cr)
                                    new_vals.update({'picking_ic_id':ic_id,})
                        super(stock_picking, self).write(cr, uid, [pick.id], new_vals, context=context)
                    else:
                        raise osv.except_osv(_('Invalid Action!'), _('You can not update this Delivery Order, because it is Locked by Inter-Company process.'))
                else:
                    super(stock_picking, self).write(cr, uid, [pick.id], new_vals, context=context)
        else:
            super(stock_picking, self).write(cr, uid, ids, vals, context=context)
        return True
    
    
    # function below may be used later
    def do_partial_unused(self, cr, uid, ids, partial_datas, context=None):
        """ Makes partial picking and moves done.
        @param partial_datas : Dictionary containing details of partial picking
                          like partner_id, partner_id, delivery_date,
                          delivery moves with product_id, product_qty, uom
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        else:
            context = dict(context)
        res = {}
        move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        currency_obj = self.pool.get('res.currency')
        uom_obj = self.pool.get('product.uom')
        sequence_obj = self.pool.get('ir.sequence')
        wf_service = netsvc.LocalService("workflow")
        
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.is_locked:
                raise osv.except_osv(_('Invalid Action!'), _('You can not process this Picking, because it is Locked by Inter-Company process.'))
            
            new_picking = None
            complete, too_many, too_few = [], [], []
            move_product_qty, prodlot_ids, product_avail, partial_qty, product_uoms = {}, {}, {}, {}, {}
            for move in pick.move_lines:
                if move.state in ('done', 'cancel'):
                    continue
                partial_data = partial_datas.get('move%s'%(move.id), {})
                product_qty = partial_data.get('product_qty',0.0)
                move_product_qty[move.id] = product_qty
                product_uom = partial_data.get('product_uom',False)
                product_price = partial_data.get('product_price',0.0)
                product_currency = partial_data.get('product_currency',False)
                prodlot_id = partial_data.get('prodlot_id')
                prodlot_ids[move.id] = prodlot_id
                product_uoms[move.id] = product_uom
                partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
                if move.product_qty == partial_qty[move.id]:
                    complete.append(move)
                elif move.product_qty > partial_qty[move.id]:
                    too_few.append(move)
                else:
                    too_many.append(move)

                # Average price computation
                if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                    product = product_obj.browse(cr, uid, move.product_id.id)
                    move_currency_id = move.company_id.currency_id.id
                    context['currency_id'] = move_currency_id
                    qty = uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)

                    if product.id in product_avail:
                        product_avail[product.id] += qty
                    else:
                        product_avail[product.id] = product.qty_available

                    if qty > 0:
                        new_price = currency_obj.compute(cr, uid, product_currency,
                                move_currency_id, product_price)
                        new_price = uom_obj._compute_price(cr, uid, product_uom, new_price,
                                product.uom_id.id)
                        if product.qty_available <= 0:
                            new_std_price = new_price
                        else:
                            # Get the standard price
                            amount_unit = product.price_get('standard_price', context=context)[product.id]
                            new_std_price = ((amount_unit * product_avail[product.id])\
                                + (new_price * qty))/(product_avail[product.id] + qty)
                        # Write the field according to price type field
                        product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})

                        # Record the values that were chosen in the wizard, so they can be
                        # used for inventory valuation if real-time valuation is enabled.
                        move_obj.write(cr, uid, [move.id],
                                {'price_unit': product_price,
                                 'price_currency_id': product_currency})


            for move in too_few:
                product_qty = move_product_qty[move.id]
                if not new_picking:
                    new_picking_name = pick.name
                    self.write(cr, uid, [pick.id], 
                               {'name': sequence_obj.get(cr, uid,
                                            'stock.picking.%s'%(pick.type)),
                               })
                    new_picking = self.copy(cr, uid, pick.id,
                            {
                                'name': new_picking_name,
                                'move_lines' : [],
                                'state':'draft',
                                'picking_ic_id': False,
                            })
                if product_qty != 0:
                    defaults = {
                            'product_qty' : product_qty,
                            'product_uos_qty': product_qty, #TODO: put correct uos_qty
                            'picking_id' : new_picking,
                            'state': 'assigned',
                            'move_dest_id': False,
                            'price_unit': move.price_unit,
                            'product_uom': product_uoms[move.id]
                    }
                    prodlot_id = prodlot_ids[move.id]
                    if prodlot_id:
                        defaults.update(prodlot_id=prodlot_id)
                    move_obj.copy(cr, uid, move.id, defaults)
                move_obj.write(cr, uid, [move.id],
                        {
                            'product_qty': move.product_qty - partial_qty[move.id],
                            'product_uos_qty': move.product_qty - partial_qty[move.id], #TODO: put correct uos_qty
                            'prodlot_id': False,
                            'tracking_id': False,
                        })

            if new_picking:
                move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
            for move in complete:
                defaults = {'product_uom': product_uoms[move.id], 'product_qty': move_product_qty[move.id]}
                if prodlot_ids.get(move.id):
                    defaults.update({'prodlot_id': prodlot_ids[move.id]})
                move_obj.write(cr, uid, [move.id], defaults)
            for move in too_many:
                product_qty = move_product_qty[move.id]
                defaults = {
                    'product_qty' : product_qty,
                    'product_uos_qty': product_qty, #TODO: put correct uos_qty
                    'product_uom': product_uoms[move.id]
                }
                prodlot_id = prodlot_ids.get(move.id)
                if prodlot_ids.get(move.id):
                    defaults.update(prodlot_id=prodlot_id)
                if new_picking:
                    defaults.update(picking_id=new_picking)
                move_obj.write(cr, uid, [move.id], defaults)

            # At first we confirm the new picking (if necessary)
            if new_picking:
                wf_service.trg_validate(1, 'stock.picking', new_picking, 'button_confirm', cr)
                # Then we finish the good picking
                self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
                self.action_move(cr, uid, [new_picking], context=context)
                wf_service.trg_validate(1, 'stock.picking', new_picking, 'button_done', cr)
                wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
                delivered_pack_id = new_picking
                back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                self.message_post(cr, uid, ids, body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name), context=context)
            else:
                self.action_move(cr, uid, [pick.id], context=context)
                wf_service.trg_validate(1, 'stock.picking', pick.id, 'button_done', cr)
                delivered_pack_id = pick.id

            delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
            res[pick.id] = {'delivered_picking': delivered_pack.id or False}
            
            # Create IC linked BackOrder
            if new_picking and pick.picking_ic_id:
                stock_pool = self.pool.get('stock.picking.%s'%(pick.type))
                company_to = stock_pool._need_to_create_intercompany_object(cr, uid, new_picking, parent_check=False, context=context)
                if company_to:
                    pick = self.browse(cr, uid, new_picking, context=context)
                    if pick.type == 'out':
                        ic_id = stock_pool._generate_is_from_do(cr, 1, pick, company_to, context=context)
                    else:
                        ic_id = stock_pool._generate_do_from_is(cr, 1, pick, company_to, context=context)
                    self.write(cr, uid, new_picking, {'picking_ic_id':ic_id,}, context={'force_ic_checking':False})
                    
                    # At first we confirm the new picking (if necessary)
                    wf_service.trg_validate(1, 'stock.picking', ic_id, 'button_confirm', cr)
                    # Then we finish the good picking
                    self.write(cr, uid, [pick.picking_ic_id.id], {'backorder_id': ic_id})
                    self.action_move(cr, uid, [ic_id], context=context)
                    wf_service.trg_validate(1, 'stock.picking', ic_id, 'button_done', cr)
                    wf_service.trg_write(uid, 'stock.picking', pick.picking_ic_id.id, cr)
                    delivered_pack_id = ic_id
                    back_order_name = self.browse(cr, uid, delivered_pack_id, context=context).name
                    self.message_post(cr, uid, ids, body=_("Back order <em>%s</em> has been <b>created</b>.") % (back_order_name), context=context)
                    
        return res
        
        
    _columns = {
        'is_locked':     fields.boolean('Locked for Intercompany'),
        'ic_create':     fields.boolean('Intercompany Picking generated'),
        'picking_ic_id': fields.many2one('stock.picking', 'Stock Picking'),
    }
stock_picking()

    

class stock_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"
    _name    = "stock.partial.picking"
    
    def do_partial_unused(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'Partial picking processing may only be done one at a time.'
        stock_picking = self.pool.get('stock.picking')
        stock_move = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        partial = self.browse(cr, uid, ids[0], context=context)
        partial_data = {
            'delivery_date' : partial.date
        }
        
        if partial.picking_id.is_locked:
            raise osv.except_osv(_('Invalid Action!'), _('You can not process this Picking, because it is Locked by Inter-Company process.'))
        
        
        picking_type = partial.picking_id.type
        for wizard_line in partial.move_ids:
            line_uom = wizard_line.product_uom
            move_id = wizard_line.move_id.id

            #Quantiny must be Positive
            if wizard_line.quantity < 0:
                raise osv.except_osv(_('Warning!'), _('Please provide proper Quantity.'))

            #Compute the quantity for respective wizard_line in the line uom (this jsut do the rounding if necessary)
            qty_in_line_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, line_uom.id)

            if line_uom.factor and line_uom.factor <> 0:
                if float_compare(qty_in_line_uom, wizard_line.quantity, precision_rounding=line_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _('The unit of measure rounding does not allow you to ship "%s %s", only roundings of "%s %s" is accepted by the Unit of Measure.') % (wizard_line.quantity, line_uom.name, line_uom.rounding, line_uom.name))
            if move_id:
                #Check rounding Quantity.ex.
                #picking: 1kg, uom kg rounding = 0.01 (rounding to 10g),
                #partial delivery: 253g
                #=> result= refused, as the qty left on picking would be 0.747kg and only 0.75 is accepted by the uom.
                initial_uom = wizard_line.move_id.product_uom
                #Compute the quantity for respective wizard_line in the initial uom
                qty_in_initial_uom = uom_obj._compute_qty(cr, uid, line_uom.id, wizard_line.quantity, initial_uom.id)
                without_rounding_qty = (wizard_line.quantity / line_uom.factor) * initial_uom.factor
                if float_compare(qty_in_initial_uom, without_rounding_qty, precision_rounding=initial_uom.rounding) != 0:
                    raise osv.except_osv(_('Warning!'), _('The rounding of the initial uom does not allow you to ship "%s %s", as it would let a quantity of "%s %s" to ship and only roundings of "%s %s" is accepted by the uom.') % (wizard_line.quantity, line_uom.name, wizard_line.move_id.product_qty - without_rounding_qty, initial_uom.name, initial_uom.rounding, initial_uom.name))
            else:
                seq_obj_name =  'stock.picking.' + picking_type
                move_id = stock_move.create(cr,1,{'name' : self.pool.get('ir.sequence').get(cr, uid, seq_obj_name),
                                                    'product_id': wizard_line.product_id.id,
                                                    'product_qty': wizard_line.quantity,
                                                    'product_uom': wizard_line.product_uom.id,
                                                    'prodlot_id': wizard_line.prodlot_id.id,
                                                    'location_id' : wizard_line.location_id.id,
                                                    'location_dest_id' : wizard_line.location_dest_id.id,
                                                    'picking_id': partial.picking_id.id
                                                    },context=context)
                stock_move.action_confirm(cr, 1, [move_id], context)
            partial_data['move%s' % (move_id)] = {
                'product_id': wizard_line.product_id.id,
                'product_qty': wizard_line.quantity,
                'product_uom': wizard_line.product_uom.id,
                'prodlot_id': wizard_line.prodlot_id.id,
            }
            if (picking_type == 'in') and (wizard_line.product_id.cost_method == 'average'):
                partial_data['move%s' % (wizard_line.move_id.id)].update(product_price=wizard_line.cost,
                                                                  product_currency=wizard_line.currency.id)
        stock_picking.do_partial(cr, 1, [partial.picking_id.id], partial_data, context=context)
        return {'type': 'ir.actions.act_window_close'}

stock_partial_picking()



class stock_move(osv.osv):
    _inherit = "stock.move"
    _name    = "stock.move"
    
    def _default_location_destination(self, cr, uid, context=None):
        """ Gets default address of partner for destination location
        @return: Address id or False
        """
        mod_obj = self.pool.get('ir.model.data')
        picking_type = context.get('picking_type')
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
        else:
            location_xml_id = False
            if picking_type  == 'internal':
                location_xml_id = 'stock_location_stock'
                location_model, location_id = mod_obj.get_object_reference(cr, uid, 'stock', location_xml_id)
            elif picking_type == 'out':
                location_xml_id = 'stock_location_customers'
                location_model, location_id = mod_obj.get_object_reference(cr, uid, 'stock', location_xml_id)
            else:      
                user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
                company_id = user.company_id.id
                cr.execute("SELECT id FROM stock_location WHERE company_id=%s AND name = 'Stock'",(company_id,))
                location_id = cr.fetchone()
                location_id = location_id[0]
        return location_id
    
    
    def _default_location_source(self, cr, uid, context=None):
        """ Gets default address of partner for source location
        @return: Address id or False
        """
        mod_obj = self.pool.get('ir.model.data')
        picking_type = context.get('picking_type')
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
        else:
            location_xml_id = False
            if picking_type == 'in':
                location_xml_id = 'stock_location_suppliers'
                location_model, location_id = mod_obj.get_object_reference(cr, uid, 'stock', location_xml_id)
            elif picking_type in ('internal'):
                location_xml_id = 'stock_location_stock'
                location_model, location_id = mod_obj.get_object_reference(cr, uid, 'stock', location_xml_id)
            else:
                user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
                company_id = user.company_id.id
                cr.execute("SELECT id FROM stock_location WHERE company_id=%s AND name = 'Stock'",(company_id,))
                location_id = cr.fetchone()
                location_id = location_id[0]       
        return location_id
    
    
    # YG: Why ????
    def onchange_move_type(self, cr, uid, ids, type, context=None):
        """ On change of move type gives source and destination location.
        @param type: Move Type
        @return: Dictionary of values
        """
        return False#{'value':{'location_id': source_location and source_location[1] or False, 'location_dest_id': dest_location and dest_location[1] or False}}


    _defaults = {
        'location_id':      _default_location_source,
        'location_dest_id': _default_location_destination,
    }
stock_move()
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: