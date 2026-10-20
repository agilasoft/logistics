// Copyright (c) 2026, AgilaSoft and contributors
// For license information, please see license.txt
// Bulk Update Studio — Desk page over Frappe's existing Bulk Update.

frappe.provide("logistics.bulk_update_studio");

logistics.bulk_update_studio.BulkUpdateStudioPage = class BulkUpdateStudioPage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Bulk Update Studio"),
			single_column: true,
		});
		this.$body = $(wrapper).find(".layout-main-section");
		this.meta = {
			default_limit: 500,
			max_limit: 500,
			background_min_records: 20,
			operators: [],
			core_doctypes: [],
		};
		this.document_type = "";
		this.update_fields = [];
		this.condition_fields = [];
		this.fields_by_name = {};
		this.conditions = [this.empty_row()];
		this.advanced = false;
		this.ready = false;
		this._running = false;
		this._field_request = 0;

		this.render_shell();
		this.bind_events();
		this.load_meta();
	}

	api(method, args) {
		return new Promise((resolve, reject) => {
			frappe.call({
				method: `logistics.logistics.page.bulk_update_studio.bulk_update_studio.${method}`,
				args: args || {},
				callback: (r) => {
					if (r.exc) {
						reject(r);
					} else {
						resolve(r);
					}
				},
				error: (r) => reject(r),
			});
		});
	}

	render_shell() {
		this.$body.html(`
			<div class="bus-page">
				<div class="bus-header">
					<p class="bus-desc">
						${__("Update multiple records efficiently using Frappe's existing Bulk Update functionality.")}
					</p>
					<div class="bus-header-actions">
						<button type="button" class="btn btn-default btn-xs bus-refresh">
							${frappe.utils.icon("refresh", "xs")} ${__("Refresh")}
						</button>
						<button type="button" class="btn btn-default btn-xs bus-open-standard">
							${__("Open Standard Bulk Update")}
						</button>
					</div>
				</div>
				<div class="bus-grid">
					<section class="bus-card">
						<div class="bus-card-title"><span class="bus-step">1</span> ${__("Select records")}</div>
						<div class="bus-fields">
							<div class="bus-field" data-field="document_type"></div>
							<div class="bus-field" data-field="limit"></div>
						</div>
						<div class="bus-conditions">
							<div class="bus-conditions-head">
								<span>${__("Filter conditions")}</span>
								<label class="bus-advanced-label">
									<input type="checkbox" class="bus-advanced-toggle"> ${__("Advanced")}
								</label>
							</div>
							<div class="bus-condition-builder">
								<div class="bus-condition-rows"></div>
								<button type="button" class="btn btn-default btn-xs bus-add-condition">
									${__("Add Condition")}
								</button>
							</div>
							<textarea class="form-control bus-advanced" rows="5" style="display:none"
								placeholder='{"status": "Open", "priority": "High"}'></textarea>
							<p class="bus-hint">
								${__("Leave conditions empty to include every record, up to the limit. All visual conditions are combined with AND. Use Advanced for the original JSON, including OR filters.")}
							</p>
						</div>
					</section>
					<section class="bus-card">
						<div class="bus-card-title"><span class="bus-step">2</span> ${__("Configure the change")}</div>
						<div class="bus-field" data-field="field"></div>
						<div class="bus-fieldname text-muted"></div>
						<div class="bus-field" data-field="update_value"></div>
						<div class="bus-field-note text-muted"></div>
					</section>
				</div>
				<section class="bus-card">
					<div class="bus-card-head">
						<div class="bus-card-title"><span class="bus-step">3</span> ${__("Preview matching records")}</div>
						<button type="button" class="btn btn-default btn-sm bus-preview">
							${__("Preview Matching Records")}
						</button>
					</div>
					<p class="bus-hint">
						${__("Preview is read-only. It uses the same filters as Bulk Update and can change before you confirm. Cancelled documents are shown here and skipped when the update runs.")}
					</p>
					<div class="bus-preview"></div>
				</section>
				<section class="bus-card">
					<div class="bus-card-head">
						<div class="bus-card-title"><span class="bus-step">4</span> ${__("Update records")}</div>
						<button type="button" class="btn btn-primary btn-sm bus-update">
							${__("Update Records")}
						</button>
					</div>
					<p class="bus-hint bus-limit-note"></p>
					<div class="bus-result">
						<div class="bus-empty">${__("Frappe's response appears here after the update runs.")}</div>
					</div>
				</section>
			</div>
		`);
		this.$rows = this.$body.find(".bus-condition-rows");
		this.$builder = this.$body.find(".bus-condition-builder");
		this.$advanced = this.$body.find(".bus-advanced");
		this.$advanced_toggle = this.$body.find(".bus-advanced-toggle");
		this.$preview = this.$body.find(".bus-preview");
		this.$result = this.$body.find(".bus-result");
		this.$fieldname = this.$body.find(".bus-fieldname");
		this.$field_note = this.$body.find(".bus-field-note");
	}

	bind_events() {
		this.$body.on("click", ".bus-refresh", () => this.refresh());
		this.$body.on("click", ".bus-open-standard", () => frappe.set_route("Form", "Bulk Update"));
		this.$body.on("click", ".bus-add-condition", () => {
			this.sync_rows_from_dom();
			this.conditions.push(this.empty_row());
			this.render_conditions();
		});
		this.$body.on("click", ".bus-cond-remove", (event) => {
			const idx = Number($(event.currentTarget).closest(".bus-condition").attr("data-idx"));
			this.sync_rows_from_dom();
			this.conditions.splice(idx, 1);
			if (!this.conditions.length) {
				this.conditions.push(this.empty_row());
			}
			this.render_conditions();
		});
		this.$body.on("change", ".bus-cond-field, .bus-cond-op", () => {
			this.sync_rows_from_dom();
			this.render_conditions();
		});
		this.$advanced_toggle.on("change", () => this.toggle_advanced(this.$advanced_toggle.is(":checked")));
		this.$body.on("click", ".bus-preview", () => this.preview());
		this.$body.on("click", ".bus-update", () => this.confirm_update());
	}

	load_meta() {
		this.set_busy(true);
		this.api("get_studio_meta")
			.then((r) => {
				this.meta = r.message || this.meta;
				this.setup_controls();
				this.render_conditions();
				this.ready = true;
				this.$body.find(".bus-limit-note").text(
					__(
						"Frappe updates fewer than {0} matching records immediately. From {0} to {1} records, Frappe queues a background job. The maximum is {1}.",
						[this.meta.background_min_records, this.meta.max_limit]
					)
				);
			})
			.catch((r) => this.render_error(r, __("Bulk Update Studio could not be loaded.")))
			.finally(() => this.set_busy(false));
	}

	setup_controls() {
		const core = this.meta.core_doctypes || [];
		this.doctype_control = frappe.ui.form.make_control({
			parent: this.$body.find('[data-field="document_type"]'),
			df: {
				fieldtype: "Link",
				options: "DocType",
				fieldname: "document_type",
				label: __("Document Type"),
				placeholder: __("Search document types"),
				reqd: 1,
				get_query: () => ({
					filters: [
						["DocType", "issingle", "=", 0],
						["DocType", "name", "not in", core],
					],
				}),
				change: () => this.on_doctype_change(),
			},
			render_input: true,
		});

		this.limit_control = frappe.ui.form.make_control({
			parent: this.$body.find('[data-field="limit"]'),
			df: {
				fieldtype: "Int",
				fieldname: "limit",
				label: __("Limit"),
				description: __("Maximum number of records processed in one update."),
				non_negative: 1,
				default: this.meta.default_limit,
			},
			render_input: true,
		});
		this.limit_control.set_value(this.meta.default_limit);

		this.field_control = frappe.ui.form.make_control({
			parent: this.$body.find('[data-field="field"]'),
			df: {
				fieldtype: "Autocomplete",
				fieldname: "field",
				label: __("Field to Update"),
				placeholder: __("Search fields"),
				reqd: 1,
				max_items: 500,
				change: () => this.on_field_change(),
			},
			render_input: true,
		});
		this.field_control.set_data([]);
	}

	on_doctype_change() {
		const value = this.doctype_control.get_value() || "";
		if (value === this.document_type) {
			return;
		}
		this.document_type = value;
		this.conditions = [this.empty_row()];
		this.set_advanced(false);
		this.clear_feedback();
		this.load_fields(false);
	}

	load_fields(keep_selection) {
		const document_type = this.doctype_control ? this.doctype_control.get_value() : "";
		const previous = keep_selection && this.field_control ? this.field_control.get_value() : "";
		if (!document_type) {
			this.update_fields = [];
			this.condition_fields = [];
			this.fields_by_name = {};
			if (this.field_control) {
				this.field_control.set_data([]);
				this.field_control.set_value("");
			}
			this.render_value_control();
			this.render_conditions();
			return;
		}
		const token = ++this._field_request;
		this.set_busy(true);
		this.api("get_eligible_fields", { document_type })
			.then((r) => {
				if (token !== this._field_request) {
					return;
				}
				const message = r.message || {};
				this.update_fields = message.update_fields || [];
				this.condition_fields = message.condition_fields || [];
				this.fields_by_name = {};
				this.update_fields.forEach((field) => {
					this.fields_by_name[field.fieldname] = field;
				});
				this.field_control.set_data(this.field_options(this.update_fields));
				const next = this.fields_by_name[previous] ? previous : "";
				this.field_control.set_value(next);
				if (!next) {
					this.render_value_control();
				}
				this.drop_unknown_condition_fields();
				this.render_conditions();
			})
			.catch((r) => this.render_error(r, __("The fields for this document type could not be loaded.")))
			.finally(() => {
				if (token === this._field_request) {
					this.set_busy(false);
				}
			});
	}

	field_options(fields) {
		const counts = {};
		fields.forEach((field) => {
			counts[field.label] = (counts[field.label] || 0) + 1;
		});
		return fields.map((field) => ({
			label: counts[field.label] > 1 ? `${field.label} (${field.fieldname})` : field.label,
			value: field.fieldname,
			description: field.fieldname,
		}));
	}

	on_field_change() {
		const field = this.selected_field();
		const fieldname = field ? field.fieldname : "";
		if (fieldname && fieldname === this._value_field) {
			return;
		}
		this._value_field = fieldname;
		this.render_value_control();
		this.clear_feedback();
	}

	selected_field() {
		if (!this.field_control) {
			return null;
		}
		const value = this.field_control.get_value();
		return this.fields_by_name[value] || null;
	}

	render_value_control() {
		const $parent = this.$body.find('[data-field="update_value"]');
		$parent.empty();
		const field = this.selected_field();
		this.value_control = null;
		if (!field) {
			this.$fieldname.text("");
			this.$field_note.text(__("Select a document type, then choose a field."));
			return;
		}
		this.$fieldname.text(__("Fieldname: {0}", [field.fieldname]));
		this.value_control = frappe.ui.form.make_control({
			parent: $parent,
			df: this.value_df(field),
			render_input: true,
		});
		if (field.fieldtype === "Check") {
			this.value_control.set_value(0);
		}
		const notes = [__("Type: {0}", [field.fieldtype])];
		if (field.fieldtype === "Dynamic Link") {
			notes.push(
				__(
					"Dynamic Link values are saved as text. Bulk Update writes the same value on every matching record."
				)
			);
		}
		if (field.read_only) {
			notes.push(
				__("This field is read-only on the form. Document save may reject the change.")
			);
		}
		if (field.fieldtype === "Check") {
			notes.push(__("Clearing the box sends 0. Bulk Update does not accept a blank value."));
		}
		this.$field_note.text(notes.join(" "));
	}

	value_df(field) {
		const df = {
			fieldname: "update_value",
			label: __("New Value"),
			reqd: field.fieldtype === "Check" ? 0 : 1,
		};
		switch (field.fieldtype) {
			case "Int":
			case "Rating":
				df.fieldtype = "Int";
				break;
			case "Float":
			case "Currency":
			case "Percent":
				df.fieldtype = "Float";
				break;
			case "Date":
			case "Datetime":
			case "Time":
			case "Check":
			case "Select":
			case "Link":
			case "Color":
			case "Duration":
			case "Password":
				df.fieldtype = field.fieldtype;
				if (field.options && field.fieldtype !== "Check") {
					df.options = field.options;
				}
				break;
			case "Dynamic Link":
				df.fieldtype = "Data";
				break;
			case "Text":
			case "Small Text":
			case "Long Text":
			case "Text Editor":
			case "Code":
			case "Markdown Editor":
			case "HTML Editor":
			case "JSON":
			case "Geolocation":
				df.fieldtype = "Small Text";
				break;
			default:
				df.fieldtype = "Data";
		}
		return df;
	}

	empty_row() {
		return { field: "", operator: "=", value: "", value_to: "" };
	}

	drop_unknown_condition_fields() {
		const known = {};
		this.condition_fields.forEach((field) => {
			known[field.fieldname] = true;
		});
		this.conditions.forEach((row) => {
			if (row.field && !known[row.field]) {
				row.field = "";
				row.value = "";
				row.value_to = "";
			}
		});
	}

	render_conditions() {
		if (!this.$rows) {
			return;
		}
		const operators = this.meta.operators || [];
		const field_options = this.condition_fields
			.map(
				(field) =>
					`<option value="${this.esc(field.fieldname)}">${this.esc(field.label)} (${this.esc(
						field.fieldname
					)})</option>`
			)
			.join("");
		const html = this.conditions
			.map((row, idx) => {
				const op_options = operators
					.map(
						(op) =>
							`<option value="${this.esc(op.value)}" ${
								op.value === row.operator ? "selected" : ""
							}>${this.esc(__(op.label))}</option>`
					)
					.join("");
				return `
					<div class="bus-condition" data-idx="${idx}">
						${idx ? '<span class="bus-and">AND</span>' : '<span class="bus-and bus-and-spacer"></span>'}
						<select class="form-control input-xs bus-cond-field">
							<option value="">${__("Field")}</option>
							${field_options.replace(
								`value="${this.esc(row.field)}"`,
								`value="${this.esc(row.field)}" selected`
							)}
						</select>
						<select class="form-control input-xs bus-cond-op">${op_options}</select>
						<div class="bus-cond-values">${this.condition_value_html(row)}</div>
						<button type="button" class="btn btn-default btn-xs bus-cond-remove" title="${__(
							"Remove"
						)}">${__("Remove")}</button>
					</div>
				`;
			})
			.join("");
		this.$rows.html(html || "");
	}

	condition_field(fieldname) {
		return this.condition_fields.find((field) => field.fieldname === fieldname) || null;
	}

	condition_value_html(row) {
		const field = this.condition_field(row.field);
		if (row.operator === "is") {
			return `
				<select class="form-control input-xs bus-cond-value">
					<option value="">${__("Select")}</option>
					<option value="set" ${row.value === "set" ? "selected" : ""}>${__("Set")}</option>
					<option value="not set" ${row.value === "not set" ? "selected" : ""}>${__("Not set")}</option>
				</select>
			`;
		}
		if (row.operator === "between") {
			return `
				<input class="form-control input-xs bus-cond-value" value="${this.esc(row.value)}" placeholder="${__(
					"From"
				)}">
				<input class="form-control input-xs bus-cond-value-to" value="${this.esc(
					row.value_to
				)}" placeholder="${__("To")}">
			`;
		}
		if (field && field.fieldtype === "Check" && (row.operator === "=" || row.operator === "!=")) {
			return `
				<select class="form-control input-xs bus-cond-value">
					<option value="">${__("Select")}</option>
					<option value="1" ${row.value === "1" ? "selected" : ""}>${__("Yes")}</option>
					<option value="0" ${row.value === "0" ? "selected" : ""}>${__("No")}</option>
				</select>
			`;
		}
		if (field && field.fieldtype === "Select" && (row.operator === "=" || row.operator === "!=")) {
			const options = String(field.options || "")
				.split("\n")
				.filter((option) => option && option !== "\n");
			const items = options
				.map(
					(option) =>
						`<option value="${this.esc(option)}" ${option === row.value ? "selected" : ""}>${this.esc(
							option
						)}</option>`
				)
				.join("");
			return `
				<select class="form-control input-xs bus-cond-value">
					<option value="">${__("Select")}</option>
					${items}
				</select>
			`;
		}
		if (field && field.fieldtype === "Date" && row.operator !== "in" && row.operator !== "not in") {
			return `<input type="date" class="form-control input-xs bus-cond-value" value="${this.esc(row.value)}">`;
		}
		let placeholder = "";
		if (row.operator === "in" || row.operator === "not in") {
			placeholder = __("Comma-separated values");
		} else if (row.operator === "like" || row.operator === "not like") {
			placeholder = __("Use % as a wildcard");
		}
		return `<input class="form-control input-xs bus-cond-value" value="${this.esc(
			row.value
		)}" placeholder="${this.esc(placeholder)}">`;
	}

	sync_rows_from_dom() {
		if (this.advanced || !this.$rows.find(".bus-condition").length) {
			return;
		}
		const rows = [];
		this.$rows.find(".bus-condition").each((_, el) => {
			const $el = $(el);
			rows.push({
				field: $el.find(".bus-cond-field").val() || "",
				operator: $el.find(".bus-cond-op").val() || "=",
				value: $el.find(".bus-cond-value").val() || "",
				value_to: $el.find(".bus-cond-value-to").val() || "",
			});
		});
		this.conditions = rows.length ? rows : [this.empty_row()];
	}

	toggle_advanced(enabled) {
		if (enabled) {
			this.sync_rows_from_dom();
			this.set_busy(true);
			this.api("compile_conditions", { conditions: this.conditions })
				.then((r) => {
					const text = (r.message && r.message.condition) || "";
					this.$advanced.val(text);
					this.set_advanced(true);
				})
				.catch((r) => {
					this.$advanced_toggle.prop("checked", false);
					this.render_error(r, __("The conditions could not be converted."));
				})
				.finally(() => this.set_busy(false));
			return;
		}
		const text = (this.$advanced.val() || "").trim();
		const rows = this.rows_from_advanced();
		if (text && !rows) {
			this.$advanced_toggle.prop("checked", true);
			this.warn(
				__(
					"These JSON conditions cannot be shown in the visual builder. They stay in Advanced mode."
				)
			);
			return;
		}
		if (rows) {
			this.conditions = rows;
		}
		this.set_advanced(false);
		this.render_conditions();
	}

	rows_from_advanced() {
		const text = (this.$advanced.val() || "").trim();
		if (!text) {
			return [this.empty_row()];
		}
		let parsed;
		try {
			parsed = JSON.parse(text);
		} catch (e) {
			return null;
		}
		if (!Array.isArray(parsed)) {
			return null;
		}
		const allowed = {};
		(this.meta.operators || []).forEach((op) => {
			allowed[op.value] = true;
		});
		const rows = [];
		for (const item of parsed) {
			if (!Array.isArray(item) || item.length < 3 || !allowed[item[1]]) {
				return null;
			}
			const field = String(item[0]);
			const operator = item[1];
			const value = item[2];
			if (operator === "between") {
				if (!Array.isArray(value) || value.length < 2) {
					return null;
				}
				rows.push({
					field,
					operator,
					value: value[0] == null ? "" : String(value[0]),
					value_to: value[1] == null ? "" : String(value[1]),
				});
			} else if (operator === "in" || operator === "not in") {
				rows.push({
					field,
					operator,
					value: Array.isArray(value) ? value.join(", ") : String(value),
					value_to: "",
				});
			} else {
				rows.push({
					field,
					operator,
					value: value == null ? "" : String(value),
					value_to: "",
				});
			}
		}
		return rows.length ? rows : [this.empty_row()];
	}

	set_advanced(enabled) {
		this.advanced = enabled;
		this.$advanced_toggle.prop("checked", enabled);
		this.$builder.toggle(!enabled);
		this.$advanced.toggle(enabled);
	}

	collect() {
		if (!this.doctype_control) {
			return null;
		}
		const document_type = this.doctype_control.get_value();
		if (!document_type) {
			this.warn(__("Select a document type."));
			return null;
		}
		const field = this.selected_field();
		if (!field) {
			this.warn(__("Select a field to update."));
			return null;
		}
		const update_value = this.update_value_for(field);
		if (field.fieldtype !== "Check" && update_value === "") {
			this.warn(__("Enter the new value."));
			return null;
		}
		const payload = {
			document_type,
			field: field.fieldname,
			field_label: field.label,
			fieldtype: field.fieldtype,
			update_value,
			limit: this.effective_limit(),
			summary: "",
		};
		if (this.advanced) {
			payload.condition = (this.$advanced.val() || "").trim();
			if (payload.condition) {
				try {
					JSON.parse(payload.condition);
				} catch (e) {
					this.warn(
						__(
							'Condition must be valid JSON. Example: {"status": "Open", "priority": "High"}'
						)
					);
					return null;
				}
			}
		} else {
			this.sync_rows_from_dom();
			for (const row of this.conditions) {
				const started = row.field || row.value || row.value_to;
				if (!started) {
					continue;
				}
				if (!row.field) {
					this.warn(__("Each condition needs a field."));
					return null;
				}
				if (row.operator === "between" && (row.value === "" || row.value_to === "")) {
					this.warn(__("Between needs a start value and an end value."));
					return null;
				}
				if (row.operator !== "between" && row.value === "") {
					this.warn(__("Enter a value for each condition, or remove the empty row."));
					return null;
				}
			}
			payload.conditions = this.conditions;
		}
		payload.summary = this.condition_summary();
		return payload;
	}

	update_value_for(field) {
		if (!this.value_control) {
			return "";
		}
		const value = this.value_control.get_value();
		if (field.fieldtype === "Check") {
			return value ? "1" : "0";
		}
		if (value === undefined || value === null) {
			return "";
		}
		return String(value);
	}

	effective_limit() {
		const entered = this.limit_control ? this.limit_control.get_value() : this.meta.default_limit;
		const number = parseInt(entered, 10);
		if (!number || number >= this.meta.max_limit) {
			return this.meta.max_limit;
		}
		return number;
	}

	condition_summary() {
		if (this.advanced) {
			const text = (this.$advanced.val() || "").trim();
			return text || __("None (all records up to the limit)");
		}
		const parts = [];
		this.conditions.forEach((row) => {
			if (!row.field) {
				return;
			}
			const field = this.condition_field(row.field);
			const label = field ? field.label : row.field;
			const op = (this.meta.operators || []).find((item) => item.value === row.operator);
			const op_label = op ? __(op.label) : row.operator;
			let value = row.value;
			if (row.operator === "between") {
				value = `${row.value} – ${row.value_to}`;
			}
			parts.push(`${label} ${op_label} ${value}`);
		});
		return parts.join(` ${__("AND")} `) || __("None (all records up to the limit)");
	}

	confirm_update() {
		const payload = this.collect();
		if (!payload || this._running) {
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: __("Confirm Bulk Update"),
			fields: [{ fieldtype: "HTML", fieldname: "summary" }],
			primary_action_label: __("Confirm Update"),
			primary_action: () => {
				dialog.hide();
				this.execute(payload);
			},
			secondary_action_label: __("Cancel"),
			secondary_action: () => dialog.hide(),
		});
		dialog.fields_dict.summary.$wrapper.html(this.summary_html(payload));
		dialog.show();
	}

	summary_html(payload) {
		const rows = [
			[__("Document Type"), payload.document_type],
			[__("Field"), `${payload.field_label} (${payload.field})`],
			[__("New Value"), payload.fieldtype === "Check" ? (payload.update_value === "1" ? __("Yes") : __("No")) : payload.update_value],
			[__("Condition"), payload.summary],
			[__("Limit"), String(payload.limit)],
		];
		const body = rows
			.map(
				([label, value]) =>
					`<div class="bus-summary-row"><span>${this.esc(label)}</span><strong>${this.esc(value)}</strong></div>`
			)
			.join("");
		return `
			<div class="bus-summary">
				${body}
				<p class="bus-fine">${__(
					"This confirmation only asks you to review the request. Frappe Bulk Update still applies its own permissions, validations, and limit."
				)}</p>
			</div>
		`;
	}

	execute(payload) {
		this._running = true;
		this.set_busy(true);
		this.$result.html(`<div class="bus-empty">${__("Submitting the update to Frappe…")}</div>`);
		const args = {
			document_type: payload.document_type,
			field: payload.field,
			update_value: payload.update_value,
			limit: payload.limit,
		};
		if (payload.condition) {
			args.condition = payload.condition;
		}
		if (payload.conditions) {
			args.conditions = payload.conditions;
		}
		this.api("execute_bulk_update", args)
			.then((r) => this.render_response(r))
			.catch((r) => this.render_error(r, __("The update could not be completed.")))
			.finally(() => {
				this._running = false;
				this.set_busy(false);
			});
	}

	preview() {
		const payload = this.collect();
		if (!payload || this._running) {
			return;
		}
		this.set_busy(true);
		this.$preview.html(`<div class="bus-empty">${__("Reading matching records…")}</div>`);
		const args = {
			document_type: payload.document_type,
			field: payload.field,
			update_value: payload.update_value,
			limit: payload.limit,
		};
		if (payload.condition) {
			args.condition = payload.condition;
		}
		if (payload.conditions) {
			args.conditions = payload.conditions;
		}
		this.api("preview_matching_records", args)
			.then((r) => this.render_preview(r.message || {}, payload))
			.catch((r) => {
				this.$preview.empty();
				this.render_error(r, __("The matching records could not be read."));
			})
			.finally(() => this.set_busy(false));
	}

	render_preview(data, payload) {
		const records = data.records || [];
		if (!records.length) {
			this.$preview.html(
				`<div class="bus-empty">${__(
					"No records match these conditions right now. Bulk Update would have nothing to change unless records are added before you confirm."
				)}</div>`
			);
			return;
		}
		const proposed = payload.update_value;
		const body = records
			.map((row, idx) => {
				const status = this.docstatus_note(row.docstatus);
				return `
					<tr>
						<td>${idx + 1}</td>
						<td>${this.esc(row.name)}</td>
						<td>${this.esc(this.display_value(row.current_value))}</td>
						<td>${this.esc(this.display_value(proposed))}</td>
						<td>${this.esc(status)}</td>
					</tr>
				`;
			})
			.join("");
		const capped = records.length >= (data.limit || payload.limit);
		this.$preview.html(`
			<div class="bus-table-scroll">
				<table class="bus-table">
					<thead>
						<tr>
							<th>#</th>
							<th>${__("Document")}</th>
							<th>${__("Current value")}</th>
							<th>${__("Proposed value")}</th>
							<th>${__("Document status")}</th>
						</tr>
					</thead>
					<tbody>${body}</tbody>
				</table>
			</div>
			<p class="bus-fine">
				${__("Showing {0} records returned for this limit.", [records.length])}
				${
					capped
						? __("Frappe will not update more than this limit in one run.")
						: ""
				}
			</p>
		`);
	}

	docstatus_note(docstatus) {
		const value = Number(docstatus);
		if (value === 2) {
			return __("Cancelled — skipped by Bulk Update");
		}
		if (value === 1) {
			return __("Submitted — saved only if the document allows it");
		}
		if (value === 0) {
			return __("Draft");
		}
		return "";
	}

	display_value(value) {
		if (value === undefined || value === null || value === "") {
			return "—";
		}
		return String(value);
	}

	render_response(r) {
		const data = r.message || {};
		const server = this.server_messages(r);
		if (data.enqueued) {
			const detail = server.length
				? server.join("<br>")
				: __("Frappe queued this update in the background.");
			this.$result.html(
				this.feedback(
					"warning",
					__("Background job queued"),
					`${detail}<p class="bus-fine">${__(
						"Frappe does not return a processed count for a queued update. When the job publishes progress, Desk shows Frappe's own progress indicator."
					)}</p>`
				)
			);
			return;
		}
		const failed = data.failed || [];
		if (failed.length) {
			const items = failed.map((name) => `<li>${this.esc(name)}</li>`).join("");
			this.$result.html(
				this.feedback(
					"danger",
					__("Some documents were not updated"),
					`<ul class="bus-failed">${items}</ul><p class="bus-fine">${__(
						'Cancelled documents are skipped. Other failures are recorded in the Error Log as "Bulk action failed". Frappe does not return a success count.'
					)}</p>`
				)
			);
			return;
		}
		const extra = server.length ? `<div class="bus-fine">${server.join("<br>")}</div>` : "";
		this.$result.html(
			this.feedback(
				"success",
				__("Frappe reported no failed documents"),
				`<p>${__("The update finished. Frappe does not return how many records changed.")}</p>${extra}`
			)
		);
	}

	render_error(r, fallback) {
		const server = this.server_messages(r);
		const message = server.length ? server.join("<br>") : this.esc(fallback);
		this.$result.html(this.feedback("danger", __("Update not completed"), message));
	}

	server_messages(r) {
		if (!r || !r._server_messages) {
			return [];
		}
		try {
			const outer = JSON.parse(r._server_messages);
			return outer.map((item) => {
				try {
					const parsed = JSON.parse(item);
					return parsed.message || item;
				} catch (e) {
					return item;
				}
			});
		} catch (e) {
			return [String(r._server_messages)];
		}
	}

	feedback(kind, title, body) {
		return `
			<div class="bus-feedback bus-feedback-${kind}">
				<strong>${this.esc(title)}</strong>
				<div>${body}</div>
			</div>
		`;
	}

	warn(message) {
		frappe.msgprint({
			title: __("Bulk Update Studio"),
			message,
			indicator: "orange",
		});
		this.$result.html(this.feedback("warning", __("Check the form"), this.esc(message)));
	}

	clear_feedback() {
		this.$preview.empty();
		this.$result.html(
			`<div class="bus-empty">${__("Frappe's response appears here after the update runs.")}</div>`
		);
	}

	set_busy(busy) {
		this.$body.find(".bus-update, .bus-preview, .bus-refresh, .bus-add-condition").prop("disabled", busy);
		this.$body.toggleClass("bus-busy", busy);
	}

	refresh() {
		if (!this.ready || !this.doctype_control || !this.doctype_control.get_value()) {
			this.clear_feedback();
			return;
		}
		this.sync_rows_from_dom();
		this.clear_feedback();
		this.load_fields(true);
	}

	esc(value) {
		return frappe.utils.escape_html(value === undefined || value === null ? "" : String(value));
	}
};
