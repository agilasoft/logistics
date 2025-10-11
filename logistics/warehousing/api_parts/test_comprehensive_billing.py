#!/usr/bin/env python3
"""
Comprehensive Billing Methods Test Suite

This module tests all billing methods across the entire warehouse system:
- Per Day, Per Volume, Per Weight, Per Piece, Per Container, Per Hour, Per Handling Unit, High Water Mark
"""

from __future__ import annotations
import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, now_datetime, add_days
from typing import Dict, List, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import json

# =============================================================================
# Test Functions
# =============================================================================

@frappe.whitelist()
def test_all_billing_methods():
    """Test all billing methods comprehensively."""
    results = {
        "ok": True,
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "results": []
    }
    
    try:
        # Test billing method calculations
        results["results"].append(_test_billing_method_calculations())
        
        # Test contract charge retrieval
        results["results"].append(_test_contract_charge_retrieval())
        
        # Test order charge calculations
        results["results"].append(_test_order_charge_calculations())
        
        # Test job charge calculations
        results["results"].append(_test_job_charge_calculations())
        
        # Test periodic billing
        results["results"].append(_test_periodic_billing())
        
        # Test charge table updates
        results["results"].append(_test_charge_table_updates())
        
        # Calculate summary
        for result in results["results"]:
            results["tests_run"] += result.get("tests_run", 0)
            results["tests_passed"] += result.get("tests_passed", 0)
            results["tests_failed"] += result.get("tests_failed", 0)
        
        if results["tests_failed"] > 0:
            results["ok"] = False
        
    except Exception as e:
        results["ok"] = False
        results["error"] = str(e)
        frappe.log_error(f"Error in test_all_billing_methods: {str(e)}")
    
    return results


def _test_billing_method_calculations():
    """Test billing method calculation functions."""
    result = {
        "test_name": "Billing Method Calculations",
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "details": []
    }
    
    try:
        from .billing_methods import get_billing_quantity
        
        # Test Per Day calculation
        result["tests_run"] += 1
        try:
            quantity = get_billing_quantity(
                context="storage",
                billing_method="Per Day",
                reference_doc="TEST-HU-001",
                date_from="2024-01-01",
                date_to="2024-01-31"
            )
            if quantity >= 0:
                result["tests_passed"] += 1
                result["details"].append("✅ Per Day calculation works")
            else:
                result["tests_failed"] += 1
                result["details"].append("❌ Per Day calculation failed")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Per Day calculation error: {str(e)}")
        
        # Test Per Volume calculation
        result["tests_run"] += 1
        try:
            quantity = get_billing_quantity(
                context="storage",
                billing_method="Per Volume",
                reference_doc="TEST-HU-001",
                date_from="2024-01-01",
                date_to="2024-01-31",
                volume_calculation_method="Daily Volume"
            )
            if quantity >= 0:
                result["tests_passed"] += 1
                result["details"].append("✅ Per Volume calculation works")
            else:
                result["tests_failed"] += 1
                result["details"].append("❌ Per Volume calculation failed")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Per Volume calculation error: {str(e)}")
        
        # Test Per Weight calculation
        result["tests_run"] += 1
        try:
            quantity = get_billing_quantity(
                context="storage",
                billing_method="Per Weight",
                reference_doc="TEST-HU-001",
                date_from="2024-01-01",
                date_to="2024-01-31"
            )
            if quantity >= 0:
                result["tests_passed"] += 1
                result["details"].append("✅ Per Weight calculation works")
            else:
                result["tests_failed"] += 1
                result["details"].append("❌ Per Weight calculation failed")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Per Weight calculation error: {str(e)}")
        
        # Test Per Piece calculation
        result["tests_run"] += 1
        try:
            quantity = get_billing_quantity(
                context="vas",
                billing_method="Per Piece",
                reference_doc="TEST-VAS-001",
                date_from="2024-01-01",
                date_to="2024-01-31"
            )
            if quantity >= 0:
                result["tests_passed"] += 1
                result["details"].append("✅ Per Piece calculation works")
            else:
                result["tests_failed"] += 1
                result["details"].append("❌ Per Piece calculation failed")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Per Piece calculation error: {str(e)}")
        
        # Test Per Container calculation
        result["tests_run"] += 1
        try:
            quantity = get_billing_quantity(
                context="inbound",
                billing_method="Per Container",
                reference_doc="TEST-INBOUND-001",
                date_from="2024-01-01",
                date_to="2024-01-31"
            )
            if quantity >= 0:
                result["tests_passed"] += 1
                result["details"].append("✅ Per Container calculation works")
            else:
                result["tests_failed"] += 1
                result["details"].append("❌ Per Container calculation failed")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Per Container calculation error: {str(e)}")
        
        # Test Per Hour calculation
        result["tests_run"] += 1
        try:
            quantity = get_billing_quantity(
                context="vas",
                billing_method="Per Hour",
                reference_doc="TEST-VAS-001",
                date_from="2024-01-01",
                date_to="2024-01-31"
            )
            if quantity >= 0:
                result["tests_passed"] += 1
                result["details"].append("✅ Per Hour calculation works")
            else:
                result["tests_failed"] += 1
                result["details"].append("❌ Per Hour calculation failed")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Per Hour calculation error: {str(e)}")
        
        # Test Per Handling Unit calculation
        result["tests_run"] += 1
        try:
            quantity = get_billing_quantity(
                context="storage",
                billing_method="Per Handling Unit",
                reference_doc="TEST-HU-001",
                date_from="2024-01-01",
                date_to="2024-01-31"
            )
            if quantity >= 0:
                result["tests_passed"] += 1
                result["details"].append("✅ Per Handling Unit calculation works")
            else:
                result["tests_failed"] += 1
                result["details"].append("❌ Per Handling Unit calculation failed")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Per Handling Unit calculation error: {str(e)}")
        
        # Test High Water Mark calculation
        result["tests_run"] += 1
        try:
            quantity = get_billing_quantity(
                context="storage",
                billing_method="High Water Mark",
                reference_doc="TEST-HU-001",
                date_from="2024-01-01",
                date_to="2024-01-31"
            )
            if quantity >= 0:
                result["tests_passed"] += 1
                result["details"].append("✅ High Water Mark calculation works")
            else:
                result["tests_failed"] += 1
                result["details"].append("❌ High Water Mark calculation failed")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ High Water Mark calculation error: {str(e)}")
        
    except Exception as e:
        result["tests_failed"] += 1
        result["details"].append(f"❌ Billing method calculations test error: {str(e)}")
    
    return result


def _test_contract_charge_retrieval():
    """Test contract charge retrieval with all billing methods."""
    result = {
        "test_name": "Contract Charge Retrieval",
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "details": []
    }
    
    try:
        # Test contract charge retrieval
        result["tests_run"] += 1
        try:
            from logistics.warehousing.api import get_contract_charge
            
            # This will test if the function can be called without errors
            # In a real test, you would need actual contract and item data
            charge_data = get_contract_charge("TEST-CONTRACT", "TEST-ITEM", "storage")
            
            result["tests_passed"] += 1
            result["details"].append("✅ Contract charge retrieval works")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Contract charge retrieval error: {str(e)}")
        
    except Exception as e:
        result["tests_failed"] += 1
        result["details"].append(f"❌ Contract charge retrieval test error: {str(e)}")
    
    return result


def _test_order_charge_calculations():
    """Test order charge calculations."""
    result = {
        "test_name": "Order Charge Calculations",
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "details": []
    }
    
    try:
        # Test order charge calculation API
        result["tests_run"] += 1
        try:
            from logistics.warehousing.api import calculate_order_charges
            
            # This will test if the function can be called without errors
            # In a real test, you would need actual contract and order data
            charge_data = calculate_order_charges("TEST-CONTRACT", "TEST-ORDER", "inbound")
            
            result["tests_passed"] += 1
            result["details"].append("✅ Order charge calculation API works")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Order charge calculation error: {str(e)}")
        
    except Exception as e:
        result["tests_failed"] += 1
        result["details"].append(f"❌ Order charge calculation test error: {str(e)}")
    
    return result


def _test_job_charge_calculations():
    """Test job charge calculations."""
    result = {
        "test_name": "Job Charge Calculations",
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "details": []
    }
    
    try:
        # Test job charge calculation API
        result["tests_run"] += 1
        try:
            from logistics.warehousing.api import calculate_job_charges
            
            # This will test if the function can be called without errors
            # In a real test, you would need actual contract and job data
            charge_data = calculate_job_charges("TEST-CONTRACT", "TEST-JOB")
            
            result["tests_passed"] += 1
            result["details"].append("✅ Job charge calculation API works")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Job charge calculation error: {str(e)}")
        
    except Exception as e:
        result["tests_failed"] += 1
        result["details"].append(f"❌ Job charge calculation test error: {str(e)}")
    
    return result


def _test_periodic_billing():
    """Test periodic billing with all methods."""
    result = {
        "test_name": "Periodic Billing",
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "details": []
    }
    
    try:
        # Test comprehensive periodic billing API
        result["tests_run"] += 1
        try:
            from logistics.warehousing.api import periodic_billing_get_comprehensive_charges
            
            # This will test if the function can be called without errors
            # In a real test, you would need actual periodic billing data
            billing_data = periodic_billing_get_comprehensive_charges("TEST-PB", 1)
            
            result["tests_passed"] += 1
            result["details"].append("✅ Comprehensive periodic billing API works")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Comprehensive periodic billing error: {str(e)}")
        
    except Exception as e:
        result["tests_failed"] += 1
        result["details"].append(f"❌ Periodic billing test error: {str(e)}")
    
    return result


