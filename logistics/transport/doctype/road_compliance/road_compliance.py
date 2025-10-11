# -*- coding: utf-8 -*-
# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, add_days, nowdate
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class RoadCompliance(Document):
    def validate(self):
        """Validate compliance rules and check expiry dates"""
        self.validate_dates()
        self.check_expiry_alerts()
        self.validate_requirements()
    
    def validate_dates(self):
        """Validate effective and expiry dates"""
        if self.expiry_date and self.effective_date:
            if getdate(self.expiry_date) <= getdate(self.effective_date):
                frappe.throw(_("Expiry Date must be after Effective Date"))
    
    def check_expiry_alerts(self):
        """Check if compliance is expiring soon and create alerts"""
        if not self.expiry_date or not self.alert_before_expiry:
            return
        
        days_until_expiry = (getdate(self.expiry_date) - getdate(nowdate())).days
        
        if days_until_expiry <= self.alert_before_expiry and days_until_expiry >= 0:
            self.create_expiry_alert()
    
    def create_expiry_alert(self):
        """Create an alert for expiring compliance"""
        alert_doc = frappe.get_doc({
            "doctype": "Alert",
            "subject": f"Road Compliance Expiring: {self.title}",
            "message": f"Road Compliance '{self.title}' will expire on {self.expiry_date}",
            "alert_type": "Info",
            "reference_doctype": "Road Compliance",
            "reference_name": self.name,
            "priority": self.priority
        })
        alert_doc.insert(ignore_permissions=True)
    
    def validate_requirements(self):
        """Validate that all requirements are properly defined"""
        if not self.requirements:
            return
        
        for req in self.requirements:
            if not req.requirement_name:
                frappe.throw(_("Requirement Name is required for all requirements"))
            
            if not req.requirement_type:
                frappe.throw(_("Requirement Type is required for all requirements"))


@frappe.whitelist()
def check_vehicle_compliance(vehicle_name: str) -> Dict[str, Any]:
    """Check compliance status for a specific vehicle"""
    try:
        vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
        
        # Get all active compliance rules that apply to vehicles
        compliance_rules = frappe.get_all(
            "Road Compliance",
            filters={
                "applies_to_vehicles": 1,
                "status": "Active",
                "effective_date": ["<=", nowdate()],
                "expiry_date": [">", nowdate()]
            },
            fields=["name", "title", "compliance_type", "expiry_date", "priority"]
        )
        
        compliance_status = []
        violations = []
        
        for rule in compliance_rules:
            # Check if vehicle meets compliance requirements
            is_compliant, violation_reason = check_vehicle_rule_compliance(vehicle, rule)
            
            compliance_status.append({
                "rule_name": rule.name,
                "rule_title": rule.title,
                "compliance_type": rule.compliance_type,
                "is_compliant": is_compliant,
                "expiry_date": rule.expiry_date,
                "priority": rule.priority,
                "violation_reason": violation_reason
            })
            
            if not is_compliant:
                violations.append({
                    "rule": rule.title,
                    "reason": violation_reason,
                    "priority": rule.priority
                })
        
        return {
            "vehicle": vehicle_name,
            "compliance_status": compliance_status,
            "violations": violations,
            "overall_compliant": len(violations) == 0,
            "total_rules": len(compliance_rules),
            "violations_count": len(violations)
        }
        
    except Exception as e:
        frappe.log_error(f"Error checking vehicle compliance: {str(e)}", "Road Compliance")
        return {"error": str(e)}


@frappe.whitelist()
def check_driver_compliance(driver_name: str) -> Dict[str, Any]:
    """Check compliance status for a specific driver"""
    try:
        driver = frappe.get_doc("Driver", driver_name)
        
        # Get all active compliance rules that apply to drivers
        compliance_rules = frappe.get_all(
            "Road Compliance",
            filters={
                "applies_to_drivers": 1,
                "status": "Active",
                "effective_date": ["<=", nowdate()],
                "expiry_date": [">", nowdate()]
            },
            fields=["name", "title", "compliance_type", "expiry_date", "priority"]
        )
        
        compliance_status = []
        violations = []
        
        for rule in compliance_rules:
            # Check if driver meets compliance requirements
            is_compliant, violation_reason = check_driver_rule_compliance(driver, rule)
            
            compliance_status.append({
                "rule_name": rule.name,
                "rule_title": rule.title,
                "compliance_type": rule.compliance_type,
                "is_compliant": is_compliant,
                "expiry_date": rule.expiry_date,
                "priority": rule.priority,
                "violation_reason": violation_reason
            })
            
            if not is_compliant:
                violations.append({
                    "rule": rule.title,
                    "reason": violation_reason,
                    "priority": rule.priority
                })
        
        return {
            "driver": driver_name,
            "compliance_status": compliance_status,
            "violations": violations,
            "overall_compliant": len(violations) == 0,
            "total_rules": len(compliance_rules),
            "violations_count": len(violations)
        }
        
    except Exception as e:
        frappe.log_error(f"Error checking driver compliance: {str(e)}", "Road Compliance")
        return {"error": str(e)}


