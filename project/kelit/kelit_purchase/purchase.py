# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Damiano Falsanisi <damiano.falsanisi@elico-corp.com>, Jon Chow <jon.chow@elico-corp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time
import pytz
from openerp import SUPERUSER_ID
from datetime import datetime
from openerp.osv import fields, osv
from openerp import pooler
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from dateutil.relativedelta import relativedelta

class purchase_order(osv.osv):
    _inherit='purchase.order'
    _columns={
        'incoterm_id': fields.many2one('stock.incoterms', 'Incoterm'),
        #jon warehouse_id required=True
        'warehouse_id': fields.many2one('stock.warehouse', 'Destination Warehouse', required=True),
        #change date_order field type to datetime
        'date_order':fields.datetime('Order Date', required=True, states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)]}, select=True, help="Date on which this document has been created."),
    }
    _defaults={
        'date_order': lambda *a: time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    }
purchase_order()

######change some function is used the date_order
from openerp.addons.purchase.purchase import purchase_order as PO

def date_to_datetime(self, cr, uid, userdate, context=None):
    #datime --> date
    userdate=userdate[:10]
    
    user_date = datetime.strptime(userdate, DEFAULT_SERVER_DATE_FORMAT)
    if context and context.get('tz'):
        tz_name = context['tz']
    else:
        tz_name = self.pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz']
    if tz_name:
        utc = pytz.timezone('UTC')
        context_tz = pytz.timezone(tz_name)
        user_datetime = user_date + relativedelta(hours=12.0)
        local_timestamp = context_tz.localize(user_datetime, is_dst=False)
        user_datetime = local_timestamp.astimezone(utc)
        return user_datetime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    return user_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    
    
setattr(PO,'date_to_datetime', date_to_datetime)
#####

from openerp.addons.purchase.purchase import purchase_order_line as POL
def _get_date_planned(self, cr, uid, supplier_info, date_order_str, context=None):
    """Return the datetime value to use as Schedule Date (``date_planned``) for
       PO Lines that correspond to the given product.supplierinfo,
       when ordered at `date_order_str`.

       :param browse_record | False supplier_info: product.supplierinfo, used to
           determine delivery delay (if False, default delay = 0)
       :param str date_order_str: date of order, as a string in
           DEFAULT_SERVER_DATE_FORMAT
       :rtype: datetime
       :return: desired Schedule Date for the PO line
    """
    ##datime --> date
    date_order_str=date_order_str[:10]
    
    supplier_delay = int(supplier_info.delay) if supplier_info else 0
    return datetime.strptime(date_order_str, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=supplier_delay)

setattr(POL,'_get_date_planned', _get_date_planned)

# When Creating a PO, set the default PO company ID = the User's company ID.
#class purchase_order(osv.osv):
#    _inherit='purchase.order'
#    
#    def _get_company(self,cr,uid,context=None):
#        user_obj=self.pool.get('res.users')
#        user=user_obj.browse(cr,uid,uid)
#        return user.company_id and  user.company_id.id or False
#    
#    _defaults={
#        'company_id': lambda self,cr,uid,context: self._get_company(cr,uid,context=context)             
#    }
# 
#purchase_order()
