# -*- coding: utf-8 -*-
##############################################################################
from openerp.osv import osv, fields
from openerp import pooler
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import netsvc
from sync_api import ALL_Platform_SO_State, Platform_End_Status
from sync_api import Platform_List, time_ago
import logging
_logger = logging.getLogger(__name__)

wf_service = netsvc.LocalService("workflow")

YKS_SO_TYPE = [('online', u'线上订单'), ('offline', u'线下订单'), ]
SALE_MODEL = [('normal', u'普通'), ('zy', u'直邮'), ('df', u'代发')]

# add wait_account, shipped, sign_in status
Sale_Status = [
    ('draft', u'草稿'),
    ('wait_account', u'待财务'),
    ('sent', u'待主管'),
    ('cancel', 'Cancelled'),
    ('waiting_date', 'Waiting Schedule'),
    ('progress', u'待发货'),
    ('shipping_except', u'发货异常'),
    ('manual', 'Sale to Invoice'),
    ('invoice_except', 'Invoice Exception'),
    ('shipped', u'待签收'),
    ('done', 'Done'),
]

Sale_Stage = [
    ('sent', u'待主管'),
    ('progress', u'待发货'),
]


class sale_order(osv.osv):
    _inherit = 'sale.order'

    def _auto_init(self, cr, context=None):
        cr.execute('''
            SELECT
                so.id, us.default_section_id
            FROM sale_order AS so
                LEFT JOIN res_users AS us ON(so.user_id = us.id )
            WHERE so.section_id IS Null AND us.default_section_id IS NOT Null;
        ''')
        for i in cr.fetchall():
            cr.execute('''update sale_order set (section_id)=('%s') where id = %s ''' % (i[1], i[0]))

        return super(sale_order, self)._auto_init(cr, context=context)

    def _get_express_url(self, cr, uid, ids, name, arg, context=None):
        res = {}
        default_url = "http://www.kuaidi100.com/chaxun?com=%s&nu=%s"
        for r in self.browse(cr, uid, ids, context=context):
            if r.yks_carrier_tracking and r.yks_carrier_id and r.yks_carrier_id.partner_id.code:
                res[r.id] = default_url % (r.yks_carrier_id.partner_id.code, r.yks_carrier_tracking)
            else:
                res[r.id] = u"请补充快递公司编码和快递单号"
        return res
    
    def _default_deliver_info(self, cr, uid, context=None):
        return {
            'deliver_name': self._default_deliver_name(cr, uid, context=context),
            'deliver_company_name': self._default_deliver_company_name(cr, uid, context=context),
            'deliver_tel': self._default_deliver_tel(cr, uid, context=context),
            'deliver_address': self._default_deliver_address(cr, uid, context=context),
        }

    def _default_deliver_name(self, cr, uid, context=None):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).name

    def _default_deliver_company_name(self, cr, uid, context=None):
        return '-'
        #return self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.name

    def _default_deliver_address(self, cr, uid, context=NameError):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.street

    def _default_deliver_tel(self, cr, uid, context=NameError):
        return self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.mobile

    _columns = {
        'state': fields.selection(Sale_Status, 'Status', readonly=True, track_visibility='onchange'),
        'api_id': fields.many2one('sync.api', 'API'),
        'api_type': fields.related('api_id', 'type', type="selection", selection=Platform_List, string=u"平台", readonly=True),
        'receive_user': fields.char(u'收件人', size=20),
        "receiver_city_id": fields.many2one('res.city', u'城市'),
        "receiver_district": fields.char(u'区域', size=30),
        "receiver_state_id": fields.many2one('res.country.state', u'省'),
        'receive_address': fields.char(u'收货地址', size=80),
        'receive_phone': fields.char(u'收货电话', size=20),
        'receiver_zip': fields.char(u'邮编', size=20),

        'platform_user_id': fields.char(u'买家昵称', size=30, help=u"例如淘宝买家昵称",),
        'platform_seller_id': fields.char(u'卖家昵称', size=30, help=u"例如淘宝卖家昵称",),
        'platform_so_id': fields.char(u'交易编号', size=50, help=u"例如淘宝TID",),
        'platform_so_state': fields.selection(ALL_Platform_SO_State, u'平台交易状态', readonly=False, size=50),
        'platform_create_time': fields.datetime(u'平台创建时间',),
        'platform_pay_time': fields.datetime(u'平台付款时间',),
        'seller_pay_no': fields.char(u'收款帐号', size=40,),
        'buyer_pay_no': fields.char(u'付款帐号', size=40,),
        'payment': fields.float(u'付款金额', digits_compute=dp.get_precision('Account')),
        'payment_number': fields.char(u'支付流水号', size=45),

        'yks_type': fields.selection(YKS_SO_TYPE, u"线上／线下"),
        'yks_carrier_id': fields.many2one('delivery.carrier', u'快递方式', ),
        
        'yks_carrier_tracking': fields.char(u'快递单号', size=50,),
        'express_url': fields.function(_get_express_url, arg=None, type='char', string=u'快递详情', readonly=1,),
        'express_sign': fields.boolean(u'已签收', ),
        'create_type': fields.selection([('auto', u'自动同步订单'), ('manual', u'人工创建订单')], string=u'创建方式', help=u"手动创建的订单需要财务审核"),
        'account_state': fields.selection([('wait_account_approve', u'待财务审核'), ('account_approved', u'财务审核完成')], u'财务状态'),
         ##送货人信息
        'is_drop_shopping': fields.boolean(u'代发打印', help=u'发货信息的切换按钮标记'),
        'deliver_name': fields.char(u'发货人', size=20),
        'deliver_city_id': fields.many2one('res.city', u'发货城市'),
        'deliver_company_name': fields.char(u'发货单位', size=50),
        'deliver_tel': fields.char(u'发货电话', size=20),
        'deliver_address': fields.char(u'发货地址', size=80),
        
        'unneed_express': fields.boolean(u'无需快递'),
        'carrier_id': fields.many2one('delivery.carrier', u'快递方式'),
        'need_express_count': fields.integer(u'需要快递单数量'),
        'sale_model': fields.selection(SALE_MODEL, u'代发|直邮'),
        'need_split_picking': fields.boolean(u'需要拆分出库'),
        
        'rdo_id': fields.many2one('requirement.distribution.order', u'需求分配',),
        'stage': fields.selection(Sale_Stage, u'阶段'),
        
    }
    _sql_constraints = [
        ('platform_so_id_uniq', 'unique (platform_so_id)', u'平台交易编号已经存在，请在报价单、销售订单中查找此订单!'),
        #('platform_so_id_uniq', 'unique (api_id,platform_so_id)', u'交易编号已经存在，请在报价单、销售订单中查找此订单!'),
     ]

    _defaults = {
        'yks_type': 'online',
        'create_type': 'manual',
        'account_state': 'wait_account_approve',
        'deliver_name': lambda self, cr, uid, c: self._default_deliver_name(cr, uid, context=c),
        'deliver_company_name': lambda self, cr, uid, c: self._default_deliver_company_name(cr, uid, context=c),
        'deliver_address': lambda self, cr, uid, c: self._default_deliver_address(cr, uid, context=c),
        'deliver_tel': lambda self, cr, uid, c: self._default_deliver_tel(cr, uid, context=c),
        'deliver_city_id': 544,
        'need_express_count': lambda *a: 1,
        'sale_model': 'normal',
    }
    
    def create(self, cr, uid, value, context=None):

        api_obj = self.pool.get('sync.api')
        user_id = value.get('user_id', 0)
        api_id = value.get('api_id', 0)
        #create by sync.api
        if user_id and user_id != uid:
            value.update(self._default_deliver_info(cr, user_id, context=context))

        #如果帐号有设置，用帐号送货信息替换
        if api_id:
            record = api_obj.browse(cr, uid, api_id, context=context)
            if record.deliver_name:
                value.update({'deliver_name': record.deliver_name})
            if record.deliver_city_id:
                value.update({'deliver_city_id': record.deliver_city_id.id})
            if record.deliver_company_name:
                value.update({'deliver_company_name': record.deliver_company_name})
            if record.deliver_tel:
                value.update({'deliver_tel': record.deliver_tel})
            if record.deliver_address:
                value.update({'deliver_address': record.deliver_address})

        return super(sale_order, self).create(cr, uid, value, context=context)

    def action_button_confirm(self, cr, uid, ids, context=None):
        res = super(sale_order, self).action_button_confirm(cr, uid, ids, context=context)
        res = res
        #don not  return new view, only return True, so SO charge can approve next
        return True
    
    def replace_deliver_info_default(self, cr, uid, ids, context=None):
        
        so = self.browse(cr, uid, ids[0], context=context)
        user_id = so.user_id.id
        
        value = self._default_deliver_info(cr, user_id, context=context)
        record = so.api_id
        if record:
            if record.deliver_name:
                value.update({'deliver_name': record.deliver_name})
            if record.deliver_city_id:
                value.update({'deliver_city_id': record.deliver_city_id.id})
            if record.deliver_company_name:
                value.update({'deliver_company_name': record.deliver_company_name})
            if record.deliver_tel:
                value.update({'deliver_tel': record.deliver_tel})
            if record.deliver_address:
                value.update({'deliver_address': record.deliver_address})
                
        self.write(cr, uid, so.id, value, context=context)
        return True
        
    def replace_deliver_info_df(self, cr, uid, ids, context=None):
        
        so = self.browse(cr, uid, ids[0], context=context)
        partner = so.partner_id
        drop_shopping = (not so.is_drop_shopping)
        
        self.write(cr, uid, so.id, {
            'deliver_name': partner.name,
            'deliver_tel': partner.phone or partner.mobile or '',
            'deliver_address': partner.street or '',
            'deliver_company_name': partner.code or '-',
            'is_drop_shopping': drop_shopping,
            'deliver_city_id': False,
        }, context=context)
        
        return True

    def set_to_manual(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'create_type': 'manual'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        for sale in self.browse(cr, uid, ids, context=context):
            if all([pick.state in ['assigned', 'confirmed', 'draft'] for pick in sale.picking_ids]):
                for pick in sale.picking_ids:
                    if pick.printed:
                        raise osv.except_osv('Error', u"出库单已经打印，请先联系仓库，取消发货单")
                    else:
                        wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_cancel', cr)
        return super(sale_order, self).action_cancel(cr, uid, ids, context=context)

    def oepnerp_form_view(self, cr, uid, ids, context=None):
        return{
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': self._inherit,
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
        }

    def _prepare_order_picking(self, cr, uid, order, context=None):
        res = super(sale_order, self)._prepare_order_picking(cr, uid, order, context=context)
        res.update({
            'location_id': order.shop_id.warehouse_id.lot_stock_id.id,
            'carrier_id': order.yks_carrier_id and order.yks_carrier_id.id or False,
            'carrier_tracking_ref': order.yks_carrier_tracking,
            'receive_user': order.receive_user,
            'receive_phone': order.receive_phone,
            "receiver_district": order.receiver_district,
            'receive_address': order.receive_address,
            'receiver_city_id': order.receiver_city_id and order.receiver_city_id.id,
            'receiver_state_id': order.receiver_state_id and order.receiver_state_id.id,
            'deliver_name': order.deliver_name,
            'deliver_city_id': order.deliver_city_id.id,
            'deliver_company_name': order.deliver_company_name,
            'deliver_tel': order.deliver_tel,
            'deliver_address': order.deliver_address,
            'receiver_zip': order.receiver_zip,
            'carrier_id': order.carrier_id and order.carrier_id.id or False,
            'need_express_count': order.need_express_count or 0,
            'unneed_express': order.unneed_express,
        })
        return res

    def reget_order(self, cr, uid, ids, context=None):
        api_obj = self.pool.get('sync.api')
        so = self.browse(cr, uid, ids[0], context=context)
        if so.api_id and so.platform_so_id:
            context.update({'default_ds_partner': so.partner_id})
            data = api_obj.reget_order(cr, uid, so.api_id, so.platform_so_id, context=context)
            if data:
                data.update({
                    'order_line': [(5, ), ] + data['order_line'],
                    'user_id': data.get('user_id') or so.user_id.id,
                    'shop_id': so.shop_id.id,
                })
                self.write(cr, uid, so.id, data, context=context)
        return True
    
    def rush_platform_so_state(self, cr, uid, ids, context=None):
        _logger.info('Start rush_platform_so_state')
        api_obj = self.pool.get('sync.api')
        for so in self.browse(cr, uid, ids, context=context):
            api = so.api_id
            platform_so_id = so.platform_so_id
            if api and platform_so_id:
                new_state = api_obj.get_one_status(cr, uid, platform_so_id, api, context=context)
                if new_state:
                    if new_state != so.platform_so_state:
                        self.write(cr, uid, so.id, {'platform_so_state': new_state}, context=context)
                        _logger.info('rush_platform_so_state OK %s' % so.name)
                    else:
                        _logger.info('rush_platform_so_state Status not change, %s' % so.name)
        _logger.info('End rush_platform_so_state')
        return True
    
    def schedule_rush_platform_so_state(self, cr, uid, days=90, limit=100, context=None):
        _logger.info("schedule_rush_platform_so_state Start")
        use_new_cursor = True
        try:
            if use_new_cursor:
                cr = pooler.get_db(cr.dbname).cursor()
                self._rush_platform_so_state(cr, uid, days=days, limit=limit, context=None)
            if use_new_cursor:
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
        _logger.info("schedule_rush_platform_so_state End")
        return True
    
    def _rush_platform_so_state(self, cr, uid, days=90, limit=100, context=None):
        """
        @days: 平台最大可查询天数
        TODO: 取消limit限制，分多次例如每次 len(todo_ids） =  50 来提交数据
        """
        _logger.info('Start _rush_platform_so_state')
        
        if context is None:
            context = {}
        api_obj = self.pool.get('sync.api')
        ok_api = api_obj.get_connection_ok_api(cr, uid, None, context=context)
            
        start_time = time_ago(24 * days)
        ids = self.search(cr, uid, [('create_date', '>', start_time),
                                           ('platform_so_state', 'not in', Platform_End_Status),
                                           ('api_id', '!=', False),
                                           ('state', '!=', 'cancel')], limit=limit, order='id')
        datas = self.read(cr, uid, ids, ['api_id'], context=context, load='_classic_write')
        todo_ids = [d['id'] for d in datas if d['api_id'] in ok_api]

        _logger.info('schedule_rush_platform_so_state todo_ids %s' % todo_ids)
        self.rush_platform_so_state(cr, uid, todo_ids, context=context)
        
        _logger.info('End _rush_platform_so_state')
        return True

    def onchange_yks_type(self, cr, uid, ids, yks_type, context=None):
        res = {'value': {}}
        if ids and yks_type == 'offline':
            name = self.read(cr, uid, ids[0], ['name'])['name']
            res['value'].update({'platform_so_id': name})
        if yks_type == 'online':
            res['value'].update({'platform_so_id': ''})
        return res
    
    def sale_man_approve_check(self, cr, uid, ids, context=None):
        def asterisk_init(s):
            s = s or ''
            return r'*' in s
        
        self.check_stock_enough(cr, uid, ids, context=context)
        
        so = self.browse(cr, uid, ids[0], context=context)
        todo = [so.receive_user, so.receive_address, so.receive_phone]
        if filter(asterisk_init, todo):
            raise osv.except_osv(_('Error!'), _(u'收货信息有 * 内容，请补充完整'))
        if not so.platform_so_id:
            raise osv.except_osv(_('Error!'), _(u'线上订单“交易编号”为必填，如果是线下订单，请把“报价单编号”复制到“交易编号”'))
        if 'Error_Sku' in [l.product_id.default_code for l in so.order_line]:
            raise osv.except_osv(_('Error!'), _(u'有错误的SKU未处理，请点击按钮 设为手工订单 后修正！'))
        if not so.section_id or not so.user_id:
            raise osv.except_osv(_('Error!'), _(u'请在“其他信息”中完善“业务员”和“销售团队”'))
        if not all([so.deliver_name, so.deliver_tel, so.deliver_address]):
            raise osv.except_osv(_('Error!'), _(u'请补充发货人，发货电话，发货地址信息'))
        if so.need_express_count < 1 and not so.unneed_express:
            raise osv.except_osv(_('Error!'), _(u'快递单数量小于1，如果不需发快递，请勾选 无需快递'))
        if so.sale_model != 'normal' and so.shop_id.id == 1:
            raise osv.except_osv(_('Error!'), _(u'直邮订单，请勿选择深圳仓库发货！'))
        return True
    
    def sale_man_approve(self, cr, uid, ids, context=None):
        self.sale_man_approve_check(cr, uid, ids, context=context)
        sol_obj = self.pool.get('sale.order.line')
        
        for so in self.browse(cr, uid, ids, context=context):
            sol_obj.write(cr, uid, [l.id for l in so.order_line], {'date_order': so.date_order})
            wf_service.trg_validate(uid, 'sale.order', so.id, 'quotation_sent', cr)
        True

    def account_approve(self, cr, uid, ids, context=None):
        for so_id in ids:
            wf_service.trg_validate(uid, 'sale.order', so_id, 'account_approve', cr)
        return True
    
    def sale_charge_approve(self, cr, uid, ids, context=None):
        """
        """
        assert len(ids) == 1
        pick_obj = self.pool.get('stock.picking')

        self.confirm_rdo(cr, uid, ids, context=context)
        res = self.action_button_confirm(cr, uid, ids, context=context)

        so = self.browse(cr, uid, ids[0], context=context)
        pick_ids = [x.id for x in so.picking_ids]
        if pick_ids:
            pick_obj.action_assign(cr, uid, pick_ids)

        return res
        
    def action_ship_end(self, cr, uid, ids, context=None):
        res = super(sale_order, self).action_ship_end(cr, uid, ids, context=context)
        return res and self.write(cr, uid, ids, {'state': 'shipped'})
    
    def make_sign_in(self, cr, uid, ids, context=None):
        for so_id in ids:
            wf_service.trg_validate(uid, 'sale.order', so_id, 'sign_in', cr)
        return True
    
    def return_draft(self, cr, uid, ids, context=None):
        for so in self.browse(cr, uid, ids, context=context):
            if so.state in ['sent', 'wait_account']:
                wf_service.trg_validate(uid, 'sale.order', so.id, 'back_draft', cr)
                self.write(cr, uid, so.id, {'state': 'draft'})
        return True
    
    def reset_wkf(self, cr, uid, ids, context=None):
        for so in self.browse(cr, uid, ids, context=None):
            if so.state == 'draft':
                wf_service.trg_delete(uid, 'sale.order', so.id, cr)
                wf_service.trg_create(uid, 'sale.order', so.id, cr)
        return True
    
    def onchange_sale_model(self, cr, uid, ids, sale_model, carrier_id, need_express_count, context=None):
        value = {}
        if sale_model == 'zy':
            value.update({'need_express_count': 0, 'carrier_id': False})
        if sale_model == 'normal':
            value.update({'need_express_count': need_express_count or 1, 'carrier_id': carrier_id})
        return {'value': value}
    
    def sign_in_by_express(self, cr, uid, ids, context=None):
        todo_ids = []
        for so in self.browse(cr, uid, ids, context=context):
            ok = True
            for pick in so.picking_ids:
                for express in pick.express_ids:
                    if express.state != '3':
                        ok = False
            if ok:
                todo_ids.append(so.id)
        self.make_sign_in(cr, uid, todo_ids, context=context)
        return True
    
    def auto_sign_in(self, cr, uid, context=None):
        _logger.info('Start auto_sign_in')
        
        ids = self.search(cr, uid, [('state', '=', 'shipped')], context=context)
        self.sign_in_by_express(cr, uid, ids, context=None)
        
        _logger.info('End auto_sign_in')
        return True
    
    def onchange_receive_address(self, cr, uid, ids, eceive_address, context=None):
        warning = {
            'title': _(u'注意!'),
            'message': _(u'完整地址=省+城市+区域+地址，修改收货地址，请一定将 省 城市 区域 修改一致，否则会打印错误的快递信息。')
        }
        return {'warning': warning}
    
    def express_post(self, cr, uid, ids, context=None):
        pick_obj = self.pool.get('stock.picking')
        so = self.browse(cr, uid, ids[0], context=context)
        for pick in so.picking_ids:
            if pick.express_id:
                pick_obj.express_post_to_platform(cr, uid, [pick.id, ], context=context)
                return True
        return True
    
    def onchage_unneed_express(self, cr, uid, ids, unneed_express, context=None):
        value = {}
        if unneed_express:
            value.update({"carrier_id": False, "need_express_count": 0})
        return {'value': value}
    
    def check_stock_enough(self, cr, uid, ids, context=None):
        """
        check stock_qty_a, is enough for sale order
        """
        wrsa_obj = self.pool.get('wms.report.stock.available')
        message = ''
        mess_line = u"<[%s]可用数量%s,订单数量%s> "

        for so in self.browse(cr, uid, ids, context=context):
            if so.need_split_picking:
                continue
            
            location_id = so.shop_id.warehouse_id.lot_stock_id.id
            for line in so.order_line:
                product = line.product_id
                if product.type != 'product':
                    continue
                else:
                    if product.supply_method == 'produce':
                        bom_lines = product.bom_ids and product.bom_ids[0].bom_lines
                        for bline in bom_lines:
                            need_sku = bline.product_id.default_code
                            need_qty = line.product_uom_qty * bline.product_qty
                            info_qty = wrsa_obj.get_qty(cr, uid, bline.product_id.id, location_id, context=context)
                            product_qty_a = info_qty['product_qty_a']
                            if product_qty_a < need_qty:
                                message += mess_line % (need_sku, product_qty_a, need_qty)
                    else:
                        info_qty = wrsa_obj.get_qty(cr, uid, line.product_id.id, location_id, context=context)
                        product_qty_a = info_qty['product_qty_a']
                        if product_qty_a < line.product_uom_qty:
                            message += mess_line % (line.product_id.default_code, product_qty_a, line.product_uom_qty)
                            
        if message:
            raise osv.except_osv(u'库存可用数量不足，请勾选 需要拆分出库', message)
            
        return True
    
    #===========================================================================
    # def adjustable_goods(self, cr, uid, ids, context=None):
    #         """代发货"""
    #         so = self.browse(cr, uid, ids[0], context=context)
    #         if context is None:
    #             context = {}
    #         
    #         ctx = context.copy()
    #         ctx.update({
    #             'active_model': self._name,
    #             'active_ids': ids,
    #             'active_id': len(ids) and ids[0] or False,
    #             'default_carrier_id': so.carrier_id and so.carrier_id.id or False,
    #             'default_location_dest_id': so.shop_id.warehouse_id.lot_stock_id.id,
    #             'default_sale_id': so.id,
    #         })
    #         return {
    #             'name': u'从其他仓库调货',
    #             'view_type': 'form',
    #             'view_mode': 'form',
    #             'res_model': "sale.adjustable.goods",
    #             'type': 'ir.actions.act_window',
    #             'target': 'new',
    #             'context': ctx,
    #             'nodestroy': True,
    #         }
    #===========================================================================
            
    def create_rdo(self, cr, uid, ids, context=None):
        rdo_obj = self.pool.get('requirement.distribution.order')
        rdo_id = rdo_obj.create(cr, uid, {'sale_id': ids[0]})
        self.write(cr, uid, ids[0], {'rdo_id': rdo_id}, context=context)
        return True
    
    def confirm_rdo(self, cr, uid, ids, context=None):
        rdo_obj = self.pool.get('requirement.distribution.order')
        so = self.browse(cr, uid, ids[0], context=context)
        if so.rdo_id and so.rdo_id.state == 'draft':
            rdo_obj.action_confirm(cr, uid, so.rdo_id.id, context=context)
        return True
    
    
sale_order()


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
    
    def _auto_init(self, cr, context=None):
        cr.execute('''
            select
              sol.id,
              so.date_order
            from
              sale_order_line as sol
              left join sale_order as so on(sol.order_id = so.id)
            where
              sol.date_order is null and so.date_order is not null;
        ''')
        for i in cr.fetchall():
            cr.execute('''update sale_order_line set (date_order)=('%s') where id = %s ''' % (i[1], i[0]))
        return super(sale_order_line, self)._auto_init(cr, context=context)

    _columns = {
        'platform_sol_id': fields.char(u'平台明细ID', size=50, help=u"例如淘宝OID"),
        'platform_so_id': fields.related('order_id', 'platform_so_id', type='char', string=u'交易编号', readonly=True),
        'date_order': fields.date(u'日期'),
    }
    
sale_order_line()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: