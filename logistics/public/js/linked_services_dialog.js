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
				"Select a service type to link. You can add multiple services of the same type."
			),
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
					<div class="lsd1-item-meta">${source_html}${job_html}</div>
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
						<button type="button" class="lsd1-add-btn lsd1-add">
							${_lsd1_icon("add", "xs") || "+"}
							<span>${__("Add Service")}</span>
						</button>
					</div>
					<p class="lsd1-hint">${_lsd1_escape(opts.addHint)}</p>
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
		df.get_options = function () {
			const sibling = (state.editControls || []).find(
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

function _lsd1_collect_edit_values(state) {
	const values = {};
	(state.editControls || []).forEach((c) => {
		if (!c || c.read_only) return;
		values[c.fieldname] = c.get_value();
	});
	return values;
}

function _lsd1_edit_is_dirty(state) {
	if (!state.editValuesBaseline) return false;
	const current = _lsd1_collect_edit_values(state);
	return JSON.stringify(current) !== JSON.stringify(state.editValuesBaseline);
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

	if (opts.allowAdd && opts.addMethod) {
		$wrap.on("click.lsd1", "button.lsd1-add", () => {
			const service_type = ($wrap.find(".lsd1-service-type").val() || "").trim();
			if (!service_type) {
				frappe.msgprint({
					message: __("Select a Service Type."),
					indicator: "orange",
				});
				return;
			}
			const args = _lsd1_parent_args(frm, opts);
			args.service_type = service_type;
			frappe.call({
				method: opts.addMethod,
				args,
				freeze: true,
				freeze_message: __("Adding linked service..."),
				callback(r) {
					$wrap.find(".lsd1-service-type").val("");
					_lsd1_reload(dialog, frm, opts, state);
					frm.reload_doc();
					const created =
						r && r.message && r.message.linked_service
							? r.message.linked_service
							: null;
					if (created && opts.allowEdit && opts.getMethod) {
						_lsd1_open_edit(dialog, frm, opts, state, created);
					}
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
