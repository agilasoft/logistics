# Copyright (c) 2024, Logistics and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RecognitionPolicySettings(Document):
    def validate(self):
        self.validate_accounts()
        self.validate_unique_combination()

    def validate_accounts(self):
        """Validate that accounts belong to the selected company."""
        account_fields = [
            "wip_account",
            "revenue_liability_account",
            "cost_accrual_account",
            "accrued_cost_liability_account"
        ]
        
        for field in account_fields:
            account = self.get(field)
            if account:
                account_company = frappe.db.get_value("Account", account, "company")
                if account_company != self.company:
                    frappe.throw(
                        f"Account {account} does not belong to company {self.company}"
                    )

    def validate_unique_combination(self):
        """Ensure unique combination of company, cost_center, profit_center, branch."""
        filters = {
            "company": self.company,
            "cost_center": self.cost_center or ["is", "not set"],
            "profit_center": self.profit_center or ["is", "not set"],
            "branch": self.branch or ["is", "not set"],
            "name": ["!=", self.name]
        }
        
        existing = frappe.db.exists("Recognition Policy Settings", filters)
        if existing:
            frappe.throw(
                f"A Recognition Policy Settings already exists for this combination of "
                f"Company, Cost Center, Profit Center, and Branch"
            )
