# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import io
import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

try:
    from reportlab.graphics.barcode import code128
    from reportlab.graphics import renderPM
    from reportlab.lib.units import mm
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False


class ITAsset(models.Model):
    _name = 'it.asset'
    _description = 'IT Asset'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin'
    ]
    _order = 'name'
    _rec_name = 'name'

    # Basic Information
    active = fields.Boolean('Active', default=True, tracking=True)
    name = fields.Char('Asset Name', required=True, tracking=True)
    code = fields.Char(
        'Asset Code',
        required=True,
        copy=False,
        tracking=True,
        help="Unique identifier for the asset"
    )
    category_id = fields.Many2one(
        'it.asset.category',
        'Category',
        required=True,
        tracking=True,
        ondelete='restrict'
    )

    # Status and Lifecycle
    state = fields.Selection([
        ('draft', 'Draft'),
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('maintenance', 'Under Maintenance'),
        ('repair', 'Under Repair'),
        ('disposed', 'Disposed'),
    ], default='draft', required=True, tracking=True, string='Status')

    # Technical Specifications
    brand = fields.Char('Brand', tracking=True)
    model = fields.Char('Model', tracking=True)
    serial_number = fields.Char('Serial Number', tracking=True, copy=False)
    asset_tag = fields.Char('Asset Tag', copy=False)
    specifications = fields.Html('Technical Specifications')

    # Additional technical fields
    operating_system = fields.Char('Operating System')
    processor = fields.Char('Processor')
    memory_ram = fields.Char('RAM Memory')
    storage = fields.Char('Storage')
    network_name = fields.Char('Network Name/Hostname')
    ip_address = fields.Char('IP Address')

    # Purchase Information
    purchase_date = fields.Date('Purchase Date', tracking=True)
    purchase_price = fields.Float('Purchase Price', tracking=True)
    currency_id = fields.Many2one(
        'res.currency',
        'Currency',
        default=lambda self: self.env.company.currency_id
    )
    supplier_id = fields.Many2one('res.partner', 'Supplier', domain=[('is_company', '=', True)])
    invoice_reference = fields.Char('Invoice Reference')

    # Warranty Information
    warranty_start = fields.Date('Warranty Start Date')
    warranty_end = fields.Date('Warranty End Date')
    warranty_type = fields.Selection([
        ('manufacturer', 'Manufacturer Warranty'),
        ('extended', 'Extended Warranty'),
        ('none', 'No Warranty'),
    ], default='manufacturer')
    warranty_description = fields.Text('Warranty Description')

    # Assignment Information
    current_assignment_id = fields.Many2one(
        'it.asset.assignment',
        'Current Assignment',
        copy=False
    )
    assigned_user_id = fields.Many2one(
        'res.users',
        'Assigned To',
        related='current_assignment_id.user_id',
        store=True,
        readonly=True
    )
    assignment_ids = fields.One2many(
        'it.asset.assignment',
        'asset_id',
        'Assignment History',
        copy=False
    )
    assignment_count = fields.Integer(
        'Assignment Count',
        compute='_compute_assignment_count'
    )

    # Location and Management
    location = fields.Char('Physical Location', tracking=True)
    department_id = fields.Many2one('hr.department', 'Department')
    responsible_user_id = fields.Many2one(
        'res.users',
        'Responsible Person',
        help="Person responsible for this asset management"
    )

    # Maintenance Information
    last_maintenance_date = fields.Date('Last Maintenance Date')
    next_maintenance_date = fields.Date('Next Maintenance Date')
    maintenance_notes = fields.Text('Maintenance Notes')

    # QR Code and Barcode Information
    qr_code = fields.Image('QR Code', max_width=256, max_height=256, compute='_compute_qr_code', store=True)
    barcode = fields.Char('Barcode', copy=False, help="Barcode for the asset")
    barcode_image = fields.Image('Barcode Image', max_width=400, max_height=100, compute='_compute_barcode_image', store=True)
    qr_data = fields.Char('QR Code Data', compute='_compute_qr_data', store=True, help="Data encoded in QR code")

    # Additional Information
    notes = fields.Html('Additional Notes')
    image = fields.Image('Asset Image', max_width=1024, max_height=1024)

    # Computed fields
    age_days = fields.Integer('Age (Days)', compute='_compute_age')
    warranty_status = fields.Selection([
        ('valid', 'Under Warranty'),
        ('expired', 'Warranty Expired'),
        ('expiring', 'Expiring Soon'),
        ('none', 'No Warranty'),
    ], compute='_compute_warranty_status', store=True)

    # Request related
    request_ids = fields.One2many('it.asset.request', 'asset_id', 'Related Requests')
    request_count = fields.Integer('Request Count', compute='_compute_request_count')

    # SQL Constraints
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Asset code must be unique!'),
        ('serial_number_unique', 'UNIQUE(serial_number)', 'Serial number must be unique when specified!'),
        ('asset_tag_unique', 'UNIQUE(asset_tag)', 'Asset tag must be unique when specified!'),
        ('purchase_price_positive', 'CHECK(purchase_price >= 0)', 'Purchase price must be positive!'),
        ('warranty_dates_check', 'CHECK(warranty_start <= warranty_end)', 'Warranty start date must be before or equal to end date!'),
        ('name_not_empty', 'CHECK(LENGTH(TRIM(name)) >= 3)', 'Asset name must be at least 3 characters long!'),
    ]

    @api.depends('assignment_ids')
    def _compute_assignment_count(self):
        for asset in self:
            asset.assignment_count = len(asset.assignment_ids)

    @api.depends('request_ids')
    def _compute_request_count(self):
        for asset in self:
            asset.request_count = len(asset.request_ids)

    @api.depends('purchase_date')
    def _compute_age(self):
        for asset in self:
            if asset.purchase_date:
                delta = fields.Date.today() - asset.purchase_date
                asset.age_days = delta.days
            else:
                asset.age_days = 0

    @api.depends('warranty_end', 'warranty_type')
    def _compute_warranty_status(self):
        today = fields.Date.today()
        for asset in self:
            if asset.warranty_type == 'none' or not asset.warranty_end:
                asset.warranty_status = 'none'
            elif asset.warranty_end < today:
                asset.warranty_status = 'expired'
            elif asset.warranty_end <= today + timedelta(days=30):
                asset.warranty_status = 'expiring'
            else:
                asset.warranty_status = 'valid'

    @api.depends('code', 'name', 'category_id', 'serial_number')
    def _compute_qr_data(self):
        """Compute QR code data containing asset information"""
        for asset in self:
            if asset.code:
                qr_data = {
                    'asset_code': asset.code,
                    'asset_name': asset.name,
                    'category': asset.category_id.name if asset.category_id else '',
                    'serial_number': asset.serial_number or '',
                    'url': f'/my/asset/scan/{asset.code}' if asset.code else '',
                    'id': asset.id
                }
                asset.qr_data = json.dumps(qr_data)
            else:
                asset.qr_data = ''

    @api.depends('qr_data')
    def _compute_qr_code(self):
        """Generate QR code image"""
        for asset in self:
            if asset.qr_data and QRCODE_AVAILABLE:
                try:
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=4,
                        border=4,
                    )
                    qr.add_data(asset.qr_data)
                    qr.make(fit=True)

                    img = qr.make_image(fill_color="black", back_color="white")
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    buffer.seek(0)

                    asset.qr_code = base64.b64encode(buffer.read())
                except Exception as e:
                    asset.qr_code = False
            else:
                asset.qr_code = False

    @api.depends('barcode')
    def _compute_barcode_image(self):
        """Generate barcode image"""
        for asset in self:
            if asset.barcode and BARCODE_AVAILABLE:
                try:
                    # Generate barcode using Code128
                    barcode_obj = code128.Code128(asset.barcode, humanReadable=True)

                    # Create image
                    drawing_width = barcode_obj.width
                    drawing_height = barcode_obj.height

                    from reportlab.graphics.shapes import Drawing
                    drawing = Drawing(drawing_width, drawing_height)
                    drawing.add(barcode_obj)

                    # Render to PNG
                    buffer = io.BytesIO()
                    renderPM.drawToFile(drawing, buffer, fmt='PNG')
                    buffer.seek(0)

                    asset.barcode_image = base64.b64encode(buffer.read())
                except Exception as e:
                    asset.barcode_image = False
            else:
                asset.barcode_image = False

    @api.constrains('serial_number')
    def _check_serial_number_unique(self):
        for asset in self:
            if asset.serial_number:
                existing = self.search([
                    ('serial_number', '=', asset.serial_number),
                    ('id', '!=', asset.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise ValidationError(
                        _('Serial number "%s" already exists for asset "%s"!') %
                        (asset.serial_number, existing[0].name)
                    )

    @api.constrains('code')
    def _check_code_unique(self):
        for asset in self:
            if asset.code:
                existing = self.search([
                    ('code', '=', asset.code),
                    ('id', '!=', asset.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise ValidationError(
                        _('Asset code "%s" already exists for asset "%s"!') %
                        (asset.code, existing[0].name)
                    )

    @api.constrains('warranty_start', 'warranty_end')
    def _check_warranty_dates(self):
        for asset in self:
            if asset.warranty_start and asset.warranty_end:
                if asset.warranty_start > asset.warranty_end:
                    raise ValidationError(_('Warranty start date must be before end date!'))

    @api.constrains('purchase_date', 'warranty_start')
    def _check_purchase_warranty_dates(self):
        for asset in self:
            if asset.purchase_date and asset.warranty_start:
                if asset.warranty_start < asset.purchase_date:
                    raise ValidationError(_('Warranty start date cannot be before purchase date!'))

    @api.constrains('purchase_price')
    def _check_purchase_price(self):
        for asset in self:
            if asset.purchase_price and asset.purchase_price < 0:
                raise ValidationError(_('Purchase price cannot be negative!'))

    @api.constrains('ip_address')
    def _check_ip_address_format(self):
        import re
        ip_pattern = re.compile(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$')

        for asset in self:
            if asset.ip_address and not ip_pattern.match(asset.ip_address):
                raise ValidationError(_('Invalid IP address format! Please use format: 192.168.1.1'))

    @api.constrains('asset_tag')
    def _check_asset_tag_unique(self):
        for asset in self:
            if asset.asset_tag:
                existing = self.search([
                    ('asset_tag', '=', asset.asset_tag),
                    ('id', '!=', asset.id),
                    ('active', '=', True)
                ])
                if existing:
                    raise ValidationError(_('Asset tag "%s" already exists for asset "%s"!') % (asset.asset_tag, existing[0].name))

    @api.constrains('name')
    def _check_name_length(self):
        for asset in self:
            if asset.name and len(asset.name.strip()) < 3:
                raise ValidationError(_('Asset name must be at least 3 characters long!'))

    @api.constrains('state', 'assigned_user_id')
    def _check_assignment_state_consistency(self):
        for asset in self:
            if asset.state == 'assigned' and not asset.assigned_user_id:
                raise ValidationError(_('An asset in "Assigned" state must have an assigned user!'))
            if asset.state != 'assigned' and asset.assigned_user_id:
                # Auto-fix: clear assignment if state is not assigned
                asset.write({'assigned_user_id': False})

    @api.model_create_multi
    def create(self, vals_list):
        # Auto-generate code if not provided
        for vals in vals_list:
            if not vals.get('code'):
                category = self.env['it.asset.category'].browse(vals.get('category_id'))
                sequence = self.env['ir.sequence'].next_by_code('it.asset') or '001'
                if category:
                    vals['code'] = f"{category.code}-{sequence}"
                else:
                    vals['code'] = f"AST-{sequence}"

        assets = super().create(vals_list)

        # Log creation activity for each asset
        for asset in assets:
            asset.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Asset created: %s') % asset.name,
                note=_('New asset has been added to the system.'),
                user_id=self.env.user.id,
            )

        return assets

    def write(self, vals):
        # Track state changes
        if 'state' in vals:
            for asset in self:
                old_state = asset.state
                new_state = vals['state']
                if old_state != new_state:
                    asset.message_post(
                        body=_('Asset status changed from %s to %s') % (
                            dict(asset._fields['state'].selection)[old_state],
                            dict(asset._fields['state'].selection)[new_state]
                        )
                    )

        return super().write(vals)

    def action_set_available(self):
        """Set asset status to available"""
        if self.current_assignment_id:
            raise UserError(_('Cannot set asset as available while it is assigned to a user.'))
        self.state = 'available'

    def action_set_maintenance(self):
        """Set asset status to maintenance"""
        self.state = 'maintenance'
        self.last_maintenance_date = fields.Date.today()

    def action_set_repair(self):
        """Set asset status to repair"""
        self.state = 'repair'

    def action_dispose(self):
        """Dispose asset"""
        if self.current_assignment_id:
            raise UserError(_('Cannot dispose asset while it is assigned to a user.'))
        self.state = 'disposed'
        self.active = False

    def action_assign_to_user(self):
        """Open wizard to assign asset to user"""
        self.ensure_one()
        if self.state not in ['available']:
            raise UserError(_('Only available assets can be assigned to users.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Asset'),
            'res_model': 'it.asset.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_assignment_date': fields.Datetime.now(),
            }
        }

    def action_view_assignments(self):
        """View asset assignments"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset Assignments'),
            'res_model': 'it.asset.assignment',
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_view_requests(self):
        """View related requests"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Requests'),
            'res_model': 'it.asset.request',
            'view_mode': 'list,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_create_maintenance_request(self):
        """Create maintenance request for this asset"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Maintenance Request'),
            'res_model': 'it.asset.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_request_type': 'repair',
                'default_category_id': self.category_id.id,
                'default_description': _('Maintenance required for %s') % self.name,
            }
        }

    def action_generate_qr_code(self):
        """Manually regenerate QR code"""
        self.ensure_one()
        if not QRCODE_AVAILABLE:
            raise UserError(_('QR code library is not installed. Please install qrcode library.'))

        # Force recomputation
        self._compute_qr_data()
        self._compute_qr_code()

        if self.qr_code:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('QR code generated successfully!'),
                    'type': 'success',
                }
            }
        else:
            raise UserError(_('Failed to generate QR code. Please check asset data.'))

    def action_generate_barcode(self):
        """Generate barcode for asset"""
        self.ensure_one()
        if not BARCODE_AVAILABLE:
            raise UserError(_('Barcode library is not installed. Please install reportlab library.'))

        if not self.barcode:
            # Auto-generate barcode from asset code
            self.barcode = self.code

        # Force recomputation
        self._compute_barcode_image()

        if self.barcode_image:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Barcode generated successfully!'),
                    'type': 'success',
                }
            }
        else:
            raise UserError(_('Failed to generate barcode. Please check barcode data.'))

    def action_print_qr_code(self):
        """Print QR code"""
        self.ensure_one()
        return self.env.ref('it_asset_management.action_report_asset_qr_code').report_action(self)

    def action_print_barcode(self):
        """Print barcode"""
        self.ensure_one()
        return self.env.ref('it_asset_management.action_report_asset_barcode').report_action(self)

    def action_print_asset_label(self):
        """Print asset label with both QR code and barcode"""
        self.ensure_one()
        return self.env.ref('it_asset_management.action_report_asset_label').report_action(self)

    @api.model
    def search_by_qr_code(self, qr_data):
        """Search asset by QR code data"""
        try:
            data = json.loads(qr_data)
            asset_code = data.get('asset_code')
            if asset_code:
                return self.search([('code', '=', asset_code)], limit=1)
        except (json.JSONDecodeError, TypeError):
            pass
        return self.browse()

    @api.model
    def search_by_barcode(self, barcode):
        """Search asset by barcode"""
        return self.search([('barcode', '=', barcode)], limit=1)

    @api.model
    def _get_warranty_expiring_assets(self, days=30):
        """Get assets with warranty expiring in specified days"""
        expiry_date = fields.Date.today() + timedelta(days=days)
        return self.search([
            ('warranty_end', '<=', expiry_date),
            ('warranty_end', '>=', fields.Date.today()),
            ('warranty_status', 'in', ['valid', 'expiring']),
            ('active', '=', True)
        ])

    def name_get(self):
        result = []
        for asset in self:
            name = f"[{asset.code}] {asset.name}"
            if asset.brand and asset.model:
                name += f" ({asset.brand} {asset.model})"
            result.append((asset.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            # Search in name, code, serial_number, and brand fields
            asset_ids = self._search([
                '|', '|', '|',
                ('name', operator, name),
                ('code', operator, name),
                ('serial_number', operator, name),
                ('brand', operator, name)
            ] + args, limit=limit, access_rights_uid=name_get_uid)
        else:
            asset_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        return asset_ids