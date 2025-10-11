// Copyright (c) 2025, www.agilasoft.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Transport Vehicle", {
	refresh(frm) {
		// Add button to fetch latest position
		if (frm.doc.telematics_external_id) {
			frm.add_custom_button(__("Get Latest Position"), function() {
				frm.call({
					method: "get_latest_position",
					doc: frm.doc,
					callback: function(r) {
						if (r.message) {
							// Show position details in a dialog
							show_position_details(r.message);
						}
						frm.reload_doc();
					},
					freeze: true,
					freeze_message: __("Fetching latest position...")
				});
			}, __("Telematics"));
		}
		
		// Add button to view position on map if coordinates are available
		if (frm.doc.last_telematics_lat && frm.doc.last_telematics_lon) {
			frm.add_custom_button(__("View on Map"), function() {
				open_map(frm.doc.last_telematics_lat, frm.doc.last_telematics_lon);
			}, __("Telematics"));
		}
		
		// Add debug button for troubleshooting
		if (frm.doc.telematics_external_id) {
			frm.add_custom_button(__("Debug Telematics"), function() {
				// Try the class method first, fallback to direct API call
				frm.call({
					method: "debug_telematics_connection",
					doc: frm.doc,
					callback: function(r) {
						if (r.message) {
							show_debug_info(r.message);
						}
					},
					error: function(r) {
						// Fallback: try API endpoint
						frappe.call({
							method: "logistics.transport.api_telematics_debug.debug_vehicle_telematics",
							args: {
								vehicle_name: frm.doc.name
							},
							callback: function(api_r) {
								if (api_r.message) {
									show_debug_info(api_r.message);
								} else {
									show_basic_debug_info(frm.doc);
								}
							},
							error: function() {
								show_basic_debug_info(frm.doc);
							}
						});
					},
					freeze: true,
					freeze_message: __("Debugging telematics connection...")
				});
			}, __("Telematics"));
		}
		
		// Add button to fetch CAN data specifically
		if (frm.doc.telematics_external_id) {
			frm.add_custom_button(__("Get CAN Data"), function() {
				frm.call({
					method: "get_can_data",
					doc: frm.doc,
					callback: function(r) {
						if (r.message) {
							// Show CAN data details in a dialog
							show_can_data_details(r.message);
						}
						frm.reload_doc();
					},
					freeze: true,
					freeze_message: __("Fetching CAN data...")
				});
			}, __("Telematics"));
		}
		
		// Add button to get all device IDs
		frm.add_custom_button(__("Get All Device IDs"), function() {
			frappe.call({
				method: "logistics.transport.api_telematics_debug.get_all_device_ids",
				callback: function(r) {
					if (r.message) {
						show_all_devices(r.message);
					}
				},
				freeze: true,
				freeze_message: __("Retrieving all device IDs...")
			});
		}, __("Telematics"));
		
		// Add button to debug CAN data specifically
		if (frm.doc.telematics_external_id) {
			frm.add_custom_button(__("Debug CAN Data"), function() {
				frappe.call({
					method: "logistics.transport.api_telematics_debug.debug_can_data",
					args: {
						vehicle_name: frm.doc.name
					},
					callback: function(r) {
						if (r.message) {
							show_can_debug_info(r.message);
						}
					},
					freeze: true,
					freeze_message: __("Debugging CAN data...")
				});
			}, __("Telematics"));
		}
	}
});

// Function to show CAN data details in a dialog
function show_can_data_details(can_data) {
	let content = `
		<div style="padding: 20px;">
			<h4>CAN Data Details</h4>
			<table class="table table-bordered">
				<tr><td><strong>Timestamp:</strong></td><td>${can_data.timestamp || 'N/A'}</td></tr>
				<tr><td><strong>Fuel Level:</strong></td><td>${can_data.fuel_level || 'N/A'}%</td></tr>
				<tr><td><strong>RPM:</strong></td><td>${can_data.rpm || 'N/A'}</td></tr>
				<tr><td><strong>Engine Hours:</strong></td><td>${can_data.engine_hours || 'N/A'}</td></tr>
				<tr><td><strong>Coolant Temperature:</strong></td><td>${can_data.coolant_temp || 'N/A'}°C</td></tr>
				<tr><td><strong>Ambient Temperature:</strong></td><td>${can_data.ambient_temp || 'N/A'}°C</td></tr>
			</table>
		</div>
	`;
	
	let d = new frappe.ui.Dialog({
		title: 'CAN Data Results',
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'can_data_content',
				options: content
			}
		],
		primary_action_label: 'Close',
		primary_action: function() {
			d.hide();
		}
	});
	
	d.show();
}

function show_position_details(position_data) {
	let dialog = new frappe.ui.Dialog({
		title: __("Latest Position Details"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "position_info",
				options: `
					<div style="padding: 20px;">
						<h4>Position Information</h4>
						<table class="table table-bordered">
							<tr>
								<td><strong>Timestamp:</strong></td>
								<td>${position_data.timestamp || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Latitude:</strong></td>
								<td>${position_data.latitude || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Longitude:</strong></td>
								<td>${position_data.longitude || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Speed:</strong></td>
								<td>${position_data.speed_kph || 'N/A'} km/h</td>
							</tr>
							<tr>
								<td><strong>Ignition:</strong></td>
								<td>${position_data.ignition ? 'On' : 'Off'}</td>
							</tr>
							<tr>
								<td><strong>Odometer:</strong></td>
								<td>${position_data.odometer_km || 'N/A'} km</td>
							</tr>
						</table>
						${position_data.latitude && position_data.longitude ? 
							`<button class="btn btn-primary" onclick="open_map(${position_data.latitude}, ${position_data.longitude})">View on Map</button>` 
							: ''
						}
					</div>
				`
			}
		]
	});
	
	dialog.show();
}

function show_debug_info(debug_data) {
	let devices_html = '';
	if (debug_data.available_devices && debug_data.available_devices.length > 0) {
		devices_html = `
			<h5>Available Devices:</h5>
			<table class="table table-bordered">
				<thead>
					<tr><th>Device ID</th><th>Name</th></tr>
				</thead>
				<tbody>
					${debug_data.available_devices.map(dev => `
						<tr>
							<td>${dev.device_id || 'N/A'}</td>
							<td>${dev.name || 'N/A'}</td>
						</tr>
					`).join('')}
				</tbody>
			</table>
		`;
	}
	
	let positions_html = '';
	if (debug_data.available_positions && debug_data.available_positions.length > 0) {
		positions_html = `
			<h5>Available Positions:</h5>
			<table class="table table-bordered">
				<thead>
					<tr><th>External ID</th><th>Device ID</th><th>Timestamp</th><th>Lat/Lon</th><th>Speed</th><th>Ignition</th><th>Odometer</th><th>Fuel</th></tr>
				</thead>
				<tbody>
					${debug_data.available_positions.map(pos => `
						<tr>
							<td>${pos.external_id || 'N/A'}</td>
							<td>${pos.device_id || 'N/A'}</td>
							<td>${pos.timestamp || 'N/A'}</td>
							<td>${pos.latitude || 'N/A'}, ${pos.longitude || 'N/A'}</td>
							<td>${pos.speed_kph || 'N/A'} km/h</td>
							<td>${pos.ignition || 'N/A'}</td>
							<td>${pos.odometer_km || 'N/A'} km</td>
							<td>${pos.fuel_l || 'N/A'}</td>
						</tr>
					`).join('')}
				</tbody>
			</table>
		`;
	}
	
	let can_data_html = '';
	if (debug_data.available_can_data && debug_data.available_can_data.length > 0) {
		can_data_html = `
			<h5>Available CAN Data:</h5>
			<table class="table table-bordered">
				<thead>
					<tr><th>External ID</th><th>Device ID</th><th>Timestamp</th><th>Fuel Level</th><th>RPM</th><th>Engine Hours</th><th>Coolant Temp</th><th>Ambient Temp</th></tr>
				</thead>
				<tbody>
					${debug_data.available_can_data.map(can => `
						<tr>
							<td>${can.external_id || 'N/A'}</td>
							<td>${can.device_id || 'N/A'}</td>
							<td>${can.timestamp || 'N/A'}</td>
							<td>${can.fuel_l || 'N/A'}</td>
							<td>${can.rpm || 'N/A'}</td>
							<td>${can.engine_hours || 'N/A'}</td>
							<td>${can.coolant_c || 'N/A'}°C</td>
							<td>${can.ambient_c || 'N/A'}°C</td>
						</tr>
					`).join('')}
				</tbody>
			</table>
		`;
	}
	
	// API Response Details
	let api_responses_html = '';
	if (debug_data.api_responses) {
		api_responses_html = `
			<h5>API Response Details:</h5>
			<div class="panel-group" id="api-responses">
		`;
		
		// Version Info
		if (debug_data.api_responses.version_info) {
			const version = debug_data.api_responses.version_info;
			api_responses_html += `
				<div class="panel panel-default">
					<div class="panel-heading">
						<h6 class="panel-title">
							<a data-toggle="collapse" href="#version-info">
								Version Info ${version.success ? '✅' : '❌'}
							</a>
						</h6>
					</div>
					<div id="version-info" class="panel-collapse collapse">
						<div class="panel-body">
							${version.success ? `
								<h6>Raw API Response:</h6>
								<pre style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(version.raw_response || version.data || version, null, 2)}</pre>
							` : `
								<h6>API Error:</h6>
								<div class="alert alert-danger">
									<strong>Error Type:</strong> ${version.error_type || 'Unknown'}<br>
									<strong>Error Message:</strong> ${version.error || 'No error message available'}
								</div>
								<h6>Raw Error Response:</h6>
								<pre style="max-height: 200px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(version, null, 2)}</pre>
							`}
						</div>
					</div>
				</div>
			`;
		}
		
		// Devices Response
		if (debug_data.api_responses.devices_response) {
			const devices = debug_data.api_responses.devices_response;
			api_responses_html += `
				<div class="panel panel-default">
					<div class="panel-heading">
						<h6 class="panel-title">
							<a data-toggle="collapse" href="#devices-response">
								Devices Response ${devices.success ? '✅' : '❌'} (${devices.count || 0} devices)
							</a>
						</h6>
					</div>
					<div id="devices-response" class="panel-collapse collapse">
						<div class="panel-body">
							${devices.success ? `
								<h6>Raw API Response (${devices.count || 0} devices):</h6>
								<pre style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(devices.raw_response || devices.data || devices, null, 2)}</pre>
							` : `
								<h6>API Error:</h6>
								<div class="alert alert-danger">
									<strong>Error Type:</strong> ${devices.error_type || 'Unknown'}<br>
									<strong>Error Message:</strong> ${devices.error || 'No error message available'}
								</div>
								<h6>Raw Error Response:</h6>
								<pre style="max-height: 200px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(devices, null, 2)}</pre>
							`}
						</div>
					</div>
				</div>
			`;
		}
		
		// Positions Response
		if (debug_data.api_responses.positions_response) {
			const positions = debug_data.api_responses.positions_response;
			api_responses_html += `
				<div class="panel panel-default">
					<div class="panel-heading">
						<h6 class="panel-title">
							<a data-toggle="collapse" href="#positions-response">
								Positions Response ${positions.success ? '✅' : '❌'} (${positions.count || 0} positions)
							</a>
						</h6>
					</div>
					<div id="positions-response" class="panel-collapse collapse">
						<div class="panel-body">
							${positions.success ? `
								<h6>Raw API Response (${positions.count || 0} positions):</h6>
								<pre style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(positions.raw_response || positions.data || positions, null, 2)}</pre>
							` : `
								<h6>API Error:</h6>
								<div class="alert alert-danger">
									<strong>Error Type:</strong> ${positions.error_type || 'Unknown'}<br>
									<strong>Error Message:</strong> ${positions.error || 'No error message available'}
								</div>
								<h6>Raw Error Response:</h6>
								<pre style="max-height: 200px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(positions, null, 2)}</pre>
							`}
						</div>
					</div>
				</div>
			`;
		}
		
		// CAN Data Response
		if (debug_data.api_responses.can_data_response) {
			const can_data = debug_data.api_responses.can_data_response;
			api_responses_html += `
				<div class="panel panel-default">
					<div class="panel-heading">
						<h6 class="panel-title">
							<a data-toggle="collapse" href="#can-data-response">
								CAN Data Response ${can_data.success ? '✅' : '❌'} (${can_data.count || 0} CAN records)
							</a>
						</h6>
					</div>
					<div id="can-data-response" class="panel-collapse collapse">
						<div class="panel-body">
							${can_data.success ? `
								<h6>Raw API Response (${can_data.count || 0} CAN records):</h6>
								<pre style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(can_data.raw_response || can_data.data || can_data, null, 2)}</pre>
							` : `
								<h6>API Error:</h6>
								<div class="alert alert-danger">
									<strong>Error Type:</strong> ${can_data.error_type || 'Unknown'}<br>
									<strong>Error Message:</strong> ${can_data.error || 'No error message available'}
								</div>
								<h6>Raw Error Response:</h6>
								<pre style="max-height: 200px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(can_data, null, 2)}</pre>
							`}
						</div>
					</div>
				</div>
			`;
		}
		
		// Vehicle Positions Response
		if (debug_data.api_responses.vehicle_positions_response) {
			const vehicle_positions = debug_data.api_responses.vehicle_positions_response;
			api_responses_html += `
				<div class="panel panel-default">
					<div class="panel-heading">
						<h6 class="panel-title">
							<a data-toggle="collapse" href="#vehicle-positions-response">
								Vehicle Positions Response ${vehicle_positions.success ? '✅' : '❌'} (${vehicle_positions.count || 0} positions)
							</a>
						</h6>
					</div>
					<div id="vehicle-positions-response" class="panel-collapse collapse">
						<div class="panel-body">
							${vehicle_positions.success ? `
								<h6>Raw API Response (${vehicle_positions.count || 0} positions for vehicle ${vehicle_positions.vehicle_id || 'N/A'}):</h6>
								<pre style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(vehicle_positions.raw_response || vehicle_positions.data || vehicle_positions, null, 2)}</pre>
							` : `
								<h6>API Error:</h6>
								<div class="alert alert-danger">
									<strong>Error Type:</strong> ${vehicle_positions.error_type || 'Unknown'}<br>
									<strong>Error Message:</strong> ${vehicle_positions.error || 'No error message available'}
								</div>
								<h6>Raw Error Response:</h6>
								<pre style="max-height: 200px; overflow-y: auto; background: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; font-size: 12px;">${JSON.stringify(vehicle_positions, null, 2)}</pre>
							`}
						</div>
					</div>
				</div>
			`;
		}
		
		
		api_responses_html += `</div>`;
		
		// Add a dedicated Raw API Responses section
		if (debug_data.api_responses) {
			api_responses_html += `
				<h5>Raw API Responses Summary:</h5>
				<div class="alert alert-info">
					<strong>Complete API Response Data:</strong> The sections above show the raw, unprocessed data returned by the Remora API. 
					This includes all fields, values, and structure exactly as received from the telematics provider.
				</div>
			`;
		}
	}
	
	let errors_html = '';
	if (debug_data.errors && debug_data.errors.length > 0) {
		errors_html = `
			<h5>Errors:</h5>
			<div class="alert alert-danger">
				${debug_data.errors.map(error => `<div>${error}</div>`).join('')}
			</div>
		`;
	}
	
	let dialog = new frappe.ui.Dialog({
		title: __("Telematics Debug Information"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "debug_info",
				options: `
					<div style="padding: 20px;">
						<h4>Debug Information</h4>
						<table class="table table-bordered">
							<tr>
								<td><strong>Vehicle:</strong></td>
								<td>${debug_data.vehicle_name || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>External ID:</strong></td>
								<td>${debug_data.telematics_external_id || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Provider:</strong></td>
								<td>${debug_data.telematics_provider || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Provider Enabled:</strong></td>
								<td>${debug_data.provider_enabled ? 'Yes' : 'No'}</td>
							</tr>
						${debug_data.provider_config ? `
						<tr>
							<td><strong>Provider Type:</strong></td>
							<td>${debug_data.provider_config.provider_type || 'N/A'}</td>
						</tr>
						<tr>
							<td><strong>SOAP Endpoint:</strong></td>
							<td>${debug_data.provider_config.soap_endpoint || 'Default'}</td>
						</tr>
						` : ''}
						${debug_data.debug_info ? `
						<tr>
							<td><strong>Debug Mode:</strong></td>
							<td>${debug_data.debug_info.debug_mode_enabled ? 'Enabled' : 'Disabled'}</td>
						</tr>
						<tr>
							<td><strong>Timeout:</strong></td>
							<td>${debug_data.debug_info.timeout_seconds || 30} seconds</td>
						</tr>
						` : ''}
						</table>
						
						${devices_html}
						${positions_html}
						${can_data_html}
						${api_responses_html}
						${errors_html}
						
						<div class="alert alert-info">
							<strong>Note:</strong> Make sure the External ID matches one of the available Device IDs above.
							Click on the API Response sections above to see detailed response data.
						</div>
					</div>
				`
			}
		]
	});
	
	dialog.show();
}

