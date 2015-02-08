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
    'name': 'Kelit Stock',
    'version': '1.0',
    'author': 'Elico Corp',
    'website': 'http://www.elico-corp.com',
    'summary': 'Kelit Stock',
    'description' : """
    Kelit Stock Module. Customize Movelist view.
    """,
    'depends': ['base','stock','sale','sale_stock', 'sale_multi_shop', 'kelit_fields'],
    'category': '',
    'sequence': 10,
    'demo': [],
    'data': [
        'ir_rule.xml',        
        'stock_view.xml',
        'wizard/stock_fill_inventory_view.xml',
        'wizard/stock_change_product_qty_vim.xml',
        ],
    'test': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'css': ['static/src/css/tree_view_groupby.css',],
    #'js':['static/src/js/view_list_groupby.js',],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: