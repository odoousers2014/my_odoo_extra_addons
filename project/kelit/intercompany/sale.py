# -*- coding: utf-8 -*-
##############################################################################
#

from openerp import SUPERUSER_ID, netsvc
from openerp.osv import fields, osv
from openerp.tools.translate import _
import logging

wkf_service = netsvc.LocalService("workflow")
_logger = logging.getLogger(__name__)


def what_ic_action(value,ic):
    state = value.get('state', '')
    res = 'None Action'
    if state in ['progress','confirmed'] and ic.status=='confirm':
        res = 'confirm'
    if state == 'cancel' and ic.status=='cancel':
        res = 'cancel'
    _logger.info('>>> what_ic_action %s', res)
    return res

class purchase_order(osv.osv):
    _inherit = 'purchase.order'
    _columns = {
        'is_locked': fields.boolean('Locked for Intercompany'),
        'ic_create': fields.boolean('Intercompany SO generated'),
        'parent_so': fields.many2one('sale.order', 'Parent SO'),
        'child_so': fields.many2one('sale.order', 'Child SO'),
        'ic':fields.many2one('res.intercompany', 'Inter-Company'),
        'from_ic':fields.many2one('res.intercompany', 'From Inter-Company'),
    }
    
    def create(self, cr, uid, value, context=None):
        _logger.info('>>> PO create %s', value)
        if context==None:
            context={}
        
        po_id = super(purchase_order, self).create(cr, uid, value, context=context)
        
        so_pool = self.pool.get('sale.order')
        user_pool = self.pool.get('res.users')
        company_pool = self.pool.get('res.company')
        ic_pool = self.pool.get('res.intercompany')
        
        user = user_pool.browse(cr, SUPERUSER_ID, uid)
        partner_id = value.get('partner_id', False)
         
        company_from = value.get('company_id', False) or user.company_id.id
        company_to = company_pool.search(cr, SUPERUSER_ID, [('partner_id','=',partner_id)])
        company_to = company_to and company_to[0] or False
         
        ic_id = company_to and  ic_pool.get_intercompany(cr, uid, company_from, company_to, 'po2so') or False
        
        if ic_id:
            po = self.browse(cr, uid, po_id)
            ic = ic_pool.browse(cr, uid, ic_id)
            
            context.update({'no_update_child_so':True, 'no_update_parent_so':True})
            
            if ic.status == 'draft':
                so_data = self._prepare_child_so(cr, uid, po,  ic)
                so_id = so_pool.create(cr, ic.intercompany_uid.id, so_data)
                self.write(cr, uid, po_id, {'child_so': so_id, 'ic':ic_id }, context=context)
            else:
                self.write(cr, uid, po_id, {'ic':ic_id }, context=context)
                
        return po_id
    def write(self, cr, uid, ids, value, context=None,):
        """
        When write PO,  update the relation intercompany SO
        @is_inverse_update, important, avoid PO SO circulation update
        """
        _logger.info('>>> PO write %s %s',ids ,context)
        
        if context == None:
            context={}
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]
        res = super(purchase_order, self).write(cr, uid, ids, value, context=context)
        
        for po in self.browse(cr, uid, ids, context=context):
            (child_so, parent_so, ic, from_id) = (po.child_so, po.parent_so, po.ic, po.from_ic)
            if not (ic or from_ic):
                continue
            
            if ic and what_ic_action(value, ic) == 'confirm' and not child_so:
                _logger.info('>>> PO %s write confirm-action %s',po.name ,context)
                so_pool = self.pool.get('sale.order')
                so_data = self._prepare_child_so(cr, uid, po,  ic)
                so_id = so_pool.create(cr, ic.intercompany_uid.id, so_data)
                context.update({'no_update_child_so':True, 'no_update_parent_po':True})
                self.write(cr, uid, po.id, {'child_so': so_id},context=context)
            
            if (child_so
                    and value.get('state','') == 'cancel'
                    and po.ic.sync_cancel == True
                    and child_so.state in ['draft',]  ):
                _logger.info('>>> PO %s write sync_cancel SO %s',po.name ,child_so.name)
                
                #TODO  minimax_admin  can not read other company SO and PO. 
                #wkf_service.trg_validate(ic.intercompany_uid.id, 'sale.order', child_so.id, 'cancel', cr)
                _logger.info('>>> PO %s write sync_cancel SO %s finish',po.name ,child_so.name)
            
            if child_so or parent_so:
                self.update_ic_so(cr, uid, po, context=context)
            
        return res
    def _prepare_child_so(self, cr, uid, po, ic,  context=None):
        """
        according the PO and company_to, prepare the SO data,
        It can be used to create or update SO record.
        @purchase_order  SO browse record
        @company_to      company_id
        @ic_uid
        return { }, value of SO data
        """

        part_pool = self.pool.get('res.partner')
        customer_id = po.company_id.partner_id.id
        customer = part_pool.browse(cr, ic.intercompany_uid.id, customer_id)

        addr = part_pool.address_get(cr, uid, [customer_id],
                                     ['delivery', 'invoice', 'contact'])
        pricelist = (customer.property_product_pricelist
                     and customer.property_product_pricelist.id) or False
        payment_term = (customer.property_payment_term
                        and customer.property_payment_term.id) or False
        fiscal_position = (customer.property_account_position
                           and customer.property_account_position.id) or False
        salesman = customer.user_id and customer.user_id.id or ic.intercompany_uid.id

        shop_ids = self.pool.get('sale.shop').search(
            cr, ic.intercompany_uid.id, [('company_id', '=', ic.company_to.id)], context=context)
        if not shop_ids:
            raise osv.except_osv(
                _('Error!'),
                _('There is no default shop for the destination company!'))

        sol_datas = [(5,)]
        for po_line in po.order_line:
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
            'purchase_id': po.id,
            'is_locked': True,
            'ic_create': True,
            'shop_id': shop_ids[0],
            'origin': 'IC:' + po.name,
            'order_line': sol_datas,
            'from_ic':ic.id,
            'parent_po': po.id,
        }
        
        _logger.info('>>> PO %s _prepare_child_so finish')
        return so_data
    
    
    def update_ic_so(self, cr, uid, po, context=None):
        """
        Update the relation intercompany PO
        """ 
        if context == None:
            context = {}
        no_update_child_so = context.get('no_update_child_so',False)
        no_update_parent_so = context.get('no_update_parent_so',False)
        _logger.info('>>> PO %s update_ic_so no_update_child_so:%s no_update_parent_so:%s Modif_mode:%s',
                      po.name, no_update_child_so, no_update_parent_so,  po.ic.modify_mode)
        if (po.ic.modify_mode in ['bidirectional', 'regular']
                and po.child_so
                and po.child_so.state in ['draft',]  
                and not no_update_child_so):
            context.update({'no_update_parent_po':True})
            self.update_child_so(cr, uid, po, context)

        if (po.from_ic.modify_mode in ['bidirectional', 'inverse']
                and po.parent_so
                and not no_update_parent_so):
            context.update({'no_update_child_po':True})
            self.update_parent_so(cr, uid, po, context)
    def update_child_so(self, cr, uid, po, context=None):
        _logger.info('>>> PO %s update_child_so SO%s', po.name, po.child_so.name)
        
        if context==None:
            context={}
        so_pool = self.pool.get('sale.order')
        data = self._prepare_child_so(cr, uid, po, po.ic, context=None)
        context.update({'no_uodate_parent_po':True})
        so_pool.write(cr, po.ic.intercompany_uid.id, po.child_so.id, data, context=context)
            
    def update_parent_so(self, cr, uid, po, context=None):
        if context == None:
            context={}
        so_pool = self.pool.get('sale.order')

        so = po.parent_so
        solines_data = [(5,)]
        for po_line in po.order_line:
            data = (0, 0, {
                #'order_id': so_id,
                'name': po_line.name,
                #'ic_pol_id': po_line.id,
                'product_uom_qty': po_line.product_qty,
                'product_id': po_line.product_id.id,
                'product_uom': po_line.product_uom.id,
                'price_unit': po_line.price_unit,
            })
            solines_data.append(data)

        so_user = so.create_uid.id
        
        context.update({'no_update_child_po': True})
        _logger.info('>>> PO %s update_parent_so SO %s Context %s',po.name, so.name, context)
        so_pool.write(cr, so_user, so.id, {'order_line': solines_data}, context=context, )
        
        
