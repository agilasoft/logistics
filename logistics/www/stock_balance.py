# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
from frappe.utils import formatdate


def get_context(context):
    """Get context for stock balance web page"""
    
    # Get all customers for user
    all_customers = get_customers_for_user()
    
    if not all_customers:
        # For testing, use a default customer or show a message
        context.update({
            "title": "Stock Balance",
            "page_title": "Stock Balance",
            "error_message": "Customer not found. Please contact support."
        })
        return context
    
    # Get selected customer from request or use first one
    customer = get_customer_from_request()
    
    # If user has multiple customers, show customer selection
    if len(all_customers) > 1:
        context.update({
            "all_customers": all_customers,
            "selected_customer": customer,
            "show_customer_dropdown": True,
            "title": "Stock Balance - Select Customer",
            "page_title": "Stock Balance"
        })
        
        # If no customer selected, show selection page
        if not customer:
            return context
    
    # Get customer info
    try:
        customer_doc = frappe.get_doc("Customer", customer)
        customer_name = customer_doc.customer_name
        customer_email = customer_doc.email_id
    except:
        customer_name = "Unknown Customer"
        customer_email = ""
    
    # Get filter parameters
    form_dict = frappe.form_dict or {}
    date_from = form_dict.get('date_from')
    date_to = form_dict.get('date_to')
    item_code = form_dict.get('item_code')
    branch = form_dict.get('branch')
    
    # Set default date range (last 30 days)
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
    
    # Get stock balance data with filters
    try:
        stock_balance = get_customer_stock_balance(customer, date_from, date_to, item_code, branch)
    except Exception as e:
        frappe.log_error(f"Error getting stock balance: {str(e)}", "Stock Balance Portal")
        stock_balance = []
    
    # Get available items for filter
    try:
        available_items = get_available_items(customer)
    except Exception as e:
        frappe.log_error(f"Error getting available items: {str(e)}", "Stock Balance Portal")
        available_items = []
    
    # Get available branches for filter
    try:
        available_branches = get_available_branches(customer)
    except Exception as e:
        frappe.log_error(f"Error getting available branches: {str(e)}", "Stock Balance Portal")
        available_branches = []
    
    # Debug logging
    print(f"Debug: get_context - available_branches count: {len(available_branches)}")
    print(f"Debug: get_context - available_branches: {available_branches}")
    
    # Calculate summary statistics
    try:
        total_items = len(stock_balance) if stock_balance else 0
        total_quantity = sum(item.get('qty', 0) for item in stock_balance) if stock_balance else 0
        total_value = sum(item.get('stock_value', 0) for item in stock_balance) if stock_balance else 0
    except Exception as e:
        frappe.log_error(f"Error calculating summary statistics: {str(e)}", "Stock Balance Portal")
        total_items = 0
        total_quantity = 0
        total_value = 0
    
    # Calculate expired items count
    try:
        expiring_items_count = get_expired_items_count(customer, date_to, item_code, branch)
    except Exception as e:
        frappe.log_error(f"Error getting expired items count: {str(e)}", "Stock Balance Portal")
        expiring_items_count = 0
    
    # Calculate handling units count
    try:
        handling_units_count = get_handling_units_count(customer, item_code, branch)
    except Exception as e:
        frappe.log_error(f"Error getting handling units count: {str(e)}", "Stock Balance Portal")
        handling_units_count = 0
    
    context.update({
        "customer_id": customer or "",
        "customer_name": customer_name or "Unknown Customer",
        "customer_email": customer_email or "",
        "stock_balance": stock_balance or [],
        "available_items": available_items or [],
        "available_branches": available_branches or [],
        "date_from": date_from or "",
        "date_to": date_to or "",
        "item_code": item_code or "",
        "branch": branch or "",
        "total_items": total_items or 0,
        "total_quantity": total_quantity or 0,
        "total_value": total_value or 0,
        "expiring_items_count": expiring_items_count or 0,
        "handling_units_count": handling_units_count or 0,
        "title": f"Stock Balance - {customer_name}" if customer_name else "Stock Balance",
        "page_title": "Stock Balance"
    })
    
    return context


