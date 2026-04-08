// Copyright (c) 2026, www.agilasoft.com and contributors
// When Transport Mode changes on Declaration / Declaration Order, apply Default Transport
// Document Type from the master if the user has not overridden the field.

frappe.provide("logistics.transport_mode_defaults");

logistics.transport_mode_defaults.apply = function (frm) {
	const prev_mode = frm._prev_transport_mode;
	const new_mode = frm.doc.transport_mode;
	const sync_prev = function () {
		frm._prev_transport_mode = new_mode;
	};
	if (!new_mode) {
		sync_prev();
		return;
	}
	frappe.db.get_value("Transport Mode", new_mode, "default_transport_document_type").then(function (r) {
		const new_default = r.message && r.message.default_transport_document_type;
		if (!new_default) {
			sync_prev();
			return;
		}
		const finish = function (prev_def) {
			const cur = frm.doc.transport_document_type;
			if (!cur || cur === prev_def) {
				frm.set_value("transport_document_type", new_default);
			}
			sync_prev();
		};
		if (prev_mode) {
			frappe.db
				.get_value("Transport Mode", prev_mode, "default_transport_document_type")
				.then(function (r2) {
					const prev_def = r2.message && r2.message.default_transport_document_type;
					finish(prev_def || null);
				});
		} else {
			finish(null);
		}
	});
};

["Declaration Order", "Declaration"].forEach(function (doctype) {
	frappe.ui.form.on(doctype, {
		refresh: function (frm) {
			frm._prev_transport_mode = frm.doc.transport_mode;
			frm.set_query("transport_document_type", function () {
				return {
					query:
						"logistics.utils.transport_document_type_link_query.transport_document_type_by_mode_search",
					filters: { transport_mode: frm.doc.transport_mode || "" },
				};
			});
			// Saved / new forms: mode is set but default was never applied (no transport_mode change event).
			if (frm.doc.transport_mode && !frm.doc.transport_document_type) {
				logistics.transport_mode_defaults.apply(frm);
			}
		},
		transport_mode: function (frm) {
			logistics.transport_mode_defaults.apply(frm);
		},
	});
});
