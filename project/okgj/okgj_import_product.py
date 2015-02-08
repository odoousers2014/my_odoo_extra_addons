# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import osv, fields
import time
import xlrd
import base64
from openerp.tools.translate import _
import copy

IMPORT_PRODUCT_TABLE = (u'编码', u'品名', u'类别', u'规格', u'最小包装数', u'计量单位', u'市场价', u'采购价', u'会员价', u'品牌', u'产地', 
                        u'重量（g）', u'标记（产品状态）', u'长', u'宽', u'高',	u'备注', u'商品报废时间', u'商品保质期', u'禁止入库时间',
                        u'禁止出库时间', u'供应商编号', u'供应商名称', u'物流中心', u'销项税', u'进项税', u'快购商品', u'快购价')

IMPORT_BOM_TABLE = (u'组合装编码', u'组合装名称', u'类别', u'规格', u'计量单位', u'市场价', u'会员价', u'明细货品编码', u'组合数量', u'快购商品', u'快购价')
UPDATE_PRODUCT_TABLE = (u'编码', u'品名', u'类别', u'规格', u'最小包装数', u'市场价', u'会员价', u'品牌', u'产地', u'重量（g）',
                        u'标记（产品状态）', u'长', u'宽', u'高', u'备注', u'商品报废时间', u'商品保质期', u'禁止入库时间', u'禁止出库时间',
                        u'采购状态', u'主供应商编号', u'主供应商名称', u'物流中心', u'采购价', u'销项税', u'进项税', u'快购商品', u'快购价')

UPDATE_BOM_TABLE = (u'组合装编码', u'组合装名称', u'类别', u'规格', u'市场价', u'会员价',
                    ## u'明细货品编码', u'组合数量',
                    u'快购商品', u'快购价')

class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'okgj_long': fields.float(u'长'),
        'okgj_wight': fields.float(u'宽'), ##由于最初代码实现人的拼写错误，数据已写入，更改正确容易出错
        'okgj_height': fields.float(u'高'), 
        'okgj_note': fields.char(u'备注', size=256), 
        'okgj_place': fields.char(u'产地', size=64),   
        'okgj_mark': fields.char(u'标记(产品状态)', size=64),                                    
    }
product_product()    
          
class okgj_product_import(osv.osv_memory):
    _name = "okgj.product.import"
    _columns = {
        'excel': fields.binary(u'excel文件', filters='*.xls', required=True),
        'import_address':fields.text(u'请从以下地址下载导入模板', readonly=True),
        'update_address':fields.text(u'请从以下地址下载更新模板', readonly=True),
    }
    
    _defaults = {
        'import_address': "http://192.168.10.137/import.xls",
        'update_address': "http://192.168.10.137/update.xls",
    }

    def number_to_str(self, number):
        if isinstance(number, float):                         
            return str(int(number)).strip()
        return str(number).strip()

    def number_to_float(self, number):
        if not number:
            return None
        if isinstance(number, float):                         
            answer = number
        else:
            try:
                answer = float(number)
            except:
                answer = False
        return answer
        
    def _get_purchase_state(self, change):
        if not change:
            return 'keep'
        if change == 'Y' or change == 'y':
            return True
        elif change == 'N' or change == 'n':
            return False
        else:
            return 'not'

    def _get_okkg_state(self, change):
        if not change:
            return 'keep'
        if change == 'Y' or change == 'y':
            return True
        elif change == 'N' or change == 'n':
            return False
        else:
            return 'not'

    def _get_categ_id(self, cr, uid, categ_name, context):
        if not context:
            context = {}
        if not categ_name:
            return None
        categ_obj = self.pool.get('product.category')  
        categ_ids = categ_obj.search(cr, uid, [('name', '=', categ_name)], context=context)
        if not categ_ids:
            return False
            ## categ_ids = [categ_obj.create(cr, uid, {'name':categ_name},context=context)]
        return categ_ids[0]

    def _get_uom_id(self, cr, uid, uom_name, context):
        if not context:
            context = {}
        uom_obj = self.pool.get('product.uom')     
        uom_categ_obj = self.pool.get('product.uom.categ') 
        uom_ids = uom_obj.search(cr, uid, [('name', '=', uom_name)], context=context)
        if not uom_ids:
            uom_categ_ids = uom_categ_obj.search(cr, uid, [('name', '=', 'Unit')], context=context)
            if not uom_categ_ids:
                uom_categ_ids = [uom_categ_obj.create(cr, uid, {'name':'Unit'}, context=context)]
            uom_ids = [uom_obj.create(cr, uid, {
                'name':uom_name,
                'category_id':uom_categ_ids[0],
                'factor':1,
                'rounding':1,
                'uom_type':'reference',
                }, context=context)]
        return uom_ids[0]

    def _get_brand_id(self, cr, uid, brand_name, context):
        if not context:
            context = {}
        brand_obj =  self.pool.get('okgj.product.brand') 
        brand_ids = brand_obj.search(cr, uid, [('name', '=', brand_name)], context=context)
        if not brand_ids:
            brand_ids = [brand_obj.create(cr, uid, {'name':brand_name}, context=context)]
        return brand_ids[0]

    def _get_supplier_id(self, cr, uid, company_name, company_ref, context):
        if not context:
            context = {}
        res_partner_obj =  self.pool.get('res.partner')
        supplier_ids = res_partner_obj.search(cr, uid, [('name', '=', company_name), ('ref', '=', company_ref), ('is_company','=',True)], context=context)
        if not supplier_ids:
            return False
            ## supplier_ids = [res_partner_obj.create(cr, uid, {
            ##     'name':company_name,
            ##     'ref':company_ref,
            ##     'supplier':True,
            ##     'is_company':True,
            ##     'customer':False
            ##     }, context=context)]
        return supplier_ids[0]

    def _get_warehouse_id(self, cr, uid, warehouse_name, context):
        if not context:
            context = {}
        if not warehouse_name:
            return None
        warehouse_obj =  self.pool.get('stock.warehouse') 
        warehouse_ids = warehouse_obj.search(cr, uid, [('name', '=', warehouse_name)], context=context)
        if warehouse_ids:
            return warehouse_ids[0]
        else:
            return False

    def _get_tax_id(self, cr, uid, type_tax_use, tax_code, context):
        if not tax_code:
            return None
        if not context:
            context = {}
        tax_ids = self.pool.get('account.tax').search(cr, uid, [('type_tax_use', '=', type_tax_use), ('description', '=', tax_code)], context=context)
        if tax_ids:
            return [(4, tax_ids[0])]
        return [(5)]

    def _get_tax_id_update(self, cr, uid, type_tax_use, tax_code, context):
        if not tax_code:
            return None
        if not context:
            context = {}
        tax_ids = self.pool.get('account.tax').search(cr, uid, [('type_tax_use', '=', type_tax_use), ('description', '=', tax_code)], context=context)
        if tax_ids:
            return [(6, 0, tax_ids)]
        return [(5)]

    def _update_tracking(self, use_time):
        if use_time is None:
            return (False, False)
        elif use_time != 0:
            return (True, True)
        else:
            return (False, False)

    def _update_basic_method(self, table_name):
        """
        依据导入的表返回成本计算方法，供应方式，商品类型
        入参
        @1,product
        """
        res = {}
        if table_name == 'table_product':
            res['cost_method'] = 'average'
            res['type'] = 'product'
            res['supply_method'] = 'buy'
        elif table_name == 'table_bom':
            res['cost_method'] = 'standard'
            res['type'] = 'consu'
            res['supply_method'] = 'produce'               
            res['purchase_ok'] = False
            res['is_group_product'] = True
        return res

    def _validate_product_data(self, line, line_data):
        message = ''
        ## if line_data['purchase_ok'] not in ['Y', 'y', 'N', 'n']:
        ##     message += u'商品表第' + str(line + 1) + u'行未知字符,导入未能开始' + '....................,'
        if line_data['min_qty'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品最小包装数错误,导入未能开始' + '....................,'
        if line_data['weight'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品重量错误,导入未能开始' + '....................,'
        if line_data['okgj_long'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品长错误,导入未能开始' + '....................,'
        if line_data['okgj_wight'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品宽错误,导入未能开始' + '....................,'
        if line_data['okgj_height'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品高错误,导入未能开始' + '....................,'
        if line_data['life_time'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品商品报废时间错误,导入未能开始' + '....................,'
        if line_data['use_time'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品商品保质期错误,导入未能开始' + '....................,'
        if line_data['alert_time'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品禁止入库时间错误,导入未能开始' + '....................,'
        if line_data['removal_time'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品禁止出库时间错误,导入未能开始' + '....................,'
        if line_data['other_price'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品市场价错误,导入未能开始' + '....................,'
        elif (line_data['other_price'] <= 0) or (line_data['other_price'] is None):
            message += u'商品表第' + str(line + 1) + u'行商品市场价不能为空或零,导入未能开始' + ';....................,'
        if line_data['standard_price'] is False :
            message += u'商品表第' + str(line + 1) + u'行商品采购价错误,导入未能开始' + '....................,'
        elif (line_data['standard_price'] <= 0)  or (line_data['standard_price'] is None):
            message += u'商品表第' + str(line + 1) + u'行商品采购价为空或零,导入未能开始' + ';....................,'
        if line_data['list_price'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品会员价错误,导入未能开始' + '....................,'
        elif (line_data['list_price'] <= 0) or (line_data['list_price'] is None):
            message += u'商品表第' + str(line + 1) + u'行商品会员价为空或零,导入未能开始' + ';....................,'
        if not line_data['default_code']:
            message += u'商品表第' + str(line + 1) + u'行商品无商品编码,导入未能开始' + '....................,'
        if not line_data['name']:
            message += u'商品表第' + str(line + 1) + u'行商品无商品名称,导入未能开始' + '....................,'
        if not line_data['categ']:
            message += u'商品表第' + str(line + 1) + u'行商品无商品类别,导入未能开始' + '....................,'
        if not line_data['uom']:
            message += u'商品表第' + str(line + 1) + u'行商品无计量单位,导入未能开始' + '....................,'
        if (line_data['list_price']
            and line_data['standard_price']
            and (line_data['list_price'] < line_data['standard_price'])):
            message += u'商品表第' + str(line + 1) + u'行商品会员价低于成本价,导入未能开始' + '....................,'
        if (line_data['list_price']
            and line_data['other_price'] 
            and line_data['list_price'] >= line_data['other_price']):
            message += u'商品表第' + str(line + 1) + u'行商品会员价高于市场价,导入未能开始' + '....................,'
        if not line_data['taxes']:
            message += u'商品表第' + str(line + 1) + u'行无销项税,导入未能开始' + '....................,'
        if not line_data['supplier_taxes']:
            message += u'商品表第' + str(line + 1) + u'行无进项税,导入未能开始' + '....................,'
        if not line_data['partner_ref']:
            message += u'商品表第' + str(line + 1) + u'行无供应商编号,导入未能开始' + '....................,'
        if not line_data['partner_name']:
            message += u'商品表第' + str(line + 1) + u'行无供应商名称,导入未能开始' + '....................,'
        if line_data['is_okkg'] == 'not':
            message += u'商品表第' + str(line + 1) + u'行快购状态未知,导入未能开始' + '....................,'
        if line_data['okkg_price'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品快购价错误,导入未能开始' + '....................,'
        return message

    def _get_from_product_table(self, product_table):
        result = []
        wrong_message = ''
        prows = product_table.nrows #行数
        for rx in range(1, prows): 
            line_data = {
                'default_code' : unicode(product_table.cell(rx, 0).value).strip(),
                'name' : unicode(product_table.cell(rx, 1).value).strip(),
                'categ' : unicode(product_table.cell(rx, 2).value).strip(),
                'variants' : unicode(product_table.cell(rx, 3).value).strip(),
                'min_qty' : self.number_to_float(product_table.cell(rx, 4).value) or 1, 
                'uom' : unicode(product_table.cell(rx, 5).value).strip(),
                'other_price' : self.number_to_float(product_table.cell(rx, 6).value),
                'standard_price':self.number_to_float(product_table.cell(rx, 7).value),
                'list_price' : self.number_to_float(product_table.cell(rx, 8).value),
                'brand_name': unicode(product_table.cell(rx, 9).value).strip(),
                'okgj_place': unicode(product_table.cell(rx, 10).value).strip(),
                'weight': self.number_to_float(product_table.cell(rx, 11).value),
                'okgj_mark': unicode(product_table.cell(rx, 12).value).strip(),
                'okgj_long': self.number_to_float(product_table.cell(rx, 13).value), 
                'okgj_wight': self.number_to_float(product_table.cell(rx, 14).value), 
                'okgj_height':self.number_to_float(product_table.cell(rx, 15).value), 
                'okgj_note': unicode(product_table.cell(rx, 16).value).strip(),   
                'life_time': self.number_to_float(product_table.cell(rx, 17).value), 
                'use_time': self.number_to_float(product_table.cell(rx, 18).value), 
                'alert_time': self.number_to_float(product_table.cell(rx, 19).value),
                'removal_time': self.number_to_float(product_table.cell(rx, 20).value),  
                'partner_ref' : unicode(product_table.cell(rx, 21).value).strip(),
                'partner_name':unicode(product_table.cell(rx, 22).value).strip(),
                'warehouse': unicode(product_table.cell(rx, 23).value).strip(),
                'taxes':unicode(product_table.cell(rx, 24).value).strip(),
                'supplier_taxes':unicode(product_table.cell(rx, 25).value).strip(),
                'is_okkg': self._get_okkg_state(product_table.cell(rx, 26).value),
                'okkg_price' : self.number_to_float(product_table.cell(rx, 27).value),
            }
            check_info = self._validate_product_data(rx, line_data)
            if check_info:
                wrong_message += check_info + '....................,'
                continue
            else:
                result.append(line_data)
        return (result, wrong_message)


    def _validate_bom_data(self, line, line_data):
        message = ''
        if not line_data['sub_default_code']:
            message += u'组合品表第' + str(line + 1) + u'行无明细商品编码,导入未能开始' + '....................,'
        if line_data['sub_qty'] is False:
            message += u'组合品表第' + str(line + 1) + u'行商品组合数量错误,导入未能开始' + '....................,'
        elif line_data['sub_qty'] is None:
            message += u'组合品表第' + str(line + 1) + u'行商品组合数量为空,导入未能开始' + '....................,'
        elif line_data['sub_qty'] <= 0 :
            message += u'组合品表第' + str(line + 1) + u'行商品组合数量为零,导入未能开始' + ';....................,'
        if line_data['default_code']:
            if not line_data['name']:
                message += u'组合品表第' + str(line + 1) + u'行商品无名称,导入未能开始' + '....................,'
            if not line_data['categ']:
                message += u'组合品表第' + str(line + 1) + u'行商品无类别,导入未能开始' + '....................,'
            if not line_data['uom']:
                message += u'组合品表第' + str(line + 1) + u'行商品无计量单位,导入未能开始' + '....................,'
            if line_data['other_price'] is False:
                message += u'商品表第' + str(line + 1) + u'行商品市场价错误,导入未能开始' + '....................,'
            elif line_data['other_price'] is None:
                message += u'商品表第' + str(line + 1) + u'行商品市场价为空,导入未能开始' + ';....................,'
            elif line_data['other_price'] <= 0:
                message += u'商品表第' + str(line + 1) + u'行商品市场价为零,导入未能开始' + ';....................,'
            if line_data['list_price'] is False:
                message += u'组合品表第' + str(line + 1) + u'行商品会员价错误,导入未能开始' + '....................,'
            if line_data['list_price'] is None:
                message += u'组合品表第' + str(line + 1) + u'行商品会员价为空,导入未能开始' + '....................,'
            elif line_data['list_price'] <= 0:
                message += u'组合品品表第' + str(line + 1) + u'行商品会员价为零,导入未能开始' + ';....................,'
            if (line_data['list_price']
                and line_data['other_price']
                and (line_data['list_price'] >= line_data['other_price'])):
                message += u'组合品表第' + str(line + 1) + u'行商品会员价高于市场价,导入未能开始' + '....................,'
            if line_data['is_okkg'] == 'not':
                message += u'组合品表第' + str(line + 1) + u'行快购状态未知,更新未能开始' + '....................,'
            if line_data['okkg_price'] is False:
                message += u'组合品表第' + str(line + 1) + u'行快购价错误,导入未能开始' + '....................,'
        return message

    def _prepare_subbom_data(self, cr, uid, sub_default_code, sub_qty, context):
        """
        准备子产品数据，传入字产品编码与子产品数量，返回子bom所需的数据
        """
        wrong_message = ''
        result = {}
        if not context:
            context = {}
        product_obj = self.pool.get('product.product')
        sub_product_id = product_obj.search(cr, uid, [
            ('default_code', '=', sub_default_code),
            ('is_group_product', '=', False),
            ], context=context)
        if not sub_product_id:
            wrong_message += u'商品:'+ str(sub_default_code) + u'不存在，组合品导入未能开始....................,'
            return (result, wrong_message)
        else:
            subproduct_data = product_obj.read(cr, uid, sub_product_id[0], ['name', 'uom_id'], context=context)
            result = {
                'name':subproduct_data['name'],
                'type':'normal',
                'product_id':sub_product_id[0],
                'product_qty':sub_qty,
                'product_uom':subproduct_data['uom_id'][0],
            }
        return (result, wrong_message)
                
    def _prepare_bom_import_data(self, cr, uid, bom_data, context):
        if not context: context = {}
        res = {}
        temp_key = ''
        pass_status = False
        wrong_message = ''
        product_obj = self.pool.get('product.product')
        for one_line in bom_data:
            if one_line['default_code']:
                main_product_id = product_obj.search(cr, uid, [
                    ('default_code', '=', one_line['default_code']),
                    ('is_group_product', '=', True),
                    ], context=context)
                if main_product_id:
                    temp_key = main_product_id[0]
                    if temp_key not in res:
                        pass_status = False
                        product_data = product_obj.read(cr, uid, main_product_id[0], ['name', 'uom_id'], context=context)
                        res[temp_key] = {
                            'name':product_data['name'],
                            'type':'phantom',
                            'product_id':main_product_id[0],
                            'product_qty':1,
                            'product_uom':product_data['uom_id'][0],
                            'bom_lines':[]
                        }
                else:
                    wrong_message += u'商品:'+ str(one_line['default_code']) + u'不存在，该商品所有组合关系均不会导入....................,'
                    pass_status = True
                    continue
            if one_line['sub_default_code'] and (not pass_status):
                if not temp_key:
                    wrong_message += u'组合关系找不到组合商品:'+ str(one_line['sub_default_code']) + u'该商品所有组合关系均不会导入....................,'
                    continue
                (subbom, temp_message) = self._prepare_subbom_data(cr, uid, one_line['sub_default_code'], one_line['sub_qty'] or 0, context)
                if temp_message:
                    wrong_message += temp_message
                if subbom:
                    res[temp_key]['bom_lines'].append((0, 0, subbom))
        return (res, wrong_message)

    def _get_from_bom_table(self, bom_table):
        result = []
        wrong_message = ''
        prows = bom_table.nrows #行数
        for rx in range(1,prows): 
            line_data = {
                'default_code' : unicode(bom_table.cell(rx, 0).value).strip(),
                'name' : unicode(bom_table.cell(rx, 1).value).strip(),
                'categ' : unicode(bom_table.cell(rx, 2).value).strip(),
                'variants' : unicode(bom_table.cell(rx, 3).value).strip(),
                'uom' : unicode(bom_table.cell(rx, 4).value).strip(),
                'other_price':self.number_to_float(bom_table.cell(rx, 5).value),
                'list_price':self.number_to_float(bom_table.cell(rx, 6).value),
                'sub_default_code': unicode(bom_table.cell(rx, 7).value).strip() ,
                'sub_qty':self.number_to_float(bom_table.cell(rx, 8).value),
                'is_okkg':self._get_okkg_state(bom_table.cell(rx, 9).value),
                'okkg_price' : self.number_to_float(bom_table.cell(rx, 10).value),
            }
            check_info = self._validate_bom_data(rx, line_data)
            if check_info:
                wrong_message += check_info + '....................,'
                continue
            else:
                result.append(line_data)
        return (result, wrong_message)

    def _verify_table(self, table_type, table):
        """
        强制检验模板是否正确
        """
        if table_type == 'import_product':
            if table.ncols < len(IMPORT_PRODUCT_TABLE):
                return False
            try:
                if (unicode(table.cell(0, 0).value).strip() == IMPORT_PRODUCT_TABLE[0] and
                    unicode(table.cell(0, 1).value).strip() == IMPORT_PRODUCT_TABLE[1] and
                    unicode(table.cell(0, 2).value).strip() == IMPORT_PRODUCT_TABLE[2] and
                    unicode(table.cell(0, 3).value).strip() == IMPORT_PRODUCT_TABLE[3] and
                    unicode(table.cell(0, 4).value).strip() == IMPORT_PRODUCT_TABLE[4] and
                    unicode(table.cell(0, 5).value).strip() == IMPORT_PRODUCT_TABLE[5] and
                    unicode(table.cell(0, 6).value).strip() == IMPORT_PRODUCT_TABLE[6] and
                    unicode(table.cell(0, 7).value).strip() == IMPORT_PRODUCT_TABLE[7] and
                    unicode(table.cell(0, 8).value).strip() == IMPORT_PRODUCT_TABLE[8] and
                    unicode(table.cell(0, 9).value).strip() == IMPORT_PRODUCT_TABLE[9] and
                    unicode(table.cell(0, 10).value).strip() == IMPORT_PRODUCT_TABLE[10] and
                    unicode(table.cell(0, 11).value).strip() == IMPORT_PRODUCT_TABLE[11] and
                    unicode(table.cell(0, 12).value).strip() == IMPORT_PRODUCT_TABLE[12] and
                    unicode(table.cell(0, 13).value).strip() == IMPORT_PRODUCT_TABLE[13] and
                    unicode(table.cell(0, 14).value).strip() == IMPORT_PRODUCT_TABLE[14] and
                    unicode(table.cell(0, 15).value).strip() == IMPORT_PRODUCT_TABLE[15] and
                    unicode(table.cell(0, 16).value).strip() == IMPORT_PRODUCT_TABLE[16] and
                    unicode(table.cell(0, 17).value).strip() == IMPORT_PRODUCT_TABLE[17] and
                    unicode(table.cell(0, 18).value).strip() == IMPORT_PRODUCT_TABLE[18] and
                    unicode(table.cell(0, 19).value).strip() == IMPORT_PRODUCT_TABLE[19] and
                    unicode(table.cell(0, 20).value).strip() == IMPORT_PRODUCT_TABLE[20] and
                    unicode(table.cell(0, 21).value).strip() == IMPORT_PRODUCT_TABLE[21] and
                    unicode(table.cell(0, 22).value).strip() == IMPORT_PRODUCT_TABLE[22] and
                    unicode(table.cell(0, 23).value).strip() == IMPORT_PRODUCT_TABLE[23] and
                    unicode(table.cell(0, 24).value).strip() == IMPORT_PRODUCT_TABLE[24] and
                    unicode(table.cell(0, 25).value).strip() == IMPORT_PRODUCT_TABLE[25] and
                    unicode(table.cell(0, 26).value).strip() == IMPORT_PRODUCT_TABLE[26] and
                    unicode(table.cell(0, 27).value).strip() == IMPORT_PRODUCT_TABLE[27]):
                    return True
            except:
                return False
        if table_type == 'import_bom':
            if table.ncols < len(IMPORT_BOM_TABLE):
                return False
            try:
                if (unicode(table.cell(0, 0).value).strip() == IMPORT_BOM_TABLE[0] and
                    unicode(table.cell(0, 1).value).strip() == IMPORT_BOM_TABLE[1] and
                    unicode(table.cell(0, 2).value).strip() == IMPORT_BOM_TABLE[2] and
                    unicode(table.cell(0, 3).value).strip() == IMPORT_BOM_TABLE[3] and
                    unicode(table.cell(0, 4).value).strip() == IMPORT_BOM_TABLE[4] and
                    unicode(table.cell(0, 5).value).strip() == IMPORT_BOM_TABLE[5] and
                    unicode(table.cell(0, 6).value).strip() == IMPORT_BOM_TABLE[6] and
                    unicode(table.cell(0, 7).value).strip() == IMPORT_BOM_TABLE[7] and
                    unicode(table.cell(0, 8).value).strip() == IMPORT_BOM_TABLE[8] and
                    unicode(table.cell(0, 9).value).strip() == IMPORT_BOM_TABLE[9] and
                    unicode(table.cell(0, 10).value).strip() == IMPORT_BOM_TABLE[10]):
                    return True
            except:
                return False
        if table_type == 'update_product':
            if table.ncols < len(UPDATE_PRODUCT_TABLE):
                return False
            try:
                if (unicode(table.cell(0, 0).value).strip() == UPDATE_PRODUCT_TABLE[0] and
                    unicode(table.cell(0, 1).value).strip() == UPDATE_PRODUCT_TABLE[1] and
                    unicode(table.cell(0, 2).value).strip() == UPDATE_PRODUCT_TABLE[2] and
                    unicode(table.cell(0, 3).value).strip() == UPDATE_PRODUCT_TABLE[3] and
                    unicode(table.cell(0, 4).value).strip() == UPDATE_PRODUCT_TABLE[4] and
                    unicode(table.cell(0, 5).value).strip() == UPDATE_PRODUCT_TABLE[5] and
                    unicode(table.cell(0, 6).value).strip() == UPDATE_PRODUCT_TABLE[6] and
                    unicode(table.cell(0, 7).value).strip() == UPDATE_PRODUCT_TABLE[7] and
                    unicode(table.cell(0, 8).value).strip() == UPDATE_PRODUCT_TABLE[8] and
                    unicode(table.cell(0, 9).value).strip() == UPDATE_PRODUCT_TABLE[9] and
                    unicode(table.cell(0, 10).value).strip() == UPDATE_PRODUCT_TABLE[10] and
                    unicode(table.cell(0, 11).value).strip() == UPDATE_PRODUCT_TABLE[11] and
                    unicode(table.cell(0, 12).value).strip() == UPDATE_PRODUCT_TABLE[12] and
                    unicode(table.cell(0, 13).value).strip() == UPDATE_PRODUCT_TABLE[13] and
                    unicode(table.cell(0, 14).value).strip() == UPDATE_PRODUCT_TABLE[14] and
                    unicode(table.cell(0, 15).value).strip() == UPDATE_PRODUCT_TABLE[15] and
                    unicode(table.cell(0, 16).value).strip() == UPDATE_PRODUCT_TABLE[16] and
                    unicode(table.cell(0, 17).value).strip() == UPDATE_PRODUCT_TABLE[17] and
                    unicode(table.cell(0, 18).value).strip() == UPDATE_PRODUCT_TABLE[18] and
                    unicode(table.cell(0, 19).value).strip() == UPDATE_PRODUCT_TABLE[19] and
                    unicode(table.cell(0, 20).value).strip() == UPDATE_PRODUCT_TABLE[20] and
                    unicode(table.cell(0, 21).value).strip() == UPDATE_PRODUCT_TABLE[21] and
                    unicode(table.cell(0, 22).value).strip() == UPDATE_PRODUCT_TABLE[22] and
                    unicode(table.cell(0, 23).value).strip() == UPDATE_PRODUCT_TABLE[23] and
                    unicode(table.cell(0, 24).value).strip() == UPDATE_PRODUCT_TABLE[24] and
                    unicode(table.cell(0, 25).value).strip() == UPDATE_PRODUCT_TABLE[25] and
                    unicode(table.cell(0, 26).value).strip() == UPDATE_PRODUCT_TABLE[26] and
                    unicode(table.cell(0, 27).value).strip() == UPDATE_PRODUCT_TABLE[27]):
                    return True
            except:
                    return False
        if table_type == 'update_bom':
            if table.ncols < len(UPDATE_BOM_TABLE):
                return False
            try:
                if (unicode(table.cell(0, 0).value).strip() == UPDATE_BOM_TABLE[0] and
                    unicode(table.cell(0, 1).value).strip() == UPDATE_BOM_TABLE[1] and
                    unicode(table.cell(0, 2).value).strip() == UPDATE_BOM_TABLE[2] and
                    unicode(table.cell(0, 3).value).strip() == UPDATE_BOM_TABLE[3] and
                    unicode(table.cell(0, 4).value).strip() == UPDATE_BOM_TABLE[4] and
                    unicode(table.cell(0, 5).value).strip() == UPDATE_BOM_TABLE[5] and
                    unicode(table.cell(0, 6).value).strip() == UPDATE_BOM_TABLE[6] and
                    unicode(table.cell(0, 7).value).strip() == UPDATE_BOM_TABLE[7]):
                    return True
            except:
                return False
        return False

    def _verify_table_format(self, table_type, table):
        """
        强制检验单元格类型是否为文本
        """
        prows = table.nrows #行数
        pcols = 0 #列数
        if table_type == 'import_product':
            pcols = len(IMPORT_PRODUCT_TABLE) - 1
        elif table_type == 'import_bom':
            pcols = len(IMPORT_BOM_TABLE) - 1
        elif table_type == 'update_product':
            pcols = len(UPDATE_PRODUCT_TABLE) - 1 
        elif table_type == 'update_bom':
            pcols = len(UPDATE_BOM_TABLE) - 1
        else:
            return False
        for rx in range(0, prows): 
            for rc in range(0, pcols):
                try:
                    if (table.cell(rx, rc).ctype != 1) and (table.cell(rx, rc).ctype != 0):
                        return False
                except:
                    return False
        return True

    def do_import(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context.update({'active_test':False})
        wrong_message = ''
        product_obj = self.pool.get('product.product')   
        product_supplierinfo_obj = self.pool.get('product.supplierinfo')
        partnerinfo_obj = self.pool.get('pricelist.partnerinfo')   
        bom_obj =  self.pool.get('mrp.bom') 
        if isinstance(ids, list):
            ids = ids[0]
        excel_file = self.browse(cr, uid, ids, context=context).excel   
        excel = xlrd.open_workbook(file_contents=base64.decodestring(excel_file))
        #table = data.sheet_by_name(u'Sheet1')#通过名称获取
        try:
            table_product = excel.sheet_by_index(0)
            table_bom = excel.sheet_by_index(1)
        except:
            raise osv.except_osv(_('Error!'), _(u'模板错误'))
        ##校验模板与基本格式
        if table_product:
            if not self._verify_table('import_product', table_product):
                raise osv.except_osv(_('Error!'), _(u'导入商品模板错误'))
            if not self._verify_table_format('import_product', table_product):
                raise osv.except_osv(_('Error!'), _(u'请将导入商品单元格格式全部设置为文本'))
        if table_bom:
            if not self._verify_table('import_bom', table_bom):
                raise osv.except_osv(_('Error!'), _(u'导入组合品模板错误!'))
            if not self._verify_table_format('import_bom', table_product):
                raise osv.except_osv(_('Error!'), _(u'请将导入组合品单元格格式全部设置为文本'))
        product_data = []
        if table_product:
            (product_data, wrong_message) = self._get_from_product_table(table_product)
        ##校验单品，分类，供应商
        for one_line in product_data:
            product_ids = product_obj.search(cr, uid, [('default_code', '=', one_line['default_code'])], context=context)  
            if product_ids:
                wrong_message += u'商品编码:' + str(one_line['default_code']) + u'已存在，导入未开始' + '....................,'
            categ_id = self._get_categ_id(cr, uid, one_line['categ'], context=context)
            if not categ_id:
                wrong_message += u'分类:' + one_line['categ'] + u'不存在，导入未开始' + '....................,'
            the_supplier_id = self._get_supplier_id(cr, uid, one_line['partner_name'], one_line['partner_ref'], context=context)
            if not the_supplier_id:
                wrong_message += u'供应商:' + one_line['partner_name'] + '(' + one_line['partner_ref'] + ')' + u'不存在，导入未开始' + '....................,'
            if one_line['warehouse']:
                the_warehouse_id = self._get_warehouse_id(cr, uid, one_line['warehouse'], context=context)
                if not the_warehouse_id:
                    wrong_message += u'物流中心:' + one_line['warehouse'] + u'不存在，导入未开始' + '....................,'
            taxes_id = self._get_tax_id(cr, uid, 'sale', one_line['taxes'], context=context)
            supplier_taxes_id = self._get_tax_id(cr, uid, 'purchase', one_line['supplier_taxes'], context=context)
            if (taxes_id == [(5)]):
                wrong_message += u'销项税' + one_line['taxes'] + u'不正确,导入未能开始' + '....................,'
            if (supplier_taxes_id == [(5)]):
                wrong_message += u'进项税' + one_line['supplier_taxes'] + u'不正确,导入未能开始' + '....................,'
        if wrong_message:
            raise osv.except_osv(_('Error!'), (wrong_message))
        ##开始导入商品
        new_product_count = 0
        for one_line in product_data:
            product_ids = product_obj.search(cr, uid, [('default_code', '=', one_line['default_code'])], context=context)  
            if product_ids:
                wrong_message += u'商品编码:' + str(one_line['default_code']) + u'已存在' + '....................,'
                continue
            one_line.update({
                'categ_id':self._get_categ_id(cr, uid, one_line['categ'], context=context),
                'uom_id':self._get_uom_id(cr, uid, one_line['uom'], context=context),
                'uom_po_id':self._get_uom_id(cr, uid, one_line['uom'], context=context),
                'brand_id': self._get_brand_id(cr, uid, one_line['brand_name'], context=context),
                'taxes_id': self._get_tax_id(cr, uid, 'sale', one_line['taxes'], context=context),
                'supplier_taxes_id': self._get_tax_id(cr, uid, 'purchase', one_line['supplier_taxes'], context=context),
            })
            if one_line['is_okkg'] == 'keep':
                del one_line['is_okkg']
            if not one_line['categ_id']:
                wrong_message += u'分类:' + one_line['categ'] + u'不存在，该行不会导入' + '....................,'
                continue
            the_supplier_id = self._get_supplier_id(cr, uid, one_line['partner_name'], one_line['partner_ref'], context=context)
            if not the_supplier_id:
                wrong_message += u'供应商:' + one_line['partner_name'] + '(' + one_line['partner_ref'] + ')' + u'不存在，该行不会导入' + '....................,'
                continue
            (one_line['track_incoming'], one_line['track_outgoing']) = self._update_tracking(one_line['use_time'])
            one_line.update(self._update_basic_method('table_product'))
            new_id = product_obj.create(cr, uid, one_line, context=context)
            new_prod_tmpl_id = product_obj.read(cr, uid, new_id, {'product_tmpl_id'}, context=context)['product_tmpl_id'][0]
            new_product_count += 1
            if one_line['warehouse']:
                the_warehouse_id = self._get_warehouse_id(cr, uid, one_line['warehouse'], context=context)
            else:
                the_warehouse_id = False
            suppinfo_id = product_supplierinfo_obj.create(cr, uid, {
                'name':the_supplier_id,
                'min_qty': 0,
                'warehouse_id':the_warehouse_id,
                'sequence':1,
                'product_id' : new_prod_tmpl_id,
                }, context=context)
            pricelist_id = partnerinfo_obj.create(cr, uid, {
                'suppinfo_id':suppinfo_id,
                'min_quantity':0,
                'price':one_line['standard_price'],
                }, context=context)
        cr.commit()
        ##导入组合商品，组合品单品校验
        bom_data = []
        if table_bom:
            (bom_data, temp_message) = self._get_from_bom_table(table_bom)
            wrong_message += temp_message
        ##校验组合品分类
        for one_line in bom_data:
            if one_line['default_code']:
                product_ids = product_obj.search(cr, uid, [('default_code', '=', one_line['default_code'])], context=context)  
                if product_ids:
                    wrong_message += u'商品编码:' + str(one_line['default_code']) + u'已存在，组合品导入未开始' + '....................,'
                categ_id = self._get_categ_id(cr, uid, one_line['categ'], context=context)
                if not categ_id:
                    wrong_message += u'分类:' + one_line['categ'] + u'不存在，组合品导入未开始' + '....................,'
            (subbom, temp_message) = self._prepare_subbom_data(cr, uid, one_line['sub_default_code'], one_line['sub_qty'] or 0, context)
            wrong_message += temp_message
        if wrong_message:
            raise osv.except_osv(_('Error!'), (wrong_message))
        for one_line in bom_data:
            if one_line['default_code']:
                product_ids = product_obj.search(cr, uid, [('default_code', '=', one_line['default_code'])], context=context)  
                if product_ids:
                    wrong_message += u'商品编码:' + str(one_line['default_code']) + u'已存在，该行不会导入' + '....................,'
                    continue
                one_line.update({
                    'categ_id':self._get_categ_id(cr, uid, one_line['categ'], context=context),
                    'uom_id':self._get_uom_id(cr, uid, one_line['uom'], context=context),
                    'uom_po_id':self._get_uom_id(cr, uid, one_line['uom'], context=context),
                })
                if not one_line['categ_id']:
                    wrong_message += u'分类:' + one_line['categ'] + u'不存在，该行不会导入' + '....................,'
                    continue
                if one_line['is_okkg'] == 'keep':
                    del one_line['is_okkg']
                one_line.update(self._update_basic_method('table_bom'))
                #组合品创建　
                new_id = product_obj.create(cr, uid, one_line, context=context)
                new_product_count += 1
        cr.commit()
        (bom_args, temp_message) = self._prepare_bom_import_data(cr, uid, bom_data, context)
        wrong_message += temp_message
        #导入组合关系
        new_bom_count = 0
        for one_bom in bom_args:
            has_id = bom_obj.search(cr, uid, [
                ('product_id', '=', one_bom),
                ('type', '=', 'phantom')
                ], context=context)
            if has_id:
                default_code = product_obj.read(cr, uid, one_bom, ['default_code'], context=context)['default_code']
                wrong_message += u'组合关系:' + str(default_code) + u'已存在，不会导入' + '....................,'
            else:
                if bom_args[one_bom]['bom_lines']:
                    bom_args_copy = copy.deepcopy(bom_args[one_bom])
                    del bom_args[one_bom]['bom_lines']
                    bom_id = bom_obj.create(cr, uid, bom_args[one_bom], context=context)
                    bom_obj.write(cr, uid, [bom_id], {'bom_lines':bom_args_copy['bom_lines']}, context=context)
                    new_bom_count += 1
                else:
                    wrong_message += u'组合品:' + str(default_code) + u'的组合明细为空，不会导入' + '....................,'
        cr.commit()
        context.update({'wrong_message':wrong_message, 'success_product':new_product_count, 'success_bom':new_bom_count})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'okgj.product.import.end',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    def _validate_product_update_data(self, cr, uid, line, line_data, context=None):
        if not context:
            context = {}
        product_obj = self.pool.get('product.product')
        price_line_obj = self.pool.get('okgj.base.price.change.line')
        message = ''
        if line_data['purchase_ok'] == 'not':
            message += u'商品表第' + str(line + 1) + u'行采购状态未知,更新未能开始' + '....................,'
        if not line_data['default_code']:
            message += u'商品表第' + str(line + 1) + u'行商品无商品编码' + u'更新未能开始....................,'
            return message
        product_ids = product_obj.search(cr, uid, [('default_code', '=', line_data['default_code'])], context=context)
        if product_ids:
            now_product_data = product_obj.read(cr, uid, product_ids[0], ['list_price', 'other_price', 'standard_price'], context=context)
        else:
            message += u'商品表第' + str(line + 1) + u'行商品未在系统中找到' + u'更新未能开始....................,'
            return message
        if line_data['new_partner_name'] and line_data['new_partner_ref']:
            supplier_id = self._get_supplier_id(cr, uid, line_data['new_partner_name'], line_data['new_partner_ref'], context=context)
            if not supplier_id:
                message += u'商品表第' + str(line + 1) + u'行供应商名称与供应商编码未在系统中找到' + u'更新未能开始....................,'
        if line_data['is_okkg'] == 'not':
            message += u'商品表第' + str(line + 1) + u'行快购状态未知,更新未能开始' + '....................,'
        if line_data['okkg_price'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品快购价错误,导入未能开始' + '....................,'
        if line_data['min_qty'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品最小包装数错误,更新未能开始' + '....................,'
        if line_data['weight'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品重量错误,更新未能开始' + '....................,'
        if line_data['okgj_long'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品长错误,更新未能开始' + '....................,'
        if line_data['okgj_wight'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品宽错误,更新未能开始' + '....................,'
        if line_data['okgj_height'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品高错误,更新未能开始' + '....................,'
        if line_data['life_time'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品商品报废时间错误,更新未能开始' + '....................,'
        if line_data['use_time'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品商品保质期错误,更新未能开始' + '....................,'
        if line_data['alert_time'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品禁止入库时间错误,更新未能开始' + '....................,'
        if line_data['removal_time'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品禁止出库时间错误,更新未能开始' + '....................,'
        if line_data['other_price'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品市场价错误,更新未能开始' + '....................,'
        elif ((line_data['other_price'] is not None) and
              line_data['other_price'] <= 0):
            message += u'商品表第' + str(line + 1) + u'行商品市场价为零,更新未能开始' + ';....................,'
        if line_data['standard_price'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品采购价错误,更新未能开始' + '....................,'
        elif ((line_data['standard_price'] is not None) and
              line_data['standard_price'] <= 0):
            message += u'商品表第' + str(line + 1) + u'行商品采购价为零,更新未能开始' + ';....................,'
        if line_data['list_price'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品会员价错误,更新未能开始' + '....................,'
        elif ((line_data['list_price'] is not None) and
              line_data['list_price'] <= 0):
            message += u'商品表第' + str(line + 1) + u'行商品会员价为零,更新未能开始' + ';....................,'
        if (line_data['other_price'] or
            line_data['standard_price'] or
            line_data['list_price']):
            if line_data['other_price']:
                o_price = line_data['other_price']
            else:
                o_price = now_product_data['other_price']
            if line_data['list_price']:
                l_price = line_data['list_price']
               # if not price_line_obj.verify_list_price(cr, uid, product_ids[0], line_data['list_price'], context=context):
               #     message += u'商品表第' + str(line + 1) + u'行商品所调会员价会导致该商品组合后销售价低于成本价,更新未能开始' + '....................,'
            else:
                l_price = now_product_data['list_price']
            if line_data['standard_price']:
                s_price = line_data['standard_price']
            else:
                s_price = now_product_data['standard_price']
            if  ((line_data['list_price'] or line_data['standard_price']) and l_price <= s_price):
                message += u'商品表第' + str(line + 1) + u'行商品会员价低于成本价或待更新的采购价,更新未能开始' + '....................,'
            if ((line_data['list_price'] or line_data['other_price']) and l_price >= o_price):
                message += u'商品表第' + str(line + 1) + u'行商品会员价高于市场价,更新未能开始' + '....................,'
        return message

    def _get_from_product_update_table(self, cr, uid, product_table):
        result = []
        wrong_message = ''
        prows = product_table.nrows 
        for rx in range(1, prows):
            line_data = {
                'default_code' : unicode(product_table.cell(rx, 0).value).strip(), 
                'name' : unicode(product_table.cell(rx, 1).value).strip(),
                'categ' : unicode(product_table.cell(rx, 2).value).strip(), 
                'variants' : unicode(product_table.cell(rx, 3).value).strip(), 
                'min_qty' : self.number_to_float(product_table.cell(rx, 4).value),
                'other_price' : self.number_to_float(product_table.cell(rx, 5).value),
                'list_price' : self.number_to_float(product_table.cell(rx, 6).value),
                'brand_name': unicode(product_table.cell(rx, 7).value).strip(),
                'okgj_place': unicode(product_table.cell(rx, 8).value).strip(),
                'weight': self.number_to_float(product_table.cell(rx, 9).value),
                'okgj_mark': unicode(product_table.cell(rx, 10).value).strip(),
                'okgj_long': self.number_to_float(product_table.cell(rx, 11).value), 
                'okgj_wight': self.number_to_float(product_table.cell(rx, 12).value), 
                'okgj_height':self.number_to_float(product_table.cell(rx, 13).value), 
                'okgj_note': unicode(product_table.cell(rx, 14).value).strip(),   
                'life_time': self.number_to_float(product_table.cell(rx, 15).value), 
                'use_time': self.number_to_float(product_table.cell(rx, 16).value), 
                'alert_time': self.number_to_float(product_table.cell(rx, 17).value),
                'removal_time': self.number_to_float(product_table.cell(rx, 18).value),  
                'purchase_ok':self._get_purchase_state(product_table.cell(rx, 19).value),
                'new_partner_ref' : unicode(product_table.cell(rx, 20).value).strip(),
                'new_partner_name':unicode(product_table.cell(rx, 21).value).strip(),
                'warehouse': unicode(product_table.cell(rx, 22).value).strip(),
                'standard_price':self.number_to_float(product_table.cell(rx, 23).value),
                'taxes':unicode(product_table.cell(rx, 24).value).strip(),
                'supplier_taxes':unicode(product_table.cell(rx, 25).value).strip(),
                'is_okkg':self._get_okkg_state(product_table.cell(rx, 26).value),
                'okkg_price':self.number_to_float(product_table.cell(rx, 27).value),
            }
            check_info = self._validate_product_update_data(cr, uid, rx, line_data)
            if check_info:
                wrong_message += check_info + '....................,'
                continue
            else:
                result.append(line_data)
        return (result, wrong_message)

    def _get_last_purchase_price(self, cr, uid, prod_tmpl_id, context):
        if not context:
            context = {}
        product_supplierinfo_obj = self.pool.get('product.supplierinfo')
        partnerinfo_obj = self.pool.get('pricelist.partnerinfo')
        last_supp_info_ids = product_supplierinfo_obj.search(cr, uid, [
            ('product_id', '=', prod_tmpl_id), ('sequence', '=', 1)
            ], context=context)
        if not last_supp_info_ids:
            last_supp_info_ids = product_supplierinfo_obj.search(cr, uid, [
                ('product_id', '=', prod_tmpl_id)], context=context)
        purchase_pricelist_ids = partnerinfo_obj.search(cr, uid, [('suppinfo_id', '=', last_supp_info_ids[0])], context=context)
        if purchase_pricelist_ids:
            purchase_price = partnerinfo_obj.read(cr, uid, purchase_pricelist_ids[0], ['price'], context)['price']
        else:
            purchase_price = 0
        return purchase_price

    def _update_supplier_info(self, cr, uid, one_product_data, context):
        product_obj = self.pool.get('product.product')
        product_supplierinfo_obj = self.pool.get('product.supplierinfo')
        partnerinfo_obj = self.pool.get('pricelist.partnerinfo')
        product_ids = product_obj.search(cr, uid, [('default_code', '=', one_product_data['default_code'])], context=context)
        prod_tmpl_id = product_obj.read(cr, uid, product_ids[0], {'product_tmpl_id'}, context=context)['product_tmpl_id'][0]
        last_all_supplier_info_ids = product_supplierinfo_obj.search(cr, uid, [('product_id', '=', prod_tmpl_id)], context=context)
        #更改供应商与价格
        if one_product_data['new_partner_name'] and one_product_data['new_partner_ref']:
            supplier_id = self._get_supplier_id(cr, uid, one_product_data['new_partner_name'], one_product_data['new_partner_ref'], context=context)
            now_supp_info_ids = product_supplierinfo_obj.search(cr, uid, [
                ('name', '=', supplier_id), ('product_id', '=', prod_tmpl_id)
                ], context=context)
            #现有供应商
            if now_supp_info_ids:
                if one_product_data['standard_price']:
                    purchase_pricelist_ids = partnerinfo_obj.search(cr, uid, [('suppinfo_id', '=', now_supp_info_ids[0])], context=context)
                    if purchase_pricelist_ids:
                        partnerinfo_obj.write(cr, uid, purchase_pricelist_ids[0], {'price':one_product_data['standard_price']}, context=context)
                    else:
                        partnerinfo_obj.create(cr, uid, {
                            'suppinfo_id':now_supp_info_ids[0],
                            'min_quantity':0,
                            'price':one_product_data['standard_price']}, context=context)
                product_supplierinfo_obj.write(cr, uid, last_all_supplier_info_ids, {'sequence':2}, context=context)
                if one_product_data['warehouse']:
                    the_warehouse_id = self._get_warehouse_id(cr, uid, one_product_data['warehouse'], context=context)
                    product_supplierinfo_obj.write(cr, uid, now_supp_info_ids, {'sequence':1, 'warehouse_id':the_warehouse_id}, context=context)
                else:
                    product_supplierinfo_obj.write(cr, uid, now_supp_info_ids, {'sequence':1}, context=context)
                return True
            #无供应商
            else:
                if one_product_data['standard_price']:
                    purchase_price = one_product_data['standard_price']
                else:
                    purchase_price = self._get_last_purchase_price(cr, uid, prod_tmpl_id, context)
                if one_product_data['warehouse']:
                    the_warehouse_id = self._get_warehouse_id(cr, uid, one_product_data['warehouse'], context=context)
                else:
                    the_warehouse_id = False
                suppinfo_id = product_supplierinfo_obj.create(cr, uid, {
                    'name':supplier_id,
                    'min_qty': 0,
                    'sequence':1,
                    'product_id' : prod_tmpl_id,
                    'warehouse_id':the_warehouse_id,
                }, context=context)
                pricelist_id = partnerinfo_obj.create(cr, uid, {
                    'suppinfo_id':suppinfo_id,
                    'min_quantity':0,
                    'price':purchase_price,
                    }, context=context)
                product_supplierinfo_obj.write(cr, uid, last_all_supplier_info_ids, {'sequence':2}, context=context)
                return True
        #仅改价
        else:
            if one_product_data['standard_price']:
                last_supp_info_ids = product_supplierinfo_obj.search(cr, uid, [
                    ('product_id', '=', prod_tmpl_id), ('sequence', '=', 1)
                    ], context=context)
                if last_supp_info_ids:
                    purchase_pricelist_ids = partnerinfo_obj.search(cr, uid, [('suppinfo_id', '=', last_supp_info_ids[0])], context=context)
                    if purchase_pricelist_ids:
                        partnerinfo_obj.write(cr, uid, purchase_pricelist_ids[0], {'price':one_product_data['standard_price']}, context=context)
                    else:
                        partnerinfo_obj.create(cr, uid, {
                            'suppinfo_id':last_supp_info_ids[0],
                            'min_quantity':0,
                            'price':one_product_data['standard_price']}, context=context)
            return True

    def _validate_bom_update_data(self, cr, uid, line, line_data, context=None):
        message = ''
        product_obj = self.pool.get('product.product')
        if not line_data['default_code']:
            message += u'更新商品表第' + str(line + 1) + u'行商品无商品编码' + u'更新未能开始....................,'
            return message
        product_ids = product_obj.search(cr, uid, [('default_code', '=', line_data['default_code'])], context=context)
        if product_ids:
            now_product_data = product_obj.read(cr, uid, product_ids[0], ['list_price', 'other_price', 'standard_price', 'okgj_cost_price'], context=context)
        else:
            message += u'商品表第' + str(line + 1) + u'行商品未在系统中找到' + u'更新未能开始....................,'
            return message
        if line_data['is_okkg'] == 'not':
            message += u'商品表第' + str(line + 1) + u'行快购状态未知,更新未能开始' + '....................,'
        if line_data['okkg_price'] is False:
            message += u'商品表第' + str(line + 1) + u'行商品快购价错误,导入未能开始' + '....................,'
        if (line_data['other_price'] or line_data['list_price']):
            if line_data['other_price']:
                o_price = line_data['other_price']
            else:
                o_price = now_product_data['other_price']
            if line_data['list_price']:
                l_price = line_data['list_price']
            else:
                l_price = now_product_data['list_price']
            s_price = now_product_data['okgj_cost_price']
            if  (line_data['list_price'] and l_price <= s_price):
                message += u'商品表第' + str(line + 1) + u'行商品会员价低于成本价或待更新的采购价,更新未能开始' + '....................,'
            if ((line_data['list_price'] or line_data['other_price']) and l_price >= o_price):
                message += u'商品表第' + str(line + 1) + u'行商品会员价高于市场价,更新未能开始' + '....................,'
        return message


    def _get_from_bom_update_table(self, cr, uid, bom_table, context=None):
        result = []
        wrong_message = ''
        prows = bom_table.nrows #行数
        for rx in range(1,prows): 
            line_data = {
                'default_code' : unicode(bom_table.cell(rx, 0).value).strip(),
                'name' : unicode(bom_table.cell(rx, 1).value).strip(),
                'categ' : unicode(bom_table.cell(rx, 2).value).strip(),
                'variants' : unicode(bom_table.cell(rx, 3).value).strip(),
                'other_price':self.number_to_float(bom_table.cell(rx, 4).value),
                'list_price':self.number_to_float(bom_table.cell(rx, 5).value),
                'is_okkg':self._get_okkg_state(bom_table.cell(rx, 6).value),
                'okkg_price' : self.number_to_float(bom_table.cell(rx, 7).value),
                ## 'sub_default_code': unicode(bom_table.cell(rx, 6).value).strip(),
                ## 'sub_qty':self.number_to_float(bom_table.cell(rx, 7).value),
            }
            check_info = self._validate_bom_update_data(cr, uid, rx, line_data, context=context)
            if check_info:
                wrong_message += check_info + '....................,'
                continue
            else:
                result.append(line_data)
        return (result, wrong_message)

    def _prepare_bom_update_data(self, cr, uid, bom_data, context=None):
        if not context: context = {}
        res = {}
        wrong_message = ''
        temp_bom = {}
        temp_main_bom_id = False
        continue_status = False
        product_obj = self.pool.get('product.product')
        bom_obj = self.pool.get('mrp.bom')
        for one_line in bom_data:
            if one_line['default_code']:
                product_ids = product_obj.search(cr, uid, [('default_code', '=', one_line['default_code'])], context=context)
                if not product_ids:
                    wrong_message += u'商品:'+ str(one_line['default_code']) + u'不存在，该商品所有组合关系均不会更新....................,'
                    continue_status = True
                    continue
        return (res, wrong_message)

   
    def do_update(self, cr, uid, ids, context=None):
        wrong_message = ''
        product_obj = self.pool.get('product.product')   
        product_supplierinfo_obj = self.pool.get('product.supplierinfo')
        partnerinfo_obj = self.pool.get('pricelist.partnerinfo')   
        bom_obj =  self.pool.get('mrp.bom') 
        if isinstance(ids, list):
            ids = ids[0]
        excel_file = self.browse(cr, uid, ids, context=context).excel   
        excel = xlrd.open_workbook(file_contents=base64.decodestring(excel_file))
        #table = data.sheet_by_name(u'Sheet1')#通过名称获取
        try:
            table_product = excel.sheet_by_index(0)
            table_bom = excel.sheet_by_index(1)                
        except:
            raise osv.except_osv(_('Error!'), _(u'模板错误'))
        product_data = []
        if table_product:
            if not self._verify_table('update_product', table_product):
                raise osv.except_osv(_('Error!'), _(u'更新商品模板错误'))
            if not self._verify_table_format('update_product', table_product):
                raise osv.except_osv(_('Error!'), _(u'请将更新商品单元格格式全部设置为文本'))
        if table_bom:
            if not self._verify_table('update_bom', table_bom):
                raise osv.except_osv(_('Error!'), _(u'更新组合品模板错误!'))
            if not self._verify_table_format('update_bom', table_product):
                raise osv.except_osv(_('Error!'), _(u'请将更新组合品单元格格式全部设置为文本'))
        if table_product:
            (product_data, wrong_message) = self._get_from_product_update_table(cr, uid, table_product)
        ##校验单品更新
        for one_line in product_data:
            product_ids = product_obj.search(cr, uid, [('default_code', '=', one_line['default_code'])], context=context)  
            if not product_ids:
                wrong_message += u'商品编码:' + one_line['default_code'] + u'不存在，更新未能开始' + '....................,'
            if one_line['categ']:
                categ_id = self._get_categ_id(cr, uid, one_line['categ'], context=context)
                if not categ_id:
                    wrong_message += u'商品分类:' + one_line['categ'] + u'不存在，更新未能开始' + '....................,'
            if one_line['new_partner_name'] or one_line['new_partner_ref']:
                the_supplier_id = self._get_supplier_id(cr, uid, one_line['new_partner_name'], one_line['new_partner_ref'], context=context)
                if not the_supplier_id:
                    wrong_message += u'供应商:' + one_line['new_partner_name'] + '(' + one_line['new_partner_ref'] + ')' + u'不存在，更新未能开始' + '....................,'
            if one_line['warehouse']:
                the_warehouse_id = self._get_warehouse_id(cr, uid, one_line['warehouse'], context=context)
                if not the_warehouse_id:
                    wrong_message += u'物流中心:' + one_line['warehouse'] + u'不存在，更新未能开始' + '....................,'
            if one_line['taxes']:
                taxes_id = self._get_tax_id_update(cr, uid, 'sale', one_line['taxes'], context=context)
                if taxes_id == [(5)]:
                    wrong_message += u'销项税:' + one_line['taxes'] + u'不存在，更新未能开始' + '....................,'
            if one_line['supplier_taxes']:
                supplier_taxes_id = self._get_tax_id_update(cr, uid, 'purchase', one_line['supplier_taxes'], context=context)
                if supplier_taxes_id == [(5)]:
                    wrong_message += u'进项税:' + one_line['supplier_taxes'] + u'不存在，更新未能开始' + '....................,'
        if wrong_message:
            raise osv.except_osv(_('Error!'), (wrong_message))

        #开始更新商品
        write_product_count = 0
        for one_line in product_data:
            product_ids = product_obj.search(cr, uid, [('default_code', '=', one_line['default_code'])], context=context)  
            if not product_ids:
                wrong_message += u'商品编码:' + one_line['default_code'] + u'不存在，不会更新' + '....................,'
                continue
            if one_line['purchase_ok'] == 'keep' or one_line['purchase_ok'] == 'not':
                del one_line['purchase_ok']
            if one_line['categ']:
                one_line.update({'categ_id':self._get_categ_id(cr, uid, one_line['categ'], context=context)})
            if one_line['brand_name']:
                one_line.update({'brand_id':self._get_brand_id(cr, uid, one_line['brand_name'], context=context)})
            if one_line['taxes']:
                one_line.update({'taxes_id':self._get_tax_id_update(cr, uid, 'sale', one_line['taxes'], context=context)})
            if one_line['supplier_taxes']:
                one_line.update({'supplier_taxes_id':self._get_tax_id_update(cr, uid, 'purchase', one_line['supplier_taxes'], context=context)})
            one_line_copy = copy.deepcopy(one_line)
            if not one_line_copy['name']:
                del one_line_copy['name']
            if not one_line_copy['variants']:
                del one_line_copy['variants']
            if not one_line_copy['okgj_place']:
                del one_line_copy['okgj_place']
            if not one_line_copy['okgj_mark']:
                del one_line_copy['okgj_mark']
            if not one_line_copy['okgj_note']:
                del one_line_copy['okgj_note']
            del one_line_copy['categ']
            del one_line_copy['brand_name']
            del one_line_copy['new_partner_name']
            del one_line_copy['new_partner_ref']
            del one_line_copy['warehouse']
            del one_line_copy['standard_price']
            if (one_line_copy['list_price'] is None or
                one_line_copy['list_price'] is False):
                del one_line_copy['list_price']
            if (one_line_copy['other_price'] is None or
                one_line_copy['other_price'] is False):
                del one_line_copy['other_price']
            if (one_line_copy['min_qty'] is None or
                one_line_copy['min_qty'] is False):
                del one_line_copy['min_qty']
            if (one_line_copy['weight'] is None or
                one_line_copy['weight'] is False):
                del one_line_copy['weight']
            if (one_line_copy['okgj_long'] is None or
                one_line_copy['okgj_long'] is False):
                del one_line_copy['okgj_long']
            if (one_line_copy['okgj_height'] is None or
                one_line_copy['okgj_height'] is False):
                del one_line_copy['okgj_height']
            if (one_line_copy['okgj_wight'] is None or
                one_line_copy['okgj_wight'] is False):
                del one_line_copy['okgj_wight']
            if (one_line_copy['life_time'] is None or
                one_line_copy['life_time'] is False):
                del one_line_copy['life_time']
            if (one_line_copy['use_time'] is None or
                one_line_copy['use_time'] is False):
                del one_line_copy['use_time']
            if (one_line_copy['alert_time'] is None or
                one_line_copy['alert_time'] is False):
                del one_line_copy['alert_time']
            if (one_line_copy['removal_time'] is None or
                one_line_copy['removal_time'] is False):
                del one_line_copy['removal_time']
            if one_line_copy['is_okkg'] == 'keep':
                del one_line_copy['is_okkg']
            if (one_line_copy['okkg_price'] is None or
                one_line_copy['okkg_price'] is False):
                del one_line_copy['okkg_price']
            del one_line_copy['taxes']
            del one_line_copy['supplier_taxes']
            product_obj.write(cr, uid, [product_ids[0]], one_line_copy, context=context)
            if (one_line['new_partner_name'] and one_line['new_partner_ref']) or one_line['standard_price']:
                self._update_supplier_info(cr, uid, one_line, context=context)
            write_product_count += 1
        cr.commit()
        #组合品更新
        bom_data = []
        temp_message = ''
        if table_bom:
            (bom_data, temp_message) = self._get_from_bom_update_table(cr, uid, table_bom, context=context)
            wrong_message += temp_message
        ##校验组合品分类
        for one_line in bom_data:
            if one_line['default_code']:
                product_ids = product_obj.search(cr, uid, [('default_code', '=', one_line['default_code'])], context=context)  
                if not product_ids:
                    wrong_message += u'商品编码:' + str(one_line['default_code']) + u'不存在，组合品更新未能开始' + '....................,'
                if one_line['categ']:
                    categ_id = self._get_categ_id(cr, uid, one_line['categ'], context=context)
                    if not categ_id:
                        wrong_message += u'分类:' + one_line['categ'] + u'不存在，组合品更新未能开始' + '....................,'
        if wrong_message:
            raise osv.except_osv(_('Error!'), (wrong_message))
        ##开始更新组合品
        for one_line in bom_data:
            product_ids = product_obj.search(cr, uid, [('default_code', '=', one_line['default_code'])], context=context)  
            if not product_ids:
                wrong_message += u'商品编码:' + one_line['default_code'] + u'不存在' + '....................,'
                continue
            if one_line['categ']:
                one_line.update({'categ_id':self._get_categ_id(cr, uid, one_line['categ'], context=context)})
            one_line_copy = copy.deepcopy(one_line)
            del one_line_copy['categ']
            del one_line_copy['name']
            if not one_line_copy['variants']:
                del one_line_copy['variants']
            if (one_line_copy['list_price'] is None or
                one_line_copy['list_price'] is False):
                del one_line_copy['list_price']
            if (one_line_copy['other_price'] is None or
                one_line_copy['other_price'] is False):
                del one_line_copy['other_price']
            if one_line_copy['is_okkg'] == 'keep':
                del one_line_copy['is_okkg']
            if (one_line_copy['okkg_price'] is None or
                one_line_copy['okkg_price'] is False):
                del one_line_copy['okkg_price']
            if (one_line['name'] or
                one_line['categ'] or
                one_line['variants'] or
                one_line['other_price'] or
                one_line['list_price'] or
                (one_line.get('is_okkg') is not None) or
                one_line['okkg_price']):
                product_obj.write(cr, uid, [product_ids[0]], one_line_copy, context=context)
            write_product_count += 1

        ## (bom_args, temp_message) = self._prepare_bom_update_data(cr, uid, bom_data, context=context)
        ## wrong_message += temp_message
        write_bom_count = 0
        ## for one_bom_id in bom_args:
        ##     bom_obj.write(cr, uid, one_bom_id, bom_args[one_bom_id], context=context)
        ##     write_bom_count += 1
        cr.commit()
        context.update({'wrong_message':wrong_message, 'success_product':write_product_count, 'success_bom':write_bom_count})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'okgj.product.import.end',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

okgj_product_import()


class okgj_product_import_end(osv.osv_memory):
    _name = "okgj.product.import.end"
    _columns = {
        'success_product':fields.integer(u'商品成功条数（含组合品）', readonly=True),
        'success_bom':fields.integer(u'组合关系成功条数', readonly=True),
        'note': fields.text(u'失败', readonly=True),                                                              
    }

    def default_get(self, cr, uid, fields, context=None):
        if not context:
            context = {}
        res = super(okgj_product_import_end, self).default_get(cr, uid, fields, context=context)
        res.update({
            'success_product': context.get('success_product', 0),
            'success_bom': context.get('success_bom', 0),
            'note': context.get('wrong_message', '')
        })
        return res
okgj_product_import_end()



                   
                        


