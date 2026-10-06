// Copyright (c) 2026, Agilasoft and contributors

frappe.ui.form.on("Sales Quote Pack", {
	refresh(frm) {
		frm.set_query("sales_quote", "quotations", function () {
			const filters = {
				customer: frm.doc.customer || "",
			};
			if (frm._pack_quotation_type) {
				filters.quotation_type = frm._pack_quotation_type;
			}
			return { filters };
		});
		sync_pack_quotation_type(frm);
	},

	quotations_remove(frm) {
		sync_pack_quotation_type(frm);
	},
});

frappe.ui.form.on("Sales Quote Pack Line", {
	sales_quote(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.sales_quote) {
			sync_pack_quotation_type(frm);
			return;
		}
		frappe.db.get_value("Sales Quote", row.sales_quote, "quotation_type").then((r) => {
			const quotation_type = (r.message && r.message.quotation_type) || "";
			const others = (frm.doc.quotations || []).filter(
				(line) => line.name !== row.name && line.sales_quote
			);
			if (
				frm._pack_quotation_type &&
				quotation_type &&
				frm._pack_quotation_type !== quotation_type &&
				others.length
			) {
				const selected = row.sales_quote;
				const locked = frm._pack_quotation_type;
				frappe.model.set_value(cdt, cdn, "sales_quote", "");
				frappe.msgprint({
					title: __("Cannot Mix Quotation Types"),
					indicator: "red",
					message: __(
						"Sales Quote {0} is {1}. This pack already includes {2} quotes.",
						[selected, quotation_type, locked]
					),
				});
				return;
			}
			if (quotation_type && !others.length) {
				frm._pack_quotation_type = quotation_type;
			}
			bind_add_sales_quote(frm);
		});
	},
});

function quote_names(frm) {
	return [...new Set((frm.doc.quotations || []).map((row) => row.sales_quote).filter(Boolean))];
}

function sync_pack_quotation_type(frm) {
	const names = quote_names(frm);
	if (!names.length) {
		frm._pack_quotation_types = [];
		frm._pack_quotation_type = null;
		bind_add_sales_quote(frm);
		return;
	}
	frappe.db
		.get_list("Sales Quote", {
			filters: { name: ["in", names] },
			fields: ["quotation_type"],
			limit: names.length,
		})
		.then((rows) => {
			const types = [...new Set((rows || []).map((row) => row.quotation_type).filter(Boolean))];
			frm._pack_quotation_types = types;
			frm._pack_quotation_type = types.length === 1 ? types[0] : null;
			bind_add_sales_quote(frm);
		});
}

function bind_add_sales_quote(frm) {
	if (frm.is_new()) {
		return;
	}
	if ((frm._pack_quotation_types || []).length > 1) {
		return;
	}
	if (frm._pack_quotation_type && frm._pack_quotation_type !== "One-off") {
		return;
	}
	logistics.menu.add(frm, {
		label: __("Add Sales Quote"),
		doctype: "Sales Quote",
		ptype: "create",
		action: () => {
			if (frm.is_dirty()) {
				frappe.msgprint(__("Save the Sales Quote Pack before adding a Sales Quote."));
				return;
			}
			frappe.call({
				method: "logistics.pricing_center.doctype.sales_quote_pack.sales_quote_pack.create_sales_quote_from_pack",
				args: { pack_name: frm.doc.name },
				callback(r) {
					if (r.message) {
						frappe.set_route("Form", "Sales Quote", r.message);
					}
				},
			});
		},
	});
}
