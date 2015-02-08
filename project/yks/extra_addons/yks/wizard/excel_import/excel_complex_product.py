#-*-coding:utf-8 -*-

import base64
from openerp.osv import  osv


class excel_complex_product(osv.osv_memory):
    """"""
    _inherit = "excel.base"

    def apply(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = super(excel_complex_product, self).apply(cr, uid, ids, context=context)
        wizard = self.browse(cr, uid, ids[0], context=context)
        
        if wizard.model == 'complex_product':
            res_ids = self.create_complex_product(cr, uid, wizard, context)
            res.update({
                'name': u'新导入产品',
                'view_type': 'form',
                "view_mode": 'tree,form',
                'res_model': 'mrp.bom',
                "domain": [('id', 'in', res_ids)],
                'type': 'ir.actions.act_window',
            })

        return res

    def create_complex_product(self, cr, uid, wizard, context=None):
        """"""
        res_ids = []

        title_data = self.parse_title_data(file_contents=base64.decodestring(wizard.file))
        self.check_complex_product(wizard.model, title_data)
        """导入或者创建"""
        product_obj = self.pool.get('product.product')
        bom_boj = self.pool.get('mrp.bom')
        uom_id = 1
        dic = {}
        this_sku = None
        for info in title_data['data']:
            complex_sku = info.get('complex_sku')
            name = info.get('name',)
            sub_sku = info.get('sub_sku')
            qty = info.get('qty')

            if complex_sku:
                this_sku = complex_sku
            if this_sku:
                if this_sku in dic:
                    dic[this_sku][1].append((sub_sku, qty))
                else:
                    dic[this_sku] = [name, [(sub_sku, qty)]]
            else:
                dic[this_sku][1].append((sub_sku, qty))

        #create complex_product and bom
        for sku in dic:
            sku_search = product_obj.search(cr, uid, [('default_code', '=', sku)])
            if sku_search:
                raise osv.except_osv("Error", u"组合SKU已经存在 %s" % sku)

            complex_id = product_obj.create(cr, uid, {
                'name': dic[sku][0],
                'default_code': sku,
                'supply_method': 'produce',
            })

            lines = []
            for j in dic[sku][1]:
                sub_pdt_search = product_obj.search(cr, uid, [('default_code', '=', j[0])])
                sub_pdt_id = sub_pdt_search and sub_pdt_search[0]
                if sub_pdt_id:
                    lines.append((0, 0, {'product_id': sub_pdt_id, 'product_qty': j[1], 'product_uom': uom_id}))
                else:
                    raise osv.except_osv("Error", "Not found SKU %s" % j[0])

            bom_id = bom_boj.create(cr, uid, {
                'product_id': complex_id,
                'product_uom': uom_id,
                'bom_lines': lines,
            }, context=context)
            res_ids.append(bom_id)

        return res_ids

    def check_complex_product(self, model, title_data):
        if model == "complex_product":
            bad_title = ''
            for title in self.Excel_model[model]['title']:
                if title not in title_data['title']:
                    bad_title += '%s\t' % title
            if bad_title:
                raise osv.except_osv(u'错误', u'下列必须字段不存在，请添加\n%s' % bad_title)
            bad_line = ''
            for line in title_data['data']:
                if (not line.get('sub_sku')) or (not line.get('qty')):
                    bad_line += "%s\t" % line['row_nu']
            if bad_line:
                raise osv.except_osv(u'错误', u'下列行信息不全，请补全\n%s' % bad_line)
        return True


excel_complex_product()

########################################################