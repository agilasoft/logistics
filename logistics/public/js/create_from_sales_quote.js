// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Create order/booking from Sales Quote (One-off type)
frappe.provide("logistics.transport");
frappe.provide("logistics.air_freight");
frappe.provide("logistics.sea_freight");

/**
 * Navigate to the freshly created booking/order. Wraps
 * ``window.logistics_navigate_when_doc_exists`` (defined in internal_job_create_from_source.js,
 * which is loaded via app_include_js) so the new form is only loaded once the row is visible
 * to the next request. Prevents the spurious "<Doctype> ... not found" the desk shows when
 * ``frappe.set_route`` races the DB commit / replica visibility for the just-inserted row.
 *
 * Falls back to a direct ``frappe.set_route`` if the helper isn't loaded (e.g. older bundle).
 */
function _logistics_set_route_when_exists(doctype, docname, after) {
	function is_valid_docname(name) {
		if (name == null) {
			return false;
		}
		var s = String(name).trim().toLowerCase();
		return s && s !== "undefined" && s !== "null" && s !== "none" && s !== "new";
	}
	function navigate() {
		if (!is_valid_docname(docname)) {
			return;
		}
		// Clear any cached document data before navigating to ensure fresh load
		if (frappe.model && frappe.model.clear_doc) {
			frappe.model.clear_doc(doctype, docname);
		}
		frappe.set_route("Form", doctype, docname);
		if (typeof after === "function") {
			after();
		}
	}
	if (!is_valid_docname(docname)) {
		return;
	}
	if (window.logistics_navigate_when_doc_exists) {
		window.logistics_navigate_when_doc_exists(doctype, docname, navigate);
	} else {
		navigate();
	}
}

logistics.transport.create_transport_order_from_sales_quote = function() {
	const d = new frappe.ui.Dialog({
		title: __("Create Transport Order from Sales Quote"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "sales_quote",
				label: __("Sales Quote"),
				options: "Sales Quote",
				reqd: 1,
				get_query: function() {
					return {
						query: "logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search",
						filters: {
							service_type: "Transport",
							dialog_one_off: 1
						}
					};
				}
			}
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			if (!values.sales_quote) return;
			d.hide();
			frappe.show_alert({ message: __("Creating Transport Order..."), indicator: "blue" });
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_transport_order_from_sales_quote",
				args: { sales_quote_name: values.sales_quote },
				callback: function(r) {
					if (r.exc) return;
					if (r.message && r.message.success && r.message.transport_order) {
						frappe.msgprint({ title: __("Transport Order Created"), message: r.message.message, indicator: "green" });
						// Existence-poll before set_route — see _logistics_set_route_when_exists.
						_logistics_set_route_when_exists("Transport Order", r.message.transport_order, function () {
							frappe.model.with_doctype("Transport Order", function () {
								var meta = frappe.get_meta("Transport Order");
								if (meta && meta.module) {
									frappe.breadcrumbs.add(meta.module, "Transport Order");
								}
							});
						});
					}
				},
				error: function() {
					frappe.msgprint({ title: __("Error"), message: __("Failed to create Transport Order."), indicator: "red" });
				}
			});
		}
	});
	d.show();
};

logistics.air_freight.create_air_booking_from_sales_quote = function() {
	const d = new frappe.ui.Dialog({
		title: __("Create Air Booking from Sales Quote"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "sales_quote",
				label: __("Sales Quote"),
				options: "Sales Quote",
				reqd: 1,
				get_query: function() {
					return {
						query: "logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search",
						filters: {
							service_type: "Air",
							dialog_one_off: 1
						}
					};
				}
			}
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			if (!values.sales_quote) return;
			d.hide();
			frappe.show_alert({ message: __("Creating Air Booking..."), indicator: "blue" });
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_air_booking_from_sales_quote",
				args: { sales_quote_name: values.sales_quote },
				callback: function(r) {
					if (r.exc) return;
					if (r.message && r.message.success && r.message.air_booking) {
						frappe.msgprint({ title: __("Air Booking Created"), message: r.message.message, indicator: "green" });
						// Existence-poll before set_route — see _logistics_set_route_when_exists.
						_logistics_set_route_when_exists("Air Booking", r.message.air_booking);
					}
				},
				error: function() {
					frappe.msgprint({ title: __("Error"), message: __("Failed to create Air Booking."), indicator: "red" });
				}
			});
		}
	});
	d.show();
};

logistics.sea_freight.create_sea_booking_from_sales_quote = function() {
	const d = new frappe.ui.Dialog({
		title: __("Create Sea Booking from Sales Quote"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "sales_quote",
				label: __("Sales Quote"),
				options: "Sales Quote",
				reqd: 1,
				get_query: function() {
					return {
						query: "logistics.utils.sales_quote_link_query.sales_quote_by_service_link_search",
						filters: {
							service_type: "Sea",
							dialog_one_off: 1
						}
					};
				}
			}
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			if (!values.sales_quote) return;
			d.hide();
			frappe.show_alert({ message: __("Creating Sea Booking..."), indicator: "blue" });
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_sea_booking_from_sales_quote",
				args: { sales_quote_name: values.sales_quote },
				callback: function(r) {
					if (r.exc) return;
					if (r.message && r.message.success && r.message.sea_booking) {
						frappe.msgprint({ title: __("Sea Booking Created"), message: r.message.message, indicator: "green" });
						// Existence-poll before set_route — see _logistics_set_route_when_exists.
						_logistics_set_route_when_exists("Sea Booking", r.message.sea_booking);
					}
				},
				error: function() {
					frappe.msgprint({ title: __("Error"), message: __("Failed to create Sea Booking."), indicator: "red" });
				}
			});
		}
	});
	d.show();
};
