# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountInvoiceReport(models.Model):

    _inherit = 'account.invoice.report'

    product_sama_category_id = fields.Many2one('sama.category', copy=False)
    product_sama_subcategory_id = fields.Many2one('sama.subcategory', copy=False)
    product_sama_brand_id = fields.Many2one('sama.brand', copy=False)
    price_subtotal_usd = fields.Float(string='Untaxed Total(USD)', readonly=True)

    def _select(self):
        select_str = super(AccountInvoiceReport, self)._select()
        return select_str.replace(
            "template.categ_id                                           AS product_categ_id,",
            """
            template.categ_id                                           AS product_categ_id,
            template.sama_category_id                                           AS product_sama_category_id,
            template.sama_subcategory_id                                           AS product_sama_subcategory_id,
            template.sama_brand_id                                           AS product_sama_brand_id,
            line.price_subtotal * move.currency_rate_usd                         AS price_subtotal_usd,
            """
        )
