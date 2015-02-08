# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc


class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'
    _name = 'purchase.order.line'
    _columns = {
        'ic_sol_id': fields.many2one('sale.order.line', 'IC SOL'),
    }

    def write(self, cr, uid, ids, values, context=None):
        """
        When change qty of intercompany PO Line,
            update the relation SO Line qty too.
        """

        res = super(purchase_order_line, self).write(
            cr, uid, ids, values, context=context)
        sol_obj = self.pool.get('sale.order.line')
        qty = values.get('product_qty', False)

        if type(ids) != list:
            ids = [ids]

        if qty and res:
            for data in self.read(cr, uid, ids,
                                  ['ic_sol_id'], load='_classic_write'):
                if data['ic_sol_id']:
                    sol_obj.write(cr, uid,
                                  data['ic_sol_id'], {'product_uom_qty': qty})
        return res
    #TODO: when cancel it ,  when unlink it
    #def unlink(self, cr, uid, ids, context=None):
    #def action_cancel()
purchase_order_line()


class purchase_order(osv.osv):
    _inherit = 'purchase.order'
    _name = 'purchase.order'
    _columns = {
        'is_locked': fields.boolean('Locked for Intercompany'),
        'ic_create': fields.boolean('Intercompany PO generated'),
        'sale_id': fields.many2one('sale.order', 'Sales Order'),
    }

    def get_intercompany(self, cr, uid, id, context=None):
        """
        get company from and to
        """

        assert not isinstance(id, list)
        #type(id) != type([])
        cr.execute("""
            SELECT
                po.company_id AS from_c, cmp.id AS to_c, cmp.intercompany_uid
            FROM
                purchase_order AS po
                LEFT JOIN res_partner AS part ON (po.partner_id=part.id)
                LEFT JOIN res_company AS cmp  ON (part.id=cmp.partner_id)
            WHERE
                po.id=%s """, (id,))
        return cr.fetchone()

    def action_draft(self, cr, uid, ids, context=None):
        """
        function of wkf active draft,
        intercompany action operate by Administrator
        SUPERUSER_ID used to search, browse kinds of object.
        but not used of create, write anything
        """

        assert len(ids) == 1
        self.create_intercompany_so(cr, SUPERUSER_ID, ids,
                                    node='draft', context=None)
        return True

    def create_intercompany_so(self, cr, uid, ids, node='draft', context=None):
        """
        1: check_create_intercompany_so
        2: create_intercompany_so
        @node 'draft' or 'confirm'  res.intercompany.po2so value,
        which node of work flow to create so,
        """

        intercompnay_pool = self.pool.get('res.intercompany')
        po = self.browse(cr, uid, ids[0])
        company_from, company_to, ic_uid = self.get_intercompany(cr, uid,
                                                                 ids[0])
        if company_to:
            if intercompnay_pool.check_need_create_intercompany_object(
                    cr, uid, company_from, company_to, "po2so", node):

                if not ic_uid:
                    raise osv.except_osv(_('Error!'),
                                         _('Not found Internal Company User'))
                self._create_intercompany_so(
                    cr, uid, po, company_to, ic_uid, context=context)
            return True
        return True

    def _prepare_IC_so(self, cr, uid, purchase_order,
                       company_to, ic_uid, context=None):
        """
        according the PO and company_to, prepare the SO data,
        It can be used to create or update SO record.
        @purchase_order  SO browse record
        @company_to      company_id
        @ic_uid
        return { }, value of SO data
        """

        part_pool = self.pool.get('res.partner')
        customer_id = purchase_order.company_id.partner_id.id
        customer = part_pool.browse(cr, ic_uid, customer_id)

        addr = part_pool.address_get(cr, uid, [customer_id],
                                     ['delivery', 'invoice', 'contact'])
        pricelist = (customer.property_product_pricelist
                     and customer.property_product_pricelist.id) or False
        payment_term = (customer.property_payment_term
                        and customer.property_payment_term.id) or False
        fiscal_position = (customer.property_account_position
                           and customer.property_account_position.id) or False
        salesman = customer.user_id and customer.user_id.id or ic_uid

        shop_ids = self.pool.get('sale.shop').search(
            cr, ic_uid, [('company_id', '=', company_to)], context=context)
        if not shop_ids:
            raise osv.except_osv(
                _('Error!'),
                _('There is no default shop for the destination company!'))

        sol_datas = [(5,)]
        for po_line in purchase_order.order_line:
            line_data = (0, 0, {
                #'order_id':       so_id,
                'name': po_line.name,
                'ic_pol_id': po_line.id,
                'product_uom_qty': po_line.product_qty,
                'product_id': po_line.product_id.id,
                'product_uom': po_line.product_uom.id,
                'price_unit': po_line.price_unit,
            })
            sol_datas.append(line_data)

        so_data = {
            'partner_id': customer.id,
            'pricelist_id': pricelist,
            'partner_invoice_id': addr['invoice'],
            'partner_order_id': addr['contact'],
            'partner_shipping_id': addr['delivery'],
            'payment_term': payment_term,
            'fiscal_position': fiscal_position,
            'user_id': salesman,
            'purchase_id': purchase_order.id,
            'is_locked': True,
            'ic_create': True,
            'shop_id': shop_ids[0],
            'origin': 'IC:' + str(purchase_order.name),
            'order_line': sol_datas,
        }
        return so_data

    def _create_intercompany_so(
            self, cr, uid, purchase_order, company_to, ic_uid, context=None):
        """
        @purchase_order
        @company_to
        @ic_uid, the intercompany obj create user
        """

        so_data = self._prepare_IC_so(
            cr, uid, purchase_order, company_to, ic_uid, context=context)
        return self.pool.get('sale.order').create(cr, ic_uid,
                                                  so_data, context=context)

    def unlink(self, cr, uid, ids, context=None):
        """
        when unlink PO, unlink the relation internal company SO
        """
        so_pool = self.pool.get('sale.order')
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]
        relation_so_info = self.get_IC_so_info(cr, uid, ids)
        res = super(purchase_order, self).unlink(cr, uid, ids,
                                                 context=context)

        def need_unlink(dic, named=None):
            if named == 'father':
                return (dic['father_so']
                        and (dic['father_moidf']
                             in ['inverse', 'bidirectional'])
                        and (dic['father_state']
                             in ['draft', 'cancel']))
            if named == 'son':
                return (dic['son_so']
                        and (dic['son_moidf']
                             in ['regular', 'bidirectional'])
                        and (dic['son_state']
                             in ['draft', 'cancel']))

        if res:
            for po_id in ids:
                dic = relation_so_info[po_id]
                if need_unlink(dic, named='father'):
                    so_pool.unlink(cr, dic['father_ic_uid'], dic['father_so'],
                                   context=context)
                if need_unlink(dic, named='son'):
                    so_pool.unlink(cr, dic['son_ic_uid'], dic['son_so'],
                                   context=context)

        return res

    def write(self, cr, uid, ids, values, context=None,
              ban_update_so=False, ban_inverse_so=False):
        """
        When write PO,  update the relation intercompany SO
        @is_inverse_update, important, avoid PO SO circulation update
        """

        res = super(purchase_order, self).write(cr, uid, ids, values,
                                                context=context)
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]
        if res and not ban_update_so:
            self.update_IC_so(cr, SUPERUSER_ID, ids, context=context)
        if res and not ban_inverse_so:
            self.inverse_IC_so(cr, SUPERUSER_ID, ids, context=context)
        return res

    def update_IC_so(self, cr, uid, ids, context=None):
        """
        according PO update relation intercompany SO
        TODO? If intercompany_so create by confirm,
        is it need to update? when PO is confirm, it is can't  be change.
        """

        sale_pool = self.pool.get('sale.order')
        ic_pool = self.pool.get('res.intercompany')
        for po in self.browse(cr, uid, ids):
            cf, ct, ic_uid = self.get_intercompany(cr, uid, po.id)
            ic_so_ids = sale_pool.search(cr, ic_uid,
                                         [('purchase_id', '=', po.id)],
                                         context=context)
            ic_so_id = ic_so_ids and ic_so_ids[0]
            if ic_so_id:
                modify_mode = ic_pool.get_modify_model(cr, uid, cf,
                                                       ct, 'po2so',)
                if modify_mode in ['regular', 'bidirectional']:
                    data = self._prepare_IC_so(cr, uid, po, ct, ic_uid,
                                               context=None)
                    sale_pool.write(cr, ic_uid, ic_so_id, data,
                                    ban_inverse_po=True)

    def inverse_IC_so(self, cr, uid, ids, context=None):
        """
        if PO is create by intercompany. when update PO,
        at the same time, inverse update relation SO.
        """

        if context is None:
            context = {}
        so_pool = self.pool.get('sale.order')
        ic_pool = self.pool.get('res.intercompany')

        for po in self.browse(cr, uid, ids, context=context):
            so = po.sale_id
            if so:
                cf, ct = so_pool.get_intercompany(cr, uid, so.id)[0:2]
                modify_mode = ic_pool.get_modify_model(cr, uid, cf,
                                                       ct, 'so2po',)
                if modify_mode in ['inverse', 'bidirectional']:
                    solines_data = [(5,)]
                    for po_line in po.order_line:
                        data = (0, 0, {
                            #'order_id': so_id,
                            'name': po_line.name,
                            'ic_pol_id': po_line.id,
                            'product_uom_qty': po_line.product_qty,
                            'product_id': po_line.product_id.id,
                            'product_uom': po_line.product_uom.id,
                            'price_unit': po_line.price_unit,
                        })
                        solines_data.append(data)

                    ic_user = so.company_id.intercompany_uid
                    if not ic_user:
                        raise osv.except_osv(
                            _('Error!'),
                            _('''Pls select IC-user for company %s'''
                              % so.company_id.name))

                    so_pool.write(cr, ic_user.id, so.id,
                                  {'order_line': solines_data},
                                  context=context, ban_update_po=True)
        return True

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        """
        Create intercompany SO when confirm PO
        """

        res = super(purchase_order, self).wkf_confirm_order(
            cr, uid, ids, context=context)
        if res:
            self.create_intercompany_so(cr, SUPERUSER_ID, ids, node='confirm',
                                        context=context)
        return res

    def action_cancel(self, cr, uid, ids, context=None):
        """
        add action_cancel for PO cancel Node.
        when cancel PO, cancel the relation SO too
        """
        assert len(ids) == 1
        wkf_service = netsvc.LocalService("workflow")
        #sale_pool = self.pool.get('sale.order')

        relation_so_info = self.get_IC_so_info(cr, uid, ids)
        print relation_so_info
        res = self.write(cr, uid, ids, {'state': 'cancel'})

        def need_cancel(dic, named=None):
            if named == 'father':
                return (dic['father_so']
                        and (dic['father_moidf']
                             in ['inverse', 'bidirectional'])
                        and (dic['father_state']
                             in ['draft', 'cancel']))
            if named == 'son':
                return (dic['son_so']
                        and (dic['son_moidf']
                             in ['regular', 'bidirectional'])
                        and (dic['son_state']
                             in ['draft', 'cancel']))

        if res:
            for po_id in ids:
                dic = relation_so_info[po_id]
                if need_cancel(dic, named='father'):
                    wkf_service.trg_validate(dic['father_ic_uid'],
                                             'sale.order',
                                             dic['father_so'],
                                             'cancel', cr)
                if need_cancel(dic, named='son'):
                    wkf_service.trg_validate(dic['son_ic_uid'],
                                             'sale.order',
                                             dic['son_so'],
                                             'cancel', cr)

        return True

    def get_IC_so_info(self, cr, uid, ids, context=None):
        """
        """
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]

        ic_pool = self.pool.get('res.intercompany')
        so_pool = self.pool.get('sale.order')
        po_pool = self

        cr.execute("""
        select po.id, po.sale_id, so.id
            from purchase_order as po
            left join sale_order as so on (so.purchase_id = po.id)
        where
            po.id in (%s)
        """, (ids))
        res = {}
        for i in cr.fetchall():
            po_id, father_so, son_so = i
            father_moidf = False
            father_ic_uid = False
            father_state = False
            son_moidf = False
            son_ic_uid = False
            son_state = False
            if father_so:
                f_so = so_pool.browse(cr, SUPERUSER_ID, father_so)
                f_cf, f_ct, f_ic_uid = so_pool.get_intercompany(cr, uid,
                                                                father_so)
                father_moidf = ic_pool.get_modify_model(cr, uid, f_cf,
                                                        f_ct, 'so2po',)
                father_ic_uid = f_so.company_id.intercompany_uid.id
                father_state = f_so.state
            if son_so:
                s_so = so_pool.browse(cr, SUPERUSER_ID, son_so)
                s_cf, s_ct, s_ic_uid = po_pool.get_intercompany(cr, uid, po_id)
                son_moidf = ic_pool.get_modify_model(cr, uid, s_cf,
                                                     s_ct, 'po2so',)
                son_ic_uid = s_ic_uid
                son_state = s_so.state

        res[po_id] = {
            'father_so': father_so,
            'father_moidf': father_moidf,
            'father_ic_uid': father_ic_uid,
            'father_state': father_state,
            'son_so': son_so,
            'son_moidf': son_moidf,
            'son_ic_uid': son_ic_uid,
            'son_state': son_state,
        }

        return res

purchase_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
