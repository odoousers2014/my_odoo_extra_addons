# -*- coding: utf-8 -*-
##############################################################################

import md5
import hmac
import hashlib
from hashlib import sha1
import  urllib2
import  urllib
import json

##香港有棵树
##yks123  ea0760b2-08ae-44f9-b732-c5766c4638d7



default_code_arg={
'client_id':  '1014105',
'site' :'china',
'redirect_uri':  'http://localhost',
}

def  get_code(arg, secert='ilj3xdr6yrAH', url='http://gw.open.1688.com/auth/authorize.htm', ):
    data=''
    keys = arg.keys()
    keys.sort()
    for k in keys:
        data+=k +arg[k]
    secert='ilj3xdr6yrAH'
    sign =  hmac.new(secert, data, hashlib.sha1).hexdigest().upper()
    arg.update({'_aop_signature' : sign})
    postData = urllib.urlencode(arg)
    
    return  url + r'/?' +  postData

#print get_code(default_code_arg)
#exit()



default_token_arg={
      'grant_type':'authorization_code',
      'need_refresh_token':'true',
      'client_id':'1014105',
      'client_secret':'ilj3xdr6yrAH',
      'redirect_uri':'http://localhost',
}     

def get_token(arg, url='https://gw.open.1688.com/openapi/http/1/system.oauth2/getToken/' , code=False):
    if not code:
        return 'Pls input code first'
    
    url += arg['client_id']
    arg.update({ 'code': code,    }) 
    postData = urllib.urlencode(arg);
    req = urllib2.Request(url, postData);
    resp = urllib2.urlopen(req)
    print resp.read()
    
code = 'e68c6379-8959-4ffe-8815-844d4a949b8c'
print get_token(default_token_arg, code=code)


exit()


"""
{"refresh_token_timeout":"20150626174405000+0800","
aliId":"2379510033","resource_owner":"海豚供应链",
"memberId":"b2b-2379510033",
"expires_in":"36000",
"refresh_token":"98031047-4caa-403d-b579-d01f159f182a",
"access_token":"316d5376-1ba0-491d-b5e7-ec1ac68c5839"}
"""


appkey='1014105'
secret='ilj3xdr6yrAH'

def  alibaba_sign(url_path, arg, secret):
    st=''
    keys=arg.keys()
    keys.sort()
    for k in keys:
        st+=k +arg[k]
        
    print '签名因子',url_path + st
    print  """签名因子 /param2/1/cn.alibaba.open/convertMemberIdsByLoginIds/1014105loginIds海豚供应链access_token=316d5376-1ba0-491d-b5e7-ec1ac68c5839"""
    
    x=url_path + st
    print type(x),x
    
    return   hmac.new(secret, x, hashlib.sha1).hexdigest().upper()

def  alibaba_get_order(url,  url_pp,  method, arg, appkey, secret):
    
    urlpath= '/'.join([url_pp, method, appkey])
    sign = alibaba_sign(urlpath, arg, secret)
    
    print 'sign: ', sign
    arg.update({ '_aop_signature'  :sign})

    postData = urllib.urlencode(arg)
    
    new=url + urlpath
    print'new:', new
    
    req = urllib2.Request(new  , postData)
    resp = urllib2.urlopen(req)
    res = resp.read()
    res=json.loads(res)

    
  
get_order_arg={
    "sellerMemberId":"b2b-2379510033",    
    'access_token': '316d5376-1ba0-491d-b5e7-ec1ac68c5839'
}
url_api='http://gw.open.1688.com:80/openapi/'
method='/trade.order.list.get'

alibaba_get_order(url_api,'param2/2/cn.alibaba.open' ,method,  get_order_arg, appkey, secret)
    
exi()
#rerush acc
refresh_token='4eaffa5f-e329-4b57-8720-5481e83ff789'
def rerush(refresh_token):
    url='https://gw.open.1688.com/openapi/param2/1/system.oauth2/getToken/1014105'
    arg={
         'grant_type':'refresh_token',
         'client_id':'1014105',
         'client_secret':'ilj3xdr6yrAH',
         'refresh_token':refresh_token,
    }
    pd = urllib.urlencode(arg);
    req = urllib2.Request(url, pd);
    resp = urllib2.urlopen(req)
    return  resp.read()
    
print 'hehe', rerush(refresh_token)






