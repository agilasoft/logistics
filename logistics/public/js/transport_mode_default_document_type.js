// Copyright (c) 2026, www.agilasoft.com and contributors
// When Transport Mode changes on Declaration / Declaration Order, apply Default Transport
// Document Type from the master if the user has not overridden the field.

frappe.provide("logistics.transport_mode_defaults");

function _transport_doc_type_is_empty(v) {
	return v == null || (typeof v === "string" && v.trim() === "");
}

/** Deferred so frm.doc / link fields match the server after save or render (avoids needing a manual reload). */
function _schedule_transport_document_type_apply_if_empty(frm) {
	if (!frm || !frm.doc) {
		return;
	}
	if (frm._transport_doc_type_apply_tid) {
		clearTimeout(frm._transport_doc_type_apply_tid);
	}
	frm._transport_doc_type_apply_tid = setTimeout(function () {
		frm._transport_doc_type_apply_tid = null;
		if (!frm.doc || !frm.doc.transport_mode) {
			return;
		}
		if (!_transport_doc_type_is_empty(frm.doc.transport_document_type)) {
			return;
		}
		logistics.transport_mode_defaults.apply(frm);
	}, 0);
}

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
			if (_transport_doc_type_is_empty(cur) || cur === prev_def) {
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

/** Link query + optional default; runs without waiting for a later form refresh. */
function _transport_document_type_setup_query_and_maybe_apply(frm) {
	frm._prev_transport_mode = frm.doc.transport_mode;
	frm.set_query("transport_document_type", function () {
		return {
			query:
				"logistics.utils.transport_document_type_link_query.transport_document_type_by_mode_search",
			filters: { transport_mode: frm.doc.transport_mode || "" },
		};
	});
	// Mode set without a transport_mode change event (e.g. loaded from DB, after save sync, quick entry).
	if (frm.doc.transport_mode && _transport_doc_type_is_empty(frm.doc.transport_document_type)) {
		_schedule_transport_document_type_apply_if_empty(frm);
	}
}

if (!window._logistics_transport_doc_type_form_refresh_bound) {
	window._logistics_transport_doc_type_form_refresh_bound = true;
	$(document).on("form-refresh.logistics_transport_doc_type", function (_e, frm) {
		if (!frm || (frm.doctype !== "Declaration Order" && frm.doctype !== "Declaration")) {
			return;
		}
		if (frm.doc && frm.doc.transport_mode && _transport_doc_type_is_empty(frm.doc.transport_document_type)) {
			_schedule_transport_document_type_apply_if_empty(frm);
		}
	});
}

["Declaration Order", "Declaration"].forEach(function (doctype) {
	frappe.ui.form.on(doctype, {
		onload_post_render: function (frm) {
			_transport_document_type_setup_query_and_maybe_apply(frm);
		},
		refresh: function (frm) {
			_transport_document_type_setup_query_and_maybe_apply(frm);
		},
		transport_mode: function (frm) {
			logistics.transport_mode_defaults.apply(frm);
		},
	});
});
