frappe.ui.form.on('Air Consolidation', {
    onload: function(frm) {
        // Apply settings defaults when creating new document
        if (frm.is_new()) {
            apply_settings_defaults(frm);
        }
    },
    
    refresh: function(frm) {
        // Add custom buttons
        add_consolidation_buttons(frm);
        
        // Update consolidation metrics
        update_consolidation_metrics(frm);
    },
    
    consolidation_type: function(frm) {
        // Update form based on consolidation type
        update_consolidation_type_fields(frm);
    },
    
    status: function(frm) {
        // Update status-dependent fields
        update_status_fields(frm);
    },
    
    departure_date: function(frm) {
        // Validate departure date
        validate_departure_date(frm);
    },
    
    arrival_date: function(frm) {
        // Validate arrival date
        validate_arrival_date(frm);
    }
});

// Air Consolidation Packages child table events
frappe.ui.form.on('Air Consolidation Packages', {
    package_weight: function(frm, cdt, cdn) {
        calculate_package_charges(frm, cdt, cdn);
        update_consolidation_totals(frm);
    },
    
    package_volume: function(frm, cdt, cdn) {
        calculate_volume_weight(frm, cdt, cdn);
        update_consolidation_totals(frm);
    },
    
    contains_dangerous_goods: function(frm, cdt, cdn) {
        validate_dangerous_goods(frm, cdt, cdn);
    }
});

// Air Consolidation Routes child table events
frappe.ui.form.on('Air Consolidation Routes', {
    route_sequence: function(frm, cdt, cdn) {
        validate_route_sequence(frm, cdt, cdn);
    },
    
    departure_date: function(frm, cdt, cdn) {
        calculate_transit_time(frm, cdt, cdn);
    },
    
    arrival_date: function(frm, cdt, cdn) {
        calculate_transit_time(frm, cdt, cdn);
    },
    
    cargo_capacity_kg: function(frm, cdt, cdn) {
        calculate_capacity_utilization(frm, cdt, cdn);
    },
    
    cargo_capacity_volume: function(frm, cdt, cdn) {
        calculate_capacity_utilization(frm, cdt, cdn);
    }
});

// Air Consolidation Charges child table events
frappe.ui.form.on('Air Consolidation Charges', {
    charge_basis: function(frm, cdt, cdn) {
        update_charge_calculation(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_charge_amount(frm, cdt, cdn);
    },
    
    quantity: function(frm, cdt, cdn) {
        calculate_charge_amount(frm, cdt, cdn);
    },
    
    discount_percentage: function(frm, cdt, cdn) {
        calculate_charge_amount(frm, cdt, cdn);
    }
});

// Air Consolidation Shipments child table events
frappe.ui.form.on('Air Consolidation Shipments', {
    consolidation_status: function(frm, cdt, cdn) {
        update_job_status_timestamps(frm, cdt, cdn);
    },
    
    air_freight_job: function(frm, cdt, cdn) {
        load_job_details(frm, cdt, cdn);
    }
});

// Function to apply settings defaults
function apply_settings_defaults(frm) {
	if (frm.doc._settings_applied) {
		return;
	}
	
	// Get company
	const company = frm.doc.company || frappe.defaults.get_user_default("Company");
	if (!company) {
		return;
	}
	
	// Get Air Freight Settings
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Air Freight Settings",
			filters: {
				company: company
			},
			limit_page_length: 1
		},
		callback: function(r) {
			if (r.message && r.message.length > 0) {
				// Get the first settings document
				frappe.call({
					method: "frappe.client.get",
					args: {
						doctype: "Air Freight Settings",
						name: r.message[0].name
					},
					callback: function(r2) {
						if (r2.message) {
							const settings = r2.message;
				
				// Apply general settings
				if (!frm.doc.branch && settings.default_branch) {
					frm.set_value("branch", settings.default_branch);
				}
				if (!frm.doc.cost_center && settings.default_cost_center) {
					frm.set_value("cost_center", settings.default_cost_center);
				}
				if (!frm.doc.profit_center && settings.default_profit_center) {
					frm.set_value("profit_center", settings.default_profit_center);
				}
				
				// Apply consolidation settings
				if (!frm.doc.consolidation_type && settings.default_consolidation_type) {
					frm.set_value("consolidation_type", settings.default_consolidation_type);
				}
				
				// Mark as applied
				frm.set_value("_settings_applied", 1);
					}
				}
			});
		}
	}
	});
}

