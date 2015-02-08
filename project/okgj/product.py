# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta
from datetime import datetime
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import logging

_logger = logging.getLogger(__name__)

class okgj_product_category(osv.osv):

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            ids = self.search(cr, user, [('name', '=', name)]+ args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, user, [('okgj_code', '=', name)]+ args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result

    _inherit = "product.category"
    _columns = {
        'okgj_code': fields.char(u'分类号', size=32, select=True),
    }
okgj_product_category()

class okgj_product_rack(osv.osv):
    _name = "okgj.product.rack"
    _description = "OKGJ Warehouse Rack"
    _columns = {
        'name':fields.char(u'货位名称', size=64, required=True),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True),
        'pick_product_rack_ids':fields.many2many('product.product', 'rack_usage_rel1', 'product_id', 'rack_id', string=u'拣货商品', readonly=True),
        'store_product_rack_ids':fields.many2many('product.product', 'rack_usage_rel2', 'product_id', 'rack_id', string=u'存货商品', readonly=True),
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique(name, warehouse_id)', 'Name must be unique in one warehouse!'),
    ]

    ## def name_get(self, cr, uid, ids, context=None):
    ##     if isinstance(ids, (list, tuple)) and not len(ids):
    ##         return []
    ##     if isinstance(ids, (long, int)):
    ##         ids = [ids]
    ##     reads = self.read(cr, uid, ids, ['name','warehouse_id'], context=context)
    ##     res = []
    ##     for record in reads:
    ##         warehouse = record['warehouse_id']
    ##         if warehouse:
    ##             newname = record['warehouse_id'][1] +' / '+ record['name']
    ##         else:
    ##             newname = record['name']
    ##         res.append((record['id'], newname))
    ##     return res

    ## def unlink(self, cr, uid, ids, context=None):
    ##     raise osv.except_osv(_('Invalid Action!'), _('货位不允许删除'))

okgj_product_rack()

