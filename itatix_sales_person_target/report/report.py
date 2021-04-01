# -*- coding: utf-8 -*-

from odoo import tools
from odoo import api, fields, models


class SalesTargetReport(models.Model):
    _name = "sales.target.report"
    _description = "Sales Target Report"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    date = fields.Date('Target Date', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    sales_team_id = fields.Many2one(related='user_id.sale_team_id', store=True)
    target = fields.Float('Quota', readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)
    gap = fields.Float(readonly=True)
    achieve_total = fields.Float('Achieve', readonly=True)
    sales = fields.Integer("Invoicing", readonly=True)
    achieve_perct = fields.Float('Achievement %',  group_operator="avg", readonly=True)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(SalesTargetReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        groupby = [groupby] if isinstance(groupby, str) else groupby
        if any("date" in s for s in groupby):
            for record in res:
                if record['target']:
                    record['achieve_perct'] = record['achieve_total'] * 100 / record['target']
                else:
                    record['achieve_perct'] = record['achieve_total'] or 1.0 / 1.0
        if not groupby:
            for record in res:
                if record['target']:
                    record['achieve_perct'] = record['achieve_total'] * 100 / record['target']
                else:
                    record['achieve_perct'] = record['achieve_total'] or 1.0 / 1.0
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(SalesTargetReport, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        for rec in self.env['sales.target'].search([]):
            rec._get_sales_target_lines()
        for l in self.env['sales.target.lines'].search([]):
            l._get_total_sales()
        return res
    
    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""
        select_ = """
            min(stl.id) as id,
            stl.date_order as date,
            st.salesperson as user_id,
            stl.monthly_target as target,
            stl.currency_id as currency_id,
            stl.monthly_target_achieve as achieve_total,
            stl.no_of_sales as sales,
            stl.monthly_target_achieve * 100 / NULLIF(stl.monthly_target, 0) as achieve_perct,   
            st.sales_team_id as sales_team_id,
            sum(stl.monthly_target_achieve - stl.monthly_target) as gap
        """

        for field in fields.values():
            select_ += field

        from_ = """
                sales_target_lines stl
                    left join sales_target st on (st.id = stl.target_id and st.salesperson = stl.user_id)
                %s
        """ % from_clause

        groupby_ = """
            stl.date_order,
            st.salesperson,
            stl.monthly_target,
            stl.currency_id,
            stl.monthly_target_achieve,
            stl.no_of_sales,
            st.sales_team_id,
            stl.monthly_target_achieve_per
             %s
        """ % (groupby)

        return '%s (SELECT %s FROM %s WHERE stl.user_id IS NOT NULL GROUP BY %s)' % (with_, select_, from_, groupby_)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

