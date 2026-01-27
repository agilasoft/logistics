/**
 * Client-side integration for Revenue and Cost Recognition
 * 
 * This script adds recognition buttons and actions to job documents.
 */

frappe.provide("logistics.recognition");

logistics.recognition = {
    /**
     * Setup recognition buttons on a job form
     * @param {Object} frm - The form object
     */
    setup_form: function(frm) {
        if (frm.doc.docstatus !== 1) return;
        
        // Add WIP Recognition button
        if (!frm.doc.wip_journal_entry && !frm.doc.wip_closed) {
            frm.add_custom_button(__('Recognize WIP'), function() {
                logistics.recognition.recognize_wip(frm);
            }, __('Recognition'));
        }
        
        // Add Accrual Recognition button
        if (!frm.doc.accrual_journal_entry && !frm.doc.accrual_closed) {
            frm.add_custom_button(__('Recognize Accruals'), function() {
                logistics.recognition.recognize_accruals(frm);
            }, __('Recognition'));
        }
        
        // Add WIP Adjustment button if WIP is recognized
        if (frm.doc.wip_journal_entry && frm.doc.wip_amount > 0 && !frm.doc.wip_closed) {
            frm.add_custom_button(__('Adjust WIP'), function() {
                logistics.recognition.adjust_wip(frm);
            }, __('Recognition'));
        }
        
        // Add Accrual Adjustment button if accrual is recognized
        if (frm.doc.accrual_journal_entry && frm.doc.accrual_amount > 0 && !frm.doc.accrual_closed) {
            frm.add_custom_button(__('Adjust Accruals'), function() {
                logistics.recognition.adjust_accruals(frm);
            }, __('Recognition'));
        }
        
        // Add Close Recognition button if there are open WIP or accruals
        if ((frm.doc.wip_amount > 0 && !frm.doc.wip_closed) || 
            (frm.doc.accrual_amount > 0 && !frm.doc.accrual_closed)) {
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
