# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import osv, fields

class okgj_product_demo(osv.osv_memory):
    _name = "okgj.product.demo"
    _columns = {
        'default_code': fields.char(u'编号', size=64, required=True),                
        'name': fields.char(u'品名', size=64, required=True),
        'type': fields.char(u'类别'),
        'variants': fields.char(u'规格', size=64),
        'uom_id': fields.many2one('product.uom', u'单位', required=True),
        'uom_po_id': fields.many2one('product.uom', u'采购单位', required=True),
        'other_price': fields.float(u'零售价'), 
        'default_purchase_price': fields.float(u'默认进货价'),               
        'list_price': fields.float(u'会员价'),    
        'brand_id':fields.many2one('okgj.product.brand', u'品牌'),  
        'place': fields.char(u'产地', size=64),    
        'ean128': fields.char(u'条码'),     
        'weight': fields.float(u'重量'),  
        'mark': fields.char(u'标记'),  
        'standard_price': fields.float(u'固定成本价'),                                
        'long': fields.float(u'长'),
        'wight': fields.float(u'宽'), 
        'height': fields.float(u'高'),        
        'note': fields.char(u'备注', size=256),    
        'life_time': fields.many2one('product.product','保质期'), 
        'categ_id': fields.many2one('product.category',u'标签', required=True),  
        'seller_code':fields.float(u'供应商编号'),       
        'seller_ids': fields.many2one('product.supplierinfo', u'供应商名称'),  
        'purchase_price': fields.float(u'进货价'),                                       
    }    
    
okgj_product_demo()

class okgj_bom_demo(osv.osv_memory):
    _name = "okgj.bom.demo"
    _columns = {
        'product_id' : fields.many2one('product.product', '组合装名称',size=64,required=True),                
        'bom_code': fields.char(u'组合装编号', size=64, required=True),                
        'bom_type': fields.char(u'类别'),
        'bom_price': fields.float(u'零售价'),              
        'bom_ok_price': fields.float(u'会员价'),        
        'bom_note': fields.char(u'备注', size=256),   
        'uom_id': fields.many2one('product.uom', u'单位', required=True),   
        'line_ids': fields.one2many('okgj.bom.line', 'wizard_id',u'行数'),                                                             
    }
okgj_bom_demo()

class okgj_bom_line(osv.osv_memory):
    _name = "okgj.bom.line"
    _columns = {
        'wizard_id': fields.many2one('okgj.bom.demo','Parent Wizard'), 
        'product_id' : fields.many2one('product.product', '名称',required=True),                 
        'bom_id': fields.many2one('mrp.bom', 'Parent BoM', ondelete='cascade', select=True),                
        'bom_line_code': fields.char(u'组合装编号', size=64, required=True),  
        'bom_line_detail_code': fields.char(u'明细货品编号', size=64),                       
        'variants': fields.char(u'规格', size=64),
        'uom_id': fields.many2one('product.uom', u'单位', required=True),
        'product_qty':fields.float(u'数量'),              
        'list_price': fields.float(u'会员价'),                                         
    }
okgj_bom_line()