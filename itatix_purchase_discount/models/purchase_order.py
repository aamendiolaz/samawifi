from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sale_id = fields.Many2one('sale.order',
                              string='Sale Order',
                              copy=False)
    partner_shipping_id = fields.Many2one(
        'res.partner',
        string='Delivery Address',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Delivery address for current purchase.")

    dna = fields.Char(copy=False)
    final_user_id = fields.Many2one('res.partner', copy=False)
    channel = fields.Many2one('res.partner', copy=False)

    def _add_supplier_to_product(self):
        self.ensure_one()
        po_line_map = {
            line.product_id.product_tmpl_id.id: line for line in self.order_line
        }
        return super(
            PurchaseOrder, self.with_context(po_line_map=po_line_map)
        )._add_supplier_to_product()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, company_id, values, po):
        result = super(PurchaseOrderLine, self)._prepare_purchase_order_line_from_procurement(
            product_id, product_qty, product_uom, company_id, values, po
        )
        if values.get('group_id', False) and po:
            group_id = values.get('group_id')
            if group_id.sale_id:
                sale_id = group_id.sale_id
                po.sale_id = sale_id.id or False
                po.partner_shipping_id = sale_id.partner_shipping_id.id or False
                po.dna = sale_id.dna or False
                po.final_user_id = sale_id.final_user_id or False
                po.channel = sale_id.channel or False

        return result

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        res = super(PurchaseOrderLine, self)._prepare_purchase_order_line(
            product_id, product_qty, product_uom, company_id, supplier, po
        )
        seller = product_id._select_seller()
        res.update(self._prepare_purchase_order_line_from_seller(seller))
        return res

    @api.model
    def _prepare_purchase_order_line_from_seller(self, seller):
        if not seller:
            return {}
        dict_values = {
            "discount": seller.discount,
            "price_list": seller.price_list
         }
        return dict_values

    @api.depends("discount")
    def _compute_amount(self):
        return super()._compute_amount()

    def _prepare_compute_all_values(self):
        vals = super()._prepare_compute_all_values()
        vals.update(
            {
                "price_unit": self._get_discounted_price_unit()
            })
        self.price_unit = self._get_discounted_price_unit()
        return vals

    discount = fields.Float(string="Discount (%)", digits="Discount")
    price_list = fields.Float(digits="Price list")

    _sql_constraints = [
        (
            "discount_limit",
            "CHECK (discount <= 100.0)",
            "Discount must be lower than 100%.",
        )
    ]

    def _get_discounted_price_unit(self):
        self.ensure_one()
        if self.discount:
            return self.price_list * (1 - self.discount / 100)
        return self.price_list

    def _get_stock_move_price_unit(self):
        price_unit = False
        price = self._get_discounted_price_unit()
        if price != self.price_unit:
            price_unit = self.price_unit
            self.price_unit = price
        price = super()._get_stock_move_price_unit()
        if price_unit:
            self.price_unit = price_unit
        return price

    @api.onchange("product_qty", "product_uom")
    def _onchange_quantity(self):
        res = super()._onchange_quantity()
        if self.product_id:
            date = None
            if self.order_id.date_order:
                date = self.order_id.date_order.date()
            seller = self.product_id._select_seller(
                partner_id=self.partner_id,
                quantity=self.product_qty,
                date=date,
                uom_id=self.product_uom,
            )
            self._apply_value_from_seller(seller)
        return res

    @api.model
    def _apply_value_from_seller(self, seller):
        if not seller:
            return
        self.discount = seller.discount
        self.price_list = seller.price_list
        self.price_unit = self._get_discounted_price_unit() if seller.price_list else self.price_unit

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        res.update(
            {
                'discount':self.discount,
                'price_unit': self.price_list
            }
        )
        return res