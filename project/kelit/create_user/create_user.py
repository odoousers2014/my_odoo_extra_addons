##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class res_users(osv.osv):
    _inherit = 'res.users'

    def create(self,cr,uid,values,context=None):
    #Jon when create a user,  
    #1:the res.partner.company_id  is the same as the res.user.comany_id  
    #2: user_id =False
    #3:partner.shop_id  is the same as the   user.shop_id  
        user_id = super(res_users,self).create(cr,uid,values,context=context)
        user=self.browse(cr,uid,user_id,context=None)
        user_company_id=user.company_id and user.company_id.id or False
        partner_id = user.partner_id.id
        shop_id=user.shop_id and user.shop_id.id or False
        partner_obj=self.pool.get('res.partner')
        
        partner_obj.write(cr,uid,partner_id,{'company_id':user_company_id ,'user_id':False ,'shop_id':shop_id})
     
        return user_id
res_users()


 