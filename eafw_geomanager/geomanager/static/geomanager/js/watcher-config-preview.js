/**
 * WatcherConfig Preview Feature
 *
 * Adds a "Preview" button to WatcherConfig form that:
 * - Collects all form data (including unsaved changes)
 * - Sends AJAX request to preview endpoint
 * - Displays results in modal overlay
 * - Handles loading states and errors
 */

$(document).ready(function() {
    // Only run on WatcherConfig forms
    if (!isWatcherConfigForm()) {
        return;
    }

    // Load CSS for modal
    loadPreviewCSS();

    // Inject preview button into form footer
    injectPreviewButton();

    // Attach event handlers
    $('#watcher-config-preview-btn').on('click', handlePreviewClick);
});

function loadPreviewCSS() {
    // Check if CSS is already loaded
    if ($('link[href*="watcher-config-preview.css"]').length === 0) {
        var cssLink = $('<link>', {
            rel: 'stylesheet',
            type: 'text/css',
            href: '/static/geomanager/css/watcher-config-preview.css'
        });
        $('head').append(cssLink);
    }
}

function isWatcherConfigForm() {
    // Check if we're on a WatcherConfig form by presence of specific fields
    return $('#id_parser_type').length > 0 && $('#id_period_type').length > 0;
}

function injectPreviewButton() {
    // Find form footer (submit button area)
    var $footer = $('footer.footer');

    if ($footer.length === 0) {
        // Try alternative selector
        $footer = $('.object-help').closest('footer');
    }

    if ($footer.length === 0) {
        console.warn('Could not find footer to inject preview button');
        return;
    }

    // Get preview URL from window object (set by Django template)
    var previewUrl = window.watcherConfigPreviewUrl || '/admin/preview-watcher-config/';
    var configId = window.watcherConfigId || '';

    var buttonHtml =
        '<button type="button" ' +
        'id="watcher-config-preview-btn" ' +
        'class="button button-secondary" ' +
        'data-preview-url="' + previewUrl + '" ' +
        'data-config-id="' + configId + '" ' +
        'style="margin-right: 10px;">' +
        '<svg class="icon icon-view" aria-hidden="true" focusable="false">' +
        '<use href="#icon-view"></use>' +
        '</svg>' +
        '<span>Preview Configuration</span>' +
        '</button>';

    // Insert before submit button
    $footer.prepend(buttonHtml);
}

function handlePreviewClick(e) {
    e.preventDefault();

    var $button = $(this);
    var previewUrl = $button.data('preview-url');

    // Validate required fields before sending
    var validation = validateForm();
    if (!validation.valid) {
        showErrorModal('Validation Error', validation.errors.join('<br>'));
        return;
    }

    // Show loading state
    setButtonLoading($button, true);

    // Collect form data
    var formData = collectFormData();

    // Send AJAX request
    $.ajax({
        url: previewUrl,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(formData),
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        success: function(response) {
            setButtonLoading($button, false);
            if (response.success) {
                showPreviewModal(response);
            } else {
                showErrorModal('Preview Failed', response.error);
            }
        },
        error: function(xhr, status, error) {
            setButtonLoading($button, false);
            var errorMsg = 'An unexpected error occurred.';
            if (xhr.responseJSON && xhr.responseJSON.error) {
                errorMsg = xhr.responseJSON.error;
            } else if (xhr.status === 403) {
                errorMsg = 'Permission denied. Please ensure you have access to preview configurations.';
            } else if (xhr.status === 0) {
                errorMsg = 'Network error. Please check your internet connection.';
            }
            showErrorModal('Request Failed', errorMsg);
        }
    });
}

function validateForm() {
    var errors = [];

    // Required fields
    var apiUrl = $('#id_api_url').val();
    var parserType = $('#id_parser_type').val();
    var periodType = $('#id_period_type').val();

    if (!apiUrl || apiUrl.trim() === '') {
        errors.push('API URL is required');
    }

    if (!parserType) {
        errors.push('Parser Type is required');
    }

    if (!periodType) {
        errors.push('Period Type is required');
    }

    // dataset_start_year is optional — when absent only the latest API date is indexed

    // Parser-specific validation
    if (parserType === 'direct_date_field') {
        var jsonPath = $('#id_json_path').val();
        if (!jsonPath || jsonPath.trim() === '') {
            errors.push('Date Field Path is required for direct_date_field parser');
        }
    } else if (parserType === 'multi_field_constructor') {
        var yearField = $('#id_year_field').val();
        var monthField = $('#id_month_field').val();
        var dayField = $('#id_day_field').val();

        if (!yearField || !monthField || !dayField) {
            errors.push('Year, Month, and Day fields are required for multi_field_constructor parser');
        }
    }

    return {
        valid: errors.length === 0,
        errors: errors
    };
}

