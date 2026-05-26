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
			".sp-ship-row{display:flex;align-items:center;gap:10px;padding:8px 12px;border:1px solid var(--border-color,#e2e8f0);border-radius:8px;background:var(--control-bg,#fff);transition:border-color .15s,box-shadow .15s,background .15s;}" +
			".sp-ship-row.has-qty{border-color:var(--primary,#5c6ac4);background:rgba(92,106,196,0.04);box-shadow:0 0 0 1px rgba(92,106,196,0.12);}" +
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
			".sp-ship-input .sp-ship-uom{font-size:11px;color:var(--text-muted,#64748b);min-width:24px;text-transform:lowercase;}" +
			".sp-ship-empty{padding:24px 12px;text-align:center;color:var(--text-muted,#64748b);font-size:12px;border:1px dashed var(--border-color,#e2e8f0);border-radius:8px;}" +
			".sp-ship-summary{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:10px 2px 0;border-top:1px solid var(--border-color,#e2e8f0);margin-top:10px;font-size:12px;color:var(--text-muted,#64748b);}" +
			".sp-ship-summary .sp-ship-summary-count{font-weight:600;color:var(--text-color,#0f172a);}" +
			"</style>"
		);
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
				const rate = c.rate != null ? c.rate : c.unit_rate != null ? c.unit_rate : c.per_unit_rate;
				const cur = c.currency || c.selling_currency || "";
				const label = (c.item_code || "") + (c.item_name ? " — " + c.item_name : "");
				return (
					"<tr><td>" +
					esc(c.service_type || "") +
					"</td><td>" +
					esc(String(label)) +
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
			[__("Sales Quote"), esc(sc.sales_quote || "—")],
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

	function _loadCardPreview($pv, frm, choiceEnc, onLoaded) {
		const dec = _decodeChoice(choiceEnc);
		$pv.html(_renderPreviewHtml(null));
		frappe.call({
			method: "logistics.special_projects.special_project_booking_creation.get_special_project_booking_preview",
			args: {
				special_project: frm.doc.name,
				job_type: dec.job_type != null ? dec.job_type : "",
				lifecycle_job_idx: dec.detail_idx,
				lifecycle_jobs: _lifecycleJobsPayload(frm),
			},
			callback: function (r) {
				if (r.exc) {
					$pv.html(
						_styles() +
							"<div class='" + PREVIEW_CLASS + "'><div class='sp-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
							__("Preview could not be loaded.") + "</div></div>"
					);
				} else {
					$pv.html(_renderPreviewHtml(r.message || {}));
				}
				if (onLoaded) onLoaded();
			},
			error: function () {
				$pv.html(
					_styles() +
						"<div class='" + PREVIEW_CLASS + "'><div class='sp-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
						__("Preview could not be loaded.") + "</div></div>"
				);
				if (onLoaded) onLoaded();
			},
		});
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
				.text(__("Scroll the list of Lifecycle Jobs lines below. Expand a card for details; use Create in the card header when ready."))
		);
		const $scroll = $("<div class='sp-cards-scroll'>");
		const $cards = $("<div class='sp-cards'>");
		choices.forEach(function (c) {
			const enc = _encodeChoice(c);
			const creatable = c.creatable !== false;
			const $card = $("<div class='sp-card'>").attr("data-choice", enc);
			if (c.suggested_order_title) {
				$card.attr("data-suggested-order-title", c.suggested_order_title);
			}
			const $hd = $("<div class='sp-card-hd'>");
			const $toggle = $("<div class='sp-card-toggle' role='button' tabindex='0'>");
			$toggle.append($("<span class='sp-card-chevron'>").text("\u25B8"));
			$toggle.append(_buildHead(c));
			$hd.append($toggle);
			if (creatable) {
				$hd.append($("<button type='button'>").addClass("btn btn-primary btn-sm sp-card-create").text(__("Create")));
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

	function _routeAfterCreate(msg) {
		if (msg.air_booking) {
			frappe.set_route("Form", "Air Booking", msg.air_booking);
		} else if (msg.sea_booking) {
			frappe.set_route("Form", "Sea Booking", msg.sea_booking);
		} else if (msg.transport_order) {
			frappe.set_route("Form", "Transport Order", msg.transport_order);
		} else if (msg.declaration_order) {
			frappe.set_route("Form", "Declaration Order", msg.declaration_order);
		} else if (msg.inbound_order) {
			frappe.set_route("Form", "Inbound Order", msg.inbound_order);
		} else if (msg.project_order) {
			frappe.set_route("Form", "Project Order", msg.project_order);
		}
	}

	const _PACKAGE_JOB_TYPES = ["Transport Order", "Air Booking", "Sea Booking", "Inbound Order"];

	function _shipRowTitle(row) {
		return (
			row.warehouse_item_name ||
			row.warehouse_item ||
			row.commodity ||
			row.description ||
			__("Line") + " " + row.site_material_row
		);
	}

	function _shipRowIconText(row) {
		const t = _shipRowTitle(row).toString().trim();
		const m = t.match(/[A-Za-z0-9]/);
		return m ? m[0].toUpperCase() : "?";
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
			const $row = $("<div class='sp-ship-row'>").attr("data-row", row.site_material_row);
			const title = _shipRowTitle(row);
			$row.attr("data-search", title.toString().toLowerCase());

			const iconText = _shipRowIconText(row);
			const $mono = $("<span class='sp-ship-mono'>").text(iconText);
			if (iconText.length > 1) $mono.addClass("compact");
			$row.append($mono);

			const $main = $("<div class='sp-ship-main'>");
			$main.append($("<div class='sp-ship-title'>").text(title));
			const $chips = $("<div class='sp-ship-chips'>");
			$chips.append(
				$("<span class='sp-ship-chip short'>")
					.append($("<span class='sp-ship-chip-k'>").text(__("Short")))
					.append($("<span class='sp-ship-chip-v'>").text(_fmtQty(row.qty_short || 0)))
			);
			$chips.append(
				$("<span class='sp-ship-chip'>")
					.append($("<span class='sp-ship-chip-k'>").text(__("Required")))
					.append($("<span class='sp-ship-chip-v'>").text(_fmtQty(row.qty_required || 0)))
			);
			$chips.append(
				$("<span class='sp-ship-chip'>")
					.append($("<span class='sp-ship-chip-k'>").text(__("On site")))
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

			const $inputWrap = $("<div class='sp-ship-input'>");
			const $input = $("<input type='number' min='0' step='any' inputmode='decimal' placeholder='0'>")
				.attr("aria-label", __("Qty for {0}", [title]))
				.attr("data-short", row.qty_short || 0);
			$inputWrap.append($input);
			if (row.uom) {
				$inputWrap.append($("<span class='sp-ship-uom'>").text(String(row.uom)));
			}
			$row.append($inputWrap);
			$list.append($row);
		});
		return $list;
	}

	function _updateShipSummary($wrap) {
		const $rows = $wrap.find(".sp-ship-row");
		let withQty = 0;
		let total = 0;
		$rows.each(function () {
			const v = parseFloat($(this).find("input").val()) || 0;
			if (v > 0) {
				withQty += 1;
				total += v;
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
	}

	function _bindShipmentDialog($wrap, rows, onContinue) {
		$wrap.on("input", ".sp-ship-row input", function () {
			const $input = $(this);
			const v = parseFloat($input.val()) || 0;
			const $row = $input.closest(".sp-ship-row");
			$row.toggleClass("has-qty", v > 0);
			$input.toggleClass("has-value", v > 0);
			_updateShipSummary($wrap);
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
			$wrap.find(".sp-ship-row input").val("").removeClass("has-value");
			$wrap.find(".sp-ship-row").removeClass("has-qty");
			_updateShipSummary($wrap);
		});

		$wrap.on("click", ".sp-ship-quick-fill", function () {
			$wrap.find(".sp-ship-row").each(function () {
				const $r = $(this);
				if ($r.hasClass("hidden")) return;
				const $input = $r.find("input");
				const short = parseFloat($input.attr("data-short")) || 0;
				if (short > 0) {
					$input.val(short).addClass("has-value");
					$r.addClass("has-qty");
				}
			});
			_updateShipSummary($wrap);
		});

		_updateShipSummary($wrap);
	}

	function _collectShipmentLines($wrap, rows) {
		const byIdx = {};
		rows.forEach(function (r) { byIdx[r.site_material_row] = r; });
		const lines = [];
		$wrap.find(".sp-ship-row").each(function () {
			const $r = $(this);
			const idx = $r.attr("data-row");
			const qty = parseFloat($r.find("input").val()) || 0;
			if (qty > 0 && byIdx[idx]) {
				const row = byIdx[idx];
				lines.push({
					site_material_row: row.site_material_row,
					warehouse_item: row.warehouse_item,
					commodity: row.commodity,
					description: row.description,
					uom: row.uom,
					qty: qty,
				});
			}
		});
		return lines;
	}

	function _promptShipmentLines(frm, dec, callback) {
		frappe.call({
			method: "logistics.special_projects.special_project_site_materials.get_site_materials_for_shipment_picker",
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
						const lines = _collectShipmentLines($wrap, rows);
						d.hide();
						callback(lines.length ? JSON.stringify(lines) : null);
					},
					secondary_action_label: __("Skip"),
					secondary_action: function () {
						d.hide();
						callback(null);
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
								"Pick the quantities to include in this shipment. Filter by name, fill all to short qty, or set quantities individually. Rows left at 0 are skipped."
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
				$quick.append($("<button type='button' class='sp-ship-quick-fill'>").text(__("Fill all to short")));
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
					$("<span>").text(__("Leave at 0 to skip a line."))
				);
				$wrap.append($summary);

				$host.append($wrap);
				_bindShipmentDialog($wrap, rows, null);
				d.show();
				setTimeout(function () {
					$host.find(".sp-ship-search input").trigger("focus");
				}, 80);
			},
		});
	}

	function _callCreate(frm, dec, orderTitle, onDialogHide, shipmentLines) {
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
				_routeAfterCreate(r.message);
			},
		});
	}

	function _runCreate(frm, dec, $card, onDialogHide) {
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
					_callCreate(frm, dec, values.order_title, onDialogHide, null);
				},
				__("Create Project Order"),
				__("Create")
			);
			return;
		}
		if (_PACKAGE_JOB_TYPES.indexOf(dec.job_type) >= 0) {
			_promptShipmentLines(frm, dec, function (shipmentLines) {
				_callCreate(frm, dec, null, onDialogHide, shipmentLines);
			});
			return;
		}
		_callCreate(frm, dec, null, onDialogHide, null);
	}

	function _bindCards($root, frm, d) {
		$root.on("click", ".sp-card-toggle", function () {
			const $card = $(this).closest(".sp-card");
			$card.toggleClass("open");
			if ($card.hasClass("open")) {
				const $pv = $card.find(".sp-card-preview");
				if ($pv.data("sp-loaded")) return;
				const enc = $card.attr("data-choice");
				_loadCardPreview($pv, frm, enc, function () {
					$pv.data("sp-loaded", true);
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
					message: __("This line cannot be created automatically from here."),
					indicator: "orange",
				});
				return;
			}
			_runCreate(frm, dec, $card, function () {
				d.hide();
			});
		});
	}

	function _introHtml(frm) {
		const esc = frappe.utils.escape_html;
		const ref = esc(__("Special Project") + " · " + (frm.doc.name || ""));
		return (
			"<div class='" + PREVIEW_CLASS + "' style='margin-bottom:4px'>" +
			"<div style='font-size:12px;color:var(--text-muted,#64748b);line-height:1.5'>" +
			"<strong style='color:var(--text-color,#0f172a)'>" + __("From") + "</strong> " + ref + "<br>" +
			__("Each card is one Lifecycle Jobs line. Expand to preview; use Create in the card header when ready.") +
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
					$cardsRoot.append(_buildCards(choices));
					_bindCards($cardsRoot, frm, d);
				}
				d.show();
			},
		});
	};
})();