def get_customer_from_request():
    """Get customer from request parameters or session"""
    
    # Try to get customer from URL parameters
    customer = frappe.form_dict.get('customer')
    if customer:
        return customer
    
    # Try to get customer from session
    customer = frappe.session.get('customer')
    if customer:
        return customer
    
    # Try user email - improved logic
    user = frappe.session.user
    if user and user != "Guest":
        # Method 1: Check Portal Users field in Customer doctype
        try:
            portal_users = frappe.get_all(
                "Portal User",
                filters={"user": user},
                fields=["parent"],
                limit=1
            )
            if portal_users:
                return portal_users[0].parent
        except Exception as e:
            frappe.log_error(f"Error checking portal users: {str(e)}", "Stock Balance Portal")
        
        # Method 2: Direct email match in Customer
        customers = frappe.get_all(
            "Customer",
            filters={"email_id": user},
            fields=["name"],
            limit=1
        )
        if customers:
            return customers[0].name
        
        # Method 3: Through Contact links
        contact = frappe.get_value("Contact", {"email_id": user}, "name")
        if contact:
            # Get customer links from contact
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
        
        # Method 4: Check if user has Customer role and find through contact
        try:
            user_doc = frappe.get_doc("User", user)
            if user_doc.email:
                # Find customer by email
                customers = frappe.get_all("Customer", 
                    filters={"email_id": user_doc.email}, 
                    fields=["name"]
                )
                if customers:
                    return customers[0].name
        except Exception as e:
            frappe.log_error(f"Error getting customer from user email: {str(e)}", "Stock Balance Portal")
    
    return None


def get_customers_for_user():
    """Get all customers associated with the current user"""
    user = frappe.session.user
    customers = []
    
    if user and user != "Guest":
        # Method 1: Check Portal Users field in Customer doctype
        try:
            portal_users = frappe.get_all(
                "Portal User",
                filters={"user": user, "parenttype": "Customer"},
                fields=["parent", "parenttype"]
            )
            for pu in portal_users:
                customers.append(pu.parent)
        except Exception as e:
            pass
        
        # Method 2: Direct email match in Customer
        direct_customers = frappe.get_all(
            "Customer",
            filters={"email_id": user},
            fields=["name"]
        )
        for dc in direct_customers:
            if dc.name not in customers:
                customers.append(dc.name)
        
        # Method 3: Through Contact links
        contact = frappe.get_value("Contact", {"email_id": user}, "name")
        if contact:
            customer_links = frappe.get_all(
                "Dynamic Link",
                filters={
                    "parent": contact,
                    "link_doctype": "Customer"
                },
                fields=["link_name"]
            )
            for cl in customer_links:
                if cl.link_name not in customers:
                    customers.append(cl.link_name)
    
    return customers


