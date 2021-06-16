from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    billing_goal = fields.Float(copy=False)
