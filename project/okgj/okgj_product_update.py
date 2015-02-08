# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import osv, fields
import time, xlrd, base64
from openerp.tools.translate import _
import sys
crows_lst = []
brows_lst = []
           
class okgj_product_update(osv.osv_memory):
    _name = "okgj.product.update"
    _columns = {
        'excel': fields.binary(u'excel文件', filters='*.xls'),                                                              
    }     
    
    def cols_data(self,name,colnames,crows):
        '''获取单品表首行字段的序号 '''       
        if name in colnames:  
            index = colnames.index(name)                          
            if index in range(crows):
                crows_lst.remove(index)                 
                return index
        else:
            return None
        
    def bcols_data(self,name,colnames,crows):
        '''获取组合品表首行字段的序号 '''
        if name in colnames:  
            index = colnames.index(name)                          
            if index in range(crows):
                brows_lst.remove(index)                 
                return index
        else:
            return None        
      

    def write_cr(self, cr, uid, obj, ids, arg, sheet, rx, colname, context=None):
        '''更新 '''
        try:
            write_id = obj.write(cr, uid, ids, arg, context=context)  
        except:
            cr.commit()
            raise osv.except_osv(_(u'警告!'), _(u'%s表-第%s行%s更新失败!') % (sheet, rx+1, colname))
        
    def search_data(self,cr,uid,obj,name,sheetname,colnames,rx,context=None):
        '''搜索字段对应的ids '''
        obj_ids = obj.search(cr, uid, [('name', '=', name)], context=context)
        if (not obj_ids) or (not name): 
            cr.commit()
            raise osv.except_osv(_(u'警告!'), _(u'%s-%s-第%s行为空或者系统不存在此%s!') % (sheetname,colnames , rx+1, colnames))         
        else:
            return obj.browse(cr, uid, obj_ids)[0].id  
        
    def cell_data(self,cr,uid,cell,sheetname,colnames,rx):
        '''判断单元格是否为空 '''
        if not cell:
            cr.commit()
            raise osv.except_osv(_(u'警告!'), _(u'%s-%s-第%s行为空;若此列无需修改,请将整列删除!') % (sheetname,colnames,rx+1)) 
        else:          
            return cell   
        
    def excpet_mes(self,cr,uid,sheetname,colnames,rx,message):
        cr.commit()
        raise osv.except_osv(_(u'警告!'), _(u'%s  %s  第%s行%s!') % (sheetname,colnames,rx+1,message)) 
   
    def update_bill(self, cr, uid, ids, context=None):
        for excel_data in self.browse(cr, uid, ids):   
            if not excel_data.excel: 
                raise osv.except_osv(_(u'警告!'), _(u'请上传表格!'))          
            excel = xlrd.open_workbook(file_contents=base64.decodestring(excel_data.excel))
            table_product = excel.sheet_by_index(0)
            table_bom = excel.sheet_by_index(1)                         
            product_obj = self.pool.get('product.product')   
            categ_obj = self.pool.get('product.category')  
            uom_obj = self.pool.get('product.uom')                 
            brand_obj =  self.pool.get('okgj.product.brand') 
                         
            if table_product:
                prows = table_product.nrows #行数
                crows = table_product.ncols
                for c in range(crows):
                    crows_lst.append(c)               
                try:
                    colnames =  table_product.row_values(0) #第0行数据  
                except:
                    colnames = []                                
                col_default_code = self.cols_data(u'编号',colnames,crows)
                col_product_name = self.cols_data(u'品名',colnames,crows)
                col_categ = self.cols_data(u'类别',colnames,crows)
                col_variants = self.cols_data(u'规格',colnames,crows) 
                col_min_qty = self.cols_data(u'箱规',colnames,crows)
                col_uom = self.cols_data(u'单位',colnames,crows) 
                col_other_price = self.cols_data(u'市场价',colnames,crows)
                col_list_price = self.cols_data(u'会员价',colnames,crows)
                col_brand = self.cols_data(u'品牌',colnames,crows) 
                col_place = self.cols_data(u'产地',colnames,crows)
                col_ean13 = self.cols_data(u'条码',colnames,crows) 
                col_weight = self.cols_data(u'重量（g）',colnames,crows)
                col_okgj_mark = self.cols_data(u'标记（产品状态）',colnames,crows) 
                col_okgj_long = self.cols_data(u'长',colnames,crows)
                col_okgj_wight = self.cols_data(u'宽',colnames,crows) 
                col_okgj_height = self.cols_data(u'高',colnames,crows)
                col_okgj_note = self.cols_data(u'备注',colnames,crows)
                col_life_time = self.cols_data(u'商品报废时间',colnames,crows)                 
                col_use_time = self.cols_data(u'商品保质期',colnames,crows)   
                col_alert_time = self.cols_data(u'禁止入库时间',colnames,crows)                   
                col_removal_time = self.cols_data(u'禁止出库时间',colnames,crows)                                                                                                                                                                                                                                                                       
                                                                                                  
                for rx in range(1,prows): 
                    row = table_product.row_values(rx)
                    local_res = {} 

                    if col_default_code >= 0:                                                            
                        sheet0_default_code = self.cell_data(cr,uid,table_product.cell(rx, col_default_code).value,u'单品表', u'编号', rx)
                        if isinstance(sheet0_default_code, float):                         
                            local_res['default_code'] = str(int(sheet0_default_code)).lstrip().rstrip()                        
                        else:                           
                            local_res['default_code'] = str(sheet0_default_code).lstrip().rstrip()  
                        product_ids = product_obj.search(cr, uid, [('default_code', '=', local_res['default_code'])], context=context)
                        if not product_ids:
                            self.excpet_mes(cr,uid,u'单品表','',rx,u'商品不存在,请导入或创建此商品')                            
                        else:
                            standard_price =  product_obj.browse(cr, uid, product_ids[0],context=context).standard_price 
                            other_price =  product_obj.browse(cr, uid, product_ids[0],context=context).other_price                                                                      
                    else:
                        self.excpet_mes(cr,uid,u'单品表','',rx-1,u'系统无法找到[编号],请确认编号列是否存在') 
                    
                    if col_product_name >= 0:
                        sheet0_name = str(table_product.cell(rx, col_product_name).value).lstrip().rstrip() 
                        local_res['name'] = self.cell_data(cr,uid,sheet0_name,u'单品表', u'品名', rx)
                    if col_variants >= 0:
                        local_res['variants'] = self.cell_data(cr,uid,table_product.cell(rx, col_variants).value,u'单品表', u'规格', rx)
                    if col_min_qty >= 0:
                        local_res['min_qty'] = self.cell_data(cr,uid,table_product.cell(rx, col_min_qty).value,u'单品表', u'箱规', rx) 
                    
                    if col_other_price >= 0:
                        other_price = self.cell_data(cr,uid,table_product.cell(rx, col_other_price).value,u'单品表', u'市场价', rx) 
                        if isinstance(other_price, float):                         
                            fother_price = other_price                       
                        else:
                            fother_price = float(str(other_price))
                        local_res['other_price'] = fother_price                    
                    
                    if col_list_price >= 0:
                        list_price = self.cell_data(cr,uid,table_product.cell(rx, col_list_price).value,u'单品表', u'会员价', rx)                          
                        if isinstance(list_price, float):                         
                            flist_price = list_price                       
                        else:
                            flist_price = float(str(list_price))
                        if col_other_price < 0:
                            local_res['other_price'] = float(other_price)                            
                        if flist_price < standard_price:
                            self.excpet_mes(cr,uid,u'单品表',u'会员价列',rx,u'会员价低于成本价') 
                        elif local_res['other_price'] <= flist_price:
                            self.excpet_mes(cr,uid,u'单品表',u'会员价列',rx,u'会员价高于或等于市场价')                      
                        else:
                            local_res['list_price'] = flist_price                          

                    if col_place >= 0:
                        local_res['okgj_place'] = self.cell_data(cr,uid,table_product.cell(rx, col_place).value,u'单品表', u'产地', rx)
                    if col_ean13 >= 0:
                        local_res['ean13'] = self.cell_data(cr,uid,table_product.cell(rx, col_ean13).value,u'单品表', u'条码', rx) 
                    if col_weight >= 0:
                        local_res['weight'] = self.cell_data(cr,uid,table_product.cell(rx, col_weight).value,u'单品表', u'重量（g）', rx)
                    if col_okgj_mark >= 0:
                        local_res['okgj_mark'] = self.cell_data(cr,uid,table_product.cell(rx, col_okgj_mark).value,u'单品表', u'标记（产品状态）', rx) 
                    if col_okgj_long >= 0:
                        local_res['okgj_long'] = self.cell_data(cr,uid,table_product.cell(rx, col_okgj_long).value,u'单品表', u'长', rx)
                    if col_okgj_wight >= 0:
                        local_res['okgj_wight'] = self.cell_data(cr,uid,table_product.cell(rx, col_okgj_wight).value,u'单品表', u'宽', rx)   
                    if col_okgj_height >= 0:
                        local_res['okgj_height'] = self.cell_data(cr,uid,table_product.cell(rx, col_okgj_height).value,u'单品表', u'高', rx)
                    if col_okgj_note >= 0:
                        local_res['okgj_note'] = self.cell_data(cr,uid,table_product.cell(rx, col_okgj_note).value,u'单品表', u'备注', rx) 
                    if col_life_time >= 0:
                        local_res['life_time'] = self.cell_data(cr,uid,table_product.cell(rx, col_life_time).value,u'单品表', u'商品报废时间', rx)
                    if col_use_time >= 0:
                        local_res['use_time'] = table_product.cell(rx, col_use_time).value
                        if local_res['use_time']:
                            local_res['track_incoming'] = True
                            local_res['track_outgoing'] = True
                        else:
                            local_res['track_incoming'] = False
                            local_res['track_outgoing'] = False
                    if col_alert_time >= 0:
                        local_res['alert_time'] = self.cell_data(cr,uid,table_product.cell(rx, col_alert_time).value,u'单品表', u'禁止入库时间', rx)
                    if col_removal_time >= 0:
                        local_res['removal_time'] = self.cell_data(cr,uid,table_product.cell(rx, col_removal_time).value,u'单品表', u'禁止出库时间', rx)  
                    if col_categ >= 0:
                        sheet0_categ = str(table_product.cell(rx, col_categ).value).lstrip().rstrip()
                        local_res['categ_id'] = self.search_data(cr, uid, categ_obj, sheet0_categ,u'单品表', u'类别',rx)
                    if col_uom >= 0:
                        sheet0_uom = table_product.cell(rx, col_uom).value
                        local_res['uom_id'] = self.search_data(cr, uid, uom_obj, sheet0_uom,u'单品表', u'单位',rx)
                        local_res['uom_po_id'] = self.search_data(cr, uid, uom_obj, sheet0_uom,u'单品表', u'单位',rx)                                                
                    if col_brand >= 0:
                        sheet0_brand = table_product.cell(rx, col_brand).value
                        local_res['brand_id'] = self.search_data(cr, uid, brand_obj, sheet0_brand,u'单品表', u'品牌',rx)
                                                                        
                    if not product_ids: 
                        self.excpet_mes(cr,uid,u'单品表','',rx,u'商品不存在,请导入或创建此商品')                                                                    
                    else:
                        product_update = self.write_cr(cr, uid,product_obj, product_ids, local_res, u'单品',  rx,u'商品')                                           
           
            if crows_lst:
                tmp = crows_lst[0]
                crows_lst.remove(crows_lst[0])                          
                raise osv.except_osv(_(u'警告!'), _(u'单品表,第%s列,与模板的名称不一致,数据未更新!') % (tmp+1))        

            if table_bom:        
                bbrows = table_bom.nrows #行数
                bcrows = table_bom.ncols
                for c in range(bcrows):
                    brows_lst.append(c) 
                try:
                    bom_colnames =  table_bom.row_values(0) #某一行数据 
                except:
                    bom_colnames = []
                col_bom_default_code = self.bcols_data(u'组合装编号',bom_colnames,bcrows)                 
                col_bom_product_name = self.bcols_data(u'组合装名称',bom_colnames,bcrows)
                col_bom_categ = self.bcols_data(u'类别',bom_colnames,bcrows)
                col_bom_variants = self.bcols_data(u'规格',bom_colnames,bcrows) 
                col_bom_uom = self.bcols_data(u'单位',bom_colnames,bcrows) 
                col_other_price = self.bcols_data(u'市场价',bom_colnames,bcrows)  
                col_list_price = self.bcols_data(u'会员价',bom_colnames,bcrows)                              
                for rx in range(1,bbrows):                   
                    bom_res = {}                          
                    if col_bom_default_code >= 0:                                                            
                        sheet1_default_code = self.cell_data(cr,uid,table_bom.cell(rx, col_bom_default_code).value,u'组合品表', u'组合装编号', rx)
                        if isinstance(sheet1_default_code, float):  
                            bom_res['default_code'] = str(int(sheet1_default_code)).lstrip().rstrip()
                        else:
                            bom_res['default_code'] = str(sheet1_default_code).lstrip().rstrip()  
                        bom_product_ids = product_obj.search(cr, uid, [('default_code', '=', bom_res['default_code'])], context=context)                          
                    else:
                        self.excpet_mes(cr,uid,u'组合品表','',rx-1,u'系统无法找到[组合装编号],请确认组合装编号列是否存在')                                                                        
                    if col_bom_product_name >= 0 :
                        sheet1_name = str(table_bom.cell(rx, col_bom_product_name).value).lstrip().rstrip()
                        bom_res['name'] = self.cell_data(cr,uid,sheet1_name,u'组合品表', u'组合装名称', rx)
                    if col_bom_categ >= 0:
                        sheet1_categ = str(table_bom.cell(rx, col_bom_categ).value).lstrip().rstrip()
                        bom_res['categ_id'] = self.search_data(cr, uid, categ_obj, sheet1_categ,u'组合品表', u'类别',rx)                                               
                    if col_bom_uom >= 0:
                        sheet1_uom = table_bom.cell(rx, col_bom_uom).value 
                        bom_res['uom_id'] = self.search_data(cr, uid, uom_obj, sheet1_uom,u'组合品表', u'单位',rx)                                            
                    if col_bom_variants >= 0:
                        bom_res['variants'] = self.cell_data(cr,uid,table_bom.cell(rx, col_bom_variants).value,u'组合品表', u'规格', rx)                                                                                             

                    if col_other_price >= 0:
                        bom_other_price = self.cell_data(cr,uid,table_bom.cell(rx, col_other_price).value,u'组合品表', u'市场价', rx) 
                        if isinstance(bom_other_price, float):                         
                            fbom_other_price = bom_other_price                       
                        else:
                            fbom_other_price = float(str(bom_other_price))  
                        bom_res['other_price'] = fbom_other_price                    
                    
                    if col_list_price >= 0:                        
                        bom_list_price = self.cell_data(cr,uid,table_bom.cell(rx, col_list_price).value,u'组合品表', u'会员价', rx)
                        if bom_product_ids:
                            group_cost = product_obj._get_okgj_group_product_cost(cr, uid, bom_product_ids, context)
                            bom_other_price =  product_obj.browse(cr, uid, bom_product_ids[0],context=context).other_price
                            if isinstance(bom_list_price, float):                         
                                fbom_list_price = bom_list_price                       
                            else:
                                fbom_list_price = float(str(bom_list_price))  
                            if group_cost:
                                if col_other_price < 0:
                                    bom_res['other_price'] = float(bom_other_price)
                                if fbom_list_price < group_cost.values()[0]:
                                    self.excpet_mes(cr,uid,u'组合品表',u'会员价列',rx,u'会员价低于成本价')                                                                     
                                elif bom_res['other_price'] <= fbom_list_price:
                                    self.excpet_mes(cr,uid,u'组合品表',u'会员价列',rx,u'会员价高于或等于市场价')                                                             
                                else:
                                    bom_res['list_price'] = fbom_list_price                                                 
                                             
                    if not bom_product_ids:
                        self.excpet_mes(cr,uid,u'组合品表','',rx,u'组合品不存在,请导入或创建此组合品')
                    else:
                        bom_update = self.write_cr(cr, uid, product_obj, bom_product_ids, bom_res, u'组合品',  rx,u'商品')                 

            if brows_lst: 
                btmp = brows_lst[0]
                brows_lst.remove(brows_lst[0])                               
                raise osv.except_osv(_(u'警告!'), _(u'组合品表,第%s列,与模板的名称不一致,数据未更新!') % (btmp+1))

        return {'type': 'ir.actions.act_window_close'}  
    
okgj_product_update()

