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

from mako import exceptions
from openerp import addons, pooler, tools
from openerp.addons.report_webkit.report_helper import WebKitHelper
from openerp.addons.report_webkit.webkit_report\
    import WebKitParser, mako_template
from openerp.osv import fields, osv
from openerp.osv.osv import except_osv
from openerp.tools.translate import _
import os
import logging
_logger = logging.getLogger(__name__)


class res_partner(osv.osv):
    _inherit = 'res.partner'
    _name = 'res.partner'
    _columns = {
        'header_webkit': fields.many2one('ir.header_webkit', 'Webkit Head'),
        'header_image':  fields.many2one('ir.header_img',    'Webkit Image'),
    }

res_partner()


def embed_logo_by_partner(self, partner_id, width=0, height=0):
    partner = self.pool.get('res.partner').browse(self.cursor,
                                                  self.uid, partner_id)
    if not partner.header_image:
        return u''
    img, type = (partner.header_image, 'png')
    return self.embed_image(type, img, width, height)
WebKitHelper.embed_logo_by_partner = embed_logo_by_partner


def new_create_single_pdf(self, cursor, uid, ids, data,
                          report_xml, context=None):
    """ Generate the PDF """
    context = context or {}
    htmls = []
    if report_xml.report_type != 'webkit':
        return super(WebKitParser, self).create_single_pdf(cursor, uid, ids,
                                                           data, report_xml,
                                                           context=context)

    self.parser_instance = self.parser(cursor, uid, self.name2,
                                       context=context)

    template = False
    self.pool = pooler.get_pool(cursor.dbname)
    objs = self.getObjects(cursor, uid, ids, context)
    self.parser_instance.set_context(objs, data, ids, report_xml.report_type)

    if report_xml.report_file:
        path = addons.get_module_resource(
            *report_xml.report_file.split(os.path.sep))
        if path and os.path.exists(path):
            template = file(path).read()
    if not template and report_xml.report_webkit_data:
        template = report_xml.report_webkit_data
    if not template:
        raise except_osv(_('Error!'), _('Webkit report template not found!'))

    header = report_xml.webkit_header.html

    #jon   if the parser includes
    #get_webkit_header_by_partner  function,
    #use this function replace header
    header_function = getattr(self.parser, 'get_webkit_header_by_partner',
                              False)
    _logger.debug(header_function)

    if header_function:
        header_function = self.parser.get_webkit_header_by_partner
        partner_header = header_function(cursor, uid, ids)
        header = partner_header and partner_header.html or header

    footer = report_xml.webkit_header.footer_html
    if not header and report_xml.header:
        raise except_osv(_('No header defined for this Webkit report!'),
                         _('Please set a header in company settings.'))

    if not report_xml.header:
        header = ''
        default_head = addons.get_module_resource('report_webkit',
                                                  'default_header.html')
        with open(default_head, 'r') as f:
            header = f.read()
    css = report_xml.webkit_header.css
    if not css:
        css = ''

    #default_filters = ['unicode', 'entity'] can be used to set global filter
    body_mako_tpl = mako_template(template)
    helper = WebKitHelper(cursor, uid, report_xml.id, context)
    if report_xml.precise_mode:
        for obj in objs:
            self.parser_instance.localcontext['objects'] = [obj]
            try:
                html = body_mako_tpl.render(
                    helper=helper,
                    css=css,
                    _=self.translate_call,
                    **self.parser_instance.localcontext)
                htmls.append(html)
            except Exception:
                msg = exceptions.text_error_template().render()
                _logger.error(msg)
                raise except_osv(_('Webkit render!'), msg)
    else:
        try:
            html = body_mako_tpl.render(helper=helper,
                                        css=css,
                                        _=self.translate_call,
                                        **self.parser_instance.localcontext)
            htmls.append(html)
        except Exception:
            msg = exceptions.text_error_template().render()
            _logger.error(msg)
            raise except_osv(_('Webkit render!'), msg)
    head_mako_tpl = mako_template(header)
    try:
        head = head_mako_tpl.render(helper=helper,
                                    css=css,
                                    _=self.translate_call,
                                    _debug=False,
                                    **self.parser_instance.localcontext)
    except Exception:
        raise except_osv(_('Webkit render!'),
                         exceptions.text_error_template().render())
    foot = False
    if footer:
        foot_mako_tpl = mako_template(footer)
        try:
            foot = foot_mako_tpl.render(helper=helper,
                                        css=css,
                                        _=self.translate_call,
                                        **self.parser_instance.localcontext)
        except:
            msg = exceptions.text_error_template().render()
            _logger.error(msg)
            raise except_osv(_('Webkit render!'), msg)
    if report_xml.webkit_debug:
        try:
            deb = head_mako_tpl.render(helper=helper,
                                       css=css,
                                       _debug=tools.ustr("\n".join(htmls)),
                                       _=self.translate_call,
                                       **self.parser_instance.localcontext)
        except Exception:
            msg = exceptions.text_error_template().render()
            _logger.error(msg)
            raise except_osv(_('Webkit render!'), msg)
        return (deb, 'html')
    bin = self.get_lib(cursor, uid)
    pdf = self.generate_pdf(bin, report_xml, head, foot, htmls)
    return (pdf, 'pdf')


WebKitParser.create_single_pdf = new_create_single_pdf

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
