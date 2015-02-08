# -*- coding: utf-8 -*-
##############################################################################
from osv import osv, fields
from anjuke import pinyin

converter = pinyin.Converter()


def _PINYIN(hanzi):
    res = False
    if hanzi:
        res = converter.convert(hanzi)
    return res


class so_to_dst(osv.osv_memory):
    """
    dst :  direct.sell.template
    """
    _name = 'so.to.dst'
    _columns = {
        'name': fields.char('Name', size=32, ),
    }
    
    def create_dst(self, cr, uid, ids, context=None):
        so_pool = self.pool.get('sale.order')
        dst_pool = self.pool.get('direct.sell.template')
        so_ids = context.get('active_ids')
        
        dst_ids = []
        for so in so_pool.browse(cr, uid, so_ids, context=context):
            dest_country = so.receiver_state_id and so.receiver_state_id.country_id.code or ''
            customer_reference = 'YKS'
            if so.api_id:
                if so.api_id.type == 'taobao':
                    customer_reference += '-TMGJ'
                elif so.api_id.type == 'yhd':
                    customer_reference += '-YHD'
                    
            number_of_items = sum([l.product_uom_qty for l in so.order_line if l.product_id.type != 'service'])
            value_of_items = sum([l.price_subtotal for l in so.order_line])
            netto_weight = sum([l.product_id.weight_net * l.product_uom_qty for l in so.order_line if l.product_id.type != 'service'])
            origin_of_goods = so.order_line[0].product_id.place_production and so.order_line[0].product_id.place_production.code or ''
            cn_product = ';'.join([str(int(l.product_uom_qty)) + 'X' + l.product_id.name for l in so.order_line if l.product_id.type != 'service'])
            
            new_id = dst_pool.create(cr, uid, {
                'so_id': so.id,
                'name': _PINYIN(so.receive_user),
                 #  'dest_department':
                 #  'dest_contact':
                'dest_street': _PINYIN(so.receive_address),
                 #  'dest_place':
                 #  'dest_house_nr':
                 #  'dest_box_nr':
                'dest_zip_code': so.receiver_zip,
                'dest_city': _PINYIN(so.receiver_city_id and so.receiver_city_id.name),
                'dest_state': _PINYIN(so.receiver_state_id and so.receiver_state_id.name),
                'dest_country': dest_country,
                'dest_phone': so.receive_phone,
                # 'dest_mobile':
                # 'weight':
                # 'description':
                # 'category':
                # 'non_delivery':
                # 'value':
                # 'value_currency':
                # 'export_flage':
                 'customer_reference': customer_reference,
                 'number_of_items': number_of_items,
                 'value_of_items': value_of_items,
                # 'currence':
                # 'item_description':
                'netto_weight': netto_weight,
                # 'hs_tarrif_code':
                'origin_of_goods': origin_of_goods,
                # 'bpost':
                #
                'cn_name': so.receive_user,
                'cn_street': so.receive_address,
                'cn_city': so.receiver_city_id and  so.receiver_city_id.name,
                'cn_state': so.receiver_state_id and  so.receiver_state_id.name,
                'cn_zip': so.receiver_zip,
                'cn_phone': so.receive_phone,
                # 'cn_date' :
                'cn_product': cn_product,
                'need_receipt': True,
                'need_newspaper': True,
                'need_bage': True,
                             
            })
            dst_ids.append(new_id)
            
        return{
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'direct.sell.template',
            'domain': [('id', 'in', dst_ids)],
            'type': 'ir.actions.act_window',
        }

so_to_dst()

#=================================