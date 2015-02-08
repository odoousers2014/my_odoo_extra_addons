# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

{
    'name': 'MMX InterCompany',
    'version': '1.0',
    'author': 'Jon Chow',
    'website': 'http://www.elico-corp.com',
    'summary': '',
    'description': """
         MMX InterCompany
         EX:Company1 PO auto create Company2 SO
    """,
    'depends': ['base', 'sale_stock', 'purchase', 'sale' , 'stock',],
    'category': '',
    'sequence': 10,
    'demo': [],
    'data': [
        'company_view.xml',
        'sale_view.xml',
        #'purchase_wkf.xml',
        #'stock_picking_wkf.xml',
        #'security/intercompany_security.xml',
        #'security/ir.model.access.csv',
        ],
    'test': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'css': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
