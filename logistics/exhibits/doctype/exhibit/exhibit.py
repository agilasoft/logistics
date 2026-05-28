# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html, flt

from logistics.exhibits import exhibit_lifecycle
from logistics.exhibits.exhibit_lifecycle import validate_lifecycle_stage_advance
from logistics.utils.lifecycle_stage import (
	FOR_EXHIBITS,
	resolve_default_lifecycle_stage,
	validate_internal_job_activity_codes,
)


INGRESS_PROGRESS_WEIGHTS = {
	"Draft": 0.0,
	"Booked": 0.0,
	"Ingress Pending": 0.0,
	"Ingress In Progress": 0.5,
	"Ingress Completed": 1.0,
	"On Site": 1.0,
	"Egress Pending": 1.0,
	"Egress In Progress": 1.0,
	"Egress Completed": 1.0,
	"In Progress": 0.5,
	"Completed": 1.0,
}

EGRESS_PROGRESS_WEIGHTS = {
	"Draft": 0.0,
	"Booked": 0.0,
	"Ingress Pending": 0.0,
	"Ingress In Progress": 0.0,
	"Ingress Completed": 0.0,
	"On Site": 0.0,
	"Egress Pending": 0.0,
	"Egress In Progress": 0.5,
	"Egress Completed": 1.0,
	"In Progress": 0.0,
	"Completed": 1.0,
}

DOCKET_EXCLUDED_STATUSES = {"Cancelled", "On Hold"}


class Exhibit(Document):
	def onload(self):
		"""Populate the virtual ``dockets`` child table from live Docket records.

		``Exhibit Docket`` is a virtual child doctype (``is_virtual: 1``), so
		Frappe does not load it from the database. We rebuild the rows here so
		the Dockets tab always reflects the current Dockets linked to this
		Exhibit.
		"""
		self._load_dockets_view()

	def _load_dockets_view(self):
		"""Replace ``self.dockets`` with a snapshot of every Docket linked to
		this Exhibit (excluding cancelled ones)."""
		self.set("dockets", [])
		if not self.name or getattr(self, "__islocal", False):
			return
		try:
			rows = frappe.get_all(
				"Docket",
				filters={"exhibit": self.name, "docstatus": ["<", 2]},
				fields=[
					"name",
					"exhibitor",
					"exhibitor_name",
					"booth_no",
					"status",
					"docket_date",
				],
				order_by="docket_date asc, creation asc",
			)
		except Exception:
			rows = []
		for r in rows:
			self.append(
				"dockets",
				{
					"docket": r.get("name"),
					"exhibitor": r.get("exhibitor"),
					"exhibitor_name": r.get("exhibitor_name"),
					"booth_no": r.get("booth_no"),
					"status": r.get("status"),
					"docket_date": r.get("docket_date"),
				},
			)

	def validate(self):
		validate_internal_job_activity_codes(self, module_filter=FOR_EXHIBITS)
		validate_lifecycle_stage_advance(self)

	def autoname(self):
		"""Use ERPNext Project ID as Exhibit ID (created in before_insert)."""
		if self.flags.get("erpnext_project_name"):
			self.name = self.flags.erpnext_project_name

	def before_insert(self):
		"""Create ERPNext Project first, then use its ID as this document's ID."""
		self._create_erpnext_project_before_insert()
		self._normalize_default_lifecycle_stage()
		exhibit_lifecycle.load_standard_service_activities(self)

	def _normalize_default_lifecycle_stage(self):
		"""Ensure ``lifecycle_stage`` references an existing master row.

		Mirror of the guard on ``Special Project``: avoid ``LinkValidationError`` on
		insert when the shared Lifecycle Stage master has not been seeded yet.
		"""
		stage = (self.lifecycle_stage or "").strip()
		if stage and frappe.db.exists("Lifecycle Stage", stage):
			self.lifecycle_stage = stage
			return
		self.lifecycle_stage = resolve_default_lifecycle_stage(
			module_filter=FOR_EXHIBITS, preferred="Pre-Show"
		)

	def on_update(self):
		"""Hook reserved for future status-change side effects."""
		return

	def _create_erpnext_project_before_insert(self):
		"""Create ERPNext Project first; its ID will be used as Exhibit ID via autoname."""
		if self.project:
			self.flags.erpnext_project_name = self.project
			return

		if not frappe.db.exists("DocType", "Project"):
			return

		try:
			project = frappe.new_doc("Project")
			project.project_name = (
				self.project_name
				or f"Exhibit {frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}"
			)
			project.customer = self.customer
			project.expected_start_date = self.planned_start or self.start_date
			project.expected_end_date = self.planned_end or self.end_date
			project.status = self._map_status_to_project(self.status)
			project.project_type = (
				self.project_type
				or frappe.db.get_single_value("Exhibit Settings", "default_project_type")
				or frappe.db.get_value("Project Type", {"name": "External"}, "name")
			)
			project.company = frappe.defaults.get_defaults().get("company")

			project.insert(ignore_permissions=True)

			self.project = project.name
			self.flags.erpnext_project_name = project.name
		except Exception:
			frappe.log_error(
				title=_("Exhibit: Failed to create ERPNext Project"),
				message=frappe.get_traceback(),
			)
			raise

	def _map_status_to_project(self, status):
		"""Map Exhibit status to ERPNext Project status."""
		status_map = {
			"Draft": "Open",
			"Booked": "Open",
			"Planning": "Open",
			"Approved": "Open",
			"In Progress": "Open",
			"On Hold": "Open",
			"Completed": "Completed",
			"Cancelled": "Cancelled",
		}
		return status_map.get(status, "Open")


def _strip_or_none(value):
	if value is None:
		return None
	s = str(value).strip()
	return s or None


@frappe.whitelist()
def get_sales_quote_defaults_from_exhibit(exhibit_name, customer=None):
	"""Return Sales Quote field defaults pre-filled from an Exhibit and exhibitor row."""
	exhibit_name = _strip_or_none(exhibit_name)
	if not exhibit_name:
		frappe.throw(_("Exhibit is required."))
	if not frappe.db.exists("Exhibit", exhibit_name):
		frappe.throw(_("Exhibit {0} does not exist.").format(frappe.bold(exhibit_name)))

	customer = _strip_or_none(customer)
	if not customer:
		frappe.throw(_("Customer (exhibitor) is required."))

	ep = frappe.get_doc("Exhibit", exhibit_name)

	defaults = {
		"main_service": "Exhibits",
		"quotation_type": "Regular",
		"naming_series": "SQU.#########",
		"exhibit": ep.name,
		"customer": customer,
	}
	if _strip_or_none(ep.project_name):
		defaults["exhibit_show_name"] = ep.project_name
	if ep.show_open_date:
		defaults["exhibit_show_open_date"] = str(ep.show_open_date)
	if ep.show_close_date:
		defaults["exhibit_show_close_date"] = str(ep.show_close_date)
	if _strip_or_none(ep.project_type):
		defaults["project_type"] = ep.project_type
	if _strip_or_none(ep.priority):
		defaults["priority"] = ep.priority
	if ep.planned_start:
		defaults["planned_start"] = str(ep.planned_start)
	if ep.planned_end:
		defaults["planned_end"] = str(ep.planned_end)
	if _strip_or_none(ep.description):
		defaults["description"] = ep.description
	if _strip_or_none(ep.special_handling_instructions):
		defaults["special_handling_instructions"] = ep.special_handling_instructions
	if _strip_or_none(ep.logistics_service_level):
		defaults["service_code"] = ep.logistics_service_level
	if ep.project and frappe.db.exists("Project", ep.project):
		company = frappe.db.get_value("Project", ep.project, "company")
		if _strip_or_none(company):
			defaults["company"] = company
	return defaults


def _exhibitors_on_exhibit(exhibit_name):
	"""Return set of exhibitor Customer names already on non-cancelled Dockets for this Exhibit."""
	if not exhibit_name:
		return set()
	rows = frappe.get_all(
		"Docket",
		filters={"exhibit": exhibit_name, "docstatus": ["<", 2]},
		pluck="exhibitor",
	)
	return {_strip_or_none(r) for r in rows if _strip_or_none(r)}


@frappe.whitelist()
def get_linkable_dockets_for_exhibit(
	exhibit_name, search=None, limit=50, exclude_dockets=None
):
	"""Dockets tagged on this Exhibit (picker dialog), optionally excluding names already on the grid."""
	exhibit_name = _strip_or_none(exhibit_name)
	if not exhibit_name:
		frappe.throw(_("Exhibit is required."))
	if not frappe.db.exists("Exhibit", exhibit_name):
		frappe.throw(_("Exhibit {0} does not exist.").format(frappe.bold(exhibit_name)))

	limit = min(int(limit or 50), 200)
	search = _strip_or_none(search)

	if isinstance(exclude_dockets, str):
		try:
			exclude_dockets = json.loads(exclude_dockets)
		except json.JSONDecodeError:
			exclude_dockets = []
	exclude_names = [
		_strip_or_none(n) for n in (exclude_dockets or []) if _strip_or_none(n)
	]

	conditions = ["d.docstatus < 2", "d.exhibit = %(exhibit)s"]
	params = {"exhibit": exhibit_name, "limit": limit}
	if exclude_names:
		placeholders = ", ".join(f"%(exclude_{i})s" for i in range(len(exclude_names)))
		conditions.append(f"d.name NOT IN ({placeholders})")
		for i, name in enumerate(exclude_names):
			params[f"exclude_{i}"] = name
	if search:
		conditions.append(
			"(d.name LIKE %(search)s OR d.exhibitor_name LIKE %(search)s "
			"OR d.exhibitor LIKE %(search)s)"
		)
		params["search"] = f"%{search}%"

	where = " AND ".join(conditions)
	rows = frappe.db.sql(
		f"""
		SELECT
			d.name,
			d.exhibitor,
			d.exhibitor_name,
			d.booth_no,
			d.status,
			d.docket_date,
			d.exhibit
		FROM `tabDocket` d
		WHERE {where}
		ORDER BY d.docket_date ASC, d.creation ASC
		LIMIT %(limit)s
		""",
		params,
		as_dict=True,
	)

	out = []
	for r in rows:
		exhibitor = _strip_or_none(r.get("exhibitor"))
		out.append(
			{
				"name": r.name,
				"exhibitor": exhibitor,
				"exhibitor_name": r.get("exhibitor_name") or "",
				"booth_no": r.get("booth_no") or "",
				"status": r.get("status") or "",
				"docket_date": str(r.docket_date) if r.get("docket_date") else "",
				"exhibit": exhibit_name,
				"row_type": "eligible",
				"reason": "",
			}
		)
	return out


@frappe.whitelist()
def link_dockets_to_exhibit(exhibit_name, dockets):
	"""Set ``Docket.exhibit`` on selected Dockets (tag them on this Exhibit)."""
	exhibit_name = _strip_or_none(exhibit_name)
	if not exhibit_name:
		frappe.throw(_("Exhibit is required."))
	if not frappe.db.exists("Exhibit", exhibit_name):
		frappe.throw(_("Exhibit {0} does not exist.").format(frappe.bold(exhibit_name)))

	if isinstance(dockets, str):
		try:
			dockets = json.loads(dockets)
		except json.JSONDecodeError:
			frappe.throw(_("Invalid docket list."))
	if not dockets:
		frappe.throw(_("Select at least one Docket."))

	taken_exhibitors = _exhibitors_on_exhibit(exhibit_name)
	linked = []
	skipped = []
	errors = []

	for name in dockets:
		docket_name = _strip_or_none(name)
		if not docket_name:
			continue
		if not frappe.db.exists("Docket", docket_name):
			errors.append({"docket": docket_name, "message": _("Docket does not exist.")})
			continue

		row = frappe.db.get_value(
			"Docket",
			docket_name,
			["exhibit", "exhibitor", "docstatus"],
			as_dict=True,
		)
		if not row:
			continue
		if row.docstatus >= 2:
			skipped.append(
				{
					"docket": docket_name,
					"message": _("Cancelled dockets cannot be linked."),
				}
			)
			continue
		if _strip_or_none(row.exhibit) == exhibit_name:
			skipped.append(
				{
					"docket": docket_name,
					"message": _("Already on this Exhibit."),
				}
			)
			continue

		exhibitor = _strip_or_none(row.exhibitor)
		if exhibitor and exhibitor in taken_exhibitors:
			errors.append(
				{
					"docket": docket_name,
					"message": _("Exhibitor {0} already has a Docket on this Exhibit.").format(
						exhibitor
					),
				}
			)
			continue

		try:
			doc = frappe.get_doc("Docket", docket_name)
			previous_exhibit = _strip_or_none(doc.exhibit)
			doc.exhibit = exhibit_name
			doc.save(ignore_permissions=True)
			linked.append(
				{
					"docket": docket_name,
					"moved_from": previous_exhibit or None,
				}
			)
			if exhibitor:
				taken_exhibitors.add(exhibitor)
		except Exception as e:
			errors.append({"docket": docket_name, "message": str(e)})

	if not linked and errors:
		frappe.throw(errors[0]["message"])

	return {"linked": linked, "skipped": skipped, "errors": errors}


