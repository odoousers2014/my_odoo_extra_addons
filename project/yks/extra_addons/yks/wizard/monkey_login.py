# -*- coding: utf-8 -*-
##############################################################################
from osv import osv, fields


class monkey_login(osv.osv_memory):
    _name = 'monkey.login'

    def get_monkey_login_url(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users')
        login = user_obj.read(cr, uid, uid, ['login', ], context=context)['login']
        return 'http://crm.mtytrack.com/index.php?m=user&a=loginfromother&name=%s' % login
    _columns = {
        'name': fields.char(u'登录到悟空CRM系统', size=100,),
    }
    _defaults = {
        'name': lambda self, cr, uid, c: self.get_monkey_login_url(cr, uid, c),
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(monkey_login, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            login = self.pool.get('res.users').read(cr, uid, uid, ['login'])['login']
            res['arch']= u'''
                <form string="悟空登录" version="7.0">
                    <group>
                        <h1>
                            <a target="_blank" href='http://crm.mtytrack.com/index.php?m=user&amp;a=loginfromother&amp;name=%s'>%s 登录悟空CRM系统</a>
                        </h1>
                    </group>
                    <footer>
                        <button string="取消" class="oe_link" special="cancel" />
                    </footer>
                </form>
            '''  % (login, login)
        return res
    
monkey_login()


class view_sc(osv.osv):
    _inherit = 'ir.ui.view_sc'
    _columns = {
        'is_global': fields.boolean('All user can see', size=64),
    }

    def get_sc(self, cr, uid, user_id, model='ir.ui.menu', context=None):
        ids = self.search(cr, uid, ['|', ('is_global', '=', True), '&', ('user_id', '=', user_id), ('resource', '=', model)], context=context)
        results = self.read(cr, uid, ids, ['res_id'], context=context)
        name_map = dict(self.pool.get(model).name_get(cr, uid, [x['res_id'] for x in results], context=context))
        # Make sure to return only shortcuts pointing to exisintg menu items.
        filtered_results = filter(lambda result: result['res_id'] in name_map, results)
        for result in filtered_results:
            result.update(name=name_map[result['res_id']])
        return filtered_results
view_sc()


##################################################################################################