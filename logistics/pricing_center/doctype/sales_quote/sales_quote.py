# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import format_date, today, flt, getdate, cint

from logistics.utils.module_integration import copy_sales_quote_fields_to_target
from logistics.utils.party_address_contact_from_masters import (
	append_transport_order_door_leg_from_party_masters,
	apply_party_address_contact_from_source_or_masters,
)
from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults
from logistics.utils.sales_quote_validity import throw_if_sales_quote_expired_for_creation
from logistics.utils.charge_service_type import (
	canonical_charge_service_type_for_storage,
	count_sales_quote_charges_for_service,
	filter_sales_quote_charge_rows_for_operational_doc,
	sales_quote_charge_filters,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.sales_quote_routing import apply_sales_quote_routing_to_booking
from logistics.utils.sales_quote_routing_defaults import apply_sales_quote_routing_defaults
from logistics.utils.service_role_rules import (
	SERVICE_ROLE_MAIN,
	apply_main_service_flags,
	get_main_service_name,
	get_main_service_type,
	is_linked_service_satellite,
	is_main_service_doc,
)


def map_sales_quote_entry_type_to_air_booking(sales_quote_entry_type):
	"""
	Validate and return entry type for Air Booking. Options are aligned across Sales Quote and Air Booking.
	
	Unified options (industry standard): Direct, Transit, Transshipment, ATA Carnet
	
	Args:
		sales_quote_entry_type: Entry type value from Sales Quote
	
	Returns:
		str: Entry type value for Air Booking, or None if invalid
	"""
	if not sales_quote_entry_type:
		return None
	
	valid_entry_types = ["Direct", "Transit", "Transshipment", "ATA Carnet"]
	if sales_quote_entry_type in valid_entry_types:
		return sales_quote_entry_type
	
	frappe.log_error(
		f"Invalid entry_type value '{sales_quote_entry_type}' from Sales Quote. "
		f"Valid values: {', '.join(valid_entry_types)}.",
		"Sales Quote - Entry Type"
	)
	return None


# Unit types allowed when Sales Quote customs charges are synced to Declaration Order / Declaration Charges.
# Aligned with Declaration Charges (includes Value for Percentage Break; Job/Trip supported).
CUSTOMS_ALLOWED_UNIT_TYPES = frozenset({
	"Weight", "Volume", "Distance", "Package", "Piece", "TEU", "Container", "Operation Time", "Job", "Trip", "Value",
})
CUSTOMS_ALLOWED_UNIT_TYPES_DISPLAY = (
	"Weight", "Volume", "Distance", "Package", "Piece", "TEU", "Container", "Operation Time", "Job", "Trip", "Value"
)


def _sq_strip_or_none(val):
	if val is None:
		return None
	s = str(val).strip()
	return s or None


def _sq_charge_row_matches_service(row, service_type_label):
	st = (
		getattr(row, "service_type", None)
		if not isinstance(row, dict)
		else row.get("service_type")
	)
	return sales_quote_charge_service_types_equal(st, service_type_label)


def _sync_sales_quote_charge_load_type_filter_flags_for_row(row):
	"""Keep hidden per-mode flags aligned with service_type (used for Load Type link filtering in the desk)."""
	row.load_type_filter_air = 0
	row.load_type_filter_sea = 0
	row.load_type_filter_transport = 0
	row.load_type_filter_customs = 0
	row.load_type_filter_warehousing = 0
	st = canonical_charge_service_type_for_storage(getattr(row, "service_type", None))
	if st == "air":
		row.load_type_filter_air = 1
	elif st == "sea":
		row.load_type_filter_sea = 1
	elif st == "transport":
		row.load_type_filter_transport = 1
	elif st == "custom":
		row.load_type_filter_customs = 1
	elif st == "warehousing":
		row.load_type_filter_warehousing = 1


def _sales_quote_has_warehousing_for_contract(sales_quote):
	"""Legacy warehousing child rows or unified charges with service_type Warehousing (matches sales_quote.js + get_rates_from_sales_quote)."""
	if sales_quote.get("warehousing"):
		return True
	for row in sales_quote.get("charges") or []:
		if _sq_charge_row_matches_service(row, "Warehousing"):
			return True
	return False


def _is_special_project_programme_quote(doc) -> bool:
	quotation_type = getattr(doc, "quotation_type", None)
	main_service = getattr(doc, "main_service", None)
	return quotation_type == "Project" or main_service == "Special Project"


def get_special_project_for_sales_quote(sales_quote_name):
	"""Special Project linked to this quote via ``Special Project.sales_quote``."""
	if not _sq_strip_or_none(sales_quote_name):
		return None
	return frappe.db.get_value(
		"Special Project",
		{"sales_quote": sales_quote_name},
		"name",
	)


def resolve_erpnext_project_name_for_sales_quote(sales_quote):
	"""ERPNext ``Project.project_name`` used when creating a Special Project from this quote."""
	name = _sq_strip_or_none(getattr(sales_quote, "project_name", None))
	if name:
		return name
	customer = _sq_strip_or_none(getattr(sales_quote, "customer", None))
	if not customer:
		return None
	return _sq_strip_or_none(
		frappe.db.get_value("Customer", customer, "customer_name")
	) or customer


def validate_erpnext_project_name_available_for_sales_quote(sales_quote):
	"""Reject when a new Special Project would need an ERPNext Project name that already exists."""
	if not _is_special_project_programme_quote(sales_quote):
		return
	if cint(getattr(sales_quote, "additional_charge", 0)):
		return
	if not frappe.db.exists("DocType", "Project"):
		return
	# MICE / multi-service Project quotes often leave project_name blank (customer-name fallback)
	# but only create Dockets — not a new ERPNext Project — until Special Project content exists.
	if not _sales_quote_has_special_project_content(sales_quote):
		return

	project_name = resolve_erpnext_project_name_for_sales_quote(sales_quote)
	if not project_name:
		return

	existing_project = frappe.db.get_value("Project", {"project_name": project_name}, "name")
	if not existing_project:
		return

	sp_name = get_special_project_for_sales_quote(sales_quote.name) if sales_quote.name else None
	if sp_name:
		linked = frappe.db.get_value("Special Project", sp_name, "project")
		if linked and linked == existing_project:
			return

	frappe.throw(
		_(
			"ERPNext Project name {0} is already used by Project {1}. "
			"Choose a different Project Name on this quote before submitting."
		).format(frappe.bold(project_name), frappe.bold(existing_project)),
		title=_("Duplicate Project Name"),
	)


# Sales Quote Special Project tab → Special Project Details tab (same fieldnames).
_SALES_QUOTE_TO_SPECIAL_PROJECT_DETAIL_FIELDS = (
	"project_name",
	"project_type",
	"priority",
	"planned_start",
	"planned_end",
	"description",
	"special_handling_instructions",
)


def _copy_sales_quote_special_project_details(sales_quote, special_project):
	"""Copy programme header fields from Sales Quote onto Special Project."""
	for fn in _SALES_QUOTE_TO_SPECIAL_PROJECT_DETAIL_FIELDS:
		if not hasattr(special_project, fn):
			continue
		val = getattr(sales_quote, fn, None)
		if val is not None and val != "":
			special_project.set(fn, val)


def _sync_special_project_fields_from_sales_quote(sales_quote):
	"""Push programme detail fields from Sales Quote to its Special Project (``sales_quote`` link)."""
	if not _is_special_project_programme_quote(sales_quote):
		return
	sp_name = get_special_project_for_sales_quote(sales_quote.name)
	if not sp_name:
		return
	sp = frappe.get_doc("Special Project", sp_name)
	_copy_sales_quote_special_project_details(sales_quote, sp)
	sp.flags.ignore_permissions = True
	try:
		sp.save(ignore_permissions=True)
	except frappe.ValidationError:
		frappe.log_error(
			title=_("Sales Quote Special Project sync"),
			message=frappe.get_traceback(),
		)


def _sales_quote_has_special_project_content(sales_quote):
	"""Project quotes: Special Project charge lines or project resource rows."""
	if sales_quote.get("project_resources"):
		return True
	for row in sales_quote.get("charges") or []:
		if _sq_charge_row_matches_service(row, "Special Project"):
			return True
	return False


def _sync_show_from_sales_quote(doc):
	"""When a Sales Quote references an Exhibit, back-fill empty show dates on the Exhibit."""
	ep_name = _sq_strip_or_none(getattr(doc, "exhibit", None))
	if not ep_name or not frappe.db.exists("MICE Project", ep_name):
		return
	row = frappe.db.get_value(
		"MICE Project",
		ep_name,
		["show_open_date", "show_close_date"],
		as_dict=True,
	)
	if not row:
		return
	updates = {}
	open_d = getattr(doc, "exhibit_show_open_date", None)
	if open_d and not row.get("show_open_date"):
		updates["show_open_date"] = open_d
	close_d = getattr(doc, "exhibit_show_close_date", None)
	if close_d and not row.get("show_close_date"):
		updates["show_close_date"] = close_d
	if not updates:
		return
	frappe.db.set_value("MICE Project", ep_name, updates)


def _sync_special_project_from_sales_quote(doc):
	"""Back-fill empty customer / sales_quote on the Special Project owned by this quote."""
	sp_name = get_special_project_for_sales_quote(doc.name)
	if not sp_name:
		return
	row = frappe.db.get_value(
		"Special Project",
		sp_name,
		["customer", "sales_quote"],
		as_dict=True,
	)
	if not row:
		return
	updates = {}
	cust = _sq_strip_or_none(getattr(doc, "customer", None))
	if cust and not _sq_strip_or_none(row.get("customer")):
		updates["customer"] = cust
	if not _sq_strip_or_none(row.get("sales_quote")):
		updates["sales_quote"] = doc.name
	if not updates:
		return
	frappe.db.set_value("Special Project", sp_name, updates, update_modified=False)


def throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote):
	"""Additional-charge quotes (from Change Request) bill an existing job — do not spawn new bookings or orders."""
	if not cint(getattr(sales_quote, "additional_charge", 0)):
		return
	job = _sq_strip_or_none(getattr(sales_quote, "job", None))
	jt = _sq_strip_or_none(getattr(sales_quote, "job_type", None))
	msg = _(
		"This Sales Quote is for additional charges on an existing job (Change Request). "
		"Creating a new booking or order from it is not allowed."
	)
	if job and jt:
		msg = msg + " " + _("Additional charges apply on {0} {1}.").format(jt, job)
	elif job:
		msg = msg + " " + _("Additional charges apply on job {0}.").format(job)
	frappe.throw(msg, title=_("Additional-Charge Quote"))


class SalesQuote(Document):
	def __setup__(self):
		"""Keep virtual ``linked_services`` initialised; honour desk grid rows on save."""
		self._stage_linked_services_from_form()

	@property
	def linked_services(self):
		"""Live view of Linked Service documents owned by this Sales Quote."""
		if self.flags.get("_linked_services_from_form"):
			return self.__dict__.get("linked_services") or []
		rows = self.__dict__.get("linked_services")
		if rows and any(getattr(r, "__islocal", None) for r in rows):
			self.flags._linked_services_from_form = True
			return rows
		if self.flags.get("_linked_services_view_cached"):
			return self.__dict__.get("linked_services") or []
		value = self._build_linked_services_view()
		self.__dict__["linked_services"] = value
		self.flags._linked_services_view_cached = True
		return value

	def _build_linked_services_view(self):
		"""Return Linked Service Detail row dicts sourced from ``Linked Service`` documents."""
		if not getattr(self, "name", None) or getattr(self, "__islocal", False):
			return []
		from logistics.logistics.doctype.linked_service.linked_service import (
			get_linked_services_for_sales_quote,
		)

		view_fields = {
			"linked_service",
			"service_type",
			"job_type",
			"job_no",
			"job_description",
		}
		for fn in (
			"air_house_type",
			"airline",
			"freight_agent",
			"sea_house_type",
			"freight_agent_sea",
			"shipping_line",
			"transport_mode",
			"load_type",
			"direction",
			"origin_port",
			"destination_port",
			"transport_template",
			"vehicle_type",
			"container_type",
			"container_no",
			"location_type",
			"location_from",
			"location_to",
			"pick_mode",
			"drop_mode",
			"customs_authority",
			"declaration_type",
			"customs_broker",
			"customs_charge_category",
			"planned_cost",
			"actual_cost",
			"planned_revenue",
			"actual_revenue",
		):
			view_fields.add(fn)

		rows = []
		for ls in get_linked_services_for_sales_quote(self.name):
			row = {"linked_service": ls.name}
			for fn in view_fields:
				if fn == "linked_service":
					continue
				if hasattr(ls, fn):
					row[fn] = getattr(ls, fn, None)
			rows.append(row)
		return rows

	def _drop_virtual_linked_services_rows(self):
		"""Clear desk grid rows after sync; source of truth is ``Linked Service`` documents."""
		self.flags._linked_services_from_form = False
		self.flags._linked_services_view_cached = False
		if "linked_services" in self.__dict__:
			del self.__dict__["linked_services"]

	def _stage_linked_services_from_form(self):
		"""Honour desk/API grid rows on save, including an intentional empty grid."""
		if "linked_services" not in self.__dict__:
			return
		if self.__dict__.get("linked_services") is None:
			self.__dict__["linked_services"] = []
		if not self.flags.get("_linked_services_view_cached"):
			self.flags._linked_services_from_form = True

	def _honour_linked_services_form_rows(self):
		"""Rows staged in ``__dict__`` (desk grid / API append) must sync before the virtual view reloads."""
		self._stage_linked_services_from_form()

	def _discard_duplicate_linked_services_staging(self):
		"""Desk duplicate should not implicitly create Linked Services from copied grid rows."""
		if not self.is_new():
			return
		marker = (getattr(self, "logistics_duplicate_from", None) or "").strip()
		if not marker or self.flags.get("_linked_services_copy_applied"):
			return
		if "linked_services" not in self.__dict__:
			return
		self.__dict__["linked_services"] = []
		self.flags._linked_services_from_form = True

	def validate(self):
		"""Validate Sales Quote data"""
		self._discard_duplicate_linked_services_staging()
		self._honour_linked_services_form_rows()
		for ch in getattr(self, "charges", None) or []:
			_sync_sales_quote_charge_load_type_filter_flags_for_row(ch)
		self.validate_naming_series_quotation_type()
		self.validate_blanket_quotation()
		self.clear_hidden_one_off_fields_for_non_one_off()
		self.ensure_one_off_status()
		self.validate_one_off_required_parameters()
		self.validate_direction_ports()
		self.validate_freight_agent_locations()
		self.validate_programme_required_parameters()
		self.validate_planned_dates()
		self.validate_additional_charge_job()
		self.validate_load_type_matches_service()
		self.validate_transport_mode_matches_service()
		self.validate_freight_agent_matches_service()
		self.validate_transport_template_compatibility()
		self.validate_vehicle_type_load_type()
		self.validate_vehicle_type_capacity()
		apply_sales_quote_routing_defaults(self)
		self.validate_multimodal_main_job()
		self.validate_customs_unit_types()
		self.validate_linked_service_charge_tagging()
		self.auto_scope_title()
		self.refresh_charge_parameters_display()
		from logistics.utils.operational_exchange_rates import resolve_sales_quote_charge_exchange_rates

		resolve_sales_quote_charge_exchange_rates(self)

	def validate_planned_dates(self):
		"""Hard-block inverted Planned Start/End; soft-warn when window ends before quote date."""
		from logistics.utils.document_date_validation import (
			validate_planned_date_range,
			warn_if_planned_end_before_reference,
		)

		validate_planned_date_range(self)
		warn_if_planned_end_before_reference(
			self,
			reference_field="date",
			reference_label=_("Quote Date"),
		)

	def refresh_charge_parameters_display(self):
		"""Populate read-only parameters text on charge rows from tagged services."""
		from logistics.utils.sales_quote_charge_parameters import (
			refresh_sales_quote_charge_parameters_display,
		)

		for row in getattr(self, "charges", None) or []:
			refresh_sales_quote_charge_parameters_display(row, self)

	def after_insert(self):
		_sync_special_project_from_sales_quote(self)
		_sync_show_from_sales_quote(self)
		self._drop_virtual_linked_services_rows()

	def on_update(self):
		_sync_special_project_from_sales_quote(self)
		_sync_show_from_sales_quote(self)
		_sync_special_project_fields_from_sales_quote(self)
		self._drop_virtual_linked_services_rows()
		from logistics.utils.module_integration import propagate_high_value_from_sales_quote
		propagate_high_value_from_sales_quote(self.name)

	def clear_hidden_one_off_fields_for_non_one_off(self):
		"""Prevent link validation errors from hidden scope parameter fields on Project quotes."""
		if getattr(self, "quotation_type", None) in ("One-off", "Regular"):
			return
		if getattr(self, "transport_mode", None):
			self.transport_mode = None

	def ensure_one_off_status(self):
		"""``status`` is read-only in the desk; keep it aligned with ``converted_to_doc``."""
		if getattr(self, "quotation_type", None) != "One-off":
			return
		ref = _sq_strip_or_none(getattr(self, "converted_to_doc", None))
		if ref:
			normalized = normalize_one_off_converted_to_ref(
				ref,
				getattr(self, "converted_to_doctype", None) if hasattr(self, "converted_to_doctype") else None,
				getattr(self, "converted_to_name", None) if hasattr(self, "converted_to_name") else None,
			)
			if normalized and normalized != ref:
				self.converted_to_doc = normalized
				ref = normalized
		expected = "Converted" if ref else "Draft"
		if (getattr(self, "status", None) or "").strip() != expected:
			self.status = expected

	def before_submit(self):
		"""Validate before submitting the document"""
		self.validate_main_service_has_charges()
		self.validate_air_sea_charge_ports_before_submit()
		self.validate_erpnext_project_name_before_submit()

	def validate_erpnext_project_name_before_submit(self):
		"""Block submit when the programme name would collide with an existing ERPNext Project."""
		validate_erpnext_project_name_available_for_sales_quote(self)

	def validate_air_sea_charge_ports_before_submit(self):
		"""At least one Air/Sea charge line must have Origin Port and Destination Port (row or quote-level fallbacks)."""
		if getattr(self, "quotation_type", None) == "Project":
			return
		doc_origin, doc_dest = self._document_level_origin_destination_for_charges()
		has_air_or_sea = False
		has_complete_corridor = False
		for row in getattr(self, "charges", None) or []:
			st = _sq_strip_or_none(getattr(row, "service_type", None))
			if canonical_charge_service_type_for_storage(st) not in ("air", "sea"):
				continue
			has_air_or_sea = True
			row_o = _sq_strip_or_none(getattr(row, "origin_port", None))
			row_d = _sq_strip_or_none(getattr(row, "destination_port", None))
			eff_o = row_o or doc_origin
			eff_d = row_d or doc_dest
			if eff_o and eff_d:
				has_complete_corridor = True
				break
		if has_air_or_sea and not has_complete_corridor:
			frappe.throw(
				_(
					"At least one Air or Sea charge line must have Origin Port and Destination Port "
					"(on that line or from the quote: Origin Port / Destination Port, or Location From / Location To). "
					"Other Air/Sea lines may leave ports blank."
				),
				title=_("Charge Ports Required"),
			)

	def _document_level_origin_destination_for_charges(self):
		"""Match booking/shipment behavior: prefer port fields, then transport locations."""
		o = _sq_strip_or_none(getattr(self, "origin_port", None))
		d = _sq_strip_or_none(getattr(self, "destination_port", None))
		if not o:
			o = _sq_strip_or_none(getattr(self, "location_from", None))
		if not d:
			d = _sq_strip_or_none(getattr(self, "location_to", None))
		return o, d

	def validate_main_service_has_charges(self):
		"""Require at least one charge line for the selected Main Service (aligned with UI create-booking logic)."""
		if getattr(self, "change_request", None):
			return
		main = getattr(self, "main_service", None)
		if not main:
			return
		if main == "Warehousing":
			if not _sales_quote_has_warehousing_for_contract(self):
				frappe.throw(
					_("Add warehousing details or at least one charge line with Service Type \"Warehousing\"."),
					title=_("Main Service Has No Charges"),
				)
			return
		if main == "Special Project":
			if not _sales_quote_has_special_project_content(self):
				frappe.throw(
					_(
						"Add at least one charge line with Service Type \"Special Project\" "
						"or at least one row on the Special Project tab Resources table."
					),
					title=_("Main Service Has No Charges"),
				)
			return
		charges = getattr(self, "charges", None) or []
		if not any(_sq_charge_row_matches_service(r, main) for r in charges):
			frappe.throw(
				_("Add at least one charge line with Service Type \"{0}\" (Main Service).").format(main),
				title=_("Main Service Has No Charges"),
			)

	def on_submit(self):
		"""Additional-charge quotes: push charge lines to the linked job with sales_quote_link."""
		from logistics.pricing_center.additional_charge_to_job import apply_additional_charge_sales_quote_to_job

		apply_additional_charge_sales_quote_to_job(self)

	def on_cancel(self):
		"""Remove job charge lines created from this additional-charge Sales Quote."""
		from logistics.pricing_center.additional_charge_to_job import remove_additional_charge_sales_quote_from_job

		remove_additional_charge_sales_quote_from_job(self)

	def validate_naming_series_quotation_type(self):
		"""Validate that naming_series matches quotation_type"""
		if not self.quotation_type or not self.naming_series:
			return  # Skip validation if either field is empty
		
		# Mapping of quotation_type to allowed naming_series prefixes (dot and hyphen both accepted)
		allowed_prefixes_mapping = {
			"Regular": ("SQU.", "SQU-"),
			"One-off": ("OOQ.", "OOQ-"),
			"Project": ("PQ.", "PQ-"),
		}
		
		allowed_prefixes = allowed_prefixes_mapping.get(self.quotation_type)
		if not allowed_prefixes:
			return  # Unknown quotation_type, skip validation
		
		if not any(self.naming_series.startswith(p) for p in allowed_prefixes):
			expected_example = {
				"Regular": "SQU.#########",
				"One-off": "OOQ.#####",
				"Project": "PQ.#####",
			}.get(self.quotation_type, "")
			expected_display = " / ".join(allowed_prefixes)
			frappe.throw(
				_("Naming Series '{0}' does not match Quotation Type '{1}'. Expected series starting with '{2}' (e.g., {3}).").format(
					self.naming_series,
					self.quotation_type,
					expected_display,
					expected_example,
				),
				title=_("Naming Series Mismatch"),
			)

	def validate_blanket_quotation(self):
		"""Blanket Quotation is allowed only on Regular quotes."""
		if not cint(getattr(self, "blanket_quotation", 0)):
			return
		qt = (getattr(self, "quotation_type", None) or "").strip()
		if qt != "Regular":
			frappe.throw(
				_("Blanket Quotation is only allowed when Quotation Type is Regular."),
				title=_("Blanket Quotation"),
			)
		if cint(getattr(self, "additional_charge", 0)):
			frappe.throw(
				_("Additional-charge Sales Quotes cannot be marked as Blanket Quotation."),
				title=_("Blanket Quotation"),
			)
		if self.docstatus == 1 and not (getattr(self, "charges", None) or []):
			frappe.throw(
				_("Submitted Blanket Quotation must have at least one charge line."),
				title=_("Blanket Quotation"),
			)

	def validate_additional_charge_job(self):
		"""When Additional Charge is checked, Job Type and Job are required."""
		if getattr(self, "additional_charge", 0):
			if not getattr(self, "job_type", None) or not getattr(self, "job", None):
				frappe.throw(_("For Additional Charge quotes, Job Type and Job are required."))

	def validate_one_off_required_parameters(self):
		"""Require core scope parameters for Regular and One-off quotes based on service."""
		quotation_type = getattr(self, "quotation_type", None)
		if quotation_type not in ("One-off", "Regular"):
			return

		# Additional-charge quotes are linked to an existing job and should not
		# require full one-off routing parameters to be created.
		if getattr(self, "additional_charge", 0):
			return

		main_service = getattr(self, "main_service", None)

		# Air and Sea flows depend on origin/destination ports.
		if main_service in ("Air", "Sea"):
			missing_fields = []
			if not getattr(self, "origin_port", None):
				missing_fields.append(_("Origin Port"))
			if not getattr(self, "destination_port", None):
				missing_fields.append(_("Destination Port"))
			if missing_fields:
				frappe.throw(
					_("For {0} {1} quotes, these fields are required: {2}.").format(
						quotation_type,
						main_service,
						", ".join(missing_fields),
					)
				)

		# Transport flow depends on concrete pickup/drop details.
		if main_service == "Transport":
			missing_fields = []
			if not getattr(self, "location_type", None):
				missing_fields.append(_("Location Type"))
			if not getattr(self, "location_from", None):
				missing_fields.append(_("Location From"))
			if not getattr(self, "location_to", None):
				missing_fields.append(_("Location To"))
			if missing_fields:
				frappe.throw(
					_("For {0} Transport quotes, these fields are required: {1}.").format(
						quotation_type,
						", ".join(missing_fields),
					)
				)

		if main_service == "MICE":
			missing_fields = []
			if not _sq_strip_or_none(getattr(self, "exhibit", None)):
				missing_fields.append(_("MICE Project"))
			if not getattr(self, "exhibit_show_open_date", None):
				missing_fields.append(_("Exhibit Open Date"))
			if not getattr(self, "exhibit_show_close_date", None):
				missing_fields.append(_("Exhibit Close Date"))
			if missing_fields:
				frappe.throw(
					_("For {0} Exhibits quotes, these fields are required: {1}.").format(
						quotation_type,
						", ".join(missing_fields),
					)
				)

	def validate_direction_ports(self):
		"""Direction must align with origin/destination ports for the quote company country."""
		from logistics.utils.direction_port_validation import validate_sales_quote_direction_ports

		validate_sales_quote_direction_ports(self)

	def validate_freight_agent_locations(self):
		"""UNLOCO ports must fall within the selected freight agent's covered locations."""
		from logistics.utils.freight_agent_location_validation import (
			validate_sales_quote_freight_agent_locations,
		)

		validate_sales_quote_freight_agent_locations(self)

	def validate_programme_required_parameters(self):
		"""Require programme header links and exhibit show fields based on main_service / quotation_type."""
		if getattr(self, "additional_charge", 0):
			return

		main_service = getattr(self, "main_service", None)

		if main_service == "MICE":
			missing_fields = []
			if not _sq_strip_or_none(getattr(self, "exhibit", None)):
				missing_fields.append(_("MICE Project"))
			if not getattr(self, "exhibit_show_open_date", None):
				missing_fields.append(_("Exhibit Open Date"))
			if not getattr(self, "exhibit_show_close_date", None):
				missing_fields.append(_("Exhibit Close Date"))
			if missing_fields:
				frappe.throw(
					_("For Exhibits quotes, these fields are required: {0}.").format(", ".join(missing_fields)),
					title=_("Exhibit Details Required"),
				)

	def auto_scope_title(self):
		"""Default scope_title from corridor + incoterm when blank."""
		if (getattr(self, "scope_title", None) or "").strip():
			return
		parts = []
		origin = _sq_strip_or_none(getattr(self, "origin_port", None))
		dest = _sq_strip_or_none(getattr(self, "destination_port", None))
		if origin and dest:
			parts.append(f"{origin} → {dest}")
		inc = _sq_strip_or_none(getattr(self, "incoterm", None))
		if inc:
			parts.append(f"({inc})")
		if parts:
			self.scope_title = " ".join(parts)

	def validate_linked_service_charge_tagging(self):
		"""Validate per-charge Linked Service tagging on Sales Quote."""
		from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
		from logistics.utils.linked_service_compat import (
			CHARGE_SCOPE_LINKED,
			CHARGE_SCOPE_MAIN,
			charge_row_linked_service_link,
			linked_service_doctype,
			linked_service_rows,
			normalize_charge_scope,
			set_charge_row_linked_service_link,
		)

		charges = getattr(self, "charges", None) or []
		allowed_ls: set[str] = set()
		for ls_row in linked_service_rows(self):
			ls_name = charge_row_linked_service_link(ls_row)
			if ls_name:
				allowed_ls.add(ls_name)

		for row in charges:
			scope = normalize_charge_scope(getattr(row, "charge_scope", None))
			ls_link = charge_row_linked_service_link(row)
			if scope != CHARGE_SCOPE_LINKED:
				if ls_link:
					set_charge_row_linked_service_link(row, None)
				row.charge_scope = CHARGE_SCOPE_MAIN
				continue
			row.charge_scope = CHARGE_SCOPE_LINKED
			if not ls_link:
				frappe.throw(
					_("Charges row {0}: select a Linked Service when Scope is \"Linked\".").format(
						getattr(row, "idx", "") or "?",
					),
					title=_("Linked Service Required"),
				)
			if allowed_ls and ls_link not in allowed_ls:
				frappe.throw(
					_(
						"Charges row {0}: Linked Service {1} is not defined on this quote. "
						"Add it to the Services grid first."
					).format(
						getattr(row, "idx", "") or "?",
						frappe.bold(ls_link),
					),
					title=_("Linked Service Not Found"),
				)
			ls_service_type = frappe.db.get_value(
				linked_service_doctype(), ls_link, "service_type"
			)
			if ls_service_type and not sales_quote_charge_service_types_equal(
				getattr(row, "service_type", None), ls_service_type
			):
				frappe.throw(
					_(
						"Charges row {0}: Linked Service {1} is {2}, but this charge is {3}."
					).format(
						getattr(row, "idx", "") or "?",
						frappe.bold(ls_link),
						frappe.bold(ls_service_type),
						frappe.bold(getattr(row, "service_type", None) or "?"),
					),
					title=_("Linked Service Type Mismatch"),
				)

	def validate_internal_job_charge_tagging(self):
		"""Backward-compatible alias."""
		self.validate_linked_service_charge_tagging()

	def validate_multimodal_main_job(self):
		"""When multimodal routing legs exist, require at least one Main Job."""
		legs = getattr(self, "routing_legs", None) or []
		if not legs:
			return
		main_count = sum(1 for r in legs if getattr(r, "is_main_job", 0))
		if main_count == 0:
			frappe.throw(_("Multimodal routing requires at least one Main Job. Please check 'Main Job' on one or more legs."))

	def validate_load_type_matches_service(self):
		"""Load Type must have the checkbox for the current service mode enabled (air/sea/transport/customs/warehousing).

		A Load Type may have several mode flags set; validation only checks that the flag matching the charge's
		service_type (or one-off main_service) is enabled—not that other flags are off.
		"""
		from logistics.utils.service_mode_flags import validate_service_mode_link

		if getattr(self, "quotation_type", None) in ("One-off", "Regular") and not getattr(self, "additional_charge", 0):
			main = getattr(self, "main_service", None)
			lt = getattr(self, "load_type", None)
			if lt and main:
				validate_service_mode_link(
					"Load Type",
					lt,
					main,
					context=_("this quote's Main Service"),
				)

		for row in getattr(self, "charges", None) or []:
			st = getattr(row, "service_type", None)
			lt = getattr(row, "load_type", None)
			if lt and st:
				validate_service_mode_link(
					"Load Type",
					lt,
					st,
					context=_("charge row {0}").format(getattr(row, "idx", "") or ""),
				)

	def validate_transport_mode_matches_service(self):
		"""Transport Mode must match Main Service module flags on Regular / One-off quotes."""
		from logistics.utils.service_mode_flags import validate_service_mode_link

		if getattr(self, "quotation_type", None) not in ("One-off", "Regular"):
			return
		if getattr(self, "additional_charge", 0):
			return
		tm = getattr(self, "transport_mode", None)
		main = getattr(self, "main_service", None)
		if tm and main:
			validate_service_mode_link(
				"Transport Mode",
				tm,
				main,
				context=_("this quote's Main Service"),
			)

	def validate_freight_agent_matches_service(self):
		"""Freight Agent must have the module flag for the quote's Main Service."""
		from logistics.utils.freight_agent_service import validate_freight_agent_link

		if getattr(self, "quotation_type", None) not in ("One-off", "Regular"):
			return
		if getattr(self, "additional_charge", 0):
			return
		main = getattr(self, "main_service", None)
		if not main:
			return
		for fieldname in ("freight_agent", "freight_agent_sea"):
			agent = getattr(self, fieldname, None)
			if not agent:
				continue
			validate_freight_agent_link(
				agent,
				main,
				context=_("this quote's Main Service"),
			)

	def validate_customs_unit_types(self):
		"""Ensure customs charge rows use unit types allowed by Declaration Order / Declaration Charges.
		Prevents submission with e.g. 'Job' so that creating Declaration Order from the quote does not fail."""
		customs_rows = []
		if getattr(self, "charges", None):
			customs_rows = [r for r in self.charges if _sq_charge_row_matches_service(r, "Customs")]
		if not sales_quote_charge_service_types_equal(getattr(self, "main_service", None) or "", "Customs") or not customs_rows:
			return
		for idx, row in enumerate(customs_rows, start=1):
			unit_type = getattr(row, "unit_type", None)
			if unit_type and unit_type not in CUSTOMS_ALLOWED_UNIT_TYPES:
				frappe.throw(
					_("Row #{0} (Customs): Unit Type cannot be \"{1}\". It should be one of: {2}.").format(
						idx,
						unit_type,
						", ".join(f'"{u}"' for u in CUSTOMS_ALLOWED_UNIT_TYPES_DISPLAY),
					),
					title=_("Invalid Unit Type"),
				)
			cost_unit_type = getattr(row, "cost_unit_type", None)
			if cost_unit_type and cost_unit_type not in CUSTOMS_ALLOWED_UNIT_TYPES:
				frappe.throw(
					_("Row #{0} (Customs): Cost Unit Type cannot be \"{1}\". It should be one of: {2}.").format(
						idx,
						cost_unit_type,
						", ".join(f'"{u}"' for u in CUSTOMS_ALLOWED_UNIT_TYPES_DISPLAY),
					),
					title=_("Invalid Cost Unit Type"),
				)

	def validate_transport_template_compatibility(self):
		"""Load Type / Vehicle Type must match the selected Transport Template (#1122)."""
		from logistics.transport.doctype.transport_template.transport_template import (
			validate_doc_transport_template,
		)

		if getattr(self, "main_service", None) != "Transport":
			return
		if not getattr(self, "transport_template", None):
			return

		validate_doc_transport_template(self, context=_("Sales Quote"))

	def validate_vehicle_type_load_type(self):
		"""Validate that the selected vehicle_type is allowed for the selected load_type in each Transport charge"""
		transport_rows = [c for c in (getattr(self, "charges") or []) if _sq_charge_row_matches_service(c, "Transport")]
		if getattr(self, "main_service", None) != "Transport" or not transport_rows:
			return

		for transport_row in transport_rows:
			vehicle_type = getattr(transport_row, 'vehicle_type', None)
			load_type = getattr(transport_row, 'load_type', None)
			
			# Skip validation if either field is missing
			if not vehicle_type or not load_type:
				continue
			
			# Check if the vehicle_type has the selected load_type in its allowed_load_types
			allowed_load_types = frappe.db.get_all(
				"Vehicle Type Load Types",
				filters={"parent": vehicle_type},
				fields=["load_type"]
			)
			
			allowed_load_type_names = [alt.load_type for alt in allowed_load_types]
			
			if load_type not in allowed_load_type_names:
				frappe.throw(
					_("Vehicle Type '{0}' is not allowed for Load Type '{1}' in row {2}. Please select a Vehicle Type that allows this Load Type.").format(
						vehicle_type, load_type, transport_row.idx
					),
					title=_("Invalid Vehicle Type")
				)
	
	def validate_vehicle_type_capacity(self):
		"""Validate vehicle type capacity when vehicle_type is assigned. Uses Transport charges."""
		if getattr(self, "main_service", None) != "Transport":
			return

		transport_rows = [c for c in (getattr(self, "charges") or []) if _sq_charge_row_matches_service(c, "Transport")]
		has_vehicle_type = any(getattr(r, "vehicle_type", None) for r in transport_rows)
		if not has_vehicle_type:
			return

		try:
			from logistics.transport.capacity.vehicle_type_capacity import get_vehicle_type_capacity_info
			from logistics.transport.capacity.uom_conversion import convert_weight, convert_volume, get_default_uoms
			from logistics.utils.default_uom import get_default_uoms_for_domain

			required_weight = flt(getattr(self, "transport_weight", None) or getattr(self, "weight", 0))
			required_weight_uom = getattr(self, "transport_weight_uom", None) or getattr(self, "weight_uom", None)
			required_volume = flt(getattr(self, "transport_volume", None) or getattr(self, "volume", 0))
			required_volume_uom = getattr(self, "transport_volume_uom", None) or getattr(self, "volume_uom", None)
			if not required_weight_uom or not required_volume_uom:
				defaults = get_default_uoms_for_domain("transport")
				required_weight_uom = required_weight_uom or defaults.get("weight_uom")
				required_volume_uom = required_volume_uom or defaults.get("volume_uom")
			default_uoms = get_default_uoms(self.company)
			required_weight_uom = required_weight_uom or default_uoms.get("weight")
			required_volume_uom = required_volume_uom or default_uoms.get("volume")

			if required_weight == 0 and required_volume == 0:
				return

			required_weight_std = convert_weight(required_weight, required_weight_uom, default_uoms["weight"], self.company)
			required_volume_std = convert_volume(required_volume, required_volume_uom, default_uoms["volume"], self.company)

			for transport_row in transport_rows:
				vehicle_type = getattr(transport_row, 'vehicle_type', None)
				if not vehicle_type:
					continue
				
				# Get vehicle type capacity (average or minimum from vehicles of this type)
				capacity_info = get_vehicle_type_capacity_info(vehicle_type, self.company)

				# Check if capacity is sufficient (compare in standard UOMs)
				if required_weight_std > 0 and capacity_info.get('max_weight', 0) < required_weight_std:
					frappe.msgprint(_("Warning: Required weight ({0} {1}) may exceed typical capacity for vehicle type {2} in row {3}").format(
						required_weight, required_weight_uom, vehicle_type, transport_row.idx
					), indicator='orange')

				if required_volume_std > 0 and capacity_info.get('max_volume', 0) < required_volume_std:
					frappe.msgprint(_("Warning: Required volume ({0} {1}) may exceed typical capacity for vehicle type {2} in row {3}").format(
						required_volume, required_volume_uom, vehicle_type, transport_row.idx
					), indicator='orange')
		except ImportError:
			# Capacity management not fully implemented yet
			pass
		except Exception as e:
			frappe.log_error(f"Error validating vehicle type capacity in Sales Quote: {str(e)}", "Capacity Validation Error")
	
	def _determine_transport_job_type(self, current_job_type, load_type, container_type):
		from logistics.utils.transport_job_type import determine_transport_job_type

		return determine_transport_job_type(current_job_type, load_type, container_type)
	
	@frappe.whitelist()
	def create_air_shipment_from_sales_quote(self):
		"""
		Create an Air Shipment from a Sales Quote when the quote is tagged as One-Off.
		
		Returns:
			dict: Result with created Air Shipment name and status
		"""
		try:
			throw_if_sales_quote_expired_for_creation(self)
			throw_if_additional_charge_sales_quote_blocks_booking_order_creation(self)
			# Check if Sales Quote has air charges (new) or air freight (legacy)
			air_charge_count = count_sales_quote_charges_for_service(self.name, "Air")
			air_freight_count = frappe.db.count("Sales Quote Air Freight", {
				"parent": self.name,
				"parenttype": "Sales Quote"
			}) if frappe.db.table_exists("Sales Quote Air Freight") else 0
			if air_charge_count == 0 and air_freight_count == 0:
				frappe.throw(_("No Air Freight lines found in this Sales Quote."))
			
			# Get port fields from Air tab (preferred) or fall back to Transport tab
			origin_airport = getattr(self, 'origin_port', None)
			destination_airport = getattr(self, 'destination_port', None)
			
			# Fall back to Transport tab location fields if Air tab fields are not set
			if not origin_airport:
				origin_airport = getattr(self, 'location_from', None)
			if not destination_airport:
				destination_airport = getattr(self, 'location_to', None)
			
			# Clean up airport fields: strip whitespace and convert empty strings to None
			if origin_airport:
				origin_airport = str(origin_airport).strip() or None
			if destination_airport:
				destination_airport = str(destination_airport).strip() or None
			
			# Check if origin and destination ports are set (required for Air Shipment)
			missing_fields = []
			if not origin_airport:
				missing_fields.append("Origin Port")
			if not destination_airport:
				missing_fields.append("Destination Port")
			
			if missing_fields:
				error_msg = _("Cannot create Air Shipment: {0} {1} required in Sales Quote.").format(
					", ".join(missing_fields),
					"is" if len(missing_fields) == 1 else "are"
				)
				instructions = _(
					"To fix this:\n"
					"1. Go to the 'Air' tab in this Sales Quote\n"
					"2. In the 'Routing & Dates' section, fill in:\n"
					"   - 'Origin Port' - select a valid Location for the origin port\n"
					"   - 'Destination Port' - select a valid Location for the destination port\n"
					"3. Save the Sales Quote\n"
					"4. Then try creating the Air Shipment again\n\n"
					"Note: You can also use 'Location From' and 'Location To' in the Transport tab as an alternative."
				)
				frappe.throw(
					f"{error_msg}\n\n{instructions}",
					title=_("Required Fields Missing")
				)
			
			# Verify that origin_airport and destination_airport are valid Location/UNLOCO records
			# Air Shipment requires UNLOCO records
			if not frappe.db.exists("UNLOCO", origin_airport):
				if not frappe.db.exists("Location", origin_airport):
					frappe.throw(_("Origin Airport '{0}' is not a valid UNLOCO or Location. Please select a valid Location record in the Air tab.").format(origin_airport))
			
			if not frappe.db.exists("UNLOCO", destination_airport):
				if not frappe.db.exists("Location", destination_airport):
					frappe.throw(_("Destination Airport '{0}' is not a valid UNLOCO or Location. Please select a valid Location record in the Air tab.").format(destination_airport))
			
			# Allow creation of multiple Air Shipments from the same Sales Quote
			# No duplicate prevention - users can create multiple shipments as needed
			
			# Create new Air Shipment
			air_shipment = frappe.new_doc("Air Shipment")
			
			# Map basic fields from Sales Quote to Air Shipment
			air_shipment.local_customer = self.customer
			air_shipment.booking_date = today()
			air_shipment.sales_quote = self.name
			air_shipment.shipper = getattr(self, 'shipper', None)
			air_shipment.consignee = getattr(self, 'consignee', None)
			air_shipment.origin_port = origin_airport
			air_shipment.destination_port = destination_airport
			air_shipment.direction = getattr(self, 'direction', None)
			# Use Air tab dimensions (fallback to old top-level for backward compat)
			weight = getattr(self, 'air_weight', None) or getattr(self, 'weight', None)
			air_shipment.total_weight = weight if weight and flt(weight) > 0 else None
			volume = getattr(self, 'air_volume', None) or getattr(self, 'volume', None)
			air_shipment.total_volume = volume if volume and flt(volume) > 0 else None
			chargeable = getattr(self, 'air_chargeable', None) or getattr(self, 'chargeable', None)
			air_shipment.chargeable = chargeable if chargeable and flt(chargeable) > 0 else None
			air_shipment.service_level = getattr(self, 'service_level', None)
			air_shipment.incoterm = getattr(self, 'incoterm', None)
			air_shipment.additional_terms = getattr(self, 'additional_terms', None)
			air_shipment.company = self.company
			air_shipment.branch = self.branch
			air_shipment.cost_center = self.cost_center
			air_shipment.profit_center = self.profit_center
			apply_main_service_flags(air_shipment)
			air_shipment.is_high_value = cint(getattr(self, "is_high_value", 0))
			copy_sales_quote_fields_to_target(self, air_shipment)
			apply_party_address_contact_from_source_or_masters(air_shipment, self)

			# Insert the Air Shipment
			air_shipment.insert(ignore_permissions=True)
			
			# Populate charges from Sales Quote Air Freight
			_populate_charges_from_sales_quote_air_freight(air_shipment, self)

			# Save the Air Shipment
			air_shipment.save(ignore_permissions=True)
			
			# Ensure commit before client navigates (avoids "not found" on form load)
			frappe.db.commit()
			
			# Prepare success message
			success_msg = f"Air Shipment {air_shipment.name} created successfully from Sales Quote {self.name}"
			
			frappe.msgprint(
				success_msg,
				title="Air Shipment Created",
				indicator="green"
			)
			
			return {
				"success": True,
				"message": f"Air Shipment {air_shipment.name} created successfully.",
				"air_shipment": air_shipment.name
			}
			
		except Exception as e:
			frappe.log_error(f"Error creating Air Shipment: {str(e)}", "Sales Quote - Create Air Shipment")
			frappe.throw(f"Error creating Air Shipment: {str(e)}")

	@frappe.whitelist()
	def create_sea_shipment_from_sales_quote(self):
		"""
		Create a Sea Booking from Sales Quote, then convert it to Sea Shipment.
		Shipments can only be created by converting a Sea Booking.
		
		Returns:
			dict: Result with created Sea Shipment name and status
		"""
		try:
			throw_if_sales_quote_expired_for_creation(self)
			throw_if_additional_charge_sales_quote_blocks_booking_order_creation(self)
			# First create the Sea Booking from Sales Quote
			booking_result = _create_sea_booking_from_sales_quote(self)
			booking_name = booking_result.get("sea_booking")
			
			if not booking_name:
				frappe.throw(_("Failed to create Sea Booking from Sales Quote"))
			
			# Get the booking and convert it to shipment
			booking = frappe.get_doc("Sea Booking", booking_name)
			shipment_result = booking.convert_to_shipment()
			
			return shipment_result
			
		except Exception as e:
			frappe.log_error(f"Error creating Sea Shipment: {str(e)}", "Sales Quote - Create Sea Shipment")
			frappe.throw(f"Error creating Sea Shipment: {str(e)}")

	@frappe.whitelist()
	def create_warehouse_contract_from_sales_quote(self):
		"""
		Create a Warehouse Contract from a Sales Quote when the quote is submitted and has warehousing items.
		
		Returns:
			dict: Result with created Warehouse Contract name and status
		"""
		try:
			# Check if the quote is submitted
			if self.docstatus != 1:
				frappe.throw(_("This Sales Quote must be submitted before creating a Warehouse Contract."))
			throw_if_additional_charge_sales_quote_blocks_booking_order_creation(self)

			# Check if Sales Quote has warehousing details (legacy table or unified Warehousing charges)
			if not _sales_quote_has_warehousing_for_contract(self):
				frappe.throw(_("No warehousing details found in this Sales Quote."))
			
			# Create new Warehouse Contract
			warehouse_contract = frappe.new_doc("Warehouse Contract")
			
			# Map basic fields from Sales Quote to Warehouse Contract
			warehouse_contract.customer = self.customer
			warehouse_contract.date = today()
			warehouse_contract.valid_until = self.valid_until
			warehouse_contract.site = self.site
			warehouse_contract.sales_quote = self.name
			warehouse_contract.company = self.company
			warehouse_contract.branch = self.branch
			warehouse_contract.profit_center = self.profit_center
			warehouse_contract.cost_center = self.cost_center
			warehouse_contract.is_high_value = cint(getattr(self, "is_high_value", 0))

			# Insert the Warehouse Contract
			warehouse_contract.insert(ignore_permissions=True)

			record_one_off_quote_conversion(self.name, "Warehouse Contract", warehouse_contract.name)
			
			# Import rates from Sales Quote using the existing function
			from logistics.warehousing.doctype.warehouse_contract.warehouse_contract import get_rates_from_sales_quote
			get_rates_from_sales_quote(warehouse_contract.name, self.name)
			
			# Ensure commit before client navigates (avoids "not found" on form load)
			frappe.db.commit()
			
			# Prepare success message
			success_msg = f"Warehouse Contract {warehouse_contract.name} created successfully from Sales Quote {self.name}"
			
			frappe.msgprint(
				success_msg,
				title="Warehouse Contract Created",
				indicator="green"
			)
			
			return {
				"success": True,
				"message": f"Warehouse Contract {warehouse_contract.name} created successfully.",
				"warehouse_contract": warehouse_contract.name
			}
			
		except Exception as e:
			frappe.log_error(
				f"Error creating Warehouse Contract from Sales Quote {self.name}: {str(e)}",
				"Sales Quote to Warehouse Contract Creation Error"
			)
			frappe.throw(f"Error creating Warehouse Contract: {str(e)}")

	@frappe.whitelist()
	def create_special_project_from_sales_quote(self):
		"""Create or update a Special Project from this Sales Quote and copy programme charges."""
		return _create_special_project_from_sales_quote(self)

	def _map_sales_quote_entry_type_to_air_booking(self, sales_quote_entry_type):
		"""Wrapper method that calls the module-level mapping function"""
		return map_sales_quote_entry_type_to_air_booking(sales_quote_entry_type)


def _create_special_project_from_sales_quote(sales_quote):
	if sales_quote.docstatus != 1:
		frappe.throw(_("This Sales Quote must be submitted before creating a Special Project."))
	throw_if_sales_quote_expired_for_creation(sales_quote)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote)

	if not _sales_quote_has_special_project_content(sales_quote):
		frappe.throw(
			_(
				"Add at least one charge line with Service Type \"Special Project\" "
				"or at least one row on the Special Project tab Resources table."
			)
		)

	sp_name = get_special_project_for_sales_quote(sales_quote.name)
	if sp_name:
		sp = frappe.get_doc("Special Project", sp_name)
	else:
		validate_erpnext_project_name_available_for_sales_quote(sales_quote)
		sp = frappe.new_doc("Special Project")
		sp.customer = sales_quote.customer
		sp.sales_quote = sales_quote.name
		_copy_sales_quote_special_project_details(sales_quote, sp)
		if not _sq_strip_or_none(getattr(sp, "project_name", None)):
			sp.project_name = resolve_erpnext_project_name_for_sales_quote(sales_quote)
		sp.insert(ignore_permissions=True)

	if not sp.sales_quote:
		sp.sales_quote = sales_quote.name
	if not sp.customer:
		sp.customer = sales_quote.customer
	sp.company = sales_quote.company or sp.company
	sp.branch = sales_quote.branch or sp.branch
	sp.cost_center = sales_quote.cost_center or sp.cost_center
	sp.profit_center = sales_quote.profit_center or sp.profit_center
	sp.sales_rep = sales_quote.sales_rep or sp.sales_rep
	sp.operations_rep = sales_quote.operations_rep or sp.operations_rep
	sp.customer_service_rep = sales_quote.customer_service_rep or sp.customer_service_rep
	copy_sales_quote_fields_to_target(sales_quote, sp)
	_copy_sales_quote_special_project_details(sales_quote, sp)
	if not _sq_strip_or_none(getattr(sp, "project_name", None)):
		sp.project_name = resolve_erpnext_project_name_for_sales_quote(sales_quote)
	from logistics.utils.sales_quote_programme_charges import (
		copy_sales_quote_charge_breaks_to_programme_parent,
	)

	from logistics.special_projects.special_project_services_from_sales_quote import (
		copy_special_project_programme_data_from_sales_quote,
	)

	copy_special_project_programme_data_from_sales_quote(
		sp, sales_quote.name, clear_existing=True
	)
	from logistics.special_projects.special_project_packages import (
		seed_packages_from_sales_quote,
	)

	seed_packages_from_sales_quote(sp, sales_quote, clear_existing=False)
	sp.flags.ignore_links = True
	sp.save(ignore_permissions=True)
	copy_sales_quote_charge_breaks_to_programme_parent(sp, sales_quote.name)
	frappe.db.commit()

	frappe.msgprint(
		_("Special Project {0} updated from Sales Quote {1}.").format(sp.name, sales_quote.name),
		title=_("Special Project"),
		indicator="green",
	)
	return {"success": True, "special_project": sp.name, "message": sp.name}


def _is_project_exhibits_programme_quote(sales_quote) -> bool:
	"""Project (PQ) programme quotes get one Docket per Sales Quote, named after the quote."""
	return (
		getattr(sales_quote, "quotation_type", None) == "Project"
		and getattr(sales_quote, "main_service", None) == "MICE"
	)


@frappe.whitelist()
def create_special_project_from_sales_quote(sales_quote_name):
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_special_project_from_sales_quote(sales_quote)


def _propagate_linked_services_to_docket(sales_quote, docket_doc):
	"""Clone quote-owned Linked Services onto *docket_doc* and remap charge links."""
	if not sales_quote or not docket_doc:
		return
	from logistics.utils.sales_quote_one_off_internal_jobs import (
		propagate_linked_services_from_sales_quote_to_booking,
	)

	try:
		propagate_linked_services_from_sales_quote_to_booking(
			sales_quote,
			docket_doc,
			exclude_main_booking_service_type=False,
		)
	except Exception:
		frappe.log_error(
			title="Sales Quote Linked Service propagation to Docket failed",
			message=(
				f"Sales Quote: {getattr(sales_quote, 'name', None)}; "
				f"Docket: {getattr(docket_doc, 'name', None)}\n{frappe.get_traceback()}"
			),
		)


def _heal_linked_services_on_existing_docket(sales_quote, docket_name: str) -> None:
	"""Clone quote Linked Services onto an existing Docket when it has none yet."""
	if not sales_quote or not docket_name or not frappe.db.exists("Docket", docket_name):
		return
	from logistics.utils.internal_job_persistence import _linked_service_names_from_db

	if _linked_service_names_from_db("Docket", docket_name):
		return
	docket_doc = frappe.get_doc("Docket", docket_name)
	_propagate_linked_services_to_docket(sales_quote, docket_doc)


def _create_docket_from_sales_quote(sales_quote, booth_no=None):
	"""Create (or return) the Docket for ``sales_quote.customer`` on the linked Exhibit.

	The Sales Quote's customer is treated as the exhibitor (booth holder). The
	Exhibit's Dockets table is now a virtual view of existing Dockets, so we no
	longer seed a participant row up front — the Docket itself is the only
	source of truth for which exhibitors belong to an Exhibit.
	"""
	if sales_quote.docstatus != 1:
		frappe.throw(_("This Sales Quote must be submitted before creating a Docket."))
	throw_if_sales_quote_expired_for_creation(sales_quote)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote)

	if sales_quote.main_service != "MICE":
		frappe.throw(_("Main Service must be Exhibits to create a Docket."))

	exhibit_name = _sq_strip_or_none(getattr(sales_quote, "exhibit", None))
	if not exhibit_name:
		frappe.throw(
			_("Link an Exhibit on this Sales Quote before creating a Docket.")
		)
	if not frappe.db.exists("MICE Project", exhibit_name):
		frappe.throw(_("Exhibit {0} does not exist.").format(frappe.bold(exhibit_name)))

	exhibitor = _sq_strip_or_none(getattr(sales_quote, "customer", None))
	if not exhibitor:
		frappe.throw(_("Sales Quote must have a Customer to create a Docket."))

	ep = frappe.get_doc("MICE Project", exhibit_name)

	project_exhibits_quote = _is_project_exhibits_programme_quote(sales_quote)
	docket_name = sales_quote.name if project_exhibits_quote else None

	if docket_name and frappe.db.exists("Docket", docket_name):
		from logistics.utils.sales_quote_programme_charges import (
			copy_sales_quote_charge_breaks_to_programme_parent,
			populate_programme_charges_from_sales_quote,
		)

		doc = frappe.get_doc("Docket", docket_name)
		if not _sq_strip_or_none(getattr(doc, "sales_quote", None)):
			doc.sales_quote = sales_quote.name
		populate_programme_charges_from_sales_quote(
			doc, sales_quote.name, clear_existing=True, service_types="__all__"
		)
		doc.save(ignore_permissions=True)
		copy_sales_quote_charge_breaks_to_programme_parent(doc, sales_quote.name)
		_propagate_linked_services_to_docket(sales_quote, doc)
		frappe.db.commit()
		return {"success": True, "docket": docket_name, "message": docket_name}

	if not project_exhibits_quote:
		existing_docket = frappe.db.get_value(
			"Docket",
			{"exhibit": ep.name, "exhibitor": exhibitor, "docstatus": ["<", 2]},
			"name",
		)
		if existing_docket:
			_heal_linked_services_on_existing_docket(sales_quote, existing_docket)
			return {"success": True, "docket": existing_docket, "message": existing_docket}

		predicted_name = f"{ep.name}-{exhibitor}"
		if frappe.db.exists("Docket", predicted_name):
			_heal_linked_services_on_existing_docket(sales_quote, predicted_name)
			return {"success": True, "docket": predicted_name, "message": predicted_name}

	doc = frappe.new_doc("Docket")
	doc.exhibit = ep.name
	doc.exhibitor = exhibitor
	doc.sales_quote = sales_quote.name
	booth_no = _sq_strip_or_none(booth_no)
	if booth_no:
		doc.booth_no = booth_no
	doc.company = sales_quote.company or doc.company
	doc.branch = sales_quote.branch or doc.branch
	doc.cost_center = sales_quote.cost_center or doc.cost_center
	doc.profit_center = sales_quote.profit_center or doc.profit_center
	doc.sales_rep = sales_quote.sales_rep or doc.sales_rep
	doc.operations_rep = sales_quote.operations_rep or doc.operations_rep
	doc.customer_service_rep = sales_quote.customer_service_rep or doc.customer_service_rep
	copy_sales_quote_fields_to_target(sales_quote, doc)
	from logistics.utils.sales_quote_programme_charges import (
		copy_sales_quote_charge_breaks_to_programme_parent,
		populate_programme_charges_from_sales_quote,
	)

	populate_programme_charges_from_sales_quote(
		doc, sales_quote.name, clear_existing=True, service_types="__all__"
	)
	insert_kwargs = {"ignore_permissions": True}
	if docket_name:
		insert_kwargs["set_name"] = docket_name
	doc.insert(**insert_kwargs)
	copy_sales_quote_charge_breaks_to_programme_parent(doc, sales_quote.name)
	_propagate_linked_services_to_docket(sales_quote, doc)
	frappe.db.commit()

	frappe.msgprint(
		_("Docket {0} created from Sales Quote {1}.").format(doc.name, sales_quote.name),
		title=_("Docket"),
		indicator="green",
	)
	return {"success": True, "docket": doc.name, "message": doc.name}


@frappe.whitelist()
def create_docket_from_sales_quote(sales_quote_name, booth_no=None):
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_docket_from_sales_quote(sales_quote, booth_no=booth_no)


@frappe.whitelist()
def create_transport_order_from_sales_quote(sales_quote_name):
	"""
	Create a Transport Order from Sales Quote. Populates job_no on matching routing leg if multimodal.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_transport_order_from_sales_quote(sales_quote)


@frappe.whitelist()
def create_air_booking_from_sales_quote(sales_quote_name):
	"""
	Create an Air Booking from Sales Quote. Populates job_no on matching routing leg if multimodal.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_air_booking_from_sales_quote(sales_quote)


@frappe.whitelist()
def create_sea_booking_from_sales_quote(sales_quote_name):
	"""
	Create a Sea Booking from Sales Quote. Populates job_no on matching routing leg if multimodal.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_sea_booking_from_sales_quote(sales_quote)


@frappe.whitelist()
def create_air_shipment_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Air Shipment from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_air_shipment_from_sales_quote()


@frappe.whitelist()
def create_sea_shipment_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Sea Shipment from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_sea_shipment_from_sales_quote()


@frappe.whitelist()
def create_warehouse_contract_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Warehouse Contract from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_warehouse_contract_from_sales_quote()


@frappe.whitelist()
def create_sales_invoice_from_sales_quote(sales_quote_name, posting_date=None):
	"""
	Create Sales Invoice from multimodal Sales Quote.
	Uses Main Job for billing; aggregates or splits per billing_mode.
	- Consolidated: One invoice with charges from Main Job + all Sub-Jobs.
	- Per Product: Separate invoice per routing leg that has a job.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_sales_invoice_from_multimodal_quote(sales_quote, posting_date)


def _create_sales_invoice_from_multimodal_quote(sales_quote, posting_date=None):
	"""Create Sales Invoice from multimodal Sales Quote using Main Job and billing_mode."""
	legs = getattr(sales_quote, "routing_legs", None) or []
	if not legs:
		frappe.throw(_("No routing legs found. Add routing legs and designate one as Main Job."))

	main_job_type, main_job_no = _resolve_main_job_for_sales_quote(sales_quote)
	if not main_job_type or not main_job_no:
		frappe.throw(_("Main Job not found. Create the main-service booking or order from this quote first."))

	billing_mode = getattr(sales_quote, "billing_mode", None) or "Consolidated"
	posting_date = posting_date or today()

	if billing_mode == "Per Product":
		return _create_separate_invoices_per_leg(sales_quote, legs, posting_date)
	else:
		main_leg = next((r for r in legs if getattr(r, "is_main_job", 0)), None) or legs[0]
		return _create_consolidated_invoice(sales_quote, legs, main_leg, main_job_type, main_job_no, posting_date)


def _get_contributors_for_leg(leg):
	"""Return list of (contributor_job_type, contributor_job_no) for this routing leg (cross-module billing)."""
	contributors = []
	# Nested child table: load from DB if not on leg
	contrib_list = getattr(leg, "bill_with_contributors", None)
	if contrib_list:
		for c in contrib_list:
			ct = getattr(c, "contributor_job_type", None)
			cn = getattr(c, "contributor_job_no", None)
			if ct and cn:
				contributors.append((ct, cn))
	else:
		leg_name = getattr(leg, "name", None)
		if leg_name and frappe.db.exists("Sales Quote Routing Leg Contributor", {"parent": leg_name, "parenttype": "Sales Quote Routing Leg"}):
			for c in frappe.get_all(
				"Sales Quote Routing Leg Contributor",
				filters={"parent": leg_name, "parenttype": "Sales Quote Routing Leg"},
				fields=["contributor_job_type", "contributor_job_no"],
			):
				if c.get("contributor_job_type") and c.get("contributor_job_no"):
					contributors.append((c["contributor_job_type"], c["contributor_job_no"]))
	return contributors


_SALES_QUOTE_LINKED_OPERATIONAL_DOCTYPES = (
	"Declaration Order",
	"Air Booking",
	"Sea Booking",
	"Transport Order",
	"Inbound Order",
	"Warehouse Job",
	"Declaration",
)

_MAIN_SERVICE_PRIMARY_DOCTYPE = {
	"Air": "Air Booking",
	"Sea": "Sea Booking",
	"Transport": "Transport Order",
	"Customs": "Declaration Order",
	"Warehousing": "Inbound Order",
}


def _resolve_main_job_for_sales_quote(sales_quote):
	"""Return (doctype, name) for the quote's main-service operational document."""
	sq_name = sales_quote.name if hasattr(sales_quote, "name") else sales_quote
	main_service = (getattr(sales_quote, "main_service", None) or "").strip()
	primary = _MAIN_SERVICE_PRIMARY_DOCTYPE.get(main_service)
	if primary and frappe.db.has_column(primary, "sales_quote"):
		names = frappe.get_all(
			primary,
			filters={"sales_quote": sq_name, "service_role": "Main", "docstatus": ["!=", 2]},
			pluck="name",
			limit=1,
		)
		if names:
			return primary, names[0]
	for dt in _SALES_QUOTE_LINKED_OPERATIONAL_DOCTYPES:
		if not frappe.db.has_column(dt, "sales_quote"):
			continue
		if not frappe.get_meta(dt).has_field("service_role"):
			continue
		names = frappe.get_all(
			dt,
			filters={"sales_quote": sq_name, "service_role": "Main", "docstatus": ["!=", 2]},
			pluck="name",
			limit=1,
		)
		if names:
			return dt, names[0]
	return None, None


def _iter_linked_jobs_for_sales_quote(sales_quote):
	"""Yield (doctype, name) for operational documents linked to this Sales Quote."""
	sq_name = sales_quote.name if hasattr(sales_quote, "name") else sales_quote
	seen = set()
	for dt in _SALES_QUOTE_LINKED_OPERATIONAL_DOCTYPES:
		if not frappe.db.has_column(dt, "sales_quote"):
			continue
		for name in frappe.get_all(
			dt,
			filters={"sales_quote": sq_name, "docstatus": ["!=", 2]},
			pluck="name",
			order_by="creation asc",
		):
			key = (dt, name)
			if key not in seen:
				seen.add(key)
				yield dt, name


def _resolve_job_for_routing_leg(sales_quote, leg):
	"""Best-effort anchor job for a routing leg via ``sales_quote`` linkage."""
	from logistics.utils.transport_mode_flags import get_air_sea_flags_for_transport_mode

	sq_name = sales_quote.name
	mode = (getattr(leg, "mode", None) or "").strip()
	air_flag, sea_flag = get_air_sea_flags_for_transport_mode(mode)
	candidates = []
	if air_flag:
		candidates.extend(["Air Booking", "Air Shipment"])
	if sea_flag:
		candidates.extend(["Sea Booking", "Sea Shipment"])
	if not air_flag and not sea_flag:
		candidates.extend(["Transport Order", "Transport Job"])
	if not candidates:
		candidates = list(_SALES_QUOTE_LINKED_OPERATIONAL_DOCTYPES)

	for dt in candidates:
		if not frappe.db.has_column(dt, "sales_quote"):
			continue
		filters = {"sales_quote": sq_name, "docstatus": ["!=", 2]}
		meta = frappe.get_meta(dt)
		if meta.has_field("service_role"):
			main_names = frappe.get_all(
				dt,
				filters={**filters, "service_role": "Main"},
				pluck="name",
				limit=1,
			)
			if main_names:
				return dt, main_names[0]
		names = frappe.get_all(dt, filters=filters, pluck="name", limit=1)
		if names:
			return dt, names[0]
	return None, None


def _create_consolidated_invoice(sales_quote, legs, main_leg, main_job_type, main_job_no, posting_date):
	"""Create one Sales Invoice aggregating charges from Main Job + all Sub-Jobs (anchor + contributors per leg)."""
	from logistics.billing.cross_module_billing import get_billing_set_items

	# Get header from Main Job
	main_doc = frappe.get_doc(main_job_type, main_job_no)
	customer = getattr(main_doc, "customer", None) or getattr(main_doc, "local_customer", None) or sales_quote.customer
	company = getattr(main_doc, "company", None) or sales_quote.company
	if not customer or not company:
		frappe.throw(_("Customer and Company are required. Set them on the Main Job or Sales Quote."))

	# Collect invoice items from all linked jobs: each leg anchor + contributors (billing set)
	all_items = []
	processed_jobs = set()
	for leg in legs:
		job_type, job_no = _resolve_job_for_routing_leg(sales_quote, leg)
		if not job_type or not job_no:
			continue
		job_key = (job_type, job_no)
		if job_key in processed_jobs:
			continue
		processed_jobs.add(job_key)
		contributors = _get_contributors_for_leg(leg)
		leg_prefix = _("Leg {0}").format(getattr(leg, "idx", ""))
		items = get_billing_set_items(job_type, job_no, contributors, customer=customer, description_prefix=leg_prefix)
		for item in items:
			if not item.get("description"):
				item["description"] = f"{job_type} {job_no} ({leg_prefix})"
			all_items.append(item)

	# Include any linked jobs not matched to a routing leg
	for job_type, job_no in _iter_linked_jobs_for_sales_quote(sales_quote):
		job_key = (job_type, job_no)
		if job_key in processed_jobs:
			continue
		processed_jobs.add(job_key)
		items = get_billing_set_items(job_type, job_no, [], customer=customer)
		for item in items:
			if not item.get("description"):
				item["description"] = f"{job_type} {job_no}"
			all_items.append(item)

	if not all_items:
		frappe.throw(_("No charges found in any linked job. Add charges to the jobs before creating the invoice."))

	# Create Sales Invoice
	si = frappe.new_doc("Sales Invoice")
	si.customer = customer
	si.company = company
	si.posting_date = posting_date
	si.quotation_no = sales_quote.name
	if getattr(main_doc, "branch", None):
		si.branch = main_doc.branch
	elif sales_quote.branch:
		si.branch = sales_quote.branch
	if getattr(main_doc, "cost_center", None):
		si.cost_center = main_doc.cost_center
	elif sales_quote.cost_center:
		si.cost_center = sales_quote.cost_center
	if getattr(main_doc, "profit_center", None):
		si.profit_center = main_doc.profit_center
	elif sales_quote.profit_center:
		si.profit_center = sales_quote.profit_center
	if getattr(main_doc, "job_number", None):
		si.job_number = main_doc.job_number

	base_remarks = _("Auto-created from Sales Quote {0} (Consolidated - Main Job: {1})").format(sales_quote.name, main_job_no)
	si.remarks = base_remarks

	for item in all_items:
		si.append("items", {
			"item_code": item.get("item_code"),
			"item_name": item.get("item_name"),
			"qty": flt(item.get("qty"), 2) or 1,
			"rate": flt(item.get("rate"), 2),
			"uom": item.get("uom"),
			"description": item.get("description"),
		})

	si.set_missing_values()
	si.insert(ignore_permissions=True)

	return {"success": True, "sales_invoice": si.name, "message": _("Sales Invoice {0} created (Consolidated).").format(si.name)}


def _create_separate_invoices_per_leg(sales_quote, legs, posting_date):
	"""Create separate Sales Invoice per routing leg (billing set = anchor + contributors)."""
	from logistics.billing.cross_module_billing import get_billing_set_items

	invoices_created = []
	processed_jobs = set()
	for leg in legs:
		job_type, job_no = _resolve_job_for_routing_leg(sales_quote, leg)
		if not job_type or not job_no:
			continue
		job_key = (job_type, job_no)
		if job_key in processed_jobs:
			continue
		processed_jobs.add(job_key)
		try:
			contributors = _get_contributors_for_leg(leg)
			anchor_doc = frappe.get_doc(job_type, job_no)
			customer = getattr(anchor_doc, "customer", None) or getattr(anchor_doc, "local_customer", None) or sales_quote.customer
			company = getattr(anchor_doc, "company", None) or sales_quote.company
			if not customer or not company:
				frappe.msgprint(_("Skipping leg {0}: missing customer/company on {1} {2}.").format(getattr(leg, "idx", ""), job_type, job_no), indicator="orange")
				continue
			items = get_billing_set_items(job_type, job_no, contributors, customer=customer)
			if not items:
				frappe.msgprint(_("No charges for leg {0} ({1} {2}). Add charges or contributors.").format(getattr(leg, "idx", ""), job_type, job_no), indicator="orange")
				continue
			si = _create_sales_invoice_from_items(
				items=items,
				customer=customer,
				company=company,
				posting_date=posting_date,
				sales_quote_name=sales_quote.name,
				anchor_doc=anchor_doc,
				sales_quote=sales_quote,
				remarks_suffix=_("Per Product - {0} {1}").format(job_type, job_no),
			)
			if si:
				invoices_created.append(si.name)
		except Exception as e:
			frappe.log_error(str(e), "Multimodal Per-Product Invoice")
			frappe.msgprint(_("Could not create invoice for {0} {1}: {2}").format(job_type, job_no, str(e)), indicator="orange")

	if not invoices_created:
		frappe.throw(_("No invoices could be created. Ensure jobs have charges and are in a billable state."))

	return {"success": True, "sales_invoices": invoices_created, "message": _("Created {0} Sales Invoice(s).").format(len(invoices_created))}


def _create_sales_invoice_from_items(
	items,
	customer,
	company,
	posting_date,
	sales_quote_name,
	anchor_doc,
	sales_quote,
	remarks_suffix,
):
	"""Create one Sales Invoice from item list and header from anchor_doc/sales_quote. Returns the SI doc."""
	si = frappe.new_doc("Sales Invoice")
	si.customer = customer
	si.company = company
	si.posting_date = posting_date
	si.quotation_no = sales_quote_name
	si.branch = getattr(anchor_doc, "branch", None) or sales_quote.branch
	si.cost_center = getattr(anchor_doc, "cost_center", None) or sales_quote.cost_center
	si.profit_center = getattr(anchor_doc, "profit_center", None) or sales_quote.profit_center
	si.job_number = getattr(anchor_doc, "job_number", None)
	si.remarks = _("Auto-created from Sales Quote {0} ({1})").format(sales_quote_name, remarks_suffix)
	for item in items:
		si.append("items", {
			"item_code": item.get("item_code"),
			"item_name": item.get("item_name"),
			"qty": flt(item.get("qty"), 2) or 1,
			"rate": flt(item.get("rate"), 2),
			"uom": item.get("uom"),
			"description": item.get("description"),
		})
	si.set_missing_values()
	si.insert(ignore_permissions=True)
	return si


def _get_invoice_items_from_job(job_type, job_name, customer):
	"""Extract Sales Invoice items from a job/shipment (unified API). Returns list of item dicts."""
	from logistics.billing.cross_module_billing import get_invoice_items_from_job as billing_get_items
	return billing_get_items(job_type, job_name, customer=customer)


def _get_service_params(sales_quote, service_type):
	"""Get params from first charge with the given service_type."""
	charges = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, service_type)]
	return charges[0] if charges else None


def _first_charge_for_call_off(sales_quote, service_label, selected_charge_row_names=None, legacy_fallback=None):
	"""Prefer first selected charge row for blanket call-off param resolution."""
	if selected_charge_row_names:
		by_name = {c.name: c for c in (getattr(sales_quote, "charges") or [])}
		for nm in selected_charge_row_names:
			row = by_name.get(nm)
			if row and _sq_charge_row_matches_service(row, service_label):
				return row
	return _get_service_params(sales_quote, service_label) or legacy_fallback


def _apply_parent_overrides_to_doc(doc, parent_overrides: dict | None):
	if not parent_overrides:
		return
	for key, val in parent_overrides.items():
		if val is None:
			continue
		if isinstance(val, str) and not str(val).strip():
			continue
		if doc.meta.has_field(key):
			doc.set(key, val)


def _propagate_linked_services_to_created_booking(
	sales_quote,
	booking_doc,
	*,
	blanket_call_off=False,
	selected_charge_row_names=None,
):
	"""Mirror SQ-owned Linked Services onto the new booking and remap per-charge links.

	Subsidiary legs are **cloned** onto the booking; the quote retains its ``IJ-…`` originals
	(the same pattern as charge rows). Blanket call-offs restrict which legs are cloned.

	Raises on failure so conversion does not complete with an empty Linked Services grid.
	"""
	from logistics.utils.sales_quote_one_off_internal_jobs import (
		propagate_linked_services_from_sales_quote_to_booking,
	)

	return propagate_linked_services_from_sales_quote_to_booking(
		sales_quote,
		booking_doc,
		blanket_call_off=blanket_call_off,
		selected_charge_row_names=selected_charge_row_names,
	)


def _propagate_one_off_internal_jobs_to_created_booking(sales_quote, booking_doc):
	"""Backward-compatible alias."""
	_propagate_linked_services_to_created_booking(sales_quote, booking_doc)


def _resolve_transport_locations_from_sales_quote(
	sales_quote,
	first,
	parent_overrides=None,
	transport_charges=None,
):
	"""Resolve location_from / location_to / location_type for Transport Order creation."""
	transport_charges = transport_charges or []
	location_from = getattr(first, "location_from", None) or getattr(sales_quote, "location_from", None)
	location_to = getattr(first, "location_to", None) or getattr(sales_quote, "location_to", None)
	if parent_overrides:
		location_from = parent_overrides.get("location_from") or location_from
		location_to = parent_overrides.get("location_to") or location_to
	if not location_from or not location_to:
		for ch in transport_charges:
			if not location_from and getattr(ch, "location_from", None):
				location_from = ch.location_from
			if not location_to and getattr(ch, "location_to", None):
				location_to = ch.location_to
			if location_from and location_to:
				break
	if (not location_from or not location_to) and (
		getattr(sales_quote, "origin_port", None) or getattr(sales_quote, "destination_port", None)
	):
		if not location_from:
			location_from = getattr(sales_quote, "origin_port", None)
		if not location_to:
			location_to = getattr(sales_quote, "destination_port", None)
	if (not location_from or not location_to) and getattr(sales_quote, "routing_legs", None):
		for leg in sales_quote.routing_legs:
			mode = getattr(leg, "mode", None)
			if mode in ("Road", "Transport") or (mode and str(mode).lower() in ("road", "transport")):
				if not location_from and getattr(leg, "origin", None):
					location_from = leg.origin
				if not location_to and getattr(leg, "destination", None):
					location_to = leg.destination
				if location_from and location_to:
					break
	location_type = getattr(first, "location_type", None) or getattr(sales_quote, "location_type", None)
	if parent_overrides and parent_overrides.get("location_type"):
		location_type = parent_overrides.get("location_type") or location_type
	if not location_type and (location_from or location_to):
		location_type = "UNLOCO"
	return location_from, location_to, location_type


def _build_transport_scope_row_from_sales_quote(
	sales_quote,
	first,
	parent_overrides=None,
	transport_charges=None,
):
	"""Merge Sales Quote Main Service scope with the selected Transport charge row."""
	from logistics.utils.sales_quote_charge_parameters import (
		SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
		resolve_parameters_from_sales_quote_scope,
	)

	row = frappe._dict(resolve_parameters_from_sales_quote_scope(sales_quote))
	row.service_type = "Transport"
	for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
		if fn == "charge_group":
			continue
		val = getattr(first, fn, None) if first else None
		if val is not None and str(val).strip() != "":
			row[fn] = val
	if parent_overrides:
		for k, v in parent_overrides.items():
			if v is not None and str(v).strip() != "":
				row[k] = v
	location_from, location_to, location_type = _resolve_transport_locations_from_sales_quote(
		sales_quote, first, parent_overrides, transport_charges
	)
	row.location_from = location_from
	row.location_to = location_to
	if location_type:
		row.location_type = location_type
	return row


def _create_transport_order_from_sales_quote(
	sales_quote,
	parent_overrides=None,
	selected_charge_row_names=None,
	blanket_call_off=False,
):
	"""Create Transport Order from Sales Quote."""
	throw_if_sales_quote_expired_for_creation(sales_quote)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote)
	transport_charges = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, "Transport")]
	legacy_transport = getattr(sales_quote, "transport", None) or []
	main_ok = getattr(sales_quote, "main_service", None) == "Transport"
	has_transport = bool(transport_charges) or bool(legacy_transport)
	if not main_ok and not has_transport:
		frappe.throw(_("Only Sales Quotes with Transport as main service or Transport charges can create Transport Orders."))
	if not transport_charges and not legacy_transport:
		frappe.throw(_("No transport lines found in this Sales Quote."))

	from logistics.transport.doctype.transport_order.transport_order import _sync_quote_and_sales_quote

	# Use service params (preferred) or first transport charge/row
	first = _first_charge_for_call_off(
		sales_quote,
		"Transport",
		selected_charge_row_names,
		(legacy_transport[0] if legacy_transport else (transport_charges[0] if transport_charges else None)),
	)
	scope_row = _build_transport_scope_row_from_sales_quote(
		sales_quote, first, parent_overrides, transport_charges
	)
	if not scope_row.location_from or not scope_row.location_to:
		frappe.throw(_(
			"Location From and Location To are required for Transport. Set them in Transport charges (location_from, location_to), "
			"in One-off Parameters (Origin Port, Destination Port), or in the Routing leg with mode Road."
		))

	transport_order = frappe.new_doc("Transport Order")
	transport_order.customer = sales_quote.customer
	transport_order.shipper = getattr(sales_quote, "shipper", None)
	transport_order.consignee = getattr(sales_quote, "consignee", None)
	transport_order.booking_date = today()
	transport_order.scheduled_date = today()
	transport_order.quote_type = "Sales Quote"
	transport_order.quote = sales_quote.name
	transport_order.sales_quote = sales_quote.name
	_sync_quote_and_sales_quote(transport_order)

	from logistics.utils.sales_quote_charge_parameters import apply_scope_fields_to_operational_doc
	from logistics.utils.internal_job_from_source import apply_internal_job_detail_row_to_operational_doc

	apply_scope_fields_to_operational_doc(transport_order, scope_row, overwrite=True)
	apply_internal_job_detail_row_to_operational_doc(transport_order, scope_row, overwrite=True)

	if transport_order.transport_template:
		from logistics.transport.doctype.transport_template.transport_template import (
			on_transport_template_selected,
			validate_doc_transport_template,
		)

		on_transport_template_selected(transport_order)
		validate_doc_transport_template(transport_order, context=_("Transport Order"))
	transport_order.company = sales_quote.company
	transport_order.branch = sales_quote.branch
	transport_order.cost_center = sales_quote.cost_center
	transport_order.profit_center = sales_quote.profit_center

	transport_order.transport_job_type = sales_quote._determine_transport_job_type(
		current_job_type=None,
		load_type=transport_order.load_type,
		container_type=transport_order.container_type,
	)
	apply_main_service_flags(transport_order)
	transport_order.is_high_value = cint(getattr(sales_quote, "is_high_value", 0))
	copy_sales_quote_fields_to_target(sales_quote, transport_order)
	apply_party_address_contact_from_source_or_masters(transport_order, sales_quote)
	append_transport_order_door_leg_from_party_masters(transport_order)
	apply_shipper_consignee_defaults(transport_order)
	_apply_parent_overrides_to_doc(transport_order, parent_overrides)

	transport_order.flags.skip_container_no_validation = True
	transport_order.flags.skip_container_type_validation = True
	transport_order.flags.skip_vehicle_type_validation = True
	transport_order.flags.skip_sales_quote_on_change = True

	transport_order.insert(ignore_permissions=True)
	transport_order.reload()
	transport_order.quote_type = "Sales Quote"
	transport_order.quote = sales_quote.name
	transport_order.sales_quote = sales_quote.name
	_sync_quote_and_sales_quote(transport_order)
	if selected_charge_row_names:
		transport_order.flags.blanket_call_off_charge_row_names = list(selected_charge_row_names)
	# Use Transport Order's implementation (separate_billings_per_service_type, main job, legacy tables).
	transport_order._populate_charges_from_sales_quote()
	transport_order.save(ignore_permissions=True)

	_propagate_linked_services_to_created_booking(
		sales_quote,
		transport_order,
		blanket_call_off=blanket_call_off,
		selected_charge_row_names=selected_charge_row_names,
	)
	if not blanket_call_off:
		record_one_off_quote_conversion(sales_quote.name, "Transport Order", transport_order.name)

	frappe.db.commit()
	return {"success": True, "transport_order": transport_order.name, "message": _("Transport Order {0} created.").format(transport_order.name)}


def _get_air_weight_volume_from_sales_quote(sales_quote):
	"""Derive total weight and volume from Sales Quote Air charges (quantity where unit_type is Weight/Volume)."""
	total_weight = flt(getattr(sales_quote, "air_weight", None) or getattr(sales_quote, "weight", None) or 0)
	total_volume = flt(getattr(sales_quote, "air_volume", None) or getattr(sales_quote, "volume", None) or 0)
	air_rows = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, "Air")]
	if not air_rows and getattr(sales_quote, "air_freight", None):
		air_rows = sales_quote.air_freight
	for row in (air_rows or []):
		ut = getattr(row, "unit_type", None) or ""
		qty = flt(getattr(row, "quantity", 0) or 0)
		if ut == "Weight" and qty > 0:
			total_weight += qty
		elif ut == "Volume" and qty > 0:
			total_volume += qty
		# Cost side
		cut = getattr(row, "cost_unit_type", None) or ""
		cq = flt(getattr(row, "cost_quantity", 0) or 0)
		if cut == "Weight" and cq > 0:
			total_weight = max(total_weight, cq)
		elif cut == "Volume" and cq > 0:
			total_volume = max(total_volume, cq)
	return total_weight, total_volume