@frappe.whitelist()
def reload_standard_service_activities(show):
	"""Reload the standard lifecycle jobs on an existing programme."""
	doc = frappe.get_doc("Exhibit", show)
	doc.set(
		"lifecycle_jobs",
		[r for r in doc.get("lifecycle_jobs") or [] if not (r.activity_code or "").strip()],
	)
	exhibit_lifecycle.load_standard_lifecycle_jobs(doc)
	doc.save()
	return _("Standard lifecycle jobs loaded.")


@frappe.whitelist()
def load_standard_service_activities(show):
	"""Backward-compatible alias for reload_standard_service_activities."""
	return reload_standard_service_activities(show)


@frappe.whitelist()
def get_cost_revenue_summary(show):
	"""Return HTML for Cost & Revenue Summary from project job lines."""
	if not show:
		return ""
	doc = frappe.get_doc("Exhibit", show)
	rows = doc.get("lifecycle_jobs") or []

	planned_cost = sum((flt(a.planned_cost) or 0) for a in rows)
	actual_cost = sum((flt(a.actual_cost) or 0) for a in rows)
	planned_revenue = sum((flt(a.planned_revenue) or 0) for a in rows)
	actual_revenue = sum((flt(a.actual_revenue) or 0) for a in rows)
	planned_margin = planned_revenue - planned_cost if planned_revenue or planned_cost else None
	actual_margin = actual_revenue - actual_cost if actual_revenue or actual_cost else None

	def fmt(v):
		return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

	html_rows = [
		f"<tr><td>{_('Planned Cost')}</td><td class='text-right'>{fmt(planned_cost)}</td>"
		f"<td>{_('Planned Revenue')}</td><td class='text-right'>{fmt(planned_revenue)}</td></tr>",
		f"<tr><td>{_('Actual Cost')}</td><td class='text-right'>{fmt(actual_cost)}</td>"
		f"<td>{_('Actual Revenue')}</td><td class='text-right'>{fmt(actual_revenue)}</td></tr>",
		f"<tr><td>{_('Planned Margin')}</td><td class='text-right'>{fmt(planned_margin)}</td>"
		f"<td>{_('Actual Margin')}</td><td class='text-right'>{fmt(actual_margin)}</td></tr>",
	]
	return (
		'<table class="table table-bordered table-sm" style="max-width: 500px;">'
		f'<tbody>{"".join(html_rows)}</tbody></table>'
	)


