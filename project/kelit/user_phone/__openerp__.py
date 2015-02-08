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
    'name': 'Users Phone',
    'version': '1.0',
    'author': 'FLK International Ltd',
    'website': 'http://www.flkintl.com',
    'summary': '',
    'description' : """
         This module adds a phone field on the user object
    """,
    'depends': ['base',],
    'category': '',
    'sequence': 10,
    'demo': [],
    'data': [
        'res_users_view.xml',
        ],
    'test': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'css': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: