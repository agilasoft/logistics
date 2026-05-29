# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import escape_html, flt

from logistics.special_projects.special_project_lifecycle import (
	validate_special_project_lifecycle_stage_advance,
)
from logistics.utils.lifecycle_stage import (
	FOR_SPECIAL_PROJECT,
	resolve_default_lifecycle_stage,
	validate_internal_job_activity_codes,
)
from logistics.utils.special_project_internal_jobs import (
	job_refs_from_lifecycle_jobs,
	resolve_internal_job_detail_row_to_operational_ref,
)


def _format_qty(value: float) -> str:
	"""Format a quantity for display: thousands separator, drop unnecessary trailing zeros."""
	value = flt(value)
	if value == int(value):
		return f"{int(value):,}"
	# Up to 3 decimal places, strip trailing zeros and decimal if not needed
	formatted = f"{value:,.3f}".rstrip("0").rstrip(".")
	return formatted


_LIFECYCLE_STATUS_INDICATORS = {
	"Not Started": "gray",
	"On Hold": "orange",
	"In Progress": "blue",
	"Pending": "orange",
	"Blocked": "red",
	"Cancelled": "red",
	"Completed": "green",
	"N/A": "gray",
}


def _status_to_indicator(status: str) -> str:
	"""Map a lifecycle activity status to a Frappe indicator-pill colour class."""
	return _LIFECYCLE_STATUS_INDICATORS.get(status, "orange")


def _resolve_package_label(row) -> tuple[str, str]:
	"""Return (display_name, secondary_code) for a package row.

	Prefers user-friendly names (Warehouse Item.item_name, Commodity.description) over
	the system code, and only shows the code as small secondary text when it differs
	from the friendly name.
	"""
	warehouse_item = (getattr(row, "warehouse_item", None) or "").strip()
	commodity = (getattr(row, "commodity", None) or "").strip()
	description = (getattr(row, "description", None) or "").strip()

	display = ""
	code = ""

	if warehouse_item:
		item_name = frappe.db.get_value("Warehouse Item", warehouse_item, "item_name") or ""
		item_name = (item_name or "").strip()
		display = item_name or warehouse_item
		code = warehouse_item if item_name and item_name != warehouse_item else ""
	elif commodity:
		commodity_desc = frappe.db.get_value("Commodity", commodity, "description") or ""
		commodity_desc = (commodity_desc or "").strip()
		display = commodity_desc or commodity
		code = commodity if commodity_desc and commodity_desc != commodity else ""
	elif description:
		display = description
	else:
		display = _("Row {0}").format(row.idx)

	return display, code


def _format_row_idx_list(row_idxs: list[int], max_inline: int = 12) -> str:
	"""Return a compact comma-separated list of row indices, truncating overflow."""
	if not row_idxs:
		return "—"
	if len(row_idxs) <= max_inline:
		return ", ".join(str(i) for i in row_idxs)
	visible = ", ".join(str(i) for i in row_idxs[:max_inline])
	remaining = len(row_idxs) - max_inline
	return f"{visible} <span class=\"text-muted\">+{remaining} {_('more')}</span>"


class SpecialProject(Document):
	def validate(self):
		validate_internal_job_activity_codes(self, module_filter=FOR_SPECIAL_PROJECT)
		validate_special_project_lifecycle_stage_advance(self)
		self._ensure_charges_tab_defaults()
		from logistics.utils.charges_calculation import (
			clear_charge_resolution_parent,
			register_charge_resolution_parent,
		)

		register_charge_resolution_parent(self)
		try:
			self.validate_accounts()
			from logistics.special_projects.special_project_packages import (
				validate_packages,
			)

			validate_packages(self)
			self._sync_charges_with_parent_actuals()
			from logistics.special_projects.lifecycle_job_financial_rollup import (
				sync_lifecycle_job_financials,
			)

			sync_lifecycle_job_financials(self)
		finally:
			clear_charge_resolution_parent(self)

	def validate_accounts(self):
		"""Ensure cost center / profit center / branch belong to company (same checks as Sea Shipment)."""
		if not self.company:
			return
		if self.cost_center:
			cc_co = frappe.db.get_value("Cost Center", self.cost_center, "company")
			if cc_co and cc_co != self.company:
				frappe.throw(
					_("Cost Center {0} does not belong to Company {1}").format(self.cost_center, self.company)
				)
		if self.profit_center:
			try:
				pc_meta = frappe.get_meta("Profit Center")
				if pc_meta.has_field("company"):
					pc_co = frappe.db.get_value("Profit Center", self.profit_center, "company")
					if pc_co and pc_co != self.company:
						frappe.throw(
							_("Profit Center {0} does not belong to Company {1}").format(
								self.profit_center, self.company
							)
						)
			except Exception as e:
				if "Unknown column" not in str(e) and "1054" not in str(e):
					raise
		if self.branch:
			try:
				br_meta = frappe.get_meta("Branch")
				if br_meta.has_field("company"):
					br_co = frappe.db.get_value("Branch", self.branch, "company")
					if br_co and br_co != self.company:
						frappe.throw(_("Branch {0} does not belong to Company {1}").format(self.branch, self.company))
			except Exception as e:
				if "Unknown column" not in str(e) and "1054" not in str(e):
					raise

	def _sync_charges_with_parent_actuals(self):
		if getattr(frappe.flags, "in_import", False) or getattr(frappe.flags, "in_migrate", False):
			return
		if getattr(self.flags, "ignore_charges_sync", False):
			return
		for charge in self.get("charges") or []:
			if hasattr(charge, "calculate_charge_amount"):
				charge.calculate_charge_amount(parent_doc=self)

	def before_submit(self):
		"""Block submission until packages are fully delivered and lifecycle jobs are complete."""
		self._validate_submit_gates()

	def _validate_submit_gates(self):
		"""Enforce closure gates: every package fully delivered, every lifecycle activity completed."""
		packages = self._collect_package_blockers()
		lifecycle = self._collect_lifecycle_blockers()

		if not packages and not lifecycle:
			return

		primary_target = "fulfillment_tab" if packages else "lifecycle_tab"
		primary_label = (
			_("Go to Fulfillment") if packages else _("Go to Lifecycle")
		)

		summary_lines: list[str] = []
		if packages:
			n_packages = len(packages["groups"])
			n_rows = packages["total_rows"]
			summary_lines.append(
				_("{0} package(s) are not fully delivered, affecting {1} row(s).").format(
					f"<strong>{n_packages}</strong>", f"<strong>{n_rows}</strong>"
				)
			)
		if lifecycle:
			n_pending = len(lifecycle["items"])
			summary_lines.append(
				_("{0} lifecycle activity(ies) are not yet completed.").format(
					f"<strong>{n_pending}</strong>"
				)
			)

		intro = _("Resolve the items below before submitting this Special Project.")
		body_sections: list[str] = []
		if packages:
			body_sections.append(self._render_packages_card(packages))
		if lifecycle:
			body_sections.append(self._render_lifecycle_card(lifecycle))

		footer_tip = _(
			"Tip: review the affected rows in the corresponding tab, then try submitting again."
		)
		summary_html = "".join(f"<li>{line}</li>" for line in summary_lines)
		sections_html = "".join(body_sections)

		body = (
			'<div class="submission-blocker" '
			'style="font-size: 13px; line-height: 1.5; color: var(--text-color, #1f272e);">'
			'<div style="padding: 4px 0 14px 0;">'
			f'<div style="margin: 0 0 6px 0; color: var(--text-muted, #6c757d);">{escape_html(intro)}</div>'
			f'<ul style="margin: 0; padding-left: 18px; line-height: 1.7;">{summary_html}</ul>'
			"</div>"
			f"{sections_html}"
			'<div class="text-muted" style="margin-top: 6px; font-size: 12px;">'
			f"{escape_html(footer_tip)}"
			"</div>"
			"</div>"
		)

		frappe.throw(
			body,
			title=_("Submission Blocked"),
			wide=True,
			primary_action={
				"label": primary_label,
				"client_action": "logistics.special_project_modals.go_to_tab",
				"args": {"fieldname": primary_target},
				"hide_on_success": True,
			},
			allow_dangerous_html=True,
		)

	def _collect_package_blockers(self) -> dict | None:
		"""Group undelivered rows by (package, uom). Returns dict with groups + totals or None."""
		grouped: dict[tuple[str, str, str], dict] = {}
		for row in self.get("packages") or []:
			short = flt(getattr(row, "qty_short", 0))
			if short <= 0:
				continue
			display, code = _resolve_package_label(row)
			uom = (getattr(row, "uom", None) or "").strip()
			key = (display, code, uom)
			info = grouped.setdefault(
				key,
				{
					"display": display,
					"code": code,
					"uom": uom,
					"total_short": 0.0,
					"row_idxs": [],
					"sites": set(),
				},
			)
			info["total_short"] += short
			info["row_idxs"].append(row.idx)
			site = (getattr(row, "site", None) or "").strip()
			if site:
				info["sites"].add(site)

		if not grouped:
			return None

		groups = sorted(grouped.values(), key=lambda x: x["total_short"], reverse=True)
		total_rows = sum(len(g["row_idxs"]) for g in groups)
		total_sites = len({s for g in groups for s in g["sites"]})
		return {"groups": groups, "total_rows": total_rows, "total_sites": total_sites}

	def _render_packages_card(self, materials: dict) -> str:
		"""Render the grouped package shortages as a card with a compact table."""
		MAX_VISIBLE = 12
		groups = materials["groups"]
		visible = groups[:MAX_VISIBLE]
		hidden_count = len(groups) - len(visible)

		body_rows: list[str] = []
		for item in visible:
			short_display = _format_qty(item["total_short"])
			uom_html = (
				f' <span class="text-muted" style="font-weight: 400; font-size: 11px;">'
				f'{escape_html(item["uom"])}</span>'
				if item["uom"]
				else ""
			)
			code_html = (
				f'<div class="text-muted" style="font-size: 11px; margin-top: 2px;">'
				f'{escape_html(item["code"])}</div>'
				if item["code"]
				else ""
			)
			rows_html = _format_row_idx_list(item["row_idxs"])

			body_rows.append(
				"<tr>"
				# Material — bold name with optional small code underneath
				'<td style="padding: 8px 10px;">'
				f'<div style="font-weight: 600;">{escape_html(item["display"])}</div>'
				f"{code_html}"
				"</td>"
				# Rows affected
				'<td style="padding: 8px 10px; vertical-align: top;">'
				f'<div style="font-variant-numeric: tabular-nums;">{rows_html}</div>'
				f'<div class="text-muted" style="font-size: 11px; margin-top: 2px;">'
				+ (
					_("{0} rows").format(len(item["row_idxs"]))
					if len(item["row_idxs"]) > 1
					else _("1 row")
				)
				+ (
					f" · {_('{0} sites').format(len(item['sites']))}"
					if len(item["sites"]) > 1
					else (f" · {_('1 site')}" if item["sites"] else "")
				)
				+ "</div></td>"
				# Total shortage — large red number with subtle UOM
				'<td style="padding: 8px 10px; text-align: right; vertical-align: top; '
				'white-space: nowrap;">'
				'<div style="font-size: 16px; font-weight: 700; '
				'color: var(--red-600, #c0392b); font-variant-numeric: tabular-nums;">'
				f"{short_display}{uom_html}"
				"</div>"
				"</td>"
				"</tr>"
			)

		if hidden_count > 0:
			body_rows.append(
				'<tr><td colspan="3" class="text-muted text-center" '
				'style="padding: 8px 10px; font-style: italic;">'
				+ escape_html(_("…and {0} more package(s)").format(hidden_count))
				+ "</td></tr>"
			)

		title = _("Packages Not Yet Delivered")
		guidance = _(
			"Review the affected packages in the Fulfillment tab and receive the remaining "
			"quantities, or reduce the required quantity on rows no longer needed."
		)
		col_material = _("Package")
		col_rows = _("Rows Affected")
		col_short = _("Remaining")

		return (
			'<div class="submission-blocker-card" '
			'style="border: 1px solid var(--border-color, #e5e7eb); border-radius: 8px; '
			'margin-bottom: 14px; overflow: hidden; background: var(--card-bg, #fff);">'
			# Card header
			'<div style="padding: 10px 14px; background: var(--fg-hover-color, #fafbfc); '
			'border-bottom: 1px solid var(--border-color, #e5e7eb); '
			'display: flex; flex-wrap: wrap; align-items: center; gap: 8px;">'
			'<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; '
			'background: var(--red-500, #e74c3c);"></span>'
			f'<strong style="font-size: 13px;">{escape_html(title)}</strong>'
			'<span class="text-muted" style="font-size: 11px;">'
			+ _("{0} packages · {1} rows").format(
				f"<strong>{len(materials['groups'])}</strong>",
				f"<strong>{materials['total_rows']}</strong>",
			)
			+ (
				_(" · {0} sites").format(f"<strong>{materials['total_sites']}</strong>")
				if materials["total_sites"]
				else ""
			)
			+ "</span>"
			"</div>"
			# Card guidance
			f'<div class="text-muted" style="padding: 8px 14px 0 14px; font-size: 12px;">'
			f"{escape_html(guidance)}</div>"
			# Card table
			'<table class="table table-sm" '
			'style="margin: 8px 0 0 0; font-size: 13px;">'
			'<thead>'
			'<tr style="font-size: 11px; text-transform: uppercase; '
			'letter-spacing: 0.4px; color: var(--text-muted, #6c757d);">'
			f'<th style="padding: 6px 10px; border-top: 0; width: 35%;">{escape_html(col_material)}</th>'
			f'<th style="padding: 6px 10px; border-top: 0;">{escape_html(col_rows)}</th>'
			f'<th style="padding: 6px 10px; border-top: 0; text-align: right; '
			f'width: 25%;">{escape_html(col_short)}</th>'
			"</tr>"
			"</thead>"
			f"<tbody>{''.join(body_rows)}</tbody>"
			"</table>"
			"</div>"
		)

	def _collect_lifecycle_blockers(self) -> dict | None:
		"""Collect pending lifecycle activities. Returns dict with items + status counts or None."""
		pending: list[dict] = []
		for row in self.get("lifecycle_jobs") or []:
			if not (getattr(row, "activity_code", None) or "").strip():
				continue
			status = (getattr(row, "lifecycle_activity_status", None) or "Not Started").strip()
			if status in ("Completed", "N/A"):
				continue
			label = (
				getattr(row, "activity_name", None)
				or getattr(row, "activity_code", None)
				or _("Row {0}").format(row.idx)
			)
			pending.append({"idx": row.idx, "label": str(label), "status": status})

		if not pending:
			return None

		by_status: dict[str, int] = {}
		for item in pending:
			by_status[item["status"]] = by_status.get(item["status"], 0) + 1

		return {"items": pending, "by_status": by_status}

	def _render_lifecycle_card(self, lifecycle: dict) -> str:
		"""Render pending lifecycle activities as a card with a compact table."""
		MAX_VISIBLE = 15
		items = lifecycle["items"]
		visible = items[:MAX_VISIBLE]
		hidden_count = len(items) - len(visible)

		body_rows: list[str] = []
		for item in visible:
			body_rows.append(
				"<tr>"
				f'<td class="text-muted" style="padding: 8px 10px; text-align: right; '
				f'font-variant-numeric: tabular-nums; width: 60px;">#{item["idx"]}</td>'
				f'<td style="padding: 8px 10px; font-weight: 500;">{escape_html(item["label"])}</td>'
				'<td style="padding: 8px 10px; width: 140px;">'
				f'<span class="indicator-pill {_status_to_indicator(item["status"])}">'
				f'{escape_html(item["status"])}</span></td>'
				"</tr>"
			)

		if hidden_count > 0:
			body_rows.append(
				'<tr><td colspan="3" class="text-muted text-center" '
				'style="padding: 8px 10px; font-style: italic;">'
				+ escape_html(_("…and {0} more activity(ies)").format(hidden_count))
				+ "</td></tr>"
			)

		status_chips = " ".join(
			f'<span class="indicator-pill {_status_to_indicator(status)}" '
			f'style="margin-right: 4px;">{escape_html(status)}: {count}</span>'
			for status, count in sorted(
				lifecycle["by_status"].items(), key=lambda kv: kv[1], reverse=True
			)
		)

		title = _("Lifecycle Activities Not Yet Completed")
		guidance = _(
			"Mark each activity as Completed, or set N/A if it does not apply, before submitting."
		)
		col_row = _("Row")
		col_activity = _("Activity")
		col_status = _("Status")

		return (
			'<div class="submission-blocker-card" '
			'style="border: 1px solid var(--border-color, #e5e7eb); border-radius: 8px; '
			'margin-bottom: 14px; overflow: hidden; background: var(--card-bg, #fff);">'
			# Card header
			'<div style="padding: 10px 14px; background: var(--fg-hover-color, #fafbfc); '
			'border-bottom: 1px solid var(--border-color, #e5e7eb); '
			'display: flex; flex-wrap: wrap; align-items: center; gap: 8px;">'
			'<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; '
			'background: var(--orange-500, #f39c12);"></span>'
			f'<strong style="font-size: 13px;">{escape_html(title)}</strong>'
			f'<span style="font-size: 11px;">{status_chips}</span>'
			"</div>"
			# Card guidance
			f'<div class="text-muted" style="padding: 8px 14px 0 14px; font-size: 12px;">'
			f"{escape_html(guidance)}</div>"
			# Card table
			'<table class="table table-sm" '
			'style="margin: 8px 0 0 0; font-size: 13px;">'
			'<thead>'
			'<tr style="font-size: 11px; text-transform: uppercase; '
			'letter-spacing: 0.4px; color: var(--text-muted, #6c757d);">'
			f'<th style="padding: 6px 10px; border-top: 0; text-align: right; '
			f'width: 60px;">{escape_html(col_row)}</th>'
			f'<th style="padding: 6px 10px; border-top: 0;">{escape_html(col_activity)}</th>'
			f'<th style="padding: 6px 10px; border-top: 0; '
			f'width: 140px;">{escape_html(col_status)}</th>'
			"</tr>"
			"</thead>"
			f"<tbody>{''.join(body_rows)}</tbody>"
			"</table>"
			"</div>"
		)

	def autoname(self):
		"""Use ERPNext Project ID as Special Project ID (created in before_insert)."""
		if self.flags.get("erpnext_project_name"):
			self.name = self.flags.erpnext_project_name

	def before_insert(self):
		"""Create ERPNext Project first, then use its ID as this document's ID."""
		self._create_erpnext_project_before_insert()
		self._ensure_charges_tab_defaults()
		self._normalize_default_lifecycle_stage()

	def _normalize_default_lifecycle_stage(self):
		"""Ensure ``lifecycle_stage`` references an existing master row.

		The DocType default is ``Pre-Show``, but new sites or sites that pre-date the
		shared Lifecycle Stage master may not have that record. Validating links during
		``insert`` would then raise ``LinkValidationError``, blocking creation from
		Sales Quote and similar flows. We resolve a safe fallback instead.
		"""
		stage = (self.lifecycle_stage or "").strip()
		if stage and frappe.db.exists("Lifecycle Stage", stage):
			self.lifecycle_stage = stage
			return
		self.lifecycle_stage = resolve_default_lifecycle_stage(
			module_filter=FOR_SPECIAL_PROJECT, preferred="Pre-Show"
		)

	def _ensure_charges_tab_defaults(self):
		"""Default company / cost center from Project or session (Charges tab matches Sea Shipment)."""
		if not self.company:
			co = None
			if self.project:
				co = frappe.db.get_value("Project", self.project, "company")
			if not co:
				co = frappe.defaults.get_user_default("Company")
			if not co:
				co = frappe.db.get_single_value("Global Defaults", "default_company")
			if co:
				self.company = co
		if self.company and not self.cost_center:
			cc = frappe.db.get_value("Company", self.company, "cost_center")
			if cc:
				self.cost_center = cc

	def on_update(self):
		"""Auto-charge scoping costs when status changes to Booked."""
		if self.has_value_changed("status") and self.status in ("Booked", "Approved", "Planning", "In Progress"):
			self._maybe_charge_scoping_costs()

	def after_insert(self):
		"""Create Job Number on first save (deferred so the row exists before lookup)."""
		frappe.enqueue(
			"logistics.special_projects.doctype.special_project.special_project.create_job_number_for_special_project",
			queue="default",
			special_project_name=self.name,
			company=self.company,
			branch=self.branch,
			cost_center=self.cost_center,
			profit_center=self.profit_center,
			open_date=self.start_date or self.planned_start,
		)

	def before_save(self):
		"""Create Job Number synchronously on subsequent saves if it is still missing."""
		if self.name and not self.job_number and frappe.db.exists("Special Project", self.name):
			self.create_job_number_if_needed()

	def create_job_number_if_needed(self):
		"""Create Job Number when document is first saved (matches Sea Shipment pattern)."""
		if self.job_number:
			return
		existing_jcn = frappe.db.get_value(
			"Job Number",
			{"job_type": "Special Project", "job_no": self.name},
		)
		if existing_jcn:
			self.job_number = existing_jcn
			return
		job_ref = frappe.new_doc("Job Number")
		job_ref.job_type = "Special Project"
		job_ref.job_no = self.name
		job_ref.company = self.company
		job_ref.branch = self.branch
		job_ref.cost_center = self.cost_center
		job_ref.profit_center = self.profit_center
		job_ref.job_open_date = self.start_date or self.planned_start
		job_ref.project = self.project
		job_ref.insert(ignore_permissions=True)
		self.job_number = job_ref.name
		frappe.msgprint(_("Job Number {0} created successfully").format(job_ref.name))

	def _maybe_charge_scoping_costs(self):
		"""Charge completed scoping activities when project is booked."""
		changed = False
		for row in self.scoping_activities or []:
			if row.status == "Completed" and not row.charged_to_project:
				row.charged_to_project = 1
				row.charged_date = frappe.utils.today()
				changed = True
		# Save is handled by on_update flow

	def _create_erpnext_project_before_insert(self):
		"""Create ERPNext Project first; its ID will be used as Special Project ID via autoname."""
		if self.project:
			# Link Existing Project: use that Project's ID as our name
			self.flags.erpnext_project_name = self.project
			return

		if not frappe.db.exists("DocType", "Project"):
			return

		try:
			project = frappe.new_doc("Project")
			project.project_name = (
				self.project_name
				or f"Special Project {frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}"
			)
			project.customer = self.customer
			project.expected_start_date = self.planned_start or self.start_date
			project.expected_end_date = self.planned_end or self.end_date
			project.status = self._map_status_to_project(self.status)
			project.project_type = (
				self.project_type
				or frappe.db.get_single_value("Special Project Settings", "default_project_type")
				or frappe.db.get_value("Project Type", {"name": "External"}, "name")
			)
			project.company = frappe.defaults.get_defaults().get("company")

			project.insert(ignore_permissions=True)

			self.project = project.name
			self.flags.erpnext_project_name = project.name
		except Exception as e:
			frappe.log_error(
				title=_("Special Project: Failed to create ERPNext Project"),
				message=frappe.get_traceback(),
			)
			raise

	def _map_status_to_project(self, status):
		"""Map Special Project status to ERPNext Project status."""
		status_map = {
			"Draft": "Open",
			"Scoping": "Open",
			"Booked": "Open",
			"Planning": "Open",
			"Approved": "Open",
			"In Progress": "Open",
			"On Hold": "Open",
			"Completed": "Completed",
			"Cancelled": "Cancelled",
		}
		return status_map.get(status, "Open")

	def populate_charges_from_sales_quote(self, sales_quote=None):
		"""Copy charge lines from the linked Sales Quote (or explicit quote name)."""
		from logistics.utils.sales_quote_programme_charges import populate_programme_charges_from_sales_quote

		sq_name = sales_quote or self.sales_quote
		if not sq_name:
			frappe.throw(_("No Sales Quote linked."))
		populate_programme_charges_from_sales_quote(self, sq_name, clear_existing=True)


def create_job_number_for_special_project(
	special_project_name,
	company,
	branch=None,
	cost_center=None,
	profit_center=None,
	open_date=None,
):
	"""Deferred: create Job Number for Special Project after commit (avoids 'not found' during insert)."""
	if not frappe.db.exists("Special Project", special_project_name):
		return
	if frappe.db.get_value("Special Project", special_project_name, "job_number"):
		return
	existing = frappe.db.get_value("Job Number", {"job_type": "Special Project", "job_no": special_project_name})
	if existing:
		frappe.db.set_value("Special Project", special_project_name, "job_number", existing)
		frappe.db.commit()
		return
	project = frappe.db.get_value("Special Project", special_project_name, "project")
	job_ref = frappe.new_doc("Job Number")
	job_ref.job_type = "Special Project"
	job_ref.job_no = special_project_name
	job_ref.company = company
	job_ref.branch = branch
	job_ref.cost_center = cost_center
	job_ref.profit_center = profit_center
	job_ref.job_open_date = open_date
	job_ref.project = project
	job_ref.insert(ignore_permissions=True)
	frappe.db.set_value("Special Project", special_project_name, "job_number", job_ref.name)
	frappe.db.commit()


@frappe.whitelist()
def charge_scoping_costs(special_project):
	"""Charge all completed scoping activities to the project when it is booked."""
	doc = frappe.get_doc("Special Project", special_project)
	if doc.status not in ("Booked", "Approved", "Planning", "In Progress", "Completed"):
		frappe.throw(_("Project must be Booked or Approved to charge scoping costs."))

	changed = False
	for row in doc.scoping_activities or []:
		if row.status == "Completed" and not row.charged_to_project:
			row.charged_to_project = 1
			row.charged_date = frappe.utils.today()
			changed = True

	if changed:
		doc.save()
	return "Scoping costs charged."


@frappe.whitelist()
def recalculate_all_charges(docname):
	"""Recalculate all Special Project charge lines on this programme."""
	doc = frappe.get_doc("Special Project", docname)
	if not doc.get("charges"):
		return {"success": False, "message": _("No charges found to recalculate")}
	try:
		n = 0
		for charge in doc.charges:
			if hasattr(charge, "calculate_charge_amount"):
				charge.calculate_charge_amount(parent_doc=doc)
				n += 1
		doc.save()
		return {
			"success": True,
			"message": _("Successfully recalculated {0} charges").format(n),
			"charges_recalculated": n,
		}
	except Exception as e:
		frappe.log_error(str(e), "Special Project - Recalculate Charges Error")
		frappe.throw(_("Error recalculating charges: {0}").format(str(e)))


def _job_map_payload(job_type, job_name):
	movements = _collect_movements_from_jobs([frappe._dict(job_type=job_type, job=job_name)])
	map_points = []
	for m in movements:
		oc = m.get("origin_coords")
		if oc and oc.get("lat") is not None and oc.get("lon") is not None:
			map_points.append(
				{
					"lat": float(oc["lat"]),
					"lon": float(oc["lon"]),
					"label": m.get("origin_label", "Origin"),
				}
			)
		dc = m.get("dest_coords")
		if dc and dc.get("lat") is not None and dc.get("lon") is not None:
			tup = (float(dc["lat"]), float(dc["lon"]))
			if not map_points or (map_points[-1].get("lat"), map_points[-1].get("lon")) != tup:
				map_points.append(
					{
						"lat": tup[0],
						"lon": tup[1],
						"label": m.get("dest_label", "Destination"),
					}
				)
	if not map_points:
		return {
			"map_mode": "empty",
			"map_points": [],
			"label": _("No origin/destination coordinates for this job yet."),
		}
	label = f"{job_type} {job_name}"
	road = job_type == "Transport Job"
	if len(map_points) == 1:
		return {
			"map_mode": "pin",
			"map_points": map_points,
			"straight_line": True,
			"label": label,
		}
	return {
		"map_mode": "route",
		"map_points": map_points,
		"straight_line": not road,
		"label": label,
	}


def _format_internal_job_location(row, which):
	"""Display name for location_from / location_to (UNLOCO code or Transport Zone name)."""
	val = getattr(row, "location_from" if which == "from" else "location_to", None)
	if not val:
		return ""
	lt = (getattr(row, "location_type", None) or "").strip()
	if lt == "Transport Zone" and frappe.db.exists("Transport Zone", val):
		zn = frappe.db.get_value("Transport Zone", val, "zone_name")
		return (zn or val).strip()
	return str(val).strip()


def _map_points_from_internal_job_transport_unloco(row):
	"""When no booking: route from UNLOCO location_from → location_to (location_type must be UNLOCO)."""
	if (getattr(row, "location_type", None) or "").strip() != "UNLOCO":
		return []
	from logistics.document_management.dashboard_layout import get_unloco_coords

	map_points = []
	for loc in (getattr(row, "location_from", None), getattr(row, "location_to", None)):
		if not loc:
			continue
		c = get_unloco_coords(loc)
		if not c:
			continue
		pt = {"lat": float(c["lat"]), "lon": float(c["lon"]), "label": c.get("label") or loc}
		if (
			not map_points
			or pt["lat"] != map_points[-1]["lat"]
			or pt["lon"] != map_points[-1]["lon"]
		):
			map_points.append(pt)
	return map_points


def _transport_fallback_route_label(row):
	a = _format_internal_job_location(row, "from")
	b = _format_internal_job_location(row, "to")
	if a or b:
		return f"{a or '—'} → {b or '—'}"
	return _("Transport")


def _internal_job_card_title(row):
	st = (getattr(row, "service_type", None) or "").strip() or _("Line")
	jt = (getattr(row, "job_type", None) or "").strip()
	jn = (getattr(row, "job_no", None) or "").strip()
	if jn and jt:
		return f"{st} · {jt}: {jn}"
	if jn:
		return f"{st} · {jn}"
	if st == "Transport":
		return f"{st} · {_transport_fallback_route_label(row)}"
	if st in ("Air", "Sea"):
		op = (getattr(row, "origin_port", None) or "").strip()
		dp = (getattr(row, "destination_port", None) or "").strip()
		if op or dp:
			return f"{st} · {op or '—'} → {dp or '—'}"
	if st == "Customs" and (getattr(row, "customs_authority", None) or "").strip():
		return f"{st} · {row.customs_authority}"
	if st == "Special Project" and jn:
		return f"{st} · {jn}"
	return st


def _internal_job_card_sub(row):
	parts = []
	st = (getattr(row, "service_type", None) or "").strip()
	if st == "Air":
		for x in (
			getattr(row, "airline", None),
			getattr(row, "freight_agent", None),
			getattr(row, "load_type", None),
			getattr(row, "direction", None),
			getattr(row, "air_house_type", None),
		):
			if x:
				parts.append(str(x).strip())
	elif st == "Sea":
		for x in (
			getattr(row, "shipping_line", None),
			getattr(row, "freight_agent_sea", None),
			getattr(row, "load_type", None),
			getattr(row, "direction", None),
			getattr(row, "sea_house_type", None),
		):
			if x:
				parts.append(str(x).strip())
	elif st == "Transport":
		for x in (
			getattr(row, "transport_template", None),
			getattr(row, "vehicle_type", None),
			getattr(row, "container_type", None),
			getattr(row, "container_no", None),
			getattr(row, "pick_mode", None),
			getattr(row, "drop_mode", None),
		):
			if x:
				parts.append(str(x).strip())
		ltp = (getattr(row, "location_type", None) or "").strip()
		if ltp:
			parts.append(ltp)
		if not (getattr(row, "job_no", None) or "").strip():
			lf = _format_internal_job_location(row, "from")
			lt = _format_internal_job_location(row, "to")
			if lf or lt:
				parts.append(f"{lf or '—'} → {lt or '—'}")
	elif st == "Customs":
		for x in (
			getattr(row, "customs_broker", None),
			getattr(row, "declaration_type", None),
			getattr(row, "customs_charge_category", None),
		):
			if x:
				parts.append(str(x).strip())
	elif st == "Special Project":
		for x in (getattr(row, "sp_equipment_type", None), getattr(row, "sp_handling", None)):
			if x:
				parts.append(str(x).strip())
		sp_site = getattr(row, "sp_site", None)
		if sp_site:
			site_lbl = frappe.db.get_value("Address", sp_site, "address_title")
			parts.append((site_lbl or sp_site)[:120])
		sn = getattr(row, "sp_resource_notes", None)
		if sn:
			parts.append((sn or "")[:120])
	return " · ".join(parts) if parts else "—"


def _map_payload_from_site_address(addr_name):
	"""Single pin on the map from a linked Address (customer site), if lat/lon are set on the address."""
	if not addr_name:
		return None
	try:
		from logistics.transport.api_optimized import get_address_coordinates_batch

		c = (get_address_coordinates_batch([addr_name]) or {}).get(addr_name)
		if c and c.get("lat") is not None and c.get("lon") is not None:
			lbl = frappe.db.get_value("Address", addr_name, "address_title") or addr_name
			return {
				"map_mode": "pin",
				"map_points": [
					{"lat": float(c["lat"]), "lon": float(c["lon"]), "label": lbl},
				],
				"straight_line": True,
				"label": lbl,
			}
	except Exception:
		pass
	return None


def _internal_job_row_map_payload(row):
	"""Map payload for one Internal Job Detail row: resolved job, else ports/locations on the line."""
	op = resolve_internal_job_detail_row_to_operational_ref(row)
	if op:
		return _job_map_payload(op[0], op[1])

	st = (getattr(row, "service_type", None) or "").strip()
	if st == "Special Project":
		site = getattr(row, "sp_site", None)
		if site:
			pl = _map_payload_from_site_address(site)
			if pl:
				return pl

	if st in ("Air", "Sea"):
		try:
			from logistics.document_management.dashboard_layout import get_unloco_coords

			o_code = getattr(row, "origin_port", None)
			d_code = getattr(row, "destination_port", None)
			o = get_unloco_coords(o_code) if o_code else None
			d = get_unloco_coords(d_code) if d_code else None
			map_points = []
			if o:
				map_points.append({"lat": float(o["lat"]), "lon": float(o["lon"]), "label": o.get("label") or o_code or "Origin"})
			if d and (
				not map_points
				or float(d["lat"]) != map_points[-1].get("lat")
				or float(d["lon"]) != map_points[-1].get("lon")
			):
				map_points.append({"lat": float(d["lat"]), "lon": float(d["lon"]), "label": d.get("label") or d_code or "Destination"})
			if len(map_points) == 1:
				return {
					"map_mode": "pin",
					"map_points": map_points,
					"straight_line": True,
					"label": o_code or d_code or _("Port"),
				}
			if len(map_points) >= 2:
				lbl = f"{o_code or '—'} → {d_code or '—'}"
				return {
					"map_mode": "route",
					"map_points": map_points,
					"straight_line": True,
					"label": lbl,
				}
		except Exception:
			pass

	if st == "Transport":
		tpts = _map_points_from_internal_job_transport_unloco(row)
		lbl = _transport_fallback_route_label(row)
		if len(tpts) >= 2:
			return {
				"map_mode": "route",
				"map_points": tpts,
				"straight_line": False,
				"label": lbl,
			}
		if len(tpts) == 1:
			return {
				"map_mode": "pin",
				"map_points": tpts,
				"straight_line": True,
				"label": lbl,
			}

	return {
		"map_mode": "empty",
		"map_points": [],
		"label": _("Link a booking/order, set Air/Sea ports, or set Location From/To (UNLOCO) for Transport to see the map."),
	}


_LIFECYCLE_STAGE_COLORS = {
	"Pre-Show": "#14b8a6",
	"Logistics": "#ec4899",
	"On-Site": "#eab308",
	"Post-Show": "#a855f7",
	"Closed": "#64748b",
}


def _sp_dash_card_html(title, sub, badge, kind="task", map_index=None):
	border = "#17a2b8" if kind == "job" else "#667eea"
	idx_attr = f' data-sp-map-idx="{int(map_index)}"' if map_index is not None else ""
	return (
		f'<div class="sp-dash-card" style="border-left-color: {border};" role="button" tabindex="0"{idx_attr}>'
		f'<div class="sp-dash-card-title">{escape_html(title)}</div>'
		f'<div class="sp-dash-card-sub">{escape_html(sub)}</div>'
		f'<span class="sp-dash-card-badge">{escape_html(badge)}</span></div>'
	)


def _lifecycle_collapsible_group_html(stage, entries, current_stage):
	"""Collapsible lifecycle section wrapping dashboard job cards."""
	color = _LIFECYCLE_STAGE_COLORS.get(stage, "#94a3b8")
	current = (current_stage or "Pre-Show").strip()
	is_current = stage == current
	collapsed = "" if is_current else " collapsed"
	chevron = "fa-chevron-down" if is_current else "fa-chevron-right"
	current_badge = (
		f' <span class="badge badge-primary" style="margin-left:6px;font-size:10px">{_("Current")}</span>'
		if is_current
		else ""
	)
	body = (
		"".join(e["card_html"] for e in entries)
		if entries
		else f'<div class="text-muted small" style="padding:6px 8px 4px;">{escape_html(_("No jobs in this stage"))}</div>'
	)
	return (
		f'<div class="sp-dash-lifecycle-group{collapsed}" data-stage="{escape_html(stage)}" '
		f'style="margin-bottom:10px;border:1px solid #e9ecef;border-radius:8px;border-left:4px solid {color};overflow:hidden">'
		f'<div class="sp-dash-lifecycle-group-header" role="button" tabindex="0" '
		f'style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:#f8f9fa;cursor:pointer;user-select:none">'
		f'<i class="fa {chevron} sp-dash-lifecycle-chevron" style="width:12px;font-size:11px;color:#6c757d"></i>'
		f"<strong style=\"font-size:13px\">{escape_html(stage)}{current_badge}</strong>"
		f'<span class="text-muted small" style="margin-left:auto">{len(entries)} {_("jobs")}</span>'
		f"</div>"
		f'<div class="sp-dash-lifecycle-group-body" style="padding:8px 10px 6px">{body}</div>'
		f"</div>"
	)


def _build_lifecycle_grouped_job_cards_sidebar(card_entries, current_stage):
	"""Group Route-tab job cards by lifecycle stage (collapsible)."""
	from logistics.utils.lifecycle_stage import FOR_SPECIAL_PROJECT, get_lifecycle_stages

	stage_names = get_lifecycle_stages(FOR_SPECIAL_PROJECT)
	by_stage = {name: [] for name in stage_names}
	unassigned = []

	for entry in card_entries:
		stage = (entry.get("lifecycle_stage") or "").strip()
		if stage and stage in by_stage:
			by_stage[stage].append(entry)
		else:
			unassigned.append(entry)

	parts = [
		_lifecycle_collapsible_group_html(stage, by_stage.get(stage) or [], current_stage)
		for stage in stage_names
	]
	if unassigned:
		parts.append(_lifecycle_collapsible_group_html(_("Unassigned"), unassigned, current_stage))
	return "".join(parts)


@frappe.whitelist()
def get_dashboard_html(special_project):
	"""Dashboard tab: Transport Job style header/tabs; Route = internal job lines + map (ports or shipment route)."""
	if not special_project:
		return "<div class='alert alert-info'>Save the project to view the dashboard.</div>"
	try:
		from logistics.air_freight.doctype.air_booking.air_booking_dashboard import _milestones_ro_panel_html
		from logistics.document_management.dashboard_layout import render_special_project_interactive_route_tab_html
		from logistics.document_management.logistics_form_dashboard import (
			build_customer_hero_html,
			build_special_project_meta_cluster_html,
			build_special_project_route_panel_html,
			render_logistics_form_dashboard_html,
		)
		from logistics.utils.sales_quote_validity import get_sales_quote_validity_dashboard_html

		doc = frappe.get_doc("Special Project", special_project)
		quote_html = get_sales_quote_validity_dashboard_html(doc) or ""

		status = doc.status or "Draft"
		job_rows = doc.get("lifecycle_jobs") or []
		job_refs = job_refs_from_lifecycle_jobs(doc)
		charges = doc.get("charges") or []
		from logistics.special_projects.special_project_packages import (
			validate_packages,
		)

		validate_packages(doc)
		materials = doc.get("packages") or []
		mat_count = len(materials)
		short_count = sum(1 for m in materials if flt(getattr(m, "qty_short", 0)) > 0)
		on_site_pct = ""
		if mat_count:
			total_req = sum(flt(getattr(m, "qty_required", 0)) for m in materials)
			total_on = sum(flt(getattr(m, "qty_on_site", 0)) for m in materials)
			if total_req > 0:
				on_site_pct = f"{min(100, int(100 * total_on / total_req))}%"
		planned_cost = sum(flt(a.planned_cost or 0) for a in job_rows)
		actual_cost = sum(flt(a.actual_cost or 0) for a in job_rows)
		actual_rev = sum(flt(a.actual_revenue or 0) for a in job_rows)

		def fmt(v):
			return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

		header_items = [
			("Status", status),
			("Job lines", str(len(job_rows))),
			("Logistics jobs", str(len(job_refs))),
			("Budget", fmt(planned_cost)),
			("Actual Revenue", fmt(actual_rev)),
			("Site materials", str(mat_count)),
			("Materials short", str(short_count)),
			("On-site fill", on_site_pct or "—"),
			("Charges", str(len(charges))),
		]
		if doc.priority:
			header_items.append(("Priority", doc.priority))

		header_items_for_hero = list(header_items)
		hero_html = build_customer_hero_html(doc, header_items_for_hero)
		route_panel_html = build_special_project_route_panel_html(doc)
		meta_cluster_html = build_special_project_meta_cluster_html(doc)

		# Aggregated milestones from linked logistics jobs
		all_milestones = []
		for row in job_refs:
			jt = (row.job_type or "").strip()
			jn = (row.job or "").strip()
			if not jt or not jn:
				continue
			ms = frappe.get_all(
				"Job Milestone",
				filters={"job_type": jt, "job_number": jn},
				fields=["name", "milestone", "status", "planned_start", "planned_end", "actual_start", "actual_end"],
				order_by="planned_start",
			)
			for m in ms:
				all_milestones.append(frappe._dict(m))
		all_milestones.sort(key=lambda x: (x.planned_start or frappe.utils.now_datetime(), x.name or ""))

		milestone_details = {}
		if all_milestones:
			names = [m.milestone for m in all_milestones if m.milestone]
			if names:
				for lm in frappe.get_all(
					"Logistics Milestone", filters={"name": ["in", names]}, fields=["name", "description"]
				):
					milestone_details[lm.name] = lm.description or lm.name

		milestone_rows = list(all_milestones)
		ms_inner = _milestones_ro_panel_html(
			milestone_rows,
			milestone_details,
			doc.name or "",
			scroll_doctype="Special Project",
			scroll_field="milestone_html",
			empty_hint_html='<p class="text-muted ab-tab-empty" style="margin:0;">'
			+ _("No milestones from linked logistics jobs. Add jobs under <strong>Jobs</strong>.")
			+ "</p>",
		)
		n_ms = len(milestone_rows)
		done_ms = sum(1 for m in milestone_rows if str(m.status or "").strip() == "Completed")

		card_entries = []
		map_payloads = []

		lines_ordered = sorted(job_rows, key=lambda r: int(getattr(r, "idx", None) or 0))
		for map_index, row in enumerate(lines_ordered):
			payload = _internal_job_row_map_payload(row)
			map_payloads.append(payload)
			title = _internal_job_card_title(row)[:200]
			sub = _internal_job_card_sub(row)
			pc = getattr(row, "planned_cost", None)
			pr = getattr(row, "planned_revenue", None)
			if pc or pr:
				bits = []
				if pc:
					bits.append(_("Planned cost {0}").format(fmt(pc)))
				if pr:
					bits.append(_("Planned revenue {0}").format(fmt(pr)))
				fin = " · ".join(bits)
				if sub and sub != "—":
					sub = sub + " · " + fin
				else:
					sub = fin
			op = resolve_internal_job_detail_row_to_operational_ref(row)
			badge = (
				_("{0} (linked)").format(op[0])
				if op
				else (getattr(row, "service_type", None) or _("Job line"))
			)
			kind = "job" if op or (payload.get("map_points") or []) else "task"
			card_entries.append(
				{
					"lifecycle_stage": (getattr(row, "lifecycle_stage", None) or "").strip(),
					"card_html": _sp_dash_card_html(
						title[:200],
						sub,
						badge,
						kind=kind,
						map_index=map_index,
					),
				}
			)

		if not card_entries:
			cards_sidebar_html = (
				f'<div class="text-muted" style="padding:8px;">'
				f'{escape_html(_("Add lines under Lifecycle jobs to see them here."))}</div>'
			)
			map_payloads.append({"map_mode": "empty", "map_points": [], "label": _("Nothing to show on the map yet.")})
		else:
			cards_sidebar_html = _build_lifecycle_grouped_job_cards_sidebar(
				card_entries, doc.lifecycle_stage
			)

		route_tab_override_html = render_special_project_interactive_route_tab_html(
			"sp-form-dash",
			map_payloads,
			cards_sidebar_html,
		)

		cfg = {
			"doctype": "Special Project",
			"map_id_prefix": "sp-form-dash",
			"header_items": header_items_for_hero,
			"hero_html": hero_html,
			"route_panel_html": route_panel_html,
			"meta_cluster_html": meta_cluster_html,
			"route_tab_override_html": route_tab_override_html,
			"milestones_tab_inner_html": ms_inner,
			"milestone_count_override": n_ms,
			"milestone_done_override": done_ms,
			"scroll_doctype": "Special Project",
			"scroll_field": "milestone_html",
			"ring_status_from": "workflow",
			"ring_status_field": "status",
			"include_default_dg": False,
			"map_points": [],
			"map_segments": None,
		}
		dash = render_logistics_form_dashboard_html(doc, cfg)
		return quote_html + dash
	except Exception as e:
		frappe.log_error(f"Special Project get_dashboard_html: {str(e)}", "Special Project Dashboard")
		return "<div class='alert alert-warning'>Error loading dashboard.</div>"


def _get_unloco_coords(unloco_code):
	"""Get (lat, lon) for UNLOCO code, or None."""
	if not unloco_code:
		return None
	try:
		coords = frappe.db.get_value("UNLOCO", unloco_code, ["latitude", "longitude"], as_dict=True)
		if coords and coords.latitude is not None and coords.longitude is not None:
			lat = float(coords.latitude)
			lon = float(coords.longitude)
			if -90 <= lat <= 90 and -180 <= lon <= 180:
				return (lat, lon)
	except Exception:
		pass
	return None


def _collect_movements_from_jobs(jobs):
	"""Collect movement points (origin/dest) from logistics job refs. Each row: job_type (DocType), job (name)."""
	movements = []
	address_names = []

	for row in jobs or []:
		job_type = (row.job_type or "").strip()
		job_name = (row.job or "").strip()
		if not job_type or not job_name:
			continue

		try:
			if job_type == "Transport Job":
				job_doc = frappe.get_doc("Transport Job", job_name)
				legs = job_doc.get("legs") or []
				for leg in legs:
					pa = leg.get("pick_address")
					da = leg.get("drop_address")
					if pa:
						address_names.append(pa)
					if da:
						address_names.append(da)
					if pa or da:
						movements.append({
							"job_type": job_type,
							"job_name": job_name,
							"origin_addr": pa,
							"dest_addr": da,
							"origin_label": pa or "Pick",
							"dest_label": da or "Drop",
						})
			elif job_type == "Air Shipment":
				vals = frappe.db.get_value(
					"Air Shipment", job_name,
					["origin_port", "destination_port"],
					as_dict=True
				)
				if vals and (vals.origin_port or vals.destination_port):
					movements.append({
						"job_type": job_type,
						"job_name": job_name,
						"origin_unloco": vals.origin_port,
						"dest_unloco": vals.destination_port,
						"origin_label": vals.origin_port or "Origin",
						"dest_label": vals.destination_port or "Destination",
					})
			elif job_type == "Sea Shipment":
				vals = frappe.db.get_value(
					"Sea Shipment", job_name,
					["origin_port", "destination_port"],
					as_dict=True
				)
				if vals and (vals.origin_port or vals.destination_port):
					movements.append({
						"job_type": job_type,
						"job_name": job_name,
						"origin_unloco": vals.origin_port,
						"dest_unloco": vals.destination_port,
						"origin_label": vals.origin_port or "Origin",
						"dest_label": vals.destination_port or "Destination",
					})
			elif job_type == "Declaration":
				vals = frappe.db.get_value(
					"Declaration", job_name,
					["port_of_loading", "port_of_discharge"],
					as_dict=True
				)
				if vals and (vals.port_of_loading or vals.port_of_discharge):
					movements.append({
						"job_type": job_type,
						"job_name": job_name,
						"origin_unloco": vals.port_of_loading,
						"dest_unloco": vals.port_of_discharge,
						"origin_label": vals.port_of_loading or "Port of Loading",
						"dest_label": vals.port_of_discharge or "Port of Discharge",
					})
		except Exception:
			continue

	# Resolve UNLOCO coords
	for m in movements:
		if m.get("origin_unloco"):
			c = _get_unloco_coords(m["origin_unloco"])
			m["origin_coords"] = {"lat": c[0], "lon": c[1]} if c else None
		else:
			m["origin_coords"] = None
		if m.get("dest_unloco"):
			c = _get_unloco_coords(m["dest_unloco"])
			m["dest_coords"] = {"lat": c[0], "lon": c[1]} if c else None
		else:
			m["dest_coords"] = None

	# Batch resolve address coords (dedupe for efficiency)
	addr_coords = {}
	if address_names:
		try:
			from logistics.transport.api_optimized import get_address_coordinates_batch
			addr_coords = get_address_coordinates_batch(list(set(address_names))) or {}
		except Exception:
			addr_coords = {}

	for m in movements:
		if m.get("origin_addr"):
			c = addr_coords.get(m["origin_addr"]) if addr_coords else None
			m["origin_coords"] = c
		if m.get("dest_addr"):
			c = addr_coords.get(m["dest_addr"]) if addr_coords else None
			m["dest_coords"] = c

	return movements


def _get_movement_map_html_fragment(special_project):
	"""Return map HTML fragment for embedding in dashboard. Used by get_dashboard_html and get_movement_map_html."""
	if not special_project:
		return "<div class='alert alert-info'>Save the project to view the map.</div>"
	try:
		doc = frappe.get_doc("Special Project", special_project)
		movements = _collect_movements_from_jobs(job_refs_from_lifecycle_jobs(doc))

		# Filter to movements that have at least one valid coordinate
		valid_movements = [
			m for m in movements
			if (m.get("origin_coords") or m.get("dest_coords"))
		]
		if not valid_movements:
			return """
			<div class="map-container" style="padding: 20px;">
				<div class="alert alert-info">
					<i class="fa fa-map"></i> No movement jobs with coordinates found.
					Add Transport Jobs, Air Shipments, Sea Shipments, or Declarations with origin/destination locations.
				</div>
			</div>
			"""

		# Build JSON for client
		import json
		movements_json = json.dumps(valid_movements)

		# Map renderer from Logistics Settings, fallback to Transport Settings (same as dashboard_layout)
		map_renderer = None
		try:
			ls = frappe.get_single("Logistics Settings")
			if ls:
				map_renderer = getattr(ls, "map_renderer", None)
			if not map_renderer or not str(map_renderer).strip():
				ts = frappe.get_single("Transport Settings")
				if ts:
					map_renderer = getattr(ts, "map_renderer", None)
		except Exception:
			pass
		if not map_renderer or not str(map_renderer).strip():
			map_renderer = "OpenStreetMap"

		html = f"""
		<div class="map-container" style="margin: 10px 0;">
			<div style="width: 100%; height: 450px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative;">
				<div id="sp-movement-map" style="width: 100%; height: 100%;"></div>
				<div id="sp-movement-map-fallback" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); display: flex; align-items: center; justify-content: center; flex-direction: column;">
					<div style="text-align: center; color: #6c757d;">
						<i class="fa fa-map" style="font-size: 32px; margin-bottom: 15px;"></i>
						<div style="font-size: 18px; font-weight: 500; margin-bottom: 10px;">Movement Map</div>
						<div style="font-size: 12px; color: #999;">Loading map...</div>
					</div>
				</div>
			</div>
			<div class="text-muted small" style="margin-top: 10px;">Jobs with movements: Transport, Air, Sea, Declaration</div>
		</div>
		<script>
		(function() {{
			const movements = {movements_json};
			const mapRenderer = {json.dumps(map_renderer)};
			const mapId = 'sp-movement-map';
			const fallbackId = 'sp-movement-map-fallback';

			function showFallback() {{
				const fallback = document.getElementById(fallbackId);
				if (fallback) fallback.style.display = 'flex';
			}}
			function hideFallback() {{
				const fallback = document.getElementById(fallbackId);
				if (fallback) fallback.style.display = 'none';
			}}

			function initMap() {{
				const el = document.getElementById(mapId);
				if (!el) {{ setTimeout(initMap, 100); return; }}
				try {{
					const points = [];
					movements.forEach(function(m) {{
						if (m.origin_coords) points.push([m.origin_coords.lat, m.origin_coords.lon, m.origin_label || 'Origin', m.job_type, m.job_name]);
						if (m.dest_coords) points.push([m.dest_coords.lat, m.dest_coords.lon, m.dest_label || 'Dest', m.job_type, m.job_name]);
					}});
					if (points.length === 0) {{ showFallback(); return; }}

					const renderer = (mapRenderer || '').toLowerCase();
					if (renderer === 'google maps') {{
						initGoogleMap(el, points); return;
					}}
					if (renderer === 'mapbox' || renderer === 'maplibre') {{
						initMapLibre(el, points); return;
					}}
					initLeaflet(el, points);
				}} catch (e) {{
					console.error('Movement map init error:', e);
					showFallback();
				}}
			}}

			function initLeaflet(el, points) {{
				if (!window.L) {{
					const css = document.createElement('link');
					css.rel = 'stylesheet';
					css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
					document.head.appendChild(css);
					const script = document.createElement('script');
					script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
					script.onload = function() {{ initLeaflet(el, points); }};
					document.head.appendChild(script);
					return;
				}}
				const map = L.map(mapId).setView([points[0][0], points[0][1]], 4);
				L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '© OpenStreetMap contributors' }}).addTo(map);
				const group = [];
				points.forEach(function(p) {{
					const m = L.marker([p[0], p[1]]).addTo(map);
					m.bindPopup('<b>' + (p[2] || '') + '</b><br>' + (p[3] || '') + ': ' + (p[4] || ''));
					group.push(m);
				}});
				if (group.length) {{
					const bounds = L.latLngBounds(group.map(function(m) {{ return m.getLatLng(); }}));
					map.fitBounds(bounds.pad(0.1));
				}}
				hideFallback();
			}}

			function initMapLibre(el, points) {{
				if (!window.maplibregl) {{
					const css = document.createElement('link');
					css.rel = 'stylesheet';
					css.href = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css';
					document.head.appendChild(css);
					const script = document.createElement('script');
					script.src = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js';
					script.onload = function() {{ initMapLibre(el, points); }};
					document.head.appendChild(script);
					return;
				}}
				const centerLat = points.reduce(function(s, p) {{ return s + p[0]; }}, 0) / points.length;
				const centerLon = points.reduce(function(s, p) {{ return s + p[1]; }}, 0) / points.length;
				const map = new maplibregl.Map({{
					container: mapId,
					style: {{ version: 8, sources: {{ 'osm': {{ type: 'raster', tiles: ['https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'], tileSize: 256 }} }}, layers: [{{ id: 'osm', type: 'raster', source: 'osm' }}] }},
					center: [centerLon, centerLat],
					zoom: 4
				}});
				points.forEach(function(p) {{
					const marker = new maplibregl.Marker({{ color: 'blue' }}).setLngLat([p[1], p[0]]).setPopup(new maplibregl.Popup().setHTML('<b>' + (p[2] || '') + '</b><br>' + (p[3] || '') + ': ' + (p[4] || ''))).addTo(map);
				}});
				if (points.length > 1) {{
					const lngs = points.map(function(p) {{ return p[1]; }});
					const lats = points.map(function(p) {{ return p[0]; }});
					map.fitBounds([[Math.min.apply(null, lngs), Math.min.apply(null, lats)], [Math.max.apply(null, lngs), Math.max.apply(null, lats)]], {{ padding: 50 }});
				}}
				hideFallback();
			}}

			function initGoogleMap(el, points) {{
				showFallback();
			}}

			if (document.readyState === 'loading') {{
				document.addEventListener('DOMContentLoaded', initMap);
			}} else {{
				initMap();
			}}
		}})();
		</script>
		"""
		return html
	except Exception as e:
		frappe.log_error(f"Special Project get_movement_map_html: {str(e)}", "Special Project Map")
		return "<div class='alert alert-warning'>Error loading map.</div>"


@frappe.whitelist()
def get_movement_map_html(special_project):
	"""Whitelisted API: returns map HTML (same as dashboard-embedded fragment)."""
	return _get_movement_map_html_fragment(special_project)


@frappe.whitelist()
def get_cost_revenue_summary(special_project):
	"""Return HTML for Cost & Revenue Summary from project job lines."""
	if not special_project:
		return ""
	doc = frappe.get_doc("Special Project", special_project)
	rows = doc.get("lifecycle_jobs") or []

	planned_cost = sum((a.planned_cost or 0) for a in rows)
	actual_cost = sum((a.actual_cost or 0) for a in rows)
	planned_revenue = sum((a.planned_revenue or 0) for a in rows)
	actual_revenue = sum((a.actual_revenue or 0) for a in rows)
	planned_margin = planned_revenue - planned_cost if planned_revenue or planned_cost else None
	actual_margin = actual_revenue - actual_cost if actual_revenue or actual_cost else None

	def fmt(v):
		return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

	rows = [
		f"<tr><td>{_('Planned Cost')}</td><td class='text-right'>{fmt(planned_cost)}</td>"
		f"<td>{_('Planned Revenue')}</td><td class='text-right'>{fmt(planned_revenue)}</td></tr>",
		f"<tr><td>{_('Actual Cost')}</td><td class='text-right'>{fmt(actual_cost)}</td>"
		f"<td>{_('Actual Revenue')}</td><td class='text-right'>{fmt(actual_revenue)}</td></tr>",
		f"<tr><td>{_('Planned Margin')}</td><td class='text-right'>{fmt(planned_margin)}</td>"
		f"<td>{_('Actual Margin')}</td><td class='text-right'>{fmt(actual_margin)}</td></tr>",
	]
	html = f'<table class="table table-bordered table-sm" style="max-width: 500px;"><tbody>{"".join(rows)}</tbody></table>'
	return html


def _packages_summary_qty_label(qty: float) -> str:
	value = flt(qty)
	if value == int(value):
		return str(int(value))
	return str(value)


_STAGE_PALETTE: list[tuple[str, str]] = [
	("#6366F1", "#A5B4FC"),
	("#06B6D4", "#67E8F9"),
	("#10B981", "#6EE7B7"),
	("#F59E0B", "#FCD34D"),
	("#EF4444", "#FCA5A5"),
	("#8B5CF6", "#C4B5FD"),
	("#EC4899", "#F9A8D4"),
	("#14B8A6", "#5EEAD4"),
]


def _stage_color_pair(idx: int) -> tuple[str, str]:
	return _STAGE_PALETTE[idx % len(_STAGE_PALETTE)]


def _packages_summary_row_status(
	stage_qtys: list[float],
	required: float,
	final_idx: int | None,
	*,
	is_always_along: bool,
) -> tuple[str, str]:
	"""Return (status_key, status_label) for a package row."""
	if is_always_along:
		return ("aa", _("Always-Along"))
	req = flt(required)
	final_qty = flt(stage_qtys[final_idx]) if (final_idx is not None and final_idx < len(stage_qtys)) else 0.0
	if req > 0 and final_qty >= req:
		return ("complete", _("Complete"))
	if any(flt(q) > 0 for q in stage_qtys):
		return ("in_progress", _("In Progress"))
	return ("pending", _("Pending"))


def _packages_summary_cell_html(
	qty: float,
	required: float,
	*,
	stage_idx: int,
	is_final_stage: bool = False,
	is_always_along: bool = False,
) -> str:
	"""Render one stage cell: numeric qty + thin fill bar (width = qty/required)."""
	stage_cls = f"sp-pfn-stage-{stage_idx % len(_STAGE_PALETTE)}"
	if is_always_along:
		return (
			f'<span class="sp-pfn-cell sp-pfn-cell-stage sp-pfn-cell-na {stage_cls}" '
			f'aria-label="N/A">'
			f'<span class="sp-pfn-qty">'
			f'<span class="sp-pfn-qty-num sp-pfn-qty-na">&mdash;</span>'
			f'<span class="sp-pfn-cell-check sp-pfn-cell-check--empty" aria-hidden="true"></span>'
			f"</span>"
			f'<span class="sp-pfn-bar" aria-hidden="true">'
			f'<span class="sp-pfn-bar-fill" style="width:0%"></span></span>'
			f"</span>"
		)
	qty_val = flt(qty)
	req_val = flt(required)
	if qty_val <= 0:
		return (
			f'<span class="sp-pfn-cell sp-pfn-cell-stage sp-pfn-cell-empty {stage_cls}">'
			'<span class="sp-pfn-qty">'
			'<span class="sp-pfn-qty-num sp-pfn-qty-zero">0</span>'
			'<span class="sp-pfn-cell-check sp-pfn-cell-check--empty" aria-hidden="true"></span>'
			"</span>"
			'<span class="sp-pfn-bar"><span class="sp-pfn-bar-fill" style="width:0%"></span></span>'
			"</span>"
		)
	pct = 0.0 if req_val <= 0 else min(100.0, qty_val / req_val * 100.0)
	complete = req_val > 0 and qty_val >= req_val
	complete_cls = " sp-pfn-cell-complete" if complete else ""
	final_cls = " sp-pfn-cell-final" if is_final_stage else ""
	check_icon = (
		'<span class="sp-pfn-cell-check" aria-hidden="true">&#10003;</span>'
		if complete
		else '<span class="sp-pfn-cell-check sp-pfn-cell-check--empty" aria-hidden="true"></span>'
	)
	label = escape_html(_packages_summary_qty_label(qty_val))
	return (
		f'<span class="sp-pfn-cell sp-pfn-cell-stage {stage_cls}{complete_cls}{final_cls}">'
		f'<span class="sp-pfn-qty"><span class="sp-pfn-qty-num">{label}</span>{check_icon}</span>'
		f'<span class="sp-pfn-bar"><span class="sp-pfn-bar-fill" style="width:{pct:.2f}%"></span></span>'
		"</span>"
	)


