#!/usr/bin/env python3
"""Convert frm.add_custom_button to logistics.menu.add with permission gates."""
import re
from pathlib import Path

LABEL_OPTS = {
    "Sales Invoice": {"ptype": "create", "doctype": "Sales Invoice"},
    "Purchase Invoice": {"ptype": "create", "doctype": "Purchase Invoice"},
    "Change Request": {"ptype": "create", "doctype": "Change Request"},
    "Run Sheet": {"ptype": "create", "doctype": "Run Sheet"},
    "Declaration": {"ptype": "create", "doctype": "Declaration"},
    "Declaration Order": {"ptype": "create", "doctype": "Declaration Order"},
    "Create Transport Order": {"ptype": "create", "doctype": "Transport Order"},
    "Create Air Booking": {"ptype": "create", "doctype": "Air Booking"},
    "Create Sea Booking": {"ptype": "create", "doctype": "Sea Booking"},
    "Create Run Sheet": {"ptype": "create", "doctype": "Run Sheet"},
    "Create Sales Quote": {"ptype": "create", "doctype": "Sales Quote"},
    "Add Sales Quote": {"ptype": "create", "doctype": "Sales Quote"},
    "Create Sales Invoice": {"ptype": "create", "doctype": "Sales Invoice"},
    "Create Special Project": {"ptype": "create", "doctype": "Special Project"},
    "Create Docket": {"ptype": "create", "doctype": "Docket"},
    "Create Warehouse Contract": {"ptype": "create", "doctype": "Warehouse Contract"},
    "Create Declaration": {"ptype": "create", "doctype": "Declaration"},
    "Create e-AWB": {"ptype": "create", "doctype": "Air Shipment IATA Transaction"},
    "Create Warehouse Job": {"ptype": "create", "doctype": "Warehouse Job"},
    "Warehouse Job": {"ptype": "create", "doctype": "Warehouse Job"},
    "Inbound Order": {"ptype": "create", "doctype": "Inbound Order"},
    "Release Order": {"ptype": "create", "doctype": "Release Order"},
    "Cross-Docking Order": {"ptype": "create", "doctype": "Cross-Docking Order"},
    "Transfer Order": {"ptype": "create", "doctype": "Transfer Order"},
    "VAS Order": {"ptype": "create", "doctype": "VAS Order"},
    "Stocktake Order": {"ptype": "create", "doctype": "Stocktake Order"},
    "MICE Job": {"ptype": "read", "doctype": "MICE Job"},
    "Job": {"ptype": "create", "doctype": "MICE Job"},
    "Permit Application": {"ptype": "create", "doctype": "Permit Application"},
    "Exemption Certificate": {"ptype": "create", "doctype": "Exemption Certificate"},
    "Create Draft Purchase Invoices": {"ptype": "create", "doctype": "Purchase Invoice"},
    "Request Deposit Refund": {"ptype": "write"},
    "View Declaration Order": {"ptype": "read", "doctype": "Declaration Order"},
    "View Sales Quote": {"ptype": "read", "doctype": "Sales Quote"},
    "View Declaration": {"ptype": "read", "doctype": "Declaration"},
    "View Sales Invoice": {"ptype": "read", "doctype": "Sales Invoice"},
    "View Declaration Orders": {"ptype": "read", "doctype": "Declaration Order"},
    "View Warehouse Contracts": {"ptype": "read", "doctype": "Warehouse Contract"},
    "View Call-Offs": {"ptype": "read", "doctype": "Sales Quote"},
    "View Gate Passes": {"ptype": "read", "doctype": "Gate Pass"},
    "View CASS Billing": {"ptype": "read", "doctype": "CASS Settlement Period"},
    "Open Project": {"ptype": "read", "doctype": "Project"},
    "View Declaration Order": {"ptype": "read", "doctype": "Declaration Order"},
    "Get Documents": {"ptype": "write"},
    "Get Milestones": {"ptype": "write"},
    "Calculate Charges": {"ptype": "write"},
    "Get Additional Charges from Quote": {"ptype": "write"},
    "Get Additional Charges": {"ptype": "write"},
    "Get Charges from Contract": {"ptype": "write"},
    "Get Rates": {"ptype": "write"},
    "Get Rates from Cost Sheet": {"ptype": "write"},
    "Revert Charges": {"ptype": "write"},
    "Fetch Missing Leg Data": {"ptype": "write"},
    "Fetch Count Sheet": {"ptype": "write"},
    "Fetch Charges": {"ptype": "write"},
    "Generate from Template": {"ptype": "write"},
    "Refresh Legs": {"ptype": "write"},
    "Sync to Transport Legs": {"ptype": "write"},
    "Create Support Legs": {"ptype": "write"},
    "Jobs": {"ptype": "write"},
    "Run Sheets": {"ptype": "create", "doctype": "Run Sheet"},
    "Process File": {"ptype": "write"},
    "Extend Validity": {"ptype": "write"},
    "Copy Quotation Services": {"ptype": "write"},
    "Apply Lifecycle Template": {"ptype": "write"},
    "Refresh Delivery Funnel": {"ptype": "write"},
    "Suggest contributors for leg": {"ptype": "write"},
    "Get Count Items": {"ptype": "write"},
    "Create Operations": {"ptype": "write"},
    "Populate Adjustments": {"ptype": "write"},
    "Post by Scan": {"ptype": "write"},
    "Create Gate Passes": {"ptype": "write"},
    "Refresh refund checklist": {"ptype": "write"},
    "Sign e-AWB": {"ptype": "write"},
    "Submit e-AWB": {"ptype": "write"},
    "Lookup TACT Rate": {"ptype": "write"},
    "Validate DG (AutoCheck)": {"ptype": "write"},
    "Lalamove": {"ptype": "write"},
    "Services": {"ptype": "write"},
    "Fetch from Sales Quote": {"ptype": "write"},
    "Acknowledge": {"ptype": "write"},
    "Standard Costs": {"ptype": "write", "also": [{"doctype": "Journal Entry", "ptype": "create"}]},
    "Post Standard Costs": {"ptype": "write", "also": [{"doctype": "Journal Entry", "ptype": "create"}]},
    "Intercompany Transactions": {"ptype": "write", "also": [{"doctype": "Sales Invoice", "ptype": "create"}, {"doctype": "Purchase Invoice", "ptype": "create"}]},
    "Internal Billing": {"ptype": "write", "also": [{"doctype": "Journal Entry", "ptype": "create"}]},
    "WIP and Accrual": {"ptype": "write", "also": [{"doctype": "Journal Entry", "ptype": "create"}]},
    "Adjust WIP": {"ptype": "write", "also": [{"doctype": "Journal Entry", "ptype": "create"}]},
    "Adjust Accruals": {"ptype": "write", "also": [{"doctype": "Journal Entry", "ptype": "create"}]},
    "Close Recognition": {"ptype": "write", "also": [{"doctype": "Journal Entry", "ptype": "create"}]},
    "Post Receiving": {"ptype": "write"},
    "Post Putaway": {"ptype": "write"},
    "Post Pick": {"ptype": "write"},
    "Post Release": {"ptype": "write"},
    "Post VAS Pick": {"ptype": "write"},
    "Post VAS": {"ptype": "write"},
    "Post VAS Putaway": {"ptype": "write"},
}

