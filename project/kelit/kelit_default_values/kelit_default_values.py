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

#JON 2013-03-06  set the res.partner default values

class res_partner(osv.osv):
    _inherit = 'res.partner'
    def _get_default_section(self,cr,uid,context=None):
        """
        get the  default_section_id('Salse  Team') of work user 'uid'
        """
        users_obj=self.pool.get('res.users')
        user = users_obj.browse(cr,uid,uid)
        return user.default_section_id.id
        
    _defaults={
        'user_id': lambda self,cr,uid,context: uid,
        'section_id': lambda self,cr,uid,context: self._get_default_section(cr,uid,context),
    }
res_partner()


# Jon 2013-03-07  set  default value for fields user_id section_id of   crm.lead 
class crm_lead(osv.osv):
    _inherit='crm.lead'
    def _get_default_section(self,cr,uid,context=None):
        """
        get the  default_section_id('Sales  Team') of work user 'uid'
        """
        users_obj=self.pool.get('res.users')
        user = users_obj.browse(cr,uid,uid)
        return user.default_section_id.id
    _defaults={
        'user_id': lambda self,cr,uid,context: uid,
        'section_id': lambda self,cr,uid,context: self._get_default_section(cr,uid,context),    
    }    
crm_lead()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: