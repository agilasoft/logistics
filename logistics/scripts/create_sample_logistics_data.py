# Copyright (c) 2026, www.agilasoft.com and contributors
# Create sample Sales Quote, bookings, jobs/shipments, and related invoices.
# Run: bench --site logistics.agilasoft.com execute logistics.scripts.create_sample_logistics_data.run

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import today, add_days, flt


def run():
    """Create sample logistics data: Sales Quote, bookings, shipments, jobs, and invoices."""
    frappe.db.rollback()
    results = []

    try:
        # 1. Ensure master data
        data = _ensure_master_data()
        results.append({"step": "Master Data", "status": "ok", "data": data})

        company = data["company"]
        customer = data["customer"]
        shipper = data["shipper"]
        consignee = data["consignee"]
        origin = data["origin"]
        dest = data["dest"]
        air_item = data["air_item"]
        sea_item = data["sea_item"]
        transport_item = data["transport_item"]
        supplier = data.get("supplier")
        branch = data.get("branch")
        cost_center = data.get("cost_center")
        profit_center = data.get("profit_center")

        # 2. Create Sales Quote (Air + Sea)
        sq = _create_sales_quote(company, customer, shipper, consignee, origin, dest, air_item, sea_item, branch, cost_center, profit_center)
        sq.save()
        frappe.db.commit()
        results.append({"step": "Sales Quote", "status": "ok", "name": sq.name})

        # 3. Create Air Booking from Sales Quote
        from logistics.pricing_center.doctype.sales_quote.sales_quote import create_air_booking_from_sales_quote
        r_air_booking = create_air_booking_from_sales_quote(sq.name)
        air_booking_name = r_air_booking.get("air_booking")
        if air_booking_name:
            results.append({"step": "Air Booking", "status": "ok", "name": air_booking_name})

            # Set weight/volume on Air Booking (required for convert_to_shipment)
            air_booking = frappe.get_doc("Air Booking", air_booking_name)
            air_booking.weight = 100
            air_booking.volume = 0.5
            air_booking.chargeable = 100
            air_booking.override_volume_weight = 1
            air_booking.save()
            frappe.db.commit()

            # 4. Convert Air Booking to Air Shipment
            r_shipment = air_booking.convert_to_shipment()
            air_shipment_name = r_shipment.get("air_shipment") or r_shipment.get("name")
            frappe.db.commit()
            if air_shipment_name:
                results.append({"step": "Air Shipment", "status": "ok", "name": air_shipment_name})

                # Add charges to Air Shipment
                air_shipment = frappe.get_doc("Air Shipment", air_shipment_name)
                _add_air_charges(air_shipment, air_item)
                air_shipment.save()
                frappe.db.commit()

                # Submit Air Shipment
                air_shipment.submit()
                frappe.db.commit()
                results.append({"step": "Air Shipment Submitted", "status": "ok"})

        # 5. Create Sea Shipment directly from Sales Quote (avoids Sea Booking conversion validation)
        sea_shipment_name = None
        try:
            from logistics.pricing_center.doctype.sales_quote.sales_quote import create_sea_shipment_from_sales_quote
            r_sea = create_sea_shipment_from_sales_quote(sq.name)
            sea_shipment_name = r_sea.get("sea_shipment") or r_sea.get("name")
            frappe.db.commit()
        except Exception as e:
            results.append({"step": "Sea Shipment", "status": "skip", "reason": str(e)})
        if sea_shipment_name:
            results.append({"step": "Sea Shipment", "status": "ok", "name": sea_shipment_name})

            # Add charges to Sea Shipment
            sea_shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
            _add_sea_charges(sea_shipment, sea_item)
            sea_shipment.save()
            frappe.db.commit()

            # Submit Sea Shipment
            sea_shipment.submit()
            frappe.db.commit()
            results.append({"step": "Sea Shipment Submitted", "status": "ok"})

        # 7. Create Transport Order and Job from Air Shipment (optional)
        transport_order_name = None
        transport_job_name = None
        if air_shipment_name:
            try:
                from logistics.utils.module_integration import create_transport_order_from_air_shipment
                r_to = create_transport_order_from_air_shipment(air_shipment_name)
                transport_order_name = r_to.get("transport_order")
                frappe.db.commit()
                if transport_order_name:
                    results.append({"step": "Transport Order", "status": "ok", "name": transport_order_name})

                    # Submit Transport Order (required before creating Transport Job)
                    transport_order = frappe.get_doc("Transport Order", transport_order_name)
                    transport_order.submit()
                    frappe.db.commit()

                    # 8. Create Transport Job from Transport Order
                    from logistics.transport.doctype.transport_order.transport_order import action_create_transport_job
                    r_job = action_create_transport_job(transport_order_name)
                    transport_job_name = r_job.get("name") or r_job.get("transport_job")
                    if not transport_job_name and isinstance(r_job, dict) and r_job.get("transport_jobs"):
                        transport_job_name = r_job["transport_jobs"][0]
                    frappe.db.commit()
                    if transport_job_name:
                        results.append({"step": "Transport Job", "status": "ok", "name": transport_job_name})

                        # Add charges to Transport Job
                        transport_job = frappe.get_doc("Transport Job", transport_job_name)
                        _add_transport_charges(transport_job, transport_item)
                        transport_job.save()
                        frappe.db.commit()

                        # Set status to Completed for Sales Invoice
                        frappe.db.set_value("Transport Job", transport_job_name, "status", "Completed", update_modified=False)
                        frappe.db.commit()

                        # Submit Transport Job
                        transport_job.reload()
                        transport_job.submit()
                        frappe.db.commit()
                        results.append({"step": "Transport Job Submitted", "status": "ok"})
            except Exception as e:
                results.append({"step": "Transport Order/Job", "status": "skip", "reason": str(e)[:80]})

        # 9. Create Purchase Invoices
        if supplier:
            from logistics.invoice_integration.purchase_invoice_api import create_purchase_invoice
            for job_type, job_name in [
                ("Air Shipment", air_shipment_name) if air_shipment_name else (None, None),
                ("Sea Shipment", sea_shipment_name) if sea_shipment_name else (None, None),
                ("Transport Job", transport_job_name) if transport_job_name else (None, None),
            ]:
                if job_type and job_name:
                    try:
                        r_pi = create_purchase_invoice(job_type, job_name, supplier=supplier)
                        if r_pi.get("ok"):
                            results.append({"step": f"Purchase Invoice ({job_type})", "status": "ok", "name": r_pi.get("purchase_invoice")})
                    except Exception as e:
                        results.append({"step": f"Purchase Invoice ({job_type})", "status": "skip", "reason": str(e)})

        # 10. Create Sales Invoices
        if air_shipment_name:
            try:
                r_si = _create_sales_invoice_from_air_shipment(air_shipment_name, customer)
                if r_si:
                    results.append({"step": "Sales Invoice (Air Shipment)", "status": "ok", "name": r_si})
            except Exception as e:
                results.append({"step": "Sales Invoice (Air Shipment)", "status": "skip", "reason": str(e)})

        if sea_shipment_name:
            try:
                from logistics.sea_freight.doctype.sea_shipment.sea_shipment import create_sales_invoice as sea_create_si
                r_si = sea_create_si(sea_shipment_name, today(), customer)
                si_name = r_si.name if hasattr(r_si, "name") else (r_si.get("sales_invoice") if isinstance(r_si, dict) else None)
                if si_name:
                    results.append({"step": "Sales Invoice (Sea Shipment)", "status": "ok", "name": si_name})
            except Exception as e:
                results.append({"step": "Sales Invoice (Sea Shipment)", "status": "skip", "reason": str(e)})

        if transport_job_name:
            try:
                from logistics.transport.doctype.transport_job.transport_job import create_sales_invoice
                r_si = create_sales_invoice(transport_job_name)
                if r_si and r_si.get("sales_invoice"):
                    results.append({"step": "Sales Invoice (Transport Job)", "status": "ok", "name": r_si.get("sales_invoice")})
            except Exception as e:
                results.append({"step": "Sales Invoice (Transport Job)", "status": "skip", "reason": str(e)})

        frappe.db.commit()
        return results

    except Exception as e:
        frappe.log_error(str(e), "Sample Logistics Data")
        results.append({"step": "Error", "status": "error", "error": str(e)})
        frappe.db.rollback()
        raise


