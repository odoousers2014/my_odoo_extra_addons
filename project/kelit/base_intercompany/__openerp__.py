# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Yannick Gouin <yannick.gouin@elico-corp.com>
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
    'name': 'Base Inter-company',
    'version': '1.0',
    'category': 'Tools',
    'complexity': "easy",
    'description': """
This module allows you to configure your companies in order to automatically create the Sales Order/Purchase Order, Incoming Shipments/Delivery Orders, and Customer/Supplier Invoices from one company to another.
""",
    'author': 'Elico Corp',
    'website': 'http://www.elico-corp.com',
    'images': [],
    'depends': ['sale_stock','purchase','account_cancel'],
    'init_xml': [],
    'update_xml': [
        'company_view.xml',
        'orders_view.xml',
        'stock_view.xml',
        'invoice_view.xml',
    ],
    'data':[
        'security/intercompany_security.xml',
        'security/ir.model.access.csv',
    ],
    'demo_xml': [], 
    'test': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'active': True,
    'certificate': '',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: