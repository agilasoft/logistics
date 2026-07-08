"""
IATA Cargo-XML Message Parser
Parses incoming XML messages and updates system records
"""

import frappe
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, Optional

from .base_connector import IATAConnector
from logistics.air_freight.iata_cargo_xml.eawb_utils import (
	SPLIT_FSU_CODES,
	map_fsu_status,
)


class MessageParser(IATAConnector):
	"""Parses incoming IATA Cargo-XML messages"""

	def __init__(self):
		super().__init__()
		self.namespace = "http://www.iata.org/IATA/CargoXML/1.0"

	def process_incoming_message(self, xml_content: str, message_type: str) -> Dict[str, Any]:
		"""Process incoming XML message"""
		try:
			root = ET.fromstring(xml_content)
			message_data = self._extract_message_data(root, message_type)
			message_data = self._augment_inbound_data(root, message_type, message_data, xml_content)

			if message_type in ("FSU", "XFSU"):
				result = self._process_fsu_message(message_data)
			elif message_type in ("FMA", "XFMA"):
				result = self._process_fma_message(message_data)
			elif message_type in ("FWB", "XFWB"):
				result = self._process_fwb_message(message_data)
			elif message_type in ("XFNM", "FNA"):
				result = self._process_xfnm_message(message_data, xml_content)
			elif message_type in ("XFHL", "FHL"):
				result = self._process_xfhl_message(message_data)
			else:
				result = {"success": False, "error": f"Unsupported message type: {message_type}"}

			self.log_transaction({
				"message_type": message_type,
				"direction": "inbound",
				"status": "processed" if result.get("success") else "failed",
				"message_data": message_data,
				"response_content": str(result),
			})
			return result

		except Exception as e:
			frappe.log_error(f"Message parsing error: {str(e)}")
			return {"success": False, "error": str(e)}

	def _process_fsu_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
		try:
			awb_number = message_data.get("awb_number")
			status_code = (message_data.get("status_code") or "").upper()
			status_description = message_data.get("status_description")

			if not awb_number:
				return {"success": False, "error": "AWB number not found in FSU message"}

			job = self._find_job_by_awb(awb_number)
			mawb = None
			if not job:
				mawb = self._find_mawb_by_awb_no(awb_number)
				if mawb:
					job = self._find_primary_shipment_for_mawb(mawb.name)

			if not job and not mawb:
				return {"success": False, "error": f"No job found for AWB: {awb_number}"}

			if status_code in SPLIT_FSU_CODES:
				self._handle_split_arrival(job, message_data)

			if job:
				self._update_job_status(job, status_code, status_description)
				self._create_milestone(job.name, status_code, status_description)

			if mawb and status_code == "RCS":
				mawb.eawb_status = "Accepted"
				mawb.flags.ignore_permissions = True
				mawb.save(ignore_permissions=True)

			return {
				"success": True,
				"job_updated": job.name if job else None,
				"mawb_updated": mawb.name if mawb else None,
				"status_code": status_code,
				"status_description": status_description,
			}

		except Exception as e:
			frappe.log_error(f"FSU processing error: {str(e)}")
			return {"success": False, "error": str(e)}

	def _process_xfnm_message(self, message_data: Dict[str, Any], xml_content: str) -> Dict[str, Any]:
		"""Process negative acknowledgement / error messages."""
		awb_number = message_data.get("awb_number")
		error_text = message_data.get("error_text") or xml_content[:500]
		target = None

		if awb_number:
			mawb = self._find_mawb_by_awb_no(awb_number)
			if mawb:
				mawb.eawb_status = "Rejected"
				mawb.flags.ignore_permissions = True
				mawb.save(ignore_permissions=True)
				target = mawb.name
			else:
				job = self._find_job_by_awb(awb_number)
				if job:
					tx = self._get_or_create_iata_tx(job)
					tx.eawb_status = "Rejected"
					tx.iata_message_id = message_data.get("message_id")
					tx.last_status_update = datetime.now()
					tx.flags.ignore_permissions = True
					tx.save(ignore_permissions=True)
					target = job.name

		return {
			"success": True,
			"rejected": True,
			"target": target,
			"error": error_text,
		}

	def _process_xfhl_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
		awb_number = message_data.get("awb_number")
		if not awb_number:
			return {"success": False, "error": "House AWB number missing in XFHL"}
		job = self._find_job_by_awb(awb_number)
		if not job:
			return {"success": False, "error": f"No shipment for house AWB {awb_number}"}
		tx = self._get_or_create_iata_tx(job)
		tx.iata_status = "Manifest Confirmed"
		tx.last_status_update = datetime.now()
		tx.flags.ignore_permissions = True
		tx.save(ignore_permissions=True)
		return {"success": True, "job_updated": job.name}

	def _handle_split_arrival(self, job: Optional[frappe.Document], message_data: Dict[str, Any]):
		if not job:
			return
		split_qty = message_data.get("split_pieces") or message_data.get("pieces")
		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Air Shipment",
			"reference_name": job.name,
			"content": f"Split arrival reported by carrier. Pieces: {split_qty or 'unknown'}",
		}).insert(ignore_permissions=True)
		tx = self._get_or_create_iata_tx(job)
		tx.iata_status = "Split Arrival"
		tx.last_status_update = datetime.now()
		tx.flags.ignore_permissions = True
		tx.save(ignore_permissions=True)

	def _find_mawb_by_awb_no(self, awb_number: str) -> Optional[frappe.Document]:
		clean = (awb_number or "").replace("-", "").replace(" ", "")
		name = frappe.db.get_value("Master Air Waybill", {"master_awb_no": clean}, "name")
		if not name:
			name = frappe.db.get_value("Master Air Waybill", {"master_awb_no": awb_number}, "name")
		return frappe.get_doc("Master Air Waybill", name) if name else None

	def _find_primary_shipment_for_mawb(self, mawb_name: str) -> Optional[frappe.Document]:
		ship_name = frappe.db.get_value("Air Shipment", {"master_awb": mawb_name}, "name")
		return frappe.get_doc("Air Shipment", ship_name) if ship_name else None

	def _process_fma_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
		try:
			flight_number = message_data.get("flight_number")
			flight_date = message_data.get("flight_date")

			if not flight_number:
				return {"success": False, "error": "Flight number not found in FMA message"}

			mawb = self._find_mawb_by_flight(flight_number, flight_date)
			if not mawb:
				return {"success": False, "error": f"No MAWB found for flight: {flight_number}"}

			mawb.flight_no = flight_number
			if flight_date:
				mawb.origin_receipt_requested = datetime.strptime(flight_date, "%Y-%m-%d").date()
			mawb.save()

			return {
				"success": True,
				"mawb_updated": mawb.name,
				"flight_number": flight_number,
				"flight_date": flight_date,
			}

		except Exception as e:
			frappe.log_error(f"FMA processing error: {str(e)}")
			return {"success": False, "error": str(e)}

	def _process_fwb_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
		try:
			awb_number = message_data.get("awb_number")
			origin_airport = message_data.get("origin_airport")
			destination_airport = message_data.get("destination_airport")

			if not awb_number:
				return {"success": False, "error": "AWB number not found in FWB message"}

			job = self._find_job_by_awb(awb_number)
			if not job:
				job = self._create_job_from_fwb(message_data)
			else:
				self._update_job_from_fwb(job, message_data)

			return {
				"success": True,
				"job_processed": job.name,
				"action": "created" if not job.get("__islocal") else "updated",
			}

		except Exception as e:
			frappe.log_error(f"FWB processing error: {str(e)}")
			return {"success": False, "error": str(e)}

	def _find_job_by_awb(self, awb_number: str) -> Optional[frappe.Document]:
		try:
			jobs = frappe.get_all(
				"Air Shipment",
				filters={"master_awb": awb_number},
				limit=1,
			)
			if jobs:
				return frappe.get_doc("Air Shipment", jobs[0].name)

			jobs = frappe.get_all(
				"Air Shipment",
				filters={"house_awb_no": awb_number},
				limit=1,
			)
			if jobs:
				return frappe.get_doc("Air Shipment", jobs[0].name)

			try:
				return frappe.get_doc("Air Shipment", awb_number)
			except Exception:
				pass

			mawbs = frappe.get_all(
				"Master Air Waybill",
				filters={"master_awb_no": awb_number},
				limit=1,
			)
			if mawbs:
				jobs = frappe.get_all(
					"Air Shipment",
					filters={"master_awb": mawbs[0].name},
					limit=1,
				)
				if jobs:
					return frappe.get_doc("Air Shipment", jobs[0].name)

			return None

		except Exception as e:
			frappe.log_error(f"Find job by AWB error: {str(e)}")
			return None

	def _find_mawb_by_flight(self, flight_number: str, flight_date: str = None) -> Optional[frappe.Document]:
		try:
			filters = {"flight_no": flight_number}
			if flight_date:
				filters["origin_receipt_requested"] = datetime.strptime(flight_date, "%Y-%m-%d").date()

			mawbs = frappe.get_all("Master Air Waybill", filters=filters, limit=1)
			if mawbs:
				return frappe.get_doc("Master Air Waybill", mawbs[0].name)
			return None

		except Exception as e:
			frappe.log_error(f"Find MAWB by flight error: {str(e)}")
			return None

	def _get_or_create_iata_tx(self, job):
		name = frappe.db.get_value("Air Shipment IATA Transaction", {"air_shipment": job.name}, "name")
		if name:
			return frappe.get_doc("Air Shipment IATA Transaction", name)
		tx = frappe.get_doc({"doctype": "Air Shipment IATA Transaction", "air_shipment": job.name})
		tx.flags.ignore_permissions = True
		tx.insert()
		return tx

	def _update_job_status(self, job: frappe.Document, status_code: str, status_description: str):
		try:
			new_status = map_fsu_status(status_code, status_description)
			tx = self._get_or_create_iata_tx(job)
			tx.iata_status = new_status
			tx.last_status_update = datetime.now()
			if status_code == "RCS":
				tx.eawb_status = "Accepted"
			tx.flags.ignore_permissions = True
			tx.save()
		except Exception as e:
			frappe.log_error(f"Update job status error: {str(e)}")

	def _create_milestone(self, job_name: str, status_code: str, status_description: str):
		try:
			label = map_fsu_status(status_code, status_description)
			milestone = frappe.get_doc({
				"doctype": "Job Milestone",
				"parent": job_name,
				"parenttype": "Air Shipment",
				"parentfield": "milestones",
				"milestone": label,
				"status": "Completed",
				"expected_date": datetime.now().date(),
				"actual_date": datetime.now().date(),
			})
			milestone.insert(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Create milestone error: {str(e)}")

	def _create_job_from_fwb(self, message_data: Dict[str, Any]) -> frappe.Document:
		try:
			job = frappe.get_doc({
				"doctype": "Air Shipment",
				"master_awb": message_data.get("awb_number"),
				"direction": "Export",
				"origin_port": self._find_location_by_iata(message_data.get("origin_airport")),
				"destination_port": self._find_location_by_iata(message_data.get("destination_airport")),
				"booking_date": datetime.now().date(),
			})
			job.insert(ignore_permissions=True)
			tx = self._get_or_create_iata_tx(job)
			tx.iata_status = "Received from IATA"
			if message_data.get("message_id"):
				tx.iata_message_id = message_data.get("message_id")
			tx.last_status_update = datetime.now()
			tx.flags.ignore_permissions = True
			tx.save()
			return job
		except Exception as e:
			frappe.log_error(f"Create job from FWB error: {str(e)}")
			raise

	def _update_job_from_fwb(self, job: frappe.Document, message_data: Dict[str, Any]):
		try:
			if message_data.get("origin_airport"):
				job.origin_port = self._find_location_by_iata(message_data.get("origin_airport"))
			if message_data.get("destination_airport"):
				job.destination_port = self._find_location_by_iata(message_data.get("destination_airport"))

			tx = self._get_or_create_iata_tx(job)
			tx.iata_status = "Confirmed via IATA"
			if message_data.get("message_id"):
				tx.iata_message_id = message_data.get("message_id")
			tx.last_status_update = datetime.now()
			tx.flags.ignore_permissions = True
			tx.save()
			job.save()
		except Exception as e:
			frappe.log_error(f"Update job from FWB error: {str(e)}")

	def _find_location_by_iata(self, iata_code: str) -> Optional[str]:
		try:
			if not iata_code:
				return None
			locations = frappe.get_all("Location", filters={"custom_iata_code": iata_code}, limit=1)
			if locations:
				return locations[0].name
			return None
		except Exception as e:
			frappe.log_error(f"Find location by IATA error: {str(e)}")
			return None

	def _augment_inbound_data(
		self,
		root: ET.Element,
		message_type: str,
		message_data: Dict[str, Any],
		xml_content: str,
	) -> Dict[str, Any]:
		message_data = dict(message_data or {})
		if message_type in ("FSU", "XFSU"):
			status = self._find_element(root, "StatusUpdate")
			if status is not None:
				message_data.setdefault("status_code", status.get("StatusCode"))
				message_data.setdefault("status_description", status.get("StatusDescription"))
				if status.get("Pieces"):
					message_data["split_pieces"] = status.get("Pieces")
		if message_type in ("XFNM", "FNA"):
			message_data["error_text"] = xml_content[:1000]
			for elem in root.iter():
				tag = elem.tag.split("}")[-1]
				if tag in ("Error", "Reason", "Remarks") and elem.text:
					message_data["error_text"] = elem.text
		return message_data

	def _find_element(self, root: ET.Element, local_name: str):
		found = root.find(local_name)
		if found is not None:
			return found
		for elem in root.iter():
			if elem.tag.split("}")[-1] == local_name:
				return elem
		return None