function show_basic_debug_info(doc) {
	let dialog = new frappe.ui.Dialog({
		title: __("Basic Telematics Debug Information"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "basic_debug_info",
				options: `
					<div style="padding: 20px;">
						<h4>Vehicle Configuration</h4>
						<table class="table table-bordered">
							<tr>
								<td><strong>Vehicle:</strong></td>
								<td>${doc.name || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>External ID:</strong></td>
								<td>${doc.telematics_external_id || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Provider:</strong></td>
								<td>${doc.telematics_provider || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Last Position:</strong></td>
								<td>${doc.last_telematics_lat || 'N/A'}, ${doc.last_telematics_lon || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Last Update:</strong></td>
								<td>${doc.last_telematics_ts || 'N/A'}</td>
							</tr>
						</table>
						
						<div class="alert alert-warning">
							<strong>Note:</strong> The debug method is not available. Please check:
							<ol>
								<li>Make sure the server has been restarted after code changes</li>
								<li>Check if the telematics provider is properly configured</li>
								<li>Verify the external ID matches a device in your telematics system</li>
							</ol>
						</div>
					</div>
				`
			}
		]
	});
	
	dialog.show();
}

function show_all_devices(data) {
	let devices_html = '';
	
	if (data.error) {
		devices_html = `
			<div class="alert alert-danger">
				<strong>Error:</strong> ${data.error}
			</div>
		`;
	} else if (data.devices && data.devices.length > 0) {
		devices_html = `
			<h5>Available Devices (${data.total_devices}):</h5>
			<table class="table table-bordered table-striped">
				<thead>
					<tr>
						<th>Device ID</th>
						<th>Device Name</th>
						<th>Provider</th>
						<th>Provider Type</th>
					</tr>
				</thead>
				<tbody>
					${data.devices.map(device => `
						<tr>
							<td><strong>${device.device_id}</strong></td>
							<td>${device.device_name}</td>
							<td>${device.provider}</td>
							<td>${device.provider_type}</td>
						</tr>
					`).join('')}
				</tbody>
			</table>
		`;
	} else {
		devices_html = `
			<div class="alert alert-warning">
				<strong>No devices found.</strong> Check your telematics provider configuration.
			</div>
		`;
	}
	
	let dialog = new frappe.ui.Dialog({
		title: __("All Available Device IDs"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "devices_info",
				options: `
					<div style="padding: 20px;">
						<h4>Telematics Device IDs</h4>
						${devices_html}
						
						<div class="alert alert-info">
							<strong>Instructions:</strong>
							<ol>
								<li>Copy the Device ID you want to use</li>
								<li>Update your vehicle's "Telematics External ID" field with this Device ID</li>
								<li>Make sure the Provider matches your vehicle's telematics provider</li>
							</ol>
						</div>
					</div>
				`
			}
		]
	});
	
	dialog.show();
}

