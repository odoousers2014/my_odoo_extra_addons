# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'NoSpace FiedChar',
    'version': '1.0',
    'author': 'Jon Chow<alangwansui@mail.com>',
    'category': 'Hidden',
    'description': """
        Some very critical char.filds auto deleted all space word for user input.

        Example:
            <field name='code' class='oe_form_field_char_not_sapce'>
    
        When user input ' aa  bb cc ' for 'code', web client auto transform to 'aabbcc'.
            
    """,
    'website': '',
    'images': [],
    'depends': ['web'],
    'data': [],
    'js': ['static/src/js/*.js'],
     #qweb': ['static/src/js/nospace_fieldchar.xml'],
    'css': ['static/src/js/*.css'],
    'demo': [
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: