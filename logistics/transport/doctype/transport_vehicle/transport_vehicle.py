# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import datetime as dt


class TransportVehicle(Document):
	@frappe.whitelist()
	def get_latest_position(self):
		"""Fetch the latest position from the telematics provider"""
		if not self.telematics_external_id:
			frappe.throw(_("No telematics external ID configured for this vehicle"))
		
		if not self.telematics_provider:
			# Try to get default provider
			default_provider = frappe.db.get_single_value("Transport Settings", "default_telematics_provider")
			if not default_provider:
				frappe.throw(_("No telematics provider configured for this vehicle and no default provider set"))
			self.telematics_provider = default_provider
		
		try:
			# Get provider configuration
			from logistics.transport.telematics.resolve import _provider_conf
			conf = _provider_conf(self.telematics_provider)
			if not conf:
				frappe.throw(_("Telematics provider {0} is not enabled or not found").format(self.telematics_provider))
			
			# Create provider instance
			from logistics.transport.telematics.providers import make_provider
			provider = make_provider(conf["provider_type"], conf)
			
			# Fetch latest positions
			positions = list(provider.fetch_latest_positions())
			
			# Debug: Log available positions and external IDs
			frappe.logger().info(f"Fetched {len(positions)} positions from provider")
			available_external_ids = [str(pos.get("external_id", pos.get("device_id", ""))) for pos in positions]
			frappe.logger().info(f"Available external IDs: {available_external_ids}")
			frappe.logger().info(f"Looking for vehicle external ID: {self.telematics_external_id}")
			
			# Find position for this vehicle - try multiple field mappings
			vehicle_position = None
			for pos in positions:
				# Try different field names for external ID
				pos_external_id = pos.get("external_id") or pos.get("device_id") or pos.get("DeviceId")
				if str(pos_external_id) == str(self.telematics_external_id):
					vehicle_position = pos
					break
			
			if not vehicle_position:
				# Try to get more specific position data using GetPositionsByInterval
				try:
					from datetime import datetime, timedelta
					now = datetime.now()
					yesterday = now - timedelta(days=1)
					
					# Try to get positions for this specific device
					if hasattr(provider, 'GetPositionsByInterval'):
						device_positions = provider.GetPositionsByInterval(
							self.telematics_external_id, 
							yesterday, 
							now
						)
						if device_positions:
							# Use the most recent position
							vehicle_position = device_positions[-1] if device_positions else None
							frappe.logger().info(f"Found {len(device_positions)} positions using GetPositionsByInterval")
				except Exception as e:
					frappe.logger().error(f"Error fetching positions by interval: {str(e)}")
			
			if not vehicle_position:
				error_msg = f"No recent position data found for vehicle {self.name} (External ID: {self.telematics_external_id}). Available external IDs: {available_external_ids}"
				frappe.logger().error(error_msg)
				frappe.msgprint(_(error_msg))
				return
			
			# Update vehicle with latest position data
			self.last_telematics_ts = vehicle_position.get("timestamp")
			self.last_telematics_lat = vehicle_position.get("latitude")
			self.last_telematics_lon = vehicle_position.get("longitude")
			self.last_speed_kph = vehicle_position.get("speed_kph")
			self.last_ignition_on = bool(vehicle_position.get("ignition"))
			self.last_odometer_km = vehicle_position.get("odometer_km")
			self.last_provider = self.telematics_provider
			
			# Save the document
			self.save()
			
			frappe.msgprint(_("Latest position updated successfully!"), alert=True)
			
			# Return position data for display
			return {
				"timestamp": self.last_telematics_ts,
				"latitude": self.last_telematics_lat,
				"longitude": self.last_telematics_lon,
				"speed_kph": self.last_speed_kph,
				"ignition": self.last_ignition_on,
				"odometer_km": self.last_odometer_km
			}
			
		except Exception as e:
			frappe.log_error(f"Error fetching latest position for vehicle {self.name}: {str(e)}", "Transport Vehicle Position Fetch")
			frappe.throw(_("Failed to fetch latest position: {0}").format(str(e)))

	@frappe.whitelist()
	def debug_telematics_connection(self):
		"""Debug method to check telematics connection and available data with API response details"""
		debug_info = {
			"vehicle_name": self.name,
			"telematics_external_id": self.telematics_external_id,
			"telematics_provider": self.telematics_provider,
			"provider_enabled": False,
			"available_devices": [],
			"available_positions": [],
			"api_responses": {
				"version_info": None,
				"devices_response": None,
				"positions_response": None,
				"vehicle_positions_response": None
			},
			"debug_info": {
				"debug_mode_enabled": True,
				"timeout_seconds": 30,
				"provider_type": None
			},
			"errors": []
		}
		
		try:
			# Check provider configuration
			from logistics.transport.telematics.resolve import _provider_conf
			conf = _provider_conf(self.telematics_provider)
			if conf:
				debug_info["provider_enabled"] = True
				debug_info["provider_config"] = {
					"provider_type": conf.get("provider_type"),
					"base_url": conf.get("base_url"),
					"username": conf.get("username"),
					"soap_endpoint": conf.get("soap_endpoint_override")
				}
				debug_info["debug_info"]["provider_type"] = conf.get("provider_type")
				
				# Enable debug mode to capture API responses
				conf["debug"] = 1
				conf["request_timeout_sec"] = 30
				
				# Try to get devices with debug mode
				from logistics.transport.telematics.providers import make_provider
				provider = make_provider(conf["provider_type"], conf)
				
				# Test 1: Get Version Info
				try:
					if hasattr(provider, 'GetVersionInfo'):
						version_info = provider.GetVersionInfo()
						debug_info["api_responses"]["version_info"] = {
							"success": True,
							"data": version_info,
							"raw_response": version_info  # Show the actual API response
						}
				except Exception as e:
					debug_info["api_responses"]["version_info"] = {
						"success": False,
						"error": str(e),
						"error_type": type(e).__name__,
						"raw_response": None
					}
				
				# Test 2: Get Devices
				try:
					if hasattr(provider, 'GetDevices'):
						devices = provider.GetDevices()
						debug_info["available_devices"] = [
							{
								"device_id": dev.get("deviceId") or dev.get("DeviceId"),
								"name": dev.get("name") or dev.get("Name"),
								"raw": dev
							} for dev in devices
						]
						debug_info["api_responses"]["devices_response"] = {
							"success": True,
							"count": len(devices),
							"data": devices[:5] if len(devices) > 5 else devices,  # Limit to first 5 for display
							"raw_response": devices  # Show the actual API response
						}
				except Exception as e:
					debug_info["api_responses"]["devices_response"] = {
						"success": False,
						"error": str(e),
						"error_type": type(e).__name__,
						"raw_response": None
					}
				
				# Test 3: Get Positions
				try:
					positions = list(provider.fetch_latest_positions())
					debug_info["available_positions"] = [
						{
							"external_id": pos.get("external_id"),
							"device_id": pos.get("device_id"),
							"timestamp": pos.get("timestamp"),
							"latitude": pos.get("latitude"),
							"longitude": pos.get("longitude"),
							"speed_kph": pos.get("speed_kph"),
							"heading_deg": pos.get("heading_deg"),
							"ignition": pos.get("ignition")
						} for pos in positions
					]
					debug_info["api_responses"]["positions_response"] = {
						"success": True,
						"count": len(positions),
						"data": positions[:5] if len(positions) > 5 else positions,  # Limit to first 5 for display
						"raw_response": positions  # Show the actual API response
					}
				except Exception as e:
					debug_info["api_responses"]["positions_response"] = {
						"success": False,
						"error": str(e),
						"error_type": type(e).__name__,
						"raw_response": None
					}
				
				# Test 4: Get Positions for this specific vehicle
				if self.telematics_external_id:
					try:
						from datetime import datetime, timedelta
						end_time = datetime.now()
						start_time = end_time - timedelta(days=1)
						
						if hasattr(provider, 'GetPositionsByInterval'):
							vehicle_positions = provider.GetPositionsByInterval(
								self.telematics_external_id, 
								start_time, 
								end_time
							)
							debug_info["api_responses"]["vehicle_positions_response"] = {
								"success": True,
								"count": len(vehicle_positions),
								"vehicle_id": self.telematics_external_id,
								"time_range": f"{start_time} to {end_time}",
								"data": vehicle_positions[:5] if len(vehicle_positions) > 5 else vehicle_positions,
								"raw_response": vehicle_positions  # Show the actual API response
							}
					except Exception as e:
						debug_info["api_responses"]["vehicle_positions_response"] = {
							"success": False,
							"error": str(e),
							"error_type": type(e).__name__,
							"raw_response": None
						}
				
				
		except Exception as e:
			debug_info["errors"].append(str(e))
			frappe.log_error(f"Debug telematics connection error: {str(e)}", "Transport Vehicle Debug")
		
		return debug_info
