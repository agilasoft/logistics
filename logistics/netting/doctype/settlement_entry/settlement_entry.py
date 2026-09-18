# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, today
from erpnext.accounts.utils import get_account_currency
from erpnext.setup.utils import get_exchange_rate


AMOUNT_PRECISION = 2
FX_THRESHOLD = 0.01


def fetch_exchange_rate(from_currency, to_currency, transaction_date=None, args=None, throw=True):
	"""Return exchange rate from_currency → to_currency. Same currency is 1."""
	if not from_currency or not to_currency or from_currency == to_currency:
		return 1.0

	rate = get_exchange_rate(from_currency, to_currency, transaction_date, args)
	rate = flt(rate)
	if rate:
		return rate

	if throw:
		frappe.throw(
			_("Unable to find exchange rate for {0} to {1} on {2}. Please create a Currency Exchange record.").format(
				from_currency, to_currency, transaction_date or today()
			)
		)
	return 0.0


def settlement_amount(allocated_amount, exchange_rate):
	"""Allocated invoice amount converted to settlement currency."""
	return flt(flt(allocated_amount) * flt(exchange_rate), AMOUNT_PRECISION)


def original_book_amount(allocated_amount, invoice_conversion_rate):
	"""Allocated amount in company currency at the invoice's original rate."""
	return flt(flt(allocated_amount) * flt(invoice_conversion_rate or 1), AMOUNT_PRECISION)


def settlement_in_base(allocated_in_settlement, conversion_rate):
	"""Settlement-currency amount converted to company currency."""
	return flt(flt(allocated_in_settlement) * flt(conversion_rate or 1), AMOUNT_PRECISION)


def row_exchange_gain_loss(allocated_amount, invoice_conversion_rate, allocated_in_settlement, conversion_rate, party_type):
	"""FX in company currency. Positive = gain. Payable sign is flipped so a cheaper payable is a gain."""
	book = original_book_amount(allocated_amount, invoice_conversion_rate)
	settled_base = settlement_in_base(allocated_in_settlement, conversion_rate)
	diff = flt(settled_base - book, AMOUNT_PRECISION)
	if party_type == "Supplier":
		diff = flt(book - settled_base, AMOUNT_PRECISION)
	return diff


def party_clearing_amounts(allocated_amount, invoice_currency, invoice_conversion_rate, account_currency, company_currency):
	"""Account-currency amount, account→company rate, and company amount for clearing AR/AP at original book."""
	book = original_book_amount(allocated_amount, invoice_conversion_rate)
	if account_currency == invoice_currency:
		rate = flt(invoice_conversion_rate) or 1.0
		acc_amount = flt(allocated_amount)
		return acc_amount, rate, flt(acc_amount * rate, AMOUNT_PRECISION)
	if account_currency == company_currency:
		return book, 1.0, book
	return None


def net_settlement_amounts(net_amount, settlement_currency, conversion_rate, account_currency, company_currency):
	"""Account-currency amount, account→company rate, and company amount for the net settlement line."""
	abs_net = abs(flt(net_amount))
	company_amount = settlement_in_base(abs_net, conversion_rate)
	if account_currency == settlement_currency:
		rate = flt(conversion_rate) or 1.0
		return abs_net, rate, flt(abs_net * rate, AMOUNT_PRECISION)
	if account_currency == company_currency:
		return company_amount, 1.0, company_amount
	return None


def fx_plug(total_debit, total_credit):
	"""Company-currency debit/credit to balance the JE. Credit = gain, debit = loss."""
	diff = flt(flt(total_debit) - flt(total_credit), AMOUNT_PRECISION)
	if abs(diff) < FX_THRESHOLD:
		return 0.0, 0.0
	if diff > 0:
		return 0.0, diff
	return abs(diff), 0.0


def apply_row_conversion(row, conversion_rate):
	"""Set settlement amount and row FX from allocated amount and rates."""
	row.allocated_amount_in_settlement_currency = settlement_amount(
		row.allocated_amount, row.exchange_rate
	)
	row.exchange_gain_loss = row_exchange_gain_loss(
		row.allocated_amount,
		row.invoice_conversion_rate,
		row.allocated_amount_in_settlement_currency,
		conversion_rate,
		row.party_type,
	)
	return row


def get_reference_currency_fields(reference_doctype, reference_name, company_currency=None):
	"""Invoice (or JE party-line) currency and original conversion rate to company currency."""
	if not reference_doctype or not reference_name:
		return company_currency, 1.0

	if reference_doctype in ("Sales Invoice", "Purchase Invoice"):
		values = frappe.db.get_value(
			reference_doctype, reference_name, ["currency", "conversion_rate"], as_dict=True
		)
		if not values:
			return company_currency, 1.0
		return values.currency or company_currency, flt(values.conversion_rate) or 1.0

	if reference_doctype == "Journal Entry":
		accounts = frappe.get_all(
			"Journal Entry Account",
			filters={"parent": reference_name},
			fields=["party_type", "party", "account", "account_currency", "exchange_rate"],
		)
		for acc in accounts:
			if acc.party_type in ("Customer", "Supplier") and acc.party:
				account_currency = acc.account_currency or (
					get_account_currency(acc.account) if acc.account else company_currency
				)
				return account_currency or company_currency, flt(acc.exchange_rate) or 1.0
		return company_currency, 1.0

	return company_currency, 1.0


class SettlementEntry(Document):
	def validate(self):
		"""Validate settlement entry document."""
		self.set_currency_defaults()
		self.validate_settlement_group()
		self.validate_filters()
		self.validate_references()
		self.set_reference_currency_fields()
		self.set_missing_exchange_rates()
		self.validate_exchange_rates()
		self.calculate_totals()

	def set_currency_defaults(self):
		"""Fill company/settlement currency and settlement→company rate when blank."""
		if self.company and not self.company_currency:
			self.company_currency = frappe.db.get_value("Company", self.company, "default_currency")

		if not self.settlement_currency and self.company_currency:
			self.settlement_currency = self.company_currency

		if self.settlement_currency and self.company_currency:
			if self.settlement_currency == self.company_currency:
				self.conversion_rate = 1.0
			elif not flt(self.conversion_rate) or flt(self.conversion_rate) == 1:
				self.conversion_rate = fetch_exchange_rate(
					self.settlement_currency, self.company_currency, self.posting_date
				)

	def set_reference_currency_fields(self):
		"""Copy invoice currency and original conversion rate onto each row."""
		for ref in self.references or []:
			currency, invoice_rate = get_reference_currency_fields(
				ref.reference_doctype, ref.reference_name, self.company_currency
			)
			if not ref.currency:
				ref.currency = currency
			if not flt(ref.invoice_conversion_rate):
				ref.invoice_conversion_rate = invoice_rate or 1.0

	def set_missing_exchange_rates(self, overwrite=False):
		"""Fill invoice→settlement rates when missing (or when overwrite is set)."""
		for ref in self.references or []:
			from_currency = ref.currency or self.settlement_currency
			if not overwrite:
				if from_currency == self.settlement_currency and flt(ref.exchange_rate):
					continue
				if flt(ref.exchange_rate) and flt(ref.exchange_rate) != 1:
					continue
			args = "for_selling" if ref.party_type == "Customer" else "for_buying"
			ref.exchange_rate = fetch_exchange_rate(
				from_currency, self.settlement_currency, self.posting_date, args
			)

	def validate_exchange_rates(self):
		if not self.settlement_currency:
			frappe.throw(_("Settlement Currency is required."))
		if not flt(self.conversion_rate) or flt(self.conversion_rate) <= 0:
			frappe.throw(_("Exchange Rate (Settlement to Company) must be greater than 0."))
		for ref in self.references or []:
			if not flt(ref.exchange_rate) or flt(ref.exchange_rate) <= 0:
				frappe.throw(
					_("Exchange Rate must be greater than 0 for reference {0}.").format(ref.reference_name)
				)

	def validate_settlement_group(self):
		"""Validate that settlement group is properly configured."""
		if not self.settlement_group:
			frappe.throw(_("Settlement Group is required."))

		if not frappe.db.exists("Settlement Group", self.settlement_group):
			frappe.throw(_("Settlement Group {0} does not exist.").format(self.settlement_group))

		settlement_group = frappe.get_doc("Settlement Group", self.settlement_group)

		if not settlement_group.is_active:
			frappe.throw(_("Settlement Group {0} is not active.").format(self.settlement_group))

		if settlement_group.company != self.company:
			frappe.throw(
				_("Settlement Group {0} belongs to company {1}, but Settlement Entry is for company {2}.").format(
					self.settlement_group, settlement_group.company, self.company
				)
			)

		self.settlement_customer = settlement_group.settlement_customer
		self.settlement_supplier = settlement_group.settlement_supplier

		if not self.settlement_customer and not self.settlement_supplier:
			frappe.throw(
				_("Settlement Group {0} must have at least one Settlement Customer or Settlement Supplier configured.").format(
					self.settlement_group
				)
			)

	def validate_filters(self):
		"""Validate that at least one filter is selected."""
		if not self.include_receivables and not self.include_payables:
			frappe.throw(_("At least one of Include Receivables or Include Payables must be selected."))

		if self.include_receivables and not self.settlement_customer:
			frappe.throw(
				_("Include Receivables is selected, but Settlement Customer is not configured in Settlement Group {0}.").format(
					self.settlement_group
				)
			)

		if self.include_payables and not self.settlement_supplier:
			frappe.throw(
				_("Include Payables is selected, but Settlement Supplier is not configured in Settlement Group {0}.").format(
					self.settlement_group
				)
			)

	def validate_references(self):
		"""Validate that all references are valid and belong to the settlement group."""
		if not self.references:
			return

		settlement_group = frappe.get_doc("Settlement Group", self.settlement_group)
		member_list = settlement_group.get_member_list()

		all_members = set()

		if settlement_group.settlement_customer:
			all_members.add(f"Customer|{settlement_group.settlement_customer}")
		if settlement_group.settlement_supplier:
			all_members.add(f"Supplier|{settlement_group.settlement_supplier}")

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

			if ref.reference_doctype == "Sales Invoice":
				if not self.include_receivables:
					frappe.throw(
						_("Sales Invoice {0} is a receivable transaction, but Include Receivables is not selected.").format(
							ref.reference_name
						)
					)

				member_key = f"Customer|{ref_doc.customer}"
				if member_key not in all_members:
					frappe.throw(
						_("Sales Invoice {0} customer {1} is not a member of Settlement Group {2}.").format(
							ref.reference_name, ref_doc.customer, self.settlement_group
						)
					)

			elif ref.reference_doctype == "Purchase Invoice":
				if not self.include_payables:
					frappe.throw(
						_("Purchase Invoice {0} is a payable transaction, but Include Payables is not selected.").format(
							ref.reference_name
						)
					)

				member_key = f"Supplier|{ref_doc.supplier}"
				if member_key not in all_members:
					frappe.throw(
						_("Purchase Invoice {0} supplier {1} is not a member of Settlement Group {2}.").format(
							ref.reference_name, ref_doc.supplier, self.settlement_group
						)
					)

			elif ref.reference_doctype == "Journal Entry":
				party_type = None
				party = None
				for acc in ref_doc.accounts:
					if acc.party_type in ["Customer", "Supplier"] and acc.party:
						party_type = acc.party_type
						party = acc.party
						break

				if not party_type or not party:
					frappe.throw(
						_("Journal Entry {0} must have at least one account with Customer or Supplier party.").format(
							ref.reference_name
						)
					)

				if party_type == "Customer":
					if not self.include_receivables:
						frappe.throw(
							_("Journal Entry {0} is a receivable transaction (Customer {1}), but Include Receivables is not selected.").format(
								ref.reference_name, party
							)
						)
				elif party_type == "Supplier":
					if not self.include_payables:
						frappe.throw(
							_("Journal Entry {0} is a payable transaction (Supplier {1}), but Include Payables is not selected.").format(
								ref.reference_name, party
							)
						)

				member_key = f"{party_type}|{party}"
				if member_key not in all_members:
					frappe.throw(
						_("Journal Entry {0} party {1} {2} is not a member of Settlement Group {3}.").format(
							ref.reference_name, party_type, party, self.settlement_group
						)
					)

			if not ref.allocated_amount or ref.allocated_amount <= 0:
				frappe.throw(_("Allocated Amount must be greater than 0 for reference {0}.").format(ref.reference_name))

			if not ref.outstanding_amount:
				if ref.reference_doctype == "Sales Invoice":
					ref.outstanding_amount = flt(ref_doc.outstanding_amount)
				elif ref.reference_doctype == "Purchase Invoice":
					ref.outstanding_amount = flt(ref_doc.outstanding_amount)
				elif ref.reference_doctype == "Journal Entry":
					total_debit = sum([flt(acc.debit_in_account_currency) for acc in ref_doc.accounts])
					total_credit = sum([flt(acc.credit_in_account_currency) for acc in ref_doc.accounts])
					ref.outstanding_amount = abs(total_debit - total_credit)

			if ref.outstanding_amount and ref.allocated_amount > ref.outstanding_amount:
				frappe.throw(
					_("Allocated Amount {0} cannot be greater than Outstanding Amount {1} for reference {2}.").format(
						ref.allocated_amount, ref.outstanding_amount, ref.reference_name
					)
				)

	def calculate_totals(self):
		"""Calculate receivable, payable, and net in settlement currency and company currency."""
		total_receivable = 0
		total_payable = 0
		total_fx = 0
		conversion_rate = flt(self.conversion_rate) or 1.0

		if not self.references:
			self.total_receivable = 0
			self.total_payable = 0
			self.net_amount = 0
			self.base_total_receivable = 0
			self.base_total_payable = 0
			self.base_net_amount = 0
			self.total_exchange_gain_loss = 0
			return

		for ref in self.references:
			if not ref.allocated_amount:
				continue

			apply_row_conversion(ref, conversion_rate)
			amount = flt(ref.allocated_amount_in_settlement_currency)

			if ref.party_type == "Customer":
				total_receivable += amount
			elif ref.party_type == "Supplier":
				total_payable += amount

			total_fx += flt(ref.exchange_gain_loss)

		self.total_receivable = flt(total_receivable, AMOUNT_PRECISION)
		self.total_payable = flt(total_payable, AMOUNT_PRECISION)
		self.net_amount = flt(total_receivable - total_payable, AMOUNT_PRECISION)
		self.base_total_receivable = settlement_in_base(self.total_receivable, conversion_rate)
		self.base_total_payable = settlement_in_base(self.total_payable, conversion_rate)
		self.base_net_amount = settlement_in_base(self.net_amount, conversion_rate)
		self.total_exchange_gain_loss = flt(total_fx, AMOUNT_PRECISION)

	def on_submit(self):
		"""Create journal entry for settlement on submit."""
		if not self.references:
			frappe.throw(_("At least one reference is required before submitting."))

		self.create_journal_entry()

	def on_cancel(self):
		"""Cancel journal entry if it was submitted."""
		if self.journal_entry:
			je = frappe.get_doc("Journal Entry", self.journal_entry)
			if je.docstatus == 1:
				je.cancel()

	def _get_outstanding_transactions(self, clear_existing=0):
		"""Internal method to get all outstanding transactions for settlement group members filtered by checkboxes."""
		if not self.settlement_group or not self.company:
			frappe.throw(_("Settlement Group and Company are required."))

		if not self.include_receivables and not self.include_payables:
			frappe.throw(_("At least one of Include Receivables or Include Payables must be selected."))

		self.set_currency_defaults()

		settlement_group = frappe.get_doc("Settlement Group", self.settlement_group)
		all_transactions = settlement_group.get_all_outstanding_transactions(company=self.company)

		filtered_transactions = []
		for trans in all_transactions:
			if trans["reference_doctype"] == "Sales Invoice" or (
				trans["reference_doctype"] == "Journal Entry" and trans["party_type"] == "Customer"
			):
				if self.include_receivables:
					filtered_transactions.append(trans)
			elif trans["reference_doctype"] == "Purchase Invoice" or (
				trans["reference_doctype"] == "Journal Entry" and trans["party_type"] == "Supplier"
			):
				if self.include_payables:
					filtered_transactions.append(trans)

		if int(clear_existing or 0):
			self.set("references", [])

		for trans in filtered_transactions:
			self.append(
				"references",
				{
					"reference_doctype": trans["reference_doctype"],
					"reference_name": trans["reference_name"],
					"party_type": trans["party_type"],
					"party": trans["party"],
					"outstanding_amount": trans["outstanding_amount"],
					"allocated_amount": trans["outstanding_amount"],
					"total_amount": trans["total_amount"],
					"reference_date": trans["reference_date"],
					"due_date": trans.get("due_date"),
					"currency": trans.get("currency"),
					"invoice_conversion_rate": trans.get("conversion_rate") or 1.0,
				},
			)

		self.set_reference_currency_fields()
		self.set_missing_exchange_rates(overwrite=True)
		self.calculate_totals()
		self.save()
		return len(filtered_transactions)

	def _get_party_account(self, party_type, party, fallback):
		if not party:
			return fallback
		accounts = frappe.get_all(
			"Party Account",
			filters={"parenttype": party_type, "parent": party, "company": self.company},
			fields=["account"],
			limit=1,
		)
		if accounts:
			return accounts[0].account
		return fallback

	def _account_line_amounts(self, company_amount, account_currency, invoice_currency, invoice_conversion_rate, allocated_amount, args=None):
		"""Convert a company-currency book amount into the party account currency."""
		company_currency = self.company_currency
		amounts = party_clearing_amounts(
			allocated_amount, invoice_currency, invoice_conversion_rate, account_currency, company_currency
		)
		if amounts:
			return amounts

		rate = fetch_exchange_rate(account_currency, company_currency, self.posting_date, args)
		acc_amount = flt(company_amount) / flt(rate)
		return flt(acc_amount), rate, flt(acc_amount * rate, AMOUNT_PRECISION)

	def _net_line_amounts(self, account_currency):
		amounts = net_settlement_amounts(
			self.net_amount,
			self.settlement_currency,
			self.conversion_rate,
			account_currency,
			self.company_currency,
		)
		if amounts:
			return amounts

		company_amount = abs(flt(self.base_net_amount))
		rate = fetch_exchange_rate(account_currency, self.company_currency, self.posting_date)
		acc_amount = flt(company_amount) / flt(rate)
		return flt(acc_amount), rate, flt(acc_amount * rate, AMOUNT_PRECISION)

	def _je_account_row(
		self,
		account,
		account_currency,
		exchange_rate,
		debit_acc=0,
		credit_acc=0,
		party_type=None,
		party=None,
		reference_type=None,
		reference_name=None,
		user_remark=None,
	):
		return {
			"account": account,
			"account_currency": account_currency,
			"exchange_rate": flt(exchange_rate) or 1.0,
			"party_type": party_type,
			"party": party,
			"debit_in_account_currency": flt(debit_acc),
			"credit_in_account_currency": flt(credit_acc),
			"cost_center": self.cost_center,
			"reference_type": reference_type,
			"reference_name": reference_name,
			"user_remark": user_remark,
		}

	def build_journal_entry_accounts(self):
		"""Build JE account rows that balance in company currency. Used by create_journal_entry and tests."""
		if not self.company:
			frappe.throw(_("Company is required to create journal entry."))

		if not self.posting_date:
			self.posting_date = today()

		company_currency = self.company_currency or frappe.db.get_value(
			"Company", self.company, "default_currency"
		)
		if not company_currency:
			frappe.throw(_("Default Currency is not set for Company {0}.").format(self.company))
		self.company_currency = company_currency

		receivable_account = self.receivable_account or frappe.db.get_value(
			"Company", self.company, "default_receivable_account"
		)
		if not receivable_account:
			frappe.throw(_("Default Receivable Account is not set for Company {0}.").format(self.company))

		payable_account = self.payable_account or frappe.db.get_value(
			"Company", self.company, "default_payable_account"
		)
		if not payable_account:
			frappe.throw(_("Default Payable Account is not set for Company {0}.").format(self.company))

		settlement_customer_account = self._get_party_account(
			"Customer", self.settlement_customer, receivable_account
		)
		settlement_supplier_account = self._get_party_account(
			"Supplier", self.settlement_supplier, payable_account
		)

		je_entries = []
		total_debit = 0.0
		total_credit = 0.0
		uses_foreign_account = False

		for ref in self.references:
			if not ref.allocated_amount:
				continue

			invoice_currency = ref.currency or company_currency
			invoice_rate = flt(ref.invoice_conversion_rate) or 1.0
			args = "for_selling" if ref.party_type == "Customer" else "for_buying"

			if ref.party_type == "Customer":
				party_account = self._get_party_account("Customer", ref.party, receivable_account)
				account_currency = get_account_currency(party_account)
				if account_currency != company_currency:
					uses_foreign_account = True
				acc_amount, rate, company_amount = self._account_line_amounts(
					original_book_amount(ref.allocated_amount, invoice_rate),
					account_currency,
					invoice_currency,
					invoice_rate,
					ref.allocated_amount,
					args,
				)
				je_entries.append(
					self._je_account_row(
						party_account,
						account_currency,
						rate,
						credit_acc=acc_amount,
						party_type="Customer",
						party=ref.party,
						reference_type=ref.reference_doctype,
						reference_name=ref.reference_name,
						user_remark=f"Clear receivable from {ref.party} - {ref.reference_doctype} {ref.reference_name}",
					)
				)
				total_credit += company_amount

			elif ref.party_type == "Supplier":
				party_account = self._get_party_account("Supplier", ref.party, payable_account)
				account_currency = get_account_currency(party_account)
				if account_currency != company_currency:
					uses_foreign_account = True
				acc_amount, rate, company_amount = self._account_line_amounts(
					original_book_amount(ref.allocated_amount, invoice_rate),
					account_currency,
					invoice_currency,
					invoice_rate,
					ref.allocated_amount,
					args,
				)
				je_entries.append(
					self._je_account_row(
						party_account,
						account_currency,
						rate,
						debit_acc=acc_amount,
						party_type="Supplier",
						party=ref.party,
						reference_type=ref.reference_doctype,
						reference_name=ref.reference_name,
						user_remark=f"Clear payable to {ref.party} - {ref.reference_doctype} {ref.reference_name}",
					)
				)
				total_debit += company_amount

		net_company = flt(self.base_net_amount)
		if abs(flt(self.net_amount)) >= FX_THRESHOLD or abs(net_company) >= FX_THRESHOLD:
			if flt(self.net_amount) > 0:
				if not self.settlement_customer:
					frappe.throw(
						_("Net amount is positive (receivable), but Settlement Customer is not configured in Settlement Group {0}.").format(
							self.settlement_group
						)
					)
				if not settlement_customer_account:
					frappe.throw(_("Settlement Customer account is required but not found."))

				account_currency = get_account_currency(settlement_customer_account)
				if account_currency != company_currency:
					uses_foreign_account = True
				acc_amount, rate, company_amount = self._net_line_amounts(account_currency)
				je_entries.append(
					self._je_account_row(
						settlement_customer_account,
						account_currency,
						rate,
						debit_acc=acc_amount,
						party_type="Customer",
						party=self.settlement_customer,
						user_remark=(
							f"Net receivable from {self.settlement_customer} "
							f"(Settlement Group: {self.settlement_group}) - Settlement Entry {self.name}"
						),
					)
				)
				total_debit += company_amount
			else:
				if not self.settlement_supplier:
					frappe.throw(
						_("Net amount is negative (payable), but Settlement Supplier is not configured in Settlement Group {0}.").format(
							self.settlement_group
						)
					)
				if not settlement_supplier_account:
					frappe.throw(_("Settlement Supplier account is required but not found."))

				account_currency = get_account_currency(settlement_supplier_account)
				if account_currency != company_currency:
					uses_foreign_account = True
				acc_amount, rate, company_amount = self._net_line_amounts(account_currency)
				je_entries.append(
					self._je_account_row(
						settlement_supplier_account,
						account_currency,
						rate,
						credit_acc=acc_amount,
						party_type="Supplier",
						party=self.settlement_supplier,
						user_remark=(
							f"Net payable to {self.settlement_supplier} "
							f"(Settlement Group: {self.settlement_group}) - Settlement Entry {self.name}"
						),
					)
				)
				total_credit += company_amount

		fx_debit, fx_credit = fx_plug(total_debit, total_credit)
		if fx_debit or fx_credit:
			exchange_gain_loss_account = frappe.db.get_value(
				"Company", self.company, "exchange_gain_loss_account"
			)
			if not exchange_gain_loss_account:
				exchange_gain_loss_account = frappe.db.get_single_value(
					"Accounts Settings", "exchange_gain_loss_account"
				)
			if not exchange_gain_loss_account:
				frappe.throw(
					_("Please set Exchange Gain/Loss Account in Company {0} to post exchange differences.").format(
						self.company
					)
				)

			fx_account_currency = get_account_currency(exchange_gain_loss_account)
			if fx_account_currency != company_currency:
				uses_foreign_account = True
				rate = fetch_exchange_rate(fx_account_currency, company_currency, self.posting_date)
				debit_acc = flt(fx_debit) / flt(rate) if fx_debit else 0
				credit_acc = flt(fx_credit) / flt(rate) if fx_credit else 0
			else:
				rate = 1.0
				debit_acc = fx_debit
				credit_acc = fx_credit

			je_entries.append(
				self._je_account_row(
					exchange_gain_loss_account,
					fx_account_currency,
					rate,
					debit_acc=debit_acc,
					credit_acc=credit_acc,
					user_remark=f"Exchange gain/loss for Settlement Entry {self.name}",
				)
			)

		return je_entries, uses_foreign_account

	@frappe.whitelist()
	def create_journal_entry(self):
		"""Create journal entry for settlement transactions with multi-currency support."""
		je_entries, uses_foreign_account = self.build_journal_entry_accounts()

		je = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"posting_date": self.posting_date,
				"company": self.company,
				"accounts": je_entries,
				"user_remark": f"Settlement Entry {self.name} - Settlement Group: {self.settlement_group}",
				"voucher_type": "Journal Entry",
				"reference_no": self.name,
				"reference_date": self.posting_date,
				"multi_currency": 1 if uses_foreign_account else 0,
			}
		)
		je.flags.ignore_exchange_rate = True
		je.insert()

		frappe.db.set_value("Settlement Entry", self.name, "journal_entry", je.name)
		frappe.db.commit()

		frappe.msgprint(_("Journal Entry {0} created. Please review and submit it manually.").format(je.name))

	def update_outstanding_amounts(self, reverse=False):
		"""Update outstanding amounts on referenced documents."""
		for ref in self.references:
			if not ref.reference_doctype or not ref.reference_name:
				continue

			if ref.reference_doctype in ["Sales Invoice", "Purchase Invoice"]:
				current_outstanding = frappe.db.get_value(
					ref.reference_doctype, ref.reference_name, "outstanding_amount"
				)

				if current_outstanding is None:
					continue

				if reverse:
					new_outstanding = flt(current_outstanding) + flt(ref.allocated_amount)
				else:
					new_outstanding = flt(current_outstanding) - flt(ref.allocated_amount)

				frappe.db.set_value(
					ref.reference_doctype, ref.reference_name, "outstanding_amount", new_outstanding
				)

		frappe.db.commit()


@frappe.whitelist()
def get_outstanding_transactions(docname, clear_existing=0):
	"""Standalone function to get outstanding transactions (for static calls)."""
	doc = frappe.get_doc("Settlement Entry", docname)
	return doc._get_outstanding_transactions(clear_existing=clear_existing)


@frappe.whitelist()
def get_settlement_exchange_rate(from_currency, to_currency, transaction_date=None, args=None):
	"""Form helper: invoice/settlement exchange rate (does not throw; 0 means not found)."""
	return fetch_exchange_rate(from_currency, to_currency, transaction_date, args, throw=False)
