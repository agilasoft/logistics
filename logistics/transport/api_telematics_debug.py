# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_all_device_ids():
	"""Get all device IDs from all enabled telematics providers"""
	try:
		# Get all telematics providers
		providers = frappe.get_all("Telematics Provider", 
								 filters={"enabled": 1},
								 fields=["name", "provider_type", "base_url"])
		
		if not providers:
			return {
				"error": "No enabled telematics providers found",
				"devices": []
			}
		
		all_devices = []
		
		for provider in providers:
			try:
				# Get provider configuration
				from logistics.transport.telematics.resolve import _provider_conf
				conf = _provider_conf(provider.name)
				
				if not conf:
					continue
				
				# Create provider instance
				from logistics.transport.telematics.providers import make_provider
				telematics_provider = make_provider(conf["provider_type"], conf)
				
				# Get devices
				if hasattr(telematics_provider, 'GetDevices'):
					devices = telematics_provider.GetDevices()
					
					for device in devices:
						device_id = device.get("deviceId") or device.get("DeviceId") or device.get("id")
						device_name = device.get("name") or device.get("Name") or device.get("deviceName")
						
						all_devices.append({
							"provider": provider.name,
							"provider_type": provider.provider_type,
							"device_id": str(device_id) if device_id else "N/A",
							"device_name": device_name or "N/A",
							"raw_data": device
						})
						
			except Exception as e:
				frappe.log_error(f"Error getting devices from {provider.name}: {str(e)}", "Get All Devices")
		
		return {
			"success": True,
			"total_devices": len(all_devices),
			"devices": all_devices
		}
		
	except Exception as e:
		frappe.log_error(f"Error in get_all_device_ids: {str(e)}", "Get All Devices")
		return {
			"error": str(e),
			"devices": []
		}

@frappe.whitelist()
def debug_vehicle_telematics(vehicle_name):
	"""Debug telematics connection for a specific vehicle"""
	try:
		# Get vehicle document
		vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
		
		debug_info = {
			"vehicle_name": vehicle.name,
			"telematics_external_id": vehicle.telematics_external_id,
			"telematics_provider": vehicle.telematics_provider,
			"provider_enabled": False,
			"available_devices": [],
			"available_positions": [],
			"errors": []
		}
		
		if not vehicle.telematics_external_id:
			debug_info["errors"].append("No telematics external ID configured")
			return debug_info
		
		if not vehicle.telematics_provider:
			debug_info["errors"].append("No telematics provider configured")
			return debug_info
		
		# Check provider configuration
		from logistics.transport.telematics.resolve import _provider_conf
		conf = _provider_conf(vehicle.telematics_provider)
		if not conf:
			debug_info["errors"].append(f"Telematics provider {vehicle.telematics_provider} is not enabled or not found")
			return debug_info
		
		debug_info["provider_enabled"] = True
		debug_info["provider_config"] = {
			"provider_type": conf.get("provider_type"),
			"base_url": conf.get("base_url"),
			"username": conf.get("username")
		}
		
		# Try to get devices and positions
		from logistics.transport.telematics.providers import make_provider
		provider = make_provider(conf["provider_type"], conf)
		
		# Get devices
		if hasattr(provider, 'GetDevices'):
			devices = provider.GetDevices()
			debug_info["available_devices"] = [
				{
					"device_id": dev.get("deviceId") or dev.get("DeviceId"),
					"name": dev.get("name") or dev.get("Name"),
					"raw": dev
				} for dev in devices
			]
		
		# Get positions
		positions = list(provider.fetch_latest_positions())
		debug_info["available_positions"] = [
			{
				"external_id": pos.get("external_id"),
				"device_id": pos.get("device_id"),
				"timestamp": pos.get("timestamp"),
				"latitude": pos.get("latitude"),
				"longitude": pos.get("longitude")
			} for pos in positions
		]
		
		# Check if vehicle external ID matches any available device
		available_device_ids = [str(dev.get("device_id", "")) for dev in debug_info["available_devices"]]
		available_external_ids = [str(pos.get("external_id", "")) for pos in debug_info["available_positions"]]
		
		if str(vehicle.telematics_external_id) not in available_device_ids and str(vehicle.telematics_external_id) not in available_external_ids:
			debug_info["errors"].append(f"Vehicle external ID '{vehicle.telematics_external_id}' not found in available devices or positions")
			debug_info["available_device_ids"] = available_device_ids
			debug_info["available_external_ids"] = available_external_ids
		
		return debug_info
		
	except Exception as e:
		frappe.log_error(f"Debug telematics error: {str(e)}", "Telematics Debug")
		return {
			"vehicle_name": vehicle_name,
			"errors": [str(e)]
		}
