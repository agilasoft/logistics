# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Parse CASSLink HOT (fixed-width) and spreadsheet settlement files."""

from __future__ import unicode_literals

import csv
import io
import os
import zipfile
from typing import Any, Dict, List, Optional, Sequence, Tuple

from logistics.air_freight.casslink.awb import digits_only, format_awb_display, normalize_awb

# Packed AWB detail record (handbook data elements A1/A2/A7/A6/A8):
# Record ID 3 | Agent 11 | Prefix 3 | Serial 8 | Currency 3 | Amount 12
HOT_AWB_RECORD_LEN = 40
HOT_DETAIL_RECORD_IDS = {"AWB", "CCA", "DCM"}
HOT_SKIP_RECORD_IDS = {"ALA", "HDR", "TRL", "EOF", "ZZZ"}

SPREADSHEET_COLUMN_ALIASES = {
	"awb": "awb_number",
	"awb_number": "awb_number",
	"awbno": "awb_number",
	"awb_no": "awb_number",
	"master_awb": "awb_number",
	"mawb": "awb_number",
	"airwaybill": "awb_number",
	"air_waybill": "awb_number",
	"prefix": "airline_prefix",
	"airline_prefix": "airline_prefix",
	"airline": "airline_prefix",
	"carrier": "airline_prefix",
	"amount": "amount",
	"settlement_amount": "amount",
	"charge": "amount",
	"freight": "amount",
	"net": "amount",
	"net_amt": "amount",
	"net_amount": "amount",
	"net_payable": "amount",
	"net_payable_ex_vat": "amount",
	"payable_ex_vat": "amount",
	"awb_net": "amount",
	"awb_net_amount": "amount",
	"net_total": "amount",
	"currency": "currency",
	"curr": "currency",
	"ccy": "currency",
	"reference": "billing_reference",
	"billing_reference": "billing_reference",
	"invoice": "billing_reference",
	"invoice_no": "billing_reference",
	"invoice_number": "billing_reference",
	"agent": "agent_code",
	"agent_code": "agent_code",
	"participant": "agent_code",
	"participant_code": "agent_code",
	"cass_participant": "agent_code",
}


def unwrap_cass_payload(content: bytes, filename: Optional[str] = None) -> Tuple[bytes, str]:
	"""CASSLink HOT downloads are often a ZIP. Return the inner file bytes and name."""
	name = filename or ""
	lower_name = name.lower()
	if not content:
		return content or b"", name
	if lower_name.endswith((".xlsx", ".xlsm", ".xls")):
		return content, name
	looks_zip = lower_name.endswith(".zip") or content[:2] == b"PK"
	if not looks_zip:
		return content, name
	try:
		with zipfile.ZipFile(io.BytesIO(content)) as archive:
			members = [
				info.filename
				for info in archive.infolist()
				if not info.is_dir() and "__macosx" not in info.filename.lower()
			]
			if not members:
				return content, name
			if _is_office_open_xml(members):
				return content, name or "workbook.xlsx"
			chosen = _pick_zip_member(members)
			return archive.read(chosen), os.path.basename(chosen)
	except zipfile.BadZipFile:
		return content, name


def _is_office_open_xml(members: Sequence[str]) -> bool:
	for member in members:
		lower = member.lower().replace("\\", "/")
		if lower.endswith("[content_types].xml") or lower.startswith("xl/") or "/xl/" in lower:
			return True
	return False


def _pick_zip_member(members: Sequence[str]) -> str:
	rank = {".hot": 0, ".txt": 1, ".dat": 2, ".csv": 3, ".xlsx": 4, ".xls": 5, ".pdf": 9}

	def _key(path: str):
		ext = os.path.splitext(path.lower())[1]
		return (rank.get(ext, 8), path.lower())

	return sorted(members, key=_key)[0]


def guess_file_type(filename: Optional[str], content: Optional[bytes] = None) -> str:
	name = (filename or "").lower()
	ext = os.path.splitext(name)[1]
	if ext == ".zip":
		unwrapped, inner = unwrap_cass_payload(content or b"", filename)
		if inner and inner.lower() != name:
			return guess_file_type(inner, unwrapped)
	if ext == ".pdf":
		return "PDF"
	if ext in (".xls", ".xlsx"):
		return "XLS"
	if ext == ".csv":
		return "CSV"
	if ext in (".hot", ".txt", ".dat"):
		return "HOT"
	text = _as_text(content or b"")[:200]
	first = text.lstrip()[:3].upper()
	if first in HOT_DETAIL_RECORD_IDS or first in HOT_SKIP_RECORD_IDS:
		return "HOT"
	if "," in text.splitlines()[0] if text.splitlines() else "":
		return "CSV"
	return "HOT"


def parse_file(content: bytes, filename: Optional[str] = None, file_type: Optional[str] = None) -> Dict[str, Any]:
	detected = (file_type or guess_file_type(filename, content) or "HOT").upper()
	if detected == "PDF":
		from logistics.air_freight.casslink.pdf_parser import parse_pdf_bytes

		return parse_pdf_bytes(content, filename)
	if detected in ("XLS", "XLSX"):
		return parse_spreadsheet_bytes(content, filename)
	if detected == "CSV":
		return parse_csv_text(_as_text(content))
	return parse_hot_text(_as_text(content))


def parse_hot_text(text: str) -> Dict[str, Any]:
	"""Parse CASS HOT / fixed-width (and delimited) AWB records."""
	lines: List[Dict[str, Any]] = []
	skipped = 0
	errors: List[str] = []
	for idx, raw in enumerate((text or "").splitlines(), start=1):
		row = raw.rstrip("\n\r")
		if not row.strip():
			continue
		parsed, skip_reason = _parse_hot_line(row)
		if parsed:
			parsed["source_line"] = idx
			lines.append(parsed)
		else:
			skipped += 1
			if skip_reason and skip_reason != "header":
				errors.append(f"Line {idx}: {skip_reason}")
	return {"file_type": "HOT", "lines": lines, "skipped": skipped, "errors": errors}


