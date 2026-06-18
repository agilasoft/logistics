// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
    if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
    if (frm._milestone_html_called) return;
    frm._milestone_html_called = true;
    frappe.call({
        method: 'logistics.document_management.api.get_milestone_html',
        args: { doctype: 'Air Consolidation', docname: frm.doc.name },
        callback: function(r) {
            if (r.message && frm.fields_dict.milestone_html) {
                frm.fields_dict.milestone_html.$wrapper.html(r.message);
            }
        }
    }).always(function() {
        setTimeout(function() { frm._milestone_html_called = false; }, 2000);
    });
}

function _load_documents_html(frm) {
    if (!frm.fields_dict.documents_html || !frm.doc.name || frm.doc.__islocal) return;
    if (frm._documents_html_called) return;
    frm._documents_html_called = true;
    frappe.call({
        method: 'logistics.document_management.api.get_document_alerts_html',
        args: { doctype: 'Air Consolidation', docname: frm.doc.name },
        callback: function(r) {
            if (r.message && frm.fields_dict.documents_html) {
                frm.fields_dict.documents_html.$wrapper.html(r.message);
                if (window.logistics_bind_document_alert_cards) {
                    window.logistics_bind_document_alert_cards(frm.fields_dict.documents_html.$wrapper);
                }
            }
        }
    }).always(function() {
        setTimeout(function() { frm._documents_html_called = false; }, 2000);
    });
}

