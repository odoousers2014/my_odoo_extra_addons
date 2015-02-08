#-*-coding:utf-8-*-

from openerp.osv import osv, fields
from openerp import tools

#===============================================================================
# class stock_warehouse_orderpoint(osv.osv):
#     _inherit = "stock.warehouse.orderpoint"
#     
#     def _get_qty(self, cr, uid, ids, field_name, rag=None, context=None):
#         wrsa_obj = self.pool.get('wms.report.stock.available')
#         
#         res = dict([(i, {}.fromkeys(field_name, 0.0)) for i in ids])
#         for o in self.browse(cr, uid, ids, context=context):
#             info = wrsa_obj.get_qty(cr, uid, o.product_id.id, o.location_id.id, context=context)
#             for f in field_name:
#                 if f == 'qty_available':
#                     res[o.id][f] = info['product_qty']
#                 elif f == 'virtual_available':
#                     res[o.id][f] = info['product_qty_v']
#         return res
#     
#     _columns = {
#         'qty_available': fields.function(_get_qty, type='float', string=u'实际数量', multi='get_qty', readonly=True),
#         'virtual_available': fields.function(_get_qty, type='float', string=u'预测数量', multi='get_qty', readonly=True),
#     }
#     
#     _sql_constraints = [
#         ('sku_location_uniq', 'unique(location_id,product_id)', u'SKU和库位不能重复!'),
#     ]
# 
# stock_warehouse_orderpoint()
# 
# 
# class wizard_swo(osv.osv_memory):
#     _name = 'wizard.swo'
#     _columns = {
#         'name': fields.char('Name', size=10),
#         'safe_section': fields.selection([('all', u'所有的'), ('safe', u'库存安全的'), ('virtual_unsafe', u'预测库存告急的'), ('qty_unsafe', u'实际库存告急的')], u'查看选项'),
#     }
#     
#     _defaults = {
#         'safe_section': 'all',
#     }
#     
#     def apply(self, cr, uid, ids, context=None):
#         swo_obj = self.pool.get('stock.warehouse.orderpoint')
#         wizard = self.browse(cr, uid, ids[0], context=context)
#         
#         swo_ids = swo_obj.search(cr, uid, [], context=context)
#         to_ids = []
#         if wizard.safe_section == 'all':
#             to_ids = swo_ids
#         else:
#             for info in swo_obj.read(cr, uid, swo_ids, ['virtual_available', 'product_min_qty', 'qty_available'], context=context):
#                 if wizard.safe_section == 'safe':
#                     if info['virtual_available'] > info['product_min_qty'] and info['qty_available'] > info['product_min_qty']:
#                         to_ids.append(info['id'])
#                 elif wizard.safe_section == 'virtual_unsafe':
#                     if info['virtual_available'] <= info['product_min_qty']:
#                         to_ids.append(info['id'])
#                 elif wizard.safe_section == 'qty_unsafe':
#                     if info['qty_available'] <= info['product_min_qty']:
#                         to_ids.append(info['id'])
# 
#         return {
#             'name': (u'库存预警'),
#             'view_type': 'form',
#             "view_mode": 'tree,form',
#             'res_model': 'stock.warehouse.orderpoint',
#             "domain": [('id', 'in', to_ids)],
#             'type': 'ir.actions.act_window',
#         }
# wizard_swo()
#===============================================================================


class stock_warehouse_orderpoint_report(osv.osv):
    _name = 'stock.warehouse.orderpoint.report'
    _auto = False
    _order = 'ratio_qty'
    _columns = {
        'product_id': fields.many2one('product.product', string='产品', readonly=True),
        'product_min_qty': fields.float(string=u'预警数量', readonly=True),
        'product_qty': fields.float(string=u'库存数量', readonly=True),
        'product_qty_l': fields.float(string=u'锁定数量', readonly=True),
        'product_qty_a': fields.float(string=u'可用数量', readonly=True),
        'product_qty_v': fields.float(string=u'预测数量', readonly=True),
        'location_id': fields.many2one('stock.location', string=u'库位', readonly=True),
        'warn_qty': fields.boolean(u'实际库存预警'),
        'warn_qty_v': fields.boolean(u'在途库存预警'),
        'warn_qty_a': fields.boolean(u'可用库存预警'),
        'ratio_qty': fields.float(string=u'安全系数', readonly=True, help=u"实际库存/预警数量"),
    }
    
    def init(self, cr):
        """"""
        tools.drop_view_if_exists(cr, 'stock_warehouse_orderpoint_report')
        cr.execute("""
            CREATE OR REPLACE VIEW stock_warehouse_orderpoint_report AS (
                SELECT
                    swo.id AS id,
                    swo.product_id,
                    swo.product_min_qty,
                    swo.location_id,
                    wms.product_qty,
                    wms.product_qty_l,
                    wms.product_qty_a,
                    wms.product_qty_v,
                    wms.product_qty   < swo.product_min_qty AS warn_qty,
                    wms.product_qty_a < swo.product_min_qty AS warn_qty_a,
                    wms.product_qty_v < swo.product_min_qty AS warn_qty_v,
                    wms.product_qty   / swo.product_min_qty AS ratio_qty
                FROM stock_warehouse_orderpoint AS swo
                    LEFT JOIN wms_report_stock_available AS wms ON (wms.product_id=swo.product_id AND wms.location_id=swo.location_id)
            )
        """)

stock_warehouse_orderpoint_report()


#################################################################