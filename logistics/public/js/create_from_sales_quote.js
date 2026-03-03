// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

// Create order/booking from Sales Quote (One-off type)
frappe.provide("logistics.transport");
frappe.provide("logistics.air_freight");
frappe.provide("logistics.sea_freight");

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
							quotation_type: "One-off",
							is_transport: 1,
							status: ["not in", ["Converted", "Lost", "Expired"]]
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
						setTimeout(function() {
							frappe.set_route("Form", "Transport Order", r.message.transport_order);
						}, 100);
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
						filters: {
							quotation_type: "One-off",
							is_air: 1,
							status: ["not in", ["Converted", "Lost", "Expired"]]
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
						setTimeout(function() {
							frappe.set_route("Form", "Air Booking", r.message.air_booking);
						}, 100);
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
						filters: {
							quotation_type: "One-off",
							is_sea: 1,
							status: ["not in", ["Converted", "Lost", "Expired"]]
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
						setTimeout(function() {
							frappe.set_route("Form", "Sea Booking", r.message.sea_booking);
						}, 100);
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
