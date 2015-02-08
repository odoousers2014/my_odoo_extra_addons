#-*-coding:utf-8 -*-

import base64
from openerp.osv import  osv


class excel_product(osv.osv_memory):
    _inherit = "excel.base"

    def check_product(self, model, title_data):
        bad_title = ''
        if model == "product":
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
        res = super(excel_product, self).apply(cr, uid, ids, context=context)
        wizard = self.browse(cr, uid, ids[0], context=context)

        if wizard.model == 'product':
            res_ids = self.create_product(cr, uid, wizard, context=context)
            res.update({
                'name': u'新导入产品',
                'view_type': 'form',
                "view_mode": 'tree,form',
                'res_model': 'product.product',
                "domain": [('id', 'in', res_ids)],
                'type': 'ir.actions.act_window',
            })

        return res

    def create_product(self, cr, uid, wizard, context=None):
        """"""
        res_ids = []
        product_obj = self.pool.get('product.product')
        category_obj = self.pool.get('product.category')
        brand_obj = self.pool.get('product.brand')
        place_obj = self.pool.get('res.country')

        replace = wizard.replace
        title_data = self.parse_title_data(file_contents=base64.decodestring(wizard.file))
        self.check_product(wizard.model, title_data)
        for info in title_data['data']:
            vals = {}
            sku = info.get('sku')
            name = info.get('name')
            vals.update({
                'default_code': str(sku).strip(),
                'name': name.strip(),
                'name_template': name.strip(),
                'list_price': info.get('list_price', 1.0),
                'standard_price': info.get('standard_price', 0),
            })
            en_name = info.get('en_name', '')
            if en_name:
                vals.update({'en_name': en_name})
            warranty = info.get('warranty', '')
            if warranty:
                vals.update({'warranty': warranty})
            formula = info.get('formula', '')
            if formula:
                vals.update({'formula': formula})
            suitable_crowd = info.get('suitable_crowd', '')
            if suitable_crowd:
                vals.update({'suitable_crowd': suitable_crowd})
            hs_code = info.get('hs_code', '')
            if hs_code:
                vals.update({'hs_code': hs_code})
            ean13 = info.get('ean13', '')
            if ean13:
                vals.update({'ean13': ean13})
            variants = info.get('variants', '')
            if variants:
                vals.update({'variants': variants})
            formula = info.get('formula', '')
            if formula:
                vals.update({'formula': formula})
            old_id = info.get('old_id', '')
            if old_id:
                vals.update({'old_id': old_id})
            suitable_crowd = info.get('suitable_crowd', '')
            if suitable_crowd:
                vals.update({'suitable_crowd': suitable_crowd})
            purchase_ok = info.get('purchase_ok', '')
            if purchase_ok:
                if int(purchase_ok) == 0:
                    purchase_ok = False
                else:
                    purchase_ok = True
                vals.update({'purchase_ok': purchase_ok})
            sale_ok = info.get('sale_ok', '')
            if sale_ok:
                if int(sale_ok) == 0:
                    sale_ok = False
                else:
                    sale_ok = True
                vals.update({'sale_ok': sale_ok})
            goods_item = info.get('goods_item', '')
            if goods_item:
                vals.update({'goods_item': str(goods_item).strip()})
            product_type = info.get('type', 'product')
            if type:
                vals.update({'type': str(product_type).strip()})
            procure_method = info.get('procure_method', 'make_to_stock')
            if procure_method:
                vals.update({'procure_method': str(procure_method).strip()})
            supply_method = info.get('supply_method', 'buy')
            if supply_method:
                vals.update({'supply_method': str(supply_method).strip()})
            category = info.get('category', '')
            brand = info.get('brand', '')
            place = info.get('place_production', '')
            if place:
                place = str(place).strip()
                place_id = place_obj.search(cr, uid, [('name', '=', place)])
                if place_id:
                    vals.update({'place_production': place_id[0]})
                else:
                    raise osv.except_osv(u'错误！', u'%s原产地在系统中不存在，请添加！' % place)
            if brand:
                brand = str(brand).strip()
                brand_id = brand_obj.search(cr, uid, [('name', '=', brand)])
                if brand_id:
                    vals.update({'brand_id': brand_id[0]})
                else:
                    raise osv.except_osv(u'错误！', u'%s品牌在系统中不存在，请添加！' % brand)
            if category:
                category = str(category).strip()
                categ_id = category_obj.search(cr, uid, [('name', '=', category)])
                if  categ_id:
                    vals.update({'categ_id': categ_id[0]})
                else:
                    raise osv.except_osv(u'错误！', u'%s类别在系统中不存在，请添加！' % category)
            exist_sku_ids = product_obj.search(cr, uid, [('default_code', '=', vals['default_code'])])
            if exist_sku_ids and replace == 'update':
                product_obj.write(cr, uid, exist_sku_ids, vals)
                record = product_obj.browse(cr, uid, exist_sku_ids[0], context=context)
                res_ids.append(exist_sku_ids[0])
            elif not exist_sku_ids:
                new_id = product_obj.create(cr, uid, vals, context)
                if new_id:
                    res_ids.append(new_id)
            else:
                raise osv.except_osv(u'错误！', u'SKU %s在系统中已经存在，无法新建' % vals['default_code'])
        return res_ids

excel_product()

###############################################
