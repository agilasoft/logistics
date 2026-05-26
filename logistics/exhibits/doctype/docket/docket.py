# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Docket(Document):
	def validate(self):
		self._ensure_org_defaults()
		self._validate_exhibitor_is_participant()
		self._sync_exhibitor_metadata()
		self.validate_accounts()
		self._sync_charges()

	def after_insert(self):
		self._backfill_participant_docket_link()

	def on_update(self):
		# Keep the parent Exhibit Docket row's `docket` field in sync.
		self._backfill_participant_docket_link()

	def on_trash(self):
		"""Clear the `docket` field on any Exhibit Docket rows that point at this Docket."""
		if not self.exhibit:
			return
		try:
			rows = frappe.get_all(
				"Exhibit Docket",
				filters={
					"parent": self.exhibit,
					"parenttype": "Exhibit",
					"parentfield": "dockets",
					"docket": self.name,
				},
				pluck="name",
			)
		except Exception:
			rows = []
		for row in rows:
			try:
				frappe.db.set_value("Exhibit Docket", row, "docket", "", update_modified=False)
			except Exception:
				frappe.log_error(
					title="Docket on_trash: clear exhibit_docket.docket failed",
					message=frappe.get_traceback(),
				)

	def _backfill_participant_docket_link(self):
		"""Find the matching Exhibit Docket row (same exhibit + customer) and write our name
		into its `docket` field, so the grid on the Exhibit form shows the link."""
		if not self.exhibit or not self.exhibitor:
			return
		try:
			meta = frappe.get_meta("Exhibit Docket")
			if not meta.has_field("docket"):
				return
		except Exception:
			return
		try:
			rows = frappe.get_all(
				"Exhibit Docket",
				filters={
					"parent": self.exhibit,
					"parenttype": "Exhibit",
					"parentfield": "dockets",
					"customer": self.exhibitor,
				},
				fields=["name", "docket"],
				limit=5,
			)
		except Exception:
			rows = []
		for row in rows:
			if (row.get("docket") or "") == self.name:
				continue
			try:
				frappe.db.set_value(
					"Exhibit Docket", row["name"], "docket", self.name, update_modified=False
				)
			except Exception:
				frappe.log_error(
					title="Docket backfill: set exhibit_docket.docket failed",
					message=frappe.get_traceback(),
				)

	def _validate_exhibitor_is_participant(self):
		"""The selected exhibitor Customer must be listed on the parent Exhibit's Dockets table.
		Skipped during migrations / imports so historical data can be loaded."""
		if getattr(frappe.flags, "in_import", False) or getattr(frappe.flags, "in_migrate", False):
			return
		if not self.exhibit or not self.exhibitor:
			return
		rows = frappe.get_all(
			"Exhibit Docket",
			filters={
				"parent": self.exhibit,
				"parenttype": "Exhibit",
				"parentfield": "dockets",
				"customer": self.exhibitor,
			},
			fields=["name", "booth_no"],
			limit=1,
		)
		if not rows:
			frappe.throw(
				_(
					"Customer {0} is not listed as an Exhibitor on Exhibit {1}. "
					"Add the customer under the Exhibit's <b>Dockets</b> table "
					"before creating a Docket."
				).format(frappe.bold(self.exhibitor), frappe.bold(self.exhibit))
			)

	def _sync_exhibitor_metadata(self):
		"""Auto-fill exhibitor_name / exhibitor_code / booth_no from the exhibitor Customer
		and the matching Exhibit Docket row when blank."""
		if self.exhibitor:
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
		if self.exhibit and self.exhibitor and not self.booth_no:
			booth = frappe.db.get_value(
				"Exhibit Docket",
				{
					"parent": self.exhibit,
					"parenttype": "Exhibit",
					"parentfield": "dockets",
					"customer": self.exhibitor,
				},
				"booth_no",
			)
			if booth:
				self.booth_no = booth

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
		"""Default company / branch / cost center / profit center from the parent Exhibit when blank."""
		if not self.exhibit:
			return
		sp = frappe.db.get_value(
			"Exhibit",
			self.exhibit,
			["company", "cost_center", "branch", "profit_center"],
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
@frappe.validate_and_sanitize_search_inputs
def get_exhibitor_options_query(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for Docket.exhibitor — restricts to Customers that are listed on
	the given Exhibit's Dockets table (passed via ``filters['exhibit']``)."""
	exhibit = (filters or {}).get("exhibit")
	if not exhibit:
		return []
	conditions = [
		"ep.parent = %(exhibit)s",
		"ep.parenttype = 'Exhibit'",
		"ep.parentfield = 'dockets'",
		"ep.customer IS NOT NULL",
		"ep.customer != ''",
	]
	params = {"exhibit": exhibit, "txt": f"%{txt or ''}%", "start": start, "page_len": page_len}
	if txt:
		conditions.append("(ep.customer LIKE %(txt)s OR c.customer_name LIKE %(txt)s)")
	where_sql = " AND ".join(conditions)
	return frappe.db.sql(
		f"""
		SELECT DISTINCT ep.customer, c.customer_name, ep.booth_no
		FROM `tabExhibit Docket` ep
		LEFT JOIN `tabCustomer` c ON c.name = ep.customer
		WHERE {where_sql}
		ORDER BY ep.idx ASC, ep.customer ASC
		LIMIT %(start)s, %(page_len)s
		""",
		params,
		as_list=True,
	)
