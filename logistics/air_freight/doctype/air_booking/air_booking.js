// Copyright (c) 2025, logistics.agilasoft.com and contributors
// For license information, please see license.txt

function _load_milestone_html(frm) {
	if (!frm.fields_dict.milestone_html || !frm.doc.name || frm.doc.__islocal) return;
	if (frm._milestone_html_called) return;
	frm._milestone_html_called = true;
	frappe.call({
		method: 'logistics.document_management.api.get_milestone_html',
		args: { doctype: 'Air Booking', docname: frm.doc.name },
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
		args: { doctype: 'Air Booking', docname: frm.doc.name },
		callback: function(r) {
			if (r.message && frm.fields_dict.documents_html) {
				frm.fields_dict.documents_html.$wrapper.html(r.message);
				if (window.logistics_bind_document_alert_cards) {
					window.logistics_bind_document_alert_cards(frm.fields_dict.documents_html.$wrapper);
				}
			}
		}
	}).always(() => {
		setTimeout(() => { frm._documents_html_called = false; }, 2000);
	});
}

function _warn_if_missing_service_charges(frm, service_type) {
	var charges = frm.doc.charges || [];
	var has_match = charges.some(function(row) {
		return (row.service_type || '').trim() === service_type;
	});
	if (!has_match) {
		frappe.msgprint({
			title: __("Charges Warning"),
			message: __("No {0} charges found yet. You can continue in draft, but submit will be blocked.", [service_type]),
			indicator: "orange"
		});
	}
}

function _apply_air_booking_settings_defaults(frm, force_reload) {
	if (!frm.is_new() && !frm.doc.__islocal) return;
	if (frm._applying_air_booking_defaults) return;
	if (frm._air_booking_defaults_applied && !force_reload) return;

	var company = frm.doc.company || frappe.defaults.get_user_default("Company");
	if (!company) return;

	frm._applying_air_booking_defaults = true;
	frappe.call({
		method: "logistics.air_freight.doctype.air_booking.air_booking.get_air_booking_settings_defaults",
		args: { company: company },
		callback: function(r) {
			var defaults = (r && r.message) || {};
			var fields = [
				"branch", "cost_center", "profit_center", "incoterm", "service_level",
				"origin_port", "destination_port", "airline", "freight_agent",
				"house_type", "direction", "release_type", "entry_type", "load_type"
			];
			fields.forEach(function(fieldname) {
				if (!frm.doc[fieldname] && defaults[fieldname]) {
					frm.set_value(fieldname, defaults[fieldname]);
				}
			});
			frm._air_booking_defaults_applied = true;
		},
		always: function() {
			frm._applying_air_booking_defaults = false;
		}
	});
}

/**
 * When ATA is set but ATD is not, show one confirm that combines the standard
 * permanent-submit prompt with the ATA/ATD notice (same flow as frappe.form.savesubmit).
 */
function _install_air_booking_custom_savesubmit(frm) {
	var _savesubmit = frm.savesubmit.bind(frm);
	frm.savesubmit = function(btn, callback, on_error) {
		var me = this;
		if (!me.doc.ata || me.doc.atd) {
			return _savesubmit(btn, callback, on_error);
		}
		return new Promise(function(resolve) {
			me.validate_form_action("Submit");
			frappe.confirm(
				__(
					"Permanently submit {0}? ATA (Actual Time of Arrival) is set but ATD (Actual Time of Departure) is not. Do you want to submit this booking anyway?",
					[me.docname]
				),
				function() {
					frappe.validated = true;
					me.script_manager.trigger("before_submit").then(function() {
						if (!frappe.validated) {
							return me.handle_save_fail(btn, on_error);
						}
						me.save(
							"Submit",
							function(r) {
								if (r.exc) {
									me.handle_save_fail(btn, on_error);
								} else {
									frappe.utils.play_sound("submit");
									callback && callback();
									me.script_manager
										.trigger("on_submit")
										.then(() => resolve(me))
										.then(() => {
											if (frappe.route_hooks.after_submit) {
												var route_callback = frappe.route_hooks.after_submit;
												delete frappe.route_hooks.after_submit;
												route_callback(me);
											}
										});
								}
							},
							btn,
							() => me.handle_save_fail(btn, on_error),
							resolve
						);
					});
				},
				() => me.handle_save_fail(btn, on_error)
			);
		});
	};
}

/** Table flags for charges: `cannot_add_rows` / `allow_bulk_edit` may not match client meta; set on the docfield so the grid hides Add / Upload / Download as intended. */
function _logistics_set_charges_cannot_add_rows(frm) {
	if (!frm.get_docfield || !frm.get_docfield("charges")) {
		return;
	}
	frm.set_df_property("charges", "cannot_add_rows", 1);
	frm.set_df_property("charges", "allow_bulk_edit", 0);
}

function _patch_air_booking_milestone_actual_end_df(df) {
	if (!df || df.fieldname !== "actual_end") {
		return;
	}
	df.read_only_depends_on = null;
	df.read_only = 0;
}

/**
 * One grid row after Frappe runs set_dependant_property (setup_columns / refresh_dependency).
 * Datetime cells skip focus when df.read_only (grid_row.js trigger_focus); columns_list[].df must match.
 */
