<!DOCTYPE html SYSTEM "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
    <style type="text/css">
        ${css}
        body{font-size:16px; text-align:center;}
        
        table{
            border-left:1px solid  black;
            border-right:1px solid  black;
            border-top:1px solid  black;
            border-bottom:1px solid  black;
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
            word-break:break-all; 
        }
        .table_no_border{
            border-left:none;
            border-right:none;
            border-top:none;
            border-bottom:none;
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
            word-break:break-all;
        }
        
        .table_horizontal_border{
            frame:"vsides";
            border-left:1px solid  black;
            border-right:1px solid  black;
            border-top:none;
            border-bottom:none;
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
            word-break:break-all;
            
        }
        .table_top_border{
            border-left:1px solid  black;
            border-right:1px solid  black;
            border-top:1px solid  black;
            border-bottom:'none';
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
            word-break:break-all;
        }
        
        .undermove {
            border:1px solid #002299;
            position:absolute;
            left:5px;
        }


        .left_td{border-left:0px solid  black;}  
        .top_td{border-top:0px solid  black;} 
        .right_td{border-right:0px solid  black;}  
        .bottom_td{border-bottom:0px solid  black;} 
        
        td{
            border-left:1px solid  black;
            border-right:1px solid  black;
            border-top:1px solid  black;
            border-bottom:1px solid  black;
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
            word-break:break-all;
        }
        th{
            border-left:1px solid  black;
            border-right:1px solid  black;
            border-top:1px solid  black;
            border-bottom:1px solid  black;
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
            word-break:break-all;
        }

        .test_center{text-align:center;}
        .tdh_no_border{
            border-left:none;
            border-right:none;
            border-top:none;
            border-bottom:none;
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
            word-break:break-all;
        }

        .td_all_border{
            border-left:1px solid  black;
            border-right:1px solid  black;
            border-top:1px solid  black;
            border-bottom:1px solid  black;
            border-collapse:collapse;
            cellpadding:"0"; 
            cellspacing:"0";
            word-break:break-all;
        }
     .align_left{text-align:left;}
     .text{margin: 0; text-align:left;}
     .page_break_margin {page-break-after: always}

    </style>

</head>
<body>

<%
def embed_image(type, img, width=0, height=0) :
    "Transform a DB image into an embedded HTML image"

    if width :
        width = 'width="%spx"'%(width)
    else :
        width = ' '
    if height :
        height = 'height="%spx"'%(height)
    else :
        height = ' '
    toreturn = '<img %s %s src="data:image/%s;base64,%s" />'%(
        width,
        height,
        type, 
        str(img))
    return toreturn

%>

<% newpage=0 %>
%for so in (objects):

<h3 class=align_left>姓名：${so.receive_user or ''}（收）</h3>
<h4 class=align_left>电话：${so.receive_phone or ''} </h4>
<h4 class=align_left>地址：${so.receiver_state_id and  so.receiver_state_id.name   or ''}  ${so.receiver_city_id and  so.receiver_city_id.name   or ''}  ${so.receive_address or ''}</h4>
<h4 class=align_left>邮编：${so.receiver_zip or ''}</h4>
<h4 class=align_left>日期：${so.platform_create_time and so.platform_create_time[:10] or ''}</h4>
<h4 class=align_left>订单号：${so.name or ''}</h4>

<p style="page-break-after: always"/>
%endfor


</body>
</html>

