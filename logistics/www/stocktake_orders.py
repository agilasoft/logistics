import frappe
from frappe.website.utils import get_home_page

def get_context(context):
	# Get customer associated with current user
	customer = get_customer_from_user()
	
	if not customer:
		frappe.throw("You are not associated with any customer. Please contact support.", frappe.PermissionError)
	
	# Add customer info to context
	context.customer = customer
	context.customer_name = frappe.get_value("Customer", customer, "customer_name")
	
	# Get stocktake orders for this customer
	orders = frappe.get_all(
		"Stocktake Order",
		filters={"customer": customer},
		fields=[
			"name", "order_date", "customer", "contract", "priority", 
			"planned_date", "due_date", "docstatus"
		],
		order_by="order_date desc"
	)
	
	# Add status information
	for order in orders:
		if order.docstatus == 0:
			order.status_text = "Draft"
			order.status_color = "secondary"
		elif order.docstatus == 1:
			order.status_text = "Submitted"
			order.status_color = "success"
		elif order.docstatus == 2:
			order.status_text = "Cancelled"
			order.status_color = "danger"
		else:
			order.status_text = "Unknown"
			order.status_color = "warning"
	
	context.orders = orders
	context.title = "Stocktake Orders"

def get_customer_from_user():
	"""Get customer associated with current user"""
	user = frappe.session.user
	
	if not user or user == "Guest":
		return None
	
	# Skip for system users (Administrator, etc.)
	if user in ["Administrator", "Guest"]:
		return None
	
	try:
		# Check if user is a Portal User
		portal_user = frappe.get_value("Portal User", {"user": user}, "name")
		if portal_user:
			# Get customer from Portal User (parent field contains customer name)
			customer = frappe.get_value("Portal User", {"user": user}, "parent")
			if customer:
				return customer
		
		# Check if user email matches customer email
		user_doc = frappe.get_doc("User", user)
		if user_doc.email:
			customer = frappe.get_value("Customer", {"email_id": user_doc.email}, "name")
			if customer:
				return customer
		
		# Check if user is linked to a contact
		contact = frappe.get_value("Contact", {"user": user}, "name")
		if contact:
			contact_doc = frappe.get_doc("Contact", contact)
			for link in contact_doc.links:
				if link.link_doctype == "Customer":
					return link.link_name
		
		# Check User doctype for customer field
		user_doc = frappe.get_doc("User", user)
		if hasattr(user_doc, 'customer') and user_doc.customer:
			return user_doc.customer
		
		return None
		
	except Exception as e:
		frappe.log_error(f"Error getting customer for user {user}: {str(e)}", "Customer Resolution Error")
		return None
