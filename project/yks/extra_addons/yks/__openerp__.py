# -*- coding: utf-8 -*-
##############################################################################
##<alangwansui@gmail.com>
##############################
{
    'name': 'YKS  Extend',
    'version': '10.',
    'author': 'jon <alangwansui@gmail.com>',
    'category': 'category',
    'description': """
YKS sale.order picking Extend,
    """,
    'website': 'website',
    'images': [],
    'depends': ['base', 'sale', 'stock', 'sale_stock', 'product', 'purchase', 'mrp',
                'report_webkit', 'delivery', 'hr', 'sale_crm', 'web_shortcuts'],
    'data': [
       'security/yks_security.xml',
       'security/ir.model.access.csv',
       'report/report.xml',
       'report/sales_performance_report.xml',

       'menu.xml',
       'data/data.xml',
       'partner.xml',
       'sale.xml',
       'sale_wkf.xml',
       'purchase.xml',
       'purchase_wkf.xml',
       'stock.xml',
       'product.xml',
       'mrp.xml',
       'sync_api.xml',
       'user.xml',
       'direct_sell_template.xml',
       'sale_back.xml',
       'delivery_carrier.xml',
       'express.xml',
       'stock_warehouse_orderpoint.xml',
       'price.xml',
       'requirement_distribution_order.xml',
       'account.xml',
       
       'other/template_germany_sale.xml',
       'wizard/so_direct_sell_template.xml',
       'wizard/monkey_login.xml',
       'wizard/so_batch_modify.xml',
       'wizard/so_batch_confirm.xml',
       'wizard/quickly_shop_establish.xml',
       'wizard/picking_cancel_check.xml',
       'wizard/express_batch_create.xml',
       'wizard/express_batch_sync.xml',
       #'wizard/express_partial_picking.xml',
       'wizard/sync_single_so.xml',
       'wizard/partner_change_charge.xml',
       'wizard/excel_import/excel_base.xml',
       'wizard/excel_import/excel_product.xml',
       'wizard/excel_import/excel_complex_product.xml',
       'wizard/excel_import/excel_warehouse_orderpoint.xml',
       'wizard/excel_import/excel_sale_order.xml',
       'wizard/excel_import/excel_account.xml',
       
       'wizard/picking_batch_done.xml',
       'wizard/stock_picking_split.xml',
       'wizard/picking_scan_done.xml',
       'wizard/sale_adjustable_goods.xml',
       
       
       'ir_exports.xml',
       'ir_cron.xml',

    ],
    'js': [
    ],
    'qweb': [
    ],
    'css': [
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: