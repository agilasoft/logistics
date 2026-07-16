# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from logistics.utils.linked_service_compat import linked_service_rows
from logistics.utils.virtual_linked_services_view import VirtualLinkedServicesMixin


# Maps an Internal Job Detail row's order/booking job_type to the operational
# job_type (and its Link field back to that order/booking). Used to find the
# Job Number that ultimately tracks accounting for a Docket's internal job row.
BOOKING_TO_OPERATIONAL_JOB = {
	"Sea Booking": ("Sea Shipment", "sea_booking"),
	"Air Booking": ("Air Shipment", "air_booking"),
	"Transport Order": ("Transport Job", "transport_order"),
	"Declaration Order": ("Declaration", "declaration_order"),
	"Inbound Order": ("Warehouse Job", "reference_order"),
	"Release Order": ("Warehouse Job", "reference_order"),
	"Transfer Order": ("Warehouse Job", "reference_order"),
}


class Docket(VirtualLinkedServicesMixin, Document):
	def validate(self):
		self._ensure_org_defaults()
		self._sync_customer_from_exhibit_organizer()
		self._sync_exhibitor_metadata()
		self._validate_unique_booth_no_on_exhibit()
		from logistics.utils.document_date_validation import validate_planned_date_range

		validate_planned_date_range(self)
		self.validate_accounts()
		self._sync_charges()

	def _sync_customer_from_exhibit_organizer(self):
		"""Resolve the Account ``customer`` from ``Exhibit -> MICE Organizer.customer``.

		``MICE Project`` no longer carries a direct Customer link; the billing
		Customer is held on ``MICE Organizer`` and inherited here so postings
		that depend on the Account Customer keep working.
		"""
		if not self.exhibit:
			self.customer = None
			return
		try:
			organizer = frappe.db.get_value("MICE Project", self.exhibit, "organizer")
		except Exception:
			organizer = None
		if not organizer:
			self.customer = None
			return
		try:
			self.customer = (
				frappe.db.get_value("MICE Organizer", organizer, "customer") or None
			)
		except Exception:
			self.customer = None

	def before_save(self):
		super().before_save()
		# Create Job Number synchronously on subsequent saves if it is still missing
		# (after_insert runs the first-time enqueue; this is the safety net).
		if self.name and not self.job_number and frappe.db.exists("Docket", self.name):
			self.create_job_number_if_needed()

	def after_insert(self):
		# Create Job Number when document is first created. Deferred so the row
		# exists before lookup (matches Sea Shipment / Special Project pattern).
		frappe.enqueue(
			"logistics.mice.doctype.docket.docket.create_job_number_for_docket",
			queue="default",
			docket_name=self.name,
			company=self.company,
			branch=self.branch,
			cost_center=self.cost_center,
			profit_center=self.profit_center,
			open_date=self.docket_date or self.planned_start,
		)

	def on_update(self):
		# Push docket + project back onto every Job Number reachable through this
		# Docket (its own Job Number, and one per internal job row).
		self._sync_linked_job_numbers()

	def create_job_number_if_needed(self):
		"""Create Job Number on first save when missing (mirrors Sea Shipment / Special Project)."""
		if self.job_number:
			return
		existing = frappe.db.get_value(
			"Job Number",
			{"job_type": "Docket", "job_no": self.name},
		)
		if existing:
			self.job_number = existing
			return
		job_ref = frappe.new_doc("Job Number")
		job_ref.job_type = "Docket"
		job_ref.job_no = self.name
		job_ref.company = self.company
		job_ref.branch = self.branch
		job_ref.cost_center = self.cost_center
		job_ref.profit_center = self.profit_center
		job_ref.job_open_date = self.docket_date or self.planned_start
		job_ref.project = self.project
		job_ref.docket = self.name
		job_ref.insert(ignore_permissions=True)
		self.job_number = job_ref.name
		frappe.msgprint(_("Job Number {0} created successfully").format(job_ref.name))

	def _sync_linked_job_numbers(self):
		"""Push ``docket`` (and ``project`` if missing) onto every Job Number reachable
		from this Docket.

		Targets:
		  * The Docket's own Job Number (``self.job_number``).
		  * The Job Number of every operational job referenced by a
		    ``linked_services`` row. Rows hold booking/order doctypes; we resolve them
		    to their operational job via ``BOOKING_TO_OPERATIONAL_JOB`` and update
		    that operational job's Job Number.
		"""
		if getattr(frappe.flags, "in_install", False) or getattr(frappe.flags, "in_migrate", False):
			return

		project = (self.project or "").strip() or None
		targets: set[str] = set()

		if self.job_number:
			targets.add(self.job_number)

		for row in linked_service_rows(self) or []:
			jt = (getattr(row, "job_type", None) or "").strip()
			jn = (getattr(row, "job_no", None) or "").strip()
			if not jt or not jn:
				continue
			for op_jt, op_jn in _resolve_operational_jobs_for_internal_row(jt, jn):
				try:
					jcn = frappe.db.get_value("Job Number", {"job_type": op_jt, "job_no": op_jn})
				except Exception:
					jcn = None
				if jcn:
					targets.add(jcn)

		for jcn in targets:
			try:
				current = frappe.db.get_value(
					"Job Number", jcn, ["docket", "project"], as_dict=True
				) or {}
			except Exception:
				continue
			updates: dict[str, str] = {}
			if (current.get("docket") or "") != self.name:
				updates["docket"] = self.name
			if project and not (current.get("project") or "").strip():
				updates["project"] = project
			if not updates:
				continue
			try:
				frappe.db.set_value("Job Number", jcn, updates, update_modified=False)
			except Exception:
				frappe.log_error(
					title=f"Docket {self.name}: failed to sync Job Number {jcn}",
					message=frappe.get_traceback(),
				)

	def _sync_exhibitor_metadata(self):
		"""Auto-fill exhibitor_name / exhibitor_code from the exhibitor Customer."""
		if not self.exhibitor:
			return
		if not self.exhibitor_name:
			cust_name = frappe.db.get_value("Customer", self.exhibitor, "customer_name")
			if cust_name:
				self.exhibitor_name = cust_name
		if not self.exhibitor_code:
			try:
				meta = frappe.get_meta("Customer")
				if meta.has_field("logistics_party_code"):
					code = frappe.db.get_value(
						"Customer", self.exhibitor, "logistics_party_code"
					)
					if code:
						self.exhibitor_code = code
			except Exception:
				pass

	def _validate_unique_booth_no_on_exhibit(self):
		"""Ensure booth_no is unique within an Exhibit (including cancelled dockets)."""
		exhibit = (getattr(self, "exhibit", None) or "").strip()
		booth_no = (getattr(self, "booth_no", None) or "").strip()
		if not exhibit or not booth_no:
			return

		exists = frappe.db.get_value(
			"Docket",
			{
				"exhibit": exhibit,
				"booth_no": booth_no,
				"name": ["!=", self.name or ""],
			},
			"name",
		)
		if exists:
			frappe.throw(
				_("Booth No {0} is already used on Exhibit {1} (Docket {2}).").format(
					frappe.bold(booth_no),
					frappe.bold(exhibit),
					frappe.bold(exists),
				)
			)


	def validate_accounts(self):
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
					pc_co = frappe.db.get_value(
						"Profit Center", self.profit_center, "company"
					)
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

	def _ensure_org_defaults(self):
		"""Default company / branch / cost center / profit center / project from the parent Exhibit.

		``project`` always tracks the parent Exhibit because it is the ERPNext Project
		used as the Accounting Dimension on every posting from this docket.
		"""
		if not self.exhibit:
			return
		sp = frappe.db.get_value(
			"MICE Project",
			self.exhibit,
			["company", "cost_center", "branch", "profit_center", "project"],
			as_dict=True,
		)
		if not sp:
			return
		if not self.company and sp.get("company"):
			self.company = sp.company
		if not self.cost_center and sp.get("cost_center"):
			self.cost_center = sp.cost_center
		if not self.branch and sp.get("branch"):
			self.branch = sp.branch
		if not self.profit_center and sp.get("profit_center"):
			self.profit_center = sp.profit_center
		exhibit_project = (sp.get("project") or "").strip() or None
		if exhibit_project and getattr(self, "project", None) != exhibit_project:
			self.project = exhibit_project
		if not self.company:
			co = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
				"Global Defaults", "default_company"
			)
			if co:
				self.company = co
		if self.company and not self.cost_center:
			cc = frappe.db.get_value("Company", self.company, "cost_center")
			if cc:
				self.cost_center = cc

	def _sync_charges(self):
		if getattr(frappe.flags, "in_import", False) or getattr(frappe.flags, "in_migrate", False):
			return
		if getattr(self.flags, "ignore_charges_sync", False):
			return
		from logistics.utils.charges_calculation import (
			clear_charge_resolution_parent,
			register_charge_resolution_parent,
		)

		register_charge_resolution_parent(self)
		try:
			for charge in self.get("charges") or []:
				if hasattr(charge, "calculate_charge_amount"):
					charge.calculate_charge_amount(parent_doc=self)
		finally:
			clear_charge_resolution_parent(self)

	def get_total_weight(self):
		"""Calculate total weight from packages."""
		total_weight = 0
		for package in self.get("packages") or []:
			total_weight += flt(getattr(package, "weight", 0) or 0)
		return total_weight

	def get_total_volume(self):
		"""Calculate total volume from packages."""
		total_volume = 0
		for package in self.get("packages") or []:
			total_volume += flt(getattr(package, "volume", 0) or 0)
		return total_volume

	def _update_packing_summary(self):
		"""Update total_packages, total_volume, total_weight from packages."""
		packages = self.get("packages") or []
		self.total_packages = sum(
			flt(getattr(p, "no_of_packs", 0) or getattr(p, "quantity", 0) or 1)
			for p in packages
		)
		self.total_volume = self.get_total_volume()
		self.total_weight = self.get_total_weight()


