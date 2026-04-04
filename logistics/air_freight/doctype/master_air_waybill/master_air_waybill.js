// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Master Air Waybill", {
	refresh(frm) {
		// On new doc, offer "Issue from Stock" so user gets a MAWB from stock instead of manual entry
		if (frm.doc.__islocal) {
			frm.add_custom_button(__("Issue from Stock"), function () {
				issue_mawb_from_stock_and_open(frm);
			}, __("Action"));
		}
	},
});

// List view: add "Issue from Stock" button
frappe.listview_settings["Master Air Waybill"] = {
	add_fields: [],
	get_indicator: function () {},
	onload: function (listview) {
		listview.page.add_menu_item(__("Issue from Stock"), function () {
			issue_mawb_from_stock_dialog(listview);
		});
	},
};

function issue_mawb_from_stock_dialog(listview) {
	const d = new frappe.ui.Dialog({
		title: __("Issue MAWB from Stock"),
		fields: [
			{
				label: __("Airline"),
				fieldname: "airline",
				fieldtype: "Link",
				options: "Airline",
			},
			{
				label: __("Company"),
				fieldname: "company",
				fieldtype: "Link",
				options: "Company",
			},
			{
				label: __("MAWB Stock Range"),
				fieldname: "stock_range_name",
				fieldtype: "Link",
				options: "MAWB Stock Range",
				description: __("Leave blank to use default from Air Freight Settings"),
			},
		],
		primary_action_label: __("Issue"),
		primary_action: function (values) {
			d.hide();
			call_issue_mawb_from_stock(values, function (mawb_name) {
				listview.refresh();
				frappe.set_route("Form", "Master Air Waybill", mawb_name);
			});
		},
	});
	d.show();
}

function issue_mawb_from_stock_and_open(frm) {
	const opts = {};
	if (frm.doc.airline) opts.airline = frm.doc.airline;
	if (frm.doc.company) opts.company = frm.doc.company;
	call_issue_mawb_from_stock(opts, function (mawb_name) {
		frappe.set_route("Form", "Master Air Waybill", mawb_name);
	});
}

function call_issue_mawb_from_stock(opts, callback) {
	frappe.call({
		method: "logistics.air_freight.doctype.mawb_stock_range.mawb_stock_range.issue_mawb_from_stock",
		args: opts,
		callback: function (r) {
			if (r.exc) {
				frappe.msgprint({
					title: __("Cannot issue MAWB from stock"),
					indicator: "red",
					message: r.message || (r._server_messages && r._server_messages.join("\n")) || __("No MAWB Stock Range found. Create a MAWB Stock Range and set a default in Air Freight Settings, or select a range when issuing."),
				});
				return;
			}
			const result = r.message;
			if (result && result.mawb_name) {
				frappe.show_alert({ message: __("Issued MAWB: {0}", [result.master_awb_no]), indicator: "green" });
				if (callback) callback(result.mawb_name);
			}
		},
	});
}