function _patch_air_booking_milestone_grid_row_actual_end(grid_row) {
	if (!grid_row || !grid_row.grid || grid_row.grid.df.fieldname !== "milestones") {
		return;
	}
	if (grid_row.docfields && grid_row.docfields.length) {
		grid_row.docfields.forEach(_patch_air_booking_milestone_actual_end_df);
	}
	if (grid_row.columns_list && grid_row.columns_list.length) {
		grid_row.columns_list.forEach(function(col) {
			_patch_air_booking_milestone_actual_end_df(col.df);
		});
	}
	if (grid_row.grid_form && grid_row.grid_form.fields_dict && grid_row.grid_form.fields_dict.actual_end) {
		var fe = grid_row.grid_form.fields_dict.actual_end;
		_patch_air_booking_milestone_actual_end_df(fe.df);
		if (fe.refresh) {
			fe.refresh();
		}
	}
	if (grid_row.refresh_field) {
		grid_row.refresh_field("actual_end");
	}
}

function _patch_air_booking_milestone_all_grid_rows(frm) {
	if (!frm || !frm.fields_dict.milestones || !frm.fields_dict.milestones.grid) {
		return;
	}
	var grid = frm.fields_dict.milestones.grid;
	if (grid.docfields && grid.docfields.length) {
		grid.docfields.forEach(_patch_air_booking_milestone_actual_end_df);
	}
	if (grid.grid_rows && grid.grid_rows.length) {
		grid.grid_rows.forEach(_patch_air_booking_milestone_grid_row_actual_end);
	}
}

/**
 * Milestone grid: keep Actual End editable (no read_only_depends_on / read_only from it).
 * Meta copies + live grid_row df objects (Frappe applies dependencies per row in setup_columns).
 */
function _ensure_air_booking_milestone_actual_end_editable_meta(frm) {
	var dt = "Air Booking Milestone";
	var fn = "actual_end";

	var list = frappe.meta.docfield_list[dt];
	if (list && list.length) {
		list.forEach(function(df) {
			if (df.fieldname === fn) {
				_patch_air_booking_milestone_actual_end_df(df);
			}
		});
	} else {
		var base = frappe.meta.docfield_map[dt];
		if (base && base[fn]) {
			_patch_air_booking_milestone_actual_end_df(base[fn]);
		}
	}

	var copies = frappe.meta.docfield_copy[dt];
	if (copies) {
		Object.keys(copies).forEach(function(dn) {
			var row = copies[dn];
			if (row && row[fn]) {
				_patch_air_booking_milestone_actual_end_df(row[fn]);
			}
		});
	}

	_patch_air_booking_milestone_all_grid_rows(frm);

	if (!frm || !frm.fields_dict.milestones || !frm.fields_dict.milestones.grid) {
		return;
	}

	frm.set_df_property("milestones", "read_only_depends_on", null, dt, fn);
	frm.set_df_property("milestones", "read_only", 0, dt, fn);

	(frm.doc.milestones || []).forEach(function(row) {
		if (!row.name) {
			return;
		}
		frm.set_df_property("milestones", "read_only_depends_on", null, dt, fn, row.name);
		frm.set_df_property("milestones", "read_only", 0, dt, fn, row.name);
	});
}

