# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, nowtime, get_datetime
import json


def get_customer_from_user():
    """Get customer associated with current user"""
    user = frappe.session.user
    if not user or user == "Guest":
        return None
    
    try:
        # Method 1: Check Portal Users field in Customer doctype
        portal_users = frappe.get_all(
            "Portal User",
            filters={"user": user, "parenttype": "Customer"},
            fields=["parent"],
            limit=1
        )
        if portal_users:
            return portal_users[0].parent
        
        # Method 2: Direct email match in Customer
        direct_customers = frappe.get_all(
            "Customer",
            filters={"email_id": user},
            fields=["name"],
            limit=1
        )
        if direct_customers:
            return direct_customers[0].name
        
        # Method 3: Through Contact links
        contacts = frappe.get_all(
            "Contact",
            filters={"email_id": user},
            fields=["name"],
            limit=1
        )
        if contacts:
            contact_links = frappe.get_all(
                "Dynamic Link",
                filters={"parent": contacts[0].name, "link_doctype": "Customer"},
                fields=["link_name"],
                limit=1
            )
            if contact_links:
                return contact_links[0].link_name
        
        return None
    except Exception as e:
        frappe.log_error(f"Error getting customer from user: {str(e)}", "Customer Resolution")
        return None



@frappe.whitelist(allow_guest=False)
def test_database_orders():
    """Test if orders exist in database"""
    try:
        # Test 1: Check all Release Orders
        all_orders = frappe.get_all("Release Order", fields=["name", "customer", "order_date", "docstatus"], limit=10)
        
        # Test 2: Check orders for Adidas specifically
        adidas_orders = frappe.get_all("Release Order", filters={"customer": "Adidas"}, fields=["name", "customer", "order_date", "docstatus"], limit=10)
        
        return {
            "total_orders": len(all_orders),
            "adidas_orders": len(adidas_orders),
            "all_orders": all_orders,
            "adidas_orders_list": adidas_orders
        }
    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist(allow_guest=False)
def test_portal_customer_resolution():
    """Test customer resolution for portal"""
    try:
        # Test the same customer resolution as portal
        from logistics.api import get_customer_from_user
        customer = get_customer_from_user()
        
        # Test the portal's order query
        from datetime import datetime, timedelta
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date_to = datetime.now().strftime('%Y-%m-%d')
        
        orders = frappe.get_all(
            "Release Order",
            filters={
                "customer": customer,
                "order_date": ["between", [date_from, date_to]]
            },
            fields=["name", "customer", "order_date", "docstatus"],
            order_by="order_date desc, creation desc"
        )
        
        return {
            "current_user": frappe.session.user,
            "resolved_customer": customer,
            "date_from": date_from,
            "date_to": date_to,
            "orders_found": len(orders),
            "orders": orders
        }
    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist(allow_guest=False)
def debug_release_orders():
    """Debug function to check release orders"""
    try:
        # Get all release orders
        orders = frappe.get_all("Release Order", fields=["name", "customer", "order_date", "docstatus"], limit=10)
        
        # Get customer for current user
        customer = get_customer_from_user()
        
        # Test portal query logic
        from datetime import datetime, timedelta
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date_to = datetime.now().strftime('%Y-%m-%d')
        
        # Test the exact query used by portal
        portal_orders = frappe.get_all(
            "Release Order",
            filters={
                "customer": customer,
                "order_date": ["between", [date_from, date_to]]
            },
            fields=["name", "customer", "order_date", "docstatus"],
            order_by="order_date desc, creation desc"
        )
        
        # Test customer resolution for both users
        test_users = ["Administrator", "maria.santos@adidas.com"]
        test_results = {}
        for test_user in test_users:
            test_customer = None
            try:
                # Check if this user exists and what customer they're linked to
                portal_users = frappe.get_all(
                    "Portal User",
                    filters={"user": test_user, "parenttype": "Customer"},
                    fields=["parent"],
                    limit=1
                )
                if portal_users:
                    test_customer = portal_users[0].parent
            except Exception:
                pass
            test_results[test_user] = test_customer
        
        return {
            "total_orders": len(orders),
            "orders": orders,
            "current_user": frappe.session.user,
            "resolved_customer": customer,
            "date_from": date_from,
            "date_to": date_to,
            "portal_orders": len(portal_orders),
            "portal_orders_list": portal_orders,
            "test_results": test_results
        }
    except Exception as e:
        return {"error": str(e)}

