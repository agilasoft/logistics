// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Special Project Request", {
	refresh: function (frm) {
		if (frm.doc.special_project) {
			frm.add_custom_button(__("Link Existing Order"), () => link_existing_order(frm));
		}
		if (frm.doc.special_project && frm.doc.product_requests && frm.doc.product_requests.length) {
			const has_inbound = frm.doc.product_requests.some((r) => r.fulfillment_type === "Inbound");
			const has_release = frm.doc.product_requests.some((r) => r.fulfillment_type === "Release");
			const has_transport = frm.doc.product_requests.some((r) => r.fulfillment_type === "Transport");
			const has_air = frm.doc.product_requests.some((r) => r.fulfillment_type === "Air Freight");
			const has_sea = frm.doc.product_requests.some((r) => r.fulfillment_type === "Sea Freight");
			const has_transfer = frm.doc.product_requests.some((r) => r.fulfillment_type === "Transfer");

			if (has_inbound) {
				frm.add_custom_button(__("Create Inbound Order"), () => create_order(frm, "create_inbound_order_from_request"));
			}
			if (has_release) {
				frm.add_custom_button(__("Create Release Order"), () => create_order(frm, "create_release_order_from_request"));
			}
			if (has_transport) {
				frm.add_custom_button(__("Create Transport Order"), () => create_order(frm, "create_transport_order_from_request"));
			}
			if (has_air) {
				frm.add_custom_button(__("Create Air Booking"), () => create_order(frm, "create_air_booking_from_request"));
			}
			if (has_sea) {
				frm.add_custom_button(__("Create Sea Booking"), () => create_order(frm, "create_sea_booking_from_request"));
			}
			if (has_transfer) {
				frm.add_custom_button(__("Create Transfer Order"), () => create_order(frm, "create_transfer_order_from_request"));
			}
		}
	},
});

function create_order(frm, method) {
	const args = { special_project_request: frm.doc.name };
	frappe.call({
		method: `logistics.special_projects.doctype.special_project_request.special_project_request_api.${method}`,
		args: args,
		callback: function (r) {
			if (r.message && r.message.order_name) {
				frappe.msgprint({
					title: __("Order Created"),
					message: __("Created {0}: {1}", [r.message.order_type, r.message.order_name]),
					indicator: "green",
				});
				frm.reload_doc();
			}
		},
	});
}

function link_existing_order(frm) {
	const order_doctypes = [
		"Transport Order", "Air Booking", "Sea Booking",
		"Inbound Order", "Release Order", "Transfer Order", "VAS Order",
	];
	frappe.prompt(
		[
			{ fieldname: "reference_doctype", fieldtype: "Select", label: __("DocType"), options: order_doctypes.join("\n"), reqd: 1 },
			{ fieldname: "reference_doc", fieldtype: "Data", label: __("Document Name"), description: __("Enter the document name (e.g. TO-00001, ABK-00001)"), reqd: 1 },
		],
		(values) => {
			frappe.call({
				method: "logistics.special_projects.doctype.special_project_request.special_project_request_api.link_existing_order_to_request",
				args: {
					special_project_request: frm.doc.name,
					reference_doctype: values.reference_doctype,
					reference_doc: values.reference_doc,
				},
				callback: function (r) {
					if (r.message && r.message.linked) {
						frappe.msgprint({
							title: __("Order Linked"),
							message: __("Project {0} set on document.", [r.message.project]),
							indicator: "green",
						});
						frm.reload_doc();
					} else {
						frappe.msgprint({
							title: __("Link Failed"),
							message: r.message?.message || __("Could not link order."),
							indicator: "red",
						});
					}
				},
			});
		},
		__("Link Existing Order"),
	);
}