def get_customer_stock_balance(customer, date_from, date_to, item_code=None, branch=None):
    """Get stock balance for customer with filters using Warehouse Stock Ledger"""
    try:
        # Build the SQL query similar to warehouse_stock_balance report
        params = {"from_date": date_from, "to_date": date_to, "customer": customer}
        where_bits = ["1=1"]
        
        # Add customer filter
        where_bits.append("wi.customer = %(customer)s")
        
        # Optional filters
        if item_code:
            where_bits.append("wsl.item = %(item)s")
            params["item"] = item_code
        
        if branch:
            where_bits.append("wsl.branch = %(branch)s")
            params["branch"] = branch
        
        where_sql = " AND ".join(where_bits)
        
        # Use the same logic as warehouse_stock_balance report
        data = frappe.db.sql(
            """
            WITH base AS (
                SELECT
                    wsl.item,
                    wsl.posting_date,
                    wsl.quantity,
                    wsl.creation,
                    COALESCE(hu.company, sl.company) AS company,
                    wsl.branch
                FROM `tabWarehouse Stock Ledger` wsl
                LEFT JOIN `tabStorage Location` sl ON sl.name = wsl.storage_location
                LEFT JOIN `tabHandling Unit`   hu ON hu.name = wsl.handling_unit
                LEFT JOIN `tabWarehouse Item`  wi ON wi.name = wsl.item
                WHERE {where_sql}
            ),
            first_on_day AS (
                SELECT item, MIN(creation) AS first_creation
                FROM base
                WHERE posting_date = %(from_date)s
                GROUP BY item
            )
            SELECT
                b.item,
                wi.item_name,
                wi.customer,
                b.branch,
                -- Beginning: balance after the first entry on from_date
                COALESCE(SUM(CASE WHEN b.posting_date < %(from_date)s THEN b.quantity ELSE 0 END), 0)
                +
                COALESCE(SUM(CASE
                    WHEN b.posting_date = %(from_date)s AND b.creation = fod.first_creation
                    THEN b.quantity ELSE 0 END), 0) AS beg_qty,
                -- In within window
                COALESCE(SUM(CASE
                    WHEN b.posting_date BETWEEN %(from_date)s AND %(to_date)s
                     AND b.quantity > 0 THEN b.quantity ELSE 0 END), 0) AS in_qty,
                -- Out within window
                COALESCE(SUM(CASE
                    WHEN b.posting_date BETWEEN %(from_date)s AND %(to_date)s
                     AND b.quantity < 0 THEN -b.quantity ELSE 0 END), 0) AS out_qty,
                -- Ending up to to_date
                COALESCE(SUM(CASE
                    WHEN b.posting_date <= %(to_date)s THEN b.quantity ELSE 0 END), 0) AS ending_qty,
                -- Get latest transaction info
                MAX(b.posting_date) AS last_transaction_date,
                MAX(b.creation) AS last_creation
            FROM base b
            LEFT JOIN first_on_day fod ON fod.item = b.item
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = b.item
            GROUP BY b.item, wi.item_name, wi.customer, b.branch
            HAVING ending_qty > 0
            ORDER BY wi.item_name
            """.format(where_sql=where_sql),
            params,
            as_dict=True,
        )
        
        # Format the data for display
        result = []
        for row in data:
            # Convert datetime to string to avoid JSON serialization issues
            last_transaction_date = row.last_transaction_date
            if last_transaction_date:
                try:
                    # Format as datetime instead of just date
                    if hasattr(last_transaction_date, 'strftime'):
                        last_transaction_date = last_transaction_date.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        last_transaction_date = str(last_transaction_date)
                except:
                    last_transaction_date = str(last_transaction_date)
            else:
                last_transaction_date = "N/A"
            
            result.append({
                "item_code": row.item,
                "item_name": row.item_name,
                "customer": row.customer,
                "branch": row.branch or "N/A",
                "qty": row.ending_qty,
                "beg_qty": row.beg_qty,
                "in_qty": row.in_qty,
                "out_qty": row.out_qty,
                "last_transaction_date": last_transaction_date,
                "stock_value": 0,  # Calculate if needed
                "last_voucher_type": "Warehouse Stock Ledger",
                "last_voucher_no": "N/A"
            })
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error getting stock balance: {str(e)}", "Stock Balance Portal")
        return []


def get_available_items(customer):
    """Get list of available items for customer"""
    try:
        items = frappe.get_all(
            "Warehouse Item",
            filters={"customer": customer},
            fields=["name", "item_name"],
            order_by="item_name"
        )
        return items
    except Exception as e:
        frappe.log_error(f"Error getting available items: {str(e)}", "Stock Balance Portal")
        return []


def get_available_branches(customer):
    """Get list of available branches for customer from Warehouse Stock Ledger"""
    try:
        # Get branches from Warehouse Stock Ledger for this customer
        branches = frappe.db.sql("""
            SELECT DISTINCT wsl.branch AS name, wsl.branch AS warehouse_name
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = wsl.item
            WHERE wi.customer = %s
            AND wsl.branch IS NOT NULL
            AND wsl.branch != ''
            ORDER BY wsl.branch
        """, (customer,), as_dict=True)
        
        print(f"Debug: Found {len(branches)} branches from Warehouse Stock Ledger for customer {customer}: {branches}")
        
        if not branches:
            # If no customer-specific branches, get all branches from stock ledger
            branches = frappe.db.sql("""
                SELECT DISTINCT wsl.branch AS name, wsl.branch AS warehouse_name
                FROM `tabWarehouse Stock Ledger` wsl
                WHERE wsl.branch IS NOT NULL
                AND wsl.branch != ''
                ORDER BY wsl.branch
            """, as_dict=True)
            
            print(f"Debug: Found {len(branches)} branches from all Warehouse Stock Ledger entries: {branches}")
        
        return branches
        
    except Exception as e:
        print(f"Error getting available branches: {str(e)}")
        return []