frappe.ui.form.on('Air Consolidation', {
	document_list_template: function (frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_documents_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					}
				}
			});
		});
	},
	milestone_template: function (frm) {
		if (!frm.doc.name || frm.doc.__islocal) return;
		frm.save().then(function () {
			frappe.call({
				method: "logistics.document_management.api.populate_milestones_from_template",
				args: { doctype: frm.doctype, docname: frm.doc.name },
				callback: function (r) {
					if (r.message) {
						frm.reload_doc();
						if (r.message.added) frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 5);
					}
				}
			});
		});
	},
	setup: function(frm) {
		frm.set_query('milestone_template', function() {
			return frappe.call('logistics.document_management.api.get_milestone_template_filters', { doctype: frm.doctype })
				.then(function(r) { return r.message || { filters: [] }; });
		});
	},
    onload: function(frm) {
        // Apply settings defaults when creating new document
        if (frm.is_new()) {
            apply_settings_defaults(frm);
        }
    },
    
    refresh: function (frm) {
		if (frm.fields_dict.dashboard_html && frm.doc.name && !frm.doc.__islocal) {
			if (!frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frm.call("get_dashboard_html").then(function (r) {
					if (r.message && frm.fields_dict.dashboard_html) {
						frm.fields_dict.dashboard_html.$wrapper.html(r.message);
						if (window.logistics_group_and_collapse_dash_alerts) {
							setTimeout(function () {
								window.logistics_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
							}, 100);
						}
						if (window.logistics_bind_document_alert_cards) {
							window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
						}
					}
				});
				setTimeout(function () {
					frm._dashboard_html_called = false;
				}, 2000);
			}
		}
		_load_documents_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.documents_html").on("click.documents_html", '[data-fieldname="documents_tab"]', function () {
				_load_documents_html(frm);
			});
		}
		_load_milestone_html(frm);
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off("click.milestone_html").on("click.milestone_html", '[data-fieldname="milestones_tab"]', function () {
				_load_milestone_html(frm);
			});
		}
		(function lock_planning_and_cargo_grids() {
			const planningLocked =
				(frm.doc.air_planning_status || "Draft") === "Submitted" && frm.doc.docstatus === 0;
			["consolidation_planning_lines", "consolidation_packages"].forEach(function (fieldname) {
				if (!frm.fields_dict[fieldname]) {
					return;
				}
				frm.set_df_property(fieldname, "read_only", planningLocked ? 1 : 0);
				frm.set_df_property(fieldname, "cannot_add_rows", planningLocked ? 1 : 0);
				frm.set_df_property(fieldname, "cannot_delete_rows", planningLocked ? 1 : 0);
				frm.refresh_field(fieldname);
				if (planningLocked && window.logistics_hide_cannot_add_rows_buttons) {
					setTimeout(function () {
						window.logistics_hide_cannot_add_rows_buttons(frm, fieldname);
					}, 0);
				}
			});
		})();
		if (!frm.doc.__islocal && frm.doc.docstatus === 0) {
			if ((frm.doc.air_planning_status || "Draft") === "Draft") {
				frm.add_custom_button(__("Aligned Air Shipments…"), function () {
					if (window.logistics && logistics.open_air_consolidation_matching_shipments_dialog) {
						logistics.open_air_consolidation_matching_shipments_dialog(frm);
					} else {
						frappe.msgprint(__("Air consolidation UI is still loading — try again in a moment."));
					}
				}, __("Action"));
			}
			const distinctPlannedAirShipments = new Set(
				(frm.doc.consolidation_planning_lines || [])
					.map((row) => row.air_shipment)
					.filter(Boolean)
			).size;
			if (
				(frm.doc.air_planning_status || "Draft") === "Draft" &&
				distinctPlannedAirShipments >= 2
			) {
				frm.add_custom_button(
					__("Submit planned shipments"),
					function () {
						frappe.confirm(
							__("Submit planned shipment list? It will lock until reset."),
							function () {
								frm.call("submit_air_planning").then(function () {
									frappe.show_alert({ message: __("Planning submitted"), indicator: "green" }, 3);
									frm.reload_doc();
								});
							}
						);
					},
					__("Action")
				);
			}
			if (frm.doc.air_planning_status === "Submitted") {
				frm.add_custom_button(
					__("Reset planned shipments to draft"),
					function () {
						frappe.confirm(
							__(
								"Planning will return to draft. Planned shipments and packages stay as they are; the tables become editable again, and you can add more from Aligned Air Shipments. Continue?"
							),
							function () {
								frm.call("cancel_air_planning_submit").then(function () {
									frappe.show_alert({ message: __("Planning set to draft"), indicator: "blue" }, 3);
									frm.reload_doc();
								});
							}
						);
					},
					__("Action")
				);
			}
		}
		if (!frm.is_new() && !frm.doc.__islocal) {
			frm.add_custom_button(__("Get Milestones"), function () {
				frappe.call({
					method: "logistics.document_management.api.populate_milestones_from_template",
					args: { doctype: "Air Consolidation", docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					},
				});
			}, __("Action"));
			frm.add_custom_button(__("Get Documents"), function () {
				frappe.call({
					method: "logistics.document_management.api.populate_documents_from_template",
					args: { doctype: "Air Consolidation", docname: frm.doc.name },
					callback: function (r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: "blue" }, 3);
						}
					},
				});
			}, __("Action"));
		}
		add_consolidation_buttons(frm);
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
frappe.ui.form.on("Air Consolidation Packages", {
	package_weight: function (frm, cdt, cdn) {
		calculate_package_charges(frm, cdt, cdn);
		update_consolidation_totals(frm);
	},
	package_volume: function (frm, cdt, cdn) {
		calculate_volume_weight(frm, cdt, cdn);
		update_consolidation_totals(frm);
	},
	contains_dangerous_goods: function (frm, cdt, cdn) {
		validate_dangerous_goods(frm, cdt, cdn);
		frm.refresh_field("consolidation_packages");
	},
	temperature_controlled: function (frm) {
		frm.refresh_field("consolidation_packages");
	},
	air_freight_job: function (frm) {
		refresh_consolidation_charges_quantities_from_parent(frm);
	},
});

frappe.ui.form.on("Air Consolidation Planning Line", {
	air_shipment: function (frm) {
		refresh_consolidation_charges_quantities_from_parent(frm);
	},
});

// Inline grid: unit_type / UOM / method → quantity + amounts without save.
frappe.ui.form.on("Air Consolidation", "consolidation_charges", {
	unit_type: function (frm, cdt, cdn) {
		if (window.logistics && logistics.update_air_consolidation_charge_row_from_parent) {
			logistics.update_air_consolidation_charge_row_from_parent(frm, cdt, cdn);
		}
	},
	unit_of_measure: function (frm, cdt, cdn) {
		if (window.logistics && logistics.update_air_consolidation_charge_row_from_parent) {
			logistics.update_air_consolidation_charge_row_from_parent(frm, cdt, cdn);
		}
	},
	revenue_calculation_method: function (frm, cdt, cdn) {
		if (window.logistics && logistics.update_air_consolidation_charge_row_from_parent) {
			logistics.update_air_consolidation_charge_row_from_parent(frm, cdt, cdn);
		}
	},
});

// Air Consolidation Routes child table events
frappe.ui.form.on('Air Consolidation Routes', {
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
				
				// Mark as applied (virtual field - set directly on doc)
				frm.doc._settings_applied = 1;
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
        }, __('Action'));

        if (!frm.doc.master_awb) {
            frm.add_custom_button(__('Assign MAWB from Stock'), function() {
                frm.call({
                    method: 'assign_mawb_from_stock',
                    doc: frm.doc,
                    callback: function(r) {
                        if (r.exc) return;
                        if (r.message && r.message.mawb_name) {
                            frappe.show_alert({
                                message: __('MAWB {0} assigned', [r.message.master_awb_no || r.message.mawb_name]),
                                indicator: 'green'
                            }, 5);
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Action'));
        }
        
        frm.add_custom_button(__('Optimize Routes'), function() {
            optimize_routes(frm);
        }, __('Action'));
        
        frm.add_custom_button(__('Check Capacity'), function() {
            check_capacity_availability(frm);
        }, __('Action'));

        if (!frm.doc.__islocal && frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Copy routing from shipment'), function () {
                copy_routing_from_shipment_dialog(frm);
            }, __('Action'));
            if (frm.doc.origin_airport && frm.doc.destination_airport) {
                frm.add_custom_button(__('Populate routing from airports'), function () {
                    frappe.call({
                        method:
                            'logistics.air_freight.doctype.air_consolidation.air_consolidation.populate_routing_from_airports',
                        args: { docname: frm.doc.name },
                        callback: function (r) {
                            if (r.message && r.message.message) {
                                frm.reload_doc();
                                frappe.show_alert({
                                    message: __(r.message.message),
                                    indicator: 'green',
                                }, 4);
                            }
                        },
                    });
                }, __('Action'));
            }
        }
    }
    
    if (frm.doc.status === 'Planning' || frm.doc.status === 'Ready for Departure') {
        frm.add_custom_button(__('Generate Report'), function() {
            generate_consolidation_report(frm);
        }, __('Action'));
        
        frm.add_custom_button(__('Cost Breakdown'), function() {
            show_cost_breakdown(frm);
        }, __('Action'));
    }
    
}

function copy_routing_from_shipment_dialog(frm) {
    var planned = (frm.doc.consolidation_planning_lines || [])
        .map(function (row) { return row.air_shipment; })
        .filter(Boolean);
    var fields = [
        {
            fieldtype: 'Link',
            fieldname: 'air_shipment',
            label: __('Air Shipment'),
            options: 'Air Shipment',
            reqd: 1,
            get_query: function () {
                var filters = [];
                if (frm.doc.origin_airport) {
                    filters.push(['origin_port', '=', frm.doc.origin_airport]);
                }
                if (frm.doc.destination_airport) {
                    filters.push(['destination_port', '=', frm.doc.destination_airport]);
                }
                if (planned.length) {
                    filters.push(['name', 'in', planned]);
                }
                return { filters: filters };
            },
        },
    ];
    if (planned.length === 1) {
        fields[0].default = planned[0];
    }
    var d = new frappe.ui.Dialog({
        title: __('Copy routing from shipment'),
        fields: fields,
        primary_action_label: __('Copy'),
        primary_action: function (values) {
            frappe.call({
                method:
                    'logistics.air_freight.doctype.air_consolidation.air_consolidation.populate_routing_from_air_shipment',
                args: {
                    docname: frm.doc.name,
                    air_shipment: values.air_shipment,
                },
                callback: function (r) {
                    if (r.message && r.message.message) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __(r.message.message),
                            indicator: 'green',
                        }, 4);
                    }
                },
            });
            d.hide();
        },
    });
    d.show();
}

