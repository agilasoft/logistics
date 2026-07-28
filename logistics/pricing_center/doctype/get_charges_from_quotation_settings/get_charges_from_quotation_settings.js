// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt

frappe.ui.form.on("Get Charges from Quotation Settings", {
	refresh(frm) {
		if (!(frm.doc.filter_settings || []).length) {
			frappe.call({
				method:
					"logistics.utils.get_charges_from_quotation.seed_gcfq_filter_settings_if_empty",
				freeze: true,
				callback() {
					frm.reload_doc();
				},
			});
			return;
		}
		_gcfq_mount_dashboard(frm);
	},
});

frappe.ui.form.on("GCFQ Filter Setting", {
	job_doctype(frm, cdt, cdn) {
		_gcfq_settings_sync_filter_key_options(frm, cdt, cdn);
	},
	filter_settings_add(frm, cdt, cdn) {
		_gcfq_settings_sync_filter_key_options(frm, cdt, cdn);
	},
});

function _gcfq_mount_dashboard(frm) {
	var field = frm.get_field("dashboard_html");
	if (!field || !field.$wrapper) {
		return;
	}
	var $host = field.$wrapper.find(".gcfq-dash-host");
	if (!$host.length) {
		$host = $('<div class="gcfq-dash-host">');
		field.$wrapper.empty().append($host);
	}
	if (window.logistics && logistics.gcfq_dashboard && logistics.gcfq_dashboard.mount) {
		logistics.gcfq_dashboard.mount($host);
	} else {
		$host.html(
			'<div class="text-muted">' +
				__("Dashboard script not loaded. Hard-refresh the page (Ctrl+Shift+R).") +
				"</div>"
		);
	}
}

function _gcfq_settings_sync_filter_key_options(frm, cdt, cdn) {
	var row = locals[cdt][cdn];
	if (!row || !row.job_doctype) {
		return;
	}
	frappe.call({
		method: "logistics.utils.get_charges_from_quotation.get_gcfq_catalog_keys_for_doctype",
		args: { doctype: row.job_doctype },
		callback(r) {
			var keys = (r && r.message) || [];
			var grid = frm.get_field("filter_settings");
			if (!grid || !grid.grid) {
				return;
			}
			var grid_row = grid.grid.grid_rows_by_docname[cdn];
			if (!grid_row) {
				return;
			}
			var field = grid_row.get_field("filter_key");
			if (!field) {
				return;
			}
			field.df.options = keys.join("\n");
			field.refresh();
			if (row.filter_key && keys.indexOf(row.filter_key) === -1) {
				frappe.model.set_value(cdt, cdn, "filter_key", "");
			}
		},
	});
}
