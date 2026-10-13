// Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
// For license information, please see license.txt

(function () {
	"use strict";

	const DEDUCTION_CHARGE_CODES = { DIS: 1, DED: 1 };

	function _to_num(value) {
		const n = parseFloat(value);
		return Number.isFinite(n) ? n : 0;
	}

	function _charge_amount(row, inv_currency) {
		const amount = _to_num(row.amount);
		if (!amount) {
			return 0;
		}
		const row_currency = (row.currency || inv_currency || "").trim();
		const invoice_currency = (inv_currency || "").trim();
		if (!row_currency || !invoice_currency || row_currency === invoice_currency) {
			return amount;
		}
		// Unsaved rows with mixed currencies fall back to raw amount until save.
		return amount;
	}

	function _positive_qty(value) {
		const n = parseFloat(value);
		return Number.isFinite(n) && n > 0 ? n : 0;
	}

	function _line_qty(row) {
		const invoiceQty = _positive_qty(row.invoice_qty);
		if (invoiceQty > 0) {
			return invoiceQty;
		}
		return _positive_qty(row.customs_qty);
	}

	function _line_total(doc) {
		let total = 0;
		const rows = doc.commercial_invoice_line_items || [];
		for (let i = 0; i < rows.length; i++) {
			const row = rows[i];
			total += _line_qty(row) * _to_num(row.price);
		}
		return total;
	}

	/** Mirrors ``calculate_commercial_invoice_totals`` in Python. */
	function calculateCommercialInvoiceTotals(doc) {
		const inv_currency = doc.inv_currency || "";
		const line_total = _line_total(doc);
		let fob_additions = 0;
		let post_fob_additions = 0;
		let deductions = 0;
		let charges_for_itot = 0;
		const charges_excl_from_itot = cint(doc.charges_excl_from_itot);
		const rows = doc.commercial_invoice_charges || [];

		for (let i = 0; i < rows.length; i++) {
			const row = rows[i];
			const included_in_inv_amt = cint(row.included_in_inv_amt);
			const amount = _charge_amount(row, inv_currency);
			if (!amount) {
				continue;
			}
			if (!included_in_inv_amt && !charges_excl_from_itot) {
				charges_for_itot += amount;
			}
			if (included_in_inv_amt) {
				continue;
			}
			const code = ((row.charge_code || "") + "").trim().toUpperCase();
			if (DEDUCTION_CHARGE_CODES[code]) {
				deductions += amount;
			} else if (cint(row.add_to_fob)) {
				fob_additions += amount;
			} else {
				post_fob_additions += amount;
			}
		}

		const hasLines = (doc.commercial_invoice_line_items || []).length > 0;
		const typedInvTotal = _to_num(doc.inv_total_amount);
		const inv_total = hasLines ? line_total : typedInvTotal;
		const base = line_total > 0 ? line_total : inv_total;
		const fob = Math.max(base + fob_additions - deductions, 0);
		const cif = Math.max(fob + post_fob_additions, 0);
		const balance =
			inv_total > 0 ? (inv_total - (line_total + charges_for_itot)).toFixed(2) : "";

		const totals = {
			expected_invoice_line_total: line_total,
			fob: fob,
			cif: cif,
			balance: balance,
		};
		if (hasLines) {
			totals.inv_total_amount = line_total;
		}
		return totals;
	}

	const INVOICE_DETAIL_FIELDS = [
		"inv_volume",
		"inv_volume_uom",
		"inv_gross_weight",
		"inv_gross_weight_uom",
		"inv_net_weight",
		"inv_net_weight_uom",
		"packages",
		"packages_uom",
	];

	/** Local mirror of ``calculate_invoice_detail_measures`` when no UOM conversion is required. */
	function _local_invoice_detail_measures(doc) {
		const rows = doc.commercial_invoice_line_items || [];
		const specs = [
			["volume", "volume_uom", "inv_volume", "inv_volume_uom"],
			["gross_weight", "gross_weight_uom", "inv_gross_weight", "inv_gross_weight_uom"],
			["net_weight", "net_weight_uom", "inv_net_weight", "inv_net_weight_uom"],
		];
		const totals = {};
		let needsServer = false;

		specs.forEach(function (spec) {
			const valueField = spec[0];
			const uomField = spec[1];
			const headerValue = spec[2];
			const headerUom = spec[3];
			let total = 0;
			let used = false;
			const explicit = [];
			const seenUom = {};
			rows.forEach(function (row) {
				const value = _to_num(row[valueField]);
				if (value <= 0) {
					return;
				}
				used = true;
				total += value;
				const uom = ((row[uomField] || "") + "").trim();
				const key = uom.toUpperCase();
				if (uom && !seenUom[key]) {
					seenUom[key] = 1;
					explicit.push(uom);
				}
			});
			if (!used) {
				return;
			}
			if (explicit.length > 1) {
				needsServer = true;
				return;
			}
			totals[headerValue] = total;
			if (explicit.length === 1) {
				totals[headerUom] = explicit[0];
			}
		});

		let packages = 0;
		let packagesUsed = false;
		rows.forEach(function (row) {
			const packs = _to_num(row.no_of_packs);
			if (packs <= 0) {
				return;
			}
			packagesUsed = true;
			packages += packs;
		});
		if (packagesUsed) {
			totals.packages = packages;
		}
		return { needsServer: needsServer, totals: totals };
	}

	function _shared_package_type(rows) {
		let shared = "";
		let sawType = false;
		for (let i = 0; i < rows.length; i++) {
			const packs = _to_num(rows[i].no_of_packs);
			if (packs <= 0) {
				continue;
			}
			const packageType = ((rows[i].package_type || "") + "").trim();
			if (!packageType) {
				continue;
			}
			if (!sawType) {
				shared = packageType;
				sawType = true;
			} else if (shared !== packageType) {
				return "";
			}
		}
		return sawType ? shared : "";
	}

	function _set_measure_value(frm, fieldname, value) {
		const current = frm.doc[fieldname];
		if (typeof value === "string") {
			if ((current || "") === value) {
				return;
			}
			frm.set_value(fieldname, value);
			return;
		}
		if (current != null && current !== "" && Math.abs(flt(current) - flt(value)) <= 1e-6) {
			return;
		}
		frm.set_value(fieldname, value);
	}

	function _write_invoice_detail_measures(frm, totals) {
		INVOICE_DETAIL_FIELDS.forEach(function (fieldname) {
			const derived = Object.prototype.hasOwnProperty.call(totals, fieldname);
			if (cint(frm.doc.docstatus) === 0 && frm.fields_dict[fieldname]) {
				frm.set_df_property(fieldname, "read_only", derived ? 1 : 0);
			}
			if (derived) {
				_set_measure_value(frm, fieldname, totals[fieldname]);
			}
		});
	}

	function _fetch_invoice_detail_measures(frm) {
		const seq = (frm._invoice_detail_measure_seq = (frm._invoice_detail_measure_seq || 0) + 1);
		frappe.call({
			method: "logistics.utils.commercial_invoice_totals.recalculate_commercial_invoice_totals",
			args: { doc_json: frm.doc },
			callback: function (r) {
				if (!frm.doc || frm._invoice_detail_measure_seq !== seq) {
					return;
				}
				const message = (r && r.message) || {};
				const totals = {};
				INVOICE_DETAIL_FIELDS.forEach(function (fieldname) {
					if (Object.prototype.hasOwnProperty.call(message, fieldname)) {
						totals[fieldname] = message[fieldname];
					}
				});
				_write_invoice_detail_measures(frm, totals);
			},
		});
	}

	function _maybe_set_packages_uom(frm, rows) {
		const candidate = _shared_package_type(rows);
		if (!candidate || !frappe.db || !frappe.db.exists) {
			return;
		}
		const seq = (frm._packages_uom_seq = (frm._packages_uom_seq || 0) + 1);
		Promise.resolve(frappe.db.exists("UOM", candidate)).then(function (found) {
			if (!frm.doc || frm._packages_uom_seq !== seq || !found) {
				return;
			}
			if (cint(frm.doc.docstatus) === 0 && frm.fields_dict.packages_uom) {
				frm.set_df_property("packages_uom", "read_only", 1);
			}
			_set_measure_value(frm, "packages_uom", candidate);
		});
	}

	function _apply_invoice_detail_measures(frm) {
		const local = _local_invoice_detail_measures(frm.doc);
		if (local.needsServer) {
			_fetch_invoice_detail_measures(frm);
			return;
		}
		_write_invoice_detail_measures(frm, local.totals);
		_maybe_set_packages_uom(frm, frm.doc.commercial_invoice_line_items || []);
	}

	function _apply_totals_to_form(frm) {
		const totals = calculateCommercialInvoiceTotals(frm.doc);
		const updates = [
			["expected_invoice_line_total", totals.expected_invoice_line_total],
			["fob", totals.fob],
			["cif", totals.cif],
			["balance", totals.balance],
		];
		if (Object.prototype.hasOwnProperty.call(totals, "inv_total_amount")) {
			updates.push(["inv_total_amount", totals.inv_total_amount]);
		}
		updates.forEach(function (entry) {
			const fieldname = entry[0];
			const value = entry[1];
			if (Math.abs(flt(frm.doc[fieldname]) - flt(value)) > 1e-6 || frm.doc[fieldname] !== value) {
				frm.set_value(fieldname, value);
			}
		});
		_apply_invoice_detail_measures(frm);
		_sync_number_of_line_items_on_form(frm);
	}

	function _invoice_line_row_count(doc) {
		return (doc.commercial_invoice_line_items || []).length;
	}

	function _charge_item_count_qty(charge) {
		let qty = 0;
		if ((charge.unit_type || "") === "Item Count") {
			qty = Math.max(qty, flt(charge.quantity));
		}
		if ((charge.cost_unit_type || "") === "Item Count") {
			qty = Math.max(qty, flt(charge.cost_quantity));
		}
		return qty;
	}

	function _seed_number_of_line_items_from_charges(frm) {
		if (cint(frm.doc.number_of_line_items) > 0) {
			return;
		}
		let qty = 0;
		(frm.doc.charges || []).forEach(function (ch) {
			qty = Math.max(qty, _charge_item_count_qty(ch));
		});
		qty = cint(qty);
		if (qty > 0) {
			frm.doc.number_of_line_items_manual = 1;
			frm.set_value("number_of_line_items", qty);
		}
	}

	function _sync_number_of_line_items_on_form(frm) {
		if (!frm || !frm.doc) {
			return;
		}
		if (frm.doctype !== "Declaration" && frm.doctype !== "Declaration Order") {
			return;
		}
		if (!frm.fields_dict.number_of_line_items) {
			return;
		}
		_seed_number_of_line_items_from_charges(frm);
		const rowCount = _invoice_line_row_count(frm.doc);
		const current = cint(frm.doc.number_of_line_items);
		const manual = cint(frm.doc.number_of_line_items_manual);
		if (manual) {
			if (rowCount > current) {
				frm.doc.number_of_line_items_manual = 0;
				frm.set_value("number_of_line_items", rowCount);
			}
			return;
		}
		if (rowCount > 0 && current !== rowCount) {
			frm.set_value("number_of_line_items", rowCount);
		}
	}

	function _mark_number_of_line_items_manual(frm) {
		if (!frm || !frm.doc) {
			return;
		}
		const rowCount = _invoice_line_row_count(frm.doc);
		const value = cint(frm.doc.number_of_line_items);
		frm.doc.number_of_line_items_manual = value === rowCount ? 0 : 1;
	}

	const timers = {};

	function scheduleCommercialInvoiceTotalsRecalc(frm) {
		if (!frm || !frm.doc) {
			return;
		}
		if (frm.doctype !== "Declaration" && frm.doctype !== "Declaration Order") {
			return;
		}
		const key = frm.doctype + ":" + (frm.doc.name || "new");
		clearTimeout(timers[key]);
		timers[key] = setTimeout(function () {
			_apply_totals_to_form(frm);
		}, 200);
	}

	window.logistics = window.logistics || {};
	logistics.calculate_commercial_invoice_totals = calculateCommercialInvoiceTotals;
	logistics.local_invoice_detail_measures = _local_invoice_detail_measures;
	logistics.schedule_commercial_invoice_totals_recalc = scheduleCommercialInvoiceTotalsRecalc;
	logistics.apply_commercial_invoice_totals_to_form = _apply_totals_to_form;
	logistics.sync_number_of_line_items_on_form = _sync_number_of_line_items_on_form;

	["Declaration", "Declaration Order"].forEach(function (dt) {
		frappe.ui.form.on(dt, {
			number_of_line_items: function (frm) {
				_mark_number_of_line_items_manual(frm);
				if (window.logistics && logistics.schedule_customs_line_charge_recalc) {
					logistics.schedule_customs_line_charge_recalc(frm);
				}
			},
			commercial_invoice_line_items_add: function (frm) {
				scheduleCommercialInvoiceTotalsRecalc(frm);
			},
			commercial_invoice_line_items_remove: function (frm) {
				scheduleCommercialInvoiceTotalsRecalc(frm);
			},
		});
	});
})();
