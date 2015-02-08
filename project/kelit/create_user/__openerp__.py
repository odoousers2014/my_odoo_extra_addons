# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: jon chow<jon.chow @elico-corp.com>
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
    'name': 'Create  user',
    'version': '1.0',
    'author': 'Elico Corp',
    'website': 'http://www.elico-corp.com',
    'summary': '',
    'description' : """
     New user creation action for multicompany environment.
     When creating a new user, OpenERP by default creates 2 object:
res.user
res.partner
    - company_id = res.user (the user you are creating) company_id
    - salesman = blank

Eg:
1- You login as admin (COMPANY1)

2- Create new user: JC (we want COMPANY2)
    - res.user/company_id: COMPANY2

3- Press button CREATE
    -OE create res.partner: JC
        - company_id = COMPANY1 -> COMPANY2
        - salesman = admin    -> BLANK
        """,
    'depends': ['base','crm','sale','purchase'],
    'category': '',
    'sequence': 10,
    'demo': [],
    'data': [
        #'create_user_view.xml',
        ],
    'test': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'css': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: