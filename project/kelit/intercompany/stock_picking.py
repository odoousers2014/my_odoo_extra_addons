# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

from openerp import SUPERUSER_ID, netsvc
from openerp.osv import fields, osv
from openerp.tools.translate import _


class stock_move(osv.osv):
    _inherit = 'stock.move'
    _name = 'stock.move'

    def _default_location_source(self, cr, uid, context=None):
        """
        Gets default address of partner for source location
        @return: Address id or False
        """
        context = context or {}
        mod_pool = self.pool.get('ir.model.data')
        picking_type = context.get('picking_type')
        location_id = False

        if context.get('move_line', []):
            try:
                location_id = context['move_line'][0][2]['location_id']
            except:
                pass
        elif context.get('address_in_id', False):
            part_obj_add = self.pool.get('res.partner').browse(
                cr, uid, context['address_in_id'], context=context)
            if part_obj_add:
                location_id = part_obj_add.property_stock_supplier.id
        else:
            location_xml_id = False
            if picking_type == 'in':
                location_xml_id = 'stock_location_suppliers'
                location_model, location_id = mod_pool.get_object_reference(
                    cr, uid, 'stock', location_xml_id)
            elif picking_type in ('internal'):
                location_xml_id = 'stock_location_stock'
                location_model, location_id = mod_pool.get_object_reference(
                    cr, uid, 'stock', location_xml_id)
            else:
                company_id = self.pool.get('res.users').browse(
                    cr, uid, uid, context=context).company_id.id
                cr.execute("""
                SELECT
                    id
                FROM
                    stock_location
                WHERE
                    company_id=%s AND name = 'Stock'
                """, (company_id,))
                location_id = cr.fetchone()[0]
        return location_id

    def _default_location_destination(self, cr, uid, context=None):
        """
        Gets default address of partner for destination location
        @return: Address id or False
        """

        context = context or {}
        mod_pool = self.pool.get('ir.model.data')
        picking_type = context.get('picking_type')
        location_id = False

        if context.get('move_line', []):
            if context['move_line'][0]:
                if isinstance(context['move_line'][0], (tuple, list)):
                    location_id = (context['move_line'][0][2]
                                   and context['move_line'][0][2].get(
                                       'location_dest_id', False)
                                   )
                else:
                    move_list = self.pool.get('stock.move').read(
                        cr, uid, context['move_line'][0], ['location_dest_id'])
                    location_id = (move_list
                                   and move_list['location_dest_id'][0]
                                   or False)
        elif context.get('address_out_id', False):
            property_out = self.pool.get('res.partner').browse(
                cr, uid, context['address_out_id'],
                context).property_stock_customer
            location_id = property_out and property_out.id or False
        else:
            location_xml_id = False
            if picking_type == 'internal':
                location_xml_id = 'stock_location_stock'
                location_model, location_id = mod_pool.get_object_reference(
                    cr, uid, 'stock', location_xml_id)
            elif picking_type == 'out':
                location_xml_id = 'stock_location_customers'
                location_model, location_id = mod_pool.get_object_reference(
                    cr, uid, 'stock', location_xml_id)
            else:
                company_id = self.pool.get('res.users').browse(
                    cr, uid, uid, context=context).company_id.id
                cr.execute("""
                SELECT
                    id
                FROM
                    stock_location
                WHERE
                    company_id=%s AND name = 'Stock'
                """, (company_id,))
                location_id = cr.fetchone()[0]
        return location_id
    
    def onchange_move_type(self, cr, uid, ids, type, context=None):
        """ On change of move type gives sorce and destination location.
        @param type: Move Type
        @return: Dictionary of values
        """
        user_pool = self.pool.get('res.users')
        
        if type == 'in':
            r
            
            
            
        
        
        mod_obj = self.pool.get('ir.model.data')
        location_source_id = 'stock_location_stock'
        location_dest_id = 'stock_location_stock'
        if type == 'in':
            location_source_id = 'stock_location_suppliers'
            location_dest_id = 'stock_location_stock'
        elif type == 'out':
            location_source_id = 'stock_location_stock'
            location_dest_id = 'stock_location_customers'
            
        source_location = mod_obj.get_object_reference(cr, uid, 'stock', location_source_id)
        dest_location = mod_obj.get_object_reference(cr, uid, 'stock', location_dest_id)
        return {'value':{'location_id': source_location and source_location[1] or False, 'location_dest_id': dest_location and dest_location[1] or False}}


    _defaults = {
        'location_id': _default_location_source,
        'location_dest_id': _default_location_destination,
    }
stock_move()


class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _name = 'stock.picking'

    _columns = {
        'is_locked': fields.boolean('Locked for Intercompany'),
        'ic_create': fields.boolean('Intercompany Picking generated'),
        'picking_ic_id': fields.many2one('stock.picking', 'Stock Picking'),
    }

    def get_intercompany(self, cr, uid, id, context=None):
        """
        Return company_from company_to
        """

        assert isinstance(id, int) or isinstance(id, long)
        cr.execute("""
        SELECT
            pick.company_id AS from_c, cmp.id AS to_c, cmp.intercompany_uid
        FROM
            stock_picking AS pick
            LEFT JOIN res_partner AS part ON (pick.partner_id=part.id)
            LEFT JOIN res_company AS cmp  ON (part.id=cmp.partner_id)
        WHERE
            pick.id=%s
        """, (id,))
        return cr.fetchone()

    def need_to_create_intercompany_picking(
            self, cr, uid, ids, o2o_field_name=None, node=None, context=None):
        """
        @o2o_field_name
        @node,  draft' or 'confirm', res.intercompany.so2po value,
        """

        intercompany_obj = self.pool.get('res.intercompany')
        cf, ct, ic_uid = self.get_intercompany(cr, uid, ids[0],
                                               context=context)
        return intercompany_obj.check_need_create_intercompany_object(
            cr, uid, cf, ct, o2o_field_name, node)

    def action_draft(self, cr, uid, ids, context=None):
        """
        Picking wkf Draft action,
        Use Administrator operate intercompany action
        """

        assert len(ids) == 1
        self.action_intercompany(cr, SUPERUSER_ID, ids,
                                 node='draft', context=context)
        return True

    def action_confirm(self, cr, uid, ids, context=None):
        """
        Action confirm include intercompany action
        """

        res = super(stock_picking, self).action_confirm(cr, uid, ids,
                                                        context=context)
        if res:
            self.action_intercompany(cr, uid, ids, node='confirm',
                                     context=context)
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        """
        """

        res = super(stock_picking, self).action_cancel(cr, uid, ids,
                                                       context=context)
        wkf_service = netsvc.LocalService("workflow")

        if res:
            for pick_id in ids:
                ic_uid = self.get_intercompany(cr, uid, pick_id)[2]
                pick_ic_ids = self.search(cr, uid,
                                          [('picking_ic_id', '=', pick_id)]
                                          )
                for pick_ic_id in pick_ic_ids:
                    wkf_service.trg_validate(ic_uid, 'stock.picking',
                                             pick_ic_id, 'button_cancel', cr)

        return res

    def action_intercompany(self, cr, uid, ids, node=None, context=None):
        """
        @node, draft or confirm
        """

        assert len(ids) == 1
        cr.execute("SELECT type FROM stock_picking WHERE id=%s", (ids[0],))
        pick_type = cr.fetchone()[0]

        if pick_type in ['in', 'out']:
            o2o_field_name = pick_type == 'in' and 'is2do' or 'do2is'
            if self.need_to_create_intercompany_picking(
                    cr, uid, ids, o2o_field_name, node=node, context=context):
                self.create_intercompany_picking(
                    cr, uid, ids, self_type=pick_type, context=None)

    def create_intercompany_picking(self, cr, uid,
                                    ids, self_type, context=None):
        """
        prepare out and prepare in is similar, but don to merger it,
        @self_type,  self.type
        """

        pick = self.browse(cr, uid, ids[0])
        cf, ct, ic_uid = self.get_intercompany(cr, uid, ids[0],
                                               context=context)
        picking_pool = (self_type == 'in'
                        and self.pool.get('stock.picking.out')
                        or self.pool.get('stock.picking.in'))

        if self_type == 'in':
            picking_data = self.prepare_intercompany_picking_out_data(
                cr, uid, pick, ct, ic_uid, context=context)
        elif self_type == 'out':
            picking_data = self.prepare_intercompany_picking_in_data(
                cr, uid, pick, ct, ic_uid, context=context)

        return picking_pool.create(cr, ic_uid, picking_data, context=context)

    def prepare_intercompany_picking_out_data(
            self, cr, uid, pick_in, company_to, ic_uid, context=None):
        """
        prepare the picking.out data
        @pick_in  browse record of stock.picking, type == in
        @company_to  the company_id of this picking.out record
        """

        context = context or {}
        # context for to create stock.move, count the location
        context.update({'picking_type': 'out'})
        part_pool = self.pool.get('res.partner')
        customer = part_pool.browse(cr, ic_uid,
                                    pick_in.company_id.partner_id.id)

        location_id = False
        cr.execute("""
        SELECT
            id
        FROM
            stock_location
        WHERE
            company_id=%s
            AND name='Stock'
        """, (company_to,))
        location = cr.fetchone()
        if location and location[0]:
            location_id = location[0]
        location_dest_id = (customer.property_stock_customer
                            and customer.property_stock_customer.id
                            or False)

        if (not location_dest_id or not location_id):
            raise osv.except_osv(
                _('Error!'),
                _("""prepare_intercompany_picking_out_data location%s
                    location_dest%s"""
                  % (location_id, location_dest_id)))

        move_lines_data = [(5,)]
        for move_line in pick_in.move_lines:
            line_data = {
                #'picking_id':        ic_id,
                'name': move_line.name,
                'product_qty': move_line.product_qty,
                'product_id': move_line.product_id.id,
                'product_uom': move_line.product_uom.id,
                'price_unit': move_line.price_unit,
                'price_currency_id': (move_line.price_currency_id
                                      and move_line.price_currency_id.id
                                      or False),
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': company_to,
            }
            move_lines_data.append((0, 0, line_data))

        picking_data = {
            'partner_id': customer.id,
            'picking_ic_id': pick_in.id,
            'is_locked': True,
            'ic_create': True,
            'company_id': company_to,
            'type': 'out',
            'origin': 'IC:' + pick_in.name,
            'move_lines': move_lines_data,
            'magento_bind_ids': False,
            'related_backorder_ids': False,
        }
        return picking_data

    def prepare_intercompany_picking_in_data(
            self, cr, uid, pick_out, company_to, ic_uid, context=None):
        """
        prepare the picking.out data
        @pick_out  browse record of stock.picking, type == in
        @company_to  the company_id of this picking.out record
        """
        context = context or {}
        #context for to create stock.move, count the location
        context.update({'picking_type': 'in'})
        part_pool = self.pool.get('res.partner')
        supplier = part_pool.browse(cr, ic_uid,
                                    pick_out.company_id.partner_id.id)

        location_id = (supplier.property_stock_supplier
                       and supplier.property_stock_supplier.id
                       or False)
        location_dest_id = False
        cr.execute("""
        SELECT
            id
        FROM
            stock_location
        WHERE
            company_id=%s
            AND name='Stock'
        """, (company_to,))
        location = cr.fetchone()
        if location and location[0]:
            location_dest_id = location[0]

        if (not location_dest_id or not location_id):
            raise osv.except_osv(
                _('Error!'),
                _('''prepare_intercompany_picking_in_data
                    location%s location_dest%s'''
                  % (location_id, location_dest_id)))

        move_lines_data = [(5,)]
        for move_line in pick_out.move_lines:
            line_data = {
                #'picking_id': ic_id,
                'name': move_line.name,
                'product_qty': move_line.product_qty,
                'product_id': move_line.product_id.id,
                'product_uom': move_line.product_uom.id,
                'price_unit': move_line.price_unit,
                'price_currency_id': (move_line.price_currency_id
                                      and move_line.price_currency_id.id
                                      or False),
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': company_to,
            }
            move_lines_data.append((0, 0, line_data))

        picking_data = {
            'partner_id': supplier.id,
            'picking_ic_id': pick_out.id,
            'is_locked': True,
            'ic_create': True,
            'company_id': company_to,
            'type': 'in',
            'origin': 'IC:' + pick_out.name,
            'move_lines': move_lines_data,
            'magento_bind_ids': False,
            'related_backorder_ids': False,
        }
        return picking_data

stock_picking()


class stock_picking_in(osv.osv):
    _inherit = 'stock.picking.in'
    _name = 'stock.picking.in'

    _columns = {
        'is_locked': fields.boolean('Locked for Intercompany'),
        'ic_create': fields.boolean('Intercompany Picking generated'),
        'picking_ic_id': fields.many2one('stock.picking', 'Stock Picking'),
    }

    def get_intercompany(self, cr, uid, id, context=None):
        """
        get company from and to
        """

        assert isinstance(id, int) or isinstance(id, long)
        cr.execute("""
        SELECT
            pick.company_id AS from_c, cmp.id AS to_c,cmp.intercompany_uid
        FROM
            stock_picking AS pick
            LEFT JOIN res_partner AS part ON (pick.partner_id=part.id)
            LEFT JOIN res_company AS cmp ON (part.id=cmp.partner_id)
        WHERE pick.id=%s
        """, (id,))
        return cr.fetchone()

    #this function is same as the stock.picking function,
    #when modify this function of  stock.picking ,
    #copy and replace this.
    def prepare_IC_pick_out(self, cr, uid, pick_in, company_to,
                            ic_uid, context=None):
        """
        prepare the picking.out data
        @pick_in  browse record of stock.picking, type == in
        @company_to  the company_id of this picking.out record
        """

        context = context or {}
        # context for to create stock.move, count the location
        context.update({'picking_type': 'out'})
        part_pool = self.pool.get('res.partner')
        customer = part_pool.browse(cr, ic_uid,
                                    pick_in.company_id.partner_id.id)
        location_id = False
        cr.execute("""
        SELECT
            id
        FROM
            stock_location
        WHERE company_id=%s
            AND name='Stock'
        """, (company_to,))

        location = cr.fetchone()
        if location and location[0]:
            location_id = location[0]
        location_dest_id = (customer.property_stock_customer
                            and customer.property_stock_customer.id
                            or False)

        if (not location_dest_id or not location_id):
            raise osv.except_osv(
                _('Error!'),
                _('''prepare_intercompany_picking_out_data
                location%s location_dest%s'''
                    % (location_id, location_dest_id)))

        move_lines_data = [(5,)]
        for move_line in pick_in.move_lines:
            line_data = {
                #'picking_id':        ic_id,
                'name': move_line.name,
                'product_qty': move_line.product_qty,
                'product_id': move_line.product_id.id,
                'product_uom': move_line.product_uom.id,
                'price_unit': move_line.price_unit,
                'price_currency_id': (move_line.price_currency_id
                                      and move_line.price_currency_id.id
                                      or False),
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': company_to,
            }
            move_lines_data.append((0, 0, line_data))

        picking_data = {
            'partner_id': customer.id,
            'picking_ic_id': pick_in.id,
            'is_locked': True,
            'ic_create': True,
            'company_id': company_to,
            'type': 'out',
            'origin': 'IC:' + pick_in.name,
            'move_lines': move_lines_data,
            'magento_bind_ids': False,
            'related_backorder_ids': False,
        }
        return picking_data

    def write(self, cr, uid, ids, values, context=None,
              ban_update_out=False, ban_inverse_out=False):
        """
        @need_update_out
            auto: according the IC set,return True or False
            True   update_intercompany_picking_out
            False  no update_intercompany_picking_out
        @need_inverse_out
            like need_update_out
        """
        print """>>>>picking in write ids:%s ban_update_out%s,
            ban_inverse_out%s
            """ % (ids, ban_update_out, ban_inverse_out)
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]
        res = super(stock_picking_in, self).write(cr, uid, ids,
                                                  values, context=context)

        if res and not ban_update_out:
            self.update_IC_pick_out(cr, SUPERUSER_ID, ids, context=context)
        if res and not ban_inverse_out:
            self.inverse_IC_pick_out(cr, SUPERUSER_ID, ids, context=context)
        return res

    def update_IC_pick_out(self, cr, uid, ids, context=None):
        """
        """
        out_pool = self.pool.get('stock.picking.out')
        ic_pool = self.pool.get('res.intercompany')

        for pick_in in self.browse(cr, uid, ids, context):
            out_id = out_pool.search(
                cr, uid, [('picking_ic_id', '=', pick_in.id)])
            if out_id:
                cf, ct, ic_uid = self.get_intercompany(cr, uid, pick_in.id,
                                                       context=context)
                modify_mode = ic_pool.get_modify_model(cr, uid, cf,
                                                       ct, 'is2do',)
                if modify_mode in ['regular', 'bidirectional']:
                    p_out_data = self.prepare_IC_pick_out(
                        cr, uid, pick_in, ct, ic_uid, context=context)
                    out_pool.write(cr, ic_uid, out_id,
                                   p_out_data, ban_inverse_in=True)
        return True

    def inverse_IC_pick_out(self, cr, uid, ids, context=None):
        """
        """
        pick_out_pool = self.pool.get('stock.picking.out')
        intercompany_pool = self.pool.get('res.intercompany')

        for pick_in in self.browse(cr, uid, ids, context=context):
            pick_out = pick_in.picking_ic_id
            if pick_out:
                company_from, company_to = pick_out_pool.get_intercompany(
                    cr, uid, pick_out.id)[0:2]
                modify_mode = intercompany_pool.get_modify_model(
                    cr, uid, company_from, company_to, 'do2is',)
                if modify_mode in ['inverse', 'bidirectional']:

                    lines_data = [(5,)]
                    #TODO， all location is the same ?
                    #or how to make sure the location?
                    location_id = pick_out.move_lines[0].location_id.id
                    dest_id = pick_out.move_lines[0].location_dest_id.id

                    for in_line in pick_in.move_lines:
                        data = (0, 0, {
                            'name': in_line.name,
                            'product_qty': in_line.product_qty,
                            'product_id': in_line.product_id.id,
                            'product_uom': in_line.product_uom.id,
                            'price_unit': in_line.price_unit,
                            'price_currency_id': (
                                in_line.price_currency_id
                                and in_line.price_currency_id.id
                                or False),
                            'location_id': location_id,
                            'location_dest_id': dest_id,
                            'company_id': pick_out.company_id.id,
                        })
                        lines_data.append(data)

                    pick_out_pool.write(cr, uid, pick_out.id,
                                        {'move_lines': lines_data},
                                        ban_update_in=True)
        return True

    def unlink(self, cr, uid, ids, context=None):
        res = super(stock_picking_in, self).unlink(cr, uid, ids,
                                                   context=context)
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]

        pick_out_pool = self.pool.get('stock.picking.out')
        for pick_in_id in ids:
            pick_out_ids = pick_out_pool.search(
                cr, uid,
                [('picking_ic_id', '=', pick_in_id)],
                context=context)
            if pick_out_ids:
                pick_out_pool.unlink(cr, uid, pick_out_ids, context=context)
        return res

stock_picking_in()


class stock_picking_out(osv.osv):
    _inherit = 'stock.picking.out'
    _name = 'stock.picking.out'

    _columns = {
        'is_locked': fields.boolean('Locked for Intercompany'),
        'ic_create': fields.boolean('Intercompany Picking generated'),
        'picking_ic_id': fields.many2one('stock.picking', 'Stock Picking'),
    }

    def get_intercompany(self, cr, uid, id, context=None):
        """
        get company from and to
        """

        assert isinstance(id, int) or isinstance(id, long)
        cr.execute("""
        SELECT
            pick.company_id AS from_c, cmp.id AS to_c, cmp.intercompany_uid
        FROM stock_picking AS pick
            LEFT JOIN res_partner AS part ON (pick.partner_id=part.id)
            LEFT JOIN res_company AS cmp  ON (part.id=cmp.partner_id)
        WHERE pick.id=%s
        """, (id,))
        return cr.fetchone()

    def write(self, cr, uid, ids, values, context=None,
              ban_update_in=False, ban_inverse_in=False):
        """
        """

        res = super(stock_picking_out, self).write(cr, uid, ids,
                                                   values, context=context)
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]
        if res and not ban_update_in:
            self.update_IC_pick_in(cr, SUPERUSER_ID, ids, context=context)
        if res and not ban_inverse_in:
            self.inverse_IC_pick_in(cr, SUPERUSER_ID, ids, context=context)

        return res

    def update_IC_pick_in(self, cr, uid, ids, context=None):
        pick_in_obj = self.pool.get('stock.picking.in')
        ic_pool = self.pool.get('res.intercompany')

        for pick_out in self.browse(cr, uid, ids, context):
            pick_in_id = pick_in_obj.search(
                cr, uid, [('picking_ic_id', '=', pick_out.id)])
            if pick_in_id:
                cf, ct, ic_uid = self.get_intercompany(cr, uid, pick_out.id,
                                                       context=context)
                modify_mode = ic_pool.get_modify_model(cr, uid, cf, ct,
                                                       'do2is',)
                if modify_mode in ['regular', 'bidirectional']:
                    p_in_data = self.prepare_intercompany_picking_in_data(
                        cr, uid, pick_out, ct, ic_uid, context=context)
                    pick_in_obj.write(cr, ic_uid, pick_in_id, p_in_data,
                                      ban_inverse_out=True)
        return True

    def inverse_IC_pick_in(self, cr, uid, ids, context=None):
        """
        """

        pick_in_pool = self.pool.get('stock.picking.in')
        intercompany_pool = self.pool.get('res.intercompany')

        for pick_out in self.browse(cr, uid, ids, context=context):
            pick_in = pick_out.picking_ic_id
            if pick_in:
                cf, ct = pick_in_pool.get_intercompany(cr, uid,
                                                       pick_in.id)[0:2]
                modify_mode = intercompany_pool.get_modify_model(cr, uid, cf,
                                                                 ct, 'is2do',)
                if modify_mode in ['inverse', 'bidirectional']:
                    lines_data = [(5,)]
                    #TODO， all location is the same ?
                    #or how to make sure the location?
                    location_id = pick_in.move_lines[0].location_id.id
                    dest_id = pick_in.move_lines[0].location_dest_id.id

                    for out_line in pick_out.move_lines:
                        data = (0, 0, {
                            'picking_id': pick_in.id,
                            'name': out_line.name,
                            'product_qty': out_line.product_qty,
                            'product_id': out_line.product_id.id,
                            'product_uom': out_line.product_uom.id,
                            'price_unit': out_line.price_unit,
                            'price_currency_id': (
                                out_line.price_currency_id
                                and out_line.price_currency_id.id
                                or False),
                            'location_id': location_id,
                            'location_dest_id': dest_id,
                            'company_id': pick_in.company_id.id,
                        })
                        lines_data.append(data)
                    #pick_in_uid = pick_in.create_uid or
                    #pick_in.company_id.itercompany_uid
                    pick_in_pool.write(cr, uid, pick_in.id,
                                       {'move_lines': lines_data},
                                       ban_update_out=True)
        return True

    def unlink(self, cr, uid, ids, context=None):
        res = super(stock_picking_out, self).unlink(cr, uid, ids,
                                                    context=context)
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]

        pick_in_pool = self.pool.get('stock.picking.in')
        for pick_out_id in ids:
            pick_in_ids = pick_in_pool.search(
                cr, uid, [('picking_ic_id', '=', pick_out_id)],
                context=context)
            if pick_in_ids:
                pick_in_pool.unlink(cr, uid, pick_in_ids, context=context)
        return res

    #this function is same as stock.picking,
    #when modify that, copy and replace this
    def prepare_intercompany_picking_in_data(
            self, cr, uid, pick_out, company_to, ic_uid, context=None):
        """
        prepare the picking.out data
        @pick_out  browse record of stock.picking, type == in
        @company_to  the company_id of this picking.out record
        """

        context = context or {}
        # context for to create stock.move, count the location
        context.update({'picking_type': 'in'})
        part_pool = self.pool.get('res.partner')
        supplier_id = pick_out.company_id.partner_id.id
        supplier = part_pool.browse(cr, ic_uid, supplier_id)

        location_id = (supplier.property_stock_supplier
                       and supplier.property_stock_supplier.id
                       or False)
        location_dest_id = False
        cr.execute("""
        SELECT
            id
        FROM
            stock_location
        WHERE company_id=%s
            AND name='Stock'
        """, (company_to,))
        location = cr.fetchone()
        if location and location[0]:
            location_dest_id = location[0]

        if (not location_dest_id or not location_id):
            raise osv.except_osv(
                _('Error!'),
                _('''prepare_intercompany_picking_in_data
                    location%s location_dest%s'''
                    % (location_id, location_dest_id)))

        move_lines_data = [(5,)]
        for move_line in pick_out.move_lines:
            line_data = {
                #'picking_id': ic_id,
                'name': move_line.name,
                'product_qty': move_line.product_qty,
                'product_id': move_line.product_id.id,
                'product_uom': move_line.product_uom.id,
                'price_unit': move_line.price_unit,
                'price_currency_id': (move_line.price_currency_id
                                      and move_line.price_currency_id.id
                                      or False),
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'company_id': company_to,
            }
            move_lines_data.append((0, 0, line_data))

        picking_data = {
            'partner_id': supplier.id,
            'picking_ic_id': pick_out.id,
            'is_locked': True,
            'ic_create': True,
            'company_id': company_to,
            'type': 'in',
            'origin': 'IC:' + pick_out.name,
            'move_lines': move_lines_data,
            'magento_bind_ids': False,
            'related_backorder_ids': False,
        }
        return picking_data

stock_picking_out()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