@frappe.whitelist(allow_guest=False)
def create_inbound_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, branch=None):
    """Create a new Inbound Order for the customer"""
    
    try:
        # Get customer from current user
        customer = get_customer_from_user()
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."), frappe.PermissionError)
        
        # Get default values for mandatory fields
        company = get_default_company()
        if not company:
            frappe.throw(_("No company found. Please contact support."))
        
        branch = get_default_branch(company, branch)
        if not branch:
            frappe.throw(_("No branch found for company {0}. Please contact support.").format(company))
        
        cost_center = get_default_cost_center(company)
        if not cost_center:
            frappe.throw(_("No cost center found for company {0}. Please contact support.").format(company))
        
        profit_center = get_default_profit_center(company, customer)
        if not profit_center:
            frappe.throw(_("No profit center found for company {0}. Please contact support.").format(company))
        
        # Create new Inbound Order
        inbound_order = frappe.new_doc("Inbound Order")
        inbound_order.customer = customer
        inbound_order.company = company
        inbound_order.branch = branch
        inbound_order.cost_center = cost_center
        inbound_order.profit_center = profit_center
        inbound_order.order_date = order_date
        inbound_order.cust_reference = cust_reference
        inbound_order.priority = priority
        inbound_order.planned_date = planned_date
        inbound_order.due_date = due_date
        inbound_order.notes = notes
        inbound_order.status = "Draft"
        
        # Add sample items to the order
        try:
            # Add a sample item
            inbound_order.append("items", {
                "item_code": "SAMPLE-ITEM-002",
                "item_name": "Sample Inbound Item",
                "description": "Sample inbound item for testing",
                "qty": 2,
                "rate": 150.00,
                "amount": 300.00
            })
            frappe.log_error("Added sample item to Inbound Order", "Item Addition Debug")
        except Exception as e:
            frappe.log_error(f"Error adding sample item: {str(e)}", "Item Addition Debug")
        
        # Save the document
        inbound_order.insert(ignore_permissions=True)
        
        return {
            "message": f"Inbound Order {inbound_order.name} created successfully",
            "order_id": inbound_order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating inbound order: {str(e)}", "Create Inbound Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))


@frappe.whitelist(allow_guest=False)
def create_release_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, branch=None):
    """Create a new Release Order for the customer"""
    
    try:
        # Get customer from current user
        customer = get_customer_from_user()
        frappe.log_error(f"Release Order Creation - Customer resolved: {customer}", "Customer Debug")
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."), frappe.PermissionError)
        
        # Get default values for mandatory fields
        company = get_default_company()
        if not company:
            frappe.throw(_("No company found. Please contact support."))
        
        branch = get_default_branch(company, branch)
        if not branch:
            frappe.throw(_("No branch found for company {0}. Please contact support.").format(company))
        
        cost_center = get_default_cost_center(company)
        if not cost_center:
            frappe.throw(_("No cost center found for company {0}. Please contact support.").format(company))
        
        profit_center = get_default_profit_center(company, customer)
        if not profit_center:
            frappe.throw(_("No profit center found for company {0}. Please contact support.").format(company))
        
        # Get customer contract
        contract = get_customer_contract(customer, order_date)
        frappe.log_error(f"Contract lookup result for {customer} on {order_date}: {contract}", "Contract Debug")
        
        if not contract:
            # Try to create a default contract for the customer
            frappe.log_error(f"No contract found, attempting to create default contract for {customer}", "Contract Debug")
            try:
                contract = create_default_contract(customer, company, order_date)
                frappe.log_error(f"Default contract creation result: {contract}", "Contract Debug")
                if not contract:
                    frappe.throw(_("No active contract found for customer {0}. Please contact support.").format(customer))
            except Exception as e:
                frappe.log_error(f"Error creating default contract for {customer}: {str(e)}", "Contract Creation")
                frappe.throw(_("No active contract found for customer {0}. Please contact support.").format(customer))
        
        # Debug: Log the values we're setting
        frappe.log_error(f"Release Order Debug - Company: {company}", "Release Order Debug")
        frappe.log_error(f"Branch: {branch}, Cost Center: {cost_center}", "Release Order Debug")
        frappe.log_error(f"Profit Center: {profit_center}, Contract: {contract}", "Release Order Debug")
        
        # Create new Release Order
        release_order = frappe.new_doc("Release Order")
        
        # Set basic fields first
        release_order.customer = customer
        release_order.order_date = order_date
        release_order.cust_reference = cust_reference
        release_order.priority = priority
        release_order.planned_date = planned_date
        release_order.due_date = due_date
        release_order.notes = notes
        release_order.status = "Draft"
        
        # Set mandatory fields
        try:
            release_order.contract = contract
            frappe.log_error(f"Set contract: {contract}", "Field Assignment Debug")
        except Exception as e:
            frappe.log_error(f"Error setting contract: {str(e)}", "Field Assignment Debug")
            
        try:
            release_order.company = company
            frappe.log_error(f"Set company: {company}", "Field Assignment Debug")
        except Exception as e:
            frappe.log_error(f"Error setting company: {str(e)}", "Field Assignment Debug")
            
        try:
            release_order.branch = branch
            frappe.log_error(f"Set branch: {branch}", "Field Assignment Debug")
        except Exception as e:
            frappe.log_error(f"Error setting branch: {str(e)}", "Field Assignment Debug")
            
        try:
            release_order.cost_center = cost_center
            frappe.log_error(f"Set cost_center: {cost_center}", "Field Assignment Debug")
        except Exception as e:
            frappe.log_error(f"Error setting cost_center: {str(e)}", "Field Assignment Debug")
            
        try:
            release_order.profit_center = profit_center
            frappe.log_error(f"Set profit_center: {profit_center}", "Field Assignment Debug")
        except Exception as e:
            frappe.log_error(f"Error setting profit_center: {str(e)}", "Field Assignment Debug")
        
        # Debug: Log the actual values in the document
        frappe.log_error(f"Document Values - Company: {release_order.company}", "Release Order Document Debug")
        frappe.log_error(f"Branch: {release_order.branch}, Cost Center: {release_order.cost_center}", "Release Order Document Debug")
        frappe.log_error(f"Profit Center: {release_order.profit_center}, Contract: {release_order.contract}", "Release Order Document Debug")
        
        # Add sample items to the order
        try:
            # Add a sample item
            release_order.append("items", {
                "item_code": "SAMPLE-ITEM-001",
                "item_name": "Sample Item",
                "description": "Sample item for testing",
                "qty": 1,
                "rate": 100.00,
                "amount": 100.00
            })
            frappe.log_error("Added sample item to Release Order", "Item Addition Debug")
        except Exception as e:
            frappe.log_error(f"Error adding sample item: {str(e)}", "Item Addition Debug")
        
        # Save the document
        release_order.insert(ignore_permissions=True)
        
        # Simple debug to confirm order creation
        print(f"=== RELEASE ORDER CREATED: {release_order.name} ===")
        
        return {
            "message": f"Release Order {release_order.name} created successfully",
            "order_id": release_order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating release order: {str(e)}", "Create Release Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))