SKIP_FILES = {
    "menu_permission.js", "submitted_child_doc_toolbar.js",
    "get_charges_from_quotation.js", "get_charges_from_tariff.js",
    "time_sensitive_form.js", "job_change_lock.js", "crm_sales_quote_actions.js",
    "sales_invoice_dialog.js", "purchase_invoice_dialog.js",
    "recognition_client.js", "job_readiness.js", "job_charge_reopen.js",
    "air_booking.js", "sea_booking.js", "internal_job_create_from_source.js",
    "logistics_settings.js", "sales_quote_simple.js",
}

FOCUS_GLOBS = [
    "air_freight/doctype/air_shipment/air_shipment.js",
    "sea_freight/doctype/sea_shipment/sea_shipment.js",
    "transport/doctype/transport_order/transport_order.js",
    "transport/doctype/transport_job/transport_job.js",
    "transport/doctype/transport_consolidation/transport_consolidation.js",
    "transport/doctype/transport_plan/transport_plan.js",
    "transport/doctype/run_sheet/run_sheet.js",
    "transport/doctype/transport_leg/transport_leg.js",
    "transport/doctype/transport_vehicle/transport_vehicle.js",
    "customs/doctype/declaration_order/declaration_order.js",
    "customs/doctype/declaration/declaration.js",
    "pricing_center/doctype/sales_quote/sales_quote.js",
    "pricing_center/doctype/sales_quote_pack/sales_quote_pack.js",
    "pricing_center/doctype/change_request/change_request.js",
    "warehousing/doctype/**/*.js",
    "special_projects/doctype/**/*.js",
    "mice/doctype/**/*.js",
    "exhibits/doctype/**/*.js",
    "time_sensitive/doctype/time_sensitive_case/time_sensitive_case.js",
    "air_freight/doctype/air_consolidation/air_consolidation.js",
    "air_freight/doctype/cass_file/cass_file.js",
    "air_freight/doctype/cass_settlement_period/cass_settlement_period.js",
    "air_freight/doctype/master_air_waybill/master_air_waybill.js",
    "air_freight/doctype/dangerous_goods_declaration/dangerous_goods_declaration.js",
    "air_freight/doctype/air_shipment_iata_transaction/air_shipment_iata_transaction.js",
    "sea_freight/doctype/sea_consolidation/sea_consolidation.js",
    "sea_freight/doctype/master_bill/master_bill.js",
    "logistics/doctype/general_job/general_job.js",
    "logistics/doctype/container/container.js",
    "logistics/doctype/unloco/unloco.js",
    "cash_advance/doctype/**/*.js",
    "lalamove/lalamove_form.js",
    "public/js/lalamove_form.js",
    "public/js/purchase_invoice_container_deposit.js",
]


