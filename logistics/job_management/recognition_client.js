/**
 * Client-side integration for Revenue and Cost Recognition
 * 
 * This script adds recognition buttons and actions to job documents.
 */

frappe.provide("logistics.recognition");

logistics.recognition = {
    row_charge_disbursement: function(r) {
        return (r.charge_type || '').toLowerCase() === 'disbursement';
    },
    row_wip_amount: function(r) {
        return (
            flt(r.estimated_revenue) ||
            flt(r.base_amount) ||
            flt(r.actual_revenue) ||
            flt(r.amount) ||
            flt(r.total) ||
            0
        );
    },
    row_accrual_cost: function(r) {
        return (
            flt(r.estimated_cost) ||
            flt(r.cost_base_amount) ||
            flt(r.actual_cost) ||
            flt(r.cost) ||
            0
        );
    },
    needs_wip_recognition: function(doc) {
        var rows = doc.charges || [];
        var eligible = false;
        for (var i = 0; i < rows.length; i++) {
            var r = rows[i];
            if (logistics.recognition.row_charge_disbursement(r)) {
                continue;
            }
            var er = logistics.recognition.row_wip_amount(r);
            if (er <= 0) {
                continue;
            }
            eligible = true;
            if (!r.wip_recognition_journal_entry) {
                return true;
            }
        }
        if (eligible) {
            return false;
        }
        return flt(doc.estimated_revenue) > flt(doc.wip_amount);
    },
    needs_accrual_recognition: function(doc) {
        var rows = doc.charges || [];
        var eligible = false;
        for (var k = 0; k < rows.length; k++) {
            var row = rows[k];
            if (logistics.recognition.row_charge_disbursement(row)) {
                continue;
            }
            var c = logistics.recognition.row_accrual_cost(row);
            if (c <= 0) {
                continue;
            }
            eligible = true;
            if (!row.accrual_recognition_journal_entry) {
                return true;
            }
        }
        if (eligible) {
            return false;
        }
        return flt(doc.estimated_costs) > flt(doc.accrual_amount);
    },
    /**
     * Setup recognition buttons on a job form
     * @param {Object} frm - The form object
     */
    setup_form: function(frm) {
        // Show recognition buttons for both draft and submitted documents
        // Post > Recognize: charge-line JE links + open balances vs job estimates (no header JE checks)
        var needs_wip = logistics.recognition.needs_wip_recognition(frm.doc);
        var needs_accrual = logistics.recognition.needs_accrual_recognition(frm.doc);
        if (needs_wip || needs_accrual) {
            frm.add_custom_button(__('Recognize WIP & Accrual'), function() {
                logistics.recognition.recognize(frm);
            }, __('Post'));
        }
        
        // Add WIP Recognition button (individual)
        if (needs_wip) {
            frm.add_custom_button(__('Recognize WIP'), function() {
                logistics.recognition.recognize_wip(frm);
            }, __('Recognition'));
        }
        
        // Add Accrual Recognition button (individual)
        if (needs_accrual) {
            frm.add_custom_button(__('Recognize Accruals'), function() {
                logistics.recognition.recognize_accruals(frm);
            }, __('Recognition'));
        }
        
        // Add WIP Adjustment button if there is open WIP balance
        if (frm.doc.wip_amount > 0) {
            frm.add_custom_button(__('Adjust WIP'), function() {
                logistics.recognition.adjust_wip(frm);
            }, __('Recognition'));
        }
        
        // Add Accrual Adjustment button if there is open accrual balance
        if (frm.doc.accrual_amount > 0) {
            frm.add_custom_button(__('Adjust Accruals'), function() {
                logistics.recognition.adjust_accruals(frm);
            }, __('Recognition'));
        }
        
        // Add Close Recognition button if there are open WIP or accruals
        if (frm.doc.wip_amount > 0 || frm.doc.accrual_amount > 0) {
            frm.add_custom_button(__('Close Recognition'), function() {
                logistics.recognition.close_recognition(frm);
            }, __('Recognition'));
        }
    },
    
    /**
     * Recognize WIP for a job
     */
    recognize_wip: function(frm) {
        frappe.prompt([
            {
                fieldname: 'recognition_date',
                fieldtype: 'Date',
                label: __('Recognition Date'),
                default: frappe.datetime.get_today(),
                reqd: 1
            }
        ], function(values) {
            frappe.call({
                method: 'logistics.job_management.recognition_engine.recognize_wip',
                args: {
                    doctype: frm.doc.doctype,
                    docname: frm.doc.name,
                    recognition_date: values.recognition_date
                },
                freeze: true,
                freeze_message: __('Creating WIP Recognition...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('WIP Recognition created: {0}', [r.message]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }, __('Recognize WIP'), __('Create'));
    },
    
    /**
     * Recognize Accruals for a job
     */
    recognize_accruals: function(frm) {
        frappe.prompt([
            {
                fieldname: 'recognition_date',
                fieldtype: 'Date',
                label: __('Recognition Date'),
                default: frappe.datetime.get_today(),
                reqd: 1
            }
        ], function(values) {
            frappe.call({
                method: 'logistics.job_management.recognition_engine.recognize_accruals',
                args: {
                    doctype: frm.doc.doctype,
                    docname: frm.doc.name,
                    recognition_date: values.recognition_date
                },
                freeze: true,
                freeze_message: __('Creating Accrual Recognition...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Accrual Recognition created: {0}', [r.message]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }, __('Recognize Accruals'), __('Create'));
    },
    
    /**
     * Adjust WIP for a job
     */
    adjust_wip: function(frm) {
        frappe.prompt([
            {
                fieldname: 'adjustment_amount',
                fieldtype: 'Currency',
                label: __('Adjustment Amount'),
                description: __('Current WIP: {0}', [frm.doc.wip_amount]),
                reqd: 1
            },
            {
                fieldname: 'adjustment_date',
                fieldtype: 'Date',
                label: __('Adjustment Date'),
                default: frappe.datetime.get_today(),
                reqd: 1
            }
        ], function(values) {
            frappe.call({
                method: 'logistics.job_management.recognition_engine.adjust_wip',
                args: {
                    doctype: frm.doc.doctype,
                    docname: frm.doc.name,
                    adjustment_amount: values.adjustment_amount,
                    adjustment_date: values.adjustment_date
                },
                freeze: true,
                freeze_message: __('Creating WIP Adjustment...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('WIP Adjustment created: {0}', [r.message]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }, __('Adjust WIP'), __('Create'));
    },
    
    /**
     * Adjust Accruals for a job
     */
    adjust_accruals: function(frm) {
        frappe.prompt([
            {
                fieldname: 'adjustment_amount',
                fieldtype: 'Currency',
                label: __('Adjustment Amount'),
                description: __('Current Accrual: {0}', [frm.doc.accrual_amount]),
                reqd: 1
            },
            {
                fieldname: 'adjustment_date',
                fieldtype: 'Date',
                label: __('Adjustment Date'),
                default: frappe.datetime.get_today(),
                reqd: 1
            }
        ], function(values) {
            frappe.call({
                method: 'logistics.job_management.recognition_engine.adjust_accruals',
                args: {
                    doctype: frm.doc.doctype,
                    docname: frm.doc.name,
                    adjustment_amount: values.adjustment_amount,
                    adjustment_date: values.adjustment_date
                },
                freeze: true,
                freeze_message: __('Creating Accrual Adjustment...'),
                callback: function(r) {
                    if (r.message) {
                        frappe.show_alert({
                            message: __('Accrual Adjustment created: {0}', [r.message]),
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    }
                }
            });
        }, __('Adjust Accruals'), __('Create'));
    },
    
    /**
     * Recognize WIP and accruals (manual action - both in one call)
     */
    recognize: function(frm) {
        frappe.call({
            method: 'logistics.job_management.recognition_engine.recognize',
            args: {
                doctype: frm.doc.doctype,
                docname: frm.doc.name
            },
            freeze: true,
            freeze_message: __('Recognizing WIP and Accruals...'),
            callback: function(r) {
                if (r.message) {
                    var msg = [];
                    if (r.message.wip_journal_entry) {
                        msg.push(__('WIP: {0}', [r.message.wip_journal_entry]));
                    }
                    if (r.message.accrual_journal_entry) {
                        msg.push(__('Accruals: {0}', [r.message.accrual_journal_entry]));
                    }
                    if (msg.length) {
                        frappe.show_alert({
                            message: msg.join(' | '),
                            indicator: 'green'
                        });
                    } else {
                        var reason = r.message.message || __('Nothing to recognize (already recognized or below minimum)');
                        frappe.msgprint({ title: __('Recognition'), message: reason, indicator: 'blue' });
                    }
                    frm.reload_doc();
                }
            }
        });
    },
    
    /**
     * Close all recognition for a job
     */
    close_recognition: function(frm) {
        frappe.confirm(
            __('This will close all remaining WIP and Accruals. Continue?'),
            function() {
                frappe.prompt([
                    {
                        fieldname: 'closure_date',
                        fieldtype: 'Date',
                        label: __('Closure Date'),
                        default: frappe.datetime.get_today(),
                        reqd: 1
                    }
                ], function(values) {
                    frappe.call({
                        method: 'logistics.job_management.recognition_engine.close_job_recognition',
                        args: {
                            doctype: frm.doc.doctype,
                            docname: frm.doc.name,
                            closure_date: values.closure_date
                        },
                        freeze: true,
                        freeze_message: __('Closing Recognition...'),
                        callback: function(r) {
                            if (r.message) {
                                let msg = [];
                                if (r.message.wip_journal_entry) {
                                    msg.push(__('WIP closed: {0}', [r.message.wip_journal_entry]));
                                }
                                if (r.message.accrual_journal_entry) {
                                    msg.push(__('Accrual closed: {0}', [r.message.accrual_journal_entry]));
                                }
                                if (msg.length) {
                                    frappe.show_alert({
                                        message: msg.join('<br>'),
                                        indicator: 'green'
                                    });
                                }
                                frm.reload_doc();
                            }
                        }
                    });
                }, __('Close Recognition'), __('Close'));
            }
        );
    }
};

// Register form refresh for job doctypes
// Transport Job adds the same actions in transport_job.js (deferred with Create/Post menu); skip here to avoid duplicates.
frappe.ui.form.on([
    'Air Shipment', 'Sea Shipment',
    'Warehouse Job', 'Declaration', 'General Job'
], {
    refresh: function(frm) {
        if (typeof logistics !== 'undefined' && logistics.recognition) {
            logistics.recognition.setup_form(frm);
        }
    }
});
