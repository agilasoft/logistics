# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta
import math


def get_context(context):
    """Get context for warehousing portal web page"""
    
    # Get all customers for user
    all_customers = get_customers_for_user()
    
    if not all_customers:
        # For testing, use a default customer or show a message
        context.update({
            "title": "Warehousing Portal",
            "page_title": "Warehousing Portal",
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
            "title": "Warehousing Portal - Select Customer",
            "page_title": "Warehousing Portal"
        })
        
        # If no customer selected, show selection page
        if not customer:
            return context
    
    # Get customer info
    try:
        customer_doc = frappe.get_doc("Customer", customer)
        customer_name = customer_doc.customer_name
        customer_email = customer_doc.email_id
    except Exception:
        customer_name = "Unknown Customer"
        customer_email = ""
    
    # Get filter parameters
    form_dict = frappe.form_dict or {}
    date_from = form_dict.get('date_from')
    date_to = form_dict.get('date_to')
    item_code = form_dict.get('item_code')
    warehouse = form_dict.get('warehouse')
    
    # Set default date range (last 30 days)
    if not date_from:
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
    
    # Get stock balance data
    try:
        stock_data = get_customer_stock_balance(customer, date_from, date_to, item_code, warehouse)
    except Exception as e:
        frappe.log_error(f"Error getting stock balance: {str(e)}", "Warehousing Portal")
        stock_data = []
    
    # Get available items for filter
    try:
        available_items = get_available_items(customer)
    except Exception as e:
        frappe.log_error(f"Error getting available items: {str(e)}", "Warehousing Portal")
        available_items = []
    
    # Get available warehouses for filter
    try:
        available_warehouses = get_available_warehouses(customer)
    except Exception as e:
        frappe.log_error(f"Error getting available warehouses: {str(e)}", "Warehousing Portal")
        available_warehouses = []
    
    # Calculate summary statistics
    try:
        total_items = len(stock_data) if stock_data else 0
        total_quantity = sum(item.get('qty', 0) for item in stock_data) if stock_data else 0
        total_value = sum(item.get('stock_value', 0) for item in stock_data) if stock_data else 0
    except Exception as e:
        frappe.log_error(f"Error calculating summary statistics: {str(e)}", "Warehousing Portal")
        total_items = 0
        total_quantity = 0
        total_value = 0
    
    # Calculate expired items (items that have already expired)
    try:
        expiring_items_count = get_expired_items_count(customer, date_to)
    except Exception as e:
        frappe.log_error(f"Error getting expired items count: {str(e)}", "Warehousing Portal")
        expiring_items_count = 0
    
    # Calculate handling units count
    try:
        handling_units_count = get_handling_units_count(customer)
    except Exception as e:
        frappe.log_error(f"Error getting handling units count: {str(e)}", "Warehousing Portal")
        handling_units_count = 0
    
    # Get transaction metrics
    try:
        transaction_metrics = get_transaction_metrics(customer)
    except Exception as e:
        frappe.log_error(f"Error getting transaction metrics: {str(e)}", "Warehousing Portal")
        transaction_metrics = {"this_month": 0, "this_year": 0}
    
    # Get expiry risk data
    try:
        expiry_risk_data = get_expiry_risk_data(customer)
    except Exception as e:
        frappe.log_error(f"Error getting expiry risk data: {str(e)}", "Warehousing Portal")
        expiry_risk_data = {"expiring_30_days": 0, "expiring_90_days": 0, "expiring_items": [], "risk_percentage": 0, "needle_x": 100, "needle_y": 20}
    
    # Get pending orders
    try:
        pending_orders = get_pending_orders(customer)
    except Exception as e:
        frappe.log_error(f"Error getting pending orders: {str(e)}", "Warehousing Portal")
        pending_orders = {"pending_jobs": [], "pending_stock_entries": [], "total_pending": 0, "inbound_count": 0, "release_count": 0, "vas_count": 0, "transfer_count": 0, "stocktake_count": 0}
    
    # Get handling units trend data
    try:
        handling_units_trend = get_handling_units_trend(customer)
    except Exception as e:
        frappe.log_error(f"Error getting handling units trend: {str(e)}", "Warehousing Portal")
        handling_units_trend = {"trend_data": [], "trend_direction": "stable", "trend_percentage": 0, "current_units": 0, "peak_units": 0}
    
    context.update({
        "customer": customer or "",
        "customer_name": customer_name or "Unknown Customer",
        "customer_email": customer_email or "",
        "stock_data": stock_data or [],
        "available_items": available_items or [],
        "available_warehouses": available_warehouses or [],
        "date_from": date_from or "",
        "date_to": date_to or "",
        "item_code": item_code or "",
        "warehouse": warehouse or "",
        "selected_branch": warehouse or "",
        "total_items": total_items or 0,
        "total_quantity": total_quantity or 0,
        "total_value": total_value or 0,
        "expiring_items_count": expiring_items_count or 0,
        "handling_units_count": handling_units_count or 0,
        "transaction_metrics": transaction_metrics or {"this_month": 0, "this_year": 0},
        "expiry_risk_data": expiry_risk_data or {"expiring_30_days": 0, "expiring_90_days": 0, "expiring_items": [], "risk_percentage": 0, "needle_x": 100, "needle_y": 20},
        "pending_orders": pending_orders or {"pending_jobs": [], "pending_stock_entries": [], "total_pending": 0, "inbound_count": 0, "release_count": 0, "vas_count": 0, "transfer_count": 0, "stocktake_count": 0},
        "handling_units_trend": handling_units_trend or {"trend_data": [], "monthly_data": [], "trend_direction": "stable", "trend_percentage": 0, "current_units": 0, "peak_units": 0},
        "title": f"Warehousing Portal - {customer_name}" if customer_name else "Warehousing Portal",
        "page_title": "Warehousing Portal"
    })
    
    return context


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