function collectFormData() {
    var startYearRaw = $('#id_dataset_start_year').val();
    var startYear = (startYearRaw && startYearRaw.trim() !== '') ? parseInt(startYearRaw, 10) : null;
    return {
        id: $('#watcher-config-preview-btn').data('config-id') || null,
        api_url: $('#id_api_url').val(),
        parser_type: $('#id_parser_type').val(),
        json_path: $('#id_json_path').val(),
        date_format: $('#id_date_format').val(),
        year_field: $('#id_year_field').val(),
        month_field: $('#id_month_field').val(),
        day_field: $('#id_day_field').val(),
        period_type: $('#id_period_type').val(),
        dataset_start_year: startYear
    };
}

function setButtonLoading($button, loading) {
    if (loading) {
        $button.prop('disabled', true);
        $button.find('span').text('Testing Configuration...');
        $button.addClass('button--loading');
    } else {
        $button.prop('disabled', false);
        $button.find('span').text('Preview Configuration');
        $button.removeClass('button--loading');
    }
}

function showPreviewModal(data) {
    var datasetContextHtml = '';
    if (data.dataset_context && data.dataset_context.length > 0) {
        var datasetListHtml = data.dataset_context.map(function(ds) {
            return '<li><strong>' + escapeHtml(ds.title) + '</strong> <span class="help-text">(' + escapeHtml(ds.slug) + ')</span></li>';
        }).join('');
        var datasetLabel = data.dataset_context.length === 1 ? 'Dataset using this config' : 'Datasets using this config (' + data.dataset_context.length + ')';
        datasetContextHtml =
            '<div class="watcher-preview-section">' +
            '<h3>' + datasetLabel + '</h3>' +
            '<ul class="watcher-preview-dataset-list">' + datasetListHtml + '</ul>' +
            '</div>';
    } else {
        datasetContextHtml =
            '<div class="watcher-preview-section">' +
            '<p class="help-block">' +
            'No datasets currently use this configuration. Preview is running in standalone mode.' +
            '</p>' +
            '</div>';
    }

    // Build existing dates sections if available
    var existingDatesHtml = '';
    if (data.existing_count && data.existing_count > 0) {
        var existingFirstHtml = data.existing_first_dates.map(function(d) {
            return '<li>' + escapeHtml(d) + '</li>';
        }).join('');

        var existingLastHtml = '';
        if (data.existing_last_dates && data.existing_last_dates.length > 0) {
            existingLastHtml = data.existing_last_dates.map(function(d) {
                return '<li>' + escapeHtml(d) + '</li>';
            }).join('');
        }

        var existingOmittedHtml = '';
        if (data.existing_count > 10) {
            existingOmittedHtml =
                '<div class="watcher-preview-section">' +
                '<p class="help-text">... (' + (data.existing_count - 10) + ' stored dates omitted) ...</p>' +
                '</div>';
        }

        var existingLastSection = '';
        if (existingLastHtml) {
            existingLastSection =
                '<div class="watcher-preview-section">' +
                '<h3>Last 5 Stored Dates</h3>' +
                '<ul class="watcher-preview-date-list">' +
                existingLastHtml +
                '</ul>' +
                '</div>';
        }

        existingDatesHtml =
            '<div class="watcher-preview-section">' +
            '<h3>Currently Stored Dates</h3>' +
            '<p><strong>Total dates in database:</strong> ' + data.existing_count + '</p>' +
            '</div>' +
            '<div class="watcher-preview-section">' +
            '<h3>First 5 Stored Dates</h3>' +
            '<ul class="watcher-preview-date-list">' +
            existingFirstHtml +
            '</ul>' +
            '</div>' +
            existingOmittedHtml +
            existingLastSection;
    }

    var backfillSectionHtml = '';
    if (data.total_count > 0) {
        var omittedHtml = '';
        if (data.total_count > 10) {
            omittedHtml =
                '<div class="watcher-preview-section">' +
                '<p class="help-text">... (' + (data.total_count - 10) + ' dates omitted) ...</p>' +
                '</div>';
        }

        var firstDatesHtml = data.first_dates.map(function(d) {
            return '<li>' + escapeHtml(d) + '</li>';
        }).join('');

        var lastDatesSection = '';
        if (data.last_dates && data.last_dates.length > 0) {
            var lastDatesHtml = data.last_dates.map(function(d) {
                return '<li>' + escapeHtml(d) + '</li>';
            }).join('');
            lastDatesSection =
                '<div class="watcher-preview-section">' +
                '<h3>Last 5 Dates to Backfill</h3>' +
                '<ul class="watcher-preview-date-list">' +
                lastDatesHtml +
                '</ul>' +
                '</div>';
        }

        backfillSectionHtml =
            '<div class="watcher-preview-section">' +
            '<h3>Backfill Calculation</h3>' +
            '<p><strong>Total dates to backfill:</strong> ' + data.total_count + '</p>' +
            '<p><strong>Period type:</strong> ' + escapeHtml(data.period_type) + '</p>' +
            '</div>' +
            '<div class="watcher-preview-section">' +
            '<h3>First 5 Dates to Backfill</h3>' +
            '<ul class="watcher-preview-date-list">' +
            firstDatesHtml +
            '</ul>' +
            '</div>' +
            omittedHtml +
            lastDatesSection;
    } else {
        // total_count is 0: either no start_year (no backfill mode) or backfill fully complete
        var dateStatusHtml = '';
        if (data.date_already_applied === true) {
            dateStatusHtml =
                '<p class="watcher-no-backfill-status watcher-no-backfill-status--applied">' +
                'Latest date already applied.' +
                '</p>';
        } else if (data.date_already_applied === false) {
            dateStatusHtml =
                '<p class="watcher-no-backfill-status watcher-no-backfill-status--new">' +
                'New date to be added: <strong>' + escapeHtml(data.latest_date_formatted) + '</strong>' +
                '</p>';
        }

        if (data.has_start_year) {
            backfillSectionHtml =
                '<div class="watcher-preview-section">' +
                '<h3>Backfill Status</h3>' +
                '<p class="help-text">All dates up to date — no new dates to backfill.</p>' +
                dateStatusHtml +
                '</div>';
        } else {
            backfillSectionHtml =
                '<div class="watcher-preview-section">' +
                '<p class="help-text">No backfill configured — only the latest date from the API will be indexed. ' +
                'Set a Dataset Start Year to enable historical backfilling.</p>' +
                dateStatusHtml +
                '</div>';
        }
    }

    // "Update Dates" button — only shown on edit view (configId is set)
    var configId = window.watcherConfigId || '';
    var triggerUrl = window.watcherConfigTriggerUrl || '';
    var dateAlreadyApplied = data.date_already_applied === true;
    var hasDatasets = data.dataset_context && data.dataset_context.length > 0;
    var updateBtnHtml = '';
    if (configId && triggerUrl) {
        updateBtnHtml =
            '<button class="button button-secondary" id="watcher-update-dates-btn" ' +
            'data-config-id="' + escapeHtml(configId) + '" ' +
            'data-trigger-url="' + escapeHtml(triggerUrl) + '" ' +
            'data-already-applied="' + dateAlreadyApplied + '" ' +
            'data-no-datasets="' + !hasDatasets + '">' +
            'Update Dates' +
            '</button>';
    }

    var modalHtml =
        '<div class="watcher-preview-modal-overlay" id="watcher-preview-modal">' +
        '<div class="watcher-preview-modal">' +
        '<div class="watcher-preview-modal__header">' +
        '<h2>Watcher Configuration Preview</h2>' +
        '<button class="button button-small button--icon" onclick="closePreviewModal()">' +
        '<svg class="icon icon-cross" aria-hidden="true">' +
        '<use href="#icon-cross"></use>' +
        '</svg>' +
        '</button>' +
        '</div>' +
        '<div class="watcher-preview-modal__body">' +
        datasetContextHtml +
        '<div class="watcher-preview-section">' +
        '<h3>Latest Date from API</h3>' +
        '<p class="watcher-preview-highlight">' + escapeHtml(data.latest_date_formatted) + '</p>' +
        '<p class="help-text">Raw: ' + escapeHtml(data.latest_date) + '</p>' +
        '</div>' +
        existingDatesHtml +
        backfillSectionHtml +
        '</div>' +
        '<div class="watcher-preview-modal__footer">' +
        '<button class="button button-secondary" onclick="closePreviewModal()">Close</button>' +
        updateBtnHtml +
        '</div>' +
        '</div>' +
        '</div>';

    $('body').append(modalHtml);

    // Bind Update Dates button
    $('#watcher-update-dates-btn').on('click', function() {
        var $btn = $(this);
        handleUpdateDates($btn.data('config-id'), $btn.data('trigger-url'), $btn);
    });

    // Add click-outside-to-close
    $('.watcher-preview-modal-overlay').on('click', function(e) {
        if (e.target === this) {
            closePreviewModal();
        }
    });

    // Add escape key to close
    $(document).on('keydown.previewModal', function(e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            closePreviewModal();
        }
    });
}

