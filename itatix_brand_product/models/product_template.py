from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sama_category = fields.Char(copy=False)
    sama_subcategory = fields.Char(copy=False)
    sama_brand = fields.Char(copy=False)
