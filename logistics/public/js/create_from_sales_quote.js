// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Make functions globally available
frappe.provide("logistics.transport");
frappe.provide("logistics.air_freight");
frappe.provide("logistics.sea_freight");

// Function to open dialog for creating Transport Order from Sales Quote
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
						filters: {
							one_off: 1,
							docstatus: 1,
							transport: ["!=", ""]
						}
					};
				}
			}
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			if (!values.sales_quote) {
				frappe.msgprint({
					title: __("Error"),
					message: __("Please select a Sales Quote"),
					indicator: "red"
				});
				return;
			}

			d.hide();
			frappe.show_alert({
				message: __("Creating Transport Order..."),
				indicator: "blue"
			});

			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_transport_order_from_sales_quote",
				args: {
					sales_quote_name: values.sales_quote
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __("Transport Order Created"),
							message: __("Transport Order {0} has been created successfully.", [r.message.transport_order]),
							indicator: "green"
						});
						frappe.set_route("Form", "Transport Order", r.message.transport_order);
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						if (r.message.transport_order) {
							frappe.set_route("Form", "Transport Order", r.message.transport_order);
						}
					}
				},
				error: function(r) {
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Transport Order. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	});
	d.show();
};

// Function to open dialog for creating Air Booking from Sales Quote
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
						filters: {
							one_off: 1,
							docstatus: 1,
							air_freight: ["!=", ""]
						}
					};
				}
			}
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			if (!values.sales_quote) {
				frappe.msgprint({
					title: __("Error"),
					message: __("Please select a Sales Quote"),
					indicator: "red"
				});
				return;
			}

			d.hide();
			frappe.show_alert({
				message: __("Creating Air Booking..."),
				indicator: "blue"
			});

			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_air_booking_from_sales_quote",
				args: {
					sales_quote_name: values.sales_quote
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __("Air Booking Created"),
							message: __("Air Booking {0} has been created successfully.", [r.message.air_booking]),
							indicator: "green"
						});
						frappe.set_route("Form", "Air Booking", r.message.air_booking);
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						if (r.message.air_booking) {
							frappe.set_route("Form", "Air Booking", r.message.air_booking);
						}
					}
				},
				error: function(r) {
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Air Booking. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	});
	d.show();
};

// Function to open dialog for creating Sea Booking from Sales Quote
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
						filters: {
							one_off: 1,
							docstatus: 1,
							sea_freight: ["!=", ""]
						}
					};
				}
			}
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			if (!values.sales_quote) {
				frappe.msgprint({
					title: __("Error"),
					message: __("Please select a Sales Quote"),
					indicator: "red"
				});
				return;
			}

			d.hide();
			frappe.show_alert({
				message: __("Creating Sea Booking..."),
				indicator: "blue"
			});

			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote.sales_quote.create_sea_booking_from_sales_quote",
				args: {
					sales_quote_name: values.sales_quote
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __("Sea Booking Created"),
							message: __("Sea Booking {0} has been created successfully.", [r.message.sea_booking]),
							indicator: "green"
						});
						frappe.set_route("Form", "Sea Booking", r.message.sea_booking);
					} else if (r.message && r.message.message) {
						frappe.msgprint({
							title: __("Information"),
							message: r.message.message,
							indicator: "blue"
						});
						if (r.message.sea_booking) {
							frappe.set_route("Form", "Sea Booking", r.message.sea_booking);
						}
					}
				},
				error: function(r) {
					frappe.msgprint({
						title: __("Error"),
						message: __("Failed to create Sea Booking. Please try again."),
						indicator: "red"
					});
				}
			});
		}
	});
	d.show();
};


