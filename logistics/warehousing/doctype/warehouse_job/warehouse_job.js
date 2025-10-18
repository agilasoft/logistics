// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on('Warehouse Job', {
    onload: function(frm) {
        // Load dashboard HTML when document is loaded
        if (frm.doc.name) {
            // Check if this is an unsaved job
            if (frm.doc.name.startsWith('new-warehouse-job-') || (frm.doc.name.startsWith('WRO') && frm.doc.name.length > 10)) {
                const $wrapper = frm.get_field('warehouse_job_html').$wrapper;
                if ($wrapper) {
                    $wrapper.html(`
                        <div style="padding: 24px; text-align: center; color: #64748b; background: #fef3c7; border-radius: 8px; border: 1px solid #fbbf24;">
                            <h3 style="color: #d97706; margin: 0 0 8px 0; font-size: 18px; font-weight: 600;">Save Required</h3>
                            <p style="margin: 0 0 16px 0; font-size: 14px; line-height: 1.5;">This warehouse job has not been saved yet. Please save the job first to load the dashboard.</p>
                            <div style="background: #fef3c7; padding: 12px; border-radius: 6px; border-left: 3px solid #f59e0b;">
                                <p style="margin: 0; font-size: 13px; color: #92400e; font-weight: 500;">Click the "Save" button to save your changes and then refresh the dashboard.</p>
                            </div>
                        </div>
                    `);
                }
                return;
            }
            
            frappe.call({
                method: 'logistics.warehousing.doctype.warehouse_job.warehouse_job.get_warehouse_dashboard_html',
                args: {
                    job_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message) {
                        try {
                            // Use the same pattern as run_sheet - get field wrapper and set HTML directly
                            const $wrapper = frm.get_field('warehouse_job_html').$wrapper;
                            if ($wrapper) {
                                $wrapper.html(r.message);
                                
                                // Force a small delay to ensure rendering
                                setTimeout(function() {
                                    $wrapper.find('.handling-unit-card').each(function() {
                                        // Cards loaded successfully
                                    });
                                }, 100);
                            } else {
                                frm.doc.warehouse_job_html = r.message;
                                frm.refresh_field('warehouse_job_html');
                            }
                        } catch (error) {
                            console.error('Error setting dashboard HTML:', error);
                            // Show user-friendly error message
                            frappe.msgprint({
                                title: __('Dashboard Error'),
                                message: __('Failed to load warehouse dashboard. Please refresh the page.'),
                                indicator: 'orange'
                            });
                        }
                    } else {
                        // Show user-friendly error message
                        frappe.msgprint({
                            title: __('Dashboard Error'),
                            message: __('Failed to load warehouse dashboard data. Please refresh the page.'),
                            indicator: 'orange'
                        });
                    }
                },
                error: function(r) {
                    
                    // Handle different types of errors
                    let errorMessage = __('Failed to load warehouse dashboard.');
                    let errorTitle = __('Dashboard Error');
                    
                    if (r && r.status === 502) {
                        errorTitle = __('Server Error (502)');
                        errorMessage = __('The server is temporarily unavailable. Please try again in a few moments.');
                    } else if (r && r.status === 500) {
                        errorTitle = __('Server Error (500)');
                        errorMessage = __('An internal server error occurred. Please contact support if this persists.');
                    } else if (r && r.status === 404) {
                        errorTitle = __('Not Found (404)');
                        errorMessage = __('The warehouse job was not found. Please refresh the page.');
                    } else if (r && r.status === 403) {
                        errorTitle = __('Access Denied (403)');
                        errorMessage = __('You do not have permission to view this dashboard.');
                    }
                    
                    // Show error message to user
                    frappe.msgprint({
                        title: errorTitle,
                        message: `
                            <div style="padding: 15px; font-size: 14px;">
                                <p style="text-align: center; margin-bottom: 15px;">${errorMessage}</p>
                                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">
                                    <p style="margin: 5px 0;"><strong>Troubleshooting:</strong></p>
                                    <ul style="margin: 5px 0; padding-left: 20px;">
                                        <li>Try refreshing the page</li>
                                        <li>Check if the warehouse job exists</li>
                                        <li>Contact support if the problem persists</li>
                                    </ul>
                                </div>
                            </div>
                        `,
                        indicator: 'red'
                    });
                }
            });
        }
        
        // Add gate pass methods to the form
        frm.create_gate_pass_for_dock = function(dockRow) {
            // Create gate pass for a specific dock entry
            frappe.call({
                method: 'logistics.warehousing.doctype.gate_pass.gate_pass.create_gate_pass_for_docking',
                args: {
                    warehouse_job: frm.doc.name,
                    dock_name: dockRow.name
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.msgprint(__('Created Gate Pass: {0}', [r.message]));
                        frm.reload_doc();
                    }
                },
                freeze: true,
                freeze_message: __('Creating Gate Pass...')
            });
        };

        frm.create_gate_passes_for_all_docks = function() {
            // Create gate passes for all docking entries
            frappe.confirm(
                __('Create Gate Passes for all {0} docking entries?', [frm.doc.docks.length]),
                function() {
                    frappe.call({
                        method: 'logistics.warehousing.doctype.gate_pass.gate_pass.create_gate_pass_for_docking',
                        args: {
                            warehouse_job: frm.doc.name
                        },
                        callback: function(r) {
                            if (r.message) {
                                const gatePasses = Array.isArray(r.message) ? r.message : [r.message];
                                frappe.msgprint(__('Created {0} Gate Pass{1}: {2}', [
                                    gatePasses.length,
                                    gatePasses.length > 1 ? 'es' : '',
                                    gatePasses.join(', ')
                                ]));
                                frm.reload_doc();
                            }
                        },
                        freeze: true,
                        freeze_message: __('Creating Gate Passes...')
                    });
                }
            );
        };

        frm.view_related_gate_passes = function() {
            // View gate passes related to this warehouse job
            frappe.route_options = {
                warehouse_job: frm.doc.name
            };
            frappe.set_route('List', 'Gate Pass');
        };
    },
    refresh: function(frm) {
        calculate_job_totals(frm);
        update_uom_fields_for_items(frm);
        
        // Add Allocate button if job is not completed (exclude Stocktake jobs)
        if (frm.doc.docstatus === 0 && frm.doc.status !== 'Completed' && frm.doc.type !== 'Stocktake') {
            // Determine button text based on job type
            let button_text = 'Allocate';
            if (frm.doc.type === 'Pick') {
                button_text = 'Allocate Pick';
            } else if (frm.doc.type === 'Putaway') {
                button_text = 'Allocate Putaway';
            } else if (frm.doc.type === 'Move') {
                button_text = 'Allocate Move';
            } else if (frm.doc.type === 'VAS') {
                button_text = 'Allocate VAS';
            }
            
            frm.add_custom_button(__(button_text), function() {
                allocate_items(frm);
            }, __('Actions'));
        }
        
        // Add Create Operations button if items exist
        if (frm.doc.items && frm.doc.items.length > 0) {
            frm.add_custom_button(__('Create Operations'), function() {
                create_operations(frm);
            }, __('Actions'));
        }
        
        
        // Add Post Receiving button for Putaway jobs (only when submitted)
        if (frm.doc.type === 'Putaway' && frm.doc.docstatus === 1 && frm.doc.items && frm.doc.items.length > 0) {
            frm.add_custom_button(__('Post Receiving'), function() {
                post_receiving(frm);
            }, __('Post'));
        }
        
        // Add Post Putaway button for Putaway jobs (only when submitted)
        if (frm.doc.type === 'Putaway' && frm.doc.docstatus === 1 && frm.doc.items && frm.doc.items.length > 0) {
            frm.add_custom_button(__('Post Putaway'), function() {
                post_putaway(frm);
            }, __('Post'));
        }
        
        // Add Post Pick button for Pick jobs (only when submitted)
        if (frm.doc.type === 'Pick' && frm.doc.docstatus === 1 && frm.doc.items && frm.doc.items.length > 0) {
            frm.add_custom_button(__('Post Pick'), function() {
                post_pick(frm);
            }, __('Post'));
        }
        
        // Add Post Release button for Pick jobs (only when submitted)
        if (frm.doc.type === 'Pick' && frm.doc.docstatus === 1 && frm.doc.items && frm.doc.items.length > 0) {
            frm.add_custom_button(__('Post Release'), function() {
                post_release(frm);
            }, __('Post'));
        }
        
        // Add Fetch Count Sheet button for Stocktake jobs
        if (frm.doc.type === 'Stocktake' && frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Fetch Count Sheet'), function() {
                fetch_count_sheet(frm);
            }, __('Stocktake'));
        }
        
        // Add Populate Stocktake Adjustments button for Stocktake jobs
        if (frm.doc.type === 'Stocktake' && frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Populate Adjustments'), function() {
                populate_stocktake_adjustments(frm);
            }, __('Stocktake'));
        }
        
        // Add Post by Scan button for all job types (only when submitted)
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Post by Scan'), function() {
                post_by_scan(frm);
            }, __('Post'));
        }
        
        // Add Gate Pass creation buttons - show for submitted jobs
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Gate Passes'), function() {
                if (frm.doc.docks && frm.doc.docks.length > 0) {
                    frm.create_gate_passes_for_all_docks();
                } else {
                    frappe.msgprint(__('No docking entries found. Please add docking entries first.'));
                }
            }, __('Actions'));
            
            frm.add_custom_button(__('View Gate Passes'), function() {
                frm.view_related_gate_passes();
            }, __('Actions'));
        }
        
        // Add Calculate Charges button - show for jobs with contract and charges that have standard costs
        if ((frm.doc.warehouse_contract || frm.doc.customer) && frm.doc.charges && frm.doc.charges.length > 0) {
            // Check if any charge has standard cost
            let has_standard_cost = false;
            
            frm.doc.charges.forEach(function(charge) {
                if (charge.total_standard_cost && flt(charge.total_standard_cost) > 0) {
                    has_standard_cost = true;
                }
            });
            
            if (has_standard_cost) {
                frm.add_custom_button(__('Calculate Charges'), function() {
                    calculate_charges_from_contract(frm);
                }, __('Actions'));
            }
        }
        
        // Add Post Standard Costs button - show only when submitted and has charges with standard costs that haven't been posted
        if (frm.doc.docstatus === 1 && frm.doc.charges && frm.doc.charges.length > 0) {
            // Check if any charge has standard cost and hasn't been posted
            let has_unposted_standard_cost = false;
            
            frm.doc.charges.forEach(function(charge) {
                if (charge.total_standard_cost && flt(charge.total_standard_cost) > 0 && !charge.standard_cost_posted) {
                    has_unposted_standard_cost = true;
                }
            });
            
            if (has_unposted_standard_cost) {
                frm.add_custom_button(__('Post Standard Costs'), function() {
                    post_standard_costs(frm);
                }, __('Post'));
            }
        }
        
        
    },
    items: function(frm) {
        calculate_job_totals(frm);
    },
    volume_qty_type: function(frm) {
        calculate_job_totals(frm);
    },
    weight_qty_type: function(frm) {
        calculate_job_totals(frm);
    }
});

frappe.ui.form.on('Warehouse Job Item', {
    length: function(frm, cdt, cdn) {
        calculate_item_volume(frm, cdt, cdn);
        calculate_job_totals(frm);
    },
    width: function(frm, cdt, cdn) {
        calculate_item_volume(frm, cdt, cdn);
        calculate_job_totals(frm);
    },
    height: function(frm, cdt, cdn) {
        calculate_item_volume(frm, cdt, cdn);
        calculate_job_totals(frm);
    },
    volume: function(frm, cdt, cdn) {
        calculate_job_totals(frm);
    },
    weight: function(frm, cdt, cdn) {
        calculate_job_totals(frm);
    },
    items_remove: function(frm) {
        calculate_job_totals(frm);
    }
});

frappe.ui.form.on('Warehouse Job Order Items', {
    length: function(frm, cdt, cdn) {
        calculate_item_volume(frm, cdt, cdn);
        calculate_job_totals(frm);
    },
    width: function(frm, cdt, cdn) {
        calculate_item_volume(frm, cdt, cdn);
        calculate_job_totals(frm);
    },
    height: function(frm, cdt, cdn) {
        calculate_item_volume(frm, cdt, cdn);
        calculate_job_totals(frm);
    },
    volume: function(frm, cdt, cdn) {
        calculate_job_totals(frm);
    },
    weight: function(frm, cdt, cdn) {
        calculate_job_totals(frm);
    },
    orders_remove: function(frm) {
        calculate_job_totals(frm);
    }
});

function calculate_job_totals(frm) {
    if (!frm.doc.items) {
        frm.set_value('total_volume', 0);
        frm.set_value('total_weight', 0);
        frm.set_value('total_handling_units', 0);
        return;
    }
    
    let total_volume = 0;
    let total_weight = 0;
    let total_handling_units = 0;
    let unique_handling_units = new Set();
    
    frm.doc.items.forEach(function(item) {
        // Calculate volume if dimensions are available
        let item_volume = 0;
        if (item.length && item.width && item.height) {
            item_volume = flt(item.length) * flt(item.width) * flt(item.height);
        } else if (item.volume) {
            item_volume = flt(item.volume);
        }
        
        // Add volume based on volume_qty_type setting
        if (frm.doc.volume_qty_type === 'Total') {
            // Volume is total for the entire quantity, not per unit
            total_volume += item_volume;
        } else {
            // Volume is per unit, so multiply by quantity
            total_volume += item_volume * flt(item.quantity || 0);
        }
        
        // Add weight based on weight_qty_type setting
        if (item.weight) {
            if (frm.doc.weight_qty_type === 'Per Unit') {
                // Weight is per unit, so multiply by quantity
                total_weight += flt(item.weight) * flt(item.quantity || 0);
            } else {
                // Weight is total for the entire quantity, not per unit
                total_weight += flt(item.weight);
            }
        }
        
        // Count unique handling units
        if (item.handling_unit) {
            unique_handling_units.add(item.handling_unit);
        }
    });
    
    total_handling_units = unique_handling_units.size;
    
    frm.set_value('total_volume', total_volume);
    frm.set_value('total_weight', total_weight);
    frm.set_value('total_handling_units', total_handling_units);
}