def get_customer_from_request():
    """Extract customer from request parameters"""
    # Try URL parameter first
    customer = frappe.form_dict.get('customer')
    if customer:
        return customer
    
    # Try session variable
    customer = frappe.session.get('customer')
    if customer:
        return customer
    
    # Get all customers for user and return the first one
    customers = get_customers_for_user()
    if customers:
        return customers[0]
    
    return None


def get_customer_stock_balance(customer, date_from, date_to, item_code=None, warehouse=None):
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
                    COALESCE(hu.branch,  sl.branch)  AS branch
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
            GROUP BY b.item, wi.item_name, wi.customer
            HAVING ending_qty > 0
            ORDER BY wi.item_name
            """.format(where_sql=where_sql),
            params,
            as_dict=True,
        )
        
        # Format the data for display
        result = []
        for row in data:
            result.append({
                "item_code": row.item,
                "item_name": row.item_name,
                "customer": row.customer,
                "qty": row.ending_qty,
                "beg_qty": row.beg_qty,
                "in_qty": row.in_qty,
                "out_qty": row.out_qty,
                "branch": getattr(row, 'branch', 'N/A'),
                "last_transaction_date": row.last_transaction_date,
                "stock_value": 0,  # Calculate if needed
                "last_voucher_type": "Warehouse Stock Ledger",
                "last_voucher_no": "N/A"
            })
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error getting stock balance: {str(e)}", "Warehousing Portal")
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
        frappe.log_error(f"Error getting available items: {str(e)}", "Warehousing Portal")
        return []


def get_available_warehouses(customer):
    """Get list of available branches for customer"""
    try:
        # Get all branches from Branch DocType
        branches = frappe.db.sql("""
            SELECT name, branch
            FROM `tabBranch`
            ORDER BY branch
        """, as_dict=True)
        
        print(f"Debug: Found {len(branches)} branches from Branch DocType: {branches}")
        
        # Ensure we have the right field names for dropdown
        for branch in branches:
            if not branch.get('branch'):
                branch['warehouse_name'] = branch.get('name', '')
            else:
                branch['warehouse_name'] = branch.get('branch', branch.get('name', ''))
        
        print(f"Debug: Returning {len(branches)} branches: {branches}")
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
        frappe.log_error(f"Error getting warehouse fallback: {str(e)}", "Warehousing Portal")
        return []


def get_expired_items_count(customer, current_date):
    """Get count of expired items for customer"""
    try:
        # Get count of items that have expired (expiry_date < current_date)
        expired_count = frappe.db.sql("""
            SELECT COUNT(DISTINCT wi.name) as expired_count
            FROM `tabWarehouse Item` wi
            LEFT JOIN `tabWarehouse Stock Ledger` wsl ON wsl.item = wi.name
            LEFT JOIN `tabStorage Location` sl ON sl.name = wsl.storage_location
            LEFT JOIN `tabHandling Unit` hu ON hu.name = wsl.handling_unit
            WHERE wi.customer = %s
            AND wi.expiry_date IS NOT NULL
            AND wi.expiry_date < %s
            AND wsl.quantity > 0
        """, (customer, current_date), as_dict=True)
        
        return expired_count[0].expired_count if expired_count else 0
    except Exception as e:
        frappe.log_error(f"Error getting expired items count: {str(e)}", "Warehousing Portal")
        return 0


def get_handling_units_count(customer):
    """Get count of handling units for customer"""
    try:
        # Get count of distinct handling units for this customer
        handling_units_count = frappe.db.sql("""
            SELECT COUNT(DISTINCT hu.name) as units_count
            FROM `tabHandling Unit` hu
            LEFT JOIN `tabWarehouse Stock Ledger` wsl ON wsl.handling_unit = hu.name
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = wsl.item
            WHERE wi.customer = %s
            AND hu.name IS NOT NULL
        """, (customer,), as_dict=True)
        
        return handling_units_count[0].units_count if handling_units_count else 0
    except Exception as e:
        frappe.log_error(f"Error getting handling units count: {str(e)}", "Warehousing Portal")
        return 0


def get_transaction_metrics(customer):
    """Get transaction metrics for this month and year"""
    try:
        current_date = datetime.now()
        current_month_start = current_date.replace(day=1).strftime('%Y-%m-%d')
        current_year_start = current_date.replace(month=1, day=1).strftime('%Y-%m-%d')
        
        # Get transactions this month
        monthly_transactions = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = wsl.item
            WHERE wi.customer = %s
            AND wsl.posting_date >= %s
        """, (customer, current_month_start), as_dict=True)
        
        # Get transactions this year
        yearly_transactions = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = wsl.item
            WHERE wi.customer = %s
            AND wsl.posting_date >= %s
        """, (customer, current_year_start), as_dict=True)
        
        return {
            "this_month": monthly_transactions[0].count if monthly_transactions else 0,
            "this_year": yearly_transactions[0].count if yearly_transactions else 0
        }
    except Exception as e:
        frappe.log_error(f"Error getting transaction metrics: {str(e)}", "Warehousing Portal")
        return {"this_month": 0, "this_year": 0}


def get_expiry_risk_data(customer):
    """Get expiry risk data for items expiring soon"""
    try:
        current_date = datetime.now()
        next_30_days = (current_date + timedelta(days=30)).strftime('%Y-%m-%d')
        next_90_days = (current_date + timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Items expiring in next 30 days
        expiring_30_days = frappe.db.sql("""
            SELECT COUNT(DISTINCT wi.name) as count
            FROM `tabWarehouse Item` wi
            LEFT JOIN `tabWarehouse Stock Ledger` wsl ON wsl.item = wi.name
            WHERE wi.customer = %s
            AND wi.expiry_date IS NOT NULL
            AND wi.expiry_date BETWEEN %s AND %s
            AND wsl.quantity > 0
        """, (customer, current_date.strftime('%Y-%m-%d'), next_30_days), as_dict=True)
        
        # Items expiring in next 90 days
        expiring_90_days = frappe.db.sql("""
            SELECT COUNT(DISTINCT wi.name) as count
            FROM `tabWarehouse Item` wi
            LEFT JOIN `tabWarehouse Stock Ledger` wsl ON wsl.item = wi.name
            WHERE wi.customer = %s
            AND wi.expiry_date IS NOT NULL
            AND wi.expiry_date BETWEEN %s AND %s
            AND wsl.quantity > 0
        """, (customer, current_date.strftime('%Y-%m-%d'), next_90_days), as_dict=True)
        
        # Get detailed expiring items
        expiring_items = frappe.db.sql("""
            SELECT 
                wi.name as item_code,
                wi.item_name,
                wi.expiry_date,
                SUM(wsl.quantity) as quantity,
                DATEDIFF(wi.expiry_date, %s) as days_to_expiry
            FROM `tabWarehouse Item` wi
            LEFT JOIN `tabWarehouse Stock Ledger` wsl ON wsl.item = wi.name
            WHERE wi.customer = %s
            AND wi.expiry_date IS NOT NULL
            AND wi.expiry_date BETWEEN %s AND %s
            AND wsl.quantity > 0
            GROUP BY wi.name, wi.item_name, wi.expiry_date
            ORDER BY wi.expiry_date ASC
            LIMIT 10
        """, (current_date.strftime('%Y-%m-%d'), customer, current_date.strftime('%Y-%m-%d'), next_90_days), as_dict=True)
        
        # Calculate risk percentage and meter position
        total_items = frappe.db.sql("""
            SELECT COUNT(DISTINCT wi.name) as count
            FROM `tabWarehouse Item` wi
            LEFT JOIN `tabWarehouse Stock Ledger` wsl ON wsl.item = wi.name
            WHERE wi.customer = %s
            AND wi.expiry_date IS NOT NULL
            AND wsl.quantity > 0
        """, (customer,), as_dict=True)
        
        total_count = total_items[0].count if total_items else 0
        expiring_30_count = expiring_30_days[0].count if expiring_30_days else 0
        expiring_90_count = expiring_90_days[0].count if expiring_90_days else 0
        
        # Calculate risk percentage (0-100%)
        if total_count > 0:
            risk_percentage = min(100, (expiring_30_count / total_count) * 100)
        else:
            risk_percentage = 0
        
        # Calculate needle position (0-180 degrees, where 0 is left, 90 is top, 180 is right)
        needle_angle = (risk_percentage / 100) * 180
        needle_radians = math.radians(needle_angle)
        
        # Calculate needle end position (center at 100,100, radius 80)
        needle_x = 100 + 80 * math.cos(needle_radians)
        needle_y = 100 - 80 * math.sin(needle_radians)
        
        return {
            "expiring_30_days": expiring_30_count,
            "expiring_90_days": expiring_90_count,
            "expiring_items": expiring_items,
            "risk_percentage": round(risk_percentage, 1),
            "needle_x": round(needle_x, 1),
            "needle_y": round(needle_y, 1)
        }
    except Exception as e:
        frappe.log_error(f"Error getting expiry risk data: {str(e)}", "Warehousing Portal")
        return {
            "expiring_30_days": 0, 
            "expiring_90_days": 0, 
            "expiring_items": [],
            "risk_percentage": 0,
            "needle_x": 100,
            "needle_y": 20
        }


def get_pending_orders(customer):
    """Get pending orders for customer"""
    try:
        # Get pending warehouse jobs
        pending_jobs = frappe.db.sql("""
            SELECT 
                wj.name,
                wj.job_type,
                wj.status,
                wj.creation,
                wj.scheduled_date
            FROM `tabWarehouse Job` wj
            WHERE wj.customer = %s
            AND wj.status IN ('Draft', 'Pending', 'In Progress')
            ORDER BY wj.creation DESC
            LIMIT 10
        """, (customer,), as_dict=True)
        
        # Get pending stock entries
        pending_stock_entries = frappe.db.sql("""
            SELECT 
                se.name,
                se.purpose,
                se.posting_date,
                se.status
            FROM `tabStock Entry` se
            WHERE se.customer = %s
            AND se.status IN ('Draft', 'Pending')
            ORDER BY se.creation DESC
            LIMIT 5
        """, (customer,), as_dict=True)
        
        # Count by job type
        inbound_count = len([j for j in pending_jobs if j.job_type == 'Inbound'])
        release_count = len([j for j in pending_jobs if j.job_type == 'Release'])
        vas_count = len([j for j in pending_jobs if j.job_type == 'VAS'])
        transfer_count = len([j for j in pending_jobs if j.job_type == 'Transfer'])
        stocktake_count = len([j for j in pending_jobs if j.job_type == 'Stocktake'])
        
        return {
            "pending_jobs": pending_jobs,
            "pending_stock_entries": pending_stock_entries,
            "total_pending": len(pending_jobs) + len(pending_stock_entries),
            "inbound_count": inbound_count,
            "release_count": release_count,
            "vas_count": vas_count,
            "transfer_count": transfer_count,
            "stocktake_count": stocktake_count
        }
    except Exception as e:
        frappe.log_error(f"Error getting pending orders: {str(e)}", "Warehousing Portal")
        return {
            "pending_jobs": [], 
            "pending_stock_entries": [], 
            "total_pending": 0,
            "inbound_count": 0,
            "release_count": 0,
            "vas_count": 0,
            "transfer_count": 0,
            "stocktake_count": 0
        }


def get_handling_units_trend(customer):
    """Get handling units trend data for the last 30 days"""
    try:
        current_date = datetime.now()
        start_date = (current_date - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = current_date.strftime('%Y-%m-%d')
        
        # Get daily handling units count for the last 30 days
        trend_data = frappe.db.sql("""
            SELECT 
                DATE(wsl.posting_date) as date,
                COUNT(DISTINCT wsl.handling_unit) as units_count
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = wsl.item
            WHERE wi.customer = %s
            AND wsl.posting_date BETWEEN %s AND %s
            AND wsl.handling_unit IS NOT NULL
            GROUP BY DATE(wsl.posting_date)
            ORDER BY DATE(wsl.posting_date)
        """, (customer, start_date, end_date), as_dict=True)
        
        # Create a complete date range for the last 30 days
        date_range = []
        for i in range(30):
            date = (current_date - timedelta(days=i)).strftime('%Y-%m-%d')
            date_range.append(date)
        date_range.reverse()
        
        # Fill in missing dates with 0 values
        trend_dict = {item['date'].strftime('%Y-%m-%d'): item['units_count'] for item in trend_data}
        complete_trend = []
        
        for date in date_range:
            complete_trend.append({
                'date': date,
                'units_count': trend_dict.get(date, 0)
            })
        
        # Calculate trend metrics
        if len(complete_trend) >= 2:
            first_week_avg = sum(item['units_count'] for item in complete_trend[:7]) / 7
            last_week_avg = sum(item['units_count'] for item in complete_trend[-7:]) / 7
            trend_direction = "up" if last_week_avg > first_week_avg else "down" if last_week_avg < first_week_avg else "stable"
            trend_percentage = ((last_week_avg - first_week_avg) / first_week_avg * 100) if first_week_avg > 0 else 0
        else:
            trend_direction = "stable"
            trend_percentage = 0
        
        return {
            "trend_data": complete_trend,
            "monthly_data": complete_trend,  # Add monthly_data for template compatibility
            "trend_direction": trend_direction,
            "trend_percentage": round(trend_percentage, 1),
            "current_units": complete_trend[-1]['units_count'] if complete_trend else 0,
            "peak_units": max(item['units_count'] for item in complete_trend) if complete_trend else 0
        }
    except Exception as e:
        frappe.log_error(f"Error getting handling units trend: {str(e)}", "Warehousing Portal")
        return {
            "trend_data": [],
            "monthly_data": [],  # Add monthly_data for template compatibility
            "trend_direction": "stable",
            "trend_percentage": 0,
            "current_units": 0,
            "peak_units": 0
        }

