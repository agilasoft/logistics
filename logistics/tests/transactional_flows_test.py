# Copyright (c) 2026, www.agilasoft.com and Contributors
# Transactional flow tests for logistics module conversions
# Run: bench --site all execute logistics.tests.transactional_flows_test.run

import frappe
from frappe import _
from frappe.utils import today, add_days


def run():
    """Run transactional flow tests and return results for reporting."""
    results = []
    frappe.db.rollback()

    try:
        # Setup - use existing or minimal master data
        company = frappe.db.get_value("Company", {"name": ["!=", ""]}, "name") or frappe.defaults.get_defaults().get("company")
        customer = frappe.db.get_value("Customer", {"name": ["!=", ""]}, "name")
        if not company or not customer:
            results.append({"flow": "Setup", "status": "error", "error": "Company or Customer not found in site"})
            return results
        shipper = _get_or_create_shipper()
        consignee = _get_or_create_consignee()
        _ensure_unloco()
        frappe.db.commit()

        # Flow 1: Air Booking -> Air Shipment
        r1 = _test_air_booking_to_shipment(company, customer, shipper, consignee)
        results.append(r1)
        frappe.db.rollback()

        # Flow 2: Sales Quote -> Air Shipment
        r2 = _test_sales_quote_to_air_shipment(company, customer, shipper, consignee)
        results.append(r2)
        frappe.db.rollback()

        # Flow 3: Air Shipment -> Transport Order
        r3 = _test_air_shipment_to_transport_order(company, customer, shipper, consignee)
        results.append(r3)
        frappe.db.rollback()

        # Flow 4: Transport Order -> Transport Job
        r4 = _test_transport_order_to_transport_job(company, customer)
        results.append(r4)
        frappe.db.rollback()

        # Flow 5: Air Shipment -> Inbound Order
        r5 = _test_air_shipment_to_inbound_order(company, customer, shipper, consignee)
        results.append(r5)
        frappe.db.rollback()

        # Flow 6: Inbound Order -> Warehouse Job
        r6 = _test_inbound_order_to_warehouse_job(company, customer, shipper, consignee)
        results.append(r6)
        frappe.db.rollback()

    except Exception as e:
        results.append({"flow": "Setup", "status": "error", "error": str(e)})

    frappe.db.rollback()
    return results


def _get_or_create_shipper():
    code = "TEST-SHIPPER"
    if not frappe.db.exists("Shipper", code):
        frappe.get_doc({"doctype": "Shipper", "code": code, "shipper_name": "Test Shipper"}).insert()
    return code


def _get_or_create_consignee():
    code = "TEST-CONSIGNEE"
    if not frappe.db.exists("Consignee", code):
        frappe.get_doc({"doctype": "Consignee", "code": code, "consignee_name": "Test Consignee"}).insert()
    return code


def _ensure_unloco():
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


def _test_air_booking_to_shipment(company, customer, shipper, consignee):
    """Flow: Air Booking -> Air Shipment (convert_to_shipment)"""
    flow = "Air Booking -> Air Shipment"
    try:
        booking = frappe.get_doc({
            "doctype": "Air Booking",
            "booking_date": today(),
            "company": company,
            "local_customer": customer,
            "direction": "Export",
            "shipper": shipper,
            "consignee": consignee,
            "origin_port": "USLAX",
            "destination_port": "USJFK",
            "etd": add_days(today(), 5),
            "eta": add_days(today(), 10),
        })
        booking.insert()
        frappe.db.commit()

        # Convert to shipment
        result = booking.convert_to_shipment()
        frappe.db.commit()

        shipment_name = result.get("air_shipment") or result.get("name")
        assert shipment_name, "No shipment name returned"
        shipment = frappe.get_doc("Air Shipment", shipment_name)
        assert shipment.air_booking == booking.name, "Shipment not linked to booking"

        return {"flow": flow, "status": "pass", "booking": booking.name, "shipment": shipment_name}
    except Exception as e:
        return {"flow": flow, "status": "error", "error": str(e)}


def _test_sales_quote_to_air_shipment(company, customer, shipper, consignee):
    """Flow: Sales Quote -> Air Shipment"""
    flow = "Sales Quote -> Air Shipment"
    try:
        sq = frappe.get_doc({
            "doctype": "Sales Quote",
            "company": company,
            "customer": customer,
            "shipper": shipper,
            "consignee": consignee,
            "origin_port": "USLAX",
            "destination_port": "USJFK",
            "main_service": "Air",
            "quotation_type": "One-off",
        })
        sq.append("charges", {
            "service_type": "Air",
            "origin_port": "USLAX",
            "destination_port": "USJFK",
            "direction": "Export",
        })
        sq.insert()
        frappe.db.commit()

        result = sq.create_air_shipment_from_sales_quote()
        frappe.db.commit()

        shipment_name = result.get("air_shipment") or result.get("name")
        assert shipment_name, "No shipment name returned"
        shipment = frappe.get_doc("Air Shipment", shipment_name)
        assert shipment.sales_quote == sq.name, "Shipment not linked to quote"

        return {"flow": flow, "status": "pass", "quote": sq.name, "shipment": shipment_name}
    except Exception as e:
        return {"flow": flow, "status": "error", "error": str(e)}


