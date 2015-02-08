#-*-coding:utf-8 -*-
#author:获取快递的状态信息

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import xmlrpclib
import time
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

DF = '%Y-%m-%d: %H:%M:%S'


def time_ago(hours=0):
    return (datetime.now() - timedelta(hours=hours)).strftime(DF)

host = '119.81.169.98'
user = 'monkey'
pw = '123456'
db = 'yks'
sock_common = xmlrpclib.ServerProxy('http://%s:8069/xmlrpc/common' % host)
uid = sock_common.login(db, user, pw)
sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object' % (host, 8069))


def get_express_info(domain):
    express_info = sock.execute(db, uid, pw, 'express.express', 'get_to_query', domain)
    return express_info

#查找24*3小时前的单
day_before = 3
#4小时查询一次
time_loop = 4

B = webdriver.Firefox()
B.set_page_load_timeout(30)

H = 1
while H == 1:
    H = 0
    start_time = time_ago()
    next_time = time_ago(-time_loop)
    
    domain = [('state', '=', '0'), ('create_date', '<', time_ago(day_before * 24))]
    express_info = get_express_info(domain)
    
    print len(express_info), express_info

    n = 1
    for info in express_info[:200]:
        n += 1
        print '>>>%s %s %s' % (n, info, time.strftime('%H:%M:%S'))
        
        try:
            B.get(info['url'])
        except Exception, e:
            pass
        
        queryContext = None
        notFindTip = None
        
        #检查是否有错误
        #=======================================================================
        # notFindTip = None
        # try:
        #     notFindTip = WebDriverWait(B, 5).until(EC.presence_of_element_located((By.ID, "notFindTip")))
        #     if notFindTip.is_displayed():
        #         print "        快递单号有错误，标记错误，改正前不再查询"
        #         sock.execute(db, uid, pw, 'express.express', 'write', info['id'], {'log':'ERROR'})
        #         continue
        # except Exception, e:
        #     print 'Error notFindTip %s' % e
        #     continue
        #=======================================================================
        
        #get last tr
        last_tr = None
        try:
            #last_tr = B.find_element_by_class_name('last')
            last_tr = WebDriverWait(B, 10).until(EC.presence_of_element_located((By.ID, "last")))
        except Exception, e:
            print '    Error last_tr %s' % e
            continue
        
        #查看tds
        status_str = None
        try:
            tds = last_tr.find_elements_by_tag_name('td')
            status_str = tds[1].get_attribute('class')
        except Exception, e:
            print '      Error tds  %s' % e
            continue

        #check other status   status-wait  status-check
        if status_str:
            print "      ##### %s", status_str
            value = {'log': status_str}
            if 'status-check' in status_str:
                value.update(state='3')
            elif 'status-wait' in status_str:
                value.update(state='5')
            else:
                pass
            
            sock.execute(db, uid, pw, 'express.express', 'write', info['id'], value)

