# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
import openerp.tools.config as config
from openerp import netsvc
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP

class okgj_stock_out_verify(osv.osv_memory):
    _name = "okgj.stock.out.verify"
okgj_stock_out_verify()

class okgj_stock_out_verify_line(osv.osv_memory):
    _name = "okgj.stock.out.verify.line"
    _columns = {
        'verify_id':fields.many2one('okgj.stock.out.verify', 'Verify'),
        'product_id':fields.many2one('product.product', u'商品'),
        'prodlot_id':fields.many2one('stock.production.lot', u'生产日期'),
        'product_qty':fields.float(u'出库数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_verify_qty':fields.float(u'复核数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_extra_qty':fields.float(u'外挂数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_diff_qty':fields.float(u'差异数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'treat_state': fields.selection([
            ('doing', 'Doing'),
            ('todo', 'Todo'),
            ('done', 'Done'),
            ('wrong', 'Wrong'),
            ], u'处理状态'),
        'move_id':fields.many2one('stock.move', 'move_id'),
    }
    
okgj_stock_out_verify_line()

class okgj_stock_out_verify(osv.osv_memory):
    _inherit = "okgj.stock.out.verify"
    _columns = {
        'name':fields.char(u'出库单号', size=64),
        'info':fields.text(u'信息'),
        'sale_order_id':fields.many2one('sale.order', u'销售订单'),
        'picking_id':fields.many2one('stock.picking.out', u'拣货复核单'),
        'okgj_box':fields.text(u'箱号', size=128, help=u'物流箱号，每行一个', required=True),
        'goods_weight':fields.float(u'商品重量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'all_weight':fields.float(u'含箱重量', digits_compute=dp.get_precision('Product Unit of Measure')),
        ## 'extra_ids':fields.one2many('okgj.stock.picking.extra', 'picking_id', u'外挂'),
        'scan_type': fields.selection([
            ('1', u'复核扫描'),
            ('2', u'外挂扫描'),
            ], u'扫描方式', required=True),
        'product_qty': fields.integer(u'商品数量'),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure'),
        'ean':fields.char(u'商品条码', size=64),
        'move_ids':fields.one2many('okgj.stock.out.verify.line', 'verify_id', u'明细行'),
        'inv_amount': fields.float(u'开票金额', digits_compute=dp.get_precision('Product Price'), readonly=True),
        'inv_content':fields.text(u'发票内容', readonly=True),
        'inv_payee':fields.text(u'发票抬头', readonly=True),
        'inv_state': fields.selection([
            ('1', u'未开票'),
            ('2', u'已开票'),
            ('3', u'发票已退回'),
            ], u'开票状态', readonly=True),
        'inv_type': fields.selection([
            ('1', u'普通发票'),
            ('2', u'增值税发票'),
            ], u'开票种类', readonly=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('done', 'Done'),
            ], 'State', required=True, readonly=True),
    }
    
    _defaults = {
        'scan_type': lambda x, y, z, c: '1',
        'state': lambda x, y, z, c: 'draft',
        'product_qty': lambda *a: 1,
    }

    ## 复核初始信息
    def picking_review_info(self, cr, uid, stock_out_id, context=None):
        def do_result(args):  ## 处理结果，将None替换成‘’ 
            res_id = []
            if not args :
                return res_id
            for one in args :
                a_res = []
                for i in xrange(len(one)):
                    a_res.append(one[i] or '' )
                    i +=1
                res_id.append(a_res)
            return res_id
        
        sqlstr = """
        select stockmove.id, product.default_code, stockmove.product_qty,stocklot.name as lotname ,stockmove.product_id,stockmove.prodlot_id,stockmove.state,
            stockmove.sale_line_id, stockmove.name , product.track_outgoing ,product.name_template from stock_move stockmove
        left join stock_production_lot stocklot on stocklot.id = stockmove.prodlot_id
        left join product_product product on  product.id = stockmove.product_id
            where picking_id in (
                select id from stock_picking where name = """+stock_out_id+"""
            )
        """
        print sqlstr
        cr.execute(sqlstr)
        picking_list = cr.fetchall()        
        
        '''select name,order_weight, inv_payee,inv_content,inv_amount  from sale_order where name in (
                select name from sale_order where id in (
                    select sale_id from stock_picking where name = """+stock_out_id+"""
                    )
            )
        '''
        sqlstr = """
        select saleorder.id, saleorder.name,saleorder.order_weight, saleorder.inv_payee,saleorder.inv_content,
            saleorder.inv_amount,stockpicking.state,stockpicking.id as picking_id from sale_order saleorder
        left join stock_picking stockpicking on stockpicking.sale_id = saleorder.id 
            where stockpicking.name = """+stock_out_id+"""
        """
        print sqlstr
        result = {}

        cr.execute(sqlstr)
        picking_form = cr.fetchall()

        result[stock_out_id] = [ do_result(picking_list) , do_result(picking_form) ]
        print result
        return result
    

    def onchange_name(self, cr, uid, ids, name=False, context=None):
        """ On change of name
        @return: Dictionary of values
        """
        if (not name):
            return {}
        if name:
            picking_obj = self.pool.get('stock.picking.out')
            mov_obj = self.pool.get('stock.move')
            sale_obj = self.pool.get('sale.order')
            picking_ids = picking_obj.search(cr, uid, [
                ('name', '=', name),
                ('sale_id', '!=', False)
                ], context=context)
            if not picking_ids:
                warning = {
                    'title': _('未找到匹配的销售订单'),
                    'message': name,
                }
                return {'warning':warning, 'value':{'name':False}}
            if isinstance(picking_ids, (int, long)):
                picking_ids = [picking_ids]
            if len(picking_ids) != 1:
                warning = {
                    'title': _('找到多个匹配的销售订单'),
                    'message': name,
                }
                return {'warning':warning, 'value':{'name':False}}
            picking_data = picking_obj.browse(cr, uid, picking_ids[0], context=context)
            if picking_data.state in ['done', 'cancel']:
                warning = {
                    'title': _('该订单已处理，请重新录入'),
                    'message': name,
                }
                return {'warning':warning, 'value':{'name':False}}
            vals = {}
            vals.update({
                'sale_order_id': picking_data.sale_id.id,
                'picking_id':picking_ids[0],
                'inv_amount' : picking_data.sale_id.inv_amount,
                'inv_content' : picking_data.sale_id.inv_content,
                'inv_payee' : picking_data.sale_id.inv_payee,
                'inv_type' : picking_data.sale_id.inv_type,
                'inv_state' : picking_data.sale_id.inv_state,
                'okgj_box': False,
                'goods_weight' : picking_data.sale_id.order_weight,
                'all_weight' : picking_data.sale_id.order_weight + float(config.get('okgj_box_weight', '3840'))})
            move_ids = []
            for one_line in picking_data.move_lines:
                move_ids.append((0, 0, {
                    'move_id':one_line.id,
                    'product_id':one_line.product_id.id,
                    'prodlot_id':one_line.prodlot_id.id or False,
                    'product_qty':one_line.product_qty,
                    'product_verify_qty':0,
                    'product_extra_qty':0,
                    'treat_state':'todo',
                    'product_diff_qty':one_line.product_qty,}))
            vals.update({'move_ids':move_ids})
        return {'value': vals}

    def onchange_ean(self, cr, uid, ids, picking_id=False, scan_type=False, product_qty=False, ean=False, move_ids=False, context=None):
        """ On change of ean
        @return: Dictionary of values
        """
        if (not ean) or (not picking_id):
            return {}
        product_obj = self.pool.get('product.product')
        prodlot_obj = self.pool.get('stock.production.lot')
        if not move_ids:
            raise osv.except_osv(_('错误!'), _(u"请重新扫描出库单"))            
        #move_ids数据结构:
        #[[0, False, {'product_verify_qty': 0, 'product_diff_qty': 1, 'product_id': 2, 'product_extra_qty': 0, 'product_qty': 1}], [0, False, {'product_verify_qty': 0, 'product_diff_qty': 1, 'product_id': 3, 'product_extra_qty': 0, 'product_qty': 1}]]或者[[4, 7, False], [4, 8, False]]
        #商品由于批次号，可能有多个行, prodlot_dict = {product_id:[lines, display_info]}
        prodlot_dict = {}
        info = ''
        for one_move in move_ids: 
            if one_move[2] and one_move[2]['prodlot_id']:
                lot_name = prodlot_obj.read(cr, uid, one_move[2]['prodlot_id'], ['name'], context=context)['name']
                product_id = one_move[2]['product_id']
                if prodlot_dict.get(product_id, False):
                    lines = prodlot_dict[product_id][0] + 1
                    info = prodlot_dict[product_id][1] + '\t' + lot_name + ':' + str(one_move[2]['product_qty'])
                    prodlot_dict[product_id] = [lines, info]
                else:
                    lines = 1
                    info = lot_name + ':' + str(one_move[2]['product_qty'])
                    prodlot_dict[product_id] = [lines, info]
        has_product = False

        #是否已完成，如果完成，检查下一行，如果未有下一行，出错，如果有下一行，到下一行.用现有结构是否能解析问题？
        line_count = 1
        for one_move in move_ids:
            if one_move[0] == 0:
                product_id = one_move[2] and one_move[2]['product_id']
                default_code = product_obj.read(cr, uid, product_id, ['default_code'], context=context)['default_code']
                if default_code == ean:
                    has_product = True
                    if scan_type == '1':
                        treat_state = one_move[2] and one_move[2]['treat_state']
                        if product_id not in prodlot_dict: #未有生产批次
                            info = False
                            one_move[2]['product_verify_qty'] += product_qty
                            one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                            if one_move[2]['product_diff_qty'] > 0:
                                one_move[2]['treat_state'] = 'doing'
                            elif one_move[2]['product_diff_qty'] == 0:
                                one_move[2]['treat_state'] = 'done'
                            else:
                                one_move[2]['treat_state'] = 'wrong'
                            break
                        elif product_id in prodlot_dict:
                            if prodlot_dict[product_id][0] == 1:  #只有一个生产日期
                                info = prodlot_dict[product_id][1]
                                one_move[2]['product_verify_qty'] += product_qty
                                one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                                if one_move[2]['product_diff_qty'] > 0:
                                    one_move[2]['treat_state'] = 'doing'
                                elif one_move[2]['product_diff_qty'] == 0:
                                    one_move[2]['treat_state'] = 'done'
                                else:
                                    one_move[2]['treat_state'] = 'wrong'
                                break
                            else:  #多个生产批次
                                treat_state = one_move[2]['treat_state']
                                info = prodlot_dict[product_id][1]
                                if treat_state == 'todo' or treat_state == 'doing':
                                    one_move[2]['product_verify_qty'] += product_qty
                                    one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                                    if one_move[2]['product_diff_qty'] > 0:
                                        one_move[2]['treat_state'] = 'doing'
                                    elif one_move[2]['product_diff_qty'] == 0:
                                        one_move[2]['treat_state'] = 'done'
                                    break
                                elif treat_state == 'done':  ##本行已完成，进入下一行，如果未有下一行，wrong!
                                    lot_line_count = prodlot_dict[product_id][0]
                                    if line_count < lot_line_count:
                                        line_count += 1 ##到下一行进行处理
                                        continue
                                    else:  ##已到最后一行
                                        one_move[2]['product_verify_qty'] += product_qty
                                        one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                                        one_move[2]['treat_state'] = 'wrong'
                                        break
                                elif one_move[2]['treat_state'] == 'wrong':
                                    one_move[2]['product_verify_qty'] += product_qty
                                    one_move[2]['product_diff_qty'] = one_move[2]['product_qty'] - one_move[2]['product_verify_qty']
                                    one_move[2]['treat_state'] = 'wrong'
                                    break
                    elif scan_type == '2':
                        one_move[2]['product_extra_qty'] += product_qty
                        break
                    else:
                        return {'warning':{'title':_('未知扫描方式'), 'message':_('请选择扫描方式')}}

            else:
                 return {'warning':{'title':_('请勿确认有差异的订单'), 'message':_('请重新扫描发货单并再次复核')}}
        if has_product:
            return {'value': {'move_ids':move_ids, 'ean':False, 'product_qty':1, 'info':info}}
        else:
            return {'value':{'name':False}, 'warning':{'title':_('条码错误'), 'message':_('未找到相应商品')}}

    def action_process(self, cr, uid, ids, context=None):
        picking_obj = self.pool.get('stock.picking.out')
        wf_service = netsvc.LocalService("workflow")
        for one_verify in self.browse(cr, uid, ids, context=context):
            container = ''
            container_explain = {}
            for one_line in one_verify.move_ids:
                if one_line.product_diff_qty != 0:
                    raise osv.except_osv(_('错误!'), _(u"商品'%s'有差异，无法进行复核确认.") % (one_line.product_id.name))
                extra = ''
                variants = ''
                if one_line.product_extra_qty != 0:
                    if one_line.product_id.variants:
                        variants +=  ' ' + one_line.product_id.variants
                    if one_line.product_extra_qty:
                        extra += ' ' + str(one_line.product_extra_qty)
                    if one_line.product_id and one_line.move_id:
                        key = (one_line.move_id.id, one_line.product_id.id)
                        container_explain[key] = one_line.product_extra_qty
                    container += one_line.product_id.name + variants + extra + '\n'
            picking_obj.write(cr, uid, one_verify.picking_id.id, {
                'verify_uid':uid,
                'verify_date':time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'okgj_box': one_verify.okgj_box,
                'okgj_container':container,
                'okgj_container_explain':str(container_explain),
                }, context=context)
            wf_service.trg_validate(uid, "stock.picking", one_verify.picking_id.id, 'button_done', cr)
        return True

    def action_done(self, cr, uid, ids, context=None):
        self.action_process(cr, uid, ids, context=context)
        return {
            'name': _('拣货复核'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'okgj.stock.out.verify',
            'type': 'ir.actions.act_window'
            }

okgj_stock_out_verify()

#复核更改
class okgj_verify_order_modify(osv.osv_memory):
    _name = "okgj.verify.order.modify"
    _columns={
        'picking_name':fields.char(u'已复核出库单号', size=64, required=True),
        'product_ean':fields.char(u'商品条码', size=64),
        'product_qty': fields.integer(u'外挂数量'),
        'picking_id':fields.many2one('stock.picking.out', u'拣货复核单'),
        'sale_order_id':fields.related('picking_id', 'sale_id', type='many2one', relation='sale.order', string=u'销售订单', readonly=True),
        'origin_box':fields.related('picking_id', 'okgj_box', type='text', string=u'已复核箱号', help=u'已复核物流箱号', readonly=True),
        'new_box':fields.text(u'新箱号', size=128, help=u'新的物流箱号'),
        'modify_line_ids':fields.one2many('okgj.verify.order.modify.line', 'order_modify_id', u'明细行'),
        'okgj_container':fields.text(u'外挂'),
        'okgj_container_explain':fields.text(u'外挂说明'),
        'if_modify':fields.boolean(u'更改外挂'),
        'product_out_info':fields.text(u'商品出库数量信息'),
        
    }
    
    _defaults = {
        'product_qty': lambda *a: 1,
        'if_modify': lambda *a: True,
        }
    def action_verify_modify(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')
        picking_obj = self.pool.get('stock.picking.out')
        for one_record in self.browse(cr, uid, ids, context=context):
            new_box = one_record.new_box or one_record.origin_box
            if_modify = one_record.if_modify
            picking_id = one_record.picking_id
            container = ''
            origin_container = one_record.okgj_container
            container_explain = eval(one_record.okgj_container_explain)
            new_container_explain = container_explain.copy()
            modify_product = {}
            product_ids = []
            for one_line in one_record.modify_line_ids:
                if one_line.move_id and one_line.product_id:
                    key = (one_line.move_id.id, one_line.product_id.id)
                    modify_product[key] = one_line.new_extra_qty
                    product_ids.append(one_line.product_id.id)
            if if_modify:
                container_explain.update(modify_product)
                new_container_list = [(one_container, container_explain[one_container]) for one_container in container_explain if container_explain[one_container]]
                new_container_explain = dict(new_container_list)
            for one_container in container_explain:
                product_data = product_obj.browse(cr, uid, one_container[1], context=context)
                if container_explain[one_container]:
                    prd_info = [product_data.name]
                    if product_data.variants:
                        prd_info.append(product_data.variants)
                    prd_info.append(str(container_explain[one_container]))
                    container += ' '.join(prd_info) + '\n'
            if picking_id:
                picking_obj.write(cr, uid, picking_id.id, {
                    'okgj_box': new_box,
                    'okgj_container':container or origin_container,
                    'okgj_container_explain':str(new_container_explain),
                }, context=context)
        
        return {
            'name': u'复核更改',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'okgj.verify.order.modify',
            'type': 'ir.actions.act_window'
            }
    
    def onchange_picking_name(self, cr, uid, ids, picking_name, context=None):
        if context is None:
            context = {}
        if not picking_name:
            return {}
        if picking_name:
            picking_obj = self.pool.get('stock.picking.out')
            logistics_line_obj = self.pool.get('okgj.logistics.line')
            picking_ids = picking_obj.search(cr, uid, [
                ('name', '=', picking_name),
                ('sale_id', '!=', False),
                ('state', '=', 'done'),
                ], context=context)
            if not picking_ids:
                warning = {
                    'title': _('未找到已复核的销售订单'),
                    'message': picking_name,
                }
                return {'warning':warning, 'value':{'picking_name':False}}
            #检测是否装车
            logistics_line_ids = logistics_line_obj.search(cr, uid, [('picking_id', '=', picking_ids[0])])
            if logistics_line_ids:
                return {'warning':{'title':_(picking_name), 'message':_('该订单已装车!')}, 'value':{'picking_name':False}}
            picking_data = picking_obj.browse(cr, uid, picking_ids[0], context=context)
            vals = {}
            vals.update({
                'picking_id':picking_ids[0],
                'sale_order_id':picking_data.sale_id.id,
                'origin_box':picking_data.okgj_box,
                'okgj_container': picking_data.okgj_container,
                'okgj_container_explain': picking_data.okgj_container_explain or '{}',
                })
            modify_line_ids = []
            product_out_dict = {}
            container_explain = eval(picking_data.okgj_container_explain or '{}')
            for one_line in picking_data.move_lines:
                if one_line.product_id:
                    key = (one_line.id, one_line.product_id.id)
                    modify_line_ids.append((0, 0, {
                        'move_id':one_line.id,
                        'product_id':one_line.product_id.id,
                        'product_qty':one_line.product_qty,
                        'prodlot_id':one_line.prodlot_id.id or False,
                        'origin_extra_qty':container_explain.get(key, False),
                        }))
                    product_out_dict[one_line.product_id.id] = product_out_dict.get(one_line.product_id.id, 0) + one_line.product_qty 
            vals['product_out_info'] = str(product_out_dict)
            vals.update({'modify_line_ids':modify_line_ids})
        return {'value': vals}
    
    def onchange_product_ean(self, cr, uid, ids, if_modify, picking_id, product_ean, product_qty, modify_line_ids, product_out_info, context=None):
        """ On change of product_ean
        @return: Dictionary of values
        """
        if (not product_ean) or (not picking_id):
            return {}
        product_obj = self.pool.get('product.product')
        line_obj = self.pool.get('okgj.verify.order.modify.line')
        if not modify_line_ids:
            raise osv.except_osv(_(u'错误:'), _(u"请重新扫描出库单")) 
        if not if_modify:
            raise osv.except_osv(_(u'错误'), _(u"更改外挂未勾选!"))
        res = {'value':{}}
        if product_ean and product_qty:
            product_ids = product_obj.search(cr, uid, [('default_code', '=', product_ean)], context=context)
            if not product_ids:
                raise osv.except_osv(_(u'错误:'), _(u'未找到该商品!'))
            
            product_out_lines = eval(product_out_info)
            total_qty_out = product_out_lines.get(product_ids[0], 0) #商品总出库数量
            for one_line in modify_line_ids:
                if one_line[0] == 0:
                    product_id = one_line[2] and one_line[2]['product_id']
                    origin_qty = one_line[2] and one_line[2].get('new_extra_qty', 0)
                    if product_id == product_ids[0]:
                        one_line[2]['new_extra_qty'] = product_qty + origin_qty
                        one_line[2]['extra_state'] = self._get_extra_state(cr, uid ,total_qty_out, (product_qty + origin_qty))
                        break
                elif one_line[0] == 1 and one_line[1] and one_line[2]:
                    line_data = line_obj.read(cr, uid, one_line[1], ['product_id', 'new_extra_qty'], load="_classic_write", context=context)
                    product_id = line_data['product_id']
                    origin_qty = line_data['new_extra_qty'] or 0
                    if product_id == product_ids[0]:
                        one_line[2].update({'new_extra_qty':(product_qty + origin_qty)})
                        one_line[2]['extra_state'] = self._get_extra_state(cr, uid ,total_qty_out, (product_qty + origin_qty))
                        break
                elif one_line[0] == 4 and one_line[1]:
                    line_data = line_obj.read(cr, uid, one_line[1], ['product_id', 'new_extra_qty'], load="_classic_write", context=context)
                    product_id = line_data['product_id']
                    origin_qty = line_data['new_extra_qty'] or 0
                    if product_id == product_ids[0]:
                        one_line[0] = 1
                        one_line[2] = {
                            'new_extra_qty':(product_qty + origin_qty),
                            'extra_state': self._get_extra_state(cr, uid ,total_qty_out, (product_qty + origin_qty)),
                            }
                        break
            res['value']['product_ean'] = False
            res['value']['product_qty'] = 1
            res['value']['modify_line_ids'] = modify_line_ids
        return res
   
    def _get_extra_state(self, cr, uid, total_qty, extra_qty):
        extra_state = False
        if total_qty > extra_qty:
            extra_state = '1'
        elif total_qty < extra_qty:
            extra_state = '2'
        else:
            extra_state = '3'
        return extra_state
      
okgj_verify_order_modify()

class okgj_verify_order_modify_line(osv.osv_memory):
    _name = "okgj.verify.order.modify.line"
     
    def onchange_extra_qty(self, cr, uid, ids, product_id, extra_qty, product_out_info, context=None):
        if not (product_id and product_out_info):
            return {}
        res = {'value':{}}
        product_out_lines = eval(product_out_info) 
        total_product_qty = product_out_lines.get(product_id, 0)
        extra_state = False
        if total_product_qty > extra_qty:
            extra_state = '1'
        elif total_product_qty < extra_qty:
            extra_state = '2'
        else:
            extra_state = '3'
        res['value']['extra_state'] = extra_state
        return res
    
    _columns={
        'order_modify_id':fields.many2one('okgj.verify.order.modify', 'modify'),
        'move_id':fields.many2one('stock.move', 'move_id'),
        'product_id':fields.many2one('product.product', u'商品'),
        'prodlot_id':fields.many2one('stock.production.lot', u'生产日期'),
        'product_qty':fields.float(u'出库数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'origin_extra_qty':fields.float(u'已复核外挂数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'new_extra_qty':fields.float(u'更改后外挂数量', digits_compute=dp.get_precision('Product Unit of Measure')),
        'extra_state':fields.selection([('1', u'低于出库数'), ('2',u'高于出库数量'), ('3',u'等于出库数量')], u'外挂状态'),
    }
    
okgj_verify_order_modify_line()

