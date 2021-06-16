# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = "account.move"

    currency_rate_usd = fields.Float("Currency Rate(USD)", compute='_compute_currency_rate_usd', compute_sudo=True, store=True, digits=(12, 6), readonly=True)

    @api.depends('currency_id', 'date', 'company_id')
    def _compute_currency_rate_usd(self):
        currency_usd = self.env.ref('base.USD')
        if not currency_usd:
            self.currency_rate_usd = 0.0
            return

        for move in self:
            move.currency_rate_usd = 1.0 if move.currency_id == currency_usd else currency_usd.with_context(date=move.date).rate or 1.0