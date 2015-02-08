<!DOCTYPE html SYSTEM "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
    <style type="text/css">
        ${css}
        
        body{font-size:8px; text-align:center;}

	.align_left{font-size:8px; text-align:left;}
        
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

		.new_page {page-break-after: always}
		
    </style>

</head>
<body>

<% page=0  %>
</p>
</p>
</p>
<table width="100%" class=table_no_border>
%for saler in (struct_data):
    <tr class=tdh_no_border><td class=tdh_no_border colspan=8 class=test_center><h1>Salesman: ${saler.name or ''}<h1></td></tr>

    %for partner in struct_data[saler]:
		  <tr class=tdh_no_border height='12px'><td class=tdh_no_border colspan=8 class=test_center><h2>Customer: ${partner.name or ''}<h2></td></tr>
		  <tr class=tdh_all_border>
           	<td width="10%" class=text_center><b>Date</b></td>
              <td width="50%"><b>Description</b></td>
              <td width="10%"><b>Reference</b></td>
              <td width="10%"><b>Source</b></td>
              <td width="10%"><b>Quantity</b></td>
              <td width="10%"><b>From</b></td>
             <!-- <td width="10%"><b>TO</b></td> -->
             <!-- <td width="6%"><b>Status</b></td>  -->
          </tr>    
	      %for move in struct_data[saler][partner]:
	         <tr>
           	<td width="10%">${move.date[0:11]}</td>
              <td width="50%" class=test_center>
                   ${move.name }
                   ${move.product_id.vintage}
                   ${move.product_id.bottle_size}
                   ${move.product_id.denomination and move.product_id.denomination.name or ''}  
                   ${move.product_id.name_cn}
                   ${move.product_id.vintage}
                   ${move.product_id.bottle_size}
                              
               </td>
              <td width="10%">${move.picking_id and move.picking_id.name or ''}</td>            
              <td width="10%">${move.origin or ''}</td>
              <td width="10%">${int(move.product_qty)}</td>
              <td width="10%">${move.location_id.complete_name}</td>
         <!--    <td width="10%">${move.location_id.complete_name}</td>   -->
         <!--     <td width="6%">${move.state.title()}</td>   -->
	         </tr>
	      %endfor 
	      
	      <tr>
	          <td colspan=3></td>
	          <td class=test_center>Total:</td>
	          <td class=test_center> ${total_moves(struct_data[saler][partner])}</td>
	          <td colspan=1></td>
	      </tr>
	      
    %endfor

%endfor
<p></p>

</table>


</body>
</html>


