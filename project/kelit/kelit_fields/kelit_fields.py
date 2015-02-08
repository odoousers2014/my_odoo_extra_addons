# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2013 Elico Corp. All Rights Reserved.
#    Author: Yannick Gouin <yannick.gouin@elico-corp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tools import ustr
from openerp.osv import osv, fields
from openerp.tools.translate import _
import re


#Default company_id when creating a new product is set to False
class product_template(osv.osv):
    _inherit = "product.template"

    _columns = {
        'name': fields.char('Name', size=128, translate=True, select=True),
    }
    
    _defaults = {
        'company_id': False,
    }
product_template()


class product_brand(osv.osv):
    _name = 'product.brand'
    _order='name'
    
    def _check_code(self, cr, uid, ids, context=None):
        
        for brand in self.browse(cr, uid,ids):
            if len(brand.code) != 2:
                return False
        return  True
    
    _columns = {
        'name': fields.char(_('Name'), size=128, select=True,required=True,store=True),
        'code': fields.char(_('Code'), size=2, select=True, required=True,store=True),
    }

    _sql_constraints = [        ('code_unique', 'unique (code)', 'The code of the brand #must be unique code!'),    ] 
    _constraints = [
        (_check_code, "Error:the len of Code must be 2,like 'AB' ", ['ean13'],),
    ]
product_brand()


class product_denomination(osv.osv):
    _name = 'product.denomination'
    
    _columns = {
        'name': fields.char(_('Name'), size=128, translate=True, select=True),
    }
product_denomination()


class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'
        
    def _auto_init(self, cr, context=None):
        super(product_product, self)._auto_init(cr, context)
        cr.execute("SELECT id FROM product_product WHERE name IS NULL")
        product_ids = filter(None, map(lambda x:x[0], cr.fetchall()))
        for product in self.browse(cr, 1, product_ids):
            self.write(cr, 1, product.id, {'name':product.name_template})
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        #jon  add the field  name_cn  fo  copy  function
        name_cn = self.read(cr, uid, id, ['name_cn'], )['name_cn']
        if name_cn == u' - ':
            pass
        else:
            name_cn += r' (copy)'
            
        default.update({'default_code': '',  'name_cn':name_cn })
        return super(product_product, self).copy(cr, uid, id, default, context)

# -- Yannick new code -->
    def _get_categ(self, cr, uid, name='All Wines'):
        categ_ids = self.pool.get('product.category').search(cr, uid, [('name','ilike',name.lower())])
        return categ_ids and categ_ids[0] or False
        
    def onchange_categ_id(self, cr, uid, ids, categ_id):
        result = {}
        if categ_id:
            categ = self.pool.get('product.category').browse(cr, uid, categ_id)
            if 'wine' not in categ.complete_name.lower():
                result['vintage']      = False
                result['bottle_size']  = False
                result['alcoholic']    = False
                result['denomination'] = False
                result['region_id']    = False
                result['brand_id']     = False
                result['is_wine']      = False
                
                if 'service' in categ.name.lower():
                    result['type'] = 'service'
                else:
                    result['type'] = 'consumable'
            else:
                result['type'] = 'product'
                result['is_wine'] = True
        return result and {'value': result}
    
#    def onchange_type(self, cr, uid, ids, type):
#        result = {}
#        if type and type!= 'product':
#            result['vintage']      = False
#            result['bottle_size']  = False
#            result['alcoholic']    = False
#            result['denomination'] = False
#            result['region_id']    = False
#            result['brand_id']     = False
#            result['is_wine']      = False
#            
#            if type=='service':
#                result['categ_id'] = self._get_categ(cr, uid, name='Services')
#        
#            else:
#                result['categ_id'] = self._get_categ(cr, uid, name='Other products')
#                
#        else:
#            result['is_wine'] = True
#            result['categ_id'] = self._get_categ(cr, uid)
#        return result and {'value': result}
#

