# -*- coding:utf-8 -*-

import xlrd
import base64
import sys

from datetime import datetime
from openerp.osv import fields,osv
from openerp.tools.translate import _
    
##table template field
IMPORT_PRODUCT_TABLE = (u'供应商', u'商品', u'物流中心', u'开始时间', u'结束时间', u'促销进价')

class bargain_product_import(osv.osv_memory):
    _name='bargain.product.import'
    _columns={
            'excel': fields.binary(u'excel文件', filters='*.xls', required=True),
            'import_address':fields.text(u'请从以下地址下载导入模板', readonly=True),
            'file_name':fields.char(u'excel文件名'),
            'import_info':fields.text(u'导入商品信息记录'),
            'state':fields.selection([('start', 'start'),('end', 'end')],u'状态',readonly=True),
    }
    _defaults={
            #'state':lambda *a:'start',
            'import_address':"http://192.168.10.137/bargain_product.xls",
    }
    
    def _validate_import_template(self, table):
        """
            验证导入商品模板是否正确
        """
        pcols, prows = table.ncols, table.nrows
        table_header = [cell.value for cell in table.row(0)] #表头数据
        if pcols != len(IMPORT_PRODUCT_TABLE):
            return False
        for rx in range(0, pcols):
            if (unicode(table_header[rx]).strip() != IMPORT_PRODUCT_TABLE[rx]):
                return False
        return True
        
    def _validate_table(self, table):
        """
            验证导入单元格格式是否为文本
        """
        prows = table.nrows
        pcols = table.ncols
        for rx in range(0, prows): 
            for rc in range(0, pcols):
                if (table.cell(rx, rc).ctype != 1) and (table.cell(rx, rc).ctype != 0):
                    return False
        return True
    
    def _validate_cell_value(self, cr, uid, table, context=None):
        """
                验证导入单元格值不能为空
                验证导入供应商,商品,物流中心是否存在
        @param table:excle表
        @param return dict of excel info:{line1:{'partner_id':(id, value), 
            'product_id':(id, value), 'warehouse_id':(id, value)},{...},} 
        """
        null_info = ""
        excel_info = {}
        prows = table.nrows
        pcols = table.ncols
        table_header = [cell.value for cell in table.row(0)] #表头数据
        col_partner = table_header.index(u'供应商')
        col_product = table_header.index(u'商品')
        col_warehouse = table_header.index(u'物流中心')
        
        product_obj = self.pool.get('product.product')
        partner_obj = self.pool.get('res.partner')
        warehouse_obj = self.pool.get('stock.warehouse')
        
        for rx in range(1, prows):
            for rp in range(0, pcols):
                if table.cell(rx, rp).value:
                    col_name = None
                    col_value = table.cell(rx, rp).value
                    if rp == col_partner:
                        col_ser = partner_obj.search(cr, uid, ['|', ('name', '=', col_value), ('ref', '=', col_value), ('supplier', '=', True)])
                        col_name = 'partner_id'
                    elif rp == col_product:
                        col_ser = product_obj.search(cr, uid, [('default_code', '=', col_value)])
                        col_name = 'product_id'
                    elif rp == col_warehouse:
                        col_ser = warehouse_obj.search(cr, uid, [('name', '=', col_value)])
                        col_name = 'warehouse_id'
                    else:
                        continue
                    if col_ser and col_name:
                        if rx in excel_info:
                            excel_info[rx].update({col_name:(col_ser[0], col_value)})
                        else:
                            excel_info[rx] = {col_name:(col_ser[0], col_value)}
                    else:
                        null_info += u'第 %s行列名为%s: 值为: "%s" 的记录不存在! \n' %(rx+1, table_header[rp], table.cell(rx, rp).value)
                else:
                    null_info += u'第 %s行 "%s" 不能为空! \n'% (rx+1, IMPORT_PRODUCT_TABLE[rp])
        return null_info, excel_info
    
    def _validate_supplier_product(self, cr, uid, table, excel_info, context=None):
        """
                验证供应商，商品，物流中心的关联是否正确
        """
        supplier_info = ''
        prows = table.nrows
        table_header = [cell.value for cell in table.row(0)] #表头数据
        col_purchase_price = table_header.index(u'促销进价')
        supinfo_obj = self.pool.get('product.supplierinfo')
        product_obj = self.pool.get('product.product')
        for rx in range(1, prows):
            row_data = [cell.value for cell in table.row(rx)]
            partner_ids = excel_info[rx].get('partner_id')
            product_ids = excel_info[rx].get('product_id')
            warehouse_ids = excel_info[rx].get('warehouse_id')
            purchase_price = row_data[col_purchase_price]
            
            sup_ids = supinfo_obj.search(cr, uid, [('product_id', '=', product_ids[0]),('name', '=', partner_ids[0])])
            sup_ware_ids = supinfo_obj.search(cr, uid, [('product_id', '=', product_ids[0]),('name', '=', partner_ids[0]), ('warehouse_id', '=', warehouse_ids[0])])
            if sup_ids:
                if sup_ware_ids:
                    product_price = product_obj.get_supplier_warehouse_price(cr, uid, partner_ids[0], product_ids[0], warehouse_ids[0], context=context)
                    if product_price:
                        if float(purchase_price) > product_price[product_ids[0]]:
                            supplier_info += u'第 %s行商品促销价必须小于原单价%s元! \n' % (rx+1, product_price[product_ids[0]])
                else:
                    supplier_info += u'第 %s行供应商"%s"、商品"%s"、物流"%s"的采购进价记录未找到! \n' %(rx+1, partner_ids[1], product_ids[1], warehouse_ids[1]) 
            else:
                supplier_info += u'第 %s行商品"%s"不是供应商"%s"的商品! \n' % (rx+1, product_ids[1], partner_ids[1])
        return supplier_info

    def _validate_cell(self, table):
        """
            验证促销进价单元格格式是否正确
        """
        prows = table.nrows
        pcols = table.ncols
        rl = IMPORT_PRODUCT_TABLE.index(u'促销进价')
        validate_info = ''
        for rx in range(1, prows):
            try:
                cell_type = float(table.cell(rx, rl).value)
            except ValueError:
                validate_info += u'第%s行"%s" 的单元格格式错误! \n' %(rx + 1, IMPORT_PRODUCT_TABLE[rl])
        return validate_info

    def _validate_date_format(self, table):
        """
              验证excel表中开始时间和结束时间的格式正确
              验证开始时间必须小于等于结束时间
        """
        format_info = ''
        prows = table.nrows
        s_index = IMPORT_PRODUCT_TABLE.index(u'开始时间')
        e_index = IMPORT_PRODUCT_TABLE.index(u'结束时间')
        for rx in range(1, prows):
            format_flg = True
            try:
                start_time = datetime.strptime(table.cell(rx, s_index).value, '%Y-%m-%d')
                end_time = datetime.strptime(table.cell(rx, e_index).value, '%Y-%m-%d')
            except ValueError:
                format_flg = False
                format_info += u'第%s行 的单元格时间格式错误! \n' %(rx + 1)
            if format_flg and (start_time > end_time):
                format_info += u'第%s行开始时间必须小于等于结束时间! \n' %(rx + 1)
        return format_info         
                
    def action_import(self, cr, uid, ids, context=None):
        """
                导入数据
        """
        for rec in self.browse(cr, uid, ids):
            if not rec.excel: 
                raise osv.except_osv(_(u'警告!'), _(u'请上传表格!'))          
            excel = xlrd.open_workbook(file_contents=base64.decodestring(rec.excel))    
            try:
                table = excel.sheet_by_index(0)
            except:
                raise osv.except_osv(_(u'警告!'), _(u'请在模板里创建一个工作表!'))                     

            ##验证模板是否准确
            if not self._validate_import_template(table):
                raise osv.except_osv(('Error:'), _(u'execl表格式错误!'))
            
            ##验证导入单元格格式是否为文本
            if not self._validate_table(table):
                raise osv.except_osv(('Error:'), _(u'请将促销商品价格表单元格格式全部设置为文本'))
            
            ##验证单元格是否空值
            null_info, excel_info = self._validate_cell_value(cr, uid, table, context=context)
            if null_info:
                raise osv.except_osv(('Error:'), _(null_info))
            
            ##验证采购进价单元格格式是否正确
            validate_info = self._validate_cell(table)
            if validate_info:
                raise osv.except_osv(('Error:'), _(validate_info))
            
            ##验证excel表中开始时间和结束时间的格式
            validate_date_info=self._validate_date_format(table)
            if validate_date_info:
                raise osv.except_osv(('Error:'), _(validate_date_info))
            
            ##验证供应商，商品，物流中心的关联是否正确
            supplier_info = self._validate_supplier_product(cr, uid, table, excel_info, context=context)
            if supplier_info:
                raise osv.except_osv(('Error:'), _(supplier_info))
            
            ## 开始正式导入数据
            prows = table.nrows
            order_data_dict = {}
            table_header = [cell.value for cell in table.row(0)] #表头数据
            col_start_time = table_header.index(u'开始时间')
            col_end_time = table_header.index(u'结束时间')
            col_purchase_price = table_header.index(u'促销进价')
            pur_magobj = self.pool.get('okgj.purchase.price.management')
            order_magobj = self.pool.get('okgj.purchase.price.order.management')
            for line_number in range(1, prows):
                row_data = [cell.value for cell in table.row(line_number)]
                start_time = row_data[col_start_time]
                end_time = row_data[col_end_time]
                new_price = row_data[col_purchase_price]
                
                partner_ids = excel_info[line_number].get('partner_id')
                product_ids = excel_info[line_number].get('product_id')
                warehouse_ids = excel_info[line_number].get('warehouse_id')
                #合并excel中供应商和物流中心相同的行
                order_key = (partner_ids[0], warehouse_ids[0])
                if order_key in order_data_dict:
                    order_management_id =  order_data_dict[order_key]
                else:
                    order_management_id = order_magobj.create(cr, uid, {'partner_id': partner_ids[0], 'warehouse_id': warehouse_ids[0]}, context=context)
                    order_data_dict[order_key] = order_management_id
                mag_id = pur_magobj.create(cr, uid, {
                                                     'order_management_id':order_management_id,
                                                     'product_id':product_ids[0],
                                                     'partner_id':partner_ids[0],
                                                     'warehouse_id':warehouse_ids[0],
                                                     'start_time':start_time,
                                                     'end_time':end_time,
                                                     'new_price':new_price,
                                            })
        return {'type':'ir.actions.act_window_close'}
