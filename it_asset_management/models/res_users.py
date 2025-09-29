# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Asset related fields
    asset_assignment_ids = fields.One2many(
        'it.asset.assignment',
        'user_id',
        'Asset Assignments',
        help="All assets assigned to this user"
    )
    current_asset_assignment_ids = fields.One2many(
        'it.asset.assignment',
        'user_id',
        'Current Assets',
        domain=[('is_active', '=', True)],
        help="Assets currently assigned to this user"
    )
    asset_request_ids = fields.One2many(
        'it.asset.request',
        'user_id',
        'Asset Requests',
        help="All requests made by this user"
    )

    # Computed fields for counts
    asset_count = fields.Integer(
        'Assets Count',
        compute='_compute_asset_count',
        help="Number of assets currently assigned"
    )
    assignment_count = fields.Integer(
        'Assignments Count',
        compute='_compute_assignment_count',
        help="Total number of asset assignments (including past)"
    )
    request_count = fields.Integer(
        'Requests Count',
        compute='_compute_request_count',
        help="Total number of requests made"
    )
    pending_request_count = fields.Integer(
        'Pending Requests',
        compute='_compute_pending_request_count',
        help="Number of pending requests"
    )

    # Asset management fields
    is_asset_manager = fields.Boolean(
        'Is Asset Manager',
        compute='_compute_is_asset_manager',
        help="Whether this user is an asset manager"
    )
    is_asset_user = fields.Boolean(
        'Is Asset User',
        compute='_compute_is_asset_user',
        help="Whether this user can manage assets"
    )

    # Portal asset access
    portal_asset_access = fields.Boolean(
        'Portal Asset Access',
        default=True,
        help="Allow this user to access assets through portal"
    )

    @api.depends('current_asset_assignment_ids')
    def _compute_asset_count(self):
        for user in self:
            user.asset_count = len(user.current_asset_assignment_ids)

    @api.depends('asset_assignment_ids')
    def _compute_assignment_count(self):
        for user in self:
            user.assignment_count = len(user.asset_assignment_ids)

    @api.depends('asset_request_ids')
    def _compute_request_count(self):
        for user in self:
            user.request_count = len(user.asset_request_ids)

    @api.depends('asset_request_ids.state')
    def _compute_pending_request_count(self):
        for user in self:
            user.pending_request_count = len(user.asset_request_ids.filtered(
                lambda r: r.state in ['draft', 'submitted', 'under_review', 'approved', 'in_progress']
            ))

    @api.depends('groups_id')
    def _compute_is_asset_manager(self):
        asset_manager_group = self.env.ref('it_asset_management.group_asset_manager', raise_if_not_found=False)
        for user in self:
            user.is_asset_manager = asset_manager_group and asset_manager_group in user.groups_id

    @api.depends('groups_id')
    def _compute_is_asset_user(self):
        asset_user_group = self.env.ref('it_asset_management.group_asset_user', raise_if_not_found=False)
        for user in self:
            user.is_asset_user = asset_user_group and asset_user_group in user.groups_id

    def action_view_my_assets(self):
        """View assets assigned to this user"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('My Assets'),
            'res_model': 'it.asset.assignment',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id), ('is_active', '=', True)],
            'context': {'default_user_id': self.id},
        }

    def action_view_my_requests(self):
        """View requests made by this user"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('My Requests'),
            'res_model': 'it.asset.request',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
        }

    def action_view_assignment_history(self):
        """View complete assignment history for this user"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assignment History'),
            'res_model': 'it.asset.assignment',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
        }

    def action_create_asset_request(self):
        """Create new asset request for this user"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Asset Request'),
            'res_model': 'it.asset.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_user_id': self.id,
                'default_request_type': 'new_asset',
            },
        }

    def get_assigned_assets(self):
        """Get all currently assigned assets for this user"""
        self.ensure_one()
        return self.current_asset_assignment_ids.mapped('asset_id')

    def get_overdue_assignments(self):
        """Get overdue assignments for this user"""
        self.ensure_one()
        today = fields.Date.today()
        return self.current_asset_assignment_ids.filtered(
            lambda a: a.expected_return_date and a.expected_return_date < today
        )

    def get_pending_requests(self):
        """Get pending requests for this user"""
        self.ensure_one()
        return self.asset_request_ids.filtered(
            lambda r: r.state in ['draft', 'submitted', 'under_review', 'approved', 'in_progress']
        )

    def has_asset_access(self):
        """Check if user has access to asset management"""
        self.ensure_one()
        return (
            self.is_asset_manager or
            self.is_asset_user or
            self.has_group('it_asset_management.group_portal_asset_user')
        )

    @api.model
    def get_users_with_overdue_assets(self):
        """Get all users with overdue asset assignments"""
        today = fields.Date.today()
        overdue_assignments = self.env['it.asset.assignment'].search([
            ('is_active', '=', True),
            ('expected_return_date', '<', today)
        ])
        return overdue_assignments.mapped('user_id')

    @api.model
    def get_users_with_pending_requests(self):
        """Get all users with pending asset requests"""
        pending_requests = self.env['it.asset.request'].search([
            ('state', 'in', ['draft', 'submitted', 'under_review', 'approved', 'in_progress'])
        ])
        return pending_requests.mapped('user_id')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Asset related fields for suppliers
    is_asset_supplier = fields.Boolean('Is Asset Supplier')
    supplied_asset_ids = fields.One2many(
        'it.asset',
        'supplier_id',
        'Supplied Assets',
        help="Assets supplied by this partner"
    )
    supplied_asset_count = fields.Integer(
        'Supplied Assets Count',
        compute='_compute_supplied_asset_count'
    )

    @api.depends('supplied_asset_ids')
    def _compute_supplied_asset_count(self):
        for partner in self:
            partner.supplied_asset_count = len(partner.supplied_asset_ids)

    def action_view_supplied_assets(self):
        """View assets supplied by this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Supplied Assets'),
            'res_model': 'it.asset',
            'view_mode': 'list,form',
            'domain': [('supplier_id', '=', self.id)],
            'context': {'default_supplier_id': self.id},
        }