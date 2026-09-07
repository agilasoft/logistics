# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Optional iiNET SFTP pull for CASSLink inbound files.

Desk attach on CASS File is the working import path. This client only runs when
IATA Settings has an iiNET SFTP host.
"""

from __future__ import unicode_literals

from typing import Any, Dict, List, Optional

import frappe


def pull_configured_companies() -> List[Dict[str, Any]]:
	"""Daily scheduler entry: pull for every company with CASS + SFTP host."""
	results = []
	if not frappe.db.table_exists("IATA Settings"):
		return results
	if not frappe.db.has_column("IATA Settings", "cass_iinet_host"):
		return results
	names = frappe.get_all(
		"IATA Settings",
		filters={"cass_enabled": 1},
		pluck="name",
	)
	for name in names:
		settings = frappe.get_doc("IATA Settings", name)
		if not getattr(settings, "cass_iinet_host", None):
			continue
		results.append(pull_inbound_files(settings.company))
	return results


def pull_inbound_files(company: Optional[str] = None) -> Dict[str, Any]:
	from logistics.air_freight.utils.iata_settings_utils import get_settings

	settings = get_settings(company=company)
	if not settings or not settings.cass_enabled:
		return {"skipped": True, "reason": "CASSLink is not enabled"}
	host = getattr(settings, "cass_iinet_host", None)
	if not host:
		return {"skipped": True, "reason": "iiNET host is not configured"}

	try:
		import paramiko
	except ImportError:
		return {"skipped": True, "reason": "paramiko is not installed"}

	username = getattr(settings, "cass_username", None)
	password = None
	key_data = None
	if hasattr(settings, "get_password"):
		password = settings.get_password("cass_password", raise_exception=False)
		key_data = settings.get_password("cass_iinet_private_key", raise_exception=False)
	remote_dir = getattr(settings, "cass_iinet_inbound_folder", None) or "."

	client = paramiko.SSHClient()
	client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	connect_kwargs = {"hostname": host, "username": username, "timeout": 30}
	if key_data:
		from io import StringIO

		connect_kwargs["pkey"] = paramiko.RSAKey.from_private_key(StringIO(key_data))
	elif password:
		connect_kwargs["password"] = password
	else:
		return {"skipped": True, "reason": "CASS / iiNET credentials are not set"}

	downloaded = []
	try:
		client.connect(**connect_kwargs)
		sftp = client.open_sftp()
		try:
			for entry in sftp.listdir_attr(remote_dir):
				if entry.filename.startswith("."):
					continue
				remote_path = f"{remote_dir.rstrip('/')}/{entry.filename}"
				with sftp.open(remote_path, "rb") as fh:
					content = fh.read()
				cass_file = _create_cass_file(settings, content, entry.filename)
				downloaded.append(cass_file)
		finally:
			sftp.close()
	finally:
		client.close()

	return {"skipped": False, "files": downloaded, "company": company or settings.company}


def _store_file(filename: str, content: bytes, cass_file_name: str):
	from frappe.utils.file_manager import save_file

	return save_file(filename, content, "CASS File", cass_file_name, is_private=1)


def _create_cass_file(settings, content: bytes, filename: str) -> Optional[str]:
	from logistics.air_freight.casslink.parser import guess_file_type

	period = frappe.db.get_value(
		"CASS Settlement Period",
		{"company": settings.company, "status": ("in", ["Open", "Imported", "Matched"])},
		"name",
		order_by="period_end desc",
	)
	if not period:
		frappe.logger().info("CASS SFTP pull: no open settlement period for %s", settings.company)
		return None
	doc = frappe.get_doc(
		{
			"doctype": "CASS File",
			"settlement_period": period,
			"company": settings.company,
			"file_type": guess_file_type(filename),
			"direction": "Inbound",
			"status": "Queued",
		}
	)
	doc.insert(ignore_permissions=True)
	file_doc = _store_file(filename, content, doc.name)
	doc.attached_file = file_doc.file_url
	doc.save(ignore_permissions=True)
	return doc.name
