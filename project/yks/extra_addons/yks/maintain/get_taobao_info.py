#-*-coding:utf-8-*-
'''
Created on 2014-11-24

@author: cloudy
'''
#-*- coding:utf-8 -*-
#author:cloudy

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import xmlrpclib
import re
import datetime
import time


import logging
import sys,os
path =sys.path[0]
def cur_file_dir():
    #获取脚本路径
    path = sys.path[0]
    #判断为脚本文件还是py2exe编译后的文件，如果是脚本文件，则返回的是脚本的目录，如果是py2exe编译后的文件，则返回的是编译后的文件路径
    if os.path.isdir(path):
        return path
    elif os.path.isfile(path):
        return os.path.dirname(path)

logging.basicConfig(level=logging.ERROR,
    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
    datefmt= '%a, %d %b %Y %H:%M%S',
    filename='getTaobaoInfo.log',#%time.strftime( '%Y-%m-%d %X', time.localtime(time.time())),
    filemode='a+')
_log = logging.getLogger(__name__)

TaobaoName={
    'pengjielaiye':'jie198871',
    'tb3308202_2011':'jiang1234567890',
    u'yks海外专营店':'maotouying2014',
    u'小小白熊00':'',
}
BaseMsg={
    'host':'192.155.86.81',#'localhost',#
    'port':'8069',
    'user':'monkey',
    'password':'123456',
    'databaseName':'yks',
} 
url = "http://trade.taobao.com/trade/itemlist/list_sold_items.htm?spm=a1z0f.3.0.0.Mm5uHt&mytmenu=ymbb&utkn=g,obsw4z3knfswyyljpfsq1416648846439&scm=1028.1.1.201"
#url ="https://login.taobao.com/member/login.jhtml"


class getTaobaoInfo(object):
    
    def __init__(self,username,password,url):
        '''
        '''
        self.username = username
        self.password = password
        self.url = url
    def login(self):
        '''
        登陆淘宝后台
        '''
        browser=webdriver.Firefox()
        browser.get(self.url)
        try:
            element = WebDriverWait(browser,5).until(
                EC.presence_of_element_located((By.XPATH,"//input[@id='TPL_username_1']"))
            )
        except Exception,e:
            msg = u'进入淘宝登陆界面失败'
            browser.close()
            return False,msg
        if not self.password:
            msg = u"不支持手动填入密码请在文件TaobaoName中的%s填入密码"%self.username
            return False,msg
        elem_login_name = browser.find_element_by_xpath("//input[@id='TPL_username_1']")
        elem_login_name.clear()
        elem_login_name.send_keys(self.username)        
        elem_login_password = browser.find_element_by_xpath("//input[@id='TPL_password_1']")
        elem_login_password.clear()
        elem_login_password.send_keys(self.password)

        elem_login_submit = browser.find_element_by_xpath("//button[@id='J_SubmitStatic']")
        elem_login_submit.click()
        #暂时不考虑验证码和控件安装
        try:
            loging_checkCode=browser.find_element_by_xpath("//div[@class='field field-checkcode']/input[@id='J_CodeInput_i']")
            current_time = datetime.datetime.now()
            #等待40senconds输入验证码，若超时则退出
            while True:
                if datetime.datetime.now()>current_time.replace(minute=current_time.minute+1):
                    break 
        except:
            pass
        #判断使否登陆成功
        try:
            elem_err_login = browser.find_element_by_xpath("//p[@class='error']")
            errMsg = elem_err_login.text()
            if not errMsg:
                return True,browser
            else:
                browser.close()
                return False,errMsg
        except :
            pass
        
        return True,browser
    def search_order(self,browser,so_id):
        '''
        根据淘宝订单编号查找订单详细信息
        '''
        browser.implicitly_wait(5)
        elem_so_id = browser.find_element_by_xpath("//input[@id='bizOrderId']")
        elem_so_id.clear()
        elem_so_id.send_keys(so_id)
        elem_search = browser.find_element_by_xpath("//button[@id='J_SearchOrders']")
        elem_search.click()
        return browser
    def get_detail(self,browser):
        """
        获得详细信息
        """
        browser.implicitly_wait(5)
        elem_detail = browser.find_element_by_xpath("//a[@class='detail-link']")
        #browser.switch_to_window(browser.window_handles[-1])
        currentHandle = browser.current_window_handle
        elem_detail.click()
        allHandles = browser.window_handles
        for handle in allHandles:
            if currentHandle != handle:
                browser.switch_to_window(handle)
        return browser
    def get_address(self,browser):
        '''
        获取地址信息
        '''
        browser.implicitly_wait(5)
        try:
            #淘宝账户
            elem_address = browser.find_element_by_id("J_BlockBuyerAddress")
        except:
            #天猫账户
            elem_address = browser.find_element_by_id('J_main_address_detail')
        newUrl = elem_address.get_attribute("data-url")
        browser.get(newUrl)
        try:
            element = WebDriverWait(browser,10).until(EC.presence_of_element_located((By.TAG_NAME,'body')))
        except Exception,e:
            msg = u'进入收货人信息获取界面失败'
            logFunc(msg)
            browser.close() #失败，关闭页面句柄
            return False,msg
        elem_body=browser.find_element_by_tag_name("body")
        address=elem_body.text
        splitAddr = address.split("\"")
        i =0
        info = {'receive_phone':None}
        for key in splitAddr:
            if u'name'==key:
                info['receive_user'] = splitAddr[i+2]
            elif u'mobilephone' ==key or u'phone' ==key:
                info['receive_phone'] =  info['receive_phone'] or splitAddr[i+2]
            elif u'addr' ==key:
                info['receive_address'] = splitAddr[i+2]
            elif u'post' ==key:
                info['receiver_zip'] = splitAddr[i+2]
            i = i+1
        browser.close()
        return True,info

