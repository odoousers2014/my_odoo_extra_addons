# -*- coding: utf-8 -*-
'''
Created on 2013-7-15
@author: lee
'''
from openerp.osv import osv, fields
import httplib
import urllib 
import urllib2
import random
import datetime
import md5
from openerp.tools.translate import _
import time
import logging
import threading
import re
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

class okgj_message(osv.osv):
    _name = 'okgj.message'
    _description = u'消息提醒'
    _columns = {                
        'message':fields.text(u'消息内容', required=True),
        'message_type':fields.selection([
            ('type_sale',u'销售订单装车'),
            ('type_sale_return', u'退换货单装车'),
            ('type_sale_sign',u'客户签收'),
            ('type_4',u'活动三'),
            ('type_5',u'活动四'),
            ('type_6',u'活动五'),
            ('type_7',u'活动六'),
            ('type_8',u'活动七'),
            ('type_9',u'活动八'),
            ('type_10',u'活动九'),
            ('type_11',u'活动十'),
            ],string=u'消息类别', required=True),                  
        'create_uid':fields.many2one('res.users', u'创建人', readonly=True),
        'create_date': fields.datetime(u'创建时间', readonly=True),
        'write_uid': fields.many2one('res.users',u'修改人', readonly=True),
        'write_date': fields.datetime(u'修改时间', readonly=True),
        'enable': fields.boolean(u'可用'),  
    }

    _defaults = {
        'enable': lambda x, y, z, c: True,
    }

    def is_mobilephone(self, cellphone):
        flg=False
        phone_head= ['130','131','132','155','156','185','186',  
                     '134','135','136','137','138','139','147','150','151','152','157','158','159','182','187','188',
                     '133','153','180','189']
        s_head=''
        if len(cellphone)==11:
            for s_head in phone_head:
                if cellphone.startswith(s_head):
                    flg=True
        return flg           

    def _get_sms_base(self):
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        origin_countall = random.randint(100, 10000)
        countall = (origin_countall * 7 + 3) * 12
        all_str = md5.new(date_str + str(countall) + 'can_you_see').hexdigest()
        return {u'ecode':all_str.encode('utf-8'),
                u'countall':str(origin_countall).encode('utf-8')}

    def _open_sms(self, uid, message_type, one_phone, message):
        url = 'http://www.okgj.com/user/erp_sms.php'
        values = self._get_sms_base()
        values.update({u'msg':message.encode('utf-8'), u'm':one_phone.encode('utf-8')})
        data = urllib.urlencode(values)
        try:
            answer = urllib2.urlopen(urllib2.Request(url, data), timeout=2).read()
            if answer and str(answer) == '1':
                log_message = str(uid) + " has send " + message_type + " type message to " + one_phone 
                _logger.info('%s', log_message)
            else:
                log_message = str(uid) + " send " + message_type + " type message to " + one_phone + " Failed!"
                _logger.info('%s', log_message)
        except:
            log_message = str(uid) + "send " + message_type + " type message to " + one_phone + " Failed!"
            _logger.info('%s', log_message)
        return True

    def send_sms(self, cr, uid, message_type, message_data={}, context=None,):
        """ mobiles 手机号列表 """
        if context is None: context = {}
        message_ids = self.search(cr, uid, [
            ('enable', '=', True),
            ('message_type', '=', message_type)
            ], context=context)
        if message_ids:
            message_template = self.read(cr, uid, message_ids[0], ['message'], context=context)['message']
            ## thread_list = []
            for one_message in  message_data:
                message = message_template
                if 'contact_phone' in one_message:
                    message= message.replace('@phone@', one_message['contact_phone'])
                if 'contact' in one_message:
                    message= message.replace('@name@', one_message['contact'])
                if 'order_no' in one_message:
                    message= message.replace('@order@', one_message['order_no'])
                if self.is_mobilephone(one_message['dest_phone']):
                    ## one_phone = '18938904956'
                    ##self._open_sms(uid, message_type, one_phone, message)
                    self._open_sms(uid, message_type, one_message['dest_phone'], message)
                    ## urlstring="http://sdk2.entinfo.cn/z_send.aspx?sn=SDK-SKY-010-01619&pwd=087989&mobile=" + one_phone + "&content=" + message
                    ## urlstring="http://sdk2.entinfo.cn/z_send.aspx?sn=SDK-SKY-010-01619&pwd=087989&mobile=" + one_message['dest_phone'] + "&content=" + message
                    ## urlstring = urlstring.encode('gb2312')
                    
            ##         thread_list.append(threading.Thread(target = self._open_sms, args = (uid, message_type, one_message['dest_phone'], urlstring)))  
            ## for thread in thread_list:  
            ##     thread.start()  
            return True
        return True
        ## else:
        ##     raise osv.except_osv(_(u'警告!'), _(u'未找到发送给客户的提醒消息，请提醒相关ERP维护人员!'))                      

    def _check_message_enable(self, cr, uid, ids, context=None):
        if context is None: context = {}
        if isinstance(ids, (list, tuple)):
            ids = ids[0]
        message_type = self.read(cr, uid, ids, ['message_type'], context=context)['message_type']
        all_record = self.search(cr, uid, [
            ('enable', '=', True),
            ('message_type', '=', message_type)
            ], context=context, count=True)
        if all_record > 1:
            return False
        else:
            return True

    def _check_message_content(self, cr, uid, ids, context=None):
        message_now=self.browse(cr, uid, ids, context=context)[0].message #当前select值
        check_ = re.findall(r'@(\w+).*?@', message_now)
        res = ['phone', 'name','order']
        for i in check_:
            if not i in res :
                return False
        return True
        
    _constraints=[
        (_check_message_enable, '每一类消息只允许存在一条可用，请选择修改!', ['message_type']),
        (_check_message_content, '请使用正确的消息格式，格式如下：@phone@或@name@或@order@', ['message']),
    ]  

    _defaults = {
        'enable': lambda *a: False,
    }
