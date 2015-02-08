# -*- coding: utf-8 -*-
##############################################################################
import oerplib
from datetime import datetime
#from datetime import datetime, timedelta

#1 所哟订单明细，增加 date_order 字段
#2 所有销售订单，流程重新触发，write compay_id = 1


host = '119.81.169.98'
user = 'admin'
pw = '5KS2pen1rp2dmin'

#===============================================================================
# host = '127.0.0.1'
# user = 'admin'
# pw = 'a'
#===============================================================================


oerp = oerplib.OERP(host, protocol='xmlrpc', port=8069)
user = oerp.login(user, pw, 'yks')

pick_obj = oerp.get('stock.picking.out')

domain = [
          ('sale_id.shop_id','=',1),
          ('type','=','out'),
          ('create_date','<','2014-12-31 23:59:59'),
          ('state','in',['draft','auto','confirmed','assigned'])]

pick_ids = pick_obj.search(domain)

print len(pick_ids)

n = 1
for x in pick_obj.browse(pick_ids):
    
    n += 1
    
    if (x.sale_id.shop_id.id == 1 
        and x.state in ['draft','auto','confirmed','assigned']
        and x.type == 'out'
        and x.create_date.strftime('%Y-%m-%d %H:%M:%S') < '2014-12-31 23:59:59'):
        
        
        print n,':', x.state, x.id, x.name, x.sale_id.shop_id.name, x.create_date
    
        pick_obj.write(x.id, {'note':'cancel oldstate: %s :cancel by WH 2015 befor' % x.state })
        pick_obj.action_cancel([x.id])
    
    
    






print "___end________"
