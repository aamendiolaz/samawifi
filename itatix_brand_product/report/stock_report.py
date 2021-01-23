from odoo import fields, models, api


class StockReport(models.Model):
    _inherit = 'stock.report'

    sama_category = fields.Char(readonly=True)
    sama_subcategory = fields.Char(readonly=True)
    sama_brand = fields.Char(readonly=True)

    def _select(self):
        query = ', t.sama_category AS sama_category, t.sama_subcategory AS sama_subcategory, t.sama_brand AS sama_brand'
        return super(StockReport, self)._select() + query

    def _group_by(self):
        query = ', t.sama_category, t.sama_subcategory, t.sama_brand'
        return super(StockReport, self)._group_by() + query