frappe.ui.form.on('Air Booking', {
	onload: function(frm) {
		if (window.logistics && logistics.apply_one_off_route_options_onload) {
			logistics.apply_one_off_route_options_onload(frm);
		}
		_apply_air_booking_settings_defaults(frm, false);
		_logistics_set_charges_cannot_add_rows(frm);
		_ensure_air_booking_milestone_actual_end_editable_meta(frm);
	},
	after_save: function(frm) {
		// After first save, sync may rename the doc in locals and delete the temporary key; the form can
		// still hold a stale object reference (wrong `modified`) — same as Declaration. Rebind to locals.
		var renamed = frappe.model.new_names && frappe.model.new_names[frm.doc.name];
		if (renamed) {
			frm.docname = renamed;
			frm.doc = (locals[frm.doctype] && locals[frm.doctype][renamed])
				? locals[frm.doctype][renamed]
				: frappe.get_doc(frm.doctype, renamed);
			return;
		}
		if (frm.doc && frm.doc.name && locals[frm.doctype] && locals[frm.doctype][frm.doc.name]) {
			frm.doc = locals[frm.doctype][frm.doc.name];
		}
	},
	milestones_on_form_rendered: function(frm) {
		_ensure_air_booking_milestone_actual_end_editable_meta(frm);
	},
	packages_on_form_rendered: function(frm) {
		if (window.logistics_attach_packages_change_listener) {
			window.logistics_attach_packages_change_listener(frm, 'Air Booking Packages', 'packages', 'air_booking_volume');
		}
	},
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
		// Suppress "Air Booking ... not found" when it refers to this form's doc (race after create/save)
		if (!window._air_booking_msgprint_suppress_patched) {
			window._air_booking_msgprint_suppress_patched = true;
			var _msgprint = frappe.msgprint;
			frappe.msgprint = function(opts) {
				var msg = (opts && (typeof opts === 'string' ? opts : opts.message)) || '';
				var cur = cur_frm;
				if (msg && msg.indexOf('Air Booking') !== -1 && msg.indexOf('not found') !== -1 &&
						cur && cur.doctype === 'Air Booking' && cur.doc && cur.doc.name &&
						msg.indexOf(cur.doc.name) !== -1) {
					return;
				}
				return _msgprint.apply(this, arguments);
			};
		}

		frm.set_query('shipper_address', function() {
			if (frm.doc.shipper) {
				return { filters: [['Dynamic Link', 'link_doctype', '=', 'Shipper'], ['Dynamic Link', 'link_name', '=', frm.doc.shipper]] };
			}
			return {};
		});
		frm.set_query('shipper_contact', function() {
			if (frm.doc.shipper) {
				return { filters: [['Dynamic Link', 'link_doctype', '=', 'Shipper'], ['Dynamic Link', 'link_name', '=', frm.doc.shipper]] };
			}
			return {};
		});
		frm.set_query('consignee_address', function() {
			if (frm.doc.consignee) {
				return { filters: [['Dynamic Link', 'link_doctype', '=', 'Consignee'], ['Dynamic Link', 'link_name', '=', frm.doc.consignee]] };
			}
			return {};
		});
		frm.set_query('consignee_contact', function() {
			if (frm.doc.consignee) {
				return { filters: [['Dynamic Link', 'link_doctype', '=', 'Consignee'], ['Dynamic Link', 'link_name', '=', frm.doc.consignee]] };
			}
			return {};
		});
		frm.set_query('warehouse_item', 'packages', function(doc) {
			const filters = {};
			if (doc.local_customer) {
				filters.customer = doc.local_customer;
			}
			return { filters: filters };
		});
		_install_air_booking_custom_savesubmit(frm);
		// After grid_row.setup_columns → set_dependant_property, patch live df on columns (Datetime skips focus if read_only).
		$(frm.wrapper)
			.off("grid-row-render.air_booking_abm")
			.on("grid-row-render.air_booking_abm", function(e, grid_row) {
				_patch_air_booking_milestone_grid_row_actual_end(grid_row);
			});
		// refresh_dependency() can set actual_end read_only without re-firing grid-row-render; patch before the cell click handler runs.
		if (frm.wrapper && frm.wrapper[0] && !frm._air_booking_abm_click_capture) {
			frm._air_booking_abm_click_capture = true;
			frm.wrapper[0].addEventListener(
				"click",
				function(e) {
					var el = e.target && e.target.closest && e.target.closest(".grid-static-col[data-fieldname='actual_end']");
					if (!el) {
						return;
					}
					var rowEl = el.closest(".grid-row");
					if (!rowEl) {
						return;
					}
					var grid_row = $(rowEl).data("grid_row");
					_patch_air_booking_milestone_grid_row_actual_end(grid_row);
				},
				true
			);
		}
	},
	company: function(frm) {
		// Re-run defaults on company selection for new docs.
		frm._air_booking_defaults_applied = false;
		_apply_air_booking_settings_defaults(frm, true);
	},

	shipper: function(frm) {
		if (!frm.doc.shipper) {
			frm.set_value('shipper_address', '');
			frm.set_value('shipper_address_display', '');
			frm.set_value('shipper_contact', '');
			frm.set_value('shipper_contact_display', '');
			return;
		}
		frappe.db.get_value('Shipper', frm.doc.shipper, ['pick_address', 'shipper_primary_address', 'shipper_primary_contact'], function(r) {
			if (r && (r.pick_address || r.shipper_primary_address)) {
				frm.set_value('shipper_address', r.pick_address || r.shipper_primary_address);
				frm.trigger('shipper_address');
			}
			if (r && r.shipper_primary_contact) {
				frm.set_value('shipper_contact', r.shipper_primary_contact);
				frm.trigger('shipper_contact');
			}
			if (logistics.party_defaults) {
				logistics.party_defaults.apply(frm);
			}
		});
	},

	consignee: function(frm) {
		if (!frm.doc.consignee) {
			frm.set_value('consignee_address', '');
			frm.set_value('consignee_address_display', '');
			frm.set_value('consignee_contact', '');
			frm.set_value('consignee_contact_display', '');
			return;
		}
		frappe.db.get_value('Consignee', frm.doc.consignee, ['delivery_address', 'consignee_primary_address', 'consignee_primary_contact'], function(r) {
			if (r && (r.delivery_address || r.consignee_primary_address)) {
				frm.set_value('consignee_address', r.delivery_address || r.consignee_primary_address);
				frm.trigger('consignee_address');
			}
			if (r && r.consignee_primary_contact) {
				frm.set_value('consignee_contact', r.consignee_primary_contact);
				frm.trigger('consignee_contact');
			}
			if (logistics.party_defaults) {
				logistics.party_defaults.apply(frm);
			}
		});
	},

	shipper_address: function(frm) {
		if (frm.doc.shipper_address) {
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: { address_dict: frm.doc.shipper_address },
				callback: function(r) {
					frm.set_value('shipper_address_display', r.message || '');
				}
			});
		} else {
			frm.set_value('shipper_address_display', '');
		}
	},

	consignee_address: function(frm) {
		if (frm.doc.consignee_address) {
			frappe.call({
				method: 'frappe.contacts.doctype.address.address.get_address_display',
				args: { address_dict: frm.doc.consignee_address },
				callback: function(r) {
					frm.set_value('consignee_address_display', r.message || '');
				}
			});
		} else {
			frm.set_value('consignee_address_display', '');
		}
	},

	shipper_contact: function(frm) {
		if (frm.doc.shipper_contact) {
			frappe.call({
				method: 'frappe.client.get',
				args: { doctype: 'Contact', name: frm.doc.shipper_contact },
				callback: function(r) {
					if (r.message) {
						var c = r.message;
						var txt = [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name;
						if (c.designation) txt += '\n' + c.designation;
						if (c.phone) txt += '\n' + c.phone;
						if (c.mobile_no) txt += '\n' + c.mobile_no;
						if (c.email_id) txt += '\n' + c.email_id;
						frm.set_value('shipper_contact_display', txt);
					} else {
						frm.set_value('shipper_contact_display', '');
					}
				}
			});
		} else {
			frm.set_value('shipper_contact_display', '');
		}
	},

	consignee_contact: function(frm) {
		if (frm.doc.consignee_contact) {
			frappe.call({
				method: 'frappe.client.get',
				args: { doctype: 'Contact', name: frm.doc.consignee_contact },
				callback: function(r) {
					if (r.message) {
						var c = r.message;
						var txt = [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name;
						if (c.designation) txt += '\n' + c.designation;
						if (c.phone) txt += '\n' + c.phone;
						if (c.mobile_no) txt += '\n' + c.mobile_no;
						if (c.email_id) txt += '\n' + c.email_id;
						frm.set_value('consignee_contact_display', txt);
					} else {
						frm.set_value('consignee_contact_display', '');
					}
				}
			});
		} else {
			frm.set_value('consignee_contact_display', '');
		}
	},

	sales_quote: function(frm) {
		if (window.logistics && logistics.apply_one_off_sales_quote_order_standard) {
			logistics.apply_one_off_sales_quote_order_standard(frm);
		}
		// Sales Quote is read-only; use Action → Get Charges from Quotation.
	},

	quote_type: function(frm) {
		// Don't clear quote fields if document is already submitted
		if (frm.doc.docstatus === 1) {
			return;
		}
		
		// If changing quote type and there's an existing quote, clear it
		// This ensures users select a new quote of the correct type
		if (frm.doc.quote) {
			frm.set_value('quote', '');
		}
		
		// Setup query filter for quote field based on quote_type
		_setup_quote_query(frm);
		
		if (!frm.doc.quote) {
			frm.clear_table('charges');
			frm.refresh_field('charges');
		} else {
			_populate_charges_from_quote(frm);
		}
	},
	
	quote: function(frm) {
		// Don't clear quote fields if document is already submitted
		if (frm.doc.docstatus === 1) {
			return;
		}
		if (!frm.doc.quote) {
			frm.clear_table('charges');
			frm.refresh_field('charges');
			return;
		}
		_populate_charges_from_quote(frm);
	},
	
	override_volume_weight: function(frm) {
		_update_measurement_fields_readonly(frm);
		if (frm.is_new() || frm.doc.__islocal) return;
		if (!frm.doc.override_volume_weight) {
			// Re-aggregate when override is turned off (no freeze).
			// Use full-path frappe.call (not frm.call) so this does not use run_doc_method / check_if_latest.
			frappe.call({
				method: 'logistics.air_freight.doctype.air_booking.air_booking.aggregate_volume_from_packages_api',
				args: { doc: frm.doc },
				freeze: false,
				callback: function(r) {
					if (r && !r.exc && r.message) {
						if (r.message.total_volume !== undefined) {
							frm.set_value('volume', r.message.total_volume);
							frm.set_value('total_volume', r.message.total_volume);
						}
						if (r.message.total_weight !== undefined) {
							frm.set_value('weight', r.message.total_weight);
							frm.set_value('total_weight', r.message.total_weight);
						}
						if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
					}
				}
			});
		}
	},

	refresh: function(frm) {
		if (window.logistics && logistics.apply_one_off_sales_quote_order_standard) {
			logistics.apply_one_off_sales_quote_order_standard(frm);
		}
		_ensure_air_booking_milestone_actual_end_editable_meta(frm);
		_logistics_set_charges_cannot_add_rows(frm);
		setTimeout(function () {
			if (window.logistics_hide_cannot_add_rows_buttons) {
				window.logistics_hide_cannot_add_rows_buttons(frm, "charges");
			}
		}, 0);
		if (frm.is_new() || frm.doc.__islocal) {
			_apply_air_booking_settings_defaults(frm, false);
		}
		_update_measurement_fields_readonly(frm);
		// Tab click handlers (safe to bind immediately)
		if (frm.layout && frm.layout.wrapper) {
			frm.layout.wrapper.off('click.documents_html').on('click.documents_html', '[data-fieldname="documents_tab"]', function() {
				_load_documents_html(frm);
			});
			frm.layout.wrapper.off('click.milestone_html').on('click.milestone_html', '[data-fieldname="milestones_tab"]', function() {
				_load_milestone_html(frm);
			});
		}

		// Defer HTML field loading so the new doc is visible on the server (avoids "Air Booking ... not found")
		var docname = frm.doc.name;
		var isNew = !docname || frm.doc.__islocal;
		if (isNew) return;

		function load_html_fields() {
			if (!frm || frm.doc.name !== docname || frm.doc.__islocal) return;

			// Load dashboard HTML via module API (never throws 'not found' — returns placeholder instead)
			if (frm.fields_dict.dashboard_html && !frm._dashboard_html_called) {
				frm._dashboard_html_called = true;
				frappe.call({
					method: 'logistics.air_freight.doctype.air_booking.air_booking.get_air_booking_dashboard_html',
					args: { docname: docname },
					callback: function(r) {
						if (frm && frm.doc.name === docname && r.message && frm.fields_dict.dashboard_html) {
							frm.fields_dict.dashboard_html.$wrapper.html(r.message);
							if (window.logistics_group_and_collapse_dash_alerts) {
								setTimeout(function() {
									window.logistics_group_and_collapse_dash_alerts(frm.fields_dict.dashboard_html.$wrapper);
								}, 100);
							}
							if (window.logistics_bind_document_alert_cards) {
								window.logistics_bind_document_alert_cards(frm.fields_dict.dashboard_html.$wrapper);
							}
						}
					},
					error: function() {
						if (frm && frm.fields_dict.dashboard_html) {
							frm.fields_dict.dashboard_html.$wrapper.html('<div class="alert alert-warning">Dashboard could not be loaded.</div>');
						}
					}
				});
				setTimeout(function() { if (frm) frm._dashboard_html_called = false; }, 2000);
			}

			_load_documents_html(frm);
			_load_milestone_html(frm);
		}

		setTimeout(load_html_fields, 400);

		// Recalculate package volumes from dimensions (fixes stale/wrong values on load).
		// Full-path frappe.call avoids run_doc_method / check_if_latest (TimestampMismatchError after save).
		if (frm.doc.packages && frm.doc.packages.length > 0) {
			frappe.call({
				method: 'logistics.air_freight.doctype.air_booking.air_booking.recalculate_package_volumes_api',
				args: { doc: frm.doc },
				freeze: false,
				callback: function(r) {
					if (r && !r.exc && r.message && Array.isArray(r.message)) {
						r.message.forEach(function(item) {
							if (item.name && item.volume !== undefined) {
								var pkg = frm.doc.packages.find(function(p) { return p.name === item.name; });
								if (pkg && parseFloat(pkg.volume || 0) !== parseFloat(item.volume || 0)) {
									frappe.model.set_value('Air Booking Packages', item.name, 'volume', item.volume);
									if (frm.fields_dict.packages && frm.fields_dict.packages.grid && frm.fields_dict.packages.grid.grid_rows_by_docname && frm.fields_dict.packages.grid.grid_rows_by_docname[item.name]) {
										frm.fields_dict.packages.grid.grid_rows_by_docname[item.name].refresh_field('volume');
									}
								}
							}
						});
						// Re-aggregate header totals
						frappe.call({
							method: 'logistics.air_freight.doctype.air_booking.air_booking.aggregate_volume_from_packages_api',
							args: { doc: frm.doc },
							freeze: false,
							callback: function(agg) {
								if (agg && !agg.exc && agg.message) {
									if (agg.message.total_volume !== undefined) frm.set_value('volume', agg.message.total_volume);
									if (agg.message.total_weight !== undefined) frm.set_value('total_weight', agg.message.total_weight);
									if (agg.message.chargeable !== undefined) frm.set_value('chargeable', agg.message.chargeable);
								}
							}
						});
					}
				}
			});
		}

		// --- Actions menu ---
		if (!frm.is_new() && !frm.doc.__islocal) {
			if (frm.doc.name && !frm.doc.__islocal && frm.doc.docstatus === 0) {
				frm.add_custom_button(__('Get Charges from Quotation'), function() {
					if (window.logistics && logistics.open_get_charges_from_quotation_dialog) {
						logistics.open_get_charges_from_quotation_dialog(frm);
					} else {
						frappe.msgprint(
							__("Charges dialog is not ready. Please refresh the page and try again.")
						);
					}
				}, __('Action'));
			}
			frm.add_custom_button(__('Get Milestones'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_milestones_from_template',
					args: { doctype: 'Air Booking', docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
						}
					}
				});
			}, __('Action'));
			frm.add_custom_button(__('Get Documents'), function() {
				frappe.call({
					method: 'logistics.document_management.api.populate_documents_from_template',
					args: { doctype: 'Air Booking', docname: frm.doc.name },
					callback: function(r) {
						if (r.message && r.message.added !== undefined) {
							frm.reload_doc();
							frappe.show_alert({ message: __(r.message.message), indicator: 'blue' }, 3);
						}
					}
				});
			}, __('Action'));
			if (frm.doc.charges && frm.doc.charges.length > 0) {
				frm.add_custom_button(__('Calculate Charges'), function() {
					frappe.call({
						method: 'logistics.air_freight.doctype.air_booking.air_booking.recalculate_all_charges',
						args: { docname: frm.doc.name },
						callback: function(r) {
							if (r.message && r.message.success) {
								frm.reload_doc();
								frappe.show_alert({ message: __(r.message.message), indicator: 'green' }, 3);
							}
						}
					});
				}, __('Action'));
			}
		}

		// --- Create menu ---
		if (frm.doc.name && !frm.doc.__islocal && frm.doc.docstatus === 1) {
			setTimeout(function() {
				// Check if Air Shipment already exists
				frappe.db.get_value("Air Shipment", {"air_booking": frm.doc.name}, "name", function(r) {
					if (r && r.name) {
						// Air Shipment exists - show view button
						frm.add_custom_button(__('View Air Shipment'), function() {
							frappe.set_route('Form', 'Air Shipment', r.name);
						}, __('Create'));
					} else {
						// No Air Shipment exists - show convert button
						frm.add_custom_button(__('Shipment'), function() {
							_warn_if_missing_service_charges(frm, "Air");
							frappe.confirm(
								__('Are you sure you want to convert this Air Booking to an Air Shipment?'),
								function() {
									frappe.call({
										method: 'logistics.air_freight.doctype.air_booking.air_booking.convert_to_shipment_api',
										args: { docname: frm.doc.name },
										callback: function(r) {
											if (r.exc) return;
											if (r.message && r.message.success && r.message.air_shipment) {
												var air_shipment_name = r.message.air_shipment;
												frm.reload_doc().then(function() {
													frappe.show_alert({
														message: __('Air Shipment {0} created', [air_shipment_name]),
														indicator: 'green'
													}, 3);
													function try_navigate(attempt) {
														var max_attempts = 15;
														if (attempt > max_attempts) {
															frappe.set_route('Form', 'Air Shipment', air_shipment_name);
															return;
														}
														frappe.call({
															method: "logistics.air_freight.doctype.air_shipment.air_shipment.air_shipment_exists",
															args: { docname: air_shipment_name },
															callback: function(res) {
																if (res.message === true) {
																	frappe.set_route('Form', 'Air Shipment', air_shipment_name);
																} else {
																	setTimeout(function() { try_navigate(attempt + 1); }, 300);
																}
															},
															error: function() {
																setTimeout(function() { try_navigate(attempt + 1); }, 300);
															}
														});
													}
													try_navigate(1);
												});
											}
										}
									});
								}
							);
						}, __('Create'));
					}
				});
			}, 100);
		}
	}
});