def _ensure_master_data():
    """Create or get required master data."""
    company = frappe.db.get_value("Company", {"name": ["!=", ""]}, "name") or frappe.defaults.get_defaults().get("company")
    if not company:
        frappe.throw(_("No Company found. Please create a Company first."))

    branch = None
    try:
        branches = frappe.get_all("Branch", fields=["name"], limit=1)
        branch = branches[0].name if branches else None
    except Exception:
        pass

    cost_center = None
    try:
        cc_list = frappe.get_all("Cost Center", filters={"company": company, "is_group": 0}, fields=["name"], limit=1)
        cost_center = cc_list[0].name if cc_list else None
    except Exception:
        pass

    profit_center = None
    try:
        pc_list = frappe.get_all("Profit Center", fields=["name"], limit=1)
        profit_center = pc_list[0].name if pc_list else None
    except Exception:
        pass

    customer = frappe.db.get_value("Customer", {"name": ["!=", ""]}, "name")
    if not customer:
        cust = frappe.get_doc({"doctype": "Customer", "customer_name": "Sample Logistics Customer", "customer_type": "Company"})
        cust.insert()
        customer = cust.name

    shipper = "SAMPLE-SHIPPER"
    if not frappe.db.exists("Shipper", shipper):
        frappe.get_doc({"doctype": "Shipper", "code": shipper, "shipper_name": "Sample Shipper"}).insert()

    consignee = "SAMPLE-CONSIGNEE"
    if not frappe.db.exists("Consignee", consignee):
        frappe.get_doc({"doctype": "Consignee", "code": consignee, "consignee_name": "Sample Consignee"}).insert()

    origin = "USLAX"
    dest = "USJFK"
    for unlocode, name, iata in [("USLAX", "Los Angeles", "LAX"), ("USJFK", "New York JFK", "JFK")]:
        if not frappe.db.exists("UNLOCO", unlocode):
            try:
                frappe.get_doc({
                    "doctype": "UNLOCO",
                    "unlocode": unlocode,
                    "location_name": name,
                    "country": "United States",
                    "country_code": "US",
                    "location_type": "Airport",
                    "auto_populate": 0,
                }).insert(ignore_permissions=True)
            except Exception:
                pass

    # Ensure USD
    if not frappe.db.exists("Currency", "USD"):
        frappe.get_doc({"doctype": "Currency", "currency_name": "USD", "symbol": "$"}).insert()

    # Create charge items
    item_group = frappe.db.get_value("Item Group", {"name": ["!=", ""]}, "name") or "Services"
    if not frappe.db.exists("Item Group", item_group):
        frappe.get_doc({"doctype": "Item Group", "item_group_name": item_group}).insert()

    air_item = _get_or_create_charge_item("SAMPLE-AIR-FREIGHT", "Sample Air Freight", item_group, air=1)
    sea_item = _get_or_create_charge_item("SAMPLE-SEA-FREIGHT", "Sample Sea Freight", item_group, sea=1)
    transport_item = _get_or_create_charge_item("SAMPLE-TRANSPORT", "Sample Transport Charge", item_group, transport=1)

    supplier = frappe.db.get_value("Supplier", {"name": ["!=", ""]}, "name")
    if not supplier:
        try:
            sup = frappe.get_doc({"doctype": "Supplier", "supplier_name": "Sample Freight Supplier", "supplier_type": "Services"})
            sup.insert()
            supplier = sup.name
        except Exception:
            supplier = None

    return {
        "company": company,
        "customer": customer,
        "shipper": shipper,
        "consignee": consignee,
        "origin": origin,
        "dest": dest,
        "air_item": air_item,
        "sea_item": sea_item,
        "transport_item": transport_item,
        "supplier": supplier,
        "branch": branch,
        "cost_center": cost_center,
        "profit_center": profit_center,
    }


def _get_or_create_charge_item(code, name, item_group, air=0, sea=0, transport=0):
    """Create Item with logistics charge flags."""
    if frappe.db.exists("Item", code):
        return code
    doc = frappe.get_doc({
        "doctype": "Item",
        "item_code": code,
        "item_name": name,
        "item_group": item_group,
        "stock_uom": "Nos",
        "is_stock_item": 0,
    })
    # Set custom fields if they exist
    meta = frappe.get_meta("Item")
    if meta.get_field("custom_logistics_charge_item"):
        doc.custom_logistics_charge_item = 1
    if meta.get_field("custom_air_forwarding_charge") and air:
        doc.custom_air_forwarding_charge = 1
    if meta.get_field("custom_sea_forwarding_charge") and sea:
        doc.custom_sea_forwarding_charge = 1
    if meta.get_field("custom_land_transport_charge") and transport:
        doc.custom_land_transport_charge = 1
    doc.insert(ignore_permissions=True)
    return code


def _create_sales_quote(company, customer, shipper, consignee, origin, dest, air_item, sea_item, branch=None, cost_center=None, profit_center=None):
    """Create Sales Quote with Air and Sea freight."""
    sq = frappe.new_doc("Sales Quote")
    sq.company = company
    sq.customer = customer
    sq.shipper = shipper
    sq.consignee = consignee
    sq.date = today()
    sq.valid_until = add_days(today(), 30)
    sq.is_air = 1
    sq.is_sea = 1
    sq.origin_port = origin
    sq.destination_port = origin  # Will be overridden per tab
    sq.location_type = "UNLOCO"
    sq.location_from = origin
    sq.location_to = dest
    sq.weight = 100  # kg - required for Air Shipment validation
    sq.volume = 0.5  # m³
    sq.chargeable = 100
    if branch:
        sq.branch = branch
    if cost_center:
        sq.cost_center = cost_center
    if profit_center:
        sq.profit_center = profit_center

    # Air freight line
    sq.append("air_freight", {
        "item_code": air_item,
        "origin_port": origin,
        "destination_port": dest,
        "air_direction": "Export",
        "calculation_method": "Fixed Amount",
        "estimated_revenue": 1500,
        "cost_calculation_method": "Fixed Amount",
        "estimated_cost": 1000,
        "currency": "USD",
        "cost_currency": "USD",
    })

    # Ensure Shipping Line exists (required for Sea Shipment on some sites)
    shipping_line = None
    try:
        shipping_line = frappe.db.get_value("Shipping Line", {"name": ["!=", ""]}, "name")
        if not shipping_line:
            sl = frappe.get_doc({"doctype": "Shipping Line", "shipping_line_name": "Sample Shipping Line"})
            sl.insert(ignore_permissions=True)
            shipping_line = sl.name
    except Exception:
        pass

    # Sea freight line
    sea_row = {
        "item_code": sea_item,
        "origin_port": origin,
        "destination_port": dest,
        "sea_direction": "Export",
        "calculation_method": "Fixed Amount",
        "unit_rate": 800,
        "estimated_revenue": 800,
        "cost_calculation_method": "Fixed Amount",
        "estimated_cost": 500,
        "currency": "USD",
        "cost_currency": "USD",
    }
    if shipping_line:
        sea_row["shipping_line"] = shipping_line
    sq.append("sea_freight", sea_row)

    return sq


