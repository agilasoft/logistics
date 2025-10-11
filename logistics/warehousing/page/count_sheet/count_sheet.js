frappe.pages['count-sheet'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Count Sheet',
		single_column: true
	});

	// Create the warehouse counting interface
	create_counting_interface(page);
}

function create_counting_interface(page) {
	// Main container
	let main_container = $(`
		<div class="count-sheet-interface">
			<div class="count-sheet-header">
				<div class="count-sheet-scan-controls">
					<div class="count-sheet-scan-group">
						<div class="input-group">
							<input type="text" class="form-control count-sheet-input" id="warehouse_job_scan" placeholder="Scan Warehouse Job">
							<button class="btn count-sheet-btn-scan" type="button" id="scan_warehouse_job" title="Scan">
								<i class="fa fa-camera"></i>
							</button>
						</div>
					</div>
				</div>
				<div class="count-sheet-filter-controls">
					<div class="count-sheet-filter-group">
						<label>Filter by:</label>
						<select class="form-control count-sheet-select" id="filter_type">
							<option value="item">Item</option>
							<option value="location">Storage Location</option>
							<option value="handling_unit">Handling Unit</option>
						</select>
					</div>
					<div class="count-sheet-filter-group">
						<div class="input-group">
							<input type="text" class="form-control count-sheet-input" id="item_filter" placeholder="Enter filter value">
							<button class="btn count-sheet-btn-scan" type="button" id="scan_filter" title="Scan">
								<i class="fa fa-camera"></i>
							</button>
						</div>
					</div>
					<div class="count-sheet-filter-group">
						<button class="btn count-sheet-btn-clear" type="button" id="clear_filter" title="Clear Filter">
							<i class="fa fa-times"></i> Clear
						</button>
					</div>
				</div>
			</div>
			<div class="content-grid">
				<div class="items-panel">
					<div class="panel-header">
						<h3>Items to Count</h3>
						<div class="status-indicator" id="item_status">0 items</div>
					</div>
					<div id="items_list" class="items-container">
						<!-- Items will be populated here -->
					</div>
				</div>
				<div class="counted-panel">
					<div class="panel-header">
						<h3>Counted Items</h3>
						<div class="status-indicator" id="counted_status">0 counted</div>
					</div>
					<div id="counted_list" class="counted-container">
						<!-- Counted items will be populated here -->
					</div>
				</div>
			</div>
		</div>
	`);

	page.main.append(main_container);

	// Add CSS styles
	$('<style>')
		.prop('type', 'text/css')
		.html(`
			.count-sheet-interface {
				background: #f8f9fa;
				min-height: 100vh;
				font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
			}
			
			.count-sheet-header {
				background: white;
				padding: 16px 24px;
				border-bottom: 1px solid #e9ecef;
				box-shadow: 0 1px 3px rgba(0,0,0,0.1);
			}
			
			.count-sheet-scan-controls {
				display: flex;
				gap: 16px;
				align-items: center;
				margin-bottom: 16px;
			}
			
			.count-sheet-scan-group {
				flex: 1;
				max-width: 300px;
			}
			
			.count-sheet-filter-controls {
				display: flex;
				gap: 16px;
				align-items: center;
				padding: 12px 0;
				border-top: 1px solid #e9ecef;
			}
			
			.count-sheet-filter-group {
				display: flex;
				align-items: center;
				gap: 8px;
			}
			
			.count-sheet-filter-group label {
				font-weight: 500;
				color: #495057;
				margin: 0;
				white-space: nowrap;
			}
			
			.count-sheet-select {
				min-width: 150px;
				border: 1px solid #e1e5e9;
				border-radius: 6px;
				padding: 8px 12px;
				font-size: 14px;
				background: white;
			}
			
			.count-sheet-btn-clear {
				background: #6c757d;
				border: none;
				color: white;
				padding: 8px 12px;
				border-radius: 6px;
				font-size: 12px;
				cursor: pointer;
				transition: all 0.2s ease;
			}
			
			.count-sheet-btn-clear:hover {
				background: #5a6268;
				transform: translateY(-1px);
			}
			
			.count-sheet-input {
				border: 1px solid #e1e5e9;
				border-radius: 8px;
				padding: 12px 16px;
				font-size: 14px;
				transition: all 0.2s ease;
				background: #fafbfc;
			}
			
			.count-sheet-input:focus {
				border-color: #007bff;
				box-shadow: 0 0 0 3px rgba(0,123,255,0.1);
				background: white;
			}
			
			.count-sheet-btn-scan {
				background: #007bff;
				border: none;
				color: white;
				padding: 12px 16px;
				border-radius: 0 8px 8px 0;
				transition: all 0.2s ease;
			}
			
			.count-sheet-btn-scan:hover {
				background: #0056b3;
				transform: translateY(-1px);
			}
			
			.content-grid {
				display: grid;
				grid-template-columns: 2fr 1fr;
				gap: 24px;
				padding: 24px;
				max-width: 1400px;
				margin: 0 auto;
			}
			
			.items-panel, .counted-panel {
				background: white;
				border-radius: 12px;
				box-shadow: 0 2px 8px rgba(0,0,0,0.1);
				overflow: hidden;
			}
			
			.panel-header {
				display: flex;
				justify-content: space-between;
				align-items: center;
				padding: 20px 24px;
				background: #f8f9fa;
				border-bottom: 1px solid #e9ecef;
			}
			
			.panel-header h3 {
				margin: 0;
				font-size: 18px;
				font-weight: 600;
				color: #2c3e50;
			}
			
			.status-indicator {
				background: #e9ecef;
				color: #6c757d;
				padding: 4px 12px;
				border-radius: 20px;
				font-size: 12px;
				font-weight: 500;
			}
			
			.items-container, .counted-container {
				max-height: 70vh;
				overflow-y: auto;
				padding: 8px;
			}
			
			.counted-container {
				display: flex;
				flex-direction: column;
				gap: 8px;
			}
			
			.location-item {
				padding: 16px 20px;
				margin: 4px 8px;
				border-radius: 8px;
				cursor: pointer;
				transition: all 0.2s ease;
				border: 1px solid transparent;
				background: #fafbfc;
			}
			
			.location-item:hover {
				background: #e3f2fd;
				border-color: #bbdefb;
				transform: translateY(-1px);
			}
			
			.location-item.selected {
				background: #e3f2fd;
				border-color: #2196f3;
				box-shadow: 0 2px 8px rgba(33,150,243,0.2);
			}
			
			.location-item.counted {
				background: #e8f4fd;
				border-color: #2196f3;
			}
			
			.location-item.pending {
				background: #f3f4f6;
				border-color: #6b7280;
			}
			
			.location-name {
				font-weight: 600;
				color: #2c3e50;
				margin-bottom: 4px;
			}
			
			.location-details {
				font-size: 12px;
				color: #6c757d;
			}
			
			.location-status {
				display: flex;
				justify-content: space-between;
				align-items: center;
				margin-top: 8px;
			}
			
			.status-badge {
				padding: 4px 8px;
				border-radius: 12px;
				font-size: 11px;
				font-weight: 600;
				text-transform: uppercase;
			}
			
			.status-counted {
				background: #2196f3;
				color: white;
			}
			
			.status-pending {
				background: #6b7280;
				color: white;
			}
			
			.item-row {
				padding: 16px 20px;
				margin: 6px 8px;
				border-radius: 8px;
				background: #fafbfc;
				border: 1px solid #e9ecef;
				transition: all 0.2s ease;
			}
			
			.item-row:hover {
				background: #f8f9fa;
				transform: translateY(-1px);
			}
			
			.item-row.counted {
				background: #d4edda;
				border-color: #28a745;
			}
			
			.count-sheet-counted-card {
				background: #f8f9fa;
				border: 1px solid #e9ecef;
				border-radius: 8px;
				padding: 12px;
				display: flex;
				justify-content: space-between;
				align-items: center;
				transition: all 0.2s ease;
			}
			
			.count-sheet-counted-card:hover {
				background: #e9ecef;
				transform: translateY(-1px);
			}
			
			.count-sheet-counted-info {
				flex: 1;
			}
			
			.count-sheet-counted-code {
				font-weight: 600;
				color: #2c3e50;
				font-size: 14px;
				margin-bottom: 2px;
			}
			
			.count-sheet-counted-details {
				font-size: 11px;
				color: #6c757d;
				margin-bottom: 4px;
			}
			
			.count-sheet-counted-location {
				font-size: 10px;
				color: #6c757d;
			}
			
			.count-sheet-counted-actions {
				display: flex;
				align-items: center;
				gap: 8px;
			}
			
			.count-sheet-counted-badge {
				background: #28a745;
				color: white;
				padding: 4px 8px;
				border-radius: 12px;
				font-size: 11px;
				font-weight: 600;
			}
			
			.count-sheet-btn-reset {
				background: #dc3545;
				border: none;
				color: white;
				padding: 6px 8px;
				border-radius: 4px;
				font-size: 10px;
				cursor: pointer;
				transition: all 0.2s ease;
			}
			
			.count-sheet-btn-reset:hover {
				background: #c82333;
				transform: translateY(-1px);
			}
			
			.count-sheet-empty-state {
				text-align: center;
				color: #6c757d;
				padding: 20px;
				font-style: italic;
			}
			
			.item-header {
				display: flex;
				justify-content: space-between;
				align-items: flex-start;
				margin-bottom: 12px;
			}
			
			.item-info {
				flex: 1;
			}
			
			.item-status {
				display: flex;
				align-items: center;
				gap: 8px;
			}
			
			.counted-checkbox {
				width: 16px;
				height: 16px;
				accent-color: #28a745;
			}
			
			.item-code {
				font-weight: 600;
				color: #2c3e50;
				font-size: 14px;
			}
			
			.item-name {
				font-size: 12px;
				color: #6c757d;
				margin-top: 2px;
			}
			
			.item-details {
				display: flex;
				gap: 16px;
				align-items: center;
				font-size: 12px;
				color: #6c757d;
			}
			
			.item-location {
				display: flex;
				gap: 12px;
				align-items: center;
				font-size: 11px;
				color: #495057;
				margin-top: 8px;
				padding: 6px 8px;
				background: #f8f9fa;
				border-radius: 4px;
			}
			
			.location-info, .handling-unit-info {
				display: flex;
				align-items: center;
				gap: 4px;
			}
			
			.count-section {
				display: flex;
				align-items: center;
				gap: 12px;
				margin-top: 12px;
			}
			
			.count-input {
				width: 80px;
				text-align: center;
				border: 1px solid #e1e5e9;
				border-radius: 6px;
				padding: 8px 12px;
				font-size: 14px;
				background: white;
			}
			
			.count-input:focus {
				border-color: #007bff;
				box-shadow: 0 0 0 2px rgba(0,123,255,0.1);
			}
			
			.btn-save {
				background: #007bff;
				border: none;
				color: white;
				padding: 8px 16px;
				border-radius: 6px;
				font-size: 12px;
				font-weight: 500;
				transition: all 0.2s ease;
			}
			
			.btn-save:hover {
				background: #0056b3;
				transform: translateY(-1px);
			}
			
			.system-count {
				background: #e9ecef;
				padding: 4px 8px;
				border-radius: 4px;
				font-size: 11px;
				font-weight: 500;
			}
			
			@media (max-width: 768px) {
				.content-grid {
					grid-template-columns: 1fr;
					padding: 16px;
				}
				
				.scan-controls {
					flex-direction: column;
					gap: 12px;
				}
				
				.scan-group {
					max-width: 100%;
				}
			}
		`)
		.appendTo('head');

	// Event handlers
	$('#warehouse_job_scan').on('keypress', function(e) {
		if (e.which === 13) { // Enter key
			load_warehouse_job($(this).val());
		}
	});

	$('#item_filter').on('input keyup', function() {
		console.log('Item filter input event triggered');
		let filter_value = $(this).val();
		let filter_type = $('#filter_type').val();
		
		if (filter_value.trim() === '') {
			// Show all items when filter is empty
			$('.item-row').show();
		} else {
			filter_items(filter_value, filter_type);
		}
	});
	
	$('#filter_type').on('change', function() {
		let filter_value = $('#item_filter').val();
		if (filter_value.trim() !== '') {
			filter_items(filter_value, $(this).val());
		}
	});
	
	$('#clear_filter').on('click', function() {
		$('#item_filter').val('');
		$('.item-row').show();
	});

	// Scan button event handlers
	$('#scan_warehouse_job').on('click', function() {
		start_barcode_scanner('warehouse_job_scan');
	});

	$('#scan_filter').on('click', function() {
		start_barcode_scanner('item_filter');
	});

	// Global variables
	let current_warehouse_job = null;
	let locations_data = [];
	let items_data = [];

	// Load warehouse job data
	function load_warehouse_job(job_name) {
		console.log('Loading warehouse job:', job_name);
		frappe.call({
			method: 'logistics.warehousing.count_sheet.get_warehouse_job_count_data',
			args: {
				warehouse_job: job_name
			},
			callback: function(r) {
				console.log('API Response:', r);
				if (r.message && !r.message.error) {
					current_warehouse_job = job_name;
					items_data = r.message.items || [];
					console.log('Items data:', items_data);
					console.log('Total items loaded:', items_data.length);
					
					// Debug: Check actual_quantity values
					items_data.forEach((item, index) => {
						console.log(`Item ${index}: ${item.item} - actual_quantity: ${item.actual_quantity} (type: ${typeof item.actual_quantity})`);
					});
					
					render_items();
					render_counted_items();
					
					frappe.show_alert({
						message: `Warehouse Job ${job_name} loaded successfully`,
						indicator: 'green'
					});
				} else {
					console.error('Error loading warehouse job:', r.message);
					frappe.show_alert({
						message: r.message?.error || 'Warehouse Job not found',
						indicator: 'red'
					});
				}
			},
			error: function(xhr, textStatus, errorThrown) {
				console.error('API call failed:', textStatus, errorThrown, xhr);
				frappe.show_alert({
					message: 'Failed to load warehouse job data',
					indicator: 'red'
				});
			}
		});
	}

	// Filter items (only uncounted items)
	function filter_items(filter_text, filter_type = 'item') {
		console.log('Filtering uncounted items with:', filter_text, 'type:', filter_type);
		$('.item-row').each(function() {
			let $row = $(this);
			let search_text = filter_text.toLowerCase();
			let should_show = false;
			
			if (filter_type === 'item') {
				let item_code = $row.find('.item-code').text().toLowerCase();
				let item_name = $row.find('.item-name').text().toLowerCase();
				should_show = item_code.includes(search_text) || item_name.includes(search_text);
			} else if (filter_type === 'location') {
				let location = $row.data('location') || '';
				should_show = location.toLowerCase().includes(search_text);
			} else if (filter_type === 'handling_unit') {
				let handling_unit = $row.data('handling-unit') || '';
				should_show = handling_unit.toLowerCase().includes(search_text);
			}
			
			if (should_show) {
				$row.show();
			} else {
				$row.hide();
			}
		});
	}

	// Render items list (only uncounted items)
	function render_items() {
		console.log('Rendering items:', items_data);
		let uncounted_items = items_data.filter(item => !item.counted);
		let html = '';
		
		console.log('Uncounted items:', uncounted_items);
		console.log('Counted status for all items:', items_data.map(item => ({item: item.item, counted: item.counted, actual_quantity: item.actual_quantity})));
		
		if (uncounted_items.length === 0) {
			html = '<div class="count-sheet-empty-state">All items have been counted!</div>';
		} else {
			uncounted_items.forEach((item, index) => {
				let system_count_display = item.blind_count ? 
					'<span class="text-muted">Hidden</span>' : 
					`<span class="system-count">${item.system_count || 0}</span>`;
				
				html += `
					<div class="item-row" data-item="${item.name}" data-location="${item.location || ''}" data-handling-unit="${item.handling_unit || ''}" data-index="${index}">
						<div class="item-header">
							<div class="item-info">
								<div class="item-code">${item.item}</div>
								<div class="item-name">${item.item_name || ''}</div>
							</div>
							<div class="item-status">
								<input type="checkbox" class="counted-checkbox" data-item="${item.name}">
							</div>
						</div>
						<div class="item-details">
							<span>UOM: ${item.uom || 'EA'}</span>
							<span>System: ${system_count_display}</span>
							${item.serial_no ? `<span>SN: ${item.serial_no}</span>` : ''}
							${item.batch_no ? `<span>Batch: ${item.batch_no}</span>` : ''}
						</div>
						<div class="item-location">
							<span class="location-info">📍 ${item.location || 'No Location'}</span>
							<span class="handling-unit-info">📦 ${item.handling_unit || 'No HU'}</span>
						</div>
						<div class="count-section">
							<input type="number" class="count-input" 
								   data-item="${item.name}"
								   placeholder="Enter count">
							<button class="btn-save save-count" data-item="${item.name}">
								Save
							</button>
						</div>
					</div>
				`;
			});
		}
		$('#items_list').html(html);
		$('#item_status').text(`${uncounted_items.length} items to count`);

		// Add event handlers
		$('.save-count').on('click', function() {
			let item_name = $(this).data('item');
			let actual_count = $(`input[data-item="${item_name}"]`).val();
			save_count(item_name, actual_count);
		});

		$('.count-input').on('keypress', function(e) {
			if (e.which === 13) { // Enter key
				let item_name = $(this).data('item');
				let actual_count = $(this).val();
				save_count(item_name, actual_count);
			}
		});

		// Add checkbox change handler
		$('.counted-checkbox').on('change', function() {
			let item_name = $(this).data('item');
			let is_checked = $(this).is(':checked');
			
			if (is_checked) {
				// If checked, ensure there's a count value
				let count_input = $(`input[data-item="${item_name}"]`);
				let count_value = count_input.val();
				if (count_value !== null && count_value !== undefined && count_value !== '') {
					save_count(item_name, count_value);
				} else {
					$(this).prop('checked', false);
					frappe.show_alert({
						message: 'Please enter a count value first',
						indicator: 'orange'
					});
				}
			}
		});
	}


	// Render counted items
	function render_counted_items() {
		let counted_items = items_data.filter(item => item.counted);
		let html = '';
		
		console.log('Rendering counted items:', counted_items);
		console.log('Counted items filter result:', items_data.map(item => ({item: item.item, counted: item.counted, actual_quantity: item.actual_quantity, filter_result: item.counted})));
		
		if (counted_items.length === 0) {
			html = '<div class="count-sheet-empty-state">No counted items yet</div>';
		} else {
			counted_items.forEach(item => {
				html += `
					<div class="count-sheet-counted-card" data-item="${item.name}">
						<div class="count-sheet-counted-info">
							<div class="count-sheet-counted-code">${item.item}</div>
							<div class="count-sheet-counted-details">${item.item_name || ''}</div>
							<div class="count-sheet-counted-location">${item.location || 'No Location'} • ${item.handling_unit || 'No HU'}</div>
						</div>
						<div class="count-sheet-counted-actions">
							<div class="count-sheet-counted-badge">${item.actual_quantity}</div>
							<button class="count-sheet-btn-reset" data-item="${item.name}" title="Reset Count">
								<i class="fa fa-undo"></i>
							</button>
						</div>
					</div>
				`;
			});
		}
		
		$('#counted_list').html(html);
		$('#counted_status').text(`${counted_items.length} counted`);

		// Add reset button handlers
		$('.count-sheet-btn-reset').on('click', function() {
			let item_name = $(this).data('item');
			reset_count(item_name);
		});
	}

	// Save count
	function save_count(item_name, actual_count) {
		frappe.call({
			method: 'logistics.warehousing.count_sheet.save_count_data',
			args: {
				warehouse_job: current_warehouse_job,
				item_name: item_name,
				actual_count: parseFloat(actual_count) || 0
			},
			callback: function(r) {
				if (r.message) {
					frappe.show_alert({
						message: 'Count saved successfully',
						indicator: 'green'
					});
					// Update the item in the data
					let item = items_data.find(i => i.name === item_name);
					if (item) {
						item.actual_quantity = parseFloat(actual_count) || 0;
						item.counted = true;
					}
					// Re-render both panels (item will move from left to right)
					render_items();
					render_counted_items();
					
					// Re-apply current filter after re-rendering
					let filter_value = $('#item_filter').val();
					let filter_type = $('#filter_type').val();
					if (filter_value.trim() !== '') {
						filter_items(filter_value, filter_type);
					}
				} else {
					frappe.show_alert({
						message: 'Failed to save count',
						indicator: 'red'
					});
				}
			}
		});
	}

	// Reset count
	function reset_count(item_name) {
		frappe.call({
			method: 'logistics.warehousing.count_sheet.reset_single_count',
			args: {
				warehouse_job: current_warehouse_job,
				item_name: item_name
			},
			callback: function(r) {
				if (r.message) {
					frappe.show_alert({
						message: 'Count reset successfully',
						indicator: 'green'
					});
					// Update the item in the data
					let item = items_data.find(i => i.name === item_name);
					if (item) {
						item.actual_quantity = null;
						item.counted = false;
					}
					// Re-render both panels (item will move from right to left)
					render_items();
					render_counted_items();
					
					// Re-apply current filter after re-rendering
					let filter_value = $('#item_filter').val();
					let filter_type = $('#filter_type').val();
					if (filter_value.trim() !== '') {
						filter_items(filter_value, filter_type);
					}
				} else {
					frappe.show_alert({
						message: 'Failed to reset count',
						indicator: 'red'
					});
				}
			}
		});
	}

	// Barcode scanning function
	function start_barcode_scanner(target_input_id) {
		// Check if browser supports camera access
		if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
			frappe.show_alert({
				message: 'Camera not supported on this device',
				indicator: 'red'
			});
			return;
		}

		// Create camera modal
		let camera_modal = $(`
			<div class="modal fade" id="barcode_scanner_modal" tabindex="-1" role="dialog">
				<div class="modal-dialog modal-lg" role="document">
					<div class="modal-content">
						<div class="modal-header">
							<h4 class="modal-title">
								<i class="fa fa-camera"></i> Barcode Scanner
							</h4>
							<button type="button" class="close" data-dismiss="modal">
								<span>&times;</span>
							</button>
						</div>
						<div class="modal-body text-center">
							<div id="camera_container" style="position: relative; display: inline-block;">
								<video id="barcode_video" width="640" height="480" autoplay style="border: 1px solid #ddd; border-radius: 4px;"></video>
								<canvas id="barcode_canvas" width="640" height="480" style="display: none;"></canvas>
								<div id="scanner_overlay" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
									width: 200px; height: 100px; border: 2px solid #007bff; border-radius: 8px; 
									background: rgba(0, 123, 255, 0.1); pointer-events: none;">
									<div style="position: absolute; top: -2px; left: -2px; right: -2px; bottom: -2px; 
										border: 2px dashed #007bff; border-radius: 8px;"></div>
								</div>
							</div>
							<div class="mt-3">
								<p class="text-muted">Position the barcode within the scanning area</p>
								<div id="scanner_status" class="alert alert-info">Initializing camera...</div>
							</div>
						</div>
						<div class="modal-footer">
							<button type="button" class="btn btn-secondary" data-dismiss="modal">Cancel</button>
							<button type="button" class="btn btn-primary" id="manual_input_btn">Manual Input</button>
						</div>
					</div>
				</div>
			</div>
		`);

		// Remove existing modal if any
		$('#barcode_scanner_modal').remove();
		$('body').append(camera_modal);
		$('#barcode_scanner_modal').modal('show');

		let video = document.getElementById('barcode_video');
		let canvas = document.getElementById('barcode_canvas');
		let context = canvas.getContext('2d');
		let scanning = false;

		// Start camera
		navigator.mediaDevices.getUserMedia({ 
			video: { 
				facingMode: 'environment', // Use back camera on mobile
				width: { ideal: 640 },
				height: { ideal: 480 }
			} 
		})
		.then(function(stream) {
			video.srcObject = stream;
			$('#scanner_status').removeClass('alert-info').addClass('alert-success').text('Camera ready - Position barcode in view');
			
			// Start scanning after a short delay
			setTimeout(function() {
				start_scanning();
			}, 1000);
		})
		.catch(function(err) {
			console.error('Camera error:', err);
			$('#scanner_status').removeClass('alert-info').addClass('alert-danger').text('Camera access denied or not available');
		});

		// Start barcode scanning
		function start_scanning() {
			scanning = true;
			scan_barcode();
		}

		// Scan for barcodes
		function scan_barcode() {
			if (!scanning) return;

			// Draw current frame to canvas
			context.drawImage(video, 0, 0, canvas.width, canvas.height);
			
			// Get image data
			let imageData = context.getImageData(0, 0, canvas.width, canvas.height);
			
			// Simple barcode detection (this is a basic implementation)
			// In a real application, you would use a proper barcode scanning library like QuaggaJS or ZXing
			try {
				// For demo purposes, we'll simulate barcode detection
				// In production, integrate with a proper barcode scanning library
				detect_barcode_simple(imageData);
			} catch (e) {
				console.log('Scanning...');
			}

			// Continue scanning
			if (scanning) {
				requestAnimationFrame(scan_barcode);
			}
		}

		// Simple barcode detection (placeholder - integrate with real barcode library)
		function detect_barcode_simple(imageData) {
			// This is a placeholder - in production, use QuaggaJS or similar
			// For now, we'll just show a message that manual input is needed
			$('#scanner_status').html('Barcode scanning active - Use manual input for now');
		}

		// Manual input button
		$('#manual_input_btn').on('click', function() {
			let manual_value = prompt('Enter barcode manually:');
			if (manual_value) {
				$('#' + target_input_id).val(manual_value);
				if (target_input_id === 'warehouse_job_scan') {
					load_warehouse_job(manual_value);
				} else if (target_input_id === 'item_filter') {
					let filter_type = $('#filter_type').val();
					filter_items(manual_value, filter_type);
				}
				$('#barcode_scanner_modal').modal('hide');
			}
		});

		// Clean up when modal is closed
		$('#barcode_scanner_modal').on('hidden.bs.modal', function() {
			scanning = false;
			if (video.srcObject) {
				video.srcObject.getTracks().forEach(track => track.stop());
			}
		});

		// Handle successful barcode detection (placeholder)
		function on_barcode_detected(barcode_data) {
			$('#' + target_input_id).val(barcode_data);
			if (target_input_id === 'warehouse_job_scan') {
				load_warehouse_job(barcode_data);
			} else if (target_input_id === 'item_filter') {
				let filter_type = $('#filter_type').val();
				filter_items(barcode_data, filter_type);
			}
			$('#barcode_scanner_modal').modal('hide');
		}
	}
}