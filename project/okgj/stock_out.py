# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

#外挂与箱
class okgj_stock_picking_container(osv.osv):
    _name = "okgj.stock.picking.container"
    _columns = {
        'name':fields.char(u'编号', size=128),
        'product_id':fields.many2one('product.product', u'商品'),
        'product_qty':fields.integer(u'数量',),
        'type': fields.selection([
            ('box', u'箱子'),
            ('extra', u'外挂'),
            ('others', u'其它'),
            ], u'类别', required=True),
        'product_variant':fields.related('product_id', 'variants', type='char', string=u'规格', readonly=True),
        'picking_id':fields.many2one('stock.picking.out', 'Picking'),
    }
okgj_stock_picking_container()

#拣货复核 view => #简要的stock.move.line确认界面，（单号，商品名称，规格型号，数量）
class okgj_stock_picking_temp(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        #复核单字段
        'okgj_box':fields.char(u'箱号', size=128, help=u'物流箱号，多个可用逗号分开'),
        'okgj_weight':fields.float(u'商品重量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'real_weight':fields.float(u'含箱重量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'okgj_container':fields.text(u'外挂'),
	'okgj_container_explain':fields.text(u'外挂说明'), 
   }

okgj_stock_picking_temp()
    
class okgj_stock_picking(osv.osv):
    _inherit = "stock.picking.out"
    _name = "stock.picking.out"
    _table = "stock_picking"
    _columns = {
        #复核单字段
        'okgj_box':fields.char(u'箱号', size=128, help=u'物流箱号，多个可用逗号分开'),
        'okgj_weight':fields.float(u'商品重量', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'real_weight':fields.float(u'含箱重量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'okgj_container':fields.text(u'外挂'),
	'okgj_container_explain':fields.text(u'外挂说明'),   
 }

    def create_box_info(self, cr, uid, ids, datas, context=None):
        '''
        创建装箱信息
        '''
        if ids and isinstance(ids, (list, tuple)):
            ## 一次只处理一个出库单
            ids = ids[0]
        box_info_data = [(0, 0, i) for i in datas]
        box_info_obj = self.pool.get("okgj.stock.picking.box.info")
        box_info_obj.create(cr, uid, {
            'picking_out_id':ids,
            'box_info_ids':box_info_data,
            }, context=context)
        return True


    def print_final_sale(self, cr, uid, ids, context=None):
        '''
        最终给客户的送货单
        This function prints the OKGJ Final sales order 
        '''
        print_order_ids = []
        for one_picking in self.browse(cr, uid, ids, context=context):
            #获取销售订单
            if one_picking.sale_id:
                print_order_ids.append(one_picking.sale_id.id)
        #进行多打印?需测试
        datas = {
            'model': 'sale.order',
            'ids': print_order_ids,
            'form': self.pool.get('sale.order').read(cr, uid, print_order_ids, context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'okgj.final.sale.print', 'datas': datas, 'nodestroy': True}


    ## def print_final_return_sale(self, cr, uid, ids, context=None):
    ##     '''
    ##     最终给客户的送货单
    ##     This function prints the OKGJ Final sales order 
    ##     '''
    ##     print_order_ids = []
    ##     for one_picking in self.browse(cr, uid, ids, context=context):
    ##         #获取销售订单
    ##         if one_picking.sale_return_id:
    ##             print_order_ids.append(one_picking.sale_return_id)
    ##     #进行多打印?需测试
    ##     datas = {
    ##         'model': 'okgj.sale.return',
    ##         'ids': print_order_ids,
    ##         'form': self.read(cr, uid, print_order_ids, context=context),
    ##     }
    ##     return {'type': 'ir.actions.report.xml', 'report_name': 'okgj.sale.return.report', 'datas': datas, 'nodestroy': True}

okgj_stock_picking()

## 装箱信息
class okgj_stock_picking_box_info(osv.osv):
    _name = "okgj.stock.picking.box.info"
    _description = 'OKGJ Stock Picking Box Info'
okgj_stock_picking_box_info()

class okgj_stock_move_box_info(osv.osv):
    _name = "okgj.stock.box.info"
    _description = 'OKGJ Stock Move Box Info'
    _order = "okgj_packing_box asc"
    _columns = {
        'picking_box_id': fields.many2one('okgj.stock.picking.box.info', u'装箱单'),
        'move_id': fields.many2one('stock.move', u'出库明细'),
        'product_id': fields.related('move_id', 'product_id',
                                     type='many2one',
                                     relation='product.product',
                                     string=u'商品', store=True),
        'product_qty': fields.integer('数量'),
        'okgj_packing_box':fields.char(u'物流箱号', size=128),
    }
okgj_stock_move_box_info()

class okgj_stock_picking_box_info(osv.osv):
    _inherit = "okgj.stock.picking.box.info"
    _columns = {
        'picking_out_id': fields.many2one('stock.picking.out', u'出库单号'),
        'box_info_ids':fields.one2many('okgj.stock.box.info', 'picking_box_id', u'detail'),
    }
okgj_stock_picking_box_info()
