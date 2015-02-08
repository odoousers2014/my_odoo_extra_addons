# -*- coding: utf-8 -*-
##############################################################################
#

from openerp.osv import osv, fields


class res_intercompany(osv.osv):
    _name = "res.intercompany"
    _description = "Inter-Company"

    def _check_intercompany_user(self, cr, uid, ids, context=None):
        for ic in self.browse(cr, uid, ids, context=context):
            if not ic.intercompany_uid:
                return False
        return True

    _columns = {
        'company_from': fields.many2one('res.company', 'Company From',
                                        required=True, ondelete='cascade'),
        'company_to': fields.many2one('res.company', 'Company', required=True,
                                      ondelete='cascade'),
        'o2o': fields.selection(
            [('so2po', 'SO to PO'),
             ('po2so', 'PO to SO'),
             ('is2do', 'IS to DO'),
             ('do2is', 'DO to IS'),
             ('ci2si', 'CI to SI'),
             ('si2ci', 'SI to CI')],
            string="Relation", required=True),
                
        'status': fields.selection(
            [('draft', 'On Creation'),
             ('confirm', 'On Confirmation'),
             ('cancel', 'On Cancel'),
             ('unlink', 'On Deletion')],
            string='Status', required=True),

        'sync_cancel': fields.boolean('Sync Cancel'),
        'sync_confirm': fields.boolean('Sync Confirm'),
                
        'modify_mode': fields.selection(
            [('bidirectional', 'Bidirectional'),
             ('regular', 'Regular'),
             ('inverse', 'Inverse')],
            'Modification Direction', required=True),
        'auto_confirm': fields.boolean('Automatic Confirm'),
        'intercompany_uid': fields.related(
            'company_to', 'intercompany_uid', type='many2one',
            relation='res.users', readonly=True, string='IC User'),
    }
    _defaults = {
        'auto_confirm': lambda *a: True,
        'modify_mode': lambda *a: 'bidirectional',
        'sync_cancel': lambda *a: False,
        'sync_confirm': lambda *a: False,
    }

    _constraints = [
        (_check_intercompany_user, 'Please set IC user for the Company first',
            ['intercompany_uid'])
    ]
    def get_intercompany(self, cr, uid, company_from, company_to, o2o, context=None):
        """
        """
        
        domain = [('company_from','=',company_from),
                  ('company_to','=',company_to),
                   ('o2o','=',o2o)]
        
        
        res = self.search(cr, uid, domain )
        assert len(res) <= 1, 'Search repeat records,Pleas check'
        
        print 'get_intercompany domain',domain, res
        return res and res[0] or False






    def check_need_create_intercompany_object(
            self, cr, uid, company_from, company_to, o2o_field_name,
            node=None, return_list_type=False):
        """ @company_from
            @company_to
            @o2o_field_name  file name.Example, so2po po2so ,,,,
            @node  value of  o2o_field_name ,  draft, confirm
            @return_list_type,  the return type is list or boolean
        """
        intercompany_ids = self.search(
            cr, uid,
            [('company_from', '=', company_from),
             ('company_to', '=', company_to),
             (o2o_field_name, '=', node)])
        if return_list_type:
            return intercompany_ids
        else:
            return intercompany_ids and True or False

    def get_modify_model(self, cr, uid, company_from,
                         company_to, o2o_field_name, ):
        """
        according the company_from company_to and
        o2o_field_name get the modify model
        """
        ids = self.search(cr, uid,
                          [('company_from', '=', company_from),
                           ('company_to', '=', company_to),
                           (o2o_field_name, '!=', False)])
        if ids:
            ic = self.browse(cr, uid, ids[0])
            return ic.modify_mode
        else:
            return None

    def check_need_automatic_confirm(
            self, cr, uid, company_from, company_to,
            o2o_field_name, node=None, return_list_type=False):
        """
        check is need to automatic confirm internal company object
        """
        intercompany_ids = self.search(
            cr, uid,
            [('company_from', '=', company_from),
             ('company_to', '=', company_to),
             (o2o_field_name, '=', node),
             ('auto_confirm', '=', True)])
        return intercompany_ids and True or False

    def _check_intercompany_loops(self, cr, uid, ids, context=None):
        for ic in self.browse(cr, uid, ids, context=context):
            if ic.so2po:
                cr.execute("SELECT po2so FROM res_intercompany\
                            WHERE company_to=%s\
                            AND company_from=%s",
                           (ic.company_from.id, ic.company_to.id))
                if cr.fetchone():
                    return False
            if ic.po2so:
                cr.execute("SELECT so2po FROM res_intercompany\
                            WHERE company_to=%s AND company_from=%s",
                           (ic.company_from.id, ic.company_to.id))
                if cr.fetchone():
                    return False
            if ic.is2do:
                cr.execute("SELECT do2is FROM res_intercompany\
                            WHERE company_to=%s AND company_from=%s",
                           (ic.company_from.id, ic.company_to.id))
                if cr.fetchone():
                    return False
            if ic.do2is:
                cr.execute("SELECT is2do FROM res_intercompany WHERE\
                            company_to=%s AND company_from=%s",
                           (ic.company_from.id, ic.company_to.id))
                if cr.fetchone():
                    return False
            if ic.ci2si:
                cr.execute("SELECT si2ci FROM res_intercompany\
                            WHERE company_to=%s AND company_from=%s",
                           (ic.company_from.id, ic.company_to.id))
                if cr.fetchone():
                    return False
            if ic.si2ci:
                cr.execute("SELECT ci2si FROM res_intercompany\
                            WHERE company_to=%s AND company_from=%s",
                           (ic.company_from.id, ic.company_to.id))
                if cr.fetchone():
                    return False
        return True

    #TODO: unique change, same for company_form and  company_to,
    # only one record of  'po2so' is not null.
    _sql_constraints = [
        ('res_intercompany_uniq', 'unique(company_from, company_to, so2po)',
         'You can only have one line for the same company !')
    ]

res_intercompany()


class res_company(osv.osv):
    _inherit = "res.company"
    _name = "res.company"

    _columns = {
        'res_ic_ids': fields.one2many(
            'res.intercompany', 'company_from', 'Inter-Company Setup'),

        'intercompany_uid': fields.many2one(
            'res.users', 'IC User',
            required=True,
            domain="[('company_id', '=',id)]",
            help="User to create update unlink IC records"),
    }

res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