class PostgresBase(object):
    
    def __init__(self,host,port,user,password,databaseName):
        self.host = host                    
        self.port = port                     
        self.user = user                   
        self.pwd = password             
        self.db = databaseName 
        self.common_url = 'http://%s:%s/xmlrpc/common'%(self.host,self.port) 
        self.sock_url = 'http://%s:%s/xmlrpc/object'%(self.host,self.port) 
        self.common = None
        self.sock = None
        try:
            self.sock_common = xmlrpclib.ServerProxy(self.common_url)
        except Exception,e:
            logFunc(u'连接服务器失败，请假差参数是否正确'+self.common_url)
        try:
            self.sock = xmlrpclib.ServerProxy(self.sock_url)
        except Exception,e:
            logFunc(u'连接服务器失败，请假差参数是否正确'+self.sock_url)
        self.uid = self.sock_common.login(self.db,self.user,self.pwd)
        
    def _searchIds(self,table,args):
        '''
        语句获得查询结果
        table:需要查询的表
        args:查询条件
        '''
        return self.sock.execute(self.db,self.uid,self.pwd,table,'search',args)

    def _readDatas(self,table,ids,fields):
        '''
        查询数据
        table：查询的表
        ids：查询的id
        fields：查询的字段
        '''
        return self.sock.execute(self.db, self.uid, self.pwd, table, 'read', ids, fields)
    def _writeDatas(self,table,ids,values):
        '''
        更新数据
        table:更新的表
        ids:更新的id
        values:待更新的数据,字典数据
        '''
        res = self.sock.execute(self.db, self.uid, self.pwd, table, 'write', ids, values)    
        return res

class SQL_obj(PostgresBase):
    '''
    连接到postgresql
    '''
    def __init__(self,host,port,user,password,databaseName):
        super(SQL_obj,self).__init__(host,port,user,password,databaseName)
      
    def getPlatFormOrderId(self,seller):
        '''
        获得需要获得信息的平台订单号
        '''
        args= [('state','=','draft'),('platform_seller_id','=',seller),]
        ids = self._searchIds('sale.order', args)
        infos = self._readDatas('sale.order', ids, ['platform_so_id','receive_phone','name'])
        #过滤掉已经写入的ID,通过判断电话号码中是否含有'*'来判断
        res=[]
        pattern = r"\d{3}-\d{8}|\d{4}-\d{7,8}|1\d{10}"
        #pattern = r"\*"
        for info in infos:
            if not re.search(pattern, info['receive_phone']):
                res.append(info)
        return res
            
    def writeData2Table(self, table, ids, values):
        '''
        数据写入表中
        '''
        return self._writeDatas(table, ids, values)
def logFunc(msg):
    """日志记录和信息打印"""
    print msg
    _log.error(msg)

