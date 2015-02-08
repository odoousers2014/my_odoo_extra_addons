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

from openerp.addons.report_webkit.report_helper import WebKitHelper


def embed_logo_by_company(self, company_id, width=0, height=0):
    company = self.pool.get('res.company').browse(self.cursor,
                                                  self.uid, company_id)
    if not company.logo:
        return u''
    img, type = (company.logo, 'png')
    return self.embed_image(type, img, width, height)


WebKitHelper.embed_logo_by_company = embed_logo_by_company

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
