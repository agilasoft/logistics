// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * ts_sq_fetch_dialog_v1 — free-edit Fetch dialog (Sales Quote ↔ Time Sensitive Case).
 * No mode cards. Every row is editable. Per-row direction + Fill/Add/Replace/Skip.
 *
 * Entry: logistics.show_ts_sq_fetch_dialog(frm, { direction })
 */

frappe.provide("logistics");

const TSFD1_API = "logistics.time_sensitive.ts_sq_fetch";

function _tsfd1_escape(text) {
	return frappe.utils.escape_html(text == null ? "" : String(text));
}

function _tsfd1_icon(name, size) {
	if (frappe.utils && typeof frappe.utils.icon === "function") {
		try {
			return frappe.utils.icon(name, size || "sm");
		} catch (e) {
			/* fall through */
		}
	}
	return "";
}

function _tsfd1_shell_html(title, direction_label, fetch_all_label) {
	return `
		<div class="tsfd1-root">
			<div class="tsfd1-header">
				<div class="tsfd1-header-left">
					<div class="tsfd1-icon" aria-hidden="true">
						${_tsfd1_icon("change", "sm") || _tsfd1_icon("refresh", "sm") || "⇄"}
					</div>
					<div>
						<h3 class="tsfd1-title">${_tsfd1_escape(title)}</h3>
						<p class="tsfd1-direction tsfd1-direction-label">${_tsfd1_escape(direction_label)}</p>
					</div>
				</div>
				<button type="button" class="tsfd1-close tsfd1-dialog-close" aria-label="${__("Close")}">
					${_tsfd1_icon("close", "sm") || "×"}
				</button>
			</div>

			<div class="tsfd1-body">
				<div class="tsfd1-fields-panel"></div>
				<div class="tsfd1-charges-panel"></div>

				<div class="tsfd1-summary-row">
					<div class="tsfd1-summary">
						<div class="tsfd1-summary-left">
							<span class="tsfd1-summary-icon">${_tsfd1_icon("info", "sm")}</span>
							<span class="tsfd1-summary-text"></span>
						</div>
						<span class="tsfd1-safe-badge"></span>
					</div>
				</div>
			</div>

			<div class="tsfd1-footer">
				<div class="tsfd1-footer-right tsfd1-footer-only">
					<button type="button" class="tsfd1-btn tsfd1-btn-secondary tsfd1-fetch-all" title="${_tsfd1_escape(
						fetch_all_label
					)}">
						${__("Fetch all")}
					</button>
					<button type="button" class="tsfd1-btn tsfd1-btn-primary tsfd1-apply" disabled>
						${__("Apply Fetch")}
					</button>
				</div>
			</div>
		</div>`;
}

function _tsfd1_empty_label(text) {
	return `<span class="tsfd1-empty-cell">${_tsfd1_escape(text || __("(empty)"))}</span>`;
}

function _tsfd1_field_input(row) {
	const val = row.working_value || "";
	const ft = row.fieldtype || "Data";
	const key = _tsfd1_escape(row.key);

	if (ft === "Link" && row.options) {
		return `<div class="tsfd1-control-host tsfd1-link-host"
			data-key="${key}"
			data-fieldtype="Link"
			data-options="${_tsfd1_escape(row.options)}"
			data-value="${_tsfd1_escape(val)}"></div>`;
	}

	if (ft === "Select" && row.options) {
		const opts = String(row.options)
			.split("\n")
			.filter(Boolean)
			.map((o) => {
				const sel = o === val ? "selected" : "";
				return `<option value="${_tsfd1_escape(o)}" ${sel}>${_tsfd1_escape(o)}</option>`;
			})
			.join("");
		return `<select class="tsfd1-input tsfd1-select tsfd1-field-value" data-key="${key}">
			<option value="">${__("—")}</option>
			${opts}
		</select>`;
	}

	if (ft === "Small Text") {
		return `<textarea class="tsfd1-input tsfd1-field-value" rows="2" data-key="${key}">${_tsfd1_escape(
			val
		)}</textarea>`;
	}

	return `<input type="text" class="tsfd1-input tsfd1-field-value" data-key="${key}" value="${_tsfd1_escape(
		val
	)}" />`;
}