def _packages_summary_status_pill_html(status_key: str, status_label: str) -> str:
	return (
		f'<span class="sp-pfn-cell sp-pfn-cell-status">'
		f'<span class="sp-pfn-pill sp-pfn-pill-{escape_html(status_key)}">{escape_html(status_label)}</span>'
		f"</span>"
	)


def _packages_summary_row_html(
	row_no: int,
	label: str,
	required: float,
	stage_qtys: list[float],
	*,
	is_always_along: bool,
	final_stage_idx: int | None,
) -> str:
	required_cell: str
	if is_always_along:
		required_cell = (
			'<span class="sp-pfn-cell sp-pfn-cell-required">'
			'<span class="sp-pfn-badge" title="Always-along package">AA</span>'
			"</span>"
		)
	else:
		required_cell = (
			'<span class="sp-pfn-cell sp-pfn-cell-required">'
			f'<span class="sp-pfn-qty">{escape_html(_packages_summary_qty_label(required))}</span>'
			"</span>"
		)
	stage_cells = "".join(
		_packages_summary_cell_html(
			q,
			required,
			stage_idx=s_idx,
			is_final_stage=(final_stage_idx is not None and s_idx == final_stage_idx),
			is_always_along=is_always_along,
		)
		for s_idx, q in enumerate(stage_qtys)
	)
	status_key, status_label = _packages_summary_row_status(
		stage_qtys, required, final_stage_idx, is_always_along=is_always_along
	)
	status_cell = _packages_summary_status_pill_html(status_key, status_label)
	return (
		f'<div class="sp-pfn-row" data-status="{status_key}">'
		f'<span class="sp-pfn-cell sp-pfn-cell-rowno">'
		f'<span class="sp-pfn-rowno">{row_no}</span></span>'
		f'<span class="sp-pfn-cell sp-pfn-cell-package sp-pfn-package" title="{label}">{label}</span>'
		f"{required_cell}"
		f"{stage_cells}"
		f"{status_cell}"
		f"</div>"
	)


def _packages_summary_kpi_card_html(
	label: str,
	value: str,
	sub: str,
	accent_color: str,
	*,
	progress_pct: float | None = None,
	icon: str | None = None,
) -> str:
	icon_html = (
		f'<span class="sp-pfn-kpi-icon" aria-hidden="true">{icon}</span>' if icon else ""
	)
	bar_html = ""
	if progress_pct is not None:
		pct = max(0.0, min(100.0, float(progress_pct)))
		bar_html = (
			'<div class="sp-pfn-kpi-bar">'
			f'<div class="sp-pfn-kpi-bar-fill" style="width:{pct:.2f}%"></div>'
			"</div>"
		)
	return (
		f'<div class="sp-pfn-kpi" style="--sp-kpi-accent: {accent_color}">'
		f'<div class="sp-pfn-kpi-top">'
		f'<div class="sp-pfn-kpi-label">{escape_html(label)}</div>'
		f"{icon_html}"
		f"</div>"
		f'<div class="sp-pfn-kpi-value">{escape_html(value)}</div>'
		f"{bar_html}"
		f'<div class="sp-pfn-kpi-sub">{escape_html(sub)}</div>'
		"</div>"
	)


def _packages_summary_stage_card_html(
	stage_idx: int,
	stage: dict,
	qty: float,
	total_required: float,
	*,
	is_final: bool,
) -> str:
	dark, light = _stage_color_pair(stage_idx)
	pct = 0.0 if total_required <= 0 else min(100.0, qty / total_required * 100.0)
	pct_label = f"{pct:.0f}%" if total_required > 0 else "—"
	name = escape_html(stage.get("name") or "")
	desc = escape_html(stage.get("description") or stage.get("name") or "")
	closed = bool(stage.get("is_closed"))
	tags: list[str] = []
	if closed:
		tags.append(
			'<span class="sp-pfn-stage-tag sp-pfn-stage-tag-closed" title="Closed/final stage">'
			f'{escape_html(_("Closed"))}</span>'
		)
	if is_final:
		tags.append(
			'<span class="sp-pfn-stage-tag sp-pfn-stage-tag-final" title="Used for overall % complete">'
			f'{escape_html(_("Final"))}</span>'
		)
	tags_html = (
		'<span class="sp-pfn-stage-tags">' + "".join(tags) + "</span>" if tags else ""
	)
	qty_label = escape_html(_packages_summary_qty_label(qty))
	req_label = escape_html(_packages_summary_qty_label(total_required))
	return (
		f'<div class="sp-pfn-stage-card" '
		f'style="--sp-stage-color: {dark}; --sp-stage-color-light: {light};" '
		f'title="{desc}">'
		f'<div class="sp-pfn-stage-card-head">'
		f'<span class="sp-pfn-stage-dot"></span>'
		f'<span class="sp-pfn-stage-card-name">{name}</span>'
		f"{tags_html}"
		f"</div>"
		f'<div class="sp-pfn-stage-card-body">'
		f'<span class="sp-pfn-stage-card-qty">{qty_label}</span>'
		f'<span class="sp-pfn-stage-card-pct">{pct_label}</span>'
		f"</div>"
		f'<div class="sp-pfn-stage-card-meter">'
		f'<div class="sp-pfn-stage-card-fill" style="width:{pct:.2f}%"></div>'
		f"</div>"
		f'<div class="sp-pfn-stage-card-foot">'
		f'{escape_html(_("of {0} required").format(req_label))}'
		f"</div>"
		f"</div>"
	)


def _packages_summary_stage_pipeline_html(
	stages: list[dict],
	per_stage_totals: list[float],
	total_required: float,
	final_idx: int | None,
) -> str:
	if not stages:
		return ""
	cards: list[str] = []
	for i, stage in enumerate(stages):
		qty = per_stage_totals[i] if i < len(per_stage_totals) else 0.0
		cards.append(
			_packages_summary_stage_card_html(
				i,
				stage,
				qty,
				total_required,
				is_final=(final_idx is not None and i == final_idx),
			)
		)
	return (
		'<div class="sp-pfn-pipeline-wrap">'
		'<div class="sp-pfn-pipeline-head">'
		f'<span class="sp-pfn-pipeline-title">{escape_html(_("Stage Throughput"))}</span>'
		f'<span class="sp-pfn-pipeline-sub">{escape_html(_("Delivered units per lifecycle stage vs total required"))}</span>'
		"</div>"
		'<div class="sp-pfn-pipeline">'
		+ "".join(cards)
		+ "</div></div>"
	)


def _packages_summary_per_stage_delivered(
	sp_doc: Any, materials: list, stages: list[dict[str, Any]]
) -> list[list[float]]:
	"""Return, for each material row, a list of delivered qty per lifecycle stage (same order).

	Per-stage qty = sum of posted, non-cancelled receipts matching the material row
	(via package_row -> warehouse_item -> commodity -> description fallback) whose
	lifecycle_stage equals that stage's name.
	"""
	from logistics.special_projects.special_project_packages import (
		POSTED_RECEIPT_STATUS,
		_norm,
		_norm_desc,
		cint_safe,
	)

	stage_names = [s["name"] for s in stages]
	stage_idx = {name: i for i, name in enumerate(stage_names)}
	n_mats = len(materials)
	out = [[0.0 for _ in stage_names] for _ in range(n_mats)]

	idx_to_row = {i + 1: m for i, m in enumerate(materials)}
	wh_to_idx: dict[str, int] = {}
	commodity_to_idx: dict[str, int] = {}
	desc_to_idx: dict[str, int] = {}
	for i, m in enumerate(materials):
		if cint_safe(getattr(m, "include_on_create", 0)):
			continue
		wh = _norm(getattr(m, "warehouse_item", None))
		if wh and wh not in wh_to_idx:
			wh_to_idx[wh] = i
		commodity = _norm(getattr(m, "commodity", None))
		if commodity and commodity not in commodity_to_idx:
			commodity_to_idx[commodity] = i
		desc = _norm_desc(getattr(m, "description", None))
		if desc and desc not in desc_to_idx:
			desc_to_idx[desc] = i

	for rc in getattr(sp_doc, "deliveries", None) or []:
		status = getattr(rc, "status", None) or POSTED_RECEIPT_STATUS
		if status != POSTED_RECEIPT_STATUS:
			continue
		qty = flt(getattr(rc, "qty_received", 0))
		if qty <= 0:
			continue
		stage = _norm(getattr(rc, "lifecycle_stage", None))
		s_idx = stage_idx.get(stage)
		if s_idx is None:
			continue
		row_idx = cint_safe(getattr(rc, "package_row", None))
		mat_pos: int | None = None
		if row_idx and row_idx in idx_to_row:
			candidate = idx_to_row[row_idx]
			if not cint_safe(getattr(candidate, "include_on_create", 0)):
				mat_pos = row_idx - 1
		if mat_pos is None:
			wh = _norm(getattr(rc, "warehouse_item", None))
			if wh and wh in wh_to_idx:
				mat_pos = wh_to_idx[wh]
		if mat_pos is None:
			commodity = _norm(getattr(rc, "commodity", None))
			if commodity and commodity in commodity_to_idx:
				mat_pos = commodity_to_idx[commodity]
		if mat_pos is None:
			desc = _norm_desc(getattr(rc, "description", None))
			if desc and desc in desc_to_idx:
				mat_pos = desc_to_idx[desc]
		if mat_pos is None:
			continue
		out[mat_pos][s_idx] += qty
	return out


