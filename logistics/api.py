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


def get_default_company():
    """Get default company"""
    return frappe.db.get_default("company") or frappe.get_single("Global Defaults").default_company


def get_default_branch(company=None, branch=None):
    """Get default branch for company"""
    if branch:
        return branch
    
    if not company:
        company = get_default_company()
    
    # Get first available branch for company
    branches = frappe.get_all(
        "Branch",
        filters={"company": company},
        fields=["name"],
        limit=1
    )
    
    if branches:
        return branches[0].name
    
    # If no branch found, create a default one
    try:
        default_branch = frappe.new_doc("Branch")
        default_branch.branch = "Main Branch"
        default_branch.company = company
        default_branch.insert(ignore_permissions=True)
        frappe.db.commit()
        return default_branch.name
    except Exception as e:
        frappe.log_error(f"Error creating default branch: {str(e)}", "Default Branch Creation")
        return None


def get_default_cost_center(company=None):
    """Get default cost center"""
    if not company:
        company = get_default_company()
    
    # First check Warehouse Settings
    try:
        warehouse_settings = frappe.get_single("Warehouse Settings")
        if warehouse_settings.default_cost_center:
            return warehouse_settings.default_cost_center
    except Exception:
        pass
    
    # Fallback to company's default cost center
    cost_centers = frappe.get_all(
        "Cost Center",
        filters={"company": company, "is_group": 0},
        fields=["name"],
        limit=1
    )
    
    if cost_centers:
        return cost_centers[0].name
    
    return None


def get_default_profit_center(company=None, customer=None):
    """Get default profit center"""
    if not company:
        company = get_default_company()
    
    # First check customer's custom field
    if customer:
        try:
            customer_doc = frappe.get_doc("Customer", customer)
            if hasattr(customer_doc, 'custom_default_warehouse_profit_center') and customer_doc.custom_default_warehouse_profit_center:
                return customer_doc.custom_default_warehouse_profit_center
        except Exception:
            pass
    
    # Fallback to company's default profit center
    profit_centers = frappe.get_all(
        "Profit Center",
        filters={"company": company, "is_group": 0},
        fields=["name"],
        limit=1
    )
    
    if profit_centers:
        return profit_centers[0].name
    
    return None


def get_customer_contract(customer, order_date=None):
    """Get customer contract - latest applicable contract that is still valid"""
    if not order_date:
        order_date = nowdate()
    
    try:
        # Get contracts for customer, ordered by start_date desc to get latest first
        contracts = frappe.get_all(
            "Warehouse Contract",
            filters={"customer": customer, "docstatus": 1},
            fields=["name", "start_date", "end_date"],
            order_by="start_date desc"
        )
        
        for contract in contracts:
            # Check if contract is valid for the order date
            if (not contract.start_date or contract.start_date <= order_date) and \
               (not contract.end_date or contract.end_date >= order_date):
                return contract.name
        
        return None
    except Exception as e:
        frappe.log_error(f"Error getting customer contract: {str(e)}", "Customer Contract")
        return None


def create_default_contract(customer, order_date=None):
    """Create a default contract for customer"""
    if not order_date:
        order_date = nowdate()
    
    try:
        contract = frappe.new_doc("Warehouse Contract")
        contract.customer = customer
        contract.start_date = order_date
        contract.end_date = frappe.utils.add_days(order_date, 365)  # 1 year from order date
        contract.contract_type = "Standard"
        contract.insert(ignore_permissions=True)
        frappe.db.commit()
        return contract.name
    except Exception as e:
        frappe.log_error(f"Error creating default contract: {str(e)}", "Default Contract Creation")
        return None