def _exhibit_docket_status_map(exhibit_name):
	"""Return a list of dicts describing every Docket linked to this Exhibit.

	The previous implementation walked the Exhibit's ``dockets`` child table,
	but that table is now virtual: rows are derived from real Dockets at load
	time. Query Dockets directly so the dashboard reflects current data even
	when the parent Exhibit doc has not been opened in this request.

	We exclude On Hold / Cancelled dockets from progress calculations so they
	don't artificially deflate the % bars (handled downstream).
	"""
	rows = frappe.get_all(
		"Docket",
		filters={"exhibit": exhibit_name, "docstatus": ["<", 2]},
		fields=["name", "status", "exhibitor", "exhibitor_name", "booth_no"],
		order_by="docket_date asc, creation asc",
	)
	statuses = []
	for r in rows:
		statuses.append(
			{
				"status": r.get("status") or "Draft",
				"docket": r.get("name"),
				"exhibitor": r.get("exhibitor_name") or r.get("exhibitor"),
				"booth_no": r.get("booth_no"),
			}
		)
	return statuses


def _compute_ingress_egress_progress(docket_rows):
	"""Compute ingress/egress % from a list of docket status dicts."""
	considered = [r for r in docket_rows if (r.get("status") or "") not in DOCKET_EXCLUDED_STATUSES]
	n = len(considered)
	if not n:
		return {
			"total": len(docket_rows),
			"active": 0,
			"ingress_pct": 0,
			"egress_pct": 0,
			"ingress_done": 0,
			"egress_done": 0,
		}
	in_sum = sum(INGRESS_PROGRESS_WEIGHTS.get(r.get("status") or "Draft", 0.0) for r in considered)
	eg_sum = sum(EGRESS_PROGRESS_WEIGHTS.get(r.get("status") or "Draft", 0.0) for r in considered)
	in_pct = int(round(100.0 * in_sum / n))
	eg_pct = int(round(100.0 * eg_sum / n))
	in_done = sum(
		1 for r in considered if INGRESS_PROGRESS_WEIGHTS.get(r.get("status") or "Draft", 0.0) >= 1.0
	)
	eg_done = sum(
		1 for r in considered if EGRESS_PROGRESS_WEIGHTS.get(r.get("status") or "Draft", 0.0) >= 1.0
	)
	return {
		"total": len(docket_rows),
		"active": n,
		"ingress_pct": in_pct,
		"egress_pct": eg_pct,
		"ingress_done": in_done,
		"egress_done": eg_done,
	}


def _exhibit_venue_map_payload(doc):
	"""Single map pin at the exhibit venue address (or None when not geocoded)."""
	addr = (getattr(doc, "venue_address", None) or "").strip()
	lat = getattr(doc, "venue_latitude", None)
	lon = getattr(doc, "venue_longitude", None)
	label = (getattr(doc, "venue_name", None) or "").strip()

	if (lat in (None, 0, 0.0)) or (lon in (None, 0, 0.0)):
		if addr:
			try:
				from logistics.transport.api_optimized import get_address_coordinates_batch

				batch = get_address_coordinates_batch([addr]) or {}
				c = batch.get(addr)
				if c and c.get("lat") is not None and c.get("lon") is not None:
					lat = c["lat"]
					lon = c["lon"]
			except Exception:
				pass

	if not label and addr:
		try:
			label = frappe.db.get_value("Address", addr, "address_title") or addr
		except Exception:
			label = addr

	try:
		lat_f = float(lat) if lat is not None else None
		lon_f = float(lon) if lon is not None else None
	except (TypeError, ValueError):
		lat_f = lon_f = None

	if (
		lat_f is None
		or lon_f is None
		or not (-90.0 <= lat_f <= 90.0)
		or not (-180.0 <= lon_f <= 180.0)
		or (lat_f == 0.0 and lon_f == 0.0)
	):
		return {
			"map_mode": "empty",
			"map_points": [],
			"label": _("Set Venue Address (with coordinates) on the Details tab to plot the show location."),
		}
	return {
		"map_mode": "pin",
		"map_points": [{"lat": lat_f, "lon": lon_f, "label": label or _("Venue")}],
		"straight_line": True,
		"label": label or _("Venue"),
	}


def _exhibit_dashboard_exhibitors_card_html(progress, map_index=0):
	"""Single sidebar card summarising exhibitors handled + ingress / egress %.

	Layout: large headline number with the ``EXHIBITORS`` label, then two slim
	progress bars (Ingress %, Egress %). No subtitle and no title row — the
	number itself is the visual anchor.
	"""
	total = int(progress.get("total") or 0)
	active = int(progress.get("active") or 0)
	in_pct = int(progress.get("ingress_pct") or 0)
	eg_pct = int(progress.get("egress_pct") or 0)
	in_done = int(progress.get("ingress_done") or 0)
	eg_done = int(progress.get("egress_done") or 0)

	exhibitors_word = _("EXHIBITOR") if total == 1 else _("EXHIBITORS")

	def _bar(label, pct, done):
		pct_clamped = max(0, min(100, int(pct)))
		bar_color = "#16a34a" if pct_clamped >= 100 else "#2563eb" if pct_clamped >= 50 else "#f59e0b"
		denom = active or total or 0
		return (
			f'<div class="exhibit-progress-row">'
			f'<div class="exhibit-progress-row-head">'
			f'<span class="exhibit-progress-label">{escape_html(label)}</span>'
			f'<span class="exhibit-progress-value">{pct_clamped}% · {done}/{denom}</span>'
			f"</div>"
			f'<div class="exhibit-progress-track">'
			f'<div class="exhibit-progress-fill" '
			f'style="width:{pct_clamped}%;background:{bar_color};"></div>'
			f"</div>"
			f"</div>"
		)

	return (
		f'<div class="sp-dash-card exhibit-summary-card" role="button" tabindex="0" '
		f'data-sp-map-idx="{int(map_index)}" '
		f'style="border-left-color:#0d6efd;">'
		f'<div class="exhibit-summary-count">'
		f'<span class="exhibit-summary-count-num">{total}</span>'
		f'<span class="exhibit-summary-count-word">{escape_html(str(exhibitors_word))}</span>'
		f"</div>"
		f'<div class="exhibit-progress-block">'
		f'{_bar(_("Ingress"), in_pct, in_done)}'
		f'{_bar(_("Egress"), eg_pct, eg_done)}'
		f"</div>"
		f"</div>"
	)


EXHIBIT_DASH_EXTRA_CSS = """
<style>
/* Floating-card layout for the Exhibit Dashboard:
   the single "Exhibitors Handled" card overlays the venue map (top-left). */
.exhibit-dash-split {
	position: relative;
	flex-wrap: nowrap !important;
	align-items: stretch;
	min-height: 480px;
}
.exhibit-dash-split .sp-dash-cards-col {
	position: absolute;
	top: 12px;
	left: 12px;
	z-index: 600;
	width: min(320px, calc(100% - 24px));
	max-width: 320px;
	min-width: 220px;
	max-height: calc(100% - 24px);
	overflow-y: auto;
	background: transparent;
	padding: 0;
	margin: 0;
	pointer-events: auto;
}
.exhibit-dash-split .sp-dash-map-wrap {
	flex: 1 1 100% !important;
	width: 100%;
	max-width: 100%;
	min-width: 0;
	min-height: 480px;
}
.exhibit-dash-split .sp-dash-map-wrap .map-box {
	height: 480px !important;
	width: 100%;
}
.sp-dash-card.exhibit-summary-card {
	cursor: default;
	background: rgba(255, 255, 255, 0.97);
	-webkit-backdrop-filter: saturate(180%) blur(6px);
	backdrop-filter: saturate(180%) blur(6px);
	box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18), 0 2px 6px rgba(0, 0, 0, 0.08);
	border: 1px solid rgba(255, 255, 255, 0.6);
	border-left: 4px solid #0d6efd;
	margin-bottom: 0;
	padding: 14px 14px 12px;
}
.sp-dash-card.exhibit-summary-card.is-selected { box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18); }
.exhibit-summary-count {
	display: flex;
	align-items: baseline;
	gap: 10px;
	margin: 0 0 10px 0;
	line-height: 1;
}
.exhibit-summary-count-num {
	font-size: 56px;
	font-weight: 800;
	color: #0d6efd;
	line-height: 1;
	letter-spacing: -0.02em;
	font-variant-numeric: tabular-nums;
}
.exhibit-summary-count-word {
	font-size: 13px;
	font-weight: 700;
	color: #495057;
	text-transform: uppercase;
	letter-spacing: 0.08em;
}
.exhibit-progress-block {
	display: flex;
	flex-direction: column;
	gap: 8px;
	margin-top: 4px;
}
.exhibit-progress-row-head {
	display: flex;
	justify-content: space-between;
	align-items: baseline;
	font-size: 11px;
	margin-bottom: 3px;
}
.exhibit-progress-label {
	font-weight: 600;
	color: #495057;
	text-transform: uppercase;
	letter-spacing: 0.03em;
}
.exhibit-progress-value {
	font-variant-numeric: tabular-nums;
	color: #6c757d;
}
.exhibit-progress-track {
	height: 6px;
	background: #e9ecef;
	border-radius: 4px;
	overflow: hidden;
}
.exhibit-progress-fill {
	height: 100%;
	border-radius: 4px;
	transition: width 0.4s ease;
}
@media (max-width: 540px) {
	.exhibit-dash-split .sp-dash-cards-col {
		position: static;
		width: 100%;
		max-width: 100%;
		margin-bottom: 10px;
	}
}
</style>
<script>
(function() {
	function mark() {
		var nodes = document.querySelectorAll('.exhibit-dash-cards');
		if (!nodes.length) return;
		nodes.forEach(function(el) {
			var split = el.closest('.sp-dash-split');
			if (split) split.classList.add('exhibit-dash-split');
		});
	}
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', mark);
	} else {
		mark();
	}
	// The cards sidebar is injected after the form loads; re-run a few times to catch late mounts.
	setTimeout(mark, 50);
	setTimeout(mark, 250);
	setTimeout(mark, 1000);
})();
</script>
"""


