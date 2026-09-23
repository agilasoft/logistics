# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Parse CASSLink Cargo Sales Invoice / Billing Statement PDFs."""

from __future__ import unicode_literals

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from logistics.air_freight.casslink.awb import digits_only, format_awb_display, normalize_awb

AWB_HYPHEN = re.compile(r"(?<!\d)(\d{3})-(\d{8})(?!\d)")
AWB_SPACED = re.compile(r"(?<!\d)(\d{3})[ \t]+(\d{8})(?!\d)")
CURRENCY_LABEL = re.compile(
	r"(?:currency|ccy|curr)\s*[:#]?\s*([A-Z]{3})\b",
	re.IGNORECASE,
)
AGENT_LABEL = re.compile(
	r"(?:iata\s*code|agent(?:\s*code)?|participant(?:\s*code)?)\s*[:#]?\s*([\d\-/]{7,20})",
	re.IGNORECASE,
)
INVOICE_LABEL = re.compile(
	r"(?:invoice\s*(?:no\.?|number)|billing\s*reference)\s*[:#]?\s*([A-Z0-9\-/]+)",
	re.IGNORECASE,
)
DATE_TOKEN = re.compile(
	r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b|"
	r"\b\d{1,2}[-/ ](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/ ]\d{2,4}\b",
	re.IGNORECASE,
)
MONEY_TOKEN = re.compile(
	r"\(?-?\d{1,3}(?:,\d{3})+\.\d{2}-?\)?|\(?-?\d+\.\d{2}-?\)?|\(?-?\d{1,3}(?:,\d{3})+-?\)?"
)
INVOICE_TOKEN = re.compile(r"^[A-Z]{2}-\d{3}-\d{4,}$", re.IGNORECASE)
AIRLINE_CODE_TOKEN = re.compile(r"^[A-Z]{2}$")
AIRLINE_CODE_STOP = {
	"OF", "IN", "TO", "ON", "OR", "BE", "BY", "AT", "AS", "AN", "NO", "HO",
	"BR", "IS", "IT", "IF", "WE", "SO", "DO", "UP", "AM", "PM", "NR", "RE",
}
SKIP_LINE = re.compile(
	r"recapitulation|net due airline|net due agent|billing statement|"
	r"page total|invoice total|grand total|cover page|intl total",
	re.IGNORECASE,
)
AMOUNT_HEADER_KEYS = {
	"net",
	"net_amt",
	"net_amount",
	"net_payable",
	"net_payable_ex_vat",
	"payable_ex_vat",
	"awb_net",
	"awb_net_amount",
	"net_total",
	"amount",
	"settlement_amount",
}


