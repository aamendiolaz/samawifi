# -*- coding: utf-8 -*-
import json
import logging
import re
from lxml import etree
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.move"


    qbo_invoice_id = fields.Char("QBO Invoice Id", copy=False, help="QBO Invoice Id")
    qbo_invoice_name = fields.Char("QBO Invoice Name", copy=False, help="QBO Invoice Name")


    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Set the correct domain for `partner_id`, depending on invoice type """
        result = super(AccountInvoice, self)._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        _logger.info("CONTEXT IS ---------------> {}".format(self._context))
        document_type = self._context.get('default_move_type')
        _logger.info("DOCUMENT TYPE IS --> {}".format(document_type))
        if view_type == 'form':
            doc = etree.XML(result['arch'])
            node = doc.xpath("//field[@name='partner_id']")[0]
            if document_type == 'in_invoice':
                _logger.info("DOCUMENT IS OF TYPE VENDOR BILL")
                node.set('domain', "[('supplier_rank', '>=', 1)]")
            if document_type == 'out_invoice':
                _logger.info("DOCUMENT IS OF TYPE CUSTOMER INVOICE")
                node.set('domain', "[('customer_rank', '>=', 1)]")
            if document_type == 'out_refund':
                _logger.info("DOCUMENT IS OF TYPE CUSTOMER CREDIT NOTE")
                node.set('domain', "[('customer_rank', '>=', 1)]")
            if document_type == 'in_refund':
                _logger.info("DOCUMENT IS OF TYPE  VENDOR CREDIT NOTE")
                node.set('domain', "[('supplier_rank', '>=', 1)]")
            result['arch'] = etree.tostring(doc)
        return result



    def check_account_id(self, cust):
        '''
        This function will check if for a particular product account exists or not
        '''

        if cust.get('Line'):
            for lines in cust.get('Line'):
                if 'SalesItemLineDetail' in lines and lines.get('SalesItemLineDetail').get('ItemRef').get('value'):
                    _logger.info("Checking for acc id ......")
                    res_product = self.env['product.product'].search(
                        [('qbo_product_id', '=', lines.get('SalesItemLineDetail').get('ItemRef').get('value'))])
                    if res_product:
                        if res_product.property_account_income_id or res_product.categ_id.property_account_income_categ_id:
                            _logger.info("Product/Category has income and expense account set ")
                            return True
                        else:
                            return False

    @api.model
    def check_if_lines_present(self, cust):
        if cust.get('Line'):
            for i in cust.get('Line'):
                if i.get('SalesItemLineDetail'):
                    return True
                else:
                    return False
        else:
            return False

    @api.model
    def check_if_lines_present_vendor_bill(self, cust):
        if 'Line' in cust and cust.get('Line'):
            for i in cust.get('Line'):
                if i.get('ItemBasedExpenseLineDetail') or i.get('AccountBasedExpenseLineDetail'):
                    if i.get('ItemBasedExpenseLineDetail'):
                        _logger.info("ItemBasedExpenseLineDetail-----------------> {}".format(i.get('ItemBasedExpenseLineDetail')))
                    elif i.get('AccountBasedExpenseLineDetail'):
                        _logger.info("AccountBasedExpenseLineDetail-----------------> {}".format(i.get('AccountBasedExpenseLineDetail')))
                    return True
                else:
                    _logger.info("NO ItemBasedExpenseLineDetail or NO AccountBasedExpenseLineDetail ")
                    return False
        else:
            return False

    def create_invoice_dict(self, cust, type):
        dict_i = {}
        if type == 'out_invoice' or type == 'out_refund':
            partner_type = 'CustomerRef'
        if type == 'in_invoice':
            partner_type = 'VendorRef'
        # print ("assssssssssssssssssssssssssssssssssssss",cust.get(partner_type).get('value'))
        if type == 'in_invoice':
            res_partner = self.env['res.partner'].search([('qbo_vendor_id', '=', cust.get(partner_type).get('value'))])
        else:
            res_partner = self.env['res.partner'].search([('qbo_customer_id', '=', cust.get(partner_type).get('value'))])

        _logger.info("Partner is ---> {}".format(res_partner))

        if res_partner:
            if cust.get('Id'):
                dict_i['partner_id'] = res_partner.id
                dict_i['qbo_invoice_id'] = cust.get('Id')
                dict_i['company_id'] = self.env.user.company_id.id
                dict_i['move_type'] = type

            if cust.get('CurrencyRef'):
                if cust.get('CurrencyRef').get('value'):
                    curr = cust.get('CurrencyRef').get('value')
                    _logger.info("Currency Value for invoice import ------> %s"%(curr))
                    currency = self.env['res.currency'].search([('name', '=', cust.get('CurrencyRef').get('value'))],
                                                               limit=1)
                    if not currency:
                        raise UserError(_("Please activate the currency %s") % (cust.get('CurrencyRef').get('value')))
                    
                    dict_i['currency_id'] = currency.id

            if res_partner.customer_rank:
                sale = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
                if sale:
                    dict_i['journal_id'] = sale.id
                else:
                    raise UserError("Please Define Sale Journal")
#                     sale = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
#                     if sale:
#                         dict_i['journal_id'] = sale.id

            if res_partner.supplier_rank:
                purchase = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
                if purchase:
                    dict_i['journal_id'] = purchase.id
                else:
                    raise UserError("Please Define Purchase Journal")
#                     purchase = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
#                     if purchase:
#                         dict_i['journal_id'] = purchase.id

            if cust.get('DocNumber'):
                dict_i['qbo_invoice_name'] = cust.get('DocNumber')
                # dict_i['number'] = cust.get('DocNumber')

            if cust.get('DueDate'):
                dict_i['invoice_date_due'] = cust.get('DueDate')

            if cust.get('TxnDate'):
                dict_i['invoice_date'] = cust.get('TxnDate')
        # if not dict_i.get('name'):
        #     raise UserError("Please define Invoice/Bill number for QBO Id "+str(cust.get('Id')))
        return dict_i

    def import_invoice(self):
        company = self.env['res.users'].search([('id', '=', 2)]).company_id

        if company.access_token:
            headers = {}
            headers['Authorization'] = 'Bearer ' + company.access_token
            headers['accept'] = 'application/json'
            headers['Content-Type'] = 'text/plain'

            query = "select * from invoice WHERE Id > '%s' order by Id STARTPOSITION %s MAXRESULTS %s " % (company.quickbooks_last_invoice_imported_id, company.start, company.limit)
            # query = "select * from invoice WHERE Id = '%s' order by Id STARTPOSITION %s MAXRESULTS %s " % (119, company.start, company.limit)
            data = requests.request('GET', company.url + str(company.realm_id) + "/query?query=" + query,headers=headers)

            self.create_invoice(data, 'out_invoice')

    def import_credit_memo(self):
        company = self.env['res.users'].search([('id', '=', 2)]).company_id

        if company.access_token:
            headers = {}
            headers['Authorization'] = 'Bearer ' + company.access_token
            headers['accept'] = 'application/json'
            headers['Content-Type'] = 'text/plain'

            query = "select * from CreditMemo WHERE Id > '%s' order by Id" % (company.quickbooks_last_credit_note_imported_id)

            data = requests.request('GET', company.url + str(company.realm_id) + "/query?query=" + query,
                                    headers=headers)
            self.create_invoice(data, 'out_refund')

    def import_vendor_bill(self):
        # print ("------------------------------------------------------------------------000000000000000000000000")
        company = self.env['res.users'].search([('id', '=', 2)]).company_id

        _logger.info("inside vendor bill ****************************")
        company = self.env['res.users'].search([('id', '=', 2)]).company_id
        if company.access_token:
            headers = {}
            headers['Authorization'] = 'Bearer ' + company.access_token
            headers['accept'] = 'application/json'
            headers['Content-Type'] = 'text/plain'

            query = "select * from Bill WHERE Id > '%s' order by Id" % (
                company.quickbooks_last_vendor_bill_imported_id)

            data = requests.request('GET', company.url + str(company.realm_id) + "/query?query=" + query, headers=headers)
            self.create_invoice(data, 'in_invoice')

    def create_invoice(self, data, type='out_invoice'):

        # print ("\n\n------------------------------------------------------------------------1111111111111111111",data,data.text,type)
        company = self.env['res.users'].search([('id', '=', 2)]).company_id
        if data:
            recs = []
            parsed_data = json.loads(str(data.text))
            count = 0
            if parsed_data:
                if type == 'out_invoice':
                    get_data_for = 'Invoice'
                elif type == 'out_refund':
                    get_data_for = 'CreditMemo'
                if type == 'in_invoice':
                    get_data_for = 'Bill'

                if parsed_data.get('QueryResponse') and parsed_data.get('QueryResponse').get(get_data_for):
                    for cust in parsed_data.get('QueryResponse').get(get_data_for):
                        return_val = self.check_account_id(cust)
                        # print("----- in vendor bill--",)
                        # if return_val and type != 'in_invoice':
                        #     if type == 'out_invoice' or type == 'out_refund':
                        #         line_present = self.check_if_lines_present(cust)
                        #         _logger.info('ORDER LINES PRESENT IN INVOICE :: %s', line_present)
                        #     if not line_present:
                        #         continue
                        # elif not return_val and type == 'in_invoice':
                        #     if type == 'in_invoice':
                        #         line_present = self.check_if_lines_present_vendor_bill(cust)
                        #         _logger.info('ORDER LINES PRESENT IN BILL :: %s', line_present)
                        #     if not line_present:
                        #         continue

                        print (" ------------------------------------------------------------------ 111")
                        count = count + 1;
                        account_invoice = self.env['account.move'].search([('qbo_invoice_id', '=', cust.get('Id'))])
                        _logger.info("ACC invoice is -----> {}".format(account_invoice))

                        if not account_invoice:
                            _logger.info("Attempting for Invoice Creation")
                            _logger.info("QBO obj is -----> {}".format(cust))
                            dict_i = self.create_invoice_dict(cust, type)
                            dict_i['invoice_line_ids'] = []
                            invoice_obj = self.env['res.partner'].search([('id', '=', dict_i.get('partner_id'))],
                                                                         limit=1)
                            invoice_line = self.odoo_create_invoice_line_dict(cust, invoice_obj, type,dict_i.get('qbo_invoice_id'))
                            for k in invoice_line:
                                dict_i['invoice_line_ids'].append((0, 0, k))

                            _logger.info("Dictionary for creation is ---> {}".format(dict_i))
                            invoice_obj = self.env['account.move'].create(dict_i)
                            _logger.info("Invoice obj is -----> {}".format(invoice_obj))

                            if invoice_obj:

                                invoice_obj.action_post()
                                # invoice_line = self.create_invoice_line_dict(cust, invoice_obj, type)
                                # _logger.info("Attempting for Invoice Line Creation!")
                                # create_p = self.env['account.move.line'].create(invoice_line)
                                # if create_p:
                                self._cr.commit()

                                _logger.info("Invoice Line Committed!!!")

                                if type == 'out_invoice':
                                    company.quickbooks_last_invoice_imported_id = cust.get('Id')
                                elif type == 'out_refund':
                                    company.quickbooks_last_credit_note_imported_id = cust.get('Id')
                                elif type == 'in_invoice':
                                    company.quickbooks_last_vendor_bill_imported_id = cust.get('Id')
                                else:

                                    _logger.error("Invoice line was not created.")
                            else:
                                _logger.error("NO ACCOUNT ID WAS ATTACHED !")


                        else:
                            _logger.info("All data seems to be imported successfully!")
                            # raise UserError("All data seems to be imported!")
#                                 _logger.info("Attempting to update the invoice!")
#                                 print("contes1!!!!!!!!!!!!!!!!!!!!!!!!11",self._context)
# 
#                                 dict_i = self.create_invoice_dict(cust, type)
#                                 _logger.info("Dictionary for updation is ---> {}".format(dict_i))
#                                 write_inv = account_invoice.write(dict_i)
#                                 if write_inv:
#                                     _logger.info('Invoice Updated Successfully..!! :: %s', cust.get('Id'))
# #                                     invoice_line = self.create_invoice_line_dict(cust, account_invoice, type)
#                                     invoice_line = self.update_invoice_line_dict(cust,account_invoice,type)
#                                     _logger.info("Dictionary for updating move line is ---> {}".format(invoice_line))
#                                     for line in invoice_line:
#                                         print("line us 1!!!!!!!!!!",line)
#                                         write_p = self.env['account.move.line'].write(invoice_line)
#                                         if write_p:
#                                             self._cr.commit()
#                                             _logger.info("Invoice Line Updated!!!")
#                                             if type == 'out_invoice':
#                                                 company.quickbooks_last_invoice_imported_id = cust.get('Id')
#                                             elif type == 'out_refund':
#                                                 company.quickbooks_last_credit_note_imported_id = cust.get('Id')
#                                             elif type == 'in_invoice':
#                                                 company.quickbooks_last_vendor_bill_imported_id = cust.get('Id')
#                                         else:
#      
#                                             _logger.error("Invoice line was not updated.")
#                                 else:
#                                     _logger.error("NO ACCOUNT ID WAS ATTACHED !")
                else:
                    raise UserError("It seems that all of the data is already imported!")
                    _logger.warning(_('Empty data'))

    def odoo_create_invoice_line_dict(self, cust, invoice_obj, type,qbo_inv_id=''):
        _logger.info("Attempting to create Invoice Line Dictionary")
        inv_line_data = []
        for i in cust.get('Line'):
            dict_ol = {}
            dict_col = {}
            dict_tol = {}

            if type == 'out_invoice' or type == 'out_refund':
                get_data_for = 'SalesItemLineDetail'
            else:
                get_data_for = 'ItemBasedExpenseLineDetail'

            if type == 'out_invoice' or type == 'out_refund':
                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                    if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):

                        qb_tax_id = cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value')
                        record = self.env['account.tax']
                        tax = record.search([('qbo_tax_id', '=', qb_tax_id), ('type_tax_use', '=', 'sale')])
                        if tax:
                            custom_tax_id = [[6, False, [tax.id]]]
                            # [[6, False, [2]]]
                            _logger.info("TAX ATTACHED {}".format(tax.id))
                        else:
                            custom_tax_id = [[6, False, []]]
                else:
                    custom_tax_id = [[6, False, []]]
            else:
                custom_tax_id = [[6, False, []]]

            if i.get('SalesItemLineDetail'):
                if i.get('SalesItemLineDetail').get('TaxCodeRef'):
                    if i.get('SalesItemLineDetail').get('TaxCodeRef').get('value'):

                        qb_tax_id = i.get('SalesItemLineDetail').get('TaxCodeRef').get('value')
                        record = self.env['account.tax']
                        tax = record.search([('qbo_tax_id', '=', qb_tax_id), ('type_tax_use', '=', 'sale')])

                        if tax:
                            dict_ol['itax_ids'] = [[6, False, [tax.id]]]

                            # [[6, False, [2]]]
                            _logger.info("TAX ATTACHED {}".format(tax.id))
                    else:
                        dict_ol['tax_ids'] = [[6, False, []]]
                else:
                    dict_ol['tax_ids'] = [[6, False, []]]

            else:
                dict_ol['tax_ids'] = [[6, False, []]]
            if i.get('Id') and not i.get(get_data_for) and not 'AccountBasedExpenseLineDetail' in i:
                dict_ol.clear()
                dict_col.clear()
                dict_tol.clear()

                dict_ol['qb_id'] = int(i.get('Id'))


                # ---------------------------TAX--------------------------------------
                if 'TxnTaxDetail' in cust and cust.get('TxnTaxDetail'):

                    if cust.get('TxnTaxDetail').get('TaxLine'):

                        if cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail'):
                            tax_val = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('TaxRateRef').get('value')


                            if tax_val:
                                record = self.env['account.tax']
                                tax = record.search([('qbo_tax_rate_id', '=', tax_val)], limit=1)

                                if tax:
                                    dict_ol['tax_ids'] = [[6, False, [tax.id]]]

                            else:
                                # dict_ol['invoice_line_tax_ids'] = None
                                dict_ol['tax_ids'] = [[6, False, []]]

                            if cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('NetAmountTaxable'):
                                dict_ol['price_unit'] = float(cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('NetAmountTaxable'))
                            else:
                                dict_ol['price_unit'] = 0

                dict_ol['quantity'] = 1.0


                if i.get('Description'):

                    dict_ol['name'] = i.get('Description')

                else:
                    dict_ol['name'] = 'NA'

                if type=='in_invoice':
                    company = self.env['res.users'].search([('id', '=', 2)]).company_id
                    if company:
                        if company.qb_expense_account:
                            dict_ol['account_id'] = company.qb_expense_account.id
                        else:
                            raise UserError("Please set the Expense Account in QBO Configuration")

                if type == 'in_invoice':
                    company = self.env['res.users'].search([('id', '=', 2)]).company_id
                    if company:
                        if company.qb_expense_account:
                            dict_ol['account_id'] = company.qb_expense_account.id
                        else:
                            raise UserError("Please set the Expense Account in QBO Configuration")
                if type == 'out_invoice' or type=='out_refund':
                    company = self.env['res.users'].search([('id', '=', 2)]).company_id
                    if company:
                        if company.qb_income_account:
                            dict_ol['account_id'] = company.qb_income_account.id
                        else:
                            raise UserError("Please set the Income Account in QBO Configuration")

                if 'account_id' in dict_ol :
                    _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                    inv_line_data.append(dict_ol)

            if 'AccountBasedExpenseLineDetail' in i and i.get('AccountBasedExpenseLineDetail'):
                res_account = self.env['account.account'].search(
                    [('qbo_id', '=', i.get('AccountBasedExpenseLineDetail').get('AccountRef').get('value'))])
                if res_account:

                    dict_ol.clear()
                    dict_col.clear()
                    dict_tol.clear()

                    # Move Id for Product Line & Customer Account Receivable Line
                    # dict_ol['move_id'] = invoice_obj.id
                    # dict_col['move_id'] = invoice_obj.id
                    # dict_tol['move_id'] = invoice_obj.id

                    # Product Id for Product Line & Customer Account Receivable Line
                    #                     dict_ol['product_id'] = res_product.id
                    #                     dict_col['product_id'] = False
                    #                     dict_tol['product_id'] = False

                    # Parent Id for Product Line & Customer Account Receivable Line
                    dict_ol['partner_id'] = invoice_obj.id
                    dict_col['partner_id'] = invoice_obj.id
                    dict_tol['partner_id'] = invoice_obj.id

                    # Exclude Receivable from Invoice Tab
                    dict_ol['exclude_from_invoice_tab'] = False
                    dict_col['exclude_from_invoice_tab'] = True
                    dict_tol['exclude_from_invoice_tab'] = True

                    # Quickbooks Id for Product Line & Customer Account Receivable Line
                    if i.get('Id'):
                        dict_ol['qb_id'] = int(i.get('Id'))
                        dict_col['qb_id'] = int(i.get('Id'))
                        dict_tol['qb_id'] = int(i.get('Id'))

                    # ---------------------------TAX--------------------------------------
                    if i.get('AccountBasedExpenseLineDetail').get('TaxCodeRef'):
                        tax_val = i.get('AccountBasedExpenseLineDetail').get('TaxCodeRef').get('value')
                        tax=''
                        if type == 'in_invoice':

                            record = self.env['account.tax']
                            tax = record.search([('qbo_tax_id', '=', tax_val), ('type_tax_use', '=', 'purchase')], limit=1)

                        else:

                            record = self.env['account.tax']
                            tax = record.search([('qbo_tax_id', '=', tax_val), ('type_tax_use', '=', 'sale')],
                                                    limit=1)

                        if tax:
                            dict_ol['tax_ids'] = [[6, False, [tax.id]]]

                        else:
                            # dict_ol['invoice_line_tax_ids'] = None
                            dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]

                    if i.get('AccountBasedExpenseLineDetail').get('Qty'):
                        dict_ol['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')
                        dict_col['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')
                        dict_tol['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')

                    else:
                        dict_ol['quantity'] = 1.0
                        dict_col['quantity'] = 1.0
                        dict_tol['quantity'] = 1.0

                    if i.get('AccountBasedExpenseLineDetail').get('UnitPrice'):
                        dict_ol['price_unit'] = float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice'))
                        dict_col['price_unit'] = -(float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice')))

                        dict_ol['credit'] = abs(
                            dict_ol['quantity'] * float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice')))
                        dict_ol['debit'] = 0

                        dict_col['credit'] = 0
                        dict_col['debit'] = abs(
                            dict_col['quantity'] * float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice')))

                    else:
                        if not i.get('AccountBasedExpenseLineDetail').get('Qty'):
                            dict_ol['price_unit'] = float(i.get('Amount'))
                            dict_col['price_unit'] = -(float(i.get('Amount')))

                            dict_ol['credit'] = abs(dict_ol['quantity'] * float(i.get('Amount')))
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = abs(dict_col['quantity'] * float(i.get('Amount')))
                        else:
                            dict_ol['price_unit'] = 0
                            dict_col['price_unit'] = 0

                            dict_ol['credit'] = 0
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = 0

                    if i.get('Description'):
                        dict_ol['name'] = i.get('Description')
                        dict_col['name'] = i.get('Description')
                        dict_tol['name'] = i.get('Description')
                    else:
                        dict_ol['name'] = 'NA'
                        dict_col['name'] = 'NA'
                        dict_tol['name'] = 'NA'

                    if type == 'out_invoice' or type == 'out_refund':
                        if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                tax_amount = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get(
                                    'TaxPercent')
                                dict_tol['price_unit'] = float(
                                    dict_ol['quantity'] * dict_ol['price_unit'] * float(tax_amount / 100))
                                dict_tol['credit'] = abs(dict_tol['price_unit'])
                                dict_tol['debit'] = 0

                                dict_col['debit'] += abs(dict_tol['credit'])
                            else:
                                dict_tol['price_unit'] = 0
                                dict_tol['credit'] = 0
                                dict_tol['debit'] = 0

                        else:
                            dict_tol['price_unit'] = 0
                            dict_tol['credit'] = 0
                            dict_tol['debit'] = 0
                    else:
                        dict_tol['price_unit'] = 0
                        dict_tol['credit'] = 0
                        dict_tol['debit'] = 0

                    if type == 'out_refund' or type == 'in_invoice':
                        dict_ol['credit'], dict_ol['debit'] = dict_ol['debit'], dict_ol['credit']
                        dict_col['credit'], dict_col['debit'] = dict_col['debit'], dict_col['credit']
                        dict_tol['credit'], dict_tol['debit'] = dict_tol['debit'], dict_tol['credit']

                    if res_account:
                        dict_ol['account_id'] = res_account.id
                        _logger.info("PRODUCT has income account set")

                    if invoice_obj.property_account_receivable_id:
                        dict_col['account_id'] = invoice_obj.property_account_receivable_id.id
                        dict_tol['account_id'] = invoice_obj.property_account_receivable_id.id

                    if 'account_id' in dict_ol and 'account_id' in dict_col:
                        _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                        inv_line_data.append(dict_ol)
                        inv_line_data.append(dict_col)
                        if type == 'out_invoice' or type == 'out_refund':
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                                dict_ol['tax_repartition_line_id'] = False
                                dict_col['tax_repartition_line_id'] = False
                                #
                                #                                 tax_repartition_line_id = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax')],limit=1)
                                dict_tol['tax_repartition_line_id'] = False
                                #                                 dict_tol['tax_repartition_line_id'] = tax_repartition_line_id.id

                                dict_ol['tax_base_amount'] = 0
                                dict_col['tax_base_amount'] = 0
                                dict_tol['tax_base_amount'] = dict_ol['quantity'] * dict_ol['price_unit']

                                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                    inv_line_data.append(dict_tol)

            if i.get(get_data_for):
                res_product = self.env['product.product'].search(
                    [('qbo_product_id', '=', i.get(get_data_for).get('ItemRef').get('value'))])
                if res_product:

                    dict_ol.clear()
                    dict_col.clear()
                    dict_tol.clear()

                    # Move Id for Product Line & Customer Account Receivable Line
                    # dict_ol['move_id'] = invoice_obj.id
                    # dict_col['move_id'] = invoice_obj.id
                    # dict_tol['move_id'] = invoice_obj.id

                    # Product Id for Product Line & Customer Account Receivable Line
                    dict_ol['product_id'] = res_product.id
                    dict_col['product_id'] = False
                    dict_tol['product_id'] = False

                    # Parent Id for Product Line & Customer Account Receivable Line
                    dict_ol['partner_id'] = invoice_obj.id
                    dict_col['partner_id'] = invoice_obj.id
                    dict_tol['partner_id'] = invoice_obj.id

                    # Exclude Receivable from Invoice Tab
                    dict_ol['exclude_from_invoice_tab'] = False
                    dict_col['exclude_from_invoice_tab'] = True
                    dict_tol['exclude_from_invoice_tab'] = True

                    # Quickbooks Id for Product Line & Customer Account Receivable Line
                    if i.get('Id'):
                        dict_ol['qb_id'] = int(i.get('Id'))
                        dict_col['qb_id'] = int(i.get('Id'))
                        dict_tol['qb_id'] = int(i.get('Id'))

                    # ---------------------------TAX--------------------------------------
                    if i.get(get_data_for).get('TaxCodeRef'):
                        tax_val = i.get(get_data_for).get('TaxCodeRef').get('value')
                        if tax_val == 'TAX':
                            #                             dict_ol['invoice_line_tax_ids'] = custom_tax_id
                            dict_ol['tax_ids'] = custom_tax_id
                            #                             print("custom tax id!!!!!!!!!!!!!!!!!!!!!!!!",custom_tax_id)
                            #                             dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]
                        else:
                            # dict_ol['invoice_line_tax_ids'] = None
                            dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]

                    if i.get(get_data_for).get('Qty'):
                        dict_ol['quantity'] = i.get(get_data_for).get('Qty')
                        dict_col['quantity'] = i.get(get_data_for).get('Qty')
                        dict_tol['quantity'] = i.get(get_data_for).get('Qty')

                    else:
                        dict_ol['quantity'] = 0
                        dict_col['quantity'] = 0
                        dict_tol['quantity'] = 0

                    if i.get(get_data_for).get('UnitPrice'):
                        dict_ol['price_unit'] = float(i.get(get_data_for).get('UnitPrice'))
                        dict_col['price_unit'] = -(float(i.get(get_data_for).get('UnitPrice')))

                        dict_ol['credit'] = abs(dict_ol['quantity'] * float(i.get(get_data_for).get('UnitPrice')))
                        dict_ol['debit'] = 0

                        dict_col['credit'] = 0
                        dict_col['debit'] = abs(dict_col['quantity'] * float(i.get(get_data_for).get('UnitPrice')))

                    else:
                        if not i.get(get_data_for).get('Qty'):
                            dict_ol['price_unit'] = float(i.get('Amount'))
                            dict_col['price_unit'] = -(float(i.get('Amount')))

                            dict_ol['credit'] = abs(dict_ol['quantity'] * float(i.get('Amount')))
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = abs(dict_col['quantity'] * float(i.get('Amount')))
                        else:
                            dict_ol['price_unit'] = 0
                            dict_col['price_unit'] = 0

                            dict_ol['credit'] = 0
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = 0

                    if i.get('Description'):
                        dict_ol['name'] = i.get('Description')
                        dict_col['name'] = i.get('Description')
                        dict_tol['name'] = i.get('Description')
                    else:
                        dict_ol['name'] = 'NA'
                        dict_col['name'] = 'NA'
                        dict_tol['name'] = 'NA'

                    if type == 'out_invoice' or type == 'out_refund':
                        if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                tax_amount = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get(
                                    'TaxPercent')
                                dict_tol['price_unit'] = float(
                                    dict_ol['quantity'] * dict_ol['price_unit'] * float(tax_amount / 100))
                                dict_tol['credit'] = abs(dict_tol['price_unit'])
                                dict_tol['debit'] = 0

                                dict_col['debit'] += abs(dict_tol['credit'])
                            else:
                                dict_tol['price_unit'] = 0
                                dict_tol['credit'] = 0
                                dict_tol['debit'] = 0

                        else:
                            dict_tol['price_unit'] = 0
                            dict_tol['credit'] = 0
                            dict_tol['debit'] = 0
                    else:
                        dict_tol['price_unit'] = 0
                        dict_tol['credit'] = 0
                        dict_tol['debit'] = 0

                    if type == 'out_refund' or type == 'in_invoice':
                        dict_ol['credit'], dict_ol['debit'] = dict_ol['debit'], dict_ol['credit']
                        dict_col['credit'], dict_col['debit'] = dict_col['debit'], dict_col['credit']
                        dict_tol['credit'], dict_tol['debit'] = dict_tol['debit'], dict_tol['credit']

                    if res_product.property_account_income_id:
                        dict_ol['account_id'] = res_product.property_account_income_id.id
                        _logger.info("PRODUCT has income account set")
                    else:
                        dict_ol['account_id'] = res_product.categ_id.property_account_income_categ_id.id
                        _logger.info("No Income account was set, taking from product category..")

                    if invoice_obj.property_account_receivable_id:
                        dict_col['account_id'] = invoice_obj.property_account_receivable_id.id
                        dict_tol['account_id'] = invoice_obj.property_account_receivable_id.id
                    else:
                        raise UserError("Account Receivable not set for Customer ---> {}".format(invoice_obj.name))
                        _logger.info("No Property Account Receivable Set!")

                    _logger.info("DICT COL IS ---> {}".format(dict_col))
                    _logger.info("DICT OL IS ---> {}".format(dict_ol))
                    _logger.info("DICT TOL IS ---> {}".format(dict_tol))
                    if 'account_id' in dict_ol and 'account_id' in dict_col:
                        _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                        inv_line_data.append(dict_ol)
                        inv_line_data.append(dict_col)
                        _logger.info("INVOICE LINE DATA FOR NOW IS ---> {}".format(inv_line_data))
                        if type == 'out_invoice' or type == 'out_refund':
                            _logger.info("Getting Additional Details!")
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                                _logger.info("Getting Transaction Details!")
                                dict_ol['tax_repartition_line_id'] = False
                                dict_col['tax_repartition_line_id'] = False

                                #                                 tax_repartition_line_id = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax')],limit=1)
                                # #                                 dict_tol['tax_repartition_line_id'] = tax_repartition_line_id.id
                                dict_tol['tax_repartition_line_id'] = False
                                dict_ol['tax_base_amount'] = 0
                                dict_col['tax_base_amount'] = 0
                                dict_tol['tax_base_amount'] = dict_ol['quantity'] * dict_ol['price_unit']

                                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                    inv_line_data.append(dict_tol)
                                else:
                                    _logger.info("TAX Code Reference Value Not Found!")
                    else:
                        _logger.info("Account ID not found in the dictionary!")
                else:
                    raise UserError('Product ' + str(
                        i.get(get_data_for).get('ItemRef').get(
                            'name')) + ' is not defined in Odoo. Invoice type '+str(type)+' Name :' + cust.get(
                        'DocNumber'))



        _logger.info("INVOICE LINE DATA SENDING FOR CREATION IS --BEFORE -> {}".format(inv_line_data))
        for j in inv_line_data:

            if j.get('credit') and j.get('debit'):
                del j['credit']
                del j['debit']
            if 'product_id' in j:
                if j.get('quantity')==0:
                    j['quantity']=1
                if not j.get('product_id'):
                    inv_line_data.remove(j)
        _logger.info("INVOICE LINE DATA SENDING FOR CREATION IS --LATER -> {}".format(inv_line_data))

        return inv_line_data


    def create_invoice_line_dict(self, cust, invoice_obj, type):
        _logger.info("Attempting to create Invoice Line Dictionary")
        inv_line_data = []
        for i in cust.get('Line'):
            dict_ol = {}
            dict_col = {}
            dict_tol = {}

            if type == 'out_invoice' or type == 'out_refund':
                get_data_for = 'SalesItemLineDetail'
            else:
                get_data_for = 'ItemBasedExpenseLineDetail'

            if type == 'out_invoice' or type == 'out_refund':
                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                    if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):

                        qb_tax_id = cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value')
                        record = self.env['account.tax']
                        tax = record.search([('qbo_tax_id', '=', qb_tax_id)])
                        if tax:
                            custom_tax_id = [[6, False, [tax.id]]]
                            # [[6, False, [2]]]
                            _logger.info("TAX ATTACHED {}".format(tax.id))
                        else:
                            custom_tax_id = [[6, False, []]]
                else:
                    custom_tax_id = [[6, False, []]]
            else:
                custom_tax_id = [[6, False, []]]
                
                
            if 'AccountBasedExpenseLineDetail' in i and i.get('AccountBasedExpenseLineDetail'):
                res_account = self.env['account.account'].search([('qbo_id', '=', i.get('AccountBasedExpenseLineDetail').get('AccountRef').get('value'))])
                if res_account:

                    dict_ol.clear()
                    dict_col.clear()
                    dict_tol.clear()

                    # Move Id for Product Line & Customer Account Receivable Line
                    dict_ol['move_id'] = invoice_obj.id
                    dict_col['move_id'] = invoice_obj.id
                    dict_tol['move_id'] = invoice_obj.id

                    # Product Id for Product Line & Customer Account Receivable Line
#                     dict_ol['product_id'] = res_product.id
#                     dict_col['product_id'] = False
#                     dict_tol['product_id'] = False

                    # Parent Id for Product Line & Customer Account Receivable Line
                    dict_ol['partner_id'] = invoice_obj.partner_id.id
                    dict_col['partner_id'] = invoice_obj.partner_id.id
                    dict_tol['partner_id'] = invoice_obj.partner_id.id

                    # Exclude Receivable from Invoice Tab
                    dict_ol['exclude_from_invoice_tab'] = False
                    dict_col['exclude_from_invoice_tab'] = True
                    dict_tol['exclude_from_invoice_tab'] = True

                    # Quickbooks Id for Product Line & Customer Account Receivable Line
                    if i.get('Id'):
                        dict_ol['qb_id'] = int(i.get('Id'))
                        dict_col['qb_id'] = int(i.get('Id'))
                        dict_tol['qb_id'] = int(i.get('Id'))

                    # ---------------------------TAX--------------------------------------
                    if i.get('AccountBasedExpenseLineDetail').get('TaxCodeRef'):
                        tax_val = i.get('AccountBasedExpenseLineDetail').get('TaxCodeRef').get('value')
                        if tax_val == 'TAX':
                            dict_ol['tax_ids'] = custom_tax_id
#                             print("CUSTOM TAX ID IS -----------",custom_tax_id)
#                             dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]
                        else:
                            # dict_ol['invoice_line_tax_ids'] = None
                            dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]
                            

                    if i.get('AccountBasedExpenseLineDetail').get('Qty'):
                        dict_ol['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')
                        dict_col['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')
                        dict_tol['quantity'] = i.get('AccountBasedExpenseLineDetail').get('Qty')

                    else:
                        dict_ol['quantity'] = 1.0
                        dict_col['quantity'] = 1.0
                        dict_tol['quantity'] = 1.0

                    if i.get('AccountBasedExpenseLineDetail').get('UnitPrice'):
                        dict_ol['price_unit'] = float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice'))
                        dict_col['price_unit'] = -(float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice')))

                        dict_ol['credit'] = dict_ol['quantity'] * float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice'))
                        dict_ol['debit'] = 0

                        dict_col['credit'] = 0
                        dict_col['debit'] = dict_col['quantity'] * float(i.get('AccountBasedExpenseLineDetail').get('UnitPrice'))

                    else:
                        if not i.get('AccountBasedExpenseLineDetail').get('Qty'):
                            dict_ol['price_unit'] = float(i.get('Amount'))
                            dict_col['price_unit'] = -(float(i.get('Amount')))

                            dict_ol['credit'] = dict_ol['quantity'] * float(i.get('Amount'))
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = dict_col['quantity'] * float(i.get('Amount'))
                        else:
                            dict_ol['price_unit'] = 0
                            dict_col['price_unit'] = 0

                            dict_ol['credit'] = 0
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = 0

                    if i.get('Description'):
                        dict_ol['name'] = i.get('Description')
                        dict_col['name'] = i.get('Description')
                        dict_tol['name'] = i.get('Description')
                    else:
                        dict_ol['name'] = 'NA'
                        dict_col['name'] = 'NA'
                        dict_tol['name'] = 'NA'

                    if type == 'out_invoice' or type == 'out_refund':
                        if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                tax_amount = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('TaxPercent')
                                dict_tol['price_unit'] = float(dict_ol['quantity'] * dict_ol['price_unit'] * float(tax_amount/100))
                                dict_tol['credit'] = dict_tol['price_unit']
                                dict_tol['debit'] = 0

                                dict_col['debit'] += dict_tol['credit']
                            else:
                                dict_tol['price_unit'] = 0
                                dict_tol['credit'] = 0
                                dict_tol['debit'] = 0

                        else:
                            dict_tol['price_unit'] = 0
                            dict_tol['credit'] = 0
                            dict_tol['debit'] = 0
                    else:
                        dict_tol['price_unit'] = 0
                        dict_tol['credit'] = 0
                        dict_tol['debit'] = 0

                    if type == 'out_refund' or type == 'in_invoice':
                        dict_ol['credit'],dict_ol['debit'] = dict_ol['debit'],dict_ol['credit']
                        dict_col['credit'],dict_col['debit'] = dict_col['debit'],dict_col['credit']
                        dict_tol['credit'],dict_tol['debit'] = dict_tol['debit'],dict_tol['credit']

                    if res_account:
                        dict_ol['account_id'] = res_account.id
                        _logger.info("PRODUCT has income account set")

                    if invoice_obj.partner_id.property_account_receivable_id:
                        dict_col['account_id'] = invoice_obj.partner_id.property_account_receivable_id.id
                        dict_tol['account_id'] = invoice_obj.partner_id.property_account_receivable_id.id

                    if 'account_id' in dict_ol and 'account_id' in dict_col:
                        _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                        inv_line_data.append(dict_ol)
                        inv_line_data.append(dict_col)
                        if type == 'out_invoice' or type == 'out_refund':
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                                dict_ol['tax_repartition_line_id'] = False
                                dict_col['tax_repartition_line_id'] = False
# 
#                                 tax_repartition_line_id = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax')],limit=1)
                                dict_tol['tax_repartition_line_id'] = False
#                                 dict_tol['tax_repartition_line_id'] = tax_repartition_line_id.id

                                dict_ol['tax_base_amount'] = 0
                                dict_col['tax_base_amount'] = 0
                                dict_tol['tax_base_amount'] = dict_ol['quantity'] * dict_ol['price_unit']

                                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                    inv_line_data.append(dict_tol)
                    

            if i.get(get_data_for):
                res_product = self.env['product.product'].search([('qbo_product_id', '=', i.get(get_data_for).get('ItemRef').get('value'))])
                if res_product:

                    dict_ol.clear()
                    dict_col.clear()
                    dict_tol.clear()

                    # Move Id for Product Line & Customer Account Receivable Line
                    dict_ol['move_id'] = invoice_obj.id
                    dict_col['move_id'] = invoice_obj.id
                    dict_tol['move_id'] = invoice_obj.id

                    # Product Id for Product Line & Customer Account Receivable Line
                    dict_ol['product_id'] = res_product.id
                    dict_col['product_id'] = False
                    dict_tol['product_id'] = False

                    # Parent Id for Product Line & Customer Account Receivable Line
                    dict_ol['partner_id'] = invoice_obj.partner_id.id
                    dict_col['partner_id'] = invoice_obj.partner_id.id
                    dict_tol['partner_id'] = invoice_obj.partner_id.id

                    # Exclude Receivable from Invoice Tab
                    dict_ol['exclude_from_invoice_tab'] = False
                    dict_col['exclude_from_invoice_tab'] = True
                    dict_tol['exclude_from_invoice_tab'] = True

                    # Quickbooks Id for Product Line & Customer Account Receivable Line
                    if i.get('Id'):
                        dict_ol['qb_id'] = int(i.get('Id'))
                        dict_col['qb_id'] = int(i.get('Id'))
                        dict_tol['qb_id'] = int(i.get('Id'))

                    # ---------------------------TAX--------------------------------------
                    if i.get(get_data_for).get('TaxCodeRef'):
                        tax_val = i.get(get_data_for).get('TaxCodeRef').get('value')
                        if tax_val == 'TAX':
#                             dict_ol['invoice_line_tax_ids'] = custom_tax_id
                            dict_ol['tax_ids'] = custom_tax_id
#                             print("custom tax id!!!!!!!!!!!!!!!!!!!!!!!!",custom_tax_id)
#                             dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]
                        else:
                            # dict_ol['invoice_line_tax_ids'] = None
                            dict_ol['tax_ids'] = [[6, False, []]]
                            dict_col['tax_ids'] = [[6, False, []]]
                            dict_tol['tax_ids'] = [[6, False, []]]

                    if i.get(get_data_for).get('Qty'):
                        dict_ol['quantity'] = i.get(get_data_for).get('Qty')
                        dict_col['quantity'] = i.get(get_data_for).get('Qty')
                        dict_tol['quantity'] = i.get(get_data_for).get('Qty')

                    else:
                        dict_ol['quantity'] = 0
                        dict_col['quantity'] = 0
                        dict_tol['quantity'] = 0

                    if i.get(get_data_for).get('UnitPrice'):
                        dict_ol['price_unit'] = float(i.get(get_data_for).get('UnitPrice'))
                        dict_col['price_unit'] = -(float(i.get(get_data_for).get('UnitPrice')))

                        dict_ol['credit'] = dict_ol['quantity'] * float(i.get(get_data_for).get('UnitPrice'))
                        dict_ol['debit'] = 0

                        dict_col['credit'] = 0
                        dict_col['debit'] = dict_col['quantity'] * float(i.get(get_data_for).get('UnitPrice'))

                    else:
                        if not i.get(get_data_for).get('Qty'):
                            dict_ol['price_unit'] = float(i.get('Amount'))
                            dict_col['price_unit'] = -(float(i.get('Amount')))

                            dict_ol['credit'] = dict_ol['quantity'] * float(i.get('Amount'))
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = dict_col['quantity'] * float(i.get('Amount'))
                        else:
                            dict_ol['price_unit'] = 0
                            dict_col['price_unit'] = 0

                            dict_ol['credit'] = 0
                            dict_ol['debit'] = 0

                            dict_col['credit'] = 0
                            dict_col['debit'] = 0

                    if i.get('Description'):
                        dict_ol['name'] = i.get('Description')
                        dict_col['name'] = i.get('Description')
                        dict_tol['name'] = i.get('Description')
                    else:
                        dict_ol['name'] = 'NA'
                        dict_col['name'] = 'NA'
                        dict_tol['name'] = 'NA'

                    if type == 'out_invoice' or type == 'out_refund':
                        if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                tax_amount = cust.get('TxnTaxDetail').get('TaxLine')[0].get('TaxLineDetail').get('TaxPercent')
                                dict_tol['price_unit'] = float(dict_ol['quantity'] * dict_ol['price_unit'] * float(tax_amount/100))
                                dict_tol['credit'] = dict_tol['price_unit']
                                dict_tol['debit'] = 0

                                dict_col['debit'] += dict_tol['credit']
                            else:
                                dict_tol['price_unit'] = 0
                                dict_tol['credit'] = 0
                                dict_tol['debit'] = 0

                        else:
                            dict_tol['price_unit'] = 0
                            dict_tol['credit'] = 0
                            dict_tol['debit'] = 0
                    else:
                        dict_tol['price_unit'] = 0
                        dict_tol['credit'] = 0
                        dict_tol['debit'] = 0

                    if type == 'out_refund' or type == 'in_invoice':
                        dict_ol['credit'],dict_ol['debit'] = dict_ol['debit'],dict_ol['credit']
                        dict_col['credit'],dict_col['debit'] = dict_col['debit'],dict_col['credit']
                        dict_tol['credit'],dict_tol['debit'] = dict_tol['debit'],dict_tol['credit']

                    if res_product.property_account_income_id:
                        dict_ol['account_id'] = res_product.property_account_income_id.id
                        _logger.info("PRODUCT has income account set")
                    else:
                        dict_ol['account_id'] = res_product.categ_id.property_account_income_categ_id.id
                        _logger.info("No Income account was set, taking from product category..")

                    if invoice_obj.partner_id.property_account_receivable_id:
                        dict_col['account_id'] = invoice_obj.partner_id.property_account_receivable_id.id
                        dict_tol['account_id'] = invoice_obj.partner_id.property_account_receivable_id.id
                    else:
                        raise UserError("Account Receivable not set for Customer ---> {}".format(invoice_obj.partner_id.name))
                        _logger.info("No Property Account Receivable Set!")
                        
                    _logger.info("DICT COL IS ---> {}".format(dict_col))
                    _logger.info("DICT OL IS ---> {}".format(dict_ol))
                    _logger.info("DICT TOL IS ---> {}".format(dict_tol))
                    if 'account_id' in dict_ol and 'account_id' in dict_col:
                        _logger.info("\n\n Invoice Line is  ---> {}".format(dict_ol))
                        inv_line_data.append(dict_ol)
                        inv_line_data.append(dict_col)
                        _logger.info("INVOICE LINE DATA FOR NOW IS ---> {}".format(inv_line_data))
                        if type == 'out_invoice' or type == 'out_refund':
                            _logger.info("Getting Additional Details!")
                            if cust.get('TxnTaxDetail').get('TxnTaxCodeRef'):
                                _logger.info("Getting Transaction Details!")
                                dict_ol['tax_repartition_line_id'] = False
                                dict_col['tax_repartition_line_id'] = False
 
#                                 tax_repartition_line_id = self.env['account.tax.repartition.line'].search([('repartition_type', '=', 'tax')],limit=1)
# #                                 dict_tol['tax_repartition_line_id'] = tax_repartition_line_id.id
                                dict_tol['tax_repartition_line_id'] = False
                                dict_ol['tax_base_amount'] = 0
                                dict_col['tax_base_amount'] = 0
                                dict_tol['tax_base_amount'] = dict_ol['quantity'] * dict_ol['price_unit']
                                
                                if cust.get('TxnTaxDetail').get('TxnTaxCodeRef').get('value'):
                                    inv_line_data.append(dict_tol)
                                else:
                                    _logger.info("TAX Code Reference Value Not Found!")
                    else:
                        _logger.info("Account ID not found in the dictionary!")
        _logger.info("INVOICE LINE DATA SENDING FOR CREATION IS ---> {}".format(inv_line_data))
        return inv_line_data


    @api.model
    def _prepare_invoice_export_line_dict(self, line):
        #         line = self
        company = self.env['res.users'].search([('id', '=', 2)]).company_id
        vals = {
            'Description': line.name,
            'Amount': line.price_subtotal,
        }
        if self.partner_id.supplier_rank:
            if line.tax_ids:
                raise UserError("Taxable vendor bill cannot be exported.")
        if line.tax_ids:
            taxCodeRef = 'TAX'
        else:
            taxCodeRef = 'NON'

        if self.partner_id.customer_rank:
            vals.update({
                'DetailType': 'SalesItemLineDetail',
                'SalesItemLineDetail': {
                    'ItemRef': {'value': self.env['product.template'].get_qbo_product_ref(line.product_id)},
                    'TaxCodeRef': {'value': taxCodeRef},
                    'UnitPrice': line.price_unit,
                    'Qty': line.quantity,
                }
            })
        elif self.partner_id.supplier_rank:
            vals.update({
                'DetailType': 'ItemBasedExpenseLineDetail',
                'ItemBasedExpenseLineDetail': {
                    'ItemRef': {'value': self.env['product.template'].get_qbo_product_ref(line.product_id)},
                    'TaxCodeRef': {'value': taxCodeRef},
                    'UnitPrice': line.price_unit,
                    'Qty': line.quantity,
                    #                     'BillableStatus' : 'Billable',
                }
            })

        return vals
    
    
    @api.model
    def get_linked_sales_order_ref(self,quickbook_id):
        qbo_id = str(quickbook_id)
        company = self.env['res.users'].search([('id', '=', 2)]).company_id
        url_str = company.get_import_query_url()
        url = url_str.get('url') + '/estimate/' + qbo_id + '?minorversion=' + url_str.get('minorversion')
        result = requests.request('GET', url, headers=url_str.get('headers'))
        if result.status_code == 200 :
            return True
        else:
            return False

    @api.model
    def _prepare_invoice_export_dict(self):
        invoice = self
        vals = {

            'TxnDate': str(invoice.invoice_date),
            'DueDate': str(invoice.invoice_date_due),
        }
        
        #Added code for linking of Sales Order to an invoice
        if invoice.invoice_origin:
            _logger.info("INVOICE HAS A SALES ORDER ASSOCIATED WITH IT---> {}".format(invoice.invoice_origin))
            #Search for the related sales order
            linked_sales_order = self.env['sale.order'].search([('name','=',invoice.invoice_origin)])
            _logger.info("LINKED SALES ORDER IS ---> {}".format(linked_sales_order))
            if linked_sales_order :
                #CHECK IF ALL THE CRITERIAS ARE MATCHED IN ORDER TO BE LINKED TO QBO
                #1 TO CHECK IF QBO ID IS ATTACHED TO SO
                if linked_sales_order.quickbook_id:
                    _logger.info("QBO ID IS PRESENT TO SO")
                    #2.TO CHECK IF SO IS PRESENT IN QBO
                    linked_so = self.get_linked_sales_order_ref(linked_sales_order.quickbook_id)
                    if linked_so:
                        _logger.info("SALES ORDER IS PRESENT IN QBO")
                        #UPDATE LINKED TRANSACTION DETAILS
                        vals.update({
                                    "LinkedTxn": [{
                                        "TxnId": linked_sales_order.quickbook_id,
                                        "TxnType": "Estimate"
                                       }
                                    ]})
                    else:
                        _logger.info("SALES ORDER NOT PRESENT IN QBO")
                        raise ValidationError(_("Sales Order : %s  is not present in  Quickbooks." % (invoice.invoice_origin)))
                else : 
                    _logger.info("Linked Sales Order is not exported to Quickbooks")
                    raise ValidationError(_("Sales Order : %s linked to this Invoice is not exported to Quickbooks.Please export Sales Order first to link the invoice into Quickbooks " % (invoice.invoice_origin)))


        if invoice.partner_id.customer_rank:
            vals.update({'DocNumber': invoice.name,
                         'CustomerRef': {'value': self.env['res.partner'].get_qbo_partner_ref(invoice.partner_id)}})
        elif invoice.partner_id.supplier_rank:
#             if invoice.invoice_sequence_number_next_prefix and invoice.invoice_sequence_number_next :
#                 _logger.info("VENDOR BILL NUMBER IS ---> {} {}".format(invoice.invoice_sequence_number_next_prefix,invoice.invoice_sequence_number_next))
#                 vendor_bill_ref_num = "{}{}".format(invoice.invoice_sequence_number_next_prefix,invoice.invoice_sequence_number_next)
#                 vals.update({'DocNumber' : vendor_bill_ref_num})
            vals.update({'DocNumber': invoice.name,
                        'VendorRef': {'value': self.env['res.partner'].get_qbo_partner_ref(invoice.partner_id)}})

        arr = []
        tax_id = 0
        lst_line = []
        for line in invoice.invoice_line_ids:
            line_vals = self._prepare_invoice_export_line_dict(line)
            lst_line.append(line_vals)

            if line.tax_ids.id:
                if line.tax_ids.qbo_tax_id:
                    tax_id = line.tax_ids.id
                    arr.append(tax_id)
                elif not line.tax_ids.qbo_tax_id:
                    exported = self.env['account.tax'].export_one_tax_at_a_time(line.tax_ids)

                    is_exported = self.env['account.tax'].search([('id', '=', line.tax_ids.id)])
                    if is_exported:
                        if line.tax_ids.qbo_tax_id:
                            tax_id = line.tax_ids.id
                            arr.append(tax_id)
        vals.update({'Line': lst_line})

        if tax_id:
            j = 0
            for i in arr:
                if len(arr) == 1:
                    tax_added = self.env['account.tax'].search([('id', '=', tax_id)])

                    vals.update({"TxnTaxDetail": {
                        "TxnTaxCodeRef": {
                            "value": tax_added.qbo_tax_id
                        }}})
                if j < len(arr) - 1:
                    if arr[j] == arr[j + 1]:
                        j = j + 1

                        tax_added = self.env['account.tax'].search([('id', '=', tax_id)])

                        vals.update({"TxnTaxDetail": {
                            "TxnTaxCodeRef": {
                                "value": tax_added.qbo_tax_id
                            }}})
                    else:
                        raise UserError("You need to add same tax for the required orderlines.")

        return vals

    @api.model
    def export_to_qbo(self):
        """export account invoice to QBO"""
        quickbook_config = self.env['res.users'].search([('id', '=', 2)]).company_id

        if self._context.get('active_ids'):
            invoices = self.browse(self._context.get('active_ids'))
        else:
            invoices = self

        for invoice in invoices:
            if len(invoices) == 1:
                if invoice.qbo_invoice_id:
                    if invoice.partner_id.customer_rank:
                        raise ValidationError(
                            _("Invoice is already exported to QBO. Please, export a different invoice."))
                    if invoice.partner_id.supplier_rank:
                        raise ValidationError(
                            _("Vendor Bill is already exported to QBO. Please, export a different Vendor Bill."))
            if len(invoices) > 1:
                if invoice.qbo_invoice_id:
                    if invoice.partner_id.customer_rank:
                        _logger.info("Invoice is already exported to QBO")
                    if invoice.partner_id.supplier_rank:
                        _logger.info("Vendor Bill is already exported to QBO")

            if not invoice.qbo_invoice_id:
                if invoice.state == 'posted':
                    vals = invoice._prepare_invoice_export_dict()
                    parsed_dict = json.dumps(vals)
                    if quickbook_config.access_token:
                        access_token = quickbook_config.access_token
                    if quickbook_config.realm_id:
                        realmId = quickbook_config.realm_id

                    if access_token:
                        headers = {}
                        headers['Authorization'] = 'Bearer ' + str(access_token)
                        headers['Content-Type'] = 'application/json'
                        
                        if not invoice.partner_id.customer_rank and not invoice.partner_id.supplier_rank:
                            raise UserError('Please define rank either customer/vendor')
                        if invoice.partner_id.customer_rank:
                            result = requests.request('POST', quickbook_config.url + str(realmId) + "/invoice",
                                                      headers=headers, data=parsed_dict)
                        elif invoice.partner_id.supplier_rank:
                            result = requests.request('POST', quickbook_config.url + str(realmId) + "/bill",
                                                      headers=headers, data=parsed_dict)

                        if result.status_code == 200:
                            response = quickbook_config.convert_xmltodict(result.text)
                            # update QBO invoice id
                            if invoice.partner_id.customer_rank:
                                invoice.qbo_invoice_id = response.get('IntuitResponse').get('Invoice').get('Id')
                                self._cr.commit()
                            elif invoice.partner_id.supplier_rank:
                                invoice.qbo_invoice_id = response.get('IntuitResponse').get('Bill').get('Id')
                                self._cr.commit()
                            _logger.info(_("%s exported successfully to QBO" % (invoice.name)))

                        else:
                            _logger.error(_("[%s] %s" % (result.status_code, result.reason)))
                            raise ValidationError(_("[%s] %s %s" % (result.status_code, result.reason, result.text)))
                else:
                    if len(invoices) == 1:
                        if invoice.move_type == 'in_invoice' :
                            raise ValidationError(_("Only posted state Vendor Bill is exported to QBO."))
                        if invoice.move_type == 'out_invoice' :
                            raise ValidationError(_("Only posted state Invoice is exported to QBO."))
                        if invoice.move_type == 'in_refund' :
                            raise ValidationError(_("Only posted state Customer Credit Note is exported to QBO."))
                        if invoice.move_type == 'out_refund' :
                            raise ValidationError(_("Only posted state Vendor Credit Note is exported to QBO."))
                            
#                         if invoice.partner_id.customer_rank:
#                             raise ValidationError(_("Only posted state Invoice is exported to QBO."))
#                         if invoice.partner_id.supplier_rank:
#                             raise ValidationError(_("Only posted state Vendor bill is exported to QBO."))
                        