_PACKAGES_SUMMARY_CSS = """
.sp-packages-summary-field .control-value {
	max-width: 100%;
	overflow: visible;
}
.sp-packages-summary {
	width: 100%;
	margin-bottom: 14px;
	box-sizing: border-box;
}
.sp-packages-summary.is-collapsed .sp-pfn-pipeline-wrap,
.sp-packages-summary.is-collapsed .sp-pfn-panel,
.sp-packages-summary.is-collapsed .sp-pfn-footer { display: none; }
.sp-packages-summary.is-collapsed .sp-pfn-titlebar { border-bottom: none; }
.sp-packages-summary.is-collapsed .sp-pfn-kpis { border-bottom: none; }
.sp-pfn-card {
	width: 100%;
	border: 1px solid #E5E7EB;
	border-radius: 12px;
	overflow: hidden;
	background: #fff;
	box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.sp-pfn-titlebar {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 12px 16px;
	background: linear-gradient(180deg, #ffffff, #fafafa);
	border-bottom: 1px solid #ECEEF1;
}
.sp-pfn-title {
	font-size: 13px;
	font-weight: 700;
	color: var(--text-color, #111827);
	letter-spacing: 0.01em;
}
.sp-pfn-title-icon {
	width: 22px;
	height: 22px;
	border-radius: 6px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	background: linear-gradient(135deg, #6366F1, #06B6D4);
	color: #fff;
	font-size: 12px;
	line-height: 1;
}
.sp-pfn-title-sub {
	font-size: 11px;
	font-weight: 500;
	color: var(--text-muted, #6b7280);
}
.sp-pks-toggle {
	margin-left: auto;
	width: 28px;
	min-width: 28px;
	height: 28px;
	padding: 0;
	border: 1px solid #E5E7EB;
	border-radius: 8px;
	background: #fff;
	color: var(--text-muted, #6b7280);
	cursor: pointer;
	line-height: 1;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	transition: background-color 0.12s ease, color 0.12s ease;
}
.sp-pks-toggle:hover { background: var(--gray-50, #F9FAFB); color: #111827; }
.sp-pks-toggle:focus { outline: 2px solid var(--primary, #2490ef); outline-offset: 1px; }
.sp-pks-toggle-icon {
	display: block;
	font-size: 10px;
	transition: transform 0.18s ease;
}
.sp-packages-summary.is-collapsed .sp-pks-toggle-icon { transform: rotate(-90deg); }

/* ----- KPI cards ----- */
.sp-pfn-kpis {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
	gap: 10px;
	padding: 14px 16px;
	background: linear-gradient(180deg, #FAFBFF, #FFFFFF);
	border-bottom: 1px solid #ECEEF1;
}
.sp-pfn-kpi {
	position: relative;
	background: #fff;
	border: 1px solid #ECEEF1;
	border-radius: 10px;
	padding: 12px 14px 12px 16px;
	overflow: hidden;
	transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.sp-pfn-kpi:hover {
	transform: translateY(-1px);
	box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}
.sp-pfn-kpi::before {
	content: '';
	position: absolute;
	left: 0; top: 0; bottom: 0;
	width: 4px;
	background: var(--sp-kpi-accent, #6366F1);
}
.sp-pfn-kpi-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	margin-bottom: 4px;
}
.sp-pfn-kpi-label {
	font-size: 10px;
	font-weight: 600;
	color: var(--text-muted, #6B7280);
	text-transform: uppercase;
	letter-spacing: 0.06em;
}
.sp-pfn-kpi-icon {
	width: 22px;
	height: 22px;
	border-radius: 6px;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	background: color-mix(in srgb, var(--sp-kpi-accent, #6366F1) 14%, transparent);
	color: var(--sp-kpi-accent, #6366F1);
	font-size: 12px;
	line-height: 1;
}
.sp-pfn-kpi-value {
	font-size: 22px;
	font-weight: 700;
	color: var(--text-color, #111827);
	line-height: 1.1;
	font-variant-numeric: tabular-nums;
}
.sp-pfn-kpi-sub {
	font-size: 10px;
	color: var(--text-muted, #9CA3AF);
	margin-top: 6px;
}
.sp-pfn-kpi-bar {
	margin-top: 8px;
	height: 6px;
	border-radius: 4px;
	background: #F1F2F4;
	overflow: hidden;
}
.sp-pfn-kpi-bar-fill {
	height: 100%;
	background: linear-gradient(90deg, var(--sp-kpi-accent, #6366F1), color-mix(in srgb, var(--sp-kpi-accent, #6366F1) 55%, white));
	border-radius: 4px;
	transition: width 0.45s ease;
}

/* ----- Stage pipeline ----- */
.sp-pfn-pipeline-wrap {
	padding: 12px 16px 16px;
	background: #fff;
	border-bottom: 1px solid #ECEEF1;
}
.sp-pfn-pipeline-head {
	display: flex;
	align-items: baseline;
	gap: 10px;
	margin-bottom: 10px;
}
.sp-pfn-pipeline-title {
	font-size: 11px;
	font-weight: 700;
	color: #111827;
	text-transform: uppercase;
	letter-spacing: 0.06em;
}
.sp-pfn-pipeline-sub {
	font-size: 11px;
	color: var(--text-muted, #6B7280);
}
.sp-pfn-pipeline {
	display: flex;
	align-items: stretch;
	gap: 10px;
	overflow-x: auto;
	-webkit-overflow-scrolling: touch;
	padding-bottom: 2px;
}
.sp-pfn-stage-card {
	position: relative;
	flex: 1 1 0;
	min-width: 168px;
	background: linear-gradient(180deg, #fff, color-mix(in srgb, var(--sp-stage-color-light, #E5E7EB) 22%, #ffffff));
	border: 1px solid color-mix(in srgb, var(--sp-stage-color, #6366F1) 18%, #E5E7EB);
	border-left: 4px solid var(--sp-stage-color, #6366F1);
	border-radius: 10px;
	padding: 10px 12px;
	display: flex;
	flex-direction: column;
	gap: 6px;
	transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.sp-pfn-stage-card:hover {
	transform: translateY(-1px);
	box-shadow: 0 4px 12px color-mix(in srgb, var(--sp-stage-color, #6366F1) 18%, transparent);
}
.sp-pfn-stage-card-head {
	display: flex;
	align-items: center;
	gap: 6px;
	min-width: 0;
}
.sp-pfn-stage-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: var(--sp-stage-color, #6366F1);
	box-shadow: 0 0 0 3px color-mix(in srgb, var(--sp-stage-color, #6366F1) 18%, transparent);
	flex: 0 0 auto;
}
.sp-pfn-stage-card-name {
	font-size: 11px;
	font-weight: 700;
	color: #1F2937;
	letter-spacing: 0.02em;
	text-transform: uppercase;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.sp-pfn-stage-tags {
	margin-left: auto;
	display: inline-flex;
	gap: 4px;
}
.sp-pfn-stage-tag {
	display: inline-flex;
	align-items: center;
	padding: 1px 6px;
	border-radius: 999px;
	font-size: 9px;
	font-weight: 700;
	letter-spacing: 0.05em;
	text-transform: uppercase;
	background: color-mix(in srgb, var(--sp-stage-color, #6366F1) 14%, transparent);
	color: var(--sp-stage-color, #6366F1);
}
.sp-pfn-stage-tag-final {
	background: #DCFCE7;
	color: #166534;
}
.sp-pfn-stage-card-body {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 6px;
}
.sp-pfn-stage-card-qty {
	font-size: 20px;
	font-weight: 700;
	color: #111827;
	line-height: 1;
	font-variant-numeric: tabular-nums;
}
.sp-pfn-stage-card-pct {
	font-size: 11px;
	font-weight: 700;
	color: var(--sp-stage-color, #6366F1);
	font-variant-numeric: tabular-nums;
}
.sp-pfn-stage-card-meter {
	height: 6px;
	border-radius: 4px;
	background: color-mix(in srgb, var(--sp-stage-color, #6366F1) 10%, #F1F2F4);
	overflow: hidden;
}
.sp-pfn-stage-card-fill {
	height: 100%;
	background: linear-gradient(90deg, var(--sp-stage-color, #6366F1), var(--sp-stage-color-light, #A5B4FC));
	border-radius: 4px;
	transition: width 0.45s ease;
}
.sp-pfn-stage-card-foot {
	font-size: 10px;
	color: var(--text-muted, #6B7280);
}

/* ----- Detail table ----- */
.sp-pfn-panel {
	width: 100%;
	overflow-x: auto;
	-webkit-overflow-scrolling: touch;
}
.sp-pfn-table {
	display: grid;
	grid-template-columns: var(--sp-pfn-cols);
	column-gap: 10px;
	width: 100%;
	min-width: max-content;
	align-items: stretch;
}
.sp-pfn-header,
.sp-pfn-row {
	display: grid;
	grid-column: 1 / -1;
	grid-template-columns: subgrid;
	align-items: stretch;
}
.sp-pfn-header {
	padding: 10px 16px;
	background: #FAFBFC;
	border-bottom: 1px solid #ECEEF1;
	position: sticky;
	top: 0;
	z-index: 1;
}
.sp-pfn-row {
	padding: 10px 16px;
	border-bottom: 1px solid #F2F3F5;
	transition: background-color 0.12s ease;
}
.sp-pfn-row:hover .sp-pfn-cell { background: #FAFBFC; }
.sp-pfn-row:last-child { border-bottom: none; }
.sp-pfn-row[data-status="complete"] .sp-pfn-cell {
	background: linear-gradient(90deg, rgba(34,197,94,0.04), transparent 30%);
}
.sp-pfn-row[data-status="aa"] .sp-pfn-cell {
	background: linear-gradient(90deg, rgba(245,158,11,0.05), transparent 30%);
}
.sp-pfn-cell {
	min-width: 0;
	display: flex;
	align-items: center;
	box-sizing: border-box;
}
.sp-pfn-col-head {
	font-size: 10px;
	font-weight: 700;
	color: var(--text-muted, #6b7280);
	line-height: 1.2;
	white-space: nowrap;
	letter-spacing: 0.06em;
	text-transform: uppercase;
}
.sp-pfn-col-head.sp-pfn-cell-required,
.sp-pfn-col-head.sp-pfn-cell-status {
	justify-content: flex-end;
	text-align: right;
}
.sp-pfn-cell-rowno {
	justify-content: center;
	color: var(--text-muted, #6b7280);
	font-size: 11px;
	font-variant-numeric: tabular-nums;
}
.sp-pfn-cell-package {
	justify-content: flex-start;
	overflow: hidden;
}
.sp-pfn-package {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-color, #111827);
	line-height: 1.3;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.sp-pfn-cell-required {
	justify-content: flex-end;
	text-align: right;
}
.sp-pfn-cell-stage {
	flex-direction: column;
	align-items: stretch;
	justify-content: center;
	gap: 5px;
	padding: 2px 0;
}
.sp-pfn-cell-stage.sp-pfn-cell-empty .sp-pfn-qty-zero { color: var(--text-muted, #9ca3af); }
.sp-pfn-cell-na .sp-pfn-qty-na {
	color: var(--text-muted, #9ca3af);
	font-weight: 500;
}
.sp-pfn-cell-stage-head {
	justify-content: center;
	text-align: center;
	border-bottom: 2px solid transparent;
	padding-bottom: 4px;
}
.sp-pfn-qty {
	font-size: 12px;
	font-weight: 600;
	font-variant-numeric: tabular-nums;
	color: var(--text-color, #111827);
	line-height: 1;
}
.sp-pfn-cell-required > .sp-pfn-qty {
	text-align: right;
}
.sp-pfn-cell-stage .sp-pfn-qty {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 3px;
	min-height: 16px;
	width: 100%;
}
.sp-pfn-cell-stage .sp-pfn-qty-num {
	min-width: 1.5ch;
	text-align: center;
}
.sp-pfn-cell-check {
	flex: 0 0 11px;
	width: 11px;
	color: #16A34A;
	font-size: 11px;
	font-weight: 700;
	line-height: 1;
	text-align: center;
}
.sp-pfn-cell-check--empty {
	visibility: hidden;
}
.sp-pfn-bar {
	display: block;
	width: 100%;
	height: 5px;
	border-radius: 3px;
	background: #F0F1F3;
	overflow: hidden;
}
.sp-pfn-bar-fill {
	display: block;
	height: 100%;
	background: #94A3B8;
	border-radius: 3px;
	transition: width 0.35s ease;
}

/* Stage palette: cell bars + header underline tint */
.sp-pfn-stage-0 .sp-pfn-bar { background: rgba(99,102,241,0.10); }
.sp-pfn-stage-0 .sp-pfn-bar-fill { background: linear-gradient(90deg, #6366F1, #A5B4FC); }
.sp-pfn-stage-0.sp-pfn-cell-stage-head { color: #4338CA; border-bottom-color: #6366F1; }
.sp-pfn-stage-1 .sp-pfn-bar { background: rgba(6,182,212,0.10); }
.sp-pfn-stage-1 .sp-pfn-bar-fill { background: linear-gradient(90deg, #06B6D4, #67E8F9); }
.sp-pfn-stage-1.sp-pfn-cell-stage-head { color: #0E7490; border-bottom-color: #06B6D4; }
.sp-pfn-stage-2 .sp-pfn-bar { background: rgba(16,185,129,0.10); }
.sp-pfn-stage-2 .sp-pfn-bar-fill { background: linear-gradient(90deg, #10B981, #6EE7B7); }
.sp-pfn-stage-2.sp-pfn-cell-stage-head { color: #047857; border-bottom-color: #10B981; }
.sp-pfn-stage-3 .sp-pfn-bar { background: rgba(245,158,11,0.10); }
.sp-pfn-stage-3 .sp-pfn-bar-fill { background: linear-gradient(90deg, #F59E0B, #FCD34D); }
.sp-pfn-stage-3.sp-pfn-cell-stage-head { color: #B45309; border-bottom-color: #F59E0B; }
.sp-pfn-stage-4 .sp-pfn-bar { background: rgba(239,68,68,0.10); }
.sp-pfn-stage-4 .sp-pfn-bar-fill { background: linear-gradient(90deg, #EF4444, #FCA5A5); }
.sp-pfn-stage-4.sp-pfn-cell-stage-head { color: #B91C1C; border-bottom-color: #EF4444; }
.sp-pfn-stage-5 .sp-pfn-bar { background: rgba(139,92,246,0.10); }
.sp-pfn-stage-5 .sp-pfn-bar-fill { background: linear-gradient(90deg, #8B5CF6, #C4B5FD); }
.sp-pfn-stage-5.sp-pfn-cell-stage-head { color: #6D28D9; border-bottom-color: #8B5CF6; }
.sp-pfn-stage-6 .sp-pfn-bar { background: rgba(236,72,153,0.10); }
.sp-pfn-stage-6 .sp-pfn-bar-fill { background: linear-gradient(90deg, #EC4899, #F9A8D4); }
.sp-pfn-stage-6.sp-pfn-cell-stage-head { color: #BE185D; border-bottom-color: #EC4899; }
.sp-pfn-stage-7 .sp-pfn-bar { background: rgba(20,184,166,0.10); }
.sp-pfn-stage-7 .sp-pfn-bar-fill { background: linear-gradient(90deg, #14B8A6, #5EEAD4); }
.sp-pfn-stage-7.sp-pfn-cell-stage-head { color: #0F766E; border-bottom-color: #14B8A6; }

/* Complete state overrides stage tint */
.sp-pfn-cell-stage.sp-pfn-cell-complete .sp-pfn-bar { background: rgba(22,163,74,0.12); }
.sp-pfn-cell-stage.sp-pfn-cell-complete .sp-pfn-bar-fill {
	background: linear-gradient(90deg, #16A34A, #4ADE80);
}
.sp-pfn-cell-stage.sp-pfn-cell-complete .sp-pfn-qty { color: #166534; }

/* Final stage column gets a subtle background to draw the eye */
.sp-pfn-cell-stage.sp-pfn-cell-final {
	box-shadow: inset 0 0 0 999px rgba(16,185,129,0.04);
	border-radius: 4px;
}

.sp-pfn-badge {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 26px;
	height: 18px;
	padding: 0 6px;
	border-radius: 999px;
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 0.04em;
	background: #FEF3C7;
	color: #92400E;
}

/* Status pill column */
.sp-pfn-cell-status {
	justify-content: flex-end;
}
.sp-pfn-pill {
	display: inline-flex;
	align-items: center;
	padding: 3px 10px;
	border-radius: 999px;
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	line-height: 1.2;
	white-space: nowrap;
}
.sp-pfn-pill::before {
	content: '';
	width: 6px;
	height: 6px;
	border-radius: 50%;
	margin-right: 6px;
	background: currentColor;
}
.sp-pfn-pill-complete { background: #DCFCE7; color: #166534; }
.sp-pfn-pill-in_progress { background: #DBEAFE; color: #1D4ED8; }
.sp-pfn-pill-pending { background: #F3F4F6; color: #6B7280; }
.sp-pfn-pill-aa { background: #FEF3C7; color: #92400E; }

.sp-pfn-footer {
	padding: 10px 16px;
	background: linear-gradient(180deg, #FAFBFC, #FFFFFF);
	border-top: 1px solid #ECEEF1;
	display: flex;
	align-items: center;
	flex-wrap: wrap;
	gap: 6px 12px;
}
.sp-pfn-footer-stat {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	font-size: 11px;
	color: var(--text-muted, #6B7280);
}
.sp-pfn-footer-stat strong {
	font-weight: 700;
	color: #111827;
	font-variant-numeric: tabular-nums;
}
.sp-pfn-footer-sep {
	color: #D1D5DB;
}
.sp-pfn-empty {
	padding: 24px;
	color: var(--text-muted, #6b7280);
	font-size: 12px;
	text-align: center;
}
@media (max-width: 860px) {
	.sp-pfn-header,
	.sp-pfn-row {
		padding-left: 12px;
		padding-right: 12px;
	}
	.sp-pfn-kpis,
	.sp-pfn-pipeline-wrap {
		padding-left: 12px;
		padding-right: 12px;
	}
}
"""


