# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import fields, osv
from openerp import pooler
import re

class purchase_order(osv.osv):
    _inherit='purchase.order'
    
    # Jon print button print_quotation  print the  rfq report 
    def print_quotation(self, cr, uid, ids, context=None):
        result= super(purchase_order,self).print_quotation(cr,uid,ids,context=context)
        return  {'type': 'ir.actions.report.xml', 'report_name': 'l10n.cn.rfq', 'datas': result['datas'], 'nodestroy': True}  
      
purchase_order()


#def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
    