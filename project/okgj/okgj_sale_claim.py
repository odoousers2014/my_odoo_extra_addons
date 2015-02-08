# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.tools.translate import _
import time
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

class okgj_claim_type(osv.osv):
    _name = "okgj.claim.type"
    _description = "OKGJ Claim Type"
    _columns = {
        'name': fields.char(u'类型名称', size=32, required=True),
    }
okgj_claim_type()    

class okgj_claim_grade(osv.osv):
    _name = "okgj.claim.grade"
    _description = "Claim Grade"
    _order = "sequence"
    _columns = {
        'sequence': fields.integer(u'序号'),
        'name': fields.char(u'级别名称', size=32, required=True),
    }
okgj_claim_grade()    

class okgj_order_claim(osv.osv):
    _name = "okgj.order.claim"
    _description = "OKGJ Order Claim"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
okgj_order_claim()

class okgj_claim_notes_temp(osv.osv_memory):
    _name = "okgj.claim.notes.temp"
    _description = "OKGJ Claim Notes Temp"
    
    def action_done(self, cr, uid, ids, context=None):
        claim_ids = context.get('claim_ids')
        if not claim_ids:
            raise osv.except_osv(_(u'错误!'), _(u'无法找到相应投诉!'))
        if isinstance(ids, (int, long)):
            ids = [ids]
        data = self.read(cr, uid, ids[0], [], context=context)
        claim_obj = self.pool.get("okgj.order.claim")
        person_obj = self.pool.get("hr.employee")
        person_id = person_obj.search(cr, uid, [
            ('user_id', '=', uid)
            ], context=context)
        if person_id:
            person_id = person_id[0]
        else:
            person_id = False 
        if data['todo_uid']:
            claim_obj.write(cr, uid, claim_ids,
                            {'todo_uid':data['todo_uid'][0],
                             'all_uids':[(4, person_id)], 
                             'claim_note_ids':
                             [(0, 0, {'description':data['description']})]}, context=context)
        else:
            claim_obj.write(cr, uid, claim_ids,
                            {'all_uids':[(4, person_id)], 
                             'claim_note_ids':
                             [(0, 0, {'description':data['description']})]}, context=context)

        return {'type': 'ir.actions.act_window_close'}            
    
    _columns = {
        'description': fields.text(u'处理意见', required=True),
        'todo_uid': fields.many2one('hr.employee', u'下一处理人'),
    }
okgj_claim_notes_temp()    

class okgj_claim_notes(osv.osv):
    _name = "okgj.claim.notes"
    _description = "OKGJ Claim Notes"
    _columns = {
        'create_date': fields.datetime(u'处理时间' , readonly=True),
        'create_uid': fields.many2one('res.users', u'处理人', readonly=True),
        'description': fields.text(u'处理意见', required=True, readonly=True),
        'claim_id':fields.many2one('okgj.order.claim', u'投诉', readonly=True),
    }
okgj_claim_notes()    

## 问题关联
def links_get(self, cr, uid, context=None):
    obj = self.pool.get('okgj.claim.link')
    ids = obj.search(cr, uid, [], context=context)
    res = obj.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]

class okgj_claim_link(osv.osv):
    _name = 'okgj.claim.link'
    _description = "Claim Link"
    _columns = {
        'name': fields.char(u'名称', size=64, required=True),
        'object': fields.char(u'对象', size=64, required=True),
    }
okgj_claim_link()

