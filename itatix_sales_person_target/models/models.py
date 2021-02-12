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

    @api.onchange('member_ids')
    def onchange_member_ids(self):
        UserObj = self.env['res.users'].sudo().search([('id','=',self.user_id.id)])
        UserObj._get_member_ids()


class SalesTarget(models.Model):
    _name = "sales.target"
    _description = "Sales Target"
    _rec_name = 'salesperson'
    _order = 'id desc'

    team_leader = fields.Many2one(related='sales_team_id.user_id', store=True)
    salesperson = fields.Many2one("res.users", string="Salesperson")
    target = fields.Float("Target")
    monthly_target = fields.Float("Monthly Target")  # Quota/Meta de facturacion
    achieve = fields.Float("Achieve", compute="_get_perct_achievement", store=True)
    currency_id = fields.Many2one("res.currency", string="Currency")
    start_date = fields.Date("From")
    end_date = fields.Date("To")
    sales = fields.Integer("Sales", compute="_get_total_sales", store=True)
    perct_achievement = fields.Float("% Achievement", compute="_get_perct_achievement", store=True)
    target_achieve = fields.Selection([('sale_order_confirm', "Sale Order Confirm"),
                                       ('delivery_order_done', 'Delivery Order Done'),
                                       ('invoice_created', 'Invoice Created'),
                                       ('invoice_paid', 'Invoice Paid')], string="Target Achieve", default="sale_order_confirm")
    sales_team_id = fields.Many2one('crm.team')
    sales_target_lines = fields.One2many("sales.target.lines", "target_id", string="Taget Lines")

    def create_months(self):
        if self.start_date:
            current_year = self.start_date.year
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
                line = self.env['sales.target.lines'].search([('target_id', '=', self.id),('user_id','=', self.salesperson.id),('date_order','=', endt)])
                if not line:
                    line.create({
                        'target_id': self.id,
                        'date_order': endt,
                        'user_id': self.salesperson.id,
                        'currency_id': self.currency_id.id,
                        })

    @api.onchange('sales_team_id')
    def _onchange_default_team_leader(self):
        if self.sales_team_id:
            self.team_leader = self.sales_team_id.user_id

    # @api.depends('target')
    # def _get_monthly_target(self):
    #     """
    #     Pone la meta de facturación según la fecha condicionada de START_DATE Y END_DATE
    #     SI no tiene una meta de facturacion establecida pone automaticamente la de meta de facturacion
    #     global de las metas de venta
    #     :return:
    #     """
    #     for record in self:
    #         if record.target:
    #             if not record.sales_team_id.invoiced_target:
    #                 raise UserError("Se requiere tener una meta de facturacion en el equipo de ventas")
    #             record.monthly_target = record.sales_team_id.invoiced_target
    #             for line in record.sales_target_lines:
    #                 if line.date_order == record.end_date:
    #                     line.monthly_target = record.monthly_target
    #         else:
    #             record.monthly_target = 0.0
            
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
            SaleOrders = self.env['sale.order'].search(
                [('user_id','=',rec.salesperson.id),
                 ('date_order','>=',stdt),
                 ('currency_id','=',rec.currency_id.id),
                 ('date_order','<=',endt)])
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
            stdt = Datetime.to_string(rec.start_date)
            endt = Datetime.to_string(rec.end_date)
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
                SaleOrders = self.env['sale.order'].search([('user_id','=',rec.salesperson.id),('currency_id','=',rec.currency_id.id),
                                                            ('date_order','>=',stdt),('date_order','<=',endt)])
                total_amount = 0.00
                for sale in SaleOrders:
                    invoice = [True if sale.invoice_ids else False]
                    if invoice[0] == True:
                        total_amount += sale.amount_total 
                if total_amount < rec.target:
                    perct_achievement = (total_amount / rec.target or 1 ) * 100
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
            SaleOrders = self.env['sale.order'].search([('user_id','=',salesperson),('currency_id','=',currency_id),
                                                        ('date_order','>=',stdt),('date_order','<=',endt)])
            total_amount = 0.00
            for sale in SaleOrders:
                invoice = [True if sale.invoice_ids else False]
                if invoice[0] == True:
                    total_amount += sale.amount_total 
            if total_amount < target:
                perct_achievement = (total_amount / target or 1 ) * 100
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
    
    def get_total_sales(self,salesperson,start_date,end_date):
        stdt = Datetime.to_string(start_date)
        endt = Datetime.to_string(end_date)
        SaleOrders = self.env['sale.order'].search([('user_id','=',salesperson),('date_order','>=',stdt)
                                                    ,('currency_id','=',self.currency_id.id),('date_order','<=',endt)])
        return len(SaleOrders)
            
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
                monthly_target_achieve , monthly_target_achieve_per = self.get_perct_achievement(rec.salesperson.id,rec.monthly_target,rec.currency_id.id,stdt,endt,rec.target_achieve)
                sales = self.get_total_sales(rec.salesperson.id,stdt,endt)
                line = self.env['sales.target.lines'].search([('target_id','=',rec.id),('user_id','=',rec.salesperson.id),('date_order','=',endt)])
                if line:
                    line.write({
                        'monthly_target': line.monthly_target,
                        'currency_id': rec.currency_id.id,
                        'monthly_target_achieve': monthly_target_achieve,
                        'monthly_target_achieve_per': monthly_target_achieve_per
                    })
                # if not line:
                #     line.create({
                #         'target_id': rec.id,
                #         'date_order': endt,
                #         'user_id': rec.salesperson.id,
                #         'monthly_target': rec.monthly_target,
                #         'currency_id': rec.currency_id.id,
                #         'monthly_target_achieve': monthly_target_achieve,
                #         'monthly_target_achieve_per' : monthly_target_achieve_per,
                #         })
                # else:
                #     line = self.env['sales.target.lines'].search([('user_id','=',rec.salesperson.id),('date_order','=',endt),('target_id','=',rec.id)])
                #     line.write({
                #         'monthly_target': rec.monthly_target,
                #         'currency_id': rec.currency_id.id,
                #         'monthly_target_achieve': monthly_target_achieve,
                #         'monthly_target_achieve_per': monthly_target_achieve_per,
                #         })