@frappe.whitelist(allow_guest=False)
def create_inbound_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, branch=None):
    """Create a new Inbound Order for the customer"""
    try:
        # Get customer
        customer = get_customer_from_user()
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."))
        
        # Get default values for mandatory fields
        company = get_default_company()
        branch = get_default_branch(company, branch)
        cost_center = get_default_cost_center(company)
        profit_center = get_default_profit_center(company, customer)
        contract = get_customer_contract(customer, order_date)
        
        # Create default contract if none found
        if not contract:
            contract = create_default_contract(customer, order_date)
            if not contract:
                frappe.throw(_("No active contract found for customer {0}. Please contact support.").format(customer))
        
        # Create the order
        order = frappe.new_doc("Inbound Order")
        order.customer = customer
        order.order_date = order_date
        order.cust_reference = cust_reference
        order.priority = priority
        order.planned_date = planned_date
        order.due_date = due_date
        order.notes = notes
        order.company = company
        order.branch = branch
        order.cost_center = cost_center
        order.profit_center = profit_center
        order.contract = contract
        
        # Add sample items
        order.append("items", {
            "item": "WHSSTR",
            "item_name": "Stripping Charge",
            "uom": "Cubic Meter",
            "quantity": 10
        })
        
        order.append("items", {
            "item": "AD-ACC-002-CUST-ADIDAS",
            "item_name": "Adidas Logo Performance Cap",
            "uom": "Box",
            "quantity": 10
        })
        
        order.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Inbound Order {order.name} created successfully",
            "order_name": order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating inbound order: {str(e)}", "Create Inbound Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))


@frappe.whitelist(allow_guest=False)
def create_release_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, branch=None):
    """Create a new Release Order for the customer"""
    try:
        # Get customer
        customer = get_customer_from_user()
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."))
        
        # Get default values for mandatory fields
        company = get_default_company()
        branch = get_default_branch(company, branch)
        cost_center = get_default_cost_center(company)
        profit_center = get_default_profit_center(company, customer)
        contract = get_customer_contract(customer, order_date)
        
        # Create default contract if none found
        if not contract:
            contract = create_default_contract(customer, order_date)
            if not contract:
                frappe.throw(_("No active contract found for customer {0}. Please contact support.").format(customer))
        
        # Create the order
        order = frappe.new_doc("Release Order")
        order.customer = customer
        order.order_date = order_date
        order.cust_reference = cust_reference
        order.priority = priority
        order.planned_date = planned_date
        order.due_date = due_date
        order.notes = notes
        order.company = company
        order.branch = branch
        order.cost_center = cost_center
        order.profit_center = profit_center
        order.contract = contract
        
        # Add sample items
        order.append("items", {
            "item": "WHSSTR",
            "item_name": "Stripping Charge",
            "uom": "Cubic Meter",
            "quantity": 10
        })
        
        order.append("items", {
            "item": "AD-ACC-002-CUST-ADIDAS",
            "item_name": "Adidas Logo Performance Cap",
            "uom": "Box",
            "quantity": 10
        })
        
        order.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Release Order {order.name} created successfully",
            "order_name": order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating release order: {str(e)}", "Create Release Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))


@frappe.whitelist(allow_guest=False)
def create_vas_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, vas_type=None, branch=None):
    """Create a new VAS Order for the customer"""
    try:
        # Get customer
        customer = get_customer_from_user()
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."))
        
        # Get default values for mandatory fields
        company = get_default_company()
        branch = get_default_branch(company, branch)
        cost_center = get_default_cost_center(company)
        profit_center = get_default_profit_center(company, customer)
        contract = get_customer_contract(customer, order_date)
        
        # Create default contract if none found
        if not contract:
            contract = create_default_contract(customer, order_date)
            if not contract:
                frappe.throw(_("No active contract found for customer {0}. Please contact support.").format(customer))
        
        # Create the order
        order = frappe.new_doc("VAS Order")
        order.customer = customer
        order.order_date = order_date
        order.cust_reference = cust_reference
        order.priority = priority
        order.planned_date = planned_date
        order.due_date = due_date
        order.notes = notes
        order.company = company
        order.branch = branch
        order.cost_center = cost_center
        order.profit_center = profit_center
        order.contract = contract
        order.type = vas_type or "Repackaging"
        
        # Add sample items
        order.append("items", {
            "item": "WHSSTR",
            "item_name": "Stripping Charge",
            "uom": "Cubic Meter",
            "quantity": 10
        })
        
        order.append("items", {
            "item": "AD-ACC-002-CUST-ADIDAS",
            "item_name": "Adidas Logo Performance Cap",
            "uom": "Box",
            "quantity": 10
        })
        
        order.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"VAS Order {order.name} created successfully",
            "order_name": order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating VAS order: {str(e)}", "Create VAS Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))


