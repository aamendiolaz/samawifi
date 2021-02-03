from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    sama_category_id = fields.Many2one(related='product_id.sama_category_id', store=True)
    sama_subcategory_id = fields.Many2one(related='product_id.sama_subcategory_id', store=True)
    sama_brand_id = fields.Many2one(related='product_id.sama_brand_id', store=True)


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    sama_category_id = fields.Many2one(related='product_id.sama_category_id', store=True)
    sama_subcategory_id = fields.Many2one(related='product_id.sama_subcategory_id', store=True)
    sama_brand_id = fields.Many2one(related='product_id.sama_brand_id', store=True)