# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import csv
import io
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AssetExportWizard(models.TransientModel):
    _name = 'it.asset.export.wizard'
    _description = 'Asset Export Wizard'

    export_format = fields.Selection([
        ('csv', 'CSV'),
        ('xlsx', 'Excel (XLSX)'),
    ], string='Export Format', default='csv', required=True)

    export_type = fields.Selection([
        ('all', 'All Assets'),
        ('filtered', 'Filtered Assets'),
        ('selected', 'Selected Assets'),
    ], string='Export Type', default='all', required=True)

    asset_ids = fields.Many2many('it.asset', string='Assets to Export')

    include_assignments = fields.Boolean('Include Assignment History', default=False)
    include_requests = fields.Boolean('Include Request History', default=False)

    # Filter options
    category_ids = fields.Many2many('it.asset.category', string='Categories')
    state_filter = fields.Selection([
        ('draft', 'Draft'),
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('maintenance', 'Under Maintenance'),
        ('repair', 'Under Repair'),
        ('disposed', 'Disposed'),
    ], string='State Filter')

    date_from = fields.Date('Purchase Date From')
    date_to = fields.Date('Purchase Date To')

    delimiter = fields.Selection([
        (',', 'Comma (,)'),
        (';', 'Semicolon (;)'),
        ('\t', 'Tab'),
        ('|', 'Pipe (|)'),
    ], string='CSV Delimiter', default=',')

    exported_file = fields.Binary('Exported File', readonly=True)
    exported_filename = fields.Char('File Name', readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Set default assets if called from asset list view"""
        defaults = super().default_get(fields_list)

        # Get selected assets from context
        active_ids = self.env.context.get('active_ids', [])
        if active_ids and 'asset_ids' in fields_list:
            defaults['asset_ids'] = [(6, 0, active_ids)]
            defaults['export_type'] = 'selected'

        return defaults

    def action_export(self):
        """Export assets based on configuration"""
        assets = self._get_assets_to_export()

        if not assets:
            raise UserError(_('No assets found to export.'))

        if self.export_format == 'csv':
            file_content, filename = self._export_csv(assets)
        else:
            file_content, filename = self._export_xlsx(assets)

        self.exported_file = base64.b64encode(file_content)
        self.exported_filename = filename

        return {
            'type': 'ir.actions.act_window',
            'name': _('Export Complete'),
            'res_model': 'it.asset.export.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_assets_to_export(self):
        """Get assets based on export type and filters"""
        domain = []

        if self.export_type == 'selected':
            if self.asset_ids:
                return self.asset_ids
            else:
                raise UserError(_('No assets selected for export.'))

        elif self.export_type == 'filtered':
            if self.category_ids:
                domain.append(('category_id', 'in', self.category_ids.ids))

            if self.state_filter:
                domain.append(('state', '=', self.state_filter))

            if self.date_from:
                domain.append(('purchase_date', '>=', self.date_from))

            if self.date_to:
                domain.append(('purchase_date', '<=', self.date_to))

        return self.env['it.asset'].search(domain)

    def _export_csv(self, assets):
        """Export assets to CSV format"""
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.delimiter)

        # Write header
        header = [
            'Asset Name', 'Asset Code', 'Category', 'Brand', 'Model',
            'Serial Number', 'Asset Tag', 'State', 'Location',
            'Purchase Date', 'Purchase Value', 'Vendor',
            'Warranty Start', 'Warranty End', 'Assigned User',
            'Created Date', 'Last Updated'
        ]

        if self.include_assignments:
            header.extend(['Assignment History'])

        if self.include_requests:
            header.extend(['Request History'])

        writer.writerow(header)

        # Write asset data
        for asset in assets:
            row = [
                asset.name or '',
                asset.code or '',
                asset.category_id.name or '',
                asset.brand or '',
                asset.model or '',
                asset.serial_number or '',
                asset.asset_tag or '',
                asset.state or '',
                asset.location or '',
                asset.purchase_date.strftime('%Y-%m-%d') if asset.purchase_date else '',
                str(asset.purchase_value) if asset.purchase_value else '',
                asset.vendor_id.name if asset.vendor_id else '',
                asset.warranty_start_date.strftime('%Y-%m-%d') if asset.warranty_start_date else '',
                asset.warranty_end_date.strftime('%Y-%m-%d') if asset.warranty_end_date else '',
                asset.assigned_user_id.name if asset.assigned_user_id else '',
                asset.create_date.strftime('%Y-%m-%d %H:%M:%S') if asset.create_date else '',
                asset.write_date.strftime('%Y-%m-%d %H:%M:%S') if asset.write_date else '',
            ]

            if self.include_assignments:
                assignments = asset.assignment_ids.mapped(lambda a: f"{a.assigned_user_id.name}: {a.assignment_date} - {a.return_date or 'Current'}")
                row.append('; '.join(assignments))

            if self.include_requests:
                requests = asset.request_ids.mapped(lambda r: f"{r.name}: {r.request_date} ({r.state})")
                row.append('; '.join(requests))

            writer.writerow(row)

        content = output.getvalue().encode('utf-8')
        filename = f"assets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return content, filename

    def _export_xlsx(self, assets):
        """Export assets to Excel format"""
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('xlsxwriter library is required for Excel export. Please install it.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Create worksheet
        worksheet = workbook.add_worksheet('Assets')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1
        })

        cell_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})
        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})

        # Write headers
        headers = [
            'Asset Name', 'Asset Code', 'Category', 'Brand', 'Model',
            'Serial Number', 'Asset Tag', 'State', 'Location',
            'Purchase Date', 'Purchase Value', 'Vendor',
            'Warranty Start', 'Warranty End', 'Assigned User',
            'Created Date', 'Last Updated'
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        for row, asset in enumerate(assets, start=1):
            worksheet.write(row, 0, asset.name or '', cell_format)
            worksheet.write(row, 1, asset.code or '', cell_format)
            worksheet.write(row, 2, asset.category_id.name or '', cell_format)
            worksheet.write(row, 3, asset.brand or '', cell_format)
            worksheet.write(row, 4, asset.model or '', cell_format)
            worksheet.write(row, 5, asset.serial_number or '', cell_format)
            worksheet.write(row, 6, asset.asset_tag or '', cell_format)
            worksheet.write(row, 7, asset.state or '', cell_format)
            worksheet.write(row, 8, asset.location or '', cell_format)

            if asset.purchase_date:
                worksheet.write_datetime(row, 9, asset.purchase_date, date_format)
            else:
                worksheet.write(row, 9, '', cell_format)

            worksheet.write(row, 10, asset.purchase_value or 0, money_format)
            worksheet.write(row, 11, asset.vendor_id.name if asset.vendor_id else '', cell_format)

            if asset.warranty_start_date:
                worksheet.write_datetime(row, 12, asset.warranty_start_date, date_format)
            else:
                worksheet.write(row, 12, '', cell_format)

            if asset.warranty_end_date:
                worksheet.write_datetime(row, 13, asset.warranty_end_date, date_format)
            else:
                worksheet.write(row, 13, '', cell_format)

            worksheet.write(row, 14, asset.assigned_user_id.name if asset.assigned_user_id else '', cell_format)

            if asset.create_date:
                worksheet.write_datetime(row, 15, asset.create_date, date_format)
            else:
                worksheet.write(row, 15, '', cell_format)

            if asset.write_date:
                worksheet.write_datetime(row, 16, asset.write_date, date_format)
            else:
                worksheet.write(row, 16, '', cell_format)

        # Auto-adjust column widths
        for col in range(len(headers)):
            worksheet.set_column(col, col, 15)

        workbook.close()
        output.seek(0)
        content = output.read()
        filename = f"assets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return content, filename

    def action_download(self):
        """Download the exported file"""
        if not self.exported_file:
            raise UserError(_('No file to download. Please export first.'))

        attachment = self.env['ir.attachment'].create({
            'name': self.exported_filename,
            'type': 'binary',
            'datas': self.exported_file,
            'res_model': 'it.asset.export.wizard',
            'res_id': self.id,
            'mimetype': 'application/octet-stream',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }