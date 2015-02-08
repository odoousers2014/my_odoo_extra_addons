# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Camptocamp 2012
#    Author : Joel Grand-Guillaume
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
{
    "name" : "Consignment",
    "version" : "1.0",
    "category": 'Sale',
    "depends" : ["stock","sale","sale_stock"],
    "author" : 'FLK International',
    "description": """
    This module is a generic porting of module Specific_fct developed by Joel Grand-Guillaume, Camptocamp
     * Add the possibility to chose the location used as counter-part in inventory to manage 
       consignation (if not set, use the default one: inventory loss)
     * Add a new type of SO : Sales or Consignment + a new location field on partner, depending on
       the choice made, the destination location in the related picking will be customer or
       Consignment one (according to partner setup). 
     
    """,
    'website': 'http://www.flkintl.com',
    'init_xml': [],
    'update_xml': [
       'stock_view.xml',
       'partner_view.xml',
       'sale_view.xml',
        ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate' : '',

}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
