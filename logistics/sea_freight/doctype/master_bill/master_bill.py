# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document

from logistics.utils import goconnect as gc


class MasterBill(Document):
	def validate(self):
		"""Validate Master Bill"""
		self.sync_ports_from_cfs()

	def on_update(self):
		"""Called after saving"""
		pass

	def sync_ports_from_cfs(self):
		"""Sync origin/destination port from CFS when CFS is set and port is not"""
		try:
			if self.origin_cfs and not self.origin_port:
				port = frappe.db.get_value("Container Freight Station", self.origin_cfs, "port")
				if port:
					self.origin_port = port

			if self.destination_cfs and not self.destination_port:
				port = frappe.db.get_value("Container Freight Station", self.destination_cfs, "port")
				if port:
					self.destination_port = port
		except Exception as e:
			frappe.log_error(f"Sync ports from CFS error: {str(e)}")


@frappe.whitelist()
def refresh_voyage_status(master_bill_name):
	"""Force-refresh the linked Vessel Schedule via GoConnect.

	When the goconnect app is installed and licensed for the vessel voyage
	tracker, this triggers a live AIS pull and persists the results back into
	both the Vessel Schedule and this Master Bill.

	When goconnect is not installed, returns the current Master Bill state
	with an informational message so the UI can render a placeholder.
	"""
	if not master_bill_name:
		frappe.throw(_("master_bill_name is required"))

	doc = frappe.get_doc("Master Bill", master_bill_name)

	if not gc.is_installed():
		return {
			"success": False,
			"app_installed": False,
			"voyage_status": doc.voyage_status,
			"actual_departure": doc.actual_departure,
			"actual_arrival": doc.actual_arrival,
			"last_position_update": doc.last_position_update,
			"message": _(
				"GoConnect is not installed. Install it to enable live "
				"vessel/voyage tracking."
			),
		}

	if not doc.get("vessel_schedule"):
		return {
			"success": False,
			"app_installed": True,
			"voyage_status": doc.voyage_status,
			"message": _(
				"No Vessel Schedule is linked to this Master Bill. "
				"Click 'Auto-link Vessel Schedule' first."
			),
		}

	try:
		result = gc.call(
			"goconnect.api.sea.sync_voyage_data",
			vessel_schedule=doc.vessel_schedule,
		)
	except frappe.PermissionError as e:
		return {
			"success": False,
			"app_installed": True,
			"licensed": False,
			"message": str(e),
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "refresh_voyage_status: connect call failed")
		return {"success": False, "app_installed": True, "error": str(e)}

	# Re-read Master Bill — the Vessel Schedule controller writes back via the
	# integrations module on its save.
	doc.reload()
	return {
		"success": bool(result and result.get("success")),
		"app_installed": True,
		"licensed": True,
		"voyage_status": doc.voyage_status,
		"actual_departure": doc.actual_departure,
		"actual_arrival": doc.actual_arrival,
		"last_position_update": doc.last_position_update,
		"current_latitude": doc.current_latitude,
		"current_longitude": doc.current_longitude,
		"current_speed_knots": doc.current_speed_knots,
		"provider": (result or {}).get("provider"),
	}


@frappe.whitelist()
def fetch_and_link_vessel_schedule(master_bill_name):
	"""Create or attach a Vessel Schedule based on this Master Bill's
	vessel + voyage_no + vessel_imo.

	If a matching Vessel Schedule already exists, link it. Otherwise create
	a new one in goconnect with the data we have.
	"""
	if not master_bill_name:
		frappe.throw(_("master_bill_name is required"))

	doc = frappe.get_doc("Master Bill", master_bill_name)

	if not gc.is_installed():
		return {
			"success": False,
			"app_installed": False,
			"message": _("GoConnect is not installed."),
		}

	voyage_no = (doc.get("voyage_no") or "").strip()
	vessel_imo = (doc.get("vessel_imo") or "").strip() or None
	vessel = (doc.get("vessel") or "").strip() or None
	if not voyage_no:
		frappe.throw(_("Voyage No is required on this Master Bill before linking a schedule."))

	# Look for an existing Vessel Schedule with matching voyage_no + IMO
	filters = {"voyage_no": voyage_no}
	if vessel_imo:
		filters["vessel_imo"] = vessel_imo
	candidates = frappe.get_all(
		"Vessel Schedule",
		filters=filters,
		fields=["name"],
		order_by="modified desc",
		limit=1,
	)
	if candidates:
		schedule_name = candidates[0]["name"]
	else:
		# Resolve vessel (Link → Vessel) by the carrier text if possible
		vessel_link = None
		if vessel:
			vessel_link = frappe.db.get_value("Vessel", {"vessel_name": vessel}, "name") or None
		new_doc = frappe.get_doc(
			{
				"doctype": "Vessel Schedule",
				"vessel": vessel_link,
				"voyage_no": voyage_no,
				"vessel_imo": vessel_imo,
				"shipping_line": doc.get("shipping_line"),
				"load_port": doc.get("origin_port"),
				"discharge_port": doc.get("destination_port"),
				"scheduled_departure": doc.get("scheduled_departure"),
				"scheduled_arrival": doc.get("scheduled_arrival"),
				"voyage_status": doc.get("voyage_status") or "Scheduled",
			}
		)
		new_doc.insert(ignore_permissions=True)
		schedule_name = new_doc.name

	frappe.db.set_value(
		"Master Bill",
		master_bill_name,
		"vessel_schedule",
		schedule_name,
		update_modified=False,
	)
	frappe.db.commit()

	return {
		"success": True,
		"app_installed": True,
		"vessel_schedule": schedule_name,
	}
