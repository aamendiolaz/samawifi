from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    exchange_currency_rate = fields.Float("PV en USD", compute='_compute_exchange_currency_rate', store=True)

    @api.depends('pricelist_id')
    def _compute_exchange_currency_rate(self):
        company_currency = self.env.company.currency_id
        foreing_currency = self.env['res.currency'].search([('name', '=', 'USD')])
        for record in self:
            if record.pricelist_id.currency_id.id == company_currency.id:
                record['exchange_currency_rate'] = company_currency._convert(
                    record.amount_untaxed,
                    foreing_currency,
                    self.env.company,
                    record.date_order
                )