function add_air_freight_job(frm) {
    if (!frm.doc.origin_airport || !frm.doc.destination_airport) {
        frappe.msgprint({
            title: __('Origin and Destination Required'),
            message: __('Please set Origin Airport and Destination Airport in the header before adding shipments.'),
            indicator: 'orange'
        });
        return;
    }
    let d = new frappe.ui.Dialog({
        title: __('Add Air Shipment'),
        fields: [
            {
                'fieldtype': 'Link',
                'fieldname': 'air_freight_job',
                'label': __('Air Shipment'),
                'options': 'Air Shipment',
                'reqd': 1,
                'get_query': function() {
                    return {
                        filters: [
                            ['origin_port', '=', frm.doc.origin_airport],
                            ['destination_port', '=', frm.doc.destination_airport]
                        ]
                    };
                }
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
            <td>Route ${route.sequence}</td>
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
            <td>${charge.unit_rate}</td>
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
        let volume_weight = total_volume * (1000 / 6); // IATA: 1 kg per 6000 cm³
        let chargeable_weight = Math.max(total_weight, volume_weight);
        frm.set_value('chargeable_weight', chargeable_weight);
        
        // Calculate consolidation ratio
        if (total_weight > 0) {
            let consolidation_ratio = (chargeable_weight / total_weight) * 100;
            frm.set_value('consolidation_ratio', consolidation_ratio);
        }
    }
    refresh_consolidation_charges_quantities_from_parent(frm);
}

function update_consolidation_type_fields(frm) {
    // Update form fields based on consolidation type
    if (frm.doc.consolidation_type === 'Transit Consolidation') {
        // Event additional fields for transit consolidation
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
        frm.refresh_field('consolidation_packages');
    }
}

function calculate_volume_weight(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.package_volume) {
        // IATA volumetric: 1000/6 kg per m³ (1 kg per 6000 cm³)
        let volume_weight = row.package_volume * (1000 / 6);
        row.volume_weight = volume_weight;
        frm.refresh_field('consolidation_packages');
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

function calculate_transit_time(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.departure_date && row.arrival_date) {
        let departure = new Date(row.departure_date);
        let arrival = new Date(row.arrival_date);
        let transit_time = (arrival - departure) / (1000 * 60 * 60); // hours
        row.transit_time_hours = transit_time;
        frm.refresh_field('consolidation_routes');
    }
}

function calculate_capacity_utilization(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.cargo_capacity_kg && frm.doc.total_weight) {
        let utilization = (frm.doc.total_weight / row.cargo_capacity_kg) * 100;
        row.utilization_percentage = utilization;
        row.available_capacity_kg = row.cargo_capacity_kg - frm.doc.total_weight;
        frm.refresh_field('consolidation_routes');
    }
}

function refresh_consolidation_charges_quantities_from_parent(frm) {
    if (!frm.doc.consolidation_charges || !frm.doc.consolidation_charges.length) {
        return;
    }
    if (
        !window.logistics ||
        !logistics.sync_air_consolidation_charge_qty_to_grid
    ) {
        return;
    }
    var cdt = "Air Consolidation Charges";
    (frm.doc.consolidation_charges || []).forEach(function (row) {
        if (!row.name) {
            return;
        }
        if (row.revenue_calculation_method !== "Per Unit") {
            return;
        }
        if (logistics.update_air_consolidation_charge_row_from_parent) {
            logistics.update_air_consolidation_charge_row_from_parent(
                frm,
                cdt,
                row.name,
                { server: false }
            );
        }
    });
}

function update_consolidation_totals(frm) {
    update_consolidation_metrics(frm);
}
