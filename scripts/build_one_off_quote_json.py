#!/usr/bin/env python3
"""
Build One-Off Quote JSON from Sales Quote: same layout (tabs), header charge params, status/converted_to_doc.
Run from repo root: python3 scripts/build_one_off_quote_json.py
"""
import json
import copy

SQ_PATH = "logistics/pricing_center/doctype/sales_quote/sales_quote.json"
OQ_PATH = "logistics/pricing_center/doctype/one_off_quote/one_off_quote.json"

with open(SQ_PATH) as f:
    sq = json.load(f)

# Deep copy and base changes
oq = copy.deepcopy(sq)
oq["name"] = "One-Off Quote"
oq["modified"] = "2026-02-11 00:00:00.000000"
# Naming
for f in oq["fields"]:
    if f.get("fieldname") == "naming_series":
        f["options"] = "OOQ-.#####"
        break
# Remove contract-only fields
REMOVE = {"amended_from", "additional_charge", "job_type", "job"}
oq["field_order"] = [x for x in oq["field_order"] if x not in REMOVE]
oq["fields"] = [f for f in oq["fields"] if f.get("fieldname") not in REMOVE]

# Add status after valid_until
idx = oq["field_order"].index("valid_until") + 1
for x in ["status_section", "status", "converted_to_doc"]:
    oq["field_order"].insert(idx, x)
    idx += 1

