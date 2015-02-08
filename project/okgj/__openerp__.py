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

{
    'name': u'OK管家',
    'version': '1.0',
    'category': 'Tools',
    'description': """
    OK管家订制模块
    """,
    'author': 'OUKEYUN',
    'website': 'http://oukeyun.com',
    'sequence': 9,
    'depends': [
        'base',
        'product',
        'stock',
        'product_expiry',
        'sale',
        'sale_stock',
        'procurement',
        'purchase',
        'mrp',
        'hr',
        'product_margin',
        'sale_margin',
    ],
    'data': [
        'security/okgj_security.xml',
        'security/ir.model.access.csv',
        'partner_view.xml',
        'okgj_sequence.xml',
        'product_view.xml',
        'okgj_product_expiry_view.xml',
        'stock_internal_view.xml',
        'order_internal_view.xml',
        'stock_in_view.xml',
        'stock_out_view.xml',
        'order_return_view.xml',
        'wizard/purchase_fill_order_view.xml',
        'wizard/purchase_return_fill_order_view.xml',
        'wizard/multi_order_print_view.xml',
        'wizard/stock_out_verify_view.xml',
        #'wizard/product_rack_change_view.xml',
        'wizard/okgj_rack_arrange.xml',
        'wizard/okgj_prom_purchase_price_import_view.xml',
        'purchase_view.xml',
        'okgj_base_price_change_view.xml',
        'okgj_shop_api_view.xml',
        'okgj_message_view.xml',
        'okgj_car_view.xml',
        'okgj_picking_reg_view.xml',
        'okgj_adjust_price.xml',
        #TODO:Only used for Test, will remove
        #'test_view.xml',
        'okgj_data.xml',
        'okgj_import_product_view.xml',
        'okgj_import_stock_view.xml',
        'okgj_import_rack_view.xml',
	#'okgj_product_update_view.xml',
        'okgj_import_order_view.xml',
        'okgj_menu.xml',
        'okgj_doc_detail_view.xml',
        'okgj_purchase_price_management_view.xml',
        'okgj_sale_claim_view.xml',
        'report/okgj_special_report.xml',
        'report/okgj_sale_report_view.xml',
        'report/okgj_jitinventory_report_view.xml',
        'report/okgj_adventgoodsinv_report_view.xml',
        'report/okgj_guestfolio_report_view.xml',
        'report/okgj_guestfolioproduct_report_view.xml',
        'report/okgj_returnamount_report_view.xml',
        'report/okgj_oemproduct_report_view.xml',
        'security/okgj_menu_security.xml',
        'procurement_data.xml',
        'okgj_oem.xml',
        'sale_view.xml',
        'okgj_field_write_access_view.xml',
        'product_get_cost_field.xml',
    ],
    #'js': [
    #    'static/src/js/okgj.js'
    #],
    #'css': [
    #    'static/src/css/okgj.css'
    #],

    'installable': True,
    'application': False,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
