# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt
"""Merge active/disabled/enabled filters into Link field link_filters on Logistics DocType JSON.

Builds a registry from Frappe, ERPNext, and Logistics DocType definitions (is_active, active
Check, disabled, enabled) and appends the corresponding filter row for every Link field in the
Logistics app whose options match.
"""

from __future__ import unicode_literals

import json
import os
import sys

# Link fields scoped via logistics.address.query_for_* in client JS — JSON link_filters break address_query.
ADDRESS_CLIENT_QUERY_FIELDS = {
    ("Docket", "site"),
    ("MICE Order", "site"),
    ("Exhibit Order", "site"),
    ("MICE Job", "site"),
    ("Exhibit Job", "site"),
    ("Project Order", "site"),
    ("Project Job", "site"),
    ("Lifecycle Job", "sp_site"),
    ("Sea Booking", "shipper_address"),
    ("Sea Booking", "consignee_address"),
    ("Sea Shipment", "shipper_address"),
    ("Sea Shipment", "consignee_address"),
    ("Air Booking", "shipper_address"),
    ("Air Booking", "consignee_address"),
    ("Air Shipment", "shipper_address"),
    ("Air Shipment", "consignee_address"),
    ("MICE Order", "shipper_address"),
    ("MICE Order", "consignee_address"),
    ("MICE Job", "shipper_address"),
    ("MICE Job", "consignee_address"),
    ("Exhibit Job", "shipper_address"),
    ("Exhibit Job", "consignee_address"),
    ("Project Job", "shipper_address"),
    ("Project Job", "consignee_address"),
    ("Warehouse Settings", "warehouse_contract_address"),
}

# CTO link fields with custom get_query — link_filters overwrite the query and merge parent filters
# (e.g. shipping_line) onto Cargo Terminal Operator, causing PermissionError on search.
CTO_CLIENT_QUERY_FIELDS = {
    ("Master Bill", "origin_cto"),
    ("Master Bill", "destination_cto"),
    ("Sea Booking", "origin_cto"),
    ("Sea Booking", "destination_cto"),
    ("Sea Shipment", "origin_cto"),
    ("Sea Shipment", "destination_cto"),
    ("Shipping Line CTO", "sea_cto"),
}

# Charge Bill To fields — Customer.disabled link_filters cause PermissionError (Customer.0).
# Filtering is handled by logistics/public/js/charge_bill_to.js and charge_bill_to.py.
CHARGE_BILL_TO_FIELDS = {
    ("Air Booking Charges", "bill_to"),
    ("Air Shipment Charges", "bill_to"),
    ("Change Request Charge", "bill_to"),
    ("Declaration Charges", "bill_to"),
    ("Declaration Order Charges", "bill_to"),
    ("Exhibit Charges", "bill_to"),
    ("MICE Project Charges", "bill_to"),
    ("Sales Quote Air Freight", "bill_to"),
    ("Sales Quote Charge", "bill_to"),
    ("Sales Quote Customs", "bill_to"),
    ("Sales Quote Sea Freight", "bill_to"),
    ("Sales Quote Transport", "bill_to"),
    ("Sea Booking Charges", "bill_to"),
    ("Sea Shipment Charges", "bill_to"),
    ("Special Project Charges", "bill_to"),
    ("Tariff Charge", "bill_to"),
    ("Transport Job Charges", "bill_to"),
    ("Transport Order Charges", "bill_to"),
}


def _logistics_app_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _apps_dir():
    return os.path.dirname(_logistics_app_root())


def build_filter_registry():
    """DocType name -> (fieldname, operator, value) for link_filters rows."""
    apps = _apps_dir()
    roots = [
        os.path.join(apps, "frappe", "frappe"),
        os.path.join(apps, "erpnext", "erpnext"),
        os.path.join(_logistics_app_root(), "logistics"),
    ]
    import glob

    reg = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for p in glob.glob(os.path.join(root, "**", "doctype", "*", "*.json"), recursive=True):
            try:
                with open(p) as f:
                    d = json.load(f)
            except Exception:
                continue
            if not isinstance(d, dict) or d.get("doctype") != "DocType":
                continue
            name = d.get("name")
            if not name:
                continue
            fields = d.get("fields") or []
            if not isinstance(fields, list):
                continue
            fnames = set()
            for f in fields:
                if isinstance(f, dict) and f.get("fieldname"):
                    fnames.add(f["fieldname"])
            filt = None
            if "is_active" in fnames:
                filt = ("is_active", "=", 1)
            elif "active" in fnames:
                fld = next(
                    (f for f in fields if isinstance(f, dict) and f.get("fieldname") == "active"),
                    None,
                )
                if fld and fld.get("fieldtype") == "Check":
                    filt = ("active", "=", 1)
            elif "disabled" in fnames:
                filt = ("disabled", "=", 0)
            elif "enabled" in fnames:
                filt = ("enabled", "=", 1)
            if filt:
                reg[name] = filt
    return reg


def merge_link_filters(lf, target_dt, field, op, value):
    if lf is None or lf == "":
        arr = []
    else:
        try:
            arr = json.loads(lf)
        except Exception:
            arr = []
    for row in arr:
        if len(row) >= 4 and tuple(row[:4]) == (target_dt, field, op, value):
            return None
    arr.append([target_dt, field, op, value])
    return json.dumps(arr)


def main():
    base = _logistics_app_root()
    dry = "--dry-run" in sys.argv
    registry = build_filter_registry()
    import glob

    paths = glob.glob(os.path.join(base, "**", "doctype", "*", "*.json"), recursive=True)
    updated_files = 0
    updated_fields = 0
    for p in paths:
        with open(p) as f:
            try:
                d = json.load(f)
            except Exception:
                continue
        if d.get("doctype") != "DocType":
            continue
        changed = False
        for fld in d.get("fields") or []:
            if fld.get("fieldtype") != "Link":
                continue
            opt = fld.get("options")
            if not opt or not isinstance(opt, str):
                continue
            if opt not in registry:
                continue
            if opt == "Address" and (d.get("name"), fld.get("fieldname")) in ADDRESS_CLIENT_QUERY_FIELDS:
                continue
            if opt == "Cargo Terminal Operator" and (d.get("name"), fld.get("fieldname")) in CTO_CLIENT_QUERY_FIELDS:
                continue
            if opt == "Customer" and (d.get("name"), fld.get("fieldname")) in CHARGE_BILL_TO_FIELDS:
                continue
            field, op, value = registry[opt]
            new_lf = merge_link_filters(fld.get("link_filters"), opt, field, op, value)
            if new_lf is not None:
                fld["link_filters"] = new_lf
                changed = True
                updated_fields += 1
        if changed:
            updated_files += 1
            if not dry:
                with open(p, "w") as f:
                    json.dump(d, f, indent=1, sort_keys=False)
                    f.write("\n")
    print("Registry DocTypes (with active flag): %s" % len(registry))
    print("Files updated: %s" % updated_files)
    print("Link fields updated: %s" % updated_fields)
    if dry:
        print("(dry-run: no files written)")


if __name__ == "__main__":
    main()
