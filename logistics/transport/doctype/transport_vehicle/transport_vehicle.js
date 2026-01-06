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
		
		// Add button to view all devices with selection capability
		frm.add_custom_button(__("View All Devices"), function() {
			frappe.call({
				method: "logistics.transport.api_telematics_debug.get_all_device_ids",
				callback: function(r) {
					if (r.message) {
						show_all_devices(r.message, frm);
					}
				},
				freeze: true,
				freeze_message: __("Retrieving all devices...")
			});
		}, __("Telematics"));
		
		// Add button to fetch Device ID using Device Name
		if (frm.doc.telematics_device_name && frm.doc.telematics_provider) {
			frm.add_custom_button(__("Fetch Device ID"), function() {
				frm.call({
					method: "fetch_device_id",
					doc: frm.doc,
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.msgprint({
								title: __("Success"),
								message: __("Device ID '{0}' has been fetched and updated in Telematics External ID field.", [r.message.device_id]),
								indicator: "green"
							});
							frm.reload_doc();
						}
					},
					freeze: true,
					freeze_message: __("Fetching Device ID...")
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


function show_all_devices(data, frm) {
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
			<div style="max-height: 400px; overflow-y: auto;">
				<table class="table table-bordered table-striped" id="devices-table">
					<thead>
						<tr>
							<th style="width: 50px;">Select</th>
							<th>Device ID</th>
							<th>Device Name</th>
							<th>Provider</th>
							<th>Provider Type</th>
						</tr>
					</thead>
					<tbody>
						${data.devices.map((device, index) => `
							<tr class="device-row" data-device-id="${device.device_id}" data-device-name="${device.device_name || ''}" style="cursor: pointer;">
								<td style="text-align: center;">
									<input type="radio" name="selected_device" value="${index}" id="device_${index}">
								</td>
								<td><strong>${device.device_id}</strong></td>
								<td>${device.device_name || 'N/A'}</td>
								<td>${device.provider}</td>
								<td>${device.provider_type}</td>
							</tr>
						`).join('')}
					</tbody>
				</table>
			</div>
		`;
	} else {
		devices_html = `
			<div class="alert alert-warning">
				<strong>No devices found.</strong> Check your telematics provider configuration.
			</div>
		`;
	}
	
	let dialog = new frappe.ui.Dialog({
		title: __("View All Devices"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "devices_info",
				options: `
					<div style="padding: 20px;">
						<h4>Select a Device</h4>
						${devices_html}
						
						<div class="alert alert-info">
							<strong>Instructions:</strong>
							<ol>
								<li>Click on a device row or select the radio button to choose a device</li>
								<li>Click "Select Device" to update the Transport Vehicle record</li>
								<li>The Device ID will be set in "Telematics External ID" field</li>
								<li>The Device Name will be set in "Telematics Device Name" field</li>
							</ol>
						</div>
					</div>
				`
			}
		],
		primary_action_label: __("Select Device"),
		primary_action: function() {
			let selected_radio = document.querySelector('input[name="selected_device"]:checked');
			if (!selected_radio) {
				frappe.msgprint({
					title: __("No Selection"),
					message: __("Please select a device first."),
					indicator: "orange"
				});
				return;
			}
			
			let selected_row = selected_radio.closest('.device-row');
			let device_id = selected_row.getAttribute('data-device-id');
			let device_name = selected_row.getAttribute('data-device-name') || '';
			
			// Update the form fields
			frm.set_value('telematics_external_id', device_id);
			frm.set_value('telematics_device_name', device_name);
			
			dialog.hide();
			
			frappe.msgprint({
				title: __("Success"),
				message: __("Device selected successfully!<br>Device ID: <strong>{0}</strong><br>Device Name: <strong>{1}</strong>", [device_id, device_name || 'N/A']),
				indicator: "green"
			});
		}
	});
	
	// Add click handler to rows for easier selection
	setTimeout(function() {
		let rows = dialog.$wrapper.find('.device-row');
		rows.on('click', function(e) {
			// Don't trigger if clicking on the radio button itself
			if (e.target.type !== 'radio') {
				let radio = $(this).find('input[type="radio"]');
				radio.prop('checked', true);
				// Add visual feedback
				rows.removeClass('table-info');
				$(this).addClass('table-info');
			}
		});
		
		// Add hover effect
		rows.on('mouseenter', function() {
			$(this).addClass('table-hover');
		}).on('mouseleave', function() {
			$(this).removeClass('table-hover');
		});
		
		// Handle radio button change
		dialog.$wrapper.find('input[name="selected_device"]').on('change', function() {
			rows.removeClass('table-info');
			$(this).closest('.device-row').addClass('table-info');
		});
	}, 100);
	
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