# Status field definitions
status_fields = [
    {"fieldname": "status_section", "fieldtype": "Section Break", "label": "Status"},
    {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Draft\nConverted", "default": "Draft", "read_only": 1},
    {"fieldname": "converted_to_doc", "fieldtype": "Data", "label": "Converted To", "read_only": 1},
]
# Insert status fields after valid_until in fields array
fidx = next(i for i, f in enumerate(oq["fields"]) if f.get("fieldname") == "valid_until") + 1
for sf in reversed(status_fields):
    oq["fields"].insert(fidx, sf)

# Table options: Sales Quote X -> One-Off Quote X
TABLE_MAP = {
    "Sales Quote Sea Freight": "One-Off Quote Sea Freight",
    "Sales Quote Air Freight": "One-Off Quote Air Freight",
    "Sales Quote Transport": "One-Off Quote Transport",
    "Sales Quote Customs": "One-Off Quote Customs",
    "Sales Quote Warehouse": "One-Off Quote Warehouse",
}
for f in oq["fields"]:
    if f.get("options") in TABLE_MAP:
        f["options"] = TABLE_MAP[f["options"]]

# Header charge parameters for One-Off (insert after each tab, before table)
# Sea: after sea_tab, before sea_freight
SEA_PARAMS = ["oo_sea_section", "sea_load_type", "sea_direction", "sea_transport_mode", "shipping_line", "freight_agent_sea", "column_break_oo_sea", "sea_weight", "sea_volume", "sea_chargeable", "sea_weight_uom", "sea_volume_uom", "sea_chargeable_uom", "origin_port_sea", "destination_port_sea"]
AIR_PARAMS = ["oo_air_section", "air_load_type", "air_direction", "airline", "freight_agent", "air_house_type", "column_break_oo_air", "origin_port", "destination_port"]
TRANSPORT_PARAMS = ["oo_transport_section", "transport_template", "load_type", "vehicle_type", "container_type", "column_break_oo_transport", "location_type", "location_from", "location_to", "pick_mode", "drop_mode"]

def insert_after(oq, after_field, new_fields):
    i = oq["field_order"].index(after_field) + 1
    for x in reversed(new_fields):
        oq["field_order"].insert(i, x)

insert_after(oq, "sea_tab", SEA_PARAMS)
insert_after(oq, "air_tab", AIR_PARAMS)
insert_after(oq, "transport_tab", TRANSPORT_PARAMS)

# Field definitions for header params (all with depends_on for their tab)
SEA_FIELD_DEFS = [
    {"depends_on": "eval:doc.is_sea", "fieldname": "oo_sea_section", "fieldtype": "Section Break", "label": "Charge Parameters"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "sea_load_type", "fieldtype": "Link", "label": "Load Type", "options": "Load Type", "link_filters": "[[\"Load Type\",\"sea\",\"=\",1]]"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "sea_direction", "fieldtype": "Select", "label": "Direction", "options": "Import\nExport"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "sea_transport_mode", "fieldtype": "Select", "label": "Transport Mode", "options": "FCL\nLCL"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "shipping_line", "fieldtype": "Link", "label": "Shipping Line", "options": "Shipping Line"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "freight_agent_sea", "fieldtype": "Link", "label": "Freight Agent", "options": "Freight Agent"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "sea_weight", "fieldtype": "Float", "label": "Weight"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "sea_volume", "fieldtype": "Float", "label": "Volume"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "sea_chargeable", "fieldtype": "Float", "label": "Chargeable"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "column_break_oo_sea", "fieldtype": "Column Break"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "sea_weight_uom", "fieldtype": "Link", "label": "Weight UOM", "options": "UOM"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "sea_volume_uom", "fieldtype": "Link", "label": "Volume UOM", "options": "UOM"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "sea_chargeable_uom", "fieldtype": "Link", "label": "Chargeable UOM", "options": "UOM"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "origin_port_sea", "fieldtype": "Link", "label": "Origin Port", "options": "UNLOCO"},
    {"depends_on": "eval:doc.is_sea", "fieldname": "destination_port_sea", "fieldtype": "Link", "label": "Destination Port", "options": "UNLOCO"},
]
AIR_FIELD_DEFS = [
    {"depends_on": "eval:doc.is_air", "fieldname": "oo_air_section", "fieldtype": "Section Break", "label": "Charge Parameters"},
    {"depends_on": "eval:doc.is_air", "fieldname": "air_load_type", "fieldtype": "Link", "label": "Load Type", "options": "Load Type", "link_filters": "[[\"Load Type\",\"air\",\"=\",1]]"},
    {"depends_on": "eval:doc.is_air", "fieldname": "air_direction", "fieldtype": "Select", "label": "Direction", "options": "Import\nExport\nDomestic"},
    {"depends_on": "eval:doc.is_air", "fieldname": "airline", "fieldtype": "Link", "label": "Airline", "options": "Airline"},
    {"depends_on": "eval:doc.is_air", "fieldname": "freight_agent", "fieldtype": "Link", "label": "Freight Agent", "options": "Freight Agent"},
    {"depends_on": "eval:doc.is_air", "fieldname": "air_house_type", "fieldtype": "Select", "label": "House Type", "options": "Standard House\nCo-load Master\nBlind Co-load Master\nCo-load House\nBuyer's Consol Lead\nShipper's Consol Lead\nBreak Bulk"},
    {"depends_on": "eval:doc.is_air", "fieldname": "column_break_oo_air", "fieldtype": "Column Break"},
    {"depends_on": "eval:doc.is_air", "fieldname": "origin_port", "fieldtype": "Link", "label": "Origin Port", "options": "UNLOCO"},
    {"depends_on": "eval:doc.is_air", "fieldname": "destination_port", "fieldtype": "Link", "label": "Destination Port", "options": "UNLOCO"},
]
TRANSPORT_FIELD_DEFS = [
    {"depends_on": "eval:doc.is_transport", "fieldname": "oo_transport_section", "fieldtype": "Section Break", "label": "Charge Parameters"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "transport_template", "fieldtype": "Link", "label": "Transport Template", "options": "Transport Template"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "load_type", "fieldtype": "Link", "label": "Load Type", "options": "Load Type", "link_filters": "[[\"Load Type\",\"transport\",\"=\",1]]"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "vehicle_type", "fieldtype": "Link", "label": "Vehicle Type", "options": "Vehicle Type"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "container_type", "fieldtype": "Link", "label": "Container Type", "options": "Container Type"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "column_break_oo_transport", "fieldtype": "Column Break"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "location_type", "fieldtype": "Link", "label": "Location Type", "options": "DocType", "link_filters": "[[\"DocType\",\"name\",\"in\",[\"UNLOCO\",\"Transport Zone\"]]]"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "location_from", "fieldtype": "Dynamic Link", "label": "Location From", "options": "location_type"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "location_to", "fieldtype": "Dynamic Link", "label": "Location To", "options": "location_type"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "pick_mode", "fieldtype": "Data", "label": "Pick Mode"},
    {"depends_on": "eval:doc.is_transport", "fieldname": "drop_mode", "fieldtype": "Data", "label": "Drop Mode"},
]

# Insert field defs: after sea_tab def, after air_tab def, after transport_tab def
def insert_field_defs_after(fields, after_fieldname, new_defs):
    i = next((j for j, f in enumerate(fields) if f.get("fieldname") == after_fieldname), -1) + 1
    for d in reversed(new_defs):
        fields.insert(i, d)

insert_field_defs_after(oq["fields"], "sea_tab", SEA_FIELD_DEFS)
insert_field_defs_after(oq["fields"], "air_tab", AIR_FIELD_DEFS)
insert_field_defs_after(oq["fields"], "transport_tab", TRANSPORT_FIELD_DEFS)

# One-Off Quote: not submittable (conversion creates order from draft or we keep submittable - design says one conversion; keep submittable so Create button can require submit)
# Remove links that reference Sales Quote
oq["links"] = []
# Optional: allow_import for One-Off
oq["allow_import"] = 1

with open(OQ_PATH, "w") as f:
    json.dump(oq, f, indent=1)

print("Written", OQ_PATH)
