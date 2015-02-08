# -*- coding: utf-8 -*-

from osv import fields, osv
from openerp.tools.translate import _


class okgj_picking_out_reg(osv.osv):
    _name = 'okgj.picking.out.reg'
okgj_picking_out_reg()

class okgj_stock_picking_reg_temp(osv.osv):
    _inherit = "stock.picking"
    _columns = {
        'reg_id':fields.many2one('okgj.picking.out.reg', 'Reg', ondelete="no action"),
        'reg_operator_id':fields.related('reg_id', 'operator_id', type='many2one', relation='res.users', string=u'拣货人'),
        'reg_date':fields.related('reg_id', 'create_date', type='datetime', string=u'拣货时间'),
        'verify_uid':fields.many2one('res.users', u'复核人', readonly=True),
        'verify_date':fields.datetime(u'复核时间', readonly=True),
    }
okgj_stock_picking_reg_temp()

class okgj_stock_picking_reg(osv.osv):
    _inherit = "stock.picking.out"
    _columns = {
        'reg_id':fields.many2one('okgj.picking.out.reg', 'Reg', ondelete="no action"),
        'reg_operator_id':fields.related('reg_id', 'operator_id', type='many2one', relation='res.users', string=u'拣货人', store=True),
        'reg_date':fields.related('reg_id', 'create_date', type='datetime', string=u'拣货时间', store=True),
        'verify_uid':fields.many2one('res.users', u'复核人', readonly=True),
        'verify_date':fields.datetime(u'复核时间', readonly=True),
    }
okgj_stock_picking_reg()

class okgj_picking_out_reg_line(osv.osv):
    _name = 'okgj.picking.out.reg.line'
    _order = 'create_date desc'
    _rec_name = 'reg_id'
    _columns = {
        'reg_id':fields.many2one('okgj.picking.out.reg', u'拣货登记'),
        'picking_id':fields.many2one('stock.picking.out', u'拣货单', readonly=True),
        'okgj_send_time':fields.char(u'送货时间', readonly='True'),
    }
okgj_picking_out_reg_line()