def _parse_hot_line(row: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
	stripped = row.strip()
	if not stripped:
		return None, "empty"
	if _looks_delimited(stripped):
		return _parse_delimited_hot_line(stripped)
	record_id = stripped[:3].upper()
	if record_id in HOT_SKIP_RECORD_IDS:
		return None, "header"
	if len(stripped) < HOT_AWB_RECORD_LEN and record_id not in HOT_DETAIL_RECORD_IDS:
		return None, f"unknown record {record_id}"
	if record_id not in HOT_DETAIL_RECORD_IDS and len(stripped) < HOT_AWB_RECORD_LEN:
		return None, f"unknown record {record_id}"
	if record_id not in HOT_DETAIL_RECORD_IDS:
		# Try packed AWB layout anyway if the line is long enough.
		if len(stripped) < HOT_AWB_RECORD_LEN:
			return None, f"unknown record {record_id}"
		packed = stripped
	else:
		packed = stripped if len(stripped) >= HOT_AWB_RECORD_LEN else stripped.ljust(HOT_AWB_RECORD_LEN)
	agent = packed[3:14].strip()
	prefix = packed[14:17].strip()
	serial = packed[17:25].strip()
	currency = packed[25:28].strip()
	amount_raw = packed[28:40].strip() if len(packed) >= 40 else packed[28:].strip()
	awb = normalize_awb(serial, prefix)
	if not awb:
		return None, "missing AWB"
	return (
		{
			"record_id": record_id,
			"agent_code": digits_only(agent) or agent,
			"airline_prefix": digits_only(prefix)[:3],
			"awb_number": awb,
			"awb_display": format_awb_display(awb),
			"currency": currency.upper() or None,
			"amount": _parse_hot_amount(amount_raw),
			"billing_reference": None,
		},
		None,
	)


def _looks_delimited(row: str) -> bool:
	return ("\t" in row) or (row.count(",") >= 3) or (row.count("|") >= 3)


def _parse_delimited_hot_line(row: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
	if "\t" in row:
		parts = [p.strip() for p in row.split("\t")]
	elif "|" in row:
		parts = [p.strip() for p in row.split("|")]
	else:
		parts = [p.strip() for p in next(csv.reader([row]))]
	if not parts:
		return None, "empty"
	head = parts[0].upper()
	if head in HOT_SKIP_RECORD_IDS:
		return None, "header"
	# Expect: record, agent, prefix, serial/awb, currency, amount, [reference]
	if head in HOT_DETAIL_RECORD_IDS and len(parts) >= 6:
		agent, prefix, serial, currency, amount = parts[1:6]
		reference = parts[6] if len(parts) > 6 else None
	elif len(parts) >= 5:
		agent, prefix, serial, currency, amount = parts[:5]
		reference = parts[5] if len(parts) > 5 else None
	else:
		return None, "not enough columns"
	awb = normalize_awb(serial, prefix)
	if not awb:
		return None, "missing AWB"
	return (
		{
			"record_id": head if head in HOT_DETAIL_RECORD_IDS else "AWB",
			"agent_code": digits_only(agent) or agent,
			"airline_prefix": digits_only(prefix)[:3],
			"awb_number": awb,
			"awb_display": format_awb_display(awb),
			"currency": (currency or "").upper() or None,
			"amount": _parse_hot_amount(amount),
			"billing_reference": reference or None,
		},
		None,
	)


def _parse_hot_amount(raw: Optional[str]) -> float:
	text = (raw or "").strip()
	if not text:
		return 0.0
	if "." in text or "," in text:
		cleaned = text.replace(",", "")
		try:
			return float(cleaned)
		except ValueError:
			return 0.0
	digits = digits_only(text)
	if not digits:
		return 0.0
	try:
		return int(digits) / 100.0
	except ValueError:
		return 0.0


def parse_csv_text(text: str) -> Dict[str, Any]:
	reader = csv.reader(io.StringIO(text or ""))
	rows = [row for row in reader if any((cell or "").strip() for cell in row)]
	return parse_spreadsheet_rows(rows, file_type="CSV")


def parse_spreadsheet_rows(rows: Sequence[Sequence[Any]], file_type: str = "XLS") -> Dict[str, Any]:
	if not rows:
		return {"file_type": file_type, "lines": [], "skipped": 0, "errors": ["File has no rows"]}
	header_idx, mapping = _header_mapping(rows[0])
	body = rows[1:] if header_idx else rows
	if not mapping:
		return {
			"file_type": file_type,
			"lines": [],
			"skipped": len(body),
			"errors": ["Could not map AWB / amount columns"],
		}
	lines: List[Dict[str, Any]] = []
	skipped = 0
	errors: List[str] = []
	for idx, row in enumerate(body, start=2 if header_idx else 1):
		parsed = _row_to_line(row, mapping)
		if not parsed:
			skipped += 1
			continue
		if not parsed.get("awb_number"):
			skipped += 1
			errors.append(f"Row {idx}: missing AWB")
			continue
		parsed["source_line"] = idx
		lines.append(parsed)
	return {"file_type": file_type, "lines": lines, "skipped": skipped, "errors": errors}


def parse_spreadsheet_bytes(content: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
	name = (filename or "").lower()
	if name.endswith(".csv"):
		return parse_csv_text(_as_text(content))
	rows = _xlsx_rows(content)
	if rows is None and name.endswith(".xls"):
		rows = _xls_rows(content)
	if rows is None:
		# Last resort: treat as CSV
		try:
			return parse_csv_text(_as_text(content))
		except Exception:
			return {
				"file_type": "XLS",
				"lines": [],
				"skipped": 0,
				"errors": ["Could not read spreadsheet. Use .xlsx or .csv."],
			}
	return parse_spreadsheet_rows(rows, file_type="XLS")


def _header_mapping(header_row: Sequence[Any]) -> Tuple[bool, Dict[int, str]]:
	mapping: Dict[int, str] = {}
	has_header = False
	for idx, cell in enumerate(header_row):
		key = _norm_header(cell)
		if key in SPREADSHEET_COLUMN_ALIASES:
			mapping[idx] = SPREADSHEET_COLUMN_ALIASES[key]
			has_header = True
	return has_header, mapping


def _norm_header(cell: Any) -> str:
	import re

	text = str(cell or "").strip().lower()
	return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _row_to_line(row: Sequence[Any], mapping: Dict[int, str]) -> Optional[Dict[str, Any]]:
	data: Dict[str, Any] = {
		"agent_code": None,
		"airline_prefix": None,
		"awb_number": None,
		"currency": None,
		"amount": 0.0,
		"billing_reference": None,
	}
	for idx, field in mapping.items():
		if idx >= len(row):
			continue
		value = row[idx]
		if field == "amount":
			data["amount"] = _parse_hot_amount(str(value) if value is not None else "")
		elif field == "awb_number":
			data["awb_number"] = str(value).strip() if value is not None else ""
		elif field == "airline_prefix":
			data["airline_prefix"] = digits_only(str(value) if value is not None else "")[:3]
		elif field == "currency":
			data["currency"] = str(value).strip().upper() if value else None
		elif field == "agent_code":
			raw = str(value).strip() if value is not None else ""
			data["agent_code"] = digits_only(raw) or raw or None
		elif field == "billing_reference":
			data["billing_reference"] = str(value).strip() if value else None
	data["awb_number"] = normalize_awb(data.get("awb_number"), data.get("airline_prefix"))
	if data["awb_number"] and not data.get("airline_prefix") and len(data["awb_number"]) >= 3:
		data["airline_prefix"] = data["awb_number"][:3]
	data["awb_display"] = format_awb_display(data.get("awb_number"))
	if not data["awb_number"] and not data.get("amount"):
		return None
	return data


def _xlsx_rows(content: bytes) -> Optional[List[List[Any]]]:
	try:
		import openpyxl
	except ImportError:
		return None
	try:
		wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
		ws = wb.active
		rows = [[cell if cell is not None else "" for cell in row] for row in ws.iter_rows(values_only=True)]
		wb.close()
		return rows
	except Exception:
		return None


def _xls_rows(content: bytes) -> Optional[List[List[Any]]]:
	try:
		import xlrd
	except ImportError:
		return None
	try:
		book = xlrd.open_workbook(file_contents=content)
		sheet = book.sheet_by_index(0)
		return [sheet.row_values(i) for i in range(sheet.nrows)]
	except Exception:
		return None


def _as_text(content: bytes) -> str:
	if content is None:
		return ""
	if isinstance(content, str):
		return content
	for encoding in ("utf-8-sig", "utf-8", "latin-1"):
		try:
			return content.decode(encoding)
		except UnicodeDecodeError:
			continue
	return content.decode("utf-8", errors="replace")
