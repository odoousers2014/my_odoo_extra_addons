# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import osv, fields
import time, xlrd, base64
from openerp.tools.translate import _
import sys
      
class okgj_rack_import(osv.osv_memory):
    _name = "okgj.rack.import"
    _columns = {
        'excel': fields.binary(u'excel文件', filters='*.xls'),                                                              
    }

    def import_rack(self, cr, uid, ids, context=None):
        for excel_data in self.browse(cr, uid, ids):   
            if not excel_data.excel: 
                raise osv.except_osv(_(u'警告!'), _(u'请上传表格!'))          
            excel = xlrd.open_workbook(file_contents=base64.decodestring(excel_data.excel))                
            product_obj = self.pool.get('product.product')    
            rack_obj = self.pool.get('okgj.product.rack')  
            warehouse_obj = self.pool.get('stock.warehouse') 
            usage_obj = self.pool.get('okgj.product.rack.usage')                                                                                                       
            table_rack = excel.sheet_by_index(0)                           

            if table_rack:
                inv_data = []
                srows = table_rack.nrows #行数
                count = 200
                for rx in range(1,srows): 
                    rack_res = {}  
                    rack_default_code = table_rack.cell(rx, 0).value 
                    rack_place = table_rack.cell(rx, 1).value 
                    rack_usage = str(table_rack.cell(rx, 2).value) 
                    rack_warehouse = table_rack.cell(rx, 3).value               
                    if isinstance(rack_default_code, float):  
                        rack_default_code = str(int(rack_default_code))                           
                    else:
                        rack_default_code = str(rack_default_code)                            
                    rack_product_ids = product_obj.search(cr, uid, [('default_code', '=', rack_default_code)], context=context)              
                    if not rack_product_ids:
                        raise osv.except_osv(_(u'警告!'), _(u'第%s行商品编码%s不存在,请添加商品信息!若已有数据,请确保格式正确或没空格!') % (rx+1,rack_default_code))
                    else:                
                        rack_res['product_id'] = rack_product_ids[0]
                    rack_ids = rack_obj.search(cr,uid,[('name', '=', rack_place)], context=context)
                    if rack_ids:
                        rack_res['rack_id'] = rack_ids[0]
                    else:
                        raise osv.except_osv(_(u'警告!'), _(u'第%s行货位%s不存在,请添加货位!若已有数据,请确保格式正确或没空格!') % (rx+1,rack_place))  
                    warehouse_ids = warehouse_obj.search(cr, uid, [('name', '=', rack_warehouse)], context=context)
                    if warehouse_ids:
                        rack_res['warehouse_id'] = warehouse_ids[0]
                    else:
                        raise osv.except_osv(_(u'警告!'), _(u'第%s行物流中心%s不存在,请添加物流中心!若已有数据,请确保格式正确或没空格!') % (rx+1,rack_warehouse))                                                        
                    if rack_usage == '拣':
                        rack_res['usage'] = 'pick'
                    elif rack_usage == '存':
                        rack_res['usage'] = 'store'                  
                    usage_ids = usage_obj.search(cr, uid, [('product_id', '=', rack_res['product_id'])], context=context)
                    if not usage_ids:
                        usage_id = usage_obj.create(cr, uid, rack_res, context=context)
                    else:
                        usage_obj.write(cr, uid, usage_ids, rack_res, context=context)
                    count -= 1
                    if count == 0:
                        cr.commit()
                        count = 200

        cr.commit()
        return {'type': 'ir.actions.act_window_close'}      
    
okgj_rack_import()


