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

import new
from openerp.osv import fields, osv
from openerp.report.report_sxw import report_sxw
import openerp.pooler as pooler
from openerp.tools.translate import _


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _name    = 'res.partner'
    
    _columns = {
        'header_id': fields.many2one('res.header', 'Header'),          
    }

res_partner()



class res_header(osv.osv):
    _inherit = 'res.header'
    _name    = 'res.header'
    
    _columns = {
        'partner_ids': fields.one2many('res.partner', 'header_id', 'Partners'),          
    }

res_header()



#fix report_sxw class, so the report_sxw.report_sxw()  object 
#  pass arg  context={'header_by_partner':True}  to select the partner 
#   jon.chow<@>elico-corp.com    Jun 8, 2013
def enhance_method(klass, method_name, replacement):
    method = getattr(klass, method_name)
    setattr(klass, method_name, new.instancemethod(lambda *args, **kwds: replacement(method, *args, **kwds), None, klass))



def new_init(old_method, self, *args, **kwds):
    if kwds.get('context', False):
        self.context = kwds.pop('context')
    else:
        self.context = {}
    return old_method(self, *args, **kwds)



def new_create(old_method, self, *args, **kwds):
    cr,uid, ids, data, context = args
    
    if context is None:
        context = {}
    if self.internal_header:
        context.update(internal_header=self.internal_header)
    # skip osv.fields.sanitize_binary_value() because we want the raw bytes in all cases
    context.update(bin_raw=True)
    
    pool           = pooler.get_pool(cr.dbname)
    ir_obj         = pool.get('ir.actions.report.xml')
    report_xml_ids = ir_obj.search(cr, uid, [('report_name', '=', self.name[7:])], context=context)
    if report_xml_ids:
        report_xml = ir_obj.browse(cr, uid, report_xml_ids[0], context=context)
    else:
        title       = ''
        report_file = tools.file_open(self.tmpl, subdir=None)
        try:
            rml         = report_file.read()
            report_type = data.get('report_type', 'pdf')
            class a(object):
                def __init__(self, *args, **argv):
                    for key,arg in argv.items():
                        setattr(self, key, arg)
            report_xml = a(title=title, report_type=report_type, report_rml_content=rml, name=title, attachment=False, header=self.header)
        finally:
            report_file.close()
    if report_xml.header:
        #jon select partner header, if context ...
        # get_header_by_partner  should be defined at the parser, 
        if  hasattr(self,'context'):
            function_header = self.context.get('function_header_get', False)
            if function_header:
                header            = function_header(cr,uid,ids)
                report_xml.header = header
                self.header       = header
        else:
            report_xml.header = self.header
    
    
    report_type = report_xml.report_type
    if report_type in ['sxw','odt']:
        fnct = self.create_source_odt
    elif report_type in ['pdf','raw','txt','html']:
        fnct = self.create_source_pdf
    elif report_type=='html2html':
        fnct = self.create_source_html2html
    elif report_type=='mako2html':
        fnct = self.create_source_mako2html
    else:
        raise NotImplementedError(_('Unknown report type: %s') % report_type)
    fnct_ret = fnct(cr, uid, ids, data, report_xml, context)
    if not fnct_ret:
        return False, False
    return fnct_ret

enhance_method(report_sxw, 'create',   new_create)
enhance_method(report_sxw, '__init__', new_init)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: