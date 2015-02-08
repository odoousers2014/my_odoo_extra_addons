# -*- coding: utf-8 -*-
##############################################################################
##<alangwansui@gmail.com>
##############################
import urllib2
import urllib
import md5
import json
import hashlib
import hmac
import base64
from openerp.osv import  osv, fields
from openerp import pooler
from openerp import SUPERUSER_ID
import time
import logging
#import top.api
#from openerp.tools.translate import _
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
_logger = logging.getLogger(__name__)

Platform_SO_State_Taobao = [
    ('TRADE_NO_CREATE_PAY', u'淘宝：没有创建支付宝交易'),
    ('WAIT_BUYER_PAY', u'淘宝：等待买家付款'),
    ('WAIT_SELLER_SEND_GOODS', u'淘宝：等待卖家发货,即:买家已付款'),
    ('WAIT_BUYER_CONFIRM_GOODS', u'淘宝：等待买家确认收货,即:卖家已发货'),
    ('TRADE_BUYER_SIGNED', u'淘宝：买家已签收,货到付款专用'),
    ('TRADE_FINISHED', u'淘宝：交易成功'),
    ('TRADE_CLOSED', u'淘宝：付款以后用户退款成功，交易自动关闭'),
    ('TRADE_CLOSED_BY_TAOBAO', u'淘宝：付款以前，卖家或买家主动关闭交易'),
    ('PAY_PENDING', u'淘宝：国际信用卡支付付款确认中'),
]
Platform_SO_State_YHD = [
    ('ORDER_WAIT_PAY', u'一号店：已下单货款未全收'),
    ('ORDER_PAYED', u'一号店：已下单货款已收'),
    ('ORDER_WAIT_SEND', u'一号店：等待发货'),
    ('ORDER_TRUNED_TO_DO', u'一号店：可以发货已送仓库'),
    ('ORDER_OUT_OF_WH', u'一号店：已出库货在途'),
    ('ORDER_RECEIVED', u'一号店：货物用户已收到'),
    ('ORDER_FINISH', u'一号店：订单完成'),
    ('ORDER_CANCEL', u'一号店：订单取消'),
]
Platform_SO_State_Suning = [
    ('10', u'苏宁：待发货'),
    ('20', u'苏宁：已发货'),
    ('21', u'苏宁：部分发货'),
    ('30', u'苏宁：交易成功'),
    ('40', u'苏宁：交易关闭'),
]
Platform_SO_State_Beibei = [
    ('1', u'贝贝网：等待商家发货'),
    ('2', u'贝贝网：等待用户收货'),
    ('3', u'贝贝网：订单完成'),
]
Platform_SO_State_Alibaba = [
    ('waitbuyerpay', u'阿里巴巴：等待买家付款'),
    ('waitsellersend', u'阿里巴巴：等待卖家发货'),
    ('waitbuyerreceive', u'阿里巴巴：等待买家收货'),
    ('success', u'阿里巴巴：交易成功'),
    ('cancel', u'阿里巴巴：交易取消，违约金等交割完毕'),
    ('waitselleract', u'阿里巴巴：等待卖家操作'),
    ('waitbuyerconfirmaction', u'阿里巴巴：等待买家确认操作'),
    ('waitsellerpush', u'阿里巴巴：等待卖家推进'),
]
ALL_Platform_SO_State = Platform_SO_State_Taobao + Platform_SO_State_YHD + Platform_SO_State_Suning + Platform_SO_State_Alibaba + Platform_SO_State_Beibei
Wait_Send_Status = ['WAIT_SELLER_SEND_GOODS', 'ORDER_PAYED', 'ORDER_WAIT_SEND', 'ORDER_TRUNED_TO_DO', 'waitsellersend', '10']
Platform_End_Status = ['TRADE_FINISHED', 'TRADE_CLOSED', 'TRADE_CLOSED_BY_TAOBAO', 'ORDER_FINISH', 'ORDER_CANCEL', '30', '40', 'success', 'cancel']

str_all_state = ','.join([i[0] for i in ALL_Platform_SO_State])

State_Filter = {
    'all': {
        'taobao': str_all_state,
        'tmall': str_all_state,
        'yhd': str_all_state,
        'alibaba': str_all_state,
        'suning': str_all_state,
        'beibei': str_all_state,
    },
    'payed': {
        'taobao': 'WAIT_SELLER_SEND_GOODS',
        'tmall': 'WAIT_SELLER_SEND_GOODS',
        'yhd': 'ORDER_PAYED,ORDER_TRUNED_TO_DO,ORDER_WAIT_SEND',
        'alibaba': 'waitsellersend',
        'suning': '10',
        'beibei': '2',
    },
}

Time_Diff = 8
Platform_List = [
    ('taobao', u"淘宝"),
    ('tmall', u'天猫'),
    ('yhd', u"一号店"),
    ('alibaba', u'阿里巴巴'),
    ('suning', u'苏宁'),
    ('beibei', u'贝贝网'),
]


def logger_popup(s, popup=False, title='Error:'):
    """
    @mode  'raise' or 'logger'
    """
    if popup:
        raise osv.except_osv(title, '%s' % s)
    else:
        _logger.info('%s %s' % (title, s))


def time_ago(hours=0, days=0):
    if hours:
        return (datetime.now() + timedelta(hours=Time_Diff) - timedelta(hours=hours)).strftime(DF)
    elif days:
        return (datetime.now() + timedelta(hours=Time_Diff) - timedelta(days=days)).strftime(DF)
    else:
        return (datetime.now() + timedelta(hours=Time_Diff)).strftime(DF)


def strp_time(string):
    return string and (datetime.strptime(string, DF) - timedelta(hours=Time_Diff)).strftime(DF)


def del_new_line_and_space(s):
    return ''.join(s.split())

TAOBAO_FILDS = del_new_line_and_space("""
    has_post_fee,seller_nick,buyer_nick,title,type,created,sid,tid,seller_rate,buyer_rate,status,payment,discount_fee,adjust_fee,
    post_fee,total_fee,pay_time,end_time,modified,consign_time,buyer_obtain_point_fee,point_fee,real_point_fee,
    received_payment,commission_fee,pic_path,num_iid,num_iid,num,price,cod_fee,cod_status,shipping_type,
    receiver_name,receiver_state,receiver_city,receiver_district,receiver_address,receiver_zip,receiver_mobile,
    receiver_phone,orders.title,orders.pic_path,orders.price,orders.num,orders.iid,orders.num_iid,orders.sku_id,
    orders.refund_status,orders.status,orders.oid,orders.total_fee,orders.payment,orders.discount_fee,orders.adjust_fee,
    orders.sku_properties_name,orders.item_meal_name,orders.buyer_rate,orders.seller_rate,orders.outer_iid,
    orders.outer_sku_id,orders.refund_id,orders.seller_type,buyer_message,buyer_alipay_no,seller_alipay_no,seller_memo
""")
TAOBAO_TRADE_TYPE = del_new_line_and_space("""
    fixed,auction,guarantee_trade,step,independent_simple_trade,independent_shop_trade,auto_delivery,ec,
    cod,game_equipment,shopex_trade,netcn_trade,external_trade,instant_trade, b2c_cod,hotel_trade,
    super_market_trade,super_market_cod_trade,taohua,waimai,nopaid,step eticket,tmall_i18n,nopaid,
    insurance_plus,inance,pre_auth_type
""")


