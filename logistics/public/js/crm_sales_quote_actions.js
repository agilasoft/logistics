// Copyright (c) 2026, Agilasoft and contributors
// Shared CRM actions: route Create / connections from Quotation to Sales Quote.

frappe.provide("logistics.crm_sales_quote");

const LOGISTICS_SALES_QUOTE_METHODS = {
	Opportunity: "logistics.pricing_center.crm_sales_quote.make_sales_quote_from_opportunity",
	Lead: "logistics.pricing_center.crm_sales_quote.make_sales_quote_from_lead",
	Prospect: "logistics.pricing_center.crm_sales_quote.make_sales_quote_from_prospect",
	Customer: "logistics.pricing_center.crm_sales_quote.make_sales_quote_from_customer",
};

function logistics_open_sales_quote_from_crm(frm) {
	const method = LOGISTICS_SALES_QUOTE_METHODS[frm.doctype];
	if (!method) {
		return;
	}
	frappe.model.open_mapped_doc({ method, frm });
}

function logistics_should_show_crm_sales_quote_button(frm) {
	if (!frm || frm.is_new() || frm.doc.docstatus === 1) {
		return false;
	}
	const onload = frm.doc.__onload || {};
	if (frm.doctype === "Lead") {
		if (onload.is_customer) {
			return true;
		}
		return !!onload.logistics_allow_sales_quote_from_lead;
	}
	if (frm.doctype === "Prospect") {
		if (onload.logistics_is_customer) {
			return true;
		}
		return !!onload.logistics_allow_sales_quote_from_prospect;
	}
	return true;
}

function logistics_replace_quotation_create_button(frm) {
	if (!frm || frm.is_new()) {
		return;
	}
	frm.remove_custom_button(__("Quotation"), __("Create"));
	if (!logistics_should_show_crm_sales_quote_button(frm)) {
		return;
	}
	if (window.logistics && logistics.menu) {
		logistics.menu.add(frm, {
			label: __("Sales Quote"),
			group: __("Create"),
			doctype: "Sales Quote",
			ptype: "create",
			action: function () {
				logistics_open_sales_quote_from_crm(frm);
			},
		});
		return;
	}
	frm.add_custom_button(__("Sales Quote"), () => logistics_open_sales_quote_from_crm(frm), __("Create"));
}

function logistics_replace_quotation_make_methods(frm) {
	if (!frm) {
		return;
	}
	frm.make_methods = frm.make_methods || {};
	frm.make_methods["Sales Quote"] = () => logistics_open_sales_quote_from_crm(frm);
	delete frm.make_methods.Quotation;
	if (frm.custom_make_buttons) {
		frm.custom_make_buttons["Sales Quote"] = "Sales Quote";
		delete frm.custom_make_buttons.Quotation;
	}
}

logistics.crm_sales_quote.open_from_form = logistics_open_sales_quote_from_crm;
logistics.crm_sales_quote.replace_create_button = logistics_replace_quotation_create_button;
logistics.crm_sales_quote.replace_make_methods = logistics_replace_quotation_make_methods;
logistics.crm_sales_quote.should_show_create_button = logistics_should_show_crm_sales_quote_button;

frappe.ui.form.on("Opportunity", {
	setup(frm) {
		logistics_replace_quotation_make_methods(frm);
	},
	refresh(frm) {
		logistics_replace_quotation_make_methods(frm);
		logistics_replace_quotation_create_button(frm);
	},
});

frappe.ui.form.on("Lead", {
	setup(frm) {
		logistics_replace_quotation_make_methods(frm);
	},
	refresh(frm) {
		logistics_replace_quotation_make_methods(frm);
		logistics_replace_quotation_create_button(frm);
	},
});

frappe.ui.form.on("Prospect", {
	setup(frm) {
		logistics_replace_quotation_make_methods(frm);
	},
	refresh(frm) {
		logistics_replace_quotation_make_methods(frm);
		logistics_replace_quotation_create_button(frm);
	},
});

frappe.ui.form.on("Customer", {
	setup(frm) {
		logistics_replace_quotation_make_methods(frm);
	},
	refresh(frm) {
		logistics_replace_quotation_make_methods(frm);
	},
});