def _add_air_charges(doc, item_code):
    """Add charges to Air Shipment."""
    if not doc.get("charges"):
        doc.charges = []
    doc.append("charges", {
        "item_code": item_code,
        "charge_type": "Freight",
        "charge_category": "Transportation",
        "charge_basis": "Per shipment",
        "rate": 1500,
        "currency": "USD",
        "quantity": 1,
        "estimated_revenue": 1500,
        "estimated_cost": 1000,
    })


def _add_sea_charges(doc, item_code):
    """Add charges to Sea Shipment."""
    if not doc.get("charges"):
        doc.charges = []
    doc.append("charges", {
        "charge_item": item_code,
        "charge_type": "Revenue",
        "bill_to": doc.local_customer or doc.customer,
        "selling_amount": 800,
        "buying_amount": 500,
        "selling_currency": "USD",
        "buying_currency": "USD",
    })


def _add_transport_charges(doc, item_code):
    """Add charges to Transport Job."""
    if not doc.get("charges"):
        doc.charges = []
    doc.append("charges", {
        "item_code": item_code,
        "calculation_method": "Fixed Amount",
        "estimated_revenue": 200,
        "cost_calculation_method": "Fixed Amount",
        "estimated_cost": 150,
    })


def _create_sales_invoice_from_air_shipment(shipment_name, customer):
    """Create Sales Invoice from Air Shipment charges (Air Shipment's built-in requires auto_billing)."""
    shipment = frappe.get_doc("Air Shipment", shipment_name)
    if shipment.docstatus != 1:
        return None
    if not shipment.charges:
        return None
    customer = customer or shipment.local_customer
    if not customer:
        return None
    invoice = frappe.new_doc("Sales Invoice")
    invoice.customer = customer
    invoice.company = shipment.company
    invoice.posting_date = today()
    if getattr(shipment, "branch", None):
        invoice.branch = shipment.branch
    if getattr(shipment, "cost_center", None):
        invoice.cost_center = shipment.cost_center
    if getattr(shipment, "profit_center", None):
        invoice.profit_center = shipment.profit_center
    base_remarks = invoice.remarks or ""
    note = _("Auto-created from Air Shipment {0}").format(shipment.name)
    invoice.remarks = f"{base_remarks}\n{note}" if base_remarks else note
    for ch in shipment.charges:
        rev = flt(getattr(ch, "estimated_revenue", 0) or getattr(ch, "rate", 0) * flt(getattr(ch, "quantity", 1) or 1))
        if rev <= 0:
            continue
        item_code = getattr(ch, "item_code", None)
        if not item_code:
            continue
        invoice.append("items", {
            "item_code": item_code,
            "qty": 1,
            "rate": rev,
        })
    if not invoice.items:
        return None
    invoice.set_missing_values()
    invoice.insert(ignore_permissions=True)
    if frappe.get_meta("Air Shipment").get_field("sales_invoice"):
        frappe.db.set_value("Air Shipment", shipment_name, "sales_invoice", invoice.name, update_modified=False)
    return invoice.name
