# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import time
import openerp.addons.decimal_precision as dp

#保质期管理
class okgj_product_expiry(osv.osv):

    def name_get(self, cr, uid, ids, context=None):
        #以下为临时引用
        if not ids:
            return []
        res = []
        reads = self.read(cr, uid, ids, ['name', 'stock_available'], context)
        for record in reads:
            name = record['name']
            if record['stock_available'] != 0:
                name += ' / ' + str(record['stock_available'])
            res.append((record['id'], name))
        ## if not ids:
        ##     return []
        ## res = []
        ## reads = self.read(cr, uid, ids, ['name'], context)
        ## for record in reads:
        ##     name = record['name']
        ##     res.append((record['id'], name))
        return res

    def _get_product_state(self, cr, uid, ids, field_names, arg, context=None):
        """
        @param field_names: Name of field
        @return: Dictionary of values
        """
        res = {}
        today = fields.date.context_today
        for m in self.browse(cr, uid, ids, context=context):
            if m.alert_date and today < m.alert_date:
                res[m.id] = 'alert'
            elif m.removal_date and today < m.removal_date:
                res[m.id] = 'remove'
            elif m.use_date and today < m.use_date:
                res[m.id] = 'use'
            elif m.life_date and today < m.life_date:
                res[m.id] = 'life'
            else:
                res[m.id] = ''
        return res
    
    _inherit = 'stock.production.lot'
    _columns = {
        'state':fields.function(_get_product_state, string=u'状态', type='selection', selection=[('',''),('life','In Life'),('use','Can Use'),('remove','Need Remove'), ('alert','Warning')], readonly=True),
    }
    _defaults = {
        'name': lambda x, y, z, c: '',
    }

    def create(self, cr, uid, vals, context=None):
        date_str = vals['name']
        product_id = vals['product_id']
        if len(date_str) != 6:
            raise osv.except_osv(_('Error!'),_("错误日期格式，格式为6位年月日"))
        try:
            pdate = datetime.strptime(date_str, '%y%m%d')
        except:
            raise osv.except_osv(_('Error!'),_("错误日期格式，格式为6位年月日"))
        new_date_str = str(20) + date_str
        vals.update({'name': new_date_str})
        life_data = self.pool.get('product.product').browse(cr, uid, product_id, context=None)
        ref = life_data.default_code
        life_time = life_data.life_time or None
        use_time = life_data.use_time or None
        removal_time = life_data.removal_time or None
        alert_time = life_data.alert_time or None
        if  life_time:
            life_str = (pdate + relativedelta(days=life_time)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            life_str = None
        if use_time:
            use_str = (pdate + relativedelta(days=use_time)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            use_str = None
        if removal_time:
            removal_str = (pdate + relativedelta(days=removal_time)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            removal_str = None
        if alert_time:
            alert_str = (pdate + relativedelta(days=alert_time)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            alert_str = None
        vals.update({'life_date': life_str})
        vals.update({'use_date': use_str})
        vals.update({'removal_date': removal_str})
        vals.update({'alert_date':alert_str})
        vals.update({'ref':ref})
        return super(okgj_product_expiry, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('name', None):
            date_str = vals['name']
            try:
                pdate = datetime.strptime(date_str, '%y%m%d')
            except:
                raise osv.except_osv(_('Error!'),_("错误日期格式，日期格式为6位年月日"))
            new_date_str = str(20) + date_str
            vals.update({'name': new_date_str})
            if vals.get('product_id', False):
                product_id = vals['product_id']
            else:
                product_id = self.browse(cr, uid, ids[0], context).product_id.id
            life_data = self.pool.get('product.product').browse(cr, uid, product_id, context=None)
            life_time = life_data.life_time or None
            use_time = life_data.use_time or None
            removal_time = life_data.removal_time or None
            alert_time = life_data.alert_time or None
            if  life_time:
                life_str = (pdate + relativedelta(days=life_time)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                life_str = None
            if use_time:
                use_str = (pdate + relativedelta(days=use_time)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                use_str = None
            if removal_time:
                removal_str = (pdate + relativedelta(days=removal_time)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                removal_str = None
            if alert_time:
                alert_str = (pdate + relativedelta(days=alert_time)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                alert_str = None
            vals.update({'life_date': life_str})
            vals.update({'use_date': use_str})
            vals.update({'removal_date': removal_str})
            vals.update({'alert_date':alert_str})
        super(okgj_product_expiry, self).write(cr, uid, ids, vals, context=context)

okgj_product_expiry()

class okgj_stock_partial_picking_line(osv.TransientModel):
    _inherit = "stock.partial.picking.line"

    _columns = {
        'okgj_lot_name': fields.char(u'生产日期', size=64),
        'purchase_price_unit':fields.float(u'单价', readonly=True, digits_compute= dp.get_precision('Product Price')),
        'picking_price_subtotal':fields.float(u'金额', readonly=True, digits_compute= dp.get_precision('Product Price')),
        'in_lot_need':fields.boolean(readonly=True, string=u'入库批次'),
        'out_lot_need':fields.boolean(readonly=True, string=u'出库批次'),
    }

    def onchange_product_qty(self, cr, uid, ids, quantity, purchase_price_unit=0, context=None):
        """
        改变数量，返回金额
        """
        if quantity is None:
            return {}
        subtotal = quantity * purchase_price_unit
        return {'value': {'picking_price_subtotal':subtotal}}

    def create(self, cr, uid, vals, context=None):
        okgj_lot_name = vals.get('okgj_lot_name', False)
        if okgj_lot_name:
            prodlot_obj = self.pool.get('stock.production.lot')
            name_check = str(20) + okgj_lot_name
            prodlot_ids = prodlot_obj.search(cr, uid, [('product_id', '=', vals.get('product_id')), ('name', '=', name_check)], context=context)
            if prodlot_ids:
                prodlot_id = prodlot_ids[0]
            else:
                prodlot_id = prodlot_obj.create(cr, uid, {
                    'product_id' : vals.get('product_id'),
                    'date' : time.strftime('%Y-%m-%d %H:%M:%S'),
                    'name' : okgj_lot_name}, context=context)
            vals.update({'prodlot_id':prodlot_id})
        return super(okgj_stock_partial_picking_line,self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        okgj_lot_name = vals.get('okgj_lot_name', False)
        if okgj_lot_name:
            prodlot_obj = self.pool.get('stock.production.lot')
            name_check = str(20) + okgj_lot_name
            product_id = self.browse(cr, uid, ids[0], context=context).product_id.id
            prodlot_ids = prodlot_obj.search(cr, uid, [('product_id', '=', product_id), ('name', '=', name_check)], context=context)
            if prodlot_ids:
                prodlot_id = prodlot_ids[0]
            else:
                prodlot_id = prodlot_obj.create(cr, uid, {
                    'product_id' : product_id,
                    'date' : time.strftime('%Y-%m-%d %H:%M:%S'),
                    'name' : okgj_lot_name}, context=context)
            vals.update({'prodlot_id':prodlot_id})
        super(okgj_stock_partial_picking_line, self).write(cr, uid, ids, vals, context=context)


class okgj_stock_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"

    def _partial_move_for(self, cr, uid, move):
        partial_move = super(okgj_stock_partial_picking, self)._partial_move_for(cr, uid, move)
        if move.purchase_line_id:
            purchase_price_unit = move.purchase_line_id.price_unit
        else:
            purchase_price_unit = 0
        quantity = move.product_qty if move.state in ('assigned','draft','confirmed') else 0
        price_unit = move.purchase_line_id.price_unit or 0
        in_lot_need = move.product_id.track_incoming or False
        out_lot_need = move.product_id.track_outgoing or False
        if move.prodlot_id:
            okgj_lot_name = move.prodlot_id.name[2:]
        else:
            okgj_lot_name = ''
        partial_move.update({
            'purchase_price_unit':purchase_price_unit,
            'okgj_lot_name':okgj_lot_name,
            'picking_price_subtotal':quantity * price_unit,
            'in_lot_need':in_lot_need,
            'out_lot_need':out_lot_need,
            })
        return partial_move

