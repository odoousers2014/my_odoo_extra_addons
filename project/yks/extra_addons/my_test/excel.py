# -*- coding: utf-8 -*-
##############################################################################

from openerp import tools
from openerp.osv import osv, fields
import time, xlrd, base64


class wizard_excel(osv.osv_memory):
    _name = 'wizard.excel'
    _columns = {
        'field': fields.binary(u'excel文件', filters='*.xls'), 
    }
wizard_excel()
    
    
    















#############################################