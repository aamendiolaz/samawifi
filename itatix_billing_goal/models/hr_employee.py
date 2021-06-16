from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    billing_goal = fields.Float(related='user_id.billing_goal', readonly=True, store=True, copy=False)
