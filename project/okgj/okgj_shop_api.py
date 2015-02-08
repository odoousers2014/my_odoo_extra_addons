# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools import config
import openerp.addons.decimal_precision as dp
import logging
from openerp import netsvc
from openerp.tools.translate import _
import redis
import uuid
import json
import time
import datetime
import copy
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import pooler
from okgj_car import OKGJ_ORDER_TYPE 

_logger = logging.getLogger(__name__)

try:
    redis_pool = redis.ConnectionPool(host=config.get('redis_interface', '127.0.0.1'), port=int(config.get('redis_port', 6379)))
except:
    _logger.error('Can not connect to redis server!')

#REDIS设计思路参见org文件
## pipe.sadd("do_product_new", "goods_no:001");
## pipe.hset("do_product_new:goods_no:001","goods_name","001");

def redis_do (redispool, table, p_key, p_value, arg):
    r = redis.StrictRedis(connection_pool=redispool)
    pipe = r.pipeline()
    if not arg:
        arg = []
    list_key = table + '_list'
    list_value = p_key + ':' + p_value
    set_table = table
    set_str = p_key + ':' + p_value
    pipe.lpush(list_key, list_value).execute()
    pipe.sadd(set_table, set_str).execute()
    if arg:
        hash_table = set_table + ':' + set_str
        pipe.hmset(hash_table, arg).execute()
    pipe.reset()
    return True

def redis_get (redispool, table, done_table, detail_table, p_column):
    r = redis.StrictRedis(connection_pool=redispool)
    pipe = r.pipeline()
    all_keys = list(pipe.sdiff(table, done_table).execute()[0])
    answers = []
    for p_key in all_keys:
        hash_table = detail_table + ':' + p_key
        value = pipe.hget(hash_table, p_column).execute()
        answers.append(value[0])
    pipe.reset()
    return answers

def redis_check (redispool, table, done_table):
    r = redis.StrictRedis(connection_pool=redispool)
    pipe = r.pipeline()
    all_keys = list(pipe.sdiff(table, done_table).execute()[0])
    pipe.reset()
    return all_keys

def redis_check_done (redispool, done_table, done_key, done_value):
    r = redis.StrictRedis(connection_pool=redispool)
    pipe = r.pipeline()
    if isinstance(done_value, (int, long)):
        done_value = str(done_value)
    done_str = done_key +':' + done_value
    pipe.sadd(done_table, done_str).execute()
    pipe.reset()
    return True

def redis_check_done_remove (redispool, remove_table, remove_key, remove_value):
    r = redis.StrictRedis(connection_pool=redispool)
    pipe = r.pipeline()
    if isinstance(remove_value, (int, long)):
        remove_value = str(remove_value)
    remove_str = remove_key +':' + remove_value
    pipe.sadd(remove_table, remove_str).execute()
    pipe.reset()
    return True

##专门用于错误处理，方便以后扩展手机通知功能
def okgj_api_log_error(error_category, error_no, error_reason):
    ##TODO:通过错误类型执行其它处理
    ##暂定类别:Basic, Sales Order, Return Order, Product, Start
    error_str = error_category + ': ' + error_no + '\t' + error_reason
    _logger.error('%s', error_str)
    return True

