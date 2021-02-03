from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move.line'

    vendor_discount = fields.Float(digits="Price list", copy=False)