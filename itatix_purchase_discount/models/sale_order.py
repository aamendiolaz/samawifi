from odoo import api, fields, models
from odoo.tools.misc import get_lang


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dna = fields.Char(copy=False)
    final_user_id = fields.Many2one('res.partner', copy=False)
    channel = fields.Many2one('res.partner', copy=False)

    @api.depends('order_line.purchase_line_ids.order_id')
    def _compute_purchase_order_count(self):
        result = super(SaleOrder, self)._compute_purchase_order_count()
        purchase_ids = self._get_purchase_orders()
        if purchase_ids:
            lst = []
            if purchase_ids:
                for line in self.order_line:
                    dict_line = {
                        'product_id': line.product_id.id,
                        'price_unit': line.price_unit,
                        'price_list': line.price_list,
                        'discount': line.vendor_discount
                    }
                    lst.append(
                        [dict_line]
                    )
        return result


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        res = super(SaleOrderLine, self)._compute_amount()
        for line in self.filtered(lambda ln: ln.price_list):
            price = line.price_list * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'price_unit': price
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])
        return res

    price_list = fields.Float(digits="Price list", copy=False)
    vendor_discount = fields.Float(digits="Price list", copy=False)

    @api.onchange('product_id')
    def product_id_change(self):
        result = super(SaleOrderLine, self).product_id_change()
        vals = {}
        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )
        self._compute_tax_id()
        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(self.price_list, product.taxes_id, self.tax_id, self.company_id)
        self.update(vals)
        return result

    @api.onchange('product_id', 'product_uom', 'product_uom_qty', 'tax_id')
    def _onchange_price_list(self):
        self.ensure_one()
        if not self.price_list and self.product_id:
            self.price_list = self.product_id._select_seller().price_list
            self.vendor_discount = self.product_id._select_seller().discount