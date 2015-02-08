#################################################################

from openerp.osv.orm import BaseModel
import new

from openerp.tools.translate import _
from openerp import SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

class except_orm(Exception):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.args = (name, value)


def enhance_method(klass, method_name, replacement):
    method = getattr(klass, method_name)
    setattr(klass, method_name, new.instancemethod(
        lambda *args, **kwds: replacement(method, *args, **kwds), None, klass))
    
def _check_record_rules_result_count_new(old_method, self, *args, **kwds):
    
    #return  old_method(self, *args, **kwds) 
    
    cr, uid, ids, result_ids, operation = args
    context=kwds.get('context', {})
    
    
    ids, result_ids = set(ids), set(result_ids)
    missing_ids = ids - result_ids
    if missing_ids:
        # Attempt to distinguish record rule restriction vs deleted records,
        # to provide a more specific error message - check if the missinf
        cr.execute('SELECT id FROM ' + self._table + ' WHERE id IN %s', (tuple(missing_ids),))
        if cr.rowcount:
            # the missing ids are (at least partially) hidden by access rules
            if uid == SUPERUSER_ID:
                return
            _logger.warning('Access Denied by record rules for operation: %s, uid: %s, model: %s', operation, uid, self._name)
            raise except_orm(_('Access Denied'),
                             _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s, IDS: %s)') % \
                                (self._description, operation, missing_ids))  ##jon  display missing_ids
                                
        else:
            # If we get here, the missing_ids are not in the database
            if operation in ('read','unlink'):
                # No need to warn about deleting an already deleted record.
                # And no error when reading a record that was deleted, to prevent spurious
                # errors for non-transactional search/read sequences coming from clients 
                return
            _logger.warning('Failed operation on deleted record(s): %s, uid: %s, model: %s', operation, uid, self._name)
            raise except_orm(_('Missing document(s)'),
                             _('One of the documents you are trying to access has been deleted, please try again after refreshing.'))
    



enhance_method(BaseModel, '_check_record_rules_result_count', _check_record_rules_result_count_new)