class okgj_picking_out_reg(osv.osv):
    _name = 'okgj.picking.out.reg'
    _order = 'create_date desc'
    _columns = {
        'create_uid':fields.many2one('res.users', u'登记人', readonly='True'),
        'create_date':fields.datetime(u'登记时间', readonly='True'),
        'person':fields.char(u'拣货员', size=64, required=True),
        'operator_id':fields.many2one('res.users', u'拣货员'),
        'pick_car':fields.char(u'拣货车号', size=32),
        'collect':fields.char(u'拣货单号', size=64),
        'picking':fields.char(u'出库单号', size=64),
        'line_ids':fields.one2many('okgj.picking.out.reg.line', 'reg_id', u'明细行'),
        #'picking_ids':fields.one2many('stock.picking.out', 'reg_id', u'出库单'),
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心'),
    }

    def _default_warehouse_id(self, cr, uid, context=None):
        user_data = self.pool.get('res.users').browse(cr,uid, uid, context=context)
        warehouse_id = False
        for one_warehouse in user_data.warehouse_ids:
            warehouse_id = one_warehouse.id
        return warehouse_id
    
    def create(self, cr, uid, vals, context=None):
        if vals.get('person'):
            user_ids = self.pool.get('res.users').search(cr, uid, [('login', '=', vals.get('person'))], context=context)
            vals.update({'operator_id':user_ids[0]})
        return super(okgj_picking_out_reg, self).create(cr, uid, vals, context)

    def onchange_person(self, cr, uid, ids, person=False, context=None):
        """ On change of person
        @return: Dictionary of values
        """
        if person:
            user_obj = self.pool.get('res.users')
            user_ids = user_obj.search(cr, uid, [('login', '=', person)], context=context)
            if not user_ids:
                warning = {
                    'title': _('未找到相应拣货员'),
                    'message': person,
                }
                return {'warning':warning, 'value':{'person':False}}
            else:
                return {'value':{'operator_id':user_ids[0]}}
        else:
            return {}

    def onchange_collect(self, cr, uid, ids, collect=False, line_ids=False, context=None):
        """ On change of collect
        @return: Dictionary of values
        """
        if not collect:
            return {}
        if line_ids is False:
            line_ids = []
        collect_obj = self.pool.get('okgj.multi.order.print')
        picking_obj = self.pool.get('stock.picking.out')
        collect_ids = collect_obj.search(cr, uid, [('name', '=', collect)], context=context)
        if not collect_ids:
            return {'value':{'collect':False}, 'warning':{'title':_('条码错误'), 'message':_('未找到相应汇拣单')}}
        if len(collect_ids) != 1:
            return {'value':{'collect':False}, 'warning':{'title':_('条码错误'), 'message':_('发现多个汇拣单，无法继续')}}

        collect_picking_ids = collect_obj.browse(cr, uid, collect_ids[0], context=context).picking_ids
        for one_picking in collect_picking_ids:
            send_time = ''
            sale_data = picking_obj.browse(cr, uid, one_picking.id, context).sale_id
            if sale_data:
                send_time = sale_data.best_time
            else:
                sale_return_data = picking_obj.browse(cr, uid, one_picking.id, context).sale_return_id
                send_time = sale_return_data.best_time
            line_ids.append((0, 0, {'picking_id':one_picking.id, 'okgj_send_time':send_time}))
        return {'value': {'line_ids':line_ids, 'picking':False, 'collect':False}}

    def onchange_picking(self, cr, uid, ids, picking=False, line_ids=False, context=None):
        """ On change of collect
        @return: Dictionary of values
        """
        if not picking:
            return {}
        picking_obj = self.pool.get('stock.picking.out')
        new_picking_ids = picking_obj.search(cr, uid, [('name', '=', picking), ('reg_id', '=', False)], context=context)
        if (not new_picking_ids):
            return {'value':{'picking':False}, 'warning':{'title':_('条码错误'), 'message':_('未找到相应拣货单或该拣货单已登记!')}}
        if len(new_picking_ids) != 1:
            return {'value':{'picking':False}, 'warning':{'title':_('条码错误'), 'message':_('发现多个拣货单，无法继续')}}
        ## if not picking_ids:
        ##     picking_ids = [(4, new_picking_ids[0], False)]
        ## else:
        ##     picking_ids.append((4, new_picking_ids[0], False))

        send_time = ''
        sale_data = picking_obj.browse(cr, uid, new_picking_ids[0], context).sale_id
        if sale_data:
            send_time = sale_data.best_time
        else:
            sale_return_data = picking_obj.browse(cr, uid, new_picking_ids[0], context).sale_return_id
            send_time = sale_return_data.best_time
        if not line_ids:
            line_ids = [(0, 0, {'picking_id':new_picking_ids[0], 'okgj_send_time':send_time})]
        else:
            line_ids.append((0, 0, {'picking_id':new_picking_ids[0], 'okgj_send_time':send_time}))
        return {'value': {'line_ids':line_ids, 'picking':False, 'collect':False}}

    def action_done(self, cr, uid, ids, context=None):
        picking_obj = self.pool.get('stock.picking.out')
        for one_reg in self.browse(cr, uid, ids, context=context):
            for one_line in one_reg.line_ids:
                picking_obj.write(cr, uid, one_line.picking_id.id, {'reg_id':one_reg.id}, context=context)
        return {
            'name': _('装车登记'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'okgj.picking.out.reg',
            'type': 'ir.actions.act_window'
            }
    
    ## def _check_repeat(self, cr, uid, ids, context=None):
    ##     for one_reg in self.browse(cr, uid, ids, context):
    ##         if one_reg.collect_id.id and one_reg.picking_id.id:
    ##             return False
    ##     return True

    ## _constraints = [
    ##     (_check_repeat, 'Error! Only one picking order or one collect order Needed!', ['collect_id', 'picking_id']),
    ## ]   

    _defaults = {
        'warehouse_id': _default_warehouse_id,
    }

okgj_picking_out_reg()
