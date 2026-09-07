# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime, today


class AirShipmentIATATransaction(Document):
	def before_insert(self):
		if not self.naming_series:
			self.naming_series = "ASIATA-.#########"

	def validate(self):
		self.validate_casslink()
		self.validate_tact()
		self.validate_eawb()

	def validate_casslink(self):
		if self.cass_settlement_status and self.cass_settlement_status != "Pending":
			if not self.cass_participant_code:
				frappe.msgprint(
					_("CASS participant code should be set when settlement status is not 'Pending'."),
					indicator="blue",
					title=_("CASSLink Information"),
				)
			if self.cass_settlement_status == "Settled":
				if not self.cass_settlement_date:
					frappe.msgprint(
						_("CASS settlement date should be set when status is 'Settled'."),
						indicator="blue",
						title=_("CASSLink Information"),
					)
		if self.cass_settlement_amount and flt(self.cass_settlement_amount) < 0:
			frappe.throw(_("CASS settlement amount cannot be negative"), title=_("Validation Error"))

	def validate_tact(self):
		if self.tact_rate_lookup:
			if not self.tact_rate_reference:
				frappe.msgprint(
					_("TACT rate reference should be set when TACT rate lookup is enabled."),
					indicator="blue",
					title=_("TACT Information"),
				)
			if self.tact_rate_validity:
				if getdate(self.tact_rate_validity) < today():
					frappe.msgprint(
						_("TACT rate validity date is in the past. Rate may no longer be valid."),
						indicator="orange",
						title=_("TACT Rate Warning"),
					)
		if self.tact_rate_amount and flt(self.tact_rate_amount) <= 0:
			frappe.throw(_("TACT rate amount must be greater than zero"), title=_("Validation Error"))

	def validate_eawb(self):
		if not self.eawb_enabled:
			return
		if self.eawb_status:
			if self.eawb_status in ["Signed", "Submitted", "Accepted"]:
				if not self.eawb_digital_signature:
					frappe.msgprint(
						_("Digital signature should be set when e-AWB status is 'Signed' or later."),
						indicator="blue",
						title=_("e-AWB Information"),
					)
				if not self.eawb_signed_date:
					frappe.msgprint(
						_("e-AWB signed date should be set when e-AWB is signed."),
						indicator="blue",
						title=_("e-AWB Information"),
					)

	@frappe.whitelist()
	def lookup_tact_rate(self):
		try:
			from logistics.air_freight.utils.iata_settings_utils import get_settings
			from logistics.air_freight.iata_cargo_xml.integrations.tact_client import lookup_tact_rate

			company = frappe.db.get_value("Air Shipment", self.air_shipment, "company")
			iata_settings = get_settings(company=company, air_shipment=self.air_shipment)
			if not iata_settings:
				frappe.throw(
					_("IATA Settings not found for company {0}. Please create IATA Settings for this company.").format(
						company or _("(unknown)")
					)
				)
			result = lookup_tact_rate(self.air_shipment, iata_settings)
			if not result.get("success"):
				frappe.throw(result.get("error") or _("TACT lookup failed"))

			self.tact_rate_lookup = 1
			self.tact_rate_reference = result.get("tact_rate_reference")
			self.tact_rate_amount = result.get("tact_rate_amount")
			self.tact_currency = result.get("tact_currency")
			self.tact_rate_validity = result.get("tact_rate_validity")
			self.save()
			return {"status": "success", **result}
		except (frappe.ValidationError, frappe.LinkValidationError, frappe.PermissionError):
			raise
		except Exception as e:
			frappe.log_error(f"TACT rate lookup error: {str(e)}", "Air Shipment IATA Transaction - TACT")
			frappe.throw(_("Error looking up TACT rate: {0}").format(str(e)))

	@frappe.whitelist()
	def submit_cass_settlement(self):
		frappe.throw(
			_(
				"CASS settlement is not submitted per shipment. "
				"Import a CASSLink file on a CASS Settlement Period (Air Freight → CASSLink)."
			)
		)

	@frappe.whitelist()
	def get_cass_billing_for_shipment(self):
		from logistics.air_freight.casslink.awb import normalize_awb

		ship = frappe.get_doc("Air Shipment", self.air_shipment)
		awb = normalize_awb(ship.get("master_awb") or ship.get("house_awb_no") or ship.get("house_awb"))
		if not awb or not frappe.db.table_exists("CASS Billing Line"):
			return {"period": None, "lines": []}
		rows = frappe.get_all(
			"CASS Billing Line",
			filters={"awb_number": awb},
			fields=["name", "parent", "match_status", "amount", "purchase_invoice"],
			limit=20,
		)
		period = None
		if rows:
			period = frappe.db.get_value("CASS File", rows[0].parent, "settlement_period")
		return {"period": period, "awb": awb, "lines": rows}

	@frappe.whitelist()
	def validate_dg_autocheck(self):
		from logistics.air_freight.utils.iata_settings_utils import get_settings
		from logistics.air_freight.iata_cargo_xml.integrations.dg_autocheck_client import (
			validate_dangerous_goods,
		)

		company = frappe.db.get_value("Air Shipment", self.air_shipment, "company")
		settings = get_settings(company=company, air_shipment=self.air_shipment)
		return validate_dangerous_goods(self.air_shipment, settings)

	@frappe.whitelist()
	def create_eawb(self):
		try:
			if not self.eawb_enabled:
				frappe.throw(_("e-AWB is not enabled for this record"))
			ship = frappe.get_doc("Air Shipment", self.air_shipment)
			if not ship.house_awb_no:
				frappe.throw(_("House AWB number is required to create e-AWB"))
			if not ship.shipper or not ship.consignee:
				frappe.throw(_("Shipper and Consignee are required to create e-AWB"))
			self.eawb_status = "Created"
			self.save()
			frappe.msgprint(_("e-AWB created successfully. Please sign and submit."), indicator="green")
			return {"status": "success", "message": "e-AWB created successfully", "eawb_status": self.eawb_status}
		except (frappe.ValidationError, frappe.LinkValidationError, frappe.PermissionError):
			raise
		except Exception as e:
			frappe.log_error(f"e-AWB creation error: {str(e)}", "Air Shipment IATA Transaction - e-AWB")
			frappe.throw(_("Error creating e-AWB: {0}").format(str(e)))

	@frappe.whitelist()
	def sign_eawb(self):
		try:
			if not self.eawb_enabled:
				frappe.throw(_("e-AWB is not enabled for this record"))
			if self.eawb_status not in ["Created", "Not Created"]:
				frappe.throw(_("e-AWB must be in 'Created' status to sign"))
			import hashlib

			ship = frappe.get_doc("Air Shipment", self.air_shipment)
			signature_data = f"{ship.name}{ship.house_awb_no or ''}{now_datetime()}"
			self.eawb_digital_signature = hashlib.sha256(signature_data.encode()).hexdigest()
			self.eawb_signed_date = now_datetime()
			self.eawb_signed_by = frappe.session.user
			self.eawb_status = "Signed"
			self.save()
			frappe.msgprint(_("e-AWB signed successfully"), indicator="green")
			return {
				"status": "success",
				"message": "e-AWB signed successfully",
				"eawb_status": self.eawb_status,
				"signed_date": self.eawb_signed_date,
			}
		except (frappe.ValidationError, frappe.LinkValidationError, frappe.PermissionError):
			raise
		except Exception as e:
			frappe.log_error(f"e-AWB signing error: {str(e)}", "Air Shipment IATA Transaction - e-AWB")
			frappe.throw(_("Error signing e-AWB: {0}").format(str(e)))

	@frappe.whitelist()
	def submit_eawb(self):
		from logistics.air_freight.iata_cargo_xml.eawb_service import submit_house_eawb

		return submit_house_eawb(self.name)
