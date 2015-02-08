# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Damiano Falsanisi <damiano.falsanisi@elico-corp.com>, Jon Chow <jon.chow@elico-corp.com>
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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'is_company': fields.boolean('Is a Company', help="Check if the contact is a company, otherwise it is a person"),
        'ref': fields.char('Reference', size=2, select=1, required=False),
        #JON    only  fields string Salesperson-->Salesman    Sales Team--> Office
        'user_id': fields.many2one('res.users', 'Salesman', help='The internal user that is in charge of communicating with this contact if any.'),
        #'section_id': fields.many2one('crm.case.section', 'Office'),
        'categ_id': fields.many2one('res.partner.category', 'Tag', required=True),
        
        #address field  required
        'street': fields.char('Street', size=128, required=True),
        'street2': fields.char('Street2', size=128, required=True),
        'city': fields.char('City', size=128, required=True),
        'state_id': fields.many2one("res.country.state", 'State', required=True),
        'country_id': fields.many2one('res.country', 'Country', required=True),  
        'mobile': fields.char('Mobile', size=64, required=True),
    }
    
    #JON    Set default partner IS COMPANY
    _defaults = {
        #'is_company': True,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: