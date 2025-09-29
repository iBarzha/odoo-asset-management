# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class ITAssetRequest(models.Model):
    _name = 'it.asset.request'
    _description = 'Asset Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # Basic Information
    name = fields.Char(
        'Request Number',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )
    user_id = fields.Many2one(
        'res.users',
        'Requested By',
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )
    request_type = fields.Selection([
        ('new_asset', 'New Asset Request'),
        ('repair', 'Repair Request'),
        ('replacement', 'Replacement Request'),
        ('return', 'Return Request'),
        ('upgrade', 'Upgrade Request'),
    ], required=True, tracking=True, string='Request Type')

    # Request Details
    asset_id = fields.Many2one(
        'it.asset',
        'Related Asset',
        help="Required for repair, replacement, and return requests"
    )
    category_id = fields.Many2one(
        'it.asset.category',
        'Asset Category',
        help="Category of asset for new asset requests"
    )
    description = fields.Html('Description', required=True)
    justification = fields.Html('Business Justification')

    # Priority and Urgency
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], default='medium', required=True, tracking=True)

    urgency = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium', string='Urgency Level')

    # Workflow State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True)

    # Dates
    request_date = fields.Datetime(
        'Request Date',
        default=fields.Datetime.now,
        required=True
    )
    required_date = fields.Date('Required By Date')
    approval_date = fields.Datetime('Approval Date', readonly=True)
    start_date = fields.Datetime('Start Date', readonly=True)
    completion_date = fields.Datetime('Completion Date', readonly=True)
    deadline = fields.Date('Deadline', compute='_compute_deadline', store=True)

    # Assignment and Approval
    approver_id = fields.Many2one('res.users', 'Approver', readonly=True)
    assigned_to_id = fields.Many2one(
        'res.users',
        'Assigned To',
        domain=[('groups_id', 'in', [lambda self: self.env.ref('it_asset_management.group_asset_user').id])]
    )
    department_id = fields.Many2one(
        'hr.department',
        'Department',
        related='user_id.department_id',
        store=True
    )

    # Approval and Progress Notes
    approval_notes = fields.Html('Approval Notes')
    rejection_reason = fields.Html('Rejection Reason')
    progress_notes = fields.Html('Progress Notes')
    completion_notes = fields.Html('Completion Notes')
    internal_notes = fields.Html('Internal Notes', groups='it_asset_management.group_asset_user')

    # Cost Information
    estimated_cost = fields.Float('Estimated Cost')
    actual_cost = fields.Float('Actual Cost')
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        default=lambda self: self.env.company.currency_id
    )

    # Request Specifications (for new asset requests)
    specifications = fields.Html('Technical Specifications')
    preferred_brand = fields.Char('Preferred Brand')
    preferred_model = fields.Char('Preferred Model')

    # Attachments and Images
    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'it.asset.request')],
        string='Attachments'
    )

    # Related Information
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    # Computed Fields
    days_open = fields.Integer('Days Open', compute='_compute_days_open')
    is_overdue = fields.Boolean('Is Overdue', compute='_compute_overdue', store=True)
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    can_edit = fields.Boolean('Can Edit', compute='_compute_can_edit')
    attachment_count = fields.Integer('Attachment Count', compute='_compute_attachment_count')

    # Portal fields
    access_url = fields.Char('Portal Access URL', compute='_compute_access_url')

    # SQL Constraints
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Request number must be unique!'),
        ('required_date_future', 'CHECK(required_date >= CURRENT_DATE OR required_date IS NULL)',
         'Required date must be today or in the future!'),
    ]

    @api.depends('priority', 'urgency', 'required_date')
    def _compute_deadline(self):
        for request in self:
            if request.required_date:
                request.deadline = request.required_date
            elif request.priority == 'urgent' or request.urgency == 'critical':
                request.deadline = fields.Date.today() + timedelta(days=1)
            elif request.priority == 'high' or request.urgency == 'high':
                request.deadline = fields.Date.today() + timedelta(days=3)
            elif request.priority == 'medium':
                request.deadline = fields.Date.today() + timedelta(days=7)
            else:
                request.deadline = fields.Date.today() + timedelta(days=14)


    @api.depends('request_date')
    def _compute_days_open(self):
        for request in self:
            if request.request_date:
                if request.completion_date:
                    delta = request.completion_date - request.request_date
                else:
                    delta = fields.Datetime.now() - request.request_date
                request.days_open = delta.days
            else:
                request.days_open = 0

    @api.depends('deadline', 'state')
    def _compute_overdue(self):
        today = fields.Date.today()
        for request in self:
            request.is_overdue = (
                request.deadline and
                request.deadline < today and
                request.state not in ['completed', 'cancelled', 'rejected']
            )

    @api.depends('state')
    def _compute_can_approve(self):
        is_manager = self.env.user.has_group('it_asset_management.group_asset_manager')
        for request in self:
            request.can_approve = (
                is_manager and
                request.state in ['submitted', 'under_review']
            )

    @api.depends('state', 'user_id')
    def _compute_can_edit(self):
        for request in self:
            request.can_edit = (
                request.state in ['draft'] and
                (request.user_id == self.env.user or
                 self.env.user.has_group('it_asset_management.group_asset_manager'))
            )

    def _compute_access_url(self):
        for request in self:
            request.access_url = f'/my/request/{request.id}'

    def _compute_attachment_count(self):
        for request in self:
            request.attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', self._name),
                ('res_id', '=', request.id)
            ])

    @api.constrains('asset_id', 'request_type')
    def _check_asset_requirement(self):
        for request in self:
            if request.request_type in ['repair', 'replacement', 'return'] and not request.asset_id:
                raise ValidationError(
                    _('Asset is required for %s requests') %
                    dict(request._fields['request_type'].selection)[request.request_type]
                )

    @api.constrains('required_date')
    def _check_required_date(self):
        for request in self:
            if request.required_date and request.required_date < fields.Date.today():
                raise ValidationError(_('Required date cannot be in the past!'))

    @api.constrains('category_id', 'request_type')
    def _check_category_requirement(self):
        for request in self:
            if request.request_type == 'new_asset' and not request.category_id:
                raise ValidationError(_('Asset category is required for new asset requests!'))

    @api.constrains('justification')
    def _check_justification_length(self):
        for request in self:
            if request.justification and len(request.justification.strip()) < 10:
                raise ValidationError(_('Justification must be at least 10 characters long!'))

    @api.constrains('state', 'rejection_reason')
    def _check_rejection_reason(self):
        for request in self:
            if request.state == 'rejected' and not request.rejection_reason:
                raise ValidationError(_('Rejection reason is required when rejecting a request!'))

    @api.constrains('approver_id', 'state')
    def _check_approver_authorization(self):
        for request in self:
            if request.state == 'approved' and request.approver_id:
                if not request.approver_id.has_group('it_asset_management.group_asset_manager'):
                    raise ValidationError(_('Only IT Asset Managers can approve requests!'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-generate sequence number
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('it.asset.request') or 'New'

            # Auto-submit if created via portal
            if self.env.context.get('portal_create'):
                vals['state'] = 'submitted'

        requests = super().create(vals_list)

        for request in requests:
            # Send notification to managers if submitted
            if request.state == 'submitted':
                request._notify_managers()

        return requests

    def write(self, vals):
        # Track state changes
        if 'state' in vals:
            for request in self:
                old_state = request.state
                new_state = vals['state']
                if old_state != new_state:
                    request._log_state_change(old_state, new_state)

        return super().write(vals)

    def action_submit(self):
        """Submit request for approval"""
        for request in self:
            if request.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))

            request.write({
                'state': 'submitted',
                'request_date': fields.Datetime.now()
            })
            request._notify_managers()

    def action_review(self):
        """Move request to under review"""
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError(_('Only submitted requests can be moved to review.'))

        self.state = 'under_review'

    def action_approve(self):
        """Approve the request"""
        self.ensure_one()
        if not self.can_approve:
            raise UserError(_('You do not have permission to approve this request.'))

        self.write({
            'state': 'approved',
            'approval_date': fields.Datetime.now(),
            'approver_id': self.env.user.id,
        })

        # Auto-assign to IT team if not assigned
        if not self.assigned_to_id:
            self._auto_assign()

        # Notify requester and assigned person
        self._notify_approval()

    def action_reject(self):
        """Reject the request"""
        self.ensure_one()
        if not self.can_approve:
            raise UserError(_('You do not have permission to reject this request.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Request'),
            'res_model': 'it.asset.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def action_start_work(self):
        """Start working on the request"""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved requests can be started.'))

        self.write({
            'state': 'in_progress',
            'start_date': fields.Datetime.now(),
            'assigned_to_id': self.assigned_to_id.id or self.env.user.id,
        })

    def action_complete(self):
        """Complete the request"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Only in-progress requests can be completed.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Complete Request'),
            'res_model': 'it.asset.request.complete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id}
        }

    def action_cancel(self):
        """Cancel the request"""
        for request in self:
            if request.state in ['completed']:
                raise UserError(_('Completed requests cannot be cancelled.'))

            request.state = 'cancelled'

    def action_reset_to_draft(self):
        """Reset request to draft"""
        for request in self:
            if request.state not in ['submitted', 'rejected']:
                raise UserError(_('Only submitted or rejected requests can be reset to draft.'))

            request.state = 'draft'

    def action_view_asset(self):
        """View related asset"""
        self.ensure_one()
        if not self.asset_id:
            raise UserError(_('No asset is associated with this request.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset Details'),
            'res_model': 'it.asset',
            'res_id': self.asset_id.id,
            'view_mode': 'form',
        }

    def action_get_attachment_tree_view(self):
        """View attachments for this request"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attachments'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }

    def _notify_managers(self):
        """Notify asset managers about new request"""
        managers = self.env['res.users'].search([
            ('groups_id', 'in', [self.env.ref('it_asset_management.group_asset_manager').id])
        ])

        for manager in managers:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('New Asset Request: %s') % self.name,
                note=_('Review request from %s for %s') % (
                    self.user_id.name,
                    dict(self._fields['request_type'].selection)[self.request_type]
                ),
                user_id=manager.id,
                date_deadline=fields.Date.today() + timedelta(days=1)
            )

    def _notify_approval(self):
        """Notify requester and assigned person about approval"""
        # Notify requester
        self.message_post(
            body=_('Your request has been approved by %s') % self.approver_id.name,
            partner_ids=[self.user_id.partner_id.id]
        )

        # Notify assigned person
        if self.assigned_to_id and self.assigned_to_id != self.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Approved Request Assigned: %s') % self.name,
                note=_('Please start working on this approved request'),
                user_id=self.assigned_to_id.id,
                date_deadline=self.deadline or fields.Date.today() + timedelta(days=3)
            )

    def _auto_assign(self):
        """Auto-assign request to available IT staff"""
        # Find available IT users (you can customize this logic)
        it_users = self.env['res.users'].search([
            ('groups_id', 'in', [self.env.ref('it_asset_management.group_asset_user').id]),
            ('active', '=', True)
        ])

        if it_users:
            # Simple round-robin assignment (you can implement more sophisticated logic)
            assigned_user = it_users[self.id % len(it_users)]
            self.assigned_to_id = assigned_user

    def _log_state_change(self, old_state, new_state):
        """Log state changes in chatter"""
        old_state_label = dict(self._fields['state'].selection)[old_state]
        new_state_label = dict(self._fields['state'].selection)[new_state]

        self.message_post(
            body=_('Request status changed from %s to %s') % (old_state_label, new_state_label)
        )

    @api.model
    def _get_overdue_requests(self):
        """Get all overdue requests"""
        today = fields.Date.today()
        return self.search([
            ('deadline', '<', today),
            ('state', 'not in', ['completed', 'cancelled', 'rejected'])
        ])

    def _get_portal_return_action(self):
        """Return action for portal"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/requests',
            'target': 'self',
        }

    def name_get(self):
        result = []
        for request in self:
            name = request.name
            if request.request_type:
                type_label = dict(request._fields['request_type'].selection)[request.request_type]
                name += f" - {type_label}"
            result.append((request.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            # Search in name and description
            request_ids = self._search([
                '|',
                ('name', operator, name),
                ('description', operator, name)
            ] + args, limit=limit, access_rights_uid=name_get_uid)
        else:
            request_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return request_ids