# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import osv, fields
import time, xlrd, base64
from openerp.tools.translate import _
import sys

class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'okgj_long': fields.float(u'长'),
        'okgj_wight': fields.float(u'宽'), 
        'okgj_height': fields.float(u'高'), 
        'okgj_note': fields.char(u'备注', size=256), 
        'okgj_place': fields.char(u'产地', size=64),   
        'okgj_mark': fields.char(u'标记(产品状态)', size=64),                                    
    }
product_product()    
          
class okgj_product_import(osv.osv_memory):
    _name = "okgj.product.import"
    _columns = {
        'excel': fields.binary(u'excel文件', filters='*.xls'),                                                              
    }

    def import_bill(self, cr, uid, ids, context=None):
        for excel_data in self.browse(cr, uid, ids):   
            if not excel_data.excel: 
                raise osv.except_osv(_(u'警告!'), _(u'请上传表格!'))          
            excel = xlrd.open_workbook(file_contents=base64.decodestring(excel_data.excel))                
            product_obj = self.pool.get('product.product')   
            categ_obj = self.pool.get('product.category')  
            uom_obj = self.pool.get('product.uom')     
            uom_categ_obj = self.pool.get('product.uom.categ') 
            product_supplierinfo_obj = self.pool.get('product.supplierinfo')           
            partnerinfo_obj = self.pool.get('pricelist.partnerinfo')   
            res_partner_obj =  self.pool.get('res.partner')
            mrp_bom_obj =  self.pool.get('mrp.bom') 
            brand_obj =  self.pool.get('okgj.product.brand')  
            stock_obj = self.pool.get('stock.move')   
            stock_location_obj = self.pool.get('stock.location')   
            lot_obj = self.pool.get('stock.production.lot') 
            warehouse_obj = self.pool.get('stock.warehouse')                                                                                                 
            table_product = excel.sheet_by_index(0)
            table_bom = excel.sheet_by_index(1)
            table_bom_line = excel.sheet_by_index(2) 
            table_stock = excel.sheet_by_index(3)                           
            if table_product:
                prows = table_product.nrows #行数
                count = 200
                for rx in range(1,prows): 
                    local_res = {} 
                    product_cell_0 = table_product.cell(rx, 0).value 
                    product_cell_4 = table_product.cell(rx, 4).value                   
                    if not product_cell_0:
                        raise osv.except_osv(_(u'警告!'), _(u'单品表-编号-第%s行为空!') % (rx+1))                            
                    else:
                        if isinstance(product_cell_0, float):                         
                            local_res['default_code'] = int(product_cell_0)                        
                        else:                           
                            local_res['default_code'] = str(product_cell_0)   
 
                    local_res['name'] = table_product.cell(rx, 1).value
                    categ_ids = categ_obj.search(cr, uid, [('name', '=', table_product.cell(rx, 2).value)], context=context)
                    if not categ_ids:
                        categ_create_id = categ_obj.create(cr, uid, {'name':table_product.cell(rx, 2).value})
                        local_res['categ_id'] = int(categ_create_id)           
                    else:
                        local_res['categ_id'] = categ_obj.browse(cr, uid, categ_ids)[0].id
                    local_res['variants'] = table_product.cell(rx, 3).value
                    if not isinstance(product_cell_4, float):                         
                        raise osv.except_osv(_(u'警告!'), _(u'单品表-箱规-第%s行非数字格式!') % (rx+1))   
                    else:                    
                        local_res['min_qty'] = int(product_cell_4)                    
                    uom_ids = uom_obj.search(cr, uid, [('name', '=', table_product.cell(rx, 5).value)], context=context)  
                    if not uom_ids:
                        uom_categ_ids = uom_categ_obj.search(cr, uid, [('name', '=', 'Unit')], context=context)                      
                        if not uom_categ_ids:
                            uom_categ_id = uom_categ_obj.create(cr, uid, {'name':'Unit'})                             
                        else:
                            uom_categ_id = uom_categ_ids[0]            
                        uom_id = uom_obj.create(cr, uid, {'name':table_product.cell(rx, 5).value, 'category_id':uom_categ_id, 'factor':1, 'factor_inv':1,'rounding':1})      
                        local_res['uom_id'] = int(uom_id)           
                        local_res['uom_po_id'] = int(uom_id)             
                    else:
                        local_res['uom_id'] = uom_obj.browse(cr, uid, uom_ids)[0].id   
                        local_res['uom_po_id'] = uom_obj.browse(cr, uid, uom_ids)[0].id 
                    local_res['other_price'] = table_product.cell(rx, 6).value   
                    local_res['standard_price'] = table_product.cell(rx, 7).value 
                    local_res['list_price'] = table_product.cell(rx, 8).value  
                    brand_ids = brand_obj.search(cr, uid, [('name', '=', table_product.cell(rx, 9).value)], context=context)                
                    if not brand_ids:
                        brand_id = brand_obj.create(cr, uid, {'name':table_product.cell(rx, 9).value})
                        local_res['brand_id'] = int(brand_id)           
                    else:
                        local_res['brand_id'] = brand_obj.browse(cr, uid, brand_ids)[0].id                         
                    local_res['okgj_place'] = table_product.cell(rx, 10).value  
                    local_res['ean13'] = table_product.cell(rx, 11).value  
                    local_res['weight'] = table_product.cell(rx, 12).value
                    local_res['okgj_mark'] = table_product.cell(rx, 13).value  
                    local_res['okgj_long'] = table_product.cell(rx, 14).value 
                    local_res['okgj_wight'] = table_product.cell(rx, 15).value 
                    local_res['okgj_height'] = table_product.cell(rx, 16).value 
                    local_res['okgj_note'] = table_product.cell(rx, 17).value   
                    local_res['life_time'] = table_product.cell(rx, 18).value 
                    local_res['use_time'] = table_product.cell(rx, 19).value 
                    if local_res['use_time']:
                        local_res['track_incoming'] = True
                        local_res['track_outgoing'] = True
                    local_res['alert_time'] = table_product.cell(rx, 20).value 
                    local_res['removal_time'] = table_product.cell(rx, 21).value  
                    local_res['cost_method'] = 'average'
                    local_res['type'] = 'product'
                    local_res['supply_method'] = 'buy'
                    product_ids = product_obj.search(cr, uid, [('default_code', '=', str(local_res['default_code']))], context=context)                                                         
                    if not product_ids:                                                                     
                        product_id = product_obj.create(cr, uid, local_res, context=context)
                    else:
                        product_id = product_ids[0]   
                    res_partner_id = res_partner_obj.search(cr, uid, [('name', '=', table_product.cell(rx, 23).value)], context=context)                                                                 
                    if not res_partner_id:
                        res_partner_id = res_partner_obj.create(cr,uid,{'name':table_product.cell(rx, 23).value,'ref':table_product.cell(rx, 22).value,'supplier':True,'is_company':True,'customer':False})    
                        product_supplierinfo_id = product_supplierinfo_obj.create(cr, uid, {'name':int(res_partner_id),'product_id':product_id, 'min_qty':table_product.cell(rx, 24).value})                      
                        partnerinfo_id = partnerinfo_obj.create(cr,uid,{'price':table_product.cell(rx, 7).value,'suppinfo_id':product_supplierinfo_id,'min_quantity':table_product.cell(rx, 24).value})                                                                                    
                    else:
                        supplierinfo_id = product_supplierinfo_obj.search(cr, uid, [('product_id', '=', product_id)], context=context)
                        if not supplierinfo_id:
                            product_supplierinfo_id = product_supplierinfo_obj.create(cr, uid, {'name':res_partner_id[0],'product_id':product_id, 'min_qty':table_product.cell(rx, 24).value})                      
                            partnerinfo_id = partnerinfo_obj.create(cr,uid,{'price':table_product.cell(rx, 7).value,'suppinfo_id':product_supplierinfo_id,'min_quantity':table_product.cell(rx, 24).value})
                    count -= 1
                    if count == 0:
                        cr.commit()
                        count = 200
            if table_bom:        
                bbrows = table_bom.nrows #行数
                count = 200
                for rx in range(1,bbrows): 
                    bom_res = {}  
                    if not table_bom.cell(rx, 0).value:
                        raise osv.except_osv(_(u'警告!'), _(u'组合品表-组合装编号-第%s行为空!') % (rx+1))    
                    else: 
                        if isinstance(table_bom.cell(rx, 0).value, float):  
                            default_code = int(table_bom.cell(rx, 0).value)
                        else:
                            default_code = str(table_bom.cell(rx, 0).value)                                                                               
                    bom_res['name'] = table_bom.cell(rx, 1).value   
                    categ_ids = categ_obj.search(cr, uid, [('name', '=', table_bom.cell(rx, 3).value)], context=context) 
                    uom_ids = uom_obj.search(cr, uid, [('name', '=', table_bom.cell(rx, 4).value)], context=context)                               
                    if not uom_ids:
                        uom_categ_ids = uom_categ_obj.search(cr, uid, [('name', '=', 'Unit')], context=context) 
                        if not uom_categ_ids:
                            uom_categ_id = uom_categ_obj.create(cr, uid, {'name':'Unit'})                              
                        else:
                            uom_categ_id = uom_categ_ids[0]                                                 
                        uom_id = uom_obj.create(cr, uid, {'name':table_bom.cell(rx,4).value, 'category_id':uom_categ_id, 'factor':1, 'factor_inv':1,'rounding':1})      
                        bom_res['product_uom'] = int(uom_id)                       
                    else:
                        bom_res['product_uom'] = int(uom_obj.browse(cr, uid, uom_ids)[0].id)                  
                    if not categ_ids:
                        categ_create_id = categ_obj.create(cr, uid, {'name':table_bom.cell(rx, 3).value})
                        bom_categ_id = int(categ_create_id)
                    else: 
                        bom_categ_id = categ_obj.browse(cr, uid, categ_ids)[0].id    
                    bom_product_ids = product_obj.search(cr, uid, [('default_code', '=', str(default_code))], context=context)                                                                                   
                    if not bom_product_ids:
                        bom_product_ids = product_obj.create(cr, uid, {
                            'name':table_bom.cell(rx, 1).value, 
                            'default_code': str(default_code),
                            'categ_id':bom_categ_id,
                            'variants':table_bom.cell(rx, 2).value,
                            'uom_id' : bom_res['product_uom'],
                            'uom_po_id': bom_res['product_uom'],
                            'other_price': table_bom.cell(rx, 5).value,
                            'list_price' : table_bom.cell(rx, 6).value,
                            'purchase_ok': False,
                            'is_group_product':True,
                            'supply_method' : 'produce'
                            })
                        bom_res['product_id'] = int(bom_product_ids)            
                    else:
                        bom_res['product_id'] = product_obj.browse(cr, uid, bom_product_ids)[0].id
                    bom_res['type'] = 'phantom' 
                    bom_only = mrp_bom_obj.search(cr, uid, [('product_id', '=', bom_res['product_id'])], context=context)                                                                                  
                    if not bom_only:                                                                                                                                             
                        bom_id = mrp_bom_obj.create(cr, uid, bom_res, context=context) 
                    count -= 1
                    if count == 0:
                        cr.commit()
                        count = 200

            if table_bom_line:        
                lblrows = table_bom_line.nrows #行数
                count = 200
                for rx in range(1,lblrows): 
                    bom_line_res = {}  
                    line_cell_0 = table_bom_line.cell(rx, 0).value
                    line_cell_1 = table_bom_line.cell(rx, 1).value                    
                    if not line_cell_0:
                        raise osv.except_osv(_(u'警告!'), _(u'组合关系表-组合装编号-第%s行为空!') % (rx+1))                            
                    else:
                        if isinstance(line_cell_0, float):  
                            line_default_code = int(line_cell_0)                           
                        else:
                            line_default_code = str(line_cell_0)                            
                        line_bom_product = product_obj.search(cr, uid, [('default_code', '=', str(line_default_code))], context=context)
                        if line_bom_product:
                            bom_obj = mrp_bom_obj.search(cr, uid,[('product_id', '=', line_bom_product[0])], context=context)                    
                            if bom_obj:                                               
                                line_bom_id = bom_obj[0]
                                bom_line_res['bom_id'] = line_bom_id  
                        else:
                            raise osv.except_osv(_(u'警告!'), _(u'组合关系表-组合装编号-没有第%s行的组合品,请在组合品表添加!若已有数据,请确保格式正确或没空格!') % (rx+1))
                    if isinstance(line_cell_1, float):  
                        line_default_code2 = int(line_cell_1)                       
                    else:
                        line_default_code2 = str(line_cell_1)                                                      
                    line_product_ids = product_obj.search(cr, uid, [('default_code', '=', str(line_default_code2))], context=context)               
                    if not line_product_ids:
                        raise osv.except_osv(_(u'警告!'), _(u'组合关系表-明细货品编号-第%s行商品%s不存在,请在单品表添加!若已有数据,请确保格式正确或没空格!') % (rx+1,line_default_code2))
                    else: 
                        line_product_id = line_product_ids[0]                  
                        bom_line_res['product_id'] = line_product_id                                       
                        uom_data = product_obj.read(cr, uid, line_product_ids,['uom_id'])[0]['uom_id'][0]
                    bom_line_res['product_uom'] = uom_data
                    bom_line_res['product_qty'] = table_bom_line.cell(rx, 2).value  
                    if line_bom_id: 
                        bom_line_id = mrp_bom_obj.search(cr, uid, [('bom_id', '=', line_bom_id),('product_id', '=', line_product_id)], context=context)                 
                        if not bom_line_id:                                                                                                                   
                            bom_line_id = mrp_bom_obj.create(cr, uid, bom_line_res, context=context)
                    count -= 1
                    if count == 0:
                        cr.commit()
                        count = 200
                        
            if table_stock:
                inv_data = []
                srows = table_stock.nrows #行数
                for rx in range(1,srows): 
                    stock_res = {}  
                    stock_cell_0 = table_stock.cell(rx, 0).value  
                    stock_cell_2 = table_stock.cell(rx, 2).value 
                    stock_cell_3 = table_stock.cell(rx, 3).value               
                    if isinstance(stock_cell_0, float):  
                        stock_default_code = int(stock_cell_0)                           
                    else:
                        stock_default_code = str(stock_cell_0)                            
                    stock_product_ids = product_obj.search(cr, uid, [('default_code', '=', str(stock_default_code))], context=context)              
                    if not stock_product_ids:
                        raise osv.except_osv(_(u'警告!'), _(u'库存表-产品编号-第%s行商品%s不存在,请在单品表添加!若已有数据,请确保格式正确或没空格!') % (rx+1,stock_default_code))
                    else: 
                        stock_product_id = stock_product_ids[0]                  
                        stock_res['product_id'] = stock_product_id                                       
                        stock_uom_data = product_obj.read(cr, uid, stock_product_ids,['uom_id'])[0]['uom_id'][0]
                    stock_res['product_qty'] = table_stock.cell(rx, 1).value
                    stock_res['product_uom'] = stock_uom_data
                    if stock_product_id:
                        if stock_cell_2 and isinstance(stock_cell_2, float):  
                            stock_lot = str(int(stock_cell_2))
                            lot_id = lot_obj.search(cr, uid, [('product_id', '=', stock_product_id), ('name', 'ilike', stock_lot), ('ref', '=', stock_default_code)], context=context)
                            if lot_id:
                                lot_id = lot_id[0]
                            else:
                                lot_id = lot_obj.create(cr, uid,{'name':stock_lot,'product_id':stock_product_id}, context=context)
                            stock_res['prod_lot_id'] = lot_id

                        else:
                            stock_res['prod_lot_id'] = False
                    warehouse_ids = warehouse_obj.search(cr, uid, [('name', '=', stock_cell_3)], context=context)
                    if warehouse_ids:
                        location_dest_id = warehouse_obj.browse(cr, uid, warehouse_ids[0], context=context).lot_stock_id
                        if not location_dest_id:
                            raise osv.except_osv(_(u'警告!'), _(u'请在%s中创建存储仓库!') %(stock_cell_3))
                        else:
                            stock_res['location_id'] = location_dest_id.id                         
                    else:
                        raise osv.except_osv(_(u'警告!'), _(u'第%s行物流中心不能为空或此物流中心不存在!') %(rx+1))

                    inv_data.append((0, 0, stock_res))
            
                self.pool.get('stock.inventory').create(cr, uid, {
                    'name':'Import: ' + time.strftime('%Y-%m-%d %H:%M:%S'),
                    'date':time.strftime('%Y-%m-%d %H:%M:%S'),
                    'inventory_line_id':inv_data,
                    'state':'draft'}, context=context)
        cr.commit()
        return {'type': 'ir.actions.act_window_close'}      
    
okgj_product_import()


