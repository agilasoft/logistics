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
				
				# Get devices - use get_device_details() if available for proper namespace handling
				if hasattr(telematics_provider, 'get_device_details'):
					# Use the namespace-aware method
					devices = telematics_provider.get_device_details()
					
					for device in devices:
						all_devices.append({
							"provider": provider.name,
							"provider_type": provider.provider_type,
							"device_id": str(device.get("device_id")) if device.get("device_id") else "N/A",
							"device_name": device.get("name") or "N/A",
							"description": device.get("description"),
							"external_id": device.get("external_id"),
							"registration": device.get("registration"),
							"make": device.get("make"),
							"model": device.get("model"),
							"vin": device.get("vin"),
							"imei": device.get("imei"),
							"serial": device.get("serial"),
							"type": device.get("type"),
							"status": device.get("status"),
							"raw_data": device.get("raw", device)
						})
				elif hasattr(telematics_provider, 'GetDevices'):
					# Fallback: manual extraction with namespace handling
					from logistics.transport.telematics.providers.remora import _get_field
					devices = telematics_provider.GetDevices()
					
					for device in devices:
						device_id = _get_field(device, "deviceId", "DeviceId", "deviceID", "id", "Id", "ID")
						device_name = _get_field(device, "name", "Name", "deviceName", "DeviceName")
						
						all_devices.append({
							"provider": provider.name,
							"provider_type": provider.provider_type,
							"device_id": str(device_id) if device_id else "N/A",
							"device_name": device_name or "N/A",
							"description": _get_field(device, "description", "Description"),
							"external_id": _get_field(device, "externalId", "ExternalId", "externalID"),
							"registration": _get_field(device, "registration", "Registration"),
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
def debug_can_data(vehicle_name):
	"""Debug CAN data specifically for a vehicle"""
	try:
		# Get vehicle document
		vehicle = frappe.get_doc("Transport Vehicle", vehicle_name)
		
		debug_info = {
			"vehicle_name": vehicle.name,
			"telematics_external_id": vehicle.telematics_external_id,
			"telematics_provider": vehicle.telematics_provider,
			"provider_enabled": False,
			"can_data_available": False,
			"can_data_count": 0,
			"can_data_for_vehicle": [],
			"all_can_data": [],
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
		
		# Try to get CAN data
		from logistics.transport.telematics.providers import make_provider
		provider = make_provider(conf["provider_type"], conf)
		
		try:
			frappe.logger().info(f"Debugging CAN data for vehicle {vehicle_name}")
			frappe.logger().info(f"Vehicle external ID: {vehicle.telematics_external_id}")
			frappe.logger().info(f"Provider type: {conf['provider_type']}")
			
			if hasattr(provider, 'fetch_latest_can_data'):
				can_data = list(provider.fetch_latest_can_data())
				debug_info["can_data_count"] = len(can_data)
				debug_info["can_data_available"] = len(can_data) > 0
				
				frappe.logger().info(f"Fetched {len(can_data)} CAN data records")
				
				# Process all CAN data
				debug_info["all_can_data"] = [
					{
						"device_id": can.get("device_id"),
						"timestamp": can.get("timestamp"),
						"fuel_l": can.get("fuel_l"),
						"rpm": can.get("rpm"),
						"engine_hours": can.get("engine_hours"),
						"coolant_c": can.get("coolant_c"),
						"ambient_c": can.get("ambient_c"),
						"raw_keys": list(can.get("raw", {}).keys()) if can.get("raw") else []
					} for can in can_data
				]
				
				# Find CAN data specifically for this vehicle
				vehicle_can_data = []
				for can in can_data:
					can_device_id = can.get("device_id")
					frappe.logger().info(f"Comparing CAN device_id '{can_device_id}' with vehicle external_id '{vehicle.telematics_external_id}'")
					if str(can_device_id) == str(vehicle.telematics_external_id):
						vehicle_can_data.append({
							"device_id": can.get("device_id"),
							"timestamp": can.get("timestamp"),
							"fuel_l": can.get("fuel_l"),
							"rpm": can.get("rpm"),
							"engine_hours": can.get("engine_hours"),
							"coolant_c": can.get("coolant_c"),
							"ambient_c": can.get("ambient_c"),
							"raw": can.get("raw")
						})
				
				debug_info["can_data_for_vehicle"] = vehicle_can_data
				frappe.logger().info(f"Found {len(vehicle_can_data)} CAN data records for vehicle {vehicle_name}")
				
			else:
				debug_info["errors"].append(f"Provider {conf['provider_type']} does not support CAN data fetching")
				frappe.logger().warning(f"Provider {conf['provider_type']} does not have fetch_latest_can_data method")
				
		except Exception as e:
			frappe.logger().error(f"Error fetching CAN data: {str(e)}")
			debug_info["errors"].append(f"Could not fetch CAN data: {str(e)}")
		
		return debug_info
		
	except Exception as e:
		frappe.logger().error(f"Error in debug_can_data: {str(e)}")
		return {
			"error": str(e),
			"vehicle_name": vehicle_name,
			"can_data_available": False,
			"can_data_count": 0,
			"can_data_for_vehicle": [],
			"all_can_data": [],
			"errors": [str(e)]
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
			"available_can_data": [],
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
		
		# Get devices - use get_device_details() if available for proper namespace handling
		if hasattr(provider, 'get_device_details'):
			devices = provider.get_device_details()
			debug_info["available_devices"] = [
				{
					"device_id": dev.get("device_id"),
					"name": dev.get("name"),
					"description": dev.get("description"),
					"external_id": dev.get("external_id"),
					"registration": dev.get("registration"),
					"make": dev.get("make"),
					"model": dev.get("model"),
					"vin": dev.get("vin"),
					"imei": dev.get("imei"),
					"serial": dev.get("serial"),
					"type": dev.get("type"),
					"status": dev.get("status"),
					"raw": dev.get("raw", dev)
				} for dev in devices
			]
		elif hasattr(provider, 'GetDevices'):
			# Fallback with namespace handling
			from logistics.transport.telematics.providers.remora import _get_field
			devices = provider.GetDevices()
			debug_info["available_devices"] = [
				{
					"device_id": _get_field(dev, "deviceId", "DeviceId", "deviceID", "id"),
					"name": _get_field(dev, "name", "Name", "deviceName", "DeviceName"),
					"description": _get_field(dev, "description", "Description"),
					"external_id": _get_field(dev, "externalId", "ExternalId"),
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
				"longitude": pos.get("longitude"),
				"speed_kph": pos.get("speed_kph"),
				"ignition": pos.get("ignition"),
				"odometer_km": pos.get("odometer_km"),
				"fuel_l": pos.get("fuel_l")
			} for pos in positions
		]
		
		# Get CAN data if available
		try:
			frappe.logger().info(f"Attempting to fetch CAN data for vehicle {vehicle_name}")
			
			# Check if provider has the method
			if hasattr(provider, 'fetch_latest_can_data'):
				can_data = list(provider.fetch_latest_can_data())
				frappe.logger().info(f"Fetched {len(can_data)} CAN data records")
				
				debug_info["available_can_data"] = [
					{
						"external_id": can.get("device_id"),  # Use device_id as external_id for CAN data
						"device_id": can.get("device_id"),
						"timestamp": can.get("timestamp"),
						"fuel_l": can.get("fuel_l"),
						"rpm": can.get("rpm"),
						"engine_hours": can.get("engine_hours"),
						"coolant_c": can.get("coolant_c"),
						"ambient_c": can.get("ambient_c"),
						"raw": can.get("raw")
					} for can in can_data
				]
				frappe.logger().info(f"Processed {len(debug_info['available_can_data'])} CAN data records for display")
			else:
				frappe.logger().warning(f"Provider {conf['provider_type']} does not have fetch_latest_can_data method")
				debug_info["errors"].append(f"Provider {conf['provider_type']} does not support CAN data fetching")
				debug_info["available_can_data"] = []
		except Exception as e:
			frappe.logger().error(f"Error fetching CAN data: {str(e)}")
			debug_info["errors"].append(f"Could not fetch CAN data: {str(e)}")
			debug_info["available_can_data"] = []
		
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
