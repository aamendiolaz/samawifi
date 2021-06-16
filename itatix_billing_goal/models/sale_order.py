from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    billing_goal = fields.Float(related='user_id.billing_goal', group_operator="avg", store=True)
    invoiced_target = fields.Float(related='team_id.invoiced_target', group_operator="avg", store=True)