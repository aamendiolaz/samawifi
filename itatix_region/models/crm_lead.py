from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    region_id = fields.Many2one(comodel_name="partner.region",string="Region",
                                domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
