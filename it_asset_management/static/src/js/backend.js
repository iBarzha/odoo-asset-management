/* IT Asset Management Backend JavaScript */

odoo.define('it_asset_management.backend', function (require) {
    'use strict';

    var core = require('web.core');
    var ListController = require('web.ListController');
    var FormController = require('web.FormController');
    var KanbanController = require('web.KanbanController');

    var _t = core._t;

    // Extend List Controller for Asset Management
    var AssetListController = ListController.extend({
        events: _.extend({}, ListController.prototype.events, {
            'click .asset_bulk_assign': '_onBulkAssign',
            'click .asset_bulk_maintenance': '_onBulkMaintenance',
        }),

        _onBulkAssign: function () {
            var self = this;
            var selectedIds = this.getSelectedIds();

            if (selectedIds.length === 0) {
                this.displayNotification({
                    type: 'warning',
                    message: _t('Please select at least one asset.'),
                });
                return;
            }

            this.do_action({
                type: 'ir.actions.act_window',
                name: _t('Bulk Assign Assets'),
                res_model: 'it.asset.bulk.assign.wizard',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_asset_ids: selectedIds,
                },
            });
        },

        _onBulkMaintenance: function () {
            var self = this;
            var selectedIds = this.getSelectedIds();

            if (selectedIds.length === 0) {
                this.displayNotification({
                    type: 'warning',
                    message: _t('Please select at least one asset.'),
                });
                return;
            }

            this._rpc({
                model: 'it.asset',
                method: 'write',
                args: [selectedIds, {state: 'maintenance'}],
            }).then(function () {
                self.displayNotification({
                    type: 'success',
                    message: _t('Assets moved to maintenance state.'),
                });
                self.reload();
            });
        },
    });

    // Extend Form Controller for Asset Management
    var AssetFormController = FormController.extend({
        events: _.extend({}, FormController.prototype.events, {
            'click .asset_quick_assign': '_onQuickAssign',
            'click .asset_generate_qr': '_onGenerateQR',
        }),

        _onQuickAssign: function () {
            var self = this;
            var recordId = this.model.get(this.handle).res_id;

            if (!recordId) {
                this.displayNotification({
                    type: 'warning',
                    message: _t('Please save the asset first.'),
                });
                return;
            }

            this.do_action({
                type: 'ir.actions.act_window',
                name: _t('Quick Assign Asset'),
                res_model: 'it.asset.assignment.wizard',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_asset_id: recordId,
                },
            });
        },

        _onGenerateQR: function () {
            var self = this;
            var recordId = this.model.get(this.handle).res_id;

            if (!recordId) {
                this.displayNotification({
                    type: 'warning',
                    message: _t('Please save the asset first.'),
                });
                return;
            }

            this._rpc({
                route: '/asset/qr_code/' + recordId,
                params: {},
            }).then(function (result) {
                if (result.qr_code) {
                    self.displayNotification({
                        type: 'success',
                        message: _t('QR Code generated successfully.'),
                    });
                    // You could open the QR code in a modal or download it
                }
            });
        },
    });

    // Dashboard Widget for Asset Statistics
    var AssetDashboard = core.Class.extend({
        init: function (parent, context) {
            this._super.apply(this, arguments);
            this.context = context || {};
        },

        start: function () {
            this._loadDashboardData();
        },

        _loadDashboardData: function () {
            var self = this;
            return this._rpc({
                model: 'it.asset.dashboard',
                method: 'create',
                args: [{}],
            }).then(function (dashboardId) {
                return self._rpc({
                    model: 'it.asset.dashboard',
                    method: 'read',
                    args: [dashboardId],
                });
            }).then(function (data) {
                self._renderDashboard(data[0]);
            });
        },

        _renderDashboard: function (data) {
            // Dashboard rendering logic
            console.log('Dashboard data:', data);
        },
    });

    // Utility functions for asset management
    var AssetUtils = {
        formatAssetCode: function (code) {
            return code ? code.toUpperCase() : '';
        },

        getAssetStatusColor: function (state) {
            var colors = {
                'draft': '#6c757d',
                'available': '#28a745',
                'assigned': '#17a2b8',
                'maintenance': '#ffc107',
                'repair': '#fd7e14',
                'disposed': '#dc3545',
            };
            return colors[state] || '#6c757d';
        },

        getRequestPriorityColor: function (priority) {
            var colors = {
                'low': '#6c757d',
                'medium': '#17a2b8',
                'high': '#ffc107',
                'urgent': '#dc3545',
            };
            return colors[priority] || '#6c757d';
        },

        formatWarrantyStatus: function (status) {
            var labels = {
                'valid': _t('Under Warranty'),
                'expiring': _t('Warranty Expiring'),
                'expired': _t('Warranty Expired'),
                'none': _t('No Warranty'),
            };
            return labels[status] || status;
        },

        showAssetQRCode: function (assetId, assetName) {
            // Generate and show QR code for asset
            var qrUrl = '/asset/qr/' + assetId;
            var content = '<div class="text-center">' +
                '<h4>' + assetName + '</h4>' +
                '<img src="' + qrUrl + '" alt="QR Code" class="img-fluid">' +
                '</div>';

            // Show in modal (implementation depends on your modal system)
            console.log('QR Code URL:', qrUrl);
        },

        exportAssetList: function (assetIds, format) {
            format = format || 'xlsx';
            var url = '/asset/export/' + format + '?ids=' + assetIds.join(',');
            window.open(url, '_blank');
        },

        bulkUpdateAssets: function (assetIds, values) {
            return rpc.query({
                model: 'it.asset',
                method: 'write',
                args: [assetIds, values],
            });
        },
    };

    // Register controllers
    if (window.odoo && window.odoo.define) {
        core.list_registry.add('it_asset_list', AssetListController);
        core.form_registry.add('it_asset_form', AssetFormController);
    }

    return {
        AssetListController: AssetListController,
        AssetFormController: AssetFormController,
        AssetDashboard: AssetDashboard,
        AssetUtils: AssetUtils,
    };
});

// Standalone functions for non-Odoo usage
if (typeof odoo === 'undefined') {
    window.AssetManagement = {
        Utils: {
            formatAssetCode: function (code) {
                return code ? code.toUpperCase() : '';
            },

            getAssetStatusColor: function (state) {
                var colors = {
                    'draft': '#6c757d',
                    'available': '#28a745',
                    'assigned': '#17a2b8',
                    'maintenance': '#ffc107',
                    'repair': '#fd7e14',
                    'disposed': '#dc3545',
                };
                return colors[state] || '#6c757d';
            },

            showNotification: function (message, type) {
                type = type || 'info';
                console.log('[' + type.toUpperCase() + '] ' + message);

                // Create simple notification
                var notification = document.createElement('div');
                notification.className = 'alert alert-' + type + ' alert-dismissible';
                notification.innerHTML = message +
                    '<button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>';

                document.body.appendChild(notification);

                setTimeout(function () {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 5000);
            },
        },
    };
}