class SalesTargetLines(models.Model):
    _name = "sales.target.lines"
    _description = "Sales Target Lines"
    _rec_name = 'user_id'
    _order = 'id desc'        
    
    target_id = fields.Many2one("sales.target",string="Sales Target", copy=False)
    date_order = fields.Date("Order Date", copy=False)
    user_id = fields.Many2one("res.users",string="Salesperson", copy=False)
    monthly_target = fields.Float("Monthly Target", copy=False)
    currency_id = fields.Many2one("res.currency",string="Currency", copy=False)
    monthly_target_achieve = fields.Float("Monthly Target Achieved", copy=False)
    no_of_sales = fields.Integer("Sales",compute="_get_total_sales",store=True, copy=False)
    monthly_target_achieve_per = fields.Float("Monthly Target Achieved Percentage", copy=False)
    gap = fields.Float(copy=False)

    @api.depends('user_id', 'date_order')
    def _get_total_sales(self):
        for rec in self:
            start_date = "%s-%s-%s" % (1,rec.date_order.month,rec.date_order.year)
            start_date = datetime.strptime(start_date, '%d-%m-%Y').date()
            stdt = Datetime.to_string(start_date)
            endt = Datetime.to_string(rec.date_order)
            SaleOrders = self.env['sale.order'].search([('user_id','=',rec.user_id.id),('date_order','>=',stdt)
                                                        ,('currency_id','=',rec.target_id.currency_id.id),('date_order','<=',endt)])

            rec.no_of_sales = len(SaleOrders)
    
    
