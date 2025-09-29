# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import xlrd
import io
import csv
from datetime import datetime


class AssetRequestRejectWizard(models.TransientModel):
    """Wizard for rejecting asset requests"""
    _name = 'it.asset.request.reject.wizard'
    _description = 'Reject Asset Request'

    request_id = fields.Many2one('it.asset.request', string='Request', required=True)
    rejection_reason = fields.Html('Rejection Reason', required=True)
    notify_requester = fields.Boolean('Notify Requester', default=True)

    def action_reject(self):
        """Reject the request with reason"""
        self.ensure_one()

        if not self.rejection_reason:
            raise ValidationError(_('Please provide a rejection reason.'))

        self.request_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })

        if self.notify_requester:
            self.request_id.message_post(
                body=_('Your request has been rejected.<br/>Reason: %s') % self.rejection_reason,
                partner_ids=[self.request_id.user_id.partner_id.id],
                subtype_xmlid='mail.mt_comment'
            )

        return {'type': 'ir.actions.act_window_close'}


class AssetRequestCompleteWizard(models.TransientModel):
    """Wizard for completing asset requests"""
    _name = 'it.asset.request.complete.wizard'
    _description = 'Complete Asset Request'

    request_id = fields.Many2one('it.asset.request', string='Request', required=True)
    completion_notes = fields.Html('Completion Notes', required=True)
    actual_cost = fields.Float('Actual Cost')
    delivered_asset_id = fields.Many2one('it.asset', string='Delivered Asset')
    notify_requester = fields.Boolean('Notify Requester', default=True)

    @api.onchange('request_id')
    def _onchange_request_id(self):
        if self.request_id:
            self.actual_cost = self.request_id.actual_cost or self.request_id.estimated_cost

    def action_complete(self):
        """Complete the request"""
        self.ensure_one()

        if not self.completion_notes:
            raise ValidationError(_('Please provide completion notes.'))

        vals = {
            'state': 'completed',
            'completion_date': fields.Datetime.now(),
            'completion_notes': self.completion_notes,
        }

        if self.actual_cost:
            vals['actual_cost'] = self.actual_cost

        if self.delivered_asset_id:
            vals['asset_id'] = self.delivered_asset_id.id

        self.request_id.write(vals)

        if self.notify_requester:
            message = _('Your request has been completed.<br/>Notes: %s') % self.completion_notes
            if self.delivered_asset_id:
                message += _('<br/>Delivered Asset: %s') % self.delivered_asset_id.name

            self.request_id.message_post(
                body=message,
                partner_ids=[self.request_id.user_id.partner_id.id],
                subtype_xmlid='mail.mt_comment'
            )

        return {'type': 'ir.actions.act_window_close'}