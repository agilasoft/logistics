// Copyright (c) 2026, www.agilasoft.com and contributors
// Create Sales Invoice dialog: header (date, customer, invoice type, etc.) and charge selection.
// Charges are pre-filtered based on header details (e.g. customer/bill_to, invoice type).

(function() {
	"use strict";

	function build_charges_table(charges, company) {
		var header = [
			'<table class="table table-bordered table-sm">',
			'<thead><tr>',
			'<th style="width:32px"><input type="checkbox" id="si_dialog_select_all" checked /></th>',
			'<th>' + __("Item") + '</th>',
			'<th class="text-right">' + __("Revenue") + '</th>',
			'<th class="text-right">' + __("Qty") + '</th>',
			'</tr></thead>',
			'<tbody id="si_dialog_charges_tbody">'
		].join("");
		var rows = (charges || []).map(function(c, i) {
			return [
				'<tr data-index="' + i + '">',
				'<td><input type="checkbox" class="si-charge-cb" data-index="' + i + '" checked /></td>',
				'<td>' + (c.item_name || c.item_code || "") + '</td>',
				'<td class="text-right">' + (c.revenue != null ? (typeof frappe.format === "function" ? frappe.format(c.revenue, { fieldtype: "Currency", options: company }) : c.revenue.toFixed(2)) : "") + '</td>',
				'<td class="text-right">' + (c.quantity != null ? c.quantity : "") + '</td>',
				'</tr>'
			].join("");
		});
		return header + rows.join("") + "</tbody></table>";
	}

	window.show_create_sales_invoice_dialog = function(frm) {
		if (!frm || !frm.doc || !frm.doc.name) {
			frappe.msgprint({ title: __("Error"), message: __("Please save the document first."), indicator: "red" });
			return;
		}
		if (frm.doc.__islocal) {
			frappe.msgprint({ title: __("Save Required"), message: __("Please save the document before creating Sales Invoice."), indicator: "orange" });
			return;
		}
		var job_type = frm.doctype;
		var job_name = frm.doc.name;
		var dialog;
		var current_eligible = [];

		function fetch_charges(customer, invoice_type, then) {
			frappe.call({
				method: "logistics.invoice_integration.sales_invoice_api.get_eligible_charges_for_sales_invoice",
				args: {
					job_type: job_type,
					job_name: job_name,
					customer: customer || undefined,
					invoice_type: invoice_type || undefined
				},
				callback: function(r) {
					if (!r.message) {
						if (then) then(null);
						return;
					}
					current_eligible = r.message.eligible_charges || [];
					if (then) then(r.message);
				}
			});
		}

		// First fetch with no filter to get defaults
		fetch_charges(null, null, function(data) {
			if (!data) {
				frappe.msgprint({ title: __("Error"), message: __("Could not load charges."), indicator: "red" });
				return;
			}
			var default_customer = data.default_customer || "";
			var default_posting = data.default_posting_date || frappe.datetime.get_today();
			var has_invoice_type = data.has_invoice_type;
			var company = data.company;
			// Second fetch pre-filtered by default customer so initial table is already filtered
			function build_dialog_with_charges(chargeData) {
				current_eligible = (chargeData && chargeData.eligible_charges) ? chargeData.eligible_charges : data.eligible_charges || [];

				var fields = [
					{ fieldname: "header_section", fieldtype: "Section Break", label: __("Header Details") },
					{ fieldname: "posting_date", fieldtype: "Date", label: __("Invoice Date"), default: default_posting, reqd: 1 },
					{ fieldname: "customer", fieldtype: "Link", label: __("Customer"), options: "Customer", default: default_customer, reqd: 1 },
					{ fieldname: "tax_category", fieldtype: "Link", label: __("Tax Category"), options: "Tax Category" }
				];
				if (has_invoice_type) {
					fields.push({ fieldname: "invoice_type", fieldtype: "Link", label: __("Invoice Type"), options: "Invoice Type" });
				}
				fields.push(
					{ fieldname: "charges_section", fieldtype: "Section Break", label: __("Charges to Include") },
					{ fieldname: "charges_html", fieldtype: "HTML", options: build_charges_table(current_eligible, company) }
				);

			dialog = new frappe.ui.Dialog({
				title: __("Create Sales Invoice"),
				size: "large",
				fields: fields,
				primary_action_label: __("Create Sales Invoice"),
				primary_action: function(values) {
					var indices = [];
					dialog.$wrapper.find("input.si-charge-cb:checked").each(function() {
						indices.push(parseInt($(this).attr("data-index"), 10));
					});
					indices.sort(function(a, b) { return a - b; });
					if (indices.length === 0) {
						frappe.msgprint({ title: __("Select Charges"), message: __("Select at least one charge to include."), indicator: "orange" });
						return;
					}
					if (!values.customer) {
						frappe.msgprint({ title: __("Customer Required"), message: __("Please select a customer."), indicator: "red" });
						return;
					}
					dialog.hide();
					frappe.call({
						method: "logistics.invoice_integration.sales_invoice_api.create_sales_invoice_from_job",
						args: {
							job_type: job_type,
							job_name: job_name,
							customer: values.customer,
							posting_date: values.posting_date,
							invoice_type: values.invoice_type || undefined,
							tax_category: values.tax_category || undefined,
							selected_charge_indices: JSON.stringify(indices)
						},
						callback: function(create_r) {
							if (create_r.message && create_r.message.ok) {
								frappe.show_alert({ message: create_r.message.message, indicator: "green" });
								if (frm.reload_doc) frm.reload_doc();
								if (create_r.message.sales_invoice) {
									frappe.set_route("Form", "Sales Invoice", create_r.message.sales_invoice);
								}
							} else {
								frappe.msgprint({
									title: __("Error"),
									message: (create_r.message && create_r.message.message) || (create_r.exc && create_r.exc.join("\n")) || __("Failed to create Sales Invoice"),
									indicator: "red"
								});
							}
						}
					});
				}
			});

			// When customer or invoice_type changes, refetch charges (pre-filter) and refresh table
			function refetch_and_refresh() {
				var customer = dialog.get_value("customer");
				var invoice_type = dialog.get_value("invoice_type");
				frappe.call({
					method: "logistics.invoice_integration.sales_invoice_api.get_eligible_charges_for_sales_invoice",
					args: {
						job_type: job_type,
						job_name: job_name,
						customer: customer || undefined,
						invoice_type: invoice_type || undefined
					},
					callback: function(r) {
						if (r.message && r.message.eligible_charges) {
							current_eligible = r.message.eligible_charges;
							var company = r.message.company || company;
							var $table = dialog.$wrapper.find("#si_dialog_charges_tbody").closest("table");
							if ($table.length) {
								$table.parent().html(build_charges_table(current_eligible, company));
								dialog.$wrapper.find("#si_dialog_select_all").prop("checked", true);
								dialog.$wrapper.find("input.si-charge-cb").prop("checked", true);
								dialog.$wrapper.find("#si_dialog_select_all").off("change").on("change", function() {
									var checked = $(this).prop("checked");
									dialog.$wrapper.find("input.si-charge-cb").prop("checked", checked);
								});
							}
						}
					}
				});
			}

			dialog.show();
			dialog.$wrapper.find("[data-fieldname='customer']").on("change", refetch_and_refresh);
			if (has_invoice_type) {
				dialog.$wrapper.find("[data-fieldname='invoice_type']").on("change", refetch_and_refresh);
			}

			dialog.$wrapper.find("#si_dialog_select_all").on("change", function() {
				var checked = $(this).prop("checked");
				dialog.$wrapper.find("input.si-charge-cb").prop("checked", checked);
			});
			}
			// Pre-filter by default customer, then build dialog
			if (default_customer) {
				fetch_charges(default_customer, null, function(filtered) {
					build_dialog_with_charges(filtered || data);
				});
			} else {
				build_dialog_with_charges(data);
			}
		});
	};
})();
