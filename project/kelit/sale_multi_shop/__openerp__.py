# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2011 Zikzakmedia S.L. (http://zikzakmedia.com)
#        All Rights Reserved, Jesús Martín <jmartin@zikzakmedia.com>
#        All Rights Reserved, Raimon Esteve <resteve@zikzakmedia.com>
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    'name' : 'Sale Multi Shop',
    'version' : '0.1',
    'author' : 'Zikzakmedia SL',
    'website' : 'http://www.zikzakmedia.com',
    "license" : "AGPL-3",
    'category' : 'Generic Modules/Sales & Purchases',
    'description' : """
This module allows to manage the multi shops by multi companies: 
- Relationship between shops and users
- Search filter and list by shop
""",
    'depends' : [
        'base','sale','sale_stock','purchase', 'account','kelit_partner'
    ],
    'init_xml' : [
    ],
    'demo_xml' : [
    ],
    'update_xml' : [
        'stock_view.xml',
        'sale_view.xml',
        'users_view.xml',
        'purchase_view.xml',
        'res_partner_view.xml',
        'security/sale_multi_shop_security.xml',
    ],
    'active' : False,
    'installable' : True,
}