function _tsfd1_action_menu(row, kind) {
	const action = row.action || "skip";
	const labels = {
		fill: __("Fill"),
		add: __("Add"),
		replace: __("Replace"),
		skip: __("Skip"),
	};
	const label = labels[action] || __("Skip");
	const tone =
		action === "fill" || action === "add"
			? "is-primary"
			: action === "replace"
			? "is-warn"
			: "is-skip";
	const reason = row.reason
		? `<span class="tsfd1-reason">${_tsfd1_escape(row.reason)}</span>`
		: "";

	const options =
		kind === "charge"
			? [
					["add", __("Add")],
					["skip", __("Skip")],
			  ]
			: [
					["fill", __("Fill")],
					["replace", __("Replace")],
					["skip", __("Skip")],
			  ];

	const menu = options
		.map(
			([val, text]) =>
				`<button type="button" class="tsfd1-menu-item" data-act="${val}">${_tsfd1_escape(
					text
				)}</button>`
		)
		.join("");

	return `
		<div class="tsfd1-action-cell">
			<div class="tsfd1-action-dd">
				<button type="button" class="tsfd1-action-btn ${tone} tsfd1-action-toggle">
					<span>${_tsfd1_escape(label)}</span>
					<span class="tsfd1-caret">▾</span>
				</button>
				<div class="tsfd1-menu">${menu}</div>
			</div>
			${reason}
		</div>`;
}

function _tsfd1_render_fields(payload) {
	const rows = payload.fields || [];
	if (!rows.length) {
		return `
			<section class="tsfd1-panel">
				<div class="tsfd1-panel-head">
					<span class="tsfd1-panel-title">${__("Header Fields")}</span>
				</div>
				<div class="tsfd1-empty">${__("No mappable header fields.")}</div>
			</section>`;
	}

	const body = rows
		.map((row) => {
			const checked = row.selected ? "checked" : "";
			const quote_cell = row.quote_empty
				? _tsfd1_empty_label(__("(empty)"))
				: _tsfd1_escape(row.quote_display || row.quote_value || "");
			return `
				<tr data-kind="field" data-key="${_tsfd1_escape(row.key)}">
					<td class="tsfd1-check">
						<input type="checkbox" class="tsfd1-row-check" ${checked}
							data-kind="field" data-key="${_tsfd1_escape(row.key)}" />
					</td>
					<td><span class="tsfd1-field-name">${_tsfd1_escape(row.label)}</span></td>
					<td class="tsfd1-src-cell">${quote_cell}</td>
					<td class="tsfd1-edit-cell">${_tsfd1_field_input(row)}</td>
					<td class="tsfd1-act-cell">${_tsfd1_action_menu(row, "field")}</td>
				</tr>`;
		})
		.join("");

	return `
		<section class="tsfd1-panel">
			<div class="tsfd1-panel-head">
				<span class="tsfd1-panel-title">${__("Header Fields")}
					<span class="tsfd1-count-bubble">${rows.length}</span>
				</span>
			</div>
			<div class="tsfd1-table-wrap">
				<table class="tsfd1-table">
					<thead>
						<tr>
							<th class="tsfd1-check"></th>
							<th>${__("Field")}</th>
							<th>${__("From Sales Quote")}</th>
							<th>${__("In Time Sensitive Case")} <span class="tsfd1-th-hint">(${__(
								"editable"
							)})</span></th>
							<th>${__("Action")}</th>
						</tr>
					</thead>
					<tbody>${body}</tbody>
				</table>
			</div>
		</section>`;
}

