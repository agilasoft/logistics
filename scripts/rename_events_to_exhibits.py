#!/usr/bin/env python3
"""One-off: rename logistics/events package and Event* symbols to exhibits/Exhibit*."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "logistics"
EVENTS = APP / "events"
EXHIBITS = APP / "exhibits"

# Longest-first string replacements inside exhibits module + selected app files.
TEXT_REPLACEMENTS = [
	("Event Job Resource", "Exhibit Job Resource"),
	("Event Job Participant", "Exhibit Job Participant"),
	("Event Activity Status Report", "Exhibit Activity Status Report"),
	("Event Billing Status Report", "Exhibit Billing Status Report"),
	("Event Pipeline Report", "Exhibit Pipeline Report"),
	("Event Scoping Activity", "Exhibit Scoping Activity"),
	("Event Service Activity", "Exhibit Service Activity"),
	("Event Job Resource", "Exhibit Job Resource"),
	("event_participants", "exhibit_participants"),
	("event_job_participant", "exhibit_job_participant"),
	("event_job_resource", "exhibit_job_resource"),
	("event_scoping_activity", "exhibit_scoping_activity"),
	("event_service_activity", "exhibit_service_activity"),
	("event_activity_status_report", "exhibit_activity_status_report"),
	("event_billing_status_report", "exhibit_billing_status_report"),
	("event_pipeline_report", "exhibit_pipeline_report"),
	("event_job_participant", "exhibit_job_participant"),
	("event_participant", "exhibit_participant"),
	("event_milestone", "exhibit_milestone"),
	("event_settings", "exhibit_settings"),
	("event_delivery", "exhibit_delivery"),
	("event_billing", "exhibit_billing"),
	("event_charges", "exhibit_charges"),
	("event_order", "exhibit_order"),
	("event_type", "exhibit_type"),
	("event_lifecycle", "exhibit_lifecycle"),
	("Event Participant", "Exhibit Participant"),
	("Event Milestone", "Exhibit Milestone"),
	("Event Settings", "Exhibit Settings"),
	("Event Delivery", "Exhibit Delivery"),
	("Event Billing", "Exhibit Billing"),
	("Event Charges", "Exhibit Charges"),
	("Event Scoping Activity", "Exhibit Scoping Activity"),
	("Event Service Activity", "Exhibit Service Activity"),
	("Event Job Resource", "Exhibit Job Resource"),
	("Event Job Participant", "Exhibit Job Participant"),
	("Event Job", "Exhibit Job"),
	("Event Order", "Exhibit Order"),
	("Event Plan", "Exhibit Plan"),
	("Event Type", "Exhibit Type"),
	('logistics.events.', 'logistics.exhibits.'),
	('logistics/events/', 'logistics/exhibits/'),
	('"module": "Events"', '"module": "Exhibits"'),
	('"Events"', '"Exhibits"'),
	('main_service == \\"Events\\"', 'main_service == \\"Exhibits\\"'),
	('["Special Project","Events"]', '["Special Project","Exhibits"]'),
	('\\nEvents', '\\nExhibits'),
	('product_type = "Events"', 'product_type = "Exhibits"'),
	('"Event": "Events"', '"Exhibit": "Exhibits"'),
	('"Event Job": "Events"', '"Exhibit Job": "Exhibits"'),
	('"Event Order": "Events"', '"Exhibit Order": "Exhibits"'),
	('"Events": "events"', '"Exhibits": "exhibits"'),
	('"exhibits": "Events"', '"exhibits": "Exhibits"'),
	('"Events": "Event Job"', '"Exhibits": "Exhibit Job"'),
	('"exhibits": "Event Job"', '"exhibits": "Exhibit Job"'),
	(', "events"', ', "exhibits"'),
	('("Events",', '("Exhibits",'),
	('frappe.ui.form.on("Event"', 'frappe.ui.form.on("Exhibit"'),
	('doctype: "Event"', 'doctype: "Exhibit"'),
	('scroll_doctype="Event"', 'scroll_doctype="Exhibit"'),
	('options": "Event"', 'options": "Exhibit"'),
	('link_doctype": "Event', 'link_doctype": "Exhibit'),
	('ref_doctype": "Event"', 'ref_doctype": "Exhibit"'),
	('frappe.get_doc("Event"', 'frappe.get_doc("Exhibit"'),
	('frappe.new_doc("Event"', 'frappe.new_doc("Exhibit"'),
	('frappe.db.exists("Event"', 'frappe.db.exists("Exhibit"'),
	('get_value("Event"', 'get_value("Exhibit"'),
	('set_value("Event"', 'set_value("Exhibit"'),
	('parenttype") == "Event"', 'parenttype") == "Exhibit"'),
	('parenttype": "Event"', 'parenttype": "Exhibit"'),
	('st == "Event"', 'st == "Exhibit"'),
	('label": "Event"', 'label": "Exhibit"'),
	('label": "Event ', 'label": "Exhibit '),
	('Event Details', 'Exhibit Details'),
	('Event Name', 'Exhibit Name'),
	('Event Open Date', 'Exhibit Open Date'),
	('Event Close Date', 'Exhibit Close Date'),
	('Event Venue', 'Exhibit Venue'),
	('Event Participants', 'Exhibit Participants'),
	('Event at most', 'Exhibit at most'),
	('class Event(', 'class Exhibit('),
	('test_event.py', 'test_exhibit.py'),
	('test_event_order.py', 'test_exhibit_order.py'),
	('"name": "Event"', '"name": "Exhibit"'),
	('"Event",', '"Exhibit",'),
	(' "Event"', ' "Exhibit"'),
	('ensure_events_workspace', 'ensure_exhibits_workspace'),
	('sync_events_desktop_icon', 'sync_exhibits_desktop_icon'),
	('add_events_to_desktop', 'add_exhibits_to_desktop'),
	('backfill_sales_quote_main_service_events', 'backfill_sales_quote_main_service_exhibits'),
	('migrate_event_booth', 'migrate_exhibit_booth'),
	('rename_events_to_exhibits', 'rename_events_to_exhibits'),
	('rename_show_link_to_event', 'rename_show_link_to_exhibit'),
	('rename_exhibits_to_events', 'rename_exhibits_to_events'),
	('remove_event_venue', 'remove_exhibit_venue'),
	('seed_event_type', 'seed_exhibit_type'),
]

CROSS_APP_FILES = [
	APP / "hooks.py",
	APP / "modules.txt",
	APP / "patches.txt",
	APP / "desktop_icon/events.json",
	APP / "workspace_sidebar/events.json",
	APP / "utils/charge_service_type.py",
	APP / "document_management/api.py",
	APP / "pricing_center/doctype/sales_quote/sales_quote.py",
	APP / "pricing_center/doctype/sales_quote/sales_quote.json",
	APP / "pricing_center/doctype/sales_quote/sales_quote.js",
	APP / "logistics/doctype/internal_job_detail/internal_job_detail.json",
	APP / "patches/v1_0_create_exhibit_templates.py",
	APP / "patches/v1_0_migrate_event_booth_no_to_participants.py",
]


def _rename_path(path: Path) -> Path:
	name = path.name
	if name.startswith("event_"):
		name = "exhibit_" + name[6:]
	elif name.startswith("event."):
		name = "exhibit." + name[6:]
	elif name == "event":
		name = "exhibit"
	elif name == "events":
		name = "exhibits"
	elif name == "test_event.py":
		name = "test_exhibit.py"
	elif name == "test_event_order.py":
		name = "test_exhibit_order.py"
	elif name == "event_doctype_compat.py":
		return path  # deleted separately
	elif name == "event_lifecycle.py":
		name = "exhibit_lifecycle.py"
	return path.parent / name


def _rename_tree(root: Path):
	for dirpath, dirnames, filenames in os.walk(root, topdown=False):
		dp = Path(dirpath)
		for fn in filenames:
			if fn.endswith(".pyc") or fn == "__pycache__":
				continue
			old = dp / fn
			new = _rename_path(old)
			if new != old and not new.exists():
				old.rename(new)
		for dn in list(dirnames):
			if dn == "__pycache__":
				continue
			old = dp / dn
			new = _rename_path(old)
			if new != old and not new.exists():
				old.rename(new)


def _apply_replacements(path: Path):
	if not path.is_file() or path.suffix not in {".py", ".js", ".json", ".md", ".txt"}:
		return
	text = path.read_text(encoding="utf-8")
	orig = text
	for old, new in TEXT_REPLACEMENTS:
		text = text.replace(old, new)
	# fieldname event -> exhibit when link field (careful)
	text = re.sub(
		r'("fieldname": "event")',
		'"fieldname": "exhibit"',
		text,
	)
	text = re.sub(
		r'(getattr\(doc, "event")',
		'getattr(doc, "exhibit"',
		text,
	)
	if text != orig:
		path.write_text(text, encoding="utf-8")


def main():
	if EXHIBITS.exists():
		shutil.rmtree(EXHIBITS)
	shutil.move(str(EVENTS), str(EXHIBITS))

	# workspace path exhibits/exhibits/
	ws_old = EXHIBITS / "workspace" / "events"
	ws_new = EXHIBITS / "workspace" / "exhibits"
	if ws_old.exists():
		ws_old.rename(ws_new)
		inner = ws_new / "events.json"
		if inner.exists():
			inner.rename(ws_new / "exhibits.json")

	_rename_tree(EXHIBITS)

	compat = EXHIBITS / "event_doctype_compat.py"
	if compat.exists():
		compat.unlink()

	for path in [EXHIBITS] + CROSS_APP_FILES:
		if isinstance(path, Path) and path.exists():
			if path.is_file():
				_apply_replacements(path)
			else:
				for f in path.rglob("*"):
					if f.is_file():
						_apply_replacements(f)

	# desktop / sidebar json files
	for old_name, new_name in (
		(APP / "desktop_icon/events.json", APP / "desktop_icon/exhibits.json"),
		(APP / "workspace_sidebar/events.json", APP / "workspace_sidebar/exhibits.json"),
	):
		if old_name.exists():
			if new_name.exists():
				old_name.unlink()
			else:
				old_name.rename(new_name)
			_apply_replacements(new_name)

	print("Renamed events → exhibits")


if __name__ == "__main__":
	main()
