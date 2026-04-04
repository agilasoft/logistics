// Copyright (c) 2026, www.agilasoft.com and contributors
// Create Purchase Invoice dialog: select charges and header details (date, supplier, due date, reference no, etc.)

(function() {
	"use strict";

	function default_due_date(posting_date) {
		if (!posting_date) return "";
		var d = frappe.datetime.str_to_obj(posting_date);
		d.setDate(d.getDate() + 30);
		return frappe.datetime.obj_to_str(d);
	}

	window.show_create_purchase_invoice_dialog = function(frm) {
		if (!frm || !frm.doc || !frm.doc.name) {
			frappe.msgprint({ title: __("Error"), message: __("Please save the document first."), indicator: "red" });
			return;
		}
		if (frm.doc.__islocal) {
			frappe.msgprint({ title: __("Save Required"), message: __("Please save the document before creating Purchase Invoice."), indicator: "orange" });
			return;
		}
		var job_type = frm.doctype;
		var job_name = frm.doc.name;

		frappe.call({
			method: "logistics.invoice_integration.purchase_invoice_api.get_eligible_charges_for_purchase_invoice",
			args: { job_type: job_type, job_name: job_name },
			callback: function(r) {
				if (!r.message) {
					frappe.msgprint({ title: __("Error"), message: __("Could not load charges."), indicator: "red" });
					return;
				}
				var data = r.message;
				var charges = data.eligible_charges || [];
				if (charges.length === 0) {
					frappe.msgprint({
						title: __("No Charges"),
						message: __("No charges with cost amount found. Add cost charges with items before creating Purchase Invoice."),
						indicator: "orange"
					});
					return;
				}

				var default_posting = data.default_posting_date || frappe.datetime.get_today();
				var default_due = default_due_date(default_posting);

				// Build charges table HTML: checkbox, item, cost, qty, pay_to
				var header = [
					'<table class="table table-bordered table-sm">',
					'<thead><tr>',
					'<th style="width:32px"><input type="checkbox" id="pi_dialog_select_all" checked /></th>',
					'<th>' + __("Item") + '</th>',
					'<th class="text-right">' + __("Cost") + '</th>',
					'<th class="text-right">' + __("Qty") + '</th>',
					'<th>' + __("Pay To") + '</th>',
					'</tr></thead>',
					'<tbody id="pi_dialog_charges_tbody">'
				].join("");
				var rows = charges.map(function(c, i) {
					var payTo = c.pay_to || "—";
					return [
						'<tr data-index="' + i + '">',
						'<td><input type="checkbox" class="pi-charge-cb" data-index="' + i + '" checked /></td>',
						'<td>' + (c.item_name || c.item_code || "") + '</td>',
						'<td class="text-right">' + (c.cost != null ? (typeof frappe.format === "function" ? frappe.format(c.cost, { fieldtype: "Currency", options: data.company }) : c.cost.toFixed(2)) : "") + '</td>',
						'<td class="text-right">' + (c.quantity != null ? c.quantity : "") + '</td>',
						'<td>' + payTo + '</td>',
						'</tr>'
					].join("");
				});
				var table_html = header + rows.join("") + "</tbody></table>";

				function normalize_supplier(value) {
					return (value || "").toString().trim();
				}

				var dialog = new frappe.ui.Dialog({
					title: __("Create Purchase Invoice"),
					size: "large",
					fields: [
						{ fieldname: "charges_section", fieldtype: "Section Break", label: __("Charges to Include") },
						{ fieldname: "charges_html", fieldtype: "HTML", options: table_html },
						{ fieldname: "header_section", fieldtype: "Section Break", label: __("Header Details") },
						{ fieldname: "posting_date", fieldtype: "Date", label: __("Posting Date"), default: default_posting },
						{ fieldname: "supplier", fieldtype: "Link", label: __("Supplier"), options: "Supplier", default: data.default_supplier || "" },
						{ fieldname: "due_date", fieldtype: "Date", label: __("Due Date"), default: default_due },
						{ fieldname: "bill_no", fieldtype: "Data", label: __("Supplier Bill No"), description: __("Reference number from supplier invoice") },
						{ fieldname: "bill_date", fieldtype: "Date", label: __("Supplier Bill Date") }
					],
					primary_action_label: __("Create Purchase Invoice"),
					primary_action: function(values) {
						var indices = [];
						dialog.$wrapper.find("input.pi-charge-cb:checked").each(function() {
							indices.push(parseInt($(this).attr("data-index"), 10));
						});
						indices.sort(function(a, b) { return a - b; });
						if (indices.length === 0) {
							frappe.msgprint({ title: __("Select Charges"), message: __("Select at least one charge to include."), indicator: "orange" });
							return;
						}
						if (!values.supplier) {
							frappe.msgprint({ title: __("Supplier Required"), message: __("Please select a supplier."), indicator: "red" });
							return;
						}
						dialog.hide();
						frappe.call({
							method: "logistics.invoice_integration.purchase_invoice_api.create_purchase_invoice",
							args: {
								job_type: job_type,
								job_name: job_name,
								supplier: values.supplier,
								posting_date: values.posting_date || undefined,
								due_date: values.due_date || undefined,
								bill_no: values.bill_no || undefined,
								bill_date: values.bill_date || undefined,
								selected_charge_indices: JSON.stringify(indices)
							},
							callback: function(create_r) {
								if (create_r.message && create_r.message.ok) {
									frappe.show_alert({ message: create_r.message.message, indicator: "green" });
									if (frm.reload_doc) frm.reload_doc();
									if (create_r.message.purchase_invoice) {
										frappe.set_route("Form", "Purchase Invoice", create_r.message.purchase_invoice);
									}
								} else {
									frappe.msgprint({
										title: __("Error"),
										message: (create_r.message && create_r.message.message) || (create_r.exc && create_r.exc.join("\n")) || __("Failed to create Purchase Invoice"),
										indicator: "red"
									});
								}
							}
						});
					}
				});

				function apply_supplier_filter(selectedSupplier) {
					var supplier = normalize_supplier(selectedSupplier);
					var hasVisibleRows = false;

					dialog.$wrapper.find("#pi_dialog_charges_tbody tr").each(function() {
						var row = $(this);
						var idx = parseInt(row.attr("data-index"), 10);
						var charge = charges[idx] || {};
						var payTo = normalize_supplier(charge.pay_to);
						var matches = !supplier || payTo === supplier;
						var checkbox = row.find("input.pi-charge-cb");

						row.toggle(matches);
						checkbox.prop("disabled", !matches);
						if (!matches) checkbox.prop("checked", false);
						if (matches) hasVisibleRows = true;
					});

					var allVisibleChecked = true;
					var visibleCount = 0;
					dialog.$wrapper.find("input.pi-charge-cb:visible").each(function() {
						visibleCount += 1;
						if (!$(this).prop("checked")) allVisibleChecked = false;
					});
					dialog.$wrapper.find("#pi_dialog_select_all").prop("checked", visibleCount > 0 && allVisibleChecked);

					return hasVisibleRows;
				}

				var noChargesMessage = $('<div class="text-muted small mt-2" id="pi_dialog_no_supplier_rows" style="display:none;"></div>');
				noChargesMessage.text(__("No charges found for the selected supplier."));
				dialog.fields_dict.charges_html.$wrapper.append(noChargesMessage);

				var supplierField = dialog.get_field("supplier");
				if (supplierField) {
					supplierField.df.onchange = function() {
						var selected = dialog.get_value("supplier");
						var hasVisibleRows = apply_supplier_filter(selected);
						noChargesMessage.toggle(!hasVisibleRows);
					};
				}

				// Select all / deselect all
				dialog.$wrapper.find("#pi_dialog_select_all").on("change", function() {
					var checked = $(this).prop("checked");
					dialog.$wrapper.find("input.pi-charge-cb:visible:not(:disabled)").prop("checked", checked);
				});

				dialog.$wrapper.on("change", "input.pi-charge-cb", function() {
					var visible = dialog.$wrapper.find("input.pi-charge-cb:visible:not(:disabled)");
					var checkedVisible = dialog.$wrapper.find("input.pi-charge-cb:visible:not(:disabled):checked");
					dialog.$wrapper.find("#pi_dialog_select_all").prop("checked", visible.length > 0 && visible.length === checkedVisible.length);
				});

				var initialHasRows = apply_supplier_filter(data.default_supplier || "");
				noChargesMessage.toggle(!initialHasRows);

				dialog.show();
			}
		});
	};

	// Make charge rows read-only when Cost Invoice Status is Requested, Posted, or Paid (avoid duplicate posting)
	function set_requested_charge_rows_readonly(frm) {
		if (!frm || !frm.doc) return;
		var charges_field = "charges";
		if (!frm.fields_dict[charges_field] || !frm.doc[charges_field] || !frm.doc[charges_field].length) return;
		var costLocked = ["Requested", "Invoiced", "Posted", "Paid"];
		var revenueLocked = ["Requested", "Posted", "Paid"];
		frm.doc[charges_field].forEach(function(row) {
			if (costLocked.indexOf(row.purchase_invoice_status) !== -1 || revenueLocked.indexOf(row.sales_invoice_status) !== -1) {
				row.__read_only = 1;
			}
		});
		if (frm.fields_dict[charges_field].grid && frm.fields_dict[charges_field].grid.grid_rows) {
			frm.fields_dict[charges_field].grid.grid_rows.forEach(function(grid_row) {
				if (grid_row.doc && (
					costLocked.indexOf(grid_row.doc.purchase_invoice_status) !== -1 ||
					revenueLocked.indexOf(grid_row.doc.sales_invoice_status) !== -1
				)) {
					grid_row.doc.__read_only = 1;
					if (grid_row.open_form_button) grid_row.open_form_button.toggle(false);
				}
			});
		}
	}

	var JOB_DOCTYPES_FOR_PI = ["Transport Job", "Air Shipment", "Sea Shipment", "Warehouse Job", "Declaration"];
	JOB_DOCTYPES_FOR_PI.forEach(function(doctype) {
		frappe.ui.form.on(doctype, {
			refresh: function(frm) {
				set_requested_charge_rows_readonly(frm);
			}
		});
	});
})();
