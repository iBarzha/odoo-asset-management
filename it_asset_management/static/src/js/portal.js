/* IT Asset Management Portal JavaScript */

odoo.define('it_asset_management.portal', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');

    // Asset Request Form Widget
    publicWidget.registry.AssetRequestForm = publicWidget.Widget.extend({
        selector: '.request-form',
        events: {
            'change #request_type': '_onRequestTypeChange',
            'change #category_id': '_onCategoryChange',
            'submit form': '_onFormSubmit',
            'click .btn-add-specification': '_onAddSpecification',
        },

        start: function () {
            this._super.apply(this, arguments);
            this._initializeForm();
            return this._super.apply(this, arguments);
        },

        _initializeForm: function () {
            // Initialize form state based on current values
            this._onRequestTypeChange();
            this._updateAssetDropdown();
        },

        _onRequestTypeChange: function () {
            var requestType = this.$('#request_type').val();
            var $specsSection = this.$('#specs_section');
            var $assetSelect = this.$('#asset_id');
            var $assetLabel = this.$('label[for="asset_id"]');

            // Show/hide specifications section
            if (['new_asset', 'replacement', 'upgrade'].includes(requestType)) {
                $specsSection.slideDown();
            } else {
                $specsSection.slideUp();
            }

            // Update asset field requirements
            if (['repair', 'replacement', 'return'].includes(requestType)) {
                $assetSelect.prop('required', true);
                $assetLabel.html('Related Asset *');
                $assetSelect.closest('.mb-3').addClass('required');
            } else {
                $assetSelect.prop('required', false);
                $assetLabel.html('Related Asset (for repairs/returns)');
                $assetSelect.closest('.mb-3').removeClass('required');
            }

            // Update form validation
            this._updateFormValidation();
        },

        _onCategoryChange: function () {
            var categoryId = this.$('#category_id').val();
            if (categoryId) {
                this._loadAssetsByCategory(categoryId);
            } else {
                this._updateAssetDropdown();
            }
        },

        _loadAssetsByCategory: function (categoryId) {
            var self = this;
            var $assetSelect = this.$('#asset_id');

            // Show loading state
            $assetSelect.prop('disabled', true);
            $assetSelect.html('<option value="">Loading...</option>');

            // Make AJAX call to get assets for category
            ajax.jsonRpc('/my/assets/api/categories/' + categoryId + '/assets', 'call', {})
                .then(function (assets) {
                    self._updateAssetDropdown(assets);
                })
                .catch(function (error) {
                    console.error('Error loading assets:', error);
                    self._updateAssetDropdown();
                })
                .finally(function () {
                    $assetSelect.prop('disabled', false);
                });
        },

        _updateAssetDropdown: function (assets) {
            var $assetSelect = this.$('#asset_id');
            var currentValue = $assetSelect.val();

            // Clear existing options
            $assetSelect.empty();
            $assetSelect.append('<option value="">Select Asset</option>');

            // Add assets to dropdown
            if (assets && assets.length > 0) {
                assets.forEach(function (asset) {
                    var optionText = asset.name + ' (' + asset.code + ')';
                    if (asset.brand || asset.model) {
                        optionText += ' - ' + (asset.brand || '') + ' ' + (asset.model || '');
                    }
                    $assetSelect.append('<option value="' + asset.id + '">' + optionText + '</option>');
                });
            } else {
                // Fallback to all user assets (server-side rendered)
                this.$('#asset_id option[value!=""]').each(function () {
                    $assetSelect.append($(this).clone());
                });
            }

            // Restore previous selection if valid
            if (currentValue && $assetSelect.find('option[value="' + currentValue + '"]').length > 0) {
                $assetSelect.val(currentValue);
            }
        },

        _onFormSubmit: function (ev) {
            var self = this;
            var $form = this.$('form');
            var $submitBtn = $form.find('button[type="submit"]');

            // Validate form
            if (!this._validateForm()) {
                ev.preventDefault();
                return false;
            }

            // Show loading state
            $submitBtn.prop('disabled', true);
            $submitBtn.html('<i class="fa fa-spinner fa-spin"></i> Submitting...');
            $form.addClass('loading');

            // Allow form to submit normally
            return true;
        },

        _validateForm: function () {
            var isValid = true;
            var $form = this.$('form');

            // Clear previous validation messages
            $form.find('.is-invalid').removeClass('is-invalid');
            $form.find('.invalid-feedback').remove();

            // Validate required fields
            $form.find('[required]').each(function () {
                var $field = $(this);
                var value = $field.val();

                if (!value || value.trim() === '') {
                    isValid = false;
                    $field.addClass('is-invalid');
                    $field.after('<div class="invalid-feedback">This field is required.</div>');
                }
            });

            // Custom validation for request type and asset
            var requestType = this.$('#request_type').val();
            var assetId = this.$('#asset_id').val();

            if (['repair', 'replacement', 'return'].includes(requestType) && !assetId) {
                isValid = false;
                this.$('#asset_id').addClass('is-invalid');
                this.$('#asset_id').after('<div class="invalid-feedback">Asset is required for this request type.</div>');
            }

            // Validate date fields
            var requiredDate = this.$('#required_date').val();
            if (requiredDate) {
                var today = new Date().toISOString().split('T')[0];
                if (requiredDate < today) {
                    isValid = false;
                    this.$('#required_date').addClass('is-invalid');
                    this.$('#required_date').after('<div class="invalid-feedback">Required date cannot be in the past.</div>');
                }
            }

            return isValid;
        },

        _updateFormValidation: function () {
            // Update Bootstrap validation classes
            var $form = this.$('form');
            $form.addClass('needs-validation');
        },

        _onAddSpecification: function (ev) {
            ev.preventDefault();
            // Add dynamic specification fields (if needed in future)
            console.log('Add specification clicked');
        },
    });

    // Asset List Widget
    publicWidget.registry.AssetList = publicWidget.Widget.extend({
        selector: '.asset-list',
        events: {
            'click .asset-action-btn': '_onAssetAction',
            'change .asset-filter': '_onFilterChange',
        },

        _onAssetAction: function (ev) {
            ev.preventDefault();
            var $btn = $(ev.currentTarget);
            var action = $btn.data('action');
            var assetId = $btn.data('asset-id');

            switch (action) {
                case 'report_issue':
                    this._reportIssue(assetId);
                    break;
                case 'request_replacement':
                    this._requestReplacement(assetId);
                    break;
                default:
                    console.log('Unknown action:', action);
            }
        },

        _reportIssue: function (assetId) {
            window.location.href = '/my/request/new?asset_id=' + assetId + '&request_type=repair';
        },

        _requestReplacement: function (assetId) {
            window.location.href = '/my/request/new?asset_id=' + assetId + '&request_type=replacement';
        },

        _onFilterChange: function (ev) {
            var $filter = $(ev.currentTarget);
            var filterValue = $filter.val();
            var filterType = $filter.data('filter-type');

            // Apply client-side filtering if needed
            this._applyFilter(filterType, filterValue);
        },

        _applyFilter: function (filterType, filterValue) {
            // Implement client-side filtering logic
            console.log('Applying filter:', filterType, filterValue);
        },
    });

    // Request List Widget
    publicWidget.registry.RequestList = publicWidget.Widget.extend({
        selector: '.request-list',
        events: {
            'click .request-action-btn': '_onRequestAction',
            'submit .cancel-request-form': '_onCancelRequest',
        },

        _onRequestAction: function (ev) {
            ev.preventDefault();
            var $btn = $(ev.currentTarget);
            var action = $btn.data('action');
            var requestId = $btn.data('request-id');

            switch (action) {
                case 'view':
                    window.location.href = '/my/request/' + requestId;
                    break;
                case 'cancel':
                    this._confirmCancel(requestId);
                    break;
                default:
                    console.log('Unknown action:', action);
            }
        },

        _onCancelRequest: function (ev) {
            var confirmed = confirm('Are you sure you want to cancel this request?');
            if (!confirmed) {
                ev.preventDefault();
                return false;
            }

            // Show loading state
            var $form = $(ev.currentTarget);
            var $submitBtn = $form.find('button[type="submit"]');
            $submitBtn.prop('disabled', true);
            $submitBtn.html('<i class="fa fa-spinner fa-spin"></i> Cancelling...');

            return true;
        },

        _confirmCancel: function (requestId) {
            if (confirm('Are you sure you want to cancel this request?')) {
                // Submit cancel form
                var $form = $('form[data-request-id="' + requestId + '"]');
                if ($form.length) {
                    $form.submit();
                }
            }
        },
    });

    // Portal Navigation Enhancement
    publicWidget.registry.PortalNavigation = publicWidget.Widget.extend({
        selector: '.o_portal_wrap',
        events: {
            'click .nav-link': '_onNavClick',
            'submit .search-form': '_onSearch',
        },

        start: function () {
            this._super.apply(this, arguments);
            this._initializeTooltips();
            this._initializeAlerts();
            return this._super.apply(this, arguments);
        },

        _initializeTooltips: function () {
            // Initialize Bootstrap tooltips
            this.$('[data-bs-toggle="tooltip"]').tooltip();
        },

        _initializeAlerts: function () {
            // Auto-hide success alerts after 5 seconds
            setTimeout(function () {
                $('.alert-success').fadeOut();
            }, 5000);

            // Make alerts dismissible
            this.$('.alert').each(function () {
                var $alert = $(this);
                if (!$alert.find('.btn-close').length) {
                    $alert.append('<button type="button" class="btn-close" data-bs-dismiss="alert"></button>');
                }
            });
        },

        _onNavClick: function (ev) {
            // Add loading state to navigation
            var $link = $(ev.currentTarget);
            if ($link.attr('href') && !$link.attr('href').startsWith('#')) {
                $link.addClass('loading');
            }
        },

        _onSearch: function (ev) {
            // Add loading state to search
            var $form = $(ev.currentTarget);
            var $submitBtn = $form.find('button[type="submit"]');
            $submitBtn.prop('disabled', true);
            $submitBtn.html('<i class="fa fa-spinner fa-spin"></i>');
        },
    });

    // Utility functions
    var AssetPortalUtils = {
        showNotification: function (message, type) {
            type = type || 'info';
            var alertClass = 'alert-' + type;
            var $alert = $('<div class="alert ' + alertClass + ' alert-dismissible fade show" role="alert">' +
                '<strong>' + message + '</strong>' +
                '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>' +
                '</div>');

            // Insert at top of content
            $('.o_portal_wrap .container').prepend($alert);

            // Auto-hide after 5 seconds
            setTimeout(function () {
                $alert.fadeOut();
            }, 5000);
        },

        formatDate: function (dateString) {
            if (!dateString) return '';
            var date = new Date(dateString);
            return date.toLocaleDateString();
        },

        formatDateTime: function (dateTimeString) {
            if (!dateTimeString) return '';
            var date = new Date(dateTimeString);
            return date.toLocaleString();
        },

        showLoading: function ($element) {
            $element.addClass('loading');
        },

        hideLoading: function ($element) {
            $element.removeClass('loading');
        },
    };

    // Export utils for global access
    window.AssetPortalUtils = AssetPortalUtils;

    // Initialize on page load
    $(document).ready(function () {
        // Add smooth scrolling
        $('a[href^="#"]').on('click', function (e) {
            var target = this.hash;
            var $target = $(target);

            if ($target.length) {
                e.preventDefault();
                $('html, body').animate({
                    scrollTop: $target.offset().top - 100
                }, 500);
            }
        });

        // Add current page highlighting to navigation
        var currentPath = window.location.pathname;
        $('.nav-link').each(function () {
            var $link = $(this);
            var href = $link.attr('href');
            if (href && currentPath.startsWith(href)) {
                $link.addClass('active');
            }
        });

        // Form enhancement
        $('form').on('submit', function () {
            var $form = $(this);
            var $submitBtn = $form.find('button[type="submit"]');

            if (!$submitBtn.hasClass('loading')) {
                $submitBtn.prop('disabled', true);
                var originalText = $submitBtn.html();
                $submitBtn.data('original-text', originalText);
                $submitBtn.html('<i class="fa fa-spinner fa-spin"></i> Processing...');
            }
        });

        // Handle browser back button
        window.addEventListener('pageshow', function (event) {
            if (event.persisted) {
                // Page was loaded from cache, reset form states
                $('button[type="submit"]').each(function () {
                    var $btn = $(this);
                    $btn.prop('disabled', false);
                    var originalText = $btn.data('original-text');
                    if (originalText) {
                        $btn.html(originalText);
                    }
                });
                $('.loading').removeClass('loading');
            }
        });
    });

    return {
        AssetRequestForm: publicWidget.registry.AssetRequestForm,
        AssetList: publicWidget.registry.AssetList,
        RequestList: publicWidget.registry.RequestList,
        PortalNavigation: publicWidget.registry.PortalNavigation,
        Utils: AssetPortalUtils,
    };
});

// Additional vanilla JS for non-Odoo environments
if (typeof odoo === 'undefined') {
    // Fallback implementation for standalone usage
    document.addEventListener('DOMContentLoaded', function () {
        console.log('IT Asset Management Portal loaded');

        // Basic form validation
        var forms = document.querySelectorAll('.needs-validation');
        Array.prototype.slice.call(forms).forEach(function (form) {
            form.addEventListener('submit', function (event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    });
}