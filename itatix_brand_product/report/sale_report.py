# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"
    sama_category = fields.Char(readonly=True)
    sama_subcategory = fields.Char(readonly=True)
    sama_brand = fields.Char(readonly=True, string="Brand")

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['sama_category'] = ', t.sama_category as sama_category'
        fields['sama_subcategory'] = ', t.sama_subcategory as sama_subcategory'
        fields['sama_brand'] = ', t.sama_brand as sama_brand'

        groupby += ', t.sama_category , t.sama_subcategory, t.sama_brand'

        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)