def _exhibit_route_panel_html(doc):
	"""Route panel: show name + venue subtext (replaces the Special Project ``Project Name`` panel)."""
	left = (getattr(doc, "project_name", None) or getattr(doc, "name", None) or "—") or "—"
	venue_label = (getattr(doc, "venue_name", None) or "").strip()
	venue_addr = (getattr(doc, "venue_address", None) or "").strip()
	if not venue_label and venue_addr:
		venue_label = frappe.db.get_value("Address", venue_addr, "address_title") or venue_addr
	venue_html = (
		f'<div class="log-ab-route-leg" style="flex:1 1 auto;">'
		f'<span class="log-ab-route-flag log-ab-route-flag--empty" aria-hidden="true"></span>'
		f'<div class="log-ab-route-leg-text">'
		f'<span class="log-ab-route-sub">{escape_html(_("Venue"))}</span>'
		f'<span class="log-ab-route-code">{escape_html(venue_label or "—")}</span>'
		f"</div></div>"
	)
	return (
		f'<div class="log-ab-route-panel">'
		f'<div class="log-ab-route-leg">'
		f'<span class="log-ab-route-flag log-ab-route-flag--empty" aria-hidden="true"></span>'
		f'<div class="log-ab-route-leg-text">'
		f'<span class="log-ab-route-sub">{escape_html(_("Exhibit Name"))}</span>'
		f'<span class="log-ab-route-code">{escape_html(str(left))}</span>'
		f"</div></div>"
		f'<div class="log-ab-route-mid"><span class="log-ab-route-arrow-h">·</span></div>'
		f"{venue_html}"
		f"</div>"
	)


