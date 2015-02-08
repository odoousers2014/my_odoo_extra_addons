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
from openerp.report import report_sxw
from lxml import etree
from openerp.osv import osv,fields
from openerp.tools.translate import _

class stock_move_sample(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        uid = 1
        super(stock_move_sample, self).__init__(cr, uid, name, context=context)
        
        company_pool = self.pool.get('res.company')
        company_ids = company_pool.search(cr,uid,[])
        company_partner_ids =[c.partner_id.id  for c in company_pool.browse(cr,uid,company_ids) ]
        
        sample_move_ids = context.get('sample_move_ids', False)
        struct_data = {} # {sale_id:{'partner_id' : [move1, move2 ] } }
        for move in self.pool.get('stock.move').browse(cr, uid, sample_move_ids):
            saler = move.picking_id.salesman_id
            partner = move.partner_id
            
            #if not saler:  
            #    print move,move.picking_id,move.picking_id.partner_id,move.picking_id.partner_id.user_id, move.picking_id.partner_id.user_id.name

            if partner.id in company_partner_ids:
                continue
            
            if struct_data.get(saler, False):
                if struct_data[saler].get(partner,False):
                    struct_data[saler][partner].append(move)
                else:
                    struct_data[saler].update({partner:[move,]})
            else:
                struct_data.update({saler:{partner:[move,]}}) 
                
        
        self.localcontext.update({
            'time': time,
            'struct_data': struct_data,
            'total_moves': self._total_moves,
        })
    def _total_moves(self, moves=[] ):
        total = int (  sum([m.product_qty  for m in moves]) )
        return total

    def _add_header(self, rml_dom, header='external'):
        if header=='internal':
            rml_head =  self.rml_header2
        elif header=='internal landscape':
            rml_head =  self.rml_header3
        elif header=='external':
            rml_head =  self.rml_header
        else:
            header_obj= self.pool.get('res.header')
            rml_head_id = header_obj.search(self.cr,self.uid,[('name','=',header)])
            if rml_head_id:
                rml_head = header_obj.browse(self.cr, self.uid, rml_head_id[0]).rml_header
        try:
            head_dom = etree.XML(rml_head)
        except:
            raise osv.except_osv(_('Error in report header''s name !'), _('No proper report''s header defined for the selected report. Check that the report header defined in your report rml_parse line exist in Administration/reporting/Reporting headers.' ))
            
        for tag in head_dom:
            found = rml_dom.find('.//'+tag.tag)
            if found is not None and len(found):
                if tag.get('position'):
                    found.append(tag)
                else :
                    found.getparent().replace(found,tag)
        return True
        
        
report_sxw.report_sxw(
    'report.stock_move_sample',
    'stock.move',
    'addons/kelit_sales/report/stock_move_sample.mako',
    parser=stock_move_sample,
    header='default portrait',
)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