purchase_order()    


class  sale_order(osv.osv):
    _inherit = 'sale.order'
    _columns = {
        'is_locked': fields.boolean('Locked for Intercompany'),
        'ic_create': fields.boolean('Intercompany SO generated'),
        'parent_po': fields.many2one('purchase.order', 'Parent PO'),
        'child_po': fields.many2one('purchase.order', 'Child PO'),
        'ic':fields.many2one('res.intercompany', 'Inter-Company'),
        'from_ic':fields.many2one('res.intercompany', 'From Inter-Company'),
    }
    
    def create(self, cr, uid, value, context=None):
        _logger.info('>>>into SO create %s', value)
        if context==None:
            context={}
        
        so_id = super(sale_order, self).create(cr, uid, value, context=context)
        
        po_pool = self.pool.get('purchase.order')
        user_pool = self.pool.get('res.users')
        company_pool = self.pool.get('res.company')
        ic_pool = self.pool.get('res.intercompany')
        
        user = user_pool.browse(cr, SUPERUSER_ID, uid)
        partner_id = value.get('partner_id', False)
         
        company_from = user.company_id.id
        company_to = company_pool.search(cr, SUPERUSER_ID, [('partner_id','=',partner_id)])
        company_to = company_to and company_to[0] or False
         
        ic_id = company_to and  ic_pool.get_intercompany(cr, uid, company_from, company_to, 'so2po') or False
        
        if ic_id:
            so = self.browse(cr, uid, so_id)
            ic = ic_pool.browse(cr, uid, ic_id)
            
            context.update({'no_update_child_po':True, 'no_update_parent_po':True})
            
            if ic.status == 'draft':
                po_data = self._prepare_child_po(cr, uid, so,  ic)
                po_id = po_pool.create(cr, ic.intercompany_uid.id, po_data)
                self.write(cr, uid, so_id, {'child_po': po_id, 'ic':ic_id }, context=context)
            else:
                self.write(cr, uid, so_id, {'ic':ic_id }, context=context)
                
        return so_id
    
    def write(self, cr, uid, ids, value, context=None,):
        """
        """
        _logger.info('>>> SO write %s %s',value, context )
        res = super(sale_order, self).write(cr, uid, ids, value,
                                            context=context)
        if isinstance(ids, int) or isinstance(ids, long):
            ids = [ids]
        po_pool = self.pool.get('purchase.order')

        sales = self.browse(cr, uid, ids)
        for so in sales:
            if not (so.ic or so.from_ic):
                continue
            
            if what_ic_action(value, so.ic) == 'confirm' and not so.child_po:
                po_data = self._prepare_child_po(cr, uid, so,  so.ic)
                po_id = po_pool.create(cr, so.ic.intercompany_uid.id, po_data)
                self.write(cr, uid, so.id, {'child_po': po_id}, context=context)

            if what_ic_action(value, so.ic) == 'cancel' and  so.child_po:
                pass
                 
            if so.child_po or so.parent_po:
                self.update_ic_po(cr, uid, so, context=context)
                
        #=======================================================================
        # if res and not ban_update_po:
        #     self.update_IC_po(cr, SUPERUSER_ID, ids, context=context)
        # if res and not ban_inverse_po:
        #     self.inverse_IC_po(cr, SUPERUSER_ID, ids, context=context)
        #=======================================================================
 
        return res
    
    def update_ic_po(self, cr, uid, so, context=None):
        """
        Update the relation intercompany PO
        """ 
        if context == None:
            context = {}
            
        no_update_child_po = context.get('no_update_child_po',False)
        no_update_parent_po = context.get('no_update_parent_po',False)
        
        _logger.info('>>> SO %s update_ic_po %s %s', so.name, no_update_child_po , no_update_parent_po)
        
        if (so.ic.modify_mode in ['bidirectional', 'regular'] 
                and so.child_po
                and not no_update_child_po):
            context.update({'no_update_parent_so':True})
            self.update_child_po(cr, uid, so, context)

        if (so.from_ic.modify_mode in ['bidirectional', 'inverse']
                and so.parent_po
                and not no_update_parent_po):
            
            context.update({'no_update_child_so':True})
            self.update_parent_po(cr, uid, so, context)
            
        _logger.info('>>> SO %s update_ic_po end', so.name,)
            
    def update_child_po(self, cr, uid, so, context=None):
        _logger.info('>>> SO %s update_child_po PO%s', so.name, so.child_po.name)
        
        if context==None:
            context={}
        
        po_pool = self.pool.get('purchase.order')
        data = self._prepare_child_po(cr, uid, so, so.ic, context=None)
        
        context.update({'no_uodate_parent_so':True})
        po_pool.write(cr, so.ic.intercompany_uid.id, so.child_po.id, data, context=context)
        
    def update_parent_po(self, cr, uid, so,  context=None):
        _logger.info('>>>>>>>>>>>>>>>>>>>>>>>>>%s %s',  uid,  so.name)
        _logger.info('>>> SO %s update_parent_po %s', so.name, so.parent_po.name)
        
        if context == None:
            context={}
            
        po_pool = self.pool.get('purchase.order')
        po = so.parent_po
        
        polines_data = [(5,)]
        for line in so.order_line:
            date_planned = self._get_date_planned(cr, uid, so, line, so.date_order, context=context)
            data = (0, 0, {
                'name': line.name,
                'product_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'price_unit': line.price_unit,
                'date_planned': date_planned,
            })
            polines_data.append(data)

        po_user = po.create_uid.id
        
        context.update({'no_update_child_po': True})
        po_pool.write(cr, po_user, po.id, {'order_line': polines_data}, context=context, )
        _logger.info('>>> SO %s update_parent_po %s END', so.name, so.parent_po.name)
            
    def _prepare_child_po(self, cr, uid, so, ic, context=None):
 
        """
        prepare the intercompany PO data,
        it can be used to create or update PO record
        @ sale_order  SO browse record
        @ company_to  company_id
        @ic_uid  Internal company user id
        """
        
        company_to, ic_uid = ic.company_to.id, ic.intercompany_uid.id
 
        supplier = self.pool.get('res.partner').browse(
            cr, ic_uid, so.company_id.partner_id.id)
        pricelist = (supplier.property_product_pricelist_purchase
                     and supplier.property_product_pricelist_purchase.id
                     or False)
        fiscal_position = (supplier.property_account_position
                           and supplier.property_account_position.id
                           or False)
        payment_term = supplier.property_supplier_payment_term.id or False
 
        cr.execute(
            """
                SELECT
                    id
                FROM
                    stock_location
                WHERE
                    company_id=%s AND name='Stock'
            """, (company_to,))
        #TODO: location select should ref the default
        location = cr.fetchone()
        if location and location[0]:
            location_id = location[0]
        else:
            raise osv.except_osv(
                _('Error!'),
                _('prepare_intercompany_po_data,not found location_id'))
 
        polines_data = [(5,)]
        for so_line in so.order_line:
 
            date_planned = self._get_date_planned(
                cr, uid, so, so_line,
                so.date_order, context=context)
 
            pol_data = (0, 0, {
                'ic_sol_id': so_line.id,
                'name': so_line.name,
                'product_qty': so_line.product_uom_qty,
                'product_id': so_line.product_id.id,
                'product_uom': so_line.product_uom.id,
                'price_unit': so_line.price_unit,
                'date_planned': date_planned,
            })
            polines_data.append(pol_data)
 
        po_data = {
            'partner_id': supplier.id,
            'pricelist_id': pricelist,
            'payment_term_id': payment_term,
            'fiscal_position': fiscal_position,
            'sale_id': so.id,
            'is_locked': True,
            'ic_create': True,
            'company_id': company_to,
            'location_id': location_id,
            'origin': 'IC:' + str(so.name),
            'order_line': polines_data,
            'from_ic': ic.id,
            'parent_so': so.id,
        }
        return po_data
    
    
sale_order()


    
    
    


#===============================================================================
#     def get_intercompany(self, cr, uid, id, context=None):
#         """
#         get company from and to
#         """
# 
#         assert isinstance(id, int) or isinstance(id, long)
#         cr.execute("""
#             SELECT
#                 so.company_id AS from_c, cmp.id AS to_c, cmp.intercompany_uid
#             FROM sale_order AS so
#                 LEFT JOIN res_partner AS part ON (so.partner_id = part.id)
#                 LEFT JOIN res_company AS cmp  ON (part.id = cmp.partner_id)
#             WHERE so.id = %s
#             """, (id,))
#         return cr.fetchone()
# 
#     def action_draft(self, cr, uid, ids, context=None):
#         """
#         SO wkf Draft action,
#         Use Administrator operate intercompany action
#         """
# 
#         assert len(ids) == 1
#         self.create_intercompany_po(cr, SUPERUSER_ID, ids, context=None)
#         return True
# 
#     def create_intercompany_po(self, cr, uid, ids, node='draft', context=None):
#         """
#         1: check_create_intercompany_po
#         2: if 1 return true, create_intercompany_po
#         TODO: action draft or confirm is the same code, want to merge it,
#               only need different argument 'draft or confirm'
#         @node  'draft' or 'confirm'  res.intercompany.so2po value
#         TODO: "if need" should move to  'action_draft'
#         """
# 
#         intercompany_pool = self.pool.get('res.intercompany')
#         sale_order = self.browse(cr, uid, ids[0])
#         company_from, company_to, ic_uid = self.get_intercompany(
#             cr, uid, ids[0], context=context)
#         if not company_to:
#             return True
# 
#         if intercompany_pool.check_need_create_intercompany_object(
#                 cr, uid, company_from, company_to, "so2po", node):
#             self._create_intercompany_po(cr, uid, sale_order,
#                                          company_to, ic_uid, context=None)
#         return True
# 
#     def _create_intercompany_po(self, cr, uid, sale_order,
#                                 company_to, ic_uid, context=None):
# 
#         po_data = self._prepare_child_po(
#             cr, uid, sale_order, company_to, ic_uid, context=context)
#         return self.pool.get('purchase.order').create(cr, ic_uid, po_data)
# 



 



