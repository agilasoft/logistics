# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, getdate, today, get_datetime
from erpnext.accounts.utils import get_account_currency
from erpnext.setup.utils import get_exchange_rate


class SettlementEntry(Document):
	def validate(self):
		"""Validate settlement entry document."""
		self.validate_settlement_group()
		self.validate_filters()
		self.validate_references()
		self.calculate_totals()
	
	def validate_settlement_group(self):
		"""Validate that settlement group is properly configured."""
		if not self.settlement_group:
			frappe.throw(_("Settlement Group is required."))
		
		# Check if settlement group exists
		if not frappe.db.exists("Settlement Group", self.settlement_group):
			frappe.throw(_("Settlement Group {0} does not exist.").format(self.settlement_group))
		
		# Get settlement group document
		settlement_group = frappe.get_doc("Settlement Group", self.settlement_group)
		
		# Validate that settlement group is active
		if not settlement_group.is_active:
			frappe.throw(_("Settlement Group {0} is not active.").format(self.settlement_group))
		
		# Validate company match
		if settlement_group.company != self.company:
			frappe.throw(_("Settlement Group {0} belongs to company {1}, but Settlement Entry is for company {2}.").format(
				self.settlement_group, settlement_group.company, self.company
			))
		
		# Set settlement entity info
		self.settlement_customer = settlement_group.settlement_customer
		self.settlement_supplier = settlement_group.settlement_supplier
		
		# Validate that at least one settlement entity exists
		if not self.settlement_customer and not self.settlement_supplier:
			frappe.throw(_("Settlement Group {0} must have at least one Settlement Customer or Settlement Supplier configured.").format(self.settlement_group))
	
	def validate_filters(self):
		"""Validate that at least one filter is selected."""
		if not self.include_receivables and not self.include_payables:
			frappe.throw(_("At least one of Include Receivables or Include Payables must be selected."))
		
		# Validate that appropriate settlement entity exists based on filters
		if self.include_receivables and not self.settlement_customer:
			frappe.throw(_("Include Receivables is selected, but Settlement Customer is not configured in Settlement Group {0}.").format(self.settlement_group))
		
		if self.include_payables and not self.settlement_supplier:
			frappe.throw(_("Include Payables is selected, but Settlement Supplier is not configured in Settlement Group {0}.").format(self.settlement_group))
	
	def validate_references(self):
		"""Validate that all references are valid and belong to the settlement group."""
		# Skip validation if references are empty (may be auto-populated)
		# Only validate if references exist
		if not self.references:
			return
		
		settlement_group = frappe.get_doc("Settlement Group", self.settlement_group)
		member_list = settlement_group.get_member_list()
		
		# Combine all members into a single list for validation
		all_members = set()
		
		# Add settlement entities
		if settlement_group.settlement_customer:
			all_members.add(f"Customer|{settlement_group.settlement_customer}")
		if settlement_group.settlement_supplier:
			all_members.add(f"Supplier|{settlement_group.settlement_supplier}")
		
		# Add all members
		for customer in member_list["customers"]:
			all_members.add(f"Customer|{customer}")
		for supplier in member_list["suppliers"]:
			all_members.add(f"Supplier|{supplier}")
		
		for ref in self.references:
			if not ref.reference_doctype or not ref.reference_name:
				frappe.throw(_("Reference DocType and Reference Name are required for all references."))
			
			if not frappe.db.exists(ref.reference_doctype, ref.reference_name):
				frappe.throw(_("Reference {0} {1} does not exist.").format(ref.reference_doctype, ref.reference_name))
			
			ref_doc = frappe.get_doc(ref.reference_doctype, ref.reference_name)
			
			# Validate reference type matches filters
			if ref.reference_doctype == "Sales Invoice":
				if not self.include_receivables:
					frappe.throw(_("Sales Invoice {0} is a receivable transaction, but Include Receivables is not selected.").format(ref.reference_name))
				
				member_key = f"Customer|{ref_doc.customer}"
				if member_key not in all_members:
					frappe.throw(_("Sales Invoice {0} customer {1} is not a member of Settlement Group {2}.").format(
						ref.reference_name, ref_doc.customer, self.settlement_group
					))
			
			elif ref.reference_doctype == "Purchase Invoice":
				if not self.include_payables:
					frappe.throw(_("Purchase Invoice {0} is a payable transaction, but Include Payables is not selected.").format(ref.reference_name))
				
				member_key = f"Supplier|{ref_doc.supplier}"
				if member_key not in all_members:
					frappe.throw(_("Purchase Invoice {0} supplier {1} is not a member of Settlement Group {2}.").format(
						ref.reference_name, ref_doc.supplier, self.settlement_group
					))
			
			elif ref.reference_doctype == "Journal Entry":
				# Extract party from journal entry
				party_type = None
				party = None
				for acc in ref_doc.accounts:
					if acc.party_type in ["Customer", "Supplier"] and acc.party:
						party_type = acc.party_type
						party = acc.party
						break
				
				if not party_type or not party:
					frappe.throw(_("Journal Entry {0} must have at least one account with Customer or Supplier party.").format(ref.reference_name))
				
				# Validate filter matches
				if party_type == "Customer":
					if not self.include_receivables:
						frappe.throw(_("Journal Entry {0} is a receivable transaction (Customer {1}), but Include Receivables is not selected.").format(
							ref.reference_name, party
						))
				elif party_type == "Supplier":
					if not self.include_payables:
						frappe.throw(_("Journal Entry {0} is a payable transaction (Supplier {1}), but Include Payables is not selected.").format(
							ref.reference_name, party
						))
				
				member_key = f"{party_type}|{party}"
				if member_key not in all_members:
					frappe.throw(_("Journal Entry {0} party {1} {2} is not a member of Settlement Group {3}.").format(
						ref.reference_name, party_type, party, self.settlement_group
					))
			
			# Validate allocated amount
			if not ref.allocated_amount or ref.allocated_amount <= 0:
				frappe.throw(_("Allocated Amount must be greater than 0 for reference {0}.").format(ref.reference_name))
			
			# Fetch outstanding amount if not set
			if not ref.outstanding_amount:
				ref_doc = frappe.get_doc(ref.reference_doctype, ref.reference_name)
				if ref.reference_doctype == "Sales Invoice":
					ref.outstanding_amount = flt(ref_doc.outstanding_amount)
				elif ref.reference_doctype == "Purchase Invoice":
					ref.outstanding_amount = flt(ref_doc.outstanding_amount)
				elif ref.reference_doctype == "Journal Entry":
					total_debit = sum([flt(acc.debit_in_account_currency) for acc in ref_doc.accounts])
					total_credit = sum([flt(acc.credit_in_account_currency) for acc in ref_doc.accounts])
					ref.outstanding_amount = abs(total_debit - total_credit)
			
			if ref.outstanding_amount and ref.allocated_amount > ref.outstanding_amount:
				frappe.throw(_("Allocated Amount {0} cannot be greater than Outstanding Amount {1} for reference {2}.").format(
					ref.allocated_amount, ref.outstanding_amount, ref.reference_name
				))
	
	def calculate_totals(self):
		"""Calculate total receivable, payable, and net amount."""
		total_receivable = 0
		total_payable = 0
		
		if not self.references:
			self.total_receivable = 0
			self.total_payable = 0
			self.net_amount = 0
			return
		
		for ref in self.references:
			if not ref.allocated_amount:
				continue
			
			if ref.party_type == "Customer":
				# Receivable
				total_receivable += flt(ref.allocated_amount)
			elif ref.party_type == "Supplier":
				# Payable
				total_payable += flt(ref.allocated_amount)
		
		self.total_receivable = total_receivable
		self.total_payable = total_payable
		self.net_amount = total_receivable - total_payable
	
	def on_submit(self):
		"""Create journal entry for settlement on submit."""
		# Validate references before submitting
		if not self.references:
			frappe.throw(_("At least one reference is required before submitting."))
		
		self.create_journal_entry()
		# Outstanding amounts will be updated automatically when the Journal Entry is submitted
	
	def on_cancel(self):
		"""Cancel journal entry if it was submitted."""
		if self.journal_entry:
			je = frappe.get_doc("Journal Entry", self.journal_entry)
			if je.docstatus == 1:
				je.cancel()
			# Outstanding amounts will be automatically reversed when the Journal Entry is cancelled
	
	def _get_outstanding_transactions(self, clear_existing=0):
		"""Internal method to get all outstanding transactions for settlement group members filtered by checkboxes."""
		if not self.settlement_group or not self.company:
			frappe.throw(_("Settlement Group and Company are required."))
		
		if not self.include_receivables and not self.include_payables:
			frappe.throw(_("At least one of Include Receivables or Include Payables must be selected."))
		
		settlement_group = frappe.get_doc("Settlement Group", self.settlement_group)
		all_transactions = settlement_group.get_all_outstanding_transactions(company=self.company)
		
		# Filter transactions based on checkboxes
		filtered_transactions = []
		for trans in all_transactions:
			if trans["reference_doctype"] == "Sales Invoice" or (trans["reference_doctype"] == "Journal Entry" and trans["party_type"] == "Customer"):
				# Receivable transaction
				if self.include_receivables:
					filtered_transactions.append(trans)
			elif trans["reference_doctype"] == "Purchase Invoice" or (trans["reference_doctype"] == "Journal Entry" and trans["party_type"] == "Supplier"):
				# Payable transaction
				if self.include_payables:
					filtered_transactions.append(trans)
		
		# Clear existing references if requested
		if int(clear_existing or 0):
			self.set("references", [])
		
		# Add filtered transactions
		for trans in filtered_transactions:
			self.append("references", {
				"reference_doctype": trans["reference_doctype"],
				"reference_name": trans["reference_name"],
				"party_type": trans["party_type"],
				"party": trans["party"],
				"outstanding_amount": trans["outstanding_amount"],
				"allocated_amount": trans["outstanding_amount"],
				"total_amount": trans["total_amount"],
				"reference_date": trans["reference_date"],
				"due_date": trans.get("due_date")
			})
		
		self.calculate_totals()
		self.save()
		return len(filtered_transactions)
	
	@frappe.whitelist()
	def create_journal_entry(self):
		"""Create journal entry for settlement transactions with multi-currency support."""
		if not self.company:
			frappe.throw(_("Company is required to create journal entry."))
		
		if not self.posting_date:
			self.posting_date = today()
		
		# Get company currency
		company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		if not company_currency:
			frappe.throw(_("Default Currency is not set for Company {0}.").format(self.company))
		
		# Get default accounts (use local variables to avoid modifying self after submit)
		receivable_account = self.receivable_account
		if not receivable_account:
			receivable_account = frappe.db.get_value("Company", self.company, "default_receivable_account")
			if not receivable_account:
				frappe.throw(_("Default Receivable Account is not set for Company {0}.").format(self.company))
		
		payable_account = self.payable_account
		if not payable_account:
			payable_account = frappe.db.get_value("Company", self.company, "default_payable_account")
			if not payable_account:
				frappe.throw(_("Default Payable Account is not set for Company {0}.").format(self.company))
		
		je_entries = []
		exchange_gain_loss_entries = []
		
		# Get settlement entity accounts
		settlement_customer_account = None
		settlement_supplier_account = None
		
		if self.settlement_customer:
			customer_account = frappe.get_all("Party Account",
				filters={"parenttype": "Customer", "parent": self.settlement_customer, "company": self.company},
				fields=["account"],
				limit=1
			)
			if customer_account:
				settlement_customer_account = customer_account[0].account
			else:
				settlement_customer_account = receivable_account
		
		if self.settlement_supplier:
			supplier_account = frappe.get_all("Party Account",
				filters={"parenttype": "Supplier", "parent": self.settlement_supplier, "company": self.company},
				fields=["account"],
				limit=1
			)
			if supplier_account:
				settlement_supplier_account = supplier_account[0].account
			else:
				settlement_supplier_account = payable_account
		
		# Entries for each reference transaction - one line per transaction to clear individual parties
		for ref in self.references:
			if not ref.allocated_amount:
				continue
			
			# Get reference document to fetch currency
			ref_doc = frappe.get_doc(ref.reference_doctype, ref.reference_name)
			ref_currency = ref_doc.currency if hasattr(ref_doc, 'currency') else company_currency
			
			# Get account for party
			if ref.party_type == "Customer":
				# Get from Party Account table (company-wise accounts)
				customer_account = frappe.get_all("Party Account",
					filters={"parenttype": "Customer", "parent": ref.party, "company": self.company},
					fields=["account"],
					limit=1
				)
				if customer_account:
					party_account = customer_account[0].account
				else:
					party_account = receivable_account
				
				# Get account currency
				account_currency = get_account_currency(party_account)
				
				# Get exchange rate if currencies differ
				if ref_currency != account_currency:
					exchange_rate = get_exchange_rate(ref_currency, account_currency, self.posting_date, "for_selling")
					amount_in_account_currency = flt(ref.allocated_amount) * exchange_rate
				else:
					exchange_rate = 1.0
					amount_in_account_currency = flt(ref.allocated_amount)
				
				# Calculate exchange gain/loss if needed
				if ref_currency != company_currency:
					# Get original invoice amount in company currency
					original_rate = ref_doc.conversion_rate if hasattr(ref_doc, 'conversion_rate') else 1.0
					current_rate = get_exchange_rate(ref_currency, company_currency, self.posting_date, "for_selling")
					
					original_amount_in_company_currency = flt(ref.allocated_amount) * original_rate
					current_amount_in_company_currency = flt(ref.allocated_amount) * current_rate
					exchange_diff = current_amount_in_company_currency - original_amount_in_company_currency
					
					if abs(exchange_diff) >= 0.01:
						# Add exchange gain/loss entry
						exchange_gain_loss_account = frappe.db.get_value("Company", self.company, "exchange_gain_loss_account")
						if not exchange_gain_loss_account:
							# Try to get from Account Settings
							exchange_gain_loss_account = frappe.db.get_single_value("Accounts Settings", "exchange_gain_loss_account")
						
						if exchange_gain_loss_account:
							exchange_gain_loss_entries.append({
								"account": exchange_gain_loss_account,
								"debit_in_account_currency": abs(exchange_diff) if exchange_diff < 0 else 0,
								"credit_in_account_currency": exchange_diff if exchange_diff > 0 else 0,
								"cost_center": self.cost_center,
								"user_remark": f"Exchange gain/loss for {ref.reference_doctype} {ref.reference_name} - {ref.party}"
							})
				
				# Clear customer receivable: Credit customer AR account (one line per transaction)
				je_entries.append({
					"account": party_account,
					"party_type": "Customer",
					"party": ref.party,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": amount_in_account_currency,
					"cost_center": self.cost_center,
					"reference_type": ref.reference_doctype,
					"reference_name": ref.reference_name,
					"user_remark": f"Clear receivable from {ref.party} - {ref.reference_doctype} {ref.reference_name}"
				})
			
			elif ref.party_type == "Supplier":
				# Get from Party Account table (company-wise accounts)
				supplier_account = frappe.get_all("Party Account",
					filters={"parenttype": "Supplier", "parent": ref.party, "company": self.company},
					fields=["account"],
					limit=1
				)
				if supplier_account:
					party_account = supplier_account[0].account
				else:
					party_account = payable_account
				
				# Get account currency
				account_currency = get_account_currency(party_account)
				
				# Get exchange rate if currencies differ
				if ref_currency != account_currency:
					exchange_rate = get_exchange_rate(ref_currency, account_currency, self.posting_date, "for_buying")
					amount_in_account_currency = flt(ref.allocated_amount) * exchange_rate
				else:
					exchange_rate = 1.0
					amount_in_account_currency = flt(ref.allocated_amount)
				
				# Calculate exchange gain/loss if needed
				if ref_currency != company_currency:
					# Get original invoice amount in company currency
					original_rate = ref_doc.conversion_rate if hasattr(ref_doc, 'conversion_rate') else 1.0
					current_rate = get_exchange_rate(ref_currency, company_currency, self.posting_date, "for_buying")
					
					original_amount_in_company_currency = flt(ref.allocated_amount) * original_rate
					current_amount_in_company_currency = flt(ref.allocated_amount) * current_rate
					exchange_diff = current_amount_in_company_currency - original_amount_in_company_currency
					
					if abs(exchange_diff) >= 0.01:
						# Add exchange gain/loss entry
						exchange_gain_loss_account = frappe.db.get_value("Company", self.company, "exchange_gain_loss_account")
						if not exchange_gain_loss_account:
							# Try to get from Account Settings
							exchange_gain_loss_account = frappe.db.get_single_value("Accounts Settings", "exchange_gain_loss_account")
						
						if exchange_gain_loss_account:
							exchange_gain_loss_entries.append({
								"account": exchange_gain_loss_account,
								"debit_in_account_currency": abs(exchange_diff) if exchange_diff < 0 else 0,
								"credit_in_account_currency": exchange_diff if exchange_diff > 0 else 0,
								"cost_center": self.cost_center,
								"user_remark": f"Exchange gain/loss for {ref.reference_doctype} {ref.reference_name} - {ref.party}"
							})
				
				# Clear supplier payable: Debit supplier AP account (one line per transaction)
				je_entries.append({
					"account": party_account,
					"party_type": "Supplier",
					"party": ref.party,
					"debit_in_account_currency": amount_in_account_currency,
					"credit_in_account_currency": 0,
					"cost_center": self.cost_center,
					"reference_type": ref.reference_doctype,
					"reference_name": ref.reference_name,
					"user_remark": f"Clear payable to {ref.party} - {ref.reference_doctype} {ref.reference_name}"
				})
		
		# Calculate net amount in company currency
		net_amount_company_currency = flt(self.net_amount)
		
		# Post net difference to settlement entity (one line for the net amount)
		if abs(net_amount_company_currency) >= 0.01:
			if net_amount_company_currency > 0:
				# Positive net amount = Receivable, use Settlement Customer
				if not self.settlement_customer:
					frappe.throw(_("Net amount is positive (receivable), but Settlement Customer is not configured in Settlement Group {0}.").format(self.settlement_group))
				
				if not settlement_customer_account:
					frappe.throw(_("Settlement Customer account is required but not found."))
				
				# Debit settlement customer AR account for net receivable
				je_entries.append({
					"account": settlement_customer_account,
					"party_type": "Customer",
					"party": self.settlement_customer,
					"debit_in_account_currency": abs(net_amount_company_currency),
					"credit_in_account_currency": 0,
					"cost_center": self.cost_center,
					"user_remark": f"Net receivable from {self.settlement_customer} (Settlement Group: {self.settlement_group}) - Settlement Entry {self.name}"
				})
			else:
				# Negative net amount = Payable, use Settlement Supplier
				if not self.settlement_supplier:
					frappe.throw(_("Net amount is negative (payable), but Settlement Supplier is not configured in Settlement Group {0}.").format(self.settlement_group))
				
				if not settlement_supplier_account:
					frappe.throw(_("Settlement Supplier account is required but not found."))
				
				# Credit settlement supplier AP account for net payable
				je_entries.append({
					"account": settlement_supplier_account,
					"party_type": "Supplier",
					"party": self.settlement_supplier,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": abs(net_amount_company_currency),
					"cost_center": self.cost_center,
					"user_remark": f"Net payable to {self.settlement_supplier} (Settlement Group: {self.settlement_group}) - Settlement Entry {self.name}"
				})
		
		# Add exchange gain/loss entries
		je_entries.extend(exchange_gain_loss_entries)
		
		# Create journal entry
		je = frappe.get_doc({
			"doctype": "Journal Entry",
			"posting_date": self.posting_date,
			"company": self.company,
			"accounts": je_entries,
			"user_remark": f"Settlement Entry {self.name} - Settlement Group: {self.settlement_group}",
			"voucher_type": "Journal Entry",
			"reference_no": self.name,
			"reference_date": self.posting_date
		})
		
		je.insert()
		
		# Update journal_entry field directly using db.set_value to avoid update validation
		frappe.db.set_value("Settlement Entry", self.name, "journal_entry", je.name)
		frappe.db.commit()
		
		frappe.msgprint(_("Journal Entry {0} created. Please review and submit it manually.").format(je.name))
	
	def update_outstanding_amounts(self, reverse=False):
		"""Update outstanding amounts on referenced documents."""
		for ref in self.references:
			if not ref.reference_doctype or not ref.reference_name:
				continue
			
			if ref.reference_doctype in ["Sales Invoice", "Purchase Invoice"]:
				# Get current outstanding amount
				current_outstanding = frappe.db.get_value(
					ref.reference_doctype,
					ref.reference_name,
					"outstanding_amount"
				)
				
				if current_outstanding is None:
					continue
				
				# Calculate new outstanding amount
				if reverse:
					# Reverse the allocation
					new_outstanding = flt(current_outstanding) + flt(ref.allocated_amount)
				else:
					# Update outstanding amount
					new_outstanding = flt(current_outstanding) - flt(ref.allocated_amount)
				
				# Update directly in database to avoid "update after submit" validation
				frappe.db.set_value(
					ref.reference_doctype,
					ref.reference_name,
					"outstanding_amount",
					new_outstanding
				)
		
		frappe.db.commit()


@frappe.whitelist()
def get_outstanding_transactions(docname, clear_existing=0):
	"""Standalone function to get outstanding transactions (for static calls)."""
	doc = frappe.get_doc("Settlement Entry", docname)
	return doc._get_outstanding_transactions(clear_existing=clear_existing)

