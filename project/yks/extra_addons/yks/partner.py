# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import  osv, fields
#from openerp.tools.translate import _
import logging
import json
from  sync_api import sync_api

_logger = logging.getLogger(__name__)

Monkey_sale_type = [('1', u'德国直邮区'), ('2', u'国内现货区'), ('3', u'现货+直邮')]
Monkey_shop_type = [('1', u'淘宝C店'), ('2', u'天猫'), ('3', u'天猫国际')]


class res_city(osv.osv):
    _name = 'res.city'
    _columns = {
        'name': fields.char(u'城市', size=16, required=True,),
        'code': fields.char(u'代码', size=12, ),
        'state_id': fields.many2one('res.country.state', u'省'),
    }
    _sql_constraints = [
        #('name_unique', 'unique (name)', 'The code of the brand #must be unique !'),
    ]
res_city()


class res_district(osv.osv):
    _name = 'res.district'
    _columns = {
        'name': fields.char(u'区县', size=16, required=True,),
        'city_id': fields.many2one('res.city', u'城市'),
    }
res_district()


class res_partner_category(osv.osv):
    _name = 'res.partner.category'
    _category_type = [('industry', u'行业')]
    _columns = {
        'type': fields.selection(_category_type, u'标签关键字'),
    }
res_partner_category()


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _check_monkey_id(self, cr, uid, ids, context=None):
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.monkey_id:
                res = self.search(cr, uid, [('monkey_id', '=', partner.monkey_id), ('is_contact', '=', partner.is_contact)])
                if len(res) > 1:
                    return False
        return True

    def _uniq_supplier_name(self, cr, uid, ids, context=None):
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.supplier:
                res = self.search(cr, uid, [('supplier', '=', True), ('name', '=', partner.name)])
                if len(res) > 1:
                    return False
            #===================================================================
            # if partner.customer:
            #     res = self.search(cr, uid, [('customer', '=', True), ('name', '=', partner.name)])
            #     if len(res) > 1:
            #         return False
            #===================================================================
        return True
    #===========================================================================
    # def _check_user_id(self, cr, uid, ids, context=None):
    #     for partner in self.browse(cr, uid, ids, context=context):
    #         if (partner.supplier or partner.customer) and not(partner.user_id):
    #             return False
    #     return True
    #===========================================================================

    _columns = {
        'code': fields.char(u'编号', size=12),
        'monkey_id': fields.integer(u'悟空ID'),
        'brand_ids': fields.many2many('product.brand', 'brand_partner_ref', 'brand_id', 'partner_id', string=u'品牌'),
        'industry': fields.char(u'行业', size=50),
        'shop_type': fields.selection(Monkey_shop_type, u'店铺类型'),
        'sale_type': fields.selection(Monkey_sale_type, u'销售类型'),
        'annual_sale': fields.char(u'年销售额', size=20),
        'month_sale': fields.integer(u'月销售额'),
        'sku_month_sale': fields.integer(u'单品月销售'),
        'taobao_rate': fields.integer(u'淘宝等级'),
        'business_content': fields.char(u'主营业务', size=100),
        'count_of_employees': fields.char(u'人工人数', size=50),
        'qq': fields.char(u'QQ', size=20,),
        'wechat': fields.char(u'微信', size=50,),
        'wangwang': fields.char(u'旺旺', size=50,),
        'gender': fields.selection([('male', u'男'), ('female', u'女')], u'性别'),
        'is_contact': fields.boolean(u'悟空联系人'),
    }
    _sql_constraints = [
        ('code_uniq', 'unique (code)', u'编码重重复！'),
        #('monkey_uniq', ' CHECK (monkey_id is not null and unique(monkey_id,is_contact)', 'The Code of the monkey_id must be unique !'),
    ]
    _constraints = [
        (_check_monkey_id, 'Monkey ID must be unique', ['is_contact', 'monkey_id']),
        (_uniq_supplier_name, u'供应商名称重复请确认', ['name', 'supplier', ]),
        #(_check_user_id, u'供应商/客户 负责人不能为空', ['supplier','customer']),
    ]
    _defaults = {
        'user_id': lambda self, cr, uid, c: uid,
    }

    def create(self, cr, uid, values, context=None):
        """
        contacts is not supplier or customer, add supplier-code
        """
        if context is None:
            context = {}
        if context.get('default_supplier'):
            values.update({
                'code': self.pool.get('ir.sequence').get(cr, uid, 'yks.res.partner.supplier'),
            })
        else:
            values.update({
                'supplier': False,
            })
        if context.get('search_default_customer'):
            pass
        else:
            values.update({
                'customer': False,
            })
        res = super(res_partner, self).create(cr, uid, values, context=None)
        return res

    def monkey_sync_partner(self, cr, uid, datas, context=None):
        _logger.info('monkey_sync_partner start')

        #brand_obj = self.pool.get('product.brand')
        #title_obj = self.pool.get('res.partner.title')
        infos = json.loads(datas)
        for info in infos:
            _logger.info('monkey_sync_partner info: %s' % info)
            monkey_id = int(info['customer_id'])
            partner_ids = self.search(cr, uid, [('monkey_id', '=', monkey_id), ('is_contact', '=', False)])
            partner_id = partner_ids and partner_ids[0] or False

            #for i in info: print i, info[i]
            login = info.get('user_name', '')
            user_id = sync_api._Login_Dict.get(login) or False
            partner_data = {
                'customer': True,
                'is_company': True,
                'monkey_id': monkey_id,
                'name': info['name'],
                #'brand_id': brand_id,
                'industry': info['industry'],
                'annual_sale': info["annual_revenue"],
                'street': info["address"],
                'shop_type': str(info["shop_type"]),
                'month_sale': float(info["sales"]),
                'sale_type': str(info["sale_type"]),
                'taobao_rate': float(info['taobao_rate']),
                'sku_month_sale': int(info["product_sales"]),
                'website': info["shop_link"],
                'wechat': info["webchart"],
                'wangwang': info["wangwang"],
                'business_content': info["yewu"],
                'count_of_employees': info["no_of_employees"],
                'comment': info["description"] + u'品牌：' + info['brand'],
                'is_contact': False,
                'user_id': user_id,
            }
            ##sync customer
            if partner_id:
                _logger.info('monkey_sync_partner,update partner monkey_id %s' % monkey_id)
                self.write(cr, uid, partner_id, partner_data)
            else:
                _logger.info('monkey_sync_partner,create partner monkey_id %s' % monkey_id)
                partner_id = self.create(cr, uid, partner_data)
            ## sync contact
            for line in info.get('contacts', []):
                contact_monkey_id = int(line['contacts_id'])
                domain = [('monkey_id', '=', contact_monkey_id), ('is_contact', '!=', False),
                          ('parent_id', '!=', False), ('is_company', '!=', True),
                          ('customer', '!=', True), ('supplier', '!=', True)]
                contact_ids = self.search(cr, uid, domain, context=context)
                contact_id = contact_ids and contact_ids[0] or False
                #title_ids = title_obj.search(cr, uid, [('name', 'like', line['saltname'])])
                #title_id = title_ids and title_ids[0] or False
                contact_data = {
                    'monkey_id': contact_monkey_id,
                    'parent_id': partner_id,
                    'customer': False,
                    'supplier': False,
                    'is_company': False,
                    'name': line['name'],
                    'function': line['post'],
                    #'title': title_id, # "saltname": "", 称谓
                    'gender': line["sex"] == "0" and 'male' or 'female',
                    'mobile': line["telephone"],
                    'email': line["email"],
                    'qq': line["qq"],
                    'street': line["address"],
                    'comment': line["description"] + u'称谓：' + line['saltname'],
                    'is_contact': True,
                    'user_id': user_id,
                }
                if contact_id:
                    _logger.info('monkey_sync_partner,update contact contact_monkey_id %s' % contact_monkey_id)
                    self.write(cr, uid, contact_id, contact_data)
                else:
                    _logger.info('monkey_sync_partner,create contact contact_monkey_id %s' % contact_monkey_id)
                    contact_id = self.create(cr, uid, contact_data)

        _logger.info('monkey_sync_partner end')
        return 'OK'

    def signup_retrieve_info(self, cr, uid, token, context=None):
        res = super(res_partner, self).signup_retrieve_info(cr, uid, token, context=context)
        if "Monkey" in token:
            partner = self._signup_retrieve_partner(cr, uid, token, raise_exception=True, context=None)
            res['password'] = partner.user_ids[0].password
            res['monkey_login'] = True
        return res

res_partner()


##############################################################################
