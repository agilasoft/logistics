// Copyright (c) 2026, www.agilasoft.com and contributors
// Shared billing currency / exchange rate helpers for invoice creation dialogs.

(function() {
	"use strict";

	function fetch_exchange_rate(posting_date, from_currency, to_currency, purpose, callback) {
		if (!posting_date || !from_currency || !to_currency) {
			if (callback) callback(1);
			return;
		}
		if (from_currency === to_currency) {
			if (callback) callback(1);
			return;
		}
		frappe.call({
			method: "erpnext.setup.utils.get_exchange_rate",
			args: {
				transaction_date: posting_date,
				from_currency: from_currency,
				to_currency: to_currency,
				args: purpose || "for_selling"
			},
			callback: function(r) {
				if (callback) callback(flt(r.message) || 1);
			}
		});
	}

	function fetch_party_billing_currency(party_type, party_name, company_currency, callback) {
		if (!party_name) {
			if (callback) callback(company_currency);
			return;
		}
		frappe.db.get_value(party_type, party_name, "default_currency", function(r) {
			var cur = (r && r.message && r.message.default_currency) || company_currency;
			if (callback) callback(cur || company_currency);
		});
	}

	/**
	 * Wire billing_currency + exchange_rate on a frappe.ui.Dialog.
	 * opts: { company_currency, default_billing_currency, exchange_purpose, party_type, party_fieldname }
	 */
	function bind_invoice_billing_currency(dialog, opts) {
		opts = opts || {};
		var company_currency = opts.company_currency || "";
		var exchange_purpose = opts.exchange_purpose || "for_selling";
		var party_type = opts.party_type || "Customer";
		var party_fieldname = opts.party_fieldname || "customer";

		function refresh_exchange_rate_field() {
			if (!dialog) return;
			var billing_currency = dialog.get_value("billing_currency");
			var posting_date = dialog.get_value("posting_date");
			var $rate = dialog.fields_dict.exchange_rate;
			if (!billing_currency || billing_currency === company_currency) {
				dialog.set_value("exchange_rate", 1);
				if ($rate) {
					$rate.df.read_only = 1;
					$rate.refresh();
				}
				return;
			}
			if ($rate) {
				$rate.df.read_only = 0;
				$rate.refresh();
			}
			fetch_exchange_rate(posting_date, billing_currency, company_currency, exchange_purpose, function(rate) {
				if (dialog) dialog.set_value("exchange_rate", rate);
			});
		}

		function set_billing_currency_from_party(party_name) {
			fetch_party_billing_currency(party_type, party_name, company_currency, function(cur) {
				if (dialog) {
					dialog.set_value("billing_currency", cur);
					refresh_exchange_rate_field();
				}
			});
		}

		if (opts.default_billing_currency) {
			dialog.set_value("billing_currency", opts.default_billing_currency);
		}
		refresh_exchange_rate_field();

		dialog.$wrapper.find("[data-fieldname='" + party_fieldname + "']").on("change", function() {
			set_billing_currency_from_party(dialog.get_value(party_fieldname));
		});
		dialog.$wrapper.find("[data-fieldname='billing_currency']").on("change", refresh_exchange_rate_field);
		dialog.$wrapper.find("[data-fieldname='posting_date']").on("change", refresh_exchange_rate_field);

		return {
			refresh_exchange_rate_field: refresh_exchange_rate_field,
			set_billing_currency_from_party: set_billing_currency_from_party
		};
	}

	function billing_currency_header_fields(default_billing_currency) {
		return [
			{ fieldname: "billing_currency", fieldtype: "Link", label: __("Billing Currency"), options: "Currency", default: default_billing_currency, reqd: 1 },
			{ fieldname: "exchange_rate", fieldtype: "Float", label: __("Exchange Rate"), precision: 9, default: 1, reqd: 1 }
		];
	}

	window.logistics_invoice_billing_currency = {
		fetch_exchange_rate: fetch_exchange_rate,
		fetch_party_billing_currency: fetch_party_billing_currency,
		bind_invoice_billing_currency: bind_invoice_billing_currency,
		billing_currency_header_fields: billing_currency_header_fields
	};
})();
