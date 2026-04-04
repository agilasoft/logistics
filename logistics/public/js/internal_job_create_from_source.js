// Copyright (c) 2026, Agilasoft and contributors
// For license information, please see license.txt

(function () {
	"use strict";

	var IJ_PREVIEW_CLASS = "logistics-ij-preview";

	function _encodeInternalJobChoice(c) {
		if (c.mode === "detail") {
			return "d|" + String(c.detail_idx) + "|" + String(c.job_type || "");
		}
		return "g||" + String(c.job_type || "");
	}

	function _decodeInternalJobChoice(s) {
		var parts = String(s || "").split("|");
		if (parts[0] === "d" && parts.length >= 3) {
			var idx = parseInt(parts[1], 10);
			return {
				detail_idx: isNaN(idx) ? null : idx,
				job_type: parts.slice(2).join("|"),
			};
		}
		if (parts[0] === "g" && parts.length >= 3) {
			return { detail_idx: null, job_type: parts.slice(2).join("|") };
		}
		return { detail_idx: null, job_type: "" };
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
			" .ij-hero{" +
			"display:flex;align-items:flex-start;gap:12px;padding:12px 14px;" +
			"border:1px solid var(--ij-border);border-radius:var(--ij-radius);" +
			"background:linear-gradient(135deg,rgba(92,106,196,0.06) 0%,transparent 55%);" +
			"margin-bottom:14px;" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-hero-mark{" +
			"flex-shrink:0;width:36px;height:36px;border-radius:9px;" +
			"background:var(--ij-accent);color:#fff;display:flex;align-items:center;justify-content:center;" +
			"font-size:15px;font-weight:700;" +
			"}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-hero-body{min-width:0}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-hero-title{font-weight:600;font-size:14px;margin:0 0 4px}" +
			"." +
			IJ_PREVIEW_CLASS +
			" .ij-hero-meta{font-size:12px;color:var(--ij-muted);margin:0}" +
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
		var jobLabel = esc(String(p.job_type || "—"));
		var markLetter = esc(String((p.job_type || "?").trim().charAt(0) || "?").toUpperCase());

		var heroSub = [];
		if (p.uses_job_detail_row) {
			heroSub.push(
				"<span class='ij-badge'>" +
					__("Job Details idx {0}", [String(p.detail_idx || "")]) +
					"</span> " +
					__("Row parameters override default routing.")
			);
		} else {
			heroSub.push(
				"<span class='ij-badge ij-badge-muted'>" + __("Default routing") + "</span> " +
					__("From first matching Job Details line or quote context.")
			);
		}
		if (sc.from_main_service_shipment) {
			heroSub.push(
				"<br><span style='margin-top:6px;display:inline-block'>" +
					__("Main-service shipment: the new document will be an internal job linked here.") +
					"</span>"
			);
		}

		var hero =
			"<div class='ij-hero'>" +
			"<div class='ij-hero-mark'>" +
			markLetter +
			"</div>" +
			"<div class='ij-hero-body'>" +
			"<p class='ij-hero-title'>" +
			jobLabel +
			"</p>" +
			"<p class='ij-hero-meta'>" +
			heroSub.join(" ") +
			"</p>" +
			"</div></div>";

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

		return _ijStyles() + "<div class='" + IJ_PREVIEW_CLASS + "'>" + hero + secContext + secParams + secCharges + "</div>";
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
		frappe.msgprint({
			title: __("Create Internal Job"),
			message: __("Unexpected response while creating {0}.", [jobType]),
			indicator: "orange",
		});
	}

	function _refreshInternalJobPreview(d, frm, choiceVal) {
		var wrap = d.fields_dict.preview_html && d.fields_dict.preview_html.$wrapper;
		if (!wrap) {
			return;
		}
		var dec = _decodeInternalJobChoice(choiceVal);
		if (!dec.job_type) {
			wrap.html(
				_ijStyles() +
					"<div class='" +
					IJ_PREVIEW_CLASS +
					"'><div class='ij-empty'>" +
					__("Select an option above to see the preview.") +
					"</div></div>"
			);
			return;
		}
		wrap.html(_renderInternalJobPreviewHtml(null));
		frappe.call({
			method: "logistics.utils.internal_job_from_source.get_internal_job_creation_preview",
			args: {
				source_doctype: frm.doctype,
				source_name: frm.doc.name,
				job_type: dec.job_type,
				internal_job_detail_idx: dec.detail_idx,
			},
			callback: function (r) {
				if (r.exc) {
					wrap.html(
						_ijStyles() +
							"<div class='" +
							IJ_PREVIEW_CLASS +
							"'><div class='ij-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
							__("Preview could not be loaded. You can still use Create.") +
							"</div></div>"
					);
					return;
				}
				wrap.html(_renderInternalJobPreviewHtml(r.message || {}));
			},
			error: function () {
				wrap.html(
					_ijStyles() +
						"<div class='" +
						IJ_PREVIEW_CLASS +
						"'><div class='ij-empty' style='border-style:solid;color:var(--red-500,#c62828)'>" +
						__("Preview could not be loaded. You can still use Create.") +
						"</div></div>"
				);
			},
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
			__("Pick what to create. The preview updates with source links, header fields, and charge lines.") +
			"</div></div>"
		);
	}

	window.logistics_show_create_internal_job_dialog = function (frm) {
		if (!frm || !frm.doc || !frm.doc.name || frm.doc.__islocal) {
			return;
		}
		frappe.call({
			method: "logistics.utils.internal_job_from_source.get_internal_job_creation_choices",
			args: { source_doctype: frm.doctype, source_name: frm.doc.name },
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
				var selectOptions = choices.map(function (c) {
					return { label: c.label, value: _encodeInternalJobChoice(c) };
				});
				var d = new frappe.ui.Dialog({
					title: __("Create internal job"),
					size: "large",
					fields: [
						{ fieldname: "info", fieldtype: "HTML" },
						{
							fieldname: "choice",
							fieldtype: "Select",
							label: __("What to create"),
							options: selectOptions,
							reqd: 1,
							default: selectOptions[0] ? selectOptions[0].value : null,
						},
						{ fieldname: "preview_html", fieldtype: "HTML", label: __("Preview") },
					],
					primary_action_label: __("Create"),
					primary_action: function (values) {
						var dec = _decodeInternalJobChoice(values.choice);
						if (!dec.job_type) {
							frappe.msgprint({ message: __("Invalid selection."), indicator: "red" });
							return;
						}
						d.hide();
						frappe.call({
							method: "logistics.utils.internal_job_from_source.create_internal_job_from_operational_source",
							args: {
								source_doctype: frm.doctype,
								source_name: frm.doc.name,
								job_type: dec.job_type,
								internal_job_detail_idx: dec.detail_idx,
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
					},
				});
				if (d.fields_dict.info && d.fields_dict.info.$wrapper) {
					d.fields_dict.info.$wrapper.html(_dialogIntroHtml(frm));
				}
				d.show();
				var $ch = d.fields_dict.choice && d.fields_dict.choice.$input;
				if ($ch && $ch.length) {
					$ch.on("change", function () {
						_refreshInternalJobPreview(d, frm, d.get_value("choice"));
					});
				}
				_refreshInternalJobPreview(d, frm, d.get_value("choice") || (selectOptions[0] && selectOptions[0].value));
			},
		});
	};
})();
