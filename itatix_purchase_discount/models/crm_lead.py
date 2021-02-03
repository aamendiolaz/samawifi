# -*- coding: utf-8 -*-

from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    dna = fields.Char(copy=False)
    final_user_id = fields.Many2one('res.partner', copy=False)
    channel = fields.Many2one('res.partner', copy=False)

    def action_new_quotation(self):
        res = super(CrmLead, self).action_new_quotation()
        if res.get('context', False):
            res['context']['default_dna'] = self.dna
            res['context']['default_final_user_id'] = self.final_user_id.id
            res['context']['deafult_channel'] = self.channel.id
            if self.final_user_id:
                self.final_user_id.write({'final_user_rank': True})
        return res