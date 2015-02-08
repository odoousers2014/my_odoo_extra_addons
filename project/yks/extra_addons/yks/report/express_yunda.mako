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



<% newpage=0 %>
<% new_objects= get_new_objects([o.id for o in objects]) %>
%for o in (new_objects):

<div style="position:relative;  top:0px; left:0px; width:200px; height:20px;">

    <h2 style="position:absolute; top:0px;   left:180px; width:380px;  background:#FFF; text-align:left;">${ get_user_name(o) }</h2>
    <h2 style="position:absolute; top:50px; left:180px; width:380px;  background:#FFF; text-align:left;">${ get_user_company(o) } </h2>
    <h2 style="position:absolute; top:100px;  left:180px; width:380px;  background:#FFF; text-align:left;">${ get_user_address(o)}</h2>
    <h2 style="position:absolute; top:190px; left:370px; width:380px;  background:#FFF; text-align:left;">${ get_user_phone(o)  }</h2>

    <h2 style="position:absolute; top:0px;   left:700px; width:380px;  background:#FFF; text-align:left;">${ get_receive_name(o) }</h2>
    <h2 style="position:absolute; top:50px; left:700px; width:380px;  background:#FFF; text-align:left;"></h2>
    <h2 style="position:absolute; top:100px;  left:700px; width:350px;  background:#FFF; text-align:left;">${ get_receive_address(o)}</h2>

    <h2 style="position:absolute; top:190px; left:700px; width:380px;  background:#FFF; text-align:left;">${ get_receive_zip(o)} </h2>
    <h2 style="position:absolute; top:190px; left:800px; width:360px;  background:#FFF; text-align:left;">${ get_receive_phone(o)} </h2>
    
    <h2 style="position:absolute; top:310px; left:700px; width:500px;  background:#FFF; text-align:left;">${get_user_signature(o)}</h2>
    <h2 style="position:absolute; top:310px; left:790px; width:500px;  background:#FFF; text-align:left;">${ time.strftime('%Y-%m-%d') }</h2>
    
    <h2 style="position:absolute; top:450px;   left:750px; width:500px;  background:#FFF; text-align:left;">${ print_num(o) }</h2>
    
 </div>   
    
    %if len(new_objects) > 1:
        <p style="page-break-after: always"/>
    %endif

%endfor


</body>
</html>

