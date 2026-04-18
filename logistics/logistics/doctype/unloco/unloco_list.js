// Copyright (c) 2025, Agilasoft Cloud Technologies Inc. and contributors
// For license information, please see license.txt
// List view: Import UNLOCO bulk dialog + Actions / toolbar entries

function show_unloco_import_dialog(listview) {
    const d = new frappe.ui.Dialog({
        title: __('Import UNLOCO'),
        fields: [
            {
                fieldname: 'help',
                fieldtype: 'HTML',
                options:
                    '<p class="text-muted small">' +
                    __(
                        'Add rows in the table and/or paste codes below. One code per line or comma-separated. Each code is created with auto-populate. Maximum 500 per run; for larger sets use Data Import.'
                    ) +
                    '</p>',
            },
            {
                fieldname: 'codes_table',
                fieldtype: 'Table',
                label: __('Codes'),
                fields: [
                    {
                        fieldname: 'unlocode',
                        fieldtype: 'Data',
                        label: __('UNLOCO Code'),
                        in_list_view: 1,
                    },
                ],
                data: [],
            },
            {
                fieldname: 'paste_codes',
                fieldtype: 'Small Text',
                label: __('Paste codes (optional)'),
            },
        ],
        primary_action_label: __('Import'),
        primary_action: function (values) {
            const from_table = (values.codes_table || [])
                .map(function (row) {
                    return (row.unlocode || '').trim().toUpperCase();
                })
                .filter(Boolean);
            const paste = (values.paste_codes || '')
                .split(/[\n,\t;]+/)
                .map(function (s) {
                    return s.trim().toUpperCase();
                })
                .filter(Boolean);
            const seen = {};
            const merged = [];
            from_table.concat(paste).forEach(function (c) {
                if (c && !seen[c]) {
                    seen[c] = 1;
                    merged.push(c);
                }
            });
            if (!merged.length) {
                frappe.msgprint({
                    title: __('No codes'),
                    message: __('Enter at least one UNLOCO code in the table or paste field.'),
                    indicator: 'orange',
                });
                return;
            }
            frappe.call({
                method: 'logistics.logistics.doctype.unloco.unloco.import_unloco_codes',
                args: { codes: merged },
                freeze: true,
                freeze_message: __('Creating UNLOCO records...'),
                callback: function (r) {
                    if (r.exc) {
                        frappe.msgprint({
                            title: __('Error'),
                            indicator: 'red',
                            message: r.exc,
                        });
                        return;
                    }
                    d.hide();
                    const res = r.message || {};
                    const created = res.created || [];
                    const skipped = res.skipped || [];
                    const errors = res.errors || [];
                    let html = '<p><strong>' + __('Created') + ':</strong> ' + created.length + '</p>';
                    html +=
                        '<p><strong>' + __('Skipped (already exist)') + ':</strong> ' + skipped.length + '</p>';
                    if (skipped.length) {
                        html +=
                            '<p class="text-muted">' + frappe.utils.escape_html(skipped.join(', ')) + '</p>';
                    }
                    if (errors.length) {
                        html += '<p><strong>' + __('Errors') + ':</strong></p><ul>';
                        errors.forEach(function (e) {
                            html +=
                                '<li>' +
                                frappe.utils.escape_html(e.code || '') +
                                ' — ' +
                                frappe.utils.escape_html(String(e.error || '')) +
                                '</li>';
                        });
                        html += '</ul>';
                    }
                    frappe.msgprint({
                        title: __('Import complete'),
                        indicator: errors.length ? 'orange' : 'green',
                        message: html,
                    });
                    listview.refresh();
                },
            });
        },
    });
    d.show();
}

function setup_unloco_list_actions(listview) {
    if (!listview.page) {
        return;
    }

    if (listview.can_create && !listview._unloco_import_action_setup) {
        listview._unloco_import_action_setup = true;
        const openImport = function () {
            show_unloco_import_dialog(listview);
        };
        if (typeof listview.page.add_action_item === 'function') {
            listview.page.add_action_item(__('Import UNLOCO'), openImport, false);
        }
        listview.page.add_inner_button(__('Import UNLOCO'), openImport);
    }

    var roles = (frappe.boot && frappe.boot.user && frappe.boot.user.roles) || frappe.user_roles || [];
    var is_system_manager = roles.indexOf('System Manager') !== -1;

    if (is_system_manager && listview.can_create && !listview._unloco_get_all_action_setup) {
        listview._unloco_get_all_action_setup = true;
        var runGetAll = function () {
            frappe.confirm(
                __(
                    'This queues a background job to create UNLOCO records for every location in the cached DataHub UN/LOCODE file. Existing codes are skipped. The job may run for a long time. Continue?'
                ),
                function () {
                    frappe.call({
                        method: 'logistics.logistics.doctype.unloco.unloco.start_get_all_unloco',
                        freeze: true,
                        freeze_message: __('Queueing job...'),
                        callback: function (r) {
                            if (!r.exc) {
                                frappe.show_alert({
                                    message: __(
                                        'Job queued. UNLOCO records are created in batches on the background worker. Refresh the list later.'
                                    ),
                                    indicator: 'green',
                                });
                            }
                            listview.refresh();
                        },
                    });
                }
            );
        };
        if (typeof listview.page.add_action_item === 'function') {
            listview.page.add_action_item(__('Get All UNLOCO'), runGetAll, false);
        }
        listview.page.add_inner_button(__('Get All UNLOCO'), runGetAll);
    }
}

frappe.listview_settings['UNLOCO'] = {
    onload: function (listview) {
        setup_unloco_list_actions(listview);
    },
    refresh: function (listview) {
        setup_unloco_list_actions(listview);
    },
};