function handleUpdateDates(configId, triggerUrl, $btn) {
    if (!configId || !triggerUrl) {
        return;
    }

    // Short-circuit: no datasets linked to this config yet
    if ($btn.data('no-datasets') === true) {
        $btn.replaceWith(
            '<span class="watcher-update-result watcher-update-result--applied">No datasets linked — nothing to update.</span>'
        );
        return;
    }

    // Short-circuit: date is already applied, nothing to do
    if ($btn.data('already-applied') === true) {
        $btn.replaceWith(
            '<span class="watcher-update-result watcher-update-result--applied">Latest date already applied — nothing to update.</span>'
        );
        return;
    }

    $btn.prop('disabled', true).text('Updating...');

    $.ajax({
        url: triggerUrl,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ config_id: configId }),
        headers: { 'X-CSRFToken': getCsrfToken() },
        success: function(response) {
            if (response.success) {
                var msg = response.updated + ' dataset(s) updated';
                if (response.failed > 0) {
                    msg += ', ' + response.failed + ' failed';
                }
                var resultClass = response.failed > 0
                    ? 'watcher-update-result watcher-update-result--warn'
                    : 'watcher-update-result watcher-update-result--success';
                $btn.replaceWith('<span class="' + resultClass + '">' + escapeHtml(msg) + '</span>');
            } else {
                $btn.prop('disabled', false).text('Update Dates');
                var $footer = $('#watcher-preview-modal .watcher-preview-modal__footer');
                $footer.prepend(
                    '<p class="watcher-update-error">' + escapeHtml(response.error) + '</p>'
                );
            }
        },
        error: function(xhr) {
            $btn.prop('disabled', false).text('Update Dates');
            var errMsg = (xhr.responseJSON && xhr.responseJSON.error) || 'An unexpected error occurred.';
            var $footer = $('#watcher-preview-modal .watcher-preview-modal__footer');
            $footer.prepend(
                '<p class="watcher-update-error">' + escapeHtml(errMsg) + '</p>'
            );
        }
    });
}

