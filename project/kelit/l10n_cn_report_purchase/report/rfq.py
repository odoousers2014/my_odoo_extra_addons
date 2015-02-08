# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author:            Eric CAUDAL <contact@elico-corp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
from lxml import etree
from openerp.osv import osv,fields
from openerp.tools.translate import _

class rfq(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(rfq, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            '_add_header':self._add_header,
            'tag':self.tag,
            'get_line_tax': self._get_line_tax,
            'get_tax': self._get_tax,
            'get_product_code': self._get_product_code,
            'get_supplier_productcode': self._get_supplier_productcode,
            'get_purchase_discount':self._get_purchase_discount,
            'get_default_bank':self._get_default_bank,
        })
    #jon  get the discount
    def _get_purchase_discount(self, pol_id):
        cr=self.cr
        uid=1
        discount=0.0
        
        pol_obj=self.pool.get('purchase.order.line')
        line=pol_obj.browse(cr,uid,pol_id)
        
        standard_price = line.product_id.standard_price
        if standard_price:
            discount= line.price_unit / standard_price

        if discount:
            return  '%.4f' %  discount
        else:
            return  ''
        
    # jon: get the  supplier produnct info     
    def _get_supplier_productcode(self,product_id,partner_id):
        code=''
        ps_obj=self.pool.get('product.supplierinfo')
        search_ids=ps_obj.search(self.cr, 1, [('product_id','=',product_id),('name','=',partner_id)])
        obj_id=search_ids and search_ids[0]
        if obj_id:
            ps=ps_obj.browse(self.cr,1,obj_id)
            code=r'[' + ps.product_code + r']' + ps.product_name
        else:
            code = self.pool.get('product.product').name_get(self.cr,1,[product_id,])[0][1]
        return code
    
    
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


    def _get_line_tax(self, line_obj):
        self.cr.execute("SELECT tax_id FROM purchase_order_taxe WHERE order_line_id=%s", (line_obj.id))
        res = self.cr.fetchall() or None
        if not res:
            return ""
        if isinstance(res, list):
            tax_ids = [t[0] for t in res]
        else:
            tax_ids = res[0]
        res = [tax.name for tax in pooler.get_pool(self.cr.dbname).get('account.tax').browse(self.cr, self.uid, tax_ids)]
        return ",\n ".join(res)
    
    
    def _get_tax(self, order_obj):
        self.cr.execute("SELECT DISTINCT tax_id FROM purchase_order_taxe, purchase_order_line, purchase_order \
            WHERE (purchase_order_line.order_id=purchase_order.id) AND (purchase_order.id=%s)", (order_obj.id))
        res = self.cr.fetchall() or None
        if not res:
            return []
        if isinstance(res, list):
            tax_ids = [t[0] for t in res]
        else:
            tax_ids = res[0]
        tax_obj = pooler.get_pool(self.cr.dbname).get('account.tax')
        res = []
        for tax in tax_obj.browse(self.cr, self.uid, tax_ids):
            self.cr.execute("SELECT DISTINCT order_line_id FROM purchase_order_line, purchase_order_taxe \
                WHERE (purchase_order_taxe.tax_id=%s) AND (purchase_order_line.order_id=%s)", (tax.id, order_obj.id))
            lines = self.cr.fetchall() or None
            if lines:
                if isinstance(lines, list):
                    line_ids = [l[0] for l in lines]
                else:
                    line_ids = lines[0]
                base = 0
                for line in pooler.get_pool(self.cr.dbname).get('purchase.order.line').browse(self.cr, self.uid, line_ids):
                    base += line.price_subtotal
                res.append({'code':tax.name,
                    'base':base,
                    'amount':base*tax.amount})
        return res
    
    
    def _get_product_code(self, product_id, partner_id):
        product_obj=pooler.get_pool(self.cr.dbname).get('product.product')
        return product_obj._product_code(self.cr, self.uid, [product_id], name=None, arg=None, context={'partner_id': partner_id})[product_id]
    def _get_default_bank(self,partner_id):
        partner_obj=self.pool.get('res.partner')
        partner=partner_obj.browse(self.cr,self.uid,partner_id)
        
        d_bank=None
        if  partner.bank_ids:
            for bank in partner.bank_ids:
                if bank.default_bank:
                    d_bank=bank
            d_bank = d_bank or partner.bank_ids[0]

        return d_bank


            


        

        
        
        
                    
            
        
        
        
        
        
        

report_sxw.report_sxw('report.l10n.cn.rfq', 'purchase.order', 'addons/l10n_cn_report_purchase/report/rfq.rml', parser=rfq, header='external portrait')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: