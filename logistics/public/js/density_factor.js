// Copyright (c) 2026, www.agilasoft.com and contributors
// Shared density-factor indicator for Air/Sea Booking, Air/Sea Shipment, Transport Order/Job.
// Renders the static `density_factor_html` field as a modern progress bar with
// numeric value, classification badge, tick scale and inline error caption.
// Companion stylesheet: logistics/public/css/density_factor.css.

(function () {
	'use strict';

	// IATA volumetric divisor: 1 kg per 6000 cm³. Used as the bar's upper bound.
	var UPPER_BOUND = 6000.0;

	// Three-zone classification — keep in sync with css [data-zone="..."] rules.
	// dense:      < 50% of break-even (weight-rated cargo)
	// standard:   50-100% of break-even
	// volumetric: ≥ break-even (volume-rated cargo)
	var ZONE_THRESHOLDS = { dense: 3000, standard: 6000 };

	// Per-doctype field mapping. Each entry tells the helper which fields hold the
	// aggregated volume/weight (and optional UOMs) to feed the density factor calc.
	var DOCTYPES = {
		'Air Booking':    { volume: ['total_volume', 'volume'], weight: ['total_weight', 'weight'], volume_uom: [], weight_uom: [] },
		'Air Shipment':   { volume: ['total_volume'], weight: ['total_weight'], volume_uom: ['total_volume_uom'], weight_uom: ['total_weight_uom'] },
		'Sea Booking':    { volume: ['total_volume'], weight: ['total_weight'], volume_uom: [], weight_uom: [] },
		'Sea Shipment':   { volume: ['total_volume'], weight: ['total_weight'], volume_uom: ['total_volume_uom'], weight_uom: ['total_weight_uom'] },
		'Transport Order':{ volume: ['total_volume'], weight: ['total_weight'], volume_uom: [], weight_uom: [] },
		'Transport Job':  { volume: ['total_volume'], weight: ['total_weight'], volume_uom: [], weight_uom: [] },
		'Docket':         { volume: ['total_volume'], weight: ['total_weight'], volume_uom: ['total_volume_uom'], weight_uom: ['total_weight_uom'] }
	};

	function _first_value(doc, fields) {
		if (!doc || !fields) return null;
		for (var i = 0; i < fields.length; i++) {
			var v = doc[fields[i]];
			if (v !== undefined && v !== null && v !== '') return v;
		}
		return null;
	}

	function _parse_number(v) {
		if (v === undefined || v === null || v === '') return 0;
		if (typeof flt === 'function') {
			var n = flt(v);
			return isNaN(n) ? 0 : n;
		}
		var n2 = parseFloat(String(v).replace(/,/g, ''));
		return isNaN(n2) ? 0 : n2;
	}

	function _classify(df) {
		if (df === null || df === undefined || isNaN(df)) return null;
		if (df < ZONE_THRESHOLDS.dense) return 'dense';
		if (df < ZONE_THRESHOLDS.standard) return 'standard';
		return 'volumetric';
	}

	function _classification_label(zone) {
		if (zone === 'dense') return __('Dense');
		if (zone === 'standard') return __('Standard');
		if (zone === 'volumetric') return __('Volumetric');
		return '';
	}

	function _format_value(df) {
		if (df === null || df === undefined || isNaN(df)) return '';
		// Use Frappe's locale-aware formatter when available so 4266.7 becomes "4,266.7"
		// (or "4.266,7" in EU locales).
		if (typeof format_number === 'function') {
			try { return format_number(df, null, 1); } catch (e) { /* fall through */ }
		}
		try {
			return Number(df).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
		} catch (e) {
			return Number(df).toFixed(1);
		}
	}

	function _local_density_factor(volume_m3, weight_kg) {
		// Assumes base UOMs are m³ and kg (which is what compute_density_factor
		// also assumes for the * 1e6 cm³/m³ multiplier).
		if (!weight_kg || weight_kg <= 0) return null;
		return (volume_m3 * 1e6) / weight_kg;
	}

	function _local_reason(volume, weight) {
		if (!volume && !weight) return null;
		if (!weight || weight <= 0) return __('Weight is required to compute density factor.');
		if (!volume || volume <= 0) return __('Volume is required to compute density factor.');
		return null;
	}

	function _render(frm, density_factor, percent, reason) {
		if (!frm || !frm.fields_dict) return;
		var field = frm.fields_dict.density_factor_html;
		if (!field || !field.$wrapper) return;
		var $w = field.$wrapper;
		var $track = $w.find('.density-factor-track');
		var $ind = $w.find('.density-factor-indicator');
		var $val = $w.find('.density-factor-value');
		var $cls = $w.find('.density-factor-classification');
		var $err = $w.find('.density-factor-error');
		if (!$track.length) return;

		var has_value = (density_factor !== null && density_factor !== undefined && !isNaN(density_factor));
		var pct = (has_value && typeof percent === 'number' && !isNaN(percent)) ? percent : 0;
		pct = Math.max(0, Math.min(100, pct));

		// Drive bar fill width AND fill gradient stretch from one CSS variable.
		// See density_factor.css: .density-factor-fill { width: calc(var(--df-pct) * 1%); ... }
		$track[0].style.setProperty('--df-pct', pct);

		if (has_value) {
			var zone = _classify(density_factor);
			$val.text(_format_value(density_factor))
				.attr('data-doc-value', String(density_factor))
				.removeClass('is-empty');
			$ind.attr('data-zone', zone || '').addClass('is-visible');
			if (zone) {
				$cls.text(_classification_label(zone))
					.attr('data-zone', zone)
					.addClass('is-visible');
			} else {
				$cls.removeClass('is-visible').text('').removeAttr('data-zone');
			}
			$err.removeClass('is-visible').text('');
			$track.attr('aria-valuenow', Number(density_factor).toFixed(1))
				.attr('aria-valuetext', _format_value(density_factor) + ' cm³/kg' + (zone ? ' (' + _classification_label(zone) + ')' : ''));
		} else {
			$val.text('').addClass('is-empty').attr('data-doc-value', '');
			$ind.removeAttr('data-zone').removeClass('is-visible');
			$cls.removeClass('is-visible').text('').removeAttr('data-zone');
			if (reason) {
				$err.text(reason).addClass('is-visible');
			} else {
				$err.removeClass('is-visible').text('');
			}
			$track.attr('aria-valuenow', '').attr('aria-valuetext', reason || '');
		}
	}

	function _update_density_factor(frm) {
		if (!frm || !frm.doc) return;
		var cfg = DOCTYPES[frm.doctype];
		if (!cfg) return;

		var volume = _parse_number(_first_value(frm.doc, cfg.volume));
		var weight = _parse_number(_first_value(frm.doc, cfg.weight));
		var volume_uom = _first_value(frm.doc, cfg.volume_uom);
		var weight_uom = _first_value(frm.doc, cfg.weight_uom);
		var company = frm.doc.company || (frappe.defaults && frappe.defaults.get_user_default && frappe.defaults.get_user_default('Company')) || null;

		// Quick local render (assuming base m³/kg) so the bar reflects edits immediately.
		var local_df = _local_density_factor(volume, weight);
		var local_pct = (local_df === null) ? 0 : Math.max(0, Math.min(100, (local_df / UPPER_BOUND) * 100));
		var local_reason = (local_df === null) ? _local_reason(volume, weight) : null;
		_render(frm, local_df, local_pct, local_reason);

		// Server confirmation when we have at least one value, so per-doc UOM
		// conversion (and richer error messages) is honoured.
		if (!frappe || !frappe.call) return;
		if (!volume && !weight) return;
		frappe.call({
			method: 'logistics.utils.measurements.get_density_factor_api',
			args: {
				volume: volume,
				weight: weight,
				volume_uom: volume_uom || null,
				weight_uom: weight_uom || null,
				company: company
			},
			freeze: false,
			callback: function (r) {
				if (!r || !r.message) return;
				var df = r.message.density_factor;
				var pct = r.message.percent;
				var reason = r.message.reason || null;
				if (df === undefined) df = null;
				_render(frm, df, pct, reason);
			}
		});
	}

	function _attach(doctype) {
		var cfg = DOCTYPES[doctype];
		if (!cfg) return;
		var handlers = {
			refresh: _update_density_factor,
			onload_post_render: _update_density_factor
		};
		// Watch every field that contributes to the density factor.
		var watched = [].concat(cfg.volume, cfg.weight, cfg.volume_uom, cfg.weight_uom);
		watched.forEach(function (fname) {
			if (!fname || handlers[fname]) return;
			handlers[fname] = _update_density_factor;
		});
		// Also recompute when the packages grid changes, since validate() rolls
		// package totals into total_volume / total_weight on save and refresh.
		handlers.packages_on_form_rendered = _update_density_factor;
		handlers.validate = _update_density_factor;
		frappe.ui.form.on(doctype, handlers);
	}

	Object.keys(DOCTYPES).forEach(_attach);

	// Expose for ad-hoc callers that want to refresh after a custom mutation.
	window.logistics_update_density_factor = _update_density_factor;
})();