def parse_pdf_bytes(content: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
	text, table_rows, word_rows = _extract_pdf(content)
	return parse_pdf_text(text, filename=filename, table_rows=table_rows, word_rows=word_rows)


def parse_pdf_text(
	text: str,
	filename: Optional[str] = None,
	table_rows: Optional[Sequence[Sequence[Any]]] = None,
	word_rows: Optional[Sequence[Sequence[str]]] = None,
) -> Dict[str, Any]:
	from logistics.air_freight.casslink.parser import parse_spreadsheet_rows

	errors: List[str] = []
	snippet = (text or "")[:2000]
	if not (text or "").strip() and not table_rows:
		return {
			"file_type": "PDF",
			"lines": [],
			"skipped": 0,
			"errors": [
				"This PDF has no selectable text. Use a CASSLink text PDF, or attach HOT / XLS / CSV."
			],
			"text_snippet": snippet,
		}

	defaults = {
		"currency": _detect_currency(text),
		"agent_code": _detect_agent(text),
		"billing_reference": _detect_reference(text, filename),
	}

	lines: List[Dict[str, Any]] = []
	skipped = 0

	header_net_idx = None
	buffered: List[str] = []

	def flush_buffer():
		nonlocal skipped
		if not buffered:
			return
		parsed = _parse_pdf_line(" ".join(buffered), defaults, net_idx=header_net_idx)
		if parsed:
			parsed["source_line"] = len(lines) + 1
			lines.append(parsed)
		elif AWB_HYPHEN.search(" ".join(buffered)) or AWB_SPACED.search(" ".join(buffered)):
			skipped += 1
		buffered.clear()

	for idx, raw in enumerate((text or "").splitlines(), start=1):
		row = raw.strip()
		if not row:
			continue
		if SKIP_LINE.search(row) and not AWB_HYPHEN.search(row):
			flush_buffer()
			continue
		if _looks_like_header(row):
			flush_buffer()
			header_net_idx = _net_column_index(row)
			continue
		if AWB_HYPHEN.search(row) or AWB_SPACED.search(row):
			flush_buffer()
			buffered.append(row)
			if MONEY_TOKEN.search(row):
				flush_buffer()
			continue
		if buffered:
			buffered.append(row)
			if MONEY_TOKEN.search(" ".join(buffered)) or len(buffered) > 12:
				flush_buffer()

	flush_buffer()

	token_rows = [list(row) for row in (word_rows or []) if any(str(cell).strip() for cell in row)]
	if not token_rows:
		token_rows = [ln.split() for ln in (text or "").splitlines() if ln.strip()]
	statement_lines = _parse_statement_matrix(token_rows, defaults)

	if not lines and table_rows:
		table_result = parse_spreadsheet_rows(table_rows, file_type="PDF")
		if table_result.get("lines"):
			for line in table_result["lines"]:
				_apply_defaults(line, defaults)
			lines = table_result["lines"]
			skipped += table_result.get("skipped") or 0

	if not lines and statement_lines:
		lines = statement_lines

	lines = _dedupe_lines(lines)

	if not lines:
		errors.append(
			"No AWB or airline billing rows were found in this PDF. "
			"This file may be only the cover page or payment summary. "
			"Use Output Agents View PDF (Cargo Sales Invoice pages), HOT, or XLS."
		)
	return {
		"file_type": "PDF",
		"lines": lines,
		"skipped": skipped,
		"errors": errors,
		"text_snippet": snippet,
	}


def _extract_pdf(content: bytes) -> Tuple[str, List[List[Any]], List[List[str]]]:
	try:
		import fitz
	except ImportError:
		return "", [], []
	try:
		doc = fitz.open(stream=content, filetype="pdf")
	except Exception:
		return "", [], []
	try:
		if getattr(doc, "needs_pass", False):
			doc.authenticate("")
		pages: List[str] = []
		table_rows: List[List[Any]] = []
		word_rows: List[List[str]] = []
		for page in doc:
			native = page.get_text("text") or ""
			token_rows = _reconstruct_token_rows(page)
			pages.append(native)
			reconstructed = "\n".join(" ".join(row) for row in token_rows)
			if reconstructed and reconstructed.strip() != native.strip():
				pages.append(reconstructed)
			table_rows.extend(_table_rows(page))
			word_rows.extend(token_rows)
		return "\n".join(pages), table_rows, word_rows
	finally:
		doc.close()


def _reconstruct_token_rows(page) -> List[List[str]]:
	try:
		words = page.get_text("words") or []
	except Exception:
		return []
	rows: List[List[str]] = []
	current_y = None
	current: List[str] = []
	for word in sorted(words, key=lambda item: (round(item[1], 1), item[0])):
		y = round(word[1], 1)
		token = str(word[4] or "").strip()
		if not token:
			continue
		if current_y is None or abs(y - current_y) <= 2.5:
			current.append(token)
			if current_y is None:
				current_y = y
		else:
			if current:
				rows.append(current)
			current = [token]
			current_y = y
	if current:
		rows.append(current)
	return rows


def _reconstruct_rows(page) -> List[str]:
	return [" ".join(row) for row in _reconstruct_token_rows(page)]


def _dedupe_lines(lines: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
	seen = set()
	unique: List[Dict[str, Any]] = []
	for line in lines:
		key = (
			line.get("awb_number") or "",
			line.get("airline_prefix") or "",
			line.get("airline_code") or "",
			line.get("billing_reference") or "",
			round(float(line.get("amount") or 0), 2),
		)
		if key in seen:
			continue
		seen.add(key)
		unique.append(line)
	return unique


def _table_rows(page) -> List[List[Any]]:
	try:
		finder = page.find_tables()
	except Exception:
		return []
	tables = getattr(finder, "tables", None) or []
	rows: List[List[Any]] = []
	for table in tables:
		try:
			extracted = table.extract() or []
		except Exception:
			continue
		for row in extracted:
			rows.append([cell if cell is not None else "" for cell in row])
	return rows


def _detect_currency(text: str) -> Optional[str]:
	match = CURRENCY_LABEL.search(text or "")
	if match:
		return match.group(1).upper()
	return None


def _detect_agent(text: str) -> Optional[str]:
	match = AGENT_LABEL.search(text or "")
	if not match:
		return None
	return digits_only(match.group(1)) or match.group(1)


def _detect_reference(text: str, filename: Optional[str]) -> Optional[str]:
	match = INVOICE_LABEL.search(text or "")
	if match:
		return match.group(1)
	name = filename or ""
	period = re.search(r"(20\d{2}\d{2})", name)
	if period:
		return period.group(1)
	return None


def _apply_defaults(line: Dict[str, Any], defaults: Dict[str, Any]) -> None:
	if not line.get("currency"):
		line["currency"] = defaults.get("currency")
	if not line.get("agent_code"):
		line["agent_code"] = defaults.get("agent_code")
	if not line.get("billing_reference"):
		line["billing_reference"] = defaults.get("billing_reference")


def _looks_like_header(row: str) -> bool:
	compact = re.sub(r"[^a-z]+", "", row.lower())
	return "awb" in compact and ("net" in compact or "amount" in compact or "payable" in compact)


def _net_column_index(row: str) -> Optional[int]:
	if not re.search(r"\s{2,}", row):
		return None
	cols = _split_columns(row)
	for idx, col in enumerate(cols):
		key = re.sub(r"[^a-z0-9]+", "_", col.lower()).strip("_")
		if key in AMOUNT_HEADER_KEYS or key.startswith("net"):
			return idx
	return None


def _split_columns(row: str) -> List[str]:
	if re.search(r"\s{2,}", row):
		return [part.strip() for part in re.split(r"\s{2,}", row.strip()) if part.strip()]
	return row.split()


def _parse_pdf_line(
	row: str,
	defaults: Dict[str, Any],
	net_idx: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
	awb_match = AWB_HYPHEN.search(row) or AWB_SPACED.search(row)
	if not awb_match:
		return None
	if SKIP_LINE.search(row):
		return None
	prefix, serial = awb_match.group(1), awb_match.group(2)
	awb = normalize_awb(serial, prefix)
	if not awb:
		return None

	amount = 0.0
	cols = _split_columns(row)
	if net_idx is not None and net_idx < len(cols):
		amount = _parse_pdf_amount(cols[net_idx])
	if not amount:
		amount = _amount_from_line(row)

	line = {
		"record_id": "AWB",
		"agent_code": defaults.get("agent_code"),
		"airline_prefix": prefix,
		"awb_number": awb,
		"awb_display": format_awb_display(awb),
		"currency": defaults.get("currency"),
		"amount": amount,
		"billing_reference": defaults.get("billing_reference"),
	}
	return line


def _amount_from_line(row: str) -> float:
	cleaned = DATE_TOKEN.split(row)[0]
	cleaned = AWB_HYPHEN.sub(" ", cleaned)
	cleaned = AWB_SPACED.sub(" ", cleaned)
	money = MONEY_TOKEN.findall(cleaned)
	if not money:
		return 0.0
	return _parse_pdf_amount(money[-1])


def _parse_pdf_amount(raw: Optional[str]) -> float:
	from logistics.air_freight.casslink.parser import _parse_hot_amount

	text = (raw or "").strip()
	if not text:
		return 0.0
	if text.endswith("-") and not text.startswith("-"):
		text = "-" + text[:-1].rstrip()
	negative = text.startswith("(") and text.endswith(")")
	text = text.replace("(", "").replace(")", "")
	value = _parse_hot_amount(text)
	if negative and value > 0:
		return -value
	return value


def _parse_statement_matrix(
	rows: Sequence[Sequence[str]],
	defaults: Dict[str, Any],
) -> List[Dict[str, Any]]:
	codes: List[str] = []
	for tokens in rows:
		found = _airline_codes(tokens)
		if len(found) > len(codes):
			codes = found
	n = len(codes)
	if n < 2:
		return []

	prefixes: List[str] = []
	invoices: List[str] = []
	due_candidates: List[Tuple[int, List[float]]] = []
	for tokens in rows:
		token_list = [str(tok).strip() for tok in tokens if str(tok).strip()]
		nums3 = [tok for tok in token_list if re.fullmatch(r"\d{3}", tok)]
		if len(nums3) == n:
			prefixes = nums3
		inv = [tok for tok in token_list if INVOICE_TOKEN.match(tok)]
		if len(inv) == n:
			invoices = inv
		money = [_parse_pdf_amount(tok) for tok in _money_tokens(token_list)]
		if len(money) == n:
			joined = " ".join(token_list).lower()
			score = 0
			if "due" in joined and "airline" in joined:
				score += 3
			if "payable" in joined:
				score += 2
			if "net due" in joined:
				score -= 4
			due_candidates.append((score, money))

	if not prefixes and not invoices and not due_candidates:
		return []
	amounts = [0.0] * n
	if due_candidates:
		due_candidates.sort(key=lambda item: item[0], reverse=True)
		amounts = due_candidates[0][1]

	lines: List[Dict[str, Any]] = []
	for idx in range(n):
		prefix = prefixes[idx] if idx < len(prefixes) else ""
		invoice = invoices[idx] if idx < len(invoices) else defaults.get("billing_reference")
		code = codes[idx]
		if not prefix and not invoice:
			continue
		lines.append(
			{
				"record_id": "STMT",
				"agent_code": defaults.get("agent_code"),
				"airline_prefix": prefix,
				"airline_code": code,
				"awb_number": None,
				"awb_display": None,
				"currency": defaults.get("currency"),
				"amount": amounts[idx] if idx < len(amounts) else 0.0,
				"billing_reference": invoice,
			}
		)
	return lines


def _airline_codes(tokens: Sequence[str]) -> List[str]:
	codes: List[str] = []
	for token in tokens:
		value = str(token or "").strip().upper()
		if AIRLINE_CODE_TOKEN.fullmatch(value) and value not in AIRLINE_CODE_STOP:
			codes.append(value)
	return codes


def _money_tokens(tokens: Sequence[str]) -> List[str]:
	found: List[str] = []
	for token in tokens:
		compact = str(token or "").replace(" ", "")
		if MONEY_TOKEN.fullmatch(compact):
			found.append(compact)
	return found
