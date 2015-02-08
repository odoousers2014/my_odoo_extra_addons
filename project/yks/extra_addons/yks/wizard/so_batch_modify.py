# -*- coding: utf-8 -*-
##############################################################################
from osv import osv, fields


class so_batch_modify(osv.osv_memory):
    _name = 'so.batch.modify'
    _columns = {
        'name': fields.char(u'Name', size=32,),
        'carrier_id': fields.many2one('delivery.carrier', u'快递方式', ),
        'prefix': fields.char(u'前缀', size=24),
        'start_number': fields.integer(u'开始号码'),
        'end_number': fields.integer(u'结束号码'),
        'select_count': fields.integer(u'选中记录数量'),
    }
    _defaults = {
        "select_count": lambda self, cr, uid, c: len(c.get('active_ids', [])),
    }
    
    def check(self, cr, uid, ):
        return True
    
    def apply(self, cr, uid, ids, context=None):
        so_ids = context.get('active_ids')
        so_obj = self.pool.get('sale.order')
        wizard = self.browse(cr, uid, ids[0], context=context)
        n = 0
        for so in so_obj.browse(cr, uid, so_ids, context=context):
            track = ''
            if wizard.prefix:
                track = wizard.prefix + str(wizard.start_number + n)
            so_obj.write(cr, uid, so.id, {
                'yks_carrier_id': wizard.carrier_id.id,
                'yks_carrier_tracking': track,
            })
            n += 1

        return True
so_batch_modify()

##############################################################