# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"
    sama_category_id = fields.Many2one('sama.category', readonly=True)
    sama_subcategory_id = fields.Many2one('sama.subcategory', readonly=True)
    sama_brand_id = fields.Many2one('sama.brand', readonly=True, string="Brand")

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['sama_category_id'] = ', t.sama_category_id as sama_category_id'
        fields['sama_subcategory_id'] = ', t.sama_subcategory_id as sama_subcategory_id'
        fields['sama_brand_id'] = ', t.sama_brand_id as sama_brand_id'

        groupby += ', t.sama_category_id , t.sama_subcategory_id, t.sama_brand_id'

        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)