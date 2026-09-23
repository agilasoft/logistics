/*!
 * Job / Shipment change lock + Change Request dialog.
 * Submitted jobs are read-only for amendable fields; use Change Request to edit.
 */
(function () {
	frappe.provide("logistics.job_change_lock");

	const LOCKED_JOB_TYPES = new Set([
		"Air Shipment",
		"Sea Shipment",
		"Transport Job",
		"Warehouse Job",
		"Declaration",
		"Run Sheet",
	]);

	const EXEMPT_FIELDS = new Set([
		"job_status",
		"status",
		"shipping_status",
		"tracking_status",
		"consolidation_status",
		"billing_status",
		"tracking_number",
		"tracking_url",
		"tracking_provider",
		"real_time_tracking_enabled",
		"last_tracking_update",
		"sla_status",
		"sla_notes",
		"sla_target_date",
		"sla_target_source",
		"atd",
		"ata",
		"actual_completion_time",
		"route_optimization_score",
		"selected_route_polyline",
		"selected_route_index",
		"driver_name",
		"document_list_template",
		"milestone_template",
		"amended_from",
		"naming_series",
		"job_number",
		"branch",
		"cost_center",
		"profit_center",
		"service_role",
		"main_service_type",
		"main_service",
		"linked_service",
		"shipper_address_display",
		"consignee_address_display",
		"shipper_contact_display",
		"consignee_contact_display",
		"terms",
		"service_level_details",
		"estimated_revenue",
		"estimated_costs",
		"chargeable",
		"total_packages",
		"total_volume",
		"total_weight",
		"wip_amount",
		"accrual_amount",
		"recognized_revenue",
		"recognized_costs",
		"wip_journal_entry",
		"wip_closed",
		"accrual_closed",
		"wip_recognition_enabled",
		"accrual_recognition_enabled",
		"recognition_policy_reference",
		"recognition_date_basis",
		"recognition_date",
		"is_high_value",
	]);

	const EXEMPT_TABLES = new Set([
		"milestones",
		"documents",
		"operational_exchange_rates",
		"reference_numbers",
	]);

	const EXEMPT_TABLES_BY_DOCTYPE = {
		"Run Sheet": new Set(["legs"]),
	};

	const SECTION_OPTIONS = [
		"Parties",
		"Places & Dates",
		"Packages",
		"Charges",
		"Notes",
	];

	const SECTION_OPTIONS_BY_DOCTYPE = {
		"Run Sheet": ["Places & Dates", "Notes"],
		// Declaration ``packages`` is a Float count, not a package table.
		Declaration: ["Parties", "Places & Dates", "Charges", "Notes"],
	};

	function sections_for(doctype) {
		return SECTION_OPTIONS_BY_DOCTYPE[doctype] || SECTION_OPTIONS;
	}

	function is_locked_frm(frm) {
		if (!frm || !frm.doc || !LOCKED_JOB_TYPES.has(frm.doctype)) return false;
		if (frm.is_new && frm.is_new()) return false;
		return cint(frm.doc.docstatus) === 1;
	}

	function set_banner(frm) {
		if (!frm || !frm.dashboard) return;
		frm.dashboard.clear_headline();
		if (!is_locked_frm(frm)) return;
		frm.dashboard.set_headline(
			__(
				"This {0} is locked after submit. Use <b>Change Request</b> to amend parties, places, packages, charges, or notes.",
				[frm.doctype]
			),
			"blue"
		);
	}

	function lock_amendable_fields(frm) {
		if (!is_locked_frm(frm)) return;
		const meta = frappe.get_meta(frm.doctype);
		(meta.fields || []).forEach(function (df) {
			const fn = df.fieldname;
			if (!fn) return;
			if (
				df.fieldtype === "Section Break" ||
				df.fieldtype === "Column Break" ||
				df.fieldtype === "Tab Break" ||
				df.fieldtype === "HTML" ||
				df.fieldtype === "Button" ||
				df.fieldtype === "Heading"
			) {
				return;
			}
			if (df.fieldtype === "Table") {
				const exemptTables = new Set([
					...EXEMPT_TABLES,
					...(EXEMPT_TABLES_BY_DOCTYPE[frm.doctype] || []),
				]);
				if (exemptTables.has(fn)) return;
				frm.set_df_property(fn, "read_only", 1);
				frm.set_df_property(fn, "cannot_add_rows", 1);
				frm.set_df_property(fn, "cannot_delete_rows", 1);
				return;
			}
			if (EXEMPT_FIELDS.has(fn)) return;
			frm.set_df_property(fn, "read_only", 1);
		});
	}

	function open_change_request_dialog(frm) {
		if (!frm || !frm.doc || !frm.doc.name) return;

		frappe.call({
			method: "logistics.job_management.job_change_lock.get_open_change_requests",
			args: { job_type: frm.doctype, job_name: frm.doc.name },
			callback: function (r) {
				const data = r.message || {};
				const drafts = data.drafts || [];
				const pending = data.pending || [];
				_show_dialog(frm, drafts, pending);
			},
		});
	}

	function _show_dialog(frm, drafts, pending) {
		const mode_options = ["New Change Request"];
		if (drafts.length) mode_options.push("Continue Draft");
		if (pending.length) mode_options.push("View Pending");

		const fields = [
			{
				fieldname: "mode",
				fieldtype: "Select",
				label: __("Action"),
				options: mode_options.join("\n"),
				default: drafts.length ? "Continue Draft" : "New Change Request",
				reqd: 1,
			},
		];

		if (drafts.length) {
			fields.push({
				fieldname: "draft_name",
				fieldtype: "Select",
				label: __("Draft Change Request"),
				options: drafts.map((d) => d.name).join("\n"),
				default: drafts[0].name,
				depends_on: "eval:doc.mode==='Continue Draft'",
			});
		}
		if (pending.length) {
			fields.push({
				fieldname: "pending_name",
				fieldtype: "Select",
				label: __("Pending Change Request"),
				options: pending.map((d) => d.name).join("\n"),
				default: pending[0].name,
				depends_on: "eval:doc.mode==='View Pending'",
			});
		}

		fields.push(
			{
				fieldname: "sections_html",
				fieldtype: "HTML",
				options: `<p class="text-muted">${__(
					"Select what you want to amend. The Change Request will be filled with current job values."
				)}</p>`,
				depends_on: "eval:doc.mode==='New Change Request'",
			},
			{
				fieldname: "sections",
				fieldtype: "MultiCheck",
				label: __("Sections"),
				columns: 2,
				options: sections_for(frm.doctype).map((s) => ({
					label: __(s),
					value: s,
					checked: true,
				})),
				depends_on: "eval:doc.mode==='New Change Request'",
			},
			{
				fieldname: "reason",
				fieldtype: "Small Text",
				label: __("Reason"),
				reqd: 0,
				depends_on: "eval:doc.mode==='New Change Request'",
			}
		);

		const d = new frappe.ui.Dialog({
			title: __("Change Request for {0}", [frm.doc.name]),
			fields: fields,
			primary_action_label: __("Open Change Request"),
			primary_action(values) {
				const mode = values.mode || "New Change Request";
				if (mode === "Continue Draft") {
					const name = values.draft_name || (drafts[0] && drafts[0].name);
					d.hide();
					if (name) frappe.set_route("Form", "Change Request", name);
					return;
				}
				if (mode === "View Pending") {
					const name = values.pending_name || (pending[0] && pending[0].name);
					d.hide();
					if (name) frappe.set_route("Form", "Change Request", name);
					return;
				}
				const reason = (values.reason || "").trim();
				if (!reason) {
					frappe.msgprint({
						title: __("Reason Required"),
						message: __("Please enter a reason for the change."),
						indicator: "orange",
					});
					return;
				}
				let sections = values.sections;
				if (!Array.isArray(sections) || !sections.length) {
					sections = sections_for(frm.doctype).slice();
				}
				d.hide();
				frappe.call({
					method:
						"logistics.pricing_center.doctype.change_request.change_request.create_change_request",
					args: {
						job_type: frm.doctype,
						job_name: frm.doc.name,
						sections: JSON.stringify(sections),
						reason: reason,
						reuse_draft: 0,
					},
					freeze: true,
					freeze_message: __("Creating Change Request..."),
					callback: function (res) {
						if (res.message) {
							frappe.set_route("Form", "Change Request", res.message);
						}
					},
				});
			},
		});
		d.show();
	}

	function add_change_request_button(frm) {
		if (!frm || !frm.doc || !frm.doc.name || frm.is_new()) return;
		if (!LOCKED_JOB_TYPES.has(frm.doctype)) return;

		if (window.logistics && logistics.menu) {
			logistics.menu.add(frm, {
				label: __("Change Request"),
				doctype: "Change Request",
				ptype: "create",
				css_class: "btn-primary",
				action: function () {
					open_change_request_dialog(frm);
				},
			});
			return;
		}
		frm.add_custom_button(__("Change Request"), function () {
			open_change_request_dialog(frm);
		}).addClass("btn-primary");
	}

	/**
	 * Call from each job form refresh.
	 */
	logistics.job_change_lock.apply = function (frm) {
		if (!frm || !LOCKED_JOB_TYPES.has(frm.doctype)) return;
		set_banner(frm);
		lock_amendable_fields(frm);
		add_change_request_button(frm);
	};

	logistics.job_change_lock.open_dialog = open_change_request_dialog;
	logistics.job_change_lock.is_locked = is_locked_frm;
})();