def _resolve_operational_jobs_for_internal_row(job_type: str, job_no: str) -> list[tuple[str, str]]:
	"""Return a list of (operational_job_type, operational_job_name) candidates that the
	(``job_type``, ``job_no``) pair from a Docket's ``internal_jobs`` row maps to.

	The first candidate is always the row's own (job_type, job_no) — covering cases
	where a Job Number is created directly against the order/booking. The second
	(if applicable) is the operational shipment/job that points back at that
	order/booking through a Link field (e.g. ``Sea Shipment.sea_booking``).
	"""
	candidates: list[tuple[str, str]] = [(job_type, job_no)]

	mapping = BOOKING_TO_OPERATIONAL_JOB.get(job_type)
	if not mapping:
		return candidates

	op_dt, link_field = mapping
	try:
		if op_dt == "Warehouse Job":
			# Reference is a Dynamic Link: match on both the type and name.
			rows = frappe.get_all(
				"Warehouse Job",
				filters={"reference_order_type": job_type, "reference_order": job_no},
				pluck="name",
			)
		else:
			rows = frappe.get_all(op_dt, filters={link_field: job_no}, pluck="name")
	except Exception:
		rows = []
	for name in rows or []:
		candidates.append((op_dt, name))
	return candidates


def create_job_number_for_docket(
	docket_name,
	company,
	branch=None,
	cost_center=None,
	profit_center=None,
	open_date=None,
):
	"""Deferred: create Job Number for Docket after commit (avoids 'not found' during insert)."""
	if not frappe.db.exists("Docket", docket_name):
		return
	if frappe.db.get_value("Docket", docket_name, "job_number"):
		return
	existing = frappe.db.get_value("Job Number", {"job_type": "Docket", "job_no": docket_name})
	if existing:
		frappe.db.set_value(
			"Docket", docket_name, "job_number", existing, update_modified=False
		)
		frappe.db.commit()
		return
	project = frappe.db.get_value("Docket", docket_name, "project")
	job_ref = frappe.new_doc("Job Number")
	job_ref.job_type = "Docket"
	job_ref.job_no = docket_name
	job_ref.company = company
	job_ref.branch = branch
	job_ref.cost_center = cost_center
	job_ref.profit_center = profit_center
	job_ref.job_open_date = open_date
	job_ref.project = project
	job_ref.docket = docket_name
	job_ref.insert(ignore_permissions=True)
	frappe.db.set_value(
		"Docket", docket_name, "job_number", job_ref.name, update_modified=False
	)
	frappe.db.commit()


