# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class ITAssetAssignment(models.Model):
    _name = 'it.asset.assignment'
    _description = 'Asset Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'assignment_date desc'
    _rec_name = 'display_name'

    # Core assignment fields
    asset_id = fields.Many2one(
        'it.asset',
        'Asset',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    user_id = fields.Many2one(
        'res.users',
        'Assigned To',
        required=True,
        tracking=True
    )
    assigned_by_id = fields.Many2one(
        'res.users',
        'Assigned By',
        default=lambda self: self.env.user,
        required=True
    )

    # Date fields
    assignment_date = fields.Datetime(
        'Assignment Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    expected_return_date = fields.Date('Expected Return Date')
    return_date = fields.Datetime('Return Date', tracking=True)

    # Status
    is_active = fields.Boolean('Active Assignment', default=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
    ], default='active', required=True, tracking=True)

    # Assignment details
    assignment_reason = fields.Text('Assignment Reason')
    assignment_notes = fields.Text('Assignment Notes')
    location = fields.Char('Assignment Location')

    # Return details
    return_reason = fields.Text('Return Reason')
    return_notes = fields.Text('Return Notes')
    returned_by_id = fields.Many2one('res.users', 'Returned By')

    # Condition tracking
    condition_on_assignment = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], 'Condition on Assignment', default='good')

    condition_on_return = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], 'Condition on Return')

    # Related fields for easier access
    asset_name = fields.Char(related='asset_id.name', string='Asset Name', readonly=True)
    asset_code = fields.Char(related='asset_id.code', string='Asset Code', readonly=True)
    asset_category = fields.Char(related='asset_id.category_id.name', string='Category', readonly=True)
    user_name = fields.Char(related='user_id.name', string='User Name', readonly=True)
    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True)

    # Computed fields
    display_name = fields.Char('Display Name', compute='_compute_display_name')
    duration_days = fields.Integer('Duration (Days)', compute='_compute_duration')
    is_overdue = fields.Boolean('Is Overdue', compute='_compute_overdue', store=True)

    # SQL Constraints
    _sql_constraints = [
        ('assignment_dates_check', 'CHECK(assignment_date <= return_date OR return_date IS NULL)',
         'Assignment date must be before or equal to return date!'),
        ('expected_return_after_assignment', 'CHECK(expected_return_date >= DATE(assignment_date) OR expected_return_date IS NULL)',
         'Expected return date must be after assignment date!'),
    ]

    @api.depends('asset_id', 'user_id')
    def _compute_display_name(self):
        for assignment in self:
            if assignment.asset_id and assignment.user_id:
                assignment.display_name = f"{assignment.asset_id.name} → {assignment.user_id.name}"
            else:
                assignment.display_name = _('Asset Assignment')

    @api.depends('assignment_date', 'return_date')
    def _compute_duration(self):
        for assignment in self:
            if assignment.assignment_date:
                end_date = assignment.return_date or fields.Datetime.now()
                delta = end_date - assignment.assignment_date
                assignment.duration_days = delta.days
            else:
                assignment.duration_days = 0

    @api.depends('expected_return_date', 'return_date', 'is_active')
    def _compute_overdue(self):
        today = fields.Date.today()
        for assignment in self:
            assignment.is_overdue = (
                assignment.is_active and
                assignment.expected_return_date and
                assignment.expected_return_date < today
            )

    @api.constrains('assignment_date', 'return_date')
    def _check_dates(self):
        for assignment in self:
            if assignment.return_date and assignment.assignment_date:
                if assignment.return_date < assignment.assignment_date:
                    raise ValidationError(_('Return date cannot be before assignment date!'))

    @api.constrains('asset_id', 'is_active')
    def _check_unique_active_assignment(self):
        for assignment in self:
            if assignment.is_active:
                existing = self.search([
                    ('asset_id', '=', assignment.asset_id.id),
                    ('is_active', '=', True),
                    ('id', '!=', assignment.id)
                ])
                if existing:
                    raise ValidationError(
                        _('Asset "%s" is already assigned to "%s"!') %
                        (assignment.asset_id.name, existing[0].user_id.name)
                    )

    @api.constrains('expected_return_date', 'assignment_date')
    def _check_expected_return_date(self):
        for assignment in self:
            if assignment.expected_return_date and assignment.assignment_date:
                assignment_date = assignment.assignment_date.date() if isinstance(assignment.assignment_date, datetime) else assignment.assignment_date
                if assignment.expected_return_date < assignment_date:
                    raise ValidationError(_('Expected return date cannot be before assignment date!'))

    @api.constrains('asset_id', 'user_id')
    def _check_asset_availability(self):
        for assignment in self:
            if assignment.is_active and assignment.asset_id.state not in ['available', 'assigned']:
                raise ValidationError(_('Asset "%s" is not available for assignment (current state: %s)!') %
                                    (assignment.asset_id.name, assignment.asset_id.state))

    @api.constrains('user_id')
    def _check_user_active(self):
        for assignment in self:
            if not assignment.user_id.active:
                raise ValidationError(_('Cannot assign asset to inactive user "%s"!') % assignment.user_id.name)

    @api.model_create_multi
    def create(self, vals_list):
        assignments = super().create(vals_list)

        for assignment in assignments:
            # Update asset's current assignment and state
            if assignment.is_active:
                assignment.asset_id.write({
                    'current_assignment_id': assignment.id,
                    'state': 'assigned'
                })

            # Send notification email
            assignment._send_assignment_notification()

            # Log assignment activity
            assignment.message_post(
                body=_('Asset "%s" assigned to "%s"') % (
                    assignment.asset_id.name,
                    assignment.user_id.name
                )
            )

        return assignments

    def write(self, vals):
        # Handle state changes
        if 'is_active' in vals or 'state' in vals:
            for assignment in self:
                old_active = assignment.is_active
                old_state = assignment.state

        result = super().write(vals)

        # Update asset after write
        for assignment in self:
            if 'is_active' in vals:
                if not assignment.is_active and assignment.asset_id.current_assignment_id == assignment:
                    assignment.asset_id.write({
                        'current_assignment_id': False,
                        'state': 'available'
                    })
                elif assignment.is_active:
                    assignment.asset_id.write({
                        'current_assignment_id': assignment.id,
                        'state': 'assigned'
                    })

        return result

    def action_return_asset(self):
        """Return the asset"""
        self.ensure_one()
        if not self.is_active:
            raise UserError(_('This assignment is already inactive.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Asset'),
            'res_model': 'it.asset.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_assignment_id': self.id,
                'default_return_date': fields.Datetime.now(),
            }
        }

    def action_mark_lost(self):
        """Mark asset as lost"""
        self.ensure_one()
        self.write({
            'state': 'lost',
            'is_active': False,
            'return_date': fields.Datetime.now(),
            'returned_by_id': self.env.user.id,
        })
        self.asset_id.state = 'disposed'

        self.message_post(body=_('Asset marked as lost'))

    def action_mark_damaged(self):
        """Mark asset as damaged"""
        self.ensure_one()
        self.write({
            'state': 'damaged',
            'is_active': False,
            'return_date': fields.Datetime.now(),
            'returned_by_id': self.env.user.id,
        })
        self.asset_id.state = 'repair'

        self.message_post(body=_('Asset marked as damaged'))

    def action_view_asset(self):
        """View the assigned asset"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset Details'),
            'res_model': 'it.asset',
            'res_id': self.asset_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_user(self):
        """View the assigned user"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('User Details'),
            'res_model': 'res.users',
            'res_id': self.user_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _send_assignment_notification(self):
        """Send email notification to assigned user"""
        if not self.user_id.email:
            return

        template = self.env.ref('it_asset_management.email_template_asset_assignment', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_return_notification(self):
        """Send email notification when asset is returned"""
        template = self.env.ref('it_asset_management.email_template_asset_return', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    @api.model
    def _get_overdue_assignments(self):
        """Get all overdue assignments"""
        today = fields.Date.today()
        return self.search([
            ('is_active', '=', True),
            ('expected_return_date', '<', today)
        ])

    @api.model
    def _cron_check_overdue_assignments(self):
        """Cron job to check and notify about overdue assignments"""
        overdue_assignments = self._get_overdue_assignments()

        for assignment in overdue_assignments:
            # Create activity for the assigned user
            assignment.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Overdue Asset Return'),
                note=_('Asset "%s" was expected to be returned on %s') % (
                    assignment.asset_id.name,
                    assignment.expected_return_date
                ),
                user_id=assignment.user_id.id,
                date_deadline=fields.Date.today()
            )

            # Notify asset manager
            if assignment.asset_id.responsible_user_id:
                assignment.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Overdue Asset Assignment'),
                    note=_('Asset "%s" assigned to "%s" is overdue for return') % (
                        assignment.asset_id.name,
                        assignment.user_id.name
                    ),
                    user_id=assignment.asset_id.responsible_user_id.id,
                    date_deadline=fields.Date.today()
                )

    def name_get(self):
        result = []
        for assignment in self:
            name = f"{assignment.asset_id.name} → {assignment.user_id.name}"
            if assignment.assignment_date:
                name += f" ({assignment.assignment_date.strftime('%Y-%m-%d')})"
            result.append((assignment.id, name))
        return result