# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    currency_rate_usd = fields.Float("Currency Rate(USD)", compute='_compute_currency_rate_usd', compute_sudo=True, store=True, digits=(12, 6), readonly=True)
    product_id = fields.Many2one('product.product', compute='_compute_product_id', store=True, copy=False)
    sama_brand_id = fields.Many2one('sama.brand', related='product_id.sama_brand_id', store=True, copy=False)

    @api.depends('currency_id', 'date', 'company_id')
    def _compute_currency_rate_usd(self):
        currency_usd = self.env.ref('base.USD')
        if not currency_usd:
            self.currency_rate_usd = 0.0
            return

        for move in self:
            move.currency_rate_usd = 1.0 if move.currency_id == currency_usd else currency_usd.with_context(date=move.date).rate or 1.0

    @api.depends('invoice_line_ids','invoice_line_ids.product_id')
    def _compute_product_id(self):
        for move in self:
            move.product_id = False
            for line in move.invoice_line_ids.filtered(lambda l: l.product_id):
                move.product_id =  line.product_id

class SalesTargetLines(models.Model):
    _inherit = "sales.target.lines"

    team_id = fields.Many2one(related='target_id.sales_team_id')
            