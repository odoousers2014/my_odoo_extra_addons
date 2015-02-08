# -*- coding: utf-8 -*-
##############################################################################

from openerp.osv import  osv, fields


class res_users(osv.osv):
    _inherit = 'res.users'
    
    def _check_section(self, cr, uid, ids, context=None):
        for user in self.browse(cr, uid, ids, context=context):
            defaut_id = user.default_section_id and user.default_section_id.id
            section_ids = user.section_ids and [x.id for x in user.section_ids]
            if defaut_id and section_ids and defaut_id not in section_ids:
                return False
        return True
    
    _columns = {
        'job_id': fields.many2one('hr.job', u'职位'),
        'section_ids': fields.many2many('crm.case.section', 'res_user_section', 'uid', 'section_id', u"管理的销售团队")
    }
    
    _constraints = [
       (_check_section, 'The defaut sectin must includ the section ids', ['default_section_id','section_ids']),             
    ]

    def reset_signup_token(self, cr, uid, ids, context=None):
        for user in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, user.id, {"signup_token": 'Monkey' + user.login})
res_users()

##############################################################################