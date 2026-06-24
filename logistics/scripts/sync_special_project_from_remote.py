"""Fetch Special Project from remote Frappe site; update existing target doc."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

import frappe
from frappe import _
from frappe.model.document import copy_doc

from logistics.scripts.copy_document_between_sites import _load_from_site
from logistics.scripts.update_special_project_from_site import _apply_source_to_target


REMOTE_SITES = {
	"atndemo.cargonext.io": "https://atndemo.s.frappe.cloud",
	"atndemo.s.frappe.cloud": "https://atndemo.s.frappe.cloud",
}


def run(
	source_name: str = "PROJ-0011",
	target_name: str = "PROJ-0110",
	source_site: str = "atndemo.cargonext.io",
	api_key: str | None = None,
	api_secret: str | None = None,
):
	"""Pull *source_name* from atndemo and overwrite fields on *target_name* on current site."""
	if not frappe.db.exists("Special Project", target_name):
		frappe.throw(_("Target Special Project {0} was not found.").format(target_name))

	src_doc = _load_remote_or_local(source_site, source_name, api_key, api_secret)
	prepared = copy_doc(src_doc, ignore_no_copy=True)

	target = frappe.get_doc("Special Project", target_name)
	_apply_source_to_target(prepared, target)

	frappe.set_user("Administrator")
	target.flags.ignore_validate = True
	target.flags.ignore_links = True
	target.save(ignore_permissions=True)
	frappe.db.commit()

	result = {
		"source_site": source_site,
		"source_name": source_name,
		"target_name": target_name,
		"project_name": target.project_name,
		"child_counts": _child_counts(target),
	}
	print(frappe.as_json(result))
	return result


def _load_remote_or_local(source_site: str, name: str, api_key: str | None, api_secret: str | None):
	base_url = REMOTE_SITES.get(source_site)
	if base_url and api_key and api_secret:
		data = _fetch_remote_doc(base_url, "Special Project", name, api_key, api_secret)
		data["doctype"] = "Special Project"
		return frappe.get_doc(data)

	# Same-bench fallback when remote auth is unavailable.
	for local_site in (source_site, "cargonext.io"):
		if local_site in frappe.utils.get_sites() and local_site != frappe.local.site:
			doc = _load_from_site(local_site, "Special Project", name)
			if doc:
				return doc

	frappe.throw(
		_(
			"Cannot load {0} from {1}. Provide api_key and api_secret for {2}."
		).format(name, source_site, REMOTE_SITES.get(source_site, source_site))
	)


def _fetch_remote_doc(base_url: str, doctype: str, name: str, api_key: str, api_secret: str) -> dict:
	url = (
		f"{base_url.rstrip('/')}/api/resource/"
		f"{urllib.parse.quote(doctype)}/{urllib.parse.quote(name)}"
	)
	req = urllib.request.Request(url, headers={"Authorization": f"token {api_key}:{api_secret}"})
	try:
		with urllib.request.urlopen(req, timeout=60) as resp:
			payload = json.loads(resp.read().decode())
	except urllib.error.HTTPError as exc:
		body = exc.read().decode(errors="replace")
		frappe.throw(_("Remote fetch failed ({0}): {1}").format(exc.code, body[:500]))
	return payload.get("data") or payload


def _child_counts(doc) -> dict:
	counts = {}
	for df in doc.meta.fields:
		if df.fieldtype == "Table":
			counts[df.fieldname] = len(doc.get(df.fieldname) or [])
	return counts
