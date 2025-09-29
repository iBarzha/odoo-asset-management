# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Asset Management Settings
    asset_auto_generate_code = fields.Boolean(
        'Auto-generate Asset Codes',
        config_parameter='it_asset_management.auto_generate_code',
        default=True,
        help='Automatically generate unique asset codes when creating new assets'
    )

    asset_code_prefix = fields.Char(
        'Asset Code Prefix',
        config_parameter='it_asset_management.code_prefix',
        default='ASSET-',
        help='Prefix for automatically generated asset codes'
    )

    asset_code_sequence = fields.Many2one(
        'ir.sequence',
        'Asset Code Sequence',
        config_parameter='it_asset_management.code_sequence_id',
        domain=[('code', '=', 'it.asset.code')],
        help='Sequence used for generating asset codes'
    )

    # Assignment Settings
    assignment_auto_approve = fields.Boolean(
        'Auto-approve Assignments',
        config_parameter='it_asset_management.auto_approve_assignments',
        default=False,
        help='Automatically approve asset assignments without manual approval'
    )

    assignment_require_return_reason = fields.Boolean(
        'Require Return Reason',
        config_parameter='it_asset_management.require_return_reason',
        default=True,
        help='Require a reason when returning assigned assets'
    )

    assignment_notification_email = fields.Boolean(
        'Send Assignment Notifications',
        config_parameter='it_asset_management.assignment_notifications',
        default=True,
        help='Send email notifications for asset assignments and returns'
    )

    # Request Settings
    request_auto_create_asset = fields.Boolean(
        'Auto-create Assets from Requests',
        config_parameter='it_asset_management.auto_create_from_request',
        default=False,
        help='Automatically create asset records when fulfilling approved requests'
    )

    request_approval_required = fields.Boolean(
        'Request Approval Required',
        config_parameter='it_asset_management.request_approval_required',
        default=True,
        help='Require manager approval for asset requests'
    )

    request_notification_email = fields.Boolean(
        'Send Request Notifications',
        config_parameter='it_asset_management.request_notifications',
        default=True,
        help='Send email notifications for request status changes'
    )

    # Maintenance Settings
    maintenance_auto_schedule = fields.Boolean(
        'Auto-schedule Maintenance',
        config_parameter='it_asset_management.auto_schedule_maintenance',
        default=False,
        help='Automatically schedule maintenance based on asset lifecycle'
    )

    maintenance_reminder_days = fields.Integer(
        'Maintenance Reminder (Days)',
        config_parameter='it_asset_management.maintenance_reminder_days',
        default=30,
        help='Number of days before maintenance due date to send reminders'
    )

    maintenance_notification_email = fields.Boolean(
        'Send Maintenance Notifications',
        config_parameter='it_asset_management.maintenance_notifications',
        default=True,
        help='Send email notifications for maintenance schedules and reminders'
    )

    # Warranty Settings
    warranty_reminder_days = fields.Integer(
        'Warranty Expiry Reminder (Days)',
        config_parameter='it_asset_management.warranty_reminder_days',
        default=60,
        help='Number of days before warranty expires to send reminders'
    )

    warranty_notification_email = fields.Boolean(
        'Send Warranty Notifications',
        config_parameter='it_asset_management.warranty_notifications',
        default=True,
        help='Send email notifications for warranty expiry reminders'
    )

    # Portal Settings
    portal_asset_view = fields.Boolean(
        'Portal Asset View',
        config_parameter='it_asset_management.portal_asset_view',
        default=True,
        help='Allow users to view their assigned assets in portal'
    )

    portal_request_creation = fields.Boolean(
        'Portal Request Creation',
        config_parameter='it_asset_management.portal_request_creation',
        default=True,
        help='Allow users to create asset requests from portal'
    )

    portal_assignment_history = fields.Boolean(
        'Portal Assignment History',
        config_parameter='it_asset_management.portal_assignment_history',
        default=True,
        help='Show assignment history to users in portal'
    )

    # Security Settings
    asset_access_restriction = fields.Selection([
        ('none', 'No Restriction'),
        ('assigned_only', 'Assigned Assets Only'),
        ('department', 'Department Assets Only'),
    ], string='Asset Access Restriction',
        config_parameter='it_asset_management.access_restriction',
        default='assigned_only',
        help='Restrict which assets users can view based on their role'
    )

    # Dashboard Settings
    dashboard_refresh_interval = fields.Integer(
        'Dashboard Refresh Interval (minutes)',
        config_parameter='it_asset_management.dashboard_refresh_interval',
        default=5,
        help='How often to refresh dashboard data automatically'
    )

    dashboard_show_charts = fields.Boolean(
        'Show Dashboard Charts',
        config_parameter='it_asset_management.dashboard_show_charts',
        default=True,
        help='Display charts and graphs on the dashboard'
    )

    # Reporting Settings
    report_include_images = fields.Boolean(
        'Include Images in Reports',
        config_parameter='it_asset_management.report_include_images',
        default=False,
        help='Include asset images in printed reports'
    )

    report_barcode_format = fields.Selection([
        ('code128', 'Code 128'),
        ('qr', 'QR Code'),
        ('datamatrix', 'Data Matrix'),
    ], string='Asset Tag Barcode Format',
        config_parameter='it_asset_management.barcode_format',
        default='code128',
        help='Format for asset tag barcodes'
    )

    @api.model
    def get_values(self):
        res = super().get_values()

        # Create sequence if it doesn't exist
        sequence = self.env['ir.sequence'].search([('code', '=', 'it.asset.code')], limit=1)
        if not sequence:
            sequence = self.env['ir.sequence'].create({
                'name': 'IT Asset Code',
                'code': 'it.asset.code',
                'prefix': 'ASSET-',
                'padding': 5,
                'number_increment': 1,
                'implementation': 'standard',
            })

        res.update(asset_code_sequence=sequence.id)
        return res

    def set_values(self):
        super().set_values()

        # Additional processing if needed
        if self.asset_code_sequence:
            # Update sequence prefix if changed
            if self.asset_code_prefix:
                self.asset_code_sequence.prefix = self.asset_code_prefix

    @api.onchange('asset_code_prefix')
    def _onchange_asset_code_prefix(self):
        """Update sequence prefix when prefix changes"""
        if self.asset_code_sequence and self.asset_code_prefix:
            self.asset_code_sequence.prefix = self.asset_code_prefix