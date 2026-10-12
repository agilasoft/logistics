// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

// Frappe report number cards only aggregate Sum, Average, Minimum, and Maximum.
// Report cards that store Function = Count (row count of a report column) throw
// "is not a function" in frappe.report_utils.get_result_of_fn and leave the card blank.
(function (root) {
	"use strict";

	var KNOWN = { Sum: 1, Average: 1, Minimum: 1, Maximum: 1 };

	function asList(values) {
		return Array.isArray(values) ? values : [];
	}

	function aggregateReportValues(fn, values, original) {
		var list = asList(values);
		if (fn === "Count") {
			return list.length;
		}
		if (!KNOWN[fn]) {
			return 0;
		}
		if (!list.length) {
			return 0;
		}
		if (typeof original === "function") {
			return original(fn, list);
		}
		if (fn === "Sum") {
			return list.reduce(function (total, value) {
				return total + Number(value || 0);
			}, 0);
		}
		if (fn === "Average") {
			return (
				list.reduce(function (total, value) {
					return total + Number(value || 0);
				}, 0) / list.length
			);
		}
		var numbers = list.map(function (value) {
			return Number(value);
		});
		return fn === "Minimum" ? Math.min.apply(null, numbers) : Math.max.apply(null, numbers);
	}

	function install() {
		var frappe = root.frappe;
		if (!frappe || !frappe.report_utils || typeof frappe.report_utils.get_result_of_fn !== "function") {
			return false;
		}
		if (frappe.report_utils.get_result_of_fn.__logisticsReportFn) {
			return true;
		}
		var original = frappe.report_utils.get_result_of_fn;
		function wrapped(fn, values) {
			return aggregateReportValues(fn, values, function (name, list) {
				return original.call(frappe.report_utils, name, list);
			});
		}
		wrapped.__logisticsReportFn = true;
		frappe.report_utils.get_result_of_fn = wrapped;
		return true;
	}

	root.logistics = root.logistics || {};
	root.logistics.aggregateReportValues = aggregateReportValues;
	install();
	if (root.frappe && typeof root.frappe.ready === "function") {
		root.frappe.ready(install);
	}
	// report_utils.js assigns its object when the desk bundle evaluates. Re-apply
	// if that assignment happens after this include.
	var tries = 0;
	var timer = setInterval(function () {
		var current = root.frappe && root.frappe.report_utils && root.frappe.report_utils.get_result_of_fn;
		if (!current || !current.__logisticsReportFn) {
			install();
		}
		if (++tries > 40) {
			clearInterval(timer);
		}
	}, 250);
	if (timer && typeof timer.unref === "function") {
		timer.unref();
	}
})(typeof window !== "undefined" ? window : this);
