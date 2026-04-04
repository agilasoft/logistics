# Master data: active flag and Link filters

## Summary

All **Link** fields in Logistics DocTypes whose **target DocType** defines a standard “active” style flag get **`link_filters`** so the link search only shows usable rows.

### How targets are detected

The merge tool scans **Frappe**, **ERPNext**, and **Logistics** DocType JSON and, for each target DocType, picks the first matching field (priority order):

1. **`is_active`** = 1  
2. **`active`** (Check) = 1  
3. **`disabled`** = 0 (common on Customer, Item, Address, etc.)  
4. **`enabled`** = 1 (e.g. User)

That yields **119** target DocTypes with a filter rule. **Link** rows in Logistics forms use Frappe’s `link_filters` format: JSON array of `[Target DocType, fieldname, operator, value]`.

### What was applied

- **DocType JSON (Logistics app):** every **Link** field whose `options` is one of those 119 DocTypes gets the corresponding filter merged (no duplicate rows). Latest run added **628** field updates across **217** files (on top of earlier logistics-master-only merges). Re-run the script after adding new Link fields; it is idempotent.
- **Client `get_query`:** when JavaScript replaces the default query (so JSON `link_filters` are not used), filters must include the same logic. **Vehicle Type** queries include **`is_active: 1`**. **Item** `set_query` on Sales Quote and Change Request charge rows includes **`disabled: 0`** next to the custom charge flags. **Transport Job** `set_query` for packages targets **`warehouse_item`** (aligned with the child table field name).

### Re-run the merge

From the Logistics app root (`apps/logistics`):

```bash
python3 logistics/tools/merge_master_link_filters.py
python3 logistics/tools/merge_master_link_filters.py --dry-run   # expect 0 updates when up to date
```

Implementation: `logistics/tools/merge_master_link_filters.py` (expects the bench layout: `apps/frappe`, `apps/erpnext`, `apps/logistics`).

### Targets without a filter

If a linked DocType has **no** `is_active` / `active` (Check) / `disabled` / `enabled` in its definition (e.g. some **Contact** setups, **Branch** in stock ERPNext), the registry has no rule and **no** filter is added—there is nothing consistent to filter on without custom business rules.

---

## Logistics-only masters using `is_active` or `active` (reference table)

Non–child Logistics DocTypes that use **`is_active`** or **`active`** are listed below for reference (party/location/rates). ERPNext/Frappe targets (Customer, Item, …) use **`disabled`** / **`enabled`** instead.

| DocType | Active field |
|--------|----------------|
| Ad-Hoc Transport Factor | is_active |
| Airline | is_active |
| Broker | is_active |
| Cargo Terminal Operator | is_active |
| Commodity | active |
| Consignee | is_active |
| Container | is_active |
| Container Depot | is_active |
| Container Freight Station | is_active |
| Container Mode | is_active |
| Container Type | active |
| Cost Sheet | is_active |
| Customs Authority | is_active |
| Declaration Product Code | active |
| Economic Zone | is_active |
| Emission Factors | is_active |
| Exemption Type | is_active |
| Exporter Category | is_active |
| Flight Route | is_active |
| Freight Agent | is_active |
| Freight Consolidator | is_active |
| IATA Rate Class | is_active |
| Issuing Authority | is_active |
| Permit Type | is_active |
| Plate Coding Rule | is_active |
| Release Type | is_active |
| Settlement Group | is_active |
| Shipper | is_active |
| Shipping Line | is_active |
| Storage Facility | is_active |
| Tariff | is_active |
| Time Zone | is_active |
| Transport Company | is_active |
| Transport Mode | is_active |
| Transport Portal Page | is_active |
| Transport Terminal | is_active |
| Transport Vehicle | is_active |
| Truck Ban Constraint | is_active |
| ULD Type | is_active |
| UNLOCO | is_active |
| Vehicle Make | is_active |
| Vehicle Type | is_active |

---

## Notes

- **Backfill:** `logistics/patches/v1_0_backfill_master_is_active.py` covers selected master tables for data backfill.
- **Exceptions:** If a workflow must allow an inactive linked record, use a dedicated client `get_query` or a small override—do not strip filters globally without a documented reason.