def _create_air_booking_from_sales_quote(
	sales_quote,
	parent_overrides=None,
	selected_charge_row_names=None,
	blanket_call_off=False,
):
	"""Create Air Booking from Sales Quote."""
	throw_if_sales_quote_expired_for_creation(sales_quote)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote)
	air_charges = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, "Air")]
	legacy_air = getattr(sales_quote, "air_freight", None) or []
	main_ok = getattr(sales_quote, "main_service", None) == "Air"
	has_air = bool(air_charges) or bool(legacy_air)
	if not main_ok and not has_air:
		frappe.throw(_("Only Sales Quotes with Air as main service or Air charges can create Air Bookings."))
	if not air_charges and not legacy_air:
		frappe.throw(_("No air freight lines found in this Sales Quote."))

	first = _first_charge_for_call_off(
		sales_quote,
		"Air",
		selected_charge_row_names,
		(legacy_air[0] if legacy_air else (air_charges[0] if air_charges else None)),
	)
	origin = getattr(first, "origin_port", None) or getattr(sales_quote, "origin_port", None)
	dest = getattr(first, "destination_port", None) or getattr(sales_quote, "destination_port", None)
	if parent_overrides:
		origin = parent_overrides.get("origin_port") or origin
		dest = parent_overrides.get("destination_port") or dest
	# Fallback: scan all Air charges for origin/destination
	if not origin or not dest:
		for ch in air_charges:
			if not origin and getattr(ch, "origin_port", None):
				origin = ch.origin_port
			if not dest and getattr(ch, "destination_port", None):
				dest = ch.destination_port
			if origin and dest:
				break
	# Fallback: get from routing leg with mode Air
	if (not origin or not dest) and getattr(sales_quote, "routing_legs", None):
		for leg in sales_quote.routing_legs:
			if getattr(leg, "mode", None) == "Air" and (getattr(leg, "origin", None) or getattr(leg, "destination", None)):
				if not origin and getattr(leg, "origin", None):
					origin = leg.origin
				if not dest and getattr(leg, "destination", None):
					dest = leg.destination
				if origin and dest:
					break
	if not origin or not dest:
		frappe.throw(_("Origin Port and Destination Port are required for Air mode. Set them in the Air charge parameters (Origin Port, Destination Port) or in the Routing leg with mode Air."))
	if not sales_quote.shipper or not sales_quote.consignee:
		frappe.throw(_("Shipper and Consignee are required for Air mode."))

	air_booking = frappe.new_doc("Air Booking")
	air_booking.booking_date = sales_quote.date or today()
	air_booking.local_customer = sales_quote.customer
	air_booking.quote_type = "Sales Quote"
	air_booking.quote = sales_quote.name
	air_booking.sales_quote = sales_quote.name
	air_booking.origin_port = origin
	air_booking.destination_port = dest
	air_booking.direction = getattr(first, "direction", None) or getattr(sales_quote, "direction", None) or "Export"
	air_booking.shipper = sales_quote.shipper
	air_booking.consignee = sales_quote.consignee
	air_booking.airline = getattr(first, "airline", None) or getattr(sales_quote, "airline", None)
	air_booking.freight_agent = getattr(first, "freight_agent", None) or getattr(sales_quote, "freight_agent", None)
	air_booking.house_type = getattr(first, "air_house_type", None) or getattr(first, "house_type", None)
	# Normalize legacy house_type values
	if air_booking.house_type == "Direct":
		air_booking.house_type = "Standard House"
	elif air_booking.house_type == "Consolidation":
		air_booking.house_type = "Co-load Master"
	air_booking.company = sales_quote.company
	air_booking.branch = sales_quote.branch
	air_booking.cost_center = sales_quote.cost_center
	air_booking.profit_center = sales_quote.profit_center
	apply_main_service_flags(air_booking)
	air_booking.is_high_value = cint(getattr(sales_quote, "is_high_value", 0))
	copy_sales_quote_fields_to_target(sales_quote, air_booking)

	# Set weight/volume from Sales Quote so charge quantities can be calculated when populating
	weight = getattr(first, "weight", None) or getattr(sales_quote, "weight", None)
	volume = getattr(first, "volume", None) or getattr(sales_quote, "volume", None)
	if weight is not None and flt(weight) > 0:
		air_booking.weight = weight
	if volume is not None and flt(volume) > 0:
		air_booking.volume = volume

	apply_party_address_contact_from_source_or_masters(air_booking, sales_quote)
	apply_shipper_consignee_defaults(air_booking)
	_apply_parent_overrides_to_doc(air_booking, parent_overrides)

	from logistics.utils.sales_quote_charge_parameters import (
		apply_scope_fields_to_operational_doc,
		build_main_service_scope_row,
	)

	scope_row = build_main_service_scope_row(sales_quote, first, parent_overrides)
	scope_row.origin_port = origin
	scope_row.destination_port = dest
	apply_scope_fields_to_operational_doc(air_booking, scope_row, overwrite=False)

	# Populate charges + routing before insert so they are saved with the document
	# (routing is applied inside _populate_charges_from_sales_quote; #1135)
	from logistics.air_freight.doctype.air_booking.air_booking import _sync_quote_and_sales_quote
	_sync_quote_and_sales_quote(air_booking)
	if selected_charge_row_names:
		air_booking.flags.blanket_call_off_charge_row_names = list(selected_charge_row_names)
	air_booking.flags.skip_sales_quote_on_change = True
	try:
		air_booking._populate_charges_from_sales_quote(sales_quote.name)
		air_booking._normalize_charges_before_save()
		air_booking.insert(ignore_permissions=True)
	finally:
		air_booking.flags.skip_sales_quote_on_change = False

	_propagate_linked_services_to_created_booking(
		sales_quote,
		air_booking,
		blanket_call_off=blanket_call_off,
		selected_charge_row_names=selected_charge_row_names,
	)
	if not blanket_call_off:
		record_one_off_quote_conversion(sales_quote.name, "Air Booking", air_booking.name)

	frappe.db.commit()
	return {"success": True, "air_booking": air_booking.name, "message": _("Air Booking {0} created.").format(air_booking.name)}


def _create_sea_booking_from_sales_quote(
	sales_quote,
	parent_overrides=None,
	selected_charge_row_names=None,
	blanket_call_off=False,
):
	"""Create Sea Booking from Sales Quote."""
	throw_if_sales_quote_expired_for_creation(sales_quote)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote)

	if getattr(sales_quote, "quotation_type", None) == "One-off" and not blanket_call_off:
		existing_sb = resolve_single_main_sea_booking_for_sales_quote(sales_quote.name)
		if existing_sb:
			record_one_off_quote_conversion(sales_quote.name, "Sea Booking", existing_sb)
			return {
				"success": True,
				"sea_booking": existing_sb,
				"already_exists": True,
				"message": _("Sea Booking {0} already exists for this One-off Sales Quote.").format(existing_sb),
			}
		validate_one_off_quote_not_converted(
			sales_quote.name,
			current_doctype="Sea Booking",
			allow_main_transport_if_converted_to_declaration_order=True,
		)

	sea_charges = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, "Sea")]
	legacy_sea = getattr(sales_quote, "sea_freight", None) or []
	main_ok = getattr(sales_quote, "main_service", None) == "Sea"
	has_sea = bool(sea_charges) or bool(legacy_sea)
	if not main_ok and not has_sea:
		frappe.throw(_("Only Sales Quotes with Sea as main service or Sea charges can create Sea Bookings."))
	if not sea_charges and not legacy_sea:
		frappe.throw(_("No sea freight lines found in this Sales Quote."))

	first = _first_charge_for_call_off(
		sales_quote,
		"Sea",
		selected_charge_row_names,
		(legacy_sea[0] if legacy_sea else (sea_charges[0] if sea_charges else None)),
	)
	origin = (
		getattr(first, "origin_port", None)
		or getattr(sales_quote, "origin_port_sea", None)
		or getattr(sales_quote, "origin_port", None)
		or getattr(sales_quote, "location_from", None)
	)
	dest = (
		getattr(first, "destination_port", None)
		or getattr(sales_quote, "destination_port_sea", None)
		or getattr(sales_quote, "destination_port", None)
		or getattr(sales_quote, "location_to", None)
	)
	if parent_overrides:
		origin = parent_overrides.get("origin_port") or origin
		dest = parent_overrides.get("destination_port") or dest
	if not origin or not dest:
		for ch in sea_charges:
			if not origin and getattr(ch, "origin_port", None):
				origin = ch.origin_port
			if not dest and getattr(ch, "destination_port", None):
				dest = ch.destination_port
			if origin and dest:
				break
	if (not origin or not dest) and getattr(sales_quote, "routing_legs", None):
		for leg in sales_quote.routing_legs:
			if getattr(leg, "mode", None) == "Sea" and (
				getattr(leg, "origin", None) or getattr(leg, "destination", None)
			):
				if not origin and getattr(leg, "origin", None):
					origin = leg.origin
				if not dest and getattr(leg, "destination", None):
					dest = leg.destination
				if origin and dest:
					break
	if not origin or not dest:
		frappe.throw(
			_(
				"Origin Port and Destination Port are required for Sea mode. Set them in Sea charge parameters, "
				"One-off Parameters (Origin Port, Destination Port), or in the Routing leg with mode Sea."
			)
		)
	if not sales_quote.shipper or not sales_quote.consignee:
		frappe.throw(_("Shipper and Consignee are required for Sea mode."))

	sea_booking = frappe.new_doc("Sea Booking")
	sea_booking.booking_date = sales_quote.date or today()
	sea_booking.local_customer = sales_quote.customer
	sea_booking.quote_type = "Sales Quote"
	sea_booking.quote = sales_quote.name
	sea_booking.sales_quote = sales_quote.name
	sea_booking.origin_port = origin
	sea_booking.destination_port = dest
	sea_booking.direction = getattr(first, "direction", None) or getattr(sales_quote, "direction", None) or "Export"
	sea_booking.shipping_line = getattr(first, "shipping_line", None) or getattr(sales_quote, "shipping_line", None)
	sea_booking.freight_agent = (
		getattr(first, "freight_agent_sea", None) or getattr(first, "freight_agent", None)
		or getattr(sales_quote, "freight_agent_sea", None)
	)
	sea_booking.transport_mode = getattr(first, "transport_mode", None) or getattr(sales_quote, "transport_mode", None) or "FCL"
	sea_booking.shipper = sales_quote.shipper
	sea_booking.consignee = sales_quote.consignee
	sea_booking.company = sales_quote.company
	sea_booking.branch = sales_quote.branch
	sea_booking.cost_center = sales_quote.cost_center
	sea_booking.profit_center = sales_quote.profit_center
	apply_main_service_flags(sea_booking)
	sea_booking.is_high_value = cint(getattr(sales_quote, "is_high_value", 0))
	copy_sales_quote_fields_to_target(sales_quote, sea_booking)

	apply_sales_quote_routing_to_booking(sea_booking, sales_quote)
	apply_party_address_contact_from_source_or_masters(sea_booking, sales_quote)
	apply_shipper_consignee_defaults(sea_booking)
	_apply_parent_overrides_to_doc(sea_booking, parent_overrides)

	from logistics.utils.sales_quote_charge_parameters import (
		apply_scope_fields_to_operational_doc,
		build_main_service_scope_row,
	)

	scope_row = build_main_service_scope_row(sales_quote, first, parent_overrides)
	scope_row.origin_port = origin
	scope_row.destination_port = dest
	apply_scope_fields_to_operational_doc(sea_booking, scope_row, overwrite=False)

	# Populate charges before insert (same as Air Booking) so One-off validation and desk load are consistent.
	from logistics.sea_freight.doctype.sea_booking.sea_booking import _sync_quote_and_sales_quote

	_sync_quote_and_sales_quote(sea_booking)
	if selected_charge_row_names:
		sea_booking.flags.blanket_call_off_charge_row_names = list(selected_charge_row_names)
	sea_booking._populate_charges_from_sales_quote(sales_quote)

	sea_booking.insert(ignore_permissions=True)

	_propagate_linked_services_to_created_booking(
		sales_quote,
		sea_booking,
		blanket_call_off=blanket_call_off,
		selected_charge_row_names=selected_charge_row_names,
	)
	if not blanket_call_off:
		record_one_off_quote_conversion(sales_quote.name, "Sea Booking", sea_booking.name)

	frappe.db.commit()
	return {"success": True, "sea_booking": sea_booking.name, "message": _("Sea Booking {0} created.").format(sea_booking.name)}


@frappe.whitelist()
def suggest_contributors_for_routing_leg(sales_quote_name, leg_idx):
	"""Suggest cross-module billing contributors for a Sales Quote routing leg."""
	from logistics.billing.cross_module_billing import get_suggested_contributors_for_anchor

	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	leg_idx = int(leg_idx)
	leg = next((row for row in (sales_quote.routing_legs or []) if row.idx == leg_idx), None)
	if not leg:
		frappe.throw(_("Routing leg {0} not found.").format(leg_idx))
	job_type, job_no = _resolve_job_for_routing_leg(sales_quote, leg)
	if not job_type or not job_no:
		return []
	return get_suggested_contributors_for_anchor(
		job_type,
		job_no,
		sales_quote=sales_quote_name,
	)


@frappe.whitelist()
def get_load_type_service_flags(load_types=None):
	"""Return mode flags for Load Type names (client sanitization vs service_type)."""
	from logistics.utils.service_mode_flags import get_service_mode_flags_bulk

	return get_service_mode_flags_bulk("Load Type", load_types)


@frappe.whitelist()
def get_transport_mode_service_flags(transport_modes=None):
	"""Return mode flags for Transport Mode names (client sanitization vs main_service)."""
	from logistics.utils.service_mode_flags import get_service_mode_flags_bulk

	return get_service_mode_flags_bulk("Transport Mode", transport_modes)


@frappe.whitelist()
def get_freight_agent_service_flags(freight_agents=None):
	"""Return mode flags for Freight Agent names (client sanitization vs main_service)."""
	from logistics.utils.service_mode_flags import get_service_mode_flags_bulk

	return get_service_mode_flags_bulk("Freight Agent", freight_agents)


@frappe.whitelist()
def get_vehicle_types_for_load_type(load_type):
	"""
	Get list of Vehicle Types that have the specified load_type in their allowed_load_types.
	
	Args:
		load_type: The Load Type name to filter by
		
	Returns:
		dict: List of Vehicle Type names that allow the specified load_type
	"""
	if not load_type:
		return {"vehicle_types": []}
	
	# Verify that the load_type exists
	if not frappe.db.exists("Load Type", load_type):
		return {"vehicle_types": []}
	
	# Get all Vehicle Types that have this load_type in their allowed_load_types child table
	vehicle_types = frappe.db.sql("""
		SELECT DISTINCT parent
		FROM `tabVehicle Type Load Types`
		WHERE load_type = %s
		AND parent IS NOT NULL
	""", (load_type,), as_dict=True)
	
	vehicle_type_names = [vt.parent for vt in vehicle_types if vt.parent]
	
	return {"vehicle_types": vehicle_type_names}


def _populate_charges_from_sales_quote_air_freight(air_shipment, sales_quote):
	"""
	Populate charges in Air Shipment from Sales Quote Air Freight records.
	
	Args:
		air_shipment: Air Shipment document
		sales_quote: Sales Quote document
	"""
	try:
		# Clear existing charges
		air_shipment.set("charges", [])
		
		filters = sales_quote_charge_filters(air_shipment, sales_quote)

		# Get from Sales Quote Charge (filtered) or Sales Quote Air Freight (legacy)
		from logistics.utils.sales_quote_charge_parameters import (
			SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
			filter_fields_existing_in_doctype,
		)
		from logistics.utils.sales_quote_charge_copy import extend_charge_fields_with_scope_and_internal_job

		charge_fields = extend_charge_fields_with_scope_and_internal_job(
			[
				"item_code", "item_name", "description", "revenue_calculation_method", "calculation_method", "uom", "currency",
				"unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
				"maximum_charge", "base_amount", "estimated_revenue",
				"charge_type", "charge_category",
				"apply_95_5_rule", "taxable_freight_item", "taxable_freight_item_tax_template",
				"use_tariff_in_revenue", "use_tariff_in_cost", "tariff",
				"revenue_tariff", "cost_tariff", "bill_to_exchange_rate", "pay_to_exchange_rate",
				"bill_to_exchange_rate_source", "pay_to_exchange_rate_source", "service_type",
			]
			+ list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS)
		)
		sqc_fields = filter_fields_existing_in_doctype("Sales Quote Charge", charge_fields)
		legacy_air_fields = filter_fields_existing_in_doctype("Sales Quote Air Freight", charge_fields)
		sales_quote_air_freight_records = frappe.get_all(
			"Sales Quote Charge",
			filters=filters,
			fields=sqc_fields,
			order_by="idx"
		)
		if not sales_quote_air_freight_records and frappe.db.table_exists("Sales Quote Air Freight"):
			sales_quote_air_freight_records = frappe.get_all(
				"Sales Quote Air Freight",
				filters={"parent": sales_quote.name, "parenttype": "Sales Quote"},
				fields=legacy_air_fields,
				order_by="idx"
			)
		sales_quote_air_freight_records = filter_sales_quote_charge_rows_for_operational_doc(
			air_shipment, sales_quote_air_freight_records
		)

		# Map and populate charges
		charges_added = 0
		for sqaf_record in sales_quote_air_freight_records:
			charge_row = _map_sales_quote_air_freight_to_charge(sqaf_record, air_shipment)
			if charge_row:
				air_shipment.append("charges", charge_row)
				charges_added += 1

		from logistics.utils.operational_exchange_rates import sync_operational_exchange_rates_from_charge_rows

		sync_operational_exchange_rates_from_charge_rows(air_shipment, air_shipment.charges)
		
		if charges_added > 0:
			frappe.msgprint(
				f"Successfully populated {charges_added} charges from Sales Quote",
				title="Charges Updated",
				indicator="green"
			)
		
	except Exception as e:
		frappe.log_error(
			f"Error populating charges from Sales Quote Air Freight: {str(e)}",
			"Sales Quote Air Freight - Charges Population Error"
		)
		raise


def _normalize_uom_for_air_booking_charges(uom_value, unit_type=None):
	"""
	Normalize UOM value from Link field (UOM DocType name) to Select field options.
	
	Air Booking Charges has a Select field with options: "kg", "m³", "package", "shipment", "hour", "day"
	This function converts UOM record names (like "Kg", "KG", "M³", etc.) to the allowed lowercase values.
	
	Args:
		uom_value: UOM value from Link field (could be "Kg", "kg", "M³", etc.)
		unit_type: Optional unit_type to help determine the correct UOM
	
	Returns:
		Normalized UOM value matching one of the allowed options
	"""
	if not uom_value:
		# If no UOM provided, try to infer from unit_type
		if unit_type in ("Weight", "Chargeable Weight"):
			return "kg"
		elif unit_type == "Volume":
			return "m³"
		elif unit_type in ["Package", "Piece"]:
			return "package"
		elif unit_type == "Shipment":
			return "shipment"
		elif unit_type == "Operation Time":
			return "hour"
		else:
			return "package"  # Default fallback
	
	# Normalize the UOM value (case-insensitive matching)
	uom_lower = str(uom_value).strip().lower()
	
	# Map common UOM variations to allowed values
	uom_mapping = {
		# Weight variations -> "kg"
		"kg": "kg",
		"kilogram": "kg",
		"kilograms": "kg",
		"kgs": "kg",
		# Volume variations -> "m³"
		"m³": "m³",
		"m3": "m³",
		"cbm": "m³",
		"cubic meter": "m³",
		"cubic meters": "m³",
		"m^3": "m³",
		# Package variations -> "package"
		"package": "package",
		"packages": "package",
		"pkg": "package",
		"pkgs": "package",
		"piece": "package",
		"pieces": "package",
		"pc": "package",
		"pcs": "package",
		# Shipment variations -> "shipment"
		"shipment": "shipment",
		"shipments": "shipment",
		"ship": "shipment",
		# Hour variations -> "hour"
		"hour": "hour",
		"hours": "hour",
		"hr": "hour",
		"hrs": "hour",
		# Day variations -> "day"
		"day": "day",
		"days": "day",
		"d": "day",
	}
	
	# Check if we have a direct match
	if uom_lower in uom_mapping:
		return uom_mapping[uom_lower]
	
	# If no match found, try to infer from unit_type
	if unit_type:
		if unit_type in ("Weight", "Chargeable Weight"):
			return "kg"
		elif unit_type == "Volume":
			return "m³"
		elif unit_type in ["Package", "Piece"]:
			return "package"
		elif unit_type == "Shipment":
			return "shipment"
		elif unit_type == "Operation Time":
			return "hour"
	
	# Default fallback
	return "package"


