// List action "Create Prospect" asks ERPNext for Lead fields and omits annual_revenue.
// Register the same action first so the core handler is ignored (duplicate labels
// are skipped) and Annual Revenue is copied onto the new Prospect.

(function () {
	const settings = frappe.listview_settings["Lead"] || {};
	if (settings._logistics_create_prospect_patched) {
		return;
	}
	const original_onload = settings.onload;

	settings.onload = function (listview) {
		const can_create = frappe.boot.user && frappe.boot.user.can_create;
		if (can_create && can_create.includes("Prospect")) {
			listview.page.add_action_item(__("Create Prospect"), function () {
				frappe.model.with_doctype("Prospect", function () {
					const prospect = frappe.model.get_new_doc("Prospect");
					const leads = listview.get_checked_items();
					if (!leads.length) {
						return;
					}
					frappe.db.get_value(
						"Lead",
						leads[0].name,
						[
							"company_name",
							"no_of_employees",
							"industry",
							"market_segment",
							"territory",
							"fax",
							"website",
							"lead_owner",
							"annual_revenue",
						],
						(r) => {
							if (!r) {
								return;
							}
							prospect.company_name = r.company_name;
							prospect.no_of_employees = r.no_of_employees;
							prospect.industry = r.industry;
							prospect.market_segment = r.market_segment;
							prospect.territory = r.territory;
							prospect.fax = r.fax;
							prospect.website = r.website;
							prospect.prospect_owner = r.lead_owner;
							prospect.annual_revenue = r.annual_revenue;

							leads.forEach(function (lead) {
								const lead_prospect_row = frappe.model.add_child(prospect, "leads");
								lead_prospect_row.lead = lead.name;
							});
							frappe.set_route("Form", "Prospect", prospect.name);
						}
					);
				});
			});
		}
		if (original_onload) {
			return original_onload.call(this, listview);
		}
	};

	settings._logistics_create_prospect_patched = true;
	frappe.listview_settings["Lead"] = settings;
})();
