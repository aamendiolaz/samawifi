from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_id')
    def _default_lot_ids(self):
        if self.product_id:
            lot_id = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id), ('import_document', '!=', False)])
            if not lot_id:
                return {'domain': {'lot_id': [('id', '=', [])]}}
            res = {'domain': {'lot_id': [('id', 'in', lot_id.ids)]}}
            return res