def _map_sales_quote_air_freight_to_charge(sqaf_record, air_shipment):
	"""
	Map sales_quote_air_freight record to air_shipment_charges format.
	
	Args:
		sqaf_record: Sales Quote Air Freight record
		air_shipment: Air Shipment document
		
	Returns:
		dict: Mapped charge data
	"""
	try:
		def _af_r(key, default=None):
			return sqaf_record.get(key, default) if isinstance(sqaf_record, dict) else getattr(sqaf_record, key, default)

		# Get the item details to fetch additional required fields
		item_doc = frappe.get_doc("Item", _af_r("item_code"))
		
		# Get default currency from system settings
		default_currency = frappe.get_system_settings("currency") or "USD"

		unit_type = _af_r("unit_type")
		from logistics.utils.charges_calculation import get_quantity_from_parent_by_unit_type

		quantity = get_quantity_from_parent_by_unit_type(air_shipment, unit_type)
		if unit_type in ("Package", "Piece") and flt(quantity) <= 0:
			quantity = 1
		cost_unit_type = _af_r("cost_unit_type")
		cost_quantity = (
			get_quantity_from_parent_by_unit_type(air_shipment, cost_unit_type)
			if cost_unit_type
			else None
		)
		if cost_unit_type in ("Package", "Piece") and flt(cost_quantity or 0) <= 0:
			cost_quantity = 1

		revenue_calculation_method = (
			_af_r("revenue_calculation_method") or _af_r("calculation_method") or "Per Unit"
		)

		from logistics.utils.charges_calculation import normalize_operational_charge_type

		raw_charge_type = _af_r("charge_type") or (
			item_doc.custom_charge_type if hasattr(item_doc, "custom_charge_type") and item_doc.custom_charge_type else None
		)
		charge_type = normalize_operational_charge_type(raw_charge_type, default="Revenue")
		charge_category = _af_r("charge_category") or (
			item_doc.custom_charge_category if hasattr(item_doc, "custom_charge_category") and item_doc.custom_charge_category else None
		) or "Other"
		
		normalized_uom = _normalize_uom_for_air_booking_charges(
			_af_r("uom"),
			_af_r("unit_type"),
		)
		
		_sq_st = (
			sqaf_record.get("service_type")
			if isinstance(sqaf_record, dict)
			else getattr(sqaf_record, "service_type", None)
		) or "Air"
		# Prefer description from quote charge row; fall back to item master
		_af_description = _af_r("description")
		if not _af_description:
			if hasattr(item_doc, "description") and item_doc.description:
				_af_description = item_doc.description
			else:
				_af_description = _af_r("item_name") or item_doc.item_name

		charge_data = {
			"service_type": _sq_st,
			"item_code": _af_r("item_code"),
			"item_name": _af_r("item_name") or item_doc.item_name,
			"description": _af_description,
			"charge_type": charge_type,
			"charge_category": charge_category,
			"revenue_calculation_method": revenue_calculation_method,
			"unit_rate": _af_r("unit_rate") or 0,
			"currency": _af_r("currency") or default_currency,
			"quantity": quantity,
			"unit_type": unit_type,
			"unit_of_measure": normalized_uom,
			"billing_status": "To Bill",
			"bill_to": getattr(sqaf_record, "bill_to", None),
			"pay_to": getattr(sqaf_record, "pay_to", None),
			"use_tariff_in_revenue": getattr(sqaf_record, "use_tariff_in_revenue", False),
			"use_tariff_in_cost": getattr(sqaf_record, "use_tariff_in_cost", False),
			"tariff": getattr(sqaf_record, "tariff", None),
			"revenue_tariff": getattr(sqaf_record, "revenue_tariff", None),
			"cost_tariff": getattr(sqaf_record, "cost_tariff", None),
			"bill_to_exchange_rate": _af_r("bill_to_exchange_rate"),
			"pay_to_exchange_rate": _af_r("pay_to_exchange_rate"),
			"bill_to_exchange_rate_source": _af_r("bill_to_exchange_rate_source"),
			"pay_to_exchange_rate_source": _af_r("pay_to_exchange_rate_source"),
		}
		
		# Add minimum/maximum charge if available
		if _af_r("minimum_charge"):
			charge_data["minimum_charge"] = _af_r("minimum_charge")
		if _af_r("maximum_charge"):
			charge_data["maximum_charge"] = _af_r("maximum_charge")
		if _af_r("cost_calculation_method"):
			charge_data["cost_calculation_method"] = _af_r("cost_calculation_method")
		if _af_r("unit_cost") is not None:
			charge_data["unit_cost"] = _af_r("unit_cost")
		if cost_unit_type:
			charge_data["cost_unit_type"] = cost_unit_type
		if cost_quantity is not None:
			charge_data["cost_quantity"] = cost_quantity
		if _af_r("cost_currency"):
			charge_data["cost_currency"] = _af_r("cost_currency")

		if _af_r("apply_95_5_rule") is not None:
			charge_data["apply_95_5_rule"] = cint(_af_r("apply_95_5_rule"))
		if _af_r("taxable_freight_item"):
			charge_data["taxable_freight_item"] = _af_r("taxable_freight_item")
		if _af_r("taxable_freight_item_tax_template"):
			charge_data["taxable_freight_item_tax_template"] = _af_r("taxable_freight_item_tax_template")

		from logistics.utils.sales_quote_charge_copy import apply_scope_tagging_to_mapped_charge

		apply_scope_tagging_to_mapped_charge(sqaf_record, charge_data)

		return charge_data

	except Exception as e:
		frappe.log_error(
			f"Error mapping sales quote air freight record: {str(e)}",
			"Sales Quote Air Freight Mapping Error"
		)
		return None


def _populate_charges_from_sales_quote_sea_freight(sea_shipment, sales_quote):
	"""
	Populate charges in Sea Shipment from Sales Quote Sea Freight records.
	
	Args:
		sea_shipment: Sea Shipment document
		sales_quote: Sales Quote document
	"""
	try:
		# Clear existing charges
		sea_shipment.set("charges", [])
		
		filters = sales_quote_charge_filters(sea_shipment, sales_quote)

		# Get from Sales Quote Charge (filtered) or Sales Quote Sea Freight (legacy)
		from logistics.utils.sales_quote_charge_parameters import (
			SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
			filter_fields_existing_in_doctype,
		)

		charge_fields = [
			"item_code", "item_name", "description", "revenue_calculation_method", "calculation_method", "uom", "currency",
			"unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
			"maximum_charge", "base_amount", "estimated_revenue",
			"charge_type", "charge_category",
			"apply_95_5_rule", "taxable_freight_item", "taxable_freight_item_tax_template",
			"use_tariff_in_revenue", "use_tariff_in_cost", "tariff",
			"revenue_tariff", "cost_tariff", "bill_to_exchange_rate", "pay_to_exchange_rate",
			"bill_to_exchange_rate_source", "pay_to_exchange_rate_source", "service_type",
		] + list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS)
		sqc_fields = filter_fields_existing_in_doctype("Sales Quote Charge", charge_fields)
		legacy_sea_fields = filter_fields_existing_in_doctype("Sales Quote Sea Freight", charge_fields)
		sales_quote_sea_freight_records = frappe.get_all(
			"Sales Quote Charge",
			filters=filters,
			fields=sqc_fields,
			order_by="idx"
		)
		if not sales_quote_sea_freight_records and frappe.db.table_exists("Sales Quote Sea Freight"):
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Sea Freight",
				filters={"parent": sales_quote.name, "parenttype": "Sales Quote"},
				fields=legacy_sea_fields,
				order_by="idx"
			)
		sales_quote_sea_freight_records = filter_sales_quote_charge_rows_for_operational_doc(
			sea_shipment, sales_quote_sea_freight_records
		)

		# Map and populate charges
		charges_added = 0
		for sqsf_record in sales_quote_sea_freight_records:
			charge_row = _map_sales_quote_sea_freight_to_charge(sqsf_record, sea_shipment)
			if charge_row:
				sea_shipment.append("charges", charge_row)
				charges_added += 1

		from logistics.utils.operational_exchange_rates import sync_operational_exchange_rates_from_charge_rows

		sync_operational_exchange_rates_from_charge_rows(sea_shipment, sea_shipment.charges)
		
		if charges_added > 0:
			frappe.msgprint(
				f"Successfully populated {charges_added} charges from Sales Quote",
				title="Charges Updated",
				indicator="green"
			)
		
	except Exception as e:
		frappe.log_error(
			f"Error populating charges from Sales Quote Sea Freight: {str(e)}",
			"Sales Quote Sea Freight - Charges Population Error"
		)
		raise


def _map_sales_quote_sea_freight_to_charge(sqsf_record, sea_shipment):
	"""
	Map sales_quote_sea_freight record to sea_shipment_charges format.
	
	Args:
		sqsf_record: Sales Quote Sea Freight record
		sea_shipment: Sea Shipment document
		
	Returns:
		dict: Mapped charge data
	"""
	try:
		def _sf_r(key, default=None):
			return sqsf_record.get(key, default) if isinstance(sqsf_record, dict) else getattr(sqsf_record, key, default)

		# Get the item details to fetch additional required fields
		item_doc = frappe.get_doc("Item", _sf_r("item_code"))
		
		# Get default currency from system settings
		default_currency = frappe.get_system_settings("currency") or "USD"
		
		# Map unit_type to determine quantity
		unit_type_to_unit = {
			"Weight": "kg",
			"Chargeable Weight": "kg",
			"Volume": "m³",
			"Package": "package",
			"Piece": "package",
			"Shipment": "shipment",
			"Container": "container"
		}
		unit = unit_type_to_unit.get(_sf_r("unit_type"), "shipment")
		
		# Get quantity based on unit type
		quantity = 0
		if _sf_r("unit_type") == "Chargeable Weight":
			quantity = flt(
				sea_shipment.get("chargeable", 0)
				or sea_shipment.get("chargeable_weight", 0)
			)
		elif _sf_r("unit_type") == "Weight":
			quantity = flt(sea_shipment.get("total_weight")) or 0
		elif _sf_r("unit_type") == "Volume":
			quantity = flt(sea_shipment.get("total_volume")) or 0
		elif _sf_r("unit_type") == "Package":
			# Get package count from Sea Shipment if available
			if hasattr(sea_shipment, 'packages') and sea_shipment.packages:
				quantity = len(sea_shipment.packages)
			else:
				quantity = 1
		elif _sf_r("unit_type") == "Container":
			# Get container count from Sea Shipment if available
			if hasattr(sea_shipment, 'containers') and sea_shipment.containers:
				quantity = len(sea_shipment.containers)
			else:
				quantity = 1
		elif _sf_r("unit_type") == "Shipment":
			quantity = 1
		else:
			quantity = 1
		
		# Calculate selling amount based on calculation method
		_sf_rev = (_sf_r("revenue_calculation_method") or _sf_r("calculation_method") or "").strip()
		_sf_ur = flt(_sf_r("unit_rate")) or 0
		selling_amount = 0
		if _sf_rev == "Per Unit":
			selling_amount = _sf_ur * quantity
			# Apply minimum/maximum charge
			if _sf_r("minimum_charge") and selling_amount < flt(_sf_r("minimum_charge")):
				selling_amount = flt(_sf_r("minimum_charge"))
			if _sf_r("maximum_charge") and selling_amount > flt(_sf_r("maximum_charge")):
				selling_amount = flt(_sf_r("maximum_charge"))
		elif _sf_rev == "Fixed Amount":
			selling_amount = _sf_ur
		elif _sf_rev == "Base Plus Additional":
			base = flt(_sf_r("base_amount")) or 0
			additional = _sf_ur * max(0, quantity - 1)
			selling_amount = base + additional
		elif _sf_rev == "First Plus Additional":
			min_qty = flt(_sf_r("minimum_quantity")) or 1
			if quantity <= min_qty:
				selling_amount = _sf_ur
			else:
				additional = _sf_ur * (quantity - min_qty)
				selling_amount = _sf_ur + additional
		else:
			selling_amount = _sf_ur
		
		charge_type = _sf_r("charge_type") or (
			item_doc.custom_charge_type if hasattr(item_doc, "custom_charge_type") and item_doc.custom_charge_type else None
		) or "Other"
		charge_category = _sf_r("charge_category") or (
			item_doc.custom_charge_category if hasattr(item_doc, "custom_charge_category") and item_doc.custom_charge_category else None
		) or "Other"

		_sq_st = (
			sqsf_record.get("service_type")
			if isinstance(sqsf_record, dict)
			else getattr(sqsf_record, "service_type", None)
		) or "Sea"
		# Prefer description from quote charge row; fall back to item master
		_sf_description = _sf_r("description")
		if not _sf_description:
			if hasattr(item_doc, "description") and item_doc.description:
				_sf_description = item_doc.description
			else:
				_sf_description = _sf_r("item_name") or item_doc.item_name

		# Map the fields from sales_quote_sea_freight to sea_shipment_charges
		charge_data = {
			"service_type": _sq_st,
			"charge_item": _sf_r("item_code"),
			"charge_name": _sf_r("item_name") or item_doc.item_name,
			"charge_type": charge_type,
			"charge_category": charge_category,
			"description": _sf_description,
			"charge_description": _sf_r("item_name") or item_doc.item_name,
			"bill_to": getattr(sqsf_record, "bill_to", None) or (sea_shipment.local_customer if hasattr(sea_shipment, 'local_customer') else None),
			"pay_to": getattr(sqsf_record, "pay_to", None),
			"selling_currency": _sf_r("currency") or default_currency,
			"selling_amount": selling_amount,
			"per_unit_rate": _sf_r("unit_rate") or 0,
			"unit": unit,
			"revenue_calc_type": _sf_r("revenue_calculation_method") or _sf_r("calculation_method") or "Manual",
			"base_amount": _sf_r("base_amount") or 0,
			"use_tariff_in_revenue": getattr(sqsf_record, "use_tariff_in_revenue", False),
			"use_tariff_in_cost": getattr(sqsf_record, "use_tariff_in_cost", False),
			"tariff": getattr(sqsf_record, "tariff", None),
			"revenue_tariff": getattr(sqsf_record, "revenue_tariff", None),
			"cost_tariff": getattr(sqsf_record, "cost_tariff", None),
			"bill_to_exchange_rate": _sf_r("bill_to_exchange_rate"),
			"pay_to_exchange_rate": _sf_r("pay_to_exchange_rate"),
			"bill_to_exchange_rate_source": _sf_r("bill_to_exchange_rate_source"),
			"pay_to_exchange_rate_source": _sf_r("pay_to_exchange_rate_source"),
		}
		
		# Add minimum charge if available
		if _sf_r("minimum_charge"):
			charge_data["minimum"] = _sf_r("minimum_charge")

		if _sf_r("apply_95_5_rule") is not None:
			charge_data["apply_95_5_rule"] = cint(_sf_r("apply_95_5_rule"))
		if _sf_r("taxable_freight_item"):
			charge_data["taxable_freight_item"] = _sf_r("taxable_freight_item")
		if _sf_r("taxable_freight_item_tax_template"):
			charge_data["taxable_freight_item_tax_template"] = _sf_r("taxable_freight_item_tax_template")

		return charge_data

	except Exception as e:
		frappe.log_error(
			f"Error mapping sales quote sea freight record: {str(e)}",
			"Sales Quote Sea Freight Mapping Error"
		)
		return None


def format_one_off_converted_to_ref(doctype: str | None, document_name: str | None) -> str | None:
	"""Human-readable target for One-off *Converted To* (e.g. ``Sea Booking SBK000000312``)."""
	dn = (document_name or "").strip()
	if not dn:
		return None
	dt = (doctype or "").strip()
	ref = f"{dt} {dn}" if dt else dn
	return ref[:140] if len(ref) > 140 else ref


_ONE_OFF_CONVERTED_REF_PREFIX_DOCTYPE = (
	("SBK", "Sea Booking"),
	("DCO", "Declaration Order"),
	("TRO", "Transport Order"),
	("ABK", "Air Booking"),
	("SF", "Sea Shipment"),
	("AF", "Air Shipment"),
	("WHC", "Warehouse Contract"),
)


def normalize_one_off_converted_to_ref(
	converted_ref: str | None,
	doctype: str | None = None,
	document_name: str | None = None,
) -> str | None:
	"""Normalize legacy ``Doctype: Name`` or bare document id to ``Doctype Name`` when possible."""
	cr = (converted_ref or "").strip()
	if not cr:
		if doctype and document_name:
			return format_one_off_converted_to_ref(doctype, document_name)
		return None
	if ": " in cr:
		parts = cr.split(": ", 1)
		if len(parts) == 2 and parts[0].strip() and parts[1].strip():
			return format_one_off_converted_to_ref(parts[0].strip(), parts[1].strip())
	for _, dt in _ONE_OFF_CONVERTED_REF_PREFIX_DOCTYPE:
		if cr.startswith(f"{dt} "):
			return cr
	if doctype:
		dn = (document_name or cr).strip()
		if dn:
			formatted = format_one_off_converted_to_ref(doctype, dn)
			if formatted:
				return formatted
	for prefix, dt in _ONE_OFF_CONVERTED_REF_PREFIX_DOCTYPE:
		if cr.startswith(prefix):
			return format_one_off_converted_to_ref(dt, cr)
	return cr


def one_off_stored_conversion_matches(
	converted_ref: str, doctype: str | None, document_name: str | None
) -> bool:
	"""True if ``converted_ref`` (DB) refers to the same document as ``doctype`` + ``document_name``.

	Supports **compact** storage (``ABK-000000426``), **standard** ``Air Booking ABK-...``,
	legacy ``Air Booking: ABK-...``, and exact match to ``{doctype} {name}``."""
	cr = normalize_one_off_converted_to_ref(converted_ref) or (converted_ref or "").strip()
	if not cr or not (document_name or "").strip():
		return False
	dn = document_name.strip()
	dt = (doctype or "").strip()
	if cr == dn:
		return True
	if dt and cr == f"{dt} {dn}".strip():
		return True
	if dt and cr.startswith(f"{dt} "):
		return cr[len(dt) + 1 :].strip() == dn
	if dt:
		legacy_colon = f"{dt}: {dn}"
		if cr == legacy_colon:
			return True
	return False


def record_one_off_quote_conversion(
	sales_quote_name: str, doctype: str, document_name: str
) -> None:
	"""Record which booking/order a One-off Sales Quote was converted to (on create or submit)."""
	if not sales_quote_name or not (document_name or "").strip():
		return
	if not frappe.db.exists("Sales Quote", sales_quote_name):
		return
	if (frappe.db.get_value("Sales Quote", sales_quote_name, "quotation_type") or "").strip() != "One-off":
		return
	_one_off_persist_converted(sales_quote_name, doctype, document_name)


@frappe.whitelist()
def sync_one_off_quote_status_from_links(sales_quote_name: str) -> dict:
	"""Desk: back-fill *Converted To* / *Status* from linked main jobs when missing."""
	if not sales_quote_name or not frappe.db.exists("Sales Quote", sales_quote_name):
		return {"updated": False}
	qt = (frappe.db.get_value("Sales Quote", sales_quote_name, "quotation_type") or "").strip()
	if qt != "One-off":
		return {"updated": False}
	link_cols = ["converted_to_doc"]
	if frappe.db.has_column("Sales Quote", "converted_to_doctype"):
		link_cols.extend(["converted_to_doctype", "converted_to_name"])
	row = frappe.db.get_value("Sales Quote", sales_quote_name, link_cols, as_dict=True) or {}
	current = _sq_strip_or_none(row.get("converted_to_doc"))
	if current:
		normalized = normalize_one_off_converted_to_ref(
			current,
			row.get("converted_to_doctype"),
			row.get("converted_to_name"),
		)
		if normalized and normalized != current:
			_one_off_persist_converted_from_ref(sales_quote_name, normalized)
			return {"updated": True, "converted_to_doc": normalized, "status": "Converted"}
		return {"updated": False}
	inferred = _infer_one_off_converted_ref_from_links(sales_quote_name)
	if not inferred:
		return {"updated": False}
	_one_off_persist_converted_from_ref(sales_quote_name, inferred)
	return {"updated": True, "converted_to_doc": inferred, "status": "Converted"}


def _infer_one_off_converted_ref_from_links(sales_quote_name: str) -> str | None:
	"""First linked main operational document for this quote (priority: customs order, then main freight/transport)."""
	linked_checks = (
		("Declaration Order", {"sales_quote": sales_quote_name}),
		("Sea Booking", {"sales_quote": sales_quote_name, "service_role": "Main"}),
		("Air Booking", {"sales_quote": sales_quote_name, "service_role": "Main"}),
		("Transport Order", {"sales_quote": sales_quote_name, "service_role": "Main"}),
		("Warehouse Contract", {"sales_quote": sales_quote_name}),
		("Declaration", {"sales_quote": sales_quote_name, "service_role": "Main"}),
	)
	for doctype, filters in linked_checks:
		filters = {**filters, "docstatus": ["!=", 2]}
		names = frappe.get_all(doctype, filters=filters, pluck="name", limit=1)
		if names:
			return format_one_off_converted_to_ref(doctype, names[0])
	return None


def _one_off_persist_converted_from_ref(sales_quote_name: str, ref: str) -> None:
	frappe.db.sql(
		"""
		UPDATE `tabSales Quote`
		SET `status`=%(st)s,
		    `converted_to_doc`=%(ref)s
		WHERE `name`=%(nm)s
		""",
		{"st": "Converted", "ref": ref, "nm": sales_quote_name},
	)
	frappe.clear_document_cache("Sales Quote", sales_quote_name)


def _one_off_persist_converted(sales_quote_name: str, doctype: str, document_name: str) -> None:
	"""Set status + Converted To. ``converted_to_doc`` stores ``{Doctype} {name}`` for desk display."""
	doc_name = (document_name or "").strip()
	dt = (doctype or "").strip()
	ref = format_one_off_converted_to_ref(dt, doc_name)

	frappe.db.sql(
		"""
		UPDATE `tabSales Quote`
		SET `status`=%(st)s,
		    `converted_to_doc`=%(ref)s
		WHERE `name`=%(nm)s
		""",
		{"st": "Converted", "ref": ref, "nm": sales_quote_name},
	)

	if frappe.db.has_column("Sales Quote", "converted_to_doctype"):
		frappe.db.sql(
			"""
			UPDATE `tabSales Quote`
			SET `converted_to_doctype`=%(cdt)s
			WHERE `name`=%(nm)s
			""",
			{"cdt": dt or None, "nm": sales_quote_name},
		)
	if frappe.db.has_column("Sales Quote", "converted_to_name"):
		frappe.db.sql(
			"""
			UPDATE `tabSales Quote`
			SET `converted_to_name`=%(cn)s
			WHERE `name`=%(nm)s
			""",
			{"cn": doc_name or None, "nm": sales_quote_name},
		)

	frappe.clear_document_cache("Sales Quote", sales_quote_name)


_ONE_OFF_CONVERSION_PRIMARY_DOCTYPES = frozenset({"Declaration Order", "Warehouse Contract"})
_ONE_OFF_FREIGHT_HUB_TYPES = frozenset({"Air Shipment", "Sea Shipment"})


def should_persist_one_off_quote_conversion_on_submit(doctype: str, document_name: str) -> bool:
	"""Only main-service primaries (or customs/warehouse primaries) own the quote conversion pointer.

	Internal-job satellites (e.g. Air Booking under a main Air Shipment) share the one-off quote but
	must not overwrite *Converted To* — otherwise later legs such as Transport Order cannot be created (#1037).
	"""
	dt = (doctype or "").strip()
	dn = (document_name or "").strip()
	if not dt or not dn:
		return True
	if dt in _ONE_OFF_CONVERSION_PRIMARY_DOCTYPES:
		return True
	if not frappe.db.exists(dt, dn):
		return True
	meta = frappe.get_meta(dt)
	if not meta.has_field("service_role"):
		return True
	return (frappe.db.get_value(dt, dn, "service_role") or "").strip() == SERVICE_ROLE_MAIN


