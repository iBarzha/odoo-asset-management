# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import csv
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AssetImportWizard(models.TransientModel):
    _name = 'it.asset.import.wizard'
    _description = 'Asset Import Wizard'

    file_data = fields.Binary('CSV File', required=True)
    file_name = fields.Char('File Name')

    import_type = fields.Selection([
        ('create_only', 'Create New Assets Only'),
        ('update_existing', 'Update Existing Assets'),
        ('create_update', 'Create New and Update Existing'),
    ], string='Import Type', default='create_only', required=True)

    has_header = fields.Boolean('Has Header Row', default=True)
    delimiter = fields.Selection([
        (',', 'Comma (,)'),
        (';', 'Semicolon (;)'),
        ('\t', 'Tab'),
        ('|', 'Pipe (|)'),
    ], string='CSV Delimiter', default=',', required=True)

    preview_data = fields.Text('Preview', readonly=True)
    import_results = fields.Text('Import Results', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('preview', 'Preview'),
        ('done', 'Done'),
    ], default='draft')

    @api.onchange('file_data', 'delimiter', 'has_header')
    def _onchange_file_data(self):
        if self.file_data:
            self._generate_preview()

    def _generate_preview(self):
        if not self.file_data:
            return

        try:
            file_content = base64.b64decode(self.file_data).decode('utf-8')
            csv_reader = csv.reader(io.StringIO(file_content), delimiter=self.delimiter)

            preview_lines = []
            for i, row in enumerate(csv_reader):
                if i >= 10:  # Show only first 10 rows in preview
                    break
                preview_lines.append(' | '.join(row))

            self.preview_data = '\n'.join(preview_lines)

        except Exception as e:
            self.preview_data = f"Error reading file: {str(e)}"

    def action_preview(self):
        self._generate_preview()
        self.state = 'preview'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset Import Preview'),
            'res_model': 'it.asset.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_import(self):
        if not self.file_data:
            raise UserError(_('Please select a file to import.'))

        try:
            file_content = base64.b64decode(self.file_data).decode('utf-8')
            csv_reader = csv.reader(io.StringIO(file_content), delimiter=self.delimiter)

            rows = list(csv_reader)
            if not rows:
                raise UserError(_('The file is empty.'))

            # Extract header row if exists
            if self.has_header:
                header_row = rows[0]
                data_rows = rows[1:]
            else:
                header_row = None
                data_rows = rows

            results = self._process_import_data(data_rows, header_row)

            self.import_results = results
            self.state = 'done'

            return {
                'type': 'ir.actions.act_window',
                'name': _('Import Results'),
                'res_model': 'it.asset.import.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        except Exception as e:
            raise UserError(_('Import failed: %s') % str(e))

    def _process_import_data(self, data_rows, header_row):
        """Process the CSV data and import assets"""
        asset_model = self.env['it.asset']
        category_model = self.env['it.asset.category']

        created_count = 0
        updated_count = 0
        error_count = 0
        errors = []

        # Expected column mapping (can be customized)
        column_mapping = {
            'name': 0,
            'code': 1,
            'category': 2,
            'brand': 3,
            'model': 4,
            'serial_number': 5,
            'asset_tag': 6,
            'location': 7,
            'purchase_date': 8,
            'purchase_value': 9,
            'state': 10,
        }

        for row_num, row in enumerate(data_rows, start=2):  # Start at 2 if has header
            try:
                if len(row) < len(column_mapping):
                    # Pad row with empty strings
                    row.extend([''] * (len(column_mapping) - len(row)))

                # Extract data from row
                asset_data = self._extract_asset_data(row, column_mapping)

                # Check if asset exists (by code)
                existing_asset = asset_model.search([('code', '=', asset_data.get('code'))], limit=1)

                if existing_asset:
                    if self.import_type in ['update_existing', 'create_update']:
                        existing_asset.write(asset_data)
                        updated_count += 1
                    else:
                        errors.append(f"Row {row_num}: Asset code {asset_data.get('code')} already exists")
                        error_count += 1
                else:
                    if self.import_type in ['create_only', 'create_update']:
                        asset_model.create(asset_data)
                        created_count += 1
                    else:
                        errors.append(f"Row {row_num}: Asset code {asset_data.get('code')} not found for update")
                        error_count += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                error_count += 1

        # Generate results summary
        results = [
            f"Import completed:",
            f"- Assets created: {created_count}",
            f"- Assets updated: {updated_count}",
            f"- Errors: {error_count}",
            "",
        ]

        if errors:
            results.append("Errors:")
            results.extend(errors)

        return '\n'.join(results)

    def _extract_asset_data(self, row, column_mapping):
        """Extract asset data from CSV row"""
        category_model = self.env['it.asset.category']

        # Basic asset data
        asset_data = {
            'name': row[column_mapping['name']].strip() if row[column_mapping['name']] else '',
            'code': row[column_mapping['code']].strip() if row[column_mapping['code']] else '',
            'brand': row[column_mapping['brand']].strip() if row[column_mapping['brand']] else '',
            'model': row[column_mapping['model']].strip() if row[column_mapping['model']] else '',
            'serial_number': row[column_mapping['serial_number']].strip() if row[column_mapping['serial_number']] else '',
            'asset_tag': row[column_mapping['asset_tag']].strip() if row[column_mapping['asset_tag']] else '',
            'location': row[column_mapping['location']].strip() if row[column_mapping['location']] else '',
        }

        # Required fields validation
        if not asset_data['name']:
            raise ValidationError(_('Asset name is required'))
        if not asset_data['code']:
            raise ValidationError(_('Asset code is required'))

        # Category handling
        category_name = row[column_mapping['category']].strip() if row[column_mapping['category']] else ''
        if category_name:
            category = category_model.search([('name', '=', category_name)], limit=1)
            if not category:
                raise ValidationError(_('Category "%s" not found') % category_name)
            asset_data['category_id'] = category.id
        else:
            raise ValidationError(_('Category is required'))

        # Date handling
        purchase_date = row[column_mapping['purchase_date']].strip() if row[column_mapping['purchase_date']] else ''
        if purchase_date:
            try:
                asset_data['purchase_date'] = datetime.strptime(purchase_date, '%Y-%m-%d').date()
            except ValueError:
                try:
                    asset_data['purchase_date'] = datetime.strptime(purchase_date, '%m/%d/%Y').date()
                except ValueError:
                    raise ValidationError(_('Invalid purchase date format. Use YYYY-MM-DD or MM/DD/YYYY'))

        # Numeric handling
        purchase_value = row[column_mapping['purchase_value']].strip() if row[column_mapping['purchase_value']] else ''
        if purchase_value:
            try:
                asset_data['purchase_value'] = float(purchase_value.replace(',', ''))
            except ValueError:
                raise ValidationError(_('Invalid purchase value: %s') % purchase_value)

        # State handling
        state = row[column_mapping['state']].strip().lower() if row[column_mapping['state']] else 'draft'
        valid_states = ['draft', 'available', 'assigned', 'maintenance', 'repair', 'disposed']
        if state in valid_states:
            asset_data['state'] = state
        else:
            asset_data['state'] = 'draft'

        return asset_data

    def action_download_template(self):
        """Generate and download CSV template"""
        template_data = [
            ['name', 'code', 'category', 'brand', 'model', 'serial_number', 'asset_tag',
             'location', 'purchase_date', 'purchase_value', 'state'],
            ['Dell Laptop', 'LAPTOP-001', 'Laptops', 'Dell', 'Latitude 7420', 'DL001', 'IT-001',
             'IT Office', '2023-01-15', '1200.00', 'available'],
            ['HP Desktop', 'DESKTOP-001', 'Desktop Computers', 'HP', 'EliteDesk 800', 'HP001', 'IT-002',
             'Main Office', '2023-02-01', '950.00', 'assigned'],
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        for row in template_data:
            writer.writerow(row)

        template_content = output.getvalue().encode('utf-8')
        template_b64 = base64.b64encode(template_content)

        attachment = self.env['ir.attachment'].create({
            'name': 'asset_import_template.csv',
            'type': 'binary',
            'datas': template_b64,
            'res_model': 'it.asset.import.wizard',
            'res_id': self.id,
            'mimetype': 'text/csv',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }