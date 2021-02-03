from odoo import fields, models


class StockReport(models.Model):
    _inherit = 'stock.report'

    sama_category_id = fields.Many2one('sama.category', readonly=True)
    sama_subcategory_id = fields.Many2one('sama.subcategory', readonly=True)
    sama_brand_id = fields.Many2one('sama.brand', readonly=True, string="Brand")

    def _select(self):
        query = ', t.sama_category_id AS sama_category_id, t.sama_subcategory_id AS sama_subcategory_id, t.sama_brand_id AS sama_brand_id'
        return super(StockReport, self)._select() + query

    def _group_by(self):
        query = ', t.sama_category_id, t.sama_subcategory_id, t.sama_brand_id'
        return super(StockReport, self)._group_by() + query
