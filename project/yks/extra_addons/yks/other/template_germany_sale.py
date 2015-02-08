# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import  osv, fields
from openerp.tools.translate import _


class yks_germany_sale_template (osv.osv):
    _name = 'yks.germany.sale.template'
    _columns = {
        'create_date': fields.date('Create Date', readonly=True),
                
        'name': fields.char(_(u'DEST_NAME'), size=40, required=True,),
        'dest_department': fields.char(_(u'DEST_DEPARTMENT'), size=40),
        'dest_contact': fields.char(_(u'DEST_CONTACT'), size=40, required=0),
        'dest_street': fields.char(_(u'DEST_STREET'), size=100, required=1),
        'dest_place': fields.char(_(u'DEST_PLACE'), size=40, required=0),
        'dest_house_nr': fields.integer(_(u'DEST_HOUSE_NR'), required=1),
        'dest_box_nr': fields.char(_(u'DEST_BOX_NR'), size=8, required=0),
        'dest_zip_code': fields.char(_(u'DEST_ZIPCODE'), size=10, required=1),
        'dest_city': fields.char(_(u'DEST_CITY'), size=40, required=1),
        'dest_state': fields.char(_(u'DEST_STATE'), size=40, required=0),
        'dest_country': fields.char(_(u'DEST_COUNTRY'), size=2, required=1),
        'dest_phone': fields.char(_(u'DEST_PHONE'), size=20, required=1),
        'dest_mobile': fields.char(_(u'DEST_MOBILE'), size=20, required=0),
        'weight': fields.char(_(u'WEIGHT'), size=40, required=0),
        'description': fields.char(_(u'DESCRIPTION'), required=1, size=100),
        'category': fields.char(_(u'CATEGORY'), size=40, required=1),
        'non_delivery': fields.char(_(u'NON_DELIVERY'), size=40, required=1),
        'value': fields.float(_(u'VALUE'), required=1),
        'value_currency': fields.char(_(u'VALUE_CURRENCY'), size=3, required=1),
        'export_flage': fields.char(_(u'EXPORT_FLAG'), size=1, required=1),
        'customer_reference': fields.char(_(u'CUSTOMER_REFERENCE'), size=128, required=1),
        'number_of_items': fields.float(_(u'NUMBER_OF_ITEMS'), size=6, required=1),
        'value_of_items': fields.float(_(u'VALUE_OF_ITEMS'), size=11, required=1),
        'currence': fields.char(_(u'CURRENCY'), size=3, required=1),
        'item_description': fields.char(_(u'ITEM_DESCRIPTION'), size=30, required=1),
        'netto_weight': fields.float(_(u'NETTO_WEIGHT'), size=18, required=0),
        'hs_tarrif_code': fields.char(_(u'HS_TARRIF_CODE'), size=6, required=1),
        'origin_of_goods': fields.char(_(u'ORIGIN_OF_GOODS'), size=2, required=1),
        'bpost': fields.char(_(u'Bpost'), size=40, required=0),
        
        'cn_name': fields.char(_(u'cn_name'), size=20, required=0),
        'cn_street': fields.char(_(u'cn_street'), size=20, required=0),
        'cn_zip': fields.char(_(u'cn_zip'), size=20, required=0),
        'cn_phone': fields.char(_(u'cn_phone'), size=20, required=0),
        'cn_date': fields.char(_(u'cn_date'), size=20, required=0),
        'cn_product': fields.char(_(u'cn_product'), size=120, required=0),
        'need_receipt': fields.boolean(_(u'need_receipt')),
        'new_newspaper': fields.boolean(_(u'new_newspaper')),
        'need_bage': fields.boolean(_(u'need_bage'),),
    }
    _defaults = {
        'export_flage': '1',
        'value_currency': 'EUR',
        'currence': 'EUR',
        'non_delivery': 'RTS',
    }
    
yks_germany_sale_template()

##############################################################################
