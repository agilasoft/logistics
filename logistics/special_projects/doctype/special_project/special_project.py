# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import escape_html, flt

from logistics.special_projects.special_project_lifecycle import (
	validate_special_project_lifecycle_stage_advance,
)
from logistics.utils.lifecycle_stage import FOR_SPECIAL_PROJECT, validate_internal_job_activity_codes
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


def _resolve_site_material_label(row) -> tuple[str, str]:
	"""Return (display_name, secondary_code) for a site material row.

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
			from logistics.special_projects.special_project_site_materials import (
				validate_site_materials,
			)

			validate_site_materials(self)
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
		"""Block submission until site materials are fully on-site and lifecycle jobs are all complete."""
		self._validate_submit_gates()

	def _validate_submit_gates(self):
		"""Enforce closure gates: every site material row delivered, every lifecycle activity completed."""
		materials = self._collect_site_material_blockers()
		lifecycle = self._collect_lifecycle_blockers()

		if not materials and not lifecycle:
			return

		# Decide which tab the primary CTA should jump to (whichever blocker exists).
		primary_target = "site_materials_tab" if materials else "lifecycle_tab"
		primary_label = (
			_("Go to Site Materials") if materials else _("Go to Lifecycle")
		)

		summary_lines: list[str] = []
		if materials:
			n_materials = len(materials["groups"])
			n_rows = materials["total_rows"]
			summary_lines.append(
				_("{0} site material(s) are not fully on-site, affecting {1} row(s).").format(
					f"<strong>{n_materials}</strong>", f"<strong>{n_rows}</strong>"
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
		if materials:
			body_sections.append(self._render_site_materials_card(materials))
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

	def _collect_site_material_blockers(self) -> dict | None:
		"""Group short rows by (material, uom). Returns dict with groups + totals or None."""
		grouped: dict[tuple[str, str, str], dict] = {}
		for row in self.get("site_materials") or []:
			short = flt(getattr(row, "qty_short", 0))
			if short <= 0:
				continue
			display, code = _resolve_site_material_label(row)
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

	def _render_site_materials_card(self, materials: dict) -> str:
		"""Render the grouped site-material shortages as a card with a compact table."""
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
				+ escape_html(_("…and {0} more material(s)").format(hidden_count))
				+ "</td></tr>"
			)

		title = _("Site Materials Short on Site")
		guidance = _(
			"Review the affected materials in the Site Materials tab and receive the missing "
			"quantities, or reduce the required quantity on rows no longer needed."
		)
		col_material = _("Material")
		col_rows = _("Rows Affected")
		col_short = _("Total Shortage")

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
			+ _("{0} materials · {1} rows").format(
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
		if not self.lifecycle_stage:
			self.lifecycle_stage = "Pre-Show"

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
		from logistics.special_projects.special_project_site_materials import (
			validate_site_materials,
		)

		validate_site_materials(doc)
		materials = doc.get("site_materials") or []
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


def _site_materials_summary_bar_segments(required: float, on_site: float, short: float) -> tuple[float, float]:
	"""Return on-site and short bar widths (0–100) as share of required qty."""
	required = flt(required)
	if required <= 0:
		return 0.0, 0.0
	on_pct = min(100.0, flt(on_site) / required * 100.0)
	short_pct = min(100.0 - on_pct, flt(short) / required * 100.0)
	return on_pct, short_pct


def _site_materials_summary_qty_label(qty: float) -> str:
	value = flt(qty)
	if value == int(value):
		return str(int(value))
	return str(value)


def _site_materials_summary_bar_label_html(qty: float) -> str:
	if flt(qty) <= 0:
		return ""
	label = escape_html(_site_materials_summary_qty_label(qty))
	return f'<span class="sp-sms-bar-label">{label}</span>'


def _site_materials_summary_bar_html(required: float, on_site: float, short: float) -> str:
	on_pct, short_pct = _site_materials_summary_bar_segments(required, on_site, short)
	remainder = max(0.0, 100.0 - on_pct - short_pct)
	segments: list[str] = []
	if on_pct >= 0.5 and flt(on_site) > 0:
		segments.append(
			f'<div class="sp-sms-bar-on" style="flex-grow:{on_pct:.4f}">'
			f"{_site_materials_summary_bar_label_html(on_site)}</div>"
		)
	if short_pct >= 0.5 and flt(short) > 0:
		only_short = not segments
		cls = "sp-sms-bar-short sp-sms-bar-short-only" if only_short else "sp-sms-bar-short"
		segments.append(
			f'<div class="{cls}" style="flex-grow:{short_pct:.4f}">'
			f"{_site_materials_summary_bar_label_html(short)}</div>"
		)
	if remainder >= 0.5 and segments:
		segments.append(f'<div class="sp-sms-bar-empty" style="flex-grow:{remainder:.4f}"></div>')
	if not segments:
		segments.append('<div class="sp-sms-bar-empty sp-sms-bar-empty-only"></div>')
	return f'<div class="sp-sms-bar">{"".join(segments)}</div>'


def _site_materials_summary_row_html(
	row_no: int, label: str, required: float, on_site: float, short: float
) -> str:
	return (
		f'<div class="sp-sms-row">'
		f'<span class="sp-sms-cell sp-sms-cell-toggle" aria-hidden="true"></span>'
		f'<span class="sp-sms-cell sp-sms-cell-rowno">'
		f'<span class="sp-sms-rowno">{row_no}</span></span>'
		f'<span class="sp-sms-cell sp-sms-cell-material sp-sms-material" title="{label}">{label}</span>'
		f'<div class="sp-sms-cell sp-sms-cell-bar">'
		f'<div class="sp-sms-bar-wrap">'
		f"{_site_materials_summary_bar_html(required, on_site, short)}"
		f"</div></div>"
		f'<span class="sp-sms-cell sp-sms-cell-required">'
		f'<span class="sp-sms-qty">{_site_materials_summary_qty_label(required)}</span>'
		f"</span></div>"
	)


_SITE_MATERIALS_SUMMARY_CSS = """
.sp-site-materials-summary-field .control-value {
	max-width: 100%;
	overflow: visible;
}
.sp-site-materials-summary {
	--sp-sms-cols: 24px 40px minmax(150px, 17%) minmax(280px, 1fr) 88px;
	--sp-sms-gap: 14px;
	--sp-sms-row-h: 38px;
	width: 100%;
	margin-bottom: 14px;
	box-sizing: border-box;
}
.sp-site-materials-summary.is-collapsed .sp-sms-panel,
.sp-site-materials-summary.is-collapsed .sp-sms-footer { display: none; }
.sp-site-materials-summary.is-collapsed .sp-sms-header { border-bottom: none; }
.sp-sms-layout {
	display: flex;
	flex-direction: column;
	align-items: stretch;
	width: 100%;
	min-width: 0;
	box-sizing: border-box;
}
.sp-sms-table {
	width: 100%;
	max-width: 100%;
	min-width: 0;
	border: 1px solid #E8E8E8;
	border-radius: 8px;
	overflow: hidden;
	background: #fff;
}
.sp-sms-header,
.sp-sms-row {
	display: grid;
	grid-template-columns: var(--sp-sms-cols);
	column-gap: var(--sp-sms-gap);
	align-items: center;
	width: 100%;
	min-height: var(--sp-sms-row-h);
	box-sizing: border-box;
}
.sp-sms-header {
	background: var(--gray-50, #fafafa);
	border-bottom: 1px solid #E8E8E8;
	padding-left: 12px;
	padding-right: 16px;
	box-sizing: border-box;
}
.sp-sms-header .sp-sms-cell,
.sp-sms-row .sp-sms-cell {
	min-width: 0;
	min-height: var(--sp-sms-row-h);
	height: 100%;
	padding: 0;
	display: flex;
	align-items: center;
	box-sizing: border-box;
}
.sp-sms-rows {
	max-height: 280px;
	overflow-y: auto;
	overflow-x: auto;
	padding-left: 12px;
	padding-right: 16px;
	box-sizing: border-box;
	scrollbar-gutter: stable;
}
.sp-sms-row {
	border-bottom: 1px solid #F0F0F0;
	transition: background-color 0.12s ease;
}
.sp-sms-row:hover { background: #fafbfc; }
.sp-sms-row:last-child { border-bottom: none; }
.sp-sms-cell-toggle {
	width: 24px;
	min-width: 24px;
	max-width: 24px;
	justify-content: center;
	padding: 0 2px 0 0;
	flex-shrink: 0;
}
.sp-sms-toggle {
	width: 24px;
	min-width: 24px;
	height: 24px;
	padding: 0;
	border: none;
	border-radius: 6px;
	background: var(--gray-100, #f3f4f6);
	color: var(--text-muted, #6b7280);
	cursor: pointer;
	line-height: 1;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}
.sp-sms-toggle:hover { background: var(--gray-200, #e5e7eb); }
.sp-sms-toggle:focus { outline: 2px solid var(--primary, #2490ef); outline-offset: 1px; }
.sp-sms-toggle-icon {
	display: block;
	font-size: 9px;
	transition: transform 0.15s ease;
}
.sp-site-materials-summary.is-collapsed .sp-sms-toggle-icon { transform: rotate(-90deg); }
.sp-sms-cell-rowno {
	justify-content: center;
	flex-shrink: 0;
}
.sp-sms-header .sp-sms-cell-rowno.sp-sms-metric-label {
	text-align: center;
	padding-right: 0;
	width: auto;
}
.sp-sms-rowno {
	font-size: 11px;
	font-weight: 500;
	font-variant-numeric: tabular-nums;
	color: var(--text-muted, #6b7280);
	text-align: center;
}
.sp-sms-cell-material { justify-content: flex-start; padding-right: 2px; }
.sp-sms-cell-bar {
	justify-content: center;
	align-items: center;
	padding: 0 3px;
}
.sp-sms-cell-required {
	justify-content: flex-end;
	align-items: center;
	padding-right: 8px;
	padding-left: 0;
}
.sp-sms-col-head {
	font-size: 11px;
	font-weight: 600;
	color: var(--text-muted, #6b7280);
	line-height: 1.3;
	white-space: nowrap;
}
.sp-sms-header .sp-sms-cell-material.sp-sms-col-head {
	justify-content: flex-start;
}
.sp-sms-bar-head {
	display: block;
	width: 100%;
	font-size: 11px;
	font-weight: 600;
	color: var(--text-muted, #6b7280);
	text-align: center;
	letter-spacing: 0.02em;
}
.sp-sms-metric-label {
	display: block;
	width: 100%;
	padding-right: 8px;
	box-sizing: border-box;
	font-size: 11px;
	font-weight: 600;
	color: var(--text-muted, #6b7280);
	text-align: right;
	white-space: nowrap;
}
.sp-sms-material {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-color, #1f2937);
	line-height: 1.3;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.sp-sms-qty {
	display: inline-flex;
	align-items: center;
	justify-content: flex-end;
	min-width: 2.25rem;
	padding-right: 2px;
	font-size: 12px;
	font-weight: 600;
	line-height: 1;
	font-variant-numeric: tabular-nums;
	color: var(--text-color, #1f2937);
	text-align: right;
}
.sp-sms-bar-wrap {
	display: flex;
	align-items: center;
	width: 100%;
	min-width: 0;
	max-width: 100%;
	height: 100%;
}
.sp-sms-bar {
	display: flex;
	align-items: stretch;
	gap: 3px;
	width: 100%;
	min-height: 20px;
	padding: 3px;
	box-sizing: border-box;
	border-radius: 10px;
	background: #F3F3F3;
	box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.06);
}
.sp-sms-bar-on,
.sp-sms-bar-short,
.sp-sms-bar-empty {
	display: flex;
	align-items: center;
	flex: 0 1 auto;
	min-width: 0;
	border-radius: 7px;
	overflow: hidden;
}
.sp-sms-bar-on {
	background: #0289F7;
	justify-content: center;
	padding: 0 8px;
	min-width: 2.75rem;
}
.sp-sms-bar-short {
	background: #E0E0E0;
	justify-content: center;
	padding: 0 8px;
	min-width: 2.75rem;
}
.sp-sms-bar-short-only {
	flex: 1 1 auto;
	min-width: 3rem;
}
.sp-sms-bar-empty {
	background: transparent;
	flex: 1 1 auto;
	min-width: 0;
	padding: 0;
}
.sp-sms-bar-empty-only {
	flex: 1 1 auto;
	min-height: 14px;
}
.sp-sms-bar-label {
	display: inline-block;
	font-size: 10px;
	font-weight: 700;
	line-height: 1.2;
	white-space: nowrap;
	font-variant-numeric: tabular-nums;
}
.sp-sms-bar-on .sp-sms-bar-label { color: #fff; }
.sp-sms-bar-short .sp-sms-bar-label { color: #374151; }
.sp-sms-footer {
	width: 100%;
	margin-top: 12px;
	padding-top: 0;
	text-align: center;
	flex-shrink: 0;
}
.sp-sms-more {
	margin: 0;
	padding: 0;
	font-size: 11px;
	color: var(--text-muted, #6b7280);
	line-height: 1.4;
}
@media (max-width: 860px) {
	.sp-site-materials-summary {
		--sp-sms-cols: 24px 36px minmax(120px, 22%) minmax(200px, 1fr) 76px;
		--sp-sms-gap: 12px;
	}
}
/* Mobile: switch each row to a 2-line card (info on top, bar below) so the
   progress bar always has full width and column headers do not clip. */
@media (max-width: 640px) {
	.sp-site-materials-summary {
		--sp-sms-cols: 36px 24px minmax(0, 1fr) auto;
		--sp-sms-gap: 8px;
		--sp-sms-row-h: 32px;
	}
	.sp-sms-table { border-radius: 10px; }
	.sp-sms-header {
		grid-template-columns: var(--sp-sms-cols);
		padding-left: 10px;
		padding-right: 10px;
	}
	/* The bar gets its own line in each row, so the bar column header is redundant. */
	.sp-sms-header .sp-sms-cell-bar { display: none; }
	.sp-sms-header .sp-sms-cell-required { padding-right: 4px; }
	.sp-sms-rows {
		max-height: none;
		overflow-x: hidden;
		overflow-y: visible;
		padding-left: 10px;
		padding-right: 10px;
		-webkit-overflow-scrolling: touch;
	}
	.sp-sms-row {
		grid-template-columns: var(--sp-sms-cols);
		grid-template-areas:
			"toggle no material required"
			"bar    bar bar      bar";
		row-gap: 6px;
		padding: 10px 0;
		min-height: 0;
	}
	.sp-sms-row .sp-sms-cell { min-height: 28px; }
	.sp-sms-row .sp-sms-cell-toggle { grid-area: toggle; }
	.sp-sms-row .sp-sms-cell-rowno  { grid-area: no; }
	.sp-sms-row .sp-sms-cell-material { grid-area: material; }
	.sp-sms-row .sp-sms-cell-required { grid-area: required; padding-right: 4px; }
	.sp-sms-row .sp-sms-cell-bar {
		grid-area: bar;
		padding: 0;
		min-height: 28px;
	}
	.sp-sms-cell-toggle {
		width: 36px;
		min-width: 36px;
		max-width: 36px;
	}
	.sp-sms-toggle {
		width: 36px;
		min-width: 36px;
		height: 36px;
		border-radius: 8px;
	}
	.sp-sms-material {
		font-size: 13px;
		line-height: 1.35;
		white-space: normal;
		overflow: visible;
		text-overflow: clip;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
		word-break: break-word;
	}
	.sp-sms-qty { font-size: 13px; }
	.sp-sms-rowno { font-size: 11px; }
	.sp-sms-bar {
		min-height: 24px;
		padding: 3px;
		gap: 3px;
	}
	.sp-sms-bar-on,
	.sp-sms-bar-short {
		padding: 0 6px;
		min-width: 2.5rem;
	}
	.sp-sms-bar-label { font-size: 11px; }
	.sp-sms-footer { margin-top: 10px; }
	.sp-sms-more { font-size: 12px; }
}
"""


@frappe.whitelist()
def get_site_materials_summary_html(special_project: str) -> str:
	"""HTML summary for Site Materials tab."""
	if not special_project:
		return ""
	doc = frappe.get_doc("Special Project", special_project)
	from logistics.special_projects.special_project_site_materials import (
		site_material_label,
		validate_site_materials,
	)

	validate_site_materials(doc)
	materials = doc.get("site_materials") or []
	if not materials:
		return f"<p class='text-muted'>{_('No site material requirements. Add rows or seed from Sales Quote project products.')}</p>"

	rows_html = []
	for row_no, m in enumerate(materials, start=1):
		label = escape_html(site_material_label(m) or "—")
		rows_html.append(
			_site_materials_summary_row_html(
				row_no,
				label,
				flt(m.qty_required or 0),
				flt(m.qty_on_site or 0),
				flt(m.qty_short or 0),
			)
		)

	footer = ""
	if len(materials) > 1:
		footer = (
			f'<div class="sp-sms-footer">'
			f'<p class="sp-sms-more">'
			f"{_('{0} material lines').format(len(materials))}"
			f"</p></div>"
		)

	return (
		f'<div class="sp-site-materials-summary">'
		f"<style>{_SITE_MATERIALS_SUMMARY_CSS}</style>"
		f'<div class="sp-sms-layout">'
		f'<div class="sp-sms-table">'
		f'<div class="sp-sms-header sp-sms-thead">'
		f'<span class="sp-sms-cell sp-sms-cell-toggle">'
		f'<button type="button" class="sp-sms-toggle" aria-expanded="true" '
		f'title="{_("Collapse summary")}" aria-label="{_("Toggle site materials summary")}">'
		f'<span class="sp-sms-toggle-icon" aria-hidden="true">&#9660;</span>'
		f"</button></span>"
		f'<span class="sp-sms-cell sp-sms-cell-rowno sp-sms-metric-label">{_("No.")}</span>'
		f'<span class="sp-sms-cell sp-sms-cell-material sp-sms-col-head">{_("Material")}</span>'
		f'<span class="sp-sms-cell sp-sms-cell-bar"><span class="sp-sms-bar-head">'
		f"{_('On Site')} · {_('Short')}</span></span>"
		f'<span class="sp-sms-cell sp-sms-cell-required sp-sms-metric-label">{_("Required")}</span>'
		f"</div>"
		f'<div class="sp-sms-panel">'
		f'<div class="sp-sms-rows sp-sms-tbody">{"".join(rows_html)}</div>'
		f"</div></div>"
		f"{footer}"
		f"</div></div></div>"
	)