@frappe.whitelist(allow_guest=False)
def create_vas_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, vas_type=None, branch=None):
    """Create a new VAS Order for the customer"""
    
    try:
        # Get customer from current user
        customer = get_customer_from_user()
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."), frappe.PermissionError)
        
        # Get default values for mandatory fields
        company = get_default_company()
        if not company:
            frappe.throw(_("No company found. Please contact support."))
        
        branch = get_default_branch(company, branch)
        if not branch:
            frappe.throw(_("No branch found for company {0}. Please contact support.").format(company))
        
        cost_center = get_default_cost_center(company)
        if not cost_center:
            frappe.throw(_("No cost center found for company {0}. Please contact support.").format(company))
        
        profit_center = get_default_profit_center(company, customer)
        if not profit_center:
            frappe.throw(_("No profit center found for company {0}. Please contact support.").format(company))
        
        # Get customer contract
        contract = get_customer_contract(customer, order_date)
        frappe.log_error(f"VAS Order Contract lookup result for {customer} on {order_date}: {contract}", "Contract Debug")
        if not contract:
            frappe.throw(_("No active contract found for customer {0}. Please contact support.").format(customer))
        
        # Get default VAS type if not provided
        if not vas_type:
            try:
                vas_types = frappe.get_all("VAS Order Type", fields=["name"], limit=1)
                if vas_types:
                    vas_type = vas_types[0].name
                else:
                    frappe.throw(_("No VAS Order Type found. Please contact support."))
            except Exception:
                frappe.throw(_("No VAS Order Type found. Please contact support."))
        
        # Set default planned_date if not provided (VAS Order requires it)
        if not planned_date:
            planned_date = now_datetime()
        
        # Create new VAS Order
        vas_order = frappe.new_doc("VAS Order")
        vas_order.customer = customer
        vas_order.contract = contract
        vas_order.company = company
        vas_order.branch = branch
        vas_order.cost_center = cost_center
        vas_order.profit_center = profit_center
        vas_order.type = vas_type
        vas_order.order_date = order_date
        vas_order.cust_reference = cust_reference
        vas_order.priority = priority
        vas_order.planned_date = planned_date
        vas_order.due_date = due_date
        vas_order.notes = notes
        vas_order.status = "Draft"
        
        # Add sample items to the order
        try:
            # Add a sample item
            vas_order.append("items", {
                "item_code": "SAMPLE-ITEM-003",
                "item_name": "Sample VAS Item",
                "description": "Sample VAS item for testing",
                "qty": 1,
                "rate": 200.00,
                "amount": 200.00
            })
            frappe.log_error("Added sample item to VAS Order", "Item Addition Debug")
        except Exception as e:
            frappe.log_error(f"Error adding sample item: {str(e)}", "Item Addition Debug")
        
        # Save the document
        vas_order.insert(ignore_permissions=True)
        
        return {
            "message": f"VAS Order {vas_order.name} created successfully",
            "order_id": vas_order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating VAS order: {str(e)}", "Create VAS Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))


@frappe.whitelist(allow_guest=False)
def create_transfer_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, branch=None):
    """Create a new Transfer Order for the customer"""
    
    try:
        # Get customer from current user
        customer = get_customer_from_user()
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."), frappe.PermissionError)
        
        # Get default values for mandatory fields
        company = get_default_company()
        if not company:
            frappe.throw(_("No company found. Please contact support."))
        
        branch = get_default_branch(company, branch)
        if not branch:
            frappe.throw(_("No branch found for company {0}. Please contact support.").format(company))
        
        cost_center = get_default_cost_center(company)
        if not cost_center:
            frappe.throw(_("No cost center found for company {0}. Please contact support.").format(company))
        
        profit_center = get_default_profit_center(company, customer)
        if not profit_center:
            frappe.throw(_("No profit center found for company {0}. Please contact support.").format(company))
        
        # Create new Transfer Order
        transfer_order = frappe.new_doc("Transfer Order")
        transfer_order.customer = customer
        transfer_order.company = company
        transfer_order.branch = branch
        transfer_order.cost_center = cost_center
        transfer_order.profit_center = profit_center
        transfer_order.order_date = order_date
        transfer_order.cust_reference = cust_reference
        transfer_order.priority = priority
        transfer_order.planned_date = planned_date
        transfer_order.due_date = due_date
        transfer_order.notes = notes
        transfer_order.status = "Draft"
        
        # Add sample items to the order
        try:
            # Add a sample item
            transfer_order.append("items", {
                "item_code": "SAMPLE-ITEM-004",
                "item_name": "Sample Transfer Item",
                "description": "Sample transfer item for testing",
                "qty": 3,
                "rate": 75.00,
                "amount": 225.00
            })
            frappe.log_error("Added sample item to Transfer Order", "Item Addition Debug")
        except Exception as e:
            frappe.log_error(f"Error adding sample item: {str(e)}", "Item Addition Debug")
        
        # Save the document
        transfer_order.insert(ignore_permissions=True)
        
        return {
            "message": f"Transfer Order {transfer_order.name} created successfully",
            "order_id": transfer_order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating transfer order: {str(e)}", "Create Transfer Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))