def _test_air_shipment_to_transport_order(company, customer, shipper, consignee):
    """Flow: Air Shipment -> Transport Order"""
    flow = "Air Shipment -> Transport Order"
    try:
        from logistics.utils.module_integration import create_transport_order_from_air_shipment

        # Create Air Shipment first
        booking = frappe.get_doc({
            "doctype": "Air Booking",
            "booking_date": today(),
            "company": company,
            "local_customer": customer,
            "direction": "Export",
            "shipper": shipper,
            "consignee": consignee,
            "origin_port": "USLAX",
            "destination_port": "USJFK",
            "etd": add_days(today(), 5),
            "eta": add_days(today(), 10),
        })
        booking.insert()
        frappe.db.commit()

        shipment_result = booking.convert_to_shipment()
        frappe.db.commit()
        shipment_name = shipment_result.get("air_shipment") or shipment_result.get("name")

        # Create Transport Order from Air Shipment
        result = create_transport_order_from_air_shipment(shipment_name)
        order_name = result.get("transport_order")
        assert order_name, "No transport order returned"

        order = frappe.get_doc("Transport Order", order_name)
        assert order.air_shipment == shipment_name, "Order not linked to shipment"

        return {"flow": flow, "status": "pass", "shipment": shipment_name, "order": order_name}
    except Exception as e:
        return {"flow": flow, "status": "error", "error": str(e)}


def _test_transport_order_to_transport_job(company, customer):
    """Flow: Transport Order -> Transport Job"""
    flow = "Transport Order -> Transport Job"
    try:
        # Create minimal Transport Order
        order = frappe.get_doc({
            "doctype": "Transport Order",
            "company": company,
            "customer": customer,
            "booking_date": today(),
            "scheduled_date": today(),
            "location_type": "UNLOCO",
            "location_from": "USLAX",
            "location_to": "USJFK",
            "transport_job_type": "Non-Container",
        })
        order.append("legs", {
            "facility_type_from": "Shipper",
            "facility_from": "TEST-SHIPPER",
            "facility_type_to": "Consignee",
            "facility_to": "TEST-CONSIGNEE",
            "scheduled_date": today(),
            "transport_job_type": "Non-Container",
        })
        order.insert()
        frappe.db.commit()

        # Create Transport Job
        result = order.action_create_transport_job()
        job_name = result.get("transport_job") or result.get("name")
        if not job_name and isinstance(result, dict):
            job_name = result.get("transport_jobs", [None])[0] if result.get("transport_jobs") else None
        if not job_name:
            raise frappe.ValidationError("No transport job returned")

        job = frappe.get_doc("Transport Job", job_name)
        assert job.transport_order == order.name or order.name in str(job.get("transport_order", "")), "Job not linked"

        return {"flow": flow, "status": "pass", "order": order.name, "job": job_name}
    except Exception as e:
        return {"flow": flow, "status": "error", "error": str(e)}


def _test_air_shipment_to_inbound_order(company, customer, shipper, consignee):
    """Flow: Air Shipment -> Inbound Order"""
    flow = "Air Shipment -> Inbound Order"
    try:
        from logistics.utils.module_integration import create_inbound_order_from_air_shipment

        # Create Air Shipment
        booking = frappe.get_doc({
            "doctype": "Air Booking",
            "booking_date": today(),
            "company": company,
            "local_customer": customer,
            "direction": "Export",
            "shipper": shipper,
            "consignee": consignee,
            "origin_port": "USLAX",
            "destination_port": "USJFK",
            "etd": add_days(today(), 5),
            "eta": add_days(today(), 10),
        })
        booking.insert()
        frappe.db.commit()
        shipment_result = booking.convert_to_shipment()
        frappe.db.commit()
        shipment_name = shipment_result.get("air_shipment") or shipment_result.get("name")

        # Create Inbound Order
        result = create_inbound_order_from_air_shipment(shipment_name)
        order_name = result.get("inbound_order") or result.get("name")
        if not order_name:
            raise frappe.ValidationError("No inbound order returned")

        order = frappe.get_doc("Inbound Order", order_name)
        assert order.air_shipment == shipment_name, "Order not linked to shipment"

        return {"flow": flow, "status": "pass", "shipment": shipment_name, "order": order_name}
    except Exception as e:
        return {"flow": flow, "status": "error", "error": str(e)}


def _test_inbound_order_to_warehouse_job(company, customer, shipper, consignee):
    """Flow: Inbound Order -> Warehouse Job"""
    flow = "Inbound Order -> Warehouse Job"
    try:
        from logistics.warehousing.doctype.inbound_order.inbound_order import make_warehouse_job

        # Create warehouse if needed
        warehouse = frappe.db.get_value("Warehouse", {"company": company}, "name")
        if not warehouse:
            wh = frappe.get_doc({
                "doctype": "Warehouse",
                "warehouse_name": "Test Warehouse",
                "company": company,
            })
            wh.insert()
            warehouse = wh.name

        # Create item
        item = "TEST-INBOUND-ITEM"
        if not frappe.db.exists("Item", item):
            frappe.get_doc({"doctype": "Item", "item_code": item, "item_name": "Test Inbound Item", "item_group": "Services"}).insert()

        # Create Inbound Order
        order = frappe.get_doc({
            "doctype": "Inbound Order",
            "company": company,
            "customer": customer,
            "shipper": shipper,
            "consignee": consignee,
            "warehouse": warehouse,
            "planned_date": today(),
            "due_date": today(),
        })
        order.append("items", {"item": item, "quantity": 10, "uom": "Nos"})
        order.insert()
        frappe.db.commit()

        # Create Warehouse Job
        job_doc = make_warehouse_job(order.name)
        if job_doc is None:
            raise frappe.ValidationError("make_warehouse_job returned None")
        job_name = job_doc.name if hasattr(job_doc, "name") else str(job_doc)
        frappe.db.commit()

        job = frappe.get_doc("Warehouse Job", job_name)
        assert job.reference_order == order.name, "Job not linked to order"

        return {"flow": flow, "status": "pass", "order": order.name, "job": job_name}
    except Exception as e:
        return {"flow": flow, "status": "error", "error": str(e)}
