// Copyright (c) 2026, www.agilasoft.com and contributors
// For license information, please see license.txt

/**
 * Shared Manage Linked Services dialog (linked_services_dialog_1).
 * Entry: logistics.show_linked_services_dialog(frm, options)
 *
 * List + add/remove, with optional in-dialog edit panel for Linked Service fields.
 */

frappe.provide("logistics");

const LSD1_DEFAULT_SERVICE_TYPES = [
	"Air",
	"Sea",
	"Transport",
	"Customs",
	"Warehousing",
	"Cross-Docking",
	"On-Demand Last Mile",
	"Special Project",
	"MICE",
];

/** Map service type → Desktop Icon / workspace module label (SVG under desktop_icons). */
const LSD1_MODULE_BY_TYPE = {
	Air: "Air Freight",
	Sea: "Sea Freight",
	Transport: "Transport",
	Customs: "Customs",
	Warehousing: "Warehousing",
	"Cross-Docking": "Warehousing",
	"On-Demand Last Mile": "Transport",
	"Special Project": "Special Projects",
	MICE: "MICE",
};

const LSD1_LS_API = "logistics.logistics.doctype.linked_service.linked_service";

function _lsd1_escape(text) {
	return frappe.utils.escape_html(text == null ? "" : String(text));
}

function _lsd1_icon(name, size) {
	if (frappe.utils && typeof frappe.utils.icon === "function") {
		try {
			return frappe.utils.icon(name, size || "sm");
		} catch (e) {
			/* fall through */
		}
	}
	return "";
}

function _lsd1_module_label(service_type) {
	return LSD1_MODULE_BY_TYPE[service_type] || service_type || "";
}

/** Official logistics module SVG from public/icons/desktop_icons/. */
function _lsd1_module_icon_html(service_type) {
	const label = _lsd1_module_label(service_type);
	if (!label) return "";

	let url = "";
	if (frappe.utils && typeof frappe.utils.get_desktop_icon === "function") {
		url = frappe.utils.get_desktop_icon(label, "subtle") || "";
	}
	if (!url) {
		const scrubbed = frappe.scrub
			? frappe.scrub(label)
			: String(label).toLowerCase().replace(/\s+/g, "_");
		url = `/assets/logistics/icons/desktop_icons/subtle/${scrubbed}.svg`;
	}

	return `<img class="lsd1-module-icon" src="${_lsd1_escape(
		url
	)}" alt="${_lsd1_escape(label)}" width="28" height="28" draggable="false" />`;
}

function _lsd1_normalize_options(options) {
	const opts = options || {};
	return {
		listMethod: opts.listMethod,
		addMethod: opts.addMethod,
		removeMethod: opts.removeMethod,
		getMethod: opts.getMethod || LSD1_LS_API + ".get_dialog_edit_payload",
		updateMethod: opts.updateMethod || LSD1_LS_API + ".update_dialog_edit",
		parentField: opts.parentField || "name",
		parentLabel: opts.parentLabel || __("Document"),
		emptyHint:
			opts.emptyHint ||
			__("Add a service type above to link it to this document."),
		addHint:
			opts.addHint ||
			__(
				"Choose a service type and quantity, fill in the service details, then Add Service. Qty is stored on that one service."
			),
		createPayloadMethod:
			opts.createPayloadMethod || LSD1_LS_API + ".get_dialog_create_payload",
		unsavedMessage:
			opts.unsavedMessage ||
			__("Save the document before managing services."),
		removeConfirm:
			opts.removeConfirm ||
			((ls) =>
				__("Remove linked service {0} from this document?", [
					`<strong>${_lsd1_escape(ls)}</strong>`,
				])),
		serviceTypes: opts.serviceTypes || LSD1_DEFAULT_SERVICE_TYPES,
		allowAdd: opts.allowAdd !== false,
		allowRemove: opts.allowRemove !== false,
		allowEdit: opts.allowEdit !== false,
		previewMethod: opts.previewMethod || null,
		createMethod: opts.createMethod || null,
		allowGenerate: !!(
			opts.previewMethod &&
			opts.createMethod &&
			opts.allowAdd !== false
		),
	};
}

function _lsd1_parent_args(frm, opts) {
	const args = {};
	args[opts.parentField] = frm.doc.name;
	return args;
}

function _lsd1_parent_context(frm) {
	return {
		parent_doctype: frm.doctype,
		parent_name: frm.doc.name,
	};
}

function _lsd1_fetch(frm, opts, callback) {
	frappe.call({
		method: opts.listMethod,
		args: _lsd1_parent_args(frm, opts),
		callback(r) {
			callback((r && r.message) || { linked_services: [] });
		},
	});
}

function _lsd1_render_list(rows, opts, selected) {
	if (!rows || !rows.length) {
		return `
			<div class="lsd1-empty">
				<div class="lsd1-empty-icon">${_lsd1_icon("link", "md")}</div>
				<div class="lsd1-empty-title">${__("No linked services yet")}</div>
				<div class="lsd1-empty-hint">${_lsd1_escape(opts.emptyHint)}</div>
			</div>`;
	}

	return rows
		.map((row) => {
			const ls = row.linked_service || "";
			const st = row.service_type || "";
			const from_job =
				row.owned_by_change_request === 0 || row.owned_by_change_request === "0";
			const job_html = row.job_no
				? `<span class="lsd1-pill lsd1-pill-job">${_lsd1_escape(row.job_no)}</span>`
				: row.order_no
				? `<span class="lsd1-pill lsd1-pill-job">${_lsd1_escape(row.order_no)}</span>`
				: `<span class="lsd1-pill">${__("No Job")}</span>`;
			const company_html = row.company
				? `<span class="lsd1-pill">${_lsd1_escape(row.company)}</span>`
				: "";
			const qty_html = `<span class="lsd1-pill">${__("Qty {0}", [
				cint(row.quantity) || 1,
			])}</span>`;
			const source_html = from_job
				? `<span class="lsd1-pill">${__("From job")}</span>`
				: "";

			const edit_btn =
				opts.allowEdit && opts.getMethod && !from_job
					? `<button type="button" class="lsd1-icon-btn lsd1-edit" title="${__(
							"Edit"
					  )}" aria-label="${__("Edit")}">
						${_lsd1_icon("edit", "sm") || _lsd1_icon("pencil", "sm") || "✎"}
					</button>`
					: "";

			const remove_btn = opts.allowRemove
				? `<button type="button" class="lsd1-icon-btn lsd1-remove" title="${__(
						"Remove"
				  )}" aria-label="${__("Remove")}">
						${_lsd1_icon("trash", "sm") || _lsd1_icon("delete", "sm")}
					</button>`
				: "";

			const selected_cls = selected && selected === ls ? " is-selected" : "";

			return `
				<div class="lsd1-item${selected_cls}" data-linked-service="${_lsd1_escape(
					ls
				)}" data-service-type="${_lsd1_escape(st)}">
					<div class="lsd1-item-icon">${_lsd1_module_icon_html(st)}</div>
					<div class="lsd1-item-main">
						<div class="lsd1-type-label">${_lsd1_escape(st)}</div>
						<a href="#" class="lsd1-doc-link lsd1-open">
							<span class="lsd1-doc-id">${_lsd1_escape(ls)}</span>
							${_lsd1_icon("es-line-open", "xs") || _lsd1_icon("external-link", "xs")}
						</a>
					</div>
					<div class="lsd1-item-meta">${source_html}${qty_html}${company_html}${job_html}</div>
					<div class="lsd1-item-actions">${edit_btn}${remove_btn}</div>
				</div>`;
		})
		.join("");
}

function _lsd1_shell_html(frm, opts) {
	const options = [`<option value="">${__("Select a service type")}</option>`]
		.concat(
			(opts.serviceTypes || []).map(
				(t) => `<option value="${_lsd1_escape(t)}">${_lsd1_escape(t)}</option>`
			)
		)
		.join("");

	const generate_btn = opts.allowGenerate
		? `
						<button type="button" class="lsd1-add-btn lsd1-generate-open">
							${_lsd1_icon("add", "xs") || "+"}
							<span>${__("Generate from main")}</span>
						</button>`
		: "";

	const add_panel = opts.allowAdd
		? `
				<section class="lsd1-panel">
					<div class="lsd1-panel-head">
						<span class="lsd1-panel-title">${__("Add Linked Service")}</span>
					</div>
					<div class="lsd1-add-controls">
						<select class="lsd1-select lsd1-service-type" aria-label="${__(
							"Service Type"
						)}">${options}</select>
						<label class="lsd1-add-qty-wrap">
							<span>${__("Qty")}</span>
							<input type="number" class="lsd1-add-qty" min="1" max="50" step="1" value="1"
								aria-label="${__("Quantity")}">
						</label>
						<button type="button" class="lsd1-add-btn lsd1-add">
							${_lsd1_icon("add", "xs") || "+"}
							<span>${__("Add Service")}</span>
						</button>
						${generate_btn}
					</div>
					<p class="lsd1-hint">${_lsd1_escape(opts.addHint)}</p>
					${_lsd1_compose_panel_html()}
					${_lsd1_generate_panel_html(opts)}
				</section>`
		: "";

	const edit_panel =
		opts.allowEdit && opts.getMethod
			? `
				<section class="lsd1-panel lsd1-edit-panel" hidden>
					<div class="lsd1-edit-head">
						<div class="lsd1-edit-head-text">
							<span class="lsd1-panel-title">${__("Edit Linked Service")}</span>
							<span class="lsd1-edit-meta"></span>
						</div>
						<a href="#" class="lsd1-open-full">
							<span>${__("Open full form")}</span>
							${_lsd1_icon("es-line-open", "xs") || _lsd1_icon("external-link", "xs")}
						</a>
					</div>
					<div class="lsd1-edit-grid"></div>
					<div class="lsd1-edit-actions">
						<button type="button" class="lsd1-btn-secondary lsd1-edit-cancel">${__(
							"Cancel"
						)}</button>
						<button type="button" class="lsd1-btn-primary lsd1-edit-save">${__(
							"Save Changes"
						)}</button>
					</div>
				</section>`
			: "";

	return `
		<div class="lsd1-root">
			<div class="lsd1-header">
				<div class="lsd1-header-text">
					<h3 class="lsd1-title">${__("Manage Linked Services")}</h3>
					<p class="lsd1-subtitle">${_lsd1_escape(opts.parentLabel)} <span class="lsd1-case">${_lsd1_escape(
						frm.doc.name
					)}</span></p>
				</div>
				<button type="button" class="lsd1-close lsd1-dialog-close" aria-label="${__(
					"Close"
				)}">
					${_lsd1_icon("close", "sm") || "×"}
				</button>
			</div>

			<div class="lsd1-body">
				${add_panel}
				<section class="lsd1-panel">
					<div class="lsd1-panel-head">
						<span class="lsd1-panel-title">${__("Linked Services")}</span>
						<span class="lsd1-count-badge lsd1-count">0</span>
					</div>
					<div class="lsd1-list lsd1-services-list"></div>
				</section>
				${edit_panel}
			</div>
		</div>`;
}

function _lsd1_compose_panel_html() {
	return `
		<div class="lsd1-compose-panel" hidden>
			<div class="lsd1-edit-head">
				<div class="lsd1-edit-head-text">
					<span class="lsd1-panel-title">${__("Service details")}</span>
					<span class="lsd1-compose-meta"></span>
				</div>
			</div>
			<p class="lsd1-hint lsd1-compose-note">${__(
				"Qty is stored on this one service. Orders created for it cannot exceed that quantity."
			)}</p>
			<div class="lsd1-edit-grid lsd1-compose-grid"></div>
		</div>`;
}

function _lsd1_generate_panel_html(opts) {
	if (!opts.allowGenerate) return "";
	return `
		<div class="lsd1-generate-panel" hidden>
			<p class="lsd1-hint lsd1-generate-note">${__(
				"Each selected row creates one service. How many is stored as that service's quantity."
			)}</p>
			<div class="lsd1-generate-list"></div>
			<div class="lsd1-generate-actions">
				<button type="button" class="lsd1-btn-secondary lsd1-generate-cancel">${__(
					"Cancel"
				)}</button>
				<button type="button" class="lsd1-btn-primary lsd1-generate-create">${__(
					"Create selected"
				)}</button>
			</div>
		</div>`;
}

function _lsd1_render_generate_list(proposals) {
	if (!proposals.length) {
		return `<p class="lsd1-generate-empty">${__(
			"Fill main service parameters or container rows first."
		)}</p>`;
	}
	return proposals
		.map((proposal, index) => {
			const detail = proposal.detail
				? `<span class="lsd1-generate-detail">${_lsd1_escape(proposal.detail)}</span>`
				: "";
			const qty =
				proposal.key === "transport_container"
					? `<label class="lsd1-generate-qty-wrap">
						<span>${__("How many")}</span>
						<input type="number" class="lsd1-generate-qty" min="0" max="50" step="1"
							value="${cint(proposal.quantity) || 1}" data-index="${index}"
							aria-label="${__("How many")}">
					</label>`
					: "";
			return `
				<div class="lsd1-generate-row">
					<label class="lsd1-generate-check-wrap">
						<input type="checkbox" class="lsd1-generate-check" checked data-index="${index}">
						<span class="lsd1-generate-copy">
							<span class="lsd1-generate-label">${_lsd1_escape(proposal.label || "")}</span>
							${detail}
						</span>
					</label>
					${qty}
				</div>`;
		})
		.join("");
}

function _lsd1_close_generate(dialog) {
	const $panel = dialog.$wrapper.find(".lsd1-generate-panel");
	$panel.attr("hidden", true);
	$panel.find(".lsd1-generate-list").empty();
}

function _lsd1_open_generate(dialog, frm, opts, state) {
	const $panel = dialog.$wrapper.find(".lsd1-generate-panel");
	const $list = $panel.find(".lsd1-generate-list");
	frappe.call({
		method: opts.previewMethod,
		args: _lsd1_parent_args(frm, opts),
		freeze: true,
		freeze_message: __("Preparing linked services..."),
		callback(r) {
			const proposals = (r && r.message && r.message.proposals) || [];
			state.generateProposals = proposals;
			$list.html(_lsd1_render_generate_list(proposals));
			$panel.find(".lsd1-generate-create").prop("disabled", !proposals.length);
			$panel.removeAttr("hidden");
		},
	});
}

function _lsd1_create_generated(dialog, frm, opts, state) {
	const proposals = state.generateProposals || [];
	const $wrap = dialog.$wrapper;
	const selected = [];
	$wrap.find(".lsd1-generate-check:checked").each(function () {
		const index = cint($(this).attr("data-index"));
		const proposal = proposals[index];
		if (!proposal) return;
		let quantity = 1;
		if (proposal.key === "transport_container") {
			quantity = cint($wrap.find(`.lsd1-generate-qty[data-index="${index}"]`).val());
		}
		selected.push({
			key: proposal.key,
			container_row: proposal.container_row || null,
			quantity,
		});
	});
	if (!selected.length) {
		frappe.msgprint({
			message: __("Select at least one service to create."),
			indicator: "orange",
		});
		return;
	}

	const $create = $wrap.find(".lsd1-generate-create");
	$create.prop("disabled", true);
	frappe.call({
		method: opts.createMethod,
		args: Object.assign(_lsd1_parent_args(frm, opts), {
			proposals: selected,
		}),
		freeze: true,
		freeze_message: __("Creating linked services..."),
		callback(r) {
			$create.prop("disabled", false);
			const created =
				(r && r.message && r.message.linked_services) || [];
			_lsd1_close_generate(dialog);
			_lsd1_reload(dialog, frm, opts, state);
			frm.reload_doc();
			if (!created.length) {
				frappe.msgprint({
					message: __("No linked services were created."),
					indicator: "orange",
				});
				return;
			}
			frappe.show_alert({
				message:
					created.length === 1
						? __("Linked service created")
						: __("{0} linked services created", [created.length]),
				indicator: "green",
			});
			if (created.length === 1 && opts.allowEdit && opts.getMethod) {
				_lsd1_open_edit(dialog, frm, opts, state, created[0]);
			}
		},
		error() {
			$create.prop("disabled", false);
		},
	});
}

function _lsd1_update_counts($root, count) {
	$root.find(".lsd1-count").text(String(count));
}

function _lsd1_clear_edit_controls(state) {
	(state.editControls || []).forEach((ctrl) => {
		try {
			if (ctrl && typeof ctrl.$wrapper !== "undefined") {
				ctrl.$wrapper.remove();
			}
		} catch (e) {
			/* ignore */
		}
	});
	state.editControls = [];
	state.editValuesBaseline = null;
}

function _lsd1_close_edit(dialog, state) {
	const $root = dialog.$wrapper.find(".lsd1-root");
	_lsd1_clear_edit_controls(state);
	state.editing = null;
	$root.find(".lsd1-edit-panel").attr("hidden", true);
	$root.find(".lsd1-item").removeClass("is-selected");
}

function _lsd1_parse_link_filters(raw) {
	if (!raw) return null;
	if (Array.isArray(raw)) return raw;
	try {
		const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
		return Array.isArray(parsed) ? parsed : null;
	} catch (e) {
		return null;
	}
}

function _lsd1_mount_edit_field($grid, field, value, state) {
	const label = field.label || field.fieldname || "";
	const $cell = $(
		`<div class="lsd1-edit-field" data-fieldname="${_lsd1_escape(field.fieldname)}">
			<label class="lsd1-field-label" for="lsd1-${_lsd1_escape(field.fieldname)}">${_lsd1_escape(
			label
		)}</label>
			<div class="lsd1-field-input"></div>
		</div>`
	);
	$grid.append($cell);
	const $input = $cell.find(".lsd1-field-input");

	if (field.read_only) {
		const lock = _lsd1_icon("lock", "xs") || "";
		$input.html(`
			<div class="lsd1-readonly-wrap">
				<span class="lsd1-lock">${lock}</span>
				<input type="text" class="form-control" id="lsd1-${_lsd1_escape(
					field.fieldname
				)}" readonly tabindex="-1"
					value="${_lsd1_escape(value || "")}" aria-label="${_lsd1_escape(label)}" />
			</div>`);
		return {
			fieldname: field.fieldname,
			read_only: true,
			get_value: () => value || "",
		};
	}

	const df = {
		fieldname: field.fieldname,
		label: label,
		fieldtype: field.fieldtype || "Data",
		options: field.options || "",
		reqd: 0,
	};

	const filters = _lsd1_parse_link_filters(field.link_filters);
	if (filters && df.fieldtype === "Link") {
		df.get_query = () => ({ filters });
	}

	if (df.fieldtype === "Dynamic Link" && df.options) {
		const options_field = df.options;
		const controls = state._mountControls || state.editControls;
		df.get_options = function () {
			const sibling = (controls || []).find(
				(c) => c && c.fieldname === options_field
			);
			return (sibling && sibling.get_value && sibling.get_value()) || "UNLOCO";
		};
	}

	const ctrl = frappe.ui.form.make_control({
		df,
		parent: $input,
		render_input: true,
	});
	ctrl.refresh();
	if (value != null && value !== "") {
		ctrl.set_value(value);
	}

	return {
		fieldname: field.fieldname,
		read_only: false,
		control: ctrl,
		get_value: () => ctrl.get_value(),
	};
}

function _lsd1_collect_control_values(controls) {
	const values = {};
	(controls || []).forEach((c) => {
		if (!c || c.read_only) return;
		values[c.fieldname] = c.get_value();
	});
	return values;
}

function _lsd1_collect_edit_values(state) {
	return _lsd1_collect_control_values(state.editControls);
}

function _lsd1_edit_is_dirty(state) {
	if (!state.editValuesBaseline) return false;
	const current = _lsd1_collect_edit_values(state);
	return JSON.stringify(current) !== JSON.stringify(state.editValuesBaseline);
}

function _lsd1_clear_compose_controls(state) {
	(state.composeControls || []).forEach((ctrl) => {
		try {
			if (ctrl && ctrl.control && ctrl.control.$wrapper) {
				ctrl.control.$wrapper.remove();
			}
		} catch (e) {
			/* ignore */
		}
	});
	state.composeControls = [];
	state.composeDetailFields = [];
	state.composeServiceType = "";
	state.composeReady = false;
	state.composeRequest = (state.composeRequest || 0) + 1;
}

function _lsd1_close_compose(dialog, state) {
	_lsd1_clear_compose_controls(state);
	const $panel = dialog.$wrapper.find(".lsd1-compose-panel");
	$panel.attr("hidden", true);
	$panel.find(".lsd1-compose-grid").empty();
	$panel.find(".lsd1-compose-meta").text("");
}

function _lsd1_compose_has_details(state) {
	const required = state.composeDetailFields || [];
	if (!required.length) return true;
	const values = _lsd1_collect_control_values(state.composeControls);
	return required.some((name) => {
		const value = values[name];
		return value != null && String(value).trim() !== "";
	});
}

function _lsd1_open_compose(dialog, frm, opts, state, service_type) {
	if (!service_type || !opts.createPayloadMethod) return;
	if (state.composeServiceType === service_type && state.composeReady) {
		return;
	}

	const $panel = dialog.$wrapper.find(".lsd1-compose-panel");
	const $grid = $panel.find(".lsd1-compose-grid");
	_lsd1_clear_compose_controls(state);
	state.composeServiceType = service_type;
	const request_id = state.composeRequest;
	$grid.empty();
	$panel.find(".lsd1-compose-meta").text(service_type);
	$panel.removeAttr("hidden");

	frappe.call({
		method: opts.createPayloadMethod,
		args: Object.assign(_lsd1_parent_context(frm), {
			service_type,
		}),
		callback(r) {
			if (state.composeRequest !== request_id) return;
			const payload = (r && r.message) || {};
			const fields = payload.fields || [];
			const values = payload.values || {};
			state.composeDetailFields = payload.detail_fields || [];
			const mountState = {
				editControls: state.composeControls,
				_mountControls: state.composeControls,
			};
			fields.forEach((field) => {
				const mounted = _lsd1_mount_edit_field(
					$grid,
					field,
					values[field.fieldname],
					mountState
				);
				state.composeControls.push(mounted);
			});
			state.composeReady = true;
			const el = $panel.get(0);
			if (el && typeof el.scrollIntoView === "function") {
				el.scrollIntoView({ behavior: "smooth", block: "nearest" });
			}
		},
	});
}

function _lsd1_open_edit(dialog, frm, opts, state, linked_service) {
	if (!linked_service || !opts.getMethod) return;

	const $root = dialog.$wrapper.find(".lsd1-root");
	const $panel = $root.find(".lsd1-edit-panel");
	const $grid = $panel.find(".lsd1-edit-grid");

	frappe.call({
		method: opts.getMethod,
		args: Object.assign(_lsd1_parent_context(frm), {
			linked_service,
		}),
		freeze: true,
		freeze_message: __("Loading linked service..."),
		callback(r) {
			const payload = (r && r.message) || {};
			_lsd1_clear_edit_controls(state);
			$grid.empty();

			const fields = payload.fields || [];
			const values = payload.values || {};
			if (!fields.length) {
				$grid.html(
					`<div class="lsd1-edit-empty">${__(
						"No quick-edit fields for this service type. Use Open full form."
					)}</div>`
				);
			} else {
				fields.forEach((field) => {
					const mounted = _lsd1_mount_edit_field(
						$grid,
						field,
						values[field.fieldname],
						state
					);
					state.editControls.push(mounted);
				});
			}

			state.editing = linked_service;
			state.editServiceType = payload.service_type || "";
			state.editValuesBaseline = _lsd1_collect_edit_values(state);

			$panel.find(".lsd1-edit-meta").text(
				`${payload.service_type || ""} · ${payload.name || linked_service}`
			);
			$panel.removeAttr("hidden");
			$root.find(".lsd1-item").removeClass("is-selected");
			$root.find(".lsd1-item").each(function () {
				if ($(this).attr("data-linked-service") === linked_service) {
					$(this).addClass("is-selected");
				}
			});

			const el = $panel.get(0);
			if (el && typeof el.scrollIntoView === "function") {
				el.scrollIntoView({ behavior: "smooth", block: "nearest" });
			}
		},
	});
}

function _lsd1_save_edit(dialog, frm, opts, state) {
	if (!state.editing || !opts.updateMethod) return;

	const values = _lsd1_collect_edit_values(state);
	const $save = dialog.$wrapper.find(".lsd1-edit-save");
	$save.prop("disabled", true);

	frappe.call({
		method: opts.updateMethod,
		args: Object.assign(_lsd1_parent_context(frm), {
			linked_service: state.editing,
			values,
		}),
		freeze: true,
		freeze_message: __("Saving linked service..."),
		callback() {
			$save.prop("disabled", false);
			frappe.show_alert({
				message: __("Linked service updated"),
				indicator: "green",
			});
			_lsd1_close_edit(dialog, state);
			_lsd1_reload(dialog, frm, opts, state);
			frm.reload_doc();
		},
		error() {
			$save.prop("disabled", false);
		},
	});
}

function _lsd1_reload(dialog, frm, opts, state) {
	const $root = dialog.$wrapper.find(".lsd1-root");
	const $list = $root.find(".lsd1-services-list");
	const selected = state && state.editing;
	_lsd1_fetch(frm, opts, (payload) => {
		const rows = payload.linked_services || [];
		$list.html(_lsd1_render_list(rows, opts, selected));
		_lsd1_update_counts($root, rows.length);
		if (selected) {
			const still_there = rows.some((r) => r.linked_service === selected);
			if (!still_there) {
				_lsd1_close_edit(dialog, state);
			}
		}
	});
}

function _lsd1_bind(dialog, frm, opts, state) {
	const $wrap = dialog.$wrapper;

	$wrap.off("click.lsd1");
	$wrap.on("click.lsd1", ".lsd1-dialog-close", () => dialog.hide());

	$wrap.on("click.lsd1", "a.lsd1-open", function (e) {
		e.preventDefault();
		const ls = $(this).closest(".lsd1-item").attr("data-linked-service");
		if (ls) {
			frappe.set_route("Form", "Linked Service", ls);
		}
	});

	$wrap.on("click.lsd1", "a.lsd1-open-full", function (e) {
		e.preventDefault();
		if (state.editing) {
			frappe.set_route("Form", "Linked Service", state.editing);
		}
	});

	if (opts.allowEdit && opts.getMethod) {
		$wrap.on("click.lsd1", "button.lsd1-edit", function () {
			const ls = $(this).closest(".lsd1-item").attr("data-linked-service");
			if (!ls) return;
			if (state.editing === ls) {
				return;
			}
			const open = () => _lsd1_open_edit(dialog, frm, opts, state, ls);
			if (state.editing && _lsd1_edit_is_dirty(state)) {
				frappe.confirm(
					__("Discard unsaved changes to this linked service?"),
					open
				);
			} else {
				open();
			}
		});

		$wrap.on("click.lsd1", ".lsd1-edit-cancel", () => {
			_lsd1_close_edit(dialog, state);
		});

		$wrap.on("click.lsd1", ".lsd1-edit-save", () => {
			_lsd1_save_edit(dialog, frm, opts, state);
		});
	}

	if (opts.allowRemove && opts.removeMethod) {
		$wrap.on("click.lsd1", "button.lsd1-remove", function () {
			const ls = $(this).closest(".lsd1-item").attr("data-linked-service");
			if (!ls) return;
			frappe.confirm(opts.removeConfirm(ls), () => {
				const args = _lsd1_parent_args(frm, opts);
				args.linked_service = ls;
				frappe.call({
					method: opts.removeMethod,
					args,
					freeze: true,
					freeze_message: __("Removing linked service..."),
					callback() {
						if (state.editing === ls) {
							_lsd1_close_edit(dialog, state);
						}
						_lsd1_reload(dialog, frm, opts, state);
						frm.reload_doc();
					},
				});
			});
		});
	}

	if (opts.allowGenerate) {
		$wrap.on("click.lsd1", "button.lsd1-generate-open", () => {
			_lsd1_open_generate(dialog, frm, opts, state);
		});
		$wrap.on("click.lsd1", ".lsd1-generate-cancel", () => {
			_lsd1_close_generate(dialog);
		});
		$wrap.on("click.lsd1", ".lsd1-generate-create", () => {
			_lsd1_create_generated(dialog, frm, opts, state);
		});
	}

	if (opts.allowAdd && opts.addMethod) {
		$wrap.on("change.lsd1", ".lsd1-service-type", () => {
			const service_type = ($wrap.find(".lsd1-service-type").val() || "").trim();
			if (!service_type) {
				_lsd1_close_compose(dialog, state);
				return;
			}
			_lsd1_open_compose(dialog, frm, opts, state, service_type);
		});

		$wrap.on("click.lsd1", "button.lsd1-add", () => {
			const service_type = ($wrap.find(".lsd1-service-type").val() || "").trim();
			if (!service_type) {
				frappe.msgprint({
					message: __("Select a Service Type."),
					indicator: "orange",
				});
				return;
			}
			const quantity = cint($wrap.find(".lsd1-add-qty").val());
			if (quantity < 1 || quantity > 50) {
				frappe.msgprint({
					message: __("Enter a quantity from 1 to 50."),
					indicator: "orange",
				});
				return;
			}
			if (state.composeServiceType !== service_type || !state.composeReady) {
				_lsd1_open_compose(dialog, frm, opts, state, service_type);
				frappe.msgprint({
					message: __(
						"Service details are still loading. Enter them, then Add Service."
					),
					indicator: "orange",
				});
				return;
			}
			if (!_lsd1_compose_has_details(state)) {
				frappe.msgprint({
					message: __("Enter the linked service details before creating them."),
					indicator: "orange",
				});
				return;
			}
			const values = _lsd1_collect_control_values(state.composeControls);
			const form_qty = cint(values.quantity);
			if (form_qty >= 1 && form_qty <= 50) {
				quantity = form_qty;
			}
			delete values.quantity;
			const args = _lsd1_parent_args(frm, opts);
			args.service_type = service_type;
			args.quantity = quantity;
			args.values = values;
			const $add = $wrap.find("button.lsd1-add");
			$add.prop("disabled", true);
			frappe.call({
				method: opts.addMethod,
				args,
				freeze: true,
				freeze_message: __("Adding linked service..."),
				callback(r) {
					$add.prop("disabled", false);
					$wrap.find(".lsd1-service-type").val("");
					$wrap.find(".lsd1-add-qty").val(1);
					_lsd1_close_compose(dialog, state);
					_lsd1_reload(dialog, frm, opts, state);
					frm.reload_doc();
					const message = (r && r.message) || {};
					const names = message.linked_services || [];
					const count = names.length || (message.linked_service ? 1 : 0);
					if (count) {
						frappe.show_alert({
							message:
								quantity > 1
									? __("Linked service created with quantity {0}", [quantity])
									: __("Linked service created"),
							indicator: "green",
						});
					}
				},
				error() {
					$add.prop("disabled", false);
				},
			});
		});
	}
}