#货位用途
class okgj_product_rack_usage(osv.osv):
    _name = "okgj.product.rack.usage"
    _description = "OKGJ Warehouse Rack Usage"
    _columns = {
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心'),
        'rack_id':fields.many2one('okgj.product.rack', u'货位', required=True),
        'usage':fields.selection([
            ('pick', u'拣'),
            ('store', u'存'),
        ], string=u'状态', required=True),
        'product_id':fields.many2one('product.product', string=u'商品', required=True, domain=[('is_group_product', '=', False)]),
        ## 'rack_id':fields.many2one('okgj.product.rack', u'货位', required=True),
        ## 'usage':fields.selection([
        ##     ('pick', u'拣'),
        ##     ('store', u'存'),
        ## ], string=u'状态', required=True),
        ## 'product_ids':fields.many2many('product.product', 'rack_usage_rel', 'rack_id', 'product_id', string=u'商品', domain=[('is_group_product', '=', False)]),
    }
    _defaults = {
        'usage': lambda *a: 'pick',
    }

    _sql_constraints = [
        ('product_rack_usage_unique', 'unique(rack_id,product_id,usage)', 'The combine of rack, usage, product must be unique!'),
    ]
    
    def _check_rack_warehouse_id(self, cr, uid, ids, context=None):
        rack_obj = self.pool.get('okgj.product.rack')
        for rec in self.browse(cr, uid, ids, context=context):
            rack_warehouse_id = rec.rack_id.warehouse_id.id
            rack_name = rec.rack_id.name
            if rack_warehouse_id != rec.warehouse_id.id:
                new_rack_ids = rack_obj.search(cr, uid, [('name', '=', rack_name), ('warehouse_id', '=', rec.warehouse_id.id)])
                if new_rack_ids:
                    self.write(cr, uid, ids, {'rack_id':new_rack_ids[0]})
                else:
                    return False
        return True
    _constraints = [(_check_rack_warehouse_id, u'物流中心不存在该货位!', [u'物流中心', u'货位'])]
    
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
                rack_obj.write(cr, uid, rack_id, {'pick_product_rack_ids':[(4, product_id)]}, context=context)
        if usage == 'store':
            store_products = rack_data.store_product_rack_ids
            change_state = True
            for one_product in store_products:
                if one_product.id == product_id:
                    change_state = False
                    break
            if change_state:
                rack_obj.write(cr, uid, rack_id, {'store_product_rack_ids':[(4, product_id)]}, context=context)
        return usage_id
    
    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        rack_usage_dict = {}
        product_rack_dict = {'pick':'product_pick_rack_ids', 'store':'product_store_rack_ids'}
        for usage_id in ids:
            one_data = self.read(cr, uid, usage_id, ['rack_id', 'product_id', 'usage', 'warehouse_id'], load="_classic_write", context=context)
            rack_usage_dict[usage_id] = one_data
        super(okgj_product_rack_usage, self).write(cr, uid, ids, vals, context=context)
        rack_obj = self.pool.get('okgj.product.rack')
        product_obj = self.pool.get('product.product')
        usage_data = self.browse(cr, uid, ids, context=context)
        for one_usage in usage_data:
            origin_product_rack = rack_usage_dict.get(one_usage.id, {})
            origin_rack_id = origin_product_rack.get('rack_id', False)
            origin_product_id = origin_product_rack.get('product_id', False)
            origin_usage = origin_product_rack.get('usage', False)
            origin_warehouse_id = origin_product_rack.get('warehouse_id', False)
            product_rack_field = product_rack_dict.get(origin_usage, False)
            rack_id = one_usage.rack_id.id
            usage = one_usage.usage
            product_id = one_usage.product_id.id
            warehouse_id = one_usage.warehouse_id.id
            rack_data = rack_obj.browse(cr, uid, rack_id, context=context)
            if usage == 'pick':
                pick_products = rack_data.pick_product_rack_ids
                change_state = True
                for one_product in pick_products:
                    if one_product.id == product_id and origin_warehouse_id == warehouse_id:
                        change_state = False
                        break
                if change_state:
                    if product_rack_field and origin_product_id:
                        product_obj.write(cr, uid, origin_product_id, {product_rack_field:[(3, origin_rack_id)]}, context=context)
                    rack_obj.write(cr, uid, rack_id, {'pick_product_rack_ids':[(4, product_id)]}, context=context)
            if usage == 'store':
                store_products = rack_data.store_product_rack_ids
                change_state = True
                for one_product in store_products:
                    if one_product.id == product_id and origin_warehouse_id == warehouse_id:
                        change_state = False
                        break
                if change_state:
                    if product_rack_field and origin_product_id:
                        product_obj.write(cr, uid, origin_product_id, {product_rack_field:[(3, origin_rack_id)]}, context=context)
                    rack_obj.write(cr, uid, rack_id, {'store_product_rack_ids':[(4, product_id)]}, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        usage_data = self.browse(cr, uid, ids, context=context)
        rack_obj = self.pool.get('okgj.product.rack')
        for one_usage in usage_data:
            rack_id = one_usage.rack_id.id
            product_id = one_usage.product_id.id
            usage = one_usage.usage
            if usage == 'pick':
                rack_obj.write(cr, uid, rack_id,  {'pick_product_rack_ids':[(3, product_id)]}, context=context) 
            if usage == 'store':
                rack_obj.write(cr, uid, rack_id,  {'store_product_rack_ids':[(3, product_id)]}, context=context)
        return super(okgj_product_rack_usage, self).unlink(cr, uid, ids, context=context)
    
okgj_product_rack_usage()

class okgj_product_brand(osv.osv):
    _name = "okgj.product.brand"
    _description = "OKGJ Product Brand"
    _columns = {
        'name':fields.char(u'品牌', size=32),
    }
okgj_product_brand()

class okgj_product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'list_price': fields.float('Sale Price', digits_compute=dp.get_precision('Product Price'), help="Base price to compute the customer price. Sometimes called the catalog price.", track_visibility='onchange'),
        'standard_price': fields.float('Cost', digits_compute=dp.get_precision('Product Price'), help="Cost price of the product used for standard stock valuation in accounting and used as a base price on purchase orders.", groups="base.group_user", track_visibility='onchange'),
    }