def _packages_summary_titlebar_html(toggle_title: str, aria_label: str) -> str:
	return (
		f'<div class="sp-pfn-titlebar">'
		f'<span class="sp-pfn-title-icon" aria-hidden="true">&#9783;</span>'
		f'<span class="sp-pfn-title">{escape_html(_("Fulfillment Snapshot"))}</span>'
		f'<span class="sp-pfn-title-sub">{escape_html(_("Delivery throughput across lifecycle stages"))}</span>'
		f'<button type="button" class="sp-pks-toggle" aria-expanded="true" '
		f'title="{escape_html(toggle_title)}" aria-label="{escape_html(aria_label)}">'
		f'<span class="sp-pks-toggle-icon" aria-hidden="true">&#9660;</span>'
		f"</button>"
		f"</div>"
	)


@frappe.whitelist()
def get_packages_summary_html(special_project: str) -> str:
	"""HTML summary for the Fulfillment tab: row per package x column per Lifecycle Stage."""
	if not special_project:
		return ""
	doc = frappe.get_doc("Special Project", special_project)
	from logistics.special_projects.special_project_packages import (
		cint_safe,
		lifecycle_stages_for_special_project,
		package_label,
		validate_packages,
	)

	validate_packages(doc)
	materials = doc.get("packages") or []
	if not materials:
		return (
			f'<div class="sp-packages-summary">'
			f"<style>{_PACKAGES_SUMMARY_CSS}</style>"
			f'<div class="sp-pfn-card"><div class="sp-pfn-empty">'
			f"{escape_html(_('No packages defined. Add rows below or seed from Sales Quote project products.'))}"
			f"</div></div></div>"
		)

	stages = lifecycle_stages_for_special_project()
	if not stages:
		return (
			f'<div class="sp-packages-summary">'
			f"<style>{_PACKAGES_SUMMARY_CSS}</style>"
			f'<div class="sp-pfn-card"><div class="sp-pfn-empty">'
			f"{escape_html(_('No Lifecycle Stages configured for Special Projects. Set For Special Project on at least one Lifecycle Stage.'))}"
			f"</div></div></div>"
		)

	per_stage = _packages_summary_per_stage_delivered(doc, materials, stages)

	final_idx: int | None = None
	for i, s in enumerate(stages):
		if cint_safe(s.get("is_closed")):
			final_idx = i
	if final_idx is None and stages:
		final_idx = len(stages) - 1

	always_along_count = sum(1 for m in materials if cint_safe(getattr(m, "include_on_create", 0)))
	tracked_count = len(materials) - always_along_count

	total_required = 0.0
	for m in materials:
		if cint_safe(getattr(m, "include_on_create", 0)):
			continue
		total_required += flt(getattr(m, "qty_required", 0))

	n_stages = len(stages)
	per_stage_totals = [0.0] * n_stages
	for i, m in enumerate(materials):
		if cint_safe(getattr(m, "include_on_create", 0)):
			continue
		qtys = per_stage[i]
		for s_idx in range(n_stages):
			per_stage_totals[s_idx] += flt(qtys[s_idx])

	total_delivered = (
		per_stage_totals[final_idx] if (final_idx is not None and final_idx < len(per_stage_totals)) else 0.0
	)
	complete_pct = 0.0 if total_required <= 0 else min(100.0, total_delivered / total_required * 100.0)

	complete_rows = 0
	in_progress_rows = 0
	pending_rows = 0
	for i, m in enumerate(materials):
		if cint_safe(getattr(m, "include_on_create", 0)):
			continue
		qtys = per_stage[i]
		req = flt(getattr(m, "qty_required", 0))
		final_qty = flt(qtys[final_idx]) if (final_idx is not None and final_idx < len(qtys)) else 0.0
		if req > 0 and final_qty >= req:
			complete_rows += 1
		elif any(flt(q) > 0 for q in qtys):
			in_progress_rows += 1
		else:
			pending_rows += 1

	# ----- Build rows -----
	rows_html: list[str] = []
	for row_no, (m, qtys) in enumerate(zip(materials, per_stage), start=1):
		label = escape_html(package_label(m) or "—")
		rows_html.append(
			_packages_summary_row_html(
				row_no,
				label,
				flt(m.qty_required or 0),
				qtys,
				is_always_along=bool(cint_safe(getattr(m, "include_on_create", 0))),
				final_stage_idx=final_idx,
			)
		)

	stage_cols = " ".join("minmax(92px, 1fr)" for _ in stages)
	col_template = f"40px minmax(140px, 1.5fr) 72px {stage_cols} 116px"

	stage_headers = "".join(
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-stage-head sp-pfn-stage-{i % len(_STAGE_PALETTE)}" '
		f'title="{escape_html(stage.get("description") or stage["name"])}">'
		f"{escape_html(stage['name'])}</span>"
		for i, stage in enumerate(stages)
	)

	header_html = (
		f'<div class="sp-pfn-header">'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-rowno">#</span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-package">{escape_html(_("Package"))}</span>'
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-required">{escape_html(_("Required"))}</span>'
		f"{stage_headers}"
		f'<span class="sp-pfn-cell sp-pfn-col-head sp-pfn-cell-status">{escape_html(_("Status"))}</span>'
		f"</div>"
	)

	# ----- KPI cards -----
	total_req_label = _packages_summary_qty_label(total_required) if tracked_count else "—"
	total_delivered_label = _packages_summary_qty_label(total_delivered) if tracked_count else "—"
	final_stage_name = (
		stages[final_idx]["name"] if (final_idx is not None and final_idx < len(stages)) else "—"
	)
	pct_value_label = f"{complete_pct:.0f}%" if total_required > 0 else "—"

	kpi_cards = "".join(
		[
			_packages_summary_kpi_card_html(
				_("Packages"),
				str(len(materials)),
				_("{0} tracked · {1} always-along").format(tracked_count, always_along_count),
				"#6366F1",
				icon="&#128230;",
			),
			_packages_summary_kpi_card_html(
				_("Units Required"),
				total_req_label,
				_("Across {0} tracked package row(s)").format(tracked_count) if tracked_count else _("No tracked rows"),
				"#06B6D4",
				icon="&#931;",
			),
			_packages_summary_kpi_card_html(
				_("Units Delivered"),
				total_delivered_label,
				_("Counted at final stage: {0}").format(final_stage_name),
				"#10B981",
				icon="&#10003;",
			),
			_packages_summary_kpi_card_html(
				_("% Complete"),
				pct_value_label,
				_("{0} complete · {1} in progress · {2} pending").format(
					complete_rows, in_progress_rows, pending_rows
				),
				"#F59E0B",
				progress_pct=complete_pct if total_required > 0 else 0.0,
				icon="&#9889;",
			),
		]
	)
	kpis_html = f'<div class="sp-pfn-kpis">{kpi_cards}</div>'

	# ----- Stage pipeline -----
	pipeline_html = _packages_summary_stage_pipeline_html(
		stages, per_stage_totals, total_required, final_idx
	)

	# ----- Footer (chip-style) -----
	def _stat(label: str, value: str) -> str:
		return (
			'<span class="sp-pfn-footer-stat">'
			f'<strong>{escape_html(value)}</strong>{escape_html(label)}</span>'
		)

	sep = '<span class="sp-pfn-footer-sep" aria-hidden="true">|</span>'
	stats: list[str] = [
		_stat(" " + _("package row(s)"), str(len(materials))),
		_stat(" " + _("tracked"), str(tracked_count)) if tracked_count else "",
		_stat(" " + _("always-along (AA)"), str(always_along_count)) if always_along_count else "",
		_stat(" " + _("lifecycle stage(s)"), str(len(stages))),
	]
	stats = [s for s in stats if s]
	footer_inner = sep.join(stats)
	footer_html = f'<div class="sp-pfn-footer">{footer_inner}</div>'

	rows_block = "".join(rows_html)
	titlebar_html = _packages_summary_titlebar_html(
		_("Collapse summary"), _("Toggle fulfillment summary")
	)
	return (
		f'<div class="sp-packages-summary" style="--sp-pfn-cols: {col_template}">'
		f"<style>{_PACKAGES_SUMMARY_CSS}</style>"
		f'<div class="sp-pfn-card">'
		f"{titlebar_html}"
		f"{kpis_html}"
		f"{pipeline_html}"
		f'<div class="sp-pfn-panel">'
		f'<div class="sp-pfn-table">{header_html}{rows_block}</div>'
		f"</div>"
		f"{footer_html}"
		f"</div></div>"
	)