class sync_api(osv.osv):
    """
    """
    _State_Dict = {}
    _City_Dict = {}
    _Login_Dict = {}
    _Partner_Dict = {}
    _Product_Dict = {}
    _Exist_Dict = False
    _State_Filter = State_Filter
    #data struct {member_id: source_sku, member_id:source_sku  }
    _Alibaba_Poduct_SKU = {}

    _API_URL = {
        'taobao': 'http://gw.api.taobao.com/router/rest',
        'yhd': 'http://openapi.yhd.com/app/api/rest/router',
        'alibaba': 'http://gw.open.1688.com:80/openapi',
        'suning': 'http://open.suning.com/api/http/sopRequest',
        'beibei': 'http://d.beibei.com/outer_api/out_gateway/route.html?',
    }
    _API_ARG = {
        'taobao': {'format': 'json', 'v': '2.0', 'sign_method': 'md5'},
        'yhd': {'format': 'json', 'ver': '1.0'},
        'suning': {'Format': 'json', 'VersionNo': 'v1.2'},
        'beibei': {'Format': 'json', 'VersionNo': 'v1.2'},
    }

    def _get_default_currency(self, cr, uid, context=None):
        mod_obj = self.pool.get('ir.model.data')
        return mod_obj.get_object_reference(cr, uid, 'base', 'CNY')[1]

    def _get_default_partner(self, cr, uid, context=None):
        mod_obj = self.pool.get('ir.model.data')
        return mod_obj.get_object_reference(cr, uid, 'yks', 'yks_res_partner_direct_sale')[1]

    def _get_default_shop(self, cr, uid, context=None):
        return 1

    _name = 'sync.api'
    _columns = {
        'name': fields.char(u'名称(账户)', size=20, required=True),
        'nickname': fields.char(u'店铺名称', size=40, ),
        'password': fields.char(u'密码', size=20),
        'app_key': fields.char(u'APP-Key', size=40),
        'key_secret': fields.char(u'Key-Secret', size=40),
        'session_key': fields.char(u'Session-Key', size=70),
        'refresh_token': fields.char(u'Refresh Token', size=50),
        'member_id': fields.char(u'Member ID', size=50),
        'type': fields.selection(Platform_List, u'平台类型', required=True),
        'active': fields.boolean(u'可用'),
        'connection_error': fields.text(u'连接错误信息',),
        'user_id': fields.many2one('res.users', u'业务员', required=True),
        'section_id': fields.many2one('crm.case.section', u'销售团队'),
        'currency_id': fields.many2one('res.currency', 'Currency', required=True),
        'offset_time': fields.integer(u'同步N小时前的订单', ),
        'state': fields.selection([('draft', 'Draft'), ('done', 'Done')], 'Status'),
        'partner_id': fields.many2one('res.partner', u'默认客户', required=True),
        'is_multi_user': fields.boolean('多用户帐号'),
        #帐号送货信息
        'carrier_id': fields.many2one('delivery.carrier', u'快递方式'),
        'deliver_name': fields.char(u'发货人', size=20),
        'deliver_city_id': fields.many2one('res.city', u'发货城市'),
        'deliver_company_name': fields.char(u'发货单位', size=50),
        'deliver_tel': fields.char(u'发货电话', size=20),
        'deliver_address': fields.char(u'发货地址', size=80),
        'address_format': fields.char('Address  Format', size=50, required=True),
        'state_filter': fields.selection([('payed', 'Payed'), ('all', 'ALL')], u'状态过滤'),
        'shop_id': fields.many2one('sale.shop', u'商店'),
        'product_ids': fields.many2many('product.product', 'onsale_product', 'api_ids', 'product_ids', string=u'在售商品'),
    }

    _defaults = {
          'active': True,
          'user_id': lambda self, cr, uid, c: uid,
          'currency_id': lambda self, cr, uid, c: self._get_default_currency(cr, uid, c),
          'offset_time': 48,
          'partner_id': lambda self, cr, uid, c: self._get_default_partner(cr, uid, c),
          'address_format': '%(state)s %(city)s %(district)s %(address)s',
          'state_filter': lambda *a: 'payed',
          'shop_id': lambda self, cr, uid, c: self._get_default_shop(cr, uid, c),
    }
    _sql_constraints = [('name_uniq', 'unique (name)', 'The Name of the SYNC API must be unique !'),
        ('session_key', 'unique (session_key)', 'The Name of the Session-Key must be unique !'),
    ]

    def report_dict_info(self, cr, uid, ids, context=None):
        _logger.info(" _Product_Dict %s" % self._Product_Dict)
        _logger.info(" _Login_Dict %s" % self._Login_Dict)
        _logger.info(" _Partner_Dict %s" % self._Partner_Dict)
        return True

    def get_state_id_by_name(self, state):
        if not state:
            return None

        suf = u'省'
        suf1 = u'市'
        suf2 = u'自治区'
        state_id = (self._State_Dict.get(state) or
                    self._State_Dict.get(state + suf) or
                    self._State_Dict.get(state + suf1)
                    or self._State_Dict.get(state + suf2))
        if not state_id:
            _logger.info('get_state_id_by_name Failure %s' % state)
        return state_id

    def get_city_id_by_name(self, city):
        if not city:
            return None

        suf = u'市'
        city_id = self._City_Dict.get(city) or self._City_Dict.get(city + suf)
        if not city_id:
            _logger.info('get_city_id_by_name Failure %s' % city)
        return city_id

    def name_get(self, cr, uid, ids, context=None):
        if not len(ids):
            return []
        type_dict = dict(Platform_List)
        reads = self.read(cr, uid, ids, ['name', 'type'], context=context)
        res = []
        for record in reads:
            new_name = type_dict.get(record['type']) + ':' + record['name']
            res.append((record['id'], new_name))
        return res

    @staticmethod
    def check_get_all_dict(cr, context=None):
        if not sync_api._Exist_Dict:
            sync_api.get_all_dict(cr)

    @staticmethod
    def get_all_dict(cr, uid=False, ids=None, context=None):
        #uid = SUPERUSER_ID
        #mod_obj = self.pool.get('ir.model.data')

        sync_api._State_Dict = {}
        sync_api._City_Dict = {}
        sync_api._Login_Dict = {}
        sync_api._Partner_Dict = {}
        sync_api._Product_Dict = {}

        cr.execute('select id, name from res_country_state')
        for i in cr.fetchall():
            sync_api._State_Dict[i[1]] = i[0]

        cr.execute('select id, name from res_city')
        for i in cr.fetchall():
            sync_api._City_Dict[i[1]] = i[0]

        cr.execute('select id, login from res_users')
        for i in cr.fetchall():
            sync_api._Login_Dict[i[1]] = i[0]

        cr.execute("""select  name, id, monkey_id from res_partner where customer = 't' and active='t'""")
        for i in cr.fetchall():
            sync_api._Partner_Dict[i[0]] = {'id': i[1], 'monkey_id': i[2]}

        cr.execute("""
            select
                default_code, id, name_template
            from
                product_product
            where
                active='t' and default_code is not null
        """)
        for i in cr.fetchall():
            sync_api._Product_Dict[i[0]] = {'id': i[1], 'name': i[2]}

        sync_api._Exist_Dict = True
        return sync_api._Exist_Dict

    @staticmethod
    def Make_Sign(arg, secret):
        s = ''
        keys = arg.keys()
        keys.sort()
        for k in keys:
            s += k + arg[k]
        s = secret + s + secret
        sign = md5.md5(s).hexdigest().upper()
        return sign

    @staticmethod
    def Make_Sign_Yhd(arg, secret):
        s = ''
        keys = arg.keys()
        keys.sort()
        for k in keys:
            s += k + arg[k]
        s = secret + s + secret
        sign = md5.md5(s).hexdigest()
        return sign

    @staticmethod
    def Make_Sign_Alibaba(urlpath, arg, key_secret):
        s = ''
        keys = arg.keys()
        keys.sort()
        for k in keys:
            s += k + arg[k]
        s = urlpath + s
        s = s.encode('utf8')
        key_secret = key_secret.encode('utf8')
        sign = hmac.new(key_secret, s, hashlib.sha1).hexdigest().upper()
        return sign

    @staticmethod
    def Make_Sign_Suning(app_key, key_secret, method, date, version, body):
        basestr = base64.b64encode(body).decode('utf_8')
        tomd5 = '%s%s%s%s%s%s' % tuple([key_secret, method, date, app_key, version, basestr])
        hashlib1 = hashlib.md5(tomd5.encode('utf_8'))
        sign = hashlib1.hexdigest()
        return sign

    @staticmethod
    def Make_Sign_Beibei(arg, key_secret):
        ''''''
        keys = arg.keys()
        keys.sort()
        url = ''
        sign_add = key_secret
        for key in keys:
            sign_add += '%s%s' % (key, arg[key])
            url += '%s=%s&' % (key, arg[key])
        sign_add += key_secret
        sign = hashlib.md5(sign_add)
        sign = sign.hexdigest().upper()
        sign = '%ssign=%s' % (url, sign)
        return sign

    @staticmethod
    def Beibei_Request(arg, key_secret):
        sign = sync_api.Make_Sign_Beibei(arg, key_secret)
        url = '%s%s' % (sync_api._API_URL['beibei'], sign)
        request = urllib2.urlopen(url)
        res = request.read()
        return res

    @staticmethod
    def Suning_Request(body, header, key_secret):
        app_key = header.get('AppKey')
        method = header.get('AppMethod')
        version = header.get('VersionNo')
        date = header.get('AppRequestTime')
        sign = sync_api.Make_Sign_Suning(app_key, key_secret, method, date, version, body)
        header.update({'signInfo': sign})
        req = urllib2.Request(sync_api._API_URL['suning'], body, header)
        res = None
        try:
            request = urllib2.urlopen(req)
            res = request.read()
        except Exception, e:
            res = e
        return res

    @staticmethod
    def Top_Request(arg, key_secret):
        sign = sync_api.Make_Sign(arg, key_secret)
        arg.update({'sign': sign})
        postdata = urllib.urlencode(arg)
        req = urllib2.Request(sync_api._API_URL['taobao'], postdata)
        res = None
        try:
            request = urllib2.urlopen(req)
            res = request.read()
        except Exception, e:
            res = e
        return res

    @staticmethod
    def Yhd_Request(arg, key_secret):
        sign = sync_api.Make_Sign_Yhd(arg, key_secret)
        arg.update({'sign': sign})
        postdata = urllib.urlencode(arg)
        req = urllib2.Request(sync_api._API_URL['yhd'], postdata)
        res = None
        try:
            request = urllib2.urlopen(req)
            res = request.read()
        except Exception, e:
            res = e
        return res

    @staticmethod
    def Alibaba_Request(urlpath, arg, key_secret):
        sign = sync_api.Make_Sign_Alibaba(urlpath, arg, key_secret)
        arg.update({'_aop_signature': sign})
        full_url = sync_api._API_URL['alibaba'] + '/' + urlpath
        req = urllib2.Request(full_url, urllib.urlencode(arg))
        try:
            request = urllib2.urlopen(req)
            res = request.read()
            request.close()
        except Exception, e:
            res = e
        return res

    def scheduler_sync_api(self, cr, uid, use_new_cursor=True, context=None):
        _logger.info("scheduler_sync_api start")
        
        ids = self.search(cr, uid, [('active', '=', True)])
        
        start_time = time.time()
        
        if context is None:
            context = {}
        try:
            if use_new_cursor:
                cr = pooler.get_db(cr.dbname).cursor()
            self.get_order(cr, uid, ids, context=context)
            if use_new_cursor:
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
                
        end_time = time.time()
        
        cost_second = end_time - start_time
        
        _logger.info("scheduler_sync_api end")
        _logger.info("sync_api cost time %s second, from %s to %s" % (cost_second, start_time, end_time))

        return True

    def sync_this_api(self, cr, uid, ids, use_new_cursor=True, context=None):
        #user super uid avoid access rule error
        uid = SUPERUSER_ID
        if context is None:
            context = {}
        try:
            if use_new_cursor:
                cr = pooler.get_db(cr.dbname).cursor()
            self.get_order(cr, uid, ids, context=context)
            if use_new_cursor:
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
        return True

    def _check_create_so(self, cr, uid, data, context=None,):
        difference = 0.01
        payment = data.get('payment')
        total = sum(float(line[2]['product_uom_qty']) * float(line[2]['price_unit']) for line in data['order_line'])
        if abs(payment - total) > difference:
            _logger.error("_check_create_so, Price difference, platform_so_id:%s" % data['platform_so_id'])
        so_id = self.pool.get('sale.order').create(cr, uid, data)
        _logger.info("_check_create_so OK %s %s" % (data['platform_so_id'], so_id))
        return so_id

    def get_order(self, cr, uid, ids, context=None):
        _logger.info("Start get_order")
        if context is None:
            context = {}

        mod_obj = self.pool.get('ir.model.data')
        partner_obj = self.pool.get('res.partner')
        #parter for dreict sale
        partner_id = mod_obj.get_object_reference(cr, uid, 'yks', 'yks_res_partner_direct_sale')[1]
        default_ds_partner = partner_obj.browse(cr, uid, partner_id)
        context.update({'default_ds_partner': default_ds_partner})
        ##get all dict
        self.check_get_all_dict(cr, context=context)
        #if not sync_api._Exist_Dict:
            #self.get_all_dict(cr, context=context)

        ok_ids = self.get_connection_ok_api(cr, uid, ids, context=context)
        # get order
        records = self.browse(cr, uid, ok_ids, context=context)
        for record in records:
            _logger.info("%s %s want to get_order" % (record.type, record.name))

            if record.type in ['taobao', 'tmall']:
                self.get_order_taobao(cr, uid, record, context=context)
            elif record.type == 'yhd':
                self.get_order_yhd(cr, uid, record, context=context)
            elif record.type == 'alibaba':
                self.get_order_alibaba(cr, uid, record, context=context)
            elif record.type == 'suning':
                self.get_order_suning(cr, uid, record, context=context)
            elif record.type == 'beibei':
                self.get_order_beibei(cr, uid, record, context=context)

        _logger.info("End get_order")
        return True

    def get_order_alibaba(self, cr, uid, record, context=None):
        _logger.info("get_order_alibaba: start")

        alibaba_tids_info = self._alibaba_trades_sold_get(cr, uid, record, context=context)
        if not alibaba_tids_info:
            _logger.info("get_order_alibaba: not alibaba_tids_info")
            return True
        platform_trades = [str(i['id']) for i in alibaba_tids_info]
        exist_trades = self.get_exist_platform_trade(cr, uid, platform_trades)
        todo_tids_info = filter(lambda i: str(i['id'])  not in exist_trades, alibaba_tids_info)
        so_datas = self._alibaba_prepare_data(cr, uid, todo_tids_info, record, context=context)
        for i in so_datas:
            if i['flag_create']:
                self._check_create_so(cr, uid, i['data'], context=context)

        self._alibaba_refresh_access_token(cr, uid, record, context=context)
        _logger.info("get_order_alibaba: end")
        return True

    def get_exist_platform_trade(self, cr, uid, platform_trades, context=None):
        _logger.info("filter_exist_platform_trade Start")

        so_pool = self.pool.get('sale.order')
        exist_ids = so_pool.search(cr, uid, [('platform_so_id', 'in', [str(i) for i in platform_trades])])
        read_info = exist_ids and so_pool.read(cr, uid, exist_ids, ['platform_so_id'], context=context) or False
        res = read_info and  [i['platform_so_id']  for i in read_info] or []

        _logger.info("filter_exist_platform_trade End")
        return res

    def _alibaba_prepare_data(self, cr, uid, alibaba_tids_info, record, context=None):
        _logger.info("_alibaba_prepare_data: start")

        res = []
        ## multi login source-sku get
        member_id = record.member_id
        if not sync_api._Alibaba_Poduct_SKU.get(member_id):
            sync_api._Alibaba_Poduct_SKU[member_id] = self._alibaba_product_sku_get(cr, uid, record, context=context)
        source_sku = sync_api._Alibaba_Poduct_SKU.get(member_id)
        if not source_sku:
            _logger.info("_alibaba_prepare_data, not get source sku: %s" % record.name)
            return res

        partner_obj = self.pool.get('res.partner')
        #team_code = record.section_id and record.section_id.code or ''
        #default_partner = context.get('default_ds_partner')
        default_partner = record.partner_id

        memberIds = ','.join([x['buyerMemberId'] for x in alibaba_tids_info])
        membersinfo = self._alibaba_convertLoginIdsByMemberIds(cr, uid, record, memberIds, context=context)

        for info in alibaba_tids_info:
            flag_create = True
            order_line = []
            for line in info['orderEntries']:
                if  line['entryStatus'] == 'cancel':
                    continue
                plateform_sku = source_sku.get(line.get('sourceId'))
                sku_data = sync_api._Product_Dict.get(plateform_sku) or sync_api._Product_Dict.get('Error_Sku')
                order_line.append((0, 0, {
                    'name': '[' + str(plateform_sku) + ']' + sku_data['name'],
                    'product_id': sku_data['id'],
                    'product_uom_qty': line['quantity'],
                    'price_unit': line['price'] / 100,
                    'platform_sol_id': str(line['id']),
                }))
            if info['carriage']:
                pdt_post = sync_api._Product_Dict.get('PostageFee')
                order_line.append((0, 0, {'name': pdt_post['name'], 'product_id': pdt_post['id'], 'product_uom_qty': 1, 'price_unit': info['carriage'] / 100}))
            if info['discount']:
                pdt_discount = sync_api._Product_Dict.get('DiscountFee')
                order_line.append((0, 0, {'name': pdt_discount['name'], 'product_id': pdt_discount['id'], 'product_uom_qty': 1, 'price_unit': info['discount'] / 100}))

            gt = info.get('gmtCreate')
            pt = info.get('gmtPayment')
            #if time-format is 20141026120419000+0800
            if r'+' in gt:
                gt = gt[0:4] + '-' + gt[4:6] + '-' + gt[6:8] + ' ' + gt[8:10] + ':' + gt[10:12] + ':' + gt[12:14]
            if r'+'  in pt:
                pt = pt[0:4] + '-' + pt[4:6] + '-' + pt[6:8] + ' ' + pt[8:10] + ':' + pt[10:12] + ':' + pt[12:14]

            platform_create_time = strp_time(gt)
            platform_pay_time = pt and strp_time(pt) or False
            state, city = info['toArea'].split(' ')[:2]
            # get user_id
            memos = info.get('memos', '')
            remark = memos and memos[0].get('remark', '')
            login = '#' in remark and remark.split('#')[1] or 'None'
            _logger.info("_alibaba_prepare_data get login: %s %s" % (str(info['id']), login))

            partner = default_partner
            #get user_id and customer
            if record.is_multi_user:
                user_id = sync_api._Login_Dict.get(login)
                partner_name = membersinfo.get(info['buyerMemberId'], '')
                partner_info = self._Partner_Dict.get(partner_name, '')
                if partner_info and partner_info['monkey_id']:
                    partner = partner_obj.browse(cr, uid, partner_info['id'], context=context)
            else:
                user_id = record.user_id.id
     
            data = {
                'partner_id': partner.id,
                'pricelist_id': partner.property_product_pricelist.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
                'api_id': record.id,
                'carrier_id': record.carrier_id and record.carrier_id.id,
                'receive_user': info['toFullName'],
                'receiver_city_id': self.get_city_id_by_name(city),
                'receiver_state_id': self.get_state_id_by_name(state),
                'receiver_district': False,
                'receive_address': info.get('toArea'),
                'receiver_zip': info.get('toPost'),
                'receive_phone': info.get('toMobile'),
                'order_line': order_line,
                'platform_so_id': str(info['id']),
                'platform_so_state': info['status'],
                'payment': float(info['sumPayment']) / 100,
                'platform_user_id': membersinfo.get(info['buyerMemberId'], info['buyerMemberId']),
                'platform_create_time': platform_create_time,
                'platform_pay_time': platform_pay_time,
                'platform_seller_id': record.name,
                'seller_pay_no': info['sellerAlipayId'],
                'note': info.get('buyerFeedback', ''),
                'user_id': user_id,
                'section_id': record.section_id.id,
                'create_type': 'auto',
                'shop_id': record.shop_id.id,
                #'date_order': platform_create_time[0:10]
            }
            res.append({'flag_create': flag_create, 'data': data})

        _logger.info("_alibaba_prepare_data: end")
        return res

    ##TODO
    def alibaba_refresh_token(self, cr, uid, ids, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        return self._alibaba_refresh_access_token(cr, uid, record, context=context)

    def _alibaba_refresh_access_token(self, cr, uid, record, context=None):
        _logger.info("_alibaba_refresh_access_token: start")

        url = 'https://gw.open.1688.com/openapi/param2/1/system.oauth2'
        arg = {
             'grant_type': 'refresh_token',
             'client_id': record.app_key,
             'client_secret': record.key_secret,
             'refresh_token': record.refresh_token,
        }
        post_data = urllib.urlencode(arg)
        post_url = '/'.join([url, 'getToken', record.app_key])
        req = urllib2.Request(post_url, post_data)

        try:
            request = urllib2.urlopen(req)
            res = request.read()
            res = json.loads(res)
            self.write(cr, uid, record.id, {'session_key': res.get('access_token', '')})
        except Exception, e:
            _logger.error("_alibaba_refresh_access_token error %s:" % e)

        _logger.info("_alibaba_refresh_access_token: end")
        return True

    def _alibaba_convertLoginIdsByMemberIds(self, cr, uid, record, memberIds, context=None):
        _logger.info("_alibaba_convertLoginIdsByMemberIds: start")
        arg = {
             'memberIds': memberIds,
             'access_token': record.session_key,
        }
        urlpath = '/'.join(['param2/1/cn.alibaba.open', 'convertLoginIdsByMemberIds', record.app_key])
        res = self.Alibaba_Request(urlpath, arg, record.key_secret)
        if  isinstance(res, Exception):
            _logger.error("_alibaba_convertLoginIdsByMemberIds Error: %s" % res)
            res = {}
        else:
            res = json.loads(res)
            res = res['loginIdMap']
        _logger.info("_alibaba_convertLoginIdsByMemberIds: end")
        return res

    def _alibaba_product_sku_get(self, cr, uid, record, context=None):
        _logger.info("_alibaba_product_sku_get: start")
        max_pageSize = 50

        def update_source_sku(source_sku, res):
            for a in res['result']['toReturn']:
                for f in a['productFeatureList'][::-1]:
                    if f['name'].upper() == 'SKU':
                        source_sku[a['offerId']] = f['value']
            return True
        arg = {
            'type': 'SALE',
            'returnFields': 'offerId,productFeatureList',
            'access_token': record.session_key,
            'pageSize': str(max_pageSize),
        }
        urlpath = '/'.join(['param2/1/cn.alibaba.open', 'offer.getAllOfferList', record.app_key])
        res = self.Alibaba_Request(urlpath, arg, record.key_secret)

        if isinstance(res, (Exception, urllib2.HTTPError)):
            _logger.error("_alibaba_product_sku_get Error: %s" % res)
            return False

        res = json.loads(res)
        #{alibaba.product_id: openerp.sku  }
        source_sku = {}
        update_source_sku(source_sku, res)

        #when total record > 50,
        total = int(res['result']['total']) - max_pageSize

        page = 2
        while total > 0:
            arg.update({'page': str(page)})
            if '_aop_signature' in arg:
                del arg['_aop_signature']
            more_res = self.Alibaba_Request(urlpath, arg, record.key_secret)
            if isinstance(res, Exception):
                _logger.error("_alibaba_product_sku_get Error page:%s:%s" % (page, res))

            more_res = json.loads(more_res)
            update_source_sku(source_sku, more_res)
            page += 1
            total -= max_pageSize

        _logger.info("_alibaba_product_sku_get: end")
        return source_sku

    def _alibaba_trades_sold_get(self, cr, uid, record, context=None):
        """
        """
        _logger.info("_alibaba_trades_sold_get: start")

        tids_info = []
        pageSize = 20
        pageNO = 1
        createStartTime = time_ago(record.offset_time)

        arg = {
             'sellerMemberId': record.member_id,
             'access_token': record.session_key,
             'orderStatus': 'waitsellersend',
             'pageSize': str(pageSize),
             'pageNO': str(pageNO),
             'createStartTime': createStartTime,
        }
        urlpath = '/'.join(['param2/1/cn.alibaba.open', 'trade.order.orderList.get', record.app_key])
        res = self.Alibaba_Request(urlpath, arg, record.key_secret)
        if isinstance(res, Exception) or not res:
            _logger.error("_alibaba_trades_sold_get error: %s" % res)
            res = False
        else:
            res = json.loads(res)
            if res.get('error_code'):
                _logger.error("_alibaba_trades_sold_get error2: %s" % res)
                res = False
            else:
                tids_info += res['result']['toReturn']
                #return tids_info
                rest_count = int(res['result']['total']) - pageSize
                while rest_count > 0:
                    pageNO += 1
                    rest_count -= pageSize
                    new_arg = {
                     'sellerMemberId': record.member_id,
                     'access_token': record.session_key,
                     'orderStatus': 'waitsellersend',
                     'pageSize': str(pageSize),
                     'pageNO': str(pageNO),
                     'createStartTime': createStartTime,
                    }
                    new_res = self.Alibaba_Request(urlpath, new_arg, record.key_secret)
                    new_res = json.loads(new_res)
                    tids_info += new_res['result']['toReturn']

        _logger.info("_alibaba_trades_sold_get: end")
        return tids_info

    def _get_taoba_tids(self, cr, uid, record, context=None):
        _logger.info("_get_taoba_tids: start")
        tids = False
        page_size = 100
        page_no = 1
        filter_status = self._State_Filter[record.state_filter][record.type]
        arg_fixed = {
            'timestamp': time_ago(),
            'app_key': record.app_key,
            'session': record.session_key,
            'method': 'taobao.trades.sold.get',
            'fields': 'tid',
            'type': TAOBAO_TRADE_TYPE,
            'start_created': time_ago(record.offset_time),
            'status': filter_status,
        }

        arg = self._API_ARG['taobao'].copy()
        arg.update(arg_fixed)
        arg.update({'page_no': str(page_no), 'page_size': str(page_size)})
        res = self.Top_Request(arg, record.key_secret)
        try:
            res = json.loads(res)
            if res['trades_sold_get_response']['total_results'] == 0:
                _logger.info("_get_taoba_tids: total_results ==0")
                return False

            tids_info = res['trades_sold_get_response']['trades']['trade']
            remain_count = int(res['trades_sold_get_response']['total_results']) - page_size
            while remain_count > 0:
                page_no += 1
                remain_count -= page_size
                new_arg = self._API_ARG['taobao'].copy()
                new_arg.update(arg_fixed)
                new_arg.update({'page_no': str(page_no), 'page_size': str(page_size)})
                new_res = self.Top_Request(new_arg, record.key_secret)
                new_res = json.loads(new_res)
                tids_info += new_res['trades_sold_get_response']['trades']['trade']
            tids = tids_info and [i['tid'] for i in tids_info] or False

        except Exception, e:
            _logger.info("_get_taoba_tids Error %s %s" % (res, e))
            return False

        _logger.info("_get_taoba_tids: end")
        return tids

    def _get_tabao_tid_fullinfo(self, cr, uid, record, tids, context=None, taobaofields=TAOBAO_FILDS):
        """
        @tids [tid1,tid2,tid2]
        """
        _logger.info("_get_tabao_tid_fullinfo: start")
        tids_info = []

        for tid in tids:
            info = False
            arg = self._API_ARG['taobao'].copy()
            arg.update({
                'method': 'taobao.trade.fullinfo.get',
                'session': record.session_key,
                'app_key': record.app_key,
                'timestamp': time.strftime(DF),
                'tid': str(tid),
                'fields': taobaofields,
            })
            res = self.Top_Request(arg, record.key_secret)
            if isinstance(res, Exception):
                _logger.info("_get_tabao_tid_fullinfo: Exception %s" % res)
            else:
                res = json.loads(res)
                if res.get('error_response'):
                    _logger.info("_get_tabao_tid_fullinfo: error_response %s %s %s" % (record.name, arg, res))
                else:
                    info = res['trade_fullinfo_get_response']['trade']

            tids_info.append(info)

        _logger.info("_get_tabao_tid_fullinfo: end")
        return tids_info

    def get_order_taobao(self, cr, uid, record, context=None):
        """
        taoba batch get can not get the seller_memo.
        """
        _logger.info("get_order_taobao: start")

        tids = self._get_taoba_tids(cr, uid, record, context=context)
        todo_tids = tids and self._taobao_filter_exist_trade(cr, uid, tids, context=context)
        todo_tids_info = todo_tids and self._get_tabao_tid_fullinfo(cr, uid, record, todo_tids, context=context) or []
        for info in todo_tids_info:
            data = self._taobao_prepare_data(cr, uid, info, record, context=context,)
            if data:
                self._check_create_so(cr, uid, data, context=context)

        _logger.info("get_order_taobao: end")
        return True

    def _yhd_trades_sold_get(self, cr, uid, record,):
        arg = sync_api._API_ARG['yhd'].copy()

        arg.update({
            'appKey': record.app_key,
            'sessionKey': record.session_key,
            'timestamp': time_ago(0),
            'method': 'yhd.orders.get',
            'orderStatusList': 'ORDER_WAIT_SEND,ORDER_PAYED',
            'startTime': time_ago(record.offset_time),
            'endTime': time_ago(0),
        })

        res = sync_api.Yhd_Request(arg, record.key_secret)
        if  isinstance(res, Exception) or not res:
            _logger.error("_yhd_trades_sold_get error: %s" % res)
            res = False
        else:
            res = json.loads(res)
            if res['response']['errorCount'] == 0:
                res = res['response']
            else:
                _logger.error("_yhd_trades_sold_get error2: %s" % res)
                res = False
        return res

    def get_order_yhd(self, cr, uid, record, context=None):
        _logger.info("get_order_yhd: Start")
        yhd_tids_info = self._yhd_trades_sold_get(cr, uid, record,)
        if yhd_tids_info:
            yhd_tids = [i['orderCode'] for i in  yhd_tids_info['orderList']['order']]
            todo_tids = yhd_tids and self._yhd_filter_exist_trade(cr, uid, yhd_tids, context=None) or []
            if  todo_tids:
                orderCodeList = ','.join(todo_tids)
                tids_detail = self._yhd_orders_detail_get(cr, uid, record, orderCodeList, context=context)
                so_datas = self._yhd_prepare_data(cr, uid, tids_detail, record, context=context)
                for i in so_datas:
                    if i['flag_create']:
                        self._check_create_so(cr, uid, i['data'], context=context)
        else:
            _logger.info("get_order_yhd:not get yhd_tids_info")

        _logger.info("get_order_yhd: end")
        return True

    def _yhd_prepare_data(self, cr, uid, tids_detail, record, context=None):
        _logger.info("_yhd_prepare_data: Start")

        #partner = context.get('default_ds_partner')
        partner = record.partner_id

        res = []
        for info  in tids_detail['orderInfoList']['orderInfo']:
            orderDetail = info['orderDetail']
            orderItemList = info['orderItemList']

            order_line = []
            flag_create = True
            for item in orderItemList['orderItem']:
                plateform_sku = item.get('outerId')
                sku_data = sync_api._Product_Dict.get(plateform_sku) or sync_api._Product_Dict.get('Error_Sku')
                order_line.append((0, 0, {
                    'name': '[' + str(plateform_sku) + ']' + sku_data['name'],
                    'product_id': sku_data['id'],
                    'product_uom_qty': item['orderItemNum'],
                    'price_unit': item['orderItemPrice'],
                    'platform_sol_id': str(item['id']),
                }))

            #realAmount:实收款==产品金额-促销活动立减金额 -商家抵用券金额+运费
            #orderAmount:订购金额=商品金额+运费-优惠，即为顾客应付款（抵用券属于支付手段）
            #运费
            orderDeliveryFee = orderDetail['orderDeliveryFee']
            #参加促销活动立减金额
            orderPromotionDiscount = orderDetail['orderPromotionDiscount']
            #商家抵用券支付金额
            orderCouponDiscount = orderDetail['orderCouponDiscount']
            #1mall平台抵用券支付金额
            #orderPlatformDiscount =  orderDetail['orderPlatformDiscount']

            if orderDeliveryFee:
                pdt_post = sync_api._Product_Dict.get('PostageFee')
                order_line.append((0, 0, {'name': pdt_post['name'], 'product_id': pdt_post['id'], 'product_uom_qty': 1, 'price_unit': orderDeliveryFee}))
            if orderPromotionDiscount:
                pdt_discount = sync_api._Product_Dict.get('DiscountFee')
                order_line.append((0, 0, {'name': pdt_discount['name'], 'product_id': pdt_discount['id'], 'product_uom_qty': 1, 'price_unit': 0 - orderPromotionDiscount}))
            if orderCouponDiscount:
                pdt_coupon = sync_api._Product_Dict.get('CouponFee')
                order_line.append((0, 0, {'name': pdt_coupon['name'], 'product_id': pdt_coupon['id'], 'product_uom_qty': 1, 'price_unit': 0 - orderCouponDiscount}))

            # order_line.append((0,0,))   add  post fee
            # order_line.append   add  free_fee
            platform_create_time = strp_time(orderDetail['orderCreateTime'])

            data = {
                'partner_id': partner.id,
                'pricelist_id': partner.property_product_pricelist.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
                'api_id': record.id,
                'carrier_id': record.carrier_id and record.carrier_id.id,
                'receive_user': orderDetail.get('goodReceiverName'),
                'receiver_city_id': self.get_city_id_by_name(orderDetail.get('goodReceiverCity', '')),
                'receiver_state_id': self.get_state_id_by_name(orderDetail.get('goodReceiverProvince', '')),
                'receiver_district': orderDetail.get('goodReceiverCounty'),
                'receive_address': orderDetail.get('goodReceiverAddress'),
                'receive_phone': orderDetail.get('goodReceiverMoblie',),
                'receiver_zip': orderDetail.get('goodReceiverPostCode'),
                'order_line': order_line,
                'platform_so_id': orderDetail['orderCode'],
                'platform_so_state': orderDetail['orderStatus'],
                'payment': float(orderDetail['realAmount']),
                'platform_user_id': str(orderDetail['endUserId']),
                'platform_create_time': platform_create_time,
                'platform_pay_time': strp_time(orderDetail.get('depositPaidTime')),
                'platform_seller_id': record.name,
                'create_type': 'auto',
                'user_id': record.user_id.id,
                'section_id': record.section_id.id,
                'shop_id': record.shop_id.id,
                #'date_order': platform_create_time[0:10]
                #===============================================================
            }
            res.append({'flag_create': flag_create, 'data': data})

        _logger.info("_yhd_prepare_data: End")
        return res

    def _yhd_orders_detail_get(self, cr, uid, record, orderCodeList, context=None):
        arg = sync_api._API_ARG['yhd'].copy()
        arg.update({
            'appKey': record.app_key,
            'sessionKey': record.session_key,
            'timestamp': time_ago(0),
            'method': 'yhd.orders.detail.get',
            'orderCodeList': orderCodeList,
        })
        res = sync_api.Yhd_Request(arg, record.key_secret)
        if  isinstance(res, Exception) or not res:
            _logger.error("_yhd_orders_detail_get error: %s" % res)
            res = False
        else:
            res = json.loads(res)
            if res['response']['errorCount'] == 0:
                res = res['response']
            else:
                _logger.error("_yhd_orders_detail_get error2: %s" % res)
                res = False
        return res

    def _taobao_prepare_data(self, cr, uid, info, record, context=None):
        _logger.info("Start  _prepare_data_taobao")

        Taobao_Spread_Product_id = 40340349149
        partner_obj = self.pool.get('res.partner')

        #TODO partner should get from _Partner_dict,
        partner = record.partner_id

        order_line = []
        for line in info['orders']['order']:
            #close order.line dont need
            if line['status'] == 'TRADE_CLOSED_BY_TAOBAO':
                continue

            num = float(line['num'])
            total_fee = float(line['total_fee'])
            plateform_sku = line.get('outer_iid')
            if line['num_iid'] == Taobao_Spread_Product_id:
                plateform_sku = 'SpreadFee'
            sku_data = sync_api._Product_Dict.get(plateform_sku) or sync_api._Product_Dict.get('Error_Sku')

            order_line.append((0, 0, {
                'name': '[' + str(plateform_sku) + ']' + sku_data['name'],
                'product_id': sku_data['id'],
                'product_uom_qty': num,
                'price_unit': total_fee / num,
                'platform_sol_id': str(line['oid']),
            }))

        discount_fee = float((info['discount_fee']))
        post_fee = float(info['post_fee'])
        if post_fee:
            pdt_post = sync_api._Product_Dict.get('PostageFee')
            order_line.append((0, 0, {'name': pdt_post['name'], 'product_id': pdt_post['id'], 'product_uom_qty': 1, 'price_unit': post_fee}))
        if discount_fee:
            pdt_discount = sync_api._Product_Dict.get('DiscountFee')
            order_line.append((0, 0, {'name': pdt_discount['name'], 'product_id': pdt_discount['id'], 'product_uom_qty': 1, 'price_unit': 0 - discount_fee}))

        #matcing user by memeory "#login-name#"
        seller_memo = info.get('seller_memo', '')
        login = '#' in seller_memo and seller_memo.split('#')[1] or 'None'
        _logger.info("_prepare_data_taobao get login:%s %s" % (str(info['tid']), login))

        #get user_id and partner
        if record.is_multi_user:
            user_id = sync_api._Login_Dict.get(login)
            partner_info = sync_api._Partner_Dict.get(info['buyer_nick'], '')
            if partner_info and partner_info['monkey_id']:
                partner = partner_obj.browse(cr, uid, partner_info['id'], context=context)
        else:
            user_id = record.user_id.id

        platform_create_time = strp_time(info['created'])
        data = {
            'partner_id': partner.id,
            'pricelist_id': partner.property_product_pricelist.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'api_id': record.id,
            'carrier_id': record.carrier_id and record.carrier_id.id,
            'receive_user': info.get('receiver_name', ''),
            'receiver_city_id': self.get_city_id_by_name(info.get('receiver_city', '')),
            'receiver_state_id': self.get_state_id_by_name(info.get('receiver_state', '')),
            'receiver_district': info.get('receiver_district', ''),
            'receive_address': info.get('receiver_address'),
            'receive_phone': info.get('receiver_mobile') or info.get('receiver_phone'),
            'receiver_zip': info.get('receiver_zip'),
            'order_line': order_line,
            'platform_so_id': str(info['tid']),
            'platform_so_state': info.get('status', ),
            'payment': float(info.get('payment', 0)),
            'platform_user_id': info.get('buyer_nick',),
            'platform_create_time': platform_create_time,
            'platform_pay_time': strp_time(info.get('pay_time')),
            'platform_seller_id': info.get('seller_nick'),
            'note': info.get('buyer_message', ''),
            'seller_pay_no': info.get('seller_alipay_no', ''),
            'buyer_pay_no': info.get('buyer_alipay_no', ''),
            'user_id': user_id,
            'section_id': record.section_id.id,
            'create_type': 'auto',
            'shop_id': record.shop_id.id,
            #'date_order': platform_create_time[0:10],
        }

        _logger.info("End  _prepare_data_taobao")
        return data

    def _taobao_filter_exist_trade(self, cr, uid, trade_ids, context=None):
        _logger.info("Start  _taobao_filter_exist_trade")

        todo = []
        so_pool = self.pool.get('sale.order')
        exist_ids = so_pool.search(cr, uid, [('platform_so_id', 'in', [str(i) for i in trade_ids])])
        if exist_ids:
            read_ifno = so_pool.read(cr, uid, exist_ids, ['platform_so_id'], context=None)
            exist_trade_ids = [int(i['platform_so_id'])  for i in read_ifno]
            todo = list(set(trade_ids) - set(exist_trade_ids))
        else:
            todo = trade_ids
        _logger.info("End  _taobao_filter_exist_trade")
        return todo

    def _yhd_filter_exist_trade(self, cr, uid, trade_ids, context=None):
        _logger.info("Start  _yhd_filter_exist_trade")

        todo = []
        so_pool = self.pool.get('sale.order')
        exist_ids = so_pool.search(cr, uid, [('platform_so_id', 'in', [i for i in trade_ids])])
        if exist_ids:
            read_ifno = so_pool.read(cr, uid, exist_ids, ['platform_so_id'], context=None)
            exist_trade_ids = [i['platform_so_id']  for i in read_ifno]
            todo = list(set(trade_ids) - set(exist_trade_ids))
        else:
            todo = trade_ids
        _logger.info("End  _yhd_filter_exist_trade")
        return todo

    def get_connection_ok_api(self, cr, uid, ids=None, context=None,):
        ids = ids or self.search(cr, uid, [])
        ok_ids = []
        for i in ids:
            if self.connection_test(cr, uid, i, context=context, popup=False):
                ok_ids.append(i)

        _logger.info("get_connection_ok_api %s" % ok_ids)
        return ok_ids

    def connection_test(self, cr, uid, ids, context=None, popup=True):
        """
        @return:  Boolean
        """
        api_id = isinstance(ids, list) and ids[0] or ids
        me = self.browse(cr, uid, api_id, context=context)

        ok = None
        if me.type in ['taobao', 'tmall']:
            ok = self._taobao_connection_test(cr, uid, ids, me, context=context, popup=popup)
        elif me.type == 'yhd':
            ok = self._yhd_connection_test(cr, uid, ids, me, context=context, popup=popup)
        elif me.type == 'alibaba':
            ok = self._alibaba_connection_test(cr, uid, ids, me, context=context, popup=popup)
        elif me.type == 'suning':
            ok = self._suning_connection_test(cr, uid, ids, me, context=context, popup=popup)
        elif me.type == 'beibei':
            ok = self._beibei_connection_test(cr, uid, ids, me, context=context, popup=popup)
        else:
            raise osv.except_osv((u"连接失败"), (u"未知平台类型"))
        return ok

    def _beibei_connection_test(self, cr, uid, ids, me, context=None, popup=True):
        '''贝贝网链接测试'''
        params = {
            'app_id': me.app_key,
            'session': me.session_key,
            'timestamp': int(time.time()),
            'method': 'beibei.outer.item.onsale.get',
            'page_no': 0,
        }
        res = self.Beibei_Request(params, me.key_secret)
        success = None
        try:
            res = json.loads(res)
            success = res['success']
        except:
            pass
        if success:
            logger_popup(success, popup, u"连接OK")
        else:
            logger_popup(res, popup, u"连接Failure")
        return success and True or False

    def _suning_connection_test(self, cr, ui, ids, me, context=None, popup=True):

        body = '{"sn_request":{"sn_body":{"getShopInfo":{}}}}'
        header = self._API_ARG['suning'].copy()

        header.update({
            'AppMethod': 'suning.custom.shopinfo.get',
            'AppRequestTime': time_ago(),
            'AppKey': me.app_key,
        })
        res = self.Suning_Request(body, header, me.key_secret)
        shopName = None
        try:
            res = json.loads(res)
            shopName = res['sn_responseContent']['sn_body']['getShopInfo']['shopName']
        except Exception, e:
            pass
        if shopName:
            logger_popup(shopName, popup, u"连接OK")
        else:
            logger_popup(res, popup, u"连接Failure")

        return shopName and True or False

    def _alibaba_connection_test(self, cr, uid, ids, me, context=None, popup=True):
        arg = {'access_token': me.session_key, 'memberId': me.member_id}
        urlpath = '/'.join(['param2/1/cn.alibaba.open', 'trade.logisticsCompany.logisticsCompanyList.get', me.app_key])
        res = self.Alibaba_Request(urlpath, arg, me.key_secret)
        success = None
        try:
            res = json.loads(res)
            success = res['result']['success']
        except Exception, e:
            pass
        if success:
            logger_popup(success, popup, u"连接OK")
        else:
            logger_popup(res, popup, u"连接Failure")

        return success and True or False

    def _yhd_connection_test(self, cr, uid, ids, me, context=None, popup=True):
        arg = self._API_ARG['yhd'].copy()
        arg.update({
            'appKey': me.app_key,
            'sessionKey': me.session_key,
            'timestamp': time_ago(),
            'method': 'yhd.store.get',
        })
        res = self.Yhd_Request(arg, me.key_secret)
        storeName = None
        try:
            res = json.loads(res)
            storeName = res['response']['storeMerchantStoreInfo']['storeName']
        except Exception, e:
            pass
        if storeName:
            logger_popup(storeName, popup, u"连接OK")
        else:
            logger_popup(res, popup, u"连接Failure")
        return storeName and True or False

    def _taobao_connection_test(self, cr, uid, ids, me, context=None, popup=True):
        arg = self._API_ARG['taobao'].copy()
        arg.update({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'app_key': me.app_key,
            'session': me.session_key,
            'method': 'taobao.user.seller.get',
            'fields': 'nick',
        })
        res = self.Top_Request(arg, me.key_secret)
        nick = None
        try:
            res = json.loads(res)
            nick = res['user_seller_get_response']['user']['nick']
        except Exception, e:
            pass
        if nick:
            logger_popup(nick, popup, u"连接OK")
        else:
            logger_popup(res, popup, u"连接Failure")
        return nick and True or False

    def onchange_type(self, cr, uid, ids, p_type):

        address_format = '%(state)s %(city)s %(district)s %(address)s'
        if p_type in ['taobao', 'yhd', 'tmall']:
            address_format = '%(state)s %(city)s %(district)s %(address)s'
        elif p_type in ['alibaba', 'suning']:
            address_format = '%(address)s'

        icp = self.pool.get('ir.config_parameter')
        type_param = dict([(i[0], 'appkey_' + i[0]) for i in Platform_List])
        app_key, key_secret = icp.get_param(cr, uid, type_param[p_type], '::').split("::")
        return {'value': {
            'app_key': app_key,
            'key_secret': key_secret,
            'address_format': address_format,
        }}

    def get_order_beibei(self, cr, uid, record, context=None):
        '''获得贝贝网的订单，并同步到数据库'''
        _logger.info('get_order_beibei:start')
        beibei_tids_info = self._beibei_trades_sold_get(cr, uid, record, context=context)
        beibei_tids = [i['oid'] for i in beibei_tids_info] or []
        todo_tids = beibei_tids and self._beibei_filter_exist_trade(cr, uid, beibei_tids, context)
        todo_tids_info = filter(lambda i: str(i['oid']) in todo_tids, beibei_tids_info)
        so_datas = self._beibei_prepare_data(cr, uid, todo_tids_info, record, context=context)
        for i in so_datas:
            if i['flag_create']:
                self._check_create_so(cr, uid, i['data'], context=context)
        _logger.info('get_order_beibei: end')
        return True

    def _beibei_prepare_data(self, cr, uid, beibei_tids_info, record, context=None):
        ''''''
        _logger.info('_beibei_prepare_data: start')

        #partner = context.get('default_ds_partner')
        
        partner = record.partner_id
        res = []
        for info in beibei_tids_info:
            flag_create = True
            order_line = []
            for detail in info['item']:
                sku = detail.get('outer_id')
                sku_data = sync_api._Product_Dict.get(sku) or sync_api._Product_Dict.get('Error_Sku')
                order_line.append((0, 0, {
                    'name': '[' + str(sku) + ']' + sku_data['name'],
                    'product_id': sku_data['id'],
                    'product_uom_qty': float(detail['num']),
                    'price_unit': float(detail['price']),
                }))
            if info['shipping_fee'] > 0:
                pdt_post = sync_api._Product_Dict.get('PostageFee')
                order_line.append((0, 0, {'name': pdt_post['name'], 'product_id': pdt_post['id'], 'product_uom_qty': 1, 'price_unit': info['shipping_fee']}))

            payment = info.get('payment', 0)
            platform_create_time = strp_time(info['create_time'])
            platform_pay_time = strp_time(info['pay_time'])
            note = info.get('remark', '') and u'买家备注：' + info.get('remark', '') + info.get('seller_remark', '') and u'卖家备注：' + info.get('seller_remark', '')
            data = {
                'partner_id': partner.id,
                'pricelist_id': partner.property_product_pricelist.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
                'api_id': record.id,
                'carrier_id': record.carrier_id and record.carrier_id.id,
                'receive_user': info.get('receiver_name', ''),
                'receiver_city_id': self.get_city_id_by_name(info.get('city', '')),
                'receiver_state_id': self.get_state_id_by_name(info.get('province', '')),
                'receiver_district': info.get('county', ''),
                'receive_address': info.get('receiver_address', ''),
                'receive_phone': info.get('receiver_phone', ''),
                'order_line': order_line,
                'receiver_zip': '',
                'platform_so_id': info.get('oid', ''),
                'platform_so_state': str(info['status']),
                'payment': payment,
                'platform_user_id': info.get('nick', ''),
                'platform_create_time': platform_create_time,
                'platform_pay_time': platform_pay_time,
                'platform_seller_id': record.name,
                'note': note,
                'create_type': 'auto',
                'user_id': record.user_id.id,
                'section_id': record.section_id.id,
                'shop_id': record.shop_id.id,
            }
            res.append({'flag_create': flag_create, 'data': data})
        _logger.info('_beibei_prepare_data: end')
        return res

    def _beibei_filter_exist_trade(self, cr, uid, beibei_tids, context=None):
        '''过滤已经存在的订单'''
        _logger.info('Start _beibei_filter_exist_trade')
        todo = []
        so_pool = self.pool.get('sale.order')
        exists_ids = so_pool.search(cr, uid, [('platform_so_id', 'in', [str(i) for i in beibei_tids])])
        if exists_ids:
            read_ifno = so_pool.read(cr, uid, exists_ids, ['platform_so_id'], context=context)
            exist_trade_ids = [i['platform_so_id']for i in read_ifno]
            todo = list(set(beibei_tids) - set(exist_trade_ids))
        else:
            todo = beibei_tids
        _logger.info('End _beibei_filter_exist_trade')
        return todo

    def _beibei_trades_sold_get(self, cr, uid, record, context=None):
        '''获得贝贝网的订单'''
        orderDatas = []
        count = 0
        page_no = 1
        page_size = 150
        while(count >= 0):
            timestamp = time.time()
            dateArray = datetime.now() + timedelta(hours=-record.offset_time)
            params = {
                    'app_id': record.app_key,
                    'session': record.session_key,
                    'method': 'beibei.outer.trade.order.get',
                    'timestamp': int(timestamp),
                    'status': 1,
                    'page_no': page_no,
                    'page_size': page_size,
                    'start_time': int(time.mktime(dateArray.timetuple())),
                    'end_time': int(timestamp),
                }
            res = self.Beibei_Request(params, record.key_secret)
            orderData = []
            try:
                res = json.loads(res)
                orderData = res['data']
                if page_no == 1:
                    count = int(res['count'])
                count = count - page_size
            except:
                pass
            if orderData:
                orderDatas += orderData
            page_no += 1
        return orderDatas

    def get_order_suning(self, cr, uid, record, context=None):
        '''
        获取苏宁的订单，并同步到数据库
        '''
        _logger.info('get_order_suning:start')
        #获得苏宁订单，
        suning_tids_info = self._suning_trades_sold_get(cr, uid, record, context=context)
        if not suning_tids_info:
            return True
        #过滤已经存在订单
        suning_tids = [i['orderCode'] for i in suning_tids_info] or []
        todo_tids = suning_tids and self._suning_filter_exist_trade(cr, uid, suning_tids, context=context) or []
        todo_tids_info = filter(lambda i: str(i['orderCode']) in todo_tids, suning_tids_info)
        #准备数据
        so_datas = self._suning_prepare_data(cr, uid, todo_tids_info, record, context=context)
        #创建订单
        for i in so_datas:
            if i['flag_create']:
                self._check_create_so(cr, uid, i['data'], context=context)
        _logger.info('get_order_suning: end')
        return True

    def _suning_prepare_data(self, cr, uid, suning_tids_info, record, context=None):
        '''
        对从苏宁获得的订单数据进行处理，获取相应的字段
        '''
        _logger.info('_suning_prepare_data: start')

        #partner = context.get('default_ds_partner')
        partner = record.partner_id
        res = []
        for info in suning_tids_info:
            flag_create = True
            #订单明细
            post_fee = 0
            discount_fee = 0
            payment = 0.0
            order_line = []
            for detail in info['orderDetail']:
                discount_fee += float(detail['coupontotalMoney']) + float(detail['vouchertotalMoney'])
                post_fee += float(detail['transportFee'])
                #价格*数量+运费-优惠劵金额，由于现在没有做收入的细分，暂时不扣除优惠卷
                payment += float(detail['unitPrice']) * float(detail['saleNum']) + post_fee
                #get sku data
                plateform_sku = detail.get('itemCode')
                sku_data = sync_api._Product_Dict.get(plateform_sku) or sync_api._Product_Dict.get('Error_Sku')

                order_line.append((0, 0, {
                    'name': '[' + str(plateform_sku) + ']' + sku_data['name'],
                    'product_id': sku_data['id'],
                    'product_uom_qty': float(detail['saleNum']),
                    'price_unit': float(detail['unitPrice']),
                    'platform_sol_id': detail['orderLineNumber'],
                }))

            if post_fee:
                pdt_post = sync_api._Product_Dict.get('PostageFee')
                order_line.append((0, 0, {'name': pdt_post['name'], 'product_id': pdt_post['id'], 'product_uom_qty': 1, 'price_unit': post_fee}))
            #由于现在没有做收入的细分，暂时不扣除优惠卷
            #if  discount_fee:
            #    order_line.append((0, 0, {'name':pdt_discount.name, 'product_id':pdt_discount.id, 'product_uom_qty':1, 'price_unit': 0-discount_fee    }))
            platform_create_time = strp_time(info['orderSaleTime'])

            data = {
               'partner_id': partner.id,
               'pricelist_id': partner.property_product_pricelist.id,
               'partner_invoice_id': partner.id,
               'partner_shipping_id': partner.id,
               'api_id': record.id,
               'carrier_id': record.carrier_id and record.carrier_id.id,
               'receive_user': info.get('customerName', ''),
               'receiver_city_id': self.get_city_id_by_name(info.get('cityName', '')),
               'receiver_state_id': self.get_state_id_by_name(info.get('provinceName', '')),
               'receiver_district': info.get('districtName', ''),
               'receive_address': info.get('customerAddress', ''),
               'receive_phone': info.get('mobNum', ''),
               'order_line': order_line,
               'receiver_zip': '',
               'platform_so_id': info.get('orderCode', ''),
               'platform_so_state': str(info['orderTotalStatus']),
               'payment': payment,
               'platform_user_id': info.get('userName', ''),
               'platform_create_time': platform_create_time,
               'platform_seller_id': record.name,
               'note': info.get('buyerOrdRemark', ''),
               'create_type': 'auto',
               'user_id': record.user_id.id,
               'section_id': record.section_id.id,
               'shop_id': record.shop_id.id,
               #'date_order': platform_create_time[0:10],
            }
            res.append({'flag_create': flag_create, 'data': data})
        _logger.info('_suning_prepare_data: end')
        return res

    def _suning_filter_exist_trade(self, cr, uid, trade_ids, context=None):
        '''
        滤出数据库中已经存在的订单
        '''
        _logger.info('Start _suning_filter_exist_trade')
        todo = []
        so_pool = self.pool.get('sale.order')
        exists_ids = so_pool.search(cr, uid, [('platform_so_id', 'in', [str(i) for i in trade_ids])])
        if exists_ids:
            read_ifno = so_pool.read(cr, uid, exists_ids, ['platform_so_id'], context=context)
            exist_trade_ids = [i['platform_so_id']for i in read_ifno]
            todo = list(set(trade_ids) - set(exist_trade_ids))
        else:
            todo = trade_ids
        _logger.info('End _suning_filter_exist_trade')
        return todo

    def _suning_trades_sold_get(self, cr, uid, record, context=None):
        '''
        获得苏宁的订单信息，默认为未发货的订单
        pageNo:查询页码
        pageSize:单页显示结果数量
        orderStatus:订单状态 10待发货，20已发货，21部分发货，30交易成功 ，40交易关闭
        return:返回结果为列表,元素为字典,列表长度为查询到的订单个数
        '''
        _logger.info('Start _suning_trades_sold_get')

        now = time_ago()
        startTime = time_ago(record.offset_time)
        body = '{"sn_request":{"sn_body":{"orderQuery":{"pageNo":"1","pageSize":"100","orderStatus":"","endTime":"%s","startTime":"%s"}}}}' % (now, startTime)
        header = self._API_ARG['suning'].copy()
        header.update({
            'AppMethod': 'suning.custom.order.query',
            'AppRequestTime': now,
            'AppKey': record.app_key,
        })
        res = self.Suning_Request(body, header, record.key_secret)

        if isinstance(res, Exception):
            _logger.info('Start _suning_trades_sold_get error %s' % res)
            res = False
        else:
            res = json.loads(res)
            if res['sn_responseContent'].get('sn_error'):
                _logger.info('Start _suning_trades_sold_get error2 %s' % res)
                res = False
            else:
                res = res['sn_responseContent']['sn_body']['orderQuery']

        return res

    def reget_order(self, cr, uid, record, platform_so_id, context=None):
        _logger.info("Start reget_order")
        self.check_get_all_dict(cr, context=context)
        infos = self.get_one_by_platform_so_id(cr, uid, platform_so_id, record, context=context)
        data = infos and self.prepare_one(cr, uid, infos, record, context)
        _logger.info("End reget_order")
        return data

    def prepare_one(self, cr, uid, infos, record, context=None):
        data = None
        if record.type in ['taobao', 'tmall']:
            data = infos and self._taobao_prepare_data(cr, uid, infos, record, context=context)
        elif record.type == 'yhd':
            datas = infos and self._yhd_prepare_data(cr, uid, infos, record, context=context)
            if datas and datas[0]['flag_create']:
                data = datas[0]['data']
        elif record.type == 'alibaba':
            datas = infos and self._alibaba_prepare_data(cr, uid, infos, record, context=context)
            if datas and datas[0]['flag_create']:
                data = datas[0]['data']
        elif record.type == 'suning':
            datas = infos and self._suning_prepare_data(cr, uid, infos, record, context=context)
            if datas and datas[0]['flag_create']:
                data = datas[0]['data']
        elif record.type == 'beibei':
            datas = infos and self._beibei_prepare_data(cr, uid, infos, record, context=context)
            if datas and datas[0]['flag_create']:
                data = datas[0]['data']
        return data

    def get_one_status(self, cr, uid, platform_so_id, record, context=None):
        infos = self.get_one_by_platform_so_id(cr, uid, platform_so_id, record, context=context)
        state = infos and self.parse_one_status(cr, uid, infos, record, context=context)
        return state

    def parse_one_status(self, cr, uid, infos, record, context=None):
        _logger.info("Start parse_one_status")

        state = None
        try:
            if record.type in ['taobao', 'tmall']:
                state = infos['status']
            elif record.type == 'yhd':
                state = infos['orderInfoList']['orderInfo'][0]['orderDetail']['orderStatus']
            elif record.type == 'alibaba':
                state = infos[0]['status']
            elif record.type == 'suning':
                state = str(infos[0]['orderTotalStatus'])
            elif record.type == 'beibei':
                state = str(infos[0]['status'])
            else:
                pass
        except Exception, e:
            _logger.info("Error parse_one_status, %s %s" % (infos, e))

        _logger.info("End parse_one_status")
        return state

    def get_one_by_platform_so_id(self, cr, uid, platform_so_id, record, context=None):
        infos = None
        if record.type in ['taobao', 'tmall']:
            infos = self.get_one_taobao(cr, uid, platform_so_id, record, context=context)
        elif record.type == 'yhd':
            infos = self.get_one_yhd(cr, uid, platform_so_id, record, context=context)
        elif record.type == 'alibaba':
            infos = self.get_one_alibaba(cr, uid, platform_so_id, record, context=context)
        elif record.type == 'suning':
            infos = self.get_one_suning(cr, uid, platform_so_id, record, context=context)
        elif record.type == 'beibei':
            infos = self.get_one_beibei(cr, uid, platform_so_id, record, context=context)
        return infos

    def get_one_taobao(self, cr, uid, platform_so_id, record, context=None):
        _logger.info("Start get_one_taobao")
        info = self._get_tabao_tid_fullinfo(cr, uid, record, [platform_so_id, ], context=context)[0]
        _logger.info("End get_one_taobao")
        return info

    def get_one_yhd(self, cr, uid, platform_so_id, record, context=None):
        _logger.info("Start get_one_yhd")

        infos = False
        arg = sync_api._API_ARG['yhd'].copy()
        arg.update({
            'appKey': record.app_key,
            'sessionKey': record.session_key,
            'timestamp': time_ago(0),
            'method': 'yhd.order.detail.get',
            'orderCode': platform_so_id,
        })
        res = self.Yhd_Request(arg, record.key_secret)
        try:
            res = json.loads(res)
            infos = {"orderInfoList": {"orderInfo": [res['response']['orderInfo']]}}
        except Exception, e:
            _logger.info("Error reget_order_yhd %s %s" % (res, e))
        _logger.info("End get_one_yhd")
        return infos

    def get_one_alibaba(self, cr, uid, platform_so_id, record, context=None):
        _logger.info("Start get_one_alibaba")
        infos = False
        arg = {
            'orderId': platform_so_id,
            'access_token': record.session_key,
        }
        urlpath = '/'.join(['param2/1/cn.alibaba.open', 'trade.order.orderList.get', record.app_key])
        res = self.Alibaba_Request(urlpath, arg, record.key_secret)
        try:
            res = json.loads(res)
            infos = res['result']['toReturn']
        except Exception, e:
            _logger.info("Error reget_order_alibaba2 %s %s" % (res, e))

        _logger.info("End get_one_alibaba")
        return infos

    def get_one_suning(self, cr, uid, platform_so_id, record, context=None):
        _logger.info("Start get_one_suning")

        infos = False
        body = '''{"sn_request":{"sn_body":{"orderGet":{"orderCode":"%s"}}}}''' % platform_so_id
        header = self._API_ARG['suning'].copy()
        header.update({
            'AppMethod': 'suning.custom.order.get',
            'AppRequestTime': time_ago(0),
            'AppKey': record.app_key,
        })
        res = self.Suning_Request(body, header, record.key_secret)
        try:
            res = json.loads(res)
            infos = [res['sn_responseContent']['sn_body']['orderGet']]
        except Exception, e:
            _logger.info("Error reget_order_suning2 %s : %s : %s: %s" % (header, body, res, e))

        _logger.info("End get_one_suning")
        return infos

    def get_one_beibei(self, cr, uid, platform_so_id, record, context=None):
        ''''''
        timestamp = time.time()
        params = {
            'oid': platform_so_id,
            'method': 'beibei.outer.trade.order.detail.get',
            'app_id': record.app_key,
            'session': record.session_key,
            'timestamp': int(timestamp),
        }
        res = self.Beibei_Request(params, record.key_secret)
        orderData = None
        try:
            res = json.loads(res)
            orderData = res['data']
        except:
            pass
        return [orderData]

    def action_delivery(self, cr, uid, record, value, context=None):
        """
        已经发货信息，提交到 销售平台
        """
        _logger.info("Start action_delivery")
        self.check_get_all_dict(cr, context=context)

        res = None
        if record.type in ['taobao', 'tmall']:
            res = self.action_delivery_taobao(cr, uid, record, value, context=context)
        if record.type == 'yhd':
            res = self.action_delivery_yhd(cr, uid, record, value, context=context)
        if record.type == 'alibaba':
            res = self.action_delivery_alibaba(cr, uid, record, value, context=context)
        if record.type == 'suning':
            res = self.action_delivery_suning(cr, uid, record, value, context=context)

        _logger.info("End action_delivery")
        return res

    def action_delivery_alibaba(self, cr, uid, record, value, context=None):
        """
        @return the new so platform_status
        """
        _logger.info("Start action_delivery_alibaba")
        state_todo = 'waitsellersend'
        new_status = False
        tid_status = self.get_one_status(cr, uid, value['platform_so_id'], record, context=context)
        if tid_status:
            if tid_status == state_todo:
                arg = {
                    'orderId': value['platform_so_id'],
                    'orderEntryIds': value['platform_sol_id'],
                    'tradeSourceType': 'cbu-trade',
                    'logisticsCompanyId': value['company_code'],
                    'logisticsBillNo': value['tracking'],
                    'gmtSystemSend': time.strftime(DF),
                    'gmtLogisticsCompanySend': time.strftime(DF),
                    'access_token': record.session_key,
                }
                #8为其他快递，用公司名字提交
                if value['company_code'] == '8':
                    arg.update({'selfCompanyName': value.get('company_name', '')})
                urlpath = '/'.join(['param2/1/cn.alibaba.open', 'e56.logistics.offline.send', record.app_key])
                res = self.Alibaba_Request(urlpath, arg, record.key_secret)
                try:
                    res = json.loads(res)
                    if res['success']:
                        _logger.info('action_delivery_alibaba OK %s' % value['platform_so_id'])
                        new_status = 'waitbuyerreceive'
                    else:
                        _logger.info('action_delivery_alibaba Failure %s %s' % (res, arg))
                except Exception, e:
                    _logger.info('Error, action_delivery_alibaba %s %s' % (res, e))
            #不是待发货状态，直接返回获取的状态
            else:
                _logger.info('Error, action_delivery_alibaba state %s is not %s' % (tid_status, state_todo))
                new_status = tid_status

        _logger.info("End action_delivery_alibaba")
        return new_status

    def action_delivery_yhd(self, cr, uid, record, value, context=None):
        """
        @param return: 如果发货提交成果，返回新的状态值， 否则返回False
        """
        #YHD不需要自动同步
        return False

        _logger.info("Start  action_delivery_yhd")
        state_todo = ['ORDER_PAYED', 'ORDER_WAIT_SEND', 'ORDER_TRUNED_TO_DO']
        new_status = False
        tid_status = self.get_one_status(cr, uid, value['platform_so_id'], record, context=context)
        if tid_status:
            #提交发货信息
            if tid_status in state_todo:
                arg = sync_api._API_ARG['yhd'].copy()
                arg.update({
                    'appKey': record.app_key,
                    'sessionKey': record.session_key,
                    'timestamp': time_ago(0),
                    'method': 'yhd.logistics.order.shipments.update',
                    'orderCode': value['platform_so_id'],
                    'expressNbr': value['tracking'],
                    'deliverySupplierId': value['company_code'],
                })
                res = self.Yhd_Request(arg, record.key_secret)
                try:
                    res = json.loads(res)
                    if not res['response']['errorCount']:
                        _logger.info("action_delivery_yhd OK%s" % arg['platform_so_id'])
                        new_status = 'ORDER_OUT_OF_WH'
                    else:
                        _logger.info("action_delivery_yhd Failure %s %s" % (res, arg))
                except Exception, e:
                    _logger.info("Error action_delivery_yhd %s %s" % (res, e))
            #发货已经提交，返回获取状态
            else:
                _logger.info("Error action_delivery_yhd state %s is not %s" % (tid_status, state_todo))
                new_status = tid_status

        _logger.info("End  action_delivery_yhd")
        return new_status

    def action_delivery_taobao(self, cr, uid, record, value, context=None):
        """
        @param return: 如果发货信息提交成功或者状态为已经提交，则返回订单状态。 失败则返回False
        """
        _logger.info("Start  action_delivery_taobao")
        state_todo = 'WAIT_SELLER_SEND_GOODS'
        new_status = False
        tid_status = self.get_one_status(cr, uid, value['platform_so_id'], record, context=context)
        if tid_status:
            if tid_status == state_todo:
                arg = self._API_ARG['taobao'].copy()
                arg.update({
                    'timestamp': time.strftime(DF),
                    'app_key': record.app_key,
                    'session': record.session_key,
                    'method': 'taobao.logistics.offline.send',
                    'tid': value.get('platform_so_id',),
                    'out_sid': value.get('tracking'),
                    'company_code': value['company_code'],
                })
                res = self.Top_Request(arg, record.key_secret)
                try:
                    res = json.loads(res)
                    # logistics_offline_send_response,delivery_offline_send_response
                    if (res.get('logistics_offline_send_response', {}).get('shipping', {}).get('is_success') or
                        res.get('delivery_offline_send_response', {}).get('shipping', {}).get('is_success')):
                        new_status = 'WAIT_BUYER_CONFIRM_GOODS'
                        _logger.info("action_delivery_taobao post express OK %s" % res, value['platform_so_id'])
                    else:
                        _logger.info("Error action_delivery_taobao Failure %s %s" % (res, arg))
                except Exception, e:
                    _logger.info("Error action_delivery_taobao %s %s" % (res, e))
            #状态不是待发货，直接返回取得的状态
            else:
                _logger.info("action_delivery_taobao state %s is not %s" % (tid_status, state_todo))
                new_status = tid_status

        return new_status
        _logger.info("End action_delivery_taobao")

    def action_delivery_suning(self, cr, uid, record, value, context=None):
        """
        同步苏宁平台快递信息
        suning.custom.orderdelivery.add 自己联系物流（线下物流）发货
        orderLineNumber_sent:表示未发货的订单行项目号
        """
        _logger.info("Starts  action_delivery_suning")
        new_status = False

        infos = self.get_one_suning(cr, uid, value['platform_so_id'], record, context=context)
        info = infos and infos[0]
        if not info:
            return new_status

        todo_status = ['10', '21']

        tid_status = str(info['orderTotalStatus'])
        if tid_status in todo_status:
            #同步快递信息到苏宁
            method = 'suning.custom.orderdelivery.add'
            orderCode = value.get('platform_so_id')
            expressNo = value.get('tracking')
            expressCompanyCode = value.get('company_code')
            orderLineNumber = [str(l['orderLineNumber']) for l in info['orderDetail']]
            #orderLineNumber = ','.join([l['orderLineNumber'] for l in info['orderDetail']])
            #print tid_status, type(orderLineNumber), orderLineNumber
            ###TODO mult orderLineNumber how todo
            #if len(orderLineNumber) == 1:
            #    orderLineNumber = str(orderLineNumber[0])

            body = '''{"sn_request":{"sn_body":{"orderDelivery":{"expressNo":"%s","deliveryTime":"","orderLineNumbers":{"orderLineNumber":%s},"sendDetail":{"productCode":""},"expressCompanyCode":"%s","orderCode":"%s"}}}}''' % (expressNo, orderLineNumber, expressCompanyCode, orderCode,)
            header = self._API_ARG['suning'].copy()
            header.update({
                'AppMethod': method,
                'AppRequestTime': time_ago(0),
                'AppKey': record.app_key,
            })
            res = self.Suning_Request(body, header, record.key_secret)
            try:
                res = json.loads(res)
                detial = res['sn_responseContent']['sn_body']['orderDelivery']['sendDetail']
                if all([l['sendresult'] == 'Y' and True or False for l in detial]):
                    new_status = '20'
                    _logger.info("action_delivery_suning OK %s" % value['platform_so_id'])
                else:
                    _logger.info("action_delivery_suning Failure % %s %s" % (res, body, header))
            except Exception, e:
                _logger.info("Error action_delivery_suning %s %s" % (res, e))
        else:
            _logger.info("action_delivery_suning %s not in %s" % (tid_status, todo_status))
            new_status = tid_status

        _logger.info("End  action_delivery_suning")
        return new_status

    #===========================================================================
    # def suning_custom_shelves_move(self, cr, uid, ids, record, itemCode, productCode, context=None):
    #     '''商品下架'''
    #     body = '''{"sn_request":{"sn_body":{"shelves":{"productCode":"%s"}}}}''' % productCode
    #     header = self._API_ARG['suning'].copy()
    #     header.update({
    #         'AppMethod': 'suning.custom.shelves.move',
    #         'AppRequestTime': time_ago(),
    #         'AppKey': record.app_key,
    #     })
    #     res = self.Suning_Request(body, header, record.key_secret)
    #     try:
    #         res = json.loads(res)
    #         try:
    #             back_productCode = res['sn_responseContent']['sn_body']['shelves']['productCode']
    #             if back_productCode != productCode:
    #                 return False #raise osv.except_osv(u'错误', u'苏宁商品下架失败：%s返回值错误:%s' % (productCode, back_productCode))
    #         except:
    #             return False #raise osv.except_osv(u'错误', u'苏宁商品下架失败：%S没有成功返回结果' % productCode)
    #     except:
    #         return False #raise osv.except_osv(u'错误', u'苏宁商品下架失败：%s' % productCode)
    #     return True
    #===========================================================================

    def suning_custom_inventory_modify(self, cr, uid, record, itemCode, destInvNum, context=None):
        '''苏宁商品SKU数量修改'''
        _logger.info("Start suning_custom_inventory_modify")
        
        body = '''{"sn_request": {"sn_body": {"inventory":
        {"itemCode": "%s", "destInvNum": "%s"}}}}''' % (itemCode, destInvNum)
        header = self._API_ARG['suning'].copy()
        header.update({
            'AppMethod': 'suning.custom.inventory.modify',
            'AppRequestTime': time_ago(),
            'AppKey': record.app_key,
        })
        res = self.Suning_Request(body, header, record.key_secret)
        try:
            res = json.loads(res)
            result = res['sn_responseContent']['sn_body']['inventory']['result']
            if result != 'Y':
                return False
        except:
            pass
        
        _logger.info("End suning_custom_inventory_modify")
        return True

    def _update_platform_stock_qty_suning(self, cr, uid, record, context=None):
        '''修改suning在售库存数量'''
        _logger.info("Start _update_platform_stcok_qty_suning")

        stock_location_id = record.shop_id.warehouse_id.lot_stock_id.id
        wms_obj = self.pool.get('wms.report.stock.available')
        product_ids = [x.id for x in record.product_ids if x.type == 'product']
        wms_ids = wms_obj.search(cr, uid, [('location_id', '=', stock_location_id), ('product_id', 'in', product_ids)], context=context)
        wms_records = wms_obj.browse(cr, uid, wms_ids, context=context)
        for wms in wms_records:
            qty = int(wms.product_qty_a)
            destInvNum = qty > 0 and qty or 0
            self.suning_custom_inventory_modify(cr, uid, record, wms.product_id.default_code, destInvNum, context=context)
            
        _logger.info("End _update_platform_stcok_qty_suning")
        return True
 
    def update_platform_stcok_qty(self, cr, uid, ids, context=None):
        '''更新平台库存数量'''
        _logger.info("Start update_platform_stcok_qty")
        for record in self.browse(cr, uid, ids, context=context):
            if record.type == 'suning':
                self._update_platform_stock_qty_suning(cr, uid, record, context=context)
            else:
                pass
            
        _logger.info("End update_platform_stcok_qty")
        return True

    def _get_suning_onsale_sku(self, cr, uid, ids, record, context=None):
        '''获得苏宁的在售商品的sku'''
        _logger.info("Start  _get_suning_onsale_sku")
        onsale_sku_info = []
        pageTotal = 1
        pageNum = 1
        pageSize = 50
        body_template = '''{"sn_request":{"sn_body":{"itemSale":{"priceLimit":"",
          "productCode":"","saleStatus":"","pageNo":"%s","categoryCode":"",
          "pageSize":"%s","productName":"","priceUpper":""}}}}'''
        hearder_arg = {
            'AppMethod': 'suning.custom.itemsale.query',
            'AppRequestTime': time_ago(),
            'AppKey': record.app_key,
        }
        header = self._API_ARG['suning'].copy()
        header.update(hearder_arg)
        body = body_template % (pageNum, pageSize)
        res = self.Suning_Request(body, header, record.key_secret)
        try:
            res = json.loads(res)
            pageTotal = res['sn_responseContent']['sn_head']['pageTotal']
            onsale_sku_info += res['sn_responseContent']['sn_body']['itemSale']
        except Exception, e:
            _logger.info("Error _get_suning_onsale_sku %s" % e)
        #if pageTotal >1, get the rest page data
        while pageNum < pageTotal:
            pageNum += 1
            header = self._API_ARG['suning'].copy()
            header.update(hearder_arg)
            body = body_template % (pageNum, pageSize)
            res = self.Suning_Request(body, header, record.key_secret)
            try:
                res = json.loads(res)
                onsale_sku_info += res['sn_responseContent']['sn_body']['itemSale']
            except Exception, e:
                _logger.info("Error _get_suning_onsale_sku %s" % e)

        _logger.info("End  _get_suning_onsale_sku")
        return onsale_sku_info

    def get_onsale_product(self, cr, uid, ids, context=None):
        '''获得平台账号的在售商品'''
        _logger.info("Start get_onsale_product")
        sync_api.check_get_all_dict(cr)
        onsale_product_info = []
        list_ids = set([])
        record = self.browse(cr, uid, ids[0], context=context)
        if record.type == 'suning':
            onsale_product_info = self._get_suning_onsale_sku(cr, uid, ids, record, context=context)
        else:
            raise osv.except_osv(u'错误', u'该平台暂时没有查看库存功能，若需要请联系开发人员')
        
        if onsale_product_info:
            for info in onsale_product_info:
                sku = info['itemCode']
                if sku:
                    product = sync_api._Product_Dict.get(sku)
                    if product:
                        list_ids.add(product['id'])
        self.write(cr, uid, ids[0], {'product_ids': [(6, 0, set(list_ids))]}, context=context)
        _logger.info("End  get_onsale_product")
        return True

    def onsale_stock_available(self, cr, uid, ids, context=None):
        ''''''
        record = self.browse(cr, uid, ids[0], context=context)
        if not record.product_ids:
            raise osv.except_osv(u'错误', u'帐号没有在售的SKU，请先完善在售商品信息')
        product_ids = [x.id for x in record.product_ids]
        return {
            'name': (u'查看库存'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'wms.report.stock.available',
            'domain': [('product_id', 'in', product_ids)],
            'type': 'ir.actions.act_window',
        }

sync_api()
###################################################################
