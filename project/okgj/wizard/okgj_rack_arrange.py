# -*- coding: utf-8 -*-

from openerp import tools
from osv import fields, osv
from openerp.tools.translate import _

#批量生成货位
class okgj_rack_arrange(osv.osv_memory):
    _name = 'okgj.rack.arrange'
    _columns = {
        'warehouse_id':fields.many2one('stock.warehouse', u'物流中心', required=True),
        'group_one_1':fields.char(u'第一组'),
        'group_one_2':fields.char(u'到'),   
        'group_one_3':fields.char(u'分隔符'),    
        'group_two_1':fields.char(u'第二组'),
        'group_two_2':fields.char(u'到'),   
        'group_two_3':fields.char(u'分隔符'), 
        'group_three_1':fields.char(u'第三组'),
        'group_three_2':fields.char(u'到'),   
        'group_three_3':fields.char(u'分隔符'), 
        'group_four_1':fields.char(u'第四组'),
        'group_four_2':fields.char(u'到'),   
        'group_four_3':fields.char(u'分隔符'),                                    
    }
    
    def is_chinese(self,uchar):
        """判断一个unicode是否是汉字"""
        if uchar >= u'\u4e00' and uchar<=u'\u9fa5':
            return True
        else:
            return False
 
    def is_number(self,uchar):
        """判断一个unicode是否是数字"""
        if uchar and uchar.isdigit():
            return True
        else:
            return False
 
    def is_alphabet(self,uchar):
        """判断一个unicode是否是英文字母"""
        if (uchar >= u'\u0041' and uchar<=u'\u005a') or (uchar >= u'\u0061' and uchar<=u'\u007a'):
            return True
        else:
            return False
 
    def is_other(self,uchar):
        """判断是否非汉字，数字和英文字符"""
        if not (self.is_chinese(uchar) or self.is_number(uchar) or self.is_alphabet(uchar)) :
            return True
        else:
            return False    

    def number_or_alphabet(self,group_data,uchar):
        if self.is_alphabet(group_data):
            data = chr(uchar)           
        elif self.is_number(group_data) and (uchar < 10):
            data = '0' + str(uchar)
        else:
            data = str(uchar)           
        return data

    def check_format(self, group_data):
        if self.is_alphabet(group_data):
            try:
                format_data = ord(group_data)   
            except:
                raise osv.except_osv(_(u'警告!'), _(u'请输入单个字母!'))       
        elif self.is_number(group_data):
            format_data = int(group_data)                              
        elif not group_data:
            raise osv.except_osv(_(u'警告!'), _(u'第一组和第二组的表格不能为空,请输入字母或数字!'))            
        else:            
            raise osv.except_osv(_(u'警告!'), _(u'[%s]的格式有误,请输入字母或数字!') % (group_data))
        return format_data
            
    def check_other(self, group_data):        
        if group_data and self.is_other(group_data):
            group_other_data = str(group_data)
        elif not group_data:
            group_other_data = ''
        else:
            raise osv.except_osv(_(u'警告!'), _(u'[%s]的格式有误,请输入分隔符!') % (group_data)) 
        return group_other_data
    
    def create_rack(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        local_res = {}     
        rack_obj = self.pool.get('okgj.product.rack')  
        arrange_obj = self.browse(cr, uid, ids, context = context) 
        if arrange_obj:
            one_1 = arrange_obj[0].group_one_1
            one_2 = arrange_obj[0].group_one_2
            one_3 = arrange_obj[0].group_one_3
            two_1 = arrange_obj[0].group_two_1
            two_2 = arrange_obj[0].group_two_2
            two_3 = arrange_obj[0].group_two_3
            three_1 = arrange_obj[0].group_three_1
            three_2 = arrange_obj[0].group_three_2
            three_3 = arrange_obj[0].group_three_3
            four_1 = arrange_obj[0].group_four_1
            four_2 = arrange_obj[0].group_four_2  
            if four_1:            
                for i in xrange(self.check_format(one_1),(self.check_format(one_2)+1)):
                    for r in xrange(self.check_format(two_1),(self.check_format(two_2)+1)):  
                        for p in xrange(self.check_format(three_1),(self.check_format(three_2)+1)): 
                            for q in xrange(self.check_format(four_1),(self.check_format(four_2)+1)): 
                                local_res['name'] = self.number_or_alphabet(one_1,i) + self.check_other(one_3) + self.number_or_alphabet(two_1,r) + self.check_other(two_3)+self.number_or_alphabet(three_1,p) + self.check_other(three_3)+self.number_or_alphabet(four_1,q)
                                local_res['warehouse_id'] = arrange_obj[0].warehouse_id.id                  
                                rack_id = rack_obj.create(cr, uid, local_res, context=context)    
            elif three_1:
                for i in xrange(self.check_format(one_1),(self.check_format(one_2)+1)):
                    for r in xrange(self.check_format(two_1),(self.check_format(two_2)+1)):  
                        for p in xrange(self.check_format(three_1),(self.check_format(three_2)+1)): 
                                local_res['name'] = self.number_or_alphabet(one_1,i) + self.check_other(one_3) + self.number_or_alphabet(two_1,r) + self.check_other(two_3)+self.number_or_alphabet(three_1,p)
                                local_res['warehouse_id'] = arrange_obj[0].warehouse_id.id                  
                                rack_id = rack_obj.create(cr, uid, local_res, context=context)  
            else:
                for i in xrange(self.check_format(one_1),(self.check_format(one_2)+1)):
                    for r in xrange(self.check_format(two_1),(self.check_format(two_2)+1)):  
                                local_res['name'] = self.number_or_alphabet(one_1,i) + self.check_other(one_3) + self.number_or_alphabet(two_1,r)
                                local_res['warehouse_id'] = arrange_obj[0].warehouse_id.id                  
                                rack_id = rack_obj.create(cr, uid, local_res, context=context)                  
                
        return {'type': 'ir.actions.act_window_close'} 


okgj_rack_arrange()


