// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Create Booking/Order dialog for Docket: lists each Linked Service row, lets the user create
// the matching Air/Sea Booking, Transport/Declaration/Inbound Order from it.

(function () {
	"use strict";

	const PREVIEW_CLASS = "logistics-dk-ij-preview";

	function _linkedServicesPayload(frm) {
		var rows = (frm && frm.doc && (frm.doc.linked_services || frm.doc.internal_jobs)) || [];
		return JSON.stringify(rows);
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
			"." + PREVIEW_CLASS + " .dk-section{border:1px solid var(--border-color,#e2e8f0);border-radius:10px;background:var(--control-bg,#fff);margin-bottom:12px;overflow:hidden;}" +
			"." + PREVIEW_CLASS + " .dk-section-hd{padding:10px 14px;border-bottom:1px solid var(--border-color,#e2e8f0);background:var(--fg-color,#f8fafc);display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;}" +
			"." + PREVIEW_CLASS + " .dk-section-title{font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:var(--text-muted,#64748b);margin:0;}" +
			"." + PREVIEW_CLASS + " .dk-section-bd{padding:12px 14px;}" +
			"." + PREVIEW_CLASS + " .dk-dl{display:grid;grid-template-columns:minmax(110px,36%) 1fr;gap:8px 16px;margin:0;font-size:12px;}" +
			"." + PREVIEW_CLASS + " .dk-dl dt{margin:0;color:var(--text-muted,#64748b);font-weight:500;}" +
			"." + PREVIEW_CLASS + " .dk-dl dd{margin:0;word-break:break-word;}" +
			"." + PREVIEW_CLASS + " .dk-kvgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;}" +
			"." + PREVIEW_CLASS + " .dk-kv{padding:8px 10px;border-radius:8px;border:1px solid var(--border-color,#e2e8f0);background:var(--fg-color,#f8fafc);font-size:11px;}" +
			"." + PREVIEW_CLASS + " .dk-kv-k{display:block;color:var(--text-muted,#64748b);font-weight:600;text-transform:capitalize;margin-bottom:2px;}" +
			"." + PREVIEW_CLASS + " .dk-kv-v{display:block;font-weight:500;word-break:break-word;}" +
			"." + PREVIEW_CLASS + " .dk-empty{padding:16px;text-align:center;font-size:12px;color:var(--text-muted,#64748b);border:1px dashed var(--border-color,#e2e8f0);border-radius:8px;}" +
			"." + PREVIEW_CLASS + " .dk-scroll{max-height:240px;overflow:auto;border-radius:8px;border:1px solid var(--border-color,#e2e8f0);}" +
			"." + PREVIEW_CLASS + " .dk-table{width:100%;border-collapse:collapse;font-size:12px;}" +
			"." + PREVIEW_CLASS + " .dk-table th{position:sticky;top:0;z-index:1;text-align:left;padding:8px 10px;font-size:10px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:var(--text-muted,#64748b);background:var(--fg-color,#f1f5f9);border-bottom:1px solid var(--border-color,#e2e8f0);}" +
			"." + PREVIEW_CLASS + " .dk-table td{padding:8px 10px;border-bottom:1px solid var(--border-color,#e2e8f0);vertical-align:top;}" +
			"." + PREVIEW_CLASS + " .dk-table tr:last-child td{border-bottom:none;}" +
			"." + PREVIEW_CLASS + " .dk-loading{display:flex;align-items:center;gap:10px;padding:20px;color:var(--text-muted,#64748b);font-size:13px;}" +
			"." + PREVIEW_CLASS + " .dk-spin{width:18px;height:18px;border:2px solid var(--border-color,#e2e8f0);border-top-color:var(--primary,#5c6ac4);border-radius:50%;animation:dkspin 0.7s linear infinite;}" +
			"@keyframes dkspin{to{transform:rotate(360deg)}}" +
			".dk-cards-wrap{font-size:13px;color:var(--text-color,#0f172a);}" +
			".dk-cards-scroll{max-height:min(58vh,520px);overflow-y:auto;overflow-x:hidden;min-height:0;padding:2px 2px 6px 0;-webkit-overflow-scrolling:touch;}" +
			".dk-cards{display:flex;flex-direction:column;gap:10px;}" +
			".dk-card{border:1px solid var(--border-color,#e2e8f0);border-radius:10px;overflow:hidden;background:var(--control-bg,#fff);}" +
			".dk-card.open{border-color:var(--primary,#5c6ac4);box-shadow:0 0 0 1px rgba(92,106,196,0.12);}" +
			".dk-card-hd{display:flex;align-items:center;gap:10px;padding:10px 12px;font-weight:600;font-size:13px;flex-wrap:wrap;}" +
			".dk-card-toggle{cursor:pointer;display:flex;align-items:flex-start;gap:10px;flex:1;min-width:0;user-select:none;border-radius:6px;margin:-4px;padding:4px 6px 4px 4px;}" +
			".dk-card-toggle .dk-card-chevron{align-self:center;margin-top:8px;}" +
			".dk-card-head-block{display:flex;align-items:flex-start;gap:12px;min-width:0;flex:1;}" +
			".dk-card-mono-icon{flex-shrink:0;width:36px;height:36px;border-radius:8px;background:#1a1a1a;color:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;line-height:1;}" +
			".dk-card-mono-icon.dk-card-mono-icon--compact{font-size:11px;letter-spacing:-0.02em;}" +
			".dk-card-head-text{min-width:0;flex:1;}" +
			".dk-card-head-title{font-weight:600;font-size:14px;color:var(--text-color,#0f172a);line-height:1.3;margin:0 0 6px;}" +
			".dk-card-head-row2{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;line-height:1.45;}" +
			".dk-card-pill{display:inline-flex;align-items:center;padding:2px 10px;border-radius:999px;background:rgba(92,106,196,0.14);color:var(--primary,#5c6ac4);font-size:11px;font-weight:600;white-space:nowrap;max-width:100%;}" +
			".dk-card-sub{color:var(--text-muted,#64748b);font-weight:400;min-width:0;word-break:break-word;}" +
			".dk-card-toggle:hover{background:var(--fg-color,#f8fafc);}" +
			".dk-card-toggle:focus{outline:2px solid var(--primary);outline-offset:2px;}" +
			".dk-card-chevron{flex-shrink:0;width:22px;height:22px;display:flex;align-items:center;justify-content:center;color:var(--text-muted,#64748b);transition:transform .18s ease;font-size:11px;}" +
			".dk-card.open .dk-card-chevron{transform:rotate(90deg);}" +
			".dk-card-hd .dk-card-create{flex-shrink:0;margin-left:auto;cursor:pointer;}" +
			".dk-card-badges{display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center;margin-left:auto;flex-shrink:0;}" +
			".dk-chip-cancelled{font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;background:#fee2e2;color:#b91c1c;}" +
			".dk-card-bd{display:none;border-top:1px solid var(--border-color,#e2e8f0);padding:12px 14px;background:var(--modal-bg,#fafafa);max-height:min(45vh,380px);overflow-y:auto;overflow-x:hidden;}" +
			".dk-card.open .dk-card-bd{display:block;}" +
			".dk-chip-na{font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;background:var(--fill-color,#fef3c7);color:#b45309;flex-shrink:0;margin-left:auto;}" +
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
			return "<div class='dk-empty'>" + __("No parameters on this selection.") + "</div>";
		}
		const esc = frappe.utils.escape_html;
		const cells = keys
			.map(function (k) {
				return (
					"<div class='dk-kv'><span class='dk-kv-k'>" +
					esc(k.replace(/_/g, " ")) +
					"</span><span class='dk-kv-v'>" +
					esc(String(params[k])) +
					"</span></div>"
				);
			})
			.join("");
		return "<div class='dk-kvgrid'>" + cells + "</div>";
	}

	function _formatChargesHtml(charges) {
		if (!charges || !charges.length) {
			return "<div class='dk-empty'>" + __("No charge lines match this service on the docket.") + "</div>";
		}
		const esc = frappe.utils.escape_html;
		const rows = charges
			.map(function (c) {
				const rate = c.unit_rate != null ? c.unit_rate : c.per_unit_rate;
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
			"<div class='dk-scroll'><table class='dk-table'><thead><tr>" +
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
				"<div class='" + PREVIEW_CLASS + "'><div class='dk-loading'><span class='dk-spin'></span>" +
				__("Loading preview…") + "</div></div>"
			);
		}
		const esc = frappe.utils.escape_html;
		const sc = p.source_context || {};

		let uncreatable = "";
		if (p.not_creatable_message) {
			uncreatable =
				"<div class='dk-section' style='border-color:var(--orange-500,#ed6c02)'>" +
				"<div class='dk-section-bd' style='font-size:12px;line-height:1.45'>" +
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
			"<dl class='dk-dl'>" +
			ctxRows.map(function (r) { return "<dt>" + r[0] + "</dt><dd>" + r[1] + "</dd>"; }).join("") +
			"</dl>";

		const secContext =
			"<section class='dk-section'><header class='dk-section-hd'>" +
			"<h3 class='dk-section-title'>" + __("Source & links") + "</h3></header>" +
			"<div class='dk-section-bd'>" + ctxDl + "</div></section>";

		const secParams =
			"<section class='dk-section'><header class='dk-section-hd'>" +
			"<h3 class='dk-section-title'>" + __("Line parameters") + "</h3>" +
			"<span style='font-size:10px;color:var(--text-muted,#64748b)'>" + __("Applied on create") + "</span>" +
			"</header><div class='dk-section-bd'>" + _formatParamsHtml(p.job_detail_parameters) + "</div></section>";

		const charges = p.charges || [];
		const secCharges =
			"<section class='dk-section'><header class='dk-section-hd'>" +
			"<h3 class='dk-section-title'>" + __("Matching docket charges") + "</h3>" +
			"<span style='font-size:10px;color:var(--text-muted,#64748b)'>" + String(charges.length) + " " + __("rows") + "</span>" +
			"</header><div class='dk-section-bd'>" + _formatChargesHtml(charges) + "</div></section>";

		return (
			_styles() +
			"<div class='" + PREVIEW_CLASS + "'>" + uncreatable + secContext + secParams + secCharges + "</div>"
		);
	}

	function _loadCardPreview($pv, frm, choiceEnc, onLoaded) {
		const dec = _decodeChoice(choiceEnc);
		$pv.html(_renderPreviewHtml(null));
		frappe.call({
			method: "logistics.mice.doctype.docket.docket_booking_creation.get_docket_booking_preview",
			args: {
				docket: frm.doc.name,
				job_type: dec.job_type != null ? dec.job_type : "",
				internal_job_idx: dec.detail_idx,
				linked_services: _linkedServicesPayload(frm),
				internal_jobs: _linkedServicesPayload(frm),
			},
			callback: function (r) {
				if (r.exc) {
					$pv.html(
						_styles() +
							"<div class='" + PREVIEW_CLASS + "'><div class='dk-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
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
						"<div class='" + PREVIEW_CLASS + "'><div class='dk-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
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

		const $block = $("<div>").addClass("dk-card-head-block");
		const iconText = _iconText(c);
		const $icon = $("<span>").addClass("dk-card-mono-icon").text(iconText);
		if (iconText.length > 1) $icon.addClass("dk-card-mono-icon--compact");
		$block.append($icon);

		const $text = $("<div>").addClass("dk-card-head-text");
		$text.append($("<div>").addClass("dk-card-head-title").text(title));
		const $row2 = $("<div>").addClass("dk-card-head-row2");
		$row2.append($("<span>").addClass("dk-card-pill").text(badge));
		if (sub) $row2.append($("<span>").addClass("dk-card-sub").text(sub));
		$text.append($row2);
		$block.append($text);
		return $block;
	}

	function _buildCards(choices) {
		const $wrap = $("<div class='dk-cards-wrap'>");
		$wrap.append(
			$("<p>")
				.addClass("text-muted")
				.css({ fontSize: "12px", marginBottom: "10px", lineHeight: 1.45 })
				.text(__("Each card is one Services line on this Docket. Expand for details; use Create in the card header when ready."))
		);
		const $scroll = $("<div class='dk-cards-scroll'>");
		const $cards = $("<div class='dk-cards'>");
		choices.forEach(function (c) {
			const enc = _encodeChoice(c);
			const creatable = c.creatable !== false;
			const $card = $("<div class='dk-card'>").attr("data-choice", enc);
			const $hd = $("<div class='dk-card-hd'>");
			const $toggle = $("<div class='dk-card-toggle' role='button' tabindex='0'>");
			$toggle.append($("<span class='dk-card-chevron'>").text("\u25B8"));
			$toggle.append(_buildHead(c));
			$hd.append($toggle);
			if (creatable) {
				$hd.append($("<button type='button'>").addClass("btn btn-primary btn-sm dk-card-create").text(__("Create")));
			} else {
				const linked = c.job_no != null && String(c.job_no).trim() !== "";
				const $badges = $("<span class='dk-card-badges'>");
				if (c.linked_job_cancelled) $badges.append($("<span class='dk-chip-cancelled'>").text(__("Cancelled")));
				$badges.append($("<span class='dk-chip-na'>").text(linked ? __("Linked") : __("Cannot create")));
				$hd.append($badges);
			}
			const $bd = $("<div class='dk-card-bd'>");
			const $pv = $("<div class='dk-card-preview'>");
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
		} else if (msg.mice_order) {
			_go("MICE Order", msg.mice_order);
		}
	}

	function _callCreate(frm, dec, onDialogHide) {
		frappe.call({
			method: "logistics.mice.doctype.docket.docket_booking_creation.create_booking_or_order_from_docket",
			args: {
				docket: frm.doc.name,
				job_type: dec.job_type,
				internal_job_idx: dec.detail_idx,
				linked_services: _linkedServicesPayload(frm),
				internal_jobs: _linkedServicesPayload(frm),
			},
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

	function _bindCards($root, frm, d) {
		$root.on("click", ".dk-card-toggle", function () {
			const $card = $(this).closest(".dk-card");
			$card.toggleClass("open");
			if ($card.hasClass("open")) {
				const $pv = $card.find(".dk-card-preview");
				if ($pv.data("dk-loaded")) return;
				const enc = $card.attr("data-choice");
				_loadCardPreview($pv, frm, enc, function () {
					$pv.data("dk-loaded", true);
				});
			}
		});
		$root.on("keydown", ".dk-card-toggle", function (e) {
			if (e.which === 13 || e.which === 32) {
				e.preventDefault();
				$(this).trigger("click");
			}
		});
		$root.on("click", ".dk-card-create", function (e) {
			e.stopPropagation();
			const $card = $(this).closest(".dk-card");
			const enc = $card.attr("data-choice");
			const dec = _decodeChoice(enc);
			if (!dec.job_type) {
				frappe.msgprint({
					title: __("Create Booking / Order"),
					message: __("Set Service Type on this Services line before creating."),
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
			_callCreate(frm, dec, function () {
				d.hide();
			});
		});
	}

	function _introHtml(frm) {
		const esc = frappe.utils.escape_html;
		const ref = esc(__("Docket") + " · " + (frm.doc.name || ""));
		return (
			"<div class='" + PREVIEW_CLASS + "' style='margin-bottom:4px'>" +
			"<div style='font-size:12px;color:var(--text-muted,#64748b);line-height:1.5'>" +
			"<strong style='color:var(--text-color,#0f172a)'>" + __("From") + "</strong> " + ref + "<br>" +
			__("Each card is one Services line. Expand to preview; use Create in the card header when ready.") +
			"</div></div>"
		);
	}

	window.logistics_show_docket_booking_dialog = function (frm) {
		if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
			frappe.msgprint({
				title: __("Save Required"),
				message: __("Save the Docket before creating bookings or orders."),
				indicator: "orange",
			});
			return;
		}
		frappe.call({
			method: "logistics.mice.doctype.docket.docket_booking_creation.get_docket_booking_choices",
			args: {
				docket: frm.doc.name,
				linked_services: _linkedServicesPayload(frm),
				internal_jobs: _linkedServicesPayload(frm),
			},
			freeze: true,
			freeze_message: __("Loading options..."),
			callback: function (r) {
				const msg = r.message || {};
				const choices = msg.choices || [];
				if (!choices.length) {
					frappe.msgprint({
						title: __("Create Booking / Order"),
						message: __("No Services lines on this Docket. Link a Sales Quote with subsidiary services first."),
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
