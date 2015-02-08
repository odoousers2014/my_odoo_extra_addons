#-*- coding:utf-8 -*-

from osv import osv, fields


class express_batch_create(osv.osv_memory):
    _name = 'express.batch.create'
    _columns = {
        'name': fields.char(u'Name', size=32),
        'carrier_id': fields.many2one('delivery.carrier', u'快递公司'),
        'prefix': fields.char(u'单号前缀', size=24),
        'amount': fields.float(u'快递费用'),
        'start_number': fields.integer(u'开始号码'),
        'end_number': fields.integer(u'结束号码'),
        #'select_count':fields.integer(u'选中数量'),
    }

    def express_create(self, cr, uid, ids, context=None):
        """批量增加快递信息"""
        express_obj = self.pool.get('express.express')
        info = self.browse(cr, uid, ids[0], context=context)
        num = info.end_number - info.start_number
        tmp = ''
        for i in range(num):
            tmp = info.prefix + str(info.start_number + i)
            express_obj.create(cr, uid, {
                    'delivery_carrier_id': info.carrier_id.id,
                    'name': tmp,
                    "amount": float(info.amount),
                }, context=context)
        
        return True
         
express_batch_create()

############################################