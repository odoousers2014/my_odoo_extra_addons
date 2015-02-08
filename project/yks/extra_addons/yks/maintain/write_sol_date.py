# -*- coding: utf-8 -*-
##############################################################################
import oerplib
import redis
import json
import xmlrpclib
from datetime import datetime

#1 所哟订单明细，增加 date_order 字段
#2 所有销售订单，流程重新触发，write compay_id = 1

#stable
host = '192.155.86.81'
user = 'admin'
pw = '5KS2pen1rp2dmin'

oerp = oerplib.OERP(host, protocol='xmlrpc', port=8069)
user = oerp.login(user, pw, 'yks')

so_obj = oerp.get('sale.order')
sol_obj = oerp.get('sale.order.line')

sol_ids = sol_obj.search([('date_order', '=', False)], limit=1000)
print sol_ids
print len(sol_ids)

i=0
for sol in sol_obj.browse(sol_ids):
    print str(sol.order_id.date_order), i
    sol_obj.write(sol.id, {'date_order': str(sol.order_id.date_order) })
    i += 1

print "___end________"
