# -*- coding:utf-8 -*-

import base64
from openerp.osv import osv


class excel_warehouse_orderpoint(osv.osv_memory):
    _inherit = "excel.base"

    def check_orderpoint(self, model, title_data):
        if model == "orderpoint":
            bad_title = ''
            for title in self.Excel_model[model]['title']:
                if title not in title_data['title']:
                    bad_title += '%s\t' % title
            if bad_title:
                raise osv.except_osv(u'错误', u'下列必须字段不存在，请添加\n%s' % bad_title)
            bad_line = ''
            for line in title_data['data']:
                for title in self.Excel_model[model]['title']:
                    if not line[title]:
                        bad_line += "%s\t" % line['row_nu']
            if bad_line:
                raise osv.except_osv(u'错误', u'下列行信息不全，请补全\n%s' % bad_line)

    def apply(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = super(excel_warehouse_orderpoint, self).apply(cr, uid, ids, context)
        wizard = self.browse(cr, uid, ids[0], context)
        if wizard.model == 'orderpoint':
            res_ids = self.create_warehouse_orderpoint(cr, uid, wizard, context)
            res.update({
                'name': u'新导入产品',
                'view_type': 'form',
                "view_mode": 'tree,form',
                'res_model': 'stock.warehouse.orderpoint',
                "domain": [('id', 'in', res_ids)],
                'type': 'ir.actions.act_window',
            })
        return res

    def create_warehouse_orderpoint(self, cr, uid, wizard, context=None):

        title_data = self.parse_title_data(file_contents=base64.decodestring(wizard.file))
        self.check_orderpoint(wizard.model, title_data)
        res_ids = []
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        product_obj = self.pool.get('product.product')
        warehouse_obj = self.pool.get('stock.warehouse')
        bad_sku = ''
        for info in title_data['data']:
            sku = str(info.get('sku')).strip()
            product_id = product_obj.search(cr, uid, [('default_code', '=', sku)])
            if not product_id:
                bad_sku += "%s,\t" % info['row_nu']
        if bad_sku:
            raise osv.except_osv(u"错误", u"下列行的SKU不存在,请先添加\n%s" % bad_sku)

        for info in title_data['data']:
            sku = str(info.get('sku')).strip()
            #warehouse = str(info.get('warehouse')).strip()
            product_min_qty = info.get('product_min_qty')
            #warehouse_id = warehouse_obj.search(cr,uid,[('name','=',warehouse)])[0]
            ware_obj = warehouse_obj.browse(cr, uid, 1, context)
            #if not warehouse_id:
            #   raise osv.except_osv(u"错误", u"%s不存在，请核对或者添加" % warehouse)

            product_id = product_obj.search(cr, uid, [('default_code', '=', sku)])
            if  not product_id:
                raise osv.except_osv(u"错误", u"%s不存在，请先添加" % sku)
            else:
                product_id = product_id[0]
            vals = {
                'product_min_qty': product_min_qty,
                'product_id': product_id,
                'warehouse_id': 1,
                'location_id': ware_obj.lot_stock_id.id,
                'product_max_qty': product_min_qty,
                'product_uom': 1,
            }
            exist_sku_ids = orderpoint_obj.search(cr, uid, [('product_id', '=', product_id)])
            if exist_sku_ids:
                orderpoint_obj.write(cr, uid, exist_sku_ids, vals)
                res_ids.append(exist_sku_ids[0])
            else:
                new_id = orderpoint_obj.create(cr, uid, vals, context)
                res_ids.append(new_id)

        return  res_ids

excel_warehouse_orderpoint()

####################################################