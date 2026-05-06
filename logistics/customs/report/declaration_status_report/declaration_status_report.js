// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.query_reports["Declaration Status Report"] = {
	// Build chart from grid data so the chart always renders (server chart can be dropped by API/serialization).
	get_chart_data(columns, result) {
		const rows = (result || []).filter((r) => r && Object.keys(r).length);
		if (!rows.length) {
			return {
				data: {
					labels: [__("No data")],
					datasets: [{ name: __("Declarations"), values: [0] }],
				},
				type: "bar",
				colors: ["#5e64ff"],
			};
		}
		const counts = {};
		for (const row of rows) {
			const key = row.status || __("Unknown");
			counts[key] = (counts[key] || 0) + 1;
		}
		const labels = Object.keys(counts);
		const values = labels.map((k) => counts[k]);
		return {
			data: {
				labels,
				datasets: [{ name: __("Declarations"), values }],
			},
			type: "bar",
			colors: ["#5e64ff"],
		};
	},
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "customs_authority",
			"label": __("Customs Authority"),
			"fieldtype": "Link",
			"options": "Customs Authority"
		},
		{
			"fieldname": "declaration_type",
			"label": __("Declaration Type"),
			"fieldtype": "Select",
			"options": "Import\nExport\nTransit\nBonded"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "Draft\nSubmitted\nUnder Review\nCleared\nReleased\nRejected\nCancelled"
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		}
	]
};