okgj_message()    

class okgj_logistics_message_remind(osv.osv):
    _inherit = 'okgj.logistics'
    
    def action_start(self, cr, uid, ids, context=None):
        if context is None: context = {}
        super(okgj_logistics_message_remind, self).action_start(cr, uid, ids, context=context)
        message_type_sale = 'type_sale'
        message_type_sale_return = 'type_sale_return'
        message_obj = self.pool.get('okgj.message')
        driver = self.browse(cr, uid, ids, context=context) and self.browse(cr, uid, ids, context=context)[0].car_id.driver or ''
        driver_phone = self.browse(cr, uid, ids, context=context) and self.browse(cr, uid, ids, context=context)[0].car_id.driver_phone or ''
        order_id = ''
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        mobiles_sale_data = []
        mobiles_sale_return_data = []
        for one_logistics in self.browse(cr, uid, ids, context=context):
            if one_logistics.type == 'local':
                for one_line in one_logistics.line_ids:
                    if one_line.picking_id:
                        one_mobile = one_line.picking_id.sale_id and one_line.picking_id.sale_id.okgj_tel or False#one_line.sale_order_id.mobile
                        order_name = one_line.picking_id.sale_id and one_line.picking_id.sale_id.name or ''
                        if one_mobile:
                            mobiles_sale_data.append({
                                'dest_phone': one_mobile,
                                'order_no':order_name,
                                'contact':driver,
                                'contact_phone':driver_phone,
                            })
                    elif one_line.sale_return_id:
                        one_mobile = one_line.sale_return_id.okgj_tel or False
                        return_order = one_line.sale_return_id and one_line.sale_return_id.name or ''
                        if one_mobile:
                            mobiles_sale_return_data.append({
                                'dest_phone': one_mobile,
                                'order_no': return_order,
                                'contact': driver,
                                'contact_phone': driver_phone,
                            })
        if mobiles_sale_data:
            message_obj.send_sms(cr, uid, message_type_sale, mobiles_sale_data, context=context)
        if mobiles_sale_return_data:
            message_obj.send_sms(cr, uid, message_type_sale_return,
                                 mobiles_sale_return_data,
                                 context=context,)
        return True

class okgj_logistics_line_message(osv.osv):
    _inherit = "okgj.logistics.line"

    def write(self, cr, uid, ids, vals, context=None):
        if context is None: context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        old_state = self.read(cr, uid, ids[0], ['state'], context=context)['state']
        super(okgj_logistics_line_message, self).write(cr, uid, ids, vals, context=context)
        message_type = 'type_sale_sign'
        form = self.browse(cr, uid, ids[0], context=context)
        ## 干线装车不发送短信
        if form.logistics_id.type == 'route':
            return True
        ## 退换货收货不发送短信
        if form.sale_return_id:
            return True
        message_obj = self.pool.get('okgj.message')
        order_no = form.picking_id and form.picking_id.sale_id and form.picking_id.sale_id.name
        mobile = form.picking_id and form.picking_id.sale_id and form.picking_id.sale_id.okgj_tel or False
        if (old_state == 'todo') and (vals.get('state', False) == 'done'):
            message_data = {
                'dest_phone' : mobile,
                'order_no' : order_no,
            }
            message_obj.send_sms(cr, uid, message_type, [message_data], context=context)
        return True
