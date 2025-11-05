# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class SettlementGroup(Document):
	def validate(self):
		"""Validate settlement group document."""
		self.validate_settlement_entity()
		self.validate_members()
		self.validate_duplicate_members()
	
	def validate_settlement_entity(self):
		"""Validate that at least one settlement entity exists."""
		if not self.settlement_customer and not self.settlement_supplier:
			frappe.throw(_("At least one Settlement Customer or Settlement Supplier is required."))
		
		if self.settlement_customer:
			if not frappe.db.exists("Customer", self.settlement_customer):
				frappe.throw(_("Settlement Customer {0} does not exist.").format(self.settlement_customer))
		
		if self.settlement_supplier:
			if not frappe.db.exists("Supplier", self.settlement_supplier):
				frappe.throw(_("Settlement Supplier {0} does not exist.").format(self.settlement_supplier))
	
	def validate_members(self):
		"""Validate that at least one member is added."""
		if not self.members:
			frappe.throw(_("At least one member is required in the settlement group."))
		
		# Validate that members exist
		for member in self.members:
			if not member.party:
				frappe.throw(_("Party is required for all members."))
			
			if member.party_type == "Customer":
				if not frappe.db.exists("Customer", member.party):
					frappe.throw(_("Customer {0} does not exist.").format(member.party))
			elif member.party_type == "Supplier":
				if not frappe.db.exists("Supplier", member.party):
					frappe.throw(_("Supplier {0} does not exist.").format(member.party))
			
			# Validate that member is not the same as settlement entity
			if member.party_type == "Customer" and member.party == self.settlement_customer:
				frappe.throw(_("Settlement Customer {0} cannot be a member of its own settlement group.").format(self.settlement_customer))
			elif member.party_type == "Supplier" and member.party == self.settlement_supplier:
				frappe.throw(_("Settlement Supplier {0} cannot be a member of its own settlement group.").format(self.settlement_supplier))
	
	def validate_duplicate_members(self):
		"""Validate that there are no duplicate members."""
		seen = set()
		for member in self.members:
			key = f"{member.party_type}|{member.party}"
			if key in seen:
				frappe.throw(_("Duplicate member found: {0} {1}").format(member.party_type, member.party))
			seen.add(key)
	
	def get_member_list(self):
		"""Get list of all members in this settlement group."""
		members = {
			"customers": [],
			"suppliers": []
		}
		
		for member in self.members:
			if member.party_type == "Customer":
				members["customers"].append(member.party)
			elif member.party_type == "Supplier":
				members["suppliers"].append(member.party)
		
		return members
	
	@frappe.whitelist()
	def get_member_list_api(self):
		"""Get member list for frontend."""
		return self.get_member_list()
	
	@frappe.whitelist()
	def get_all_outstanding_transactions(self, company=None, as_on_date=None):
		"""Get all outstanding transactions for all members in the settlement group."""
		if not company:
			company = self.company
		
		all_transactions = []
		member_list = self.get_member_list()
		
		# Get all customers (members + settlement customer)
		customers = member_list["customers"].copy()
		if self.settlement_customer:
			customers.append(self.settlement_customer)
		
		# Get all suppliers (members + settlement supplier)
		suppliers = member_list["suppliers"].copy()
		if self.settlement_supplier:
			suppliers.append(self.settlement_supplier)
		
		# Get outstanding Sales Invoices
		if customers:
			sales_invoices = frappe.get_all("Sales Invoice",
				filters={
					"customer": ["in", customers],
					"company": company,
					"docstatus": 1,
					"outstanding_amount": [">", 0]
				},
				fields=["name", "customer", "posting_date", "due_date", "outstanding_amount", "grand_total"]
			)
			for si in sales_invoices:
				all_transactions.append({
					"reference_doctype": "Sales Invoice",
					"reference_name": si.name,
					"party_type": "Customer",
					"party": si.customer,
					"outstanding_amount": si.outstanding_amount,
					"total_amount": si.grand_total,
					"reference_date": si.posting_date,
					"due_date": si.due_date
				})
		
		# Get outstanding Purchase Invoices
		if suppliers:
			purchase_invoices = frappe.get_all("Purchase Invoice",
				filters={
					"supplier": ["in", suppliers],
					"company": company,
					"docstatus": 1,
					"outstanding_amount": [">", 0]
				},
				fields=["name", "supplier", "posting_date", "due_date", "outstanding_amount", "grand_total"]
			)
			for pi in purchase_invoices:
				all_transactions.append({
					"reference_doctype": "Purchase Invoice",
					"reference_name": pi.name,
					"party_type": "Supplier",
					"party": pi.supplier,
					"outstanding_amount": pi.outstanding_amount,
					"total_amount": pi.grand_total,
					"reference_date": pi.posting_date,
					"due_date": pi.due_date
				})
		
		# Get Journal Entries with party (Customer or Supplier)
		if customers:
			je_customers = frappe.db.sql("""
				SELECT DISTINCT je.name, je.posting_date, jea.party, jea.party_type
				FROM `tabJournal Entry` je
				INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
				WHERE je.company = %(company)s
					AND je.docstatus = 1
					AND jea.party_type = 'Customer'
					AND jea.party IN %(customers)s
					AND jea.party IS NOT NULL
			""", {
				"company": company,
				"customers": customers
			}, as_dict=True)
			
			for je in je_customers:
				# Get debit and credit amounts
				je_accounts = frappe.get_all("Journal Entry Account",
					filters={"parent": je.name},
					fields=["debit_in_account_currency", "credit_in_account_currency"]
				)
				total_debit = sum([flt(acc.debit_in_account_currency) for acc in je_accounts])
				total_credit = sum([flt(acc.credit_in_account_currency) for acc in je_accounts])
				je_amount = abs(total_debit - total_credit)
				
				if je_amount > 0:
					all_transactions.append({
						"reference_doctype": "Journal Entry",
						"reference_name": je.name,
						"party_type": "Customer",
						"party": je.party,
						"outstanding_amount": je_amount,
						"total_amount": je_amount,
						"reference_date": je.posting_date,
						"due_date": je.posting_date
					})
		
		if suppliers:
			je_suppliers = frappe.db.sql("""
				SELECT DISTINCT je.name, je.posting_date, jea.party, jea.party_type
				FROM `tabJournal Entry` je
				INNER JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
				WHERE je.company = %(company)s
					AND je.docstatus = 1
					AND jea.party_type = 'Supplier'
					AND jea.party IN %(suppliers)s
					AND jea.party IS NOT NULL
			""", {
				"company": company,
				"suppliers": suppliers
			}, as_dict=True)
			
			for je in je_suppliers:
				# Get debit and credit amounts
				je_accounts = frappe.get_all("Journal Entry Account",
					filters={"parent": je.name},
					fields=["debit_in_account_currency", "credit_in_account_currency"]
				)
				total_debit = sum([flt(acc.debit_in_account_currency) for acc in je_accounts])
				total_credit = sum([flt(acc.credit_in_account_currency) for acc in je_accounts])
				je_amount = abs(total_debit - total_credit)
				
				if je_amount > 0:
					all_transactions.append({
						"reference_doctype": "Journal Entry",
						"reference_name": je.name,
						"party_type": "Supplier",
						"party": je.party,
						"outstanding_amount": je_amount,
						"total_amount": je_amount,
						"reference_date": je.posting_date,
						"due_date": je.posting_date
					})
		
		return all_transactions

