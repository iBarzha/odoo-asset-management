# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BarcodeGeneratorWizard(models.TransientModel):
    _name = 'it.asset.barcode.generator.wizard'
    _description = 'Barcode Generator Wizard'

    generation_type = fields.Selection([
        ('qr_code', 'QR Codes'),
        ('barcode', 'Barcodes'),
        ('both', 'Both QR Codes and Barcodes'),
    ], string='Generation Type', default='both', required=True)

    asset_ids = fields.Many2many(
        'it.asset',
        string='Assets',
        help="Leave empty to generate for all assets"
    )

    category_ids = fields.Many2many(
        'it.asset.category',
        string='Categories',
        help="Generate codes only for assets in these categories"
    )

    state_filter = fields.Selection([
        ('all', 'All States'),
        ('available', 'Available Only'),
        ('assigned', 'Assigned Only'),
    ], string='State Filter', default='all')

    overwrite_existing = fields.Boolean(
        'Overwrite Existing Codes',
        default=False,
        help="If checked, will regenerate codes even if they already exist"
    )

    auto_generate_barcode = fields.Boolean(
        'Auto-generate Barcode from Asset Code',
        default=True,
        help="Automatically set barcode field to asset code if barcode is empty"
    )

    @api.model
    def default_get(self, fields_list):
        """Set default assets if called from asset list view"""
        defaults = super().default_get(fields_list)

        # Get selected assets from context
        active_ids = self.env.context.get('active_ids', [])
        if active_ids and 'asset_ids' in fields_list:
            defaults['asset_ids'] = [(6, 0, active_ids)]

        return defaults

    def action_generate_codes(self):
        """Generate codes for selected assets"""
        assets = self._get_assets_to_process()

        if not assets:
            raise UserError(_('No assets found to process.'))

        success_count = 0
        error_count = 0
        errors = []

        for asset in assets:
            try:
                self._generate_codes_for_asset(asset)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"{asset.name}: {str(e)}")

        # Show results
        message = _('Code generation completed!\n\n')
        message += _('Successful: %d assets\n') % success_count

        if error_count > 0:
            message += _('Errors: %d assets\n\n') % error_count
            message += _('Errors:\n') + '\n'.join(errors[:5])
            if len(errors) > 5:
                message += f'\n... and {len(errors) - 5} more errors'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Code Generation Results'),
                'message': message,
                'type': 'success' if error_count == 0 else 'warning',
                'sticky': True,
            }
        }

    def _get_assets_to_process(self):
        """Get assets based on wizard configuration"""
        domain = []

        # If specific assets selected, use those
        if self.asset_ids:
            return self.asset_ids

        # Apply category filter
        if self.category_ids:
            domain.append(('category_id', 'in', self.category_ids.ids))

        # Apply state filter
        if self.state_filter != 'all':
            domain.append(('state', '=', self.state_filter))

        # Only active assets
        domain.append(('active', '=', True))

        return self.env['it.asset'].search(domain)

    def _generate_codes_for_asset(self, asset):
        """Generate codes for a single asset"""
        vals = {}

        # Generate barcode if needed
        if self.generation_type in ('barcode', 'both'):
            if not asset.barcode or self.overwrite_existing:
                if self.auto_generate_barcode:
                    vals['barcode'] = asset.code
                elif not asset.barcode:
                    vals['barcode'] = asset.code

        # Write changes and trigger computation
        if vals:
            asset.write(vals)

        # Force recomputation of codes
        if self.generation_type in ('qr_code', 'both'):
            if not asset.qr_code or self.overwrite_existing:
                asset._compute_qr_data()
                asset._compute_qr_code()

        if self.generation_type in ('barcode', 'both'):
            if not asset.barcode_image or self.overwrite_existing:
                asset._compute_barcode_image()

    def action_preview_selection(self):
        """Preview which assets would be affected"""
        assets = self._get_assets_to_process()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Assets to Process'),
            'res_model': 'it.asset',
            'view_mode': 'list,form',
            'domain': [('id', 'in', assets.ids)],
            'target': 'new',
            'context': {'create': False, 'edit': False, 'delete': False},
        }