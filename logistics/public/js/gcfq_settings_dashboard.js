// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt
// Get Charges from Quotation Settings — Dashboard tab UI

frappe.provide("logistics.gcfq_dashboard");

(function () {
	"use strict";

	var STATE = {
		modules: [],
		doctype: null,
		workspace: null,
		dirty: false,
		dragKey: null,
	};

	function can_write() {
		return frappe.model.can_write("Get Charges from Quotation Settings");
	}

	function mount($wrap) {
		if (!$wrap || !$wrap.length) {
			return;
		}
		$wrap.html('<div class="gcfq-dash-loading text-muted">' + __("Loading dashboard…") + "</div>");
		frappe.call({
			method: "logistics.utils.get_charges_from_quotation.get_gcfq_dashboard_modules",
			callback: function (r) {
				STATE.modules = (r && r.message && r.message.modules) || [];
				var first = STATE.doctype || (STATE.modules[0] && STATE.modules[0].doctype);
				render_shell($wrap);
				if (first) {
					select_module($wrap, first);
				} else {
					$wrap.find(".gcfq-dash-workspace").html(
						'<div class="gcfq-dash-empty">' + __("No modules available.") + "</div>"
					);
				}
			},
			error: function () {
				$wrap.html(
					'<div class="gcfq-dash-empty">' + __("Could not load dashboard.") + "</div>"
				);
			},
		});
	}

	function render_shell($wrap) {
		var $root = $('<div class="gcfq-dash">');
		var $left = $('<div class="gcfq-dash-panel gcfq-dash-left">').appendTo($root);
		$left.append($('<div class="gcfq-dash-step">').text("1 · " + __("Select Module")));
		var $list = $('<div class="gcfq-dash-modules">').appendTo($left);
		STATE.modules.forEach(function (m) {
			var $btn = $('<button type="button" class="gcfq-dash-module">')
				.attr("data-doctype", m.doctype)
				.append($('<span class="gcfq-dash-module-label">').text(m.label || m.doctype))
				.append(
					$('<span class="gcfq-dash-module-count">').text(
						String(m.enabled_count != null ? m.enabled_count : m.filter_count || 0)
					)
				);
			$list.append($btn);
		});
		$left.append(
			$('<div class="gcfq-dash-about">').text(
				__(
					"These settings control the List filter criteria layout for Get Charges from Quotation on each job type."
				)
			)
		);

		var $mid = $('<div class="gcfq-dash-panel gcfq-dash-workspace">').appendTo($root);
		$mid.append($('<div class="gcfq-dash-empty">').text(__("Select a module.")));

		var $right = $('<div class="gcfq-dash-panel gcfq-dash-right">').appendTo($root);
		$right.append(
			$('<div class="gcfq-dash-side-block">')
				.append($('<div class="gcfq-dash-side-title">').text(__("Legend")))
				.append(
					$('<ul class="gcfq-dash-legend">')
						.append($("<li>").text(__("Locked cards: Main Service & Customer (always shown)")))
						.append($("<li>").text(__("Editable: operators can change the filter in the dialog")))
						.append($("<li>").text(__("Read-only: shown but locked to the job value")))
						.append($("<li>").text(__("Disabled: hidden from the dialog; job value still used for matching")))
				)
		);
		$right.append(
			$('<div class="gcfq-dash-side-block">')
				.append($('<div class="gcfq-dash-side-title">').text(__("Tips")))
				.append(
					$('<ul class="gcfq-dash-tips">')
						.append($("<li>").text(__("Drag cards to change order (left to right, then top to bottom).")))
						.append($("<li>").text(__("Disable a filter to hide it from the dialog.")))
						.append($("<li>").text(__("Add Filters only offers unused catalog fields for this module.")))
				)
		);
		$right.append(
			$('<div class="gcfq-dash-note">').text(
				__(
					"Changes apply to all users the next time they open Get Charges from Quotation for the selected job type."
				)
			)
		);

		$wrap.empty().append($root);

		$list.on("click", ".gcfq-dash-module", function () {
			var dt = $(this).attr("data-doctype");
			if (!dt) {
				return;
			}
			if (STATE.dirty && !confirm(__("Discard unsaved changes for this module?"))) {
				return;
			}
			select_module($wrap, dt);
		});
	}

	function select_module($wrap, doctype) {
		STATE.doctype = doctype;
		$wrap.find(".gcfq-dash-module").removeClass("is-active");
		$wrap.find('.gcfq-dash-module[data-doctype="' + doctype + '"]').addClass("is-active");
		var $ws = $wrap.find(".gcfq-dash-workspace");
		$ws.html('<div class="text-muted">' + __("Loading…") + "</div>");
		frappe.call({
			method: "logistics.utils.get_charges_from_quotation.get_gcfq_dashboard_workspace",
			args: { doctype: doctype },
			callback: function (r) {
				STATE.workspace = (r && r.message) || null;
				STATE.dirty = false;
				render_workspace($wrap);
				refresh_module_counts($wrap);
			},
		});
	}

	function refresh_module_counts($wrap) {
		frappe.call({
			method: "logistics.utils.get_charges_from_quotation.get_gcfq_dashboard_modules",
			callback: function (r) {
				STATE.modules = (r && r.message && r.message.modules) || STATE.modules;
				STATE.modules.forEach(function (m) {
					$wrap
						.find('.gcfq-dash-module[data-doctype="' + m.doctype + '"] .gcfq-dash-module-count')
						.text(String(m.enabled_count != null ? m.enabled_count : m.filter_count || 0));
				});
			},
		});
	}

	function render_workspace($wrap) {
		var ws = STATE.workspace;
		var $ws = $wrap.find(".gcfq-dash-workspace").empty();
		if (!ws) {
			$ws.html('<div class="gcfq-dash-empty">' + __("Select a module.") + "</div>");
			return;
		}

		var $head = $('<div class="gcfq-dash-workspace-head">').appendTo($ws);
		$head.append(
			$('<h3 class="gcfq-dash-workspace-title">').text(
				"2 · " + __("Configure Filters for {0}", [ws.label || ws.doctype])
			)
		);
		var $actions = $('<div class="gcfq-dash-actions">').appendTo($head);
		if (can_write()) {
			var $add = $('<button type="button" class="btn btn-xs btn-default">').text(
				__("Add Filters")
			);
			$add.on("click", function () {
				open_add_filters($wrap);
			});
			$actions.append($add);
			var $reset = $('<button type="button" class="btn btn-xs btn-default">').text(
				__("Restore Defaults")
			);
			$reset.on("click", function () {
				restore_defaults($wrap);
			});
			$actions.append($reset);
			var $save = $('<button type="button" class="btn btn-xs btn-primary">').text(
				__("Save Changes")
			);
			$save.on("click", function () {
				save_workspace($wrap);
			});
			$actions.append($save);
		}

		var $locked = $('<div class="gcfq-dash-locked">').appendTo($ws);
		(ws.locked || []).forEach(function (L) {
			$locked.append(
				$('<div class="gcfq-dash-locked-card">')
					.append($("<strong>").text(L.label || L.key))
					.append($("<span>").text(__("Always shown · locked")))
			);
		});

		var $cards = $('<div class="gcfq-dash-cards">').appendTo($ws);
		(ws.filters || []).forEach(function (f, idx) {
			$cards.append(build_card(f, idx + 1));
		});
		bind_card_dnd($wrap, $cards);
		bind_card_toggles($wrap, $cards);

		if (!(ws.filters || []).length) {
			$cards.append(
				$('<div class="gcfq-dash-empty">').text(
					__("No catalog filters for this module.")
				)
			);
		}
	}

	function build_card(f, seq) {
		var enabled = !!f.enabled;
		var editable = !!f.editable;
		var $card = $('<div class="gcfq-dash-card">')
			.attr("draggable", can_write() ? "true" : "false")
			.attr("data-key", f.key)
			.toggleClass("is-disabled", !enabled);
		var $top = $('<div class="gcfq-dash-card-top">').appendTo($card);
		$top.append($('<span class="gcfq-dash-card-handle">').text("⠿"));
		$top.append($('<span class="gcfq-dash-card-seq">').text(String(seq)));
		var $meta = $("<div>").appendTo($top);
		$meta.append($('<div class="gcfq-dash-card-title">').text(f.label || f.key));
		$meta.append($('<div class="gcfq-dash-card-key">').text(f.key));

		var $toggles = $('<div class="gcfq-dash-card-toggles">').appendTo($card);
		var $en = $(
			'<label class="gcfq-dash-toggle"><input type="checkbox" data-toggle="enabled"> ' +
				__("Enabled") +
				"</label>"
		);
		$en.find("input").prop("checked", enabled).prop("disabled", !can_write());
		var $ed = $(
			'<label class="gcfq-dash-toggle"><input type="checkbox" data-toggle="editable"> ' +
				__("Editable") +
				"</label>"
		);
		$ed.find("input").prop("checked", editable).prop("disabled", !can_write() || !enabled);
		$toggles.append($en).append($ed);

		var badgeClass = !enabled ? "gcfq-dash-badge--off" : editable ? "gcfq-dash-badge--ok" : "gcfq-dash-badge--ro";
		var badgeText = !enabled ? __("Disabled") : editable ? __("Editable") : __("Read-only");
		$card.append($('<span class="gcfq-dash-badge">').addClass(badgeClass).text(badgeText));
		return $card;
	}

	function collect_filters($wrap) {
		var out = [];
		$wrap.find(".gcfq-dash-card").each(function () {
			var $c = $(this);
			out.push({
				key: $c.attr("data-key"),
				enabled: $c.find('input[data-toggle="enabled"]').is(":checked") ? 1 : 0,
				editable: $c.find('input[data-toggle="editable"]').is(":checked") ? 1 : 0,
			});
		});
		return out;
	}

	function sync_workspace_from_dom($wrap) {
		if (!STATE.workspace) {
			return;
		}
		STATE.workspace.filters = collect_filters($wrap).map(function (f) {
			var label = "";
			$wrap.find('.gcfq-dash-card[data-key="' + f.key + '"] .gcfq-dash-card-title').each(function () {
				label = $(this).text();
			});
			return {
				key: f.key,
				label: label || f.key,
				enabled: !!f.enabled,
				editable: !!f.editable,
			};
		});
		STATE.dirty = true;
	}

	function resequence_cards($cards) {
		$cards.find(".gcfq-dash-card").each(function (i) {
			$(this).find(".gcfq-dash-card-seq").text(String(i + 1));
		});
	}

	function bind_card_toggles($wrap, $cards) {
		$cards.on("change", "input[data-toggle]", function () {
			var $card = $(this).closest(".gcfq-dash-card");
			var enabled = $card.find('input[data-toggle="enabled"]').is(":checked");
			$card.toggleClass("is-disabled", !enabled);
			$card.find('input[data-toggle="editable"]').prop("disabled", !can_write() || !enabled);
			var editable = enabled && $card.find('input[data-toggle="editable"]').is(":checked");
			var $badge = $card.find(".gcfq-dash-badge");
			$badge
				.removeClass("gcfq-dash-badge--ok gcfq-dash-badge--ro gcfq-dash-badge--off")
				.addClass(!enabled ? "gcfq-dash-badge--off" : editable ? "gcfq-dash-badge--ok" : "gcfq-dash-badge--ro")
				.text(!enabled ? __("Disabled") : editable ? __("Editable") : __("Read-only"));
			sync_workspace_from_dom($wrap);
		});
	}

	function bind_card_dnd($wrap, $cards) {
		if (!can_write()) {
			return;
		}
		$cards.on("dragstart", ".gcfq-dash-card", function (e) {
			STATE.dragKey = $(this).attr("data-key");
			$(this).addClass("is-dragging");
			if (e.originalEvent && e.originalEvent.dataTransfer) {
				e.originalEvent.dataTransfer.effectAllowed = "move";
				e.originalEvent.dataTransfer.setData("text/plain", STATE.dragKey || "");
			}
		});
		$cards.on("dragend", ".gcfq-dash-card", function () {
			$(this).removeClass("is-dragging");
			STATE.dragKey = null;
		});
		$cards.on("dragover", ".gcfq-dash-card", function (e) {
			e.preventDefault();
			var key = STATE.dragKey;
			var $target = $(this);
			if (!key || $target.attr("data-key") === key) {
				return;
			}
			var $drag = $cards.find('.gcfq-dash-card[data-key="' + key + '"]');
			if (!$drag.length) {
				return;
			}
			var cards = $cards.children(".gcfq-dash-card").toArray();
			var dragEl = $drag.get(0);
			var targetEl = $target.get(0);
			var dragIdx = cards.indexOf(dragEl);
			var targetIdx = cards.indexOf(targetEl);
			if (dragIdx < 0 || targetIdx < 0) {
				return;
			}
			if (dragIdx < targetIdx) {
				$target.after($drag);
			} else {
				$target.before($drag);
			}
			resequence_cards($cards);
			sync_workspace_from_dom($wrap);
		});
	}

	function open_add_filters($wrap) {
		var ws = STATE.workspace;
		if (!ws) {
			return;
		}
		var present = {};
		(ws.filters || []).forEach(function (f) {
			present[f.key] = true;
		});
		frappe.call({
			method: "logistics.utils.get_charges_from_quotation.get_gcfq_catalog_keys_for_doctype",
			args: { doctype: ws.doctype },
			callback: function (r) {
				var keys = (r && r.message) || [];
				var missing = keys.filter(function (k) {
					return !present[k];
				});
				if (!missing.length) {
					frappe.show_alert({
						message: __("All catalog filters for this module are already in the workspace."),
						indicator: "blue",
					});
					return;
				}
				var d = new frappe.ui.Dialog({
					title: __("Add Filters"),
					fields: [
						{
							fieldname: "keys",
							fieldtype: "MultiCheck",
							label: __("Catalog filters"),
							options: missing.map(function (k) {
								return { label: k, value: k, checked: 0 };
							}),
						},
					],
					primary_action_label: __("Add"),
					primary_action: function () {
						var selected = d.get_values().keys || [];
						if (!Array.isArray(selected)) {
							selected = [];
						}
						selected.forEach(function (k) {
							if (!k || present[k]) {
								return;
							}
							ws.filters.push({
								key: k,
								label: k,
								enabled: true,
								editable: true,
							});
							present[k] = true;
						});
						STATE.dirty = true;
						d.hide();
						render_workspace($wrap);
					},
				});
				d.show();
			},
		});
	}

	function save_workspace($wrap) {
		if (!STATE.doctype) {
			return;
		}
		var filters = collect_filters($wrap);
		frappe.call({
			method: "logistics.utils.get_charges_from_quotation.save_gcfq_dashboard_workspace",
			args: {
				doctype: STATE.doctype,
				filters: filters,
			},
			freeze: true,
			freeze_message: __("Saving…"),
			callback: function (r) {
				STATE.workspace = (r && r.message) || STATE.workspace;
				STATE.dirty = false;
				frappe.show_alert({ message: __("Saved"), indicator: "green" });
				render_workspace($wrap);
				refresh_module_counts($wrap);
				if (cur_frm && cur_frm.doctype === "Get Charges from Quotation Settings") {
					cur_frm.reload_doc();
				}
			},
		});
	}

	function restore_defaults($wrap) {
		if (!STATE.doctype) {
			return;
		}
		frappe.confirm(
			__("Restore default filters for {0}? This overwrites the current layout for this module.", [
				STATE.doctype,
			]),
			function () {
				frappe.call({
					method: "logistics.utils.get_charges_from_quotation.restore_gcfq_dashboard_defaults",
					args: { doctype: STATE.doctype },
					freeze: true,
					callback: function (r) {
						STATE.workspace = (r && r.message) || STATE.workspace;
						STATE.dirty = false;
						frappe.show_alert({ message: __("Defaults restored"), indicator: "green" });
						render_workspace($wrap);
						refresh_module_counts($wrap);
						if (cur_frm && cur_frm.doctype === "Get Charges from Quotation Settings") {
							cur_frm.reload_doc();
						}
					},
				});
			}
		);
	}

	logistics.gcfq_dashboard.mount = mount;
})();
