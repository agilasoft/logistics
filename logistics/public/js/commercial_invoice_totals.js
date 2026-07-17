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

	function _line_total(doc) {
		let total = 0;
		const rows = doc.commercial_invoice_line_items || [];
		for (let i = 0; i < rows.length; i++) {
			const row = rows[i];
			const qty = _to_num(row.invoice_qty || row.customs_qty || 1);
			const price = _to_num(row.price);
			total += qty * price;
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

		const base = line_total > 0 ? line_total : _to_num(doc.inv_total_amount);
		const fob = Math.max(base + fob_additions - deductions, 0);
		const cif = Math.max(fob + post_fob_additions, 0);
		const inv_total = _to_num(doc.inv_total_amount);
		const balance =
			inv_total > 0 ? (inv_total - (line_total + charges_for_itot)).toFixed(2) : "";

		return {
			expected_invoice_line_total: line_total,
			fob: fob,
			cif: cif,
			balance: balance,
		};
	}

	function _apply_totals_to_form(frm) {
		const totals = calculateCommercialInvoiceTotals(frm.doc);
		const updates = [
			["expected_invoice_line_total", totals.expected_invoice_line_total],
			["fob", totals.fob],
			["cif", totals.cif],
			["balance", totals.balance],
		];
		updates.forEach(function (entry) {
			const fieldname = entry[0];
			const value = entry[1];
			if (Math.abs(flt(frm.doc[fieldname]) - flt(value)) > 1e-6 || frm.doc[fieldname] !== value) {
				frm.set_value(fieldname, value);
			}
		});
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
	logistics.schedule_commercial_invoice_totals_recalc = scheduleCommercialInvoiceTotalsRecalc;
	logistics.apply_commercial_invoice_totals_to_form = _apply_totals_to_form;
})();
