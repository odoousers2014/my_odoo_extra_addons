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
host = '127.0.0.1'
user = 'admin'
pw = 'a'

oerp = oerplib.OERP(host, protocol='xmlrpc', port=8069)
user = oerp.login(user, pw, 'yks')
so_obj = oerp.get('sale.order')

so_ids = so_obj.search([('state','=','progress')])
print len(so_ids), so_ids

n=0
for so_id in so_ids:
    so_obj.write(so_id, {'company_id':1})
    print n
    n += 1
    



so_ids_2 = so_obj.search([('state','=','progress')])
print len(so_ids_2)

print "___end________"
