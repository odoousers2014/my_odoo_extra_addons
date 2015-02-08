<!DOCTYPE html SYSTEM "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
    <style type="text/css">
        ${css}
        body{font-size:14px; text-align:center;}
        
        table{
        	text-align:left;
            border-left:"0";
            border-right:"0";
            border-top:px solid  black;
            border-bottom:"0";
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
             
            align:center;
            
        }
        .de_td{
            border-left:1px solid  black;
            border-right:1px solid  black;
            border-top:1px solid  black;
            border-bottom:1px solid  black;
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
            word-break:break-all;             
        }
        tr{
        	align:center;
        }

    </style>

</head>
<body>



<% newpage=0 %>
%for o in objects:

<div style="position:relative;  background:#FFF; align:center;">
    <h2 style="position:relative;  background:#FFF; text-align:center;">退款退货申请表</h2>
	% if o.type=="refund":
		<table style="align:center;">
		<tr><td >申请类型：</td><td>未发货退款</td><td>交易状态：</td><td> ${get_trade_state(o)}</td></tr>
		<tr><td>销售单号：</td><td>${get_so_id(o)}</td><td>退款金额：</td><td> ${o.amount}</td></tr>
		<tr><td>交易编号：</td><td>${o.platform_so_id}</td><td>退款账号：</td><td>${o.alipay_nick or ''}</td></tr>
		<tr><td>卖家ID：</td><td>${o.platform_seller_id}</td><td>账号姓名：</td><td>${o.alipay_name or ''}</td></tr>
		<tr><td>买家ID：</td><td>${o.platform_user_id}</td><td>业务员：</td><td>${o.create_uid.name or ''}</td></tr>
		<tr><td>出库单：</td><td>${o.need_cancel_picking_id.name}</td><td>创建时间：</td><td>${o.create_date}</td></tr>
		<tr><td>出库单状态：</td><td>${get_cancel_picking_state(o)}（状态不为“已取消”请联系仓库确认）</td></tr>
		</table>
		%if o.refund_line:
			<table style="align:center;">
			<caption>退款明细</caption>
			<tr><td class="de_td">产品</td><td class="de_td">数量</td></tr>
			%for obj in o.refund_line:
			<tr><td class="de_td">${get_name(obj)}</td><td class="de_td">${get_qty(obj)}</td></tr>
			%endfor
			
			</table>
		%endif
		<p text-align:right>审核：</p>
		<p text-align:right>日期：${ time.strftime('%Y-%m-%d') }</p>
		
	%endif
	% if o.type=="back":
		<table style="align:center;">
		<tr><td >申请类型：</td><td>已发货退款</td><td>交易状态：</td><td> ${get_trade_state(o)}</td></tr>
		<tr><td>销售单号：</td><td>${get_so_id(o)}</td><td>退款金额：</td><td> ${o.amount}</td></tr>
		<tr><td>交易编号：</td><td>${o.platform_so_id}</td><td>退款账号：</td><td>${o.alipay_nick or ''}</td></tr>
		<tr><td>卖家ID：</td><td>${o.platform_seller_id}</td><td>账号姓名：</td><td>${o.alipay_name or ''}</td></tr>
		<tr><td>买家ID：</td><td>${o.platform_user_id}</td><td>业务员：</td><td>${o.create_uid.name or ''}</td></tr>
		<tr><td>创建时间：</td><td>${o.create_date}</td></tr>
		</table>
		%if o.picking_id:
			<table style="align:center;">
			<caption>入库明细</caption>
			<tr><td class="de_td">产品</td><td class="de_td">数量</td><td class="de_td">源库位</td><td class="de_td">目的库位</td></tr>
			%for obj in o.picking_id.move_lines:
			<tr><td class="de_td">${get_name(obj)}</td><td class="de_td">${get_qty(obj)}</td><td class="de_td">${get_location(obj)}</td><td class="de_td">${get_dest(obj)}</td></tr>
			%endfor
			</table>
		%endif	
		%if o.refund_line:
			<table style="align:center;">
			<caption>退款明细</caption>
			<tr><td class="de_td">产品</td><td class="de_td">数量</td></tr>
			%for obj in o.refund_line:
			<tr><td class="de_td">${get_name(obj)}</td><td class="de_td">${get_qty(obj)}</td></tr>
			%endfor
			</table>
		%endif
		<p text-align:right>审核：</p>
		<p text-align:right>日期：${ time.strftime('%Y-%m-%d') }</p>
	%endif
	% if o.type=="exchange":
		<table style="align:center;">
		<tr><td >申请类型：</td><td>换货</td><td>交易状态：</td><td> ${get_trade_state(o)}</td></tr>
		<tr><td>销售单号：</td><td>${get_so_id(o)}</td><td>退款金额：</td><td> ${o.amount}</td></tr>
		<tr><td>交易编号：</td><td>${o.platform_so_id}</td><td>退款账号：</td><td>${o.alipay_nick or ''}</td></tr>
		<tr><td>卖家ID：</td><td>${o.platform_seller_id}</td><td>账号姓名：</td><td>${o.alipay_name or ''}</td></tr>
		<tr><td>买家ID：</td><td>${o.platform_user_id}</td><td>业务员：</td><td>${o.create_uid.name or ''}</td></tr>
		<tr><td>创建时间：</td><td>${o.create_date}</td></tr>
		</table>
		%if o.picking_id:
			<table style="align:center;">
			<caption>入库明细</caption>
			<tr><td class="de_td">产品</td><td class="de_td">数量</td><td class="de_td">源库位</td><td class="de_td">目的库位</td></tr>
			%for obj in o.picking_id.move_lines:
			<tr><td class="de_td">${get_name(obj)}</td><td class="de_td">${get_qty(obj)}</td><td class="de_td">${get_location(obj)}</td><td class="de_td">${get_dest(obj)}</td></tr>
			%endfor
			</table>
		%endif
		%if o.out_picking_id:
			<table style="align:center;">
			<caption>出库明细</caption>
			<tr><td class="de_td">产品</td><td class="de_td">数量</td><td class="de_td">源库位</td><td class="de_td">目的库位</td></tr>
			%for obj in o.out_picking_id.move_lines:
			<tr><td class="de_td">${get_name(obj)}</td><td class="de_td">${get_qty(obj)}</td><td class="de_td">${get_location(obj)}</td><td class="de_td">${get_dest(obj)}</td></tr>
			%endfor
			</table>
		%endif	
		<p text-align:right>审核：</p>
		<p text-align:right>日期：${ time.strftime('%Y-%m-%d') }</p>
	%endif
    
    
 </div>   
    
    %if len(objects) > 1:
        <p style="page-break-after: always"/>
    %endif

%endfor


</body>
</html>

