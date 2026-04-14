# Sales Quote rep fields vs operational DocTypes

## Reference: Sales Quote (`Sales Quote`)

On the **Accounts** tab, `sales_quote.json` defines three `Link` fields to **Employee**, all **required**, with the same filters used on the Employee custom checkboxes:

| UI label | Field name | Options | `link_filters` |
|----------|------------|---------|----------------|
| Sales Rep | `sales_rep` | Employee | `[["Employee","custom_sales_rep","=",1]]` |
| Operations Rep | `operations_rep` | Employee | `[["Employee","custom_operations_rep","=",1]]` |
| Customer Service Rep | `customer_service_rep` | Employee | `[["Employee","custom_customer_service_rep","=",1]]` |

There is no separate field named `operator`; the role described as “Operator” in business language matches **Operations Rep** (`operations_rep`).

Custom flags on Employee live in `logistics/logistics/custom/employee.json` (`custom_sales_rep`, `custom_operations_rep`, `custom_customer_service_rep`).

## Parity check (DocType JSON)

Searched for `sales_rep`, `operations_rep`, and `customer_service_rep` in each target DocType’s JSON.

### Freight (bookings, shipment, transport)

| DocType | Sales Rep | Operations Rep | Customer Service Rep |
|---------|-----------|----------------|----------------------|
| Air Booking | No | No | No |
| Sea Booking | No | No | No |
| Sea Shipment | No | No | No |
| Transport Order | No | No | No |
| Transport Job | No | No | No |

### Customs

| DocType | Sales Rep | Operations Rep | Customer Service Rep |
|---------|-----------|----------------|----------------------|
| Declaration Order | No | No | No |
| Declaration | No | No | No |

### Warehousing

There is **no** DocType named “Warehouse Order” in this app. **Warehouse orders** are modeled as separate DocTypes; each was checked:

| DocType | Sales Rep | Operations Rep | Customer Service Rep |
|---------|-----------|----------------|----------------------|
| Inbound Order | No | No | No |
| Release Order | No | No | No |
| Transfer Order | No | No | No |
| Stocktake Order | No | No | No |
| VAS Order | No | No | No |
| Warehouse Job | No | No | No |

## Summary

- **None** of the DocTypes above define the same three Employee link fields (with Sales Quote’s labels and `link_filters`) as Sales Quote.
- There are **no** matching assignments in Python under `logistics/**/*.py` for these field names either (as of this audit).
- To align with Sales Quote, each relevant DocType would need the three fields in JSON (and `field_order` / tab placement), plus any copy/default logic from Sales Quote or upstream documents if required by process.

---

*Audit date: 2026-04-04. Source: `logistics/pricing_center/doctype/sales_quote/sales_quote.json` and grep across listed DocType JSON paths under `logistics/`.*
