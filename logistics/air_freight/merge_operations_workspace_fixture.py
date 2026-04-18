# Merge HTML + CSS + JS into logistics/fixtures/custom_html_block.json
# Usage: python3 logistics/air_freight/merge_operations_workspace_fixture.py (from bench root)

import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(ROOT)
BENCH = os.path.abspath(os.path.join(ROOT, "..", "..", "..", ".."))
for p in (os.path.join(BENCH, "apps", "frappe"), os.path.join(BENCH, "apps", "logistics")):
	if p not in sys.path:
		sys.path.insert(0, p)
FIXTURE = os.path.join(APP, "fixtures", "custom_html_block.json")


def main():
	from logistics.air_freight.doctype.air_booking.air_booking_dashboard import AIR_BOOKING_DASH_CSS
	from logistics.document_management.dashboard_layout import RUN_SHEET_LAYOUT_CSS

	with open(os.path.join(ROOT, "operations_workspace_block.html"), encoding="utf-8") as f:
		html = f.read().strip()
	with open(os.path.join(ROOT, "operations_workspace_block_extra.css"), encoding="utf-8") as f:
		extra = f.read().strip()
	with open(os.path.join(ROOT, "operations_workspace_block.js"), encoding="utf-8") as f:
		script = f.read()

	style = RUN_SHEET_LAYOUT_CSS + "\n" + AIR_BOOKING_DASH_CSS + "\n" + extra

	with open(FIXTURE, encoding="utf-8") as f:
		data = json.load(f)
	for row in data:
		if row.get("name") == "Air Freight Operations Dashboard":
			row["html"] = html
			row["style"] = style
			row["script"] = script
			break
	else:
		raise SystemExit("block not found")

	with open(FIXTURE, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=1, ensure_ascii=False)
		f.write("\n")
	print("Updated", FIXTURE, "style chars", len(style), "script chars", len(script))


if __name__ == "__main__":
	main()
