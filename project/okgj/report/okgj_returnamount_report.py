# -*- coding: utf-8 -*-
##############################################################################

from openerp import tools
from osv import fields, osv
import openerp.addons.decimal_precision as dp
import re
import time
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
#from openerp.addons.web.controllers import main
import xlwt

class okgj_report_returnamount_lines(osv.osv_memory):
    _name = "okgj.report.returnamount.lines"
    _description = u"销售出库跟踪明细"
    _columns = {
        'okgj_rpt_stockoutno':fields.char(u'出库单号', readonly=True),    
        'okgj_rpt_orderno':fields.char(u'订单号', readonly=True),
        'okgj_rpt_okgjcity':fields.char(u'城市', readonly=True),
        'okgj_rpt_regionname':fields.char(u'区域', readonly=True),
        'okgj_rpt_consignee':fields.char(u'联系人', readonly=True),
        'okgj_rpt_tel':fields.char(u'联系电话', readonly=True),
        'okgj_rpt_address':fields.char(u'地址', readonly=True),
        'okgj_rpt_payname':fields.char(u'付款方式', readonly=True),
        'okgj_rpt_dateorder2':fields.char(u'商城下单时间', readonly=True),
        'okgj_rpt_orderdate' : fields.char(u'ERP创建时间', readonly=True),
        'okgj_rpt_sendtime' : fields.char(u'要求送货时间', readonly=True),
        'okgj_rpt_orderamount' : fields.float(u'订单金额', readonly=True),
        'okgj_rpt_orderstate' : fields.char(u'订单状态', readonly=True),
        'okgj_rpt_invpayee' : fields.char(u'发票抬头', readonly=True),
        'okgj_rpt_invcontent' : fields.char(u'发票内容', readonly=True),
        'okgj_rpt_invamount' : fields.float(u'发票金额', readonly=True),
        'okgj_rpt_pickuser' : fields.char(u'拣货人', readonly=True),
        'okgj_rpt_regdate' : fields.char(u'拣货时间', readonly=True),
        'okgj_rpt_verifyuser' : fields.char(u'复核人', readonly=True),
        'okgj_rpt_verifydate' : fields.char(u'复核时间', readonly=True),
        'okgj_rpt_logisticsno' : fields.char(u'装车单号', readonly=True),
        'okgj_rpt_incaruser' : fields.char(u'装车人', readonly=True),
        'okgj_rpt_incardate' : fields.char(u'装车时间', readonly=True),
        'okgj_rpt_carno' : fields.char(u'车辆', readonly=True),
        'okgj_rpt_cardriver' : fields.char(u'送货管家', readonly=True),
        'okgj_rpt_driverphone' : fields.char(u'管家电话', readonly=True),
        'okgj_rpt_backuser' : fields.char(u'返程登记人', readonly=True),
        'okgj_rpt_backdate' : fields.char(u'返程时间', readonly=True),
        'okgj_rpt_backstate' : fields.char(u'返程状态', readonly=True),
        'undelivered_cause' : fields.char(u'未送达原因', readonly=True),
        'okgj_rpt_moneyuser' : fields.char(u'结款人', readonly=True),
        'okgj_rpt_moneydate' : fields.char(u'结款时间', readonly=True),
        'okgj_rpt_moneyact' : fields.float(u'现金', readonly=True),
        'okgj_rpt_posact' : fields.float(u'POS', readonly=True),
        'okgj_rpt_moneydiff' : fields.float(u'差异', readonly=True),
        'okgj_rpt_needpaymoney':fields.float(u'到付金额', readonly=True),
        'okgj_rpt_notes' : fields.char(u'差异原因', readonly=True),
        'okgj_rpt_box':fields.char(u'箱号',readonly=True),
        'okgj_rpt_shopcancel':fields.char(u'复核后取消',readonly=True),
        'okgj_row_number':fields.char(u'序号',readonly=True),
        'okgj_rpt_warehouse':fields.char(u'物流中心',readonly=True),
        'okgj_rpt_saleshop':fields.char(u'配送点/分站',readonly=True),
        'okgj_rpt_container':fields.char(u'外挂信息',readonly=True),
        'okgj_rpt_outstatus':fields.char(u'出库状态',readonly=True),
        'report_returnamount_id':fields.many2one('okgj.report.returnamount',u'销售出库跟踪单号',readonly=True),
        }
okgj_report_returnamount_lines()

