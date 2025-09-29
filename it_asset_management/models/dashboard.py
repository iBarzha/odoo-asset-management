# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class AssetDashboard(models.TransientModel):
    _name = 'it.asset.dashboard'
    _description = 'IT Asset Management Dashboard'

    # Overview Statistics
    total_assets = fields.Integer('Total Assets', compute='_compute_asset_stats')
    available_assets = fields.Integer('Available Assets', compute='_compute_asset_stats')
    assigned_assets = fields.Integer('Assigned Assets', compute='_compute_asset_stats')
    maintenance_assets = fields.Integer('Under Maintenance', compute='_compute_asset_stats')
    repair_assets = fields.Integer('Under Repair', compute='_compute_asset_stats')

    # Request Statistics
    total_requests = fields.Integer('Total Requests', compute='_compute_request_stats')
    pending_requests = fields.Integer('Pending Requests', compute='_compute_request_stats')
    approved_requests = fields.Integer('Approved Requests', compute='_compute_request_stats')
    completed_requests = fields.Integer('Completed Requests', compute='_compute_request_stats')
    overdue_requests = fields.Integer('Overdue Requests', compute='_compute_request_stats')

    # Assignment Statistics
    total_assignments = fields.Integer('Total Assignments', compute='_compute_assignment_stats')
    active_assignments = fields.Integer('Active Assignments', compute='_compute_assignment_stats')
    overdue_assignments = fields.Integer('Overdue Assignments', compute='_compute_assignment_stats')

    # Warranty Statistics
    warranty_expiring = fields.Integer('Warranty Expiring Soon', compute='_compute_warranty_stats')
    warranty_expired = fields.Integer('Warranty Expired', compute='_compute_warranty_stats')

    # Financial Statistics
    total_asset_value = fields.Float('Total Asset Value', compute='_compute_financial_stats')
    monthly_cost = fields.Float('Monthly Estimated Cost', compute='_compute_financial_stats')

    @api.depends()
    def _compute_asset_stats(self):
        for dashboard in self:
            assets = self.env['it.asset'].search([('active', '=', True)])
            dashboard.total_assets = len(assets)
            dashboard.available_assets = len(assets.filtered(lambda a: a.state == 'available'))
            dashboard.assigned_assets = len(assets.filtered(lambda a: a.state == 'assigned'))
            dashboard.maintenance_assets = len(assets.filtered(lambda a: a.state == 'maintenance'))
            dashboard.repair_assets = len(assets.filtered(lambda a: a.state == 'repair'))

    @api.depends()
    def _compute_request_stats(self):
        for dashboard in self:
            requests = self.env['it.asset.request'].search([])
            dashboard.total_requests = len(requests)
            dashboard.pending_requests = len(requests.filtered(lambda r: r.state in ['submitted', 'under_review']))
            dashboard.approved_requests = len(requests.filtered(lambda r: r.state == 'approved'))
            dashboard.completed_requests = len(requests.filtered(lambda r: r.state == 'completed'))
            dashboard.overdue_requests = len(requests.filtered(lambda r: r.is_overdue))

    @api.depends()
    def _compute_assignment_stats(self):
        for dashboard in self:
            assignments = self.env['it.asset.assignment'].search([])
            dashboard.total_assignments = len(assignments)
            dashboard.active_assignments = len(assignments.filtered(lambda a: a.is_active))
            dashboard.overdue_assignments = len(assignments.filtered(lambda a: a.is_overdue))

    @api.depends()
    def _compute_warranty_stats(self):
        for dashboard in self:
            assets = self.env['it.asset'].search([('active', '=', True)])
            dashboard.warranty_expiring = len(assets.filtered(lambda a: a.warranty_status == 'expiring'))
            dashboard.warranty_expired = len(assets.filtered(lambda a: a.warranty_status == 'expired'))

    @api.depends()
    def _compute_financial_stats(self):
        for dashboard in self:
            assets = self.env['it.asset'].search([('active', '=', True)])
            dashboard.total_asset_value = sum(assets.mapped('purchase_price'))

            # Calculate monthly cost from pending requests
            pending_requests = self.env['it.asset.request'].search([
                ('state', 'in', ['submitted', 'under_review', 'approved', 'in_progress'])
            ])
            dashboard.monthly_cost = sum(pending_requests.mapped('estimated_cost'))

    def action_view_assets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('All Assets'),
            'res_model': 'it.asset',
            'view_mode': 'kanban,list,form',
            'target': 'current',
        }

    def action_view_available_assets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Available Assets'),
            'res_model': 'it.asset',
            'view_mode': 'kanban,list,form',
            'domain': [('state', '=', 'available')],
            'target': 'current',
        }

    def action_view_assigned_assets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assigned Assets'),
            'res_model': 'it.asset',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'assigned')],
            'target': 'current',
        }

    def action_view_maintenance_assets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assets Under Maintenance'),
            'res_model': 'it.asset',
            'view_mode': 'list,form',
            'domain': [('state', 'in', ['maintenance', 'repair'])],
            'target': 'current',
        }

    def action_view_pending_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pending Requests'),
            'res_model': 'it.asset.request',
            'view_mode': 'kanban,list,form',
            'domain': [('state', 'in', ['submitted', 'under_review'])],
            'target': 'current',
        }

    def action_view_overdue_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Overdue Requests'),
            'res_model': 'it.asset.request',
            'view_mode': 'list,form',
            'domain': [('is_overdue', '=', True)],
            'target': 'current',
        }

    def action_view_overdue_assignments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Overdue Assignments'),
            'res_model': 'it.asset.assignment',
            'view_mode': 'list,form',
            'domain': [('is_overdue', '=', True)],
            'target': 'current',
        }

    def action_view_warranty_expiring(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Warranty Expiring Soon'),
            'res_model': 'it.asset',
            'view_mode': 'list,form',
            'domain': [('warranty_status', '=', 'expiring')],
            'target': 'current',
        }

    def action_view_warranty_expired(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Warranty Expired'),
            'res_model': 'it.asset',
            'view_mode': 'list,form',
            'domain': [('warranty_status', '=', 'expired')],
            'target': 'current',
        }