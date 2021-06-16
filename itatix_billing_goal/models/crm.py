from odoo import api, fields, models, tools


class CrmStage(models.Model):

    _inherit = "crm.stage"

    probability = fields.Float(
        "Probability (%)",
        required=True,
        default=10.0,
        help="This percentage depicts the default/average probability of the "
             "Case for this stage to be a success",
    )
    on_change = fields.Boolean(
        "Change Probability Automatically",
        help="Setting this stage will change the probability automatically on "
             "the opportunity.",
    )

    _sql_constraints = [
        (
            "check_probability",
            "check(probability >= 0 and probability <= 100)",
            "The probability should be between 0% and 100%!",
        )
    ]


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    invoiced_target = fields.Float(group_operator="avg")

    def _compute_quotations_to_invoice(self):
        res = super(CrmTeam, self)._compute_quotations_to_invoice()
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
        return res

    def _compute_invoiced(self):
        res = super(CrmTeam, self)._compute_invoiced()
        if not self:
            return

        query = '''
            SELECT
                move.team_id         AS team_id,
                SUM(-line.amount_currency)   AS amount_untaxed_signed
            FROM account_move move
            JOIN account_move_line line ON line.move_id = move.id
            JOIN account_account account ON account.id = line.account_id
            WHERE move.move_type IN ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')
            AND move.payment_state IN ('in_payment', 'paid', 'reversed')
            AND move.state = 'posted'
            AND move.team_id IN %s
            AND move.date BETWEEN %s AND %s
            AND line.tax_line_id IS NULL
            AND line.display_type IS NULL
            AND account.internal_type NOT IN ('receivable', 'payable')
            GROUP BY move.team_id
        '''
        today = fields.Date.today()
        params = [tuple(self.ids), fields.Date.to_string(today.replace(day=1)), fields.Date.to_string(today)]
        self._cr.execute(query, params)

        data_map = dict((v[0], v[1]) for v in self._cr.fetchall())
        for team in self:
            team.invoiced = data_map.get(team.id, 0.0)
        return res


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    billing_goal = fields.Float(related='user_id.billing_goal', group_operator="avg", store=True)
    invoiced_target = fields.Float(related='team_id.invoiced_target', group_operator="avg", store=True)
    stage_probability = fields.Float(related="stage_id.probability", readonly=True)
    probability = fields.Float(readonly=True)
    is_stage_probability = fields.Boolean(
        compute="_compute_is_stage_probability", readonly=True
    )

    @api.depends("probability", "stage_id", "stage_id.probability")
    def _compute_is_stage_probability(self):
        for lead in self:
            lead.is_stage_probability = (
                    tools.float_compare(lead.probability, lead.stage_probability, 2) == 0
            )

    @api.depends("probability", "automated_probability")
    def _compute_is_automated_probability(self):
        for lead in self:
            if lead.probability != lead.stage_id.probability:
                super(CrmLead, lead)._compute_is_automated_probability()
                continue
            lead.is_automated_probability = False

    @api.depends(lambda self: ['tag_ids', 'stage_id', 'team_id'] + self._pls_get_safe_fields())
    def _compute_probabilities(self):
        for lead in self:
            lead.probability = lead.stage_id.probability

    def action_set_stage_probability(self):
        self.write({"probability": self.stage_id.probability})