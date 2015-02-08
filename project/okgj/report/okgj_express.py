# -*- coding: utf-8 -*-
##############################################################################
#
#   Copyright (c) 2011 Camptocamp SA (http://www.camptocamp.com)
#   @author Nicolas Bessi, Vincent Renaville, Guewen Baconnier
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

from openerp.report import report_sxw
from openerp import pooler


class okgj_express(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(okgj_express, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'translate_number': self._translate_number,
        })
    def _translate_number(self, nu=0.0):
        """
        """
        money_number={
            '.': '.',
            '0':u'零',
            '1':u'壹',
            '2':u'贰',
            '3':u'叁',
            '4':u'肆',
            '5':u'伍',
            '6':u'陆',
            '7':u'柒',
            '8':u'捌',
            '9':u'玖'
        }
        res=''
        for i in str(float(nu)):
            res+=money_number[i]
        return res

report_sxw.report_sxw('report.okgj.express.uc',
                      'sale.order',
                      'addons/okgj/report/okgj_express.rml',
                      parser=okgj_express)

#===============================================================================
# report_sxw.report_sxw('report.okgj.webkit.express.uc',
#                       'sale.order',
#                       'addons/okgj/report/okgj_express.mako',
#                       parser=okgj_express,
#                       header="Base Sample")
#===============================================================================


##_________end__________##