#     def unlink(self, cr, uid, ids, context=None):
#         """
#         when unlink SO, unlink the relation internal company PO
#         """
#         po_pool = self.pool.get('purchase.order')
#         if isinstance(ids, int) or isinstance(ids, long):
#             ids = [ids]
# 
#         relation_po_info = self.get_IC_po_info(cr, uid, ids)
#         res = super(sale_order, self).unlink(cr, uid, ids, context=context)
#         if res:
#             for so_id in ids:
#                 dic = relation_po_info[so_id]
#                 if (dic['father_po']
#                         and (dic['father_moidf']
#                              in ['inverse', 'bidirectional'])
#                         and (dic['father_state']
#                              in ['draft', 'cancel'])):
#                     po_pool.unlink(self, cr, dic['father_ic_uid'],
#                                    dic['father_po'])
# 
#                 if (dic['son_po']
#                         and (dic['son_moidf']
#                              in ['regular', 'bidirectional'])
#                         and (dic['son_state']
#                              in ['draft', 'cancel'])):
#                     po_pool.unlink(self, cr, dic['son_ic_uid'], dic['son_po'])
# 
#         return res
# 
#     def get_IC_po_info(self, cr, uid, ids, context=None):
#         """
#         @so_id
#         return {'father':po_id, 'son':po_id}
#             father, so_id creat by po_id
#             son, so_id crate the po_id
#         """
#         ic_pool = self.pool.get('res.intercompany')
#         po_pool = self.pool.get('purchase.order')
#         so_pool = self
# 
#         cr.execute("""
#         select so.id, so.purchase_id, po.id
#             from sale_order as so
#             left join purchase_order as po on (po.sale_id = so.id)
#         where
#             so.id in (%s)
#         """, (ids))
#         res = {}
#         for i in cr.fetchall():
#             so_id, father_po, son_po = i
#             father_moidf = False
#             father_ic_uid = False
#             father_state = False
#             son_moidf = False
#             son_ic_uid = False
#             son_state = False
#             #TODO for avoid the access error,
#             #want to cancel all the orm menthond, use SQL get info
#             if father_po:
#                 f_po = po_pool.browse(cr, SUPERUSER_ID, father_po)
#                 f_cf, f_ct, f_ic_uid = po_pool.get_intercompany(cr, uid,
#                                                                 father_po)
#                 father_moidf = ic_pool.get_modify_model(cr, uid, f_cf,
#                                                         f_ct, 'po2so',)
#                 father_ic_uid = f_po.company_id.intercompany_uid.id
#                 father_state = f_po.state
#             if son_po:
#                 s_po = po_pool.browse(cr, SUPERUSER_ID, son_po)
#                 s_cf, s_ct, s_ic_uid = so_pool.get_intercompany(cr, uid, so_id)
#                 son_moidf = ic_pool.get_modify_model(cr, uid, s_cf,
#                                                      s_ct, 'so2po',)
#                 son_ic_uid = s_ic_uid
#                 son_state = s_po.state
# 
#             res[so_id] = {
#                 'father_po': father_po,
#                 'father_moidf': father_moidf,
#                 'father_ic_uid': father_ic_uid,
#                 'father_state': father_state,
#                 'son_po': son_po,
#                 'son_moidf': son_moidf,
#                 'son_ic_uid': son_ic_uid,
#                 'son_state': son_state,
#             }
#         return res
# 
#     def write(self, cr, uid, ids, values, context=None,
#               ban_update_po=False, ban_inverse_po=False):
#         """
#         is_inverse_update : avoid PO SO circulation update
#         """
#         res = super(sale_order, self).write(cr, uid, ids, values,
#                                             context=context)
#         if isinstance(ids, int) or isinstance(ids, long):
#             ids = [ids]
# 
#         if res and not ban_update_po:
#             self.update_IC_po(cr, SUPERUSER_ID, ids, context=context)
#         if res and not ban_inverse_po:
#             self.inverse_IC_po(cr, SUPERUSER_ID, ids, context=context)
# 
#         return res
# 
#     def update_IC_po(self, cr, uid, ids, context=None):
#         """
#         Update the relation intercompany PO
#         """
# 
#         purchase_pool = self.pool.get('purchase.order')
#         ic_pool = self.pool.get('res.intercompany')
# 
#         for so in self.browse(cr, uid, ids):
#             cf, ct, ic_uid = self.get_intercompany(cr, uid, so.id)
#             ic_po_ids = purchase_pool.search(cr, SUPERUSER_ID,
#                                              [('sale_id', '=', so.id)],
#                                              context=context)
#             ic_po_id = ic_po_ids and ic_po_ids[0]
#             if ic_po_id:
#                 modify = ic_pool.get_modify_model(cr, uid, cf, ct, 'so2po',)
#                 if modify in ['regular', 'bidirectional']:
#                     data = self._prepare_child_po(cr, uid, so, ct,
#                                                ic_uid, context=None)
#                     purchase_pool.write(cr, ic_uid, ic_po_id, data,
#                                         ban_inverse_so=True)
# 
#     def inverse_IC_po(self, cr, uid, ids, context=None):
#         """
#         when update SO,inverse update relation PO.
#         #TODO: do not forget to update sol.ic_pol_id should update too.
#         """
#         if context is None:
#             context = {}
# 
#         po_pool = self.pool.get('purchase.order')
#         ic_pool = self.pool.get('res.intercompany')
# 
#         for so in self.browse(cr, uid, ids, context=context):
#             po = so.purchase_id
#             if po:
#                 cf, ct = po_pool.get_intercompany(cr, uid, po.id)[0:2]
#                 modify = ic_pool.get_modify_model(cr, uid, cf, ct, 'po2so')
#                 if modify in ['inverse', 'bidirectional']:
# 
#                     polines_data = [(5,)]
#                     for so_line in so.order_line:
#                         date_planned = self._get_date_planned(
#                             cr, uid, so, so_line, so.date_order,
#                             context=context)
#                         pol_data = (0, 0, {
#                             'name': so_line.name,
#                             'product_qty': so_line.product_uom_qty,
#                             'product_id': so_line.product_id.id,
#                             'product_uom': so_line.product_uom.id,
#                             'price_unit': so_line.price_unit,
#                             'date_planned': date_planned,
#                         })
#                         polines_data.append(pol_data)
# 
#                     ic_user = po.company_id.intercompany_uid
#                     if not ic_user:
#                         raise osv.except_osv(
#                             _('Error!'),
#                             _('''Pls select IC-user for company %s'''
#                               % po.company_id.name))
#                     po_pool.write(cr, ic_user.id, po.id,
#                                   {'order_line': polines_data},
#                                   context=context, ban_update_so=True)
# 
#         return True
# 
#     def action_wait(self, cr, uid, ids, context=None):
#         """
#         create intercompany PO by confirm SO,
#         SO confirm button trigger action_wait.
#         so action_confirm_intercompany insert at here.
#         """
# 
#         result = super(sale_order, self).action_wait(cr, uid, ids,
#                                                      context=context)
#         if result:
#             self.create_intercompany_po(cr, uid, ids, node='confirm',
#                                         context=context)
#         return result
# 
#     def action_cancel(self, cr, uid, ids, context=None):
#         """
#         when cancel SO, cancel the relation PO too
#         """
#         wkf_service = netsvc.LocalService("workflow")
# 
#         relation_po_info = self.get_IC_po_info(cr, uid, ids)
#         res = super(sale_order, self).action_cancel(cr, uid, ids,
#                                                     context=context)
#         if res:
#             for so_id in ids:
#                 dic = relation_po_info[so_id]
#                 print '>>>>', dic
#                 if (dic['father_po']
#                         and (dic['father_moidf']
#                              in ['inverse', 'bidirectional'])
#                         and (dic['father_state']
#                              in ['draft', 'cancel'])):
#                     #print 'cancel', dic['father_po']
#                     wkf_service.trg_validate(dic['father_ic_uid'],
#                                              'purchase.order',
#                                              dic['father_po'],
#                                              'purchase_cancel', cr)
#                 if (dic['son_po']
#                         and (dic['son_moidf']
#                              in ['regular', 'bidirectional'])
#                         and (dic['son_state']
#                              in ['draft', 'cancel'])):
#                     #print 'cancel', dic['son_ic_uid']
#                     wkf_service.trg_validate(dic['son_ic_uid'],
#                                              'purchase.order',
#                                              dic['son_po'],
#                                              'purchase_cancel', cr)
#         return res
# 
# sale_order()
# 
# 
# class sale_order_line(osv.osv):
#     _inherit = 'sale.order.line'
#     _name = 'sale.order.line'
#     _columns = {
#         'ic_pol_id': fields.many2one('purchase.order.line',
#                                      'Intercompany PO Line'),
#     }
# 
#     #TODO,  this write function should to change
#     # fix the security rule of internal company
#     def write__(self, cr, uid, ids, values, context=None):
#         """
#         When change qty of intercompany SO Line,
#         update the relation PO Line qty.
#         """
#         res = super(sale_order_line, self).write(cr, uid, ids, values,
#                                                  context=context)
#         pol_obj = self.pool.get('purchase.order.line')
#         qty = values.get('product_uom_qty', False)
# 
#         if type(ids) != list:
#             ids = [ids]
# 
#         if res and qty:
#             for data in self.read(cr, uid, ids, ['ic_pol_id'],
#                                   load='_classic_write'):
#                 if data['ic_pol_id']:
#                     pol_obj.write(cr, uid, data['ic_pol_id'],
#                                   {'product_qty': qty})
#         return res
#     #TODO: when cancel it ,  when unlink it
#     #def unlink(self, cr, uid, ids, context=None):
#     #def action_cancel()
# 
# sale_order_line()
#===============================================================================

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
