// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.provide("logistics.address");

/** Frappe address_query — filters via Dynamic Link child table, not Address.link_doctype. */
logistics.address.QUERY = "frappe.contacts.doctype.address.address.address_query";

/**
 * Link field search for addresses linked to a document.
 * Do not combine with JSON link_filters on Address; Frappe merges them and drops this query.
 */
logistics.address.query_for_link = function (link_doctype, link_name) {
	if (!link_name) {
		return { filters: { name: "__none__" } };
	}
	return {
		query: logistics.address.QUERY,
		filters: {
			link_doctype,
			link_name,
			disabled: 0,
		},
	};
};

logistics.address.query_for_customer = function (customer) {
	return logistics.address.query_for_link("Customer", customer);
};