@frappe.whitelist()
def aggregate_volume_from_packages_remote(doc=None):
	"""
	Recompute total_packages / total_volume / total_weight from the client's doc (including unsaved packages).
	Uses frappe.get_doc(dict) instead of run_doc_method so saving and this call cannot race on modified timestamp.
	"""
	if doc is None:
		frappe.throw(_("Document is required"))
	if isinstance(doc, str):
		parsed = frappe.parse_json(doc)
		if isinstance(parsed, dict) and parsed.get("doctype"):
			doc = parsed
	try:
		if isinstance(doc, dict):
			if doc.get("doctype") != "Docket":
				frappe.throw(_("Invalid document type"))
			docket = frappe.get_doc(doc)
		else:
			docket = frappe.get_doc("Docket", doc)
	except frappe.DoesNotExistError:
		return {}
	except Exception:
		return {}
	docket._update_packing_summary()
	return {
		"total_volume": flt(docket.total_volume),
		"total_weight": flt(docket.total_weight),
		"total_packages": flt(docket.total_packages),
	}


@frappe.whitelist()
def recalculate_all_charges(docname):
	"""Recalculate charge lines on this Docket."""
	doc = frappe.get_doc("Docket", docname)
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
		frappe.log_error(str(e), "Docket - Recalculate Charges Error")
		frappe.throw(_("Error recalculating charges: {0}").format(str(e)))


