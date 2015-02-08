#-*- coding:utf-8 -*-
import re
import urllib2
import json
from openerp.osv import  osv, fields
from openerp.tools.translate import _
from sync_api import time_ago
import logging
_logger = logging.getLogger(__name__)

Express_state = [
    ('unused', u'未使用'),
    ('0', u'在途'),
    ('1', u'揽件'),
    ('2', u'疑难'),
    ('3', u'签收'),
    ('4', u'退签'),
    ('5', u'派件'),
    ('6', u'退回'),
]


class express_express(osv.osv):
    _name = 'express.express'
    _description = "Express"
    _rec_name = 'full_name'
    _order = 'id desc'
    _query_url = "http://www.kuaidi100.com/chaxun?com=%s&nu=%s"
    _36wu_url = "http://api.36wu.com/Express/GetGeneralExpressInfo?postid=%s&com=%s"
    
    def _get_express_url(self, cr, uid, ids, name, arg=None, context=None):
        res = {}
        for exp in self.browse(cr, uid, ids, context=context):
            code = exp.delivery_carrier_id.code_100 or exp.delivery_carrier_id.code_taobao
            res[exp.id] = self._query_url % (code, exp.name)
        return res
    
    def _get_full_name(self, cr, uid, ids, name, arg=None, context=None):
        res = {}
        for exp in self.browse(cr, uid, ids, context=context):
            res[exp.id] = '%s:%s' % (exp.delivery_carrier_id.name, exp.name)
        return res
    
    def _default_picking(self, cr, uid, ids, field_name, arg=None, context=None):
        res = {}
        for express in self.browse(cr, uid, ids, context=context):
            res[express.id] = express.picking_ids and express.picking_ids[0].id or None
        return res
    
    def _default_plan_date(self, cr, uid, context=None):
        return time_ago(24 * -3)
        
    _columns = {
        'name': fields.char(u'单号', size=50, required=True),
        'delivery_carrier_id': fields.many2one('delivery.carrier', string=u'快递公司', required=True),
        #'picking_id': fields.many2one('stock.picking.out', string=u'出库单号'),
        'amount': fields.float(u'费用', required=False),
        'state': fields.selection(Express_state, string=u'状态'),
        'is_used': fields.boolean(u'已使用'),
        'note': fields.text(u'备注'),
        'url': fields.function(_get_express_url, arg=None, type='char', size=60, string=u'查询快递', readonly=True, store=True),
        'full_name': fields.function(_get_full_name, arg=None, type='char', size=70, string=u'快递单号', readonly=True, store=True),
        'picking_ids': fields.many2many('stock.picking', 'res_express_picking', 'express_id', 'picking_id', string=u'出库单'),
        'create_date': fields.datetime(u'录入时间', readonly=True),
        'printed': fields.boolean(u'是否已打印', select=True,),
        'picking_id': fields.function(_default_picking, arg=None, type='many2one', relation='stock.picking', string=u"出库单", store=True),
        'so_id': fields.related('picking_id', 'sale_id', type='many2one', relation='sale.order', readonly=True, string=u"销售订单"),
        'platform_so_id': fields.related('so_id', 'platform_so_id', type="char", readonly=True, string=u'交易号'),
        'platform_user_id': fields.related('so_id', 'platform_user_id', type="char", readonly=True, string=u'买家昵称'),
        'log': fields.char('Sync log', size=20),
        'plan_date': fields.datetime(u'预计签收日期'),
        'check_date': fields.datetime(u'查询日期'),
    }
    _defaults = {
        'state': '0',
        'plan_date': lambda self, cr, uid, c: self._default_plan_date(cr, uid, context=c),
    }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', u'快递单号不能重复'),
    ]
    
    #get
    def get_to_query(self, cr, uid, domain, context=None):
        ids = self.search(cr, uid, domain, order="id", context=context)
        return self.read(cr, uid, ids, ['url'])
        
    #查询订单状态
    def query_express_state(self, cr, uid, ids, context=None):
        _logger.info('start query_express_state')
        express_obj = self.browse(cr, uid, ids[0])
        req = self._36wu_url % (express_obj.name, express_obj.code_36wu)
        try:
            request = urllib2.urlopen(req)
            res = request.read()
            res = json.loads(res)
            request.close()
        except Exception, e:
            _logger.error(u'快递单次查询失败：%s' % e)
        text = ''
        vals = {}
        if 201 == res['status']:
            raise osv.except_osv(_(u'错误'), _(u'请求失败，参数异常或缺少参数'))
        elif 301 == res['status']:
            raise osv.except_osv(_(u'错误'), _(u'免费用户访问次数已上限'))
        elif 401 == res['status']:
            raise osv.except_osv(_(u'错误'), _(u'ak错误，未授权的ak'))
        elif 501 == res['status']:
            raise osv.except_osv(_(u'错误'), _(u'请求失败，服务内部异常'))
        elif 200 == res['status']:
            for info in res['data']:
                text += info['acceptTime'] + '  ' + info['remark'] + "\n"
                result = re.search(u'已签收', info['remark'])
                if result:
                    vals.update({
                        'state': '3',
                    })
        
        vals['carrier_log'] = text
        
        self.write(cr, uid, ids, vals)
        _logger.info('end  query_express_state')
        return True
    
    #自动更新快递状态
    def scheduler_query_express_state(self, cr, uid, ids, context=None):
        #那些状态是需要查询的  0 1 2 5，，
        _logger.info('start scheduler_query_express_state')
        args = [('state', 'in', ('0', '1', '2', '4', '5', '6'))]
        query_ids = self.search(cr, uid, args)
        express_objs = self.browse(cr, uid, query_ids, limit=20)
        for express_obj in express_objs:
            req = self._36wu_url % (express_obj.name, express_obj.code_36wu)
            try:
                request = urllib2.urlopen(req)
                res = request.read()
                res = json.loads(res)
                request.close()
            except  Exception, e:
                _logger.error(u'快递自动查询失败：%s' % e)
            text = ''
            vals = {}
            if res['status'] == 200:
                for info in res['data']:
                    text += info['acceptTime'] + '  ' + info['remark'] + "\n"
                    result = re.search(u'已签收', info['remark'])
                    if result:
                        vals.update({
                            'state': '3',
                        })
            
            vals['carrier_log'] = text
            self.write(cr, uid, express_obj.id, vals, context=context)
        _logger.info('end scheduler_query_express_state')
        return True
        
express_express()

#######################################################################################