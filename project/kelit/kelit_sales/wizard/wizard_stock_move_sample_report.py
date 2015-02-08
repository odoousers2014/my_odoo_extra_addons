# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#     Jon Chow <jon.chow@elico-corp.com>
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
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from datetime import timedelta,datetime
 
class  wizard_stock_move_sample_report(osv.osv):
    _name = 'wizard.stock.move.sample.report'
    def _get_frist_day(self):
        
        t=datetime.strptime(time.strftime('%Y-%m-01 00:00:01'), DEFAULT_SERVER_DATETIME_FORMAT) 
        t= t + timedelta(hours=-8)
        return t.strftime(DEFAULT_SERVER_DATETIME_FORMAT, )
        
    _columns = {
        'name': fields.char('name', size=32),
        'start_date': fields.datetime('Start Date', ),
        'end_date': fields.datetime('End Date', ),
    }
    _defaults = {
        'start_date': lambda self, cr, uid, c:self._get_frist_day(),
        'end_date':  lambda *a: time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        
    }

    def do_report(self, cr, uid, ids, context=None):
        
        wizard = self.browse(cr, uid, ids[0])
        move_pool = self.pool.get('stock.move')
        move_ids =move_pool.search(cr, uid,
            [('is_sample','=',True),
             ('state','=','done'),
             #need this?   ('location_dest_it.usage','=','customer'),
             ('date','>',wizard.start_date),
             ('date','<',wizard.end_date)], order='picking_id')
        
        print 'move_ids', move_ids, len(move_ids)
        if not move_ids:
             raise osv.except_osv(_('Error'), _('not found any sample SOL'))

        datas = {
            'model': 'stock.move',
            'ids': move_ids,
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'stock_move_sample',
            'datas': datas,
            'context': {'sample_move_ids': move_ids},
        }
        

 # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
 
