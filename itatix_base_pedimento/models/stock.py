from odoo import fields, models, api
from odoo.tools.translate import _


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    import_document = fields.Char(copy=False)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    import_document = fields.Char(related='lot_id.import_document', store=True, copy=False)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    import_document = fields.Char(related='lot_id.import_document', copy=False)

    def _assign_production_lot(self, lot):
        super()._assign_production_lot(lot)
        self.lot_id.write({'import_document': self.picking_id.import_document})


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    import_document = fields.Char(copy=False)
    stock_move_line_count = fields.Integer(copy=False, compute='_compute_stock_move_line_count')

    # def assign_import_document(self):
    #     state = ['draft', 'waiting', 'confirmed', 'assigned']
    #     # if self.state not in state:
    #     #     raise UserError("Lo siento, no es posible actualizar los pedimentos debido a que el estado actual es : {}".format(self.state))
    #     for record in self:
    #         if record.import_document:
    #             for rec in record.move_line_ids_without_package.filtered(lambda ln: ln.tracking):
    #                 rec.import_document = record.import_document
    #         else:
    #             continue

    @api.depends('move_line_ids_without_package')
    def _compute_stock_move_line_count(self):
        for record in self:
            record.stock_move_line_count = len(record.move_line_ids_without_package.filtered(lambda ln: ln.tracking).ids)

    def action_view_stock_move_lines(self):
        self.ensure_one()
        move_line_ids = self.move_line_ids_without_package.filtered(lambda ln: ln.tracking).ids
        action = {}
        if move_line_ids:
            action = {
                'res_model': 'stock.move.line',
                'type': 'ir.actions.act_window',
                'active_picking_id': self.id,
                'default_company_id': self.company_id.id,
                'default_product_id': self.product_id.id
            }
        if len(move_line_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': move_line_ids[0],
            })
        else:
            action.update({
                'name': _("Purchase Order generated from %s", self.name),
                'domain': [('id', 'in', move_line_ids)],
                'view_id': self.env.ref('itatix_base_pedimento.view_stock_move_line_operation_custom_tree').id,
                'view_mode': 'tree',
                'type': 'ir.actions.act_window',
                'context': self.env.context,
            })
        return action