def reset_one_off_quote_on_cancel_for_document(
	sales_quote_name: str, doctype: str, document_name: str
) -> None:
	"""Reset quote conversion only when the cancelled document owns *converted_to_doc*."""
	if not sales_quote_name:
		return
	cr = (frappe.db.get_value("Sales Quote", sales_quote_name, "converted_to_doc") or "").strip()
	if not cr:
		return
	if one_off_stored_conversion_matches(cr, doctype, document_name):
		reset_one_off_quote_on_cancel(sales_quote_name)


def resolve_freight_shipment_hub_for_one_off_chain(doc):
	"""Return ``(hub_doctype, hub_name)`` for multimodal chain checks on freight / transport satellites."""
	mjt = get_main_service_type(doc)
	mj = get_main_service_name(doc)
	if mjt in _ONE_OFF_FREIGHT_HUB_TYPES and mj:
		return mjt, mj
	air = (getattr(doc, "air_shipment", None) or "").strip()
	if air:
		return "Air Shipment", air
	sea = (getattr(doc, "sea_shipment", None) or "").strip()
	if sea:
		return "Sea Shipment", sea
	return None, None


def resolve_allow_linked_internal_job_freight_satellites_from_converted(
	sales_quote_name: str,
	hub_doctype: str | None = None,
	hub_name: str | None = None,
) -> tuple[str | None, str | None]:
	"""Allow sibling legs when *converted_to_doc* is the hub shipment or an IJ booking/shipment on that hub (#1037)."""
	sq = (sales_quote_name or "").strip()
	hub_dt = (hub_doctype or "").strip()
	hub_nm = (hub_name or "").strip()
	if not sq or hub_dt not in _ONE_OFF_FREIGHT_HUB_TYPES or not hub_nm:
		return None, None

	cr = (frappe.db.get_value("Sales Quote", sq, "converted_to_doc") or "").strip()
	if not cr:
		return None, None

	booking_dt = "Air Booking" if hub_dt == "Air Shipment" else "Sea Booking"
	link_field = "air_booking" if hub_dt == "Air Shipment" else "sea_booking"

	def _row_ok(dt: str, name: str) -> bool:
		if not name or not frappe.db.exists(dt, name):
			return False
		row = frappe.db.get_value(
			dt,
			name,
			["service_role", "main_service_type", "main_service", "sales_quote", "docstatus"],
			as_dict=True,
		)
		if not row or row.docstatus == 2:
			return False
		if (row.sales_quote or "").strip() != sq:
			return False
		if dt == hub_dt and name == hub_nm:
			return True
		if is_linked_service_satellite(row):
			return get_main_service_type(row) == hub_dt and get_main_service_name(row) == hub_nm
		return False

	def _resolve_name(prefix: str, doctype: str) -> str | None:
		tail = None
		if cr.startswith(f"{prefix} "):
			tail = cr[len(prefix) + 1 :].strip()
		elif frappe.db.exists(doctype, cr):
			tail = cr
		if tail and _row_ok(doctype, tail):
			return tail
		return None

	allow_sea = None
	allow_air = None

	if hub_dt == "Air Shipment":
		shipment_name = _resolve_name("Air Shipment", "Air Shipment")
		booking_name = _resolve_name("Air Booking", "Air Booking")
		if shipment_name:
			allow_air = (frappe.db.get_value("Air Shipment", shipment_name, link_field) or "").strip() or None
		if booking_name:
			allow_air = booking_name
	else:
		shipment_name = _resolve_name("Sea Shipment", "Sea Shipment")
		booking_name = _resolve_name("Sea Booking", "Sea Booking")
		if shipment_name:
			allow_sea = (frappe.db.get_value("Sea Shipment", shipment_name, link_field) or "").strip() or None
		if booking_name:
			allow_sea = booking_name

	return allow_sea, allow_air


def resolve_one_off_chain_freight_booking_allowances(
	doc,
	sales_quote_name: str,
	*,
	prefer_sea_booking: str | None = None,
	prefer_air_booking: str | None = None,
) -> tuple[str | None, str | None]:
	"""Return ``(allow_sea_booking, allow_air_booking)`` for multimodal one-off chain validation.

	*converted_to_doc* and internal-job satellites on the same hub take priority over hub-parent
	bookings — fixes #1037 when an IJ air booking owns conversion but the hub parent booking differs.
	"""
	sq = (sales_quote_name or "").strip()
	if not sq:
		return None, None

	allow_sea = (prefer_sea_booking or "").strip() or None
	allow_air = (prefer_air_booking or "").strip() or None

	r_sea, r_air = resolve_allow_linked_freight_bookings_for_internal_job(doc)
	if not allow_sea and r_sea:
		allow_sea = (r_sea or "").strip() or None
	if not allow_air and r_air:
		allow_air = (r_air or "").strip() or None

	if not allow_sea:
		allow_sea = resolve_single_main_sea_booking_for_sales_quote(sq)
	if not allow_air:
		allow_air = resolve_single_main_air_booking_for_sales_quote(sq)

	conv_sea, conv_air = resolve_allow_linked_freight_booking_from_one_off_converted_doc(sq)
	hub_dt, hub_nm = resolve_freight_shipment_hub_for_one_off_chain(doc)
	ij_sea, ij_air = (None, None)
	if hub_dt and hub_nm:
		ij_sea, ij_air = resolve_allow_linked_internal_job_freight_satellites_from_converted(
			sq, hub_dt, hub_nm
		)

	# Converted-doc owner and IJ satellites on the hub win over hub-parent / main booking.
	if conv_sea:
		allow_sea = conv_sea
	if conv_air:
		allow_air = conv_air
	if ij_sea:
		allow_sea = ij_sea
	if ij_air:
		allow_air = ij_air

	return allow_sea, allow_air


def update_one_off_quote_on_submit(sales_quote_name: str, document_name: str, doctype: str):
	"""
	Update One-off Sales Quote *Converted To* / *Status* when a linked document is submitted.

	Same persistence as :func:`record_one_off_quote_conversion` (also used on create-from-quote).

	Lifecycle contract: Any submittable doctype that calls this on submit (and thus sets
	converted_to_doc on the Sales Quote) MUST call reset_one_off_quote_on_cancel_for_document
	in its on_cancel when the document is cancelled. If the doctype allows clearing the
	sales_quote link on save, it should in validate() (when the link is cleared) call
	reset_one_off_quote_on_cancel(original_sales_quote). Linked doctypes: Transport Order,
	Warehouse Contract, Air Booking, Sea Booking, Declaration Order, Declaration.
	
	Args:
		sales_quote_name: Name of the Sales Quote
		document_name: Name of the document that references the quote
		doctype: DocType of the referencing document
	"""
	if not sales_quote_name:
		return
	
	try:
		# Use DB reads/writes instead of get_doc + db_set so this still runs when the submitting user
		# does not have Role permission to "read" Sales Quote (get_doc would raise and fail silently).
		if not frappe.db.exists("Sales Quote", sales_quote_name):
			return
		
		qt = (frappe.db.get_value("Sales Quote", sales_quote_name, "quotation_type") or "").strip()
		if qt != "One-off":
			return

		if not should_persist_one_off_quote_conversion_on_submit(doctype, document_name):
			return
		
		record_one_off_quote_conversion(sales_quote_name, doctype, document_name)
	except Exception as e:
		frappe.log_error(
			f"Error updating One-off Sales Quote {sales_quote_name} on submit: {str(e)}",
			"One-off Quote Lifecycle Error"
		)


def reset_one_off_quote_on_cancel(sales_quote_name: str):
	"""
	Reset One-off Sales Quote status to Draft and clear converted_to_doc.

	Called in two situations: (1) when a linked document (Order/Booking/Contract/Declaration)
	is cancelled (from that doctype's on_cancel), and (2) when the user clears the
	sales_quote link on an existing document and saves (from that doctype's validate).
	See update_one_off_quote_on_submit docstring for the full lifecycle contract.
	
	Args:
		sales_quote_name: Name of the Sales Quote
	"""
	if not sales_quote_name:
		return
	
	try:
		if not frappe.db.exists("Sales Quote", sales_quote_name):
			return
		
		qt = (frappe.db.get_value("Sales Quote", sales_quote_name, "quotation_type") or "").strip()
		if qt != "One-off":
			return
		
		frappe.db.sql(
			"""
			UPDATE `tabSales Quote`
			SET `status`=%(st)s,
			    `converted_to_doc`=NULL
			WHERE `name`=%(nm)s
			""",
			{"st": "Draft", "nm": sales_quote_name},
		)
		if frappe.db.has_column("Sales Quote", "converted_to_doctype"):
			frappe.db.sql(
				"UPDATE `tabSales Quote` SET `converted_to_doctype`=NULL WHERE `name`=%(nm)s",
				{"nm": sales_quote_name},
			)
		if frappe.db.has_column("Sales Quote", "converted_to_name"):
			frappe.db.sql(
				"UPDATE `tabSales Quote` SET `converted_to_name`=NULL WHERE `name`=%(nm)s",
				{"nm": sales_quote_name},
			)
		frappe.clear_document_cache("Sales Quote", sales_quote_name)
	except Exception as e:
		frappe.log_error(
			f"Error resetting One-off Sales Quote {sales_quote_name} on cancel: {str(e)}",
			"One-off Quote Lifecycle Error"
		)


def resolve_allow_linked_freight_bookings_for_internal_job(doc):
	"""For internal-job satellites (e.g. Transport Order) sharing the main job's one-off quote, return
	Sea Booking / Air Booking names that may hold that quote on the main leg — they must not count as a
	separate consumer of the one-off.

	Uses Main Service Type + Main Service (Sea Shipment → parent Sea Booking; Air Shipment → parent Air Booking;
	Transport Job / Declaration → freight links on that job).
	"""
	if not is_linked_service_satellite(doc):
		return None, None
	mjt = get_main_service_type(doc)
	mj = get_main_service_name(doc)
	if not mj:
		return None, None
	allow_sea = None
	allow_air = None
	try:
		if mjt == "Sea Shipment":
			allow_sea = frappe.db.get_value("Sea Shipment", mj, "sea_booking")
		elif mjt == "Air Shipment":
			allow_air = frappe.db.get_value("Air Shipment", mj, "air_booking")
		elif mjt == "Transport Job":
			tj = frappe.db.get_value(
				"Transport Job",
				mj,
				["sea_shipment", "air_shipment"],
				as_dict=True,
			)
			if tj:
				if tj.get("sea_shipment"):
					allow_sea = frappe.db.get_value("Sea Shipment", tj["sea_shipment"], "sea_booking")
				if tj.get("air_shipment"):
					allow_air = frappe.db.get_value("Air Shipment", tj["air_shipment"], "air_booking")
		elif mjt == "Declaration":
			dec = frappe.db.get_value(
				"Declaration",
				mj,
				["sea_shipment", "air_shipment"],
				as_dict=True,
			)
			if dec:
				if dec.get("sea_shipment"):
					allow_sea = frappe.db.get_value("Sea Shipment", dec["sea_shipment"], "sea_booking")
				if dec.get("air_shipment"):
					allow_air = frappe.db.get_value("Air Shipment", dec["air_shipment"], "air_booking")
	except Exception:
		return None, None
	return allow_sea, allow_air


def _resolved_transport_order_name_from_one_off_conversion(converted_ref: str | None) -> str | None:
	"""Return Transport Order name if ``converted_ref`` points at one (compact id or ``Transport Order NAME``)."""
	cr = (converted_ref or "").strip()
	if not cr:
		return None
	if frappe.db.exists("Transport Order", cr):
		return cr
	if cr.startswith("Transport Order "):
		tail = cr[len("Transport Order ") :].strip()
		if tail and frappe.db.exists("Transport Order", tail):
			return tail
	return None


def _shipment_hub_for_linked_transport_order(doc):
	"""Return (hub_doctype, hub_name) when *doc* shares a one-off quote with a Transport Order on that hub."""
	dt = getattr(doc, "doctype", None) or ""
	if dt in ("Air Shipment", "Sea Shipment"):
		hub_dt = dt
		hub_name = (doc.name or "").strip()
		if is_linked_service_satellite(doc):
			mjt = get_main_service_type(doc)
			mj = get_main_service_name(doc)
			if mjt == dt and mj:
				hub_name = mj
		return hub_dt, hub_name
	if dt == "Declaration Order" and is_linked_service_satellite(doc):
		mjt = get_main_service_type(doc)
		mj = get_main_service_name(doc)
		if mjt in ("Air Shipment", "Sea Shipment") and mj:
			return mjt, mj
	return None, None


def _allow_linked_transport_order_for_shipment_hub(sales_quote_name, hub_doctype, hub_name):
	"""Return TRO name when the quote converted to a Transport Order linked to this Air/Sea Shipment hub."""
	sq = (sales_quote_name or "").strip()
	hub_dt = (hub_doctype or "").strip()
	hub_name = (hub_name or "").strip()
	if not sq or not hub_dt or not hub_name:
		return None
	cr = frappe.db.get_value("Sales Quote", sq, "converted_to_doc")
	tro_name = _resolved_transport_order_name_from_one_off_conversion(cr)
	if not tro_name:
		return None
	link_field = "air_shipment" if hub_dt == "Air Shipment" else "sea_shipment"
	tro_ship = (frappe.db.get_value("Transport Order", tro_name, link_field) or "").strip()
	if tro_ship == hub_name:
		return tro_name
	return None


def resolve_allow_linked_transport_order_for_freight_shipment(doc):
	"""If the quote is converted to a Transport Order that references this Air/Sea Shipment (or the main-job hub), return that TRO name.

	Same job chain as ``allow_linked_air_booking`` / ``allow_linked_sea_booking``: port pickup/delivery TRO shares the
	one-off quote with the linked freight shipment. Prefer :func:`resolve_allow_linked_transport_order_for_internal_job_satellite`
	for internal-job Declaration Orders and other satellites.
	"""
	hub_dt, hub_name = _shipment_hub_for_linked_transport_order(doc)
	if not hub_dt or not hub_name:
		return None
	return _allow_linked_transport_order_for_shipment_hub(
		getattr(doc, "sales_quote", None), hub_dt, hub_name
	)


def resolve_allow_linked_transport_order_for_internal_job_satellite(doc):
	"""Return Transport Order name when a one-off quote already converted to TRO is still part of this internal-job chain.

	Covers Air/Sea Shipment hubs, Declaration Order under Transport Job (TRO.main_service), and Declaration Order under
	Declaration (TRO linked via declaration's air/sea shipment).
	"""
	tro = resolve_allow_linked_transport_order_for_freight_shipment(doc)
	if tro:
		return tro

	if not is_linked_service_satellite(doc):
		return None
	sq = getattr(doc, "sales_quote", None)
	if not sq:
		return None
	mjt = get_main_service_type(doc)
	mj = get_main_service_name(doc)
	if not mjt or not mj:
		return None

	cr = frappe.db.get_value("Sales Quote", sq, "converted_to_doc")
	tro_name = _resolved_transport_order_name_from_one_off_conversion(cr)
	if not tro_name:
		return None

	if mjt == "Transport Job":
		tro_row = frappe.db.get_value(
			"Transport Order", tro_name, ["main_service_type", "main_service"], as_dict=True
		)
		if (
			tro_row
			and get_main_service_type(tro_row) == "Transport Job"
			and get_main_service_name(tro_row) == mj
		):
			return tro_name

	if mjt == "Declaration" and frappe.db.exists("Declaration", mj):
		dec = frappe.db.get_value(
			"Declaration", mj, ["sea_shipment", "air_shipment"], as_dict=True
		) or {}
		for hub_dt, hub_name in (
			("Air Shipment", (dec.get("air_shipment") or "").strip()),
			("Sea Shipment", (dec.get("sea_shipment") or "").strip()),
		):
			if hub_name:
				linked = _allow_linked_transport_order_for_shipment_hub(sq, hub_dt, hub_name)
				if linked:
					return linked

	return None


def resolve_allow_linked_transport_order_for_internal_job_freight_booking(doc):
	"""For internal-job Air/Sea Bookings whose hub is an Air/Sea Shipment, return the Transport Order name when
	the one-off quote was converted to that order and the order links to the same hub shipment — mirrors
	``resolve_allow_linked_transport_order_for_freight_shipment`` for shipment rows."""
	if not is_linked_service_satellite(doc):
		return None
	dt = getattr(doc, "doctype", None) or ""
	if dt not in ("Air Booking", "Sea Booking"):
		return None
	mjt = get_main_service_type(doc)
	mj = get_main_service_name(doc)
	if mjt not in ("Air Shipment", "Sea Shipment") or not mj:
		return None
	sq = getattr(doc, "sales_quote", None)
	if not sq:
		return None
	cr = frappe.db.get_value("Sales Quote", sq, "converted_to_doc")
	tro_name = _resolved_transport_order_name_from_one_off_conversion(cr)
	if not tro_name:
		return None
	link_field = "air_shipment" if mjt == "Air Shipment" else "sea_shipment"
	tro_ship = frappe.db.get_value("Transport Order", tro_name, link_field)
	if tro_ship and (tro_ship or "").strip() == mj.strip():
		return tro_name
	return None


def resolve_single_main_sea_booking_for_sales_quote(sales_quote_name):
	"""If exactly one non-cancelled main Sea Booking references this Sales Quote, return its name.

	Used when a Sea Shipment carries the quote but ``sea_booking`` is not set yet.
	"""
	if not sales_quote_name:
		return None
	cand = frappe.get_all(
		"Sea Booking",
		filters={
			"docstatus": ["!=", 2],
			"service_role": "Main",
			"sales_quote": sales_quote_name,
		},
		pluck="name",
		limit=2,
	)
	return cand[0] if len(cand) == 1 else None


def resolve_single_main_air_booking_for_sales_quote(sales_quote_name):
	"""If exactly one non-cancelled main Air Booking references this Sales Quote, return its name."""
	if not sales_quote_name:
		return None
	cand = frappe.get_all(
		"Air Booking",
		filters={
			"docstatus": ["!=", 2],
			"service_role": "Main",
			"sales_quote": sales_quote_name,
		},
		pluck="name",
		limit=2,
	)
	return cand[0] if len(cand) == 1 else None


def resolve_allow_linked_freight_booking_from_one_off_converted_doc(sales_quote_name: str):
	"""Return ``(sea_booking_name_or_none, air_booking_name_or_none)`` from the quote's ``converted_to_doc``.

	When :func:`resolve_single_main_sea_booking_for_sales_quote` / air returns *None* (no ``service_role=Main`` match,
	multiple mains, etc.) but submit already recorded conversion on a specific Sea/Air Booking that still links this
	quote, that booking must be accepted as the linked leg — same idea as ``allow_if_quote_converted_to`` for Declaration Order.
	"""
	if not sales_quote_name:
		return None, None
	cr = (frappe.db.get_value("Sales Quote", sales_quote_name, "converted_to_doc") or "").strip()
	if not cr:
		return None, None
	sq_key = (sales_quote_name or "").strip()

	def _booking_if_same_quote(doctype: str, prefix: str) -> str | None:
		tail = cr[len(prefix) + 1 :].strip() if cr.startswith(f"{prefix} ") else cr
		if not tail or not frappe.db.exists(doctype, tail):
			return None
		row = frappe.db.get_value(doctype, tail, ["sales_quote", "docstatus"], as_dict=True)
		if not row or row.docstatus == 2:
			return None
		if (row.sales_quote or "").strip() != sq_key:
			return None
		return tail

	allow_sea = _booking_if_same_quote("Sea Booking", "Sea Booking")
	allow_air = _booking_if_same_quote("Air Booking", "Air Booking")
	return allow_sea, allow_air


def resolve_one_off_declaration_order_chain_allowance(doc, allow_sea=None, allow_air=None):
	"""Return flags for :func:`validate_one_off_quote_not_converted` on freight bookings and shipments.

	Internal-job Air/Sea Bookings and Shipments linked to a Sea/Air Shipment (or Declaration /
	Declaration Order) may share a one-off quote already converted to a Declaration Order on the customs
	leg — same multimodal chain as Transport Order satellites.
	"""
	if is_main_service_doc(doc):
		return True, None

	is_internal = is_linked_service_satellite(doc)
	if not is_internal:
		return False, None

	main_job_type = get_main_service_type(doc)
	main_job = get_main_service_name(doc)
	linked_declaration_order = None
	if main_job_type == "Declaration Order" and main_job and frappe.db.exists("Declaration Order", main_job):
		linked_declaration_order = main_job
	elif main_job_type == "Declaration" and main_job:
		try:
			linked_declaration_order = (
				frappe.db.get_value("Declaration", main_job, "declaration_order") or None
			)
		except Exception:
			linked_declaration_order = None

	allow = bool(allow_sea) or bool(allow_air) or bool(linked_declaration_order)
	if not allow and main_job_type in ("Sea Shipment", "Air Shipment") and main_job:
		sq = (getattr(doc, "sales_quote", None) or "").strip()
		if sq:
			try:
				hub_sq = (frappe.db.get_value(main_job_type, main_job, "sales_quote") or "").strip()
				if hub_sq == sq:
					cr = (frappe.db.get_value("Sales Quote", sq, "converted_to_doc") or "").strip()
					if cr and (
						cr.startswith("Declaration Order ")
						or frappe.db.exists("Declaration Order", cr)
					):
						allow = True
						if not linked_declaration_order:
							linked_declaration_order = (
								cr[len("Declaration Order ") :].strip()
								if cr.startswith("Declaration Order ")
								else cr
							)
			except Exception:
				pass

	return allow, linked_declaration_order