@frappe.whitelist(allow_guest=False)
def create_transfer_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, branch=None):
    """Create a new Transfer Order for the customer"""
    try:
        # Get customer
        customer = get_customer_from_user()
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."))
        
        # Get default values for mandatory fields
        company = get_default_company()
        branch = get_default_branch(company, branch)
        cost_center = get_default_cost_center(company)
        profit_center = get_default_profit_center(company, customer)
        contract = get_customer_contract(customer, order_date)
        
        # Create default contract if none found
        if not contract:
            contract = create_default_contract(customer, order_date)
            if not contract:
                frappe.throw(_("No active contract found for customer {0}. Please contact support.").format(customer))
        
        # Create the order
        order = frappe.new_doc("Transfer Order")
        order.customer = customer
        order.order_date = order_date
        order.cust_reference = cust_reference
        order.priority = priority
        order.planned_date = planned_date
        order.due_date = due_date
        order.notes = notes
        order.company = company
        order.branch = branch
        order.cost_center = cost_center
        order.profit_center = profit_center
        order.contract = contract
        
        # Add sample items
        order.append("items", {
            "item": "WHSSTR",
            "item_name": "Stripping Charge",
            "uom": "Cubic Meter",
            "quantity": 10
        })
        
        order.append("items", {
            "item": "AD-ACC-002-CUST-ADIDAS",
            "item_name": "Adidas Logo Performance Cap",
            "uom": "Box",
            "quantity": 10
        })
        
        order.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Transfer Order {order.name} created successfully",
            "order_name": order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating transfer order: {str(e)}", "Create Transfer Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))


@frappe.whitelist(allow_guest=False)
def create_stocktake_order(order_date, cust_reference=None, priority="Normal", planned_date=None, due_date=None, notes=None, stocktake_type="Full", scope="Site", branch=None):
    """Create a new Stocktake Order for the customer"""
    try:
        # Get customer
        customer = get_customer_from_user()
        if not customer:
            frappe.throw(_("Customer not found. Please contact support."))
        
        # Get default values for mandatory fields
        company = get_default_company()
        branch = get_default_branch(company, branch)
        cost_center = get_default_cost_center(company)
        profit_center = get_default_profit_center(company, customer)
        contract = get_customer_contract(customer, order_date)
        
        # Create default contract if none found
        if not contract:
            contract = create_default_contract(customer, order_date)
            if not contract:
                frappe.throw(_("No active contract found for customer {0}. Please contact support.").format(customer))
        
        # Create the order
        order = frappe.new_doc("Stocktake Order")
        order.customer = customer
        order.order_date = order_date
        order.cust_reference = cust_reference
        order.priority = priority
        order.planned_date = planned_date
        order.due_date = due_date
        order.notes = notes
        order.company = company
        order.branch = branch
        order.cost_center = cost_center
        order.profit_center = profit_center
        order.contract = contract
        order.type = stocktake_type
        order.scope = scope
        
        # Add sample items
        order.append("items", {
            "item": "WHSSTR",
            "item_name": "Stripping Charge",
            "uom": "Cubic Meter",
            "quantity": 10
        })
        
        order.append("items", {
            "item": "AD-ACC-002-CUST-ADIDAS",
            "item_name": "Adidas Logo Performance Cap",
            "uom": "Box",
            "quantity": 10
        })
        
        order.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Stocktake Order {order.name} created successfully",
            "order_name": order.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating stocktake order: {str(e)}", "Create Stocktake Order API")
        frappe.throw(_("Error creating order: {0}").format(str(e)))