def check_vehicle_rule_compliance(vehicle: Document, rule: Dict[str, Any]) -> tuple[bool, str]:
    """Check if a vehicle complies with a specific rule"""
    try:
        # Get rule requirements
        requirements = frappe.get_all(
            "Road Compliance Requirement",
            filters={"parent": rule["name"]},
            fields=["requirement_name", "requirement_type", "required_value", "operator"]
        )
        
        for req in requirements:
            if req["requirement_type"] == "Vehicle Registration":
                if not vehicle.license_plate:
                    return False, "Vehicle registration not found"
            
            elif req["requirement_type"] == "Insurance":
                if not vehicle.insurance_expiry_date:
                    return False, "Vehicle insurance not found"
                elif getdate(vehicle.insurance_expiry_date) <= getdate(nowdate()):
                    return False, "Vehicle insurance expired"
            
            elif req["requirement_type"] == "Weight Limit":
                if req["required_value"] and vehicle.max_weight:
                    if vehicle.max_weight > float(req["required_value"]):
                        return False, f"Vehicle weight {vehicle.max_weight} exceeds limit {req['required_value']}"
            
            elif req["requirement_type"] == "Dimension Limit":
                if req["required_value"] and vehicle.max_volume:
                    if vehicle.max_volume > float(req["required_value"]):
                        return False, f"Vehicle volume {vehicle.max_volume} exceeds limit {req['required_value']}"
        
        return True, "Compliant"
        
    except Exception as e:
        frappe.log_error(f"Error checking vehicle rule compliance: {str(e)}", "Road Compliance")
        return False, f"Error checking compliance: {str(e)}"


def check_driver_rule_compliance(driver: Document, rule: Dict[str, Any]) -> tuple[bool, str]:
    """Check if a driver complies with a specific rule"""
    try:
        # Get rule requirements
        requirements = frappe.get_all(
            "Road Compliance Requirement",
            filters={"parent": rule["name"]},
            fields=["requirement_name", "requirement_type", "required_value", "operator"]
        )
        
        for req in requirements:
            if req["requirement_type"] == "Driver License":
                if not driver.license_number:
                    return False, "Driver license not found"
                elif driver.license_expiry_date and getdate(driver.license_expiry_date) <= getdate(nowdate()):
                    return False, "Driver license expired"
            
            elif req["requirement_type"] == "Hours of Service":
                # Check if driver has exceeded hours of service limits
                if hasattr(driver, 'hours_worked_today') and driver.hours_worked_today:
                    if req["required_value"] and driver.hours_worked_today > float(req["required_value"]):
                        return False, f"Driver hours {driver.hours_worked_today} exceed limit {req['required_value']}"
        
        return True, "Compliant"
        
    except Exception as e:
        frappe.log_error(f"Error checking driver rule compliance: {str(e)}", "Road Compliance")
        return False, f"Error checking compliance: {str(e)}"


@frappe.whitelist()
def get_compliance_dashboard() -> Dict[str, Any]:
    """Get compliance dashboard data"""
    try:
        # Get compliance statistics
        total_rules = frappe.db.count("Road Compliance", {"status": "Active"})
        expiring_soon = frappe.db.count(
            "Road Compliance",
            {
                "status": "Active",
                "expiry_date": ["<=", add_days(nowdate(), 30)],
                "expiry_date": [">", nowdate()]
            }
        )
        expired = frappe.db.count(
            "Road Compliance",
            {
                "status": "Active",
                "expiry_date": ["<", nowdate()]
            }
        )
        
        # Get recent violations
        recent_violations = frappe.get_all(
            "Road Compliance Violation",
            filters={"creation": [">=", add_days(nowdate(), -7)]},
            fields=["name", "vehicle", "driver", "rule", "violation_type", "priority", "creation"],
            order_by="creation desc",
            limit=10
        )
        
        return {
            "total_rules": total_rules,
            "expiring_soon": expiring_soon,
            "expired": expired,
            "recent_violations": recent_violations,
            "compliance_rate": ((total_rules - expired) / total_rules * 100) if total_rules > 0 else 0
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting compliance dashboard: {str(e)}", "Road Compliance")
        return {"error": str(e)}



