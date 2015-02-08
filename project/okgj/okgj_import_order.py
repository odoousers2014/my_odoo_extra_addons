# -*- coding: utf-8 -*-

from openerp import tools
from openerp.osv import osv, fields
import time, xlrd, base64
from openerp.tools.translate import _
import sys
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta

IMPORT_TABLE = RETURN_IMPORT_TABLE = [u'编号', u'数量', u'价格'] #模板
class okgj_import_order(osv.osv_memory):
    _name = 'okgj.import.order'
    _columns = {
        'excel': fields.binary(u'excel文件', filters='*.xls'), 
        'import_info':fields.text(u'导入商品信息记录:'),
        'import_address':fields.text(u'请从以下地址下载导入模板', readonly=True),
        'return_import_address':fields.text(u'请从以下地址下载退货导入模板', readonly=True),
        'return_import_info':fields.text(u'导入退货商品信息记录:'),
        'state':fields.selection([('start','start'),('end','end')],'状态',readonly=True),
    }
    _defaults={
        'return_import_address':"http://192.168.10.207/purchase_return_product.xls",
        #'state': lambda *a:'start',
    }
    def cols_data(self,name,colnames):
        '''获取excel表首行字段的序号 '''
        if name in colnames:  
            return colnames.index(name)                      
        return False
        
    def cell_data(self, cell, colnames,rx):
        '''判断单元格是否为空 '''
        if cell:
            return cell          
        return False
    
    def _validate_import_template(self, table, table_type=None):
        """
                验证导入模块是否正确
        @param table:表
        @param table_type:表类型
        """
        table_header = [cell.value for cell in table.row(0)] #表头数据
        if table.ncols != len(IMPORT_TABLE):
            return False
        for i in range(0, table.ncols):
            if (table_header[i].strip() != IMPORT_TABLE[i]):
                return False
        return True
        
    def _validate_table(self, table):
        """
                验证导入单元格格式是否为文本验证
        """
        prows = table.nrows
        pcols = table.ncols
        for rx in range(0, prows): 
            for rc in range(0, pcols):
                if (table.cell(rx, rc).ctype != 1) and (table.cell(rx, rc).ctype != 0):
                    return False
        return True
    
    def _validate_cell_value(self, cr, uid, table):
        """
                验证导入商品是否存在和单元格值不能为空
        @param table:excle表
        """
        null_info = ""
        (prows, pcols) = (table.nrows, table.ncols)
        product_obj = self.pool.get('product.product')
        table_header = [cell.value for cell in table.row(0)] #表头数据
        for rx in range(1, prows):
            for rp in range(0, pcols):
                if table.cell(rx, rp).value:
                    if rp == 0:
                        product_ser = product_obj.search(cr, uid, [('default_code', '=', table.cell(rx, 0).value)])
                        if not product_ser:
                            null_info += u'第 %s行编号为 "%s" 的商品不存在! \n' %(rx+1, table.cell(rx, 0).value)
                else:
                    null_info += u'第 %s行 "%s" 不能为空! \n'% (rx+1, table_header[rp])
                    
        return null_info

    def _validate_cell_type(self, table, cols_number):
        """
                验证导入单元格(数量)值类型是否正确
        @param table:excel表
        @param cols_number:表列号 (顺序:['编码', '数量', '价格'])
        """
        numerical_info = ''
        prows = table.nrows
        pcols = [cols_number[1], cols_number[2]]
        table_header = [cell.value for cell in table.row(0)] #表头数据
        for rx in range(1, prows):
            for rl in pcols:
                try:
                    cell_type = float(table.cell(rx, rl).value) # float
                except ValueError:
                    numerical_info += u'第%s行"%s" 的单元格格式错误! \n' %(rx + 1, IMPORT_PRODUCT_TABLE[rl])
                else:
                    if rl == cols_number[1]:
                        qty = float(table.cell(rx, rl).value) #数量
                        if qty != int(qty): # int
                            numerical_info += u'第%s行"%s" 的单元格格式错误! \n' %(rx + 1, table_header[rl])
        return numerical_info
    
    def test_repeat_excel(self, cr, uid, table, cols_number):
        """
                验证excel表中商品是否重复
        @param table:表 
        @param cols_number:表列号 (顺序:['编码', '数量'])
        """
        rep_info_excel = ''
        excel_info, repeat_info_dict = {}, {}
        for rx in range(1, table.nrows):
            row_data = [cell.value for cell in table.row(rx)]
            default_code = row_data[cols_number[0]]
            if default_code in repeat_info_dict:
                temp_info = u'excel中第 %s行编号为 "%s" 的商品重复! \n'
                if repeat_info_dict[default_code]:
                    rep_info_excel += (temp_info % (repeat_info_dict[default_code].pop(), default_code))
                rep_info_excel += (temp_info % (rx+1, default_code))
            else:
                repeat_info_dict[default_code] = [rx+1]
                excel_info[default_code] = [rx+1] 
        return rep_info_excel, excel_info
        
    def test_repeat_table(self, cr, uid, table, obj, excel_info, context=None):
        """
                验证excel表与erp中的商品是否重复
        @param excel_info:excel表信息
        """
        rep_info_table = ''
        active_id = context.get('active_id', False)
        active_model = context.get('active_model', False)
        act_rec = self.pool.get(active_model).browse(cr, uid, active_id)
        purchase_obj = self.pool.get(obj)
        
        for default_code in excel_info:
            if active_id:
                product_ser = self.pool.get('product.product').search(cr, uid, [('default_code','=',default_code)], context=context)
                if obj == 'purchase.order.line':
                    line_ids = purchase_obj.search(cr,uid,[('order_id', '=', active_id)], context=context)
                    rep_ids = purchase_obj.search(cr,uid,[('order_id', '=', active_id),('product_id', '=', product_ser[0])], context=context)
                elif obj == 'okgj.purchase.return.line':
                    line_ids = purchase_obj.search(cr, uid, [('return_order_id', '=', active_id)], context=context)
                    rep_ids = purchase_obj.search(cr, uid, [('return_order_id', '=', active_id),('product_id', '=', product_ser[0])])
                if rep_ids:
                    res_line = purchase_obj._get_line_no(cr, uid, line_ids, 'line_no', '')
                    for rep_id in rep_ids:
                        repeat_line = res_line[rep_id]
                        info = u'excel中第 %s行编号为 "%s" 的商品与列表中第 %s行的商品重复! \n'
                        rep_info_table += (info % (excel_info[default_code], default_code, repeat_line))

        return rep_info_table

    def action_import_order(self, cr, uid, ids, context=None):
        """
                采购商品导入
        """
        for excel_data in self.browse(cr, uid, ids):   
            if not excel_data.excel: 
                raise osv.except_osv(_(u'警告!'), _(u'请上传表格!'))          
            excel = xlrd.open_workbook(file_contents=base64.decodestring(excel_data.excel))
            try:
                table_product = excel.sheet_by_index(0) 
            except:
                raise osv.except_osv(_(u'警告!'), _(u'请在模板里创建一个工作表!'))                     
            
            if table_product:
                try:
                    colnames =  table_product.row_values(0) #某一行数据  
                except:
                    colnames = []                                
                prows = table_product.nrows #行数
                col_default_code = self.cols_data(u'编号',colnames)
                col_qty = self.cols_data(u'数量',colnames) 
                col_price = self.cols_data(u'价格',colnames)
                if col_default_code is False:
                    raise osv.except_osv(_(u'警告!'), _(u'系统无法找到[编号],请确认编号列是否存在!'))
                if col_qty is False:
                    raise osv.except_osv(_(u'警告!'), _(u'系统无法找到[数量],请确认数量列是否存在!')) 
                if col_qty is False:
                    raise osv.except_osv(_(u'警告!'), _(u'系统无法找到[价格],请确认价格列是否存在!'))
                
                pricelist_obj = self.pool.get('pricelist.partnerinfo')
                account_fiscal_position = self.pool.get('account.fiscal.position')
                account_tax = self.pool.get('account.tax')                        
                purchase_line_obj = self.pool.get('purchase.order.line')
                supperlier_obj = self.pool.get('product.supplierinfo')
                ## pur_mag_obj = self.pool.get('okgj.purchase.price.management')
                product_obj = self.pool.get('product.product')
                purchase_order_obj = self.pool.get('purchase.order')
                
                order_rec = purchase_order_obj.browse(cr, uid, context['active_ids'][0], context=context)
                create_date = order_rec.create_date
                partner_id = order_rec.partner_id
                warehouse_id = order_rec.warehouse_id
                row_ls = [cell.value for cell in table_product.row(0)]
                
                ##验证模板是否准确
                if not self._validate_import_template(table_product):
                    raise osv.except_osv(('Error:'), _(u'execl表格式错误!'))
            
                ##验证导入单元格格式是否为文本
                if not self._validate_table(table_product):
                    raise osv.except_osv(('Error:'), _(u'请将单元格格式全部设置为文本'))
                
                ##验证单元格是否为空
                null_info = self._validate_cell_value(cr, uid, table_product)
                if null_info:
                    raise osv.except_osv(('Error:'), _(null_info))
                
                ##验证数量, 价格单元格格式是否正确
                numerical_info = self._validate_cell_type(table_product, [col_default_code, col_qty, col_price])
                if numerical_info:
                  raise osv.except_osv(('Error:'), _(numerical_info))
                
                ##验证excel中商品重复
                rep_info_excel, excel_info = self.test_repeat_excel(cr, uid, table_product, [col_default_code, col_qty])
                if rep_info_excel:
                    raise osv.except_osv(('Error:'), _(rep_info_excel))
                
                ##验证excel中商品与erp中商品是否重复
                rep_info_table = self.test_repeat_table(cr, uid, table_product, 'purchase.order.line',excel_info, context=context)                                                                                                                                                                                                                                                                                                                                                   
                if rep_info_table:
                    raise osv.except_osv(('Error:'), _(rep_info_table))
                
                for rx in range(1,prows): 
                    row = table_product.row_values(rx)
                    local_res = {} 
                    local_res['order_id'] = context['active_ids'][0]  
                    if col_default_code >= 0:                                                            
                        sheet0_default_code = self.cell_data(table_product.cell(rx, col_default_code).value, u'编号', rx)
                        if isinstance(sheet0_default_code, float):                         
                            local_default_code = str(int(sheet0_default_code))                        
                        else:                           
                            local_default_code = str(sheet0_default_code)                                                 
                         
                    product_ids = product_obj.search(cr, uid, [('default_code', '=', local_default_code)], context=context)                                        
                    product_sup_ids =supperlier_obj.search(cr,uid,[('product_id', '=', product_ids[0]),('name','=', partner_id.id)])               
                    if not product_sup_ids:
                        raise osv.except_osv(_(u'Error:'), _(u'第 %s行编号为 "%s" 的商品不在该供应商里,导入未开始!' %(rx, local_default_code)))
                    product_sup_ware_ids = supperlier_obj.search(cr, uid, [
                        ('product_id', '=', product_ids[0]),
                        ('name', '=', partner_id.id),
                        ('warehouse_id', '=', warehouse_id.id)], context=context)
                    if not product_sup_ware_ids:
                        raise osv.except_osv(_(u'Error:'), _(u'第 %s行供应商"%s"、商品"%s"、物流"%s"的采购价记录未找到!' %(rx+1, partner_id.name, local_default_code, warehouse_id.name)))
                         
                    ## 多物流中心价格处理
                    #product_price = product_obj.get_supplier_warehouse_price(cr, uid, partner_id.id, product_ids, warehouse_id.id, context=context)
                    #if product_price:
                    #    local_res['price_unit'] = product_price[product_ids[0]]
                    
                    ##促销价处理
                    ## order_time = time.strftime('%Y-%m-%d')
                    ## product_list, purchase_time = product_ids, order_time
                    ## result = pur_mag_obj.get_price_management(cr, uid, product_list, purchase_time, partner_id.id, warehouse_id.id)
                    ## if result and result[product_ids[0]]:
                    ##     local_res['price_unit'] = result[product_ids[0]]
                    
                    local_res['product_id'] = product_ids[0]
                    uom_id = product_obj.browse(cr, uid, product_ids[0], context=context).uom_id.id                         
                    name = product_obj.browse(cr, uid, product_ids[0], context=context).name
                                            
                    produce_delay = product_obj.browse(cr, uid, product_ids[0], context=context).produce_delay
                    procurement_date_planned = datetime.strptime(create_date, DEFAULT_SERVER_DATETIME_FORMAT)                       
                    schedule_date = (procurement_date_planned + relativedelta(days=produce_delay))                                                                       
                    local_res['product_uom'] = uom_id 
                    local_res['name'] = name  
                    local_res['date_planned'] = schedule_date.strftime("%Y-%m-%d")
                    supplier_taxes_id = product_obj.browse(cr, uid, product_ids[0], context=context).supplier_taxes_id        
                    taxes = account_tax.browse(cr, uid, map(lambda x: x.id, supplier_taxes_id))
                    taxes_ids = account_fiscal_position.map_tax(cr, uid, False, taxes)                         
                    local_res['taxes_id'] = [(4,taxes_ids[0])]
                    if col_qty >= 0:
                        product_qty = self.cell_data(table_product.cell(rx, col_qty).value, u'数量', rx)
                        local_res['product_qty'] = float(product_qty)                                                                                             
                    if col_price >= 0:
                        price_unit = self.cell_data(table_product.cell(rx, col_price).value, u'单价', rx)
                        local_res['price_unit'] = float(price_unit)                                                              
                    
                    purchase_line_obj.create(cr, uid, local_res, context=context)
        return {'type': 'ir.actions.act_window_close'}
       
    def purchase_return_import(self, cr, uid, ids, context=None):
        """
                采购退货商品导入
        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        return_line_obj = self.pool.get('okgj.purchase.return.line')
        supp_obj = self.pool.get('product.supplierinfo')
        return_order_id = context.get('active_id', False)
        return_obj = self.pool.get(context.get('active_model', False))
        for rec in self.browse(cr, uid, ids):   
            if not rec.excel: 
                raise osv.except_osv(_(u'警告!'), _(u'请上传表格!'))          
            excel = xlrd.open_workbook(file_contents=base64.decodestring(rec.excel))
            try:
                table_product = excel.sheet_by_index(0) 
            except:
                raise osv.except_osv(_(u'警告!'), _(u'请在模板里创建一个工作表!'))  
            
            colnames = [cell.value for cell in table_product.row(0)]
            cols_number = [self.cols_data(name, colnames) for name in IMPORT_TABLE]
            for i, col in enumerate(cols_number):
                if col is False:
                    raise osv.except_osv(_(u'警告!'), _(u'系统无法找到["%s"],请确认列是否存在!' % IMPORT_TABLE[i]))
                
            ##验证模板是否准确
            if not self._validate_import_template(table_product):
                raise osv.except_osv(('Error:'), _(u'execl表格式错误!'))
        
            ##验证导入单元格格式是否为文本
            if not self._validate_table(table_product):
                raise osv.except_osv(('Error:'), _(u'请将单元格格式全部设置为文本'))
            
            ##验证单元格是否为空
            null_info = self._validate_cell_value(cr, uid, table_product)
            if null_info:
                raise osv.except_osv(('Error:'), _(null_info))
            
            ##验证数量单元格格式是否正确
            numerical_info = self._validate_cell_type(table_product, cols_number)
            if numerical_info:
              raise osv.except_osv(('Error:'), _(numerical_info))
            
            ##验证excel中商品重复
            rep_info_excel, excel_info = self.test_repeat_excel(cr, uid, table_product, cols_number)
            if rep_info_excel:
                raise osv.except_osv(('Error:'), _(rep_info_excel))
                
            ##验证excel中商品与erp中商品是否重复
            rep_info_table = self.test_repeat_table(cr, uid, table_product, 'okgj.purchase.return.line',excel_info, context=context)                                                                                                                                                                                                                                                                                                                                                   
            if rep_info_table:
                raise osv.except_osv(('Error:'), _(rep_info_table))
                
            ##开始导入商品数据
            prows = table_product.nrows
            for line_number in range(1,prows):
                row_ls = [cell.value for cell in table_product.row(line_number)]
                default_code, product_qty, price_unit = row_ls[cols_number[0]], row_ls[cols_number[1]], row_ls[cols_number[2]]
                product_ser = product_obj.search(cr, uid, [('default_code', '=', default_code)])
                if return_obj._name == 'okgj.purchase.return' and return_order_id:
                    partner_id = return_obj.read(cr, uid, return_order_id, ['partner_id'])['partner_id'][0]                       
                    product_sup = supp_obj.search(cr, uid, [('product_id', '=', product_ser[0]),('name', '=', partner_id)])
                    if not product_sup:
                        raise osv.except_osv(('Error:'), _(u'第 %s行编号为 "%s" 的商品不在该供应商里,导入未开始!' % (line_number, default_code)))
                uom_id = product_obj.browse(cr, uid, product_ser[0], context=context).uom_id.id
                return_id = return_line_obj.create(cr, uid, {
                    'return_order_id':return_order_id,
                    'product_id':product_ser[0],
                    'product_qty':float(product_qty),
                    'price_unit':float(price_unit),
                    'product_uom':uom_id,}, context=context)
        
        return {'type':'ir.actions.act_window_close'}
    
okgj_import_order()