function _tsfd1_render_charges(payload) {
	const rows = payload.charges || [];
	const replace_all = !!payload.replace_all_charges;

	let body = "";
	if (!rows.length) {
		body = `<tr><td colspan="5"><div class="tsfd1-empty">${__(
			"No charges on the source document."
		)}</div></td></tr>`;
	} else {
		body = rows
			.map((row) => {
				const checked = row.selected ? "checked" : "";
				const quote_cell = row.on_quote
					? `<div class="tsfd1-charge-src">
							<div>${_tsfd1_escape(row.quote_display)}</div>
							${
								row.quote_amount_display
									? `<div class="tsfd1-amount-line">${__("Amount")}: ${_tsfd1_escape(
											row.quote_amount_display
									  )}</div>`
									: ""
							}
					  </div>`
					: _tsfd1_empty_label(__("(not on quote)"));

				const amount_txt =
					typeof format_currency === "function"
						? format_currency(flt(row.qty) * flt(row.rate), row.currency)
						: (flt(row.qty) * flt(row.rate)).toFixed(2);

				const editors = row.matched
					? `<span class="tsfd1-static">${_tsfd1_escape(row.case_display || row.quote_display)}</span>`
					: `<div class="tsfd1-qty-rate">
							<input type="number" step="any" class="tsfd1-input tsfd1-charge-qty"
								data-row-id="${_tsfd1_escape(row.row_id)}" value="${_tsfd1_escape(row.qty)}" />
							<span>×</span>
							<input type="number" step="any" class="tsfd1-input tsfd1-charge-rate"
								data-row-id="${_tsfd1_escape(row.row_id)}" value="${_tsfd1_escape(row.rate)}" />
							<span class="tsfd1-amount-inline">${__("Amount")}: ${_tsfd1_escape(amount_txt)}</span>
						</div>`;

				return `
					<tr data-kind="charge" data-row-id="${_tsfd1_escape(row.row_id)}">
						<td class="tsfd1-check">
							<input type="checkbox" class="tsfd1-row-check" ${checked}
								data-kind="charge" data-row-id="${_tsfd1_escape(row.row_id)}" />
						</td>
						<td><span class="tsfd1-charge-name">${_tsfd1_escape(row.label)}</span></td>
						<td class="tsfd1-src-cell">${quote_cell}</td>
						<td class="tsfd1-edit-cell">${editors}</td>
						<td class="tsfd1-act-cell">${_tsfd1_action_menu(row, "charge")}</td>
					</tr>`;
			})
			.join("");
	}

	return `
		<section class="tsfd1-panel">
			<div class="tsfd1-panel-head">
				<span class="tsfd1-panel-title">${__("Charges")}
					<span class="tsfd1-count-bubble">${rows.length} ${__("lines")}</span>
				</span>
			</div>
			<div class="tsfd1-table-wrap">
				<table class="tsfd1-table">
					<thead>
						<tr>
							<th class="tsfd1-check"></th>
							<th>${__("Charge")}</th>
							<th>${__("From Sales Quote")}</th>
							<th>${__("In Time Sensitive Case")} <span class="tsfd1-th-hint">(${__(
								"editable"
							)})</span></th>
							<th>${__("Action")}</th>
						</tr>
					</thead>
					<tbody>${body}</tbody>
				</table>
			</div>
			<div class="tsfd1-replace-all ${replace_all ? "is-on" : ""}">
				<button type="button" class="tsfd1-replace-all-btn">
					${_tsfd1_icon("refresh", "sm") || "↻"}
					<span>${__("Replace all charges from quote")}</span>
				</button>
				<div class="tsfd1-replace-all-hint">${__(
					"This will replace all charges in the case with those from the quote."
				)}</div>
			</div>
		</section>`;
}

function _tsfd1_get_state(dialog) {
	return dialog._tsfd1_state;
}

function _tsfd1_find_field(state, key) {
	return (state.fields || []).find((f) => f.key === key);
}

function _tsfd1_find_charge(state, row_id) {
	return (state.charges || []).find((c) => c.row_id === row_id);
}

function _tsfd1_source_for_field(row, default_direction) {
	const dir = default_direction || row.direction || "from_quote";
	if (dir === "to_quote") return row.case_value || "";
	return row.quote_value || "";
}

/**
 * Select every transferable row for the dialog's default direction.
 * Case form → from_quote; Quote form → to_quote.
 */
function _tsfd1_select_all(state) {
	const dir = state.default_direction || "from_quote";
	state.replace_all_charges = false;

	(state.fields || []).forEach((row) => {
		row.direction = dir;
		row.same = false;
		const src = dir === "from_quote" ? row.quote_value : row.case_value;
		const tgt = dir === "from_quote" ? row.case_value : row.quote_value;
		if (!src) {
			row.action = "skip";
			row.selected = false;
			row.reason = __("No source value");
			return;
		}
		row.working_value = src;
		row.reason = "";
		if (tgt && String(tgt) === String(src)) {
			row.action = "skip";
			row.selected = false;
			row.reason = __("Already same");
			row.same = true;
			return;
		}
		if (tgt && String(tgt) !== String(src)) {
			row.action = "replace";
			row.selected = true;
		} else {
			row.action = "fill";
			row.selected = true;
		}
	});

	(state.charges || []).forEach((row) => {
		if (dir === "from_quote" && !row.on_quote) {
			row.action = "skip";
			row.selected = false;
			row.reason = __("Not on quote");
			return;
		}
		if (dir === "to_quote" && !row.on_case && !row.case_row_name) {
			row.action = "skip";
			row.selected = false;
			row.reason = __("Not on case");
			return;
		}
		if (row.matched) {
			row.action = "skip";
			row.selected = false;
			row.reason = __("Already same");
			return;
		}
		row.direction = dir;
		row.action = "add";
		row.selected = true;
		row.reason = "";
	});
}

function _tsfd1_apply_field_action(row, act, default_direction) {
	row.action = act;
	if (act === "skip") {
		row.selected = false;
		row.reason = row.same ? __("Already same") : "";
		return;
	}
	row.selected = true;
	row.reason = "";
	if (act === "fill" || act === "replace") {
		const src = _tsfd1_source_for_field(row, default_direction);
		if (src) row.working_value = src;
	}
}

function _tsfd1_apply_charge_action(row, act) {
	row.action = act;
	if (act === "skip") {
		row.selected = false;
		return;
	}
	row.selected = true;
	row.reason = "";
}

function _tsfd1_update_summary($root, state) {
	const fields = (state.fields || []).filter((f) => f.selected && f.action !== "skip");
	const charges = (state.charges || []).filter((c) => c.selected && c.action !== "skip");
	const replace_all = !!state.replace_all_charges;
	const in_sync = !fields.length && !charges.length && !replace_all;
	const has_overwrite =
		replace_all || fields.some((f) => f.action === "replace");

	const $summary = $root.find(".tsfd1-summary");
	$summary.removeClass("is-sync is-warn");
	let text = "";
	if (in_sync) {
		$summary.addClass("is-sync");
		text = __("Already in sync — nothing to copy.");
	} else if (replace_all) {
		$summary.addClass("is-warn");
		text = __("Summary: {0} fields, all charges will be replaced from quote.", [
			fields.length,
		]);
	} else {
		text = __("Summary: {0} fields, {1} charge will update in Time Sensitive Case.", [
			fields.length,
			charges.length,
		]);
		if (charges.length !== 1) {
			text = __("Summary: {0} fields, {1} charges will update in Time Sensitive Case.", [
				fields.length,
				charges.length,
			]);
		}
	}
	$root.find(".tsfd1-summary-text").text(text);

	const $safe = $root.find(".tsfd1-safe-badge");
	if (in_sync) {
		$safe.removeClass("is-warn").addClass("is-safe").html("✓ " + __("Nothing to apply"));
	} else if (has_overwrite) {
		$safe.removeClass("is-safe").addClass("is-warn").html(__("Overwrite selected"));
	} else {
		$safe
			.removeClass("is-warn")
			.addClass("is-safe")
			.html("✓ " + __("Safe to apply. No existing data will be lost."));
	}

	$root.find(".tsfd1-apply").prop("disabled", in_sync);
}

function _tsfd1_mount_link_controls(dialog) {
	const state = _tsfd1_get_state(dialog);
	const $root = dialog.$wrapper.find(".tsfd1-root");
	const dir = state.default_direction || "from_quote";

	$root.find(".tsfd1-link-host").each(function () {
		const $host = $(this);
		const key = $host.attr("data-key");
		const options = $host.attr("data-options");
		const row = _tsfd1_find_field(state, key);
		if (!row) return;

		$host.empty();
		const control = frappe.ui.form.make_control({
			parent: $host.get(0),
			df: {
				fieldtype: "Link",
				options: options,
				fieldname: `tsfd1_${key}`,
				label: "",
				reqd: 0,
			},
			render_input: true,
			only_input: true,
		});
		control.refresh();
		if (row.working_value) {
			control.set_value(row.working_value);
		}

		const sync = () => {
			const val = control.get_value();
			row.working_value = val || "";
			if (!row.selected && row.working_value) {
				row.selected = true;
				const tgt = dir === "from_quote" ? row.case_value : row.quote_value;
				row.action =
					tgt && String(tgt) !== String(row.working_value) ? "replace" : "fill";
				$root
					.find(`tr[data-key="${key}"] .tsfd1-row-check`)
					.prop("checked", true);
			}
			_tsfd1_update_summary($root, state);
		};

		control.$input.on("change", sync);
		control.$input.on("awesomplete-selectcomplete", sync);
		$host.data("control", control);
	});
}

function _tsfd1_rerender(dialog) {
	const state = _tsfd1_get_state(dialog);
	const $root = dialog.$wrapper.find(".tsfd1-root");
	$root.find(".tsfd1-title").text(state.title || __("Fetch"));
	$root.find(".tsfd1-direction-label").text(state.direction_label || "");
	$root.find(".tsfd1-fields-panel").html(_tsfd1_render_fields(state));
	$root.find(".tsfd1-charges-panel").html(_tsfd1_render_charges(state));
	_tsfd1_mount_link_controls(dialog);
	_tsfd1_update_summary($root, state);
}

function _tsfd1_collect_payload(dialog) {
	const state = _tsfd1_get_state(dialog);
	const $root = dialog.$wrapper.find(".tsfd1-root");
	const dir = state.default_direction || "from_quote";

	$root.find(".tsfd1-field-value").each(function () {
		const row = _tsfd1_find_field(state, $(this).data("key"));
		if (row) row.working_value = $(this).val();
	});
	$root.find(".tsfd1-link-host").each(function () {
		const key = $(this).attr("data-key");
		const row = _tsfd1_find_field(state, key);
		const control = $(this).data("control");
		if (row && control) {
			row.working_value = control.get_value() || "";
		}
	});
	$root.find(".tsfd1-charge-qty").each(function () {
		const row = _tsfd1_find_charge(state, $(this).data("row-id"));
		if (row) row.qty = flt($(this).val());
	});
	$root.find(".tsfd1-charge-rate").each(function () {
		const row = _tsfd1_find_charge(state, $(this).data("row-id"));
		if (row) row.rate = flt($(this).val());
	});

	const field_rows = (state.fields || [])
		.filter((f) => f.selected && f.action !== "skip")
		.map((f) => ({
			key: f.key,
			direction: dir,
			action: f.action,
			selected: true,
			value: f.working_value,
		}));

	const charge_rows = state.replace_all_charges
		? []
		: (state.charges || [])
				.filter((c) => c.selected && c.action !== "skip")
				.map((c) => ({
					row_id: c.row_id,
					quote_row_name: c.quote_row_name,
					case_row_name: c.case_row_name,
					direction: dir,
					action: c.action,
					selected: true,
					qty: c.qty,
					rate: c.rate,
					item_code: c.item_code,
					description: c.description,
					currency: c.currency,
					service_type: c.service_type,
					charge_scope: c.charge_scope,
					linked_service: c.linked_service,
				}));

	return {
		field_rows,
		charge_rows,
		replace_all_charges: state.replace_all_charges ? 1 : 0,
	};
}

function _tsfd1_load(dialog, opts) {
	frappe.call({
		method: `${TSFD1_API}.preview_fetch`,
		args: {
			direction: opts.direction,
			source_name: opts.source_name,
			target_name: opts.target_name,
		},
		freeze: true,
		freeze_message: __("Loading fetch preview..."),
		callback(r) {
			if (!r.message) return;
			dialog._tsfd1_state = r.message;
			dialog._tsfd1_state.replace_all_charges = false;
			_tsfd1_rerender(dialog);
		},
	});
}

function _tsfd1_bind(dialog, frm, opts) {
	const $wrap = dialog.$wrapper;

	$wrap.off("click.tsfd1 change.tsfd1 input.tsfd1");
	$wrap.on("click.tsfd1", ".tsfd1-dialog-close", () => dialog.hide());

	$wrap.on("click.tsfd1", ".tsfd1-action-toggle", function (e) {
		e.preventDefault();
		e.stopPropagation();
		const $dd = $(this).closest(".tsfd1-action-dd");
		$wrap.find(".tsfd1-action-dd.is-open").not($dd).removeClass("is-open");
		$dd.toggleClass("is-open");
	});

	$wrap.on("click.tsfd1", function (e) {
		if (!$(e.target).closest(".tsfd1-action-dd").length) {
			$wrap.find(".tsfd1-action-dd.is-open").removeClass("is-open");
		}
	});

	$wrap.on("click.tsfd1", ".tsfd1-menu-item", function (e) {
		e.preventDefault();
		const state = _tsfd1_get_state(dialog);
		const act = $(this).data("act");
		const $tr = $(this).closest("tr");
		if ($tr.data("kind") === "field") {
			const row = _tsfd1_find_field(state, $tr.data("key"));
			if (row) _tsfd1_apply_field_action(row, act, state.default_direction);
		} else {
			const row = _tsfd1_find_charge(state, $tr.data("row-id"));
			if (row) _tsfd1_apply_charge_action(row, act);
		}
		_tsfd1_rerender(dialog);
	});

	$wrap.on("change.tsfd1", ".tsfd1-row-check", function () {
		const state = _tsfd1_get_state(dialog);
		const $el = $(this);
		const checked = $el.is(":checked");
		const dir = state.default_direction || "from_quote";
		if ($el.data("kind") === "field") {
			const row = _tsfd1_find_field(state, $el.data("key"));
			if (!row) return;
			row.selected = checked;
			if (checked && row.action === "skip") {
				const src = _tsfd1_source_for_field(row, dir);
				const tgt = dir === "from_quote" ? row.case_value : row.quote_value;
				row.action = tgt && src && String(tgt) !== String(src) ? "replace" : "fill";
				if (src) row.working_value = src;
			}
			if (!checked) row.action = "skip";
		} else {
			const row = _tsfd1_find_charge(state, $el.data("row-id"));
			if (!row) return;
			row.selected = checked;
			row.action = checked ? "add" : "skip";
		}
		_tsfd1_rerender(dialog);
	});

	$wrap.on("change.tsfd1 input.tsfd1", ".tsfd1-field-value", function () {
		const state = _tsfd1_get_state(dialog);
		const row = _tsfd1_find_field(state, $(this).data("key"));
		if (!row) return;
		row.working_value = $(this).val();
		if (!row.selected) {
			row.selected = true;
			row.action =
				row.case_value && row.working_value !== row.case_value ? "replace" : "fill";
		}
		_tsfd1_update_summary($wrap.find(".tsfd1-root"), state);
		$wrap
			.find(`tr[data-key="${row.key}"] .tsfd1-row-check`)
			.prop("checked", !!row.selected);
	});

	$wrap.on("change.tsfd1 input.tsfd1", ".tsfd1-charge-qty, .tsfd1-charge-rate", function () {
		const state = _tsfd1_get_state(dialog);
		const row = _tsfd1_find_charge(state, $(this).data("row-id"));
		if (!row) return;
		if ($(this).hasClass("tsfd1-charge-qty")) row.qty = flt($(this).val());
		else row.rate = flt($(this).val());
		row.amount = flt(row.qty) * flt(row.rate);
		if (!row.selected) {
			row.selected = true;
			row.action = "add";
		}
		_tsfd1_update_summary($wrap.find(".tsfd1-root"), state);
	});

	$wrap.on("click.tsfd1", ".tsfd1-replace-all-btn", function () {
		const state = _tsfd1_get_state(dialog);
		state.replace_all_charges = !state.replace_all_charges;
		if (state.replace_all_charges) {
			(state.charges || []).forEach((c) => {
				c.selected = false;
				c.action = "skip";
			});
		}
		_tsfd1_rerender(dialog);
	});

	function run_apply(field_rows, charge_rows, replace_all_charges) {
		frappe.call({
			method: `${TSFD1_API}.apply_fetch`,
			args: {
				direction: opts.direction,
				source_name: opts.source_name,
				target_name: opts.target_name,
				field_rows: JSON.stringify(field_rows),
				charge_rows: JSON.stringify(charge_rows),
				replace_all_charges,
			},
			freeze: true,
			freeze_message: __("Applying fetch..."),
			callback(r) {
				dialog.hide();
				const msg = (r.message && r.message.message) || __("Fetch applied.");
				frappe.show_alert({ message: msg, indicator: "green" });
				frm.reload_doc();
			},
		});
	}

	$wrap.on("click.tsfd1", ".tsfd1-fetch-all", function () {
		const state = _tsfd1_get_state(dialog);
		_tsfd1_select_all(state);
		_tsfd1_rerender(dialog);

		const { field_rows, charge_rows, replace_all_charges } = _tsfd1_collect_payload(dialog);
		const n_fields = field_rows.length;
		const n_charges = charge_rows.length;
		if (!n_fields && !n_charges && !replace_all_charges) {
			frappe.show_alert({
				message: __("Already in sync — nothing to fetch."),
				indicator: "blue",
			});
			return;
		}

		const from_quote = (state.default_direction || "from_quote") === "from_quote";
		const msg = from_quote
			? __(
					"Fetch all {0} fields and {1} charges from Sales Quote into this case?",
					[n_fields, n_charges]
			  )
			: __(
					"Fetch all {0} fields and {1} charges from Time Sensitive Case into this quote?",
					[n_fields, n_charges]
			  );

		frappe.confirm(msg, () => run_apply(field_rows, charge_rows, replace_all_charges));
	});

	$wrap.on("click.tsfd1", ".tsfd1-apply", function () {
		if ($(this).prop("disabled")) return;
		const { field_rows, charge_rows, replace_all_charges } = _tsfd1_collect_payload(dialog);

		if (replace_all_charges || field_rows.some((f) => f.action === "replace")) {
			frappe.confirm(__("Some existing values will be overwritten. Continue?"), () =>
				run_apply(field_rows, charge_rows, replace_all_charges)
			);
			return;
		}
		run_apply(field_rows, charge_rows, replace_all_charges);
	});
}

