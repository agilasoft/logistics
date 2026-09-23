// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

/**
 * Time Sensitive Case → Create Service card modal (aligned with main-service Create internal job UX).
 */
frappe.provide("logistics.time_sensitive");

(function () {
	"use strict";

	var TS_CREATE_API =
		"logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case";
	var PREVIEW_CLASS = "logistics-ts-create-preview";

	function _tsCreateStyles() {
		return (
			"<style>" +
			"." +
			PREVIEW_CLASS +
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
			PREVIEW_CLASS +
			" .ij-section{" +
			"border:1px solid var(--ij-border);border-radius:var(--ij-radius);" +
			"background:var(--ij-surface);margin-bottom:12px;overflow:hidden;" +
			"}" +
			"." +
			PREVIEW_CLASS +
			" .ij-section-hd{" +
			"padding:10px 14px;border-bottom:1px solid var(--ij-border);" +
			"display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap;" +
			"background:var(--fg-color,#f8fafc);" +
			"}" +
			"." +
			PREVIEW_CLASS +
			" .ij-section-title{" +
			"font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;" +
			"color:var(--ij-muted);margin:0" +
			"}" +
			"." +
			PREVIEW_CLASS +
			" .ij-section-bd{padding:12px 14px}" +
			"." +
			PREVIEW_CLASS +
			" .ij-dl{" +
			"display:grid;grid-template-columns:minmax(110px,36%) 1fr;gap:8px 16px;margin:0;font-size:12px" +
			"}" +
			"." +
			PREVIEW_CLASS +
			" .ij-dl dt{margin:0;color:var(--ij-muted);font-weight:500}" +
			"." +
			PREVIEW_CLASS +
			" .ij-dl dd{margin:0;word-break:break-word}" +
			"." +
			PREVIEW_CLASS +
			" .ij-kvgrid{" +
			"display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px" +
			"}" +
			"." +
			PREVIEW_CLASS +
			" .ij-kv{" +
			"padding:8px 10px;border-radius:8px;border:1px solid var(--ij-border);" +
			"background:var(--ij-surface);font-size:12px" +
			"}" +
			"." +
			PREVIEW_CLASS +
			" .ij-kv-k{display:block;font-size:10px;color:var(--ij-muted);margin-bottom:2px;text-transform:capitalize}" +
			"." +
			PREVIEW_CLASS +
			" .ij-kv-v{display:block;font-weight:500;word-break:break-word}" +
			"." +
			PREVIEW_CLASS +
			" .ij-empty{" +
			"padding:12px;border:1px dashed var(--ij-border);border-radius:8px;color:var(--ij-muted);font-size:12px" +
			"}" +
			"." +
			PREVIEW_CLASS +
			" .ij-table{width:100%;border-collapse:collapse;font-size:12px}" +
			"." +
			PREVIEW_CLASS +
			" .ij-table th{" +
			"text-align:left;padding:8px 10px;border-bottom:1px solid var(--ij-border);" +
			"font-size:10px;text-transform:uppercase;color:var(--ij-muted)" +
			"}" +
			"." +
			PREVIEW_CLASS +
			" .ij-table td{padding:8px 10px;border-bottom:1px solid var(--ij-border);vertical-align:top}" +
			"." +
			PREVIEW_CLASS +
			" .ij-loading{display:flex;align-items:center;gap:10px;padding:20px;color:var(--ij-muted);font-size:13px}" +
			"." +
			PREVIEW_CLASS +
			" .ij-spin{" +
			"width:18px;height:18px;border:2px solid var(--ij-border);" +
			"border-top-color:var(--ij-accent);border-radius:50%;animation:tscspin 0.7s linear infinite" +
			"}" +
			"@keyframes tscspin{to{transform:rotate(360deg)}}" +
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
			".lij-card-pill--ij{background:rgba(217,119,6,0.14);color:#b45309;font-family:var(--font-mono,ui-monospace,monospace);}" +
			".lij-card-sub{color:var(--text-muted,#64748b);font-weight:400;min-width:0;word-break:break-word;}" +
			".lij-card-toggle:hover{background:var(--fg-color,#f8fafc);}" +
			".lij-card-toggle:focus{outline:2px solid var(--primary);outline-offset:2px;}" +
			".lij-card-chevron{flex-shrink:0;width:22px;height:22px;display:flex;align-items:center;justify-content:center;color:var(--text-muted,#64748b);transition:transform .18s ease;font-size:11px;}" +
			".lij-card.open .lij-card-chevron{transform:rotate(90deg);}" +
			".lij-card-hd .lij-card-create{flex-shrink:0;margin-left:auto;cursor:pointer;}" +
			".lij-card-badges{display:inline-flex;flex-wrap:wrap;gap:6px;align-items:center;margin-left:auto;flex-shrink:0;}" +
			".lij-card-bd{display:none;border-top:1px solid var(--border-color,#e2e8f0);padding:12px 14px;background:var(--modal-bg,#fafafa);max-height:min(45vh,380px);overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;}" +
			".lij-card.open .lij-card-bd{display:block;}" +
			".lij-card-preview{min-height:8px;}" +
			".lij-chip-na{font-size:10px;font-weight:600;padding:2px 8px;border-radius:999px;background:var(--fill-color,#fef3c7);color:#b45309;flex-shrink:0;margin-left:auto;}" +
			"</style>"
		);
	}

	function _formatParamsHtml(params) {
		if (!params || typeof params !== "object") {
			return "<div class='ij-empty'>" + __("No parameters on this selection.") + "</div>";
		}
		var keys = Object.keys(params);
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

	function _formatChargesPreviewHtml(charges) {
		if (!charges || !charges.length) {
			return (
				"<div class='ij-empty'>" +
				__("No charge lines match this service on the case.") +
				"</div>"
			);
		}
		var esc = frappe.utils.escape_html;
		var rows = charges
			.map(function (c) {
				var label = (c.item_code || "") + (c.description ? " — " + c.description : "");
				return (
					"<tr><td>" +
					esc(c.service_type || "") +
					"</td><td>" +
					esc(String(label)) +
					"</td><td style='white-space:nowrap'>" +
					esc(c.rate != null ? String(c.rate) : "—") +
					"</td><td>" +
					esc(String(c.currency || "")) +
					"</td><td>" +
					esc(String(c.qty != null ? c.qty : "—")) +
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
			__("Qty") +
			"</th></tr></thead><tbody>" +
			rows +
			"</tbody></table></div>"
		);
	}

	function _renderPreviewHtml(p) {
		if (!p) {
			return (
				_tsCreateStyles() +
				"<div class='" +
				PREVIEW_CLASS +
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
			["dt", __("Target document"), esc(p.job_type || "—")],
		];
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
			"<span style='font-size:10px;color:var(--ij-muted)'>" +
			__("Applied on create") +
			"</span></header><div class='ij-section-bd'>" +
			_formatParamsHtml(p.job_detail_parameters) +
			"</div></section>";

		var secCharges =
			"<section class='ij-section'><header class='ij-section-hd'>" +
			"<h3 class='ij-section-title'>" +
			__("Charges to copy") +
			"</h3>" +
			"<span style='font-size:10px;color:var(--ij-muted)'>" +
			String((p.charges && p.charges.length) || 0) +
			" " +
			__("rows") +
			"</span></header><div class='ij-section-bd'>" +
			_formatChargesPreviewHtml(p.charges) +
			"</div></section>";

		return (
			_tsCreateStyles() +
			"<div class='" +
			PREVIEW_CLASS +
			"'>" +
			uncreatableBanner +
			secContext +
			secParams +
			secCharges +
			"</div>"
		);
	}

	function _dialogIntroHtml(frm) {
		var esc = frappe.utils.escape_html;
		var ref = esc(__("Time Sensitive Case") + " · " + (frm.doc.name || ""));
		return (
			"<div style='margin-bottom:4px'>" +
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

	function _choiceHeaderLetter(c) {
		var st = ((c && c.service_type) || "").toString().trim();
		if (st) {
			var m0 = st.match(/[A-Za-z0-9]/);
			return m0 ? m0[0].toUpperCase() : "?";
		}
		return "?";
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
			String((c && c.service_type) || "") ||
			"";
		var badge =
			(c.header_badge != null && String(c.header_badge).trim() !== "" && String(c.header_badge)) ||
			(c.order_no != null && String(c.order_no).trim() !== "" && String(c.order_no).trim()) ||
			__("Pending");
		var sub =
			c.header_subtitle != null && String(c.header_subtitle).trim()
				? String(c.header_subtitle)
				: "";
		var ijLink =
			c.internal_job != null && String(c.internal_job).trim() !== ""
				? String(c.internal_job).trim()
				: c.linked_service || "";
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
		if (ijLink) {
			$row2.append(
				$("<span>")
					.addClass("lij-card-pill lij-card-pill--ij")
					.attr("title", __("Internal Job: {0}", [ijLink]))
					.text(ijLink)
			);
		}
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
			var linkedService = c.linked_service || "";
			var creatable = c.creatable !== false;
			var $card = $('<div class="lij-card">').attr("data-linked-service", linkedService);
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
				var linked =
					c.order_no != null && String(c.order_no).trim() !== "";
				var $badges = $('<span class="lij-card-badges">');
				$badges.append(
					$('<span class="lij-chip-na">').text(linked ? __("Linked") : __("Cannot create"))
				);
				$hd.append($badges);
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

	function _loadCardPreview($pv, frm, linkedService, onLoaded) {
		if (!linkedService) {
			$pv.html(
				_tsCreateStyles() +
					"<div class='" +
					PREVIEW_CLASS +
					"'><div class='ij-empty'>" +
					__("Nothing to preview for this option.") +
					"</div></div>"
			);
			if (onLoaded) onLoaded();
			return;
		}
		$pv.html(_renderPreviewHtml(null));
		frappe.call({
			method: TS_CREATE_API + ".get_case_service_creation_preview",
			args: {
				case_name: frm.doc.name,
				linked_service: linkedService,
			},
			callback: function (r) {
				if (r.exc) {
					$pv.html(
						_tsCreateStyles() +
							"<div class='" +
							PREVIEW_CLASS +
							"'><div class='ij-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
							__("Preview could not be loaded.") +
							"</div></div>"
					);
				} else {
					$pv.html(_renderPreviewHtml(r.message || {}));
				}
				if (onLoaded) onLoaded();
			},
			error: function () {
				$pv.html(
					_tsCreateStyles() +
						"<div class='" +
						PREVIEW_CLASS +
						"'><div class='ij-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
						__("Preview could not be loaded.") +
						"</div></div>"
				);
				if (onLoaded) onLoaded();
			},
		});
	}

	function _runCreateService(frm, linkedService, choice) {
		if (choice && choice.creatable === false) {
			frappe.msgprint({
				title: __("Create Booking / Order"),
				message:
					(choice && choice.not_creatable_message) ||
					__("This booking / order cannot be created from here."),
				indicator: "orange",
			});
			return;
		}
		frappe.call({
			method: TS_CREATE_API + ".create_service_document",
			args: {
				case_name: frm.doc.name,
				linked_service: linkedService,
			},
			freeze: true,
			freeze_message: __("Creating..."),
			callback: function (r) {
				if (r.message) {
					frm.reload_doc();
					frappe.set_route("Form", r.message.doctype, r.message.name);
				}
			},
		});
	}

	function _bindChoiceCards($root, frm, d, choicesByLinkedService) {
		$root.on("click", ".lij-card-toggle", function () {
			var $card = $(this).closest(".lij-card");
			$card.toggleClass("open");
			if ($card.hasClass("open")) {
				var linkedService = $card.attr("data-linked-service");
				var $pv = $card.find(".lij-card-preview");
				if ($pv.data("ts-loaded")) {
					return;
				}
				_loadCardPreview($pv, frm, linkedService, function () {
					$pv.data("ts-loaded", true);
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
			var linkedService = $card.attr("data-linked-service");
			var choice = choicesByLinkedService[linkedService] || null;
			d.hide();
			_runCreateService(frm, linkedService, choice);
		});
	}

	function _showBlocked(msg) {
		frappe.msgprint({
			title: __("Create Booking / Order"),
			message:
				(msg && msg.blocked_message) ||
				__("No booking / orders can be created from this case."),
			indicator: "orange",
		});
	}

	function _openCreateServiceDialog(frm, msg) {
		var choices = (msg && msg.choices) || [];
		if (window.logistics && logistics.menu) {
			choices = choices.filter(function (c) {
				if (!c || !c.linked_service) {
					return false;
				}
				if (!c.creatable) {
					return true;
				}
				if (c.job_type) {
					return logistics.menu.can(c.job_type, "create");
				}
				return true;
			});
		}
		if (!choices.length) {
			_showBlocked(msg);
			return;
		}

		var choicesByLinkedService = {};
		choices.forEach(function (c) {
			if (c && c.linked_service) {
				choicesByLinkedService[c.linked_service] = c;
			}
		});

		var d = new frappe.ui.Dialog({
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
			d.fields_dict.info.$wrapper.html(_dialogIntroHtml(frm));
		}
		var $cardsRoot = d.fields_dict.cards_html && d.fields_dict.cards_html.$wrapper;
		if ($cardsRoot && $cardsRoot.length) {
			$cardsRoot.empty();
			$cardsRoot.append(_tsCreateStyles());
			$cardsRoot.append(_buildChoiceCards(choices));
			_bindChoiceCards($cardsRoot, frm, d, choicesByLinkedService);
		}
		d.show();
	}

	function _loadChoices(frm) {
		frappe.call({
			method: TS_CREATE_API + ".get_case_service_creation_choices",
			args: { case_name: frm.doc.name },
			freeze: true,
			freeze_message: __("Loading options..."),
			callback: function (r) {
				_openCreateServiceDialog(frm, r.message || {});
			},
		});
	}

	logistics.time_sensitive.show_create_service_dialog = function (frm) {
		if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
			frappe.msgprint({
				message: __("Save the Time Sensitive Case before creating a booking / order."),
				indicator: "orange",
			});
			return;
		}
		_loadChoices(frm);
	};
})();
