import frappe
from frappe.model.document import Document
from frappe import _
from typing import Dict, List, Optional, Any


class WarehouseSettings(Document):
    def validate(self):
        """Validate warehouse settings"""
        # Only validate fields that exist in the doctype
        if hasattr(self, 'default_volume_alert_threshold') and self.default_volume_alert_threshold is not None:
            try:
                threshold = float(self.default_volume_alert_threshold)
                if threshold < 0 or threshold > 100:
                    frappe.throw(_("Default Volume Alert Threshold must be between 0 and 100"))
            except (ValueError, TypeError):
                frappe.throw(_("Default Volume Alert Threshold must be a valid number"))
                
        if hasattr(self, 'default_weight_alert_threshold') and self.default_weight_alert_threshold is not None:
            try:
                threshold = float(self.default_weight_alert_threshold)
                if threshold < 0 or threshold > 100:
                    frappe.throw(_("Default Weight Alert Threshold must be between 0 and 100"))
            except (ValueError, TypeError):
                frappe.throw(_("Default Weight Alert Threshold must be a valid number"))
                
        if hasattr(self, 'default_utilization_alert_threshold') and self.default_utilization_alert_threshold is not None:
            try:
                threshold = float(self.default_utilization_alert_threshold)
                if threshold < 0 or threshold > 100:
                    frappe.throw(_("Default Utilization Alert Threshold must be between 0 and 100"))
            except (ValueError, TypeError):
                frappe.throw(_("Default Utilization Alert Threshold must be a valid number"))
                
        if hasattr(self, 'volume_calculation_precision') and self.volume_calculation_precision is not None:
            try:
                precision = float(self.volume_calculation_precision)
                if precision < 0 or precision > 10:
                    frappe.throw(_("Volume Calculation Precision must be between 0 and 10"))
            except (ValueError, TypeError):
                frappe.throw(_("Volume Calculation Precision must be a valid number"))


@frappe.whitelist()
def get_warehouse_settings(company=None):
    """Get warehouse settings for a company"""
    if not company:
        company = frappe.defaults.get_user_default("Company")
    
    try:
        settings = frappe.get_doc("Warehouse Settings", company)
        
        volume_uom = "m³"
        weight_uom = "kg"
        
        if settings.default_volume_uom:
            try:
                volume_uom_doc = frappe.get_doc("UOM", settings.default_volume_uom)
                volume_uom = volume_uom_doc.name
            except:
                volume_uom = "m³"
        
        if settings.default_weight_uom:
            try:
                weight_uom_doc = frappe.get_doc("UOM", settings.default_weight_uom)
                weight_uom = weight_uom_doc.name
            except:
                weight_uom = "kg"
        
        return {
            "default_volume_uom": volume_uom,
            "default_weight_uom": weight_uom,
            "default_pallet_volume": getattr(settings, 'default_pallet_volume', 2.0),
            "default_pallet_weight": getattr(settings, 'default_pallet_weight', 1000.0),
            "default_box_volume": getattr(settings, 'default_box_volume', 0.1),
            "default_box_weight": getattr(settings, 'default_box_weight', 50.0),
            "enable_capacity_planning": getattr(settings, 'enable_capacity_management', True),
            "capacity_warning_threshold": getattr(settings, 'default_volume_alert_threshold', 80.0),
            "capacity_critical_threshold": getattr(settings, 'default_utilization_alert_threshold', 90.0)
        }
    except frappe.DoesNotExistError:
        # Return default settings if not found
        return {
            "default_volume_uom": "m³",
            "default_weight_uom": "kg",
            "default_pallet_volume": 2.0,
            "default_pallet_weight": 1000.0,
            "default_box_volume": 0.1,
            "default_box_weight": 50.0,
            "enable_capacity_planning": True,
            "capacity_warning_threshold": 80.0,
            "capacity_critical_threshold": 100.0
        }


@frappe.whitelist()
def get_default_uoms():
    """Get default UOMs from warehouse settings"""
    company = frappe.defaults.get_user_default("Company")
    settings = get_warehouse_settings(company)
    
    return {
        "volume_uom": settings.get('default_volume_uom', 'm³'),
        "weight_uom": settings.get('default_weight_uom', 'kg')
    }


@frappe.whitelist()
def get_default_billing_methods():
    """Get default billing methods from warehouse settings"""
    company = frappe.defaults.get_user_default("Company")
    
    try:
        settings = frappe.get_doc("Warehouse Settings", company)
        return {
            "billing_method": getattr(settings, 'default_billing_method', 'Per Volume')
        }
    except frappe.DoesNotExistError:
        return {}


