"""
UN/LOCODE codelist from DataHub Core dataset (Frictionless datapackage API).

Dataset: https://datahub.io/core/un-locode
Flow (per DataHub docs): fetch ``datapackage.json``, resolve each resource ``path``
against the package base URL, then HTTP GET the CSV bytes. Cached under the site
private files directory. Disable via site_config ``use_datahub_un_locode = 0``.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import frappe
from frappe.utils import cint, get_site_path

# Public dataset page; CSV paths are resolved from datapackage.json (stable API).
DATAHUB_UN_LOCODE_DATASET = "https://datahub.io/core/un-locode"
DATAPACKAGE_URL = f"{DATAHUB_UN_LOCODE_DATASET.rstrip('/')}/_r/-/datapackage.json"


def _datapackage_directory_url() -> str:
	"""Base URL for resolving relative resource paths (directory of datapackage.json)."""
	return DATAPACKAGE_URL.rsplit("/", 1)[0] + "/"


def _fallback_resource_urls() -> Dict[str, str]:
	"""If datapackage resources are missing, use the same layout as the published package."""
	root = f"{DATAHUB_UN_LOCODE_DATASET.rstrip('/')}/_r/-/data"
	return {
		"code-list": f"{root}/code-list.csv",
		"country-codes": f"{root}/country-codes.csv",
	}


def _resource_urls_from_datapackage(dp: Optional[dict]) -> Dict[str, str]:
	"""Map resource ``name`` (e.g. code-list) to absolute download URL."""
	if not dp or not isinstance(dp, dict):
		return {}
	base = _datapackage_directory_url()
	out: Dict[str, str] = {}
	for res in dp.get("resources") or []:
		if not isinstance(res, dict):
			continue
		rel = (res.get("path") or res.get("url") or "").strip()
		if not rel:
			continue
		abs_url = urljoin(base, rel)
		name = (res.get("name") or "").strip().lower()
		if name:
			out[name] = abs_url
	return out


def _merge_resource_urls(dp: dict) -> Dict[str, str]:
	"""Prefer URLs declared in datapackage.json; fill gaps with static fallbacks."""
	merged = dict(_fallback_resource_urls())
	merged.update(_resource_urls_from_datapackage(dp))
	return merged

CACHE_SUBDIR = "un_locode_datahub"
META_FILE = "meta.json"
CODE_LIST_FILE = "code-list.csv"
COUNTRY_CODES_FILE = "country-codes.csv"
MAX_CACHE_AGE_DAYS = 7

_INDEX: Optional[Dict[str, Dict[str, str]]] = None
_INDEX_VERSION: Optional[str] = None
_COUNTRY_NAMES: Optional[Dict[str, str]] = None
_STATUS_LABEL_BY_CODE: Optional[Dict[str, str]] = None


def is_datahub_un_locode_enabled() -> bool:
	return cint(frappe.conf.get("use_datahub_un_locode", 1))


def _cache_dir() -> str:
	path = os.path.join(get_site_path(), "private", "files", CACHE_SUBDIR)
	os.makedirs(path, exist_ok=True)
	return path


def _http_get_text(url: str, timeout: int = 120) -> str:
	import urllib.request

	req = urllib.request.Request(url, headers={"User-Agent": "Frappe-Logistics-UNLOCO/1.0"})
	with urllib.request.urlopen(req, timeout=timeout) as resp:
		return resp.read().decode("utf-8", errors="replace")


def _http_get_bytes(url: str, timeout: int = 120) -> bytes:
	import urllib.request

	req = urllib.request.Request(url, headers={"User-Agent": "Frappe-Logistics-UNLOCO/1.0"})
	with urllib.request.urlopen(req, timeout=timeout) as resp:
		return resp.read()


def _load_meta() -> Optional[dict]:
	p = os.path.join(_cache_dir(), META_FILE)
	if not os.path.isfile(p):
		return None
	try:
		with open(p, encoding="utf-8") as f:
			return json.load(f)
	except Exception:
		return None


def _save_meta(version: str, resource_urls: Optional[Dict[str, str]] = None) -> None:
	meta = {
		"version": version,
		"fetched_at": datetime.now(timezone.utc).isoformat(),
		"datapackage_url": DATAPACKAGE_URL,
		"dataset": DATAHUB_UN_LOCODE_DATASET,
		"resource_urls": resource_urls or {},
	}
	with open(os.path.join(_cache_dir(), META_FILE), "w", encoding="utf-8") as f:
		json.dump(meta, f, indent=2)


def _cache_needs_refresh(remote_version: str) -> bool:
	code_path = os.path.join(_cache_dir(), CODE_LIST_FILE)
	country_path = os.path.join(_cache_dir(), COUNTRY_CODES_FILE)
	meta = _load_meta()
	if not os.path.isfile(code_path) or not os.path.isfile(country_path):
		return True
	if not meta or meta.get("version") != remote_version:
		return True
	try:
		fetched = datetime.fromisoformat(meta["fetched_at"].replace("Z", "+00:00"))
		if datetime.now(timezone.utc) - fetched > timedelta(days=MAX_CACHE_AGE_DAYS):
			return True
	except Exception:
		return True
	return False


def ensure_datahub_un_locode_files() -> Optional[str]:
	try:
		dp = json.loads(_http_get_text(DATAPACKAGE_URL, timeout=60))
		version = str(dp.get("version") or "")
		if not version:
			return None
		if not _cache_needs_refresh(version):
			return version
		urls = _merge_resource_urls(dp)
		code_url = urls.get("code-list")
		country_url = urls.get("country-codes")
		if not code_url or not country_url:
			frappe.log_error(
				json.dumps({"urls": urls, "resources": [r.get("name") for r in (dp.get("resources") or [])]}),
				"DataHub UN/LOCODE: datapackage missing code-list or country-codes resource URL",
			)
			return None
		with open(os.path.join(_cache_dir(), CODE_LIST_FILE), "wb") as f:
			f.write(_http_get_bytes(code_url, timeout=180))
		with open(os.path.join(_cache_dir(), COUNTRY_CODES_FILE), "wb") as f:
			f.write(_http_get_bytes(country_url, timeout=60))
		_save_meta(version, resource_urls=urls)
		global _INDEX, _INDEX_VERSION, _COUNTRY_NAMES, _STATUS_LABEL_BY_CODE
		_INDEX = None
		_INDEX_VERSION = None
		_COUNTRY_NAMES = None
		_STATUS_LABEL_BY_CODE = None
		return version
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"DataHub UN/LOCODE cache: {e!s}")
		meta = _load_meta()
		return meta.get("version") if meta else None


def _load_country_names() -> Dict[str, str]:
	global _COUNTRY_NAMES
	if _COUNTRY_NAMES is not None:
		return _COUNTRY_NAMES
	out: Dict[str, str] = {}
	path = os.path.join(_cache_dir(), COUNTRY_CODES_FILE)
	if os.path.isfile(path):
		with open(path, encoding="utf-8", errors="replace", newline="") as f:
			for row in csv.DictReader(f):
				cc = (row.get("CountryCode") or "").strip().upper()
				name = (row.get("CountryName") or "").strip()
				if cc:
					out[cc] = name
	_COUNTRY_NAMES = out
	return out


def _load_status_labels() -> Dict[str, str]:
	"""
	Map 2-letter UN/LOCODE status codes to the Select option line on UNLOCO.

	DataHub's status-indicators.csv lists additional codes (e.g. AI) that are not
	options on this DocType; we only expose labels defined in ``unloco.json`` so
	populated values always match the Select field.
	"""
	global _STATUS_LABEL_BY_CODE
	if _STATUS_LABEL_BY_CODE is not None:
		return _STATUS_LABEL_BY_CODE
	by_code: Dict[str, str] = {}
	try:
		meta = frappe.get_meta("UNLOCO")
		f = meta.get_field("status")
		if f and f.options:
			for line in f.options.split("\n"):
				line = line.strip()
				if len(line) >= 4 and line[2:4] == " -":
					by_code[line[:2].strip().upper()] = line
	except Exception:
		pass
	_STATUS_LABEL_BY_CODE = by_code
	return by_code


def iter_unlocode_codes_from_codelist_cache():
	"""
