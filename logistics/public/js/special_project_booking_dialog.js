// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Create Booking/Order dialog for Special Project: lists each Lifecycle Job row, lets
// the user create the matching Air/Sea Booking, Transport/Declaration/Inbound Order from it.

(function () {
	"use strict";

	const PREVIEW_CLASS = "logistics-sp-ij-preview";

	function _lifecycleJobsPayload(frm) {
		return JSON.stringify((frm && frm.doc && frm.doc.lifecycle_jobs) || []);
	}

	function _encodeChoice(c) {
		const cr = c.creatable === false ? "0" : "1";
		const idx = c.detail_idx != null ? String(c.detail_idx) : "";
		return "d|" + idx + "|" + String(c.job_type || "") + "|" + cr;
	}

	function _decodeChoice(s) {
		const parts = String(s || "").split("|");
		if (parts[0] !== "d" || parts.length < 3) {
			return { detail_idx: null, job_type: "", creatable: true };
		}
		const idxStr = parts[1];
		const last = parts[parts.length - 1];
		let creatable = true;
		let end = parts.length;
		if (last === "0" || last === "1") {
			creatable = last === "1";
			end = parts.length - 1;
		}
		const idx = idxStr ? parseInt(idxStr, 10) : null;
		return {
			detail_idx: idx && !isNaN(idx) ? idx : null,
			job_type: parts.slice(2, end).join("|"),
			creatable: creatable,
		};
	}

	function _styles() {
		return (
			"<style>" +
			"." + PREVIEW_CLASS + "{font-size:13px;line-height:1.5;color:var(--text-color,#0f172a);}" +
			"." + PREVIEW_CLASS + " .sp-section{border:1px solid var(--border-color,#e2e8f0);border-radius:10px;background:var(--control-bg,#fff);margin-bottom:12px;overflow:hidden;}" +
			"." + PREVIEW_CLASS + " .sp-section-hd{padding:10px 14px;border-bottom:1px solid var(--border-color,#e2e8f0);background:var(--fg-color,#f8fafc);display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;}" +
			"." + PREVIEW_CLASS + " .sp-section-title{font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:var(--text-muted,#64748b);margin:0;}" +
			"." + PREVIEW_CLASS + " .sp-section-bd{padding:12px 14px;}" +
			"." + PREVIEW_CLASS + " .sp-dl{display:grid;grid-template-columns:minmax(110px,36%) 1fr;gap:8px 16px;margin:0;font-size:12px;}" +
			"." + PREVIEW_CLASS + " .sp-dl dt{margin:0;color:var(--text-muted,#64748b);font-weight:500;}" +
			"." + PREVIEW_CLASS + " .sp-dl dd{margin:0;word-break:break-word;}" +
			"." + PREVIEW_CLASS + " .sp-kvgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;}" +
			"." + PREVIEW_CLASS + " .sp-kv{padding:8px 10px;border-radius:8px;border:1px solid var(--border-color,#e2e8f0);background:var(--fg-color,#f8fafc);font-size:11px;}" +
			"." + PREVIEW_CLASS + " .sp-kv-k{display:block;color:var(--text-muted,#64748b);font-weight:600;text-transform:capitalize;margin-bottom:2px;}" +
			"." + PREVIEW_CLASS + " .sp-kv-v{display:block;font-weight:500;word-break:break-word;}" +
			"." + PREVIEW_CLASS + " .sp-empty{padding:16px;text-align:center;font-size:12px;color:var(--text-muted,#64748b);border:1px dashed var(--border-color,#e2e8f0);border-radius:8px;}" +
			"." + PREVIEW_CLASS + " .sp-scroll{max-height:240px;overflow:auto;border-radius:8px;border:1px solid var(--border-color,#e2e8f0);}" +
			"." + PREVIEW_CLASS + " .sp-table{width:100%;border-collapse:collapse;font-size:12px;}" +
			"." + PREVIEW_CLASS + " .sp-table th{position:sticky;top:0;z-index:1;text-align:left;padding:8px 10px;font-size:10px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:var(--text-muted,#64748b);background:var(--fg-color,#f1f5f9);border-bottom:1px solid var(--border-color,#e2e8f0);}" +
			"." + PREVIEW_CLASS + " .sp-table td{padding:8px 10px;border-bottom:1px solid var(--border-color,#e2e8f0);vertical-align:top;}" +
			"." + PREVIEW_CLASS + " .sp-table tr:last-child td{border-bottom:none;}" +
			"." + PREVIEW_CLASS + " .sp-loading{display:flex;align-items:center;gap:10px;padding:20px;color:var(--text-muted,#64748b);font-size:13px;}" +
			"." + PREVIEW_CLASS + " .sp-spin{width:18px;height:18px;border:2px solid var(--border-color,#e2e8f0);border-top-color:var(--primary,#5c6ac4);border-radius:50%;animation:spspin 0.7s linear infinite;}" +
			"@keyframes spspin{to{transform:rotate(360deg)}}" +
			".sp-cards-wrap{font-size:13px;color:var(--text-color,#0f172a);}" +
			".sp-cards-scroll{max-height:min(58vh,520px);overflow-y:auto;overflow-x:hidden;min-height:0;padding:2px 2px 6px 0;-webkit-overflow-scrolling:touch;}" +
			".sp-cards{display:flex;flex-direction:column;gap:10px;}" +
			".sp-card{border:1px solid var(--border-color,#e2e8f0);border-radius:10px;overflow:hidden;background:var(--control-bg,#fff);}" +
			".sp-card.open{border-color:var(--primary,#5c6ac4);box-shadow:0 0 0 1px rgba(92,106,196,0.12);}" +
			".sp-card-hd{display:flex;align-items:center;gap:10px;padding:10px 12px;font-weight:600;font-size:13px;flex-wrap:wrap;}" +
			".sp-card-toggle{cursor:pointer;display:flex;align-items:flex-start;gap:10px;flex:1;min-width:0;user-select:none;border-radius:6px;margin:-4px;padding:4px 6px 4px 4px;}" +
			".sp-card-toggle .sp-card-chevron{align-self:center;margin-top:8px;}" +
			".sp-card-head-block{display:flex;align-items:flex-start;gap:12px;min-width:0;flex:1;}" +
			".sp-card-mono-icon{flex-shrink:0;width:36px;height:36px;border-radius:8px;background:#1a1a1a;color:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;line-height:1;}" +
			".sp-card-mono-icon.sp-card-mono-icon--compact{font-size:11px;letter-spacing:-0.02em;}" +
			".sp-card-head-text{min-width:0;flex:1;}" +
			".sp-card-head-title{font-weight:600;font-size:14px;color:var(--text-color,#0f172a);line-height:1.3;margin:0 0 6px;}" +
			".sp-card-head-row2{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;line-height:1.45;}" +
			".sp-card-pill{display:inline-flex;align-items:center;padding:2px 10px;border-radius:999px;background:rgba(92,106,196,0.14);color:var(--primary,#5c6ac4);font-size:11px;font-weight:600;white-space:nowrap;max-width:100%;}" +
			".sp-card-sub{color:var(--text-muted,#64748b);font-weight:400;min-width:0;word-break:break-word;}" +
			".sp-card-toggle:hover{background:var(--fg-color,#f8fafc);}" +
			".sp-card-toggle:focus{outline:2px solid var(--primary);outline-offset:2px;}" +
			".sp-card-chevron{flex-shrink:0;width:22px;height:22px;display:flex;align-items:center;justify-content:center;color:var(--text-muted,#64748b);transition:transform .18s ease;font-size:11px;}" +
			".sp-card.open .sp-card-chevron{transform:rotate(90deg);}" +
			".sp-card-hd .sp-card-create{flex-shrink:0;margin-left:auto;cursor:pointer;}" +
			".sp-card-badges{display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center;margin-left:auto;flex-shrink:0;}" +
			".sp-chip-cancelled{font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;background:#fee2e2;color:#b91c1c;}" +
			".sp-card-bd{display:none;border-top:1px solid var(--border-color,#e2e8f0);padding:12px 14px;background:var(--modal-bg,#fafafa);max-height:min(45vh,380px);overflow-y:auto;overflow-x:hidden;}" +
			".sp-card.open .sp-card-bd{display:block;}" +
			".sp-chip-na{font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;background:var(--fill-color,#fef3c7);color:#b45309;flex-shrink:0;margin-left:auto;}" +
			".sp-ship-wrap{font-size:13px;color:var(--text-color,#0f172a);}" +
			".sp-ship-toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:0 2px 10px;border-bottom:1px solid var(--border-color,#e2e8f0);margin-bottom:10px;}" +
			".sp-ship-search{position:relative;flex:1;min-width:180px;}" +
			".sp-ship-search input{width:100%;padding:6px 10px 6px 30px;font-size:12px;border:1px solid var(--border-color,#e2e8f0);border-radius:999px;background:var(--control-bg,#fff);color:var(--text-color,#0f172a);outline:none;transition:border-color .15s,box-shadow .15s;}" +
			".sp-ship-search input:focus{border-color:var(--primary,#5c6ac4);box-shadow:0 0 0 3px rgba(92,106,196,0.15);}" +
			".sp-ship-search .sp-ship-search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--text-muted,#64748b);font-size:12px;pointer-events:none;}" +
			".sp-ship-quick{display:inline-flex;gap:6px;}" +
			".sp-ship-quick button{font-size:11px;padding:5px 10px;border-radius:6px;border:1px solid var(--border-color,#e2e8f0);background:var(--control-bg,#fff);color:var(--text-color,#0f172a);cursor:pointer;font-weight:500;transition:background .15s,border-color .15s;}" +
			".sp-ship-quick button:hover{background:var(--fg-color,#f1f5f9);border-color:var(--text-muted,#94a3b8);}" +
			".sp-ship-list{display:flex;flex-direction:column;gap:6px;max-height:min(55vh,440px);overflow-y:auto;overflow-x:hidden;padding:2px 4px 2px 2px;}" +
			".sp-ship-row{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:8px 12px;border:1px solid var(--border-color,#e2e8f0);border-radius:8px;background:var(--control-bg,#fff);transition:border-color .15s,box-shadow .15s,background .15s;}" +
			".sp-ship-row.has-qty{border-color:var(--primary,#5c6ac4);background:rgba(92,106,196,0.04);box-shadow:0 0 0 1px rgba(92,106,196,0.12);}" +
			".sp-ship-row.over-cap{border-color:#dc2626;background:#fef2f2;box-shadow:0 0 0 1px rgba(220,38,38,0.18);}" +
			".sp-ship-row.hidden{display:none;}" +
			".sp-ship-mono{flex-shrink:0;width:28px;height:28px;border-radius:6px;background:#1a1a1a;color:#fff;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;line-height:1;}" +
			".sp-ship-mono.compact{font-size:9px;letter-spacing:-0.02em;}" +
			".sp-ship-main{flex:1;min-width:0;display:flex;flex-direction:column;gap:3px;}" +
			".sp-ship-title{font-weight:600;font-size:13px;color:var(--text-color,#0f172a);line-height:1.25;word-break:break-word;}" +
			".sp-ship-chips{display:flex;flex-wrap:wrap;gap:4px;}" +
			".sp-ship-chip{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:600;padding:2px 7px;border-radius:999px;background:var(--fg-color,#f1f5f9);color:var(--text-muted,#64748b);white-space:nowrap;}" +
			".sp-ship-chip .sp-ship-chip-k{font-weight:500;color:var(--text-muted,#94a3b8);text-transform:uppercase;letter-spacing:0.04em;font-size:9px;}" +
			".sp-ship-chip .sp-ship-chip-v{font-weight:700;color:var(--text-color,#0f172a);}" +
			".sp-ship-chip.short .sp-ship-chip-v{color:#b45309;}" +
			".sp-ship-chip.short{background:#fef3c7;}" +
			".sp-ship-input{flex-shrink:0;display:flex;align-items:center;gap:6px;}" +
			".sp-ship-input input{width:100px;padding:5px 8px;font-size:12px;text-align:right;border:1px solid var(--border-color,#e2e8f0);border-radius:6px;background:var(--control-bg,#fff);color:var(--text-color,#0f172a);outline:none;font-variant-numeric:tabular-nums;transition:border-color .15s,box-shadow .15s;}" +
			".sp-ship-input input:focus{border-color:var(--primary,#5c6ac4);box-shadow:0 0 0 3px rgba(92,106,196,0.15);}" +
			".sp-ship-input input.has-value{border-color:var(--primary,#5c6ac4);font-weight:600;}" +
			".sp-ship-input input.is-invalid{border-color:#dc2626;color:#b91c1c;background:#fff;box-shadow:0 0 0 3px rgba(220,38,38,0.15);}" +
			".sp-ship-input .sp-ship-uom{font-size:11px;color:var(--text-muted,#64748b);min-width:24px;text-transform:lowercase;}" +
			".sp-ship-hint{flex-basis:100%;font-size:11px;color:#b91c1c;margin:2px 0 0 38px;display:none;line-height:1.4;}" +
			".sp-ship-row.over-cap .sp-ship-hint{display:block;}" +
			".sp-ship-empty{padding:24px 12px;text-align:center;color:var(--text-muted,#64748b);font-size:12px;border:1px dashed var(--border-color,#e2e8f0);border-radius:8px;}" +
			".sp-ship-summary{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:10px 2px 0;border-top:1px solid var(--border-color,#e2e8f0);margin-top:10px;font-size:12px;color:var(--text-muted,#64748b);}" +
			".sp-ship-summary .sp-ship-summary-count{font-weight:600;color:var(--text-color,#0f172a);}" +
			".sp-filter-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;}" +
			".sp-filter-bar label{font-size:12px;font-weight:600;color:var(--text-muted,#64748b);margin:0;}" +
			".sp-filter-bar select{min-width:160px;max-width:100%;font-size:12px;padding:5px 8px;border-radius:6px;border:1px solid var(--border-color,#e2e8f0);background:var(--control-bg,#fff);}" +
			".sp-card-filtered{display:none !important;}" +
			".sp-param-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;margin-bottom:12px;}" +
			".sp-param-cell{min-width:0;}" +
			".sp-param-cell .form-group{margin-bottom:0;}" +
			".sp-card-create:disabled,.sp-card-create.sp-card-create-disabled{opacity:0.55;cursor:not-allowed;pointer-events:none;}" +
			"</style>"
		);
	}

	function _lifecycleRowForIdx(frm, idx) {
		const rows = (frm && frm.doc && frm.doc.lifecycle_jobs) || [];
		const n = idx != null ? Number(idx) : NaN;
		if (isNaN(n)) return null;
		for (let i = 0; i < rows.length; i++) {
			if (Number(rows[i].idx) === n) return rows[i];
		}
		return null;
	}

	function _initialParamValues(frm, choice) {
		const suggested = choice.suggested_parameters || {};
		if (suggested && typeof suggested === "object" && Object.keys(suggested).length) {
			return suggested;
		}
		const row = _lifecycleRowForIdx(frm, choice.detail_idx) || {};
		const out = {};
		(choice.parameter_field_specs || []).forEach(function (spec) {
			if (spec && spec.fieldname && row[spec.fieldname] != null && String(row[spec.fieldname]).trim() !== "") {
				out[spec.fieldname] = row[spec.fieldname];
			}
		});
		return out;
	}

	function _collectCardParams($card) {
		const out = {};
		($card.data("sp-param-controls") || []).forEach(function (c) {
			if (!c || !c.key || !c.get_value) return;
			const v = c.get_value();
			if (v != null && String(v).trim() !== "") {
				out[c.key] = v;
			}
		});
		return out;
	}

	function _mountParamControl($cell, spec, frm, value) {
		if (!spec || !spec.fieldname) return null;
		const df = {
			fieldname: spec.fieldname,
			label: spec.label || spec.fieldname,
			fieldtype: spec.fieldtype || "Data",
			options: spec.options || "",
		};
		if (spec.fieldtype === "Dynamic Link" && spec.options_fieldname) {
			df.get_options = function () {
				const row = { location_type: "UNLOCO" };
				($cell.closest(".sp-card").data("sp-param-controls") || []).forEach(function (c) {
					if (c && c.key === spec.options_fieldname && c.get_value) {
						row[spec.options_fieldname] = c.get_value();
					}
				});
				return row[spec.options_fieldname] || "UNLOCO";
			};
		}
		const ctrl = frappe.ui.form.make_control({
			df: df,
			parent: $cell,
			render_input: true,
		});
		ctrl.set_value(value || "");
		return {
			key: spec.fieldname,
			control: ctrl,
			get_value: function () {
				return ctrl.get_value();
			},
		};
	}

	function _mountCardParameterControls($card, frm, choice) {
		if ($card.data("sp-params-mounted")) return;
		const specs = choice.parameter_field_specs || [];
		const $grid = $("<div class='sp-param-grid'>");
		const controls = [];
		const initial = _initialParamValues(frm, choice);
		specs.forEach(function (spec) {
			const $cell = $("<div class='sp-param-cell'>");
			$grid.append($cell);
			const c = _mountParamControl($cell, spec, frm, initial[spec.fieldname]);
			if (c) controls.push(c);
		});
		$card.find(".sp-card-bd").prepend($grid);
		$card.data("sp-param-controls", controls);
		$card.data("sp-params-mounted", true);
	}

	function _updateCardCreateState($card, preview) {
		preview = preview || {};
		$card.data("sp-preview", preview);
		const $btn = $card.find(".sp-card-create");
		if (!$btn.length) return;
		const ready = preview.creatable === true;
		$btn.prop("disabled", !ready);
		$btn.toggleClass("sp-card-create-disabled", !ready);
	}

	function _wildcardConfirmMessage(preview, choice) {
		const fields = preview.wildcard_fields || [];
		if (!fields.length) return "";
		const labels = {};
		(choice.parameter_field_specs || []).forEach(function (s) {
			if (s && s.fieldname) labels[s.fieldname] = s.label || s.fieldname;
		});
		const names = fields.map(function (fn) {
			return labels[fn] || fn.replace(/_/g, " ");
		});
		return __(
			"Matching project charge rows leave these parameters blank (wildcard): {0}. Create the booking/order anyway?",
			[names.join(", ")]
		);
	}

	function _loadCardPreview($pv, frm, choiceEnc, onLoaded, creationParameters) {
		const dec = _decodeChoice(choiceEnc);
		$pv.html(_renderPreviewHtml(null));
		const args = {
			special_project: frm.doc.name,
			job_type: dec.job_type != null ? dec.job_type : "",
			lifecycle_job_idx: dec.detail_idx,
			lifecycle_jobs: _lifecycleJobsPayload(frm),
		};
		if (creationParameters && Object.keys(creationParameters).length) {
			args.creation_parameters = JSON.stringify(creationParameters);
		}
		frappe.call({
			method: "logistics.special_projects.special_project_booking_creation.get_special_project_booking_preview",
			args: args,
			callback: function (r) {
				const $card = $pv.closest(".sp-card");
				if (r.exc) {
					$pv.html(
						_styles() +
							"<div class='" + PREVIEW_CLASS + "'><div class='sp-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
							__("Preview could not be loaded.") + "</div></div>"
					);
					_updateCardCreateState($card, { creatable: false });
				} else {
					const msg = r.message || {};
					$pv.html(_renderPreviewHtml(msg));
					_updateCardCreateState($card, msg);
				}
				if (onLoaded) onLoaded();
			},
			error: function () {
				const $card = $pv.closest(".sp-card");
				$pv.html(
					_styles() +
						"<div class='" + PREVIEW_CLASS + "'><div class='sp-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
						__("Preview could not be loaded.") + "</div></div>"
				);
				_updateCardCreateState($card, { creatable: false });
				if (onLoaded) onLoaded();
			},
		});
	}

	function _scheduleCardPreviewReload($card, frm) {
		let timer = $card.data("sp-preview-timer");
		if (timer) clearTimeout(timer);
		timer = setTimeout(function () {
			$card.data("sp-preview-timer", null);
			const enc = $card.attr("data-choice");
			const $pv = $card.find(".sp-card-preview");
			_loadCardPreview($pv, frm, enc, null, _collectCardParams($card));
		}, 350);
		$card.data("sp-preview-timer", timer);
	}

	function _buildServiceTypeFilter(filters) {
		const $bar = $("<div class='sp-filter-bar'>");
		$bar.append($("<label>").text(__("Service Type")));
		const $sel = $("<select class='sp-service-filter'>");
		$sel.append($("<option>").attr("value", "").text(__("All")));
		(filters || []).forEach(function (st) {
			$sel.append($("<option>").attr("value", st).text(st));
		});
		$bar.append($sel);
		return $bar;
	}

	function _applyServiceTypeFilter($root, value) {
		const v = (value || "").trim();
		$root.find(".sp-card").each(function () {
			const $c = $(this);
			const st = ($c.attr("data-service-type") || "").trim();
			$c.toggleClass("sp-card-filtered", !!(v && st !== v));
		});
	}

	function _formatParamsHtml(params) {
		if (!params || typeof params !== "object") {
			return "";
		}
		const keys = Object.keys(params).filter(function (k) {
			return k !== "charge_group";
		});
		if (!keys.length) {
			return "<div class='sp-empty'>" + __("No parameters on this selection.") + "</div>";
		}
		const esc = frappe.utils.escape_html;
		const cells = keys
			.map(function (k) {
				return (
					"<div class='sp-kv'><span class='sp-kv-k'>" +
					esc(k.replace(/_/g, " ")) +
					"</span><span class='sp-kv-v'>" +
					esc(String(params[k])) +
					"</span></div>"
				);
			})
			.join("");
		return "<div class='sp-kvgrid'>" + cells + "</div>";
	}

	function _formatChargesHtml(charges) {
		if (!charges || !charges.length) {
			return "<div class='sp-empty'>" + __("No charge lines match this service on the project.") + "</div>";
		}
		const esc = frappe.utils.escape_html;
		const rows = charges
			.map(function (c) {
				const rate = c.unit_rate != null ? c.unit_rate : c.per_unit_rate;
				const cur = c.currency || c.selling_currency || "";
				const label = (c.item_code || "") + (c.item_name ? " — " + c.item_name : "");
				let source = c.charge_source || "";
				if (c.sales_quote_link) {
					source = source ? source + " · " + c.sales_quote_link : String(c.sales_quote_link);
				} else if (c.change_request) {
					source = source ? source + " · " + c.change_request : String(c.change_request);
				}
				return (
					"<tr><td>" +
					esc(c.service_type || "") +
					"</td><td>" +
					esc(String(label)) +
					"</td><td>" +
					esc(String(source)) +
					"</td><td style='white-space:nowrap'>" +
					esc(rate != null ? String(rate) : "—") +
					"</td><td>" +
					esc(String(cur)) +
					"</td></tr>"
				);
			})
			.join("");
		return (
			"<div class='sp-scroll'><table class='sp-table'><thead><tr>" +
			"<th>" + __("Service") + "</th>" +
			"<th>" + __("Item") + "</th>" +
			"<th>" + __("Source") + "</th>" +
			"<th>" + __("Rate") + "</th>" +
			"<th>" + __("Curr.") + "</th>" +
			"</tr></thead><tbody>" + rows + "</tbody></table></div>"
		);
	}

	function _renderPreviewHtml(p) {
		if (!p) {
			return (
				_styles() +
				"<div class='" + PREVIEW_CLASS + "'><div class='sp-loading'><span class='sp-spin'></span>" +
				__("Loading preview…") + "</div></div>"
			);
		}
		const esc = frappe.utils.escape_html;
		const sc = p.source_context || {};

		let uncreatable = "";
		if (p.not_creatable_message) {
			uncreatable =
				"<div class='sp-section' style='border-color:var(--orange-500,#ed6c02)'>" +
				"<div class='sp-section-bd' style='font-size:12px;line-height:1.45'>" +
				esc(String(p.not_creatable_message)) +
				"</div></div>";
		}

		const ctxRows = [
			[__("Source"), esc((sc.source_doctype || "") + " · " + (sc.source_name || ""))],
			[__("Customer"), esc(sc.customer || "—")],
			[__("Company"), esc(sc.company || "—")],
		];
		const targetDoctype = (p.job_type || "").toString().trim();
		if (targetDoctype) {
			ctxRows.push([__("New document"), esc(__(targetDoctype))]);
		}
		const ctxDl =
			"<dl class='sp-dl'>" +
			ctxRows.map(function (r) { return "<dt>" + r[0] + "</dt><dd>" + r[1] + "</dd>"; }).join("") +
			"</dl>";

		const secContext =
			"<section class='sp-section'><header class='sp-section-hd'>" +
			"<h3 class='sp-section-title'>" + __("Source & links") + "</h3></header>" +
			"<div class='sp-section-bd'>" + ctxDl + "</div></section>";

		const secParams =
			"<section class='sp-section'><header class='sp-section-hd'>" +
			"<h3 class='sp-section-title'>" + __("Line parameters") + "</h3>" +
			"<span style='font-size:10px;color:var(--text-muted,#64748b)'>" + __("Applied on create") + "</span>" +
			"</header><div class='sp-section-bd'>" + _formatParamsHtml(p.job_detail_parameters) + "</div></section>";

		const charges = p.charges || [];
		const secCharges =
			"<section class='sp-section'><header class='sp-section-hd'>" +
			"<h3 class='sp-section-title'>" + __("Matching project charges") + "</h3>" +
			"<span style='font-size:10px;color:var(--text-muted,#64748b)'>" + String(charges.length) + " " + __("rows") + "</span>" +
			"</header><div class='sp-section-bd'>" + _formatChargesHtml(charges) + "</div></section>";

		return (
			_styles() +
			"<div class='" + PREVIEW_CLASS + "'>" + uncreatable + secContext + secParams + secCharges + "</div>"
		);
	}

	function _iconText(c) {
		if (c && c.detail_idx != null && c.detail_idx !== "") {
			const n = Number(c.detail_idx);
			if (!isNaN(n) && n > 0) return String(n);
		}
		const s = ((c && c.service_type) || (c && c.job_type) || "").toString().trim();
		const m = s.match(/[A-Za-z0-9]/);
		return m ? m[0].toUpperCase() : "?";
	}

	function _buildHead(c) {
		const title =
			(c.header_title && String(c.header_title).trim()) ||
			(c.service_type && String(c.service_type).trim()) ||
			String(c.job_type || "");
		const badge =
			(c.header_badge && String(c.header_badge).trim()) ||
			(c.job_no && String(c.job_no).trim()) ||
			(c.detail_idx != null ? __("Pending") : __("Job Details"));
		const sub = c.header_subtitle ? String(c.header_subtitle) : "";

		const $block = $("<div>").addClass("sp-card-head-block");
		const iconText = _iconText(c);
		const $icon = $("<span>").addClass("sp-card-mono-icon").text(iconText);
		if (iconText.length > 1) $icon.addClass("sp-card-mono-icon--compact");
		$block.append($icon);

		const $text = $("<div>").addClass("sp-card-head-text");
		$text.append($("<div>").addClass("sp-card-head-title").text(title));
		const $row2 = $("<div>").addClass("sp-card-head-row2");
		$row2.append($("<span>").addClass("sp-card-pill").text(badge));
		if (sub) $row2.append($("<span>").addClass("sp-card-sub").text(sub));
		$text.append($row2);
		$block.append($text);
		return $block;
	}

	function _buildCards(choices) {
		const $wrap = $("<div class='sp-cards-wrap'>");
		$wrap.append(
			$("<p>")
				.addClass("text-muted")
				.css({ fontSize: "12px", marginBottom: "10px", lineHeight: 1.45 })
				.text(__("Filter by service type, expand a card to set parameters, then use Create when enabled."))
		);
		const $scroll = $("<div class='sp-cards-scroll'>");
		const $cards = $("<div class='sp-cards'>");
		choices.forEach(function (c) {
			const enc = _encodeChoice(c);
			const creatable = c.creatable !== false;
			const $card = $("<div class='sp-card'>").attr("data-choice", enc);
			if (c.service_type) {
				$card.attr("data-service-type", c.service_type);
			}
			$card.data("sp-choice", c);
			if (c.suggested_order_title) {
				$card.attr("data-suggested-order-title", c.suggested_order_title);
			}
			const $hd = $("<div class='sp-card-hd'>");
			const $toggle = $("<div class='sp-card-toggle' role='button' tabindex='0'>");
			$toggle.append($("<span class='sp-card-chevron'>").text("\u25B8"));
			$toggle.append(_buildHead(c));
			$hd.append($toggle);
			if (creatable) {
				$hd.append(
					$("<button type='button'>")
						.addClass("btn btn-primary btn-sm sp-card-create sp-card-create-disabled")
						.prop("disabled", true)
						.text(__("Create"))
				);
			} else {
				const linked = c.job_no != null && String(c.job_no).trim() !== "";
				const $badges = $("<span class='sp-card-badges'>");
				if (c.linked_job_cancelled) $badges.append($("<span class='sp-chip-cancelled'>").text(__("Cancelled")));
				$badges.append($("<span class='sp-chip-na'>").text(linked ? __("Linked") : __("Cannot create")));
				$hd.append($badges);
			}
			const $bd = $("<div class='sp-card-bd'>");
			const $pv = $("<div class='sp-card-preview'>");
			$bd.append($pv);
			$card.append($hd).append($bd);
			$cards.append($card);
		});
		$scroll.append($cards);
		$wrap.append($scroll);
		return $wrap;
	}

	/**
	 * Navigate to the freshly created booking/order. Uses the shared
	 * ``logistics_navigate_when_doc_exists`` helper (from internal_job_create_from_source.js,
	 * loaded via app_include_js) to poll the row's existence first; this prevents the
	 * "<Doctype> ... not found" message that the desk shows when ``frappe.set_route``
	 * loads the new form before the just-inserted row is visible to the next request.
	 */
	function _routeAfterCreate(msg) {
		function _go(doctype, docname) {
			function navigate() {
				frappe.set_route("Form", doctype, docname);
			}
			if (window.logistics_navigate_when_doc_exists) {
				window.logistics_navigate_when_doc_exists(doctype, docname, navigate);
			} else {
				navigate();
			}
		}
		if (msg.air_booking) {
			_go("Air Booking", msg.air_booking);
		} else if (msg.sea_booking) {
			_go("Sea Booking", msg.sea_booking);
		} else if (msg.transport_order) {
			_go("Transport Order", msg.transport_order);
		} else if (msg.declaration_order) {
			_go("Declaration Order", msg.declaration_order);
		} else if (msg.inbound_order) {
			_go("Inbound Order", msg.inbound_order);
		} else if (msg.project_order) {
			_go("Project Order", msg.project_order);
		}
	}

	const _PACKAGE_JOB_TYPES = ["Transport Order", "Air Booking", "Sea Booking", "Inbound Order"];

	function _shipRowTitle(row) {
		const item =
			row.warehouse_item_name ||
			row.warehouse_item ||
			row.commodity ||
			row.description ||
			__("Item");
		const lineNo = row.package_row != null ? String(row.package_row) : "";
		if (lineNo) {
			return __("Line {0} · {1}", [lineNo, item]);
		}
		return item;
	}

	function _shipRowIconText(row) {
		if (row.package_row != null && row.package_row !== "") {
			return String(row.package_row);
		}
		const t = (row.warehouse_item_name || row.warehouse_item || row.commodity || "").toString().trim();
		const m = t.match(/[A-Za-z0-9]/);
		return m ? m[0].toUpperCase() : "?";
	}

	function _shipRowSearchText(row) {
		const parts = [
			row.package_row != null ? String(row.package_row) : "",
			_shipRowTitle(row),
			row.warehouse_item,
			row.warehouse_item_name,
			row.commodity,
			row.description,
			row.site,
			row.site_label,
			row.reference_no,
		];
		return parts
			.filter(function (p) {
				return p != null && String(p).trim() !== "";
			})
			.join(" ")
			.toLowerCase();
	}

	function _fmtQty(v) {
		const n = Number(v);
		if (!isFinite(n)) return "0";
		if (Math.abs(n - Math.round(n)) < 1e-9) return String(Math.round(n));
		return n.toFixed(3).replace(/\.?0+$/, "");
	}

	function _buildShipmentRows(rows) {
		const $list = $("<div class='sp-ship-list'>");
		rows.forEach(function (row) {
			const $row = $("<div class='sp-ship-row'>").attr("data-row", row.package_row);
			const title = _shipRowTitle(row);
			$row.attr("data-search", _shipRowSearchText(row));

			const iconText = _shipRowIconText(row);
			const $mono = $("<span class='sp-ship-mono'>").text(iconText);
			if (iconText.length > 1) $mono.addClass("compact");
			$row.append($mono);

			const $main = $("<div class='sp-ship-main'>");
			$main.append($("<div class='sp-ship-title'>").text(title));
			const $chips = $("<div class='sp-ship-chips'>");
			if (row.package_row != null) {
				$chips.append(
					$("<span class='sp-ship-chip'>")
						.append($("<span class='sp-ship-chip-k'>").text(__("Packages line")))
						.append($("<span class='sp-ship-chip-v'>").text(String(row.package_row)))
				);
			}
			if (row.site_label || row.site) {
				$chips.append(
					$("<span class='sp-ship-chip'>")
						.append($("<span class='sp-ship-chip-k'>").text(__("Site")))
						.append($("<span class='sp-ship-chip-v'>").text(String(row.site_label || row.site)))
				);
			}
			if (row.reference_no) {
				$chips.append(
					$("<span class='sp-ship-chip'>")
						.append($("<span class='sp-ship-chip-k'>").text(__("Ref")))
						.append($("<span class='sp-ship-chip-v'>").text(String(row.reference_no)))
				);
			}
			if (row.description && !row.warehouse_item && !row.commodity) {
				$chips.append(
					$("<span class='sp-ship-chip'>")
						.append($("<span class='sp-ship-chip-k'>").text(__("Desc")))
						.append($("<span class='sp-ship-chip-v'>").text(String(row.description)))
				);
			}
			$chips.append(
				$("<span class='sp-ship-chip short'>")
					.append($("<span class='sp-ship-chip-k'>").text(__("Remaining")))
					.append($("<span class='sp-ship-chip-v'>").text(_fmtQty(row.qty_short || 0)))
			);
			$chips.append(
				$("<span class='sp-ship-chip'>")
					.append($("<span class='sp-ship-chip-k'>").text(__("Required")))
					.append($("<span class='sp-ship-chip-v'>").text(_fmtQty(row.qty_required || 0)))
			);
			$chips.append(
				$("<span class='sp-ship-chip'>")
					.append($("<span class='sp-ship-chip-k'>").text(__("Delivered")))
					.append($("<span class='sp-ship-chip-v'>").text(_fmtQty(row.qty_on_site || 0)))
			);
			if (row.uom) {
				$chips.append(
					$("<span class='sp-ship-chip'>")
						.append($("<span class='sp-ship-chip-k'>").text(__("UOM")))
						.append($("<span class='sp-ship-chip-v'>").text(String(row.uom)))
				);
			}
			$main.append($chips);
			$row.append($main);

			const remaining = parseFloat(row.qty_short) || 0;
			const $inputWrap = $("<div class='sp-ship-input'>");
			const $input = $("<input type='number' min='0' step='any' inputmode='decimal' placeholder='0'>")
				.attr("aria-label", __("Qty for {0}", [title]))
				.attr("data-short", row.qty_short || 0)
				.attr("data-remaining", remaining)
				.attr("max", remaining);
			$inputWrap.append($input);
			if (row.uom) {
				$inputWrap.append($("<span class='sp-ship-uom'>").text(String(row.uom)));
			}
			$row.append($inputWrap);
			$row.append($("<div class='sp-ship-hint'>"));
			$list.append($row);
		});
		return $list;
	}

	function _updateShipSummary($wrap, dialog) {
		const $rows = $wrap.find(".sp-ship-row");
		let withQty = 0;
		let total = 0;
		let overCap = 0;
		$rows.each(function () {
			const $r = $(this);
			const v = parseFloat($r.find("input").val()) || 0;
			if (v > 0) {
				withQty += 1;
				total += v;
			}
			if ($r.hasClass("over-cap")) {
				overCap += 1;
			}
		});
		const $count = $wrap.find(".sp-ship-summary-count");
		$count.text(
			__("{0} of {1} selected", [String(withQty), String($rows.length)]) +
				" · " +
				__("Total") +
				" " +
				_fmtQty(total)
		);
		if (dialog) {
			if (withQty > 0 && overCap === 0) {
				dialog.enable_primary_action();
			} else {
				dialog.disable_primary_action();
			}
		}
	}

	function _bindShipmentDialog($wrap, rows, dialog) {
		$wrap.on("input", ".sp-ship-row input", function () {
			const $input = $(this);
			const v = parseFloat($input.val()) || 0;
			const cap = parseFloat($input.attr("data-remaining")) || 0;
			const overCap = v > cap;
			const $row = $input.closest(".sp-ship-row");
			$row.toggleClass("has-qty", v > 0 && !overCap);
			$row.toggleClass("over-cap", overCap);
			$input.toggleClass("has-value", v > 0 && !overCap);
			$input.toggleClass("is-invalid", overCap);
			const $hint = $row.find(".sp-ship-hint");
			if (overCap) {
				const uom = ($input.next(".sp-ship-uom").text() || "").trim();
				const msg = cap > 0
					? __("Only {0}{1} remaining to deliver — reduce the quantity to continue.", [
						_fmtQty(cap),
						uom ? " " + uom : "",
					])
					: __("Nothing remaining to deliver on this line.");
				$hint.text(msg);
			} else {
				$hint.empty();
			}
			_updateShipSummary($wrap, dialog);
		});

		$wrap.on("input", ".sp-ship-search input", function () {
			const q = ($(this).val() || "").toString().toLowerCase().trim();
			let visible = 0;
			$wrap.find(".sp-ship-row").each(function () {
				const $r = $(this);
				const hay = $r.attr("data-search") || "";
				const match = !q || hay.indexOf(q) >= 0;
				$r.toggleClass("hidden", !match);
				if (match) visible += 1;
			});
			const $empty = $wrap.find(".sp-ship-empty");
			$empty.toggle(visible === 0);
		});

		$wrap.on("click", ".sp-ship-quick-clear", function () {
			$wrap.find(".sp-ship-row input").val("").removeClass("has-value is-invalid");
			$wrap.find(".sp-ship-row").removeClass("has-qty over-cap");
			$wrap.find(".sp-ship-hint").empty();
			_updateShipSummary($wrap, dialog);
		});

		$wrap.on("click", ".sp-ship-quick-fill", function () {
			$wrap.find(".sp-ship-row").each(function () {
				const $r = $(this);
				if ($r.hasClass("hidden")) return;
				const $input = $r.find("input");
				const cap = parseFloat($input.attr("data-remaining")) || 0;
				if (cap > 0) {
					$input.val(cap).trigger("input");
				}
			});
			_updateShipSummary($wrap, dialog);
		});

		_updateShipSummary($wrap, dialog);
	}

	function _collectShipmentLines($wrap, rows) {
		const byIdx = {};
		rows.forEach(function (r) { byIdx[r.package_row] = r; });
		const lines = [];
		let overCap = 0;
		$wrap.find(".sp-ship-row").each(function () {
			const $r = $(this);
			const idx = $r.attr("data-row");
			const $input = $r.find("input");
			const qty = parseFloat($input.val()) || 0;
			const cap = parseFloat($input.attr("data-remaining")) || 0;
			if (qty > cap) {
				overCap += 1;
				return;
			}
			if (qty > 0 && byIdx[idx]) {
				const row = byIdx[idx];
				lines.push({
					package_row: row.package_row,
					warehouse_item: row.warehouse_item,
					commodity: row.commodity,
					description: row.description,
					uom: row.uom,
					qty: qty,
				});
			}
		});
		return { lines: lines, overCap: overCap };
	}

	function _promptShipmentLines(frm, dec, callback) {
		frappe.call({
			method: "logistics.special_projects.special_project_packages.get_packages_for_shipment_picker",
			args: { special_project: frm.doc.name },
			callback: function (r) {
				const rows = r.message || [];
				if (!rows.length) {
					callback(null);
					return;
				}
				const d = new frappe.ui.Dialog({
					title: __("Shipment lines"),
					size: "large",
					fields: [{ fieldname: "ship_html", fieldtype: "HTML" }],
					primary_action_label: __("Continue"),
				primary_action: function () {
					const $wrap = d.fields_dict.ship_html.$wrapper.find(".sp-ship-wrap");
					const result = _collectShipmentLines($wrap, rows);
					if (result.overCap > 0) {
						frappe.show_alert(
							{
								message: __(
									"Some quantities exceed what is on site. Reduce them before continuing."
								),
								indicator: "orange",
							},
							5
						);
						return;
					}
					if (!result.lines.length) {
						frappe.show_alert(
							{
								message: __("Set a quantity on at least one row, or close the dialog to cancel."),
								indicator: "orange",
							},
							5
						);
						return;
					}
					d.hide();
					callback(JSON.stringify(result.lines));
				},
				});

				const $host = d.fields_dict.ship_html.$wrapper;
				$host.empty();
				$host.append(_styles());

				const $wrap = $("<div class='sp-ship-wrap'>");
				$wrap.append(
					$("<p>")
						.addClass("text-muted")
						.css({ fontSize: "12px", marginBottom: "10px", lineHeight: 1.45 })
						.text(
							__(
								"Each row is one Packages line on this Special Project. Quantities apply only to that line. Set a quantity on at least one row to continue, or close this dialog to cancel."
							)
						)
				);

				const $toolbar = $("<div class='sp-ship-toolbar'>");
				const $search = $("<div class='sp-ship-search'>");
				$search.append($("<span class='sp-ship-search-icon'>").html("&#9906;"));
				$search.append(
					$("<input type='text'>").attr("placeholder", __("Filter items by name..."))
				);
				$toolbar.append($search);
				const $quick = $("<div class='sp-ship-quick'>");
				$quick.append($("<button type='button' class='sp-ship-quick-fill'>").text(__("Fill all to remaining")));
				$quick.append($("<button type='button' class='sp-ship-quick-clear'>").text(__("Clear all")));
				$toolbar.append($quick);
				$wrap.append($toolbar);

				$wrap.append(_buildShipmentRows(rows));
				$wrap.append(
					$("<div class='sp-ship-empty'>")
						.text(__("No items match your filter."))
						.hide()
				);

				const $summary = $("<div class='sp-ship-summary'>");
				$summary.append($("<span class='sp-ship-summary-count'>").text(""));
				$summary.append(
					$("<span>").text(__("Leave a row at 0 to omit it from this shipment."))
				);
				$wrap.append($summary);

				$host.append($wrap);
				_bindShipmentDialog($wrap, rows, d);
				d.show();
				setTimeout(function () {
					$host.find(".sp-ship-search input").trigger("focus");
				}, 80);
			},
		});
	}

	function _callCreate(frm, dec, orderTitle, onDialogHide, shipmentLines, creationParameters) {
		const args = {
			special_project: frm.doc.name,
			job_type: dec.job_type,
			lifecycle_job_idx: dec.detail_idx,
			lifecycle_jobs: _lifecycleJobsPayload(frm),
		};
		if (dec.job_type === "Project Order" && orderTitle) {
			args.order_title = orderTitle;
		}
		if (shipmentLines) {
			args.shipment_lines = shipmentLines;
		}
		if (creationParameters && Object.keys(creationParameters).length) {
			args.creation_parameters = JSON.stringify(creationParameters);
		}
		frappe.call({
			method: "logistics.special_projects.special_project_booking_creation.create_booking_or_order_from_special_project",
			args: args,
			freeze: true,
			freeze_message: __("Creating..."),
			callback: function (r) {
				if (onDialogHide) onDialogHide();
				if (!r.message) return;
				if (r.message.message) {
					frappe.show_alert({ message: r.message.message, indicator: "green" }, 5);
				}
				function _afterReload() {
					_routeAfterCreate(r.message);
				}
				if (frm && frm.doc && frm.doc.name && typeof frm.reload_doc === "function") {
					frm.reload_doc().then(_afterReload).catch(_afterReload);
				} else {
					_afterReload();
				}
			},
		});
	}

	function _proceedCreate(frm, dec, $card, onDialogHide, creationParameters) {
		if (dec.job_type === "Project Order") {
			const defaultTitle =
				($card && $card.attr("data-suggested-order-title")) ||
				(dec.suggested_order_title && String(dec.suggested_order_title)) ||
				"";
			frappe.prompt(
				[
					{
						fieldname: "order_title",
						fieldtype: "Data",
						label: __("Order Title"),
						reqd: 1,
						default: defaultTitle,
					},
				],
				function (values) {
					_promptShipmentLines(frm, dec, function (shipmentLines) {
						_callCreate(
							frm,
							dec,
							values.order_title,
							onDialogHide,
							shipmentLines,
							creationParameters
						);
					});
				},
				__("Create Project Order"),
				__("Continue")
			);
			return;
		}
		if (_PACKAGE_JOB_TYPES.indexOf(dec.job_type) >= 0) {
			_promptShipmentLines(frm, dec, function (shipmentLines) {
				_callCreate(frm, dec, null, onDialogHide, shipmentLines, creationParameters);
			});
			return;
		}
		_callCreate(frm, dec, null, onDialogHide, null, creationParameters);
	}

	function _runCreate(frm, dec, $card, onDialogHide) {
		const preview = ($card && $card.data("sp-preview")) || {};
		const choice = ($card && $card.data("sp-choice")) || {};
		const creationParameters = _collectCardParams($card);
		if (preview.has_charge_match === false || preview.has_quote_match === false) {
			frappe.msgprint({
				title: __("Create Booking / Order"),
				message:
					preview.not_creatable_message ||
					__("No parameters match on your input against project charge lines"),
				indicator: "orange",
			});
			return;
		}
		if (preview.creatable !== true) {
			frappe.msgprint({
				title: __("Create Booking / Order"),
				message:
					preview.not_creatable_message ||
					__("Set at least one parameter and ensure matching charges before creating."),
				indicator: "orange",
			});
			return;
		}
		const confirmMsg = _wildcardConfirmMessage(preview, choice);
		if (confirmMsg) {
			frappe.confirm(confirmMsg, function () {
				_proceedCreate(frm, dec, $card, onDialogHide, creationParameters);
			});
			return;
		}
		_proceedCreate(frm, dec, $card, onDialogHide, creationParameters);
	}

	function _bindCards($root, frm, d) {
		$root.on("change", ".sp-param-cell input, .sp-param-cell select", function () {
			const $card = $(this).closest(".sp-card");
			_scheduleCardPreviewReload($card, frm);
		});
		$root.on("click", ".sp-card-toggle", function () {
			const $card = $(this).closest(".sp-card");
			$card.toggleClass("open");
			if ($card.hasClass("open")) {
				const choice = $card.data("sp-choice") || {};
				_mountCardParameterControls($card, frm, choice);
				const $pv = $card.find(".sp-card-preview");
				const enc = $card.attr("data-choice");
				_loadCardPreview($pv, frm, enc, function () {
					$pv.data("sp-loaded", true);
				}, _collectCardParams($card));
				($card.data("sp-param-controls") || []).forEach(function (c) {
					if (c && c.control && c.control.$wrapper) {
						c.control.$wrapper.off("change.spparams").on("change.spparams", function () {
							_scheduleCardPreviewReload($card, frm);
						});
					}
				});
			}
		});
		$root.on("keydown", ".sp-card-toggle", function (e) {
			if (e.which === 13 || e.which === 32) {
				e.preventDefault();
				$(this).trigger("click");
			}
		});
		$root.on("click", ".sp-card-create", function (e) {
			e.stopPropagation();
			const $card = $(this).closest(".sp-card");
			if ($(this).prop("disabled")) return;
			const enc = $card.attr("data-choice");
			const dec = _decodeChoice(enc);
			if (!dec.job_type) {
				frappe.msgprint({
					title: __("Create Booking / Order"),
					message: __("Set Service Type on this Lifecycle Jobs line before creating."),
					indicator: "orange",
				});
				return;
			}
			if (dec.creatable === false) {
				frappe.msgprint({
					title: __("Create Booking / Order"),
					message:
						dec.not_creatable_message ||
						__("This line cannot be created automatically from here."),
					indicator: "orange",
				});
				return;
			}
			_runCreate(frm, dec, $card, function () {
				d.hide();
			});
		});
		$root.on("change", ".sp-service-filter", function () {
			_applyServiceTypeFilter($root, $(this).val());
		});
	}

	function _introHtml(frm) {
		const esc = frappe.utils.escape_html;
		const ref = esc(__("Special Project") + " · " + (frm.doc.name || ""));
		return (
			"<div class='" + PREVIEW_CLASS + "' style='margin-bottom:4px'>" +
			"<div style='font-size:12px;color:var(--text-muted,#64748b);line-height:1.5'>" +
			"<strong style='color:var(--text-color,#0f172a)'>" + __("From") + "</strong> " + ref + "<br>" +
			__("Each card is one Lifecycle Jobs line. Set parameters in the card, then Create when enabled.") +
			"</div></div>"
		);
	}

	window.logistics_show_special_project_booking_dialog = function (frm) {
		if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
			frappe.msgprint({
				title: __("Save Required"),
				message: __("Save the Special Project before creating bookings or orders."),
				indicator: "orange",
			});
			return;
		}
		frappe.call({
			method: "logistics.special_projects.special_project_booking_creation.get_special_project_booking_choices",
			args: {
				special_project: frm.doc.name,
				lifecycle_jobs: _lifecycleJobsPayload(frm),
			},
			freeze: true,
			freeze_message: __("Loading options..."),
			callback: function (r) {
				const msg = r.message || {};
				const choices = msg.choices || [];
				if (!choices.length) {
					frappe.msgprint({
						title: __("Create Booking / Order"),
						message: __("No Lifecycle Jobs lines on this Special Project."),
						indicator: "orange",
					});
					return;
				}
				const d = new frappe.ui.Dialog({
					title: __("Create Booking / Order"),
					size: "large",
					fields: [
						{ fieldname: "info", fieldtype: "HTML" },
						{ fieldname: "cards_html", fieldtype: "HTML", label: "" },
					],
					primary_action_label: __("Close"),
					primary_action: function () {
						d.hide();
					},
				});
				if (d.fields_dict.info && d.fields_dict.info.$wrapper) {
					d.fields_dict.info.$wrapper.html(_introHtml(frm));
				}
				const $cardsRoot = d.fields_dict.cards_html && d.fields_dict.cards_html.$wrapper;
				if ($cardsRoot && $cardsRoot.length) {
					$cardsRoot.empty();
					$cardsRoot.append(_styles());
					$cardsRoot.append(_buildServiceTypeFilter(msg.service_type_filters || []));
					$cardsRoot.append(_buildCards(choices));
					_bindCards($cardsRoot, frm, d);
				}
				d.show();
			},
		});
	};
})();
