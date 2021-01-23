from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    sama_category = fields.Char(related='product_id.sama_category', store=True)
    sama_subcategory = fields.Char(related='product_id.sama_subcategory', store=True)
    sama_brand = fields.Char(related='product_id.sama_brand', store=True)


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    sama_category = fields.Char(related='product_id.sama_category', store=True)
    sama_subcategory = fields.Char(related='product_id.sama_subcategory', store=True)
    sama_brand = fields.Char(related='product_id.sama_brand', store=True)