#===============================================================================
#    def _name_en(self, cursor, uid, ids, fields, arg, context=None, maxlength=2048):
#        result = {}
#        for product in self.browse(cursor, uid, ids, context=context):
#            cursor.execute("SELECT name, name_template FROM product_product WHERE id = %s" % (product.id))
#            name = cursor.fetchone()
#            if name and name[0]:
#                result[product.id] = name[0]
#            elif name and name[1]:
#                result[product.id] = name[1]
#        return result
# 
# 
#    def _name_sort_en(self, cursor, uid, ids, fields, arg, context=None, maxlength=2048):
#        result = {}
#        for product in self.browse(cursor, uid, ids, context=context):
#            result[product.id] = product.name_en
#        return result
#    
#    def _name_sort_cn(self, cursor, uid, ids, fields, arg, context=None, maxlength=2048):
#        result = {}
#        for product in self.browse(cursor, uid, ids, context=context):
#            result[product.id] = product.name_cn
#        return result
#    
#    
#    def _name_cn(self, cursor, uid, ids, fields, arg, context=None, maxlength=2048):
#        result = {}
#        for product in self.browse(cursor, uid, ids, context=context):
#            cursor.execute("SELECT name_template FROM product_product WHERE id = %s" % product.id)
#            t_name = cursor.fetchone()
#            t_ids = False
#            if t_name and t_name[0]:
#                value = re.sub("'", "''", t_name[0])
# 
#                cursor.execute("SELECT value FROM ir_translation WHERE lang = 'zh_CN' " + \
#                 " AND name ='product.product,name' AND src = '%s' AND type = 'model' AND res_id = %s"%(value, product.id))
#                t_ids = cursor.fetchone()
#            if not t_ids:
#                cursor.execute("SELECT value FROM ir_translation WHERE lang = 'zh_CN' " + \
#                 " AND name ='product.product,name' AND type = 'model' AND res_id = %s"%(product.id))
#                t_ids = cursor.fetchone()
#            if t_ids:
#                result[product.id] = t_ids[0]
#        return result
# 
# 
#    def _name_en_inv(self, cursor, user, id, name, value, arg, context=None):
#        """ All the logic is in the onchange_name_en()
#            Need to update the Translation table directly
#            If default language is English, then only need to save the name (useless)
#            If default language is Chinese, then we need to update the propduct_product table directly
#        """
#        if value:
#            value = re.sub("'", "''", str(value.encode('utf-8')))
#            cursor.execute("UPDATE product_product SET name = '%s' WHERE id = %s" % (value,id))
#    
#    
#    def onchange_name_en(self, cursor, uid, ids, name_en):
#        result = {}
#        if name_en:
#            #only do that in English
#            obj = self.pool.get('res.users').browse(cursor, uid, uid)
#            if obj.lang == 'en_US':
#                result['name'] = name_en
#        return result and {'value': result}
# 
# 
#    def _name_cn_inv(self, cursor, user, id, name, value, arg, context=None):
#        if value:
#            tr_pool = self.pool.get('ir.translation')
#            for product in self.browse(cursor, user, [id], context=context):
#                cursor.execute("SELECT name_template FROM product_product WHERE id = %s" % id)
#                t_name = cursor.fetchone()
#                t_ids = False
#                
#                # Do we have a source: 'src'
#                if t_name[0]:
#                    t_ids = tr_pool.search(cursor, user,
#                                     [('lang','=','zh_CN'),('name','=', 'product.product,name'),
#                                      ('type','=','model'),('src','=',t_name[0]),('res_id','=',id)])
#                
#                # It did not work with a source, lets try without a source
#                if not t_ids:
#                    t_ids = tr_pool.search(cursor, user,
#                                     [('lang','=','zh_CN'),('name','=', 'product.product,name'),
#                                      ('type','=','model'),('res_id','=',id)])
# 
#                # Did we find something, with or without a source
#                if t_ids:
#                    tr_pool.write(cursor, user, t_ids,{'value': value})
#                else:
#                    vals={
#                       'lang': 'zh_CN',
#                       'name': 'product.product,name',
#                       'type': 'model',
#                       'value': value,
#                       'res_id':id,
#                    }
#                    if t_name[0]:
#                        vals['src'] = t_name[0]
#                    tr_pool.create(cursor, user,vals)
#    
# 
    def get_default_code(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for p in self.browse(cr, uid, ids, context=context):
            default_code  = False
            main_supplier = False
            supplier_seq  = 999999
            bottle_size   = False
            pdt_sequence  = 1
            str_sequence  = False 
            tmp_sequence  = False
            brand = p.brand_id or False
            #LY for supplier in p.seller_ids:
            #LY    if supplier.sequence < supplier_seq:
            #LY        main_supplier = supplier.name.ref.upper()
            #LY        supplier_seq = supplier.sequence
            if brand and brand.code:
                default_code = ustr(brand.code.upper())
                #default_code += '.'
                #if p.vintage and len(str(p.vintage)) == 4:
                if  len(str(p.vintage)) == 4 or p.vintage == 'N.V.' :
                    if p.vintage == 'N.V.':
                        default_code += 'NV'
                        default_code += '.'
                    else:
                        default_code += ustr(p.vintage)[2:4]
                        default_code += '.'
                    
                    if p.bottle_size:
                        bottle_size = '%0.3f'  %    p.bottle_size
                        
                        bottle_size = bottle_size.replace('.', '')
                        bottle_size=bottle_size[0:-1]
 
                        if p.bottle_size >= 10:
                            bottle_size =bottle_size[0:2]+'L'
                        if len(bottle_size) == 1:
                            bottle_size += '00'
                        elif len(bottle_size) == 2:
                            bottle_size += '0'
                    
                        while (pdt_sequence <= 99 and not str_sequence):
                            tmp_sequence = default_code
                            tmp_sequence += str(pdt_sequence).rjust(2, '0')
                            #LYtmp_sequence += '.'
                            tmp_sequence += '%'#LYustr(bottle_size)
                            #print tmp_sequence
                            
                            if ( self.search(cr, uid, [('default_code','ilike',tmp_sequence)])  
                                 or self.search(cr, uid, [('default_code','ilike',tmp_sequence),('active','=',False)]) ):
                                pdt_sequence += 1
                            else:
                                str_sequence = str(pdt_sequence).rjust(2, '0')
                    
                        if str_sequence:
                            default_code += ustr(str_sequence)
                            #LY default_code += '.'
                            default_code += ustr(bottle_size)
                            self.write(cr, uid, [p.id], {'default_code': default_code}, context=context)
                        else:
                            default_code += ustr('xxx')
                            #LY default_code += '.'
                            default_code += ustr(bottle_size)
                            raise osv.except_osv(_('Error !'), _('Can not generate a Internal code for Product %s, because all the sequence has been used for %s') % (p.name,default_code))
                    else:
                        raise osv.except_osv(_('Error !'), _('Product %s has not a proper Bottle Size. The format should be x.xx in Liter, eg: 0.75') % (p.name,))
                else:
                        raise osv.except_osv(_('Error !'), _('Product %s has not a proper Vintage defined. The format should be YYYY, eg: 2001.') % (p.name,))
            else:
                raise osv.except_osv(_('Error !'), _('Product %s has no brand defined, or this brand doesn\'t have a Reference. Impossible to generate Internal code !') % (p.name,))
        return True
    
        
    def _get_is_wine(self, cr, uid, ids, fields, arg, context=None):
        result = {}
        categ_pool = self.pool.get('product.category')
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        for product in self.pool.get('product.product').browse(cr, uid, ids):
            is_wine = False
            current_categ = product.categ_id
                
            while not is_wine and current_categ:
                if 'wine' in current_categ.name.lower():
                    is_wine = True
                current_categ = current_categ.parent_id or False    
            result[product.id] = is_wine
        return result
        
    
    _columns = {
        'default_code': fields.char('Internal Reference', size=32),
        'name':         fields.char(_('Name'), size=128, translate=False, select=True),
#        'name_en':      fields.function(_name_en, method=True, type='char', size=128, string=_('Name EN'), fnct_inv=_name_en_inv,),
#        'name_cn':      fields.function(_name_cn, method=True, type='char', size=128, string=_('Name CN'), fnct_inv=_name_cn_inv,),
        'name_cn':      fields.char(_('Chinese Name'), size=128, translate=False, select=True),
#        'name_sort_en': fields.function(_name_sort_en, method=True, type='char', size=128, string=_('Name EN'), store={'product.product': (lambda self, cr, uid, ids, c={}: ids, ['name_en'], 10)}),
#        'name_sort_cn': fields.function(_name_sort_cn, method=True, type='char', size=128, string=_('Name CN'), store={'product.product': (lambda self, cr, uid, ids, c={}: ids, ['name_cn'], 10)}),
        #'name_sort_en': fields.function(_name_sort_en, method=True, type='char', size=128, string=_('Name EN'), store=True),
        #'name_sort_cn': fields.function(_name_sort_cn, method=True, type='char', size=128, string=_('Name CN'), store=True),
        'brand_id':     fields.many2one('product.brand', _('Brand')),
        'bottle_size':  fields.float(_('Bottle Size (L)'), digits=(2,3)),
        'alcoholic':    fields.float(_('Alcoholic %')),
        'denomination': fields.many2one('product.denomination', _('Denomination')),
        'region_id':    fields.many2one('res.country.state', _('Region'), domain=[('country_id.name','=','Italy')]),
        'vintage':      fields.char(_('Vintage'), size=4, help='Year format YYYY. Eg: 2001'),
        'is_wine':      fields.function(_get_is_wine, method=True, type='boolean', string='Is Wine ?', store=False), 
        
        #Jon old_code only used to update the record,not need to display 
        'old_code':     fields.char('old code', size=50, ),
    }
    _defaults = {
        'name_cn':  lambda *a : ' - ',
        'vintage':  lambda *a : 'N.V.',
        'is_wine':  lambda *a : True,
        'categ_id': lambda self, cr, uid, context: self._get_categ(cr, uid),
        'bottle_size':  lambda *a : 0.750,

    }
    

    def _check_vintage(self,cr,uid,ids,context=None):
        for p in self.browse(cr,uid,ids,context=context):
            #Temporarily changed
            #if (p.categ_id and 'wine' not in p.categ_id.complete_name.lower()) or (p.vintage and (re.search('^\d{4}$',p.vintage) or p.vintage == 'N/A')):
            if not p.categ_id or 'wine' not in p.categ_id.complete_name.lower() or not p.vintage or re.search('^\d{4}$',p.vintage) or p.vintage == 'N.V.':
                pass
            else:
                return False 
        return True
    
    _constraints = [
        (_check_vintage, 'Field vintage error,it must Year format YYYY. Eg: 2001 or default N.V.', ['vintage']),
    ]
    
    def name_get(self, cr, uid, ids, context=None):
        res = super(product_product, self).name_get(cr, uid, ids, context=context)
        new_res=[list(x) for x in res]
        
        if isinstance(ids,int) or isinstance(ids,long):
            ids=[ids]
 
        products = self.browse(cr, uid, ids)
        dic = {}
        for p in products:
            dic.update({p.id:p})
            
        for r in new_res:
            product = dic[r[0]]
            if product.brand_id and product.default_code:
                r[1] = r[1].replace(r']' ,  r']'+ ' ' + product.brand_id.name )
 
        new_res=[tuple(x) for x in new_res]
        
        return new_res

    #Jon , search product by brand name
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        results = super(product_product, self).name_search(cr, user, name, args=args ,operator=operator, context=context, limit=limit)
        
        # Get additional results using the brand_id.name
        ids = self.search(cr, user, [('brand_id.name', operator, name)],limit=limit, context=context)
        
        # Merge the results
        results = list(set(results + self.name_get(cr, user, ids, context)))
        return results
    

product_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
