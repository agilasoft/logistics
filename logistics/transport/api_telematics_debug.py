# Copyright (c) 2025, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_all_device_ids():
	"""
	Get all device IDs from all enabled telematics providers.
	Returns a list of devices with their IDs, names, and provider information.
	"""
	try:
		# Get all enabled telematics providers
		providers = frappe.get_all(
			"Telematics Provider",
			filters={"enabled": 1},
			fields=["name", "provider_type"]
		)
		
		if not providers:
			return {
				"error": "No enabled telematics providers found",
				"devices": [],
				"total_devices": 0,
				"provider_errors": []
			}
		
		all_devices = []
		provider_errors = []
		
		# Get devices from each provider
		from logistics.transport.telematics.resolve import _provider_conf
		from logistics.transport.telematics.providers import make_provider
		
		for provider_doc in providers:
			try:
				conf = _provider_conf(provider_doc.name)
				if not conf:
					provider_errors.append({
						"provider": provider_doc.name,
						"error": "Provider not configured or disabled"
					})
					continue
				
				# Enable debug mode
				conf["debug"] = 1
				conf["request_timeout_sec"] = 30
				
				provider = make_provider(conf["provider_type"], conf)
				
				# Get device details
				devices = []
				if hasattr(provider, 'get_device_details'):
					devices = provider.get_device_details()
				elif hasattr(provider, 'GetDevices'):
					from logistics.transport.telematics.providers.remora import _get_field
					raw_devices = provider.GetDevices()
					devices = [
						{
							"device_id": _get_field(dev, "deviceId", "DeviceId", "deviceID", "id", "Id", "ID"),
							"name": _get_field(dev, "name", "Name", "deviceName", "DeviceName"),
							"description": _get_field(dev, "description", "Description", "desc", "Desc"),
							"external_id": _get_field(dev, "externalId", "ExternalId", "externalID", "ExternalID"),
							"raw": dev
						} for dev in raw_devices
					]
				
				# Add provider info to each device
				for device in devices:
					device_id = device.get("device_id") or device.get("external_id")
					if device_id:
						all_devices.append({
							"device_id": str(device_id),
							"device_name": device.get("name") or device.get("description") or "N/A",
							"provider": provider_doc.name,
							"provider_type": conf.get("provider_type", "Unknown")
						})
			
			except Exception as e:
				err_msg = str(e)
				frappe.log_error(
					f"Error getting devices from provider {provider_doc.name}: {err_msg}",
					"Telematics Debug - Get All Devices"
				)
				provider_errors.append({
					"provider": provider_doc.name,
					"error": err_msg
				})
				continue
		
		return {
			"devices": all_devices,
			"total_devices": len(all_devices),
			"providers_checked": len(providers),
			"provider_errors": provider_errors
		}
	
	except Exception as e:
		frappe.log_error(f"Error in get_all_device_ids: {str(e)}", "Telematics Debug")
		return {
			"error": str(e),
			"devices": [],
			"total_devices": 0,
			"provider_errors": []
		}


@frappe.whitelist()
def debug_vehicle_telematics(vehicle_name):
	"""
	Debug telematics connection for a specific vehicle.
	Similar to the debug_telematics_connection method in TransportVehicle,
	but accessible as a standalone API endpoint.
	"""
	try:
		vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
		
		# Use the existing debug method from the TransportVehicle class
		return vehicle.debug_telematics_connection()
	
	except frappe.DoesNotExistError:
		return {
			"error": f"Vehicle {vehicle_name} not found",
			"vehicle_name": vehicle_name,
			"available_devices": [],
			"available_positions": [],
			"available_can_data": [],
			"errors": [f"Vehicle {vehicle_name} not found"]
		}
	except Exception as e:
		frappe.log_error(f"Error in debug_vehicle_telematics: {str(e)}", "Telematics Debug")
		return {
			"error": str(e),
			"vehicle_name": vehicle_name,
			"available_devices": [],
			"available_positions": [],
			"available_can_data": [],
			"errors": [str(e)]
		}


@frappe.whitelist()
def debug_can_data(vehicle_name):
	"""
	Debug CAN data specifically for a vehicle.
	Returns CAN data information including all available CAN records.
	"""
	debug_info = {
		"vehicle_name": vehicle_name,
		"telematics_external_id": None,
		"telematics_provider": None,
		"provider_enabled": False,
		"can_data_available": False,
		"can_data_count": 0,
		"can_data_for_vehicle": [],
		"all_can_data": [],
		"errors": []
	}
	
	try:
		vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
		debug_info["telematics_external_id"] = vehicle.telematics_external_id
		debug_info["telematics_provider"] = vehicle.telematics_provider
		
		if not vehicle.telematics_provider:
			debug_info["errors"].append("No telematics provider configured for this vehicle")
			return debug_info
		
		if not vehicle.telematics_external_id:
			debug_info["errors"].append("No telematics external ID configured for this vehicle")
			return debug_info
		
		# Get provider configuration
		from logistics.transport.telematics.resolve import _provider_conf
		conf = _provider_conf(vehicle.telematics_provider)
		
		if not conf:
			debug_info["errors"].append(f"Telematics provider {vehicle.telematics_provider} is not enabled or not found")
			return debug_info
		
		debug_info["provider_enabled"] = True
		
		# Enable debug mode
		conf["debug"] = 1
		conf["request_timeout_sec"] = 30
		
		# Create provider instance
		from logistics.transport.telematics.providers import make_provider
		provider = make_provider(conf["provider_type"], conf)
		
		# Fetch CAN data
		try:
			if hasattr(provider, 'fetch_latest_can_data'):
				all_can_data = list(provider.fetch_latest_can_data())
				debug_info["all_can_data"] = all_can_data
				debug_info["can_data_count"] = len(all_can_data)
				debug_info["can_data_available"] = len(all_can_data) > 0
				
				# Filter CAN data for this specific vehicle
				vehicle_can_data = []
				for can_record in all_can_data:
					device_id = can_record.get("device_id") or can_record.get("external_id")
					if str(device_id) == str(vehicle.telematics_external_id):
						vehicle_can_data.append({
							"device_id": device_id,
							"timestamp": can_record.get("timestamp"),
							"fuel_l": can_record.get("fuel_l"),
							"rpm": can_record.get("rpm"),
							"engine_hours": can_record.get("engine_hours"),
							"coolant_c": can_record.get("coolant_c"),
							"ambient_c": can_record.get("ambient_c"),
							"raw_keys": list(can_record.keys()) if isinstance(can_record, dict) else [],
							"raw": can_record.get("raw", can_record)
						})
				
				debug_info["can_data_for_vehicle"] = vehicle_can_data
			else:
				debug_info["errors"].append(f"Provider {conf['provider_type']} does not support CAN data fetching")
		
		except Exception as e:
			debug_info["errors"].append(f"Error fetching CAN data: {str(e)}")
			frappe.log_error(f"Error fetching CAN data for vehicle {vehicle_name}: {str(e)}", "Telematics Debug")
	
	except frappe.DoesNotExistError:
		debug_info["errors"].append(f"Vehicle {vehicle_name} not found")
	
	except Exception as e:
		debug_info["errors"].append(str(e))
		frappe.log_error(f"Error in debug_can_data: {str(e)}", "Telematics Debug")
	
	return debug_info