/**
 * Open the Manage Linked Services dialog for a form.
 *
 * @param {object} frm
 * @param {object} options
 * @param {string} options.listMethod - Whitelisted list API
 * @param {string} [options.addMethod] - Whitelisted add API
 * @param {string} [options.removeMethod] - Whitelisted remove API
 * @param {string} [options.getMethod] - Load edit payload (default: Linked Service API)
 * @param {string} [options.updateMethod] - Save edit (default: Linked Service API)
 * @param {string} [options.parentField] - API arg for parent name (default: name)
 * @param {string} [options.parentLabel] - Subtitle label (Case / Quote / …)
 * @param {boolean} [options.allowAdd]
 * @param {boolean} [options.allowRemove]
 * @param {boolean} [options.allowEdit]
 * @param {string} [options.previewMethod] - Sales Quote generate preview
 * @param {string} [options.createMethod] - Sales Quote generate create
 */
logistics.show_linked_services_dialog = function (frm, options) {
	const opts = _lsd1_normalize_options(options);

	if (!opts.listMethod) {
		frappe.msgprint({
			message: __("Services dialog is not configured for this document."),
			indicator: "orange",
		});
		return;
	}

	if (!frm || !frm.doc || !frm.doc.name || frm.is_new()) {
		frappe.msgprint({
			message: opts.unsavedMessage,
			indicator: "orange",
		});
		return;
	}

	const state = {
		editing: null,
		editControls: [],
		editValuesBaseline: null,
		editServiceType: "",
		composeControls: [],
		composeDetailFields: [],
		composeServiceType: "",
		composeReady: false,
		generateProposals: [],
	};

	const dialog = new frappe.ui.Dialog({
		title: __("Manage Linked Services"),
		size: "extra-large",
		static: false,
		fields: [
			{
				fieldname: "body_html",
				fieldtype: "HTML",
				options: _lsd1_shell_html(frm, opts),
			},
		],
	});

	dialog.$wrapper.find(".modal-dialog").addClass("lsd1-dialog");
	dialog.show();
	_lsd1_bind(dialog, frm, opts, state);
	_lsd1_reload(dialog, frm, opts, state);
};