frappe.ui.form.on("Air Booking Milestone", {
	actual_start: function(frm) {
		function run() {
			_ensure_air_booking_milestone_actual_end_editable_meta(frm);
		}
		setTimeout(run, 0);
		setTimeout(run, 50);
	},
});

// Setup query filter for quote field based on quote_type
function _setup_quote_query(frm) {
	frm.set_query('quote', function() {
		var quote_type = frm.doc.quote_type;
		if (quote_type === 'Sales Quote') {
			return {
				query: 'logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search',
				filters: {
					service_type: 'Air',
					reference_doctype: 'Air Booking',
					reference_name: frm.doc.name || ''
				}
			};
		} else if (quote_type === 'One-Off Quote') {
			return {
				query: 'logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search',
				filters: {
					service_type: 'Air',
					reference_doctype: 'Air Booking',
					reference_name: frm.doc.name || '',
					dialog_one_off: 1
				}
			};
		}
		return {};
	});
}

function _apply_routing_legs_from_sales_quote_response(frm, r) {
	if (!r.message || !r.message.routing_legs || !r.message.routing_legs.length) {
		return;
	}
	frm.clear_table('routing_legs');
	r.message.routing_legs.forEach(function(leg) {
		var row = frm.add_child('routing_legs');
		Object.keys(leg).forEach(function(key) {
			if (leg[key] !== null && leg[key] !== undefined) {
				row[key] = leg[key];
			}
		});
	});
	frm.refresh_field('routing_legs');
}

function _apply_internal_job_details_from_sales_quote_response(frm, r) {
	if (!r.message || !r.message.internal_job_details || !r.message.internal_job_details.length) {
		return;
	}
	frm.clear_table('internal_job_details');
	r.message.internal_job_details.forEach(function(row) {
		var d = frm.add_child('internal_job_details');
		Object.keys(row).forEach(function(key) {
			if (row[key] !== null && row[key] !== undefined) {
				d[key] = row[key];
			}
		});
	});
	frm.refresh_field('internal_job_details');
}

// Populate charges from quote (handles both Sales Quote and One-Off Quote)
function _populate_charges_from_quote(frm) {
	var docname = frm.is_new() ? null : frm.doc.name;
	var quote_type = frm.doc.quote_type;
	var quote = frm.doc.quote;
	
	// Determine which quote to use
	var target_quote = null;
	var method_name = null;
	var freeze_message = null;
	var success_message_template = null;
	
	if (quote_type === 'Sales Quote' && quote) {
		target_quote = quote;
		method_name = "logistics.air_freight.doctype.air_booking.air_booking.populate_charges_from_sales_quote";
		freeze_message = __("Fetching charges from Sales Quote...");
		success_message_template = __("Successfully populated {0} charges from Sales Quote: {1}");
	} else if (quote_type === 'One-Off Quote' && quote) {
		target_quote = quote;
		method_name = "logistics.air_freight.doctype.air_booking.air_booking.populate_charges_from_one_off_quote";
		freeze_message = __("Fetching charges from One-Off Quote...");
		success_message_template = __("Successfully populated {0} charges from One-Off Quote: {1}");
	}
	
	if (!target_quote || !method_name) {
		frm.clear_table('charges');
		frm.refresh_field('charges');
		return;
	}
	
	// Skip when quote is a temporary name (unsaved document)
	if (String(target_quote).startsWith('new-')) {
		frappe.msgprint({
			title: __("Save Required"),
			message: __("Please save the Sales Quote or One-Off Quote first before selecting it here."),
			indicator: 'orange'
		});
		return;
	}
	
	// Determine which parameter to pass based on the method being called
	var args = {
		docname: docname,
		is_internal_job: frm.doc.is_internal_job || 0,
		main_job_type: frm.doc.main_job_type || "",
		main_job: frm.doc.main_job || ""
	};
	if (method_name.includes('populate_charges_from_sales_quote')) {
		args.sales_quote = target_quote;
	} else if (method_name.includes('populate_charges_from_one_off_quote')) {
		args.one_off_quote = target_quote;
	}
	
	frappe.call({
		method: method_name,
		args: args,
		freeze: true,
		freeze_message: freeze_message,
		callback: function(r) {
			if (r.message) {
				if (!frm.doc.local_customer && r.message.customer) {
					frm.set_value('local_customer', r.message.customer);
				}
				if (r.message.error) {
					frappe.msgprint({
						title: __("Error"),
						message: r.message.error,
						indicator: 'red'
					});
					return;
				}
				_apply_routing_legs_from_sales_quote_response(frm, r);
				_apply_internal_job_details_from_sales_quote_response(frm, r);
				if (r.message.message) {
					frappe.msgprint({
						title: __("No Charges Found"),
						message: r.message.message,
						indicator: 'orange'
					});
				}
				// Update charges on the form (works for both new and saved documents)
				// This avoids "document has been modified" errors by not saving on server
				if (r.message.charges && r.message.charges.length > 0) {
					frm.clear_table('charges');
					r.message.charges.forEach(function(charge) {
						var row = frm.add_child('charges');
						Object.keys(charge).forEach(function(key) {
							if (charge[key] !== null && charge[key] !== undefined) {
								row[key] = charge[key];
							}
						});
					});
					frm.refresh_field('charges');
					if (r.message.charges_count > 0) {
						var message = success_message_template;
						if (quote_type === 'One-Off Quote') {
							message = __("Successfully populated {0} charges from One-Off Quote: {1}", [r.message.charges_count, target_quote]);
						} else {
							message = __("Successfully populated {0} charges from Sales Quote: {1}", [r.message.charges_count, target_quote]);
						}
						frappe.msgprint({
							title: __("Charges Updated"),
							message: message,
							indicator: 'green'
						});
					}
				} else {
					frm.clear_table('charges');
					frm.refresh_field('charges');
					if (
						target_quote &&
						method_name.includes('populate_charges_from_sales_quote') &&
						!_air_internal_job_dialog_handled(frm, target_quote)
					) {
						_prompt_internal_air_job_dialog(frm, target_quote);
					}
				}
			}
		},
		error: function(r) {
			frappe.msgprint({
				title: __("Error"),
				message: __("Failed to populate charges."),
				indicator: 'red'
			});
		}
	});
}

function _air_internal_job_dialog_handled(frm, sales_quote) {
	if (!frm._internal_job_dialog_shown_for_quote) {
		frm._internal_job_dialog_shown_for_quote = {};
	}
	return !!frm._internal_job_dialog_shown_for_quote[sales_quote];
}

function _prompt_internal_air_job_dialog(frm, sales_quote) {
	frm._internal_job_dialog_shown_for_quote = frm._internal_job_dialog_shown_for_quote || {};
	frm._internal_job_dialog_shown_for_quote[sales_quote] = true;
	frappe.db.get_doc("Sales Quote", sales_quote).then(function(sq) {
		var dialog = new frappe.ui.Dialog({
			title: __("Create Internal Job - Air"),
			fields: [
				{ fieldtype: "HTML", fieldname: "context_html" },
				{ fieldtype: "Check", fieldname: "is_internal_job", label: __("Internal Job"), default: 1, read_only: 1 },
				{ fieldtype: "Link", fieldname: "main_job_type", label: __("Main Job Type"), options: "DocType", reqd: 1, default: frm.doc.main_job_type || "" },
				{ fieldtype: "Dynamic Link", fieldname: "main_job", label: __("Main Job"), options: "main_job_type", reqd: 1, default: frm.doc.main_job || "" },
				{ fieldtype: "Link", fieldname: "company", label: __("Company"), options: "Company", default: frm.doc.company || sq.company || "" },
				{ fieldtype: "Link", fieldname: "branch", label: __("Branch"), options: "Branch", default: frm.doc.branch || sq.branch || "" },
				{ fieldtype: "Link", fieldname: "cost_center", label: __("Cost Center"), options: "Cost Center", default: frm.doc.cost_center || sq.cost_center || "" },
				{ fieldtype: "Link", fieldname: "profit_center", label: __("Profit Center"), options: "Profit Center", default: frm.doc.profit_center || sq.profit_center || "" },
				{ fieldtype: "Date", fieldname: "booking_date", label: __("Booking Date"), reqd: 1, default: frm.doc.booking_date || sq.date || frappe.datetime.get_today() }
			],
			primary_action_label: __("Create Internal Job"),
			primary_action: function(values) {
				frm.set_value("is_internal_job", 1);
				frm.set_value("main_job_type", values.main_job_type);
				frm.set_value("main_job", values.main_job);
				frm.set_value("company", values.company || "");
				frm.set_value("branch", values.branch || "");
				frm.set_value("cost_center", values.cost_center || "");
				frm.set_value("profit_center", values.profit_center || "");
				frm.set_value("booking_date", values.booking_date);
				dialog.hide();
				_populate_charges_from_quote(frm);
			}
		});
		dialog.fields_dict.context_html.$wrapper.html(
			'<div class="text-muted">' +
			__("No Air charges were found on Sales Quote <b>{0}</b>. Continue as Internal Job and provide additional details.", [sales_quote]) +
			"</div>"
		);
		dialog.show();
	});
}

