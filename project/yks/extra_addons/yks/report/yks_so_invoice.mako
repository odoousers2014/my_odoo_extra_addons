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
    <div class=align_left>${  embed_image('jpg', user.company_id.logo, 150 , 92)  }</div>
    
    <h3 class=align_left>Werner-von-Siemens-Str.35,Pfungstadt,Hessen</h3>
    <hr   width="63%" style="margin-left:-5px;color:#1E90FF"/>
    <h3 class=align_left>姓名：${so.receive_user or ''} 地址：  ${so.receive_address or ''}</h3>
    <h3 class=align_left>Proforma RechnungsNr.: ${so.name}</h3>
        
    
    <table width="100%">
        <tr width="100%">
            <th width="10%">Nr.</th>
            <th width="40%">Description</th>
            <th width="10%">Quantity</th>
            <th width="20%">Value (EUR)</th>
            <th width="20%">Remarks</th>
        </tr>
        <% lines = so.order_line %>
        %for i  in range( len(lines) ):
            <tr width="100%">
                <td width="10%">${i+1}</td>
                <td width="40%">${lines[i].product_id.name}</td>
                <td width="10%">${ int( lines[i].product_uom_qty)}</td>
                <td width="20%">${lines[i].price_subtotal}</td>
                <td width="20%"></td>
            </tr>
        %endfor
        <tr width="100%">
            <td width="10%">Summe</td>
            <td width="40%"></td>
            <td width="10%"></td>
            <td width="20%">${so.amount_total}</td>
            <td width="20%"></td>
        </tr>
    </table>
    
<br></br>
<br></br>

<p class=align_left>Es handelt sich um eine nach § 8 Nr. 1a i.V.m. §12 UstG steuerbefreite Ausfuhrlieferung.</p>
<p class=text>Für weitere Fragen stehen wir Ihnen gern zur Verfügung.</p>
<p class=text>Mit freundlichen Grüßen </p>
<p class=text>BFE Logistics GmbH</p>
<p class=text>Tel.: 0049 (0)6157 810 5719</p>
<p class=text>Email: eaco.lager@gmail.com</p>


<br></br>



<p style="page-break-after: always"/>
%endfor


</body>
</html>

