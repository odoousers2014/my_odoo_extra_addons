class a:
    def onchange_ean(self, cr, uid, ids, picking_id=False, scan_type=False, product_qty=False, ean=False, move_ids=False, context=None):
        """ On change of ean
        @return: Dictionary of values
        """
        if (not ean) or (not picking_id):
            return {}
        product_obj = self.pool.get('product.product')
        prodlot_obj = self.pool.get('stock.production.lot')
        if not move_ids:
            raise osv.except_osv(_('错误!'), _(u"请重新扫描出库单"))            
        #move_ids数据结构:
        #[[0, False, {'product_verify_qty': 0, 'product_diff_qty': 1, 'product_id': 2, 'product_extra_qty': 0, 'product_qty': 1}], [0, False, {'product_verify_qty': 0, 'product_diff_qty': 1, 'product_id': 3, 'product_extra_qty': 0, 'product_qty': 1}]]或者[[4, 7, False], [4, 8, False]]
        #商品由于批次号，可能有多个行, prodlot_dict = {product_id:[lines, display_info]}
        prodlot_dict = {}
        for one_move in move_ids: 
            if one_move[2]['prodlot_id']:
                lot_name = prodlot_obj.read(cr, uid, one_move[2]['prodlot_id'], ['name'], context=context)['name']
                product_id = one_move[2]['product_id']
                if prodlot_dict.get(product_id, False):
                    lines = prodlot_dict[product_id][0] + 1
                    info = prodlot_dict[product_id][1] + '\n' + lot_name + ':' + str(one_move[2]['product_qty'])
                    prodlot_dict[product_id] = [lines, info]
                else:
                    lines = 1
                    info = lot_name + ':' + str(one_move[2]['product_qty'])
                    prodlot_dict[product_id] = [lines, info]
        has_product = False

        #是否已完成，如果完成，检查下一行，如果未有下一行，出错，如果有下一行，到下一行.用现有结构是否能解析问题？
        for one_move in move_ids:
            line_count = 1
            if one_move[0] == 0:
                product_id = one_move[2]['product_id']
                default_code = product_obj.read(cr, uid, product_id, ['default_code'], context=context)['default_code']
                if default_code == ean:
                    has_product = True
                    if scan_type == '1':
                        treat_state = one_move[2]['treat_state']
                        if product_id not in prodlot_dict: #未有生产批次
                            info = False
                            one_move[2]['product_verify_qty'] += product_qty
                            one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                            if one_move[2]['product_diff_qty'] > 0:
                                one_move[2]['treat_state'] = 'doing'
                            elif one_move[2]['product_diff_qty'] == 0:
                                one_move[2]['treat_state'] = 'done'
                            else:
                                one_move[2]['treat_state'] = 'wrong'
                        elif product_id in prodlot_dict:
                            if prodlot_dict[product_id][0] == 1:  #只有一个生产日期
                                info = prodlot_dict[product_id][1]
                                one_move[2]['product_verify_qty'] += product_qty
                                one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                                if one_move[2]['product_diff_qty'] > 0:
                                    one_move[2]['treat_state'] = 'doing'
                                elif one_move[2]['product_diff_qty'] == 0:
                                    one_move[2]['treat_state'] = 'done'
                                else:
                                    one_move[2]['treat_state'] = 'wrong'
                            else:  #多个生产批次
                                treat_state = one_move[2]['treat_state']
                                info = prodlot_dict[product_id][1]
                                if treat_state == 'todo':
                                    one_move[2]['product_verify_qty'] += product_qty
                                    one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                                    if one_move[2]['product_diff_qty'] > 0:
                                        one_move[2]['treat_state'] = 'doing'
                                    elif one_move[2]['product_diff_qty'] == 0:
                                        one_move[2]['treat_state'] = 'done'
                                elif treat_state == 'done':  ##本行已完成，进入下一行，如果未有下一行，wrong!
                                    lot_line_count = prodlot_dict[product_id][0]
                                    if line_count < lot_line_count:
                                        line_count += 1 ##到下一行进行处理
                                        break
                                    else:  ##已到最后一行
                                        one_move[2]['product_verify_qty'] += product_qty
                                        one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                                        one_move[2]['treat_state'] = 'wrong'
                                elif one_move[2]['treat_state'] = 'wrong':
                                    one_move[2]['product_verify_qty'] += product_qty
                                    one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                                    one_move[2]['treat_state'] = 'wrong'
                    elif scan_type == '2':
                        one_move[2]['product_extra_qty'] += product_qty
                    else:
                        return {'warning':{'title':_('未知扫描方式'), 'message':_('请选择扫描方式')}}

            else:
                 return {'warning':{'title':_('请勿确认有差异的订单'), 'message':_('请重新扫描发货单并再次复核')}}
        if has_product:
            return {'value': {'move_ids':move_ids, 'ean':False, 'product_qty':1, 'info':info}}
        else:
            return {'value':{'name':False}, 'warning':{'title':_('条码错误'), 'message':_('未找到相应商品')}}

















