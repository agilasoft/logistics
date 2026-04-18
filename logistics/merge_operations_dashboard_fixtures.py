# Merge operations workspace HTML + CSS + JS into logistics/fixtures/custom_html_block.json
# Usage (bench root): python3 apps/logistics/logistics/merge_operations_dashboard_fixtures.py

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APPS_LOGISTICS = os.path.dirname(HERE)
# Running this file prepends HERE (.../apps/logistics/logistics) to sys.path, so
# `import logistics` would load the nested logistics/logistics package instead of the app.
if sys.path and os.path.abspath(sys.path[0]) == os.path.abspath(HERE):
	sys.path.pop(0)
sys.path.insert(0, APPS_LOGISTICS)
FIXTURE = os.path.join(HERE, "fixtures", "custom_html_block.json")

BLOCKS = (
	("Air Freight Operations Dashboard", "air_freight"),
	("Sea Freight Operations Dashboard", "sea_freight"),
	("Customs Operations Dashboard", "customs"),
	("Transport Operations Dashboard", "transport"),
)


def main():
	from logistics.air_freight.doctype.air_booking.air_booking_dashboard import AIR_BOOKING_DASH_CSS
	from logistics.document_management.dashboard_layout import RUN_SHEET_LAYOUT_CSS

	with open(FIXTURE, encoding="utf-8") as f:
		data = json.load(f)
	by_name = {row.get("name"): i for i, row in enumerate(data) if row.get("name")}

	for block_name, subdir in BLOCKS:
		folder = os.path.join(HERE, subdir)
		with open(os.path.join(folder, "operations_workspace_block.html"), encoding="utf-8") as f:
			html = f.read().strip()
		with open(os.path.join(folder, "operations_workspace_block_extra.css"), encoding="utf-8") as f:
			extra = f.read().strip()
		with open(os.path.join(folder, "operations_workspace_block.js"), encoding="utf-8") as f:
			script = f.read()
		style = RUN_SHEET_LAYOUT_CSS + "\n" + AIR_BOOKING_DASH_CSS + "\n" + extra
		if block_name in by_name:
			row = data[by_name[block_name]]
			row["html"] = html
			row["style"] = style
			row["script"] = script
		else:
			data.append(
				{
					"doctype": "Custom HTML Block",
					"name": block_name,
					"owner": "Administrator",
					"private": 0,
					"html": html,
					"style": style,
					"script": script,
				}
			)
		print("Merged", block_name, "script", len(script))

	with open(FIXTURE, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=1, ensure_ascii=False)
		f.write("\n")
	print("Updated", FIXTURE)


if __name__ == "__main__":
	main()
