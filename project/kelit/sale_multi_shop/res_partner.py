# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#     Jon Chow <jon.chow@elico-corp.com>
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

from openerp.osv import fields,osv

class  res_partner(osv.osv):
    _inherit = 'res.partner'
    
    # jon partner default shop_id come from the create user'shop_id
    def _get_default_shop(self,cr,uid,context=None):
        user=self.pool.get('res.users').browse(cr,1,uid)
        return user.shop_id and user.shop_id.id or False
        
        
    _columns={
        'shop_id': fields.many2one('sale.shop','Shop'),
    }
    _defaults={
        'shop_id':lambda self,cr,uid,context:self._get_default_shop(cr,uid,context=context),       
    }
    
    
    def write(self,cr,uid,ids, values, context=None):
        """
        when change  shop_id,  all contracts(child_ids) shop_id will the same change too 
        """
        res=super(res_partner,self).write(cr,uid,ids,values,context=context)
        shop_id=values.get('shop_id',False)
        
        ids= type(ids)==list and ids or [ids]
        if shop_id:
            for patner in self.browse(cr,uid,ids,):
                if patner.is_company and patner.child_ids:
                    self.write(cr,uid,[x.id for x in patner.child_ids],{'shop_id':shop_id},)
        return res

        
res_partner()







