# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2011 Zikzakmedia S.L. (http://zikzakmedia.com)
#        All Rights Reserved, Jesús Martín <jmartin@zikzakmedia.com>
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

from openerp.osv import osv, fields

class users(osv.osv):
    _inherit  =  "res.users"
    
    #Jon Insure that, user.shop_id  in  user.shop_ids
    def _check_shop_id_ids(self,cr,uid,ids,context=None):
        res=True
        for u in self.browse(cr,uid, ids):
            if u.shop_id:
                if u.shop_id.id not in [x.id for x in u.shop_ids]:
                    res=False
        return res
    
    _columns  =  {
        'shop_ids': fields.many2many('sale.shop', 'shop_user_rel', 'shop_id', 'user_id', "Shops"),
        'shop_id': fields.many2one('sale.shop', 'Shop', help='The current shop related to the user'),
    }
    _constraints = [
        (_check_shop_id_ids, 'shop_id must in shop_ids,Please insure Shop is contained Shops', ['shop_id','shop_ids']),
    ]  
    
    def __init__(self, *args):
        super(users, self).__init__(*args)
        if 'shop_id' not in self.SELF_WRITEABLE_FIELDS:
            self.SELF_WRITEABLE_FIELDS.append('shop_id')
            

users()
