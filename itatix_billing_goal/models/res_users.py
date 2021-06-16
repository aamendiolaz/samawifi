from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    billing_goal = fields.Float(related='partner_id.billing_goal', store=True)