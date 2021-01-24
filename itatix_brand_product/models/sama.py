from odoo import fields, models, api
from odoo.exceptions import UserError


class SamaCategory(models.Model):
    _name = 'sama.category'
    name = fields.Char(copy=False)

    @api.constrains('name')
    def _check_name_category(self):
        for record in self:
            if record.search_count([('name', '=', record.name)]) > 1:
                raise UserError("Ya existe la marca {}".format(record.name))


class SamaSubCategory(models.Model):
    _name = 'sama.subcategory'
    name = fields.Char(copy=False)

    @api.constrains('name')
    def _check_name_subcategory(self):
        for record in self:
            if record.search_count([('name', '=', record.name)]) > 1:
                raise UserError("Ya existe la Subcategoría {}".format(record.name))


class SamaBrand(models.Model):
    _name = 'sama.brand'
    name = fields.Char(copy=False)

    @api.constrains('name')
    def _check_name_category(self):
        for record in self:
            if record.search_count([('name', '=', record.name)]) > 1:
                raise UserError("Ya existe la categoría {}".format(record.name))
