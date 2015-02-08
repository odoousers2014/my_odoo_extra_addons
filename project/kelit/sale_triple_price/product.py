# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Yannick Gouin <yannick.gouin@elico-corp.com>, LIN Yu <lin.yu@elico-corp.com>
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

from openerp.tools import ustr
from openerp.osv import osv, fields
from openerp.tools.translate import _
import re

#Add 2 extra prices in product + modify Retail price string in Restaurant price
class product_template(osv.osv):
    _inherit = 'product.template'
    
    _columns = {

        'list_price': fields.property(
            None,  
            type='float',
            view_load=True,
            method=True,
            string='Restaurant Price'
        ),
        'shop_price': fields.property(
            None,  
            type='float',
            view_load=True,
            method=True,
            string='Shop Price'
        ),
        'distrib_price': fields.property(
            None,  
            type='float',
            view_load=True,
            method=True,
            string='Distributor Price'
        ),
    
    }

product_template()

#make price type multicompany field
class price_type(osv.osv):
    _inherit = 'product.price.type'
    
    _columns = {
        'company_id': fields.many2one('res.company', 'Company'),
    }

price_type()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
