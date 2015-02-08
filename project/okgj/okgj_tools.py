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

import time
from openerp.osv import fields, osv
from openerp.tools.translate import _


def check_uid_in_groups(self, cr, uid, group_name='', context=None):
    
    if not group_name:
        return False
    
    ADMIN=1
    group_pool = self.pool.get('res.groups')
    group_ids = group_pool.search(cr, ADMIN, [('name','=',group_name)], context=context)
    if len(group_ids) != 1:
        raise osv.except_osv(_('Error:'), _(u"没有找到权限组"))
    gp = group_pool.browse(cr, ADMIN, group_ids[0], context=context)
    user_ids = [u.id for u in gp.users]
    if uid in user_ids:
        return True
    else:
        return False

    
    
    
    
    
    