def get_warehouse_fallback(customer):
    """Fallback to Warehouse DocType if Branch DocType is not available"""
    try:
        # Try to get warehouses from stock ledger first
        warehouses = frappe.db.sql("""
            SELECT DISTINCT 
                wsl.warehouse AS name,
                w.warehouse_name
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabWarehouse` w ON w.name = wsl.warehouse
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = wsl.item
            WHERE wi.customer = %s
            AND wsl.warehouse IS NOT NULL
            AND wsl.warehouse != ''
            ORDER BY wsl.warehouse
        """, (customer,), as_dict=True)
        
        # If no warehouses found from stock ledger, get all active warehouses
        if not warehouses:
            warehouses = frappe.db.sql("""
                SELECT name, warehouse_name
                FROM `tabWarehouse`
                WHERE disabled = 0
                ORDER BY name
            """, as_dict=True)
        
        # Ensure we have the right field names
        for warehouse in warehouses:
            if not warehouse.get('warehouse_name'):
                warehouse['warehouse_name'] = warehouse.get('name', '')
        
        return warehouses
    except Exception as e:
        frappe.log_error(f"Error getting warehouse fallback: {str(e)}", "Stock Balance Portal")
        return []


def get_expired_items_count(customer, current_date, item_code=None, branch=None):
    """Get count of expired items for customer with filters"""
    try:
        # Build WHERE conditions
        where_conditions = ["wi.customer = %s", "wi.expiry_date IS NOT NULL", "wi.expiry_date < %s", "wsl.quantity > 0"]
        params = [customer, current_date]
        
        if item_code:
            where_conditions.append("wi.name = %s")
            params.append(item_code)
            
        if branch:
            where_conditions.append("wsl.branch = %s")
            params.append(branch)
        
        where_sql = " AND ".join(where_conditions)
        
        # Get count of items that have expired (expiry_date < current_date)
        expired_count = frappe.db.sql(f"""
            SELECT COUNT(DISTINCT wi.name) as expired_count
            FROM `tabWarehouse Item` wi
            LEFT JOIN `tabWarehouse Stock Ledger` wsl ON wsl.item = wi.name
            LEFT JOIN `tabStorage Location` sl ON sl.name = wsl.storage_location
            LEFT JOIN `tabHandling Unit` hu ON hu.name = wsl.handling_unit
            WHERE {where_sql}
        """, params, as_dict=True)
        
        return expired_count[0].expired_count if expired_count else 0
    except Exception as e:
        frappe.log_error(f"Error getting expired items count: {str(e)}", "Stock Balance Portal")
        return 0


def get_handling_units_count(customer, item_code=None, branch=None):
    """Get count of handling units for customer with filters"""
    try:
        # Build WHERE conditions
        where_conditions = ["wi.customer = %s", "hu.name IS NOT NULL"]
        params = [customer]
        
        if item_code:
            where_conditions.append("wi.name = %s")
            params.append(item_code)
            
        if branch:
            where_conditions.append("wsl.branch = %s")
            params.append(branch)
        
        where_sql = " AND ".join(where_conditions)
        
        # Get count of distinct handling units for this customer
        handling_units_count = frappe.db.sql(f"""
            SELECT COUNT(DISTINCT hu.name) as units_count
            FROM `tabHandling Unit` hu
            LEFT JOIN `tabWarehouse Stock Ledger` wsl ON wsl.handling_unit = hu.name
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = wsl.item
            WHERE {where_sql}
        """, params, as_dict=True)
        
        return handling_units_count[0].units_count if handling_units_count else 0
    except Exception as e:
        frappe.log_error(f"Error getting handling units count: {str(e)}", "Stock Balance Portal")
        return 0