// Debounced aggregation when Air Booking Packages volume/weight change (e.g. from dimension edits).
// Prevents freeze-message-container and repeated async calls during length/width/height edits.
function _air_booking_debounced_aggregate_packages(frm) {
	if (frm.is_new() || frm.doc.__islocal) return;
	if (frm.doc.override_volume_weight) return;

	if (frm._packages_aggregate_timer) clearTimeout(frm._packages_aggregate_timer);
	frm._packages_aggregate_timer = setTimeout(function() {
		frm._packages_aggregate_timer = null;
		if (frm.is_new() || frm.doc.__islocal) return;
		// Use frappe.call with freeze: false so dimension edits never show freeze-message-container
		frappe.call({
			method: 'logistics.air_freight.doctype.air_booking.air_booking.aggregate_volume_from_packages_api',
			args: { doc: frm.doc },
			freeze: false,
			callback: function(r) {
				if (r && !r.exc && r.message && frm.doc) {
					if (r.message.total_volume !== undefined) {
						frm.set_value('volume', r.message.total_volume);
						frm.set_value('total_volume', r.message.total_volume);
					}
					if (r.message.total_weight !== undefined) {
						frm.set_value('weight', r.message.total_weight);
						frm.set_value('total_weight', r.message.total_weight);
					}
					if (r.message.chargeable !== undefined) frm.set_value('chargeable', r.message.chargeable);
				}
			}
		});
	}, 300);
}

