import frappe
from frappe import _

class ZoneManager:
    """Zone and location management for transport pricing"""
    
    @staticmethod
    def get_zone_from_zip_code(zip_code, country=None):
        """Get transport zone from zip code"""
        
        try:
            # Direct zip code mapping
            zone = frappe.get_value("Zip Code Zone Mapping", 
                {"zip_code": zip_code, "enabled": 1}, 
                "transport_zone"
            )
            
            if zone:
                return zone
            
            # Partial zip code matching (first 3 digits)
            if len(zip_code) >= 3:
                partial_zip = zip_code[:3]
                zone = frappe.get_value("Zip Code Zone Mapping", 
                    {"zip_code": ["like", f"{partial_zip}%"], "enabled": 1}, 
                    "transport_zone"
                )
                
                if zone:
                    return zone
            
            # Zip code range matching
            zone = frappe.get_value("Transport Zone", 
                {
                    "zip_code_range_from": ["<=", zip_code],
                    "zip_code_range_to": [">=", zip_code],
                    "enabled": 1
                }, 
                "name"
            )
            
            if zone:
                return zone
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Zone lookup failed: {str(e)}")
            return None
    
    @staticmethod
    def get_zone_from_location(location_name, country=None):
        """Get transport zone from location name"""
        
        try:
            # Get location details
            location = frappe.get_doc("Location", location_name)
            
            if location.zip_code:
                zone = ZoneManager.get_zone_from_zip_code(location.zip_code, location.country)
                if zone:
                    return zone
            
            # Fallback to location-based zone lookup
            zone = frappe.get_value("Transport Zone", 
                {
                    "zone_name": ["like", f"%{location_name}%"],
                    "enabled": 1
                }, 
                "name"
            )
            
            if zone:
                return zone
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Location zone lookup failed: {str(e)}")
            return None
    
    @staticmethod
    def update_zones_for_locations(origin, destination):
        """Update zones for origin and destination locations"""
        
        try:
            origin_zone = ZoneManager.get_zone_from_location(origin)
            destination_zone = ZoneManager.get_zone_from_location(destination)
            
            return {
                "origin_zone": origin_zone,
                "destination_zone": destination_zone
            }
            
        except Exception as e:
            frappe.log_error(f"Zone update failed: {str(e)}")
            return {
                "origin_zone": None,
                "destination_zone": None
            }

@frappe.whitelist()
def get_zone_from_zip_code(zip_code, country=None):
    """API endpoint for zone lookup from zip code"""
    
    return ZoneManager.get_zone_from_zip_code(zip_code, country)

@frappe.whitelist()
def get_zone_from_location(location_name, country=None):
    """API endpoint for zone lookup from location"""
    
    return ZoneManager.get_zone_from_location(location_name, country)

@frappe.whitelist()
def update_zones_for_locations(origin, destination):
    """API endpoint for updating zones for locations"""
    
    return ZoneManager.update_zones_for_locations(origin, destination)