@frappe.whitelist(allow_guest=False)
def create_stocktake_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, stocktake_type="Full", scope="Site", branch=None):
    """Create a new Stocktake Order for the customer"""
    
    try:
        # Get customer from current user
        customer = get_customer_from_user()
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."), frappe.PermissionError)
        
        # Get default values for mandatory fields
        company = get_default_company()
        if not company:
            frappe.throw(_("No company found. Please contact support."))
        
        branch = get_default_branch(company, branch)
        if not branch:
            frappe.throw(_("No branch found for company {0}. Please contact support.").format(company))
        
        cost_center = get_default_cost_center(company)
        if not cost_center:
            frappe.throw(_("No cost center found for company {0}. Please contact support.").format(company))
        
        profit_center = get_default_profit_center(company, customer)
        if not profit_center:
            frappe.throw(_("No profit center found for company {0}. Please contact support.").format(company))
        
        # Get customer contract
        contract = get_customer_contract(customer, order_date)
        frappe.log_error(f"Stocktake Order Contract lookup result for {customer} on {order_date}: {contract}", "Contract Debug")
        if not contract:
            frappe.throw(_("No active contract found for customer {0}. Please contact support.").format(customer))
        
        # Set default planned_date if not provided (Stocktake Order requires it)
        if not planned_date:
            planned_date = now_datetime()
        
        # Create new Stocktake Order
        stocktake_order = frappe.new_doc("Stocktake Order")
        stocktake_order.customer = customer
        stocktake_order.contract = contract
        stocktake_order.company = company
        stocktake_order.branch = branch
        stocktake_order.cost_center = cost_center
        stocktake_order.profit_center = profit_center
        stocktake_order.type = stocktake_type
        stocktake_order.scope = scope
        stocktake_order.date = order_date
        stocktake_order.cust_reference = cust_reference
        stocktake_order.priority = priority
        stocktake_order.planned_date = planned_date
        stocktake_order.due_date = due_date
        stocktake_order.notes = notes
        stocktake_order.status = "Draft"
        
        # Add sample items to the order
        try:
            # Add a sample item
            stocktake_order.append("items", {
                "item_code": "SAMPLE-ITEM-005",
                "item_name": "Sample Stocktake Item",
                "description": "Sample stocktake item for testing",
                "qty": 5,
                "rate": 50.00,
                "amount": 250.00
            })
            frappe.log_error("Added sample item to Stocktake Order", "Item Addition Debug")
        except Exception as e:
            frappe.log_error(f"Error adding sample item: {str(e)}", "Item Addition Debug")
        
        # Save the document
        stocktake_order.insert(ignore_permissions=True)
        
        return {
            "message": f"Stocktake Order {stocktake_order.name} created successfully",
            "order_id": stocktake_order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating stocktake order: {str(e)}", "Create Stocktake Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))


def get_customer_from_user():
    """Get customer associated with current user"""
    user = frappe.session.user
    
    if user and user != "Guest":
        # Method 1: Check Portal Users field in Customer doctype
        try:
            portal_users = frappe.get_all(
                "Portal User",
                filters={"user": user, "parenttype": "Customer"},
                fields=["parent"],
                limit=1
            )
            if portal_users:
                return portal_users[0].parent
        except Exception:
            pass
        
        # Method 2: Direct email match in Customer
        try:
            customers = frappe.get_all(
                "Customer",
                filters={"email_id": user},
                fields=["name"],
                limit=1
            )
            if customers:
                return customers[0].name
        except Exception:
            pass
        
        # Method 3: Through Contact links
        try:
            contact = frappe.get_value("Contact", {"email_id": user}, "name")
            if contact:
                customer_links = frappe.get_all(
                    "Dynamic Link",
                    filters={
                        "parent": contact,
                        "link_doctype": "Customer"
                    },
                    fields=["link_name"],
                    limit=1
                )
                if customer_links:
                    return customer_links[0].link_name
        except Exception:
            pass
    
    return None


