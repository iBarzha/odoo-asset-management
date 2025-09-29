# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ITAssetCategory(models.Model):
    _name = 'it.asset.category'
    _description = 'IT Asset Category'
    _order = 'sequence, name'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'

    name = fields.Char('Category Name', required=True, translate=True)
    code = fields.Char('Category Code', required=True, size=10)
    sequence = fields.Integer('Sequence', default=10, help="Used to order categories")
    description = fields.Text('Description', translate=True)
    active = fields.Boolean('Active', default=True)

    # Hierarchy fields
    parent_id = fields.Many2one(
        'it.asset.category',
        'Parent Category',
        index=True,
        ondelete='cascade'
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        'it.asset.category',
        'parent_id',
        'Child Categories'
    )
    complete_name = fields.Char(
        'Complete Name',
        compute='_compute_complete_name',
        recursive=True,
        store=True
    )

    # Asset relationship
    asset_ids = fields.One2many('it.asset', 'category_id', 'Assets')
    asset_count = fields.Integer('Asset Count', compute='_compute_asset_count')

    # Color for kanban view
    color = fields.Integer('Color', default=0)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name

    @api.depends('asset_ids')
    def _compute_asset_count(self):
        for category in self:
            category.asset_count = len(category.asset_ids)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('You cannot create recursive categories.'))

    @api.constrains('code')
    def _check_code_unique(self):
        for category in self:
            if category.code:
                existing = self.search([
                    ('code', '=', category.code),
                    ('id', '!=', category.id)
                ])
                if existing:
                    raise ValidationError(_('Category code must be unique!'))

    @api.model
    def name_create(self, name):
        """Allow quick category creation from many2one fields"""
        return self.create({'name': name, 'code': name.upper()[:10]}).name_get()[0]

    def name_get(self):
        """Return category name with hierarchy"""
        result = []
        for category in self:
            name = category.complete_name or category.name
            result.append((category.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            # Search in both name and code fields
            category_ids = self._search([
                '|',
                ('name', operator, name),
                ('code', operator, name)
            ] + args, limit=limit, access_rights_uid=name_get_uid)
        else:
            category_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return category_ids

    def action_view_assets(self):
        """Action to view assets in this category"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assets in %s') % self.name,
            'res_model': 'it.asset',
            'view_mode': 'list,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }

    def get_descendants(self):
        """Get all descendant categories including self"""
        return self.search([('id', 'child_of', self.ids)])

    def get_ancestors(self):
        """Get all ancestor categories including self"""
        return self.search([('id', 'parent_of', self.ids)])