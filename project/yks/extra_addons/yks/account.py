# -*- coding: utf-8 -*-
##############################################################################
from openerp.osv import osv, fields
#from openerp.tools.translate import _


class collection_voucher(osv.osv):
    _name = "collection.voucher"
    _columns = {
        "name": fields.char(u"支付流水", size=50, select=1, required=True),
        "platform_so_id": fields.char(u'交易编号', size=50, select=1, help=u"例如淘宝TID",),
        "state": fields.selection([('draft', u"草稿"), ('confirmed', u"已确认"), ('done', u"完成")], u"状态", required=True),
        "trans_time": fields.datetime(u"发生时间"),
        "payer_account": fields.char(u"对方帐号"),
        "amount_in": fields.float(u"收入"),
        "amount_out": fields.float(u"支出"),
        "note": fields.char("Note", size=30),
        "so_id": fields.many2one("sale.order", u"销售订单"),
        "payment": fields.related("so_id", 'payment', type="float", string="订单金额", readonly=True),
        "create_uid": fields.many2one("res.users", u"创建人"),
    }
    
    _defaults = {
        "state": 'draft',
    }
    
    _sql_constraints = [
         ('name_uniq', 'unique(name)', u'支付流水号必须唯一'),
    ]
    
    def unlink(self, cr, uid, ids, context=None):
        for r in self.browse(cr, uid, ids, context=context):
            if r.state != "draft":
                raise osv.except_osv('Error', u"非草稿状态不允许删除")
        
        return super(collection_voucher, self).unlink(cr, uid, ids, context=context)
    
    def catch_so(self, cr, uid, ids, context=None):
        so_obj = self.pool.get("sale.order")
        for r in self.browse(cr, uid, ids, context=context):
            if not r.so_id:
                #match the SO accord by platform_so_id or payment_number
                domain = ['|', ('platform_so_id', '=', r.platform_so_id), ('payment_number', '=', r.name)]
                so_ids = so_obj.search(cr, uid, domain, context=context, limit=1)
                if so_ids:
                    self.write(cr, uid, r.id, {'so_id': so_ids[0]})
        return True
    
    def action_confirm(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': "confirmed"})
        
    def action_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': "done"})
    
    def action_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': "draft"})
        
collection_voucher()


class wizard_voucher_catch_order(osv.osv_memory):
    _name = "wizard.voucher.catch.order"
    _columns = {
        "name": fields.char("Name", size=10,),
    }
    
    def apply(self, cr, uid, ids, context=None):
        
        voucher_obj = self.pool.get("collection.voucher")
        voucher_ids = context.get("active_ids")
        
        voucher_obj.catch_so(cr, uid, voucher_ids, context=context)
        
        return True
        

wizard_voucher_catch_order()
##########################################