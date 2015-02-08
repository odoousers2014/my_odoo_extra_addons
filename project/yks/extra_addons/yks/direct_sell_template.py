# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import  osv, fields
from openerp.tools.translate import _


class direct_sell_template(osv.osv):
    _name = 'direct.sell.template'
    _columns = {
        'so_id': fields.many2one('sale.order', 'Sale Order'),
        'user_id': fields.related('so_id', 'user_id', type='many2one', relation='res.users', string="Seller", readonly=True),
        'create_date': fields.date('Create Date', readonly=True),
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                                   ('approve', 'Approve'), ('done', 'Done')], 'Status'),
        'send_mobile': fields.char('SEND_MOBILE', size=20),
        'name': fields.char(_(u'DEST_NAME'), size=40, required=False,),
        'dest_department': fields.char(_(u'DEST_DEPARTMENT'), size=40,),
        'dest_contact': fields.char(_(u'DEST_CONTACT'), size=40, required=False),
        'dest_street': fields.char(_(u'DEST_STREET'), size=100, required=False),
        'dest_place': fields.char(_(u'DEST_PLACE'), size=40, required=False),
        'dest_house_nr': fields.char(_(u'DEST_HOUSE_NR'), size=30, required=False),
        'dest_box_nr': fields.char(_(u'DEST_BOX_NR'), size=8, required=False),
        'dest_zip_code': fields.char(_(u'DEST_ZIPCODE'), size=10, required=False),
        'dest_city': fields.char(_(u'DEST_CITY'), size=40, required=False),
        'dest_state': fields.char(_(u'DEST_STATE'), size=40, required=False),
        'dest_country': fields.char(_(u'DEST_COUNTRY'), size=2, required=False),
        'dest_phone': fields.char(_(u'DEST_PHONE'), size=20, required=False),
        'dest_mobile': fields.char(_(u'DEST_MOBILE'), size=20, required=False),
        'weight': fields.float(_(u'WEIGHT'), digits=(4, 3), required=False),
        'description': fields.char(_(u'DESCRIPTION'), required=False, size=100),
        'category': fields.char(_(u'CATEGORY'), size=40, required=False),
        'non_delivery': fields.char(_(u'NON_DELIVERY'), size=40, required=False),
        'value': fields.float(_(u'VALUE'), required=False),
        'value_currency': fields.char(_(u'VALUE_CURRENCY'), size=3, required=False),
        'export_flage': fields.char(_(u'EXPORT_FLAG'), size=1, required=False),
        'customer_reference': fields.char(_(u'CUSTOMER_REFERENCE'), size=128, required=False),
        'number_of_items': fields.float(_(u'NUMBER_OF_ITEMS'), size=6, required=False),
        'value_of_items': fields.float(_(u'VALUE_OF_ITEMS'), size=11, required=False),
        'currence': fields.char(_(u'CURRENCY'), size=3, required=False),
        'item_description': fields.char(_(u'ITEM_DESCRIPTION'), size=30, required=False),
        'netto_weight': fields.float(_(u'NETTO_WEIGHT'), digits=(4, 3), required=False),
        'hs_tarrif_code': fields.char(_(u'HS_TARRIF_CODE'), size=6, required=False),
        'origin_of_goods': fields.char(_(u'ORIGIN_OF_GOODS'), size=2, required=False),
        'bpost': fields.char(_(u'Bpost'), size=40, required=False),

        'cn_name': fields.char(_(u'cn_name'), size=20, required=False),
        'cn_street': fields.char(_(u'cn_street'), size=120, required=False),
        'cn_city': fields.char(_(u'cn_city'), size=20, required=False),
        'cn_state': fields.char(_(u'cn_state'), size=20, required=False),
        'cn_zip': fields.char(_(u'cn_zip'), size=20, required=False),
        'cn_phone': fields.char(_(u'cn_phone'), size=20, required=False),
        'cn_date': fields.char(_(u'cn_date'), size=20, required=False),
        'cn_product': fields.char(_(u'cn_product'), size=120, required=False),
        'need_receipt': fields.boolean(_(u'need_receipt'),),
        'need_newspaper': fields.boolean(_(u'need_newspaper'),),
        'need_bage': fields.boolean(_(u'need_bage'),),
        'note': fields.char(_(u'Note'), size=40),

    }
    _defaults = {
        'state': 'draft',
        'export_flage': '1',
        'value_currency': 'EUR',
        'currence': 'EUR',
        'non_delivery': 'RTS',
        'category': 'GIFT',
        'dest_house_nr': '0',
    }

    _sql_constraints = [
        ('so_uniq', 'unique (so_id)', u'销售模板的订单编号不能重复'),
    ]

    def unlink(self, cr, uid, ids, context=None):
        for info in self.read(cr, uid, ids, ['state']):
            if info['state'] in ['done', 'approve']:
                raise osv.except_osv(_('Error!'), _(u'不能删除 完成 或 批准的 模板'))

        return super(direct_sell_template, self).unlink(cr, uid, ids, context=context)

    def confirm_check(self, cr, uid, ids, context=None):

        for a in self.browse(cr, uid, ids, context=context):
            #print   '>>>>>>>',  a.netto_weight , a.weight, a.netto_weight > a.weight

            if not a.name:
                raise osv.except_osv(_('Error!'), _(u'收货人不能为空'))
            if not a.dest_street:
                raise osv.except_osv(_('Error!'), _(u'收货街道地址'))
            if not a.dest_house_nr:
                raise osv.except_osv(_('Error!'), _(u'收件人门牌号码'))
            if not a.dest_zip_code:
                raise osv.except_osv(_('Error!'), _(u'收货邮编'))
            if not a.dest_city:
                raise osv.except_osv(_('Error!'), _(u'收货城市'))
            if not a.dest_country:
                raise osv.except_osv(_('Error!'), _(u'收货国家'))
            if not a.dest_phone:
                raise osv.except_osv(_('Error!'), _(u'收货电话'))
            #===================================================================
            # if not a.weight:
            #     raise osv.except_osv(_('Error!'),_(u'总重量'))
            #===================================================================
            if not a.description:
                raise osv.except_osv(_('Error!'), _(u'物品描述'))
            if not a.category:
                raise osv.except_osv(_('Error!'), _(u'邮寄类目'))
            if not a.non_delivery:
                raise osv.except_osv(_('Error!'), _(u'退运方式'))
            if not a.value:
                raise osv.except_osv(_('Error!'), _(u'价值'))
            if not a.value_currency:
                raise osv.except_osv(_('Error!'), _(u'货币'))
            if not a.export_flage:
                raise osv.except_osv(_('Error!'), _(u'出口类型'))
            if not a.customer_reference:
                raise osv.except_osv(_('Error!'), _(u'快递备注'))
            if not a.number_of_items:
                raise osv.except_osv(_('Error!'), _(u'单项物品数目'))
            if not a.value_of_items:
                raise osv.except_osv(_('Error!'), _(u'单项物品总价值'))
            if not a.currence:
                raise osv.except_osv(_('Error!'), _(u'货币单位'))
            if not a.item_description:
                raise osv.except_osv(_('Error!'), _(u'ITEM物品描述'))
            if not a.netto_weight:
                raise osv.except_osv(_('Error!'), _(u'物品净重'))
            if  a.netto_weight > a.weight:
                raise osv.except_osv(_('Error!'), _(u'物品净重 不能大于之前重量'))
            if not a.hs_tarrif_code:
                raise osv.except_osv(_('Error!'), _(u'海关代码'))
            if not a.origin_of_goods:
                raise osv.except_osv(_('Error!'), _(u'物品原产地'))

        return True

    def action_confirm(self, cr, uid, ids, context=None):
        self.confirm_check(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'confirm'})
        return True

    def action_approve(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, record.id, {
                'state': 'approve',
            })
        return True

    def action_done(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if  not record.bpost:
                raise osv.except_osv(_('Error!'), _(u'完成状态 回执单 不能为空'))
            self.write(cr, uid, record.id, {
                'state': 'done',
            })
        return True

direct_sell_template()

#########################################################################