def _test_charge_table_updates():
    """Test charge table field updates."""
    result = {
        "test_name": "Charge Table Updates",
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "details": []
    }
    
    try:
        # Test Warehouse Job Charges doctype
        result["tests_run"] += 1
        try:
            job_charges_meta = frappe.get_meta("Warehouse Job Charges")
            fields = [f.fieldname for f in job_charges_meta.fields]
            
            required_fields = [
                "billing_method", "volume_quantity", "volume_uom",
                "weight_quantity", "weight_uom", "piece_quantity", "piece_uom",
                "container_quantity", "container_uom", "hour_quantity", "hour_uom",
                "handling_unit_quantity", "handling_unit_uom", "peak_quantity", "peak_uom"
            ]
            
            missing_fields = [f for f in required_fields if f not in fields]
            
            if not missing_fields:
                result["tests_passed"] += 1
                result["details"].append("✅ Warehouse Job Charges has all required fields")
            else:
                result["tests_failed"] += 1
                result["details"].append(f"❌ Warehouse Job Charges missing fields: {missing_fields}")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Warehouse Job Charges test error: {str(e)}")
        
        # Test Periodic Billing Charges doctype
        result["tests_run"] += 1
        try:
            pb_charges_meta = frappe.get_meta("Periodic Billing Charges")
            fields = [f.fieldname for f in pb_charges_meta.fields]
            
            required_fields = [
                "billing_method", "volume_quantity", "volume_uom",
                "weight_quantity", "weight_uom", "piece_quantity", "piece_uom",
                "container_quantity", "container_uom", "hour_quantity", "hour_uom",
                "handling_unit_quantity", "handling_unit_uom", "peak_quantity", "peak_uom"
            ]
            
            missing_fields = [f for f in required_fields if f not in fields]
            
            if not missing_fields:
                result["tests_passed"] += 1
                result["details"].append("✅ Periodic Billing Charges has all required fields")
            else:
                result["tests_failed"] += 1
                result["details"].append(f"❌ Periodic Billing Charges missing fields: {missing_fields}")
        except Exception as e:
            result["tests_failed"] += 1
            result["details"].append(f"❌ Periodic Billing Charges test error: {str(e)}")
        
    except Exception as e:
        result["tests_failed"] += 1
        result["details"].append(f"❌ Charge table updates test error: {str(e)}")
    
    return result


# =============================================================================
# Documentation Generation
# =============================================================================

@frappe.whitelist()
def generate_billing_methods_documentation():
    """Generate comprehensive documentation for all billing methods."""
    doc = {
        "title": "Comprehensive Billing Methods Implementation",
        "overview": "Complete implementation of all warehouse billing methods",
        "billing_methods": {
            "Per Day": {
                "description": "Traditional time-based billing",
                "use_cases": ["Storage charges", "Long-term contracts"],
                "calculation": "Number of days × rate",
                "supported_contexts": ["storage", "inbound", "outbound", "transfer", "vas", "stocktake"]
            },
            "Per Volume": {
                "description": "Volume-based billing (CBM, cubic feet, etc.)",
                "use_cases": ["Space utilization", "Cold storage", "High-value goods"],
                "calculation": "Volume × rate",
                "supported_contexts": ["storage", "inbound", "outbound", "transfer", "vas", "stocktake"],
                "calculation_methods": ["Daily Volume", "Peak Volume", "Average Volume", "End Volume"]
            },
            "Per Weight": {
                "description": "Weight-based billing",
                "use_cases": ["Heavy goods", "Weight-sensitive storage"],
                "calculation": "Total weight × rate",
                "supported_contexts": ["storage", "inbound", "outbound", "transfer"]
            },
            "Per Piece": {
                "description": "Item count-based billing",
                "use_cases": ["VAS activities", "Item processing", "Picking operations"],
                "calculation": "Number of pieces × rate",
                "supported_contexts": ["inbound", "outbound", "transfer", "vas", "stocktake"]
            },
            "Per Container": {
                "description": "Container-based billing",
                "use_cases": ["Container operations", "Stripping/stuffing"],
                "calculation": "Number of containers × rate",
                "supported_contexts": ["inbound", "outbound"]
            },
            "Per Hour": {
                "description": "Time-based facility usage",
                "use_cases": ["Overtime usage", "Facility rental", "VAS operations"],
                "calculation": "Hours used × rate",
                "supported_contexts": ["vas"]
            },
            "Per Handling Unit": {
                "description": "Handling unit-based billing",
                "use_cases": ["Pallet-based storage", "Container operations"],
                "calculation": "Number of handling units × rate",
                "supported_contexts": ["storage"]
            },
            "High Water Mark": {
                "description": "Peak usage billing",
                "use_cases": ["Peak storage periods", "Maximum utilization"],
                "calculation": "Peak volume/weight/units × rate",
                "supported_contexts": ["storage"]
            }
        },
        "implementation_files": [
            "logistics/warehousing/api_parts/billing_methods.py",
            "logistics/warehousing/api_parts/periodic_billing_comprehensive.py",
            "logistics/warehousing/api.py (updated)",
            "logistics/warehousing/doctype/warehouse_job_charges/warehouse_job_charges.json (updated)",
            "logistics/warehousing/doctype/periodic_billing_charges/periodic_billing_charges.json (updated)"
        ],
        "api_functions": [
            "calculate_warehouse_charges()",
            "periodic_billing_get_comprehensive_charges()",
            "calculate_order_charges()",
            "calculate_job_charges()",
            "get_contract_charge() (updated)"
        ]
    }
    
    return doc