def get_default_company():
    """Get default company using version-safe fallback chain"""
    # Try frappe.db.get_default (available on v15)
    try:
        val = frappe.db.get_default("company")
        if val:
            frappe.log_error(f"Got company from frappe.db.get_default: {val}", "Company Debug")
            return val
    except Exception as e:
        frappe.log_error(f"Error getting company from frappe.db.get_default: {str(e)}", "Company Debug")
        pass
    # Try frappe.defaults.get_user_default (older patterns)
    try:
        val = frappe.defaults.get_user_default("company")
        if val:
            frappe.log_error(f"Got company from frappe.defaults.get_user_default: {val}", "Company Debug")
            return val
    except Exception as e:
        frappe.log_error(f"Error getting company from frappe.defaults.get_user_default: {str(e)}", "Company Debug")
        pass
    # Try Global Defaults doctype
    try:
        val = frappe.db.get_value("Global Defaults", "Global Defaults", "default_company")
        if val:
            frappe.log_error(f"Got company from Global Defaults: {val}", "Company Debug")
            return val
    except Exception as e:
        frappe.log_error(f"Error getting company from Global Defaults: {str(e)}", "Company Debug")
        pass
    # Fallback: get first company
    try:
        companies = frappe.get_all("Company", fields=["name"], limit=1)
        if companies:
            frappe.log_error(f"Got company from first company: {companies[0].name}", "Company Debug")
            return companies[0].name
    except Exception as e:
        frappe.log_error(f"Error getting first company: {str(e)}", "Company Debug")
        pass
    frappe.log_error("No company found in any method", "Company Debug")
    return None


def get_default_branch(company=None, branch=None):
    """Get default branch for company"""
    # If branch is provided, use it
    if branch:
        return branch
        
    if not company:
        company = get_default_company()
    
    if company:
        # Try to get default branch for company
        try:
            branch = frappe.db.get_value("Branch", {"company": company, "is_default": 1}, "name")
            if branch:
                return branch
        except Exception:
            pass
        
        # Fallback: get first branch for company
        try:
            branches = frappe.get_all("Branch", filters={"company": company}, fields=["name"], limit=1)
            if branches:
                return branches[0].name
        except Exception:
            pass
    
    return None


def get_default_cost_center(company=None):
    """Get default cost center for company from Warehouse Settings"""
    if not company:
        company = get_default_company()
    
    # Try to get default cost center from Warehouse Settings
    try:
        warehouse_settings = frappe.get_single("Warehouse Settings")
        if hasattr(warehouse_settings, 'default_cost_center') and warehouse_settings.default_cost_center:
            frappe.log_error(f"Got cost center from Warehouse Settings: {warehouse_settings.default_cost_center}", "Cost Center Debug")
            return warehouse_settings.default_cost_center
    except Exception as e:
        frappe.log_error(f"Error getting cost center from Warehouse Settings: {str(e)}", "Cost Center Debug")
        pass
    
    if company:
        # Try to get default cost center for company
        try:
            cost_center = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
            if cost_center:
                frappe.log_error(f"Got cost center from company: {cost_center}", "Cost Center Debug")
                return cost_center
        except Exception as e:
            frappe.log_error(f"Error getting cost center from company: {str(e)}", "Cost Center Debug")
            pass
        
        # Fallback: get first cost center for company
        try:
            cost_centers = frappe.get_all("Cost Center", filters={"company": company, "is_group": 0}, fields=["name"], limit=1)
            if cost_centers:
                frappe.log_error(f"Got first cost center from company: {cost_centers[0].name}", "Cost Center Debug")
                return cost_centers[0].name
        except Exception as e:
            frappe.log_error(f"Error getting first cost center from company: {str(e)}", "Cost Center Debug")
            pass
    
    frappe.log_error("No cost center found in any method", "Cost Center Debug")
    return None


def get_default_profit_center(company=None, customer=None):
    """Get default profit center from customer's custom field or company"""
    if not company:
        company = get_default_company()
    
    # Try to get profit center from customer's custom field
    if customer:
        try:
            customer_doc = frappe.get_doc("Customer", customer)
            if hasattr(customer_doc, 'custom_default_warehouse_profit_center') and customer_doc.custom_default_warehouse_profit_center:
                frappe.log_error(f"Got profit center from customer custom field: {customer_doc.custom_default_warehouse_profit_center}", "Profit Center Debug")
                return customer_doc.custom_default_warehouse_profit_center
        except Exception as e:
            frappe.log_error(f"Error getting profit center from customer custom field: {str(e)}", "Profit Center Debug")
            pass
    
    if company:
        # Try to get default profit center for company
        try:
            profit_center = frappe.db.get_value("Profit Center", {"company": company}, "name")
            if profit_center:
                frappe.log_error(f"Got profit center from company: {profit_center}", "Profit Center Debug")
                return profit_center
        except Exception as e:
            frappe.log_error(f"Error getting profit center from company: {str(e)}", "Profit Center Debug")
            pass
        
        # Fallback: get first profit center for company
        try:
            profit_centers = frappe.get_all("Profit Center", filters={"company": company}, fields=["name"], limit=1)
            if profit_centers:
                frappe.log_error(f"Got first profit center from company: {profit_centers[0].name}", "Profit Center Debug")
                return profit_centers[0].name
        except Exception as e:
            frappe.log_error(f"Error getting first profit center from company: {str(e)}", "Profit Center Debug")
            pass
    
    frappe.log_error("No profit center found in any method", "Profit Center Debug")
    return None