def getmsg():
    msg = u'开始获取收件人信息，需要获取的账号在文件中'
    logFunc(msg)
    obj = SQL_obj(BaseMsg['host'],BaseMsg['port'],BaseMsg['user'],BaseMsg['password'],BaseMsg['databaseName'])
    err_platform_so = {}
    #所有抓到的订单信息
    so_id_info = {}
    so_id_platform_id ={}
    try:
        for Account in TaobaoName.keys():
            
            #获得一个账号和密码
            name = '%s'%Account
            pwd = '%s'%TaobaoName[Account]
            msg= u'当前登陆的淘宝账号为：%s'%name
            logFunc(msg)
            #根据账号查询订单
            platform_so_ids = obj.getPlatFormOrderId(name)
            err_platform_so[name]=[];
            if not platform_so_ids:
                print name 
                msg =u"账号%s没有处于草稿状态且收件人信息模糊的订单"%name
                logFunc(msg)
                continue
            else:
                msg=u'%s需要获取信息的平台订单号为：'%name
                logFunc(msg)
                #err_platform_so[name] = platform_so_ids
                for so_id in platform_so_ids:
                    msg = u'OPENERP系统订单号:%s;淘宝平台订单号:%s'%(so_id['name'],so_id['platform_so_id'])
                    logFunc(msg)
            taobao_obj = getTaobaoInfo(name,pwd,url)
            res = taobao_obj.login()
            if res[0]:
                msg = u'%s登陆成功,开始收件人信息抓取.....'%name
                logFunc(msg)
                browser = res[1]
            else:
                msg = u'%s登陆失败'%name
                logFunc(msg)
                continue
            for so_id in platform_so_ids:
                try:
                    browser_detail = taobao_obj.search_order(browser,so_id['platform_so_id'])
                    browser_address = taobao_obj.get_detail(browser_detail)
                    res = taobao_obj.get_address(browser_address)
                    #若成功则将返回的信息写到数据库中，若失败将失败的信息写到日志文件
                    if res[0]:
                        vals = res[1]
                    else:
                        logFunc(res[1])
                        err_platform_so[name].append(so_id)
                        continue
                    try:
                        #res = obj.writeData2Table('sale.order', so_id['id'], vals)
                        so_id_info[so_id['id']] = vals
                        so_id_platform_id[so_id['id']] = so_id['platform_so_id']
                        #msg = u'完成平台订单：%s信息写入'%so_id['platform_so_id']
                        #logFunc(msg)
                    except Exception,e:
                        msg = u'淘宝平台订单：%s收货人信息写入失败，信息：%s'%(so_id['platform_so_id'],vals)
                        logFunc(msg)
                        msg = '%s'%e
                        logFunc(msg)
                        continue    #跳出执行下一个订单信息抓取
                except Exception,e:     
                    '''
                    若获取失败，需要关闭当前窗口句柄，切换到前一个窗口，进行下一个订单搜索，
                    若此处不关闭，程序会崩溃，
                    '''        
                    logFunc(u'平台订单号：%s信息获取失败'%so_id['platform_so_id'])
                    logFunc(e)
                    browser.close()
                    for handle in browser.window_handles:
                        browser.switch_to_window(handle)
                    err_platform_so[name].append(so_id)
                    #需要删除，否则会重复查找该订单
                    platform_so_ids.remove(so_id)
                    continue    #跳出执行下一个订单信息抓取
                #窗口句柄切换
                for handle in browser.window_handles:
                    browser.switch_to_window(handle)
            browser.close()
            if not err_platform_so[name]:
                logFunc(u'%s账号订单信息获取完成。'%name)
            else:
                logFunc(u'%s账号订单信息获取部分完成，请检查日志文件，查看失败记录。'%name)
                logFunc(u'%s未完成信息抓取的订单为：'%name)
                for err_so_id in err_platform_so[name]:
                    logFunc(err_so_id['platform_so_id'])
    finally:
        for so_id in so_id_info: 
            try:
                obj.writeData2Table('sale.order', so_id, so_id_info[so_id])
                msg = u'完成平台订单：%s信息写入'%so_id_platform_id[so_id]
                logFunc(msg)
            except:
                msg = u'平台订单：%s信息写入失败'%so_id_platform_id[so_id]
                logFunc(msg)
                continue;
    logFunc(u'所有账号信息获取完成，请查看')
            
if __name__ =='__main__':
    while True:
        getmsg()
	time.sleep(600)