# Main-service ops docs allowed to share a one-off quote already converted to a Declaration Order (same job chain).
_DOCTYPES_MAIN_SERVICE_WITH_DECLARATION_ORDER_CONVERSION = frozenset(
	(
		"Transport Order",
		"Sea Shipment",
		"Air Shipment",
		"Sea Booking",
		"Air Booking",
	)
)


def validate_one_off_quote_not_converted(
	sales_quote_name: str,
	current_doctype: str = None,
	current_docname: str = None,
	allow_if_quote_converted_to: str = None,
	allow_linked_sea_booking: str = None,
	allow_linked_air_booking: str = None,
	allow_linked_transport_order: str = None,
	allow_main_transport_if_converted_to_declaration_order: bool = False,
):
	"""
	Validate that One-off Sales Quote is not already converted or linked to another document.
	Raises exception if converted or already in use.
	
	Args:
		sales_quote_name: Name of the Sales Quote
		current_doctype: Doctype of the current document (to exclude from check)
		current_docname: Name of the current document (to exclude from check)
		allow_if_quote_converted_to: If the quote was converted to this doc ref (e.g. "Declaration Order DCO-001"),
			allow use — used when the current document is the next step in the same chain (e.g. Declaration from that Order).
		allow_linked_sea_booking: Sea Booking name that may hold the same quote as this doc (e.g. Sea Shipment's parent booking, or main Sea leg for an internal-job Transport Order).
		allow_linked_air_booking: Air Booking name for the same job chain (e.g. Air Shipment's parent booking).
		allow_linked_transport_order: Transport Order name when the quote converted to that order and it links to this
			Air/Sea Shipment via ``air_shipment`` / ``sea_shipment`` (same chain as pickup/delivery leg).
		allow_main_transport_if_converted_to_declaration_order: If True and current doc is a main-service Transport Order,
			Sea/Air Shipment, or Sea/Air Booking, allow when the quote is already marked converted to a Declaration Order
			(customs leg submitted first; freight main leg is part of the same job chain). For Transport Order, this
			may also be True for an internal-job order when it is tied to the same chain (caller passes True only if
			linked Sea/Air booking resolution succeeded).
		
	Raises:
		frappe.ValidationError: If quote is already converted or linked to another document
	"""
	if not sales_quote_name:
		return
	
	try:
		# Get the Sales Quote
		sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
		
		# Only validate if it's a One-off quote
		if sales_quote.quotation_type != "One-off":
			return
		
		# Check if already converted (but allow if converted to *this* document — e.g. re-saving the same order)
		if sales_quote.status == "Converted" or sales_quote.converted_to_doc:
			converted_ref = (sales_quote.converted_to_doc or "").strip()
			if current_doctype and current_docname and one_off_stored_conversion_matches(
				converted_ref, current_doctype, current_docname
			):
				return  # Same document that converted the quote — allow save
			# Same conversion chain: e.g. quote was converted to Declaration Order X, current doc is Declaration from that Order
			if allow_if_quote_converted_to and converted_ref:
				ac = allow_if_quote_converted_to.strip()
				if converted_ref == ac:
					return
				ac_parts = ac.split(None, 1)
				if len(ac_parts) == 2 and one_off_stored_conversion_matches(converted_ref, ac_parts[0], ac_parts[1]):
					return
			# Main freight/transport leg alongside a submitted Declaration Order (one-off quote covers customs + freight)
			if (
				allow_main_transport_if_converted_to_declaration_order
				and (current_doctype or "") in _DOCTYPES_MAIN_SERVICE_WITH_DECLARATION_ORDER_CONVERSION
				and converted_ref
				and (
					converted_ref.startswith("Declaration Order ")
					or frappe.db.exists("Declaration Order", converted_ref)
				)
			):
				return
			# Quote converted to Air/Sea Booking; current doc is the shipment (or other child) for that same booking
			if allow_linked_air_booking and one_off_stored_conversion_matches(
				converted_ref, "Air Booking", allow_linked_air_booking
			):
				return
			if allow_linked_sea_booking and one_off_stored_conversion_matches(
				converted_ref, "Sea Booking", allow_linked_sea_booking
			):
				return
			# Quote converted to Transport Order; current doc is the linked Air/Sea Shipment (or internal-job satellite of that hub)
			if allow_linked_transport_order and one_off_stored_conversion_matches(
				converted_ref, "Transport Order", allow_linked_transport_order
			):
				return
			converted_info = sales_quote.converted_to_doc or _("Unknown document")
			frappe.throw(
				_("One-off Sales Quote '{0}' has already been converted ({1}) and cannot be used with another document.").format(
					sales_quote_name,
					converted_info
				),
				title=_("Quote Already Converted")
			)
		
		# Check if already linked to another document (even if not yet converted)
		# This prevents the same quote from being used in multiple documents
		linked_documents = []
		
		# Check Air Booking — main-service bookings "consume" the one-off link.
		air_bookings = frappe.get_all(
			"Air Booking",
			filters={
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2],  # Exclude cancelled documents
				"service_role": "Main",
				"sales_quote": sales_quote_name,
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if air_bookings:
			abn = (air_bookings[0].name or "").strip()
			if allow_linked_air_booking and abn == (allow_linked_air_booking or "").strip():
				pass  # Same quote on parent booking + shipment is one job chain
			else:
				linked_documents.append(f"Air Booking: {abn}")
		
		# Check Sea Booking — main-service bookings "consume" the one-off link.
		sea_bookings = frappe.get_all(
			"Sea Booking",
			filters={
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2],  # Exclude cancelled documents
				"service_role": "Main",
				"sales_quote": sales_quote_name,
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if sea_bookings:
			sbn = (sea_bookings[0].name or "").strip()
			if allow_linked_sea_booking and sbn == (allow_linked_sea_booking or "").strip():
				pass  # Same quote on parent booking + shipment is one job chain
			else:
				linked_documents.append(f"Sea Booking: {sbn}")
		
		# Check Transport Order (main service only — same one-off exclusivity rule as freight bookings)
		transport_orders = frappe.get_all(
			"Transport Order",
			filters={
				"sales_quote": sales_quote_name,
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2],  # Exclude cancelled documents
				"service_role": "Main",
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if transport_orders:
			ton = (transport_orders[0].name or "").strip()
			if allow_linked_transport_order and ton == (allow_linked_transport_order or "").strip():
				pass
			else:
				linked_documents.append(f"Transport Order: {ton}")
		
		# Check Warehouse Contract
		warehouse_contracts = frappe.get_all(
			"Warehouse Contract",
			filters={
				"sales_quote": sales_quote_name,
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2]  # Exclude cancelled documents
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if warehouse_contracts:
			linked_documents.append(f"Warehouse Contract: {warehouse_contracts[0].name}")
		
		# Check Declaration (main service only)
		declarations = frappe.get_all(
			"Declaration",
			filters={
				"sales_quote": sales_quote_name,
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2],  # Exclude cancelled documents
				"service_role": "Main",
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if declarations:
			linked_documents.append(f"Declaration: {declarations[0].name}")
		
		# If quote is already linked to another document, throw error
		if linked_documents:
			doc_list = ", ".join(linked_documents)
			frappe.throw(
				_("One-off Sales Quote '{0}' is already linked to another document ({1}) and cannot be used again. Each One-off quote can only be used once.").format(
					sales_quote_name,
					doc_list
				),
				title=_("Quote Already In Use")
			)
		
	except frappe.DoesNotExistError:
		# Sales Quote doesn't exist, skip validation
		pass
	except frappe.ValidationError:
		# Re-raise validation errors
		raise
	except Exception as e:
		frappe.log_error(
			f"Error validating One-off Sales Quote {sales_quote_name}: {str(e)}",
			"One-off Quote Validation Error"
		)


@frappe.whitelist()
def copy_quotation_services_from_duplicate_source(sales_quote_name: str):
	"""Clone Linked Services from the duplicate source quote onto this draft Sales Quote."""
	if not sales_quote_name:
		frappe.throw(_("Sales Quote is required."))
	frappe.has_permission("Sales Quote", "write", doc=sales_quote_name, throw=True)

	target = frappe.get_doc("Sales Quote", sales_quote_name)
	if target.docstatus != 0:
		frappe.throw(_("Copy Quotation Services is only available on draft Sales Quotes."))
	if cint(getattr(target, "additional_charge", 0)):
		frappe.throw(_("Copy Quotation Services is not available on additional-charge quotes."))

	source_name = (getattr(target, "logistics_duplicate_from", None) or "").strip()
	if not source_name:
		frappe.throw(
			_("This Sales Quote was not created by duplicating another quote."),
			title=_("No Duplicate Source"),
		)
	if not frappe.db.exists("Sales Quote", source_name):
		frappe.throw(
			_("Source Sales Quote {0} was not found.").format(frappe.bold(source_name)),
			title=_("Source Not Found"),
		)

	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_sales_quote,
	)

	if get_linked_services_for_sales_quote(sales_quote_name):
		frappe.throw(
			_("This Sales Quote already has services. Remove them before copying again."),
			title=_("Services Already Exist"),
		)

	source_services = get_linked_services_for_sales_quote(source_name)
	if not source_services:
		frappe.throw(
			_("Source Sales Quote {0} has no services to copy.").format(frappe.bold(source_name)),
			title=_("No Services To Copy"),
		)

	mapping = _clone_sales_quote_linked_services(source_name, target.name)
	_remap_sales_quote_charges_from_duplicate_source(target, source_name, mapping)

	target.logistics_duplicate_from = None
	target.flags._linked_services_copy_applied = True
	target.flags.ignore_mandatory = True
	target.save(ignore_permissions=True)

	return {
		"success": True,
		"copied_count": len(mapping),
		"mapping": mapping,
		"message": _("Copied {0} service(s) from {1}.").format(len(mapping), source_name),
	}


def _clone_sales_quote_linked_services(source_sq_name: str, target_sq_name: str) -> dict[str, str]:
	"""Clone source-quote Linked Services onto *target_sq_name*; return ``{source_ls: target_ls}``."""
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_sales_quote,
	)
	from logistics.utils.internal_job_persistence import create_internal_job_for_parent_from_source

	mapping: dict[str, str] = {}
	for source_ls in get_linked_services_for_sales_quote(source_sq_name):
		new_name = create_internal_job_for_parent_from_source(
			"Sales Quote", target_sq_name, source_ls
		)
		mapping[source_ls.name] = new_name
	return mapping


def _remap_sales_quote_charges_from_duplicate_source(
	target_sq: Document, source_sq_name: str, ls_mapping: dict[str, str]
) -> None:
	"""Restore Linked charge scope/links on *target_sq* from the duplicate source quote."""
	if not ls_mapping:
		return
	from logistics.utils.linked_service_compat import (
		CHARGE_SCOPE_LINKED,
		charge_row_linked_service_link,
		normalize_charge_scope,
		set_charge_row_linked_service_link,
	)

	source_sq = frappe.get_doc("Sales Quote", source_sq_name)
	source_by_idx = {int(r.idx): r for r in (source_sq.charges or []) if r.idx}
	for row in target_sq.charges or []:
		idx = int(getattr(row, "idx", 0) or 0)
		if not idx:
			continue
		source_row = source_by_idx.get(idx)
		if not source_row:
			continue
		if normalize_charge_scope(getattr(source_row, "charge_scope", None)) != CHARGE_SCOPE_LINKED:
			continue
		source_ls = charge_row_linked_service_link(source_row)
		target_ls = ls_mapping.get(source_ls or "")
		if not target_ls:
			continue
		set_charge_row_linked_service_link(row, target_ls)
		row.charge_scope = CHARGE_SCOPE_LINKED


@frappe.whitelist()
def extend_sales_quote_validity(sales_quote, valid_until):
	"""
	Extend Sales Quote Valid Until. Draft quotes are saved; submitted quotes get a direct DB update
	so the field can change without amending the full document.
	"""
	if not sales_quote:
		frappe.throw(_("Sales Quote is required."))
	frappe.has_permission("Sales Quote", "write", doc=sales_quote, throw=True)

	doc = frappe.get_doc("Sales Quote", sales_quote)
	if doc.docstatus == 2:
		frappe.throw(_("Cannot extend validity of a cancelled Sales Quote."))

	new_vu = getdate(valid_until)
	today_d = getdate(today())
	if new_vu < today_d:
		frappe.throw(_("New Valid Until cannot be before today."), title=_("Invalid Date"))

	old_vu = getattr(doc, "valid_until", None)
	if old_vu:
		old_d = getdate(old_vu)
		if new_vu <= old_d:
			frappe.throw(
				_("New Valid Until must be after the current Valid Until ({0}).").format(format_date(old_d)),
				title=_("Invalid Extension"),
			)

	if doc.docstatus == 0:
		doc.valid_until = new_vu
		doc.save()
	else:
		frappe.db.set_value("Sales Quote", doc.name, "valid_until", new_vu, update_modified=True)

	return {
		"success": True,
		"valid_until": str(new_vu),
		"message": _("Valid Until extended to {0}.").format(format_date(new_vu)),
	}


@frappe.whitelist()
def recalculate_charges(docname):
	"""Recalculate all charges in Sales Quote charges table using RateCalculationEngine."""
	doc = frappe.get_doc("Sales Quote", docname)
	lines_recalculated = 0

	for row in doc.charges or []:
		if hasattr(row, "calculate_quantities"):
			row.calculate_quantities()
		if hasattr(row, "calculate_estimated_revenue"):
			row.calculate_estimated_revenue()
		if hasattr(row, "calculate_estimated_cost"):
			row.calculate_estimated_cost()
		lines_recalculated += 1

	doc.save()
	return {
		"success": True,
		"message": _("Successfully recalculated {0} charge line(s)").format(lines_recalculated),
		"lines_recalculated": lines_recalculated,
	}


@frappe.whitelist()
def get_cost_sheet_charges_for_selection(
	sales_quote,
	cost_sheet=None,
	service_type=None,
	charge_group=None,
	origin_port=None,
	destination_port=None,
	load_type=None,
	transport_mode=None,
):
	"""
	Return Cost Sheet charges for user selection, filtered by charge parameters.
	Cost Sheet is optional; when omitted, queries across all submitted Cost Sheets.
	"""
	if not sales_quote:
		frappe.throw(_("Sales Quote is required."))

	# Build filters for Cost Sheet Charge
	filters = [["parenttype", "=", "Cost Sheet"]]
	if cost_sheet:
		filters.append(["parent", "=", cost_sheet])
	else:
		# Only submitted Cost Sheets
		submitted = frappe.get_all("Cost Sheet", filters={"docstatus": 1}, pluck="name")
		if not submitted:
			return {"charges": []}
		filters.append(["parent", "in", submitted])

	if service_type:
		filters.append(["service_type", "=", service_type])
	if charge_group:
		filters.append(["charge_group", "=", charge_group])
	if origin_port:
		filters.append(["origin_port", "=", origin_port])
	if destination_port:
		filters.append(["destination_port", "=", destination_port])
	if load_type:
		filters.append(["load_type", "=", load_type])
	if transport_mode:
		filters.append(["transport_mode", "=", transport_mode])

	rows = frappe.get_all(
		"Cost Sheet Charge",
		filters=filters,
		fields=["name", "parent", "item_code", "item_name", "service_type", "charge_group", "charge_category",
			"unit_cost", "cost_currency", "cost_calculation_method", "cost_unit_type", "cost_minimum_quantity",
			"cost_minimum_charge", "cost_maximum_charge", "cost_base_amount", "cost_uom",
			"origin_port", "destination_port", "load_type", "transport_mode", "direction",
			"airline", "freight_agent", "shipping_line", "freight_agent_sea",
			"vehicle_type", "container_type", "location_type", "location_from", "location_to",
			"customs_authority", "declaration_type", "customs_broker", "pay_to"]
	)

	# Get Cost Sheet header details for each unique parent
	cs_names = list({r.get("parent") for r in rows if r.get("parent")})
	cs_headers = {}
	if cs_names:
		for cs in frappe.get_all(
			"Cost Sheet",
			filters={"name": ["in", cs_names]},
			fields=["name", "provider_type", "provider_name", "valid_from", "valid_to", "currency", "description"]
		):
			cs_headers[cs["name"]] = cs

	charges = []
	for idx, row in enumerate(rows):
		if not row.get("item_code") or not row.get("service_type"):
			continue
		parent = row.get("parent")
		cs_header = cs_headers.get(parent) or {}
		cs_currency = row.get("cost_currency") or (cs_header.get("currency") if cs_header else None)
		charges.append({
			"name": row.get("name"),
			"cost_sheet": parent,
			"provider_type": cs_header.get("provider_type"),
			"provider_name": cs_header.get("provider_name"),
			"valid_from": cs_header.get("valid_from"),
			"valid_to": cs_header.get("valid_to"),
			"cost_sheet_description": cs_header.get("description"),
			"idx": idx + 1,
			"item_code": row.get("item_code"),
			"item_name": row.get("item_name"),
			"service_type": row.get("service_type"),
			"charge_group": row.get("charge_group") or "",
			"charge_category": row.get("charge_category") or "",
			"unit_cost": flt(row.get("unit_cost")),
			"cost_currency": cs_currency,
			"cost_calculation_method": row.get("cost_calculation_method"),
			"cost_unit_type": row.get("cost_unit_type"),
			"cost_minimum_quantity": row.get("cost_minimum_quantity"),
			"cost_minimum_charge": row.get("cost_minimum_charge"),
			"cost_maximum_charge": row.get("cost_maximum_charge"),
			"cost_base_amount": row.get("cost_base_amount"),
			"cost_uom": row.get("cost_uom"),
			"origin_port": row.get("origin_port"),
			"destination_port": row.get("destination_port"),
			"load_type": row.get("load_type"),
			"transport_mode": row.get("transport_mode"),
			"direction": row.get("direction"),
			"airline": row.get("airline"),
			"freight_agent": row.get("freight_agent"),
			"shipping_line": row.get("shipping_line"),
			"freight_agent_sea": row.get("freight_agent_sea"),
			"vehicle_type": row.get("vehicle_type"),
			"container_type": row.get("container_type"),
			"location_type": row.get("location_type"),
			"location_from": row.get("location_from"),
			"location_to": row.get("location_to"),
			"customs_authority": row.get("customs_authority"),
			"declaration_type": row.get("declaration_type"),
			"customs_broker": row.get("customs_broker"),
			"pay_to": row.get("pay_to"),
		})
	return {"charges": charges}


@frappe.whitelist()
def get_rates_from_cost_sheet(sales_quote, selected_charge_names=None):
	"""
	Populate cost fields in Sales Quote charges from selected Cost Sheet charges.
	selected_charge_names: list of Cost Sheet Charge docnames to fetch. Each charge's parent is the Cost Sheet.
	"""
	if not sales_quote:
		frappe.throw(_("Sales Quote is required."))
	if not selected_charge_names:
		frappe.throw(_("Please select at least one charge to fetch."))

	if isinstance(selected_charge_names, str):
		selected_charge_names = frappe.parse_json(selected_charge_names)
	if not selected_charge_names:
		frappe.throw(_("Please select at least one charge to fetch."))

	sq_doc = frappe.get_doc("Sales Quote", sales_quote)
	selected = set(selected_charge_names)

	# Load selected Cost Sheet Charge rows (each has parent = Cost Sheet)
	rows = frappe.get_all(
		"Cost Sheet Charge",
		filters={"name": ["in", list(selected)]},
		fields=["name", "parent", "item_code", "item_name", "service_type", "charge_group", "charge_category",
			"cost_calculation_method", "unit_cost", "cost_unit_type", "cost_currency", "cost_minimum_quantity",
			"cost_minimum_charge", "cost_maximum_charge", "cost_base_amount", "cost_uom",
			"origin_port", "destination_port", "load_type", "transport_mode", "direction",
			"airline", "freight_agent", "shipping_line", "freight_agent_sea",
			"vehicle_type", "container_type", "location_type", "location_from", "location_to",
			"customs_authority", "declaration_type", "customs_broker", "pay_to"]
	)

	# Get Cost Sheet currency for rows missing cost_currency
	cs_currencies = {}
	for row in rows:
		cs = row.get("parent")
		if cs and cs not in cs_currencies:
			cs_currencies[cs] = frappe.db.get_value("Cost Sheet", cs, "currency")

	# Add each selected charge as a new row (do not update existing)
	added = 0
	for cs_row in rows:
		item = cs_row.get("item_code")
		svc = cs_row.get("service_type")
		if not item or not svc:
			continue
		cs_currency = cs_currencies.get(cs_row.get("parent"))
		new_row = sq_doc.append("charges", {
			"service_type": svc,
			"charge_group": cs_row.get("charge_group"),
			"item_code": item,
			"charge_category": cs_row.get("charge_category"),
			"charge_type": "Cost",
			"cost_calculation_method": cs_row.get("cost_calculation_method"),
			"unit_cost": flt(cs_row.get("unit_cost")),
			"cost_unit_type": cs_row.get("cost_unit_type"),
			"cost_currency": cs_row.get("cost_currency") or cs_currency,
			"cost_minimum_quantity": flt(cs_row.get("cost_minimum_quantity")),
			"cost_minimum_charge": flt(cs_row.get("cost_minimum_charge")),
			"cost_maximum_charge": flt(cs_row.get("cost_maximum_charge")),
			"cost_base_amount": flt(cs_row.get("cost_base_amount")),
			"cost_uom": cs_row.get("cost_uom"),
			"cost_sheet_source": cs_row.get("parent"),
		})
		added += 1

	sq_doc.save()
	msg = _("Added {0} charge line(s) from Cost Sheet.").format(added)
	return {
		"success": True,
		"message": msg,
		"added": added,
	}