function _update_measurement_fields_readonly(frm) {
	var readonly = !frm.doc.override_volume_weight;
	if (frm.fields_dict.total_volume) frm.set_df_property('total_volume', 'read_only', readonly);
	if (frm.fields_dict.total_weight) frm.set_df_property('total_weight', 'read_only', readonly);
	if (frm.fields_dict.chargeable) frm.set_df_property('chargeable', 'read_only', readonly);
}

function _air_booking_volume_fallback(frm, cdt, cdn, grid_row) {
	var fn = window.logistics_volume_from_dimensions_fallback;
	if (typeof fn === 'function') fn(frm, cdt, cdn, grid_row, 'packages');
}

// Air Booking Packages: handlers in parent so frm is always parent form when using cdt/cdn (incl. grid form)
frappe.ui.form.on('Air Booking Packages', {
	form_render: function(frm, cdt, cdn) {
		if (!cdt || !cdn) return;
		frm.trigger('packages_on_form_rendered');
		setTimeout(function() {
			var fn_immediate = window.logistics_calculate_volume_from_dimensions_immediate;
			var fn_debounced = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn_immediate === 'function') {
				fn_immediate(frm, cdt, cdn);
			} else if (typeof fn_debounced === 'function') {
				fn_debounced(frm, cdt, cdn);
			} else {
				var grid_row = frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form();
				_air_booking_volume_fallback(frm, cdt, cdn, grid_row);
			}
		}, 50);
	},
	refresh: function(frm) {
		// When grid form is open, frm is child form; get parent for cdt/cdn handlers
		var get_parent = window.logistics_get_parent_form;
		var parent_frm = (frm.doctype === 'Air Booking Packages' && typeof get_parent === 'function')
			? get_parent('Air Booking Packages', frm.doc && frm.doc.name)
			: frm;
		if (!parent_frm) parent_frm = frm;
		setTimeout(function() {
			if (frm.doc && frm.doc.length && frm.doc.width && frm.doc.height) {
				var cdt = frm.doctype || 'Air Booking Packages';
				var cdn = frm.doc.name || frm.doc.__temporary_name || null;
				var fn = window.logistics_calculate_volume_from_dimensions;
				if (cdn && typeof fn === 'function') fn(parent_frm, cdt, cdn);
				else if (cdn) _air_booking_volume_fallback(parent_frm, cdt, cdn, null);
			}
			// Chargeable weight is computed on parent from aggregated packages
		}, 100);
	},
	length: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	width: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	height: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	dimension_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	volume_uom: function(frm, cdt, cdn) {
		var fn = window.logistics_calculate_volume_from_dimensions;
		if (typeof fn === 'function') fn(frm, cdt, cdn);
		else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
	},
	volume: function(frm, cdt, cdn) {
		var row = (cdt && cdn && locals[cdt] && locals[cdt][cdn]) ? locals[cdt][cdn] : (frm && frm.doc ? frm.doc : null);
		if (		row && (!row.volume || row.volume === 0) && row.length && row.width && row.height) {
			var fn = window.logistics_calculate_volume_from_dimensions;
			if (typeof fn === 'function') fn(frm, cdt, cdn);
			else _air_booking_volume_fallback(frm, cdt, cdn, frappe.ui.form.get_open_grid_form && frappe.ui.form.get_open_grid_form());
		}
		_air_booking_debounced_aggregate_packages(frm);
	},
	weight: function(frm, cdt, cdn) {
		_air_booking_debounced_aggregate_packages(frm);
	},
	weight_uom: function(frm, cdt, cdn) {
		_air_booking_debounced_aggregate_packages(frm);
	}
});

