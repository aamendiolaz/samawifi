from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sama_category_id = fields.Many2one('sama.category', copy=False)
    sama_subcategory_id = fields.Many2one('sama.subcategory', copy=False)
    sama_brand_id = fields.Many2one('sama.brand', copy=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sama_category_id = fields.Many2one(related='product_tmpl_id.sama_category_id', store=True)
    sama_subcategory_id = fields.Many2one(related='product_tmpl_id.sama_subcategory_id', store=True)
    sama_brand_id = fields.Many2one(related='product_tmpl_id.sama_brand_id', store=True)