class okgj_report_returnamount(osv.osv_memory):
    _name = "okgj.report.returnamount"
    _description = u"销售出库跟踪"
    _columns = {
        'okgj_rpt_hstockoutno':fields.char(u'出库单号'),##.many2one('stock.picking', u'销售出库单',domain=[('sale_id','!=',False)]), 
        'okgj_rpt_horderno':fields.char(u'销售订单号'),##many2one('sale.order', u'销售订单'),
        'okgj_rpt_isverify':fields.boolean(u'未复核'),
        'okgj_rpt_isincar':fields.boolean(u'未装车'),
        'okgj_rpt_isback':fields.boolean(u'未返程'),
        'okgj_rpt_ispick':fields.boolean(u'未拣货'),
        'okgj_rpt_isuncancel':fields.boolean(u'未取消'),
        'okgj_rpt_sendtime':fields.char(u'要求送货时间'),
        'okgj_rpt_city':fields.char(u'城市'),
        'okgj_rpt_hwarehouse':fields.many2one('stock.warehouse', u'物流中心'),
        'okgj_rpt_hsaleshop':fields.many2one('sale.shop', u'配送点/分站',domain="[('warehouse_id','=',okgj_rpt_hwarehouse)]"),
        'line_ids':fields.one2many('okgj.report.returnamount.lines', 'report_returnamount_id', u'明细行', readonly=True),
        }

  
    # export excel to file  
    #def export_excel(self, cr, uid,request, context=None):  
        #import pdb;
        #pdb.set_trace()  
    #    response = HttpResponse(mimetype="application/ms-excel")  
    #    response['Content-Disposition'] = 'attachment; filename=detect_myspace.xls'      
    #    wb = xlwt.Workbook()  
    #    ws = wb.add_sheet('Sheetname')  
          
    #    ws.write(0, 0, 'Firstname')  
    #    ws.write(0, 1, 'Surname')  
    #    ws.write(1, 0, 'Hans')  
    #    ws.write(1, 1, 'Muster')  
      
    #    wb.save(response)  
    #    return response  

    def _default_warehouse_id(self, cr, uid, context=None):
        user_data = self.pool.get('res.users').browse(cr,uid, uid, context=context)
        warehouse_id = False
        for one_warehouse in user_data.warehouse_ids:
            warehouse_id = one_warehouse.id
            break
        return warehouse_id

    _defaults = {
        'okgj_rpt_hwarehouse': _default_warehouse_id,
    }
    
    def do_import(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = {}
        today = fields.date.context_today(cr, uid, ids, context=context)
        if isinstance(ids, (int, long)):
            curid=ids
        else:
            curid=ids[0]

        form = self.browse(cr, uid, curid, context=context)
        stockout_data = form.okgj_rpt_hstockoutno
        saleorder_data = form.okgj_rpt_horderno

        isverify=form.okgj_rpt_isverify
        isincar=form.okgj_rpt_isincar
        isback=form.okgj_rpt_isback
        ispick=form.okgj_rpt_ispick
        isuncancel=form.okgj_rpt_isuncancel
        strsendtime=form.okgj_rpt_sendtime
        strcity=form.okgj_rpt_city
        iwarehouse=form.okgj_rpt_hwarehouse.id
        isaleshop=form.okgj_rpt_hsaleshop.id

        ##删除历史数据
        line_ids = [one_line.id for one_line in form.line_ids]
        if line_ids:
            self.pool.get('okgj.report.returnamount.lines').unlink(cr, SUPERUSER_ID, line_ids,)
        
        strWhere=' AND 1=1'               
        
        if stockout_data:
            strWhere=strWhere+" And sp.name like '%"+stockout_data.encode("utf-8")+"%'"
        if saleorder_data:
            strWhere=strWhere+" And so.name like '%"+saleorder_data.encode("utf-8")+"%'"
        if isverify:
            strWhere=strWhere+" AND sp.state not in('done')" ##sp.verify_uid is null所有未完成的订单都属于未复核
        if isincar:
            strWhere=strWhere+" AND oll.create_uid is null"
        if isback:
            strWhere=strWhere+" AND ol.back_uid is null"
        if ispick:
            strWhere=strWhere+" AND sp.reg_operator_id is null"
        if isuncancel:
            strWhere=strWhere+" And so.state <>'cancel' and so.okgj_shop_cancel<>'t' and sp.state<>'cancel'"
        if strsendtime:
            strWhere=strWhere+" And so.send_time like '%"+strsendtime.encode("utf-8")+"%'"
        if strcity:
            strWhere=strWhere+" And so.okgj_city like '%"+strcity.encode("utf-8")+"%'"
        if iwarehouse:
            strWhere=strWhere+" And soshop.warehouse_id="+str(iwarehouse)+""
        if isaleshop:          
            strWhere=strWhere+" And so.shop_id="+str(isaleshop)+""

        sqlstr=""" 
            --最终查询
        select 	to_char(so.create_date+interval '8 hour','YYYY-MM-DD HH24:MI:SS') as okgj_rpt_orderdate,so.send_time as okgj_rpt_sendtime,
        (coalesce(so.amount_total,0)+coalesce(so.shipping_fee,0)-coalesce(so.coupon_pay,0)-coalesce(so.discount,0)) as okgj_rpt_orderamount,
        case so.state when 'cancel' then '取消' when 'done' then '已完成' when 'progress' then '销售订单' else '其它' end as okgj_rpt_orderstate,
        so.inv_payee as okgj_rpt_invpayee,so.inv_content as okgj_rpt_invcontent,so.inv_amount as okgj_rpt_invamount,
        pick_rp.name as okgj_rpt_pickuser,verify_rp.name as okgj_rpt_verifyuser,
        ol.name as okgj_rpt_logisticsno,incar_rp.name as okgj_rpt_incaruser,
        to_char(oll.create_date+interval '8 hour','YYYY-MM-DD HH24:MI:SS') as okgj_rpt_incardate,
        olc.name as okgj_rpt_carno,(olc.car_code||' / '||olc.driver) as okgj_rpt_cardriver,
        olc.driver_phone as okgj_rpt_driverphone,back_rp.name as okgj_rpt_backuser,
        to_char(ol.back_date+interval '8 hour','YYYY-MM-DD HH24:MI:SS') as okgj_rpt_backdate,
        case oll.state when 'cancel' then '未送达' when 'done' then '已送达' when 'todo' then '配送中' end as okgj_rpt_backstate,
        oll.cause as undelivered_cause,
        case oll.state when 'done' then money_rp.name else '' end as okgj_rpt_moneyuser,
        case oll.state when 'done' then to_char(ol.money_date+interval '8 hour','YYYY-MM-DD HH24:MI:SS') else '' end as okgj_rpt_moneydate,
        oll.money_act as okgj_rpt_moneyact,oll.pos_act as okgj_rpt_posact,so.order_amount-oll.pos_act-oll.money_act as okgj_rpt_moneydiff,
        oll.notes as okgj_rpt_notes,
        sp.name as okgj_rpt_stockoutno,so.name as okgj_rpt_orderno,so.okgj_city as okgj_rpt_okgjcity,
        so.region_name as okgj_rpt_regionname,so.consignee as okgj_rpt_consignee,so.okgj_tel as okgj_rpt_tel,
        so.okgj_address as okgj_rpt_address,so.pay_name as okgj_rpt_payname,
        to_char(so.date_order2+interval '8 hour','YYYY-MM-DD HH24:MI:SS') as okgj_rpt_dateorder2,
        to_char(sp.reg_date+interval '8 hour','YYYY-MM-DD HH24:MI:SS') as okgj_rpt_regdate,
        to_char(sp.verify_date+interval '8 hour','YYYY-MM-DD HH24:MI:SS') as okgj_rpt_verifydate,
        order_amount as okgj_rpt_needpaymoney,
        sp.okgj_box as okgj_rpt_box,
        case so.okgj_shop_cancel when 't' then '是' else '否' end as okgj_rpt_shopcancel,row_number() over() as okgj_row_number,
        soshop.name as okgj_rpt_saleshop,swarehoust.name as okgj_rpt_warehouse,sp.okgj_container as okgj_rpt_container,
        case sp.state when 'assigned' then '准备发运' when 'draft' then '草稿' when 'cancel' then '取消' when 'auto' then '等待其他操作'
        when 'confirmed' then '等待可用' when 'done' then '已出库' end as okgj_rpt_outstatus
        from sale_order so
        left join sale_shop soshop on so.shop_id=soshop.id
        left join stock_warehouse swarehoust on soshop.warehouse_id=swarehoust.id
        left join stock_picking sp on sp.sale_id = so.id
        left join res_users pick_ru on pick_ru.id = sp.reg_operator_id
        left join res_partner pick_rp on pick_rp.id = pick_ru.partner_id
        left join res_users verify_ru on verify_ru.id = sp.verify_uid
        left join res_partner verify_rp on verify_rp.id = verify_ru.partner_id
        left join (select logistics_id,create_uid,
                create_date,picking_id,cause,money_act,pos_act,state,notes from okgj_logistics_line 
                where logistics_id in
                (select max(logistics_id) from okgj_logistics_line
                where logistics_id is not null
                group by picking_id))oll on oll.picking_id = sp.id
        left join okgj_logistics ol on ol.id = oll.logistics_id
        left join okgj_logistics_car olc on olc.id = ol.car_id
        left join res_users incar_ru on incar_ru.id = oll.create_uid
        left join res_partner incar_rp on incar_rp.id = incar_ru.partner_id
            
        left join res_users back_ru on back_ru.id = ol.back_uid
        left join res_partner back_rp on back_rp.id = back_ru.partner_id
        left join res_users money_ru on money_ru.id = ol.money_uid
        left join res_partner money_rp on money_rp.id = money_ru.partner_id
        where sp.sale_id is not null   """+strWhere+"""
        --order by sp.id asc
             """

        cr.execute(sqlstr)
        results = cr.fetchall()

        data = []

        for result  in results:
            data.append((0, 0, {
                'okgj_rpt_orderdate' : result[0] and result[0] or '',
                'okgj_rpt_sendtime' : result[1] and result[1] or '',
                'okgj_rpt_orderamount' : result[2] and result[2] or 0.0,
                'okgj_rpt_orderstate' : result[3] and result[3] or '',
                'okgj_rpt_invpayee' : result[4] and result[4] or '',
                'okgj_rpt_invcontent' : result[5] and result[5] or '',
                'okgj_rpt_invamount' : result[6] and result[6] or 0.0,
                'okgj_rpt_pickuser' : result[7] and result[7] or '',
                'okgj_rpt_verifyuser' : result[8] and result[8] or '',
                'okgj_rpt_logisticsno' : result[9] and result[9] or '',
                'okgj_rpt_incaruser' : result[10] and result[10] or '',
                'okgj_rpt_incardate' : result[11] and result[11] or '',
                'okgj_rpt_carno' : result[12] and result[12] or '',
                'okgj_rpt_cardriver' : result[13] and result[13] or '',
                'okgj_rpt_driverphone' : result[14] and result[14] or '',
                'okgj_rpt_backuser' : result[15] and result[15] or '',
                'okgj_rpt_backdate' : result[16] and result[16] or '',
                'okgj_rpt_backstate': result[17] and result[17] or '',
                'undelivered_cause':result[18] and result[18] or '',
                'okgj_rpt_moneyuser' : result[19] and result[19] or '',
                'okgj_rpt_moneydate' : result[20] and result[20] or '',
                'okgj_rpt_moneyact' : result[21] and result[21] or 0.0,
                'okgj_rpt_posact' : result[22] and result[22] or 0.0,
                'okgj_rpt_moneydiff' : result[23] and result[23] or 0.0,
                'okgj_rpt_notes':result[24] and result[24] or '',
                'okgj_rpt_stockoutno' : result[25] and result[25] or '',
                'okgj_rpt_orderno' : result[26] and result[26] or '',
                'okgj_rpt_okgjcity' : result[27] and result[27] or '',
                'okgj_rpt_regionname' : result[28] and result[28] or '',
                'okgj_rpt_consignee' : result[29] and result[29] or '',
                'okgj_rpt_tel' : result[30] and result[30] or '',
                'okgj_rpt_address' : result[31] and result[31] or '',
                'okgj_rpt_payname' : result[32] and result[32] or '',
                'okgj_rpt_dateorder2' : result[33] and result[33] or '',
                'okgj_rpt_regdate' : result[34] and result[34] or '',			
                'okgj_rpt_verifydate' : result[35] and result[35] or '',
                'okgj_rpt_needpaymoney':result[36] and result[36] or 0.0,
                'okgj_rpt_box':result[37] and result[37] or '',
                'okgj_rpt_shopcancel':result[38] and result[38] or '',
                'okgj_row_number':result[39] and result[39] or '',
                'okgj_rpt_saleshop':result[40] and result[40] or '',
                'okgj_rpt_warehouse':result[41] and result[41] or '',
                'okgj_rpt_container':result[42] and result[42] or '',
                'okgj_rpt_outstatus':result[43] and result[43] or '',
                    }))
            
        self.write(cr, uid, curid, {'line_ids':data}, context=context)
        return True ##{'type': 'ir.actions.act_window_close'}     
    
okgj_report_returnamount()