// Custom functions
function add_consolidation_buttons(frm) {
    if (frm.doc.status === 'Draft' || frm.doc.status === 'Planning') {
        frm.add_custom_button(__('Add Air Shipment'), function() {
            add_air_freight_job(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Optimize Routes'), function() {
            optimize_routes(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Check Capacity'), function() {
            check_capacity_availability(frm);
        }, __('Actions'));
    }
    
    if (frm.doc.status === 'Planning' || frm.doc.status === 'Ready for Departure') {
        frm.add_custom_button(__('Generate Report'), function() {
            generate_consolidation_report(frm);
        }, __('Reports'));
        
        frm.add_custom_button(__('Cost Breakdown'), function() {
            show_cost_breakdown(frm);
        }, __('Reports'));
    }
    
    frm.add_custom_button(__('Consolidation Summary'), function() {
        show_consolidation_summary(frm);
    }, __('View'));
}

function add_air_freight_job(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Add Air Shipment'),
        fields: [
            {
                'fieldtype': 'Link',
                'fieldname': 'air_freight_job',
                'label': __('Air Shipment'),
                'options': 'Air Shipment',
                'reqd': 1
            }
        ],
        primary_action_label: __('Add'),
        primary_action: function(values) {
            frm.call('add_air_freight_job', {
                air_freight_job: values.air_freight_job
            }).then(r => {
                if (r.message) {
                    frm.reload_doc();
                    frappe.show_alert({
                        message: __('Air Shipment added successfully'),
                        indicator: 'green'
                    });
                }
            });
            d.hide();
        }
    });
    d.show();
}

function optimize_routes(frm) {
    frappe.confirm(__('Optimize route selection based on cost and time?'), function() {
        frm.call('optimize_route_selection').then(r => {
            if (r.message) {
                frm.reload_doc();
                frappe.show_alert({
                    message: __('Routes optimized successfully'),
                    indicator: 'green'
                });
            }
        });
    });
}

function check_capacity_availability(frm) {
    frm.call('check_capacity_availability').then(r => {
        if (r.message) {
            show_capacity_report(r.message);
        }
    });
}