# -*- coding: utf-8 -*-
from osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import re

class okgj_product_rack(osv.osv):
    _name = "okgj.product.rack"
    _columns = {
        'name':fields.char(u'货位名称', size=64, required=True),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True),
        'pick_product_rack_ids':fields.many2many('product.product', 'rack_usage_rel1', 'product_id', 'rack_id', string=u'拣货商品', readonly=True),
        'store_product_rack_ids':fields.many2many('product.product', 'rack_usage_rel2', 'product_id', 'rack_id', string=u'存货商品', readonly=True),
    }
    
    def unlink(self, cr, uid, ids, context=None):
        raise osv.except_osv(_('Invalid Action!'), _('货位不允许删除'))
    
okgj_product_rack()

class okgj_product_product(osv.osv):
    _name = "product.product"
    _columns = {
        'product_pick_rack_ids':fields.many2many('okgj.product.rack', 'rack_usage_rel1', 'rack_id', 'product_id', string=u'拣货货位', readonly=True),
        'product_store_rack_ids':fields.many2many('okgj.product.rack', 'rack_usage_rel2', 'rack_id', 'product_id', string=u'存货货位', readonly=True),
    }
okgj_product_product()

#货位用途
class okgj_product_rack_usage(osv.osv):
    _name = "okgj.product.rack.usage"
    _columns = {
        'rack_id':fields.many2one('okgj.product.rack', u'货位', required=True),
        'usage':fields.selection([
            ('pick', u'拣'),
            ('store', u'存'),
        ], string='状态', required=True),
        'product_id':fields.many2one('product.product', string=u'商品', required=True, domain=[('is_group_product', '=', False)]),
    }
    _sql_constraints = [
        ('rack_usage_product_uniq', 'unique(name, usage, product_id)', 'The combine of rack, usage, product must be unique!'),
    ]

    #与ERP部门沟通，一个商品在一个物流中心只有一个拣货货位，一个存货货位
    def create(self, cr, uid, vals, context=None):
        usage_id = super(okgj_product_rack_usage, self).create(cr, uid, vals, context=context)
        rack_id = vals.get('rack_id', False)
        usage = vals.get('usage', 'pick')
        product_id = vals.get('product_id', False)
        rack_obj = self.pool.get('okgj.product.rack')
        rack_data = rack_obj.browse(cr, uid, rack_id, context=context)
        if usage == 'pick':
            pick_products = rack_data.pick_product_rack_ids
            change_state = True
            for one_product in pick_products:
                if one_product.id == product_id:
                    change_state = False
                    break
            if change_state:
                rack_obj.write(cr, uid, rack_id, {'pick_product_rack_ids':(4, product_id)}, context=context)
        if usage == 'store':
            store_products = rack_data.store_product_rack_ids
            change_state = True
            for one_product in store_products:
                if one_product.id == product_id:
                    change_state = False
                    break
            if change_state:
                rack_obj.write(cr, uid, rack_id, {'store_product_rack_ids':(4, product_id)}, context=context)
            return usage_id
    
    def write(self, cr, uid, ids, vals, context=None):
        super(okgj_product_rack_usage, self).write(cr, uid, ids, vals, context=context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        rack_obj = self.pool.get('okgj.product.rack')
        rack_data = rack_obj.browse(cr, uid, ids, context=context)
        for one_rack in rack_data:
            rack_id = one_rack.rack_id
            usage = one_rack.usage
            product_id = one_rack.product_id
            if usage == 'pick':
                pick_products = one_rack.pick_product_rack_ids
                change_state = True
                for one_product in pick_products:
                    if one_product.id == product_id:
                        change_state = False
                        break
                if change_state:
                    rack_obj.write(cr, uid, rack_id, {'pick_product_rack_ids':(4, product_id)}, context=context)
            if usage == 'store':
                store_products = one_rack.store_product_rack_ids
                change_state = True
                for one_product in store_products:
                    if one_product.id == product_id:
                        change_state = False
                        break
                if change_state:
                    rack_obj.write(cr, uid, rack_id, {'store_product_rack_ids':(4, product_id)}, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        usage_data = self.browse(cr, uid, ids, context=context)
        rack_obj = self.pool.get('okgj.product.rack')
        for one_usage in usage_data:
            rack_id = one_usage.rack_id
            product_id = one_usage.product_id
            usage = one_usage.usage
            if usage == 'pick':
                rack_obj.write(cr, uid, rack_id,  {'pick_product_rack_ids':(3, product_id)}, context=context)
            if usage == 'store':
                rack_obj.write(cr, uid, rack_id,  {'store_product_rack_ids':(3, product_id)}, context=context)
        return super(okgj_product_rack_usage, self).unlink(cr, uid, ids, context=context)

okgj_product_rack_usage()


#货位生成wizard
class okgj_product_rack_gen(osv.osv_memory):
    _name = "okgj.product.rack.gen"
    _columns = {
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True),
        #长宽高?
    }
okgj_product_rack_gen()