okgj_product_template()


class okgj_warehouse_sprice(osv.osv):
    """
    因组合品即将退出，将不再保存组合品价格，如确有需要，通过product.product中get_okgj_group_product_warehouse_cost方法获取
    """
    _name = "okgj.warehouse.sprice"
    _description = "Warehouse_Cost"
    _columns = {
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心'),
        'standard_price': fields.float(u'成本', digits_compute=dp.get_precision('Product Price')),
        'product_id':fields.many2one('product.product', u'商品'),
    }
okgj_warehouse_sprice()

class okgj_product_product(osv.osv):

    def _get_okgj_group_product_warehouse_cost(self, cr, uid, warehouse_id, product_ids, context=None):
        """ 获取组合品多物流中心成本价, 仅支持一级组合
        @param warehouse_id: 
        @param product_ids: [1, 3, 5]
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        result = {}.fromkeys(product_ids, 0.0)
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        for one_product in self.browse(cr, uid, product_ids, context=context):
            if one_product.is_group_product == False:
                continue
            bom_id = bom_obj.search(cr, uid, [
                ('type', '=', 'phantom'),
                ('product_id', '=', one_product.id),
                ('bom_id', '=', False)], context=context)
            if bom_id:
                okgj_cost = 0
                bom_data = bom_obj.browse(cr, uid, bom_id[0], context=context)
                parent_qty = bom_data.product_qty
                parent_product_uom = bom_data.product_uom.id
                parent_product_default_uom = bom_data.product_id.uom_id.id
                if parent_product_default_uom != parent_product_uom:
                    parent_qty = uom_obj._compute_qty(cr, uid, parent_product_uom, parent_qty, parent_product_default_uom)
                for one_line in bom_data.bom_lines:
                    sub_product_qty = one_line.product_qty
                    sub_product_uom = one_line.product_uom.id
                    sub_product_default_uom = one_line.product_id.uom_id.id
                    if sub_product_default_uom != sub_product_uom:
                        sub_product_qty = uom_obj._compute_qty(cr, uid, sub_product_uom, sub_product_qty, sub_product_default_uom)
                    sprice = self._get_okgj_product_warehouse_cost(cr, uid, warehouse_id, one_line.product_id.id, context=context).get(one_line.product_id.id, 0.0)
                    okgj_cost += sprice * sub_product_qty
                result[one_product.id] = okgj_cost / parent_qty
        return result

    def _get_okgj_product_warehouse_cost(self, cr, uid, warehouse_id, product_ids, context=None):
        """
        获取物流中心正常商品成本
        入参:warehouse_id, [product_ids]，返回商品{product_id:product_cost}
        """
        if isinstance(product_ids, (int, long)):
            product_ids = [product_ids]
        product_ids = tuple(product_ids)

        sql_str = """
        select product_id, standard_price
        from okgj_warehouse_sprice
        where warehouse_id = %s and product_id in %s
        """
        cr.execute(sql_str, (warehouse_id, product_ids))
        results = {}
        for i in cr.fetchall():
            results.update({i[0] : i[1]})
        return results
    
    def get_okgj_product_warehouse_cost(self, cr, uid, warehouse_id, product_ids, context=None):
        """
        获取物流中心商品成本（各种商品）
        入参:warehouse_id, [product_ids]，返回商品{product_id:product_cost}
        """
        group_product_ids = []
        single_product_ids = []
        if isinstance(product_ids, (int, long)):
            product_ids = [product_ids]
        results = {}.fromkeys(product_ids, 0.0)
        for one_product in self.browse(cr, uid, product_ids, context=context):
            if one_product.is_group_product == True:
                group_product_ids.append(one_product.id)
            else:
                single_product_ids.append(one_product.id)
        if group_product_ids:
            results.update(self._get_okgj_group_product_warehouse_cost(cr, uid, warehouse_id, group_product_ids, context=context))
        if single_product_ids:
            results.update(self._get_okgj_product_warehouse_cost(cr, uid, warehouse_id, single_product_ids, context=context))
        return results

    def get_supplier_warehouse_price(self, cr, uid, supplier_id, product_ids, warehouse_id=False, context=None):
        """
        获取供应商商品价格，如提供warehouse_id，将按物流中心进行返回
        @param supplier_id: 
        @param product_ids: int or list,
        @param warehouse_id:
        @return: Dictionary of values. {'product_id':price, 100:9.00}

        """
        result = {}
        if product_ids and warehouse_id and supplier_id:
            if isinstance(product_ids, (int, long)):
                product_ids = [product_ids]
            product_ids = tuple(product_ids)
            # 默认供应商价格列表仅一条，后续有多条时要确定参数:product_qty数量
            sql_str = """SELECT ps.product_id, pr.price 
                        from pricelist_partnerinfo pr
                        LEFT JOIN product_supplierinfo ps on (pr.suppinfo_id=ps.id)
                        WHERE ps.product_id in %s and ps.warehouse_id=%s and ps.name=%s 
                        """
            cr.execute(sql_str, (product_ids, warehouse_id, supplier_id))        
            for i in cr.fetchall():
                result.update({i[0] : i[1]})
        return result

    def _get_okgj_product_cost(self, cr, uid, ids, arg, context=None):
        """ 获取单品成本价,直接读取standard_price
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        result = {}.fromkeys(ids, 0.0)
        for one_product in self.browse(cr, uid, ids, context=context):
            result[one_product.id] = one_product.standard_price
        return result

    def _get_okgj_group_product_cost(self, cr, uid, ids, arg, context=None):
        """ 组合品成本价按单品总计计算
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        result = {}.fromkeys(ids, 0.0)
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        for one_product in self.browse(cr, uid, ids, context=context):
            #仅支持一级组合
            bom_id = bom_obj.search(cr, uid, [ ('product_id', '=', one_product.id),('bom_id', '=', False)], context=context)
            if bom_id:
                okgj_cost = 0
                bom_data = bom_obj.browse(cr, uid, bom_id[0], context=context)
                parent_qty = bom_data.product_qty
                parent_product_uom = bom_data.product_uom.id
                parent_product_default_uom = bom_data.product_id.uom_id.id
                if parent_product_default_uom != parent_product_uom:
                    parent_qty = uom_obj._compute_qty(cr, uid, parent_product_uom, parent_qty, parent_product_default_uom)
                for one_line in bom_data.bom_lines:
                    sub_product_qty = one_line.product_qty
                    sub_product_uom = one_line.product_uom.id
                    sub_product_default_uom = one_line.product_id.uom_id.id
                    if sub_product_default_uom != sub_product_uom:
                        sub_product_qty = uom_obj._compute_qty(cr, uid, sub_product_uom, sub_product_qty, sub_product_default_uom)
                    okgj_cost += one_line.product_id.standard_price * sub_product_qty
                result[one_product.id] = okgj_cost / parent_qty
        return result

    def _get_okgj_cost(self, cr, uid, ids, field_names, arg, context=None):
        """ 依产品类型计算成本
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        product_cost = {}.fromkeys(ids, 0.0)
        group_ids = []
        product_ids = []
        for one_product in self.browse(cr, uid, ids, context):
            #jon:oem no_group_product user sum(bom)price too.
            #if one_product.is_group_product:
            if one_product.is_group_product or one_product.okgj_type == 'oem':
                group_ids.append(one_product.id)
            else:
                product_ids.append(one_product.id)               
        product_cost = self._get_okgj_product_cost(cr, uid, product_ids, context)
        group_cost = self._get_okgj_group_product_cost(cr, uid, group_ids, context)
        product_cost.update(group_cost)
        return product_cost


    ##组合商品保存时检查
    def _check_supply_method(self, cr, uid, ids, context=None):
        for one_record in self.browse(cr, uid, ids, context):
            if (one_record.is_group_product and one_record.supply_method != 'produce'): 
                # or ((not one_record.is_group_product) and one_record.supply_method != 'buy'):
                return False
            #jon oem: no_group_product can be 'produce' also.
            if (not one_record.is_group_product) and one_record.supply_method != 'buy' and one_record.okgj_type != 'oem':
                return False
        return True

    _inherit = "product.product"
    _columns = {
        'create_date': fields.datetime(u'创建时间', readonly=True),
        'other_price': fields.float(u'市场价', digits_compute=dp.get_precision('Product Price'),  track_visibility='onchange'),
        'product_pick_rack_ids':fields.many2many('okgj.product.rack', 'rack_usage_rel1', 'rack_id', 'product_id', string=u'拣货货位', readonly=True),
        'product_store_rack_ids':fields.many2many('okgj.product.rack', 'rack_usage_rel2', 'rack_id', 'product_id', string=u'存货货位', readonly=True),
        'brand_id':fields.many2one('okgj.product.brand', u'品牌'),
        'is_group_product':fields.boolean(u'组合品'),
        'min_qty': fields.integer(u'最小包装数'),
        'okgj_cost_price': fields.function(_get_okgj_cost, type='float', string=u'OKGJ成本价'),
        'warehouse_sprice_ids':fields.one2many('okgj.warehouse.sprice', 'product_id', u='各中心成本'),
        'is_okkg':fields.boolean(u'是否快购商品'),
        'okkg_price': fields.float(u'OK快购价', digits_compute=dp.get_precision('Product Price'),  track_visibility='onchange'),
        'okgj_type':fields.selection([('oem','OEM')], string=u'OKGJ产品类型'),
        'rebate':fields.float(u'返点%',digits_compute=dp.get_precision('Account')),
    }
    _defaults = {
        'is_group_product': lambda *a: False,
    }
    _sql_constraints = [
        ('default_code_uniq', 'unique(default_code)', 'Ref must be unique!'),
    ]

    _constraints = [
        (_check_supply_method, u'组合商品的供应方法必须为生产!', [u'供应方法'])
    ]

    def create(self, cr, uid, vals, context=None):
        product_id = super(okgj_product_product,self).create(cr, uid, vals, context=context)
        form = self.browse(cr, uid, product_id, context=context)
        sellers = form.seller_ids
        partner_obj = self.pool.get('res.partner')
        for one_sell in sellers:
            partner_obj.write(cr, uid, one_sell.name.id, {'product_ids':[(4, product_id)]}, context=context)
        return product_id
    
    def write(self, cr, uid, ids, vals, context=None):
        super(okgj_product_product, self).write(cr, uid, ids, vals, context=context)
        if vals.get('seller_ids'):
            form = self.browse(cr, uid, ids, context=context)
            partner_obj = self.pool.get('res.partner')
            for one_form in form:
                sellers = one_form.seller_ids
                for one_sell in sellers:
                    partner_obj.write(cr, uid, one_sell.name.id, {'product_ids':[(4, one_form.id)]}, context=context)
        return True

    def get_group_product_available(self, cr, uid, group_product_ids, context=None):
        """ Finds the incoming and outgoing quantity of product.
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        local_context = context
        res = {}.fromkeys(group_product_ids, 0.0)
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')

        for one_id in group_product_ids:
            #虚拟商品不考虑起始时间
            bom_id = bom_obj.search(cr, uid, [('type', '=', 'phantom'), ('product_id', '=', one_id), ('bom_id', '=', False)], context=context)
            if not bom_id:
                product_name = product_obj.name_get(cr, uid, [one_id], local_context)[0][1]          
                _logger.info('Failed to fetch bom %s', product_name)
                res.update({one_id:0})
                continue
            elif len(bom_id) > 1:
                product_name = product_obj.name_get(cr, uid, [one_id], local_context)[0][1]          
                _logger.info('Found more boms %s', product_name)
                res.update({one_id:0})
                continue
            else:
                #每个单品数量
                child_bom_id = bom_obj.search(cr, uid, [('bom_id', '=', bom_id[0])], context=context)
                child_bom_datas = bom_obj.read(cr, uid, child_bom_id, ['product_qty','product_id','product_uom'], local_context)
                group_product_qty = []       
                for one_line in child_bom_datas:
                    #库存现有数量
                    #sub_product_stock_qty = product_obj.get_product_available(self, cr, uid, one_line['product_id'][0], context=context)
                    sub_product_stock_qty = super(okgj_product_product, self).get_product_available(cr, uid, [one_line['product_id'][0]], local_context)[one_line['product_id'][0]]
                    #物料所需数量
                    sub_product_need_qty = one_line['product_qty']      
                    sub_product_default_uom = product_obj.read(cr, uid, one_line['product_id'][0], ['uom_id'], local_context)['uom_id'][0]
                    if sub_product_default_uom != one_line['product_uom'][0]:
                        sub_product_need_qty = uom_obj._compute_qty(cr, uid, one_line['product_uom'][0], sub_product_need_qty, sub_product_default_uom)
                    if sub_product_need_qty > 0:
                        #组合品数量
                        temp_qty = sub_product_stock_qty//sub_product_need_qty  
                        group_product_qty.append(temp_qty)  
                #排序后取最小数量
                if group_product_qty:
                    group_product_qty.sort()
                    res.update({one_id:group_product_qty[0]})
        return res     

    #扩展至虚拟品数量计算
    def get_product_available(self, cr, uid, ids, context=None):
        """ Finds whether product is available or not in particular warehouse.
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        local_context = context
        group_ids = []
        product_ids = []
        for one_product in self.browse(cr, uid, ids, local_context):
            if one_product.is_group_product:
                group_ids.append(one_product.id)
            else:
                product_ids.append(one_product.id)               
        group_avail = self.get_group_product_available(cr, uid, group_ids, local_context)
        product_avail = super(okgj_product_product,self).get_product_available(cr, uid, product_ids, local_context)
        product_avail.update(group_avail)
        return product_avail

    def get_product_available_str(self, cr, uid, ids, context=None):
        """
        由于xmlrpc本身的BUG，字典不能用数值，特加入此方法
        """
        value_dict = self.get_product_available(cr, uid, ids, context)
        result = {}
        for i in value_dict:
            result = {str(i): value_dict[i]}
            
        return result


    def get_out_lot(self, cr, uid, product_id, qty, warehouse_id, context=None):
        '''
        依产品数量返回生产日期ID或者IDS
        参数产品，数量，物流中心
        返回,
        '''
        if context is None:
            context = {}
        prodlot_obj = self.pool.get('stock.production.lot')
        mov_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        uom_obj = self.pool.get('product.uom')
        #仅计算每个物流中心存储库位的数量
        location_id = self.pool.get('stock.warehouse').browse(cr, uid, warehouse_id, context=context).lot_stock_id.id
        context.update({'location' : location_id})
        prodlot_ids = prodlot_obj.search(cr, uid, [('product_id', '=', product_id), ('stock_available', '>', 0)], order='name asc', context=context)
        if not prodlot_ids:
            return False
        #查出已占用lot,状态draft, assign, 'confirmed','waiting','assigned'
        mov_ids = mov_obj.search(cr, uid, [
            ('location_id', '=', location_id),
            ('product_id', '=', product_id),
            ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned']),
            ('type', 'in', ['out', 'internal']),
            ('prodlot_id', '!=' , False),
            ], context=context)
        occupy_lot_ids = {}
        product_base_uom = product_obj.browse(cr, uid, product_id, context=context).uom_id.id
        for one_move in mov_obj.browse(cr, uid, mov_ids, context=context):
            move_uom = one_move.product_uom.id
            product_real_qty = one_move.product_qty
            if product_base_uom != move_uom:
                product_real_qty = uom_obj._compute_qty(cr, uid, move_uom, one_move.product_qty, product_base_uom)
            temp_lot = one_move.prodlot_id.id or False
            if temp_lot in occupy_lot_ids:
                occupy_lot_ids.update({temp_lot:occupy_lot_ids[temp_lot] + product_real_qty})
            else:
                occupy_lot_ids[temp_lot] = product_real_qty
        will_lot_ids = {}
        for one_lot in prodlot_obj.browse(cr, uid, prodlot_ids, context=context):
            if qty <= 0: 
                break
            avail_qty = one_lot.stock_available
            if avail_qty <= 0: 
                break
            if one_lot.id in occupy_lot_ids:
                #同一产品同一批次号代表唯一
                avail_qty = avail_qty - occupy_lot_ids[one_lot.id]
                if avail_qty > 0:
                    if avail_qty > qty:
                        will_lot_ids.update({one_lot.id: qty})
                        break
                    else:
                        will_lot_ids.update({one_lot.id: avail_qty})
                        qty -= avail_qty
            else:
                if avail_qty > qty:
                    will_lot_ids.update({one_lot.id: qty})
                    break
                else:
                    qty -= avail_qty
                    will_lot_ids.update({one_lot.id: avail_qty})
        return will_lot_ids

    ## def get_last_sell(self, cr, uid, product_ids, context=None):
    ##     '''
    ##     计算商品出库数量，
    ##     参数字典，商品，物流中心
    ##     返回,
    ##     '''
    ##     if context is None:
    ##         context = {}
    ##     warehouse_id = context.get('active_warehouse_id', [])
    ##     if not warehouse_id:
    ##         raise osv.except_osv(_('Invalid Action!'), _(u'No Warehouse!'))
    ##     warehouse_obj = self.pool.get('stock.warehouse')
    ##     mov_obj = self.pool.get('stock.move')
    ##     uom_obj = self.pool.get('product.uom')
    ##     warehouse_data = warehouse_obj.browse(cr, uid, warehouse_id, context)
    ##     lot_stock_id = warehouse_data.lot_stock_id.id
    ##     if isinstance(product_ids, (int, long)):
    ##         product_ids = [product_ids]

    ##     #lot_output_id = warehouse_data.lot_output_id.id
    ##     today = datetime.today()
    ##     last_week = (today - relativedelta(days=7)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    ##     last_month = (today - relativedelta(days=30)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    ##     result = {}.fromkeys(product_ids, 0)
    ##     product_uoms = {}
    ##     for one_product in self.read(cr, uid, product_ids, ['uom_id'], context):
    ##         product_uoms[one_product['id']] = one_product['uom_id'][0]
    ##     for product_id in product_ids:
    ##         product_uom = product_uoms[product_id]
    ##         week_qty = 0
    ##         month_qty = 0
    ##         month_move_lines_ids = mov_obj.search(cr, uid, [('product_id','=',product_id), ('location_id','=',lot_stock_id),('date','>', last_month), ('state','=', 'done'), ('sale_line_id', '!=', False), ('type', '=', 'out')], context=context)
    ##         month_move_lines_data = mov_obj.read(cr, uid, month_move_lines_ids, ['product_qty', 'product_uom', 'date'], context=context)
    ##         for one_move in month_move_lines_data:
    ##             if product_uom != one_move['product_uom'][0]:
    ##                 product_qty = uom_obj._compute_qty(cr, uid, one_move['product_uom'][0], one_move['product_qty'], product_uom)
    ##             else:
    ##                 product_qty = one_move['product_qty']
    ##             if one_move['date'] >= last_week:
    ##                 week_qty = week_qty + product_qty
    ##             month_qty = month_qty + product_qty
    ##         result[product_id] = {
    ##             'last_week': week_qty,
    ##             'last_month': month_qty,
    ##             'uom_id' : product_uom
    ##         }
    ##     return result


    def get_last_sell(self, cr, uid, product_ids, context=None):
        '''
        计算商品出库数量，
        参数字典，商品，物流中心
        返回,
        '''
        if context is None:
            context = {}
        warehouse_id = context.get('active_warehouse_id', [])
        if not warehouse_id:
            raise osv.except_osv(_('Invalid Action!'), _(u'No Warehouse!'))
        warehouse_obj = self.pool.get('stock.warehouse')
        mov_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get('product.uom')
        warehouse_data = warehouse_obj.browse(cr, uid, warehouse_id, context)
        lot_stock_id = warehouse_data.lot_stock_id.id
        if isinstance(product_ids, (int, long)):
            product_ids_str = '(' + str(product_ids) + ')'
            product_ids = [product_ids]
        else:
            product_ids_str = tuple(product_ids)
        product_ids.sort()
    
        result = {}      
        for one_product in self.read(cr, uid, product_ids, ['uom_id'], context):
            result[one_product['id']] = {'uom_id': one_product['uom_id'][0]}        
        
        last_week = 7
        sql_str = """
        select pro_saleqry.product_id,sum(pro_saleqry.saleqry) as saleqry from (
        select stockmove.product_id,stockmove.product_uom,sum(coalesce(stockmove.product_qty,0)/coalesce(stockpuom.factor,0))*puom.factor as saleqry
        from stock_move stockmove
        left join (
        select pp.id as product_id,pt.uom_id,pu.factor 
        from product_product pp
        inner join product_template pt on pt.id = pp.product_tmpl_id
        left join product_uom pu on pu.id = pt.uom_id
        ) puom on puom.product_id = stockmove.product_id
        left join product_uom stockpuom on stockpuom.id = stockmove.product_uom 
        where stockmove.state in ('done')
        and stockmove.sale_line_id is not null
        and stockmove.location_id = %s
        and (stockmove.date+interval'8 hours') >= (now() - interval '%s days')
        and stockmove.product_id in %s
        group by stockmove.product_id,stockmove.product_uom,stockpuom.factor,puom.factor
        ) pro_saleqry group by product_id
        order by pro_saleqry.product_id;
        """
        cr.execute(sql_str, (lot_stock_id, last_week, product_ids_str))
        last_week_result = cr.fetchall()
        i = 0
        for one_id in product_ids:
            if last_week_result:
                for one_result in last_week_result :
                    if one_result[0] == one_id: 
                        result[one_id]['last_week'] =one_result[1]
                        break;     
                    elif one_result == last_week_result[-1] and one_result[0] !=one_id :
                        result[one_id]['last_week'] = 0
            else :
                result[one_id]['last_week'] = 0
            i += 1
        last_month = 30

        cr.execute(sql_str, (lot_stock_id, last_month, product_ids_str))
        last_month_result = cr.fetchall()
        i = 0
        for one_id in product_ids:
            if last_month_result :
                for one_result in last_month_result :
                    if one_result[0] == one_id: 
                        result[one_id]['last_month'] = one_result[1]
                        break;
                    elif one_result== last_month_result[-1] and one_result[0] != one_id :
                        result[one_id]['last_month'] = 0
            else:
                result[one_id]['last_month'] = 0
            i += 1

        return result




