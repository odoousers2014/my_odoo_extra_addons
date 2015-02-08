# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 FLK International Ltd All Rights Reserved.
#    Author: Damiano Falsanisi <d.falsanisi@flkintl.com>
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
    'name': 'Quick Scrap',
    'version': '1.0',
    'category': 'Stock',
    'sequence': 19,
    'summary': 'Quick Scrap',
    'description': """
Quick Scrap
==================================================
Create a stock picking for scrapped products
    """,
    'author': 'FLK International',
    'website': 'http://www.flkintl.com',
    'images' : [],
    'depends': ['stock'],
    'data': [
        'stock_view.xml',
    ],
    'test': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