logistics.show_ts_sq_fetch_dialog = function (frm, options) {
	const opts = options || {};
	if (!opts.direction) {
		frappe.msgprint({
			message: __("Fetch dialog is not configured."),
			indicator: "orange",
		});
		return;
	}
	if (!frm || !frm.doc || !frm.doc.name || frm.is_new()) {
		frappe.msgprint({
			message: __("Save the document before fetching."),
			indicator: "orange",
		});
		return;
	}

	if (opts.direction === "quote_to_case") {
		opts.target_name = opts.target_name || frm.doc.name;
		opts.source_name = opts.source_name || frm.doc.sales_quote;
		if (!opts.source_name) {
			frappe.msgprint({
				message: __("Link a Sales Quote on this case before fetching."),
				indicator: "orange",
			});
			return;
		}
	} else if (opts.direction === "case_to_quote") {
		opts.target_name = opts.target_name || frm.doc.name;
		opts.source_name = opts.source_name || frm.doc.time_sensitive_case;
		if (!opts.source_name) {
			frappe.msgprint({
				message: __("Link a Time Sensitive Case on this quote before fetching."),
				indicator: "orange",
			});
			return;
		}
	}

	const title =
		opts.direction === "case_to_quote"
			? __("Fetch from Time Sensitive Case")
			: __("Fetch from Sales Quote");
	const direction_label =
		opts.direction === "case_to_quote"
			? `${opts.source_name} → ${opts.target_name}`
			: `${opts.source_name} → ${opts.target_name}`;
	const fetch_all_label =
		opts.direction === "case_to_quote"
			? __("Fetch all fields and charges from Time Sensitive Case")
			: __("Fetch all fields and charges from Sales Quote");

	const dialog = new frappe.ui.Dialog({
		title,
		size: "extra-large",
		static: false,
		fields: [
			{
				fieldname: "body_html",
				fieldtype: "HTML",
				options: _tsfd1_shell_html(title, direction_label, fetch_all_label),
			},
		],
	});

	dialog.$wrapper.find(".modal-dialog").addClass("tsfd1-dialog");
	dialog.show();
	_tsfd1_bind(dialog, frm, opts);
	_tsfd1_load(dialog, opts);
};