@frappe.whitelist()
def post_standard_costs(docname):
	"""Post standard costs for Docket charges.

	Mirrors ``logistics.air_freight.doctype.air_shipment.air_shipment.post_standard_costs``:
	flags charge rows whose total standard cost is positive and not yet posted.
	Exhibit Charges does not currently expose ``standard_cost_posted`` /
	``total_standard_cost`` columns, so this is effectively a no-op today, but
	keeping the same surface lets the same Post menu work on Docket without
	requiring users to know which job types support standard costs.
	"""
	from frappe.utils import flt

	docket = frappe.get_doc("Docket", docname)
	posted = 0
	for ch in (docket.charges or []):
		total_std = getattr(ch, "total_standard_cost", None)
		if total_std and flt(total_std) > 0 and not getattr(ch, "standard_cost_posted", False):
			if frappe.get_meta(ch.doctype).get_field("standard_cost_posted"):
				ch.standard_cost_posted = 1
				ch.standard_cost_posted_at = frappe.utils.now()
				posted += 1
	if posted > 0:
		docket.save()
	return {
		"message": _("Posted {0} standard cost(s).").format(posted)
		if posted
		else _("No standard costs to post.")
	}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_exhibitor_options_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for Docket.exhibitor — any active Customer.

	Previously restricted to Customers listed on the Exhibit's persisted
	``dockets`` participant table. That table is now a virtual view of existing
	Dockets, so we no longer gate exhibitor selection by it — the Docket itself
	is the source of truth. We still exclude Customers that already have a
	non-cancelled Docket on the same Exhibit so the (exhibit, exhibitor)
	uniqueness assumption (used in docket naming) holds.
	"""
	conditions = ["c.disabled = 0"]
	params = {"txt": f"%{txt or ''}%", "start": start, "page_len": page_len}
	if txt:
		conditions.append("(c.name LIKE %(txt)s OR c.customer_name LIKE %(txt)s)")
	exhibit = (filters or {}).get("exhibit")
	if exhibit:
		conditions.append(
			"c.name NOT IN (SELECT d.exhibitor FROM `tabDocket` d "
			"WHERE d.exhibit = %(exhibit)s AND d.docstatus < 2 "
			"AND d.exhibitor IS NOT NULL AND d.exhibitor != '')"
		)
		params["exhibit"] = exhibit
	where_sql = " AND ".join(conditions)
	return frappe.db.sql(
		f"""
		SELECT c.name, c.customer_name
		FROM `tabCustomer` c
		WHERE {where_sql}
		ORDER BY c.customer_name ASC, c.name ASC
		LIMIT %(start)s, %(page_len)s
		""",
		params,
		as_list=True,
	)


@frappe.whitelist()
def get_recommended_booth_numbers(exhibit, start=0, limit=10):
	"""Return recommended booth numbers for an Exhibit.

	Seed is the first (earliest-created) Docket on this Exhibit with a non-empty booth_no.
	We derive the pattern by finding the last numeric group in that seed string and then
	incrementing it, preserving its zero-padding width.
	"""
	exhibit = (exhibit or "").strip()
	if not exhibit:
		frappe.throw(_("Exhibit is required."))
	if not frappe.db.exists("MICE Project", exhibit):
		frappe.throw(_("Exhibit {0} does not exist.").format(frappe.bold(exhibit)))

	start = max(0, cint(start or 0))
	limit = max(1, min(50, cint(limit or 10)))

	seed = frappe.db.get_value(
		"Docket",
		{"exhibit": exhibit, "booth_no": ["!=", ""]},
		"booth_no",
		order_by="creation asc",
	)
	seed = (seed or "").strip()
	if not seed:
		return {
			"seed_booth_no": None,
			"suggestions": [],
			"next_start": start,
			"has_more": False,
			"message": _("No booth number seed found yet for this Exhibit."),
		}

	import re

	m = re.match(r"^(.*?)(\d+)(\D*)$", seed)
	if not m:
		return {
			"seed_booth_no": seed,
			"suggestions": [],
			"next_start": start,
			"has_more": False,
			"message": _("Seed booth number has no numeric part to increment."),
		}

	prefix, num_str, suffix = m.group(1), m.group(2), m.group(3)
	width = len(num_str)
	base_num = int(num_str)

	used = set(
		(b or "").strip()
		for b in frappe.get_all("Docket", filters={"exhibit": exhibit}, pluck="booth_no")
		if (b or "").strip()
	)

	suggestions = []
	offset = start

	# Generate until we have `limit` unused suggestions; hard cap avoids infinite loops.
	hard_cap = 5000
	tries = 0
	while len(suggestions) < limit and tries < hard_cap:
		n = base_num + 1 + offset
		candidate = f"{prefix}{str(n).zfill(width)}{suffix}"
		offset += 1
		tries += 1
		if candidate in used:
			continue
		used.add(candidate)
		suggestions.append(candidate)

	return {
		"seed_booth_no": seed,
		"suggestions": suggestions,
		"next_start": start + offset,
		"has_more": True if suggestions else False,
	}