#普通商品
class okgj_product_product_api(osv.osv):
    _inherit = 'product.product'

    def action_upload_product(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        redis_new_table = "do_product_new"
        redis_list_price_table = "do_shop_price_change"
        redis_market_price_table = "do_market_price_change"
        redis_okkg_price_table = "do_okkg_price_change"
        redis_weight_table = "do_goods_weight_change"
        p_new_key = "goods_no"
        p_list_price_key = "goods_no"
        p_okkg_price_key = "goods_no"
        p_market_price_key = "goods_no"
        p_weight_key = "goods_no"
        for one_product in self.browse(cr, uid, ids, context=context):
            goods_no = one_product.default_code
            goods_name = one_product.name
            p_new_value = goods_no
            p_list_price_value =  goods_no + '_' + uuid.uuid4().hex
            p_okkg_price_value =  goods_no + '_' + uuid.uuid4().hex
            p_market_price_value = goods_no + '_' + uuid.uuid4().hex
            p_weight_value = goods_no + '_' + uuid.uuid4().hex
            new_arg = {"name":goods_name}
            list_price_arg = {"shop_price":float(one_product.list_price)}
            okkg_price_arg = {"okkg_price":float(one_product.okkg_price)}
            market_price_arg =  {"market_price":float(one_product.other_price)}
            weight_arg = {"weight":int(round(one_product.weight))}
            redis_do(redis_pool, redis_new_table, p_new_key, p_new_value, new_arg)
            redis_do(redis_pool, redis_list_price_table, p_list_price_key, p_list_price_value, list_price_arg)
            redis_do(redis_pool, redis_okkg_price_table, p_okkg_price_key, p_okkg_price_value, okkg_price_arg)
            redis_do(redis_pool, redis_market_price_table, p_market_price_key, p_market_price_value, market_price_arg)
            redis_do(redis_pool, redis_weight_table, p_weight_key, p_weight_value, weight_arg)
        return True

    def action_stock_change(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        redis_table = "do_stock_change"
        p_key = "goods_no"
        if isinstance(ids, (int, long)):
            ids = [ids]
        sqlstr = "select id, okgj_warehouse_id from stock_warehouse"
        cr.execute(sqlstr)
        results = cr.fetchall()
        warehouse_context = copy.deepcopy(context)
        for one_warehouse in results:
            warehouse_context.update({'warehouse':one_warehouse[0]})
            for one_product in self.browse(cr, uid, ids, context=warehouse_context):
                p_value = one_product.default_code
                arg = {'total_count':int(round(one_product.qty_available)), 'warehouse_id':one_warehouse[1]}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        return True
                   
    def action_all_stock_change(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        redis_table = "do_stock_change"
        p_key = "goods_no"
        ids = self.search(cr, uid, [], context=context)
        sqlstr = "select id, okgj_warehouse_id from stock_warehouse"
        cr.execute(sqlstr)
        results = cr.fetchall()
        warehouse_context = copy.deepcopy(context)
        for one_warehouse in results:
            warehouse_context.update({'warehouse':one_warehouse[0]})
            for one_product in self.browse(cr, uid, ids, context=warehouse_context):
                if not one_product.is_group_product:
                    p_value = one_product.default_code
                    arg = {'total_count':int(round(one_product.qty_available)), 'warehouse_id':one_warehouse[1]}
                    redis_do(redis_pool, redis_table, p_key, p_value, arg)
        return True

    def create(self, cr, uid, vals, context=None):
        new_product_id = super(okgj_product_product_api,self).create(cr, uid, vals, context=context)
        #cr.commit()
        goods_no = vals.get('default_code', False)
        goods_name = vals.get('name', False)
        redis_table = "do_product_new"
        p_key = "goods_no"
        p_value = goods_no
        arg = {"name":goods_name}
        redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if vals.get('is_okkg', 0):
            redis_table = "do_mark_okkg"
            p_key = "goods_no"
            p_value = goods_no
            if vals.get('is_okkg') :
                arg = {"is_okkg":1}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if vals.get('list_price', False):
            redis_table = "do_shop_price_change"
            p_key = "goods_no"
            p_value = goods_no + '_' + uuid.uuid4().hex
            arg = {"shop_price":float(vals.get('list_price'))}
            redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if vals.get('okkg_price', False):
            redis_table = "do_okkg_price_change"
            p_key = "goods_no"
            p_value = goods_no + '_' + uuid.uuid4().hex
            arg = {"okkg_price":float(vals.get('okkg_price'))}
            redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if vals.get('other_price', False):
            redis_table = "do_market_price_change"
            p_key = "goods_no"
            p_value = goods_no + '_' + uuid.uuid4().hex
            arg = {"market_price":float(vals.get('other_price'))}
            redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if vals.get('weight', False):
            redis_table = "do_goods_weight_change"
            p_key = "goods_no"
            p_value = goods_no + '_' + uuid.uuid4().hex
            arg = {"weight":int(round(vals.get('weight')))}
            redis_do(redis_pool, redis_table, p_key, p_value, arg)
        return new_product_id

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('default_code', False):
            vals.pop('default_code')
            #raise osv.except_osv(_('Error!'), _(u'编码不允许修改.'))
        super(okgj_product_product_api, self).write(cr, uid, ids, vals, context=context)
        if vals.get('name', False):
            redis_table = "do_product_name_change"
            p_key = "goods_no"
            for one_product in self.browse(cr, uid, ids, context=context):
                goods_no = one_product.default_code
                goods_name = vals.get('name')
                p_value = goods_no + '_' + uuid.uuid4().hex
                arg = {"name":goods_name}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        ## 快购接口
        if vals.get('is_okkg') is not None:
            redis_table = "do_mark_okkg"
            p_key = "goods_no"
            for one_product in self.browse(cr, uid, ids, context=context):
                p_value = one_product.default_code
                if vals.get('is_okkg') is True:
                    arg = {"is_okkg":1}
                elif vals.get('is_okkg') is False:
                    arg = {"is_okkg":0}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if vals.get('list_price', False):
            if isinstance(ids, (int, long)):
                ids = [ids]
            redis_table = "do_shop_price_change"
            p_key = "goods_no"
            for one_product in self.browse(cr, uid, ids, context=context):
                goods_no = one_product.default_code + '_' + uuid.uuid4().hex
                p_value = goods_no
                arg = {"shop_price":float(vals.get('list_price'))}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if vals.get('okkg_price', False):
            if isinstance(ids, (int, long)):
                ids = [ids]
            redis_table = "do_okkg_price_change"
            p_key = "goods_no"
            for one_product in self.browse(cr, uid, ids, context=context):
                goods_no = one_product.default_code + '_' + uuid.uuid4().hex
                p_value = goods_no
                arg = {"okkg_price":float(vals.get('okkg_price'))}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if vals.get('other_price', False):
            if isinstance(ids, (int, long)):
                ids = [ids]
            redis_table = "do_market_price_change"
            p_key = "goods_no"
            for one_product in self.browse(cr, uid, ids, context=context):
                goods_no = one_product.default_code + '_' + uuid.uuid4().hex
                p_value = goods_no
                arg = {"market_price":float(vals.get('other_price'))}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if vals.get('weight', False):
            if isinstance(ids, (int, long)):
                ids = [ids]
            redis_table = "do_goods_weight_change"
            p_key = "goods_no"
            for one_product in self.browse(cr, uid, ids, context=context):
                goods_no = one_product.default_code + '_' + uuid.uuid4().hex
                p_value = goods_no
                arg = {"weight":int(round(vals.get('weight')))}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        return True

##组合品
class okgj_mrp_bom_api(osv.osv):
    _inherit = 'mrp.bom'
    def create(self, cr, uid, vals, context=None):
        bom_id = super(okgj_mrp_bom_api,self).create(cr, uid, vals, context=context)
        if vals.get('type', False) == 'phantom':
            product_obj = self.pool.get('product.product')
            parent_product_id = vals.get('product_id')
            parent_goods_no = product_obj.read(cr, uid, parent_product_id, ['default_code'], context=context)['default_code']
            subproduct = vals.get('bom_lines')
            parent_goods_qty = vals.get('product_qty') or 1
            subproduct_str = '{' + '"' + parent_goods_no + '"' + ':' + str(parent_goods_qty) + '}'
            ## if subproduct:
            ##     for one_line in subproduct:
            ##         subproduct_id = one_line[2]['product_id']
            ##         subgoods_no = product_obj.read(cr, uid, subproduct_id, ['default_code'], context=context)['default_code']
            ##         subgoods_qty = one_line[2]['product_qty']
            ##         subproduct_str =  subproduct_str + '"' + subgoods_no + '"' + ':' + str(subgoods_qty) +','
            ##     subproduct_str = subproduct_str[:-1]
            ##     subproduct_str = '{' + subproduct_str + '}'
            redis_table = "combine_product_new"
            p_key = "parent_goods_no"
            p_value = parent_goods_no  ## + '_' + uuid.uuid4().hex
            arg = {"sub_goods_dict":subproduct_str}
            redis_do(redis_pool, redis_table, p_key, p_value, arg)
        if (vals.get('type', False) == 'normal') and vals.get('bom_id', False):
            parent_bom_id = vals.get('bom_id')
            bom_data = self.browse(cr, uid, parent_bom_id, context=context)
            if bom_data.bom_id and bom_data.bom_id.product_id:
                parent_goods_no = bom_data.bom_id.product_id.default_code
                subproduct_str = ''
                for one_line in bom_data.bom_lines:
                    subgoods_no = one_line.product_id.default_code
                    subgoods_qty = one_line.product_qty
                    sub_goods_uom = one_line.product_uom.id
                    sub_goods_default_uom = one_line.product_id.uom_id.id
                    if sub_goods_default_uom != sub_goods_uom:
                        subgoods_qty = uom_obj._compute_qty(cr, uid, sub_goods_uom, product_qty, sub_goods_default_uom)
                    subproduct_str =  subproduct_str + '"' + subgoods_no + '"' + ':' + str(subgoods_qty) +','
                subproduct_str = subproduct_str[:-1]
                subproduct_str = '{' + subproduct_str + '}'
                redis_table = "combine_product_update"
                p_key = "parent_goods_no"
                p_value = parent_goods_no  # + '_' + uuid.uuid4().hex
                arg = {"sub_goods_dict":subproduct_str}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        return bom_id
     
    def write(self, cr, uid, ids, vals, context=None):
        super(okgj_mrp_bom_api, self).write(cr, uid, ids, vals, context=context)
        redis_table = "combine_product_update"
        p_key = "parent_goods_no"
        uom_obj = self.pool.get('product.uom')
        for one_bom_data in self.browse(cr, uid, ids, context=context):
            if one_bom_data.bom_id and (one_bom_data.type=='normal'):
                parent_goods_no = one_bom_data.bom_id.product_id.default_code
                subproduct_str = ''
                for one_line in one_bom_data.bom_id.bom_lines:
                    subgoods_no = one_line.product_id.default_code
                    subgoods_qty = one_line.product_qty
                    sub_goods_uom = one_line.product_uom.id
                    sub_goods_default_uom = one_line.product_id.uom_id.id
                    if sub_goods_default_uom != sub_goods_uom:
                        subgoods_qty = uom_obj._compute_qty(cr, uid, sub_goods_uom, subgoods_qty, sub_goods_default_uom)
                    subproduct_str =  subproduct_str + '"' + subgoods_no + '"' + ':' + str(subgoods_qty) +','
                subproduct_str = subproduct_str[:-1]
                subproduct_str = '{' + subproduct_str + '}'
                p_value = parent_goods_no  # + '_' + uuid.uuid4().hex
                arg = {"sub_goods_dict":subproduct_str}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
            if one_bom_data.bom_lines and (one_bom_data.type=='phantom'):
                parent_goods_no = one_bom_data.product_id.default_code
                subproduct_str = ''
                for one_line in one_bom_data.bom_lines:
                    subgoods_no = one_line.product_id.default_code
                    subgoods_qty = one_line.product_qty
                    sub_goods_uom = one_line.product_uom.id
                    sub_goods_default_uom = one_line.product_id.uom_id.id
                    if sub_goods_default_uom != sub_goods_uom:
                        subgoods_qty = uom_obj._compute_qty(cr, uid, sub_goods_uom, subgoods_qty, sub_goods_default_uom)
                    subproduct_str =  subproduct_str + '"' + subgoods_no + '"' + ':' + str(subgoods_qty) +','
                subproduct_str = subproduct_str[:-1]
                subproduct_str = '{' + subproduct_str + '}'
                p_value = parent_goods_no  # + '_' + uuid.uuid4().hex
                arg = {"sub_goods_dict":subproduct_str}
                redis_do(redis_pool, redis_table, p_key, p_value, arg)
        return True

    def unlink(self, cr, uid, ids, context=None):
        redis_table = "combine_product_remove"
        p_key = "parent_goods_no"
        for one_bom in self.browse(cr, uid, ids, context=context):
            parent_goods_no = one_bom.product_id.default_code
            p_value = parent_goods_no # + '_' + uuid.uuid4().hex
            arg = False
            redis_do(redis_pool, redis_table, p_key, p_value, arg)
        return super(okgj_mrp_bom_api, self).unlink(cr, uid, ids, context=context)

##销售订单
class okgj_sale_order_api(osv.osv):

    def action_add_claim(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        context.update({'default_sale_id': ids[0]})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'okgj.order.claim',
            'type': 'ir.actions.act_window',
            'context': context,
        }

    def _get_shop(self, cr, uid, okgj_warehouse_id, city_name, context=None):
        """ 传入城市返回shop_id
        @param prop: Name of city.
        @return: shop_id
        """
        shop_id = 0
        if okgj_warehouse_id:
            sqlstr = """
            select shop.id from sale_shop shop
            left join stock_warehouse warehouse
            on shop.warehouse_id = warehouse.id
            where warehouse.okgj_warehouse_id = %s and shop.name = %s
            """
            cr.execute(sqlstr, (okgj_warehouse_id, city_name))
            shop_id = cr.fetchone()[0]
        else:
            shop_ids = self.pool.get('sale.shop').search(cr, uid, [('name', '=', city_name)], context=context)
            if shop_ids:
                shop_id = shop_ids[0]
        if shop_id :
            return shop_id
        else:
            return self._get_default_shop(cr, uid, context=None)

    def _get_weight_kg(self, cr, uid, ids, field_names, arg, context=None):
        """ Kg
        @param prop: Name of field.
        @param unknow_none:
        @return: Dictionary of values.
        """
        if context is None:
            context = {}
        result = {}.fromkeys(ids, 0.0)
        for one_order in self.browse(cr, uid, ids, context=context):
            result[one_order.id] = one_order.order_weight / 1000
        return result

    _inherit = 'sale.order'
    _order = 'create_date desc'
    _columns = {
        'okgj_address':fields.char(u'收货地址', size=32),
        'best_time':fields.char(u'送货时间', size=32),
        'bonus': fields.float(u'奖金', digits_compute=dp.get_precision('Product Price')),
        'bonus_pay': fields.float(u'奖金支付', digits_compute=dp.get_precision('Product Price')),
        'consignee':fields.char(u'收货人', size=16),
        'coupon_pay': fields.float(u'优惠券抵扣', digits_compute=dp.get_precision('Product Price')),
        'discount': fields.float(u'折扣金额', digits_compute=dp.get_precision('Product Price')),
        'goods_amount': fields.float(u'商品总价', digits_compute=dp.get_precision('Product Price')),
        'inv_amount': fields.float(u'开票金额', digits_compute=dp.get_precision('Product Price')),
        'inv_content':fields.text(u'发票内容'),
        'inv_payee':fields.text(u'发票抬头'),
        'inv_state': fields.selection([
            ('1', u'未开票'),
            ('2', u'已开票'),
            ('3', u'发票已退回'),
            ], u'开票状态', readonly=True),
        'inv_type': fields.selection([
            ('1', u'普通发票'),
            ('2', u'增值税发票'),
            ], u'开票种类',readonly=True),
        'mobile':fields.char(u'手机', size=16),
        'money_paid': fields.float(u'已支付', digits_compute=dp.get_precision('Product Price')),
        'money_own': fields.float(u'货到付款金额', digits_compute=dp.get_precision('Product Price')),
        'okgj_user_id':fields.char(u'会员ID', size=32),
        'order_amount': fields.float(u'还应支付', digits_compute=dp.get_precision('Product Price')),
        'order_weight': fields.float(u'商品总重量(g)', digits_compute=dp.get_precision('Product Price')),
        'order_weight_kg': fields.function(_get_weight_kg, type='float', string=u'商品总重量(Kg)', store=True, digits=(12, 2)),
        'pay_id': fields.char(u'付款方式', readonly=True, size=64, select=True),
        
        #jon set pay_name and pay_time readonly=False 
        'pay_time': fields.datetime(u'付款时间', readonly=False, select=True),
        'pay_name': fields.char(u'付款名称', readonly=False, size=64, select=True),
        'pay_status':fields.selection([
            ('0', u'0'),
            ('1', u'1'),
            ('2', u'2'),
            ], u'付款状态', readonly=True),
        'recharge_bonus': fields.float(u'乐享奖金', digits_compute=dp.get_precision('Product Price')),
        'reconment':fields.text(u'订单备注'),
        'okgj_province':fields.char(u'收货省份', size=32),
        'okgj_province_id':fields.char(u'收货省份ID', size=32),
        'okgj_city':fields.char(u'收货城市', size=32),
        'okgj_city_id':fields.char(u'收货城市ID', size=32),
        'region_name':fields.text(u'收货区域'),
        'region_id':fields.char(u'收货区域ID', size=32),
        'send_time_content':fields.text(u'送货备注'),
        'shipping_status':fields.selection([
            ('', ''),
            ('0', u'0'),
            ('1', u'1'),
            ('2', u'2'),
            ('3', u'3'),
            ('4', u'4'),
            ], u'付款状态', readonly=True),
        'shipping_fee': fields.float(u'物流费', digits_compute=dp.get_precision('Product Price')),
        'shipping_id':fields.integer('Shipping ID',help="5 local express"),
        'ship_fee': fields.float(u'基本运费', digits_compute=dp.get_precision('Product Price')),
        'weight_fee': fields.float(u'续重费', digits_compute=dp.get_precision('Product Price')),
        'okgj_tel':fields.char(u'联系电话', size=16),
        'okgj_shop_order_id':fields.char(u'商城订单ID', size=64),
        'send_time':fields.char(u'选择送货时间', size=128),
        'date_order2': fields.datetime(u'商城下单时间', readonly=True),
        'okgj_shop_cancel':fields.boolean(u'复核后取消', readonly=True),
        'okgj_ordinal':fields.integer(u'下单次数', readonly=True),
        'by_okgj_shop':fields.boolean(u'商城下单', readonly=True),
        'user_rank_name':fields.char(u'会员级别', size=32),
        'user_rank':fields.char(u'会员级别ID', size=32),
        'okgj_order_type':fields.selection(OKGJ_ORDER_TYPE, u'订单来源', readonly=False),
        'okgj_formulate_fee': fields.float(u'预约费', digits_compute=dp.get_precision('Product Price'), readonly=True),
        'okgj_discount_remark':fields.text(u'折扣明细'),
        'okgj_bonus_remark':fields.text(u'乐享奖金备注'),
        'will_pay_time':fields.char(u'预计付款时间', size=128),
        'is_cps_order':fields.boolean('CPS Order'),
    }
    
    
    def is_cps_order(self, cr, uid, ids, context=None):
        """
        if all product rebate != 0.0, this is a  cps order
        """
        if not isinstance(ids, list):
            ids=[ids,]
        
        for so in self.browse(cr, uid, ids, context=context):
            for line in so.order_line:
                if line.product_id.rebate == 0:
                    return False
        return True
        
    
    def action_button_confirm(self, cr, uid, ids, context=None):
        """
        If SO if not come from redis,when confirm it,auto-write some money info 
        """
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        

        if self.is_cps_order(cr, uid, ids):
            so=self.browse(cr, uid, ids[0])
            values={
                'goods_amount': so.amount_total,
                'money_paid': so.amount_total,
                'order_amount': 0.0,  
                'is_cps_order':True,   
            }
            self.write(cr, uid, ids[0], values, context=context)

        return super(okgj_sale_order_api,self).action_button_confirm(cr, uid, ids, context=context)

    def _get_okshop_order_data(self, cr, uid, group_letters='0123456789',context=None, ):
        """
        从对列中获取商场销售订单
        返回订单创建所需字典列表
        """
        
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        warehouse_obj = self.pool.get('stock.warehouse')
        warehouse_sprice_obj = self.pool.get('okgj.warehouse.sprice')
        customer_ids = self.pool.get('res.partner').search(cr, uid, [('is_ok', '=', True)], context=context)
        if not customer_ids:
            okgj_api_log_error('Basic', 'Unknown', 'Default customer has been deleted')
            return []
        redis_table = "get_order_queue"
        done_table = "get_order_queue_done"
        detail_table = "get_order_detail"
        p_column = "answer"
        order_str_datas = redis_get(redis_pool, redis_table, done_table, detail_table, p_column)
        order_list = []
        for one_order_str in order_str_datas:
            try:
                one_order_dict = json.loads(one_order_str)
            except:
                okgj_api_log_error('OKShop Sales Order', one_order_str, 'Can not dump json string!')
                continue
            order_vals = {}
            # split SO by redis_get_sale_order_last_letters
            last_letter = one_order_dict['order_no'][-1]
            if last_letter in group_letters:
                _logger.info('group_letters:SO %s last letter in %s,go on' % (one_order_dict['order_no'],group_letters))
            else:
                _logger.info('group_letters:SO %s last letter not in %s,pass' % (one_order_dict['order_no'],group_letters))
                continue
            try:
                if one_order_dict['order_info']['pay_time'] > 0:
                    pay_time = (datetime.datetime.fromtimestamp(one_order_dict['order_info']['pay_time']) + relativedelta(hours=8)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    will_pay_time = None
                else:
                    pay_time = None
                    will_pay_time = one_order_dict['order_info']['send_time']
                #订单来源
                order_type = 'okshop'
                okapp, okwd, oktg = u'手机APP', u'微店', u'商城后台'
                referer = one_order_dict['order_info'].get('referer', '')
                if referer in [okapp]:
                    order_type = 'okapp'
                elif referer in [okwd]:
                    order_type = 'okwd'
                elif referer in [oktg]:
                    order_type = 'oktg'
                order_vals = {
                    'note': group_letters,
                    'okgj_order_type': order_type,
                    'name' : one_order_dict['order_no'],
                    'state' : 'draft',
                    'okgj_shop_order_id':one_order_dict['order_id'],
                    'partner_id':customer_ids[0], 
                    'partner_invoice_id':customer_ids[0], 
                    'partner_shipping_id':customer_ids[0],
                    'pricelist_id':1, #TODO: 需要与其它部门讨论
                    'date_order2':(datetime.datetime.fromtimestamp(one_order_dict['order_info']['add_time']) + relativedelta(hours=8)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    #time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.localtime(one_order_dict['order_info']['add_time'])),
                    'okgj_address' : one_order_dict['order_info']['address'],
                    'best_time' : one_order_dict['order_info']['best_time'],
                    'bonus' : one_order_dict['order_info']['bonus'],
                    'bonus_pay' : one_order_dict['order_info']['bonus_pay'],
                    'goods_amount' : one_order_dict['order_info']['goods_amount'],
                    'coupon_pay' : one_order_dict['order_info']['coupon_pay'],
                    'discount' : one_order_dict['order_info']['discount'] or 0,
                    'consignee':one_order_dict['order_info']['consignee'],
                    'okgj_tel':one_order_dict['order_info']['mobile'],
                    'send_time':one_order_dict['order_info']['send_time'],
                    'okgj_ordinal':one_order_dict['order_info']['ordinal'],
                    'user_rank_name':one_order_dict['order_info']['user_rank_name'],
                    'user_rank':one_order_dict['order_info']['user_rank'],
                    'picking_policy' : 'one',
                    'inv_amount' : one_order_dict['order_info']['inv_amount'],
                    'inv_content' : one_order_dict['order_info']['inv_content'],
                    'inv_payee' : one_order_dict['order_info']['inv_payee'],
                    'okgj_user_id' : one_order_dict['user_info'] and one_order_dict['user_info']['user_name'] or False,
                    'inv_state' : '1',
                    'inv_type' : '1',
                    'money_paid' : one_order_dict['order_info']['money_paid'],
                    'order_amount' : one_order_dict['order_info']['order_amount'],
                    'order_weight' : one_order_dict['order_info']['order_weight'],
                    'recharge_bonus' : one_order_dict['order_info']['recharge_bonus'],
                    'send_time_content' : one_order_dict['order_info']['send_time_content'],
                    'reconment' : one_order_dict['order_info']['reconment'],
                    'pay_id' : one_order_dict['order_info']['pay_name'],
                    'pay_name' : one_order_dict['order_info']['pay_name'],
                    'pay_status' : str(one_order_dict['order_info']['pay_status']),
                    'pay_time' : pay_time,
                    #time.strftime(DEFAULT_SERVER_DATE_FORMAT, time.localtime(one_order_dict['order_info']['pay_time'])),
                    'shipping_id' : one_order_dict['order_info']['shipping_id'],
                    'shipping_fee' : one_order_dict['order_info']['shipping_fee'],
                    'ship_fee' : one_order_dict['order_info']['ship_fee'],
                    'weight_fee':one_order_dict['order_info']['weight_fee'],
                    'okgj_province' : one_order_dict['order_info']['province'],
                    'okgj_province_id' : one_order_dict['order_info']['province_id'],
                    'okgj_city' : one_order_dict['order_info']['city'],
                    'okgj_city_id' : one_order_dict['order_info']['city_id'],
                    'region_name' : one_order_dict['order_info']['region_name'],
                    'region_id' : one_order_dict['order_info']['region_id'],
                    'by_okgj_shop':True,
                    'shop_id':self._get_shop(cr, uid, one_order_dict['order_info']['warehouse_id'], one_order_dict['order_info']['city'], context=context),
                    'okgj_formulate_fee':one_order_dict['order_info']['formulate_fee'],
                    'okgj_discount_remark':one_order_dict['order_info']['discount_remark'],
                    'okgj_bonus_remark':one_order_dict['order_info']['bonus_remark'],
                    'will_pay_time':will_pay_time,
                    }
            except Exception as myerror:
                okgj_api_log_error('Sys Error', one_order_dict['order_no'], str(myerror))
                okgj_api_log_error('OKShop Sales Order', one_order_dict['order_no'], 'Fail to get order, Data errors!')
                continue
            order_lines = []
            for one_product in one_order_dict['product_list']:
                goods_sn = one_product['goods_sn']
                if isinstance(goods_sn, (int, long)):
                    goods_sn = str(goods_sn)
                product_id = product_obj.search(cr, uid, [('default_code', '=', goods_sn)], context=context)
                if isinstance(product_id, (long, int)):
                    product_id = [product_id]
                if len(product_id) != 1:
                    #未找到商品或发现多个相同编码商品
                    okgj_api_log_error('OKShop Sales Order', one_order_dict['order_no'], 'Data errors!')
                    okgj_api_log_error('Product', goods_sn, 'Not found in ERP')
                    continue
                product_data = product_obj.read(cr, uid, product_id[0], ['uom_id', 'okgj_cost_price'], context=context)
                uom_id = product_data['uom_id'][0]
                warehouse_id = warehouse_obj.search(cr, uid, [
                    ('okgj_warehouse_id', '=', one_order_dict['order_info']['warehouse_id'])
                    ], context=context)
                if len(warehouse_id) == 1:
                    sprice_ids = warehouse_sprice_obj.search(cr, uid, [
                        ('product_id', '=', product_id[0]),
                        ('warehouse_id', '=', warehouse_id[0])
                        ], context=context)
                    if sprice_ids:
                        purchase_price = warehouse_sprice_obj.read(cr, uid, sprice_ids[0], ['standard_price'], context=context)['standard_price']
                        #没有物流中心成本价，将取总公司成本价
                    else:
                        purchase_price = product_data['okgj_cost_price']
                else:
                    okgj_api_log_error('Warehouse', str(one_order_dict['order_info']['warehouse_id']), 'Not found in ERP')
                    purchase_price = product_data['okgj_cost_price']
                try:
                    sale_price = float(one_product['actual_amount'])/float(one_product['goods_number'])
                except Exception as myerror:
                    okgj_api_log_error('Sys Error', one_product['goods_name'], str(myerror))
                    sale_price = 0.0
                need_purchase = False
                try:
                    if int(one_product['is_booking']) > 0:
                        need_purchase = True
                except:
                    pass
                order_lines.append((0, 0, {'name':one_product['goods_name'],
                                           'product_id' : product_id[0],
                                           'product_uom':uom_id,
                                           'price_unit' : sale_price,
                                           'purchase_price':purchase_price,
                                           'okgj_discount': one_product['discount'],
                                           'product_uom_qty' : one_product['goods_number'],
                                           'need_purchase':need_purchase,
                                           }))
                order_vals.update({'order_line':order_lines})
                order_list.append(order_vals)
        return order_list

    def _get_okkg_order_data(self, cr, uid, context=None, group_letters='0123456789'):
        """
        从对列中获取OK快购销售订单
        返回订单创建所需字典列表
        """
        
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        warehouse_obj = self.pool.get('stock.warehouse')
        warehouse_sprice_obj = self.pool.get('okgj.warehouse.sprice')
        customer_ids = self.pool.get('res.partner').search(cr, uid, [('is_ok', '=', True)], context=context)
        if not customer_ids:
            okgj_api_log_error('Basic', 'Unknown', 'Default customer has been deleted')
            return []
        redis_table = "get_okkg_order_queue"
        done_table = "get_okkg_order_queue_done"
        detail_table = "get_okkg_order_detail"
        p_column = "answer"
        order_str_datas = redis_get(redis_pool, redis_table, done_table, detail_table, p_column)
        order_list = []
        for one_order_str in order_str_datas:
            try:
                one_order_dict = json.loads(one_order_str)
            except:
                okgj_api_log_error('OKKG Sales Order', one_order_str, 'Can not dump json string!')
                continue
            order_vals = {}
            # split SO by redis_get_sale_order_last_letters
            last_letter = one_order_dict['order_no'][-1]
            if last_letter in group_letters:
                _logger.info('group_letters:SO %s last letter in %s,go on' % (one_order_dict['order_no'],group_letters))
            else:
                _logger.info('group_letters:SO %s last letter not in %s,pass' % (one_order_dict['order_no'],group_letters))
                continue
            try:
                if one_order_dict['order_info']['pay_time'] > 0:
                    pay_time = (datetime.datetime.fromtimestamp(one_order_dict['order_info']['pay_time'])).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    will_pay_time = None
                else:
                    pay_time = None
                    will_pay_time = one_order_dict['order_info']['send_time']
                order_vals.update({
                    'okgj_order_type': 'okkg',
                    'name' : one_order_dict['order_no'],
                    'state' : 'draft',
                    'okgj_shop_order_id':one_order_dict['order_id'],
                    'partner_id':customer_ids[0], 
                    'partner_invoice_id':customer_ids[0], 
                    'partner_shipping_id':customer_ids[0],
                    'pricelist_id':1, #TODO: 需要与其它部门讨论
                    'date_order2':(datetime.datetime.fromtimestamp(one_order_dict['order_info']['add_time'])).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    #time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.localtime(one_order_dict['order_info']['add_time'])),
                    'okgj_address' : one_order_dict['order_info']['address'],
                    'best_time' : '',
                    'bonus' : 0,
                    'bonus_pay' : 0,
                    'goods_amount' : one_order_dict['order_info']['goods_amount'],
                    'coupon_pay' : 0,
                    'discount' : 0,
                    'consignee':one_order_dict['order_info']['consignee'],
                    'okgj_tel':one_order_dict['order_info']['mobile'],
                    'send_time':one_order_dict['order_info']['send_time'],
                    'okgj_ordinal':one_order_dict['order_info']['ordinal'],
                    'user_rank_name':one_order_dict['order_info']['user_rank_name'],
                    'user_rank':one_order_dict['order_info']['user_rank'],
                    'picking_policy' : 'one',
                    'inv_amount' : one_order_dict['order_info']['inv_amount'],
                    'inv_content' : one_order_dict['order_info']['inv_content'],
                    'inv_payee' : one_order_dict['order_info']['inv_payee'],
                    'okgj_user_id' : one_order_dict['order_info']['user_id'],
                    'inv_state' : '1',
                    'inv_type' : '1',
                    'money_paid' : one_order_dict['order_info']['payed_amount'],
                    'order_amount' : one_order_dict['order_info']['surplus_amount'],
                    'order_weight' : one_order_dict['order_info']['order_weight'],
                    'recharge_bonus' : 0,
                    'send_time_content' : '',
                    'reconment' : one_order_dict['order_info']['reconment'],
                    'pay_id' : one_order_dict['order_info']['pay_id'],
                    'pay_name' : one_order_dict['order_info']['pay_name'],
                    'pay_status' : str(one_order_dict['order_info']['pay_status']),
                    'pay_time' :pay_time,
                    #time.strftime(DEFAULT_SERVER_DATE_FORMAT, time.localtime(one_order_dict['order_info']['pay_time'])),
                    'shipping_id' : one_order_dict['order_info']['shipping_id'],
                    'shipping_fee' : one_order_dict['order_info']['shipping_fee'],
                    'ship_fee' : one_order_dict['order_info']['ship_fee'],
                    'weight_fee':one_order_dict['order_info']['weight_fee'],
                    'okgj_province' : one_order_dict['order_info']['province'],
                    'okgj_province_id' : one_order_dict['order_info']['province_id'],
                    'okgj_city' : one_order_dict['order_info']['city'],
                    'okgj_city_id' : one_order_dict['order_info']['city_id'],
                    'region_name' : one_order_dict['order_info']['region_name'],
                    'region_id' : one_order_dict['order_info']['region_id'],
                    'by_okgj_shop':True,
                    'shop_id':self._get_shop(cr, uid, one_order_dict['order_info']['warehouse_id'], one_order_dict['order_info']['city'], context=context),
                    'okgj_formulate_fee':0,
                    'will_pay_time':will_pay_time,
                })
            except Exception as myerror:
                okgj_api_log_error('Sys Error', one_order_dict['order_no'], str(myerror))
                okgj_api_log_error('OKKG Sales Order', one_order_dict['order_no'], 'Fail to get order, Data errors!')
                continue
            order_lines = []
            for one_product in one_order_dict['product_list']:
                goods_sn = one_product['goods_sn']
                if isinstance(goods_sn, (int, long)):
                    goods_sn = str(goods_sn)
                product_id = product_obj.search(cr, uid, [('default_code', '=', goods_sn)], context=context)
                if isinstance(product_id, (long, int)):
                    product_id = [product_id]
                if len(product_id) != 1:
                    #未找到商品或发现多个相同编码商品
                    okgj_api_log_error('OKKG Sales Order', one_order_dict['order_no'], 'Fail to get order, Data errors!')
                    okgj_api_log_error('Product', goods_sn, 'Not found in ERP')
                    continue
                product_data = product_obj.read(cr, uid, product_id[0], ['uom_id', 'okgj_cost_price'], context=context)
                uom_id = product_data['uom_id'][0]
                warehouse_id = warehouse_obj.search(cr, uid, [
                    ('okgj_warehouse_id', '=', one_order_dict['order_info']['warehouse_id'])
                    ], context=context)
                if len(warehouse_id) == 1:
                    sprice_ids = warehouse_sprice_obj.search(cr, uid, [
                        ('product_id', '=', product_id[0]),
                        ('warehouse_id', '=', warehouse_id[0])
                        ], context=context)
                    if sprice_ids:
                        purchase_price = warehouse_sprice_obj.read(cr, uid, sprice_ids[0], ['standard_price'], context=context)['standard_price']
                        #没有物流中心成本价，将取总公司成本价
                    else:
                        purchase_price = product_data['okgj_cost_price']
                else:
                    okgj_api_log_error('Warehouse', str(one_order_dict['order_info']['warehouse_id']), 'Not found in ERP')
                    purchase_price = product_data['okgj_cost_price']
                try:
                    sale_price = float(one_product['actual_amount'])/float(one_product['goods_number'])
                except Exception as myerror:
                    okgj_api_log_error('Sys Error', one_product['goods_name'], str(myerror))
                    sale_price = 0
                need_purchase = False
                try:
                    if int(one_product['is_booking']) > 0:
                        need_purchase = True
                except:
                    pass
                order_lines.append((0, 0, {'name':one_product['goods_name'],
                                           'product_id' : product_id[0],
                                           'product_uom':uom_id,
                                           'price_unit' : sale_price,
                                           'purchase_price':purchase_price,
                                           'okgj_discount': 0,
                                           'product_uom_qty' : one_product['goods_number'],
                                           'need_purchase':need_purchase,
                                           }))
            order_vals.update({'order_line':order_lines})
            order_list.append(order_vals)
        return order_list

    def _create_order_data(self, cr, uid, order_data, context=None):
        """ 
        @param order_data:订单数据信息
        @return: 移除队列与完成队列，余下部分交给下一个方法处理
        """
        done_queue = []
        remove_queue =[]
        if context is None:
            context = {}
        picking_obj = self.pool.get('stock.picking.out')
        wf_service = netsvc.LocalService("workflow")
        for one_order_data in order_data:
            has_order = self.search(cr, uid, [('name', '=', one_order_data['name'])], context=context, count=True)
            if (has_order > 0):
                okgj_api_log_error('Sales Order', one_order_data['name'], 'Has in the system!')
                continue
            try:
                sale_order_id = self.create(cr, uid, one_order_data, context=context)
            except Exception as myerror:
                okgj_api_log_error('Sys Error', one_order_data['name'], str(myerror))
                #订单创建异常
                okgj_api_log_error('Sales Order', one_order_data['name'], 'Fail to create sale order!')
                continue
            try:
                cr.commit()
            except:
                 continue
            _logger.info('Get order %s succeed!', one_order_data['name'])
            done_queue.append([one_order_data.get('okgj_order_type', ''), one_order_data['name'], one_order_data['okgj_shop_order_id']])
            remove_queue.append([one_order_data.get('okgj_order_type', ''), one_order_data['name'], one_order_data['okgj_shop_order_id']])
            try:
                wf_service.trg_validate(uid, "sale.order", sale_order_id, 'order_confirm', cr)
            except Exception as myerror:
                okgj_api_log_error('Sys Error', one_order_data['name'], str(myerror))
                #订单确认异常
                okgj_api_log_error('Sales Order', one_order_data['name'], 'Fail to confirm sale order!')
                continue
            picking_id = picking_obj.search(cr, uid, [('sale_id', '=', sale_order_id), ('type', '=', 'out')], context=context)
            if picking_id:
                try:
                    picking_obj.action_assign(cr, uid, picking_id)
                    ## picking_obj.draft_force_assign(cr, uid, picking_id)
                    ## picking_obj.force_assign(cr, uid, picking_id)
                except Exception as myerror:
                    okgj_api_log_error('Sys Error', one_order_data['name'], str(myerror))
                    #发货单确认异常
                    okgj_api_log_error('Sales Order', one_order_data['name'], 'Fail to confirm delivery order!')
        return (done_queue, remove_queue)

    def _remove_local_sale_order_queue(self, cr, uid, local_queue, context=None):
        """ 处理本地队列    
        """
        okshop_done_table = "get_order_queue_done"
        okkg_done_table = "get_okkg_order_queue_done"
        done_key = "order_no"
        for one_queue in local_queue:
            done_value = one_queue[1]
            if one_queue[0] == 'okshop':
                _logger.info('_remove_local_sale_order_queue %s %s %s' % (one_queue[0],done_key,done_value ))
                redis_check_done(redis_pool, okshop_done_table, done_key, done_value)
            elif one_queue[0] == 'okkg':
                _logger.info('_remove_local_sale_order_queue %s %s %s' % (one_queue[0],done_key,done_value ))
                redis_check_done(redis_pool, okkg_done_table, done_key, done_value)
            elif one_queue[0] == 'okapp':
                _logger.info('_remove_local_sale_order_queue %s %s %s' % (one_queue[0],done_key,done_value ))
                redis_check_done(redis_pool, okshop_done_table, done_key, done_value)
            elif one_queue[0] == 'okwd':
                # okwd order is from  get_order_queue, not okkg_order_queue
                okkg_done_table = "get_order_queue_done"
                _logger.info('_remove_local_sale_order_queue %s %s %s' % (one_queue[0],done_key,done_value ))
                redis_check_done(redis_pool, okshop_done_table, done_key, done_value)
            else:
                _logger.info('_remove_local_sale_order_queue %s %s %s' % (one_queue[0],done_key,done_value ))
                redis_check_done(redis_pool, okkg_done_table, done_key, done_value)
        return True

    def _remove_final_sale_order_queue(self, cr, uid, final_queue, context=None):
        """ 处理商场队列
        """
        if context is None:
            context = {}
        okshop_remove_table = "do_order_queue_remove"
        okkg_remove_table = "do_okkg_order_queue_remove"
        remove_key = "order_id"
        for one_queue in final_queue:
            remove_value = one_queue[2]
            if one_queue[0] == 'okshop':
                _logger.info('_remove_final_sale_order_queue %s %s %s' % (one_queue[0],remove_key,remove_value ))
                redis_check_done_remove(redis_pool, okshop_remove_table, remove_key, remove_value)
            elif one_queue[0] == 'okkg':
                _logger.info('_remove_final_sale_order_queue %s %s %s' % (one_queue[0],remove_key,remove_value ))
                redis_check_done_remove(redis_pool, okkg_remove_table, remove_key, remove_value)
            elif one_queue[0] == 'okapp':
                _logger.info('_remove_final_sale_order_queue %s %s %s' % (one_queue[0],remove_key,remove_value ))
                redis_check_done_remove(redis_pool, okshop_remove_table, remove_key, remove_value)
            else:
                _logger.info('_remove_final_sale_order_queue %s %s %s' % (one_queue[0],remove_key,remove_value ))
                redis_check_done_remove(redis_pool, okkg_remove_table, remove_key, remove_value)
        return True

    def okgj_sale_order_cron(self, cr, uid, use_new_cursor=False, group_letters='0123456789',context=None, ):
        
        
        if context is None:
            context = {}
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        ## 商城数据
        order_data = self._get_okshop_order_data(cr, uid, group_letters=group_letters,context=context,)
        ## 快购数据
        order_data += self._get_okkg_order_data(cr, uid, group_letters=group_letters,context=context,)
        
        #return True
        if order_data:
            (local_queue, final_queue) = self._create_order_data(cr, uid, order_data, context=context)
            if local_queue:
                self._remove_local_sale_order_queue(cr, uid, local_queue, context=context)
            if final_queue:
                self._remove_final_sale_order_queue(cr, uid, final_queue, context=context)
        if use_new_cursor:
            cr.close()
        return {}

    def okgj_sale_order_check_draft_cron(self, cr, uid, use_new_cursor=False, context=None):
        if context is None:
            context = {}
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        wf_service = netsvc.LocalService("workflow")
        draft_ids = self.search(cr, uid, [('state', 'in', ['draft'])], context=context)
        for one_id in draft_ids:
            try:
                wf_service.trg_validate(uid, "sale.order", one_id, 'order_confirm', cr)
            except Exception as myerror:
                okgj_api_log_error('Sys Error', str(one_id), str(myerror))
                okgj_api_log_error('Sales Order', str(one_id), 'Order_id, Fail to confirm sale order!')
                continue
        cr.commit()
        if use_new_cursor:
            cr.close()
        return {}

    ##取消订单方法开始
    def _get_okshop_cancel_order_data(self, cr, uid, context=None):
        """
        获取取消队列数据,返回订单ID
        """
        if context is None:
            context = {}
        redis_table = "get_order_cancel_list"
        done_table = "get_order_cancel_list_done"
        order_str_datas = redis_check(redis_pool, redis_table, done_table)
        count = 10
        cancel_order_queue = []
        for one_order_no in order_str_datas:
            order_no = one_order_no[9:]
            order_id = self.search(cr, uid, [('name', '=', order_no)], context=context)
            if isinstance(order_id, (long, int)):
                order_id = [order_id]
            if len(order_id) != 1:
                #未找到销售订单
                okgj_api_log_error('OKShop Cancel Order', order_no, 'Fail to get order, not found!')
                continue
            cancel_order_queue.append(['okshop', order_no, order_id[0]])
        return cancel_order_queue

    def _get_okkg_cancel_order_data(self, cr, uid, context=None):
        """
        获取取消队列数据,返回订单ID
        """
        redis_table = "get_okkg_order_cancel_list"
        done_table = "get_okkg_order_cancel_list_done"
        order_str_datas = redis_check(redis_pool, redis_table, done_table)
        count = 10
        cancel_order_queue = []
        for one_order_no in order_str_datas:
            order_no = one_order_no[9:]
            order_id = self.search(cr, uid, [('name', '=', order_no)], context=context)
            if isinstance(order_id, (long, int)):
                order_id = [order_id]
            if len(order_id) != 1:
                #未找到销售订单
                okgj_api_log_error('OKKG Cancel Order', order_no, 'Fail to get order, not found!')
                continue
            cancel_order_queue.append(['okkg', order_no, order_id[0]])
        return cancel_order_queue

    def _create_cancel_order_data(self, cr, uid, order_queue, context=None):
        done_queue = []
        remove_queue =[]
        if context is None:
            context = {}
        count = 10
        picking_obj = self.pool.get('stock.picking.out')
        sale_return_obj = self.pool.get('okgj.sale.return')
        wf_service = netsvc.LocalService("workflow")
        for one_order_data in order_queue:
            count -= 1
            order_no = one_order_data[1]
            order_id = one_order_data[2]
            origin_sale_order_data = self.browse(cr, uid, order_id, context=context)
            okgj_shop_order_id = origin_sale_order_data.okgj_shop_order_id
            warehouse_id = origin_sale_order_data.shop_id.warehouse_id.id
            picking_id = picking_obj.search(cr, uid, [('sale_id', '=', order_id), ('type', '=', 'out')], context=context)
            if picking_id:
                picking_state = picking_obj.read(cr, uid, picking_id[0], ['state'], context=context)['state']
                if picking_state == 'done':
                    return_data = {}
                    #获取源销售订单信息
                    return_data.update(sale_return_obj.onchange_order_id(cr, uid, [], order_id, context)['value'])
                    return_data.update({
                        'name': self.pool.get('ir.sequence').get(cr, uid, 'okgj.sale.return'),
                        'sale_order_id':order_id,
                        'invoice_state':'none',
                        'warehouse_id':warehouse_id,
                        'by_okgj_shop':True,
                        'date_planned':time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),})
                    try:
                        return_id = sale_return_obj.create(cr, uid, return_data, context=context)
                    except Exception as myerror:
                        okgj_api_log_error('Sys Error', order_no, str(myerror))
                        #创建退货单失败,继续创建
                        okgj_api_log_error('Return Order', order_no, 'Fail to create return order!')
                        continue
                    try:
                        cr.commit()
                    except:
                        continue
                    _logger.info('Create Return order Succeed, Cancel order %s.', order_no)
                    self.write(cr, uid, order_id, {'okgj_shop_cancel':True}, context=context)
                    try:
                        ##sale_return_obj.action_confirm(cr, uid, return_id, context=context)
                        sale_return_obj.action_validate(cr, uid, return_id, context=context)
                    except Exception as myerror:
                        #确认退换货失败
                        okgj_api_log_error('Sys Error', order_no, str(myerror))
                        okgj_api_log_error('Return Order', order_no, 'Fail to confirm return order!')
                    try:
                        cr.commit()
                    except:
                        continue
                    _logger.info('Cancel order %s Succeed. Has create return order!', order_no)
                    done_queue.append([one_order_data[0],  order_no, okgj_shop_order_id])
                    remove_queue.append([one_order_data[0],  order_no, okgj_shop_order_id])
                else:
                    try:
                        wf_service.trg_validate(uid, "stock.picking", picking_id[0], 'button_cancel', cr)
                        #形式发票未进行处理，取消该订单
                    except Exception as myerror:
                        okgj_api_log_error('Sys Error', order_no, str(myerror))
                        #取消发货单失败，继续尝试
                        okgj_api_log_error('Sales Order', order_no, 'Cancel picking order failed!')
                        #redis_check_done(redis_pool, done_table, done_key, done_value)
                        continue
                    try:
                        self.action_cancel(cr, uid, [order_id], context=context)
                    except Exception as myerror:
                        #取消销售订单失败，继续取消
                        okgj_api_log_error('Sys Error', order_no, str(myerror))
                        okgj_api_log_error('Sales Order', order_no, 'Cancel sale order failed!')
                        continue
                    try:
                        cr.commit()
                    except:
                        continue
                    _logger.info('Cancel order %s Succeed.', order_no)
                    done_queue.append([one_order_data[0],  order_no, okgj_shop_order_id])
                    remove_queue.append([one_order_data[0],  order_no, okgj_shop_order_id])
            else:
                try:
                    self.action_cancel(cr, uid, [order_id], context=context)
                except Exception as myerror:
                    okgj_api_log_error('Sys Error', order_no, str(myerror))
                    #未出库单，且取消销售订单失败，继续取消
                    okgj_api_log_error('Sales Order', order_no, 'Cancel sale order failed!')
                    continue
                cr.commit()
                _logger.info('Cancel order %s Succeed.', order_no)
                done_queue.append([one_order_data[0],  order_no, okgj_shop_order_id])
                remove_queue.append([one_order_data[0],  order_no, okgj_shop_order_id])
            if count <= 1:
                count = 10
                cr.commit()
        cr.commit()
        return (done_queue, remove_queue)

    def _remove_local_cancel_order_queue(self, cr, uid, local_queue, context=None):
        okshop_done_table = "get_order_cancel_list_done"
        okkg_done_table = "get_okkg_order_cancel_list_done"
        done_key = "order_no"
        for one_queue in local_queue:
            done_value = one_queue[1]
            if one_queue[0] == 'okshop':
                redis_check_done(redis_pool, okshop_done_table, done_key, done_value)
            elif one_queue[0] == 'okkg':
                redis_check_done(redis_pool, okkg_done_table, done_key, done_value)
        return True
    
    def _remove_final_cancel_order_queue(self, cr, uid, final_queue, context=None):
        okshop_remove_table = "do_order_cancel_queue_remove"
        okkg_remove_table = "do_okkg_order_cancel_queue_remove"
        remove_key = "order_id"
        for one_queue in final_queue:
            remove_value = one_queue[2]
            if one_queue[0] == 'okshop':
                redis_check_done_remove(redis_pool, okshop_remove_table, remove_key, remove_value)
            elif one_queue[0] == 'okkg':
                redis_check_done_remove(redis_pool, okkg_remove_table, remove_key, remove_value)
        return True

    def okgj_sale_order_cancel_cron(self, cr, uid, use_new_cursor=False, context=None):
        if context is None:
            context = {}
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        ## 商城数据
        order_data = self._get_okshop_cancel_order_data(cr, uid, context=context)
        ## 快购数据
        order_data += self._get_okkg_cancel_order_data(cr, uid, context=context)
        if order_data:
            (local_queue, final_queue) = self._create_cancel_order_data(cr, uid, order_data, context=context)
            if local_queue:
                self._remove_local_cancel_order_queue(cr, uid, local_queue, context=context)
            if final_queue:
                self._remove_final_cancel_order_queue(cr, uid, final_queue, context=context)
        if use_new_cursor:
            cr.close()
        return {}

##销售退换货单
class okgj_sale_return_order_api(osv.osv):
    _inherit = 'okgj.sale.return'
    _columns = {
        'add_time': fields.datetime(u'退货时间', readonly=True, select=True),
        'confirm_time':fields.datetime(u'确认时间'),
        'mobile':fields.char(u'手机', size=16),
        ##'order_id':fields.char(u'原销售订单ID', size=32),
        'log_time': fields.datetime(u'客服记录时间', readonly=True, select=True),
        'picking_policy': fields.selection([
            ('direct', 'Deliver each product when available'),
            ('one', 'Deliver all products at once')
            ], 'Shipping Policy', required=True),
        'return_type':fields.selection([
            ('1', u'退货单'),
            ('2', u'换货单'),
            ('3', u'退换货单'),
            ], u'单据类型', required=True),
        'refund_type':fields.selection([
            ('0', u'不需要'),
            ('1', u'需要退款'),
            ], u'退款', required=True),
        'return_time':fields.text(u'退换次数'),
        ## 'status':fields.selection([
        ##     ('1', u'需要退款'),
        ##     ('2', u'不需要'),
        ##     ], u'订单状态', required=True),
        'total_fee': fields.float(u'总费用', digits_compute=dp.get_precision('Product Price')),
        'okgj_user_id':fields.char(u'会员账号', size=32),
        'by_okgj_shop':fields.boolean(u'商城下单', readonly=True),
        'okgj_order_type':fields.selection([
            ('erp', u'ERP'),
            ('okshop', u'商场'),
            ('okkg', u'快购'),
            ('others', u'其它'),
            ], u'订单来源', readonly=True),
    }
        
    _defaults = {
        'return_type': '1',
        'refund_type':'1',
        'picking_policy':'one',
    }

    def _get_okshop_return_order_data(self, cr, uid, context=None):
        """
        获取取消队列数据,返回订单ID
        """
        if context is None:
            context = {}
        ## return type 1 退货，2 换货
        redis_table = "get_order_return_list"
        done_table = "get_order_return_list_done"
        detail_table = "get_order_return_detail"
        p_column = "answer"
        return_order_list = []
        sale_obj = self.pool.get('sale.order')
        sale_line_obj = self.pool.get('sale.order.line')
        product_obj = self.pool.get('product.product')

        order_str_datas = redis_get(redis_pool, redis_table, done_table, detail_table, p_column)
        for one_order_str in order_str_datas:
            one_order_dict = json.loads(one_order_str)
            order_sn = one_order_dict['order_info']['order_sn']
            okgj_api_log_error('Return Order', order_sn, 'start processing!')
            if isinstance(order_sn, (int, long)):
                order_sn = str(order_sn)
            sale_order_id = sale_obj.search(cr, uid, [('name', '=', order_sn)], context=context)
            if not sale_order_id:
                #未找到源销售订单，需在下次继续创建
                okgj_api_log_error('OKShop Return Order', order_sn, 'Failed to fetch sale order, not found, will move to done queue!')
                continue
            if len(sale_order_id) != 1:
                #找到多个销售订单
                okgj_api_log_error('OKShop Return Order', order_sn, 'More sale order found!')
                continue
            order_vals = {}
            order_vals.update({
                'okgj_order_type': 'okshop',
                'order_no': order_sn,
                'back_id': one_order_dict['order_info']['back_id'],
                'action_note' : (one_order_dict['order_action'] and one_order_dict['order_action'][0]['action_note']) or None,
                'date_planned':(datetime.datetime.fromtimestamp(one_order_dict['order_info']['add_time']) + relativedelta(hours=8)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                ## 'date_planned':(datetime.datetime.fromtimestamp(one_order_dict['order_action'][0]['log_time']) + relativedelta(hours=8)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                #time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.localtime(one_order_dict['order_action'][0]['log_time'])) or None,
                ## 'action_return_type' : one_order_dict['order_action'][0]['action_note'] or None,
                'action_return_type' : one_order_dict['order_info']['return_type'] or None,
                ## 'return_status' : one_order_dict['order_action'][0]['status'] or None,
                'return_status' : one_order_dict['order_info']['status'] or None,
                'sale_order_id' : sale_order_id[0],
                'region_name' : one_order_dict['order_info']['region_name'],
                'address' : one_order_dict['order_info']['address'],
                'name' : one_order_dict['order_info']['back_id'],
                'best_time' : one_order_dict['order_info']['best_time'],
                'confirm_time' : (datetime.datetime.fromtimestamp(one_order_dict['order_info']['confirm_time']) + relativedelta(hours=8)).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                #time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.localtime(one_order_dict['order_info']['confirm_time'])) or None,
                'consignee':one_order_dict['order_info']['consignee'],
                'picking_policy' : 'one',
                'mobile' : one_order_dict['order_info']['mobile'],
                'refund_amount' : one_order_dict['order_info']['refund_amount'],
                'refund_type' : str(one_order_dict['order_info']['refund_type']),
                'return_type' : str(one_order_dict['order_info']['return_type']),
                #'refund_name' : one_order_dict['order_info']['refund_name'] or None,
                'return_info' : one_order_dict['order_info']['return_info'],
                'return_time' : one_order_dict['order_info']['return_time'],
                'shipping_fee' : one_order_dict['order_info']['shipping_fee'],
                ## 'status' : one_order_dict['order_info']['status'],
                'tel' : one_order_dict['order_info']['tel'],
                'okgj_user_id' : one_order_dict['order_info']['user_id'],
                'total_fee' : one_order_dict['order_info']['total_fee'],
                'warehouse_id' : 1, #大家以后一起跟着商城跑
                'by_okgj_shop':True
                })
            ## status = one_order_dict['order_action'][0]['return_type']
            status = one_order_dict['order_info']['return_type']
            old_order_lines = []
            new_order_lines = []
            for one_product in one_order_dict['product_list']:
                goods_sn = one_product['goods_sn']
                if isinstance(goods_sn, (int, long)):
                    goods_sn = str(goods_sn)
                product_id = product_obj.search(cr, uid, [('default_code', '=', goods_sn)], context=context)
                if isinstance(product_id, (long, int)):
                    product_id = [product_id]
                if len(product_id) != 1:
                    okgj_api_log_error('Product', goods_sn, 'Failed to fetch product, not found!')
                    continue
                uom_id = product_obj.browse(cr, uid, product_id[0], context=context).uom_id.id
                origin_line_id = sale_line_obj.search(cr, uid, [('order_id', '=', sale_order_id[0]), ('product_id', '=', product_id[0])], context=context)
                price_unit = sale_line_obj.read(cr, uid, origin_line_id[0], ['price_unit'], context=context)['price_unit']
                old_order_lines.append((0, 0, {
                    'product_id':product_id[0],
                    'product_uom':uom_id,
                    #'name':one_product['goods_name'],
                    'price_unit' : price_unit or 0,
                    'product_qty' : one_product['send_number']}))
                if status == 2:
                    new_order_lines.append((0, 0, {
                        'product_id':product_id[0],
                        'product_uom':uom_id,
                        #'name':one_product['goods_name'],
                        'price_unit' : price_unit or 0,
                        'product_qty' : one_product['send_number']}))
            order_vals.update({'invoice_state':'none', 'old_line_ids':old_order_lines,'new_line_ids':new_order_lines})
            return_order_list.append(order_vals)
        return return_order_list

    def _get_okkg_return_order_data(self, cr, uid, context=None):
        """
        获取取消队列数据,返回订单ID
        """
        if context is None:
            context = {}
        ## return type 1 退货，2 换货
        redis_table = "get_okkg_order_return_list"
        done_table = "get_okkg_order_return_list_done"
        detail_table = "get_okkg_order_return_detail"
        p_column = "answer"
        return_order_list = []
        sale_obj = self.pool.get('sale.order')
        sale_line_obj = self.pool.get('sale.order.line')
        product_obj = self.pool.get('product.product')
        order_str_datas = redis_get(redis_pool, redis_table, done_table, detail_table, p_column)
        for one_order_str in order_str_datas:
            one_order_dict = json.loads(one_order_str)
            order_sn = one_order_dict['order_info']['order_sn']
            okgj_api_log_error('Return Order', order_sn, 'start processing!')
            if isinstance(order_sn, (int, long)):
                order_sn = str(order_sn)
            sale_order_id = sale_obj.search(cr, uid, [('name', '=', order_sn)], context=context)
            if not sale_order_id:
                #未找到源销售订单，需在下次继续创建
                okgj_api_log_error('Return Order', order_sn, 'Failed to fetch sale order, not found, will move to done queue!')
                continue
            if len(sale_order_id) != 1:
                #找到多个销售订单
                okgj_api_log_error('Return Order', order_sn, 'More sale order found!')
                continue
            order_vals = {}
            order_vals.update({
                'okgj_order_type': 'okkg',
                'order_no': order_sn,
                'back_id': one_order_dict['order_info']['back_id'],
                'action_note' : (one_order_dict['order_action'] and one_order_dict['order_action'][0]['action_note']) or None,
                'date_planned':(datetime.datetime.fromtimestamp(one_order_dict['order_info']['add_time'])).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                #time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.localtime(one_order_dict['order_action'][0]['log_time'])) or None,
                'action_return_type' : one_order_dict['order_info']['return_type'] or None,
                'return_status' : '',
                'sale_order_id' : sale_order_id[0],
                'region_name' : one_order_dict['order_info']['region_name'],
                'address' : one_order_dict['order_info']['address'],
                'name' : one_order_dict['order_info']['back_id'],
                'best_time' : '',
                'confirm_time' : (datetime.datetime.fromtimestamp(one_order_dict['order_info']['confirm_time'])).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                #time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.localtime(one_order_dict['order_info']['confirm_time'])) or None,
                'consignee':one_order_dict['order_info']['consignee'],
                'picking_policy' : 'one',
                'mobile' : one_order_dict['order_info']['mobile'],
                'refund_amount' : one_order_dict['order_info']['refund_amount'],
                'refund_type' : '',
                'return_type' : str(one_order_dict['order_info']['return_type']),
                #'refund_name' : one_order_dict['order_info']['refund_name'] or None,
                'return_info' : one_order_dict['order_info']['return_info'],
                'return_time' : one_order_dict['order_info']['return_time'],
                'shipping_fee' : one_order_dict['order_info']['shipping_fee'],
                ## 'status' : one_order_dict['order_info']['status'],
                'tel' : one_order_dict['order_info']['mobile'],
                'okgj_user_id' : one_order_dict['order_info']['user_id'],
                'total_fee' : one_order_dict['order_info']['total_fee'],
                'warehouse_id' : 1, #大家以后一起跟着商城跑
                'by_okgj_shop':True
                })
            status = one_order_dict['order_info']['return_type']
            old_order_lines = []
            new_order_lines = []
            for one_product in one_order_dict['product_list']:
                goods_sn = one_product['goods_sn']
                if isinstance(goods_sn, (int, long)):
                    goods_sn = str(goods_sn)
                product_id = product_obj.search(cr, uid, [('default_code', '=', goods_sn)], context=context)
                if isinstance(product_id, (long, int)):
                    product_id = [product_id]
                if len(product_id) != 1:
                    okgj_api_log_error('Product', goods_sn, 'Failed to fetch product, not found!')
                    continue
                uom_id = product_obj.browse(cr, uid, product_id[0], context=context).uom_id.id
                origin_line_id = sale_line_obj.search(cr, uid, [('order_id', '=', sale_order_id[0]), ('product_id', '=', product_id[0])], context=context)
                price_unit = sale_line_obj.read(cr, uid, origin_line_id[0], ['price_unit'], context=context)['price_unit']
                old_order_lines.append((0, 0, {
                    'product_id':product_id[0],
                    'product_uom':uom_id,
                    #'name':one_product['goods_name'],
                    'price_unit' : price_unit or 0,
                    'product_qty' : one_product['send_number']}))
                if status == 2:
                    new_order_lines.append((0, 0, {
                        'product_id':product_id[0],
                        'product_uom':uom_id,
                        #'name':one_product['goods_name'],
                        'price_unit' : price_unit or 0,
                        'product_qty' : one_product['send_number']}))
            order_vals.update({'invoice_state':'none', 'old_line_ids':old_order_lines,'new_line_ids':new_order_lines})
            return_order_list.append(order_vals)
        return return_order_list

    def _create_return_order_data(self, cr, uid, return_order_data, context=None):
        """
        依据数据创建退换货
        """
        done_queue = []
        remove_queue =[]
        count = 10
        for one_order_data in return_order_data:
            count -= 1
            order_sn = one_order_data['order_no']
            try:
                okgj_sale_return_order_id = self.create(cr, uid, one_order_data, context=context)
            except Exception as myerror:
                #退换货单创建失败，不再创建
                okgj_api_log_error('Sys Error', order_sn, str(myerror))
                okgj_api_log_error('Return Order', order_sn, 'Failed to create sale return order!')
                continue
            try:
                cr.commit()
            except:
                continue
            _logger.info('Get return order %s succeed!', order_sn)
            done_queue.append([one_order_data.get('okgj_order_type', ''),  order_sn, one_order_data['back_id']])
            remove_queue.append([one_order_data.get('okgj_order_type', ''),  order_sn, one_order_data['back_id']])
            try:
                self.action_validate(cr, uid, okgj_sale_return_order_id, context=context)
            except Exception as myerror:
                okgj_api_log_error('Sys Error', order_sn, str(myerror))
                #退换货确认失败
                okgj_api_log_error('Return Order', order_sn, 'Failed to confirm sale return order!')
            if count <= 1:
                count = 10
                cr.commit()
        cr.commit()
        return (done_queue, remove_queue)

    def _remove_local_return_order_queue(self, cr, uid, local_queue, context=None):
        okshop_done_table = "get_order_return_list_done"
        okkg_done_table = "get_okkg_order_return_list_done"
        done_key = "back_id"
        for one_queue in local_queue:
            done_value = one_queue[2]
            if one_queue[0] == 'okshop':
                redis_check_done(redis_pool, okshop_done_table, done_key, done_value)
            elif one_queue[0] == 'okkg':
                redis_check_done(redis_pool, okkg_done_table, done_key, done_value)
        return True
    
    def _remove_final_return_order_queue(self, cr, uid, final_queue, context=None):
        okshop_remove_table = "do_order_return_queue_remove"
        okkg_remove_table = "do_okkg_order_return_queue_remove"
        remove_key = "back_id"
        for one_queue in final_queue:
            remove_value = one_queue[2]
            if one_queue[0] == 'okshop':
                redis_check_done_remove(redis_pool, okshop_remove_table, remove_key, remove_value)
            elif one_queue[0] == 'okkg':
                redis_check_done_remove(redis_pool, okkg_remove_table, remove_key, remove_value)
        return True

    def okgj_sale_return_order_cron(self, cr, uid, use_new_cursor=False, context=None):
        if context is None:
            context = {}
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        ## 商城数据
        order_data = self._get_okshop_return_order_data(cr, uid, context=context)
        ## 快购数据
        order_data += self._get_okkg_return_order_data(cr, uid, context=context)
        if order_data:
            (local_queue, final_queue) = self._create_return_order_data(cr, uid, order_data, context=context)
            if local_queue:
                self._remove_local_return_order_queue(cr, uid, local_queue, context=context)
            if final_queue:
                self._remove_final_return_order_queue(cr, uid, final_queue, context=context)
        if use_new_cursor:
            cr.close()
        return {}


##库存变化, do_stock_in, do_stock_out
class okgj_stock_move_api(osv.osv):
    _inherit = 'stock.move'
    def action_done(self, cr, uid, ids, context=None):
        super(okgj_stock_move_api, self).action_done(cr, uid, ids, context=context)
        uom_obj = self.pool.get('product.uom')
        warehouse_obj = self.pool.get('stock.warehouse')
        warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)
        okgj_lot_stock_dict = {}
        for one_warehouse in warehouse_obj.browse(cr, uid, warehouse_ids, context=context):
            okgj_lot_stock_dict.update({one_warehouse.lot_stock_id.id : one_warehouse.id})
        #数据结构 {warehouse_id:{product_default_code:product_qty}}
        location_ids = okgj_lot_stock_dict.keys()
        final_in_qty_data = {}
        final_out_qty_data = {}
        final_erp_out_qty_data = {}
        for one_move in self.browse(cr, uid, ids, context=context):
            if one_move.location_id.id != one_move.location_dest_id.id:
                #商城下单销售出库
                if one_move.location_id.id in location_ids:
                    if (one_move.picking_id and one_move.picking_id.sale_id and one_move.picking_id.sale_id.by_okgj_shop) or (one_move.picking_id and one_move.picking_id.sale_return_id and one_move.picking_id.sale_return_id.by_okgj_shop) :
                        product_goods_no = one_move.product_id.default_code
                        product_base_uom = one_move.product_id.uom_id.id
                        move_uom = one_move.product_uom.id
                        product_real_qty = one_move.product_qty
                        if product_base_uom != move_uom:
                            product_real_qty = uom_obj._compute_qty(cr, uid, move_uom, one_move.product_qty, product_base_uom)
                        warehouse_id = okgj_lot_stock_dict[one_move.location_id.id]
                        if not final_out_qty_data.get(warehouse_id, False):
                            final_out_qty_data[warehouse_id] = {}
                        if not final_out_qty_data[warehouse_id].get(product_goods_no, False):
                            final_out_qty_data[warehouse_id][product_goods_no] = product_real_qty
                        else:
                            final_out_qty_data[warehouse_id][product_goods_no] += product_real_qty
                    else:
                        product_goods_no = one_move.product_id.default_code
                        product_base_uom = one_move.product_id.uom_id.id
                        move_uom = one_move.product_uom.id
                        product_real_qty = one_move.product_qty
                        if product_base_uom != move_uom:
                            product_real_qty = uom_obj._compute_qty(cr, uid, move_uom, one_move.product_qty, product_base_uom)
                        warehouse_id = okgj_lot_stock_dict[one_move.location_id.id]
                        if not final_erp_out_qty_data.get(warehouse_id, False):
                            final_erp_out_qty_data[warehouse_id] = {}
                        if not final_erp_out_qty_data[warehouse_id].get(product_goods_no, False):
                            final_erp_out_qty_data[warehouse_id][product_goods_no] = product_real_qty
                        else:
                            final_erp_out_qty_data[warehouse_id][product_goods_no] += product_real_qty
                #入库
                if one_move.location_dest_id.id in location_ids:
                    product_goods_no = one_move.product_id.default_code
                    product_base_uom = one_move.product_id.uom_id.id
                    move_uom = one_move.product_uom.id
                    product_real_qty = one_move.product_qty
                    if product_base_uom != move_uom:
                        product_real_qty = uom_obj._compute_qty(cr, uid, move_uom, one_move.product_qty, product_base_uom)
                    warehouse_id = okgj_lot_stock_dict[one_move.location_dest_id.id]
                    if not final_in_qty_data.get(warehouse_id, False):
                        final_in_qty_data[warehouse_id] = {}
                    if not final_in_qty_data[warehouse_id].get(product_goods_no, False):
                        final_in_qty_data[warehouse_id][product_goods_no] = product_real_qty
                    else:
                        final_in_qty_data[warehouse_id][product_goods_no] += product_real_qty 
        #开始提交,后期将与接口协商物流中心处理
        out_table = "do_stock_out"
        erp_out_table = "do_erp_stock_out"
        in_table = "do_stock_in"
        p_key = "goods_no"
        for one_out_warehouse in final_out_qty_data.keys():
            okgj_warehouse_id = warehouse_obj.read(cr, uid, one_out_warehouse, ['okgj_warehouse_id'], context=context)['okgj_warehouse_id']
            for one_goods_no in final_out_qty_data[one_out_warehouse].keys():
                p_value = one_goods_no + '_' + uuid.uuid4().hex
                arg = {"out_count": int(round(final_out_qty_data[one_out_warehouse][one_goods_no])), "warehouse_id":okgj_warehouse_id}
                redis_do(redis_pool, out_table, p_key,  p_value, arg)
        for one_erp_out_warehouse in final_erp_out_qty_data.keys():
            okgj_warehouse_id = warehouse_obj.read(cr, uid, one_erp_out_warehouse, ['okgj_warehouse_id'], context=context)['okgj_warehouse_id']
            for one_goods_no in final_erp_out_qty_data[one_erp_out_warehouse].keys():
                p_value = one_goods_no + '_' + uuid.uuid4().hex
                arg = {"out_count": int(round(final_erp_out_qty_data[one_erp_out_warehouse][one_goods_no])), "warehouse_id":okgj_warehouse_id}
                redis_do(redis_pool, erp_out_table, p_key,  p_value, arg)
        for one_in_warehouse in final_in_qty_data.keys():
            okgj_warehouse_id = warehouse_obj.read(cr, uid, one_in_warehouse, ['okgj_warehouse_id'], context=context)['okgj_warehouse_id']
            for one_goods_no in final_in_qty_data[one_in_warehouse].keys():
                p_value = one_goods_no + '_' + uuid.uuid4().hex
                arg = {"in_count":int(round(final_in_qty_data[one_in_warehouse][one_goods_no])), "warehouse_id":okgj_warehouse_id}
                redis_do(redis_pool, in_table, p_key, p_value, arg)
        return True

class okgj_multi_order_print_api(osv.osv):
    _inherit = "okgj.multi.order.print"

    def create(self, cr, uid, vals, context=None):
        new_multi_id = super(okgj_multi_order_print_api,self).create(cr, uid, vals, context=context)
        #cr.commit()
        picking_ids = vals.get('picking_ids', False)
        order_table = "do_update_order_status"
        p_key = "order_no"
        picking_data = self.pool.get('stock.picking.out').browse(cr, uid, picking_ids[0][2], context=context)
        uname = self.pool.get('res.users').read(cr, uid, uid, ['name'], context=context)['name'] or ''
        for one_pick in picking_data:
            p_value = one_pick.sale_id and one_pick.sale_id.name or False
            if p_value:
                p_value = p_value + '_' + uuid.uuid4().hex
                arg = {
                    "status": 10,
                    "update_time":int(round(time.time())),
                    "note":json.JSONEncoder().encode({'name':uname})}
                    #str({'name':uname})}
                redis_do(redis_pool, order_table, p_key, p_value, arg)
        return new_multi_id

## class okgj_stock_out_verify_api(osv.osv_memory):
##     _inherit = "okgj.stock.out.verify"
##     def action_process(self, cr, uid, ids, context=None):
##         super(okgj_stock_out_verify_api,self).action_process(cr, uid, ids, context=context)
##         order_table = "do_update_order_status"
##         p_key = "order_no"
##         for one_verify in self.browse(cr, uid, ids, context=context):
##             p_value = one_verify.picking_id and one_verify.picking_id.sale_id and one_verify.picking_id.sale_id.name or False
##             if p_value:
##                 p_value = p_value + '_' + uuid.uuid4().hex
##                 arg = {
##                     "status": 20,
##                     "update_time":int(round(time.time())),
##                     "note":''}
##                 redis_do(redis_pool, order_table, p_key, p_value, arg)
##         return True


#装车
class okgj_logistics_api(osv.osv):
    _inherit = "okgj.logistics"

    def action_start(self, cr, uid, ids, context=None):
        super(okgj_logistics_api,self).action_start(cr, uid, ids, context=context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        uname = self.pool.get('res.users').read(cr, uid, uid, ['name'], context=context)['name'] or ''
        for one_logistics in self.browse(cr, uid, ids, context=context):
            if one_logistics.type == 'local':
                note = json.JSONEncoder().encode({'state':u'本地装车', 'car':one_logistics.car_id.driver, 'phone':one_logistics.car_id.driver_phone, 'name':uname})
                #str({'state':u'本地装车', 'car':one_logistics.car_id.driver, 'phone':one_logistics.car_id.driver_phone, 'name':uname})
            else:
                note =json.JSONEncoder().encode({'state':u'干线装车', 'dest': one_logistics.dest_shop.name, 'name':uname})
                #str({'state':u'干线装车', 'dest': one_logistics.dest_shop.name, 'name':uname})
            for one_line in one_logistics.line_ids:
                bp_value = one_line.sale_return_id and one_line.sale_return_id.name or False
                if one_logistics.type == 'three_side':  ##第三方物流
                    note = json.JSONEncoder().encode({'state':u'第三方物流装车', 'express_company':one_logistics.car_id.driver, 'express_no':one_line.three_side_picking, 'name':uname})
                if bp_value: ## 退换货单
                    order_table = "do_update_order_return_status"
                    p_key = "back_id"
                    bp_value = bp_value + '_' + uuid.uuid4().hex
                    arg = {
                        "order_sn":one_line.sale_order_id.name,
                        "status": 30,
                        "update_time":int(round(time.time())),
                        "note":note}
                    redis_do(redis_pool, order_table, p_key, bp_value, arg)
                else:  ## 正常订单
                    ap_value = one_line.sale_order_id and one_line.sale_order_id.name or False
                    order_table = "do_update_order_status"
                    p_key = "order_no"
                    ap_value = ap_value + '_' + uuid.uuid4().hex
                    arg = {
                        "status": 30,
                        "update_time":int(round(time.time())),
                        "note":note}
                    redis_do(redis_pool, order_table, p_key, ap_value, arg)
        return True

class okgj_logistics_line_api(osv.osv):
    _inherit = "okgj.logistics.line"

    def write(self, cr, uid, ids, vals, context=None):
        super(okgj_logistics_line_api, self).write(cr, uid, ids, vals, context=context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        uname = self.pool.get('res.users').read(cr, uid, uid, ['name'], context=context)['name'] or ''
        form = self.browse(cr, uid, ids[0], context=context)
        if form.sale_return_id:
            order_table = "do_update_order_return_status"
            p_key = "back_id"
            p_value = form.sale_return_id.name
            l_type = form.logistics_id.type
            if p_value:
                if (vals.get('state', False) == 'cancel'):
                    p_value = p_value + '_' + uuid.uuid4().hex
                    arg = {
                        "order_sn":form.sale_order_id.name,
                        "status": 45,
                        "update_time":int(round(time.time())),
                        "note":json.JSONEncoder().encode({'cause':vals.get('cause'), 'name':uname})}
                        #str({'cause':vals.get('cause'), 'name':uname})}
                    redis_do(redis_pool, order_table, p_key, p_value, arg)

                if (vals.get('state', False) == 'done'):
                    p_value = p_value + '_' + uuid.uuid4().hex
                    if l_type in ['local', 'three_side']:
                        status = 50
                    elif l_type == 'route':
                        status = 40
                    arg = {
                        "order_sn":form.sale_order_id.name,
                        "status": status,
                        "update_time":int(round(time.time())),
                        "note":json.JSONEncoder().encode({'notes':vals.get('notes'), 'name':uname}),
                        #"note":str({'notes':vals.get('notes'), 'name':uname})
                        }
                    redis_do(redis_pool, order_table, p_key, p_value, arg)
                ## 退换货单钱的状态是否需要上传
                ## if (vals.get('money_state', False) == 'done'):
                ##     p_value = p_value + '_' + uuid.uuid4().hex
                ##     arg = {
                ##         "order_sn":form.sale_order_id.name,
                ##         "status": 60,
                ##         "update_time":int(round(time.time())),
                ##         "note":str({'name':uname})}
                ##     redis_do(redis_pool, order_table, p_key, p_value, arg)
        elif form.picking_id:
            order_table = "do_update_order_status"
            p_key = "order_no"
            p_value = form.picking_id.sale_id and form.picking_id.sale_id.name
            l_type = form.logistics_id.type
            if p_value:
                if (vals.get('state', False) == 'cancel'):
                    p_value = p_value + '_' + uuid.uuid4().hex
                    arg = {
                        "status": 45,
                        "update_time":int(round(time.time())),
                        "note":json.JSONEncoder().encode({'cause':vals.get('cause'), 'name':uname})}
                         ##str({'cause':vals.get('cause'), 'name':uname})}
                    redis_do(redis_pool, order_table, p_key, p_value, arg)

                if (vals.get('state', False) == 'done'):
                    p_value = p_value + '_' + uuid.uuid4().hex
                    if l_type in ['local', 'three_side']:
                        status = 50
                    elif l_type == 'route':
                        status = 40
                    arg = {
                        "status": status,
                        "update_time":int(round(time.time())),
                        ## "note":str({'notes':vals.get('notes'), 'name':uname})
                        "note":json.JSONEncoder().encode({'notes':vals.get('notes'), 'name':uname})}
                    redis_do(redis_pool, order_table, p_key, p_value, arg)
                if (vals.get('money_state', False) == 'done'):
                    p_value = p_value + '_' + uuid.uuid4().hex
                    arg = {
                        "status": 60,
                        "update_time":int(round(time.time())),
                        "note":json.JSONEncoder().encode({'name':uname})}
                        #str({'name':uname})}
                    redis_do(redis_pool, order_table, p_key, p_value, arg)
        return True

class okgj_stock_picking_out(osv.osv):
    _inherit = "stock.picking.out"

    def okgj_sale_order_picking_check_cron(self, cr, uid, use_new_cursor=False, context=None):
        if context is None:
            context = {}
        if use_new_cursor:
            cr = pooler.get_db(use_new_cursor).cursor()
        wf_service = netsvc.LocalService("workflow")
        #picking_obj = self.pool.get('stock.picking.out')
        to_check_ids = self.search(cr, uid, [('state', 'in', ['confirmed']), ('type', '=', 'out'), ('sale_id', '!=', False)], context=context)
        for one_id in to_check_ids:
            try:
                self.action_assign(cr, uid, [one_id])
                ## picking_obj.draft_force_assign(cr, uid, picking_id)
                ## picking_obj.force_assign(cr, uid, picking_id)
            except Exception as myerror:
                okgj_api_log_error('Sys Error', str(one_id), str(myerror))
                okgj_api_log_error('Sales Order', str(one_id), 'Delivery Order ID, Fail to confirm delivery order!')
                continue
        cr.commit()
        if use_new_cursor:
            cr.close()
        return {}
    

class okgj_stock_picking_api(osv.osv):
    _inherit = "stock.picking"

    def write(self, cr, uid, ids, vals, context=None):
        ## 换货商品出入库
        super(okgj_stock_picking_api, self).write(cr, uid, ids, vals, context=context)
        uname = self.pool.get('res.users').read(cr, uid, uid, ['name'], context=context)['name'] or ''
        if isinstance(ids, (int, long)):
            ids = [ids]
        all_data = self.browse(cr, uid, ids, context=context)
        if vals.get('state') == 'done':
            return_order_table = "do_update_order_return_status"
            return_p_key = "back_id"
            for form in all_data:
                if form.okgj_type == 'okgj_sale_out':
                    return_p_value = form.sale_return_id and form.sale_return_id.name
                    if return_p_value:
                        return_p_value = return_p_value + '_' + uuid.uuid4().hex
                        return_arg = {
                            "order_sn":form.sale_return_id.sale_order_id and form.sale_return_id.sale_order_id.name,
                            "status": 20,
                            "update_time":int(round(time.time())),
                            "note":json.JSONEncoder().encode({'name':uname})}
                            ##str({'name':uname})}
                        redis_do(redis_pool, return_order_table, return_p_key, return_p_value, return_arg)
                elif form.okgj_type == 'okgj_sale_in':
                    return_p_value = form.sale_return_id and form.sale_return_id.name
                    if return_p_value:
                        return_p_value = return_p_value + '_' + uuid.uuid4().hex
                        return_arg = {
                            "order_sn":form.sale_return_id.sale_order_id and form.sale_return_id.sale_order_id.name,
                            "status": 70,
                            "update_time":int(round(time.time())),
                            "note":json.JSONEncoder().encode({'name':uname})}
                            ## str({'name':uname})}
                        redis_do(redis_pool, return_order_table, return_p_key, return_p_value, return_arg)
        return True                    


class okgj_stock_picking_out_api(osv.osv):
    _inherit = "stock.picking.out"

    def write(self, cr, uid, ids, vals, context=None):
        super(okgj_stock_picking_out_api, self).write(cr, uid, ids, vals, context=context)
        uname = self.pool.get('res.users').read(cr, uid, uid, ['name'], context=context)['name'] or ''
        if isinstance(ids, (int, long)):
            ids = [ids]
        all_data = self.browse(cr, uid, ids, context=context)
        if vals.get('verify_uid') and vals.get('verify_date'):
            order_table = "do_update_order_status"
            p_key = "order_no"
            for one_verify in all_data:
                p_value = one_verify.sale_id and one_verify.sale_id.name or False
                if p_value:
                    p_value = p_value + '_' + uuid.uuid4().hex
                    arg = {
                        "status": 20,
                        "update_time":int(round(time.time())),
                        "note":json.JSONEncoder().encode({'name':uname})}
                        ## str({'name':uname})}
                    redis_do(redis_pool, order_table, p_key, p_value, arg)
        return True
    
## 退换货打单
class okgj_sale_return_api(osv.osv):
    _inherit = "okgj.sale.return"

    def write(self, cr, uid, ids, vals, context=None):
        super(okgj_sale_return_api, self).write(cr, uid, ids, vals, context=context)
        if vals.get('has_print') is True:
            order_table = "do_update_order_return_status"
            p_key = "back_id"
            if isinstance(ids, (int, long)):
                ids = [ids]
            uname = self.pool.get('res.users').read(cr, uid, uid, ['name'], context=context)['name'] or ''
            for one_order in self.browse(cr, uid, ids, context=context):
                p_value = one_order.name + '_' + uuid.uuid4().hex                
                arg = {
                    "order_sn":one_order.sale_order_id.name,
                    "status": 10,
                    "update_time":int(round(time.time())),
                    "note":json.JSONEncoder().encode({'name':uname})}
                    ## str({'name':uname})}
                redis_do(redis_pool, order_table, p_key, p_value, arg)
        return True


class base_price_change_line_api(osv.osv):
    _inherit = 'okgj.base.price.change.line'

    def action_upload_line(self, cr, uid, ids, context=None):
        if context is None:
            context ={}
        if isinstance(ids, (int, long)):
            ids = [ids]
        order_table = "do_update_sale_base_price"
        p_key = "goods_no"
        uname = self.pool.get('res.users').read(cr, uid, uid, ['name'], context=context)['name'] or ''
        for one_line in self.browse(cr, uid, ids, context=context):
            p_value = one_line.product_id.default_code + '_' + uuid.uuid4().hex
            arg = {
                "warehouse": one_line.warehouse_id.okgj_warehouse_id,
                "count":one_line.product_qty,
                "price":float(one_line.product_price_unit),
                "update_time":int(round(time.time())),
                "note":json.JSONEncoder().encode({'name':uname})}
                ## str({'name':uname})}
            redis_do(redis_pool, order_table, p_key, p_value, arg)
        super(base_price_change_line_api, self).action_upload_line(cr, uid, ids, context=context)
        return True

