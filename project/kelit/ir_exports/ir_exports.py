
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


class ir_exports_line (osv.osv):
    _inherit = "ir.exports.line"
    _order='sequence'
    def _get_filed_string(self,cr,uid,ids,fields_name,args=None,context=None):
        res={}
        f_obj=self.pool.get('ir.model.fields')
        
        for line in self.browse(cr, uid, ids, context=context):
            f_ids=f_obj.search(cr,uid,  [ ('name','=',line.name),('model_id.model','=',line.export_id.resource )])
            
            f_id = f_ids and f_ids[0] or False
            if f_id:
                f=f_obj.browse(cr,uid,f_id)
                res[line.id]=f.field_description
            else:
                res[line.id]='Null'
                
        return res
    _columns={
        #jon  add  seq for ir_exports_line
        'sequence':fields.integer('Sequence'),
        'string':fields.function(_get_filed_string, type='char',size=32,string='String',store=True),
    }
ir_exports_line()




 