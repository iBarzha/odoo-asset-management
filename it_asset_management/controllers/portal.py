# -*- coding: utf-8 -*-
# Part of IT Asset Management Module for Odoo 18
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import json
from collections import OrderedDict
from operator import itemgetter

from odoo import fields, http, tools, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.osv import expression


class AssetPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        AssetAssignment = request.env['it.asset.assignment']
        AssetRequest = request.env['it.asset.request']

        if 'asset_count' in counters:
            values['asset_count'] = AssetAssignment.search_count([
                ('user_id', '=', request.env.user.id),
                ('is_active', '=', True)
            ]) if AssetAssignment.check_access_rights('read', raise_exception=False) else 0

        if 'request_count' in counters:
            values['request_count'] = AssetRequest.search_count([
                ('user_id', '=', request.env.user.id)
            ]) if AssetRequest.check_access_rights('read', raise_exception=False) else 0

        if 'pending_request_count' in counters:
            values['pending_request_count'] = AssetRequest.search_count([
                ('user_id', '=', request.env.user.id),
                ('state', 'in', ['draft', 'submitted', 'under_review', 'approved', 'in_progress'])
            ]) if AssetRequest.check_access_rights('read', raise_exception=False) else 0

        return values

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        values.update({
            'asset_count': request.env['it.asset.assignment'].search_count([
                ('user_id', '=', request.env.user.id),
                ('is_active', '=', True)
            ]),
            'request_count': request.env['it.asset.request'].search_count([
                ('user_id', '=', request.env.user.id)
            ]),
        })
        return values

    # Asset Assignment Routes
    @http.route(['/my/assets', '/my/assets/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_assets(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        AssetAssignment = request.env['it.asset.assignment']

        domain = [
            ('user_id', '=', request.env.user.id),
            ('is_active', '=', True)
        ]

        searchbar_sortings = {
            'date': {'label': _('Assignment Date'), 'order': 'assignment_date desc'},
            'name': {'label': _('Asset Name'), 'order': 'asset_id'},
            'category': {'label': _('Category'), 'order': 'asset_category'},
        }

        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Asset Name)</span>')},
            'asset': {'input': 'asset', 'label': _('Search in Asset')},
            'category': {'input': 'category', 'label': _('Search in Category')},
        }

        # Search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'asset'):
                search_domain = expression.OR([search_domain, [('asset_name', 'ilike', search)]])
            if search_in in ('content', 'category'):
                search_domain = expression.OR([search_domain, [('asset_category', 'ilike', search)]])
            domain += search_domain

        # Default sort
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count
        assignment_count = AssetAssignment.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/assets",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'search_in': search_in, 'search': search},
            total=assignment_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        assignments = AssetAssignment.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_assets_history'] = assignments.ids[:100]

        values.update({
            'assignments': assignments,
            'page_name': 'asset',
            'pager': pager,
            'default_url': '/my/assets',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
        })
        return request.render("it_asset_management.portal_my_assets", values)

    @http.route(['/my/asset/<int:assignment_id>'], type='http', auth="user", website=True)
    def portal_my_asset(self, assignment_id, access_token=None, **kw):
        try:
            assignment_sudo = self._document_check_access('it.asset.assignment', assignment_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'assignment': assignment_sudo,
            'token': access_token,
            'bootstrap_formatting': True,
            'partner_id': assignment_sudo.user_id.partner_id.id,
            'report_type': 'html',
            'page_name': 'asset',
        }
        return request.render("it_asset_management.portal_my_asset_detail", values)

    # Asset Request Routes
    @http.route(['/my/requests', '/my/requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_requests(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        AssetRequest = request.env['it.asset.request']

        domain = [('user_id', '=', request.env.user.id)]

        searchbar_sortings = {
            'date': {'label': _('Request Date'), 'order': 'request_date desc'},
            'name': {'label': _('Request Number'), 'order': 'name desc'},
            'stage': {'label': _('Status'), 'order': 'state'},
            'priority': {'label': _('Priority'), 'order': 'priority desc'},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'submitted': {'label': _('Submitted'), 'domain': [('state', '=', 'submitted')]},
            'approved': {'label': _('Approved'), 'domain': [('state', '=', 'approved')]},
            'in_progress': {'label': _('In Progress'), 'domain': [('state', '=', 'in_progress')]},
            'completed': {'label': _('Completed'), 'domain': [('state', '=', 'completed')]},
            'rejected': {'label': _('Rejected'), 'domain': [('state', '=', 'rejected')]},
        }

        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Request)</span>')},
            'name': {'input': 'name', 'label': _('Search in Number')},
            'description': {'input': 'description', 'label': _('Search in Description')},
        }

        # Default filter
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # Search
        if search and search_in:
            search_domain = []
            if search_in in ('content', 'name'):
                search_domain = expression.OR([search_domain, [('name', 'ilike', search)]])
            if search_in in ('content', 'description'):
                search_domain = expression.OR([search_domain, [('description', 'ilike', search)]])
            domain += search_domain

        # Default sort
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Count
        request_count = AssetRequest.search_count(domain)

        # Pager
        pager = portal_pager(
            url="/my/requests",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search},
            total=request_count,
            page=page,
            step=self._items_per_page
        )

        # Content
        requests = AssetRequest.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_requests_history'] = requests.ids[:100]

        values.update({
            'requests': requests,
            'page_name': 'request',
            'pager': pager,
            'default_url': '/my/requests',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'filterby': filterby,
            'sortby': sortby,
        })
        return request.render("it_asset_management.portal_my_requests", values)

    @http.route(['/my/request/<int:request_id>'], type='http', auth="user", website=True)
    def portal_my_request(self, request_id, access_token=None, **kw):
        try:
            request_sudo = self._document_check_access('it.asset.request', request_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = {
            'request': request_sudo,
            'token': access_token,
            'bootstrap_formatting': True,
            'partner_id': request_sudo.user_id.partner_id.id,
            'report_type': 'html',
            'page_name': 'request',
        }
        return request.render("it_asset_management.portal_my_request_detail", values)

    @http.route('/my/request/new', type='http', auth="user", website=True, methods=['GET', 'POST'])
    def portal_create_request(self, **kw):
        if request.httprequest.method == 'POST':
            return self._handle_request_creation(kw)

        # GET request - show form
        values = self._prepare_request_form_values()
        return request.render("it_asset_management.portal_create_request", values)

    def _handle_request_creation(self, kw):
        """Handle POST request for creating new asset request"""
        try:
            # Validate required fields
            if not kw.get('request_type') or not kw.get('description'):
                raise ValueError(_('Request type and description are required'))

            # Prepare values
            values = {
                'request_type': kw.get('request_type'),
                'description': kw.get('description'),
                'justification': kw.get('justification', ''),
                'priority': kw.get('priority', 'medium'),
                'required_date': kw.get('required_date') if kw.get('required_date') else False,
                'category_id': int(kw.get('category_id')) if kw.get('category_id') and kw.get('category_id') != '0' else False,
                'asset_id': int(kw.get('asset_id')) if kw.get('asset_id') and kw.get('asset_id') != '0' else False,
                'user_id': request.env.user.id,
                'state': 'submitted',
                'specifications': kw.get('specifications', ''),
                'preferred_brand': kw.get('preferred_brand', ''),
                'preferred_model': kw.get('preferred_model', ''),
            }

            # Create request
            new_request = request.env['it.asset.request'].sudo().create(values)

            # Handle file uploads if any
            attachments = request.httprequest.files.getlist('attachments')
            for attachment in attachments:
                if attachment.filename:
                    request.env['ir.attachment'].sudo().create({
                        'name': attachment.filename,
                        'datas': base64.b64encode(attachment.read()),
                        'res_model': 'it.asset.request',
                        'res_id': new_request.id,
                    })

            # Success message and redirect
            request.session['form_success'] = _('Your request has been submitted successfully!')
            return request.redirect('/my/request/%s' % new_request.id)

        except Exception as e:
            # Error handling
            values = self._prepare_request_form_values()
            values.update({
                'error_message': str(e),
                'form_data': kw,
            })
            return request.render("it_asset_management.portal_create_request", values)

    def _prepare_request_form_values(self):
        """Prepare values for request creation form"""
        categories = request.env['it.asset.category'].sudo().search([])

        # Get user's currently assigned assets for repair/return requests
        user_assets = request.env['it.asset.assignment'].sudo().search([
            ('user_id', '=', request.env.user.id),
            ('is_active', '=', True)
        ]).mapped('asset_id')

        return {
            'categories': categories,
            'user_assets': user_assets,
            'page_name': 'new_request',
            'request_types': [
                ('new_asset', _('New Asset Request')),
                ('repair', _('Repair Request')),
                ('replacement', _('Replacement Request')),
                ('return', _('Return Request')),
                ('upgrade', _('Upgrade Request')),
            ],
            'priorities': [
                ('low', _('Low')),
                ('medium', _('Medium')),
                ('high', _('High')),
                ('urgent', _('Urgent')),
            ],
        }

    @http.route('/my/request/<int:request_id>/cancel', type='http', auth="user", website=True, methods=['POST'])
    def portal_cancel_request(self, request_id, **kw):
        """Cancel a request from portal"""
        try:
            request_sudo = self._document_check_access('it.asset.request', request_id)
            if request_sudo.state in ['draft', 'submitted', 'under_review']:
                request_sudo.sudo().action_cancel()
                request.session['form_success'] = _('Request cancelled successfully!')
            else:
                request.session['form_error'] = _('This request cannot be cancelled in its current state.')
        except (AccessError, MissingError):
            request.session['form_error'] = _('Request not found or access denied.')

        return request.redirect('/my/request/%s' % request_id)

    # API Routes for AJAX requests
    @http.route('/my/assets/api/categories/<int:category_id>/assets', type='json', auth="user")
    def api_get_category_assets(self, category_id):
        """Get assets for a specific category (for AJAX requests)"""
        user_assets = request.env['it.asset.assignment'].search([
            ('user_id', '=', request.env.user.id),
            ('is_active', '=', True),
            ('asset_category', '=', category_id)
        ]).mapped('asset_id')

        return [{
            'id': asset.id,
            'name': asset.name,
            'code': asset.code,
            'brand': asset.brand or '',
            'model': asset.model or '',
        } for asset in user_assets]

    # Document access check helper
    def _document_check_access(self, model_name, document_id, access_token=None):
        document = request.env[model_name].browse([document_id])
        document_sudo = document.sudo().exists()
        if not document_sudo:
            raise MissingError(_("This document does not exist."))

        try:
            document.check_access_rights('read')
            document.check_access_rule('read')
        except AccessError:
            if not access_token:
                raise
        return document_sudo

    # QR Code Scanner Routes
    @http.route('/my/scanner', type='http', auth="user", website=True)
    def portal_scanner(self, **kw):
        """QR Code and Barcode Scanner Page"""
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'scanner',
        })
        return request.render("it_asset_management.portal_scanner", values)

    @http.route('/my/asset/scan/<string:asset_code>', type='http', auth="user", website=True)
    def portal_asset_scan_redirect(self, asset_code, **kw):
        """Redirect from QR code scan to asset details"""
        try:
            asset = request.env['it.asset'].sudo().search([('code', '=', asset_code)], limit=1)
            if not asset:
                # Try to find by barcode
                asset = request.env['it.asset'].sudo().search([('barcode', '=', asset_code)], limit=1)

            if asset:
                # Check if user has assignment for this asset
                assignment = request.env['it.asset.assignment'].search([
                    ('asset_id', '=', asset.id),
                    ('user_id', '=', request.env.user.id),
                    ('is_active', '=', True)
                ], limit=1)

                if assignment:
                    return request.redirect(f'/my/asset/{assignment.id}')
                else:
                    # Show asset info even if not assigned to user
                    return request.redirect(f'/my/asset/info/{asset.id}')
            else:
                request.session['scan_error'] = _('Asset not found: %s') % asset_code
                return request.redirect('/my/scanner')
        except Exception as e:
            request.session['scan_error'] = _('Error processing scan: %s') % str(e)
            return request.redirect('/my/scanner')

    @http.route('/my/asset/info/<int:asset_id>', type='http', auth="user", website=True)
    def portal_asset_info(self, asset_id, **kw):
        """Show asset information (read-only for non-assigned assets)"""
        try:
            asset = request.env['it.asset'].sudo().browse(asset_id)
            if not asset.exists():
                return request.redirect('/my/scanner')

            values = {
                'asset': asset,
                'page_name': 'asset_info',
                'is_assigned': bool(asset.assigned_user_id == request.env.user),
            }
            return request.render("it_asset_management.portal_asset_info", values)
        except Exception:
            return request.redirect('/my/scanner')

    @http.route('/my/scan/api/process', type='json', auth="user")
    def api_process_scan(self, scan_data, scan_type='auto'):
        """Process scanned QR code or barcode data"""
        try:
            asset = None

            if scan_type == 'qr' or scan_type == 'auto':
                # Try to process as QR code JSON
                try:
                    import json
                    qr_data = json.loads(scan_data)
                    if 'asset_code' in qr_data:
                        asset = request.env['it.asset'].sudo().search([
                            ('code', '=', qr_data['asset_code'])
                        ], limit=1)
                except (json.JSONDecodeError, TypeError):
                    pass

            if not asset and (scan_type == 'barcode' or scan_type == 'auto'):
                # Try to process as barcode or asset code
                asset = request.env['it.asset'].sudo().search([
                    '|',
                    ('code', '=', scan_data),
                    ('barcode', '=', scan_data)
                ], limit=1)

            if asset:
                # Check user access
                assignment = request.env['it.asset.assignment'].search([
                    ('asset_id', '=', asset.id),
                    ('user_id', '=', request.env.user.id),
                    ('is_active', '=', True)
                ], limit=1)

                return {
                    'status': 'success',
                    'asset': {
                        'id': asset.id,
                        'name': asset.name,
                        'code': asset.code,
                        'category': asset.category_id.name,
                        'brand': asset.brand or '',
                        'model': asset.model or '',
                        'state': asset.state,
                        'is_assigned_to_user': bool(assignment),
                        'assigned_user': asset.assigned_user_id.name if asset.assigned_user_id else '',
                        'location': asset.location or '',
                    },
                    'redirect_url': f'/my/asset/{assignment.id}' if assignment else f'/my/asset/info/{asset.id}'
                }
            else:
                return {
                    'status': 'error',
                    'message': _('Asset not found')
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': _('Error processing scan: %s') % str(e)
            }

    # Override portal breadcrumbs
    def _get_portal_default_url(self):
        return '/my/assets'