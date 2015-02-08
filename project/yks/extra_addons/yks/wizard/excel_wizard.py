# -*- coding: utf-8 -*-
##############################################################################

import xlrd
import base64
from openerp.osv import  osv, fields
import logging
_logger = logging.getLogger(__name__)

Excel_model = {
    'complex_product': {'title': ['name', 'complex_sku', 'sub_sku', 'qty'], 'string': u'组合品'},
    'product':{'title':['name','sku','brand','category','replace'],'string':u'产品'},
    'orderpoint':{'title':['sku','name','product_min_qty'],'string':u'库存预警'}
}





class excel_wizard(osv.osv):
    _name = 'excel.wizard'
    _columns = {
        'name': fields.char('Name', size=20,),
        'file': fields.binary(u'Excel文件', filters='*.xls｜*.csv'),
        'model': fields.selection([(k, Excel_model[k]['string']) for k in Excel_model], u'导入内容'),
        'replace':fields.selection([('update',u'更新'),('create',u'新建')],u'导入类型'),
    }
    _defaults = {
        'replace':'create',
    }
    def parse_title_data(filename=None, file_contents=None):
        """
        parse excel, first line is title
        @return,  {'title':[],'data': [t1:v1, t2:v2])
        """
        res = {}
        try:
            book = xlrd.open_workbook(filename=filename, file_contents=file_contents)
            sheet = book.sheet_by_index(0)
            titles = sheet.row_values(1)
            datas = []
            for i in range(2, sheet.nrows):
                dic = dict(zip(titles, sheet.row_values(i)))
                dic.update({'row_nu': i + 1})
                datas.append(dic)
            res.update({'title': titles, 'data': datas})
        except Exception, e:
            _logger.info('Error,excel parse %s' % e)
        return res     
    def apply(self, cr, uid, ids, context=None):
        wizard = self.browse(cr, uid, ids[0], context=None)
        title_data = self.parse_title_data(file_contents=base64.decodestring(wizard.file))
        
        if wizard.model == 'complex_product':
            self.apply_check(cr, uid, title_data, wizard.model, context=context)
            res = self.create_complex_product(cr, uid, title_data, context=context)
        elif wizard.model =='product':
            res = self.create_product(cr,uid,title_data, wizard.replace,context)
        elif wizard.model =='orderpoint':
            res = self.create_orderpoint(cr,uid,title_data,context)
        else:
            pass
        return res
    def create_orderpoint(self,cr,uid,title_data,context=None):
        """库存预警"""
        for title in Excel_model['orderpoint']['title']:
            if title not in title_data['title']:
                raise osv.except_osv("Error", "Title %s not found" % title)
        res_ids=[]
        orderpoint_obj= self.pool.get('stock.warehouse.orderpoint')
        product_obj = self.pool.get('product.product')
        warehouse_obj = self.pool.get('stock.warehouse')
        mod_obj = self.pool.get('ir.model.data')
        bad_sku=''
        for info in title_data['data']:
            sku = str(info.get('sku')).strip()
            product_id = product_obj.search(cr,uid,[('default_code','=',sku)])
            if not product_id:
                bad_sku +="%s,\t"%info['row_nu']
        if bad_sku:
            raise osv.except_osv(u"错误", u"下列行的SKU不存在,请先添加\n%s" % bad_sku)
                
        for info in title_data['data']:
            sku = str(info.get('sku')).strip()
            #warehouse = str(info.get('warehouse')).strip()
            product_min_qty = info.get('product_min_qty')
            #warehouse_id = warehouse_obj.search(cr,uid,[('name','=',warehouse)])[0]
            ware_obj = warehouse_obj.browse(cr,uid,1,context)
            #if not warehouse_id:
            #   raise osv.except_osv(u"错误", u"%s不存在，请核对或者添加" % warehouse)
            
            product_id = product_obj.search(cr,uid,[('default_code','=',sku)])
            if  not product_id:
                raise osv.except_osv(u"错误", u"%s不存在，请先添加" % sku)
            else:
                product_id =product_id[0]
            vals ={
                'product_min_qty':product_min_qty,
                'product_id':product_id,
                'warehouse_id':1,#warehouse_id,
                'location_id':ware_obj.lot_stock_id.id,
                'product_max_qty':product_min_qty,
                'product_uom':1,
            }
            exist_sku_ids = orderpoint_obj.search(cr,uid,[('product_id','=',product_id)])
            if exist_sku_ids:
                orderpoint_obj.write(cr,uid,exist_sku_ids,vals)
                res_ids.append(exist_sku_ids)
            else:
                id = orderpoint_obj.create(cr,uid,vals,context)
                res_ids.append(id)
                
        return {
            'name': u'库存预警',
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'stock.warehouse.orderpoint',
            "domain": [('id', 'in', res_ids)],
            'type': 'ir.actions.act_window',
        }
                
            
        
    def create_product(self,cr,uid,title_data,replace,context=None):
        """导入新产品"""  
        for title in Excel_model[model]['title']:
            if title not in title_data['title']:
                raise osv.except_osv("Error", "Title %s not found" % title)
        res_ids = [] 
        product_obj = self.pool.get('product.product')
        category_obj = self.pool.get('product.category')
        brand_obj = self.pool.get('product.brand')
        place_obj = self.pool.get('res.country')
        categ_id = None
        for info in title_data['data']:
            sku = info.get('sku')
            name = info.get('name')
            if name and sku:
                vals={'default_code' :str(sku).strip(),'name':str(name).strip()}
            else:
                raise osv.except_osv(u'错误！', u'商品SKU和名称必须存在')
            vals.update({
                'en_name':info.get('en_name',''),
                'warranty':info.get('warranty',0.0),
                'formula':info.get('formula',''),
                'suitable_crowd':info.get(' ',''),
                'hs_code':info.get('hs_code',''),
                'ean13':info.get('ean13',''),
            })
            category = info.get('category')
            brand = info.get('brand')
            place=info.get('place_production','')
            sale_ok = info.get('sale_ok',False) 
            purchase_ok = info.get('purchase_ok',False)
            if purchase_ok:
                purchase_ok = int(purchase_ok) and True 
            else:
                purchase_ok = False
            if sale_ok:
                sale_ok = int(sale_ok) and True
            else:
                sale_ok =False
            vals.update({'sale_ok':sale_ok,'purchase_ok':purchase_ok})
            if place:
                place = str(place).strip()
                place_id = place_obj.search(cr,uid,[('name','=',place)])
                if place_id:
                    vals.update({'place_production':place_id[0]})
                else:
                    raise osv.except_osv(u'错误！', u'%s原产地在系统中不存在，请添加！'%place)
            else:
                raise osv.except_osv(u'错误！', u'excel文件中有商品没有原产地信息，请添加！')
            if brand:
                brand = str(brand).strip()
                brand_id = brand_obj.search(cr,uid,[('name','=',brand)])
                if brand_id:
                    vals.update({'brand_id':brand_id[0]})
                else:
                    raise osv.except_osv(u'错误！', u'%s品牌在系统中不存在，请添加！'%brand)
            else:
                raise osv.except_osv(u'错误！', u'excel文件中有商品没有品牌信息，请添加！')
            if category:
                category = str(category).strip()
                categ_id =  category_obj.search(cr,uid,[('name','=',category)])
                if  categ_id:
                    vals.update({'categ_id':categ_id[0]})
                else:
                    raise osv.except_osv(u'错误！', u'%s类别在系统中不存在，请添加！'%category)
            else:
                raise osv.except_osv(u'错误！', u'excel文件中有商品没有类别信息，请添加！')
            exist_sku_ids = product_obj.search(cr,uid,[('default_code','=',vals['default_code'])])
            if exist_sku_ids and replace=='update':
                product_obj.write(cr,uid,exist_sku_ids,vals)
                res_ids.append(exist_sku_ids)
            elif not exist_sku_ids :
               id =   product_obj.create(cr,uid,vals,context)
               if id:
                   res_ids.append(id)
            else:
                raise osv.except_osv(u'错误！', u'SKU %s在系统中已经存在，无法新建'%vals['default_code'])
        return {
            'name': u'新导入产品',
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'product.product',
            "domain": [('id', 'in', res_ids)],
            'type': 'ir.actions.act_window',
        }
        
            
        
    def create_complex_product(self, cr, uid, title_data, context=None):
        product_obj = self.pool.get('product.product')
        bom_boj = self.pool.get('mrp.bom')
        uom_id = 1
        bom_ids = []
        
        #dic {sku: ['sku_name',  [(sub_sku, qty),()]]}.
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
            bom_ids.append(bom_id)
            
        return {
            'name': u'组合品',
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'mrp.bom',
            "domain": [('id', 'in', bom_ids)],
            'type': 'ir.actions.act_window',
        }
           
    def apply_check(self, cr, uid, title_data, model, context=None):
        for title in Excel_model[model]['title']:
            if title not in title_data['title']:
                raise osv.except_osv("Error", "Title %s not found" % title)
        for line in title_data['data']:
            if (not line.get('sub_sku')) or (not line.get('qty')):
                raise osv.except_osv("Error", "Not found sub_sku,qty at Line %s" % line['row_nu'])

        return True

excel_wizard()

##############################################################################
