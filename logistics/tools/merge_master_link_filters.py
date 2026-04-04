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
