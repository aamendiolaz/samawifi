# -*- coding: utf-8 -*-

from odoo import api, fields, models, SUPERUSER_ID, _, http
from odoo.fields import Datetime
from datetime import datetime
from calendar import monthrange
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"
    
    member_ids = fields.Many2many('res.users', string="Team Members", compute="_get_member_ids")
    
    def _get_member_ids(self):
        members = []
        members.append(self.id)
        for team in self.env['crm.team'].sudo().search([('user_id','=',self.id)]):
            for t in team.member_ids.ids:
                if t not in members:
                    members.append(t)
        UserObj = self.env['res.users'].sudo().search([('id','in',members)])
        self.member_ids = UserObj.ids

                    
class CrmTeam(models.Model):
    _inherit = "crm.team"
    
    manager_id = fields.Many2one('res.users', string="Sales Manager")

    def _compute_quotations_to_invoice(self):
        query = self.env['sale.order']._where_calc([
            ('team_id', 'in', self.ids),
            ('state', 'in', ['draft', 'sent']),
        ])
        self.env['sale.order']._apply_ir_rules(query, 'read')
        _, where_clause, where_clause_args = query.get_sql()
        select_query = """
            SELECT team_id, count(*), sum(amount_total
            ) as amount_total
            FROM sale_order
            WHERE %s
            GROUP BY team_id
        """ % where_clause
        self.env.cr.execute(select_query, where_clause_args)
        quotation_data = self.env.cr.dictfetchall()
        teams = self.browse()
        for datum in quotation_data:
            team = self.browse(datum['team_id'])
            team.quotations_amount = datum['amount_total']
            team.quotations_count = datum['count']
            teams |= team
        remaining = (self - teams)
        remaining.quotations_amount = 0
        remaining.quotations_count = 0

    def view_sales_target(self):
        return {
            'name': _('Sales Target View'),
            'type': 'ir.actions.act_window',
            'domain': [('sales_team_id', '=', self.id)],
            'context': {'group_by': 'sales_team_id'},
            'view_type': 'kanban,tree,form',
            'view_mode': 'kanban,tree,form',
            'res_model': 'sales.target',
            'res_id': self[0].id,
            'view_id': self.env.ref('itatix_sales_person_target.kanban_sales_target_report_view').id,
            'views': [
                (self.env.ref('itatix_sales_person_target.kanban_sales_target_report_view').id or False, 'kanban'),
                (self.env.ref('itatix_sales_person_target.sales_target_tree_view').id or False, 'tree'),
                (self.env.ref('itatix_sales_person_target.sales_target_form_view').id or False, 'form'),
            ],
            'target': 'current',
        }

    def view_sales_target_report(self):
        return {
            'name': _('Sales Target View'),
            'type': 'ir.actions.act_window',
            'domain': [('sales_team_id', '=', self.id)],
            'context': {'group_by': 'sales_team_id'},
            'view_type': 'pivot',
            'view_mode': 'pivot',
            'res_model': 'sales.target.report',
            'res_id': self[0].id,
            'view_id': self.env.ref('itatix_sales_person_target.view_sales_target_report_pivot').id,
            'views': [
                (self.env.ref('itatix_sales_person_target.view_sales_target_report_pivot').id or False, 'pivot'),
            ],
            'target': 'current',
        }


    @api.onchange('member_ids')
    def onchange_member_ids(self):
        UserObj = self.env['res.users'].sudo().search([('id','=',self.user_id.id)])
        UserObj._get_member_ids()


