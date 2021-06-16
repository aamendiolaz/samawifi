from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'
    billing_goal = fields.Float(related='invoice_user_id.billing_goal', group_operator="avg", store=True)
    invoiced_target = fields.Float(related='team_id.invoiced_target', group_operator="avg", store=True)