## 类型，级别，次数，时间，投诉状态，处理人，处理意见，各部门流转
class okgj_order_claim(osv.osv):

    def create(self, cr, uid, vals, context=None):
        person_obj = self.pool.get("hr.employee")
        person_id = person_obj.search(cr, uid, [
            ('user_id', '=', uid)
            ], context=context)
        if person_id:
            vals.update({'all_uids': [(4, person_id[0])]})
        return super(okgj_order_claim, self).create(cr, uid, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        claim = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for s in sale_orders:
            if s['state'] in ['draft', 'cancel']:
                unlink_ids.append(s['id'])
            else:
                raise osv.except_osv(_('错误!'), _('不能删除进行中的或已完成的投诉!'))
        return osv.osv.unlink(self, cr, uid, unlink_ids, context=context)

    def action_add_note(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context.update({
            'claim_ids': ids,
        })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'okgj.claim.notes.temp',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    def action_progress(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'state':'progress'}, context=context)
    
    def action_close(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        return self.write(cr, uid, ids,
                          {'state':'done',
                           'date_closed': time.strftime('%Y-%m-%d'),
                           'to_uid':False}, context=context)

    def action_reopen(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        person_obj = self.pool.get("hr.employee")
        person_id = person_obj.search(cr, uid, [
            ('user_id', '=', uid)
            ], context=context)
        if person_id:
            person_id = person_id[0]
        else:
            person_id = False
        return self.write(cr, uid, ids,
                          {'state':'progress',
                           'to_uid':person_id}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        return self.write(cr, uid, ids,
                          {'state':'cancel',
                           'to_uid':False}, context=context)

    _inherit = 'okgj.order.claim'
    _columns = {
        'name': fields.char(u'单号', size=64, select=True, readonly=True, states={'draft':[('readonly', False)]}),
        'create_date': fields.datetime(u'创建时间' , readonly=True),
        'write_date': fields.datetime(u'修改时间' , readonly=True),
        'create_uid': fields.many2one('res.users', u'创建人', readonly=True),
        'write_uid': fields.many2one('res.users', u'修改人', readonly=True),
        'desc': fields.text(u'投诉内容', required=True),
        ## 'name_ref' : fields.reference(u'问题关联', selection=links_get, size=128,
        ##                               readonly=True, states={'draft':[('readonly', False)]}),
        'sale_id' : fields.many2one('sale.order', u'销售订单', required=True, 
                                    readonly=True, states={'draft':[('readonly', False)]}),
        'consignee':fields.related('sale_id', 'consignee', type='char', string=u'收货人', store=True),
        'okgj_tel':fields.related('sale_id', 'okgj_tel', type='char', string=u'联系电话', store=True),
        'date_closed': fields.datetime(u'关闭时间', readonly=True), 
        'state': fields.selection(
            [('draft', u'草稿'),
             ('progress', u'进行中'),
             ('cancel', u'取消'),
             ('done', u'完成'),
             ], u'进展', required=True, track_visibility='always'),
        'claim_type_id' : fields.many2one('okgj.claim.type', u'投诉类型', required=True, 
                                    readonly=True, states={'draft':[('readonly', False)]}),
        'claim_grade_id' : fields.many2one('okgj.claim.grade', u'投诉等级', 
                                    readonly=True, states={'draft':[('readonly', False)]}),
        'claim_note_ids':fields.one2many('okgj.claim.notes', 'claim_id', u'处理历史', readonly=True),
        'cc_uids': fields.many2many('hr.employee', 'claim_cc_uid', 'cc_uid', 'claim_id', u'抄送'),
        'all_uids': fields.many2many('hr.employee', 'claim_all_uid', 'all_uid', 'claim_id', u'参与人', readonly=True),
        'todo_uid': fields.many2one('hr.employee', u'下一处理人',
                                    readonly=True, states={'draft':[('readonly', False)]}, track_visibility='always'),
        'todo_deadline': fields.datetime(u'要求处理时间',
                                         readonly=True, states={'draft':[('readonly', False)]}),
        'image1': fields.binary(u'图片一'),
        'image2': fields.binary(u'图片二'),
        'image3': fields.binary(u'图片三'),
        'image4': fields.binary(u'图片四'),
        'image5': fields.binary(u'图片五'),
        'image6': fields.binary(u'图片六'), 
    }
    _defaults = {
        'state': lambda x, y, z, c: 'draft',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'okgj.order.claim'),
    }
okgj_order_claim()

class okgj_sale_order(osv.osv):

    _inherit = 'sale.order'
    
    def action_view_claim(self, cr, uid, ids, context=None):
        '''
        Show Order Claims
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'okgj', 'action_okgj_order_claim_all')
        action_id = result and result[1] or False
        result = act_obj.read(cr, uid, [action_id], context=context)[0]
        ## 计算需显示的投诉单数
        claim_obj = self.pool.get('okgj.order.claim')

        claim_ids = []
        for one_sale_id in ids:
            claim_ids += claim_obj.search(cr, uid,  [('sale_id', '=', one_sale_id)], context=context)
        #choose the view_mode accordingly
        if len(claim_ids) > 1:
            result['domain'] = "[('id','in',["+','.join(map(str, claim_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'okgj', 'view_okgj_order_claim_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = claim_ids and claim_ids[0] or False
        return result








