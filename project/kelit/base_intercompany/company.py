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
from openerp.tools.translate import _


class res_intercompany(osv.osv):
    _name = "res.intercompany"
    _description = "Inter-Company"

    _columns = {
        'company_from': fields.many2one('res.company', 'Company From', required=True, ondelete='cascade'),
        'company_to':   fields.many2one('res.company', 'Company', required=True, ondelete='cascade'),
        'so2po':        fields.selection([('draft','On Creation'),('confirm','On Confirmation')], string='SO creates PO', help='TODO'),
        'po2so':        fields.selection([('draft','On Creation'),('confirm','On Confirmation')], string='PO creates SO', help='TODO'),
        'is2do':        fields.selection([('draft','On Creation'),('confirm','On Confirmation')], string='Incoming Shipment creates Delivery Order', help='TODO'),
        'do2is':        fields.selection([('draft','On Creation'),('confirm','On Confirmation')], string='Delivery Order creates Incoming Shipment', help='TODO'),
        'ci2si':        fields.selection([('draft','On Creation'),('confirm','On Confirmation')], string='Customer Invoice creates Supplier Invoice', help='TODO'),
        'si2ci':        fields.selection([('draft','On Creation'),('confirm','On Confirmation')], string='Supplier Invoice creates Customer Invoice', help='TODO'),
    }
    
    def _check_intercompany_loops(self, cr, uid, ids, context=None):
        for ic in self.browse(cr, uid, ids, context=context):
            if ic.so2po:
                cr.execute("SELECT po2so FROM res_intercompany WHERE company_to=%s AND company_from=%s",(ic.company_from.id,ic.company_to.id,))
                if cr.fetchone():
                    return False
            if ic.po2so:
                cr.execute("SELECT so2po FROM res_intercompany WHERE company_to=%s AND company_from=%s",(ic.company_from.id,ic.company_to.id,))
                if cr.fetchone():
                    return False
            if ic.is2do:
                cr.execute("SELECT do2is FROM res_intercompany WHERE company_to=%s AND company_from=%s",(ic.company_from.id,ic.company_to.id,))
                if cr.fetchone():
                    return False
            if ic.do2is:
                cr.execute("SELECT is2do FROM res_intercompany WHERE company_to=%s AND company_from=%s",(ic.company_from.id,ic.company_to.id,))
                if cr.fetchone():
                    return False
            if ic.ci2si:
                cr.execute("SELECT si2ci FROM res_intercompany WHERE company_to=%s AND company_from=%s",(ic.company_from.id,ic.company_to.id,))
                if cr.fetchone():
                    return False
            if ic.si2ci:
                cr.execute("SELECT ci2si FROM res_intercompany WHERE company_to=%s AND company_from=%s",(ic.company_from.id,ic.company_to.id,))
                if cr.fetchone():
                    return False
        return True

#    _constraints = [
#        (_check_intercompany_loops, '/!\ You have a loop in your intercompany setup.\nEg: PO in Company A creates SO in Company B, which creates PO in Company A, ....', ['company_from','company_to','so2po','po2so','is2do','do2is','ci2si','si2ci']),
#    ]
    _sql_constraints = [
        ('res_intercompany_uniq', 'unique(company_from, company_to)', 'You can only have one line for the same company !')
    ]
res_intercompany()



class res_company(osv.osv):
    _inherit = "res.company"
    _name    = "res.company"

    _columns = {
        'intercompany': fields.one2many('res.intercompany', 'company_from', 'Inter-Company Setup'),
    }
res_company()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: