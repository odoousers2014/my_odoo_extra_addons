# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import osv, fields
import time, xlrd, base64
from openerp.tools.translate import _
import sys
      
class okgj_stock_import(osv.osv_memory):
    _name = "okgj.stock.import"
    _columns = {
        'excel': fields.binary(u'excel文件', filters='*.xls'),                                                              
    }

    def import_stock(self, cr, uid, ids, context=None):
        for excel_data in self.browse(cr, uid, ids):   
            if not excel_data.excel: 
                raise osv.except_osv(_(u'警告!'), _(u'请上传表格!'))          
            excel = xlrd.open_workbook(file_contents=base64.decodestring(excel_data.excel))                
            product_obj = self.pool.get('product.product')    
            lot_obj = self.pool.get('stock.production.lot') 
            location_obj = self.pool.get('stock.location')                                                                                                
            table_stock = excel.sheet_by_index(0)                           

            if table_stock:
                inv_data = []
                srows = table_stock.nrows #行数
                for rx in range(1,srows): 
                    stock_res = {}  
                    stock_default_code = table_stock.cell(rx, 0).value  
                    stock_lot = table_stock.cell(rx, 2).value 
                    stock_warehouse = table_stock.cell(rx, 3).value               
                    if isinstance(stock_default_code, float):  
                        stock_default_code = str(int(stock_default_code))                           
                    else:
                        stock_default_code = str(stock_default_code)                            
                    stock_product_ids = product_obj.search(cr, uid, [('default_code', '=', str(stock_default_code))], context=context)              
                    if not stock_product_ids:
                        raise osv.except_osv(_(u'警告!'), _(u'导入模板的产品编号列-第%s行商品%s不存在,请在单品表添加!若已有数据,请确保格式正确或没空格!') % (rx+1,stock_default_code))
                    else: 
                        stock_product_id = stock_product_ids[0]                  
                        stock_res['product_id'] = stock_product_id                                       
                        stock_uom_data = product_obj.read(cr, uid, stock_product_ids,['uom_id'])[0]['uom_id'][0]
                    stock_res['product_qty'] = table_stock.cell(rx, 1).value
                    stock_res['product_uom'] = stock_uom_data
                    if stock_product_id:
                        if stock_lot and isinstance(stock_lot, float):  
                            stock_lot = str(int(stock_lot))            
                            lot_id = lot_obj.search(cr, uid, [('product_id', '=', stock_product_id), ('name', 'ilike', stock_lot), ('ref', '=', stock_default_code)], context=context)
                            if lot_id:
                                lot_id = lot_id[0]
                            else:
                                lot_id = lot_obj.create(cr, uid,{'name':stock_lot,'product_id':stock_product_id}, context=context)
                            stock_res['prod_lot_id'] = lot_id
                        else:
                            stock_res['prod_lot_id'] = False
                    name_no_blank = stock_warehouse.replace(" ", "")
                    name_have_blank = name_no_blank.replace("/", " / ")  
                    location_ids = location_obj.search(cr, uid, [('complete_name', '=', name_have_blank)], context=context)
                    if stock_warehouse and (not location_ids):
                        raise osv.except_osv(_(u'警告!'), _(u'导入模板的仓库列-第%s行%s仓库不存在,请在系统创建!') %(rx+1 , stock_warehouse))
                    elif not stock_warehouse:
                        raise osv.except_osv(_(u'警告!'), _(u'导入模板的仓库列-第%s行为空') %(rx+1))
                    else:
                        stock_res['location_id'] = location_ids[0]                 

                    inv_data.append((0, 0, stock_res))
            
                self.pool.get('stock.inventory').create(cr, uid, {
                    'name':'Import: ' + time.strftime('%Y-%m-%d %H:%M:%S'),
                    'date':time.strftime('%Y-%m-%d %H:%M:%S'),
                    'inventory_line_id':inv_data,
                    'state':'draft'}, context=context)
        return {'type': 'ir.actions.act_window_close'}      
    
okgj_stock_import()
