# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _

def warp_write_group_check(func):
	"""
	decorate of write function, field write groups check.
	"""
	def _warp_write_group(self, cr, uid, ids, values, context=None):
		ADMIN=1
		model=self._name
		fgw_pool=self.pool.get('okgj.field.group.write')
		
		for field_name in values:
			fgw_ids = fgw_pool.search(cr, ADMIN, [('field_id.name','=',field_name),('field_id.model_id.model','=',model)])
			fgw_id = fgw_ids and fgw_ids[0] or False
			if fgw_id:
				fgw = fgw_pool.browse(cr, ADMIN, fgw_id, context=context)
				if fgw.group_ids:
					user_ids = set()
					for gp in fgw.group_ids:
						gp_uids=[u.id for u in gp.users]
						user_ids.update(gp_uids)
					if uid not in user_ids:
						raise osv.except_osv(_('Error!'),_(u'你没有权限更新字段:%s %s的内容，请联系系统管理员') % (model,field_name))
		return func(self, cr, uid, ids, values, context=context)	
	return _warp_write_group

class okgj_field_group_write(osv.osv):
	_name='okgj.field.group.write'
	_order='field_id'
	_columns={
		'name': fields.char('Name',size=16),
		'field_id': fields.many2one('ir.model.fields', 'Field'),
		'group_ids':fields.many2many('res.groups','field_group_write_rel', 'field_id','group_id', string='Write Groups'),		
	}
	_sql_constraints = [
		('field_uniq', 'unique(field_id)', 'field_id must be unique!'),
	]
okgj_field_group_write()


class product_product(osv.osv):
	_inherit='product.product'
	@warp_write_group_check
	def write(self, cr, uid, ids, values, context=None):
		return super(product_product,self).write(cr, uid, ids, values, context=context)
product_product()
class okgj_warehouse_sprice(osv.osv):
	_inherit='okgj.warehouse.sprice'
	@warp_write_group_check
	def write(self, cr, uid, ids, values, context=None):
		return super(okgj_warehouse_sprice,self).write(cr, uid, ids, values, context=context)
okgj_warehouse_sprice()