Yield each valid 5-letter UN/LOCODE from the cached DataHub ``code-list.csv``.

	Caller should run ``ensure_datahub_un_locode_files()`` first so the file exists.
	"""
	meta = _load_meta()
	code_path = os.path.join(_cache_dir(), CODE_LIST_FILE)
	if not meta or not os.path.isfile(code_path):
		return
	with open(code_path, encoding="utf-8", errors="replace", newline="") as f:
		for row in csv.DictReader(f):
			cc = (row.get("Country") or "").strip().upper()
			loc = (row.get("Location") or "").strip().upper()
			if len(cc) == 2 and len(loc) == 3:
				yield cc + loc


def _get_codelist_index() -> Optional[Dict[str, Dict[str, str]]]:
	global _INDEX, _INDEX_VERSION
	meta = _load_meta()
	version = (meta or {}).get("version")
	code_path = os.path.join(_cache_dir(), CODE_LIST_FILE)
	if not version or not os.path.isfile(code_path):
		return None
	if _INDEX is not None and _INDEX_VERSION == version:
		return _INDEX
	idx: Dict[str, Dict[str, str]] = {}
	with open(code_path, encoding="utf-8", errors="replace", newline="") as f:
		for row in csv.DictReader(f):
			cc = (row.get("Country") or "").strip().upper()
			loc = (row.get("Location") or "").strip().upper()
			if len(cc) == 2 and len(loc) == 3:
				idx[cc + loc] = row
	_INDEX = idx
	_INDEX_VERSION = version
	return idx


def _function_string(function_field: str) -> str:
	"""Normalised 8-character UN/LOCODE Function column (UNECE Recommendation 16)."""
	return (function_field or "").ljust(8)[:8]


def _function_positions(function_field: str) -> List[str]:
	"""
	Active UN/LOCODE function **codes** (slots 1–8) per UNECE: slot *i* (1-based) is active only
	when column position *i* contains digit ``str(i)`` (DataHub codelist follows this strictly),
	except slot 8 which uses ``8`` (inland water) or ``B`` (border — excluded here; see
	:func:`_primary_location_type`).
	"""
	s = _function_string(function_field)
	out: List[str] = []
	for i in range(7):
		if s[i] == str(i + 1):
			out.append(str(i + 1))
	if len(s) >= 8 and s[7] == "8":
		out.append("8")
	return out


def function_field_to_unloco_capabilities(function_field: str) -> Dict[str, int]:
	"""
	Map the 8-character ``Function`` column to UNLOCO check fields using UNCEFACT
	``unlcdf:1`` … ``unlcdf:8`` / ``B`` semantics (see Recommendation 16, Function column).

	Strict rule: for slots 1–7, only digit *n* in position *n* activates that function.
	Slot 8: ``8`` = inland water transport; ``B`` = cross-border (legacy; customs-related).

	Checkbox alignment (no UN digit → left unset): ``has_store`` is set for function **6**
	(multimodal: ICD / container depot storage). ``has_unload`` is set for functions **1, 6, 7, 8**
	where UNECE text refers to cargo handling or load/discharge. ``has_outport`` is used for
	function **8** (inland water ports) as the closest UNLOCO water-side flag besides ``has_seaport``.
	"""
	s = _function_string(function_field)
	f1 = s[0] == "1"
	f2 = s[1] == "2"
	f3 = s[2] == "3"
	f4 = s[3] == "4"
	f5 = s[4] == "5"
	f6 = s[5] == "6"
	f7 = s[6] == "7"
	f8 = len(s) >= 8 and s[7] == "8"
	fb = len(s) >= 8 and s[7] == "B"

	cap: Dict[str, int] = {
		"has_post": 0,
		"has_customs": 0,
		"has_unload": 0,
		"has_airport": 0,
		"has_rail": 0,
		"has_road": 0,
		"has_store": 0,
		"has_terminal": 0,
		"has_discharge": 0,
		"has_seaport": 0,
		"has_outport": 0,
	}
	if fb:
		cap["has_customs"] = 1
	if f1:
		cap["has_seaport"] = 1
	if f2:
		cap["has_rail"] = 1
	if f3:
		cap["has_road"] = 1
	if f4:
		cap["has_airport"] = 1
	if f5:
		cap["has_post"] = 1
	if f6:
		cap["has_terminal"] = 1
		cap["has_store"] = 1
	if f7:
		cap["has_discharge"] = 1
	if f8:
		cap["has_outport"] = 1
	if f1 or f6 or f7 or f8:
		cap["has_unload"] = 1
	return cap


def _primary_location_type(functions: List[str], function_field: str = "") -> str:
	s = _function_string(function_field)
	if len(s) >= 8 and s[7] == "B":
		return "Border Crossing"
	order = [
		("4", "Airport"),
		("1", "Port"),
		("8", "Port"),
		("2", "Railway Station"),
		("3", "Road Terminal"),
		("6", "Multimodal Terminal"),
		("5", "Postal Office"),
		("7", "Other"),
	]
	fs = set(functions)
	for code, label in order:
		if code in fs:
			return label
	return "Other"


def datahub_row_to_unlocode_dict(unlocode: str, row: Dict[str, str]) -> Dict[str, Any]:
	from logistics.air_freight.utils.unlocode_utils import enrich_country_info, parse_un_coordinates

	u = (unlocode or "").strip().upper()
	countries = _load_country_names()
	cc = (row.get("Country") or "").strip().upper()
	if len(cc) != 2 and len(u) >= 2:
		cc = u[:2]
	function_field = row.get("Function") or ""
	functions = _function_positions(function_field)
	status_codes = _load_status_labels()
	raw_status = (row.get("Status") or "").strip().upper()
	status_label = status_codes.get(raw_status)

	lat, lon = parse_un_coordinates(row.get("Coordinates") or "")

	name = (row.get("Name") or row.get("NameWoDiacritics") or "").strip()
	sub = (row.get("Subdivision") or "").strip()
	iata = (row.get("IATA") or "").strip()
	loc3 = (row.get("Location") or "").strip().upper()
	if not iata and len(loc3) == 3:
		iata = loc3

	country_name = countries.get(cc, "") if cc else ""
	if not country_name and len(cc) == 2:
		country_name = enrich_country_info(cc).get("country", "") or ""

	out: Dict[str, Any] = {
		"unlocode": u,
		"location_name": name,
		"country": country_name,
		"country_code": cc,
		"subdivision": sub,
		"city": "",
		"location_type": _primary_location_type(functions, function_field),
		"iata_code": iata,
		"description": (
			f"UN/LOCODE via DataHub (UNECE-derived). Status {raw_status or 'n/a'}; "
			f"Function {function_field!r}. Coordinates raw: {row.get('Coordinates') or ''}."
		).strip(),
		"data_source": "DataHub.io",
	}
	if status_label:
		out["status"] = status_label
	if lat is not None and lon is not None:
		out["latitude"] = lat
		out["longitude"] = lon
	out.update(function_field_to_unloco_capabilities(function_field))
	return out


def get_codelist_function_field(unlocode: str) -> Optional[str]:
	"""
	Raw UNECE ``Function`` column from the cached DataHub ``code-list.csv`` row, if any.

	Used on forced refresh (e.g. Update All) so ``has_*`` checkboxes always follow the
	official code-list even when ``get_unlocode_from_database`` falls back to inference
	or returns a dict without capability keys.
	"""
	if not is_datahub_un_locode_enabled():
		return None
	u = (unlocode or "").strip().upper()
	if len(u) != 5:
		return None
	try:
		ensure_datahub_un_locode_files()
		idx = _get_codelist_index()
		if not idx:
			return None
		row = idx.get(u)
		if not row:
			return None
		raw = (row.get("Function") or "").strip()
		return raw or None
	except Exception:
		return None


def get_unlocode_from_datahub(unlocode: str) -> Optional[Dict[str, Any]]:
	if not is_datahub_un_locode_enabled():
		return None
	u = (unlocode or "").strip().upper()
	if len(u) != 5:
		return None
	try:
		ensure_datahub_un_locode_files()
		idx = _get_codelist_index()
		if not idx:
			return None
		row = idx.get(u)
		if not row:
			return None
		return datahub_row_to_unlocode_dict(u, row)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"DataHub UN/LOCODE lookup {u}: {e!s}")
		return None


@frappe.whitelist()
def refresh_datahub_un_locode_cache():
	frappe.only_for("System Manager")
	global _INDEX, _INDEX_VERSION, _COUNTRY_NAMES, _STATUS_LABEL_BY_CODE
	_INDEX = None
	_INDEX_VERSION = None
	_COUNTRY_NAMES = None
	_STATUS_LABEL_BY_CODE = None
	meta = _load_meta()
	old_v = meta.get("version") if meta else None
	if old_v:
		try:
			os.remove(os.path.join(_cache_dir(), META_FILE))
		except OSError:
			pass
	v = ensure_datahub_un_locode_files()
	return {"ok": True, "version": v, "previous_version": old_v}
