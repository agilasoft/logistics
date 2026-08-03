// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

// Create Booking/Order dialog for Sales Quote: creates from Main Service scope (not per Services line).

(function () {
	"use strict";

	const PREVIEW_CLASS = "logistics-sq-ls-preview";
	const SQ_BOOKING_DIALOG_VERSION = "3";
	const MAIN_SERVICE_JOB_TYPE = {
		Air: "Air Booking",
		Sea: "Sea Booking",
		Transport: "Transport Order",
		Customs: "Declaration Order",
		Custom: "Declaration Order",
		Warehousing: "Inbound Order",
		"Time Sensitive": "Time Sensitive Case",
	};
	const SQ_SCOPE_FIELDS = [
		"transport_mode",
		"load_type",
		"direction",
		"origin_port",
		"destination_port",
		"transport_template",
		"vehicle_type",
		"container_type",
		"container_no",
		"location_type",
		"location_from",
		"location_to",
		"pick_mode",
		"drop_mode",
		"air_house_type",
		"airline",
		"freight_agent",
		"sea_house_type",
		"freight_agent_sea",
		"shipping_line",
		"customs_authority",
		"declaration_type",
		"customs_broker",
		"customs_charge_category",
	];

	function _mainServiceJobType(mainService) {
		const ms = (mainService || "").toString().trim();
		return MAIN_SERVICE_JOB_TYPE[ms] || "";
	}

	function _quoteContextPayload(frm) {
		const doc = frm && frm.doc;
		if (!doc) return "";
		const ctx = { main_service: doc.main_service || "" };
		SQ_SCOPE_FIELDS.forEach(function (fn) {
			const val = doc[fn];
			if (val != null && String(val).trim() !== "") {
				ctx[fn] = val;
			}
		});
		return JSON.stringify(ctx);
	}

	function _normalizeMainServiceChoices(frm, apiChoices) {
		const ms = ((frm && frm.doc && frm.doc.main_service) || "").toString().trim();
		const jt = _mainServiceJobType(ms);
		if (!ms || !jt) {
			return apiChoices || [];
		}
		const api = (apiChoices && apiChoices[0]) || {};
		return [
			{
				mode: "main",
				detail_idx: null,
				job_type: jt,
				service_type: ms,
				creatable: api.creatable !== false,
				header_title: ms,
				header_badge: __("Main Service"),
				header_subtitle: __("Creates {0} from Main Service scope. Regular quotes stay reusable — Services lines are not updated with Job No.", [
					__(jt),
				]),
				not_creatable_message: api.not_creatable_message,
			},
		];
	}

	function _linkedServicesPayload(frm) {
		return JSON.stringify((frm && frm.doc && frm.doc.linked_services) || []);
	}

	function _encodeChoice(c) {
		const cr = c.creatable === false ? "0" : "1";
		return "m|" + String((c && c.job_type) || "") + "|" + cr;
	}

	function _decodeChoice(s) {
		const parts = String(s || "").split("|");
		const last = parts[parts.length - 1];
		let creatable = true;
		let end = parts.length;
		if (last === "0" || last === "1") {
			creatable = last === "1";
			end = parts.length - 1;
		}
		if (parts[0] === "m" && parts.length >= 2) {
			return {
				mode: "main",
				use_main_service: true,
				detail_idx: null,
				job_type: parts.slice(1, end).join("|"),
				creatable: creatable,
			};
		}
		if (parts[0] !== "d" || parts.length < 3) {
			return {
				mode: "detail",
				use_main_service: false,
				detail_idx: null,
				job_type: "",
				creatable: true,
			};
		}
		const idxStr = parts[1];
		const idx = idxStr ? parseInt(idxStr, 10) : null;
		return {
			mode: "detail",
			use_main_service: false,
			detail_idx: idx && !isNaN(idx) ? idx : null,
			job_type: parts.slice(2, end).join("|"),
			creatable: creatable,
		};
	}

	function _mainServiceApiArgs(frm, jobType) {
		const ms = ((frm && frm.doc && frm.doc.main_service) || "").toString().trim();
		const jt = _mainServiceJobType(ms) || (jobType != null ? jobType : "");
		return {
			sales_quote: frm.doc.name,
			job_type: jt,
			detail_idx: null,
			linked_services: _linkedServicesPayload(frm),
			use_main_service: 1,
			quote_context: _quoteContextPayload(frm),
		};
	}

	function _styles() {
		return (
			"<style>" +
			"." + PREVIEW_CLASS + "{font-size:13px;line-height:1.5;color:var(--text-color,#0f172a);}" +
			"." + PREVIEW_CLASS + " .sq-section{border:1px solid var(--border-color,#e2e8f0);border-radius:10px;background:var(--control-bg,#fff);margin-bottom:12px;overflow:hidden;}" +
			"." + PREVIEW_CLASS + " .sq-section-hd{padding:10px 14px;border-bottom:1px solid var(--border-color,#e2e8f0);background:var(--fg-color,#f8fafc);display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;}" +
			"." + PREVIEW_CLASS + " .sq-section-title{font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:var(--text-muted,#64748b);margin:0;}" +
			"." + PREVIEW_CLASS + " .sq-section-bd{padding:12px 14px;}" +
			"." + PREVIEW_CLASS + " .sq-dl{display:grid;grid-template-columns:minmax(110px,36%) 1fr;gap:8px 16px;margin:0;font-size:12px;}" +
			"." + PREVIEW_CLASS + " .sq-dl dt{margin:0;color:var(--text-muted,#64748b);font-weight:500;}" +
			"." + PREVIEW_CLASS + " .sq-dl dd{margin:0;word-break:break-word;}" +
			"." + PREVIEW_CLASS + " .sq-kvgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px;}" +
			"." + PREVIEW_CLASS + " .sq-kv{padding:8px 10px;border-radius:8px;border:1px solid var(--border-color,#e2e8f0);background:var(--fg-color,#f8fafc);font-size:11px;}" +
			"." + PREVIEW_CLASS + " .sq-kv-k{display:block;color:var(--text-muted,#64748b);font-weight:600;text-transform:capitalize;margin-bottom:2px;}" +
			"." + PREVIEW_CLASS + " .sq-kv-v{display:block;font-weight:500;word-break:break-word;}" +
			"." + PREVIEW_CLASS + " .sq-empty{padding:16px;text-align:center;font-size:12px;color:var(--text-muted,#64748b);border:1px dashed var(--border-color,#e2e8f0);border-radius:8px;}" +
			"." + PREVIEW_CLASS + " .sq-scroll{max-height:240px;overflow:auto;border-radius:8px;border:1px solid var(--border-color,#e2e8f0);}" +
			"." + PREVIEW_CLASS + " .sq-table{width:100%;border-collapse:collapse;font-size:12px;}" +
			"." + PREVIEW_CLASS + " .sq-table th{position:sticky;top:0;z-index:1;text-align:left;padding:8px 10px;font-size:10px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:var(--text-muted,#64748b);background:var(--fg-color,#f1f5f9);border-bottom:1px solid var(--border-color,#e2e8f0);}" +
			"." + PREVIEW_CLASS + " .sq-table td{padding:8px 10px;border-bottom:1px solid var(--border-color,#e2e8f0);vertical-align:top;}" +
			"." + PREVIEW_CLASS + " .sq-table tr:last-child td{border-bottom:none;}" +
			"." + PREVIEW_CLASS + " .sq-loading{display:flex;align-items:center;gap:10px;padding:20px;color:var(--text-muted,#64748b);font-size:13px;}" +
			"." + PREVIEW_CLASS + " .sq-spin{width:18px;height:18px;border:2px solid var(--border-color,#e2e8f0);border-top-color:var(--primary,#5c6ac4);border-radius:50%;animation:sqspin 0.7s linear infinite;}" +
			"@keyframes sqspin{to{transform:rotate(360deg)}}" +
			".sq-cards-wrap{font-size:13px;color:var(--text-color,#0f172a);}" +
			".sq-cards-scroll{max-height:min(58vh,520px);overflow-y:auto;overflow-x:hidden;min-height:0;padding:2px 2px 6px 0;-webkit-overflow-scrolling:touch;}" +
			".sq-cards{display:flex;flex-direction:column;gap:10px;}" +
			".sq-card{border:1px solid var(--border-color,#e2e8f0);border-radius:10px;overflow:hidden;background:var(--control-bg,#fff);}" +
			".sq-card.open{border-color:var(--primary,#5c6ac4);box-shadow:0 0 0 1px rgba(92,106,196,0.12);}" +
			".sq-card-hd{display:flex;align-items:center;gap:10px;padding:10px 12px;font-weight:600;font-size:13px;flex-wrap:wrap;}" +
			".sq-card-toggle{cursor:pointer;display:flex;align-items:flex-start;gap:10px;flex:1;min-width:0;user-select:none;border-radius:6px;margin:-4px;padding:4px 6px 4px 4px;}" +
			".sq-card-toggle .sq-card-chevron{align-self:center;margin-top:8px;}" +
			".sq-card-head-block{display:flex;align-items:flex-start;gap:12px;min-width:0;flex:1;}" +
			".sq-card-mono-icon{flex-shrink:0;width:36px;height:36px;border-radius:8px;background:#1a1a1a;color:#fff;display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;line-height:1;}" +
			".sq-card-mono-icon.sq-card-mono-icon--compact{font-size:11px;letter-spacing:-0.02em;}" +
			".sq-card-head-text{min-width:0;flex:1;}" +
			".sq-card-head-title{font-weight:600;font-size:14px;color:var(--text-color,#0f172a);line-height:1.3;margin:0 0 6px;}" +
			".sq-card-head-row2{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;line-height:1.45;}" +
			".sq-card-pill{display:inline-flex;align-items:center;padding:2px 10px;border-radius:999px;background:rgba(92,106,196,0.14);color:var(--primary,#5c6ac4);font-size:11px;font-weight:600;white-space:nowrap;max-width:100%;}" +
			".sq-card-sub{color:var(--text-muted,#64748b);font-weight:400;min-width:0;word-break:break-word;}" +
			".sq-card-toggle:hover{background:var(--fg-color,#f8fafc);}" +
			".sq-card-toggle:focus{outline:2px solid var(--primary);outline-offset:2px;}" +
			".sq-card-chevron{flex-shrink:0;width:22px;height:22px;display:flex;align-items:center;justify-content:center;color:var(--text-muted,#64748b);transition:transform .18s ease;font-size:11px;}" +
			".sq-card.open .sq-card-chevron{transform:rotate(90deg);}" +
			".sq-card-hd .sq-card-create{flex-shrink:0;margin-left:auto;cursor:pointer;}" +
			".sq-card-badges{display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center;margin-left:auto;flex-shrink:0;}" +
			".sq-chip-cancelled{font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;background:#fee2e2;color:#b91c1c;}" +
			".sq-card-bd{display:none;border-top:1px solid var(--border-color,#e2e8f0);padding:12px 14px;background:var(--modal-bg,#fafafa);max-height:min(45vh,380px);overflow-y:auto;overflow-x:hidden;}" +
			".sq-card.open .sq-card-bd{display:block;}" +
			".sq-chip-na{font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;background:var(--fill-color,#fef3c7);color:#b45309;flex-shrink:0;margin-left:auto;}" +
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
			return "<div class='sq-empty'>" + __("No parameters on this selection.") + "</div>";
		}
		const esc = frappe.utils.escape_html;
		const cells = keys
			.map(function (k) {
				return (
					"<div class='sq-kv'><span class='sq-kv-k'>" +
					esc(k.replace(/_/g, " ")) +
					"</span><span class='sq-kv-v'>" +
					esc(String(params[k])) +
					"</span></div>"
				);
			})
			.join("");
		return "<div class='sq-kvgrid'>" + cells + "</div>";
	}

	function _formatChargesHtml(charges) {
		if (!charges || !charges.length) {
			return "<div class='sq-empty'>" + __("No charge lines match this service on the Sales Quote.") + "</div>";
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
			"<div class='sq-scroll'><table class='sq-table'><thead><tr>" +
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
				"<div class='" + PREVIEW_CLASS + "'><div class='sq-loading'><span class='sq-spin'></span>" +
				__("Loading preview…") + "</div></div>"
			);
		}
		const esc = frappe.utils.escape_html;
		const sc = p.source_context || {};

		let uncreatable = "";
		if (p.not_creatable_message) {
			uncreatable =
				"<div class='sq-section' style='border-color:var(--orange-500,#ed6c02)'>" +
				"<div class='sq-section-bd' style='font-size:12px;line-height:1.45'>" +
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
			"<dl class='sq-dl'>" +
			ctxRows.map(function (r) { return "<dt>" + r[0] + "</dt><dd>" + r[1] + "</dd>"; }).join("") +
			"</dl>";

		const secContext =
			"<section class='sq-section'><header class='sq-section-hd'>" +
			"<h3 class='sq-section-title'>" + __("Source & links") + "</h3></header>" +
			"<div class='sq-section-bd'>" + ctxDl + "</div></section>";

		const secParams =
			"<section class='sq-section'><header class='sq-section-hd'>" +
			"<h3 class='sq-section-title'>" + __("Scope parameters") + "</h3>" +
			"<span style='font-size:10px;color:var(--text-muted,#64748b)'>" + __("Applied on create") + "</span>" +
			"</header><div class='sq-section-bd'>" + _formatParamsHtml(p.job_detail_parameters) + "</div></section>";

		const charges = p.charges || [];
		const secCharges =
			"<section class='sq-section'><header class='sq-section-hd'>" +
			"<h3 class='sq-section-title'>" + __("Matching quote charges") + "</h3>" +
			"<span style='font-size:10px;color:var(--text-muted,#64748b)'>" + String(charges.length) + " " + __("rows") + "</span>" +
			"</header><div class='sq-section-bd'>" + _formatChargesHtml(charges) + "</div></section>";

		return (
			_styles() +
			"<div class='" + PREVIEW_CLASS + "'>" + uncreatable + secContext + secParams + secCharges + "</div>"
		);
	}

	function _loadCardPreview($pv, frm, choiceEnc, onLoaded) {
		const dec = _decodeChoice(choiceEnc);
		$pv.html(_renderPreviewHtml(null));
		frappe.call({
			method: "logistics.pricing_center.sales_quote_booking_creation.get_sales_quote_booking_preview",
			args: _mainServiceApiArgs(frm, dec.job_type),
			callback: function (r) {
				if (r.exc) {
					$pv.html(
						_styles() +
							"<div class='" + PREVIEW_CLASS + "'><div class='sq-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
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
						"<div class='" + PREVIEW_CLASS + "'><div class='sq-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
						__("Preview could not be loaded.") + "</div></div>"
				);
				if (onLoaded) onLoaded();
			},
		});
	}

	function _iconText(c) {
		const s = ((c && c.service_type) || (c && c.job_type) || "M").toString().trim();
		const m = s.match(/[A-Za-z0-9]/);
		return m ? m[0].toUpperCase() : "M";
	}

	function _buildHead(c) {
		const title =
			(c.header_title && String(c.header_title).trim()) ||
			(c.service_type && String(c.service_type).trim()) ||
			String(c.job_type || "");
		const badge =
			(c.header_badge && String(c.header_badge).trim()) ||
			(c.job_no && String(c.job_no).trim()) ||
			__("Main Service");
		const sub = c.header_subtitle ? String(c.header_subtitle) : "";

		const $block = $("<div>").addClass("sq-card-head-block");
		const iconText = _iconText(c);
		const $icon = $("<span>").addClass("sq-card-mono-icon").text(iconText);
		if (iconText.length > 1) $icon.addClass("sq-card-mono-icon--compact");
		$block.append($icon);

		const $text = $("<div>").addClass("sq-card-head-text");
		$text.append($("<div>").addClass("sq-card-head-title").text(title));
		const $row2 = $("<div>").addClass("sq-card-head-row2");
		$row2.append($("<span>").addClass("sq-card-pill").text(badge));
		if (sub) $row2.append($("<span>").addClass("sq-card-sub").text(sub));
		$text.append($row2);
		$block.append($text);
		return $block;
	}

	function _buildCards(choices) {
		const $wrap = $("<div class='sq-cards-wrap'>");
		const intro = __("Creates from Main Service scope on this Sales Quote. Expand for details; use Create when ready.");
		$wrap.append(
			$("<p>")
				.addClass("text-muted")
				.css({ fontSize: "12px", marginBottom: "10px", lineHeight: 1.45 })
				.text(intro)
		);
		const $scroll = $("<div class='sq-cards-scroll'>");
		const $cards = $("<div class='sq-cards'>");
		choices.forEach(function (c) {
			const enc = _encodeChoice(c);
			const creatable = c.creatable !== false;
			const $card = $("<div class='sq-card'>").attr("data-choice", enc);
			const $hd = $("<div class='sq-card-hd'>");
			const $toggle = $("<div class='sq-card-toggle' role='button' tabindex='0'>");
			$toggle.append($("<span class='sq-card-chevron'>").text("\u25B8"));
			$toggle.append(_buildHead(c));
			$hd.append($toggle);
			if (creatable) {
				$hd.append($("<button type='button'>").addClass("btn btn-primary btn-sm sq-card-create").text(__("Create")));
			} else {
				const linked = c.job_no != null && String(c.job_no).trim() !== "";
				const $badges = $("<span class='sq-card-badges'>");
				if (c.linked_job_cancelled) $badges.append($("<span class='sq-chip-cancelled'>").text(__("Cancelled")));
				$badges.append($("<span class='sq-chip-na'>").text(linked ? __("Linked") : __("Cannot create")));
				$hd.append($badges);
			}
			const $bd = $("<div class='sq-card-bd'>");
			const $pv = $("<div class='sq-card-preview'>");
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
		} else if (msg.cross_docking_order) {
			_go("Cross-Docking Order", msg.cross_docking_order);
		} else if (msg.time_sensitive_case) {
			_go("Time Sensitive Case", msg.time_sensitive_case);
		}
	}

	function _callCreate(frm, dec, onDialogHide) {
		frappe.call({
			method: "logistics.pricing_center.sales_quote_booking_creation.create_booking_or_order_from_sales_quote",
			args: _mainServiceApiArgs(frm, dec.job_type),
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
		$root.on("click", ".sq-card-toggle", function () {
			const $card = $(this).closest(".sq-card");
			$card.toggleClass("open");
			if ($card.hasClass("open")) {
				const $pv = $card.find(".sq-card-preview");
				if ($pv.data("sq-loaded")) return;
				const enc = $card.attr("data-choice");
				_loadCardPreview($pv, frm, enc, function () {
					$pv.data("sq-loaded", true);
				});
			}
		});
		$root.on("keydown", ".sq-card-toggle", function (e) {
			if (e.which === 13 || e.which === 32) {
				e.preventDefault();
				$(this).trigger("click");
			}
		});
		$root.on("click", ".sq-card-create", function (e) {
			e.stopPropagation();
			const $card = $(this).closest(".sq-card");
			const enc = $card.attr("data-choice");
			const dec = _decodeChoice(enc);
			if (!dec.job_type) {
				frappe.msgprint({
					title: __("Create Booking / Order"),
					message: __("Set Primary Service Type on this Sales Quote before creating."),
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

	function _introHtml(frm, choices) {
		const esc = frappe.utils.escape_html;
		const ref = esc(__("Sales Quote") + " · " + (frm.doc.name || ""));
		const body = __("Creates from Main Service scope. Expand to preview; use Create when ready.");
		return (
			"<div class='" + PREVIEW_CLASS + "' style='margin-bottom:4px'>" +
			"<div style='font-size:12px;color:var(--text-muted,#64748b);line-height:1.5'>" +
			"<strong style='color:var(--text-color,#0f172a)'>" + __("From") + "</strong> " + ref + "<br>" +
			body +
			"</div></div>"
		);
	}

	window.logistics_sales_quote_supports_booking_order_creation =
		window.logistics_sales_quote_supports_booking_order_creation ||
		function (doc) {
			if (!doc || doc.additional_charge) {
				return false;
			}
			const qt = doc.quotation_type;
			if (qt === "Regular") {
				return true;
			}
			if (qt === "Project") {
				return ["Air", "Sea", "Transport", "Customs", "Custom", "Warehousing", "Time Sensitive"].includes(
					doc.main_service
				);
			}
			return false;
		};

	window.logistics_show_sales_quote_booking_dialog = function (frm) {
		if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
			frappe.msgprint({
				title: __("Save Required"),
				message: __("Save the Sales Quote before creating bookings or orders."),
				indicator: "orange",
			});
			return;
		}
		if (frm.doc.docstatus !== 1) {
			frappe.msgprint({
				title: __("Submit Required"),
				message: __("Submit the Sales Quote before creating bookings or orders."),
				indicator: "orange",
			});
			return;
		}
		if (!logistics_sales_quote_supports_booking_order_creation(frm.doc)) {
			frappe.msgprint({
				title: __("Not available"),
				message: __(
					"Create Booking/Order is only available for Regular Sales Quotes, or Project quotes with Main Service Air, Sea, Transport, Customs, Warehousing, or Time Sensitive."
				),
				indicator: "orange",
			});
			return;
		}
		frappe.call({
			method: "logistics.pricing_center.sales_quote_booking_creation.get_sales_quote_booking_choices",
			args: {
				sales_quote: frm.doc.name,
				linked_services: _linkedServicesPayload(frm),
				quote_context: _quoteContextPayload(frm),
			},
			freeze: true,
			freeze_message: __("Loading options..."),
			callback: function (r) {
				const msg = r.message || {};
				const choices = _normalizeMainServiceChoices(frm, msg.choices || []);
				if (!choices.length) {
					frappe.msgprint({
						title: __("Create Booking / Order"),
						message: __(
							"No booking or order can be created from this Sales Quote. Set Main Service to Air, Sea, Transport, Customs, Warehousing, or Time Sensitive with matching charges, or add Services lines."
						),
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
					d.fields_dict.info.$wrapper.html(_introHtml(frm, choices));
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