def get_customer_contract(customer, order_date=None):
    """Get the latest applicable contract for customer that is still valid with the given date"""
    if not customer:
        return None
    
    if not order_date:
        order_date = frappe.utils.today()
    
    try:
        # Get contracts that are valid for the order date
        contracts = frappe.get_all(
            "Warehouse Contract",
            filters={
                "customer": customer
            },
            fields=["name", "date", "valid_until", "creation"],
            order_by="creation desc"  # Get latest first
        )
        
        # Filter contracts that are valid for the order date
        valid_contracts = []
        for contract in contracts:
            start_date = contract.date or frappe.utils.today()
            end_date = contract.valid_until or frappe.utils.add_days(frappe.utils.today(), 365)
            
            # Check if order date falls within contract period
            if start_date <= order_date <= end_date:
                valid_contracts.append(contract)
        
        # Return the latest valid contract
        if valid_contracts:
            frappe.log_error(f"Found {len(valid_contracts)} valid contracts for {customer} on {order_date}. Using: {valid_contracts[0].name}", "Contract Selection")
            return valid_contracts[0].name
            
    except Exception as e:
        frappe.log_error(f"Error getting customer contract for {customer}: {str(e)}", "Contract Selection")
        pass
    
    return None


def create_default_contract(customer, company, order_date=None):
    """Create a default contract for customer"""
    if not customer or not company:
        return None
    
    if not order_date:
        order_date = frappe.utils.today()
    
    try:
        # Check if a default contract already exists
        existing = frappe.get_all(
            "Warehouse Contract",
            filters={
                "customer": customer
            },
            fields=["name"],
            limit=1
        )
        if existing:
            return existing[0].name
        
        # Create new default contract
        contract = frappe.new_doc("Warehouse Contract")
        contract.customer = customer
        contract.date = order_date
        contract.valid_until = frappe.utils.add_days(order_date, 365)  # 1 year from order date
        contract.company = company
        contract.insert(ignore_permissions=True)
        frappe.log_error(f"Created default contract {contract.name} for customer {customer} starting {order_date}", "Contract Creation")
        return contract.name
        
    except Exception as e:
        frappe.log_error(f"Error creating default contract: {str(e)}", "Contract Creation")
        return None


