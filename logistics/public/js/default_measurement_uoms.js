// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt
//
// Fill empty dimension, volume, and weight UOM fields from Logistics Settings.
// The same map as logistics.utils.default_uom.measurement_uom_kind.

(function () {
	"use strict";

	var EXCLUDED = {
		"Dimension Volume UOM Conversion": true
	};

	function measurement_uom_kind(fieldname) {
		if (!fieldname || fieldname.indexOf("default_") === 0 || fieldname.indexOf("base_") === 0) {
			return null;
		}
		if (fieldname === "peak_uom") return "volume";
		if (fieldname.slice(-22) === "chargeable_weight_uom") return "chargeable_weight";
		if (fieldname.slice(-16) === "total_volume_uom" || fieldname === "inv_volume_uom") {
			return "aggregation_volume";
		}
		if (fieldname.slice(-13) === "dimension_uom") return "dimension";
		if (fieldname.slice(-10) === "volume_uom") return "volume";
		if (fieldname.slice(-10) === "weight_uom") return "weight";
		return null;
	}

	var _pending = null;
	function logistics_measurement_uom_defaults(company) {
		if (_pending) return _pending;
		_pending = new Promise(function (resolve, reject) {
			frappe.call({
				method: "logistics.utils.default_uom.get_measurement_uom_defaults",
				args: { company: company || undefined },
				callback: function (r) {
					if (r && r.message) resolve(r.message);
					else {
						_pending = null;
						reject();
					}
				},
				error: function () {
					_pending = null;
					reject();
				}
			});
		});
		return _pending;
	}

	function empty_fields(doc) {
		if (!doc || !doc.doctype || EXCLUDED[doc.doctype]) return [];
		var meta = frappe.get_meta && frappe.get_meta(doc.doctype);
		var names = [];
		if (meta && meta.fields) {
			meta.fields.forEach(function (df) {
				if (measurement_uom_kind(df.fieldname) && !doc[df.fieldname]) {
					names.push(df.fieldname);
				}
			});
			return names;
		}
		Object.keys(doc).forEach(function (fieldname) {
			if (measurement_uom_kind(fieldname) && !doc[fieldname]) names.push(fieldname);
		});
		return names;
	}

	function apply_to_doc(doc, company) {
		var names = empty_fields(doc);
		if (!names.length) return;
		logistics_measurement_uom_defaults(company || doc.company).then(function (defaults) {
			names.forEach(function (fieldname) {
				if (!doc || doc[fieldname]) return;
				var value = defaults[measurement_uom_kind(fieldname)];
				if (value) {
					frappe.model.set_value(doc.doctype, doc.name, fieldname, value);
				}
			});
		}).catch(function () {});
	}

	function apply_new_form(frm) {
		if (!frm || !frm.doc) return;
		if (frm.is_new && frm.is_new()) {
			apply_to_doc(frm.doc, frm.doc.company);
		}
		(frm.meta && frm.meta.fields || []).forEach(function (df) {
			if (df.fieldtype !== "Table") return;
			(frm.doc[df.fieldname] || []).forEach(function (row) {
				if (row && row.__islocal) apply_to_doc(row, frm.doc.company);
			});
		});
	}

	function install() {
		if (!frappe.ui || !frappe.ui.form || !frappe.ui.form.Form || !frappe.model) return;
		if (frappe.ui.form.Form.prototype._logistics_uom_defaults_installed) return;
		frappe.ui.form.Form.prototype._logistics_uom_defaults_installed = true;

		var refresh = frappe.ui.form.Form.prototype.refresh;
		frappe.ui.form.Form.prototype.refresh = function () {
			var out = refresh.apply(this, arguments);
			try {
				apply_new_form(this);
			} catch (e) {
				// Leave the form usable if a default lookup fails.
			}
			return out;
		};

		var add_child = frappe.model.add_child;
		frappe.model.add_child = function (parent) {
			var row = add_child.apply(this, arguments);
			try {
				if (row) apply_to_doc(row, parent && parent.company);
			} catch (e) {}
			return row;
		};
	}

	window.logistics_measurement_uom_defaults = logistics_measurement_uom_defaults;
	window.logistics_apply_measurement_uom_defaults = function (doc, company) {
		apply_to_doc(doc, company);
	};

	if (frappe.ui && frappe.ui.form && frappe.ui.form.Form) {
		install();
	} else {
		frappe.ready(install);
	}
})();
