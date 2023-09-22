from odoo import fields, models


class Region(models.Model):
    _name = "partner.region"
    _description = "Regiones"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin"]

    name = fields.Char(string="Nombre de la región")
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(string="Activo", default=True)
