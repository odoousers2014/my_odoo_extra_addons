# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Damiano Falsanisi <damiano.falsanisi@elico-corp.com>, Jon Chow <jon.chow@elico-corp.com>
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

from openerp.osv import osv, fields


class crm_lead(osv.osv):
    _inherit='crm.lead'
    #Jon add m2o field 'channel_id' (crm.case.channel)   
    _columns={   
        'channel_id':fields.many2one('crm.case.channel', string='Channel'),
        'partner_categ_id' :fields.many2one('res.partner.category', string='Customer Category'),
    }
    
    _defaults={
        'user_id': lambda self,cr,uid,context: uid,
    }
       # 'category_id': fields.many2many('res.partner.category', id1='partner_id', id2='category_id', string='Tags'),

    #jon  defined a fucnt,  finish crm_lead2opportunity  wizard functon, not need the wizard view   
    def crm_lead2opportunity(self,cr,uid,ids,context=None):
        l2o_obj = self.pool.get('crm.lead2opportunity.partner')
        l2o_ids=[]
        for id in ids:
            #jon create the wizard context, and  create the default wizard obj
            context.update( {'active_model':'crm.lead', 'active_id':id, 'active_ids':ids,} )
            l2o_id =l2o_obj.create(cr,uid, {'name': 'convert',  'action': 'create'},  context)
            l2o_ids.append(l2o_id)
            
        return l2o_obj.action_apply(cr,uid,l2o_ids,context=context)
    
    #jon  whne crm_lead2opportunity, same time, write the  partner_category_id
    def _lead_create_contact(self, cr, uid, lead, name, is_company, parent_id=False, context=None):
        
        partner_obj=self.pool.get('res.partner')
        partner_id= super(crm_lead, self)._lead_create_contact(cr, uid, lead, name, is_company, parent_id=parent_id, context=context)
        
        if partner_id:
            categ_id = lead.partner_categ_id and lead.partner_categ_id.id or False
            partner_obj.write(cr, uid, partner_id, {'categ_id': categ_id} )
            
        return partner_id
    
    #jon  defined a fucnt,  finish opportunity2order  wizard functon, not need the wizard view  
    def opportunity2order(self,cr,uid,ids,context=None):
        p2o_obj = self.pool.get('crm.make.sale')
        #user_obj = self.pool.get('res.users')
        
        p2o_ids = []
        for id in ids:
            context.update( {'active_model':'crm.lead', 'active_id':id, 'active_ids':ids,} )
            lead = self.browse(cr, uid, id, )
            shop_id = lead.user_id.shop_id  and  lead.user_id.shop_id.id   or   1
            p2o_id =p2o_obj.create(cr,uid, {'partner_id': lead.partner_id.id,  'shop_id': shop_id, 'close':False },  context)
            p2o_ids.append(p2o_id)
            
        return p2o_obj.makeOrder(cr,uid,p2o_ids,context=context)
            
crm_lead()