def extract_label(label_expr):
    m = re.search(r"__\(['\"](.+?)['\"]\)", label_expr)
    return m.group(1) if m else None


def find_matching_paren(s, start):
    depth = 0
    i = start
    in_str = None
    escape = False
    while i < len(s):
        c = s[i]
        if in_str:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == in_str:
                in_str = None
        else:
            if c in ("\"", "'", "`"):
                in_str = c
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1


def split_args(inner):
    parts = []
    depth = 0
    cur = ""
    in_str = None
    escape = False
    for ch in inner:
        if in_str:
            cur += ch
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
        else:
            if ch in ("\"", "'", "`"):
                in_str = ch
                cur += ch
            elif ch == "(":
                depth += 1
                cur += ch
            elif ch == ")":
                depth -= 1
                cur += ch
            elif ch == "," and depth == 0:
                parts.append(cur.strip())
                cur = ""
            else:
                cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def convert_call(src, idx, pattern_start):
    paren_start = src.find("(", idx + len(pattern_start))
    if paren_start == -1:
        return None, idx
    paren_end = find_matching_paren(src, paren_start)
    if paren_end == -1:
        return None, idx
    inner = src[paren_start + 1 : paren_end]
    parts = split_args(inner)
    if len(parts) < 2:
        return src[idx : paren_end + 1], paren_end + 1
    label_expr = parts[0]
    action_expr = parts[1]
    group_expr = parts[2] if len(parts) > 2 else None
    label = extract_label(label_expr)
    if not label:
        return src[idx : paren_end + 1], paren_end + 1
    if label in ("Booking / Order", "Internal Job"):
        return src[idx : paren_end + 1], paren_end + 1
    opts = LABEL_OPTS.get(label, {"ptype": "write"})
    indent = re.match(r"^(\s*)", src[:idx].split("\n")[-1]).group(1)
    lines = [f"{indent}logistics.menu.add(frm, {{"]
    lines.append(f"{indent}\tlabel: {label_expr},")
    if group_expr:
        lines.append(f"{indent}\tgroup: {group_expr},")
    lines.append(f"{indent}\tptype: '{opts.get('ptype', 'write')}',")
    if "doctype" in opts:
        lines.append(f"{indent}\tdoctype: '{opts['doctype']}',")
    if "also" in opts:
        also_parts = ", ".join(
            f"{{ doctype: '{a['doctype']}', ptype: '{a['ptype']}' }}" for a in opts["also"]
        )
        lines.append(f"{indent}\talso: [{also_parts}],")
    lines.append(f"{indent}\taction: {action_expr},")
    lines.append(f"{indent}}});")
    return "\n".join(lines), paren_end + 1


def convert_file(path):
    text = path.read_text()
    if "frm.add_custom_button" not in text and "frm.page.add_action_item" not in text:
        return 0
    for pattern in ("frm.page.add_action_item", "frm.add_custom_button"):
        pos = 0
        out = []
        while True:
            idx = text.find(pattern, pos)
            if idx == -1:
                out.append(text[pos:])
                break
            out.append(text[pos:idx])
            rep, new_pos = convert_call(text, idx, pattern)
            out.append(rep)
            pos = new_pos
        text = "".join(out)
    path.write_text(text)
    return text.count("logistics.menu.add")


def main():
    base = Path("/home/frappe/frappe-bench/apps/logistics/logistics")
    files = set()
    for g in FOCUS_GLOBS:
        files.update(base.glob(g))
    changed = []
    for f in sorted(files):
        if f.name in SKIP_FILES:
            continue
        before = f.read_text()
        if "frm.add_custom_button" not in before and "frm.page.add_action_item" not in before:
            continue
        convert_file(f)
        after = f.read_text()
        if before != after:
            remaining = after.count("frm.add_custom_button") + after.count("frm.page.add_action_item")
            changed.append((str(f.relative_to(base.parent)), remaining))
    for fp, rem in changed:
        print(f"{fp} (remaining buttons: {rem})")
    print(f"Changed {len(changed)} files")


if __name__ == "__main__":
    main()