function show_can_debug_info(debug_data) {
	let can_data_html = '';
	
	if (debug_data.can_data_for_vehicle && debug_data.can_data_for_vehicle.length > 0) {
		can_data_html = `
			<h5>CAN Data for This Vehicle (${debug_data.can_data_for_vehicle.length} records):</h5>
			<table class="table table-bordered table-striped">
				<thead>
					<tr>
						<th>Device ID</th>
						<th>Timestamp</th>
						<th>Fuel Level</th>
						<th>RPM</th>
						<th>Engine Hours</th>
						<th>Coolant Temp</th>
						<th>Ambient Temp</th>
					</tr>
				</thead>
				<tbody>
					${debug_data.can_data_for_vehicle.map(can => `
						<tr>
							<td><strong>${can.device_id}</strong></td>
							<td>${can.timestamp || 'N/A'}</td>
							<td>${can.fuel_l !== null && can.fuel_l !== undefined ? can.fuel_l : 'N/A'}</td>
							<td>${can.rpm !== null && can.rpm !== undefined ? can.rpm : 'N/A'}</td>
							<td>${can.engine_hours !== null && can.engine_hours !== undefined ? can.engine_hours : 'N/A'}</td>
							<td>${can.coolant_c !== null && can.coolant_c !== undefined ? can.coolant_c + '°C' : 'N/A'}</td>
							<td>${can.ambient_c !== null && can.ambient_c !== undefined ? can.ambient_c + '°C' : 'N/A'}</td>
						</tr>
					`).join('')}
				</tbody>
			</table>
		`;
	} else {
		can_data_html = `
			<div class="alert alert-warning">
				<strong>No CAN data found for this vehicle.</strong>
				<p>This could mean:</p>
				<ul>
					<li>The device ID doesn't match any CAN data records</li>
					<li>No CAN data is available from the telematics provider</li>
					<li>The device doesn't support CAN data transmission</li>
				</ul>
			</div>
		`;
	}
	
	let all_can_data_html = '';
	if (debug_data.all_can_data && debug_data.all_can_data.length > 0) {
		all_can_data_html = `
			<h5>All Available CAN Data (${debug_data.all_can_data.length} total records):</h5>
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>Device ID</th>
						<th>Timestamp</th>
						<th>Fuel Level</th>
						<th>RPM</th>
						<th>Engine Hours</th>
						<th>Raw Keys</th>
					</tr>
				</thead>
				<tbody>
					${debug_data.all_can_data.map(can => `
						<tr>
							<td>${can.device_id}</td>
							<td>${can.timestamp || 'N/A'}</td>
							<td>${can.fuel_l !== null && can.fuel_l !== undefined ? can.fuel_l : 'N/A'}</td>
							<td>${can.rpm !== null && can.rpm !== undefined ? can.rpm : 'N/A'}</td>
							<td>${can.engine_hours !== null && can.engine_hours !== undefined ? can.engine_hours : 'N/A'}</td>
							<td>${can.raw_keys ? can.raw_keys.join(', ') : 'N/A'}</td>
						</tr>
					`).join('')}
				</tbody>
			</table>
		`;
	}
	
	let errors_html = '';
	if (debug_data.errors && debug_data.errors.length > 0) {
		errors_html = `
			<h5>Errors:</h5>
			<div class="alert alert-danger">
				${debug_data.errors.map(error => `<div>${error}</div>`).join('')}
			</div>
		`;
	}
	
	let dialog = new frappe.ui.Dialog({
		title: __("CAN Data Debug Information"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "can_debug_info",
				options: `
					<div style="padding: 20px;">
						<h4>CAN Data Debug Information</h4>
						<table class="table table-bordered">
							<tr>
								<td><strong>Vehicle:</strong></td>
								<td>${debug_data.vehicle_name || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>External ID:</strong></td>
								<td>${debug_data.telematics_external_id || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Provider:</strong></td>
								<td>${debug_data.telematics_provider || 'N/A'}</td>
							</tr>
							<tr>
								<td><strong>Provider Enabled:</strong></td>
								<td>${debug_data.provider_enabled ? 'Yes' : 'No'}</td>
							</tr>
							<tr>
								<td><strong>CAN Data Available:</strong></td>
								<td>${debug_data.can_data_available ? 'Yes' : 'No'}</td>
							</tr>
							<tr>
								<td><strong>Total CAN Records:</strong></td>
								<td>${debug_data.can_data_count || 0}</td>
							</tr>
							<tr>
								<td><strong>Records for This Vehicle:</strong></td>
								<td>${debug_data.can_data_for_vehicle ? debug_data.can_data_for_vehicle.length : 0}</td>
							</tr>
						</table>
						
						${can_data_html}
						${all_can_data_html}
						${errors_html}
						
						<div class="alert alert-info">
							<strong>Debug Information:</strong> This shows CAN data specifically for debugging purposes.
							Make sure the External ID matches one of the Device IDs in the "All Available CAN Data" table above.
						</div>
					</div>
				`
			}
		]
	});
	
	dialog.show();
}

function open_map(lat, lon) {
	if (lat && lon) {
		const map_url = `https://www.google.com/maps?q=${lat},${lon}`;
		window.open(map_url, '_blank');
	} else {
		frappe.msgprint(__("No valid coordinates available"));
	}
}