class SalesTarget(models.Model):

    _name = "sales.target"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Sales Target"
    _rec_name = 'salesperson'
    _order = 'id desc'

    team_leader = fields.Many2one(related='sales_team_id.user_id', store=True)
    salesperson = fields.Many2one("res.users", string="Salesperson")
    target = fields.Float("Target", compute='_compute_monthly_target', store=True)
    monthly_target = fields.Float("Monthly Target", compute='_compute_monthly_target', store=True)  # Quota/Meta de facturacion
    achieve = fields.Float("Achieve", compute='_compute_monthly_target', store=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env['res.currency'].search(
        [('name', '=', 'USD')])
                                  )
    start_date = fields.Date("From")
    end_date = fields.Date("To")
    sales = fields.Integer("Sales", compute="_get_total_sales", store=True)
    perct_achievement = fields.Float("% Achievement", compute='_compute_monthly_target', store=True)
    target_achieve = fields.Selection([('sale_order_confirm', "Sale Order Confirm"),
                                       ('delivery_order_done', 'Delivery Order Done'),
                                       ('invoice_created', 'Invoice Created'),
                                       ('invoice_paid', 'Invoice Paid')], string="Target Achieve", default="invoice_created")
    sales_team_id = fields.Many2one('crm.team')
    sales_target_lines = fields.One2many("sales.target.lines", "target_id", string="Target Lines")
    current_year = fields.Date(copy=False)
    gap = fields.Float(copy=False, compute='_compute_monthly_target', store=True)
    total_target = fields.Float(copy=False, string="Teams Quota", compute='_compute_quota_sales_team', store=True)

    @api.depends('sales_team_id', 'sales_target_lines.monthly_target')
    def _compute_quota_sales_team(self):
        for record in self:
            if record.sales_team_id:
                target_ids = record.env['sales.target'].search([('sales_team_id', '=', record.sales_team_id.id)])
                quota = 0.0
                if target_ids:
                    for st in target_ids:
                        quota += st.target
                record.sales_team_id.invoiced_target = quota
                record.total_target = quota

    @api.depends('sales_target_lines.monthly_target')
    def _compute_monthly_target(self):
        for record in self:
            current_month = record.mapped("sales_target_lines").filtered(
                lambda ln: ln.date_order.month == fields.Date.today().month
                and ln.date_order.year == record.current_year.year
            )
            if current_month:
                last_days = monthrange(fields.Datetime.today().year, fields.Datetime.today().month)[1]
                stdt = fields.Datetime.today().replace(day=1)
                endt = fields.Datetime.today().replace(day=last_days)
                monthly_target_achieve, monthly_target_achieve_per = record.get_perct_achievement(
                    record.salesperson.id, record.monthly_target, record.currency_id.id, stdt, endt,record.target_achieve)
                current_month.monthly_target_achieve = monthly_target_achieve
                current_month.monthly_target_achieve_per = monthly_target_achieve_per
                record.write({
                    'monthly_target': current_month.monthly_target,
                    'target': current_month.monthly_target,
                    'achieve': monthly_target_achieve,
                    'perct_achievement': monthly_target_achieve_per,
                    'gap': current_month.monthly_target_achieve - current_month.monthly_target
                })

    @api.model
    def create(self, vals):
        res = super(SalesTarget, self).create(vals)
        if res:
            res.create_months(fields.Date.today())
            if res.mapped("sales_target_lines"):
                for line in res.mapped("sales_target_lines"):
                    line.current_year = True
            res.current_year = fields.Date.today()
        return res

    @api.onchange('current_year')
    def _onchange_target_lines(self):
        """
        SE CREA EN AUTOMATICO
        SI HAY LA FECHA DEL CURRENT YEAR, se agregara a las lineas del booleano
        si es una fecha anterior al año en curso ¿?
        :return:
        """
        if self.current_year:
            current_year = fields.Date.today()
            selected_dt = self.current_year
            diff_year = self.mapped("sales_target_lines").filtered(
                lambda ln: ln.date_order.year != selected_dt.year
            )
            if diff_year:
                self.create_months(selected_dt)
            for line in self.mapped("sales_target_lines"):
                if line.date_order.year == current_year.year:
                    line.current_year = True
                else:
                    line.current_year = False
                    if not self.mapped("sales_target_lines").filtered(
                        lambda ln: ln.date_order.year == selected_dt.year
                    ):
                        self.create_months(selected_dt)

    def create_months(self, date):
        if date:
            current_year = date.year
            jan = "1-1-%s" % current_year
            feb = "1-2-%s" % current_year
            march = "1-3-%s" % current_year
            april = "1-4-%s" % current_year
            may = "1-5-%s" % current_year
            june = "1-6-%s" % current_year
            july = "1-7-%s" % current_year
            aug = "1-8-%s" % current_year
            sept = "1-9-%s" % current_year
            octo = "1-10-%s" % current_year
            nov = "1-11-%s" % current_year
            dec = "1-12-%s" % current_year
            jan = datetime.strptime(jan, '%d-%m-%Y').date()
            feb = datetime.strptime(feb, '%d-%m-%Y').date()
            march = datetime.strptime(march, '%d-%m-%Y').date()
            april = datetime.strptime(april, '%d-%m-%Y').date()
            may = datetime.strptime(may, '%d-%m-%Y').date()
            june = datetime.strptime(june, '%d-%m-%Y').date()
            july = datetime.strptime(july, '%d-%m-%Y').date()
            aug = datetime.strptime(aug, '%d-%m-%Y').date()
            sept = datetime.strptime(sept, '%d-%m-%Y').date()
            octo = datetime.strptime(octo, '%d-%m-%Y').date()
            nov = datetime.strptime(nov, '%d-%m-%Y').date()
            dec = datetime.strptime(dec, '%d-%m-%Y').date()
            dates = [jan, feb, march, april, may, june, july, aug, sept, octo, nov, dec]
            for dt in dates:
                end_date = "%s-%s-%s" % (monthrange(current_year, dt.month)[1],dt.month,dt.year)
                endt = datetime.strptime(end_date, '%d-%m-%Y').date()
                self.env['sales.target.lines'].create({
                    'target_id': self.id,
                    'date_order': endt,
                    'user_id': self.salesperson.id,
                })

    @api.onchange('sales_team_id')
    def _onchange_default_team_leader(self):
        if self.sales_team_id:
            self.team_leader = self.sales_team_id.user_id
            
    @api.onchange('team_leader')
    def onchange_team_leader(self):
        TeamMembers = []
        for team in self.env['crm.team'].sudo().search([('user_id', '=', self.team_leader.id)]):
            for t in team.member_ids.ids:
                if t not in TeamMembers:
                    TeamMembers.append(t)
        return {'domain': {'salesperson': [('id', 'in', TeamMembers )]}}
        
    @api.depends('salesperson', 'start_date', 'end_date')
    def _get_total_sales(self):
        for rec in self:
            stdt = Datetime.to_string(rec.start_date)
            endt = Datetime.to_string(rec.end_date)
            SaleOrders = self.env['account.move'].search(
                [('user_id', '=', rec.salesperson.id),
                 ('create_date', '>=', stdt),
                 ('create_date', '<=', endt),
                 ('state', '=', 'posted'),
                 ('move_type', '=', 'out_invoice')])
            rec.sales = len(SaleOrders)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(SalesTarget, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if view_type == 'form':
            for st in self.env['sales.target'].search([]):
                st._get_perct_achievement()
                st._get_total_sales()
        return res
    
    @api.depends('salesperson', 'target', 'currency_id', 'start_date', 'end_date', 'target_achieve')
    def _get_perct_achievement(self):
        for rec in self:
            last_days = monthrange(fields.Datetime.today().year, fields.Datetime.today().month)[1]
            stdt = Datetime.to_string(fields.Datetime.today().replace(day=1))
            endt = Datetime.to_string(fields.Datetime.today().replace(day=last_days))
            perct_achievement = 0.00
            achieve = 0.00
            if rec.target_achieve == 'sale_order_confirm':
                SaleOrders = self.env['sale.order'].search([('user_id','=',rec.salesperson.id),('state','in',['sale','done']),
                                                            ('currency_id','=',rec.currency_id.id),('date_order','>=',stdt),('date_order','<=',endt)])
                total_amount = 0.00
                for sale in SaleOrders:
                    total_amount += sale.amount_total
                if total_amount < rec.target:
                    perct_achievement = (total_amount / rec.target or 1 ) * 100
                if rec.target != 0.00 and total_amount >= rec.target:
                    perct_achievement = 100
                if rec.target != 0.00 and total_amount == 0.00:
                    perct_achievement = 0
                achieve = total_amount
            if rec.target_achieve == 'delivery_order_done':
                SaleOrders = self.env['sale.order'].search([('user_id','=',rec.salesperson.id),('currency_id','=',rec.currency_id.id)
                                                            ,('date_order','>=',stdt),('date_order','<=',endt)])
                total_amount = 0.00
                for sale in SaleOrders:
                    picking_ids = self.env['stock.picking'].search([('origin','=',sale.name)])
                    delivery = [True if any(p.state =='done' for p in picking_ids) else False]
                    if delivery[0] == True:
                        total_amount += sale.amount_total
                if total_amount < rec.target:
                    perct_achievement = (total_amount / rec.target or 1 ) * 100
                if rec.target != 0.00 and total_amount >= rec.target:
                    perct_achievement = 100
                if rec.target != 0.00 and total_amount == 0.00:
                    perct_achievement = 0
                achieve = total_amount
            if rec.target_achieve == 'invoice_created':
                MoveOrders = self.env['account.move'].search([
                    ('invoice_user_id', '=', rec.salesperson.id),
                    ('create_date', '>=', stdt),
                    ('create_date', '<=', endt),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice')
                ])
                total_amount = 0.00
                company_currency = self.env.company.currency_id
                foreing_currency = self.env['res.currency'].search([('name', '=', 'USD')])
                for move in MoveOrders:
                    if move.currency_id != company_currency:
                        total_amount += move.amount_untaxed
                    if move.currency_id == company_currency:
                        # Conversion al TC de La creacion de la factura pesos a USD
                        total_amount += company_currency._convert(move.amount_untaxed, foreing_currency, self.env.company, move.create_date)
                if total_amount < rec.target:
                    perct_achievement = (total_amount / rec.target or 1) * 100
                if rec.target != 0.00 and total_amount >= rec.target:
                    perct_achievement = 100
                if rec.target != 0.00 and total_amount == 0.00:
                    perct_achievement = 0
                achieve = total_amount
            if rec.target_achieve == 'invoice_paid':
                SaleOrders = self.env['sale.order'].search([('user_id','=',rec.salesperson.id),('currency_id','=',rec.currency_id.id),
                                                            ('date_order','>=',stdt),('date_order','<=',endt)])
                total_amount = 0.00
                for sale in SaleOrders:
                    invoice_paid = [True if any(i.payment_state == 'paid' for i in sale.invoice_ids) else False]
                    if invoice_paid[0] == True:
                        total_amount += sale.amount_total 
                if total_amount < rec.target:
                    perct_achievement = (total_amount / rec.target or 1 ) * 100
                if rec.target != 0.00 and total_amount >= rec.target:
                    perct_achievement = 100
                if rec.target != 0.00 and total_amount == 0.00:
                    perct_achievement = 0
                achieve = total_amount
            rec.perct_achievement = perct_achievement 
            rec.achieve = achieve 
    
    def get_perct_achievement(self,salesperson,target,currency_id,start_date,end_date,target_achieve):
        stdt = Datetime.to_string(start_date)
        endt = Datetime.to_string(end_date)
        perct_achievement = 0.00
        achieve = 0.00
        if target_achieve == 'sale_order_confirm':
            SaleOrders = self.env['sale.order'].search([('user_id','=',salesperson),('state','in',['sale','done']),
                                                        ('currency_id','=',currency_id),('date_order','>=',stdt),('date_order','<=',endt)])
            total_amount = 0.00
            for sale in SaleOrders:
                total_amount += sale.amount_total
            if total_amount < target:
                perct_achievement = (total_amount / target or 1 ) * 100
            if target != 0.00 and total_amount >= target:
                perct_achievement = 100
            if target != 0.00 and total_amount == 0.00:
                perct_achievement = 0
            achieve = total_amount
        if target_achieve == 'delivery_order_done':
            SaleOrders = self.env['sale.order'].search([('user_id','=',salesperson),('currency_id','=',currency_id)
                                                        ,('date_order','>=',stdt),('date_order','<=',endt)])
            total_amount = 0.00
            for sale in SaleOrders:
                picking_ids = self.env['stock.picking'].search([('origin','=',sale.name)])
                delivery = [True if any(p.state =='done' for p in picking_ids) else False]
                if delivery[0] == True:
                    total_amount += sale.amount_total 
            if total_amount < target:
                perct_achievement = (total_amount / target or 1 ) * 100
            if target != 0.00 and total_amount >= target:
                perct_achievement = 100
            if target != 0.00 and total_amount == 0.00:
                perct_achievement = 0
            achieve = total_amount
        if target_achieve == 'invoice_created':
            move_ids = self.env['account.move'].search([
                ('invoice_user_id', '=', salesperson),
                ('create_date', '>=', stdt),
                ('create_date', '<=', endt),
                ('state', '=', 'posted'),
                ('move_type', '=', 'out_invoice')
            ])
            total_amount = 0.00
            company_currency = self.env.company.currency_id
            foreing_currency = self.env['res.currency'].search([('name', '=', 'USD')])
            for move in move_ids:
                if move.currency_id != company_currency:
                    total_amount += move.amount_untaxed
                if move.currency_id == company_currency:
                    # Conversion al TC de La creacion de la factura pesos a USD
                    total_amount += company_currency._convert(move.amount_untaxed, foreing_currency, self.env.company,
                                                              move.create_date)
            if total_amount < target:
                perct_achievement = (total_amount / target or 1) * 100
            if target != 0.00 and total_amount >= target:
                perct_achievement = 100
            if target != 0.00 and total_amount == 0.00:
                perct_achievement = 0
            achieve = total_amount
        if target_achieve == 'invoice_paid':
            SaleOrders = self.env['sale.order'].search([('user_id','=',salesperson),('currency_id','=',currency_id),
                                                        ('date_order','>=',stdt),('date_order','<=',endt)])
            total_amount = 0.00
            for sale in SaleOrders:
                invoice_paid = [True if any(i.payment_state == 'paid' for i in sale.invoice_ids) else False]
                if invoice_paid[0] == True:
                    total_amount += sale.amount_total 
            if total_amount < target:
                perct_achievement = (total_amount / target or 1 ) * 100
            if target != 0.00 and total_amount >= target:
                perct_achievement = 100
            if target != 0.00 and total_amount == 0.00:
                perct_achievement = 0
            achieve = total_amount
        return  achieve,perct_achievement
    
    def get_total_sales(self, salesperson, start_date, end_date):
        stdt = Datetime.to_string(start_date)
        endt = Datetime.to_string(end_date)
        BillingOrders = self.env['account.move'].search([
            ('invoice_user_id', '=', salesperson),
            ('create_date', '>=', stdt),
            ('create_date', '<=', endt),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted')
        ])
        return len(BillingOrders)
            
    def _get_sales_target_lines(self):
        current_year = datetime.now().year
        jan = "1-1-%s" % current_year
        feb = "1-2-%s" % current_year
        march = "1-3-%s" % current_year
        april = "1-4-%s" % current_year
        may = "1-5-%s" % current_year
        june = "1-6-%s" % current_year
        july = "1-7-%s" % current_year
        aug = "1-8-%s" % current_year
        sept = "1-9-%s" % current_year
        octo = "1-10-%s" % current_year
        nov = "1-11-%s" % current_year
        dec = "1-12-%s" % current_year
        jan = datetime.strptime(jan, '%d-%m-%Y').date()
        feb = datetime.strptime(feb, '%d-%m-%Y').date()
        march = datetime.strptime(march, '%d-%m-%Y').date()
        april = datetime.strptime(april, '%d-%m-%Y').date()
        may = datetime.strptime(may, '%d-%m-%Y').date()
        june = datetime.strptime(june, '%d-%m-%Y').date()
        july = datetime.strptime(july, '%d-%m-%Y').date()
        aug = datetime.strptime(aug, '%d-%m-%Y').date()
        sept = datetime.strptime(sept, '%d-%m-%Y').date()
        octo = datetime.strptime(octo, '%d-%m-%Y').date()
        nov = datetime.strptime(nov, '%d-%m-%Y').date()
        dec = datetime.strptime(dec, '%d-%m-%Y').date()
        dates = [jan, feb, march, april, may, june, july, aug, sept, octo, nov, dec]
        for rec in self:
            for dt in dates:
                stdt = dt
                end_date = "%s-%s-%s" % (monthrange(current_year, dt.month)[1],dt.month,dt.year)
                endt = datetime.strptime(end_date, '%d-%m-%Y').date()
                sales = self.get_total_sales(rec.salesperson.id,stdt,endt)
                line = self.env['sales.target.lines'].search([('target_id','=',rec.id),('user_id','=',rec.salesperson.id),('date_order','=',endt)])
                if line:
                    monthly_target_achieve, monthly_target_achieve_per = self.get_perct_achievement(rec.salesperson.id,line.monthly_target,rec.currency_id.id,stdt,endt,rec.target_achieve)
                    line.write({
                        'monthly_target': line.monthly_target,
                        'currency_id': rec.currency_id.id,
                        'monthly_target_achieve': monthly_target_achieve,
                        'monthly_target_achieve_per': monthly_target_achieve_per
                    })


class SalesTargetLines(models.Model):
    _name = "sales.target.lines"
    _description = "Sales Target Lines"
    _rec_name = 'user_id'
    _order = 'id desc'        
    
    target_id = fields.Many2one("sales.target", string="Sales Target", copy=False, index=True, ondelete='cascade')
    date_order = fields.Date("Order Date", copy=False)
    user_id = fields.Many2one("res.users", string="Salesperson", copy=False)
    monthly_target = fields.Float("Monthly Target", copy=False)
    currency_id = fields.Many2one("res.currency", string="Currency", copy=False)
    monthly_target_achieve = fields.Float("Monthly Target Achieved", copy=False)
    no_of_sales = fields.Integer("Billing Sales",compute="_get_total_sales", store=True, copy=False)
    monthly_target_achieve_per = fields.Float("Monthly Target Achieved Percentage", copy=False)
    gap = fields.Float(copy=False)
    current_year = fields.Boolean(copy=False)

    @api.depends('user_id', 'date_order')
    def _get_total_sales(self):
        for rec in self:
            if rec._origin:
                start_date = "%s-%s-%s" % (1, rec.date_order.month,rec.date_order.year)
                start_date = datetime.strptime(start_date, '%d-%m-%Y').date()
                stdt = Datetime.to_string(start_date)
                endt = Datetime.to_string(rec.date_order)
                BillingOrders = self.env['account.move'].search([
                    ('user_id', '=', rec.user_id.id),
                    ('create_date', '>=', stdt),
                    ('create_date', '<=', endt),
                    ('state', '=', 'posted'),
                    ('move_type', '=', 'out_invoice')
                ])

                rec.no_of_sales = len(BillingOrders)