# -*- coding: utf-8 -*-
##############################################################################
from lxml import etree
from openerp.osv import osv, fields
#from openerp.tools.translate import _


class partial_express_line(osv.TransientModel):
    _name = "stock.partial.picking.express.line"
    _columns = {
        'express_id': fields.many2one('express.express', u'已存在快递单'),
        'delivery_carrier_id': fields.many2one('delivery.carrier', string=u'快递公司',),
        'scan_input': fields.char(u'扫描输入', size=40),
        'wizard_id': fields.many2one('stock.partial.picking', 'Wizard'),
    }
partial_express_line()


class express_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"
    _columns = {
        'delivery_carrier_id': fields.many2one('delivery.carrier', string=u'快递公司',),
        'scan_input': fields.char(u'扫描输入', size=40),
        'express_lines': fields.one2many('stock.partial.picking.express.line', 'wizard_id', "录入快递单"),
    }
    
    def onchange_scan_input(self, cr, uid, ids, scan_input, delivery_carrier_id, express_lines, context=None):
        value = {}
        if scan_input and delivery_carrier_id:
            express_lines.append((0, 0, {
                'express_id': False,
                'delivery_carrier_id': delivery_carrier_id,
                'scan_input': scan_input,
            }))
            value.update({
                'scan_input': '',
                'express_lines': express_lines,
            })
        return {'value': value}
    
    def check_do_partial(self, wizard, context=None):
        lis = []
        for line in wizard.express_lines:
            if line.scan_input in lis:
                raise osv.except_osv('Error', u'输入的快递单号中有重号，请删除！')
            else:
                lis.append(line.scan_input)
        return True
    
    def do_partial(self, cr, uid, ids, context=None):
        if context.get('default_type', '') == 'out':
            express_obj = self.pool.get('express.express')
            express_ids = []
            wizard = self.browse(cr, uid, ids[0], context=context)
            self.check_do_partial(wizard, context=context)
            for line in wizard.express_lines:
                if line.express_id:
                    exp_id = line.express_id.id
                else:
                    exp_id = express_obj.create(cr, uid, {
                        'delivery_carrier_id': line.delivery_carrier_id.id,
                        'name': line.scan_input,
                     })
                express_ids.append(exp_id)
            context.update({'express_ids': express_ids})
        return super(express_partial_picking, self).do_partial(cr, uid, ids, context=context)
    
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(express_partial_picking, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if context.get('default_type', '') != 'out':
            doc = etree.XML(res['arch'])
            for bad in doc.xpath("//group[@name='express']"):
                bad.getparent().remove(bad)
            res['arch'] = etree.tostring(doc)
        return res
        
express_partial_picking()


###############################################################
