# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Orchestrate CASS file parse, match, and IATA Transaction updates."""

from __future__ import unicode_literals

from typing import Any, Dict, Optional

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, today

from logistics.air_freight.casslink.matcher import match_line
from logistics.air_freight.casslink.parser import guess_file_type, parse_file, unwrap_cass_payload
from logistics.air_freight.utils.iata_settings_utils import get_settings


def process_cass_file(doc) -> Dict[str, Any]:
	if not doc.attached_file:
		frappe.throw(_("Attach a CASS file first"))

	if any(getattr(row, "match_status", None) == "Invoiced" for row in (doc.billing_lines or [])):
		frappe.throw(_("This file has invoiced lines and cannot be reprocessed"))

	content = _read_attached_file(doc.attached_file)
	filename = (doc.attached_file or "").rsplit("/", 1)[-1]
	content, filename = unwrap_cass_payload(content, filename)
	# Re-detect from the bytes. Do not keep a leftover PDF/XLS type from a previous attach.
	file_type = guess_file_type(filename, content).upper()
	doc.file_type = file_type

	parsed = parse_file(content, filename=filename, file_type=file_type)
	company = doc.company or frappe.db.get_value(
		"CASS Settlement Period", doc.settlement_period, "company"
	)
	settings = get_settings(company=company)
	default_agent = None
	if settings:
		default_agent = settings.cass_participant_code

	doc.set("billing_lines", [])
	matched = 0
	for line in parsed.get("lines") or []:
		match = match_line(line, company=company)
		status = match.get("match_status") or "Unmatched"
		if status == "Matched":
			matched += 1
			_sync_iata_transaction(match, line, settings, doc)
		currency = line.get("currency")
		if currency and not frappe.db.exists("Currency", currency):
			currency = None
		doc.append(
			"billing_lines",
			{
				"awb_number": match.get("awb_number") or line.get("awb_number"),
				"awb_display": line.get("awb_display"),
				"airline_prefix": match.get("airline_prefix") or line.get("airline_prefix"),
				"airline": match.get("airline"),
				"agent_code": line.get("agent_code") or default_agent,
				"amount": flt(line.get("amount")),
				"currency": currency,
				"billing_reference": line.get("billing_reference"),
				"match_status": status,
				"master_awb": match.get("master_awb"),
				"air_shipment": match.get("air_shipment"),
				"iata_transaction": match.get("iata_transaction"),
				"supplier": match.get("supplier"),
			},
		)

	errors = list(parsed.get("errors") or [])
	doc.line_count = len(doc.billing_lines)
	doc.matched_count = matched
	doc.unmatched_count = doc.line_count - matched
	doc.raw_snippet = parsed.get("text_snippet") or _as_snippet(content)
	doc.processed_on = now_datetime()
	if doc.line_count:
		doc.status = "Parsed"
	else:
		doc.status = "Failed"
		if not errors:
			errors.append(_("No billing lines were found in the attached file."))
	doc.error_log = "\n".join(errors)[:5000]
	doc.save()
	_refresh_period(doc.settlement_period)
	return {
		"status": doc.status,
		"lines": doc.line_count,
		"matched": matched,
		"unmatched": doc.unmatched_count,
		"skipped": parsed.get("skipped") or 0,
		"errors": errors,
	}


def _sync_iata_transaction(match: Dict[str, Any], line: Dict[str, Any], settings, cass_file) -> Optional[str]:
	shipment = match.get("air_shipment")
	if not shipment:
		return None
	tx_name = frappe.db.get_value("Air Shipment IATA Transaction", {"air_shipment": shipment}, "name")
	if not tx_name:
		tx = frappe.get_doc(
			{"doctype": "Air Shipment IATA Transaction", "air_shipment": shipment}
		)
		tx.insert(ignore_permissions=True)
		tx_name = tx.name
	tx = frappe.get_doc("Air Shipment IATA Transaction", tx_name)
	tx.cass_participant_code = line.get("agent_code") or (
		settings.cass_participant_code if settings else None
	)
	tx.cass_settlement_status = "Submitted"
	tx.cass_settlement_amount = flt(line.get("amount"))
	tx.cass_billing_reference = line.get("billing_reference") or cass_file.settlement_period
	if not tx.cass_settlement_date:
		period_end = frappe.db.get_value(
			"CASS Settlement Period", cass_file.settlement_period, "period_end"
		)
		tx.cass_settlement_date = period_end or today()
	tx.flags.ignore_permissions = True
	tx.save(ignore_permissions=True)
	match["iata_transaction"] = tx.name
	# Stamp the billing line after append via caller — return name
	return tx.name


def _refresh_period(period_name: Optional[str]):
	if not period_name or not frappe.db.exists("CASS Settlement Period", period_name):
		return
	period = frappe.get_doc("CASS Settlement Period", period_name)
	period.recompute_totals()
	period.save(ignore_permissions=True)


def _read_attached_file(file_url: str) -> bytes:
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not file_name:
		frappe.throw(_("Attached file {0} was not found").format(file_url))
	content = frappe.get_doc("File", file_name).get_content()
	if content is None:
		return b""
	if isinstance(content, str):
		return content.encode("utf-8")
	return content


def _as_snippet(content: bytes) -> str:
	if not content:
		return ""
	if isinstance(content, str):
		return content[:2000]
	try:
		return content.decode("utf-8", errors="replace")[:2000]
	except Exception:
		return ""