function show_capacity_report(capacity_info) {
    let html = '<div class="capacity-report">';
    html += '<h4>Capacity Availability Report</h4>';
    html += '<table class="table table-bordered">';
    html += '<thead><tr><th>Route</th><th>Available Weight</th><th>Available Volume</th><th>Weight Utilization</th><th>Volume Utilization</th><th>Status</th></tr></thead>';
    html += '<tbody>';
    
    capacity_info.forEach(function(route) {
        let status_class = route.status === 'Available' ? 'text-success' : 'text-danger';
        html += `<tr>
            <td>Route ${route.route_sequence}</td>
            <td>${route.available_weight} kg</td>
            <td>${route.available_volume} m³</td>
            <td>${route.weight_utilization.toFixed(1)}%</td>
            <td>${route.volume_utilization.toFixed(1)}%</td>
            <td class="${status_class}">${route.status}</td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    
    let d = new frappe.ui.Dialog({
        title: __('Capacity Availability Report'),
        size: 'large',
        fields: [
            {
                'fieldtype': 'HTML',
                'fieldname': 'capacity_html',
                'options': html
            }
        ]
    });
    d.show();
}

function generate_consolidation_report(frm) {
    frm.call('generate_consolidation_report').then(r => {
        if (r.message) {
            show_consolidation_report(r.message);
        }
    });
}

function show_consolidation_report(report_data) {
    let html = '<div class="consolidation-report">';
    html += '<h4>Consolidation Report</h4>';
    html += `<p><strong>Consolidation ID:</strong> ${report_data.consolidation_id}</p>`;
    html += `<p><strong>Status:</strong> ${report_data.status}</p>`;
    html += `<p><strong>Total Packages:</strong> ${report_data.total_packages}</p>`;
    html += `<p><strong>Total Weight:</strong> ${report_data.total_weight} kg</p>`;
    html += `<p><strong>Total Volume:</strong> ${report_data.total_volume} m³</p>`;
    html += `<p><strong>Chargeable Weight:</strong> ${report_data.chargeable_weight} kg</p>`;
    html += `<p><strong>Consolidation Ratio:</strong> ${report_data.consolidation_ratio}%</p>`;
    html += `<p><strong>Cost per kg:</strong> ${report_data.cost_per_kg}</p>`;
    
    // Routes section
    html += '<h5>Routes</h5>';
    html += '<table class="table table-bordered">';
    html += '<thead><tr><th>Sequence</th><th>Origin</th><th>Destination</th><th>Airline</th><th>Flight</th><th>Departure</th><th>Arrival</th><th>Status</th></tr></thead>';
    html += '<tbody>';
    
    report_data.routes.forEach(function(route) {
        html += `<tr>
            <td>${route.sequence}</td>
            <td>${route.origin}</td>
            <td>${route.destination}</td>
            <td>${route.airline}</td>
            <td>${route.flight_number}</td>
            <td>${route.departure}</td>
            <td>${route.arrival}</td>
            <td>${route.status}</td>
        </tr>`;
    });
    
    html += '</tbody></table>';
    
    // Packages section
    html += '<h5>Packages</h5>';
    html += '<table class="table table-bordered">';
    html += '<thead><tr><th>Reference</th><th>Air Shipment</th><th>Shipper</th><th>Consignee</th><th>Weight</th><th>Volume</th><th>Status</th></tr></thead>';
    html += '<tbody>';
    
    report_data.packages.forEach(function(package) {
        html += `<tr>
            <td>${package.reference}</td>
            <td>${package.air_freight_job}</td>
            <td>${package.shipper}</td>
            <td>${package.consignee}</td>
            <td>${package.weight} kg</td>
            <td>${package.volume} m³</td>
            <td>${package.status}</td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    
    let d = new frappe.ui.Dialog({
        title: __('Consolidation Report'),
        size: 'extra-large',
        fields: [
            {
                'fieldtype': 'HTML',
                'fieldname': 'report_html',
                'options': html
            }
        ]
    });
    d.show();
}

function show_cost_breakdown(frm) {
    frm.call('calculate_cost_breakdown').then(r => {
        if (r.message) {
            show_cost_breakdown_dialog(r.message);
        }
    });
}

function show_cost_breakdown_dialog(cost_breakdown) {
    let html = '<div class="cost-breakdown">';
    html += '<h4>Cost Breakdown</h4>';
    html += `<p><strong>Total Cost:</strong> ${cost_breakdown.total_cost}</p>`;
    html += `<p><strong>Cost per kg:</strong> ${cost_breakdown.cost_per_kg}</p>`;
    
    html += '<h5>Charges</h5>';
    html += '<table class="table table-bordered">';
    html += '<thead><tr><th>Type</th><th>Category</th><th>Basis</th><th>Rate</th><th>Quantity</th><th>Base Amount</th><th>Discount</th><th>Surcharge</th><th>Total</th></tr></thead>';
    html += '<tbody>';
    
    cost_breakdown.charges.forEach(function(charge) {
        html += `<tr>
            <td>${charge.type}</td>
            <td>${charge.category}</td>
            <td>${charge.basis}</td>
            <td>${charge.rate}</td>
            <td>${charge.quantity}</td>
            <td>${charge.base_amount}</td>
            <td>${charge.discount}</td>
            <td>${charge.surcharge}</td>
            <td>${charge.total}</td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    
    let d = new frappe.ui.Dialog({
        title: __('Cost Breakdown'),
        size: 'large',
        fields: [
            {
                'fieldtype': 'HTML',
                'fieldname': 'cost_html',
                'options': html
            }
        ]
    });
    d.show();
}

function show_consolidation_summary(frm) {
    frm.call('get_consolidation_summary').then(r => {
        if (r.message) {
            show_consolidation_summary_dialog(r.message);
        }
    });
}

function show_consolidation_summary_dialog(summary) {
    let html = '<div class="consolidation-summary">';
    html += '<h4>Consolidation Summary</h4>';
    html += `<p><strong>Consolidation ID:</strong> ${summary.consolidation_id}</p>`;
    html += `<p><strong>Status:</strong> ${summary.status}</p>`;
    html += `<p><strong>Type:</strong> ${summary.consolidation_type}</p>`;
    html += `<p><strong>Route:</strong> ${summary.route}</p>`;
    html += `<p><strong>Departure:</strong> ${summary.departure}</p>`;
    html += `<p><strong>Arrival:</strong> ${summary.arrival}</p>`;
    html += `<p><strong>Airline:</strong> ${summary.airline} ${summary.flight_number}</p>`;
    html += `<p><strong>Total Jobs:</strong> ${summary.total_jobs}</p>`;
    html += `<p><strong>Total Packages:</strong> ${summary.total_packages}</p>`;
    html += `<p><strong>Total Weight:</strong> ${summary.total_weight} kg</p>`;
    html += `<p><strong>Total Volume:</strong> ${summary.total_volume} m³</p>`;
    html += `<p><strong>Chargeable Weight:</strong> ${summary.chargeable_weight} kg</p>`;
    html += `<p><strong>Consolidation Ratio:</strong> ${summary.consolidation_ratio}%</p>`;
    html += `<p><strong>Cost per kg:</strong> ${summary.cost_per_kg}</p>`;
    
    html += '</div>';
    
    let d = new frappe.ui.Dialog({
        title: __('Consolidation Summary'),
        size: 'large',
        fields: [
            {
                'fieldtype': 'HTML',
                'fieldname': 'summary_html',
                'options': html
            }
        ]
    });
    d.show();
}

function update_consolidation_metrics(frm) {
    if (frm.doc.consolidation_packages && frm.doc.consolidation_packages.length > 0) {
        let total_packages = 0;
        let total_weight = 0;
        let total_volume = 0;
        
        frm.doc.consolidation_packages.forEach(function(package) {
            total_packages += package.package_count || 0;
            total_weight += package.package_weight || 0;
            total_volume += package.package_volume || 0;
        });
        
        frm.set_value('total_packages', total_packages);
        frm.set_value('total_weight', total_weight);
        frm.set_value('total_volume', total_volume);
        
        // Calculate chargeable weight
        let volume_weight = total_volume * 167; // IATA standard
        let chargeable_weight = Math.max(total_weight, volume_weight);
        frm.set_value('chargeable_weight', chargeable_weight);
        
        // Calculate consolidation ratio
        if (total_weight > 0) {
            let consolidation_ratio = (chargeable_weight / total_weight) * 100;
            frm.set_value('consolidation_ratio', consolidation_ratio);
        }
    }
}

function update_consolidation_type_fields(frm) {
    // Update form fields based on consolidation type
    if (frm.doc.consolidation_type === 'Transit Consolidation') {
        // Show additional fields for transit consolidation
        frm.set_df_property('transit_airport', 'reqd', 1);
    } else {
        frm.set_df_property('transit_airport', 'reqd', 0);
    }
}

function update_status_fields(frm) {
    // Update fields based on status
    if (frm.doc.status === 'In Transit') {
        frm.set_df_property('master_awb', 'reqd', 1);
    }
}

function validate_departure_date(frm) {
    if (frm.doc.departure_date && frm.doc.arrival_date) {
        if (frm.doc.departure_date >= frm.doc.arrival_date) {
            frappe.msgprint(__('Departure date must be before arrival date'));
            frm.set_value('departure_date', '');
        }
    }
}

function validate_arrival_date(frm) {
    if (frm.doc.departure_date && frm.doc.arrival_date) {
        if (frm.doc.departure_date >= frm.doc.arrival_date) {
            frappe.msgprint(__('Arrival date must be after departure date'));
            frm.set_value('arrival_date', '');
        }
    }
}

function calculate_package_charges(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.package_weight) {
        // Calculate charges based on weight
        row.base_charge = row.package_weight * 10; // Example rate
        row.total_charge = row.base_charge + (row.surcharges || 0);
        refresh_field('consolidation_packages');
    }
}

function calculate_volume_weight(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.package_volume) {
        // Calculate volume weight (IATA standard: 167 kg/m³)
        let volume_weight = row.package_volume * 167;
        row.volume_weight = volume_weight;
        refresh_field('consolidation_packages');
    }
}

function validate_dangerous_goods(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.contains_dangerous_goods) {
        if (!row.dg_class || !row.un_number) {
            frappe.msgprint(__('DG Class and UN Number are required for dangerous goods'));
        }
    }
}

function validate_route_sequence(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    // Validate route sequence
    if (row.route_sequence <= 0) {
        frappe.msgprint(__('Route sequence must be greater than 0'));
        row.route_sequence = 1;
        refresh_field('consolidation_routes');
    }
}

function calculate_transit_time(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.departure_date && row.arrival_date) {
        let departure = new Date(row.departure_date);
        let arrival = new Date(row.arrival_date);
        let transit_time = (arrival - departure) / (1000 * 60 * 60); // hours
        row.transit_time_hours = transit_time;
        refresh_field('consolidation_routes');
    }
}

function calculate_capacity_utilization(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.cargo_capacity_kg && frm.doc.total_weight) {
        let utilization = (frm.doc.total_weight / row.cargo_capacity_kg) * 100;
        row.utilization_percentage = utilization;
        row.available_capacity_kg = row.cargo_capacity_kg - frm.doc.total_weight;
        refresh_field('consolidation_routes');
    }
}

function update_charge_calculation(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.charge_basis === 'Per kg' && frm.doc.chargeable_weight) {
        row.quantity = frm.doc.chargeable_weight;
    } else if (row.charge_basis === 'Per m³' && frm.doc.total_volume) {
        row.quantity = frm.doc.total_volume;
    } else if (row.charge_basis === 'Per package' && frm.doc.total_packages) {
        row.quantity = frm.doc.total_packages;
    }
    calculate_charge_amount(frm, cdt, cdn);
}

function calculate_charge_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.rate && row.quantity) {
        row.base_amount = row.rate * row.quantity;
        
        // Calculate discount
        if (row.discount_percentage) {
            row.discount_amount = row.base_amount * (row.discount_percentage / 100);
        } else {
            row.discount_amount = 0;
        }
        
        // Calculate total
        row.total_amount = row.base_amount - row.discount_amount + (row.surcharge_amount || 0);
        refresh_field('consolidation_charges');
    }
}

function update_job_status_timestamps(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.consolidation_status === 'Accepted' && !row.check_in_time) {
        row.check_in_time = frappe.datetime.now_datetime();
    } else if (row.consolidation_status === 'In Transit' && !row.check_out_time) {
        row.check_out_time = frappe.datetime.now_datetime();
    }
    refresh_field('attached_air_freight_jobs');
}

function load_job_details(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.air_freight_job) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Air Shipment',
                name: row.air_freight_job
            },
            callback: function(r) {
                if (r.message) {
                    let job = r.message;
                    row.job_status = job.status;
                    row.booking_date = job.booking_date;
                    row.shipper = job.shipper;
                    row.consignee = job.consignee;
                    row.origin_port = job.origin_port;
                    row.destination_port = job.destination_port;
                    row.weight = job.weight;
                    row.volume = job.volume;
                    row.packs = job.packs;
                    row.value = job.gooda_value;
                    row.currency = job.currency;
                    row.incoterm = job.incoterm;
                    row.contains_dangerous_goods = job.contains_dangerous_goods;
                    row.dg_compliance_status = job.dg_compliance_status;
                    row.dg_declaration_complete = job.dg_declaration_complete;
                    refresh_field('attached_air_freight_jobs');
                }
            }
        });
    }
}

function update_consolidation_totals(frm) {
    update_consolidation_metrics(frm);
}