@frappe.whitelist()
def apply_default_uoms_to_contract_item(contract_item_name):
    """Apply default UOMs to a contract item"""
    try:
        contract_item = frappe.get_doc("Warehouse Contract Item", contract_item_name)
        default_uoms = get_default_uoms()
        
        # Apply default UOMs
        if not contract_item.billing_time_unit:
            contract_item.billing_time_unit = default_uoms.get('volume_uom')
        if not contract_item.billing_time_multiplier:
            contract_item.billing_time_multiplier = 1.0
        if not contract_item.minimum_billing_time:
            contract_item.minimum_billing_time = 1.0
        if not contract_item.uom:
            contract_item.uom = default_uoms.get('weight_uom')
            
        contract_item.save()
        return {"status": "success", "message": "Default UOMs applied successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def apply_default_billing_methods(contract_item_name):
    """Apply default billing methods to a contract item"""
    try:
        contract_item = frappe.get_doc("Warehouse Contract Item", contract_item_name)
        default_methods = get_default_billing_methods()
        
        # Apply default billing method
        if not contract_item.billing_method and default_methods.get('billing_method'):
            contract_item.billing_method = default_methods.get('billing_method')
            
        contract_item.save()
        return {"status": "success", "message": "Default billing methods applied successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def validate_billing_method(charge_type, billing_method):
    """Validate a billing method for a charge type"""
    if not billing_method:
        return {"status": "success", "valid": True}
    
    # Add validation logic here based on charge type and billing method
    valid_methods = {
        'storage': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'inbound': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'outbound': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'transfer': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'vas': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'stocktake': ['per_unit', 'per_volume', 'per_weight', 'per_time']
    }
    
    if billing_method in valid_methods.get(charge_type, []):
        return {"status": "success", "valid": True}
    else:
        return {"status": "error", "valid": False, "message": f"Invalid billing method for {charge_type}"}


@frappe.whitelist()
def get_volume_billing_settings():
    """Get volume billing settings"""
    company = frappe.defaults.get_user_default("Company")
    
    try:
        settings = frappe.get_doc("Warehouse Settings", company)
        return {
            "enable_volume_billing": getattr(settings, 'enable_volume_billing', False),
            "volume_calculation_precision": getattr(settings, 'volume_calculation_precision', 3),
            "default_volume_uom": getattr(settings, 'default_volume_uom', 'm³')
        }
    except frappe.DoesNotExistError:
        return {
            "enable_volume_billing": False,
            "volume_calculation_precision": 3,
            "default_volume_uom": 'm³'
        }


@frappe.whitelist()
def bulk_apply_default_uoms(contract_names):
    """Apply default UOMs to multiple contracts"""
    if isinstance(contract_names, str):
        contract_names = frappe.parse_json(contract_names)
    
    results = []
    for contract_name in contract_names:
        result = apply_default_uoms_to_contract_item(contract_name)
        results.append({"contract": contract_name, "result": result})
    
    return results


@frappe.whitelist()
def bulk_apply_defaults(contract_names):
    """Apply default UOMs and billing methods to multiple contracts"""
    if isinstance(contract_names, str):
        contract_names = frappe.parse_json(contract_names)
    
    results = []
    for contract_name in contract_names:
        uom_result = apply_default_uoms_to_contract_item(contract_name)
        billing_result = apply_default_billing_methods(contract_name)
        results.append({
            "contract": contract_name, 
            "uom_result": uom_result,
            "billing_result": billing_result
        })
    
    return results


@frappe.whitelist()
def get_billing_method_options(charge_type):
    """Get available billing method options for a charge type"""
    options = {
        'storage': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'inbound': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'outbound': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'transfer': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'vas': ['per_unit', 'per_volume', 'per_weight', 'per_time'],
        'stocktake': ['per_unit', 'per_volume', 'per_weight', 'per_time']
    }
    
    return options.get(charge_type, [])


@frappe.whitelist()
def get_billing_method_info(billing_method):
    """Get information about a billing method"""
    info = {
        'per_unit': {
            'description': 'Billing per unit quantity',
            'uom_required': True,
            'calculation': 'quantity * rate'
        },
        'per_volume': {
            'description': 'Billing per volume (length * width * height)',
            'uom_required': True,
            'calculation': 'volume * rate'
        },
        'per_weight': {
            'description': 'Billing per weight',
            'uom_required': True,
            'calculation': 'weight * rate'
        },
        'per_time': {
            'description': 'Billing per time period',
            'uom_required': True,
            'calculation': 'time_period * rate'
        }
    }
    
    return info.get(billing_method, {})


@frappe.whitelist()
def get_default_uom_for_billing_method(billing_method):
    """Get default UOM for a billing method"""
    uom_mapping = {
        'per_unit': 'Nos',
        'per_volume': 'm³',
        'per_weight': 'kg',
        'per_time': 'Day'
    }
    
    return uom_mapping.get(billing_method, 'Nos')


@frappe.whitelist()
def validate_uom_for_billing_method(billing_method, uom):
    """Validate UOM for a billing method"""
    valid_uoms = {
        'per_unit': ['Nos', 'Pcs', 'Units'],
        'per_volume': ['m³', 'cm³', 'ft³', 'in³'],
        'per_weight': ['kg', 'g', 'lb', 'oz'],
        'per_time': ['Day', 'Week', 'Month', 'Year']
    }
    
    if uom in valid_uoms.get(billing_method, []):
        return {"status": "success", "valid": True}
    else:
        return {"status": "error", "valid": False, "message": f"Invalid UOM for {billing_method}"}