@frappe.whitelist()
def update_release_order(name, cust_reference=None, priority=None, planned_date=None, due_date=None, branch=None, notes=None):
    """Update a Release Order"""
    try:
        # Get the order
        order = frappe.get_doc("Release Order", name)
        
        # Check if user has permission to edit this order
        user_customer = get_customer_from_user()
        if not user_customer or order.customer != user_customer:
            frappe.throw(_("You don't have permission to edit this order"), frappe.PermissionError)
        
        # Check if order can be edited (only draft orders)
        if order.docstatus != 0:
            frappe.throw(_("Only draft orders can be edited"), frappe.ValidationError)
        
        # Update fields
        if cust_reference is not None:
            order.cust_reference = cust_reference
        if priority is not None:
            order.priority = priority
        if planned_date:
            order.planned_date = planned_date
        if due_date:
            order.due_date = due_date
        if branch:
            order.branch = branch
        if notes is not None:
            order.notes = notes
        
        # Save the order
        order.save(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.log_error(f"Updated Release Order {name}", "Order Update Debug")
        return {"message": "Order updated successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error updating Release Order {name}: {str(e)}", "Order Update Error")
        frappe.throw(_("Error updating order: {0}").format(str(e)))


@frappe.whitelist()
def update_inbound_order(name, cust_reference=None, priority=None, planned_date=None, due_date=None, branch=None, notes=None):
    """Update an Inbound Order"""
    try:
        # Get the order
        order = frappe.get_doc("Inbound Order", name)
        
        # Check if user has permission to edit this order
        user_customer = get_customer_from_user()
        if not user_customer or order.customer != user_customer:
            frappe.throw(_("You don't have permission to edit this order"), frappe.PermissionError)
        
        # Check if order can be edited (only draft orders)
        if order.docstatus != 0:
            frappe.throw(_("Only draft orders can be edited"), frappe.ValidationError)
        
        # Update fields
        if cust_reference is not None:
            order.cust_reference = cust_reference
        if priority is not None:
            order.priority = priority
        if planned_date:
            order.planned_date = planned_date
        if due_date:
            order.due_date = due_date
        if branch:
            order.branch = branch
        if notes is not None:
            order.notes = notes
        
        # Save the order
        order.save(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.log_error(f"Updated Inbound Order {name}", "Order Update Debug")
        return {"message": "Order updated successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error updating Inbound Order {name}: {str(e)}", "Order Update Error")
        frappe.throw(_("Error updating order: {0}").format(str(e)))


@frappe.whitelist()
def update_vas_order(name, cust_reference=None, priority=None, planned_date=None, due_date=None, branch=None, vas_type=None, notes=None):
    """Update a VAS Order"""
    try:
        # Get the order
        order = frappe.get_doc("VAS Order", name)
        
        # Check if user has permission to edit this order
        user_customer = get_customer_from_user()
        if not user_customer or order.customer != user_customer:
            frappe.throw(_("You don't have permission to edit this order"), frappe.PermissionError)
        
        # Check if order can be edited (only draft orders)
        if order.docstatus != 0:
            frappe.throw(_("Only draft orders can be edited"), frappe.ValidationError)
        
        # Update fields
        if cust_reference is not None:
            order.cust_reference = cust_reference
        if priority is not None:
            order.priority = priority
        if planned_date:
            order.planned_date = planned_date
        if due_date:
            order.due_date = due_date
        if branch:
            order.branch = branch
        if vas_type:
            order.vas_type = vas_type
        if notes is not None:
            order.notes = notes
        
        # Save the order
        order.save(ignore_permissions=True)
        frappe.db.commit()
        
        frappe.log_error(f"Updated VAS Order {name}", "Order Update Debug")
        return {"message": "Order updated successfully"}
        
    except Exception as e:
        frappe.log_error(f"Error updating VAS Order {name}: {str(e)}", "Order Update Error")
        frappe.throw(_("Error updating order: {0}").format(str(e)))


@frappe.whitelist()
def test_api():
    """Test API function"""
    return {"success": True, "message": "API is working"}

@frappe.whitelist()
def get_order_items(order_name):
    """Get items for a specific order"""
    try:
        # Check if user has permission to view this order
        user_customer = get_customer_from_user()
        if not user_customer:
            return {"success": False, "error": "Customer not found"}
        
        # Get the order to check customer
        order = frappe.get_doc("Release Order", order_name)
        if order.customer != user_customer:
            return {"success": False, "error": "Permission denied"}
        
        # Get items with proper permissions
        items = frappe.get_all(
            "Release Order Item",
            filters={"parent": order_name},
            fields=["item_code", "item_name", "description", "qty", "rate", "amount"],
            ignore_permissions=True
        )
        
        return {"success": True, "items": items}
        
    except Exception as e:
        frappe.log_error(f"Error getting order items: {str(e)}", "Get Order Items")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_customer_items(customer):
    """Get warehouse items applicable for a customer"""
    try:
        # Get warehouse items filtered by customer
        items = frappe.get_all(
            "Warehouse Item",
            filters={"customer": customer},
            fields=["name as item_code", "item_name", "uom"],
            order_by="item_name",
            limit=100  # Limit to prevent too many items
        )
        
        if not items:
            return {
                "success": False,
                "error": f"No warehouse items found for customer {customer}"
            }
        
        return {
            "success": True,
            "items": items
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting customer items: {str(e)}", "Get Customer Items")
        return {
            "success": False,
            "error": f"Error getting customer items: {str(e)}"
        }

@frappe.whitelist(allow_guest=False)
def add_order_item(order_name, doctype, item):
    """Add a new item to an order"""
    try:
        # Get the order document
        order = frappe.get_doc(doctype, order_name)
        
        # Check if order is draft
        if order.docstatus != 0:
            frappe.throw(_("Cannot add items to submitted order"), frappe.ValidationError)
        
        # Check customer permissions
        user_customer = get_customer_from_user()
        if not user_customer or order.customer != user_customer:
            frappe.throw(_("You don't have permission to edit this order"), frappe.PermissionError)
        
        # Add item to order
        order.append("items", {
            "item": item.get("item_code"),
            "item_name": item.get("item_name"),
            "uom": item.get("uom"),
            "quantity": item.get("qty", 0),
            "serial_no": item.get("serial_no"),
            "batch_no": item.get("batch_no"),
            "expiry_date": item.get("expiry_date")
        })
        
        order.save()
        
        return {
            "success": True,
            "message": "Item added successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error adding item to order: {str(e)}", "Add Order Item")
        return {
            "success": False,
            "error": f"Error adding item: {str(e)}"
        }

@frappe.whitelist(allow_guest=False)
def update_order_item(order_name, doctype, item_index, item):
    """Update an existing item in an order"""
    try:
        # Get the order document
        order = frappe.get_doc(doctype, order_name)
        
        # Check if order is draft
        if order.docstatus != 0:
            frappe.throw(_("Cannot edit items in submitted order"), frappe.ValidationError)
        
        # Check customer permissions
        user_customer = get_customer_from_user()
        if not user_customer or order.customer != user_customer:
            frappe.throw(_("You don't have permission to edit this order"), frappe.PermissionError)
        
        # Update the item
        if item_index < len(order.items):
            order.items[item_index].item = item.get("item_code")
            order.items[item_index].item_name = item.get("item_name")
            order.items[item_index].uom = item.get("uom")
            order.items[item_index].quantity = item.get("qty", 0)
            order.items[item_index].serial_no = item.get("serial_no")
            order.items[item_index].batch_no = item.get("batch_no")
            order.items[item_index].expiry_date = item.get("expiry_date")
            
            order.save()
            
            return {
                "success": True,
                "message": "Item updated successfully"
            }
        else:
            frappe.throw(_("Item not found"), frappe.ValidationError)
        
    except Exception as e:
        frappe.log_error(f"Error updating item: {str(e)}", "Update Order Item")
        return {
            "success": False,
            "error": f"Error updating item: {str(e)}"
        }

@frappe.whitelist(allow_guest=False)
def delete_order_item(order_name, doctype, item_index):
    """Delete an item from an order"""
    try:
        # Get the order document
        order = frappe.get_doc(doctype, order_name)
        
        # Check if order is draft
        if order.docstatus != 0:
            frappe.throw(_("Cannot delete items from submitted order"), frappe.ValidationError)
        
        # Check customer permissions
        user_customer = get_customer_from_user()
        if not user_customer or order.customer != user_customer:
            frappe.throw(_("You don't have permission to edit this order"), frappe.PermissionError)
        
        # Remove the item
        if item_index < len(order.items):
            order.remove(order.items[item_index])
            order.save()
            
            return {
                "success": True,
                "message": "Item deleted successfully"
            }
        else:
            frappe.throw(_("Item not found"), frappe.ValidationError)
        
    except Exception as e:
        frappe.log_error(f"Error deleting item: {str(e)}", "Delete Order Item")
        return {
            "success": False,
            "error": f"Error deleting item: {str(e)}"
        }

@frappe.whitelist(allow_guest=False)
def get_order_details(order_name, doctype):
    """Get order details for modal display"""
    try:
        frappe.log_error(f"API called with order_name={order_name}, doctype={doctype}", "Modal API Debug")
        # Validate doctype
        valid_doctypes = ['Release Order', 'Inbound Order', 'VAS Order', 'Transfer Order', 'Stocktake Order']
        if doctype not in valid_doctypes:
            frappe.throw(_("Invalid doctype: {0}").format(doctype), frappe.ValidationError)
        
        # Get the order document
        order = frappe.get_doc(doctype, order_name)
        
        # Check customer permissions
        user_customer = get_customer_from_user()
        frappe.log_error(f"Debug: user_customer={user_customer}, order.customer={order.customer}", "Order Details Debug")
        if not user_customer or order.customer != user_customer:
            frappe.log_error(f"Permission denied: user_customer={user_customer}, order.customer={order.customer}", "Modal Permission Debug")
            frappe.throw(_("You don't have permission to view this order"), frappe.PermissionError)
        
        # Get order items
        items = frappe.get_all(
            f"{doctype} Item",
            filters={"parent": order_name},
            fields=["*"],
            order_by="idx"
        )
        
        # Map field names for modal display
        for item in items:
            # Map database fields to expected modal fields
            item['item_code'] = item.get('item', '')
            item['item_name'] = item.get('item_name', '')
            item['uom'] = item.get('uom', '')
            item['qty'] = item.get('quantity', 0)
            item['serial_no'] = item.get('serial_no', '')
            item['batch_no'] = item.get('batch_no', '')
            item['expiry_date'] = item.get('expiry_date', '') if item.get('expiry_date') else ''
            # Remove rate and amount fields
            item.pop('rate', None)
            item.pop('amount', None)
        
        # Calculate totals
        total_items = len(items)
        
        # Get order charges
        charges = frappe.get_all(
            f"{doctype} Charges",
            filters={"parent": order_name},
            fields=["*"],
            order_by="idx"
        )
        
        # Format order data
        order_data = {
            "name": order.name,
            "doctype": doctype,
            "customer": order.customer,
            "order_date": order.order_date.strftime("%Y-%m-%d") if order.order_date else "",
            "cust_reference": order.cust_reference or "",
            "priority": order.priority or "",
            "planned_date": order.planned_date.strftime("%Y-%m-%d %H:%M") if order.planned_date else "",
            "due_date": order.due_date.strftime("%Y-%m-%d %H:%M") if order.due_date else "",
            "notes": getattr(order, 'notes', '') or "",
            "status": get_order_status(order.docstatus),
            "status_color": get_status_color(order.docstatus),
            "company": order.company or "",
            "branch": order.branch or "",
            "cost_center": order.cost_center or "",
            "profit_center": order.profit_center or "",
            "contract": order.contract or "",
            "creation": order.creation.strftime("%Y-%m-%d %H:%M") if order.creation else "",
            "modified": order.modified.strftime("%Y-%m-%d %H:%M") if order.modified else "",
            "items": items,
            "charges": charges,
            "total_items": total_items,
            "can_edit": order.docstatus == 0
        }
        
        # Add order-specific fields
        if doctype == "VAS Order":
            order_data["vas_type"] = order.vas_type or ""
        elif doctype == "Stocktake Order":
            order_data["stocktake_type"] = getattr(order, 'stocktake_type', '') or ""
            order_data["scope"] = getattr(order, 'scope', '') or ""
        
        return {
            "success": True,
            "order": order_data
        }
        
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "error": "Order not found"
        }
    except Exception as e:
        frappe.log_error(f"Error loading order {order_name}: {str(e)}", "Order Details Error")
        return {
            "success": False,
            "error": f"Error loading order details: {str(e)}"
        }


def get_order_status(docstatus):
    """Get human-readable order status"""
    if docstatus == 0:
        return "Draft"
    elif docstatus == 1:
        return "Submitted"
    elif docstatus == 2:
        return "Cancelled"
    else:
        return "Unknown"


def get_status_color(docstatus):
    """Get status color for display"""
    if docstatus == 0:
        return "warning"
    elif docstatus == 1:
        return "success"
    elif docstatus == 2:
        return "danger"
    else:
        return "secondary"