function showErrorModal(title, message) {
    var modalHtml =
        '<div class="watcher-preview-modal-overlay" id="watcher-preview-modal">' +
        '<div class="watcher-preview-modal watcher-preview-modal--error">' +
        '<div class="watcher-preview-modal__header">' +
        '<h2>' + escapeHtml(title) + '</h2>' +
        '<button class="button button-small button--icon" onclick="closePreviewModal()">' +
        '<svg class="icon icon-cross" aria-hidden="true">' +
        '<use href="#icon-cross"></use>' +
        '</svg>' +
        '</button>' +
        '</div>' +
        '<div class="watcher-preview-modal__body">' +
        '<div class="messages">' +
        '<div class="error">' +
        '<p>' + message + '</p>' +
        '</div>' +
        '</div>' +
        '</div>' +
        '<div class="watcher-preview-modal__footer">' +
        '<button class="button button-secondary" onclick="closePreviewModal()">Close</button>' +
        '</div>' +
        '</div>' +
        '</div>';

    $('body').append(modalHtml);

    $('.watcher-preview-modal-overlay').on('click', function(e) {
        if (e.target === this) {
            closePreviewModal();
        }
    });

    // Add escape key to close
    $(document).on('keydown.previewModal', function(e) {
        if (e.key === 'Escape' || e.keyCode === 27) {
            closePreviewModal();
        }
    });
}

function closePreviewModal() {
    $('#watcher-preview-modal').remove();
    $(document).off('keydown.previewModal');
}

function getCsrfToken() {
    var token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : '';
}

function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    var map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, function(m) { return map[m]; });
}

// Make closePreviewModal globally accessible
window.closePreviewModal = closePreviewModal;
