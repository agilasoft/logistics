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
			<div class="devices-table-wrap" style="
				max-height: 380px; overflow-y: auto;
				border: 1px solid var(--border-color, #d1d8dd);
				border-radius: 6px;
				background: var(--bg-color, #fff);
			">
				<table class="devices-table" id="devices-table" style="
					width: 100%; border-collapse: collapse; font-size: 12px;
				">
					<thead>
						<tr style="
							background: var(--table-head-bg, #f0f2f5);
							color: var(--text-color, #262626);
							font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.3px;
						">
							<th style="width: 32px; padding: 8px 10px; text-align: center;">○</th>
							<th style="padding: 8px 10px; text-align: left;">Device</th>
							<th style="padding: 8px 10px; text-align: left; max-width: 140px;">ID</th>
							<th style="padding: 8px 10px; text-align: left; width: 70px;">Provider</th>
						</tr>
					</thead>
					<tbody>
						${data.devices.map((device, index) => `
							<tr class="device-row" data-device-id="${device.device_id}" data-device-name="${device.device_name || ''}" style="
								cursor: pointer;
								border-bottom: 1px solid var(--border-color, #e8e8e8);
								transition: background 0.12s ease;
							" onmouseover="this.style.background='var(--control-bg, #f5f7fa)'" onmouseout="this.style.background='transparent'">
								<td style="padding: 6px 10px; text-align: center; vertical-align: middle;">
									<input type="radio" name="selected_device" value="${index}" id="device_${index}" style="margin: 0;">
								</td>
								<td style="padding: 6px 10px; font-weight: 500;">${device.device_name || 'N/A'}</td>
								<td style="padding: 6px 10px; font-family: monospace; font-size: 11px; color: var(--text-muted, #6c7680); max-width: 140px; overflow: hidden; text-overflow: ellipsis;" title="${device.device_id}">${device.device_id}</td>
								<td style="padding: 6px 10px; font-size: 11px; color: var(--text-muted, #6c7680);">${device.provider}</td>
							</tr>
						`).join('')}
					</tbody>
				</table>
			</div>
			<div style="margin-top: 8px; font-size: 11px; color: var(--text-muted, #6c7680);">${data.total_devices} device${data.total_devices !== 1 ? 's' : ''}</div>
		`;
	} else {
		let provider_errors_html = '';
		if (data.provider_errors && data.provider_errors.length > 0) {
			provider_errors_html = `
				<div class="alert alert-danger" style="margin-top: 10px;">
					<strong>Provider errors:</strong>
					<ul style="margin-bottom: 0;">
						${data.provider_errors.map(pe => `<li><strong>${pe.provider}:</strong> ${(pe.error || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</li>`).join('')}
					</ul>
					<small>See Error Log for full details.</small>
				</div>
			`;
		} else {
			provider_errors_html = `
				<div class="alert alert-secondary" style="margin-top: 10px; font-size: 12px;">
					<strong>Remora users:</strong> Open <b>Error Log</b> and look for <b>Remora GetDevices - empty response structure</b>. Share that entry with support to fix device listing.
				</div>
			`;
		}
		devices_html = `
			<div class="alert alert-warning">
				<strong>No devices found.</strong> Check your telematics provider configuration.
			</div>
			${provider_errors_html}
		`;
	}
	
	let dialog = new frappe.ui.Dialog({
		title: __("View All Devices"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "devices_info",
				options: `
					<div style="padding: 16px 20px;">
						<div style="font-size: 13px; font-weight: 600; margin-bottom: 12px; color: var(--text-color, #333);">Select a device</div>
						${devices_html}
						<div style="margin-top: 14px; padding: 10px 12px; background: var(--control-bg, #f8f9fa); border-radius: 6px; font-size: 11px; color: var(--text-muted, #6c7680);">
							Click a row or the radio, then <strong>Select Device</strong> to set Telematics External ID and Device Name on this vehicle.
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
