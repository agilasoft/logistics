// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

(function () {
	"use strict";

	var IJ_PREVIEW_CLASS = "logistics-ij-preview";

	function _internalJobDetailsPayload(frm) {
		return JSON.stringify((frm && frm.doc && frm.doc.internal_job_details) || []);
	}

	function _encodeInternalJobChoice(c) {
		var cr = c.creatable === false ? "0" : "1";
		if (c.mode === "detail") {
			return "d|" + String(c.detail_idx) + "|" + String(c.job_type || "") + "|" + cr;
		}
		return "g||" + String(c.job_type || "") + "|" + cr;
	}

	function _decodeInternalJobChoice(s) {
		var parts = String(s || "").split("|");
		if (parts[0] === "d" && parts.length >= 3) {
			var idx = parseInt(parts[1], 10);
			var last = parts[parts.length - 1];
			var creatable = true;
			var end = parts.length;
			if (last === "0" || last === "1") {
				creatable = last === "1";
				end = parts.length - 1;
			}
			return {
				detail_idx: isNaN(idx) ? null : idx,
				job_type: parts.slice(2, end).join("|"),
				creatable: creatable,
			};
		}
		if (parts[0] === "g" && parts.length >= 2) {
			var lastg = parts[parts.length - 1];
			var crg = true;
			var endg = parts.length;
			if (lastg === "0" || lastg === "1") {
				crg = lastg === "1";
				endg = parts.length - 1;
			}
			return {
				detail_idx: null,
				job_type: parts.slice(2, endg).join("|"),
				creatable: crg,
			};
		}
		return { detail_idx: null, job_type: "", creatable: true };
	}

	function _ijStyles() {
		return (
			"<style>" +
			"." +
			IJ_PREVIEW_CLASS +
			"{" +
			"--ij-border:var(--border-color,#e2e8f0);" +
			"--ij-surface:var(--control-bg,#fff);" +
			"--ij-muted:var(--text-muted,#64748b);" +
			"--ij-text:var(--text-color,#0f172a);" +
			"--ij-accent:var(--primary,#5c6ac4);" +
			"--ij-radius:10px;" +
			"font-size:13px;line-height:1.5;color:var(--ij-text);" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-badge{" +
			"display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;" +
			"font-size:11px;font-weight:600;letter-spacing:0.02em;" +
			"background:rgba(92,106,196,0.12);color:var(--ij-accent);" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-badge-muted{background:var(--fill-color,#f1f5f9);color:var(--ij-muted)}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-section{" +
			"border:1px solid var(--ij-border);border-radius:var(--ij-radius);" +
			"background:var(--ij-surface);margin-bottom:12px;overflow:hidden;" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-section-hd{" +
			"padding:10px 14px;border-bottom:1px solid var(--ij-border);" +
			"display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;" +
			"background:var(--fg-color,#f8fafc);" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-section-title{" +
			"font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;" +
			"color:var(--ij-muted);margin:0" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-section-bd{padding:12px 14px}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-dl{" +
			"display:grid;grid-template-columns:minmax(110px,36%) 1fr;gap:8px 16px;margin:0;font-size:12px" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-dl dt{margin:0;color:var(--ij-muted);font-weight:500}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-dl dd{margin:0;word-break:break-word}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-kvgrid{" +
			"display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-kv{" +
			"padding:8px 10px;border-radius:8px;border:1px solid var(--ij-border);" +
			"background:var(--fg-color,#f8fafc);font-size:11px" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-kv-k{display:block;color:var(--ij-muted);font-weight:600;text-transform:capitalize;margin-bottom:2px}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-kv-v{display:block;font-weight:500;word-break:break-word}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-empty{" +
			"padding:16px;text-align:center;font-size:12px;color:var(--ij-muted);" +
			"border:1px dashed var(--ij-border);border-radius:8px;background:transparent" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-scroll{max-height:240px;overflow:auto;border-radius:8px;border:1px solid var(--ij-border)}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-table{width:100%;border-collapse:collapse;font-size:12px;margin:0}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-table th{" +
			"position:sticky;top:0;z-index:1;text-align:left;padding:8px 10px;" +
			"font-size:10px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;" +
			"color:var(--ij-muted);background:var(--fg-color,#f1f5f9);border-bottom:1px solid var(--ij-border)" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-table td{padding:8px 10px;border-bottom:1px solid var(--ij-border);vertical-align:top}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-table tr:last-child td{border-bottom:none}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-table tbody tr:nth-child(even) td{background:rgba(0,0,0,0.02)}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-mini-table{font-size:10px;width:100%;border-collapse:collapse;margin:4px 0 0}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-mini-table td{padding:3px 6px;border:1px solid var(--ij-border)}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-loading{display:flex;align-items:center;gap:10px;padding:20px;color:var(--ij-muted);font-size:13px}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-spin{" +
			"width:18px;height:18px;border:2px solid var(--ij-border);" +
			"border-top-color:var(--ij-accent);border-radius:50%;animation:ijspin 0.7s linear infinite" +
			"}" +
			"@keyframes ijspin{to{transform:rotate(360deg)}}" +
			".lij-cards-wrap{font-size:13px;color:var(--text-color,#0f172a);}" +
			".lij-cards-scroll{max-height:min(58vh,520px);overflow-y:auto;overflow-x:hidden;min-height:0;padding:2px 2px 6px 0;-webkit-overflow-scrolling:touch;}" +
			".lij-cards{display:flex;flex-direction:column;gap:10px;}" +
			".lij-card{border:1px solid var(--border-color,#e2e8f0);border-radius:10px;overflow:hidden;background:var(--control-bg,#fff);}" +
			".lij-card.open{border-color:var(--primary,#5c6ac4);box-shadow:0 0 0 1px rgba(92,106,196,0.12);}" +
			".lij-card-hd{display:flex;align-items:center;gap:10px;padding:10px 12px;font-weight:600;font-size:13px;flex-wrap:wrap;}" +
			".lij-card-toggle{cursor:pointer;display:flex;align-items:flex-start;gap:10px;flex:1;min-width:0;user-select:none;border-radius:6px;margin:-4px;padding:4px 6px 4px 4px;}" +
			".lij-card-toggle .lij-card-chevron{align-self:center;margin-top:8px;}" +
			".lij-card-head-block{display:flex;align-items:flex-start;gap:12px;min-width:0;flex:1;}" +
			".lij-card-mono-icon{flex-shrink:0;width:36px;height:36px;border-radius:8px;background:#1a1a1a;color:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;line-height:1;}" +
			".lij-card-mono-icon.lij-card-mono-icon--compact{font-size:11px;letter-spacing:-0.02em;}" +
			".lij-card-head-text{min-width:0;flex:1;}" +
			".lij-card-head-title{font-weight:600;font-size:14px;color:var(--text-color,#0f172a);line-height:1.3;margin:0 0 6px;}" +
			".lij-card-head-row2{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;line-height:1.45;}" +
			".lij-card-pill{display:inline-flex;align-items:center;padding:2px 10px;border-radius:999px;background:rgba(92,106,196,0.14);color:var(--primary,#5c6ac4);font-size:11px;font-weight:600;white-space:nowrap;max-width:100%;}" +
			".lij-card-sub{color:var(--text-muted,#64748b);font-weight:400;min-width:0;word-break:break-word;}" +
			".lij-card-toggle:hover{background:var(--fg-color,#f8fafc);}" +
			".lij-card-toggle:focus{outline:2px solid var(--primary);outline-offset:2px;}" +
			".lij-card-chevron{flex-shrink:0;width:22px;height:22px;display:flex;align-items:center;justify-content:center;color:var(--text-muted,#64748b);transition:transform .18s ease;font-size:11px;}" +
			".lij-card.open .lij-card-chevron{transform:rotate(90deg);}" +
			".lij-card-hd .lij-card-create{flex-shrink:0;margin-left:auto;cursor:pointer;}" +
			".lij-card-bd{display:none;border-top:1px solid var(--border-color,#e2e8f0);padding:12px 14px;background:var(--modal-bg,#fafafa);max-height:min(45vh,380px);overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;}" +
			".lij-card.open .lij-card-bd{display:block;}" +
			".lij-card-preview{min-height:8px;}" +
			".lij-chip-na{font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;background:var(--fill-color,#fef3c7);color:#b45309;flex-shrink:0;margin-left:auto;}" +
			"</style>"
		);
	}

	function _formatParamsHtml(params) {
		if (!params || typeof params !== "object") {
			return "";
		}
		var keys = Object.keys(params).filter(function (k) {
			return k !== "charge_group";
		});
		if (!keys.length) {
			return "<div class='ij-empty'>" + __("No parameters on this selection.") + "</div>";
		}
		var esc = frappe.utils.escape_html;
		var cells = keys
			.map(function (k) {
				return (
					"<div class='ij-kv'><span class='ij-kv-k'>" +
					esc(k.replace(/_/g, " ")) +
					"</span><span class='ij-kv-v'>" +
					esc(String(params[k])) +
					"</span></div>"
				);
			})
			.join("");
		return "<div class='ij-kvgrid'>" + cells + "</div>";
	}

	function _formatParamsMiniTable(params) {
		if (!params || typeof params !== "object") {
			return "—";
		}
		var keys = Object.keys(params).filter(function (k) {
			return k !== "charge_group";
		});
		if (!keys.length) {
			return "—";
		}
		var esc = frappe.utils.escape_html;
		var rows = keys
			.map(function (k) {
				return (
					"<tr><td class='text-muted'>" +
					esc(k) +
					"</td><td>" +
					esc(String(params[k])) +
					"</td></tr>"
				);
			})
			.join("");
		return "<table class='ij-mini-table'><tbody>" + rows + "</tbody></table>";
	}

	function _formatChargesPreviewHtml(charges) {
		if (!charges || !charges.length) {
			return "<div class='ij-empty'>" + __("No charge lines match this job type on the source document.") + "</div>";
		}
		var esc = frappe.utils.escape_html;
		var rows = charges
			.map(function (c) {
				var rate = c.rate != null ? c.rate : c.unit_rate != null ? c.unit_rate : c.per_unit_rate;
				var cur = c.currency || c.selling_currency || "";
				var label = (c.item_code || "") + (c.item_name ? " — " + c.item_name : "");
				return (
					"<tr><td>" +
					esc(c.service_type || "") +
					"</td><td>" +
					esc(String(label)) +
					"</td><td style='white-space:nowrap'>" +
					esc(rate != null ? String(rate) : "—") +
					"</td><td>" +
					esc(String(cur)) +
					"</td><td>" +
					_formatParamsMiniTable(c.parameters) +
					"</td></tr>"
				);
			})
			.join("");
		return (
			"<div class='ij-scroll'><table class='ij-table'><thead><tr>" +
			"<th>" +
			__("Service") +
			"</th><th>" +
			__("Item") +
			"</th><th>" +
			__("Rate") +
			"</th><th>" +
			__("Curr.") +
			"</th><th>" +
			__("Routing") +
			"</th></tr></thead><tbody>" +
			rows +
			"</tbody></table></div>"
		);
	}

	function _renderInternalJobPreviewHtml(p) {
		if (!p) {
			return (
				_ijStyles() +
				"<div class='" +
				IJ_PREVIEW_CLASS +
				"'><div class='ij-loading'><span class='ij-spin'></span>" +
				__("Loading preview…") +
				"</div></div>"
			);
		}
		var esc = frappe.utils.escape_html;
		var sc = p.source_context || {};

		var uncreatableBanner = "";
		if (p.not_creatable_message) {
			uncreatableBanner =
				"<div class='ij-section' style='margin-bottom:12px;border-color:var(--orange-500,#ed6c02)'>" +
				"<div class='ij-section-bd' style='font-size:12px;line-height:1.45'>" +
				esc(String(p.not_creatable_message)) +
				"</div></div>";
		}

		var ctxRows = [
			["dt", __("Source"), esc((sc.source_doctype || "") + " · " + (sc.source_name || ""))],
			["dt", __("Customer"), esc(sc.customer || "—")],
			["dt", __("Company"), esc(sc.company || "—")],
			["dt", __("Sales Quote"), esc(sc.sales_quote || "—")],
			["dt", __("Source is internal job"), sc.source_is_internal_job ? __("Yes") : __("No")],
		];
		if (sc.source_main_job_type || sc.source_main_job) {
			ctxRows.push([
				"dt",
				__("Source main job"),
				esc(String((sc.source_main_job_type || "") + " " + (sc.source_main_job || "")).trim() || "—"),
			]);
		}
		var ti = p.target_internal_job;
		if (ti && ti.is_internal_job) {
			ctxRows.push([
				"dt",
				__("New document"),
				__("Internal job → {0}", [esc(String((ti.main_job_type || "") + " " + (ti.main_job || "")).trim())]),
			]);
		}
		var ctxDl =
			"<dl class='ij-dl'>" +
			ctxRows
				.map(function (r) {
					return "<dt>" + r[1] + "</dt><dd>" + r[2] + "</dd>";
				})
				.join("") +
			"</dl>";

		var secContext =
			"<section class='ij-section'><header class='ij-section-hd'>" +
			"<h3 class='ij-section-title'>" +
			__("Source & links") +
			"</h3></header><div class='ij-section-bd'>" +
			ctxDl +
			"</div></section>";

		var secParams =
			"<section class='ij-section'><header class='ij-section-hd'>" +
			"<h3 class='ij-section-title'>" +
			__("Header parameters") +
			"</h3>" +
			"<span class='ij-badge ij-badge-muted' style='font-size:10px'>" +
			__("Applied on create") +
			"</span></header><div class='ij-section-bd'>" +
			_formatParamsHtml(p.job_detail_parameters) +
			"</div></section>";

		var secCharges =
			"<section class='ij-section'><header class='ij-section-hd'>" +
			"<h3 class='ij-section-title'>" +
			__("Charges to copy") +
			"</h3>" +
			"<span class='ij-badge ij-badge-muted' style='font-size:10px'>" +
			String((p.charges && p.charges.length) || 0) +
			" " +
			__("rows") +
			"</span></header><div class='ij-section-bd'>" +
			_formatChargesPreviewHtml(p.charges) +
			"</div></section>";

		return (
			_ijStyles() +
			"<div class='" +
			IJ_PREVIEW_CLASS +
			"'>" +
			uncreatableBanner +
			secContext +
			secParams +
			secCharges +
			"</div>"
		);
	}

	function _routeAfterInternalJobCreate(frm, jobType, r) {
		var msg = r.message || {};
		if (msg.transport_order) {
			frappe.set_route("Form", "Transport Order", msg.transport_order);
			return;
		}
		if (msg.declaration_order) {
			frappe.set_route("Form", "Declaration Order", msg.declaration_order);
			if (frm && (frm.doctype === "Air Shipment" || frm.doctype === "Sea Shipment")) {
				frm.reload_doc();
			}
			return;
		}
		if (msg.air_booking) {
			frappe.set_route("Form", "Air Booking", msg.air_booking);
			return;
		}
		if (msg.sea_booking) {
			frappe.set_route("Form", "Sea Booking", msg.sea_booking);
			return;
		}
		if (msg.inbound_order) {
			frappe.show_alert(
				{
					message: msg.message || __("Inbound Order {0} created.", [msg.inbound_order]),
					indicator: "green",
				},
				5
			);
			frappe.set_route("Form", "Inbound Order", msg.inbound_order);
			return;
		}
		frappe.msgprint({
			title: __("Create Internal Job"),
			message: __("Unexpected response while creating {0}.", [jobType]),
			indicator: "orange",
		});
	}

	function _dialogIntroHtml(frm) {
		var esc = frappe.utils.escape_html;
		var ref = esc((frm.doctype || "") + " · " + (frm.doc.name || ""));
		return (
			"<div class='" +
			IJ_PREVIEW_CLASS +
			"' style='margin-bottom:4px'>" +
			"<div style='font-size:12px;color:var(--text-muted,#64748b);line-height:1.5'>" +
			"<strong style='color:var(--text-color,#0f172a)'>" +
			__("From") +
			"</strong> " +
			ref +
			"<br>" +
			__(
				"Scroll the list below. Expand a card for details; Create is in each card header."
			) +
			"</div></div>"
		);
	}

	function _loadCardPreview($pv, frm, choiceEnc, onLoaded) {
		var dec = _decodeInternalJobChoice(choiceEnc);
		if (!dec.job_type && dec.detail_idx == null) {
			$pv.html(
				_ijStyles() +
					"<div class='" +
					IJ_PREVIEW_CLASS +
					"'><div class='ij-empty'>" +
					__("Nothing to preview for this option.") +
					"</div></div>"
			);
			if (onLoaded) {
				onLoaded();
			}
			return;
		}
		$pv.html(_renderInternalJobPreviewHtml(null));
		frappe.call({
			method: "logistics.utils.internal_job_from_source.get_internal_job_creation_preview",
			args: {
				source_doctype: frm.doctype,
				source_name: frm.doc.name,
				job_type: dec.job_type != null && dec.job_type !== undefined ? dec.job_type : "",
				internal_job_detail_idx: dec.detail_idx,
				internal_job_details: _internalJobDetailsPayload(frm),
			},
			callback: function (r) {
				if (r.exc) {
					$pv.html(
						_ijStyles() +
							"<div class='" +
							IJ_PREVIEW_CLASS +
							"'><div class='ij-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
							__("Preview could not be loaded.") +
							"</div></div>"
					);
				} else {
					$pv.html(_renderInternalJobPreviewHtml(r.message || {}));
				}
				if (onLoaded) {
					onLoaded();
				}
			},
			error: function () {
				$pv.html(
					_ijStyles() +
						"<div class='" +
						IJ_PREVIEW_CLASS +
						"'><div class='ij-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
						__("Preview could not be loaded.") +
						"</div></div>"
				);
				if (onLoaded) {
					onLoaded();
				}
			},
		});
	}

	function _choiceHeaderLetter(c) {
		var st = ((c && c.service_type) || "").toString().trim();
		if (st) {
			var m0 = st.match(/[A-Za-z0-9]/);
			return m0 ? m0[0].toUpperCase() : "?";
		}
		var s = ((c && c.job_type) || (c && c.header_title) || "").toString().trim();
		if (!s) {
			return "?";
		}
		var m = s.match(/[A-Za-z0-9]/);
		return m ? m[0].toUpperCase() : "?";
	}

	function _choiceIconText(c) {
		if (c && c.detail_idx != null && c.detail_idx !== undefined && c.detail_idx !== "") {
			var n = Number(c.detail_idx);
			if (!isNaN(n) && n > 0) {
				return String(n);
			}
		}
		return _choiceHeaderLetter(c);
	}

	function _buildChoiceCardHead(c) {
		var title =
			(c.header_title != null && String(c.header_title).trim() !== "" && String(c.header_title)) ||
			(c.service_type != null && String(c.service_type).trim() !== "" && String(c.service_type)) ||
			String((c && c.job_type) || "") ||
			String((c && c.label) || "");
		var badge =
			(c.header_badge != null && String(c.header_badge).trim() !== "" && String(c.header_badge)) ||
			(c.job_no != null && String(c.job_no).trim() !== "" && String(c.job_no).trim()) ||
			(c.detail_idx != null ? __("Pending") : __("Job Details"));
		var sub =
			c.header_subtitle != null && String(c.header_subtitle).trim()
				? String(c.header_subtitle)
				: "";
		var $block = $("<div>").addClass("lij-card-head-block");
		var iconText = _choiceIconText(c);
		var $icon = $("<span>").addClass("lij-card-mono-icon").text(iconText);
		if (iconText.length > 1) {
			$icon.addClass("lij-card-mono-icon--compact");
		}
		$block.append($icon);
		var $text = $("<div>").addClass("lij-card-head-text");
		$text.append($("<div>").addClass("lij-card-head-title").text(title));
		var $row2 = $("<div>").addClass("lij-card-head-row2");
		$row2.append($("<span>").addClass("lij-card-pill").text(badge));
		if (sub) {
			$row2.append($("<span>").addClass("lij-card-sub").text(sub));
		}
		$text.append($row2);
		$block.append($text);
		return $block;
	}

	function _buildChoiceCards(choices) {
		var $wrap = $('<div class="lij-cards-wrap">');
		$wrap.append(
			$("<p>")
				.addClass("text-muted")
				.css({ fontSize: "12px", marginBottom: "10px", lineHeight: 1.45 })
				.text(
					__(
						"Scroll the list of options below. Expand a card for the preview; use Create in the card header when ready."
					)
				)
		);
		var $scroll = $('<div class="lij-cards-scroll">');
		var $cards = $('<div class="lij-cards">');
		choices.forEach(function (c) {
			var enc = _encodeInternalJobChoice(c);
			var creatable = c.creatable !== false;
			var $card = $('<div class="lij-card">').attr("data-choice", enc);
			var $hd = $('<div class="lij-card-hd">');
			var $toggle = $('<div class="lij-card-toggle" role="button" tabindex="0">');
			$toggle.append($('<span class="lij-card-chevron">').text("\u25B8"));
			$toggle.append(_buildChoiceCardHead(c));
			$hd.append($toggle);
			if (creatable) {
				$hd.append(
					$("<button type='button'>")
						.addClass("btn btn-primary btn-sm lij-card-create")
						.text(__("Create"))
				);
			} else {
				var linked = c.job_no != null && String(c.job_no).trim() !== "";
				$hd.append(
					$('<span class="lij-chip-na">').text(linked ? __("Linked") : __("Cannot create"))
				);
			}
			var $bd = $('<div class="lij-card-bd">');
			var $pv = $('<div class="lij-card-preview">');
			$bd.append($pv);
			$card.append($hd).append($bd);
			$cards.append($card);
		});
		$scroll.append($cards);
		$wrap.append($scroll);
		return $wrap;
	}

	function _bindChoiceCards($root, frm, d) {
		$root.on("click", ".lij-card-toggle", function () {
			var $card = $(this).closest(".lij-card");
			$card.toggleClass("open");
			if ($card.hasClass("open")) {
				var enc = $card.attr("data-choice");
				var $pv = $card.find(".lij-card-preview");
				if ($pv.data("ij-loaded")) {
					return;
				}
				_loadCardPreview($pv, frm, enc, function () {
					$pv.data("ij-loaded", true);
				});
			}
		});
		$root.on("keydown", ".lij-card-toggle", function (e) {
			if (e.which === 13 || e.which === 32) {
				e.preventDefault();
				$(this).trigger("click");
			}
		});
		$root.on("click", ".lij-card-create", function (e) {
			e.stopPropagation();
			var $card = $(this).closest(".lij-card");
			var enc = $card.attr("data-choice");
			var dec = _decodeInternalJobChoice(enc);
			if (!dec.job_type && dec.detail_idx == null) {
				frappe.msgprint({ message: __("Invalid selection."), indicator: "red" });
				return;
			}
			if (!dec.job_type) {
				frappe.msgprint({
					title: __("Create Internal Job"),
					message: __("Set Service Type on this Internal Jobs line before creating."),
					indicator: "orange",
				});
				return;
			}
			if (dec.creatable === false) {
				frappe.msgprint({
					title: __("Create Internal Job"),
					message: __(
						"This line cannot be created automatically from here. Pick a supported option or create the document separately."
					),
					indicator: "orange",
				});
				return;
			}
			d.hide();
			_maybeConfirmInboundThenCreate(frm, dec);
		});
	}

	function _runInternalJobCreate(frm, dec) {
		frappe.call({
			method: "logistics.utils.internal_job_from_source.create_internal_job_from_operational_source",
			args: {
				source_doctype: frm.doctype,
				source_name: frm.doc.name,
				job_type: dec.job_type,
				internal_job_detail_idx: dec.detail_idx,
				internal_job_details: _internalJobDetailsPayload(frm),
			},
			freeze: true,
			freeze_message: __("Creating..."),
			callback: function (r2) {
				if (r2.message && r2.message.already_exists && r2.message.declaration_order) {
					frappe.show_alert({ message: r2.message.message || "", indicator: "blue" }, 5);
					frappe.set_route("Form", "Declaration Order", r2.message.declaration_order);
					if (frm.doctype === "Air Shipment" || frm.doctype === "Sea Shipment") {
						frm.reload_doc();
					}
					return;
				}
				_routeAfterInternalJobCreate(frm, dec.job_type, r2);
			},
		});
	}

	function _maybeConfirmInboundThenCreate(frm, dec) {
		if (dec.creatable === false) {
			return;
		}
		if (dec.job_type !== "Inbound Order") {
			_runInternalJobCreate(frm, dec);
			return;
		}
		var go = function () {
			_runInternalJobCreate(frm, dec);
		};
		if (frm.doctype === "Transport Job") {
			var pkgs = frm.doc.packages || [];
			var needsDefault = !pkgs.length || pkgs.every(function (p) {
				return !p.warehouse_item;
			});
			if (needsDefault) {
				frappe.confirm(
					__(
						"No warehouse item on packages. The default item will be used where it is missing. Continue?"
					),
					go
				);
				return;
			}
		}
		if (frm.doctype === "Air Shipment" || frm.doctype === "Sea Shipment") {
			var wi = frm.doc.warehouse_items || [];
			if (wi.length === 0) {
				frappe.confirm(
					__(
						"No warehouse items on this shipment. The default warehouse item will be used. Continue?"
					),
					go
				);
				return;
			}
		}
		go();
	}

	window.logistics_show_create_internal_job_dialog = function (frm) {
		if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
			return;
		}
		frappe.call({
			method: "logistics.utils.internal_job_from_source.get_internal_job_creation_choices",
			args: {
				source_doctype: frm.doctype,
				source_name: frm.doc.name,
				internal_job_details: _internalJobDetailsPayload(frm),
			},
			freeze: true,
			freeze_message: __("Loading options..."),
			callback: function (r) {
				var choices = (r.message && r.message.choices) || [];
				if (!choices.length) {
					frappe.msgprint({
						title: __("Create Internal Job"),
						message: __("No internal jobs can be created from this document."),
						indicator: "orange",
					});
					return;
				}
				var d = new frappe.ui.Dialog({
					title: __("Create internal job"),
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
					d.fields_dict.info.$wrapper.html(_dialogIntroHtml(frm));
				}
				var $cardsRoot = d.fields_dict.cards_html && d.fields_dict.cards_html.$wrapper;
				if ($cardsRoot && $cardsRoot.length) {
					$cardsRoot.empty();
					$cardsRoot.append(_ijStyles());
					$cardsRoot.append(_buildChoiceCards(choices));
					_bindChoiceCards($cardsRoot, frm, d);
				}
				d.show();
			},
		});
	};
})();
