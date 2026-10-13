# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Decisions that keep intercompany invoice creation from repeating itself."""

from __future__ import annotations


# Job types that can be intercompany legs (must have company and charges).
INTERCOMPANY_JOB_TYPES = (
	"Transport Job",
	"Air Shipment",
	"Sea Shipment",
	"Warehouse Job",
	"Declaration",
	"Declaration Order",
)

# Stable prefix on the operating-company Sales Invoice. Kept untranslated so the
# submit hook can tell this invoice apart from the customer invoice.
INTERCOMPANY_SI_REMARKS_PREFIX = "Intercompany:"


def intercompany_sales_invoice_marked(is_intercompany_flag, remarks):
	"""Return True when this Sales Invoice is the operating-company leg.

	The flag set while the pair is created wins. Otherwise the remarks prefix
	identifies an invoice that was already created as the intercompany leg.
	"""
	if is_intercompany_flag:
		return True
	return (remarks or "").strip().startswith(INTERCOMPANY_SI_REMARKS_PREFIX)


def relationship_for_companies(relationships, main_job_company, operating_company):
	"""Return the internal customer and supplier for one company pair.

	``main_job_company`` matches the relationship row's billing company.
	The first matching row wins. No match returns ``None``.
	"""
	for row in relationships or []:
		if row.get("billing_company") == main_job_company and row.get("operating_company") == operating_company:
			return {
				"internal_customer": row.get("internal_customer"),
				"internal_supplier": row.get("internal_supplier"),
			}
	return None


def _text(value) -> str:
	return (value or "").strip()


def _row_value(row, fieldname: str):
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def _set_row_value(row, fieldname: str, value) -> None:
	if isinstance(row, dict):
		row[fieldname] = value
	else:
		setattr(row, fieldname, value)


def purchase_is_same_company_internal_supplier(is_internal_supplier, represents_company, company) -> bool:
	"""ERPNext calls this purchase an internal transfer.

	The supplier is internal and represents the same company as the invoice.
	"""
	return bool(is_internal_supplier) and bool(_text(represents_company)) and _text(represents_company) == _text(company)


def should_link_purchase_to_sales_invoice(
	*,
	purchase_company,
	supplier_name,
	supplier_is_internal,
	supplier_represents_company,
	sales_company,
	sales_customer_represents_company,
	supplier_found_for_sales_company,
) -> bool:
	"""True when ERPNext will accept this purchase as that sales invoice's purchase.

	The supplier must be the supplier that represents the sales company, and the
	sales customer must represent the purchase company.
	"""
	if not supplier_is_internal or not _text(supplier_name):
		return False
	if not _text(purchase_company) or not _text(sales_company):
		return False
	if _text(supplier_represents_company) != _text(sales_company):
		return False
	if _text(sales_customer_represents_company) != _text(purchase_company):
		return False
	return _text(supplier_found_for_sales_company) == _text(supplier_name)


def sales_invoice_items_cover_purchase(sales_item_names, purchase_row_count: int) -> bool:
	"""Every purchase row has a submitted sales invoice item in the same order."""
	if purchase_row_count <= 0:
		return False
	names = list(sales_item_names or [])
	if len(names) < purchase_row_count:
		return False
	return all(_text(names[index]) for index in range(purchase_row_count))


def attach_sales_invoice_reference(purchase, sales) -> None:
	"""Copy the sales invoice onto the purchase header and each matching row."""
	sales_name = _text(getattr(sales, "name", None))
	if not sales_name:
		return
	purchase.inter_company_invoice_reference = sales_name
	sales_rows = list(getattr(sales, "items", None) or [])
	for index, row in enumerate(getattr(purchase, "items", None) or []):
		if index >= len(sales_rows):
			break
		item_name = _text(_row_value(sales_rows[index], "name"))
		if item_name:
			_set_row_value(row, "sales_invoice_item", item_name)


def apply_sales_invoice_reference(
	purchase,
	sales,
	*,
	supplier_is_internal,
	supplier_represents_company,
	sales_customer_represents_company,
	supplier_found_for_sales_company,
	unrealized_profit_loss_account=None,
) -> bool:
	"""Link the purchase to the sales invoice when ERPNext's party check will pass.

	A same-company internal supplier also needs the company's unrealized profit
	or loss account. Without that account the link is left unset so the service
	purchase is not held up as a stock transfer.
	"""
	sales_rows = list(getattr(sales, "items", None) or [])
	purchase_rows = list(getattr(purchase, "items", None) or [])
	sales_item_names = [_row_value(row, "name") for row in sales_rows]
	if not sales_invoice_items_cover_purchase(sales_item_names, len(purchase_rows)):
		return False
	if not should_link_purchase_to_sales_invoice(
		purchase_company=getattr(purchase, "company", None),
		supplier_name=getattr(purchase, "supplier", None),
		supplier_is_internal=supplier_is_internal,
		supplier_represents_company=supplier_represents_company,
		sales_company=getattr(sales, "company", None),
		sales_customer_represents_company=sales_customer_represents_company,
		supplier_found_for_sales_company=supplier_found_for_sales_company,
	):
		return False
	same_company = purchase_is_same_company_internal_supplier(
		supplier_is_internal,
		supplier_represents_company,
		getattr(purchase, "company", None),
	)
	if same_company and not _text(unrealized_profit_loss_account):
		return False
	attach_sales_invoice_reference(purchase, sales)
	if supplier_is_internal:
		purchase.is_internal_supplier = 1
	if _text(supplier_represents_company):
		purchase.represents_company = _text(supplier_represents_company)
	if same_company:
		purchase.unrealized_profit_loss_account = _text(unrealized_profit_loss_account)
	return True


def _doc_flags(doc):
	return getattr(doc, "flags", None)


def logistics_service_purchase(doc) -> bool:
	"""True for a purchase raised from a logistics job or an intercompany pair."""
	flags = _doc_flags(doc)
	if flags and (flags.get("is_intercompany_invoice") or flags.get("logistics_service_purchase")):
		return True
	remarks = (getattr(doc, "remarks", None) or "").strip()
	if remarks.startswith(INTERCOMPANY_SI_REMARKS_PREFIX) or "Auto-created from" in remarks:
		return True
	job_types = set(INTERCOMPANY_JOB_TYPES)
	if _text(getattr(doc, "reference_doctype", None)) in job_types:
		return True
	for row in getattr(doc, "items", None) or []:
		if _text(_row_value(row, "reference_doctype")) in job_types:
			return True
	return False


def sales_reference_is_complete(doc) -> bool:
	if not _text(getattr(doc, "inter_company_invoice_reference", None)):
		return False
	rows = list(getattr(doc, "items", None) or [])
	if not rows:
		return False
	return all(_text(_row_value(row, "sales_invoice_item")) for row in rows)


def release_service_purchase_from_internal_transfer(doc, method=None) -> None:
	"""Let a service purchase save when it is not an internal stock transfer.

	Frappe copies the supplier's internal-transfer fields onto the purchase
	before validate. ERPNext then requires a sales invoice. A logistics cost
	invoice has no stock movement, so the internal-supplier flag is cleared
	unless the sales invoice link is already complete.
	"""
	if getattr(doc, "doctype", None) not in (None, "Purchase Invoice"):
		return
	if not logistics_service_purchase(doc):
		return
	if getattr(doc, "update_stock", 0):
		return
	if sales_reference_is_complete(doc):
		return
	if not purchase_is_same_company_internal_supplier(
		getattr(doc, "is_internal_supplier", None),
		getattr(doc, "represents_company", None),
		getattr(doc, "company", None),
	):
		return
	doc.is_internal_supplier = 0