@frappe.whitelist()
def get_dashboard_html(exhibit):
	"""Exhibit Dashboard — mirrors the Special Project Dashboard layout, but:
	- The Route-tab map pins the show venue (single point) instead of plotting routes
	- The left-hand cards panel collapses to a single 'Exhibitors Handled' card
	  driven by the linked Dockets, with Ingress / Egress % completion bars.
	"""
	if not exhibit:
		return "<div class='alert alert-info'>Save the exhibit to view the dashboard.</div>"
	try:
		from logistics.document_management.dashboard_layout import (
			render_special_project_interactive_route_tab_html,
		)
		from logistics.document_management.logistics_form_dashboard import (
			build_customer_hero_html,
			build_special_project_meta_cluster_html,
			render_logistics_form_dashboard_html,
		)

		doc = frappe.get_doc("Exhibit", exhibit)

		docket_rows = _exhibit_docket_status_map(doc.name)
		progress = _compute_ingress_egress_progress(docket_rows)

		status = doc.status or "Draft"
		job_rows = doc.get("lifecycle_jobs") or []
		billings = doc.get("billings") or []
		planned_cost = sum(flt(a.planned_cost or 0) for a in job_rows)
		actual_rev = sum(flt(a.actual_revenue or 0) for a in job_rows)

		def fmt(v):
			return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

		header_items = [
			("Status", status),
			("Exhibitors", str(progress.get("total") or 0)),
			("Ingress", f"{progress.get('ingress_pct') or 0}%"),
			("Egress", f"{progress.get('egress_pct') or 0}%"),
			("Move-in", str(doc.move_in_date) if doc.move_in_date else "—"),
			("Move-out", str(doc.move_out_date) if doc.move_out_date else "—"),
			("Open", str(doc.show_open_date) if doc.show_open_date else "—"),
			("Close", str(doc.show_close_date) if doc.show_close_date else "—"),
			("Budget", fmt(planned_cost)),
			("Actual Revenue", fmt(actual_rev)),
			("Billings", str(len(billings))),
		]
		if doc.priority and doc.priority != "Normal":
			header_items.append(("Priority", doc.priority))
		if doc.hall:
			header_items.append(("Hall", doc.hall))

		header_items_for_hero = list(header_items)
		hero_html = build_customer_hero_html(doc, header_items_for_hero)
		route_panel_html = _exhibit_route_panel_html(doc)
		meta_cluster_html = build_special_project_meta_cluster_html(doc)

		map_payload = _exhibit_venue_map_payload(doc)
		map_payloads = [map_payload]

		card_html = _exhibit_dashboard_exhibitors_card_html(progress, map_index=0)
		cards_sidebar_html = (
			EXHIBIT_DASH_EXTRA_CSS
			+ '<div class="exhibit-dash-cards">'
			+ card_html
			+ "</div>"
		)

		# Floating card sits at top-left ~12px in, ~320px wide, ~220px tall. Push the venue
		# pin to the right + down of the geometric center so it doesn't sit under the card.
		# Same offset doubles as fitBounds padding for any future multi-point routes.
		route_tab_override_html = render_special_project_interactive_route_tab_html(
			"exhibit-form-dash",
			map_payloads,
			cards_sidebar_html,
			pin_viewport_offset=(180, 60),
			fit_bounds_padding_top_left=(360, 240),
			fit_bounds_padding_bottom_right=(40, 40),
		)

		milestones_inner = (
			'<div class="text-muted ab-tab-empty" style="margin:0;">'
			+ escape_html(_("Open the Milestones tab to manage milestone status."))
			+ "</div>"
		)
		ms_rows = doc.get("milestones") or []
		n_ms = len(ms_rows)
		done_ms = sum(1 for m in ms_rows if str(getattr(m, "status", "") or "").strip() == "Completed")

		cfg = {
			"doctype": "Exhibit",
			"map_id_prefix": "exhibit-form-dash",
			"header_items": header_items_for_hero,
			"hero_html": hero_html,
			"route_panel_html": route_panel_html,
			"meta_cluster_html": meta_cluster_html,
			"route_tab_override_html": route_tab_override_html,
			"milestones_tab_inner_html": milestones_inner,
			"milestone_count_override": n_ms,
			"milestone_done_override": done_ms,
			"scroll_doctype": "Exhibit",
			"scroll_field": "milestone_html",
			"ring_status_from": "workflow",
			"ring_status_field": "status",
			"include_default_dg": False,
			"map_points": [],
			"map_segments": None,
		}
		return render_logistics_form_dashboard_html(doc, cfg)
	except Exception as e:
		frappe.log_error(f"Exhibit get_dashboard_html: {str(e)}", "Exhibit Dashboard")
		return "<div class='alert alert-warning'>Error loading dashboard.</div>"
