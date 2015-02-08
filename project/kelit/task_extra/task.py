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





class task_issue_module(osv.osv):
    _name ='task.issue.module'
    _order = 'name'     
    def _auto_init(self, cr, context=None):
        uid = 1
        res = super(task_issue_module, self)._auto_init(cr, context=context)
        mod_pool = self.pool.get('ir.module.module')
        mod_ids = mod_pool.search(cr, uid, [])
        for mod in mod_pool.browse(cr, uid, mod_ids):
            if not self.search(cr, uid, [('name', '=', mod.name)]):
                self.create(cr, uid, {"name":mod.name})
        return res
    
    _columns = {
       'name': fields.char('Module', size=32),         
    }
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'name must be unique per module!'),
    ]
task_issue_module()

class task_issue_manage(osv.osv):
    _name = 'task.issue.manage'
    _columns = {
        'name': fields.char('Name', size=32),
        'module_id':fields.many2one('task.issue.module', string='Module'),
        'task_ids': fields.many2many('project.task', 'res_manage_task', 'manage_id', 'task_id',  string='Tasks'),
        'issue_ids': fields.many2many('project.issue', 'res_manage_issue', 'manage_id', 'issue_id',  string='Issues'),          
    }
task_issue_manage()

    
class project_task(osv.osv):
    _inherit = 'project.task'
    _columns={
        'manage_ids':fields.many2many('task.issue.manage', 'res_manage_task',  'task_id','manage_id',  string='Modules'),
    }
project_task()

class project_issue(osv.osv):
    _inherit = 'project.issue'
    _columns={
        'manage_ids':fields.many2many('task.issue.manage', 'res_manage_issue', 'issue_id', 'manage_id',  string='Modules'),
    }
project_issue()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