function calculate_item_volume(frm, cdt, cdn) {
    // Get the current item row
    const item = locals[cdt][cdn];
    if (!item) return;
    
    // Get dimension values
    const length = flt(item.length || 0);
    const width = flt(item.width || 0);
    const height = flt(item.height || 0);
    
    // Calculate volume if all dimensions are provided
    if (length > 0 && width > 0 && height > 0) {
        const volume = length * width * height;
        frappe.model.set_value(cdt, cdn, "volume", volume);
    } else {
        // Clear volume if dimensions are incomplete
        frappe.model.set_value(cdt, cdn, "volume", 0);
    }
}

// Allocation functions
function allocate_items(frm) {
    // Check if there are orders to allocate from
    if (!frm.doc.orders || frm.doc.orders.length === 0) {
        frappe.msgprint({
            title: __('No Orders Found'),
            message: `
                <div style="padding: 10px; font-size: 14px;">
                    <p><strong>Orders Required</strong></p>
                    <p>Please add orders to the job before allocating.</p>
                </div>
            `,
            indicator: 'orange'
        });
        return;
    }
    
    if (!frm.doc.staging_area) {
        frappe.msgprint({
            title: __('Staging Area Required'),
            message: `
                <div style="padding: 10px; font-size: 14px;">
                    <p><strong>Staging Area Missing</strong></p>
                    <p>Please select a staging area before allocating items.</p>
                </div>
            `,
            indicator: 'orange'
        });
        return;
    }
    
    // Determine confirmation message based on job type
    let confirm_message = __('This will allocate all items to the staging area. Continue?');
    if (frm.doc.type === 'Pick') {
        confirm_message = __('This will allocate pick lines from orders. Continue?');
    } else if (frm.doc.type === 'Putaway') {
        confirm_message = __('This will allocate putaway tasks from orders. Continue?');
    } else if (frm.doc.type === 'Move') {
        confirm_message = __('This will allocate move tasks from orders. Continue?');
    } else if (frm.doc.type === 'VAS') {
        confirm_message = __('This will allocate VAS putaway tasks from orders. Continue?');
    }
    
    frappe.confirm(
        confirm_message,
        function() {
            frappe.call({
                method: 'logistics.warehousing.doctype.warehouse_job.warehouse_job.allocate_items',
                args: {
                    job_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        let message = r.message.message || __('Items allocated successfully.');
                        let allocated_count = r.message.allocated_count || 0;
                        let allocated_qty = r.message.allocated_qty || 0;
                        
                        let html_message = `
                            <div style="padding: 15px; font-size: 14px;">
                                <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                    <strong>Allocation Successful!</strong>
                                </p>
                                <p style="text-align: center; margin-bottom: 15px;">${message}</p>
                                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">
                                    <p style="margin: 5px 0;"><strong>Results:</strong></p>
                                    <p style="margin: 5px 0;">• Items Allocated: <strong>${allocated_count}</strong></p>
                                    <p style="margin: 5px 0;">• Quantity: <strong>${allocated_qty}</strong></p>
                                </div>
                        `;
                        
                        // Show warnings if any
                        if (r.message.warnings && r.message.warnings.length > 0) {
                            html_message += `
                                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin: 10px 0;">
                                    <p style="margin: 5px 0; color: #856404;"><strong>Warnings:</strong></p>
                                    <ul style="margin: 5px 0; color: #856404;">
                                        ${r.message.warnings.map(warning => `<li>${warning}</li>`).join('')}
                                    </ul>
                                </div>
                            `;
                        }
                        
                        html_message += `</div>`;
                        
                        frappe.msgprint({
                            title: __('Allocation Complete'),
                            message: html_message,
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        let error_message = r.message.error || __('Failed to allocate items.');
                        
                        let html_message = `
                            <div style="padding: 15px; font-size: 14px;">
                                <p style="text-align: center; font-size: 18px; color: #dc3545; margin-bottom: 10px;">
                                    <strong>Allocation Failed</strong>
                                </p>
                                <p style="text-align: center; margin-bottom: 15px;">${error_message}</p>
                        `;
                        
                        // Show warnings even on failure
                        if (r.message.warnings && r.message.warnings.length > 0) {
                            html_message += `
                                <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin: 10px 0;">
                                    <p style="margin: 5px 0; color: #856404;"><strong>Warnings:</strong></p>
                                    <ul style="margin: 5px 0; color: #856404;">
                                        ${r.message.warnings.map(warning => `<li>${warning}</li>`).join('')}
                                    </ul>
                                </div>
                            `;
                        }
                        
                        html_message += `</div>`;
                        
                        frappe.msgprint({
                            title: __('Allocation Error'),
                            message: html_message,
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}



// Create Operations function
function create_operations(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.msgprint({
            title: __('No Items Found'),
            message: `
                <div style="padding: 10px; font-size: 14px;">
                    <p><strong>Items Required</strong></p>
                    <p>Please add items to the job before creating operations.</p>
                </div>
            `,
            indicator: 'orange'
        });
        return;
    }
    
    frappe.confirm(
        __('This will create operations from operation templates. Continue?'),
        function() {
            frappe.call({
                method: 'logistics.warehousing.doctype.warehouse_job.warehouse_job.create_operations',
                args: {
                    job_name: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        let created_count = r.message.created_count || 0;
                        
                        frappe.msgprint({
                            title: __('Create Operations'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                        <strong>Operations Created!</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">Operations created successfully from operation templates.</p>
                                    <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">
                                        <p style="margin: 5px 0;"><strong>Results:</strong></p>
                                        <p style="margin: 5px 0;">• Operations Created: <strong>${created_count}</strong></p>
                                    </div>
                                </div>
                            `,
                            indicator: 'green'
                        });
                        frm.reload_doc();
            } else {
                        frappe.msgprint({
                            title: __('Create Operations Error'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <p style="text-align: center; font-size: 18px; color: #dc3545; margin-bottom: 10px;">
                                        <strong>Create Failed</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.error || __('Failed to create operations.')}</p>
                                </div>
                            `,
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}// Additional Warehouse Job Functions

// Post Receiving function
function post_receiving(frm) {
    frappe.confirm(
        __('This will post receiving transactions. Continue?'),
        function() {
            frappe.call({
                method: 'logistics.warehousing.api.post_receiving',
                args: {
                    warehouse_job: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.ok) {
                        frappe.msgprint({
                            title: __('Post Receiving'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                        <strong>Receiving Posted!</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.message || 'Receiving transactions posted successfully.'}</p>
                                </div>
                            `,
                            indicator: 'green'
                        });
                        frm.reload_doc();
          } else {
                        frappe.msgprint({
                            title: __('Post Receiving Error'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <p style="text-align: center; font-size: 18px; color: #dc3545; margin-bottom: 10px;">
                                        <strong>Post Failed</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.error || __('Failed to post receiving.')}</p>
                                </div>
                            `,
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

// Post Putaway function
function post_putaway(frm) {
    frappe.confirm(
        __('This will post putaway transactions. Continue?'),
        function() {
            frappe.call({
                method: 'logistics.warehousing.api.post_putaway',
                args: {
                    warehouse_job: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.ok) {
                        frappe.msgprint({
                            title: __('Post Putaway'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                        <strong>Putaway Posted!</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.message || 'Putaway transactions posted successfully.'}</p>
                                </div>
                            `,
                            indicator: 'green'
                        });
                        frm.reload_doc();
      } else {
                        frappe.msgprint({
                            title: __('Post Putaway Error'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <p style="text-align: center; font-size: 18px; color: #dc3545; margin-bottom: 10px;">
                                        <strong>Post Failed</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.error || __('Failed to post putaway.')}</p>
                                </div>
                            `,
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

// Post Pick function
function post_pick(frm) {
    frappe.confirm(
        __('This will post pick transactions. Continue?'),
        function() {
    frappe.call({
                method: 'logistics.warehousing.api.post_pick',
                args: {
                    warehouse_job: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.ok) {
                        frappe.msgprint({
                            title: __('✅ Post Pick'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <div style="text-align: center; margin-bottom: 15px;">
                                        <span style="font-size: 48px;">📦</span>
                                    </div>
                                    <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                        <strong>✅ Pick Posted!</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.message || 'Pick transactions posted successfully.'}</p>
                                </div>
                            `,
                            indicator: 'green'
                        });
                        frm.reload_doc();
        } else {
                        frappe.msgprint({
                            title: __('❌ Post Pick Error'),
                            message: r.message.error || __('Failed to post pick.'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

// Post Release function
function post_release(frm) {
          frappe.confirm(
        __('This will post release transactions. Continue?'),
            function() {
            frappe.call({
                method: 'logistics.warehousing.api.post_release',
                args: {
                    warehouse_job: frm.doc.name
                },
                callback: function(r) {
                    if (r.message && r.message.ok) {
                        frappe.msgprint({
                            title: __('✅ Post Release'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <div style="text-align: center; margin-bottom: 15px;">
                                        <span style="font-size: 48px;">📦</span>
                                    </div>
                                    <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                        <strong>✅ Release Posted!</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.message || 'Release transactions posted successfully.'}</p>
                                </div>
                            `,
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('❌ Post Release Error'),
                            message: r.message.error || __('Failed to post release.'),
                            indicator: 'red'
                        });
                    }
                }
              });
            }
          );
}

// Fetch Count Sheet function
function fetch_count_sheet(frm) {
    frappe.confirm(
        __('This will fetch count sheet for stocktake. Continue?'),
        function() {
            frappe.call({
                method: 'logistics.warehousing.api.warehouse_job_fetch_count_sheet',
                args: {
                    warehouse_job: frm.doc.name,
                    clear_existing: 1
                },
                callback: function(r) {
                    if (r.message && r.message.ok) {
                        frappe.msgprint({
                            title: __('📊 Fetch Count Sheet'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <div style="text-align: center; margin-bottom: 15px;">
                                        <span style="font-size: 48px;">📊</span>
                                    </div>
                                    <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                        <strong>✅ Count Sheet Fetched!</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.message || 'Count sheet fetched successfully.'}</p>
                                </div>
                            `,
                            indicator: 'green'
                        });
                        frm.reload_doc();
        } else {
                        frappe.msgprint({
                            title: __('❌ Fetch Count Sheet Error'),
                            message: r.message.error || __('Failed to fetch count sheet.'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

// Populate Stocktake Adjustments function
function populate_stocktake_adjustments(frm) {
    frappe.confirm(
        __('This will populate stocktake adjustments. Continue?'),
        function() {
      frappe.call({
                method: 'logistics.warehousing.api.populate_stocktake_adjustments',
        args: {
          warehouse_job: frm.doc.name,
                    clear_existing: 1
        },
        callback: function(r) {
                    if (r.message && r.message.ok) {
                        frappe.msgprint({
                            title: __('📊 Populate Adjustments'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <div style="text-align: center; margin-bottom: 15px;">
                                        <span style="font-size: 48px;">📊</span>
                                    </div>
                                    <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                        <strong>✅ Adjustments Populated!</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.message || 'Stocktake adjustments populated successfully.'}</p>
                                </div>
                            `,
                            indicator: 'green'
                        });
            frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('❌ Populate Adjustments Error'),
                            message: r.message.error || __('Failed to populate adjustments.'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}



// Post by Scan function
function post_by_scan(frm) {
      frappe.confirm(
        __('This will open the Post by Scan interface. Continue?'),
        function() {
            // Open the warehouse job scanner page
            frappe.set_route('warehouse-job-scanner', frm.doc.name);
        }
    );
}

// Update UOM fields for child table items
function update_uom_fields_for_items(frm) {
    // Get UOM values from Warehouse Settings
    const company = frappe.defaults.get_user_default("Company");
    
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Warehouse Settings",
            name: company,
            fieldname: ["default_volume_uom", "default_weight_uom"]
        },
        callback: function(r) {
            if (r.message) {
                const volume_uom = r.message.default_volume_uom;
                const weight_uom = r.message.default_weight_uom;
                
                // Update UOM fields for all items in the child table
                if (frm.doc.items && frm.doc.items.length > 0) {
                    frm.doc.items.forEach(function(item, index) {
                        if (volume_uom) {
                            frappe.model.set_value("Warehouse Job Item", item.name, "volume_uom", volume_uom);
                        }
                        if (weight_uom) {
                            frappe.model.set_value("Warehouse Job Item", item.name, "weight_uom", weight_uom);
                        }
                    });
                    frm.refresh_field("items");
                }
            }
        }
    });
}

// Calculate Charges from Contract function
function calculate_charges_from_contract(frm) {
    if (!frm.doc.warehouse_contract && !frm.doc.customer) {
        frappe.msgprint(__('Please select a warehouse contract or customer first.'));
        return;
    }
    
    if (!frm.doc.charges || frm.doc.charges.length === 0) {
        frappe.msgprint(__('No charges found. Please add charges first.'));
        return;
    }
    
    frappe.confirm(
        __('This will recalculate quantities and rates based on the warehouse contract. Continue?'),
        function() {
            frappe.call({
                method: 'logistics.warehousing.doctype.warehouse_job.warehouse_job.calculate_charges_from_contract',
                args: {
                    warehouse_job: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Calculating charges...'),
                callback: function(r) {
                    if (r.message && r.message.ok) {
                        // Check if there are warnings
                        if (r.message.warnings && r.message.warnings.length > 0) {
                            frappe.msgprint({
                                title: __('Charges Calculated with Warnings'),
                                message: `
                                    <div style="padding: 15px; font-size: 14px;">
                                        <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                            <strong>✅ Charges Calculated!</strong>
                                        </p>
                                        <p style="text-align: center; margin-bottom: 15px;">${r.message.message}</p>
                                        <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin: 10px 0;">
                                            <p style="margin: 5px 0; color: #856404;"><strong>⚠️ Standard Cost Warnings:</strong></p>
                                            <ul style="margin: 5px 0; color: #856404;">
                                                ${r.message.warnings.map(warning => `<li>${warning}</li>`).join('')}
                                            </ul>
                                        </div>
                                    </div>
                                `,
                                indicator: 'orange'
                            });
                        } else {
                            frappe.msgprint({
                                title: __('Charges Calculated'),
                                message: r.message.message,
                                indicator: 'green'
                            });
                        }
                        frm.refresh_field('charges');
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message ? r.message.message : __('Failed to calculate charges'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

// Post Standard Costs function
function post_standard_costs(frm) {
    if (!frm.doc.charges || frm.doc.charges.length === 0) {
        frappe.msgprint(__('No charges found. Please add charges first.'));
        return;
    }
    
    // Check if any charge has standard cost and hasn't been posted
    let has_unposted_standard_cost = false;
    let already_posted_charges = [];
    
    frm.doc.charges.forEach(function(charge) {
        if (charge.total_standard_cost && flt(charge.total_standard_cost) > 0) {
            if (charge.standard_cost_posted) {
                already_posted_charges.push(charge.item_code || charge.item || 'Unknown');
            } else {
                has_unposted_standard_cost = true;
            }
        }
    });
    
    if (!has_unposted_standard_cost) {
        if (already_posted_charges.length > 0) {
            frappe.msgprint({
                title: __('Standard Costs Already Posted'),
                message: __('All charges with standard costs have already been posted. Posted charges: ') + already_posted_charges.join(', '),
                indicator: 'orange'
            });
        } else {
            frappe.msgprint(__('No standard costs found in charges.'));
        }
        return;
    }
    
    frappe.confirm(
        __('This will create journal entries for standard costs. Continue?'),
        function() {
            frappe.call({
                method: 'logistics.warehousing.doctype.warehouse_job.warehouse_job.post_standard_costs',
                args: {
                    warehouse_job: frm.doc.name
                },
                freeze: true,
                freeze_message: __('Creating journal entries for standard costs...'),
                callback: function(r) {
                    if (r.message && r.message.ok) {
                        frappe.msgprint({
                            title: __('Standard Costs Posted'),
                            message: `
                                <div style="padding: 15px; font-size: 14px;">
                                    <p style="text-align: center; font-size: 18px; color: #28a745; margin-bottom: 10px;">
                                        <strong>✅ Standard Costs Posted!</strong>
                                    </p>
                                    <p style="text-align: center; margin-bottom: 15px;">${r.message.message || 'Journal entries created successfully for standard costs.'}</p>
                                    <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0;">
                                        <p style="margin: 5px 0;"><strong>Journal Entry:</strong> ${r.message.journal_entry || 'N/A'}</p>
                                        <p style="margin: 5px 0;"><strong>Total Amount:</strong> ${r.message.total_amount || 'N/A'}</p>
                                        <p style="margin: 5px 0;"><strong>Charges Posted:</strong> ${r.message.charges_posted || 'N/A'}</p>
                                    </div>
                                </div>
                            `,
                            indicator: 'green'
                        });
                        frm.reload_doc();
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: r.message ? r.message.message : __('Failed to post standard costs'),
                            indicator: 'red'
                        });
                    }
                }
            });
        }
    );
}

