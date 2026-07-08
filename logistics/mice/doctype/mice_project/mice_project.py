# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import escape_html, flt, get_url_to_form

from logistics.job_management.logistics_job_status import JOB_STATUS_SELECT_OPTIONS

from logistics.mice import mice_project_lifecycle
from logistics.mice.mice_project_lifecycle import validate_lifecycle_stage_advance
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


def _docket_allocation_basis(docket_name):
	"""Return (weight_basis, volume_basis, target_title) from a Docket's package totals."""
	docket = frappe.get_doc("Docket", docket_name)
	docket._update_packing_summary()
	title = (
		docket.exhibitor_name
		or docket.title
		or docket.booth_no
		or docket.exhibitor
		or docket.name
	)
	return flt(docket.total_weight), flt(docket.total_volume), title


class MICEProject(Document):
	@property
	def dockets(self):
		"""Live snapshot of every Docket linked to this MICE Project.

		``MICE Project Docket`` is a virtual child doctype (``is_virtual: 1``).
		Frappe's modern computed-child-table mechanism
		(``frappe.model.base_document._update_computed_ct_prop``) detects this
		class-level ``@property`` and delegates to it instead of trying to
		``safe_eval`` the field's ``options`` string (which holds the child
		doctype name ``"MICE Project Docket"`` — not a valid Python
		expression, so without this property Frappe raises ``SyntaxError``
		while serialising the document to JSON for the form).

		The rows are derived from real ``Docket`` records at access time, so
		the Dockets tab always reflects current links without persisting
		anything against the virtual child table.
		"""
		return self._build_dockets_view()

	def _build_dockets_view(self):
		"""Return a list of dicts describing every non-cancelled Docket linked
		to this MICE Project, in display order."""
		if not getattr(self, "name", None) or getattr(self, "__islocal", False):
			return []
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
			return []
		return [
			{
				"docket": r.get("name"),
				"exhibitor": r.get("exhibitor"),
				"exhibitor_name": r.get("exhibitor_name"),
				"booth_no": r.get("booth_no"),
				"status": r.get("status"),
				"docket_date": r.get("docket_date"),
			}
			for r in rows
		]

	def _validate_links(self):
		from logistics.special_projects.special_project_charge_lifecycle import (
			normalize_lifecycle_job_order_job_fields,
		)

		normalize_lifecycle_job_order_job_fields(self)
		super()._validate_links()

	def validate(self):
		self._drop_virtual_dockets_rows()
		self._ensure_org_defaults()
		self._validate_org_accounts()
		validate_internal_job_activity_codes(self, module_filter=FOR_EXHIBITS)
		validate_lifecycle_stage_advance(self)
		self._recalculate_consolidation_charge_rows()
		self._recalculate_consolidation_charge_totals()
		self._recalculate_cost_allocation_totals()

	def get_organizer_customer(self):
		"""Return the billing Customer linked to this project's Organizer, if any.

		Downstream Dockets / MICE Jobs / MICE Orders and the ERPNext Project
		creation path call this to resolve a Customer for billing context now
		that ``MICE Project`` no longer carries a direct ``customer`` link.
		"""
		if not self.organizer:
			return None
		try:
			return frappe.db.get_value("MICE Organizer", self.organizer, "customer") or None
		except Exception:
			return None

	def _ensure_org_defaults(self):
		"""Default ``company`` from the linked ERPNext Project (and ``cost_center``
		from that Company) so the Exhibit-level Organization fields are always
		populated. Mirrors ``Docket._ensure_org_defaults`` so the cascade
		``Exhibit -> Docket -> Booking/Order`` carries the same accounting
		dimensions all the way down.
		"""
		if not self.company and self.project:
			try:
				project_company = frappe.db.get_value("Project", self.project, "company")
			except Exception:
				project_company = None
			if project_company:
				self.company = project_company

		if not self.company:
			co = (
				frappe.defaults.get_user_default("Company")
				or frappe.db.get_single_value("Global Defaults", "default_company")
			)
			if co:
				self.company = co

		if self.company and not self.cost_center:
			try:
				cc = frappe.db.get_value("Company", self.company, "cost_center")
			except Exception:
				cc = None
			if cc:
				self.cost_center = cc

	def _validate_org_accounts(self):
		"""Ensure cost_center / profit_center / branch belong to the chosen Company.

		Mirrors ``Docket.validate_accounts`` so misconfigured links surface as
		early as possible (before they're rolled down to dockets / bookings).
		"""
		if not self.company:
			return

		if self.cost_center:
			cc_co = frappe.db.get_value("Cost Center", self.cost_center, "company")
			if cc_co and cc_co != self.company:
				frappe.throw(
					_("Cost Center {0} does not belong to Company {1}").format(
						self.cost_center, self.company
					)
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
						frappe.throw(
							_("Branch {0} does not belong to Company {1}").format(
								self.branch, self.company
							)
						)
			except Exception as e:
				if "Unknown column" not in str(e) and "1054" not in str(e):
					raise

	def _drop_virtual_dockets_rows(self):
		"""Discard any ``dockets`` rows posted back from the form.

		``MICE Project Docket`` is virtual, so DB persistence already ignores
		these rows; clearing them here also keeps the Version diff quiet
		(otherwise every save would record the property-derived snapshot as
		"added"). The class-level ``dockets`` ``@property`` rebuilds the rows
		from live ``Docket`` records on the next read.
		"""
		self.__dict__["dockets"] = []

	def _recalculate_consolidation_charge_rows(self):
		"""Recompute each consolidation charge row before summing or allocating."""
		for row in self.get("consolidation_charges") or []:
			row.calculate_charge_amount()
			row.calculate_allocated_amount()

	def _recalculate_consolidation_charge_totals(self):
		"""Sum ``total_amount`` across consolidation_charges rows into ``total_consolidation_charges``."""
		rows = self.get("consolidation_charges") or []
		self.total_consolidation_charges = sum(flt(r.total_amount) for r in rows)

	def _recalculate_cost_allocation_totals(self):
		"""Sum ``allocated_amount`` across cost_allocations rows into ``total_allocated_amount``."""
		rows = self.get("cost_allocations") or []
		self.total_allocated_amount = sum(flt(r.allocated_amount) for r in rows)

	def autoname(self):
		"""Use ERPNext Project ID as Exhibit ID (created in before_insert)."""
		if self.flags.get("erpnext_project_name"):
			self.name = self.flags.erpnext_project_name

	def before_insert(self):
		"""Create ERPNext Project first, then use its ID as this document's ID."""
		self._create_erpnext_project_before_insert()
		self._normalize_default_lifecycle_stage()
		mice_project_lifecycle.load_standard_service_activities(self)

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

	def _resolve_allocation_target_type(self):
		"""Pick the allocation target type based on the parent setting and what data is available.

		Auto: prefer MICE Jobs when at least one is linked, otherwise Dockets.
		Explicit: Dockets / MICE Jobs as configured.
		"""
		setting = (self.cost_allocation_target or "Auto").strip()
		if setting == "Dockets":
			return "Docket"
		if setting == "MICE Jobs":
			return "MICE Job"

		if not self.name or getattr(self, "__islocal", False):
			return "Docket"
		exhibit_jobs = frappe.db.count(
			"MICE Job",
			filters={"exhibit": self.name, "docstatus": ["<", 2]},
		)
		if exhibit_jobs:
			return "MICE Job"
		return "Docket"

	def _fetch_dockets_for_allocation(self):
		"""Live Dockets linked to this MICE Project (excluding cancelled), ordered by docket_date."""
		if not self.name or getattr(self, "__islocal", False):
			return []
		return frappe.get_all(
			"Docket",
			filters={"exhibit": self.name, "docstatus": ["<", 2]},
			fields=["name", "exhibitor_name", "exhibitor", "title", "booth_no"],
			order_by="docket_date asc, creation asc",
		)

	def _fetch_exhibit_jobs_for_allocation(self):
		"""Live MICE Jobs linked to this MICE Project (excluding cancelled), ordered by job_date."""
		if not self.name or getattr(self, "__islocal", False):
			return []
		return frappe.get_all(
			"MICE Job",
			filters={"exhibit": self.name, "docstatus": ["<", 2]},
			fields=["name", "title"],
			order_by="job_date asc, creation asc",
		)

	def _refresh_cost_allocation_targets(self, target_type):
		"""Replace ``cost_allocations`` rows with the live target list, preserving custom % entries."""
		existing_pct = {}
		existing_value_basis = {}
		for row in self.get("cost_allocations") or []:
			key = (row.target_type, row.target)
			existing_pct[key] = flt(row.cost_allocation_percentage)
			existing_value_basis[key] = flt(row.value_basis)

		self.set("cost_allocations", [])

		if target_type == "Docket":
			rows = self._fetch_dockets_for_allocation()
			for r in rows:
				key = ("Docket", r.get("name"))
				wb, vb, title = _docket_allocation_basis(r.get("name"))
				self.append(
					"cost_allocations",
					{
						"target_type": "Docket",
						"target": r.get("name"),
						"target_title": title,
						"cost_allocation_percentage": existing_pct.get(key, 0),
						"weight_basis": wb,
						"volume_basis": vb,
						"value_basis": existing_value_basis.get(key, 0),
					},
				)
			return len(rows)

		rows = self._fetch_exhibit_jobs_for_allocation()
		for r in rows:
			title = r.get("title") or r.get("name")
			key = ("MICE Job", r.get("name"))
			self.append(
				"cost_allocations",
				{
					"target_type": "MICE Job",
					"target": r.get("name"),
					"target_title": title,
					"cost_allocation_percentage": existing_pct.get(key, 0),
					"weight_basis": 0,
					"volume_basis": 0,
					"value_basis": existing_value_basis.get(key, 0),
				},
			)
		return len(rows)

	def _per_target_allocation_factor(self, charge, allocation_rows, total_targets):
		"""Return list of factors (0..1) summing to ~1 across allocation_rows for one charge.

		Mirrors Air / Sea Consolidation allocation behaviour:
		Equal / Weight-based / Volume-based / Value-based / Custom.
		Falls back to Equal when basis values are missing or sum to 0.
		"""
		if total_targets <= 0:
			return []

		method = (
			(charge.allocation_method or "").strip()
			or (self.cost_allocation_basis or "Equal").strip()
		)

		def _equal():
			share = 1.0 / float(total_targets)
			return [share for _ in allocation_rows]

		if method == "Equal" or not method:
			return _equal()

		if method == "Weight-based":
			weights = [flt(r.weight_basis) for r in allocation_rows]
			total = sum(weights)
			if total <= 0:
				return _equal()
			return [w / total for w in weights]

		if method == "Volume-based":
			volumes = [flt(r.volume_basis) for r in allocation_rows]
			total = sum(volumes)
			if total <= 0:
				return _equal()
			return [v / total for v in volumes]

		if method == "Value-based":
			values = [flt(r.value_basis) for r in allocation_rows]
			total = sum(values)
			if total <= 0:
				return _equal()
			return [v / total for v in values]

		percentages = [flt(r.cost_allocation_percentage) for r in allocation_rows]
		total_pct = sum(percentages)
		if total_pct <= 0:
			return _equal()
		return [p / total_pct for p in percentages]

	def _apply_allocation_to_targets(self):
		"""Compute per-target ``allocated_amount`` and overall ``cost_allocation_percentage``.

		For each charge row, distribute its ``total_amount`` across cost_allocations rows by
		the row's allocation method (or the parent ``cost_allocation_basis`` fallback).
		"""
		allocations = self.get("cost_allocations") or []
		if not allocations:
			return

		for row in allocations:
			row.allocated_amount = 0

		grand_total = 0.0
		n = len(allocations)
		for charge in self.get("consolidation_charges") or []:
			amount = flt(charge.total_amount)
			if amount <= 0:
				continue
			factors = self._per_target_allocation_factor(charge, allocations, n)
			row_amounts = [amount * f for f in factors]
			# Distribute rounding so per-charge sum equals charge.total_amount.
			rounded = [round(x, 2) for x in row_amounts]
			diff = round(amount - sum(rounded), 2)
			for i in range(len(rounded) - 1, -1, -1):
				if rounded[i] > 0 and diff != 0:
					rounded[i] = round(rounded[i] + diff, 2)
					break
			for r, addend in zip(allocations, rounded):
				r.allocated_amount = flt(r.allocated_amount) + flt(addend)
			grand_total += amount

		# Compute overall % from the totals so users can see the effective split.
		if grand_total > 0:
			for row in allocations:
				row.cost_allocation_percentage = (
					(flt(row.allocated_amount) / grand_total) * 100.0
				)
		else:
			for row in allocations:
				row.cost_allocation_percentage = 0

	def _effective_allocation_method(self, charge):
		"""Return the allocation method for one charge row (row override or parent default)."""
		return (
			(charge.allocation_method or "").strip()
			or (self.cost_allocation_basis or "Equal").strip()
		)

	def _validate_allocation_prerequisites(self):
		"""Ensure targets and charge amounts exist before applying allocation."""
		allocations = self.get("cost_allocations") or []
		if not allocations:
			target_type = self._resolve_allocation_target_type()
			frappe.throw(
				_("No {0} linked to this MICE Project. Create one first, then try again.").format(
					target_type
				),
				title=_("No Allocation Targets"),
			)

		self._recalculate_consolidation_charge_rows()
		self._recalculate_consolidation_charge_totals()

		charges = self.get("consolidation_charges") or []
		if not charges:
			frappe.throw(
				_("Add at least one Consolidation Charge before allocating costs."),
				title=_("No Charges"),
			)

		if flt(self.total_consolidation_charges) <= 0:
			frappe.throw(
				_(
					"Consolidation charges have no allocatable amount. "
					"Enter charge lines with Rate greater than 0 before allocating."
				),
				title=_("No Charge Amount"),
			)

		uses_custom = (self.cost_allocation_basis or "").strip() == "Custom"
		for charge in charges:
			if self._effective_allocation_method(charge) == "Custom":
				uses_custom = True
				break

		if uses_custom:
			total_pct = sum(flt(r.cost_allocation_percentage) for r in allocations)
			if total_pct <= 0:
				frappe.throw(
					_(
						"Custom allocation requires Cost Allocation % on each target row. "
						"Enter percentages in the Cost Allocation table, then try again."
					),
					title=_("Custom Percentages Required"),
				)

	@frappe.whitelist()
	def refresh_cost_allocation_targets(self, target_type=None):
		"""Refresh the Cost Allocation table with live Dockets / MICE Jobs.

		``target_type`` (optional): ``"Docket"`` or ``"MICE Job"``. Falls back to the parent's
		``cost_allocation_target`` (Auto / Dockets / MICE Jobs).
		"""
		if target_type:
			tt = target_type.strip()
			if tt not in ("Docket", "MICE Job"):
				frappe.throw(_("target_type must be 'Docket' or 'MICE Job'."))
			resolved = tt
		else:
			resolved = self._resolve_allocation_target_type()
		count = self._refresh_cost_allocation_targets(resolved)
		self._recalculate_cost_allocation_totals()
		self.save()
		return {
			"target_type": resolved,
			"targets_loaded": count,
			"message": _("Loaded {0} {1}(s) into Cost Allocation.").format(count, resolved),
		}

	@frappe.whitelist()
	def allocate_costs(self, allocation_basis=None, target_type=None):
		"""Allocate consolidation charge costs across Dockets or MICE Jobs.

		``allocation_basis`` (optional): ``Equal`` / ``Weight-based`` / ``Volume-based`` /
		``Value-based`` / ``Custom``. Stored as ``cost_allocation_basis`` (and used as the
		fallback for any charge row that does not set its own ``allocation_method``).

		``target_type`` (optional): ``Auto`` / ``Dockets`` / ``MICE Jobs``. Stored as
		``cost_allocation_target`` and used to refresh the target list.
		"""
		if allocation_basis:
			basis = allocation_basis.strip()
			allowed = {"Equal", "Weight-based", "Volume-based", "Value-based", "Custom"}
			if basis not in allowed:
				frappe.throw(_("Allocation basis must be one of: {0}.").format(", ".join(sorted(allowed))))
			self.cost_allocation_basis = basis

		if target_type:
			tt = target_type.strip()
			if tt not in ("Auto", "Docket", "Dockets", "MICE Job", "MICE Jobs"):
				frappe.throw(_("Allocation target must be Auto, Dockets, or MICE Jobs."))
			self.cost_allocation_target = (
				"Dockets"
				if tt in ("Docket", "Dockets")
				else ("MICE Jobs" if tt in ("MICE Job", "MICE Jobs") else "Auto")
			)

		resolved = self._resolve_allocation_target_type()
		self._refresh_cost_allocation_targets(resolved)
		self._validate_allocation_prerequisites()

		self._apply_allocation_to_targets()
		self._recalculate_consolidation_charge_totals()
		self._recalculate_cost_allocation_totals()
		self.save()

		return {
			"target_type": resolved,
			"targets_loaded": len(self.get("cost_allocations") or []),
			"total_charges": flt(self.total_consolidation_charges),
			"total_allocated": flt(self.total_allocated_amount),
			"message": _("Costs allocated across {0} {1}(s).").format(
				len(self.get("cost_allocations") or []), resolved
			),
		}

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
			project.customer = self.get_organizer_customer()
			project.expected_start_date = self.planned_start or self.start_date
			project.expected_end_date = self.planned_end or self.end_date
			project.status = self._map_status_to_project(self.status)
			project.project_type = (
				self.project_type
				or frappe.db.get_single_value("MICE Settings", "default_project_type")
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
def get_cost_allocation_target_basis(target_type, target):
	"""Return weight/volume basis and display title for a cost allocation target row."""
	target_type = _strip_or_none(target_type)
	target = _strip_or_none(target)
	if target_type == "Docket" and target:
		wb, vb, title = _docket_allocation_basis(target)
		return {"weight_basis": wb, "volume_basis": vb, "target_title": title}
	if target_type == "MICE Job" and target:
		title = frappe.db.get_value("MICE Job", target, "title") or target
		return {"weight_basis": 0, "volume_basis": 0, "target_title": title}
	return {}


@frappe.whitelist()
def get_sales_quote_defaults_from_exhibit(exhibit_name, customer=None):
	"""Return Sales Quote field defaults pre-filled from an Exhibit.

	Customer (exhibitor) may be omitted; if not provided, it will not be set on the quote.
	"""
	exhibit_name = _strip_or_none(exhibit_name)
	if not exhibit_name:
		frappe.throw(_("Exhibit is required."))
	if not frappe.db.exists("MICE Project", exhibit_name):
		frappe.throw(_("Exhibit {0} does not exist.").format(frappe.bold(exhibit_name)))

	customer = _strip_or_none(customer)

	ep = frappe.get_doc("MICE Project", exhibit_name)

	defaults = {
		"main_service": "MICE",
		"quotation_type": "Project",
		"naming_series": "PQ.#####",
		"exhibit": ep.name,
	}
	if customer:
		defaults["customer"] = customer
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
	if not frappe.db.exists("MICE Project", exhibit_name):
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
	if not frappe.db.exists("MICE Project", exhibit_name):
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
	doc = frappe.get_doc("MICE Project", show)
	doc.set(
		"lifecycle_jobs",
		[r for r in doc.get("lifecycle_jobs") or [] if not (r.activity_code or "").strip()],
	)
	mice_project_lifecycle.load_standard_lifecycle_jobs(doc)
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
	doc = frappe.get_doc("MICE Project", show)
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


_OPERATIONAL_JOB_TYPES = (
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Declaration",
	"Warehouse Job",
)

_SERVICE_LABEL_BY_JOB_TYPE = {
	"Air Shipment": "Air",
	"Sea Shipment": "Sea",
	"Transport Job": "Transport",
	"Declaration": "Customs",
	"Warehouse Job": "Warehousing",
}

_SERVICE_LABEL_ORDER = ("Air", "Sea", "Transport", "Customs", "Warehousing")


def _resolve_docket_operational_jobs(docket_name):
	"""Return deduplicated operational job keys for a Docket."""
	seen = set()
	results = []

	def _add(job_type, job_no):
		jt = (job_type or "").strip()
		jn = (job_no or "").strip()
		if jt not in _OPERATIONAL_JOB_TYPES or not jn:
			return
		key = (jt, jn)
		if key in seen:
			return
		seen.add(key)
		results.append({"job_type": jt, "job_no": jn})

	for row in frappe.get_all(
		"Job Number",
		filters={"docket": docket_name, "job_type": ["in", list(_OPERATIONAL_JOB_TYPES)]},
		fields=["job_type", "job_no"],
	):
		_add(row.get("job_type"), row.get("job_no"))

	from logistics.mice.doctype.docket.docket import _resolve_operational_jobs_for_internal_row

	for row in frappe.get_all(
		"Internal Job Detail",
		filters={"parent": docket_name, "parenttype": "Docket"},
		fields=["job_type", "job_no"],
	):
		jt = (row.get("job_type") or "").strip()
		jn = (row.get("job_no") or "").strip()
		if not jt or not jn:
			continue
		for op_jt, op_jn in _resolve_operational_jobs_for_internal_row(jt, jn):
			_add(op_jt, op_jn)

	return results


def _fetch_transport_job_endpoints(transport_job_names):
	"""Return ``{job_name: (pick_address, drop_address)}`` from first/last legs."""
	if not transport_job_names:
		return {}
	endpoints = {}
	for leg in frappe.get_all(
		"Transport Leg",
		filters={"transport_job": ["in", transport_job_names], "docstatus": ["<", 2]},
		fields=["transport_job", "pick_address", "drop_address"],
		order_by="transport_job asc, creation asc",
	):
		job_name = (leg.get("transport_job") or "").strip()
		if not job_name:
			continue
		if job_name not in endpoints:
			endpoints[job_name] = {
				"first_pick": (leg.get("pick_address") or "").strip(),
				"last_drop": (leg.get("drop_address") or "").strip(),
			}
		else:
			drop = (leg.get("drop_address") or "").strip()
			if drop:
				endpoints[job_name]["last_drop"] = drop
	return {
		job_name: (vals["first_pick"], vals["last_drop"])
		for job_name, vals in endpoints.items()
	}


def _fetch_operational_job_statuses(job_keys):
	"""Batch-fetch operational job fields linked to a docket."""
	by_type = {jt: [] for jt in _OPERATIONAL_JOB_TYPES}
	for item in job_keys or []:
		jt = (item.get("job_type") or "").strip()
		jn = (item.get("job_no") or "").strip()
		if jt in by_type and jn:
			by_type[jt].append(jn)

	status_map = {}
	transport_endpoints = _fetch_transport_job_endpoints(by_type.get("Transport Job") or [])

	for job_type, names in by_type.items():
		if not names:
			continue
		if job_type in ("Air Shipment", "Sea Shipment"):
			fields = ["name", "job_status", "origin_port", "destination_port", "modified"]
			for row in frappe.get_all(job_type, filters={"name": ["in", names]}, fields=fields):
				status = (row.get("job_status") or "").strip() or "Draft"
				status_map[(job_type, row.name)] = {
					"job_type": job_type,
					"name": row.name,
					"service_label": _SERVICE_LABEL_BY_JOB_TYPE[job_type],
					"job_status": status,
					"origin_code": (row.get("origin_port") or "").strip(),
					"destination_code": (row.get("destination_port") or "").strip(),
					"origin_kind": "unloco",
					"destination_kind": "unloco",
					"modified": row.get("modified"),
				}
		elif job_type == "Transport Job":
			for row in frappe.get_all(
				"Transport Job",
				filters={"name": ["in", names]},
				fields=["name", "status", "modified"],
			):
				status = (row.get("status") or "").strip() or "Draft"
				first_pick, last_drop = transport_endpoints.get(row.name, ("", ""))
				status_map[(job_type, row.name)] = {
					"job_type": job_type,
					"name": row.name,
					"service_label": _SERVICE_LABEL_BY_JOB_TYPE[job_type],
					"job_status": status,
					"origin_code": first_pick,
					"destination_code": last_drop,
					"origin_kind": "address",
					"destination_kind": "address",
					"modified": row.get("modified"),
				}
		elif job_type == "Declaration":
			for row in frappe.get_all(
				"Declaration",
				filters={"name": ["in", names]},
				fields=["name", "job_status", "port_of_loading", "port_of_discharge", "modified"],
			):
				status = (row.get("job_status") or "").strip() or "Draft"
				status_map[(job_type, row.name)] = {
					"job_type": job_type,
					"name": row.name,
					"service_label": _SERVICE_LABEL_BY_JOB_TYPE[job_type],
					"job_status": status,
					"origin_code": (row.get("port_of_loading") or "").strip(),
					"destination_code": (row.get("port_of_discharge") or "").strip(),
					"origin_kind": "unloco",
					"destination_kind": "unloco",
					"modified": row.get("modified"),
				}
		elif job_type == "Warehouse Job":
			for row in frappe.get_all(
				"Warehouse Job",
				filters={"name": ["in", names]},
				fields=["name", "job_status", "reference_order_type", "reference_order", "modified"],
			):
				status = (row.get("job_status") or "").strip() or "Draft"
				status_map[(job_type, row.name)] = {
					"job_type": job_type,
					"name": row.name,
					"service_label": _SERVICE_LABEL_BY_JOB_TYPE[job_type],
					"job_status": status,
					"origin_code": (row.get("reference_order_type") or "").strip(),
					"destination_code": (row.get("reference_order") or "").strip(),
					"origin_kind": "text",
					"destination_kind": "text",
					"modified": row.get("modified"),
				}
	return status_map


def _batch_unloco_table_labels(codes):
	"""Return ``{code: "City, CC"}`` labels for UNLOCO codes (batch lookup)."""
	unique = {str(c).strip() for c in (codes or []) if c and str(c).strip()}
	if not unique:
		return {}

	labels = {}
	for row in frappe.get_all(
		"UNLOCO",
		filters={"name": ["in", list(unique)]},
		fields=["name", "city", "location_name", "country_code"],
	):
		code = row.name
		city = (row.get("city") or "").strip() or (row.get("location_name") or "").strip()
		cc = (row.get("country_code") or "").strip()
		if city and cc:
			labels[code] = f"{city}, {cc}"
		elif city:
			labels[code] = city
		elif cc:
			labels[code] = cc
		else:
			labels[code] = code

	for code in unique:
		if code not in labels:
			labels[code] = code
	return labels


def _batch_address_table_labels(names):
	"""Return ``{address_name: address_title}`` labels for Address links (batch lookup)."""
	unique = {str(n).strip() for n in (names or []) if n and str(n).strip()}
	if not unique:
		return {}

	labels = {}
	for row in frappe.get_all(
		"Address",
		filters={"name": ["in", list(unique)]},
		fields=["name", "address_title"],
	):
		title = (row.get("address_title") or "").strip()
		labels[row.name] = title or row.name

	for name in unique:
		if name not in labels:
			labels[name] = name
	return labels


def _operational_job_sort_key(job):
	label = (job.get("service_label") or "").strip()
	try:
		order = _SERVICE_LABEL_ORDER.index(label)
	except ValueError:
		order = len(_SERVICE_LABEL_ORDER)
	return (order, job.get("name") or "")


def _resolve_endpoint_label(code, kind, unloco_labels, address_labels):
	if not code:
		return "—"
	if kind == "unloco":
		return unloco_labels.get(code) or code
	if kind == "address":
		return address_labels.get(code) or code
	return code


def _job_status_slug(status):
	return (status or "draft").strip().lower().replace(" ", "_")


def _job_status_badge_html(status):
	label = (status or "Draft").strip() or "Draft"
	slug = _job_status_slug(label)
	return (
		f'<span class="exhibit-shipment-status-badge {escape_html(slug)}">'
		f"{escape_html(label)}</span>"
	)


def _shipment_row_icon_html(status):
	if (status or "").strip().lower() == "draft":
		return (
			'<span class="exhibit-shipment-row-icon exhibit-shipment-row-icon--draft" aria-hidden="true">'
			'<i class="fa fa-file-o"></i></span>'
		)
	return (
		'<span class="exhibit-shipment-row-icon exhibit-shipment-row-icon--active" aria-hidden="true">'
		'<i class="fa fa-check"></i></span>'
	)


def _format_shipment_modified(modified):
	if not modified:
		return "—"
	return frappe.format_value(modified, {"fieldtype": "Datetime"})


def _build_operational_jobs_card_html(jobs, status_counts, unloco_labels, address_labels):
	"""Job Details card: header, status summary, and unified operational jobs table."""
	n = len(jobs)
	job_word = _("job") if n == 1 else _("jobs")
	summary_html = " · ".join(
		f"<strong>{escape_html(status)}:</strong> {count}"
		for status, count in status_counts.items()
	)

	header = (
		f'<div class="exhibit-shipment-details-card">'
		f'<div class="exhibit-shipment-details-header">'
		f'<span class="exhibit-shipment-details-title">{escape_html(_("Job Details"))}</span>'
		f'<span class="exhibit-shipment-details-count">{n} {escape_html(str(job_word))}</span>'
		f"</div>"
		f'<div class="exhibit-shipment-details-summary">{summary_html}</div>'
		f'<div class="exhibit-shipment-details-table-wrap">'
		f'<table class="exhibit-shipment-details-table">'
		f"<thead><tr>"
		f'<th>{escape_html(_("Service"))}</th>'
		f'<th>{escape_html(_("Job ID"))}</th>'
		f'<th>{escape_html(_("Origin"))}</th>'
		f'<th>{escape_html(_("Destination"))}</th>'
		f'<th>{escape_html(_("Status"))}</th>'
		f'<th>{escape_html(_("Last Updated"))}</th>'
		f"</tr></thead><tbody>"
	)

	rows = []
	for job in jobs:
		origin_label = _resolve_endpoint_label(
			job.get("origin_code"), job.get("origin_kind"), unloco_labels, address_labels
		)
		dest_label = _resolve_endpoint_label(
			job.get("destination_code"), job.get("destination_kind"), unloco_labels, address_labels
		)
		link = f'<a href="{get_url_to_form(job["job_type"], job["name"])}">{escape_html(job["name"])}</a>'
		id_cell = (
			f'<div class="exhibit-shipment-id-cell">'
			f'{_shipment_row_icon_html(job.get("job_status"))}'
			f'<span class="exhibit-shipment-id-text">{link}</span>'
			f"</div>"
		)
		rows.append(
			f"<tr>"
			f'<td class="exhibit-shipment-col-service">{escape_html(job.get("service_label") or "—")}</td>'
			f'<td class="exhibit-shipment-col-id">{id_cell}</td>'
			f"<td>{escape_html(origin_label)}</td>"
			f"<td>{escape_html(dest_label)}</td>"
			f"<td>{_job_status_badge_html(job.get('job_status'))}</td>"
			f'<td class="exhibit-shipment-col-updated">{escape_html(_format_shipment_modified(job.get("modified")))}</td>'
			f"</tr>"
		)

	return header + "".join(rows) + "</tbody></table></div></div>"


def _aggregate_job_status_counts(statuses):
	"""Return ordered ``{status: count}`` using standard job-status ordering."""
	counts = {}
	for status in statuses or []:
		label = (status or "").strip() or "Draft"
		counts[label] = counts.get(label, 0) + 1

	order = [line.strip() for line in JOB_STATUS_SELECT_OPTIONS.split("\n") if line.strip()]
	ordered = {}
	for status in order:
		if counts.get(status):
			ordered[status] = counts[status]
	for status, count in counts.items():
		if status not in ordered:
			ordered[status] = count
	return ordered


EXHIBIT_JOB_STATUS_TAB_CSS = """
<style>
.exhibit-job-status-list { display: flex; flex-direction: column; gap: 8px; }
.exhibit-docket-status-item {
	margin: 0; border: 1px solid #e0e0e0; border-radius: 6px; background: #fff; overflow: hidden;
}
.exhibit-docket-status-item-summary {
	list-style: none; cursor: pointer; user-select: none;
	padding: 10px 12px; font-size: 13px; display: flex; align-items: center; gap: 10px;
	flex-wrap: wrap; background: #f8f9fa; border-bottom: 1px solid #e9ecef;
}
.exhibit-docket-status-item-summary::-webkit-details-marker { display: none; }
.exhibit-docket-status-item-summary::before {
	content: ""; display: inline-block; width: 0; height: 0;
	border-left: 5px solid transparent; border-right: 5px solid transparent;
	border-top: 6px solid #6c757d; transition: transform 0.2s ease; flex-shrink: 0;
}
.exhibit-docket-status-item[open] > .exhibit-docket-status-item-summary::before {
	transform: rotate(180deg);
}
.exhibit-docket-status-item:not([open]) > .exhibit-docket-status-item-summary { border-bottom: none; }
.exhibit-docket-status-item-main { flex: 1 1 auto; min-width: 0; display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; }
.exhibit-docket-status-item-meta { color: #6c757d; font-size: 12px; }
.exhibit-docket-status-badge {
	display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px;
	font-weight: 600; background: #e9ecef; color: #495057; white-space: nowrap;
}
.exhibit-docket-shipment-count {
	margin-left: auto; font-size: 12px; color: #6c757d; white-space: nowrap;
	font-variant-numeric: tabular-nums;
}
.exhibit-docket-status-body { padding: 10px 12px 12px; font-size: 12px; }
.exhibit-job-status-empty { color: #6c757d; font-style: italic; margin: 0; }
.exhibit-shipment-details-card {
	border: 1px solid #e9ecef; border-radius: 8px; background: #fff; overflow: hidden;
}
.exhibit-shipment-details-header {
	display: flex; align-items: center; justify-content: space-between; gap: 12px;
	padding: 12px 14px; border-bottom: 1px solid #e9ecef;
}
.exhibit-shipment-details-title { font-size: 14px; font-weight: 600; color: #212529; }
.exhibit-shipment-details-count { font-size: 12px; color: #6c757d; white-space: nowrap; }
.exhibit-shipment-details-summary {
	padding: 10px 14px; font-size: 12px; color: #495057; border-bottom: 1px solid #f1f3f5;
}
.exhibit-shipment-details-summary strong { font-weight: 600; color: #212529; }
.exhibit-shipment-details-table-wrap { overflow-x: auto; }
.exhibit-shipment-details-table {
	width: 100%; border-collapse: collapse; font-size: 12px;
}
.exhibit-shipment-details-table th {
	text-align: left; padding: 10px 14px; font-weight: 600; color: #6c757d;
	border-bottom: 1px solid #e9ecef; white-space: nowrap;
}
.exhibit-shipment-details-table td {
	padding: 10px 14px; color: #212529; border-bottom: 1px solid #f1f3f5; vertical-align: middle;
}
.exhibit-shipment-details-table tbody tr:last-child td { border-bottom: none; }
.exhibit-shipment-id-cell { display: flex; align-items: center; gap: 10px; min-width: 0; }
.exhibit-shipment-id-text { font-weight: 600; min-width: 0; }
.exhibit-shipment-id-text a { color: #212529; text-decoration: none; }
.exhibit-shipment-id-text a:hover { color: #0d6efd; text-decoration: underline; }
.exhibit-shipment-row-icon {
	display: inline-flex; align-items: center; justify-content: center;
	width: 28px; height: 28px; border-radius: 6px; flex-shrink: 0; font-size: 13px;
}
.exhibit-shipment-row-icon--draft { background: #f1f3f5; color: #6c757d; }
.exhibit-shipment-row-icon--active { background: #d1e7dd; color: #0f5132; }
.exhibit-shipment-col-updated { color: #6c757d; white-space: nowrap; }
.exhibit-shipment-col-service { font-weight: 600; white-space: nowrap; }
.exhibit-shipment-status-badge {
	display: inline-block; padding: 3px 10px; border-radius: 999px;
	font-size: 11px; font-weight: 600; white-space: nowrap;
}
.exhibit-shipment-status-badge.draft { background: #e9ecef; color: #495057; }
.exhibit-shipment-status-badge.submitted { background: #d1e7dd; color: #0f5132; }
.exhibit-shipment-status-badge.in_progress { background: #cfe2ff; color: #084298; }
.exhibit-shipment-status-badge.completed { background: #d1e7dd; color: #0f5132; }
.exhibit-shipment-status-badge.closed { background: #e2e3e5; color: #383d41; }
.exhibit-shipment-status-badge.reopened { background: #fff3cd; color: #856404; }
.exhibit-shipment-status-badge.cancelled { background: #f8d7da; color: #721c24; }
</style>
"""


def _build_exhibit_job_status_tab_html(exhibit_name, docket_rows=None):
	"""Build expandable docket rows with operational job status counts."""
	docket_rows = docket_rows if docket_rows is not None else _exhibit_docket_status_map(exhibit_name)
	if not docket_rows:
		msg = escape_html(_("No dockets linked to this exhibit yet."))
		return EXHIBIT_JOB_STATUS_TAB_CSS + f'<div class="text-muted ab-tab-empty">{msg}</div>'

	items = []
	for row in docket_rows:
		docket_name = row.get("docket") or ""
		if not docket_name:
			continue

		job_keys = _resolve_docket_operational_jobs(docket_name)
		status_map = _fetch_operational_job_statuses(job_keys)
		jobs = sorted(status_map.values(), key=_operational_job_sort_key)
		status_counts = _aggregate_job_status_counts(j.get("job_status") for j in jobs)

		exhibitor = (row.get("exhibitor") or "").strip()
		booth_no = (row.get("booth_no") or "").strip()
		meta_parts = [p for p in (exhibitor, booth_no and f"{_('Booth')} {booth_no}") if p]
		meta_html = (
			f'<span class="exhibit-docket-status-item-meta">{" · ".join(escape_html(p) for p in meta_parts)}</span>'
			if meta_parts
			else ""
		)

		docket_status = (row.get("status") or "Draft").strip()
		docket_link = (
			f'<a href="{get_url_to_form("Docket", docket_name)}">{escape_html(docket_name)}</a>'
		)
		job_word = _("job") if len(jobs) == 1 else _("jobs")
		summary = (
			f'<details class="exhibit-docket-status-item">'
			f'<summary class="exhibit-docket-status-item-summary">'
			f'<div class="exhibit-docket-status-item-main">'
			f"{docket_link}{meta_html}"
			f'<span class="exhibit-docket-status-badge">{escape_html(docket_status)}</span>'
			f"</div>"
			f'<span class="exhibit-docket-shipment-count">'
			f"{len(jobs)} {escape_html(str(job_word))}"
			f"</span>"
			f"</summary>"
		)

		if not jobs:
			body = (
				f'<div class="exhibit-docket-status-body">'
				f'<p class="exhibit-job-status-empty">'
				f'{escape_html(_("No operational jobs linked to this docket yet."))}'
				f"</p>"
				f"</div>"
			)
		else:
			unloco_codes = []
			address_names = []
			for job in jobs:
				if job.get("origin_kind") == "unloco" and job.get("origin_code"):
					unloco_codes.append(job["origin_code"])
				if job.get("destination_kind") == "unloco" and job.get("destination_code"):
					unloco_codes.append(job["destination_code"])
				if job.get("origin_kind") == "address" and job.get("origin_code"):
					address_names.append(job["origin_code"])
				if job.get("destination_kind") == "address" and job.get("destination_code"):
					address_names.append(job["destination_code"])
			unloco_labels = _batch_unloco_table_labels(unloco_codes)
			address_labels = _batch_address_table_labels(address_names)
			card_html = _build_operational_jobs_card_html(
				jobs, status_counts, unloco_labels, address_labels
			)
			body = f'<div class="exhibit-docket-status-body">{card_html}</div>'

		items.append(summary + body + "</details>")

	return EXHIBIT_JOB_STATUS_TAB_CSS + f'<div class="exhibit-job-status-list">{"".join(items)}</div>'


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


def _exhibit_venue_label(doc):
	"""Best-effort display label for the venue (used as image alt text)."""
	label = (getattr(doc, "venue_name", None) or "").strip()
	if label:
		return label
	addr = (getattr(doc, "venue_address", None) or "").strip()
	if addr:
		try:
			return frappe.db.get_value("Address", addr, "address_title") or addr
		except Exception:
			return addr
	return ""


def _exhibit_dashboard_exhibitors_card_html(progress):
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
		f'<div class="sp-dash-card exhibit-summary-card" '
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


EXHIBIT_DASH_IMAGE_CSS = """
<style>
/* MICE Project Dashboard: static venue image with floating "Exhibitors Handled" card. */
.exhibit-image-split {
	position: relative;
	display: flex;
	width: 100%;
	min-height: 480px;
}
.exhibit-image-split .exhibit-image-cards-col {
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
.exhibit-image-split .exhibit-image-wrap {
	flex: 1 1 100%;
	width: 100%;
	max-width: 100%;
	min-width: 0;
	min-height: 480px;
}
.exhibit-venue-image-box {
	position: relative;
	width: 100%;
	height: 480px;
	border-radius: 8px;
	overflow: hidden;
	background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
	border: 1px solid var(--ro-border-soft, #e9ecef);
}
.exhibit-venue-image {
	display: block;
	width: 100%;
	height: 100%;
	object-fit: cover;
	object-position: center;
}
.exhibit-venue-image-empty {
	position: absolute;
	inset: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	color: #6c757d;
	padding: 20px;
}
.exhibit-venue-image-empty .fa {
	font-size: 36px;
	margin-bottom: 12px;
	opacity: 0.6;
}
.exhibit-venue-image-empty-msg {
	font-size: 14px;
	max-width: 320px;
	line-height: 1.45;
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
	.exhibit-image-split { flex-direction: column; }
	.exhibit-image-split .exhibit-image-cards-col {
		position: static;
		width: 100%;
		max-width: 100%;
		margin-bottom: 10px;
	}
	.exhibit-venue-image-box { height: 320px; }
}
</style>
"""


def _exhibit_dashboard_venue_image_tab_html(doc, cards_sidebar_html):
	"""Render the MICE Project Dashboard "Route" tab as a static venue image.

	Replaces the previous map view. Users upload an image into the ``venue_image``
	field on the Details tab; the exhibitors progress card floats over the
	top-left of the image (same layout language as the previous map-based view).
	"""
	image_url = (getattr(doc, "venue_image", None) or "").strip()
	venue_label = _exhibit_venue_label(doc)

	if image_url:
		image_inner = (
			f'<img src="{escape_html(image_url)}" '
			f'alt="{escape_html(venue_label or _("Venue"))}" '
			f'class="exhibit-venue-image" />'
		)
	else:
		msg = escape_html(
			_("Upload a Venue Image on the Details tab to display the show floor here.")
		)
		image_inner = (
			'<div class="exhibit-venue-image-empty">'
			'<i class="fa fa-image" aria-hidden="true"></i>'
			f'<div class="exhibit-venue-image-empty-msg">{msg}</div>'
			"</div>"
		)

	return (
		EXHIBIT_DASH_IMAGE_CSS
		+ '<div class="exhibit-image-split">'
		+ f'<div class="exhibit-image-cards-col">{cards_sidebar_html}</div>'
		+ '<div class="exhibit-image-wrap">'
		+ '<div class="exhibit-venue-image-box">'
		+ image_inner
		+ "</div>"
		+ "</div>"
		+ "</div>"
	)


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
	- The Route-tab map is replaced with a static venue image uploaded by the
	  user (``venue_image`` field on the Details tab).
	- The left-hand cards panel collapses to a single 'Exhibitors Handled' card
	  driven by the linked Dockets, with Ingress / Egress % completion bars.
	"""
	if not exhibit:
		return "<div class='alert alert-info'>Save the exhibit to view the dashboard.</div>"
	try:
		from logistics.document_management.logistics_form_dashboard import (
			build_customer_hero_html,
			build_special_project_meta_cluster_html,
			render_logistics_form_dashboard_html,
		)

		doc = frappe.get_doc("MICE Project", exhibit)

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

		cards_sidebar_html = _exhibit_dashboard_exhibitors_card_html(progress)

		route_tab_override_html = _exhibit_dashboard_venue_image_tab_html(doc, cards_sidebar_html)

		job_status_inner = _build_exhibit_job_status_tab_html(doc.name, docket_rows)

		cfg = {
			"doctype": "MICE Project",
			"map_id_prefix": "exhibit-form-dash",
			"header_items": header_items_for_hero,
			"hero_html": hero_html,
			"route_panel_html": route_panel_html,
			"meta_cluster_html": meta_cluster_html,
			"route_tab_override_html": route_tab_override_html,
			"scroll_doctype": "MICE Project",
			"scroll_field": "milestone_html",
			"ring_status_from": "workflow",
			"ring_status_field": "status",
			"include_default_dg": False,
			"map_points": [],
			"map_segments": None,
			"extra_dashboard_tabs": [
				{
					"suffix": "job_status",
					"label": _("Job Status"),
					"count": len(docket_rows),
					"inner_html": job_status_inner,
					"after_suffix": "route",
				}
			],
		}
		return render_logistics_form_dashboard_html(doc, cfg)
	except Exception as e:
		frappe.log_error(f"Exhibit get_dashboard_html: {str(e)}", "Exhibit Dashboard")
		return "<div class='alert alert-warning'>Error loading dashboard.</div>"
