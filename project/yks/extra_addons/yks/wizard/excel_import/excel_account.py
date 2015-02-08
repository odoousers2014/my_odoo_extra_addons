#-*-coding:utf-8 -*-

import base64
from openerp.osv import  osv
from xlrd import xldate_as_tuple


class excel_collection_voucher(osv.osv_memory):
    """"""
    _inherit = "excel.base"
    
    def apply(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res = super(excel_collection_voucher, self).apply(cr, uid, ids, context=context)
        wizard = self.browse(cr, uid, ids[0], context=context)
        if wizard.model == 'collection_voucher':
            res_ids = self.create_collection_voucher(cr, uid, wizard, context=context)
            res.update({
                'name': u'收款记录',
                'view_type': 'form',
                "view_mode": 'tree,form',
                'res_model': 'collection.voucher',
                "domain": [('id', 'in', res_ids)],
                'type': 'ir.actions.act_window',
            })

        return res
    
    def create_collection_voucher(self, cr, uid, wizard, context=None):
        
        voucher_obj = self.pool.get('collection.voucher')
        title_data = self.parse_title_data(file_contents=base64.decodestring(wizard.file))
        
        res_ids = []
        for data in title_data['data']:
            
            trans_time_arr = xldate_as_tuple(data['trans_time'], 0)
            if len(trans_time_arr) == 6:
                trans_time = '%s-%s-%s %s:%s:%s' % trans_time_arr
            else:
                trans_time = None
                
            name = data.get('name', '').strip()
            platform_so_id = data.get('platform_so_id', '').strip()
            voucher_id = voucher_obj.create(cr, uid, {
                'name': name,
                'platform_so_id': platform_so_id,
                'amount_in': float(data.get('amount_in', 0)),
                'amount_out': float(data.get('amount_out', 0)),
                'payer_account': data.get('payer_account'),
                'note': data.get('note'),
                'trans_time': trans_time,
            })
            res_ids.append(voucher_id)
            
        return res_ids
    
excel_collection_voucher()

##############################################