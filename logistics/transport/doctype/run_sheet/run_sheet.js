// logistics/transport/doctype/run_sheet/run_sheet.js
// Multi-leg route mapping for Run Sheet

// ---------- utils ----------
function isFiniteNum(n) { return typeof n === "number" && isFinite(n); }
function toNumber(v) {
  const n = typeof v === "number" ? v : parseFloat(v);
  return isNaN(n) ? 0 : n;
}

// Format a number respecting Frappe if available, else a sane fallback
function fmt_num(value, precision = 2) {
  const v = toNumber(value);
  try {
    if (typeof frappe.format === "function") {
      return frappe.format(v, { fieldtype: "Float", precision });
    }
  } catch (e) {}
  try {
    return v.toLocaleString(undefined, { maximumFractionDigits: precision, minimumFractionDigits: precision });
  } catch (e) {
    return v.toFixed(precision);
  }
}

// Extract coordinates from Address
async function getAddressLatLon(addrname) {
  if (!addrname) return null;

  let d = null;
  try {
    d = await frappe.db.get_doc("Address", addrname);
  } catch (e) {
    return null;
  }
  if (!d) return null;

  // Try different possible field names for coordinates
  const lat = d.custom_latitude || d.latitude || d.lat;
  const lon = d.custom_longitude || d.longitude || d.lon;

  const nlat = typeof lat === "number" ? lat : parseFloat(lat);
  const nlon = typeof lon === "number" ? lon : parseFloat(lon);

  if (isFinite(nlat) && isFinite(nlon)) {
    return { lat: nlat, lon: nlon };
  }
  return null;
}

// Determine vehicle state: 'OFF', 'IDLE', or 'ON'
// IDLE = ignition ON but speed < 5 km/h (engine running but not moving)
// ON = ignition ON and speed >= 5 km/h (vehicle moving)
// OFF = ignition OFF
function getVehicleState(vehiclePosition) {
  if (!vehiclePosition) return 'OFF';
  
  const ignition = vehiclePosition.ignition === true || vehiclePosition.ignition === 1 || vehiclePosition.ignition === '1' || vehiclePosition.ignition === 'ON';
  const speed = toNumber(vehiclePosition.speed_kph);
  const IDLE_SPEED_THRESHOLD = 5; // km/h - below this is considered idle
  
  if (!ignition) {
    return 'OFF';
  } else if (speed < IDLE_SPEED_THRESHOLD) {
    return 'IDLE';
  } else {
    return 'ON';
  }
}

// Get display text and colors for vehicle state
function getVehicleStateDisplay(state) {
  switch (state) {
    case 'IDLE':
      return {
        text: 'IDLE',
        color: '#f59e0b', // amber/orange
        bgColor: '#f59e0b',
        labelColor: '#f59e0b',
        statusColor: '#f59e0b'
      };
    case 'ON':
      return {
        text: 'ON',
        color: '#10b981', // green
        bgColor: '#10b981',
        labelColor: '#10b981',
        statusColor: '#10b981'
      };
    case 'OFF':
    default:
      return {
        text: 'OFF',
        color: '#ff0000', // red
        bgColor: '#ff0000',
        labelColor: '#ff0000',
        statusColor: '#ff0000' // red for status indicator
      };
  }
}

// ---------- Multi-leg Route Map ----------
async function render_run_sheet_route_map(frm) {
  // Wait for field to be ready
  let $wrapper;
  try {
    const field = frm.get_field('route_map');
    if (!field) {
      console.warn('Route map field not found in form');
      return;
    }
    $wrapper = field.$wrapper;
    if (!$wrapper || $wrapper.length === 0) {
      // Retry after a short delay if wrapper not ready
      setTimeout(() => render_run_sheet_route_map(frm), 500);
      return;
    }
  } catch (error) {
    console.error('Error getting route_map field:', error);
    return;
  }
  
  const legs = frm.doc.legs || [];
  if (legs.length === 0) {
    const message = frm.is_new() 
      ? 'Save the Run Sheet and add transport legs in the Transport Leg tab to see the route map.'
      : 'No transport legs added to this run sheet. Add legs in the Transport Leg tab to see the route map.';
    $wrapper.html(`<div class="text-muted" style="padding: 20px; text-align: center;">${message}</div>`);
    return;
  }

  try {
    // Get map renderer setting
    let mapRenderer = 'openstreetmap'; // default
    try {
      const settings = await frappe.call({
        method: 'frappe.client.get_value',
        args: {
          doctype: 'Transport Settings',
          fieldname: 'map_renderer'
        }
      });
      mapRenderer = settings.message?.map_renderer || 'openstreetmap';
    } catch (e) {
      // Use default
    }

    // Create unique map container ID
    const mapId = `runsheet-route-map-${frm.doc.name || 'new'}-${Date.now()}`;
    
    // Vehicle info for header
    const vehicleType = frm.doc.vehicle_type || 'Not assigned';
    const vehicleName = frm.doc.vehicle || 'Not assigned';
    const transportCompany = frm.doc.transport_company || 'Not assigned';
    const driverName = frm.doc.driver_name || frm.doc.driver || 'Not assigned';
    const runSheetId = frm.doc.name || 'New';
    const runDate = frm.doc.run_date || 'Not set';
    const status = frm.doc.status || 'Draft';
    
    const mapHtml = `
      <style>
        .run-sheet-header {
          background: #ffffff;
          border: 1px solid #e0e0e0;
          border-radius: 6px;
          margin-bottom: 20px;
          padding: 12px 16px;
        }
        
        .header-main {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 20px;
        }
        
        .header-vehicle-section {
          display: flex;
          flex-direction: column;
          gap: 0px;
        }
        
        .section-label {
          font-size: 10px;
          color: #6c757d;
          text-transform: uppercase;
          font-weight: 600;
          letter-spacing: 0.5px;
          margin-bottom: -2px;
        }
        
        .vehicle-name {
          font-size: 18px;
          font-weight: 700;
          color: #007bff;
          margin-top: -2px;
        }
        
        .header-details {
          display: flex;
          gap: 15px;
          align-items: center;
        }
        
        .header-item {
          display: flex;
          align-items: baseline;
          gap: 5px;
        }
        
        .header-item label {
          font-size: 10px;
          color: #6c757d;
          font-weight: 600;
        }
        
        .header-item span {
          font-size: 11px;
          color: #2c3e50;
          font-weight: 500;
        }
        
        .route-container {
          display: flex;
          gap: 20px;
          margin: 20px 0;
          align-items: flex-start;
        }
        
        .leg-cards-sidebar {
          flex: 1;
          max-width: 300px;
        }
        
        .map-main-container {
          flex: 2;
          align-self: flex-start;
          position: relative;
          z-index: 1;
        }
        
        .map-container {
          width: 100%;
          height: 500px;
          border: 1px solid #ddd;
          border-radius: 4px;
          overflow: hidden;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          position: relative;
        }
        
        .map-view {
          width: 100%;
          height: 100%;
        }
        
        .map-controls {
          position: absolute;
          bottom: 10px;
          left: 10px;
          display: flex;
          gap: 6px;
          z-index: 100;
          pointer-events: auto;
        }
        
        .map-btn {
          background: white;
          border: 1px solid #d1d5db;
          padding: 6px 10px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 11px;
          box-shadow: 0 1px 2px rgba(0,0,0,0.05);
          color: #6b7280;
          font-weight: 500;
          transition: all 0.2s ease;
        }
        
        .map-btn:hover {
          background: #f8f9fa;
          border-color: #9ca3af;
        }
        
        .locate-btn {
          background: #2563eb;
          color: white;
          border: none;
          box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        .locate-btn:hover {
          background: #1d4ed8;
        }
        
        .leg-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        
        .transport-leg-card {
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 6px;
          padding: 12px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.1);
          transition: all 0.3s ease;
          border-left: 4px solid #667eea;
        }
        
        .transport-leg-card:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .leg-card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 6px;
        }
        
        .leg-card-header h5 {
          margin: 0;
          font-size: 14px;
          font-weight: 600;
          color: #333;
          line-height: 1.2;
        }
        
        .leg-number {
          background: #667eea;
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 10px;
          font-weight: 600;
        }
        
        .leg-details {
          font-size: 11px;
          color: #6c757d;
          line-height: 1.4;
          margin-bottom: 8px;
        }
        
        .leg-actions {
          display: flex;
          gap: 6px;
          margin-top: 8px;
        }
        
        .action-icon {
          font-size: 14px;
          cursor: pointer;
          transition: opacity 0.2s ease;
        }
        
        .action-icon:hover {
          opacity: 0.7;
        }
        
        .status-badge {
          padding: 2px 6px;
          border-radius: 10px;
          font-size: 10px;
          font-weight: 500;
          text-transform: uppercase;
        }
        
        .status-badge.completed, .status-badge.billed {
          background: #d4edda;
          color: #155724;
        }
        
        .status-badge.started {
          background: #cfe2ff;
          color: #084298;
        }
        
        .status-badge.assigned {
          background: #fff3cd;
          color: #856404;
        }
        
        .status-badge.open {
          background: #e2e3e5;
          color: #6c757d;
        }
        
        .transport-leg-card.completed {
          border-left-color: #28a745;
        }
        
        .transport-leg-card.started {
          border-left-color: #007bff;
        }
        
        .transport-leg-card.assigned {
          border-left-color: #ffc107;
        }
        
        @media (max-width: 768px) {
          .route-container {
            flex-direction: column;
            padding: 0;
          }
          
          .leg-cards-sidebar {
            max-width: none;
            width: 100%;
            margin-bottom: 10px;
            padding: 10px;
            order: 1;
          }
          
          .map-main-container {
            position: relative;
            top: auto;
            max-height: none;
            order: 2;
            padding: 0 10px;
          }
          
          .map-container {
            height: 400px;
          }
          
          .map-controls {
            bottom: 8px;
            left: 8px;
            gap: 4px;
          }
          
          .map-btn {
            padding: 4px 8px;
            font-size: 10px;
          }
          
          .transport-leg-card {
            margin-bottom: 8px;
            padding: 12px;
          }
          
          .leg-card-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }
          
          .leg-card-header h5 {
            font-size: 14px;
            margin: 0;
          }
          
          .leg-actions {
            justify-content: center;
            margin-top: 10px;
            gap: 12px;
          }
          
          .action-icon {
            font-size: 18px;
            padding: 8px;
            border-radius: 50%;
            background: rgba(255,255,255,0.9);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-width: 36px;
            min-height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          
          .status-badge {
            font-size: 9px;
            padding: 3px 8px;
          }
          
          .leg-number {
            font-size: 11px;
          }
          
          .leg-details {
            font-size: 11px;
            margin-bottom: 10px;
          }
        }
        
        @media (max-width: 480px) {
          .route-container {
            padding: 0;
          }
          
          .leg-cards-sidebar {
            padding: 5px;
          }
          
          .map-main-container {
            padding: 0 5px;
          }
          
          .map-container {
            height: 350px;
          }
          
          .map-controls {
            bottom: 6px;
            left: 6px;
            gap: 3px;
          }
          
          .map-btn {
            padding: 3px 6px;
            font-size: 9px;
          }
          
          .transport-leg-card {
            padding: 10px;
            margin-bottom: 6px;
          }
          
          .leg-card-header h5 {
            font-size: 13px;
          }
          
          .leg-details {
            font-size: 10px;
          }
          
          .action-icon {
            font-size: 16px;
            padding: 6px;
            min-width: 32px;
            min-height: 32px;
          }
          
          .status-badge {
            font-size: 8px;
            padding: 2px 6px;
          }
          
          .leg-number {
            font-size: 10px;
          }
        }
        
        @media (max-width: 360px) {
          .transport-leg-card {
            padding: 8px;
          }
          
          .leg-card-header h5 {
            font-size: 12px;
          }
          
          .action-icon {
            font-size: 14px;
            padding: 4px;
            min-width: 28px;
            min-height: 28px;
          }
          
          .leg-actions {
            gap: 8px;
          }
          
          .map-container {
            height: 300px;
          }
          
          .map-controls {
            bottom: 4px;
            left: 4px;
            gap: 2px;
          }
          
          .map-btn {
            padding: 2px 4px;
            font-size: 8px;
          }
        }
        
        /* Mobile styles for header */
        @media (max-width: 768px) {
          .run-sheet-header {
            padding: 10px 12px;
            margin-bottom: 12px;
          }
          
          .header-main {
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
          }
          
          .header-details {
            gap: 12px;
            flex-wrap: wrap;
            width: 100%;
          }
          
          .vehicle-name {
            font-size: 16px;
          }
          
          .header-item-value {
            font-size: 12px;
          }
        }
        
        @media (max-width: 480px) {
          .run-sheet-header {
            padding: 8px 10px;
            margin-bottom: 10px;
          }
          
          .header-details {
            gap: 8px;
            flex-direction: column;
            align-items: flex-start;
          }
          
          .header-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 2px;
          }
          
          .vehicle-name {
            font-size: 15px;
          }
          
          .header-item-value {
            font-size: 11px;
          }
          
          .section-label {
            font-size: 9px;
          }
        }
      </style>
      
      <div class="run-sheet-header">
        <div class="header-main">
          <div class="header-vehicle-section">
            <label class="section-label">${vehicleType}</label>
            <div class="vehicle-name">${vehicleName}</div>
            <div style="font-size: 11px; color: #6c757d; margin-top: 4px;">
              <div><i class="fa fa-building"></i> ${transportCompany}</div>
              <div><i class="fa fa-user"></i> ${driverName}</div>
              <div><i class="fa fa-file-text"></i> ${runSheetId}</div>
            </div>
          </div>
          <div class="header-details">
            <div class="header-item">
              <label><i class="fa fa-calendar"></i> Run Date:</label>
              <span>${runDate}</span>
            </div>
            <div class="header-item">
              <label><i class="fa fa-info-circle"></i> Status:</label>
              <span>${status}</span>
            </div>
            <div class="header-item">
              <label><i class="fa fa-route"></i> Legs:</label>
              <span>${legs.length}</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="route-container">
        <div class="leg-cards-sidebar">
          <div class="leg-list" id="${mapId}-leg-cards"></div>
        </div>
        
        <div class="map-main-container">
          <div class="map-container">
            <div id="${mapId}" class="map-view"></div>
            <div class="map-controls">
              <button id="${mapId}-refresh-vehicle" class="map-btn" title="Refresh vehicle position">
                <i class="fa fa-refresh"></i>
              </button>
              <button id="${mapId}-locate-vehicle" class="map-btn locate-btn" title="Locate vehicle on map">
                <i class="fa fa-location-arrow"></i> Locate
              </button>
              <div class="map-btn" style="background: rgba(255,255,255,0.95); padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 11px; font-weight: 600; color: #2563eb; display: flex; align-items: center; gap: 4px; cursor: default;">
                <span style="color: #2563eb; font-size: 12px;">●</span> ${legs.length} Stops
              </div>
            </div>
        <div id="${mapId}-fallback" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); display: flex; align-items: center; justify-content: center; flex-direction: column;">
          <div style="text-align: center; color: #6c757d;">
            <i class="fa fa-map" style="font-size: 32px; margin-bottom: 15px;"></i>
            <div style="font-size: 18px; font-weight: 500; margin-bottom: 10px;">Route Loading...</div>
            <div style="font-size: 14px; margin-bottom: 15px; line-height: 1.4;">
              <strong>Run Sheet:</strong> ${frm.doc.name || 'New'}<br>
              <strong>Legs:</strong> ${legs.length} transport legs
            </div>
            <div style="font-size: 12px; color: #6c757d;">
              <i class="fa fa-info-circle"></i> Use the links above to view the route
            </div>
          </div>
        </div>
        <div id="${mapId}-missing-addresses" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); display: flex; align-items: center; justify-content: center; flex-direction: column;">
          <div style="text-align: center; color: #856404; max-width: 400px; padding: 20px;">
            <i class="fa fa-exclamation-triangle" style="font-size: 32px; margin-bottom: 15px;"></i>
            <div style="font-size: 18px; font-weight: 500; margin-bottom: 10px;">Missing Address Information</div>
            <div style="font-size: 14px; margin-bottom: 15px; line-height: 1.4;">
              Some Transport Legs are missing pick or drop addresses.<br>
              Complete the address information to show the full route map.
            </div>
            <div style="font-size: 12px; color: #6c757d;">
              <i class="fa fa-info-circle"></i> Check the Transport Legs tab for missing addresses
            </div>
          </div>
        </div>
      </div>
      <div class="text-muted small" style="margin-top: 10px; display: flex; gap: 20px; align-items: center; justify-content: center;">
        <a href="#" id="${mapId}-google-link" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
          <i class="fa fa-external-link"></i> Google Maps
        </a>
        <a href="#" id="${mapId}-osm-link" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
          <i class="fa fa-external-link"></i> OpenStreetMap
        </a>
        <a href="#" id="${mapId}-apple-link" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
          <i class="fa fa-external-link"></i> Apple Maps
        </a>
      </div>
    </div>
  </div>
    `;
    
    $wrapper.html(mapHtml);
    
    // Populate leg cards with status and conditional action buttons
    const legCardsContainer = document.getElementById(`${mapId}-leg-cards`);
    if (legCardsContainer) {
      // Get location labels (will be set after map initialization, so we'll update cards later)
      const updateLegCardsWithLabels = () => {
        const locationLabels = window[`${mapId}_locationLabels`];
        if (!locationLabels) {
          // Labels not ready yet, will update after map loads
          setTimeout(updateLegCardsWithLabels, 500);
          return;
        }
        
        // Update existing cards with labels instead of recreating them
        legs.forEach((leg, index) => {
          const card = legCardsContainer.querySelector(`[data-transport-leg="${leg.transport_leg}"][data-idx="${index + 1}"]`);
          if (card) {
            const legLabels = locationLabels.legLabelMap.get(index);
            const pickLabel = legLabels ? legLabels.pickLabel : '';
            const dropLabel = legLabels ? legLabels.dropLabel : '';
            
            // Update route labels with stop labels
            const routePoints = card.querySelectorAll('.route-point');
            if (routePoints.length >= 2) {
              const pickLabelEl = routePoints[0].querySelector('.route-label');
              const dropLabelEl = routePoints[1].querySelector('.route-label');
              
              if (pickLabelEl && pickLabel) {
                const facilityTypeFrom = leg.facility_type_from || 'Pickup';
                pickLabelEl.innerHTML = `<span class="stop-label-badge" style="background: #dc3545; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 6px;">${pickLabel}</span>${facilityTypeFrom}`;
              }
              
              if (dropLabelEl && dropLabel) {
                const facilityTypeTo = leg.facility_type_to || 'Drop';
                dropLabelEl.innerHTML = `<span class="stop-label-badge" style="background: #28a745; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-right: 6px;">${dropLabel}</span>${facilityTypeTo}`;
              }
            }
          }
        });
      };
      
      // First render without labels, then update with labels
      const legCardsHtml = await Promise.all(legs.map(async (leg, index) => {
        let status = 'Open';
        let startDate = null;
        let endDate = null;
        let customer = leg.customer || 'No Customer';
        let facilityTypeFrom = leg.facility_type_from || '';
        let facilityFrom = leg.facility_from || '';
        let facilityTypeTo = leg.facility_type_to || '';
        let facilityTo = leg.facility_to || '';
        
        // Get Transport Leg details for status
        if (leg.transport_leg) {
          try {
            const legDoc = await frappe.db.get_doc("Transport Leg", leg.transport_leg);
            status = legDoc.status || 'Open';
            startDate = legDoc.start_date;
            endDate = legDoc.end_date;
          } catch(e) {
            console.warn('Could not fetch leg status:', e);
          }
        }
        
        // Determine status class
        const statusClass = status.toLowerCase().replace(' ', '-');
        
        // Build action icons - show one at a time: start OR end
        const actionIcons = [];
        
        // Add drag handle icon (always first)
        actionIcons.push(`<i class="fa fa-grip-vertical drag-handle" 
           title="Drag to Reorder" 
           style="color: #6c757d; cursor: move;"></i>`);
        
        // Check if vehicle is assigned
        const hasVehicle = frm && frm.doc && frm.doc.vehicle && frm.doc.vehicle.trim() !== '';
        
        // Show start button: only if vehicle is filled AND leg hasn't started
        if (!startDate && hasVehicle) {
          actionIcons.push(`<i class="fa fa-play-circle action-icon" 
             title="Start Leg" 
             onclick="startTransportLeg('${leg.transport_leg}')"
             style="color: #28a745; cursor: pointer;"></i>`);
        }
        
        // Show end button: only if start button was pressed (leg has started) AND leg hasn't ended
        if (startDate && !endDate) {
          actionIcons.push(`<i class="fa fa-stop-circle action-icon" 
             title="End Leg" 
             onclick="endTransportLeg('${leg.transport_leg}')"
             style="color: #dc3545; cursor: pointer;"></i>`);
        }
        // Always show view icon
        actionIcons.push(`<i class="fa fa-eye action-icon" 
           title="View Leg" 
           onclick="viewTransportLeg('${leg.transport_leg}')"
           style="color: #007bff; cursor: pointer;"></i>`);
        
        return `
          <div class="transport-leg-card ${statusClass}" data-transport-leg="${leg.transport_leg}" data-idx="${index + 1}">
            <div class="leg-card-header">
              <h5><i class="fa fa-user"></i> ${customer}</h5>
              <span class="leg-number">#${index + 1}</span>
            </div>
            
            <div class="leg-details">
              <div class="route-display">
                <div class="route-point">
                  <div class="route-label">${facilityTypeFrom}</div>
                  <div class="route-value">${facilityFrom || 'Not set'}</div>
                </div>
                
                <div class="route-arrow">
                  <i class="fa fa-arrow-right"></i>
                </div>
                
                <div class="route-point">
                  <div class="route-label">${facilityTypeTo}</div>
                  <div class="route-value">${facilityTo || 'Not set'}</div>
                </div>
              </div>
            </div>
            
            <div class="leg-card-footer">
              ${actionIcons.length > 0 ? `<div class="leg-actions">${actionIcons.join('')}</div>` : '<div></div>'}
              <div class="leg-info-right">
                <div style="font-size: 10px; color: #999;">
                  ${leg.transport_leg || '<em>Not linked</em>'}
                </div>
                <span class="status-badge ${statusClass}">${status}</span>
              </div>
            </div>
          </div>
        `;
      }));
      
      legCardsContainer.innerHTML = legCardsHtml.join('');
      
      // Initialize drag-and-drop sorting
      initializeLegCardSorting(legCardsContainer, frm);
      
      // Update cards with labels after a short delay to allow map initialization
      setTimeout(updateLegCardsWithLabels, 1000);
    }
    
    // Show fallback initially
    showMapFallback(mapId);
    
    // Add refresh button handler
    setTimeout(() => {
      const refreshBtn = document.getElementById(`${mapId}-refresh-vehicle`);
      if (refreshBtn) {
        refreshBtn.onclick = async () => {
          console.log('Refreshing vehicle data...');
          refreshBtn.innerHTML = '<i class="fa fa-spin fa-spinner"></i> Refreshing...';
          refreshBtn.disabled = true;
          
          try {
            // Validate vehicle name before making API call
            if (!frm || !frm.doc || !frm.doc.vehicle || typeof frm.doc.vehicle !== 'string' || frm.doc.vehicle.trim().length === 0) {
              frappe.show_alert({
                message: __('No vehicle assigned to refresh'),
                indicator: 'orange'
              });
              refreshBtn.innerHTML = '<i class="fa fa-refresh"></i>';
              refreshBtn.disabled = false;
              return;
            }
            
            // Call the new refresh API to get fresh telematics data
            const refreshResult = await frappe.call({
              method: 'logistics.transport.api_vehicle_tracking.refresh_vehicle_data',
              args: {
                vehicle_name: frm.doc.vehicle.trim()
              }
            });
            
            if (refreshResult.message && refreshResult.message.success) {
              console.log('✓ Vehicle data refreshed successfully:', refreshResult.message);
              
              // Update the stored vehicle position with fresh data
              window[`${mapId}_vehiclePosition`] = refreshResult.message;
              
              // Re-render the map with fresh data
              await render_run_sheet_route_map(frm);
              
              frappe.show_alert({
                message: __('Vehicle data refreshed - Ignition: {0}, Speed: {1} km/h', [
                  refreshResult.message.ignition ? 'ON' : 'OFF',
                  refreshResult.message.speed_kph ? refreshResult.message.speed_kph.toFixed(1) : 'N/A'
                ]), 
                indicator: 'green'
              });
            } else {
              console.warn('Vehicle refresh failed:', refreshResult.message);
              frappe.show_alert({
                message: __('Failed to refresh vehicle data: {0}', [refreshResult.message?.error || 'Unknown error']),
                indicator: 'orange'
              });
              
              // Still re-render the map to show current data
              await render_run_sheet_route_map(frm);
            }
          } catch (error) {
            console.error('Error refreshing vehicle data:', error);
            frappe.show_alert({
              message: __('Error refreshing vehicle data: {0}', [error.message || 'Unknown error']),
              indicator: 'red'
            });
            
            // Still re-render the map to show current data
            await render_run_sheet_route_map(frm);
          } finally {
            refreshBtn.innerHTML = '<i class="fa fa-refresh"></i> Refresh Vehicle';
            refreshBtn.disabled = false;
          }
        };
      }
    }, 200);
    
    // Initialize multi-leg route map with vehicle tracking
    setTimeout(() => {
      initializeRunSheetRouteMap(mapId, legs, mapRenderer, frm);
    }, 100);
    
  } catch (error) {
    console.error('Error rendering run sheet route map:', error);
    if ($wrapper && $wrapper.length > 0) {
      $wrapper.html(`
        <div style="padding: 20px; text-align: center; color: #dc3545;">
          <i class="fa fa-exclamation-triangle" style="font-size: 24px; margin-bottom: 10px;"></i>
          <div style="font-weight: 600; margin-bottom: 5px;">Unable to load route map</div>
          <div style="font-size: 12px; color: #6c757d;">${error.message || 'Unknown error'}</div>
        </div>
      `);
    }
  }
}

// Assign sequential letter labels (A, B, C...) to unique locations
// Same locations get the same letter to avoid overlapping markers
function assignLocationLabels(legCoords) {
  const locationMap = new Map(); // Maps coordinate key to letter label
  const labelToLocation = new Map(); // Maps letter to coordinate key
  let nextLabelIndex = 0;
  
  // Helper to get coordinate key
  const getCoordKey = (lat, lon) => `${lat.toFixed(6)},${lon.toFixed(6)}`;
  
  // Helper to get letter from index (A, B, C, ..., Z, AA, AB, ...)
  const getLetterLabel = (index) => {
    if (index < 26) {
      return String.fromCharCode(65 + index); // A-Z
    } else {
      const firstLetter = String.fromCharCode(65 + Math.floor((index - 26) / 26));
      const secondLetter = String.fromCharCode(65 + ((index - 26) % 26));
      return firstLetter + secondLetter; // AA, AB, ...
    }
  };
  
  // Process all pick and drop locations
  legCoords.forEach((legData) => {
    const { pick, drop } = legData;
    
    // Process pick location
    const pickKey = getCoordKey(pick.lat, pick.lon);
    if (!locationMap.has(pickKey)) {
      const label = getLetterLabel(nextLabelIndex);
      locationMap.set(pickKey, label);
      labelToLocation.set(label, pickKey);
      nextLabelIndex++;
    }
    
    // Process drop location
    const dropKey = getCoordKey(drop.lat, drop.lon);
    if (!locationMap.has(dropKey)) {
      const label = getLetterLabel(nextLabelIndex);
      locationMap.set(dropKey, label);
      labelToLocation.set(label, dropKey);
      nextLabelIndex++;
    }
  });
  
  // Create mapping for each leg
  const legLabelMap = new Map();
  legCoords.forEach((legData, index) => {
    const pickKey = getCoordKey(legData.pick.lat, legData.pick.lon);
    const dropKey = getCoordKey(legData.drop.lat, legData.drop.lon);
    
    legLabelMap.set(index, {
      pickLabel: locationMap.get(pickKey),
      dropLabel: locationMap.get(dropKey),
      pickKey: pickKey,
      dropKey: dropKey
    });
  });
  
  return {
    locationMap: locationMap, // coordinate key -> letter
    legLabelMap: legLabelMap, // leg index -> {pickLabel, dropLabel, pickKey, dropKey}
    labelToLocation: labelToLocation // letter -> coordinate key
  };
}

// Group leg coordinates for consolidation visualization
function groupLegCoordsForConsolidation(legCoords, isPickConsolidated, isDropConsolidated) {
  if (!isPickConsolidated && !isDropConsolidated) {
    return legCoords;
  }
  
  // For pick consolidated: group by pick address (should be same), show one pick with multiple drops
  if (isPickConsolidated) {
    // Find the common pick address
    const pickCoordsMap = new Map();
    legCoords.forEach(lc => {
      const key = `${lc.pick.lat},${lc.pick.lon}`;
      if (!pickCoordsMap.has(key)) {
        pickCoordsMap.set(key, {
          pick: lc.pick,
          drops: []
        });
      }
      pickCoordsMap.get(key).drops.push({
        leg: lc.leg,
        drop: lc.drop,
        order: lc.order
      });
    });
    
    // Convert to grouped format: one pick with multiple drops
    const grouped = [];
    pickCoordsMap.forEach((group, pickKey) => {
      // Sort drops by order
      group.drops.sort((a, b) => (a.order || 0) - (b.order || 0));
      
      // Create one entry per drop, all sharing the same pick
      group.drops.forEach((dropData, index) => {
        grouped.push({
          leg: dropData.leg,
          pick: group.pick,
          drop: dropData.drop,
          order: dropData.order,
          isConsolidated: true,
          consolidationType: 'pick',
          dropIndex: index
        });
      });
    });
    
    return grouped.sort((a, b) => (a.order || 0) - (b.order || 0));
  }
  
  // For drop consolidated: group by drop address (should be same), show multiple picks with one drop
  if (isDropConsolidated) {
    // Find the common drop address
    const dropCoordsMap = new Map();
    legCoords.forEach(lc => {
      const key = `${lc.drop.lat},${lc.drop.lon}`;
      if (!dropCoordsMap.has(key)) {
        dropCoordsMap.set(key, {
          drop: lc.drop,
          picks: []
        });
      }
      dropCoordsMap.get(key).picks.push({
        leg: lc.leg,
        pick: lc.pick,
        order: lc.order
      });
    });
    
    // Convert to grouped format: multiple picks with one drop
    const grouped = [];
    dropCoordsMap.forEach((group, dropKey) => {
      // Sort picks by order
      group.picks.sort((a, b) => (a.order || 0) - (b.order || 0));
      
      // Create one entry per pick, all sharing the same drop
      group.picks.forEach((pickData, index) => {
        grouped.push({
          leg: pickData.leg,
          pick: pickData.pick,
          drop: group.drop,
          order: pickData.order,
          isConsolidated: true,
          consolidationType: 'drop',
          pickIndex: index
        });
      });
    });
    
    return grouped.sort((a, b) => (a.order || 0) - (b.order || 0));
  }
  
  return legCoords;
}

// Initialize multi-leg route map
async function initializeRunSheetRouteMap(mapId, legs, mapRenderer, frm) {
  try {
    // Get coordinates for all legs
    const legCoords = [];
    const allCoords = [];
    
    const missingAddresses = [];
    
    // Fetch vehicle position if vehicle is assigned
    let vehiclePosition = null;
    if (frm && frm.doc && frm.doc.vehicle && typeof frm.doc.vehicle === 'string' && frm.doc.vehicle.trim().length > 0) {
      try {
        console.log('Fetching vehicle position for:', frm.doc.vehicle);
        const vehicleData = await frappe.call({
          method: 'logistics.transport.api_vehicle_tracking.get_vehicle_position',
          args: {
            vehicle_name: frm.doc.vehicle.trim()
          }
        });
        
        console.log('Vehicle API response:', vehicleData);
        
        if (vehicleData.message && vehicleData.message.success) {
          vehiclePosition = vehicleData.message;
          console.log('✓ Vehicle position loaded successfully:', vehiclePosition);
          console.log('  Latitude:', vehiclePosition.latitude);
          console.log('  Longitude:', vehiclePosition.longitude);
          console.log('  Speed:', vehiclePosition.speed_kph);
          console.log('  Ignition:', vehiclePosition.ignition);
        } else {
          console.warn('Vehicle position API returned unsuccessful:', vehicleData.message);
          // Show alert to user
          frappe.show_alert({
            message: __('Vehicle tracking data not available: {0}', [vehicleData.message?.error || 'No position data']),
            indicator: 'orange'
          });
        }
      } catch (e) {
        console.error('Error fetching vehicle position:', e);
        frappe.show_alert({
          message: __('Could not fetch vehicle position: {0}', [e.message || 'Unknown error']),
          indicator: 'red'
        });
      }
    } else {
      console.log('No vehicle assigned to this run sheet');
    }
    
    // Fetch Transport Leg details for status badges and consolidation info
    const transportLegDetails = {};
    for (const leg of legs) {
      if (leg.transport_leg) {
        try {
          const legDoc = await frappe.db.get_doc("Transport Leg", leg.transport_leg);
          transportLegDetails[leg.name] = {
            status: legDoc.status,
            start_date: legDoc.start_date,
            end_date: legDoc.end_date,
            pick_consolidated: legDoc.pick_consolidated || 0,
            drop_consolidated: legDoc.drop_consolidated || 0,
            pick_address: legDoc.pick_address,
            drop_address: legDoc.drop_address
          };
        } catch(e) {
          console.warn('Could not fetch leg details:', e);
        }
      }
    }
    
    for (const leg of legs) {
      if (leg.transport_leg) {
        try {
          const legDoc = await frappe.db.get_doc("Transport Leg", leg.transport_leg);
          const pickCoords = await getAddressLatLon(legDoc.pick_address);
          const dropCoords = await getAddressLatLon(legDoc.drop_address);
          
          // Check for missing addresses - only warn if actually missing
          const missing = [];
          if (!legDoc.pick_address) missing.push('Pick Address');
          if (!legDoc.drop_address) missing.push('Drop Address');
          if (!pickCoords && legDoc.pick_address) missing.push('Pick Address Coordinates');
          if (!dropCoords && legDoc.drop_address) missing.push('Drop Address Coordinates');
          
          // Only add to missing list if there are actual missing items
          if (missing.length > 0) {
            missingAddresses.push({
              leg: leg.transport_leg,
              order: leg.order || 0,
              missing: missing,
              pickAddress: legDoc.pick_address || 'Not set',
              dropAddress: legDoc.drop_address || 'Not set'
            });
          }
          
          if (pickCoords && dropCoords) {
            legCoords.push({
              leg: leg,
              pick: pickCoords,
              drop: dropCoords,
              order: leg.order || 0
            });
            allCoords.push(pickCoords, dropCoords);
          } else {
            console.warn('Missing coordinates for leg:', leg.transport_leg, 'Pick:', pickCoords, 'Drop:', dropCoords);
          }
        } catch (e) {
          console.warn(`Could not get coordinates for leg ${leg.transport_leg}:`, e);
          missingAddresses.push({
            leg: leg.transport_leg,
            order: leg.order || 0,
            missing: ['Transport Leg not found'],
            pickAddress: 'Error loading',
            dropAddress: 'Error loading'
          });
        }
      } else {
        console.warn('No transport_leg found for leg:', leg);
        missingAddresses.push({
          leg: 'No Transport Leg linked',
          order: leg.order || 0,
          missing: ['Transport Leg not linked'],
          pickAddress: 'N/A',
          dropAddress: 'N/A'
        });
      }
    }
    
    // Clear any existing warnings first
    clearExistingWarnings(mapId);
    
    // Show missing addresses warning if any
    if (missingAddresses.length > 0) {
      showMissingAddressesWarning(mapId, missingAddresses);
    }
    
    if (legCoords.length === 0) {
      if (missingAddresses.length > 0) {
        showMissingAddressesDisplay(mapId);
      } else {
        showMapFallback(mapId);
      }
      return;
    }
    
    // Sort legs by order
    legCoords.sort((a, b) => (a.order || 0) - (b.order || 0));
    
    // Check for consolidation type from Transport Legs
    let isPickConsolidated = false;
    let isDropConsolidated = false;
    
    if (frm && frm.doc && frm.doc.transport_consolidation) {
      // Check consolidation flags from Transport Legs using already fetched data
      const pickConsolidatedCount = legCoords.filter(lc => {
        if (lc.leg && transportLegDetails[lc.leg.name]) {
          return transportLegDetails[lc.leg.name].pick_consolidated === 1;
        }
        return false;
      }).length;
      
      const dropConsolidatedCount = legCoords.filter(lc => {
        if (lc.leg && transportLegDetails[lc.leg.name]) {
          return transportLegDetails[lc.leg.name].drop_consolidated === 1;
        }
        return false;
      }).length;
      
      // If majority of legs have pick_consolidated, it's pick consolidated
      if (pickConsolidatedCount > 0 && pickConsolidatedCount >= legCoords.length / 2) {
        isPickConsolidated = true;
      }
      
      // If majority of legs have drop_consolidated, it's drop consolidated
      if (dropConsolidatedCount > 0 && dropConsolidatedCount >= legCoords.length / 2) {
        isDropConsolidated = true;
      }
      
      // Also check by address grouping as fallback
      if (!isPickConsolidated && !isDropConsolidated) {
        const pickAddresses = new Set();
        const dropAddresses = new Set();
        
        legCoords.forEach(lc => {
          if (lc.leg && transportLegDetails[lc.leg.name]) {
            const details = transportLegDetails[lc.leg.name];
            if (details.pick_address) pickAddresses.add(details.pick_address);
            if (details.drop_address) dropAddresses.add(details.drop_address);
          }
        });
        
        // Pick consolidated: one pick address, multiple drop addresses
        if (pickAddresses.size === 1 && dropAddresses.size > 1) {
          isPickConsolidated = true;
        }
        // Drop consolidated: multiple pick addresses, one drop address
        else if (pickAddresses.size > 1 && dropAddresses.size === 1) {
          isDropConsolidated = true;
        }
      }
    }
    
    // Group legCoords for consolidation visualization
    let groupedLegCoords = legCoords;
    if (isPickConsolidated || isDropConsolidated) {
      groupedLegCoords = groupLegCoordsForConsolidation(legCoords, isPickConsolidated, isDropConsolidated);
    }
    
    // Assign sequential letter labels to unique locations
    const locationLabels = assignLocationLabels(groupedLegCoords);
    
    // Store labels globally for leg cards to access
    window[`${mapId}_locationLabels`] = locationLabels;
    
    // Update external links with first and last coordinates
    updateExternalLinks(mapId, legCoords);
    
    // Initialize map based on renderer (pass vehicle position for tracking and consolidation info)
    const consolidationInfo = {
      isPickConsolidated: isPickConsolidated,
      isDropConsolidated: isDropConsolidated,
      locationLabels: locationLabels
    };
    
    if (mapRenderer && mapRenderer.toLowerCase() === 'google maps') {
      initializeGoogleRouteMap(mapId, groupedLegCoords, vehiclePosition, frm, consolidationInfo);
    } else if (mapRenderer && mapRenderer.toLowerCase() === 'mapbox') {
      initializeMapboxRouteMap(mapId, groupedLegCoords, vehiclePosition, frm, consolidationInfo);
    } else if (mapRenderer && mapRenderer.toLowerCase() === 'maplibre') {
      initializeMapLibreRouteMap(mapId, groupedLegCoords, vehiclePosition, frm, consolidationInfo);
    } else {
      initializeOpenStreetRouteMap(mapId, groupedLegCoords, vehiclePosition, frm, consolidationInfo);
    }
    
  } catch (error) {
    console.error('Error initializing run sheet route map:', error);
    showMapFallback(mapId);
  }
}

// Update external map links
function updateExternalLinks(mapId, legCoords) {
  if (legCoords.length === 0) return;
  
  // Build waypoints for multi-leg route
  const waypoints = [];
  console.log('Processing legCoords:', legCoords);
  legCoords.forEach((legData, index) => {
    console.log(`Leg ${index + 1}:`, legData);
    waypoints.push(`${legData.pick.lat},${legData.pick.lon}`); // Pickup
    waypoints.push(`${legData.drop.lat},${legData.drop.lon}`); // Drop
  });
  console.log('Final waypoints array:', waypoints);
  
  // Ensure we have at least 4 waypoints for 2 legs
  if (waypoints.length < 4 && legCoords.length >= 2) {
    console.warn('Not enough waypoints for multi-leg route. Expected 4+, got:', waypoints.length);
  }
  
  const firstPick = legCoords[0].pick;
  const lastDrop = legCoords[legCoords.length - 1].drop;
  
  // Google Maps link with waypoints
  const googleLink = document.getElementById(`${mapId}-google-link`);
  if (googleLink) {
    console.log('Waypoints for Google Maps:', waypoints, 'Length:', waypoints.length);
    console.log('Leg coords length:', legCoords.length);
    
    if (waypoints.length === 2 && legCoords.length === 1) {
      // Simple route for single leg (1 pickup + 1 drop)
      console.log('Using simple route for single leg');
      googleLink.href = `https://www.google.com/maps/dir/?api=1&origin=${firstPick.lat},${firstPick.lon}&destination=${lastDrop.lat},${lastDrop.lon}`;
    } else if (waypoints.length >= 4 && legCoords.length >= 2) {
      // Multi-waypoint route (2+ legs = 4+ waypoints)
      const waypointStr = waypoints.slice(1, -1).join('|');
      console.log('Using multi-waypoint route. Waypoint string:', waypointStr);
      googleLink.href = `https://www.google.com/maps/dir/?api=1&origin=${firstPick.lat},${firstPick.lon}&destination=${lastDrop.lat},${lastDrop.lon}&waypoints=${waypointStr}`;
    } else {
      // Fallback: use all waypoints as a single route
      console.log('Using fallback route with all waypoints');
      const allWaypointsStr = waypoints.join('|');
      googleLink.href = `https://www.google.com/maps/dir/?api=1&waypoints=${allWaypointsStr}`;
    }
  }
  
  // OpenStreetMap link with waypoints
  const osmLink = document.getElementById(`${mapId}-osm-link`);
  if (osmLink) {
    if (waypoints.length === 2) {
      // Simple route for single leg
      const osmUrl = `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${waypoints[0]}%3B${waypoints[1]}`;
      osmLink.href = osmUrl;
    } else {
      // OpenStreetMap has limited multi-waypoint support
      // Show route from first pickup to last drop with note
      const osmUrl = `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${firstPick.lat},${firstPick.lon}%3B${lastDrop.lat},${lastDrop.lon}`;
      osmLink.href = osmUrl;
      osmLink.title = 'OpenStreetMap: Shows route from first pickup to last drop (limited multi-waypoint support)';
    }
  }
  
  // Apple Maps link (limited waypoint support)
  const appleLink = document.getElementById(`${mapId}-apple-link`);
  if (appleLink) {
    if (waypoints.length === 2) {
      // Simple route for single leg (1 pickup + 1 drop)
      const appleUrl = `https://maps.apple.com/directions?source=${firstPick.lat},${firstPick.lon}&destination=${lastDrop.lat},${lastDrop.lon}`;
      appleLink.href = appleUrl;
    } else {
      // Apple Maps has limited multi-waypoint support
      // Show route from first pickup to last drop with note
      const appleUrl = `https://maps.apple.com/directions?source=${firstPick.lat},${firstPick.lon}&destination=${lastDrop.lat},${lastDrop.lon}`;
      appleLink.href = appleUrl;
      appleLink.title = 'Apple Maps: Shows route from first pickup to last drop (limited multi-waypoint support)';
    }
  }
}

// Show map fallback display
function showMapFallback(mapId) {
  const fallbackElement = document.getElementById(`${mapId}-fallback`);
  if (fallbackElement) {
    fallbackElement.style.display = 'flex';
  }
}

// Hide map fallback display
function hideMapFallback(mapId) {
  const fallbackElement = document.getElementById(`${mapId}-fallback`);
  if (fallbackElement) {
    fallbackElement.style.display = 'none';
  }
}

// Show missing addresses warning
function showMissingAddressesWarning(mapId, missingAddresses) {
  const mapElement = document.getElementById(mapId);
  if (!mapElement) return;
  
  const warningHtml = `
    <div class="missing-address-warning" style="position: absolute; top: 10px; left: 10px; right: 10px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; padding: 10px; z-index: 1000; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
      <div style="display: flex; align-items: center; margin-bottom: 8px;">
        <i class="fa fa-exclamation-triangle" style="color: #856404; margin-right: 8px;"></i>
        <strong style="color: #856404;">Missing Address Information</strong>
      </div>
      <div style="font-size: 12px; color: #856404;">
        ${missingAddresses.map(item => `
          <div style="margin-bottom: 4px;">
            <strong>Leg ${item.order}:</strong> ${item.leg}<br>
            <small style="color: #6c757d;">
              Missing: ${item.missing.join(', ')}<br>
              Pick: ${item.pickAddress} | Drop: ${item.dropAddress}
            </small>
          </div>
        `).join('')}
        <div style="margin-top: 8px; font-size: 11px; color: #6c757d;">
          <i class="fa fa-info-circle"></i> 
          Complete the Transport Leg addresses to show the full route map.
        </div>
      </div>
    </div>
  `;
  
  mapElement.insertAdjacentHTML('afterbegin', warningHtml);
}

// Show missing addresses display
function showMissingAddressesDisplay(mapId) {
  const missingElement = document.getElementById(`${mapId}-missing-addresses`);
  if (missingElement) {
    missingElement.style.display = 'flex';
  }
}

// Clear any existing warnings
function clearExistingWarnings(mapId) {
  const mapElement = document.getElementById(mapId);
  if (mapElement) {
    // Remove any existing warning overlays
    const existingWarnings = mapElement.querySelectorAll('.missing-address-warning');
    existingWarnings.forEach(warning => warning.remove());
    
    // Remove any warning elements with common warning text
    const allElements = mapElement.querySelectorAll('*');
    allElements.forEach(el => {
      if (el.textContent && el.textContent.includes('Missing Address Information')) {
        el.remove();
      }
    });
    
    // Hide missing addresses display
    const missingElement = document.getElementById(`${mapId}-missing-addresses`);
    if (missingElement) {
      missingElement.style.display = 'none';
    }
  }
}

// Initialize OpenStreetMap for multi-leg route
function initializeOpenStreetRouteMap(mapId, legCoords, vehiclePosition, frm) {
  // Load Leaflet CSS and JS if not already loaded
  if (!window.L) {
    // Load Leaflet CSS
    const leafletCSS = document.createElement('link');
    leafletCSS.rel = 'stylesheet';
    leafletCSS.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    leafletCSS.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
    leafletCSS.crossOrigin = 'anonymous';
    document.head.appendChild(leafletCSS);
    
    // Load Leaflet JS
    const leafletJS = document.createElement('script');
    leafletJS.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    leafletJS.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
    leafletJS.crossOrigin = 'anonymous';
    leafletJS.onload = () => {
      createOpenStreetRouteMap(mapId, legCoords, vehiclePosition, frm);
    };
    document.head.appendChild(leafletJS);
  } else {
    createOpenStreetRouteMap(mapId, legCoords, vehiclePosition, frm);
  }
}

function createOpenStreetRouteMap(mapId, legCoords, vehiclePosition, frm, consolidationInfo = {}) {
  console.log('createOpenStreetRouteMap called with:');
  console.log('  mapId:', mapId);
  console.log('  legCoords:', legCoords);
  console.log('  vehiclePosition:', vehiclePosition);
  console.log('  frm:', frm ? 'present' : 'missing');
  
  const checkElement = () => {
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      try {
        console.log('Map element found, creating map...');
        
        // Calculate bounds
        const allLats = [];
        const allLons = [];
        legCoords.forEach(leg => {
          allLats.push(leg.pick.lat, leg.drop.lat);
          allLons.push(leg.pick.lon, leg.drop.lon);
        });
        
        // Include vehicle position in bounds if available
        console.log('Checking vehicle position for bounds:', vehiclePosition);
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          console.log('✓ Adding vehicle position to bounds');
          allLats.push(vehiclePosition.latitude);
          allLons.push(vehiclePosition.longitude);
        } else {
          console.log('✗ Vehicle position not valid for bounds');
        }
        
        const centerLat = (Math.min(...allLats) + Math.max(...allLats)) / 2;
        const centerLon = (Math.min(...allLons) + Math.max(...allLons)) / 2;
        
        const map = L.map(mapId).setView([centerLat, centerLon], 10);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          maxZoom: 19
        }).addTo(map);
        
        // Add markers and routes for each leg
        const allMarkers = [];
        const allWaypoints = [];
        const locationMarkersMap = new Map(); // Track markers by location key to avoid duplicates
        const locationLegsMap = new Map(); // Track which legs use each location
        
        const locationLabels = consolidationInfo && consolidationInfo.locationLabels;
        
        // First pass: collect all locations and their labels
        legCoords.forEach((legData, index) => {
          const { leg, pick, drop } = legData;
          const pickKey = `${pick.lat.toFixed(6)},${pick.lon.toFixed(6)}`;
          const dropKey = `${drop.lat.toFixed(6)},${drop.lon.toFixed(6)}`;
          
          // Get labels for this leg
          const legLabels = locationLabels ? locationLabels.legLabelMap.get(index) : null;
          const pickLabel = legLabels ? legLabels.pickLabel : '';
          const dropLabel = legLabels ? legLabels.dropLabel : '';
          
          // Track which legs use each location
          if (!locationLegsMap.has(pickKey)) {
            locationLegsMap.set(pickKey, []);
          }
          locationLegsMap.get(pickKey).push({ leg, index, type: 'pick', label: pickLabel });
          
          if (!locationLegsMap.has(dropKey)) {
            locationLegsMap.set(dropKey, []);
          }
          locationLegsMap.get(dropKey).push({ leg, index, type: 'drop', label: dropLabel });
        });
        
        // Second pass: create one marker per unique location
        locationLegsMap.forEach((legsAtLocation, locationKey) => {
          const firstLeg = legsAtLocation[0];
          const isConsolidated = legsAtLocation.length > 1;
          const [lat, lon] = locationKey.split(',').map(Number);
          const isPick = firstLeg.type === 'pick';
          const label = firstLeg.label || '';
          
          // Create marker with letter label
          const marker = L.marker([lat, lon], {
            icon: L.divIcon({
              className: 'custom-div-icon',
              html: `<div style="background-color: ${isPick ? 'red' : 'green'}; width: ${isConsolidated ? '24' : '20'}px; height: ${isConsolidated ? '24' : '20'}px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: ${isConsolidated ? '12' : '10'}px;">${label}</div>`,
              iconSize: [isConsolidated ? 24 : 20, isConsolidated ? 24 : 20],
              iconAnchor: [isConsolidated ? 12 : 10, isConsolidated ? 12 : 10]
            })
          }).addTo(map);
          
          // Build popup content with all legs at this location
          const locationType = isPick ? 'Pickup' : 'Drop';
          const locationTypePlural = isPick ? 'Pickups' : 'Drops';
          let popupContent = `<strong>${isConsolidated ? `Consolidated ${locationTypePlural}` : `${locationType} (${label})`}</strong><br>`;
          
          legsAtLocation.forEach(({ leg, index }) => {
            popupContent += `Leg ${index + 1}: ${leg.transport_leg || 'N/A'}<br>`;
          });
          
          popupContent += `Coordinates: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
          marker.bindPopup(popupContent);
          
          locationMarkersMap.set(locationKey, marker);
          allMarkers.push(marker);
        });
        
        // Third pass: add route lines between locations
        // First, add route from vehicle position to first pickup (if vehicle exists)
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude && legCoords.length > 0) {
          const firstPick = legCoords[0].pick;
          const vehicleToFirstPick = L.polyline([
            [vehiclePosition.latitude, vehiclePosition.longitude],
            [firstPick.lat, firstPick.lon]
          ], {
            color: '#007bff', // Blue
            weight: 4,
            opacity: 0.8,
            dashArray: '8, 4'
          }).addTo(map);
          
          vehicleToFirstPick.bindPopup(`
            <strong>Route to First Pickup</strong><br>
            From vehicle to pickup location A
          `);
        }
        
        // Add route lines for each leg (pick to drop)
        legCoords.forEach((legData, index) => {
          const { leg, pick, drop } = legData;
          
          // Add route line from pick to drop
          const routeLine = L.polyline([
            [pick.lat, pick.lon],
            [drop.lat, drop.lon]
          ], {
            color: index === 0 ? '#007bff' : '#ff9800', // Blue for first leg, orange for others
            weight: index === 0 ? 5 : 4, // Thicker for first leg
            opacity: index === 0 ? 0.9 : 0.7,
            dashArray: index === 0 ? '8, 4' : '10, 5'
          }).addTo(map);
          
          routeLine.bindPopup(`
            <strong>Leg ${index + 1}</strong><br>
            ${leg.transport_leg || 'N/A'}
          `);
          
          allWaypoints.push([pick.lat, pick.lon], [drop.lat, drop.lon]);
        });
        
        // Add connecting lines between consecutive legs (drop of leg N to pick of leg N+1)
        for (let i = 0; i < legCoords.length - 1; i++) {
          const currentDrop = legCoords[i].drop;
          const nextPick = legCoords[i + 1].pick;
          
          // Only draw connecting line if drop and next pick are different locations
          const dropKey = `${currentDrop.lat.toFixed(6)},${currentDrop.lon.toFixed(6)}`;
          const pickKey = `${nextPick.lat.toFixed(6)},${nextPick.lon.toFixed(6)}`;
          
          if (dropKey !== pickKey) {
            const connectingLine = L.polyline([
              [currentDrop.lat, currentDrop.lon],
              [nextPick.lat, nextPick.lon]
            ], {
              color: '#9c27b0', // Purple
              weight: 3,
              opacity: 0.6,
              dashArray: '6, 6'
            }).addTo(map);
            
            connectingLine.bindPopup(`
              <strong>Connecting Route</strong><br>
              From Leg ${i + 1} drop to Leg ${i + 2} pickup
            `);
          }
        }
        
        // Add overall route line connecting all waypoints in sequence (as backup/overview)
        if (allWaypoints.length > 2) {
          const overallRoute = L.polyline(allWaypoints, {
            color: '#6c757d', // Gray - less prominent
            weight: 2,
            opacity: 0.4,
            dashArray: '20, 10'
          }).addTo(map);
          
          // Add route info popup
          overallRoute.bindPopup(`
            <strong>Complete Route Overview</strong><br>
            ${legCoords.length} transport legs<br>
            ${allWaypoints.length} total stops<br>
            <small>Click external links for turn-by-turn directions</small>
          `);
        }
        
        // Add vehicle/truck marker if position is available
        console.log('=== TRUCK MARKER SECTION ===');
        console.log('Checking if we should add truck marker...');
        console.log('vehiclePosition exists?', !!vehiclePosition);
        console.log('vehiclePosition.latitude?', vehiclePosition?.latitude);
        console.log('vehiclePosition.longitude?', vehiclePosition?.longitude);
        console.log('Full vehiclePosition:', vehiclePosition);
        
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          console.log('✓ CONDITION MET - Adding truck marker at:', vehiclePosition.latitude, vehiclePosition.longitude);
          
          const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
          const vehicleState = getVehicleState(vehiclePosition);
          const stateDisplay = getVehicleStateDisplay(vehicleState);
          const ignition = stateDisplay.text;
          // Truck icon color based on state: green when ON, amber when IDLE, gray when OFF
          const truckIconColor = stateDisplay.color;
          const truckLabelColor = stateDisplay.labelColor;
          
          // Font Awesome truck in white circle
          const truckIcon = L.divIcon({
            className: 'custom-truck-marker',
            html: `
              <div style="position: relative; width: 80px; height: 68px;">
                <!-- Ignition status card (above truck) -->
                <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: ${stateDisplay.bgColor}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 9px; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                  Ignition: ${ignition}
                </div>
                
                <!-- White circle with truck icon (color based on state) -->
                <div style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 40px; height: 40px; background: white; border-radius: 50%; border: 2px solid ${truckIconColor}; box-shadow: 0 3px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                  <i class="fa fa-truck" style="color: ${truckIconColor}; font-size: 20px;"></i>
                  <!-- Small state indicator circle -->
                  <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; background: ${stateDisplay.statusColor}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
                </div>
                
                <!-- Vehicle name label (below truck, color based on ignition) -->
                <div style="position: absolute; top: 62px; left: 50%; transform: translateX(-50%); background: white; color: ${truckLabelColor}; padding: 2px 8px; border-radius: 3px; white-space: nowrap; font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid ${truckIconColor};">
                  ${vehicleName}
                </div>
              </div>
            `,
            iconSize: [80, 68],
            iconAnchor: [40, 34]
          });
          
          console.log('Creating L.marker with icon...');
          const truckMarker = L.marker([vehiclePosition.latitude, vehiclePosition.longitude], {
            icon: truckIcon,
            zIndexOffset: 10000,  // Ensure it's on top
            riseOnHover: true,
            title: `${vehicleName} - Current Location`
          }).addTo(map);
          
          console.log('✓ L.marker created and added to map');
          
          // Add detailed popup for truck
          const speedDisplay = vehiclePosition.speed_kph ? `${vehiclePosition.speed_kph.toFixed(1)} km/h` : 'N/A';
          const timestampDisplay = vehiclePosition.timestamp || 'N/A';
          const odometerDisplay = vehiclePosition.odometer_km ? `${vehiclePosition.odometer_km.toFixed(1)} km` : null;
          
          console.log('Creating truck popup...');
          console.log('Vehicle position fuel_level:', vehiclePosition.fuel_level);
          console.log('Vehicle position odometer_km:', vehiclePosition.odometer_km);
          const fuelDisplay = vehiclePosition.fuel_level ? `${vehiclePosition.fuel_level}%` : null;
          
          truckMarker.bindPopup(`
            <div style="padding: 6px;">
              <div style="font-weight: 600; font-size: 13px; color: #007bff; margin-bottom: 8px;">${vehicleName}</div>
              <div style="font-size: 11px; color: #6b7280; line-height: 1.6;">
                <strong>Ignition:</strong> <span style="color: ${stateDisplay.color}; font-weight: 600;">${ignition}</span><br>
                ${speedDisplay !== 'N/A' ? `<strong>Speed:</strong> ${speedDisplay}<br>` : ''}
                ${fuelDisplay ? `<strong>Fuel:</strong> ${fuelDisplay}<br>` : ''}
                ${odometerDisplay ? `<strong>Mileage:</strong> ${odometerDisplay}<br>` : ''}
                <span style="font-size: 10px; color: #9ca3af;">${timestampDisplay}</span>
              </div>
            </div>
          `);
          
          console.log('Adding truck marker to markers array...');
          allMarkers.push(truckMarker);
          console.log('Total markers now:', allMarkers.length);
          
          console.log('✓✓✓ TRUCK MARKER ADDED SUCCESSFULLY TO MAP! ✓✓✓');
          console.log('  Truck coordinates:', vehiclePosition.latitude, vehiclePosition.longitude);
          console.log('  Look for: Blue square with truck icon and vehicle name label');
          
          // Store map and truck marker reference for locate button
          window[`${mapId}_map`] = map;
          window[`${mapId}_truckMarker`] = truckMarker;
          window[`${mapId}_vehiclePosition`] = vehiclePosition;
          
          // Setup locate truck button
          setTimeout(() => {
            const locateBtn = document.getElementById(`${mapId}-locate-vehicle`);
            if (locateBtn) {
              locateBtn.onclick = async () => {
                console.log('Locating truck on map...');
                locateBtn.innerHTML = '<i class="fa fa-spin fa-spinner"></i> Locating...';
                locateBtn.disabled = true;
                
                try {
                  // Validate vehicle name before making API call
                  if (!frm || !frm.doc || !frm.doc.vehicle || typeof frm.doc.vehicle !== 'string' || frm.doc.vehicle.trim().length === 0) {
                    frappe.show_alert({
                      message: __('No vehicle assigned to locate'),
                      indicator: 'orange'
                    });
                    locateBtn.innerHTML = '<i class="fa fa-location-arrow"></i> Locate';
                    locateBtn.disabled = false;
                    return;
                  }
                  
                  // First refresh vehicle data to get latest position and ignition status
                  const refreshResult = await frappe.call({
                    method: 'logistics.transport.api_vehicle_tracking.refresh_vehicle_data',
                    args: {
                      vehicle_name: frm.doc.vehicle.trim()
                    }
                  });
                  
                  let currentPosition = vehiclePosition;
                  let refreshMessage = '';
                  
                  if (refreshResult.message && refreshResult.message.success) {
                    console.log('✓ Vehicle data refreshed for location:', refreshResult.message);
                    currentPosition = refreshResult.message;
                    
                    // Update stored position
                    window[`${mapId}_vehiclePosition`] = currentPosition;
                    
                    const freshState = getVehicleState(currentPosition);
                    const freshStateDisplay = getVehicleStateDisplay(freshState);
                    refreshMessage = ` - Ignition: ${freshStateDisplay.text}, Speed: ${currentPosition.speed_kph ? currentPosition.speed_kph.toFixed(1) : 'N/A'} km/h`;
                  } else {
                    console.warn('Could not refresh vehicle data, using cached position');
                    refreshMessage = ' (using cached position)';
                  }
                  
                  const storedMap = window[`${mapId}_map`];
                  const storedMarker = window[`${mapId}_truckMarker`];
                  
                  if (storedMap && currentPosition) {
                    // Update marker position if we have fresh data
                    if (refreshResult.message && refreshResult.message.success) {
                      storedMarker.setLatLng([currentPosition.latitude, currentPosition.longitude]);
                      
                      // Update marker icon color based on vehicle state
                      const freshState = getVehicleState(currentPosition);
                      const freshStateDisplay = getVehicleStateDisplay(freshState);
                      const freshTruckIconColor = freshStateDisplay.color;
                      const freshTruckLabelColor = freshStateDisplay.labelColor;
                      const freshIgnition = freshStateDisplay.text;
                      const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
                      
                      // Recreate icon with updated colors
                      const freshTruckIcon = L.divIcon({
                        className: 'custom-truck-marker',
                        html: `
                          <div style="position: relative; width: 80px; height: 68px;">
                            <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: ${freshStateDisplay.bgColor}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 9px; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                              Ignition: ${freshIgnition}
                            </div>
                            <div style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 40px; height: 40px; background: white; border-radius: 50%; border: 2px solid ${freshTruckIconColor}; box-shadow: 0 3px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                              <i class="fa fa-truck" style="color: ${freshTruckIconColor}; font-size: 20px;"></i>
                              <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; background: ${freshStateDisplay.statusColor}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
                            </div>
                            <div style="position: absolute; top: 62px; left: 50%; transform: translateX(-50%); background: white; color: ${freshTruckLabelColor}; padding: 2px 8px; border-radius: 3px; white-space: nowrap; font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid ${freshTruckIconColor};">
                              ${vehicleName}
                            </div>
                          </div>
                        `,
                        iconSize: [80, 68],
                        iconAnchor: [40, 34]
                      });
                      storedMarker.setIcon(freshTruckIcon);
                      
                      // Update marker popup with fresh data
                      const speedDisplay = currentPosition.speed_kph ? `${currentPosition.speed_kph.toFixed(1)} km/h` : 'N/A';
                      const fuelDisplay = currentPosition.fuel_level ? `${currentPosition.fuel_level}%` : null;
                      const odometerDisplay = currentPosition.odometer_km ? `${currentPosition.odometer_km.toFixed(1)} km` : null;
                      const ignition = freshStateDisplay.text;
                      
                      storedMarker.setPopupContent(`
                        <div style="padding: 6px;">
                          <div style="font-weight: 600; font-size: 13px; color: #007bff; margin-bottom: 8px;">${vehicleName}</div>
                          <div style="font-size: 11px; color: #6b7280; line-height: 1.6;">
                            <strong>Ignition:</strong> <span style="color: ${freshStateDisplay.color}; font-weight: 600;">${ignition}</span><br>
                            ${speedDisplay !== 'N/A' ? `<strong>Speed:</strong> ${speedDisplay}<br>` : ''}
                            ${fuelDisplay ? `<strong>Fuel:</strong> ${fuelDisplay}<br>` : ''}
                            ${odometerDisplay ? `<strong>Mileage:</strong> ${odometerDisplay}<br>` : ''}
                            <span style="font-size: 10px; color: #9ca3af;">${currentPosition.timestamp || 'N/A'}</span>
                          </div>
                        </div>
                      `);
                    }
                    
                    // Pan to truck location
                    storedMap.setView([currentPosition.latitude, currentPosition.longitude], 15, {
                      animate: true,
                      duration: 1
                    });
                    
                    // Open popup
                    storedMarker.openPopup();
                    
                    // Add temporary highlight
                    locateBtn.innerHTML = '<i class="fa fa-check"></i>';
                    locateBtn.style.background = '#10b981';
                    
                    setTimeout(() => {
                      locateBtn.innerHTML = '<i class="fa fa-location-arrow"></i> Locate';
                      locateBtn.style.background = '#2563eb';
                    }, 1500);
                    
                    frappe.show_alert({
                      message: __('Truck located at {0}, {1}{2}', [
                        currentPosition.latitude.toFixed(5),
                        currentPosition.longitude.toFixed(5),
                        refreshMessage
                      ]),
                      indicator: 'green'
                    });
                  } else {
                    frappe.show_alert({
                      message: __('Could not locate truck on map'),
                      indicator: 'red'
                    });
                  }
                } catch (error) {
                  console.error('Error locating truck:', error);
                  frappe.show_alert({
                    message: __('Error locating truck: {0}', [error.message || 'Unknown error']),
                    indicator: 'red'
                  });
                } finally {
                  locateBtn.innerHTML = '<i class="fa fa-location-arrow"></i> Locate';
                  locateBtn.disabled = false;
                }
              };
              
              // Enable the button
              locateBtn.disabled = false;
              locateBtn.style.opacity = '1';
              console.log('✓ Locate truck button enabled');
            }
          }, 500);
          
        } else {
          console.log('ℹ️ Vehicle position not available for mapping');
          if (frm && frm.doc && frm.doc.vehicle) {
            console.log('  Vehicle assigned:', frm.doc.vehicle);
            console.log('  Reason: No telematics data or coordinates missing');
            console.log('  To fix: Ensure vehicle has telematics configured and position data available');
          } else {
            console.log('  No vehicle assigned to this run sheet');
          }
          
          // Hide locate button if no vehicle position
          setTimeout(() => {
            const locateBtn = document.getElementById(`${mapId}-locate-vehicle`);
            if (locateBtn) {
              locateBtn.style.display = 'none';
            }
          }, 100);
        }
        
        // Fit map to show all markers
        if (allMarkers.length > 0) {
          const group = new L.featureGroup(allMarkers);
          map.fitBounds(group.getBounds().pad(0.1));
        }
        
        // Hide fallback when map loads successfully
        hideMapFallback(mapId);
        
      } catch (error) {
        console.error('Error creating OpenStreetMap route:', error);
        // Keep fallback visible on error
      }
    } else {
      // Retry after a short delay
      setTimeout(checkElement, 100);
    }
  };
  
  checkElement();
}

// Initialize Google Maps for multi-leg route
function initializeGoogleRouteMap(mapId, legCoords, vehiclePosition, frm, consolidationInfo = {}) {
  const firstPick = legCoords[0].pick;
  const lastDrop = legCoords[legCoords.length - 1].drop;
  
  // Get API key from settings
  frappe.call({
    method: 'logistics.transport.api_vehicle_tracking.get_google_maps_api_key'
  }).then(response => {
    const apiKey = response.message?.api_key;
    
    if (apiKey && apiKey.length > 10) {
      // Load Google Maps JavaScript API if not already loaded
      if (window.google && window.google.maps && window.google.maps.DirectionsService) {
        // Build waypoints from leg coordinates (Google Maps is already loaded)
        const waypoints = [];
        legCoords.forEach(legData => {
          waypoints.push(new google.maps.LatLng(legData.pick.lat, legData.pick.lon));
          waypoints.push(new google.maps.LatLng(legData.drop.lat, legData.drop.lon));
        });
        
        const origin = new google.maps.LatLng(firstPick.lat, firstPick.lon);
        const destination = new google.maps.LatLng(lastDrop.lat, lastDrop.lon);
        
        initializeInteractiveGoogleMapWithDirections(mapId, origin, destination, waypoints, vehiclePosition, frm, apiKey, legCoords, consolidationInfo);
      } else {
        // Load Google Maps JavaScript API with directions library
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=geometry,directions`;
        script.async = true;
        script.defer = true;
        script.onload = () => {
          // Build waypoints from leg coordinates (after Google Maps loads)
          const waypoints = [];
          legCoords.forEach(legData => {
            waypoints.push(new google.maps.LatLng(legData.pick.lat, legData.pick.lon));
            waypoints.push(new google.maps.LatLng(legData.drop.lat, legData.drop.lon));
          });
          
          const origin = new google.maps.LatLng(firstPick.lat, firstPick.lon);
          const destination = new google.maps.LatLng(lastDrop.lat, lastDrop.lon);
          
          initializeInteractiveGoogleMapWithDirections(mapId, origin, destination, waypoints, vehiclePosition, frm, apiKey, legCoords, consolidationInfo);
        };
        script.onerror = () => {
          console.warn('Failed to load Google Maps JavaScript API, showing fallback');
          showMapFallback(mapId);
        };
        document.head.appendChild(script);
      }
    } else {
      console.warn('Google Maps API key not configured, showing fallback');
      showMapFallback(mapId);
    }
  }).catch(() => {
    showMapFallback(mapId);
  });
}

// Initialize interactive Google Maps with DirectionsService
function initializeInteractiveGoogleMapWithDirections(mapId, origin, destination, waypoints, vehiclePosition, frm, apiKey, legCoords = [], consolidationInfo = {}) {
  const mapElement = document.getElementById(mapId);
  if (!mapElement) return;
  
  // Clear any existing content
  mapElement.innerHTML = '';
  
  // Determine initial map center (use vehicle position if available, otherwise use origin)
  let mapCenter = origin;
  if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
    mapCenter = new google.maps.LatLng(vehiclePosition.latitude, vehiclePosition.longitude);
  }
  
  // Initialize the map
  const bounds = new google.maps.LatLngBounds();
  const map = new google.maps.Map(mapElement, {
    zoom: 10,
    center: mapCenter,
    mapTypeControl: true,
    streetViewControl: true,
    fullscreenControl: true,
    zoomControl: true,
    scaleControl: true,
    rotateControl: true
  });
  
  // Store map instance globally
  if (!window.runSheetMaps) window.runSheetMaps = {};
  window.runSheetMaps[mapId] = map;
  
  // Determine route origin (use vehicle position if available, otherwise use first pickup)
  let routeOrigin = origin;
  if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
    routeOrigin = new google.maps.LatLng(vehiclePosition.latitude, vehiclePosition.longitude);
  }
  
  // Store route data globally
  if (!window.runSheetRouteData) window.runSheetRouteData = {};
  window.runSheetRouteData[mapId] = {
    origin: routeOrigin, // Store the actual route origin (vehicle position or first pickup)
    originalOrigin: origin, // Store the original first pickup for reference
    destination: destination,
    waypoints: waypoints,
    activeRouteIndex: 0,
    directionsRenderer: null,
    directionsService: new google.maps.DirectionsService(),
    routePolylines: [],
    vehicleMarker: null,
    vehiclePosition: vehiclePosition,
    deviationCheckInterval: null,
    frm: frm
  };
  
  const routeData = window.runSheetRouteData[mapId];
  
  // Create directions renderer
  routeData.directionsRenderer = new google.maps.DirectionsRenderer({
    map: map,
    suppressMarkers: false,
    preserveViewport: false
  });
  
  // Add markers for all unique locations with letter labels
  const locationMarkersMap = new Map();
  const locationLegsMap = new Map();
  const locationLabels = consolidationInfo.locationLabels;
  
  if (legCoords && legCoords.length > 0 && locationLabels) {
    // First pass: collect all locations
    legCoords.forEach((legData, index) => {
      const { leg, pick, drop } = legData;
      const pickKey = `${pick.lat.toFixed(6)},${pick.lon.toFixed(6)}`;
      const dropKey = `${drop.lat.toFixed(6)},${drop.lon.toFixed(6)}`;
      
      const legLabels = locationLabels.legLabelMap.get(index);
      const pickLabel = legLabels ? legLabels.pickLabel : '';
      const dropLabel = legLabels ? legLabels.dropLabel : '';
      
      if (!locationLegsMap.has(pickKey)) {
        locationLegsMap.set(pickKey, []);
      }
      locationLegsMap.get(pickKey).push({ leg, index, type: 'pick', label: pickLabel });
      
      if (!locationLegsMap.has(dropKey)) {
        locationLegsMap.set(dropKey, []);
      }
      locationLegsMap.get(dropKey).push({ leg, index, type: 'drop', label: dropLabel });
    });
    
    // Second pass: create one marker per unique location
    locationLegsMap.forEach((legsAtLocation, locationKey) => {
      const firstLeg = legsAtLocation[0];
      const isConsolidated = legsAtLocation.length > 1;
      const [lat, lon] = locationKey.split(',').map(Number);
      const isPick = firstLeg.type === 'pick';
      const label = firstLeg.label || '';
      
      const marker = new google.maps.Marker({
        position: { lat: lat, lng: lon },
        map: map,
        label: {
          text: label,
          color: 'white',
          fontSize: '11px',
          fontWeight: 'bold'
        },
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: isConsolidated ? 10 : 8,
          fillColor: isPick ? '#dc3545' : '#28a745',
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2
        },
        title: `${isPick ? 'Pickup' : 'Drop'} (${label})`
      });
      
      const locationType = isPick ? 'Pickup' : 'Drop';
      const locationTypePlural = isPick ? 'Pickups' : 'Drops';
      let infoContent = `<strong>${isConsolidated ? `Consolidated ${locationTypePlural}` : `${locationType} (${label})`}</strong><br>`;
      
      legsAtLocation.forEach(({ leg, index }) => {
        infoContent += `Leg ${index + 1}: ${leg.transport_leg || 'N/A'}<br>`;
      });
      
      infoContent += `Coordinates: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
      
      const infoWindow = new google.maps.InfoWindow({
        content: infoContent
      });
      
      marker.addListener('click', () => {
        infoWindow.open(map, marker);
      });
      
      locationMarkersMap.set(locationKey, marker);
      bounds.extend({ lat: lat, lng: lon });
    });
  } else {
    // Fallback: Add start and end markers
    const startMarker = new google.maps.Marker({
      position: origin,
      map: map,
      label: 'A',
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 8,
        fillColor: '#ff0000',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2
      },
      title: 'Start Location'
    });
    bounds.extend(origin);
    
    const endMarker = new google.maps.Marker({
      position: destination,
      map: map,
      label: 'B',
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 8,
        fillColor: '#00ff00',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2
      },
      title: 'End Location'
    });
    bounds.extend(destination);
  }
  
  // Use vehicle position as origin if available, so route starts from truck icon
  // routeOrigin is already set above when initializing routeData
  let routeWaypoints = waypoints.length > 2 ? waypoints.slice(1, -1).map(wp => ({ location: wp, stopover: true })) : [];
  
  if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
    // Include all waypoints since we're starting from vehicle position, not first pickup
    routeWaypoints = waypoints.length > 0 ? waypoints.map(wp => ({ location: wp, stopover: true })) : [];
    console.log('Using vehicle position as route origin:', vehiclePosition.latitude, vehiclePosition.longitude);
  }
  
  // Request routes with alternatives
  const request = {
    origin: routeData.origin, // Use the route origin (vehicle position or first pickup)
    destination: destination,
    waypoints: routeWaypoints,
    provideRouteAlternatives: true,
    travelMode: google.maps.TravelMode.DRIVING,
    optimizeWaypoints: false
  };
  
  console.log('Requesting routes with alternatives:', request);
  
  routeData.directionsService.route(request, (result, status) => {
    if (status === google.maps.DirectionsStatus.OK) {
      console.log(`✓ Received ${result.routes.length} route(s) from DirectionsService`);
      
      // Log route details for debugging
      result.routes.forEach((route, idx) => {
        const hasOverviewPath = route.overview_path && (route.overview_path.getLength ? route.overview_path.getLength() > 0 : route.overview_path.length > 0);
        const hasLegs = route.legs && route.legs.length > 0;
        console.log(`  Route ${idx}: overview_path=${hasOverviewPath}, legs=${hasLegs}, distance=${route.legs ? route.legs.reduce((sum, leg) => sum + leg.distance.value, 0) / 1000 : 'N/A'}km`);
      });
      
      // Store routes globally
      if (!window.runSheetRoutes) window.runSheetRoutes = {};
      window.runSheetRoutes[mapId] = result.routes;
      
      // Get saved route index or default to 0
      const savedRouteIndex = frm && frm.doc && frm.doc.selected_route_index !== undefined ? frm.doc.selected_route_index : null;
      let activeRouteIndex = 0;
      if (savedRouteIndex !== null && savedRouteIndex >= 0 && savedRouteIndex < result.routes.length) {
        activeRouteIndex = savedRouteIndex;
      } else if (savedRouteIndex !== null) {
        // Saved index is out of range - log warning and use default
        console.warn(`Saved route index ${savedRouteIndex} is out of range for ${result.routes.length} routes. Using default route 0.`);
        activeRouteIndex = 0;
      }
      
      routeData.activeRouteIndex = activeRouteIndex;
      
      // Render all routes (primary in blue, alternatives in gray)
      renderAllRoutes(mapId, result.routes, activeRouteIndex, map, bounds);
      
      // Create route selector UI
      createRouteSelectorUI(mapId, result.routes, activeRouteIndex, frm);
      
      // Add vehicle marker and tracking
      addVehicleMarkerAndTracking(mapId, vehiclePosition, frm, map, bounds);
      
      // Start deviation monitoring
      startDeviationMonitoring(mapId, frm);
      
      // Fit map to show all routes
      map.fitBounds(bounds);
      
      // Hide fallback
      hideMapFallback(mapId);
    } else {
      console.error('DirectionsService failed:', status);
      frappe.show_alert({
        message: __('Failed to get routes: {0}', [status]),
        indicator: 'red'
      });
      showMapFallback(mapId);
    }
  });
}

// Render all routes (primary in blue, alternatives in gray)
function renderAllRoutes(mapId, routes, activeRouteIndex, map, bounds) {
  const routeData = window.runSheetRouteData[mapId];
  if (!routeData) return;
  
  // Clear existing polylines first
  console.log(`Clearing ${routeData.routePolylines.length} existing route polylines...`);
  routeData.routePolylines.forEach(polylineData => {
    if (polylineData.polyline) {
      polylineData.polyline.setMap(null);
    }
  });
  routeData.routePolylines = [];
  
  // Clear directions renderer before drawing new routes
  if (routeData.directionsRenderer) {
    routeData.directionsRenderer.setDirections({ routes: [] });
  }
  
  // Draw new route polylines
  routes.forEach((route, index) => {
    const isActive = index === activeRouteIndex;
    
    // Create polyline for this route
    // overview_path is an MVCArray of LatLng objects
    const routePath = [];
    
    // Try to get path from overview_path first (most efficient)
    if (route.overview_path) {
      try {
        // Handle MVCArray by converting to array
        const pathLength = route.overview_path.getLength();
        if (pathLength > 0) {
          for (let i = 0; i < pathLength; i++) {
            const point = route.overview_path.getAt(i);
            routePath.push(point);
            if (bounds) {
              bounds.extend(point);
            }
          }
        }
      } catch (e) {
        // If overview_path is not an MVCArray, try as regular array
        if (Array.isArray(route.overview_path) && route.overview_path.length > 0) {
          route.overview_path.forEach(point => {
            routePath.push(point);
            if (bounds) {
              bounds.extend(point);
            }
          });
        }
      }
    }
    
    // Fallback: build path from route legs if overview_path is not available or empty
    if (routePath.length === 0 && route.legs && route.legs.length > 0) {
      console.log(`Route ${index} has no overview_path, building from legs...`);
      route.legs.forEach((leg, legIndex) => {
        if (leg.steps && leg.steps.length > 0) {
          leg.steps.forEach(step => {
            if (step.path) {
              try {
                // Handle MVCArray
                const stepPathLength = step.path.getLength();
                if (stepPathLength > 0) {
                  for (let i = 0; i < stepPathLength; i++) {
                    const point = step.path.getAt(i);
                    routePath.push(point);
                    if (bounds) {
                      bounds.extend(point);
                    }
                  }
                }
              } catch (e) {
                // If step.path is not an MVCArray, try as regular array
                if (Array.isArray(step.path) && step.path.length > 0) {
                  step.path.forEach(point => {
                    routePath.push(point);
                    if (bounds) {
                      bounds.extend(point);
                    }
                  });
                }
              }
            }
          });
        } else if (leg.start_location && leg.end_location) {
          // If no steps, just use start and end locations
          routePath.push(leg.start_location);
          routePath.push(leg.end_location);
          if (bounds) {
            bounds.extend(leg.start_location);
            bounds.extend(leg.end_location);
          }
        }
      });
    }
    
    // Skip if no valid path was found
    if (routePath.length === 0) {
      console.warn(`Route ${index} has no valid path data, skipping polyline creation`);
      return;
    }
    
    const polyline = new google.maps.Polyline({
      path: routePath,
      geodesic: true,
      strokeColor: isActive ? '#007bff' : '#6c757d', // Blue for primary, gray for alternatives
      strokeOpacity: isActive ? 1.0 : 0.6,
      strokeWeight: isActive ? 6 : 4,
      map: map,
      zIndex: isActive ? 2 : 1,
      clickable: true
    });
    
    // Add click handler for alternative routes (gray routes)
    if (!isActive) {
      // Store original style for hover effects
      const originalWeight = 4;
      const originalOpacity = 0.6;
      
      polyline.addListener('click', (event) => {
        const frm = routeData.frm;
        console.log(`Clicked on alternative route ${index + 1}, setting as active`);
        if (frm && frm.doc && frm.doc.name) {
          window.selectRouteByIndex(mapId, index, frm.doc.name);
        } else {
          // Still allow selection even if frm is not available
          window.selectRouteByIndex(mapId, index, null);
        }
      });
      
      // Add hover effect to show route is clickable
      polyline.addListener('mouseover', () => {
        polyline.setOptions({
          strokeWeight: 5,
          strokeOpacity: 0.9,
          strokeColor: '#5a6268' // Slightly darker gray on hover
        });
        // Change cursor to pointer
        if (map.getDiv()) {
          map.getDiv().style.cursor = 'pointer';
        }
      });
      
      polyline.addListener('mouseout', () => {
        polyline.setOptions({
          strokeWeight: originalWeight,
          strokeOpacity: originalOpacity,
          strokeColor: '#6c757d' // Back to original gray
        });
        // Reset cursor
        if (map.getDiv()) {
          map.getDiv().style.cursor = '';
        }
      });
    } else {
      // For active route, show it's not clickable (already selected)
      polyline.addListener('mouseover', () => {
        if (map.getDiv()) {
          map.getDiv().style.cursor = 'default';
        }
      });
      
      polyline.addListener('mouseout', () => {
        if (map.getDiv()) {
          map.getDiv().style.cursor = '';
        }
      });
    }
    
    routeData.routePolylines.push({
      polyline: polyline,
      routeIndex: index,
      route: route
    });
  });
  
  // Set active route in directions renderer (this will also add route markers)
  // Only set directions renderer for the active route to avoid interfering with alternative route polylines
  if (routes[activeRouteIndex] && routeData.directionsRenderer) {
    // Suppress markers for alternative routes - we only want markers for the active route
    routeData.directionsRenderer.setOptions({
      suppressMarkers: false, // Show markers for active route
      preserveViewport: false
    });
    
    routeData.directionsRenderer.setDirections({
      routes: [routes[activeRouteIndex]],
      request: null
    });
  }
  
  // Log route rendering summary
  const renderedCount = routeData.routePolylines.length;
  console.log(`✓ Rendered ${renderedCount} route polyline(s) out of ${routes.length} route(s), active route index: ${activeRouteIndex}`);
  
  if (renderedCount < routes.length) {
    console.warn(`⚠️ Some routes could not be rendered (${routes.length - renderedCount} missing)`);
  }
}

// Create route selector UI
function createRouteSelectorUI(mapId, routes, activeRouteIndex, frm) {
  const mapElement = document.getElementById(mapId);
  if (!mapElement) {
    console.warn(`Map element not found for ${mapId}`);
    return;
  }
  
  if (!routes || routes.length <= 1) {
    // Remove existing selector if there's only one route or no routes
    const existingSelector = mapElement.querySelector('.route-selector-ui');
    if (existingSelector) existingSelector.remove();
    return;
  }
  
  // Remove existing selector if any (search in parent container too)
  const existingSelector = mapElement.querySelector('.route-selector-ui') || 
                           mapElement.parentElement?.querySelector('.route-selector-ui');
  if (existingSelector) {
    existingSelector.remove();
  }
  
  const routeSelectorHtml = `
    <div class="route-selector-ui" style="position: absolute; top: 10px; left: 10px; background: white; padding: 10px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); z-index: 100; max-width: 300px;">
      <div style="font-weight: bold; margin-bottom: 8px; font-size: 12px;">Select Route (${routes.length} options):</div>
      ${routes.map((route, idx) => {
        const isSelected = idx === activeRouteIndex;
        const distance = route.legs.reduce((sum, leg) => sum + leg.distance.value, 0) / 1000; // Convert to km
        const duration = route.legs.reduce((sum, leg) => sum + leg.duration.value, 0) / 60; // Convert to minutes
        
        return `
        <div 
          class="route-option" 
          data-route-index="${idx}"
          style="padding: 8px; margin: 4px 0; border: 2px solid ${isSelected ? '#007bff' : '#ddd'}; border-radius: 4px; cursor: pointer; background: ${isSelected ? '#e7f3ff' : '#fff'}; font-size: 11px; transition: all 0.2s;"
          onmouseover="this.style.background='#f0f0f0'"
          onmouseout="this.style.background='${isSelected ? '#e7f3ff' : '#fff'}'"
          onclick="window.selectRouteByIndex('${mapId}', ${idx}, '${(frm && frm.doc && frm.doc.name) ? frm.doc.name : ''}')"
        >
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <strong>Route ${idx + 1}</strong>
              ${isSelected ? '<span style="color: #007bff; margin-left: 5px;">✓ Active</span>' : ''}
            </div>
          </div>
          <div style="margin-top: 4px; color: #666;">
            ${distance.toFixed(1)} km • ${Math.round(duration)} min
          </div>
        </div>
      `;
      }).join('')}
    </div>
  `;
  
  mapElement.insertAdjacentHTML('beforeend', routeSelectorHtml);
}

// Add vehicle marker and tracking
function addVehicleMarkerAndTracking(mapId, vehiclePosition, frm, map, bounds) {
  if (!vehiclePosition || !vehiclePosition.latitude || !vehiclePosition.longitude) return;
  
  const routeData = window.runSheetRouteData[mapId];
  if (!routeData) return;
  
  const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
  const heading = vehiclePosition.heading_deg || 0;
  const vehicleState = getVehicleState(vehiclePosition);
  const stateDisplay = getVehicleStateDisplay(vehicleState);
  const arrowColor = stateDisplay.color;
  
  // Create navigation arrow icon
  const arrowIcon = {
    path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
    scale: 6,
    fillColor: arrowColor,
    fillOpacity: 1,
    strokeColor: '#ffffff',
    strokeWeight: 2,
    rotation: heading,
    anchor: new google.maps.Point(0, 0),
    labelOrigin: new google.maps.Point(0, 0)
  };
  
  const vehicleMarker = new google.maps.Marker({
    position: { lat: vehiclePosition.latitude, lng: vehiclePosition.longitude },
    map: map,
    icon: arrowIcon,
    title: `${vehicleName} - Current Location`,
    zIndex: 10000
  });
  
  bounds.extend({ lat: vehiclePosition.latitude, lng: vehiclePosition.longitude });
  routeData.vehicleMarker = vehicleMarker;
  
  // Function to build info window content
  const buildInfoWindowContent = (position, showRefresh = true) => {
    const speedDisplay = position.speed_kph ? `${position.speed_kph.toFixed(1)} km/h` : 'N/A';
    const timestampDisplay = position.timestamp || 'N/A';
    const odometerDisplay = position.odometer_km ? `${position.odometer_km.toFixed(1)} km` : 'N/A';
    const fuelDisplay = position.fuel_level !== null && position.fuel_level !== undefined 
      ? `${position.fuel_level}%` : 'N/A';
    const headingDisplay = position.heading_deg !== null && position.heading_deg !== undefined
      ? `${position.heading_deg.toFixed(1)}°` : 'N/A';
    const positionState = getVehicleState(position);
    const positionStateDisplay = getVehicleStateDisplay(positionState);
    const ignition = positionStateDisplay.text;
    const provider = position.provider || 'N/A';
    const refreshBtnId = `${mapId}-refresh-telematics`;
    
    return `
      <div style="padding: 8px 10px; min-width: 200px; max-width: 220px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; overflow: hidden;" onclick="event.stopPropagation();">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #e5e7eb;">
          <div style="font-weight: 600; font-size: 13px; color: #2563eb; display: flex; align-items: center; gap: 5px;">
            <i class="fa fa-truck" style="font-size: 12px;"></i>${vehicleName}
          </div>
          ${showRefresh ? `
          <button id="${refreshBtnId}" 
            style="background: #2563eb; color: white; border: none; padding: 4px 6px; border-radius: 3px; cursor: pointer; font-size: 12px; font-weight: 500; display: flex; align-items: center; justify-content: center; transition: background 0.2s; line-height: 1; width: 28px; height: 28px;"
            onmouseover="this.style.background='#1d4ed8'"
            onmouseout="this.style.background='#2563eb'"
            title="Refresh telematics data">
            <i class="fa fa-refresh"></i>
          </button>
          ` : ''}
        </div>
        <div style="font-size: 12px; color: #374151; line-height: 1.6;">
          <div style="margin-bottom: 4px; display: flex; justify-content: space-between;"><span style="color: #6b7280;">Provider:</span> <span style="color: #111827; font-weight: 500;">${provider}</span></div>
          <div style="margin-bottom: 4px; display: flex; justify-content: space-between;"><span style="color: #6b7280;">Ignition:</span> 
            <span style="color: ${positionStateDisplay.color}; font-weight: 600;">${ignition}</span>
          </div>
          <div style="margin-bottom: 4px; display: flex; justify-content: space-between;"><span style="color: #6b7280;">Speed:</span> <span style="color: #111827; font-weight: 500;">${speedDisplay}</span></div>
          <div style="margin-bottom: 4px; display: flex; justify-content: space-between;"><span style="color: #6b7280;">Heading:</span> <span style="color: #111827; font-weight: 500;">${headingDisplay}</span></div>
          <div style="margin-bottom: 4px; display: flex; justify-content: space-between;"><span style="color: #6b7280;">Fuel:</span> <span style="color: #111827; font-weight: 500;">${fuelDisplay}</span></div>
          <div style="margin-bottom: 4px; display: flex; justify-content: space-between;"><span style="color: #6b7280;">Odometer:</span> <span style="color: #111827; font-weight: 500;">${odometerDisplay}</span></div>
          <div style="margin-bottom: 4px; display: flex; justify-content: space-between;"><span style="color: #6b7280;">Updated:</span> <span style="color: #111827; font-size: 11px; font-weight: 500;">${timestampDisplay}</span></div>
          <div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #6b7280; word-break: break-all;">
            <div style="display: flex; justify-content: space-between; gap: 4px;"><span style="font-weight: 600;">Location:</span> <span style="text-align: right;">${position.latitude.toFixed(6)}, ${position.longitude.toFixed(6)}</span></div>
          </div>
        </div>
      </div>
    `;
  };
  
  const infoWindow = new google.maps.InfoWindow({
    content: buildInfoWindowContent(vehiclePosition),
    maxWidth: 220,
    disableAutoPan: false
  });
  
  // Refresh telematics data function
  const refreshTelematicsData = async () => {
    if (!frm || !frm.doc || !frm.doc.vehicle || typeof frm.doc.vehicle !== 'string' || frm.doc.vehicle.trim().length === 0) {
      frappe.show_alert({
        message: __('No vehicle assigned to refresh'),
        indicator: 'orange'
      });
      return;
    }
    
    try {
      const refreshBtn = document.getElementById(`${mapId}-refresh-telematics`);
      if (refreshBtn) {
        refreshBtn.innerHTML = '<i class="fa fa-spin fa-spinner"></i>';
        refreshBtn.disabled = true;
      }
      
      const refreshResult = await frappe.call({
        method: 'logistics.transport.api_vehicle_tracking.refresh_vehicle_data',
        args: {
          vehicle_name: frm.doc.vehicle.trim()
        }
      });
      
      if (refreshResult.message && refreshResult.message.success) {
        const freshData = refreshResult.message;
        routeData.vehiclePosition = freshData;
        
        if (freshData.latitude && freshData.longitude) {
          const newPosition = { lat: freshData.latitude, lng: freshData.longitude };
          vehicleMarker.setPosition(newPosition);
          
          const freshState = getVehicleState(freshData);
          const freshStateDisplay = getVehicleStateDisplay(freshState);
          const freshArrowColor = freshStateDisplay.color;
          const newArrowIcon = {
            path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
            scale: 6,
            fillColor: freshArrowColor,
            fillOpacity: 1,
            strokeColor: '#ffffff',
            strokeWeight: 2,
            rotation: freshData.heading_deg || 0,
            anchor: new google.maps.Point(0, 0),
            labelOrigin: new google.maps.Point(0, 0)
          };
          vehicleMarker.setIcon(newArrowIcon);
        }
        
        infoWindow.setContent(buildInfoWindowContent(freshData));
        
        setTimeout(() => {
          const newRefreshBtn = document.getElementById(`${mapId}-refresh-telematics`);
          if (newRefreshBtn) {
            newRefreshBtn.onclick = refreshTelematicsData;
          }
        }, 100);
        
        frappe.show_alert({
          message: __('Telematics data refreshed successfully'),
          indicator: 'green'
        });
      }
    } catch (error) {
      console.error('Error refreshing telematics data:', error);
    } finally {
      const refreshBtn = document.getElementById(`${mapId}-refresh-telematics`);
      if (refreshBtn) {
        refreshBtn.innerHTML = '<i class="fa fa-refresh"></i>';
        refreshBtn.disabled = false;
      }
    }
  };
  
  vehicleMarker.addListener('click', function() {
    infoWindow.open(map, vehicleMarker);
    setTimeout(() => {
      const refreshBtn = document.getElementById(`${mapId}-refresh-telematics`);
      if (refreshBtn) {
        refreshBtn.onclick = refreshTelematicsData;
      }
    }, 100);
  });
}

// Start deviation monitoring
function startDeviationMonitoring(mapId, frm) {
  const routeData = window.runSheetRouteData[mapId];
  if (!routeData || !frm || !frm.doc || !frm.doc.vehicle || typeof frm.doc.vehicle !== 'string' || frm.doc.vehicle.trim().length === 0) return;
  
  // Clear existing interval
  if (routeData.deviationCheckInterval) {
    clearInterval(routeData.deviationCheckInterval);
  }
  
  // Dynamic route recalculation threshold: 20 meters
  // This ensures the route updates when truck takes a different road
  const DEVIATION_THRESHOLD_METERS = 20; // 20 meters threshold for dynamic recalculation
  const CHECK_INTERVAL_MS = 30000; // Check every 30 seconds for responsive updates
  const MIN_TIME_BETWEEN_RECALCULATIONS_MS = 60000; // 1 minute minimum between recalculations to prevent excessive API calls
  
  routeData.deviationCheckInterval = setInterval(async () => {
    try {
      // Prevent recalculation if it was done recently
      const timeSinceLastRecalculation = Date.now() - (routeData.lastRecalculationTime || 0);
      if (timeSinceLastRecalculation < MIN_TIME_BETWEEN_RECALCULATIONS_MS) {
        console.log(`Skipping deviation check - last recalculation was ${Math.round(timeSinceLastRecalculation / 1000)}s ago`);
        return;
      }
      
      // Get current vehicle position (validate vehicle name first)
      if (!frm.doc.vehicle || typeof frm.doc.vehicle !== 'string' || frm.doc.vehicle.trim().length === 0) {
        console.log('Skipping deviation check - no valid vehicle assigned');
        return;
      }
      
      const vehicleData = await frappe.call({
        method: 'logistics.transport.api_vehicle_tracking.get_vehicle_position',
        args: {
          vehicle_name: frm.doc.vehicle.trim()
        }
      });
      
      if (!vehicleData.message || !vehicleData.message.success) return;
      
      const currentPosition = vehicleData.message;
      if (!currentPosition.latitude || !currentPosition.longitude) return;
      
      // Skip check if vehicle is not moving (ignition off or very low speed)
      const vehicleState = getVehicleState(currentPosition);
      if (vehicleState === 'OFF' || (currentPosition.speed_kph && currentPosition.speed_kph < 5)) {
        console.log('Skipping deviation check - vehicle is stationary');
        return;
      }
      
      const currentLatLng = new google.maps.LatLng(currentPosition.latitude, currentPosition.longitude);
      
      // Get active route
      const routes = window.runSheetRoutes && window.runSheetRoutes[mapId];
      if (!routes || routes.length === 0) return;
      
      const activeRouteIndex = routeData.activeRouteIndex;
      const activeRoute = routes[activeRouteIndex];
      if (!activeRoute) return;
      
      // Check if vehicle is on the route by finding minimum distance to any point on the route
      let minDistance = Infinity;
      let closestPointIndex = -1;
      if (activeRoute.overview_path && activeRoute.overview_path.length > 0) {
        activeRoute.overview_path.forEach((point, index) => {
          const distance = google.maps.geometry.spherical.computeDistanceBetween(
            currentLatLng,
            point
          );
          if (distance < minDistance) {
            minDistance = distance;
            closestPointIndex = index;
          }
        });
      }
      
      // Additional check: verify vehicle is moving towards destination, not away
      // If vehicle is close to destination, don't trigger recalculation
      const destination = routeData.destination;
      if (destination) {
        const distanceToDestination = google.maps.geometry.spherical.computeDistanceBetween(
          currentLatLng,
          destination
        );
        
        // If vehicle is very close to destination (< 500m), don't recalculate
        if (distanceToDestination < 500) {
          console.log(`Vehicle is close to destination (${distanceToDestination.toFixed(0)}m), skipping deviation check`);
          return;
        }
      }
      
      // Trigger recalculation if deviation exceeds threshold
      if (minDistance > DEVIATION_THRESHOLD_METERS) {
        console.log(`Vehicle deviated from route. Distance: ${minDistance.toFixed(0)}m, threshold: ${DEVIATION_THRESHOLD_METERS}m`);
        
        // Update last recalculation time
        routeData.lastRecalculationTime = Date.now();
        
        // Recalculate route from current position
        recalculateRouteFromCurrentPosition(mapId, currentPosition, frm);
      }
    } catch (error) {
      console.error('Error checking deviation:', error);
    }
  }, CHECK_INTERVAL_MS);
}

// Recalculate route from current position
// This function is called when the driver deviates from the active route.
// It recalculates routes from the current GPS position while keeping the destination fixed.
function recalculateRouteFromCurrentPosition(mapId, currentPosition, frm) {
  const routeData = window.runSheetRouteData[mapId];
  if (!routeData) return;
  
  console.log('Recalculating route from current truck position:', currentPosition.latitude, currentPosition.longitude);
  
  // Keep destination fixed - this ensures the route always goes to the intended destination
  const destination = routeData.destination;
  if (!destination) {
    console.error('Cannot recalculate: destination is not set');
    return;
  }
  
  const origin = new google.maps.LatLng(currentPosition.latitude, currentPosition.longitude);
  
  // Clear existing route polylines before requesting new route
  if (routeData.routePolylines && routeData.routePolylines.length > 0) {
    console.log('Clearing existing route polylines...');
    routeData.routePolylines.forEach(polylineData => {
      if (polylineData.polyline) {
        polylineData.polyline.setMap(null);
      }
    });
    routeData.routePolylines = [];
  }
  
  // Clear directions renderer
  if (routeData.directionsRenderer) {
    routeData.directionsRenderer.setDirections({ routes: [] });
  }
  
  // Get remaining waypoints (if any)
  const remainingWaypoints = routeData.waypoints.filter(wp => {
    const wpLatLng = new google.maps.LatLng(wp.lat(), wp.lng());
    const distanceToOrigin = google.maps.geometry.spherical.computeDistanceBetween(origin, wpLatLng);
    const distanceToDest = google.maps.geometry.spherical.computeDistanceBetween(wpLatLng, destination);
    // Keep waypoints that are closer to destination than to origin
    return distanceToDest < distanceToOrigin;
  });
  
  const request = {
    origin: origin,
    destination: destination,
    waypoints: remainingWaypoints.length > 0 ? remainingWaypoints.map(wp => ({ location: wp, stopover: true })) : [],
    provideRouteAlternatives: true,
    travelMode: google.maps.TravelMode.DRIVING,
    optimizeWaypoints: false
  };
  
  console.log('Requesting new route from Google DirectionsService...');
  routeData.directionsService.route(request, (result, status) => {
    if (status === google.maps.DirectionsStatus.OK) {
      console.log(`✓ Recalculated route from current position. Received ${result.routes.length} route(s)`);
      
      // Update stored routes
      window.runSheetRoutes[mapId] = result.routes;
      
      // Validate and adjust active route index to ensure it's within bounds
      let activeRouteIndex = routeData.activeRouteIndex;
      if (activeRouteIndex < 0 || activeRouteIndex >= result.routes.length) {
        console.warn(`Previous route index ${activeRouteIndex} is out of range for ${result.routes.length} routes. Resetting to 0.`);
        activeRouteIndex = 0;
      }
      routeData.activeRouteIndex = activeRouteIndex;
      
      // Update origin to current position
      routeData.origin = origin;
      
      // Re-render routes
      const map = routeData.directionsRenderer.getMap();
      const bounds = new google.maps.LatLngBounds();
      
      // Include vehicle position in bounds
      if (currentPosition && currentPosition.latitude && currentPosition.longitude) {
        bounds.extend({ lat: currentPosition.latitude, lng: currentPosition.longitude });
      }
      
      // Include destination in bounds
      bounds.extend(destination);
      
      // Render all routes (this will extend bounds with route paths and clear old routes)
      renderAllRoutes(mapId, result.routes, activeRouteIndex, map, bounds);
      
      // Include all waypoints in bounds
      if (remainingWaypoints && remainingWaypoints.length > 0) {
        remainingWaypoints.forEach(wp => {
          bounds.extend({ lat: wp.lat(), lng: wp.lng() });
        });
      }
      
      // Fit map to show all routes and waypoints
      if (!bounds.isEmpty()) {
        map.fitBounds(bounds, { padding: 50 });
      }
      
      // Update vehicle marker position if it exists
      if (routeData.vehicleMarker && currentPosition && currentPosition.latitude && currentPosition.longitude) {
        routeData.vehicleMarker.setPosition({ lat: currentPosition.latitude, lng: currentPosition.longitude });
      }
      
      // Recreate route selector UI after a short delay to ensure DOM is ready
      // This ensures route options remain visible after recalculation
      setTimeout(() => {
        createRouteSelectorUI(mapId, result.routes, activeRouteIndex, frm);
        
        // Double-check that selector was created (for debugging)
        const mapElement = document.getElementById(mapId);
        if (mapElement && result.routes.length > 1) {
          const selector = mapElement.querySelector('.route-selector-ui');
          if (!selector) {
            console.warn('Route selector UI was not created, retrying...');
            setTimeout(() => {
              createRouteSelectorUI(mapId, result.routes, activeRouteIndex, frm);
            }, 500);
          } else {
            console.log(`Route selector UI created with ${result.routes.length} route options`);
          }
        }
      }, 100);
      
      frappe.show_alert({
        message: __('Route recalculated from current position. Destination remains fixed.'),
        indicator: 'green'
      });
    } else {
      console.error('Failed to recalculate route:', status);
      frappe.show_alert({
        message: __('Failed to recalculate route: {0}', [status]),
        indicator: 'red'
      });
    }
  });
}

// Select a route by index and save it (global function for onclick handler)
window.selectRouteByIndex = function(mapId, routeIndex, runSheetName) {
  const routeData = window.runSheetRouteData && window.runSheetRouteData[mapId];
  if (!routeData) {
    frappe.show_alert({
      message: __('Route data not available. Please refresh the map.'),
      indicator: 'orange'
    });
    return;
  }
  
  // Get the routes
  const routes = window.runSheetRoutes && window.runSheetRoutes[mapId];
  if (!routes || routes.length === 0) {
    frappe.show_alert({
      message: __('Route data not available. Please refresh the map.'),
      indicator: 'orange'
    });
    return;
  }
  
  // Validate route index - if out of range, use the first available route
  if (routeIndex < 0 || routeIndex >= routes.length) {
    console.warn(`Route index ${routeIndex} is out of range (0-${routes.length - 1}). Using route 0 instead.`);
    routeIndex = 0; // Default to first route instead of showing error
    frappe.show_alert({
      message: __('Route index was out of range. Using Route 1 instead.'),
      indicator: 'orange'
    });
  }
  
  const selectedRoute = routes[routeIndex];
  const map = routeData.directionsRenderer.getMap();
  const bounds = new google.maps.LatLngBounds();
  
  // Update active route index
  routeData.activeRouteIndex = routeIndex;
  
  // Re-render all routes with new active route
  renderAllRoutes(mapId, routes, routeIndex, map, bounds);
  
  // Update route selector UI
  createRouteSelectorUI(mapId, routes, routeIndex, routeData.frm);
  
  // Update directions renderer
  routeData.directionsRenderer.setDirections({
    routes: [selectedRoute],
    request: null
  });
  
  // Save the selected route to Run Sheet if runSheetName is provided
  if (runSheetName) {
    // Calculate distance and duration
    const distance = selectedRoute.legs.reduce((sum, leg) => sum + leg.distance.value, 0) / 1000; // Convert to km
    const duration = selectedRoute.legs.reduce((sum, leg) => sum + leg.duration.value, 0) / 60; // Convert to minutes
    
    // Encode polyline (convert MVCArray to regular array)
    const pathArray = [];
    if (selectedRoute.overview_path) {
      selectedRoute.overview_path.forEach(point => {
        pathArray.push(point);
      });
    }
    const polyline = google.maps.geometry.encoding.encodePath(pathArray);
    
    frappe.call({
      method: 'logistics.transport.api_vehicle_tracking.save_selected_route',
      args: {
        run_sheet_name: runSheetName,
        route_index: routeIndex,
        polyline: polyline,
        distance_km: distance,
        duration_min: Math.round(duration),
        route_type: 'run_sheet'
      }
    }).then(response => {
      if (response.message && response.message.success) {
        frappe.show_alert({
          message: __('Route {0} selected and saved', [routeIndex + 1]),
          indicator: 'green'
        });
      } else {
        frappe.show_alert({
          message: __('Failed to save route: {0}', [response.message?.error || 'Unknown error']),
          indicator: 'red'
        });
      }
    }).catch(error => {
      frappe.show_alert({
        message: __('Error saving route: {0}', [error.message || 'Unknown error']),
        indicator: 'red'
      });
    });
  } else {
    frappe.show_alert({
      message: __('Route {0} selected', [routeIndex + 1]),
      indicator: 'green'
    });
  }
}

// Initialize Mapbox for multi-leg route
function initializeMapboxRouteMap(mapId, legCoords, vehiclePosition, frm, consolidationInfo = {}) {
  // Load Mapbox GL JS if not already loaded
  if (!window.mapboxgl) {
    // Load Mapbox GL JS CSS
    const mapboxCSS = document.createElement('link');
    mapboxCSS.rel = 'stylesheet';
    mapboxCSS.href = 'https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css';
    mapboxCSS.crossOrigin = 'anonymous';
    document.head.appendChild(mapboxCSS);
    
    // Load Mapbox GL JS
    const mapboxJS = document.createElement('script');
    mapboxJS.src = 'https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js';
    mapboxJS.crossOrigin = 'anonymous';
    mapboxJS.onload = () => {
      createMapboxRouteMap(mapId, legCoords, vehiclePosition, frm, consolidationInfo);
    };
    document.head.appendChild(mapboxJS);
  } else {
    createMapboxRouteMap(mapId, legCoords, vehiclePosition, frm);
  }
}

function createMapboxRouteMap(mapId, legCoords, vehiclePosition, frm, consolidationInfo = {}) {
  console.log('createMapboxRouteMap called with:');
  console.log('  mapId:', mapId);
  console.log('  legCoords:', legCoords);
  console.log('  vehiclePosition:', vehiclePosition);
  
  const checkElement = () => {
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      try {
        console.log('Mapbox: Map element found, creating map...');
        
        // Calculate bounds
        const allLats = [];
        const allLons = [];
        legCoords.forEach(leg => {
          allLats.push(leg.pick.lat, leg.drop.lat);
          allLons.push(leg.pick.lon, leg.drop.lon);
        });
        
        // Include vehicle position in bounds if available
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          console.log('Mapbox: ✓ Adding vehicle position to bounds');
          allLats.push(vehiclePosition.latitude);
          allLons.push(vehiclePosition.longitude);
        }
        
        const centerLat = (Math.min(...allLats) + Math.max(...allLats)) / 2;
        const centerLon = (Math.min(...allLons) + Math.max(...allLons)) / 2;
        
        const map = new mapboxgl.Map({
          container: mapId,
          style: 'mapbox://styles/mapbox/streets-v12',
          center: [centerLon, centerLat],
          zoom: 10
        });
        
        // Add markers and routes for each leg
        const allMarkers = [];
        const allWaypoints = [];
        const locationMarkersMap = new Map(); // Track markers by location key
        const locationLegsMap = new Map(); // Track which legs use each location
        
        const locationLabels = consolidationInfo.locationLabels;
        
        // First pass: collect all locations
        legCoords.forEach((legData, index) => {
          const { leg, pick, drop } = legData;
          const pickKey = `${pick.lat.toFixed(6)},${pick.lon.toFixed(6)}`;
          const dropKey = `${drop.lat.toFixed(6)},${drop.lon.toFixed(6)}`;
          
          const legLabels = locationLabels ? locationLabels.legLabelMap.get(index) : null;
          const pickLabel = legLabels ? legLabels.pickLabel : '';
          const dropLabel = legLabels ? legLabels.dropLabel : '';
          
          if (!locationLegsMap.has(pickKey)) {
            locationLegsMap.set(pickKey, []);
          }
          locationLegsMap.get(pickKey).push({ leg, index, type: 'pick', label: pickLabel });
          
          if (!locationLegsMap.has(dropKey)) {
            locationLegsMap.set(dropKey, []);
          }
          locationLegsMap.get(dropKey).push({ leg, index, type: 'drop', label: dropLabel });
        });
        
        // Second pass: create one marker per unique location
        locationLegsMap.forEach((legsAtLocation, locationKey) => {
          const firstLeg = legsAtLocation[0];
          const isConsolidated = legsAtLocation.length > 1;
          const [lat, lon] = locationKey.split(',').map(Number);
          const isPick = firstLeg.type === 'pick';
          const label = firstLeg.label || '';
          
          const marker = new mapboxgl.Marker({
            element: createMarkerElement(label, isPick ? 'red' : 'green'),
            anchor: 'center'
          }).setLngLat([lon, lat]).addTo(map);
          
          const locationType = isPick ? 'Pickup' : 'Drop';
          const locationTypePlural = isPick ? 'Pickups' : 'Drops';
          let popupContent = `<strong>${isConsolidated ? `Consolidated ${locationTypePlural}` : `${locationType} (${label})`}</strong><br>`;
          
          legsAtLocation.forEach(({ leg, index }) => {
            popupContent += `Leg ${index + 1}: ${leg.transport_leg || 'N/A'}<br>`;
          });
          
          popupContent += `Coordinates: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
          marker.setPopup(new mapboxgl.Popup().setHTML(popupContent));
          
          locationMarkersMap.set(locationKey, marker);
          allMarkers.push(marker);
        });
        
        // Third pass: add waypoints for route lines
        // Build waypoints array including vehicle position if available
        const routeWaypoints = [];
        
        // Add vehicle position to start if available
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          routeWaypoints.push([vehiclePosition.longitude, vehiclePosition.latitude]);
        }
        
        // Add all leg waypoints
        legCoords.forEach((legData) => {
          const { pick, drop } = legData;
          routeWaypoints.push([pick.lon, pick.lat], [drop.lon, drop.lat]);
          allWaypoints.push([pick.lon, pick.lat], [drop.lon, drop.lat]);
        });
        
        // Add route lines when map loads
        map.on('load', () => {
          // Add route from vehicle to first pickup (if vehicle exists)
          if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude && legCoords.length > 0) {
            const firstPick = legCoords[0].pick;
            map.addSource('vehicle-to-first', {
              type: 'geojson',
              data: {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: [
                    [vehiclePosition.longitude, vehiclePosition.latitude],
                    [firstPick.lon, firstPick.lat]
                  ]
                }
              }
            });
            
            map.addLayer({
              id: 'vehicle-to-first',
              type: 'line',
              source: 'vehicle-to-first',
              layout: {
                'line-join': 'round',
                'line-cap': 'round'
              },
              paint: {
                'line-color': '#007bff',
                'line-width': 4,
                'line-opacity': 0.8,
                'line-dasharray': [8, 4]
              }
            });
          }
          
          // Add individual leg routes with different colors
          legCoords.forEach((legData, index) => {
            const { pick, drop } = legData;
            const sourceId = `leg-${index}`;
            
            map.addSource(sourceId, {
              type: 'geojson',
              data: {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: [
                    [pick.lon, pick.lat],
                    [drop.lon, drop.lat]
                  ]
                }
              }
            });
            
            map.addLayer({
              id: sourceId,
              type: 'line',
              source: sourceId,
              layout: {
                'line-join': 'round',
                'line-cap': 'round'
              },
              paint: {
                'line-color': index === 0 ? '#007bff' : '#ff9800',
                'line-width': index === 0 ? 5 : 4,
                'line-opacity': index === 0 ? 0.9 : 0.7,
                'line-dasharray': index === 0 ? [8, 4] : [10, 5]
              }
            });
          });
          
          // Add connecting lines between consecutive legs
          for (let i = 0; i < legCoords.length - 1; i++) {
            const currentDrop = legCoords[i].drop;
            const nextPick = legCoords[i + 1].pick;
            
            // Only draw connecting line if drop and next pick are different locations
            const dropKey = `${currentDrop.lat.toFixed(6)},${currentDrop.lon.toFixed(6)}`;
            const pickKey = `${nextPick.lat.toFixed(6)},${nextPick.lon.toFixed(6)}`;
            
            if (dropKey !== pickKey) {
              const connectSourceId = `connect-${i}`;
              map.addSource(connectSourceId, {
                type: 'geojson',
                data: {
                  type: 'Feature',
                  properties: {},
                  geometry: {
                    type: 'LineString',
                    coordinates: [
                      [currentDrop.lon, currentDrop.lat],
                      [nextPick.lon, nextPick.lat]
                    ]
                  }
                }
              });
              
              map.addLayer({
                id: connectSourceId,
                type: 'line',
                source: connectSourceId,
                layout: {
                  'line-join': 'round',
                  'line-cap': 'round'
                },
                paint: {
                  'line-color': '#9c27b0',
                  'line-width': 3,
                  'line-opacity': 0.6,
                  'line-dasharray': [6, 6]
                }
              });
            }
          }
          
          // Add overall route line as backup (less prominent)
          if (routeWaypoints.length > 2) {
            map.addSource('route-overview', {
              type: 'geojson',
              data: {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: routeWaypoints
                }
              }
            });
            
            map.addLayer({
              id: 'route-overview',
              type: 'line',
              source: 'route-overview',
              layout: {
                'line-join': 'round',
                'line-cap': 'round'
              },
              paint: {
                'line-color': '#6c757d',
                'line-width': 2,
                'line-opacity': 0.4,
                'line-dasharray': [20, 10]
              }
            });
          }
        });
        
        // Add vehicle/truck marker if position is available (Mapbox)
        console.log('=== MAPBOX TRUCK MARKER SECTION ===');
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          console.log('Mapbox: ✓ Adding truck marker');
          
          const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
          const vehicleState = getVehicleState(vehiclePosition);
          const stateDisplay = getVehicleStateDisplay(vehicleState);
          const ignition = stateDisplay.text;
          // Truck icon color based on state: green when ON, amber when IDLE, gray when OFF
          const truckIconColor = stateDisplay.color;
          const truckLabelColor = stateDisplay.labelColor;
          
          // Font Awesome truck in white circle (Mapbox)
          const truckEl = document.createElement('div');
          truckEl.innerHTML = `
            <div style="position: relative; width: 80px; height: 68px;">
              <!-- Ignition status card (above truck) -->
              <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: ${stateDisplay.bgColor}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 9px; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                Ignition: ${ignition}
              </div>
              
              <!-- White circle with truck icon (color based on state) -->
              <div style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 40px; height: 40px; background: white; border-radius: 50%; border: 2px solid ${truckIconColor}; box-shadow: 0 3px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                <i class="fa fa-truck" style="color: ${truckIconColor}; font-size: 20px;"></i>
                <!-- Small state indicator circle -->
                <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; background: ${stateDisplay.statusColor}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
              </div>
              
              <!-- Vehicle name label (below truck, color based on state) -->
              <div style="position: absolute; top: 62px; left: 50%; transform: translateX(-50%); background: white; color: ${truckLabelColor}; padding: 2px 8px; border-radius: 3px; white-space: nowrap; font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid ${truckIconColor};">
                ${vehicleName}
              </div>
            </div>
          `;
          
          const truckMarker = new mapboxgl.Marker({element: truckEl, anchor: 'center'})
            .setLngLat([vehiclePosition.longitude, vehiclePosition.latitude])
            .addTo(map);
          
          // Add popup with fuel level
          const speedDisplay = vehiclePosition.speed_kph ? `${vehiclePosition.speed_kph.toFixed(1)} km/h` : 'N/A';
          const timestampDisplay = vehiclePosition.timestamp || 'N/A';
          const odometerDisplay = vehiclePosition.odometer_km ? `${vehiclePosition.odometer_km.toFixed(1)} km` : null;
          console.log('Mapbox: Vehicle position fuel_level:', vehiclePosition.fuel_level);
          console.log('Mapbox: Vehicle position odometer_km:', vehiclePosition.odometer_km);
          const fuelDisplay = vehiclePosition.fuel_level ? `${vehiclePosition.fuel_level}%` : null;
          
          truckMarker.setPopup(new mapboxgl.Popup({offset: 25}).setHTML(`
            <div style="padding: 6px;">
              <div style="font-weight: 600; font-size: 13px; color: #007bff; margin-bottom: 8px;">${vehicleName}</div>
              <div style="font-size: 11px; color: #6b7280; line-height: 1.6;">
                <strong>Ignition:</strong> <span style="color: ${stateDisplay.color}; font-weight: 600;">${ignition}</span><br>
                ${speedDisplay !== 'N/A' ? `<strong>Speed:</strong> ${speedDisplay}<br>` : ''}
                ${fuelDisplay ? `<strong>Fuel:</strong> ${fuelDisplay}<br>` : ''}
                ${odometerDisplay ? `<strong>Mileage:</strong> ${odometerDisplay}<br>` : ''}
                <span style="font-size: 10px; color: #9ca3af;">${timestampDisplay}</span>
              </div>
            </div>
          `));
          
          allMarkers.push(truckMarker);
          allWaypoints.push([vehiclePosition.longitude, vehiclePosition.latitude]);
          
          console.log('Mapbox: ✓✓✓ TRUCK MARKER ADDED!');
          
          // Store for locate button
          window[`${mapId}_map`] = map;
          window[`${mapId}_truckMarker`] = truckMarker;
          
          setTimeout(() => {
            const locateBtn = document.getElementById(`${mapId}-locate-vehicle`);
            if (locateBtn) {
              locateBtn.onclick = async () => {
                console.log('Mapbox: Locating truck on map...');
                locateBtn.innerHTML = '<i class="fa fa-spin fa-spinner"></i> Locating...';
                locateBtn.disabled = true;
                
                try {
                  // Validate vehicle name before making API call
                  if (!frm || !frm.doc || !frm.doc.vehicle || typeof frm.doc.vehicle !== 'string' || frm.doc.vehicle.trim().length === 0) {
                    frappe.show_alert({
                      message: __('No vehicle assigned to locate'),
                      indicator: 'orange'
                    });
                    locateBtn.innerHTML = '<i class="fa fa-location-arrow"></i> Locate';
                    locateBtn.disabled = false;
                    return;
                  }
                  
                  // First refresh vehicle data to get latest position and ignition status
                  const refreshResult = await frappe.call({
                    method: 'logistics.transport.api_vehicle_tracking.refresh_vehicle_data',
                    args: {
                      vehicle_name: frm.doc.vehicle.trim()
                    }
                  });
                  
                  let currentPosition = vehiclePosition;
                  let refreshMessage = '';
                  
                  if (refreshResult.message && refreshResult.message.success) {
                    console.log('Mapbox: ✓ Vehicle data refreshed for location:', refreshResult.message);
                    currentPosition = refreshResult.message;
                    
                    // Update stored position
                    window[`${mapId}_vehiclePosition`] = currentPosition;
                    
                    const freshState = getVehicleState(currentPosition);
                    const freshStateDisplay = getVehicleStateDisplay(freshState);
                    refreshMessage = ` - Ignition: ${freshStateDisplay.text}, Speed: ${currentPosition.speed_kph ? currentPosition.speed_kph.toFixed(1) : 'N/A'} km/h`;
                    
                    // Update marker position if we have fresh data
                    truckMarker.setLngLat([currentPosition.longitude, currentPosition.latitude]);
                    
                    // Update marker icon color based on vehicle state
                    const freshTruckIconColor = freshStateDisplay.color;
                    const freshTruckLabelColor = freshStateDisplay.labelColor;
                    const freshIgnition = freshStateDisplay.text;
                    const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
                    
                    // Recreate marker element with updated colors
                    const freshTruckEl = document.createElement('div');
                    freshTruckEl.innerHTML = `
                      <div style="position: relative; width: 80px; height: 68px;">
                        <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: ${freshStateDisplay.bgColor}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 9px; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                          Ignition: ${freshIgnition}
                        </div>
                        <div style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 40px; height: 40px; background: white; border-radius: 50%; border: 2px solid ${freshTruckIconColor}; box-shadow: 0 3px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                          <i class="fa fa-truck" style="color: ${freshTruckIconColor}; font-size: 20px;"></i>
                          <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; background: ${freshStateDisplay.statusColor}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
                        </div>
                        <div style="position: absolute; top: 62px; left: 50%; transform: translateX(-50%); background: white; color: ${freshTruckLabelColor}; padding: 2px 8px; border-radius: 3px; white-space: nowrap; font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid ${freshTruckIconColor};">
                          ${vehicleName}
                        </div>
                      </div>
                    `;
                    truckMarker.getElement().innerHTML = freshTruckEl.innerHTML;
                    
                    // Update marker popup with fresh data
                    const speedDisplay = currentPosition.speed_kph ? `${currentPosition.speed_kph.toFixed(1)} km/h` : 'N/A';
                    const fuelDisplay = currentPosition.fuel_level ? `${currentPosition.fuel_level}%` : null;
                    const odometerDisplay = currentPosition.odometer_km ? `${currentPosition.odometer_km.toFixed(1)} km` : null;
                    const ignition = freshStateDisplay.text;
                    
                    truckMarker.setPopup(new mapboxgl.Popup({offset: 25}).setHTML(`
                      <div style="padding: 6px;">
                        <div style="font-weight: 600; font-size: 13px; color: #007bff; margin-bottom: 8px;">${vehicleName}</div>
                        <div style="font-size: 11px; color: #6b7280; line-height: 1.6;">
                          <strong>Ignition:</strong> <span style="color: ${freshStateDisplay.color}; font-weight: 600;">${ignition}</span><br>
                          ${speedDisplay !== 'N/A' ? `<strong>Speed:</strong> ${speedDisplay}<br>` : ''}
                          ${fuelDisplay ? `<strong>Fuel:</strong> ${fuelDisplay}<br>` : ''}
                          ${odometerDisplay ? `<strong>Mileage:</strong> ${odometerDisplay}<br>` : ''}
                          <span style="font-size: 10px; color: #9ca3af;">${currentPosition.timestamp || 'N/A'}</span>
                        </div>
                      </div>
                    `));
                  } else {
                    console.warn('Mapbox: Could not refresh vehicle data, using cached position');
                    refreshMessage = ' (using cached position)';
                  }
                  
                  // Fly to truck location
                  map.flyTo({center: [currentPosition.longitude, currentPosition.latitude], zoom: 15});
                  truckMarker.togglePopup();
                  
                  frappe.show_alert({
                    message: __('Truck located at {0}, {1}{2}', [
                      currentPosition.latitude.toFixed(5),
                      currentPosition.longitude.toFixed(5),
                      refreshMessage
                    ]),
                    indicator: 'green'
                  });
                } catch (error) {
                  console.error('Mapbox: Error locating truck:', error);
                  frappe.show_alert({
                    message: __('Error locating truck: {0}', [error.message || 'Unknown error']),
                    indicator: 'red'
                  });
                } finally {
                  locateBtn.innerHTML = '<i class="fa fa-location-arrow"></i> Locate';
                  locateBtn.disabled = false;
                }
              };
              locateBtn.disabled = false;
            }
          }, 500);
        }
        
        // Fit map to show all markers
        const bounds = new mapboxgl.LngLatBounds();
        allWaypoints.forEach(coord => bounds.extend(coord));
        map.fitBounds(bounds, { padding: 50 });
        
        // Hide fallback when map loads successfully
        hideMapFallback(mapId);
        
      } catch (error) {
        console.error('Error creating Mapbox route:', error);
        // Keep fallback visible on error
      }
    } else {
      // Retry after a short delay
      setTimeout(checkElement, 100);
    }
  };
  
  checkElement();
}

function initializeMapLibreRouteMap(mapId, legCoords, vehiclePosition, frm, consolidationInfo = {}) {
  // Load MapLibre GL JS if not already loaded
  if (!window.maplibregl) {
    // Load MapLibre GL JS CSS
    const mapLibreCSS = document.createElement('link');
    mapLibreCSS.rel = 'stylesheet';
    mapLibreCSS.href = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css';
    mapLibreCSS.integrity = 'sha256-cxGB1ADWWosJ2EL1W3C8TcEQELFbhUnixlpp0jP73S4=';
    mapLibreCSS.crossOrigin = 'anonymous';
    document.head.appendChild(mapLibreCSS);
    
    // Load MapLibre GL JS
    const mapLibreJS = document.createElement('script');
    mapLibreJS.src = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js';
    mapLibreJS.integrity = 'sha256-xGCE32m7qplbMBpRUnSobsU5BceEWbgNzLwnoMC40Ts=';
    mapLibreJS.crossOrigin = 'anonymous';
    mapLibreJS.onload = () => {
      createMapLibreRouteMap(mapId, legCoords, vehiclePosition, frm, consolidationInfo);
    };
    document.head.appendChild(mapLibreJS);
  } else {
    createMapLibreRouteMap(mapId, legCoords, vehiclePosition, frm);
  }
}

function createMapLibreRouteMap(mapId, legCoords, vehiclePosition, frm, consolidationInfo = {}) {
  console.log('createMapLibreRouteMap called with:');
  console.log('  mapId:', mapId);
  console.log('  legCoords:', legCoords);
  console.log('  vehiclePosition:', vehiclePosition);
  console.log('  frm:', frm ? 'present' : 'missing');
  
  const checkElement = () => {
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      try {
        console.log('MapLibre: Map element found, creating map...');
        
        // Calculate bounds
        const allLats = [];
        const allLons = [];
        legCoords.forEach(leg => {
          allLats.push(leg.pick.lat, leg.drop.lat);
          allLons.push(leg.pick.lon, leg.drop.lon);
        });
        
        // Include vehicle position in bounds if available
        console.log('MapLibre: Checking vehicle position for bounds:', vehiclePosition);
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          console.log('MapLibre: ✓ Adding vehicle position to bounds');
          allLats.push(vehiclePosition.latitude);
          allLons.push(vehiclePosition.longitude);
        } else {
          console.log('MapLibre: ✗ Vehicle position not valid for bounds');
        }
        
        const centerLat = (Math.min(...allLats) + Math.max(...allLats)) / 2;
        const centerLon = (Math.min(...allLons) + Math.max(...allLons)) / 2;
        
        const map = new maplibregl.Map({
          container: mapId,
          style: {
            version: 8,
            sources: {
              'osm': {
                type: 'raster',
                tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                tileSize: 256,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              }
            },
            layers: [{
              id: 'osm',
              type: 'raster',
              source: 'osm'
            }]
          },
          center: [centerLon, centerLat],
          zoom: 10
        });
        
        // Add markers and routes for each leg
        const allMarkers = [];
        const allWaypoints = [];
        const locationMarkersMap = new Map(); // Track markers by location key
        const locationLegsMap = new Map(); // Track which legs use each location
        
        const locationLabels = consolidationInfo.locationLabels;
        
        // First pass: collect all locations
        legCoords.forEach((legData, index) => {
          const { leg, pick, drop } = legData;
          const pickKey = `${pick.lat.toFixed(6)},${pick.lon.toFixed(6)}`;
          const dropKey = `${drop.lat.toFixed(6)},${drop.lon.toFixed(6)}`;
          
          const legLabels = locationLabels ? locationLabels.legLabelMap.get(index) : null;
          const pickLabel = legLabels ? legLabels.pickLabel : '';
          const dropLabel = legLabels ? legLabels.dropLabel : '';
          
          if (!locationLegsMap.has(pickKey)) {
            locationLegsMap.set(pickKey, []);
          }
          locationLegsMap.get(pickKey).push({ leg, index, type: 'pick', label: pickLabel });
          
          if (!locationLegsMap.has(dropKey)) {
            locationLegsMap.set(dropKey, []);
          }
          locationLegsMap.get(dropKey).push({ leg, index, type: 'drop', label: dropLabel });
        });
        
        // Second pass: create one marker per unique location
        locationLegsMap.forEach((legsAtLocation, locationKey) => {
          const firstLeg = legsAtLocation[0];
          const isConsolidated = legsAtLocation.length > 1;
          const [lat, lon] = locationKey.split(',').map(Number);
          const isPick = firstLeg.type === 'pick';
          const label = firstLeg.label || '';
          
          const marker = new maplibregl.Marker({
            element: createMarkerElement(label, isPick ? 'red' : 'green'),
            anchor: 'center'
          }).setLngLat([lon, lat]).addTo(map);
          
          const locationType = isPick ? 'Pickup' : 'Drop';
          const locationTypePlural = isPick ? 'Pickups' : 'Drops';
          let popupContent = `<strong>${isConsolidated ? `Consolidated ${locationTypePlural}` : `${locationType} (${label})`}</strong><br>`;
          
          legsAtLocation.forEach(({ leg, index }) => {
            popupContent += `Leg ${index + 1}: ${leg.transport_leg || 'N/A'}<br>`;
          });
          
          popupContent += `Coordinates: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
          marker.setPopup(new maplibregl.Popup().setHTML(popupContent));
          
          locationMarkersMap.set(locationKey, marker);
          allMarkers.push(marker);
        });
        
        // Third pass: add waypoints for route lines
        // Build waypoints array including vehicle position if available
        const routeWaypoints = [];
        
        // Add vehicle position to start if available
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          routeWaypoints.push([vehiclePosition.longitude, vehiclePosition.latitude]);
        }
        
        // Add all leg waypoints
        legCoords.forEach((legData) => {
          const { pick, drop } = legData;
          routeWaypoints.push([pick.lon, pick.lat], [drop.lon, drop.lat]);
          allWaypoints.push([pick.lon, pick.lat], [drop.lon, drop.lat]);
        });
        
        // Add route lines when map loads
        map.on('load', () => {
          // Add route from vehicle to first pickup (if vehicle exists)
          if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude && legCoords.length > 0) {
            const firstPick = legCoords[0].pick;
            map.addSource('vehicle-to-first', {
              type: 'geojson',
              data: {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: [
                    [vehiclePosition.longitude, vehiclePosition.latitude],
                    [firstPick.lon, firstPick.lat]
                  ]
                }
              }
            });
            
            map.addLayer({
              id: 'vehicle-to-first',
              type: 'line',
              source: 'vehicle-to-first',
              layout: {
                'line-join': 'round',
                'line-cap': 'round'
              },
              paint: {
                'line-color': '#007bff',
                'line-width': 4,
                'line-opacity': 0.8,
                'line-dasharray': [8, 4]
              }
            });
          }
          
          // Add individual leg routes with different colors
          legCoords.forEach((legData, index) => {
            const { pick, drop } = legData;
            const sourceId = `leg-${index}`;
            
            map.addSource(sourceId, {
              type: 'geojson',
              data: {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: [
                    [pick.lon, pick.lat],
                    [drop.lon, drop.lat]
                  ]
                }
              }
            });
            
            map.addLayer({
              id: sourceId,
              type: 'line',
              source: sourceId,
              layout: {
                'line-join': 'round',
                'line-cap': 'round'
              },
              paint: {
                'line-color': index === 0 ? '#007bff' : '#ff9800',
                'line-width': index === 0 ? 5 : 4,
                'line-opacity': index === 0 ? 0.9 : 0.7,
                'line-dasharray': index === 0 ? [8, 4] : [10, 5]
              }
            });
          });
          
          // Add connecting lines between consecutive legs
          for (let i = 0; i < legCoords.length - 1; i++) {
            const currentDrop = legCoords[i].drop;
            const nextPick = legCoords[i + 1].pick;
            
            // Only draw connecting line if drop and next pick are different locations
            const dropKey = `${currentDrop.lat.toFixed(6)},${currentDrop.lon.toFixed(6)}`;
            const pickKey = `${nextPick.lat.toFixed(6)},${nextPick.lon.toFixed(6)}`;
            
            if (dropKey !== pickKey) {
              const connectSourceId = `connect-${i}`;
              map.addSource(connectSourceId, {
                type: 'geojson',
                data: {
                  type: 'Feature',
                  properties: {},
                  geometry: {
                    type: 'LineString',
                    coordinates: [
                      [currentDrop.lon, currentDrop.lat],
                      [nextPick.lon, nextPick.lat]
                    ]
                  }
                }
              });
              
              map.addLayer({
                id: connectSourceId,
                type: 'line',
                source: connectSourceId,
                layout: {
                  'line-join': 'round',
                  'line-cap': 'round'
                },
                paint: {
                  'line-color': '#9c27b0',
                  'line-width': 3,
                  'line-opacity': 0.6,
                  'line-dasharray': [6, 6]
                }
              });
            }
          }
          
          // Add overall route line as backup (less prominent)
          if (routeWaypoints.length > 2) {
            map.addSource('route-overview', {
              type: 'geojson',
              data: {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: routeWaypoints
                }
              }
            });
            
            map.addLayer({
              id: 'route-overview',
              type: 'line',
              source: 'route-overview',
              layout: {
                'line-join': 'round',
                'line-cap': 'round'
              },
              paint: {
                'line-color': '#6c757d',
                'line-width': 2,
                'line-opacity': 0.4,
                'line-dasharray': [20, 10]
              }
            });
          }
        });
        
        // Add vehicle/truck marker if position is available (MapLibre)
        console.log('=== MAPLIBRE TRUCK MARKER SECTION ===');
        console.log('Checking if we should add truck marker...');
        console.log('vehiclePosition exists?', !!vehiclePosition);
        console.log('vehiclePosition.latitude?', vehiclePosition?.latitude);
        console.log('vehiclePosition.longitude?', vehiclePosition?.longitude);
        
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          console.log('MapLibre: ✓ CONDITION MET - Adding truck marker');
          
          const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
          const vehicleState = getVehicleState(vehiclePosition);
          const stateDisplay = getVehicleStateDisplay(vehicleState);
          const ignition = stateDisplay.text;
          // Truck icon color based on state: green when ON, amber when IDLE, gray when OFF
          const truckIconColor = stateDisplay.color;
          const truckLabelColor = stateDisplay.labelColor;
          
          // Font Awesome truck in white circle (MapLibre)
          const truckEl = document.createElement('div');
          truckEl.className = 'maplibre-truck-marker';
          truckEl.innerHTML = `
            <div style="position: relative; width: 80px; height: 68px;">
              <!-- Ignition status card (above truck) -->
              <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: ${stateDisplay.bgColor}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 9px; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                Ignition: ${ignition}
              </div>
              
              <!-- White circle with truck icon (color based on state) -->
              <div style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 40px; height: 40px; background: white; border-radius: 50%; border: 2px solid ${truckIconColor}; box-shadow: 0 3px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                <i class="fa fa-truck" style="color: ${truckIconColor}; font-size: 20px;"></i>
                <!-- Small state indicator circle -->
                <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; background: ${stateDisplay.statusColor}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
              </div>
              
              <!-- Vehicle name label (below truck, color based on state) -->
              <div style="position: absolute; top: 62px; left: 50%; transform: translateX(-50%); background: white; color: ${truckLabelColor}; padding: 2px 8px; border-radius: 3px; white-space: nowrap; font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid ${truckIconColor};">
                ${vehicleName}
              </div>
            </div>
          `;
          
          const truckMarker = new maplibregl.Marker({
            element: truckEl,
            anchor: 'center'
          }).setLngLat([vehiclePosition.longitude, vehiclePosition.latitude]).addTo(map);
          
          console.log('MapLibre: ✓ Truck marker created and added');
          
          // Add popup with fuel level
          const speedDisplay = vehiclePosition.speed_kph ? `${vehiclePosition.speed_kph.toFixed(1)} km/h` : 'N/A';
          const timestampDisplay = vehiclePosition.timestamp || 'N/A';
          const odometerDisplay = vehiclePosition.odometer_km ? `${vehiclePosition.odometer_km.toFixed(1)} km` : null;
          console.log('MapLibre: Vehicle position fuel_level:', vehiclePosition.fuel_level);
          console.log('MapLibre: Vehicle position odometer_km:', vehiclePosition.odometer_km);
          const fuelDisplay = vehiclePosition.fuel_level ? `${vehiclePosition.fuel_level}%` : null;
          
          truckMarker.setPopup(new maplibregl.Popup({offset: 25}).setHTML(`
            <div style="padding: 6px;">
              <div style="font-weight: 600; font-size: 13px; color: #007bff; margin-bottom: 8px;">${vehicleName}</div>
              <div style="font-size: 11px; color: #6b7280; line-height: 1.6;">
                <strong>Ignition:</strong> <span style="color: ${stateDisplay.color}; font-weight: 600;">${ignition}</span><br>
                ${speedDisplay !== 'N/A' ? `<strong>Speed:</strong> ${speedDisplay}<br>` : ''}
                ${fuelDisplay ? `<strong>Fuel:</strong> ${fuelDisplay}<br>` : ''}
                ${odometerDisplay ? `<strong>Mileage:</strong> ${odometerDisplay}<br>` : ''}
                <span style="font-size: 10px; color: #9ca3af;">${timestampDisplay}</span>
              </div>
            </div>
          `));
          
          allMarkers.push(truckMarker);
          
          // Add truck circle to bounds
          allWaypoints.push([vehiclePosition.longitude, vehiclePosition.latitude]);
          
          console.log('MapLibre: ✓✓✓ TRUCK MARKER ADDED SUCCESSFULLY! ✓✓✓');
          console.log('  Truck at:', vehiclePosition.latitude, vehiclePosition.longitude);
          
          // Store map and truck marker reference for locate button
          window[`${mapId}_map`] = map;
          window[`${mapId}_truckMarker`] = truckMarker;
          window[`${mapId}_vehiclePosition`] = vehiclePosition;
          
          // Setup locate truck button (MapLibre version)
          setTimeout(() => {
            const locateBtn = document.getElementById(`${mapId}-locate-vehicle`);
            if (locateBtn) {
              locateBtn.onclick = async () => {
                console.log('MapLibre: Locating truck on map...');
                locateBtn.innerHTML = '<i class="fa fa-spin fa-spinner"></i> Locating...';
                locateBtn.disabled = true;
                
                try {
                  // Validate vehicle name before making API call
                  if (!frm || !frm.doc || !frm.doc.vehicle || typeof frm.doc.vehicle !== 'string' || frm.doc.vehicle.trim().length === 0) {
                    frappe.show_alert({
                      message: __('No vehicle assigned to locate'),
                      indicator: 'orange'
                    });
                    locateBtn.innerHTML = '<i class="fa fa-location-arrow"></i> Locate';
                    locateBtn.disabled = false;
                    return;
                  }
                  
                  // First refresh vehicle data to get latest position and ignition status
                  const refreshResult = await frappe.call({
                    method: 'logistics.transport.api_vehicle_tracking.refresh_vehicle_data',
                    args: {
                      vehicle_name: frm.doc.vehicle.trim()
                    }
                  });
                  
                  let currentPosition = vehiclePosition;
                  let refreshMessage = '';
                  
                  if (refreshResult.message && refreshResult.message.success) {
                    console.log('MapLibre: ✓ Vehicle data refreshed for location:', refreshResult.message);
                    currentPosition = refreshResult.message;
                    
                    // Update stored position
                    window[`${mapId}_vehiclePosition`] = currentPosition;
                    
                    const freshState = getVehicleState(currentPosition);
                    const freshStateDisplay = getVehicleStateDisplay(freshState);
                    refreshMessage = ` - Ignition: ${freshStateDisplay.text}, Speed: ${currentPosition.speed_kph ? currentPosition.speed_kph.toFixed(1) : 'N/A'} km/h`;
                    
                    // Update marker position if we have fresh data
                    truckMarker.setLngLat([currentPosition.longitude, currentPosition.latitude]);
                    
                    // Update marker icon color based on vehicle state
                    const freshTruckIconColor = freshStateDisplay.color;
                    const freshTruckLabelColor = freshStateDisplay.labelColor;
                    const freshIgnition = freshStateDisplay.text;
                    const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
                    
                    // Recreate marker element with updated colors
                    const freshTruckEl = document.createElement('div');
                    freshTruckEl.className = 'maplibre-truck-marker';
                    freshTruckEl.innerHTML = `
                      <div style="position: relative; width: 80px; height: 68px;">
                        <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: ${freshStateDisplay.bgColor}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 9px; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                          Ignition: ${freshIgnition}
                        </div>
                        <div style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 40px; height: 40px; background: white; border-radius: 50%; border: 2px solid ${freshTruckIconColor}; box-shadow: 0 3px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                          <i class="fa fa-truck" style="color: ${freshTruckIconColor}; font-size: 20px;"></i>
                          <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; background: ${freshStateDisplay.statusColor}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
                        </div>
                        <div style="position: absolute; top: 62px; left: 50%; transform: translateX(-50%); background: white; color: ${freshTruckLabelColor}; padding: 2px 8px; border-radius: 3px; white-space: nowrap; font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid ${freshTruckIconColor};">
                          ${vehicleName}
                        </div>
                      </div>
                    `;
                    truckMarker.getElement().innerHTML = freshTruckEl.innerHTML;
                    
                    // Update marker popup with fresh data
                    const speedDisplay = currentPosition.speed_kph ? `${currentPosition.speed_kph.toFixed(1)} km/h` : 'N/A';
                    const fuelDisplay = currentPosition.fuel_level ? `${currentPosition.fuel_level}%` : null;
                    const odometerDisplay = currentPosition.odometer_km ? `${currentPosition.odometer_km.toFixed(1)} km` : null;
                    const ignition = freshStateDisplay.text;
                    
                    truckMarker.setPopup(new maplibregl.Popup({offset: 25}).setHTML(`
                      <div style="padding: 6px;">
                        <div style="font-weight: 600; font-size: 13px; color: #007bff; margin-bottom: 8px;">${vehicleName}</div>
                        <div style="font-size: 11px; color: #6b7280; line-height: 1.6;">
                          <strong>Ignition:</strong> <span style="color: ${freshStateDisplay.color}; font-weight: 600;">${ignition}</span><br>
                          ${speedDisplay !== 'N/A' ? `<strong>Speed:</strong> ${speedDisplay}<br>` : ''}
                          ${fuelDisplay ? `<strong>Fuel:</strong> ${fuelDisplay}<br>` : ''}
                          ${odometerDisplay ? `<strong>Mileage:</strong> ${odometerDisplay}<br>` : ''}
                          <span style="font-size: 10px; color: #9ca3af;">${currentPosition.timestamp || 'N/A'}</span>
                        </div>
                      </div>
                    `));
                  } else {
                    console.warn('MapLibre: Could not refresh vehicle data, using cached position');
                    refreshMessage = ' (using cached position)';
                  }
                  
                  const storedMap = window[`${mapId}_map`];
                  const storedMarker = window[`${mapId}_truckMarker`];
                  
                  if (storedMap && storedMarker) {
                    // Fly to truck location
                    storedMap.flyTo({
                      center: [currentPosition.longitude, currentPosition.latitude],
                      zoom: 15,
                      duration: 2000
                    });
                    
                    // Open popup
                    storedMarker.togglePopup();
                    
                    // Add temporary highlight
                    locateBtn.innerHTML = '<i class="fa fa-check"></i>';
                    locateBtn.style.background = '#10b981';
                    
                    setTimeout(() => {
                      locateBtn.innerHTML = '<i class="fa fa-location-arrow"></i> Locate';
                      locateBtn.style.background = '#2563eb';
                    }, 1500);
                    
                    frappe.show_alert({
                      message: __('Truck located at {0}, {1}{2}', [
                        currentPosition.latitude.toFixed(5),
                        currentPosition.longitude.toFixed(5),
                        refreshMessage
                      ]),
                      indicator: 'green'
                    });
                  } else {
                    frappe.show_alert({
                      message: __('Could not locate truck on map'),
                      indicator: 'red'
                    });
                  }
                } catch (error) {
                  console.error('MapLibre: Error locating truck:', error);
                  frappe.show_alert({
                    message: __('Error locating truck: {0}', [error.message || 'Unknown error']),
                    indicator: 'red'
                  });
                } finally {
                  locateBtn.innerHTML = '<i class="fa fa-location-arrow"></i> Locate';
                  locateBtn.disabled = false;
                }
              };
              
              locateBtn.disabled = false;
              locateBtn.style.opacity = '1';
              console.log('MapLibre: ✓ Locate truck button enabled');
            }
          }, 500);
          
        } else {
          console.log('MapLibre: ℹ️ Vehicle position not available');
          
          // Hide locate button if no vehicle position
          setTimeout(() => {
            const locateBtn = document.getElementById(`${mapId}-locate-vehicle`);
            if (locateBtn) {
              locateBtn.style.display = 'none';
            }
          }, 100);
        }
        
        // Fit map to show all markers
        const bounds = new maplibregl.LngLatBounds();
        allWaypoints.forEach(coord => bounds.extend(coord));
        map.fitBounds(bounds, { padding: 50 });
        
        // Hide fallback when map loads successfully
        hideMapFallback(mapId);
        
      } catch (error) {
        console.error('Error creating MapLibre route:', error);
        // Keep fallback visible on error
      }
    } else {
      // Retry after a short delay
      setTimeout(checkElement, 100);
    }
  };
  
  checkElement();
}

// Helper function to create marker elements
function createMarkerElement(text, color) {
  const el = document.createElement('div');
  el.style.cssText = `
    background-color: ${color};
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 10px;
  `;
  el.textContent = text;
  return el;
}

// ---------- Dynamic Status Update Functions ----------
/**
 * Update Run Sheet status by calling server-side method
 * This ensures the status is recalculated based on current leg statuses
 */
function updateRunSheetStatusFromDB(frm) {
  if (!frm || !frm.doc || !frm.doc.name) {
    console.log('[Status Update] Skipping: No form or document name');
    return;
  }
  
  // Only update status for submitted documents (docstatus = 1)
  // Draft documents will have their status updated on save
  if (frm.doc.docstatus !== 1) {
    console.log(`[Status Update] Skipping: Document not submitted (docstatus=${frm.doc.docstatus})`);
    return;
  }
  
  // Don't update if status is manually set to "Hold"
  // When status = "Hold", it prevents all automatic status updates
  // This allows users to manually pause status changes (e.g., when a run is on hold)
  // Hold status must be set manually by the user - the system never sets it automatically
  if (frm.doc.status === 'Hold') {
    console.log('[Status Update] Skipping: Status is Hold (manual hold - prevents auto-updates)');
    return;
  }
  
  console.log(`[Status Update] Calling server to update status for ${frm.doc.name} (current: ${frm.doc.status})`);
  
  // Call server-side method to recalculate and update status
  frappe.call({
    method: 'logistics.transport.doctype.run_sheet.run_sheet.update_status_from_client',
    args: {
      run_sheet_name: frm.doc.name
    },
    callback: function(r) {
      if (!r.exc && r.message && r.message.success) {
        const new_status = r.message.status;
        const old_status = r.message.old_status || frm.doc.status;
        const changed = r.message.changed;
        
        console.log(`[Status Update] Server returned: old=${old_status}, new=${new_status}, changed=${changed}, current=${frm.doc.status}`);
        
        // Always update the form field if the status from server is different
        // This ensures the UI stays in sync with the database
        if (new_status) {
          if (new_status !== frm.doc.status) {
            const previous_status = frm.doc.status;
            frm.doc.status = new_status;
            frm.refresh_field('status');
            
            console.log(`✓ Run Sheet status updated in UI: ${previous_status} → ${new_status}`);
            
            // Show alert if status changed significantly
            if (old_status !== new_status && 
                (old_status === 'Dispatched' && new_status === 'In-Progress') ||
                (old_status === 'In-Progress' && new_status === 'Completed')) {
              frappe.show_alert({
                message: __('Status updated: {0} → {1}', [old_status, new_status]),
                indicator: 'blue'
              }, 3);
            }
          } else {
            console.log(`[Status Update] Status is already correct: ${new_status}`);
          }
        } else {
          console.warn(`[Status Update] No status returned from server`);
        }
      } else {
        if (r.message && r.message.error) {
          console.error('Error updating Run Sheet status:', r.message.error);
        } else if (r.exc) {
          console.error('Exception updating Run Sheet status:', r.exc);
        }
      }
    },
    error: function(r) {
      console.error('Error calling update_status_from_client:', r);
    },
    freeze: false,
    async: false
  });
}

/**
 * Start periodic status polling for submitted Run Sheets
 * Polls every 10 seconds to check for status changes
 */
function startStatusPolling(frm) {
  if (!frm || !frm.doc || !frm.doc.name) {
    return;
  }
  
  // Only poll for submitted documents
  if (frm.doc.docstatus !== 1) {
    return;
  }
  
  // Clear any existing polling interval
  if (frm._statusPollInterval) {
    clearInterval(frm._statusPollInterval);
  }
  
  // Poll every 5 seconds for more responsive updates
  frm._statusPollInterval = setInterval(() => {
    // Only poll if form is still active and document is still submitted
    // IMPORTANT: Status polling stops when status = "Hold"
    // This prevents automatic status updates when user manually sets status to "Hold"
    if (frm && frm.doc && frm.doc.docstatus === 1 && frm.doc.status !== 'Hold') {
      updateRunSheetStatusFromDB(frm);
    } else {
      // Stop polling if conditions are no longer met (including when status = "Hold")
      if (frm._statusPollInterval) {
        clearInterval(frm._statusPollInterval);
        frm._statusPollInterval = null;
      }
    }
  }, 5000); // 5 seconds for more responsive updates
  
  // Also update immediately
  updateRunSheetStatusFromDB(frm);
}

/**
 * Stop status polling
 */
function stopStatusPolling(frm) {
  if (frm && frm._statusPollInterval) {
    clearInterval(frm._statusPollInterval);
    frm._statusPollInterval = null;
  }
}

// ---------- Transport Leg Action Functions ----------
window.startTransportLeg = function(transportLegName) {
  console.log('Start Transport Leg:', transportLegName);
  if (!transportLegName) {
    frappe.show_alert({message: __('No transport leg linked'), indicator: 'orange'});
    return;
  }
  
  // Check if vehicle is assigned to the Run Sheet - prevent starting if vehicle is empty
  const frm = cur_frm || (window.cur_frm);
  if (!frm || !frm.doc) {
    frappe.show_alert({
      message: __('Cannot start leg: Run Sheet form not available'),
      indicator: 'orange'
    });
    return;
  }
  
  // Validate vehicle field is not empty
  const vehicle = frm.doc.vehicle;
  if (!vehicle || (typeof vehicle === 'string' && vehicle.trim() === '')) {
    frappe.show_alert({
      message: __('Cannot start leg: Vehicle must be assigned to the Run Sheet first. Please select a vehicle before starting the leg.'),
      indicator: 'orange'
    });
    frappe.msgprint({
      title: __('Vehicle Required'),
      message: __('Please assign a vehicle to this Run Sheet before starting any transport legs.'),
      indicator: 'orange'
    });
    return;
  }
  
  frappe.call({
    method: 'logistics.transport.doctype.transport_leg.transport_leg.set_dates_and_update_status',
    args: {
      name: transportLegName,
      start_date: frappe.datetime.now_datetime()
    },
    callback: function(r) {
      if (!r.exc && r.message && r.message.ok) {
        frappe.show_alert({message: __('Leg started - Status: {0}', [r.message.status]), indicator: 'green'});
        // Update status dynamically and refresh the map
        if (cur_frm) {
          // Wait a moment for backend to update Transport Leg status, then update Run Sheet status
          setTimeout(() => {
            updateRunSheetStatusFromDB(cur_frm);
            render_run_sheet_route_map(cur_frm);
          }, 1000); // Increased delay to ensure backend has processed the leg status change
        }
      } else {
        frappe.show_alert({message: __('Error starting leg: {0}', [r.message?.message || 'Unknown error']), indicator: 'red'});
      }
    }
  });
}

window.endTransportLeg = function(transportLegName) {
  console.log('End Transport Leg:', transportLegName);
  if (!transportLegName) {
    frappe.show_alert({message: __('No transport leg linked'), indicator: 'orange'});
    return;
  }
  
  frappe.call({
    method: 'logistics.transport.doctype.transport_leg.transport_leg.set_dates_and_update_status',
    args: {
      name: transportLegName,
      end_date: frappe.datetime.now_datetime()
    },
    callback: function(r) {
      if (!r.exc && r.message && r.message.ok) {
        frappe.show_alert({message: __('Leg ended - Status: {0}', [r.message.status]), indicator: 'green'});
        // Update status dynamically and refresh the map
        if (cur_frm) {
          // Wait a moment for backend to update Transport Leg status, then update Run Sheet status
          setTimeout(() => {
            updateRunSheetStatusFromDB(cur_frm);
            render_run_sheet_route_map(cur_frm);
          }, 1000); // Increased delay to ensure backend has processed the leg status change
        }
      } else {
        frappe.show_alert({message: __('Error ending leg: {0}', [r.message?.message || 'Unknown error']), indicator: 'red'});
      }
    }
  });
}

window.viewTransportLeg = function(transportLegName) {
  console.log('View Transport Leg:', transportLegName);
  if (transportLegName) {
    frappe.set_route('Form', 'Transport Leg', transportLegName);
  } else {
    frappe.show_alert({message: __('No transport leg linked'), indicator: 'orange'});
  }
}

// ---------- form bindings ----------
frappe.ui.form.on('Run Sheet', {
  refresh(frm) {
    // Always try to render the route map, even for new documents
    // Use setTimeout to ensure form is fully loaded
    setTimeout(() => {
      render_run_sheet_route_map(frm);
    }, 300);
    
    if (frm.doc.name) {
      // Show red form message when any leg has an Economic Zone address
      frappe.call({
        method: 'logistics.transport.doctype.run_sheet.run_sheet.has_economic_zone_address',
        args: { run_sheet_name: frm.doc.name },
        callback(r) {
          if (r && r.message && r.message.has_ez_address) {
            frm.dashboard.add_indicator(
              __('This run sheet includes leg(s) with Economic Zone addresses. Ensure all required documents and arrangements are in place.'),
              'red'
            );
          }
        }
      });

      // Fetch and update missing data from Transport Leg
      update_legs_missing_data_rs(frm);
      
      // Update status dynamically for submitted documents
      if (frm.doc.docstatus === 1) {
        // Update immediately and start polling
        setTimeout(() => {
          updateRunSheetStatusFromDB(frm);
          startStatusPolling(frm);
        }, 500);
      }
      
      // Add Refresh Legs button
      if (!frm.is_new()) {
        frm.add_custom_button(__('Refresh Legs'), function() {
          refresh_legs_from_transport_leg(frm);
        }, __('Actions'));
        
        frm.add_custom_button(__('Sync to Transport Legs'), function() {
          sync_legs_to_transport_leg(frm);
        }, __('Actions'));
        
        // Add button to manually fetch missing leg data (works for submitted docs too)
        if (frm.doc.legs && frm.doc.legs.length > 0) {
          frm.add_custom_button(__('Fetch Missing Leg Data'), function() {
            fetch_missing_leg_data_rs(frm);
          }, __('Actions'));
        }
        
        // Add Create Support Legs button
        if (frm.doc.dispatch_terminal && frm.doc.return_terminal) {
          frm.add_custom_button(__('Create Support Legs'), function() {
            create_support_legs_rs(frm);
          }, __('Actions'));
        }
      }
    }
  },
  
  validate(frm) {
    // Fetch and update missing data from Transport Leg before save
    update_legs_missing_data_rs(frm);
  },
  
  before_submit(frm) {
    // Prevent submission if vehicle is empty
    if (!frm.doc.vehicle) {
      frappe.msgprint({
        title: __('Validation Error'),
        message: __('Vehicle is required. Please select a vehicle before submitting the document.'),
        indicator: 'red'
      });
      frappe.validated = false;
      return Promise.reject(__('Vehicle is required. Please select a vehicle before submitting the document.'));
    }
  },
  
  after_submit(frm) {
    // Immediately set status to "Dispatched" in the UI after submission
    // The Python after_submit() hook will also set it to "Dispatched" via db_set()
    // This ensures the UI reflects the correct status immediately
    frm.doc.status = 'Dispatched';
    frm.refresh_field('status');
    
    // Refresh status field after submission to ensure it matches database
    // The Python after_submit() hook updates the status via db_set()
    // Use a retry mechanism to ensure Python after_submit completes and status is updated
    let retry_count = 0;
    const max_retries = 10;
    const retry_delay = 400;
    
    const fetch_and_update_status = function() {
      // Fetch the latest status directly from database (bypassing form cache)
      frappe.db.get_value('Run Sheet', frm.doc.name, ['status', 'docstatus'], (r) => {
        if (r && r.docstatus === 1) {
          const db_status = r.status || 'Dispatched';
          
          // Update the document's status value directly
          // Ensure it's "Dispatched" if backend hasn't set it yet
          const new_status = r.status || 'Dispatched';
          if (new_status !== frm.doc.status) {
            frm.doc.status = new_status;
            // Refresh the status field to ensure UI reflects current value
            frm.refresh_field('status');
          }
          
          // Update docstatus if needed
          if (r.docstatus !== undefined && r.docstatus !== frm.doc.docstatus) {
            frm.doc.docstatus = r.docstatus;
          }
          
          // Start periodic polling for status updates after submission
          setTimeout(() => {
            startStatusPolling(frm);
          }, 500);
        } else if (retry_count < max_retries) {
          // Retry if docstatus is not 1 yet (backend still processing)
          retry_count++;
          setTimeout(fetch_and_update_status, retry_delay);
        } else {
          // If max retries reached, ensure status is at least "Dispatched"
          if (frm.doc.status !== 'Dispatched') {
            frm.doc.status = 'Dispatched';
            frm.refresh_field('status');
          }
          // Start polling anyway
          setTimeout(() => {
            startStatusPolling(frm);
          }, 500);
        }
      });
    };
    
    // Start fetching status after a short delay to allow backend to process
    setTimeout(fetch_and_update_status, 200);
    
    // Also trigger status recalculation using the new method
    setTimeout(() => {
      updateRunSheetStatusFromDB(frm);
    }, 1000);
  },
  
  legs(frm) {
    // Re-render map when legs change
    setTimeout(() => {
      render_run_sheet_route_map(frm);
    }, 300);
    // Update status dynamically when legs change (legs added/removed)
    if (!frm.is_new()) {
      // For submitted documents, fetch from DB; for drafts, just refresh field
      if (frm.doc.docstatus === 1) {
        setTimeout(() => {
          updateRunSheetStatusFromDB(frm);
        }, 500);
      } else {
        frm.refresh_field('status');
      }
    }
  },
  
  // Re-render map when Dashboard tab is shown
  map_tab(frm) {
    setTimeout(() => {
      render_run_sheet_route_map(frm);
    }, 200);
  },
  
  status: function(frm) {
    // Handle status change events - update UI if status changed
    // Status is automatically updated by backend, this is just for UI feedback
    if (frm.doc.docstatus === 1) {
      // If status changed to "Hold", stop polling immediately
      // Hold status prevents automatic updates, so polling should stop
      if (frm.doc.status === 'Hold') {
        console.log('[Status Change] Status set to Hold - stopping status polling');
        stopStatusPolling(frm);
        return; // Don't update status when manually set to Hold
      }
      
      // For submitted documents, ensure we have the latest status
      // (unless status is Hold, which updateRunSheetStatusFromDB will check)
      updateRunSheetStatusFromDB(frm);
    }
  },
  
  // Clean up polling when form is closed
  onload_post_render(frm) {
    // Stop polling when form is unloaded
    $(frm.wrapper).on('remove', function() {
      stopStatusPolling(frm);
    });
  }
});

// Refresh legs from Transport Leg doctype
async function refresh_legs_from_transport_leg(frm) {
  frappe.show_alert({
    message: __('Refreshing legs from Transport Leg...'),
    indicator: 'blue'
  });
  
  try {
    const result = await frappe.call({
      method: 'logistics.transport.doctype.run_sheet.run_sheet.refresh_legs',
      args: {
        run_sheet_name: frm.doc.name
      }
    });
    
    if (result.message && result.message.status === 'success') {
      frm.reload_doc();
      // After reload, update status dynamically for submitted documents
      setTimeout(() => {
        if (frm.doc.docstatus === 1) {
          updateRunSheetStatusFromDB(frm);
        }
      }, 500);
      frappe.show_alert({
        message: __('Legs refreshed successfully'),
        indicator: 'green'
      });
    }
  } catch (error) {
    frappe.show_alert({
      message: __('Error refreshing legs: ') + error.message,
      indicator: 'red'
    });
  }
}

// Sync legs to Transport Leg doctype
async function sync_legs_to_transport_leg(frm) {
  frappe.show_alert({
    message: __('Syncing legs to Transport Leg...'),
    indicator: 'blue'
  });
  
  try {
    const result = await frappe.call({
      method: 'logistics.transport.doctype.run_sheet.run_sheet.sync_legs_to_transport',
      args: {
        run_sheet_name: frm.doc.name
      }
    });
    
    if (result.message && result.message.status === 'success') {
      // Update status dynamically after syncing
      setTimeout(() => {
        if (frm.doc.docstatus === 1) {
          updateRunSheetStatusFromDB(frm);
        }
      }, 500);
      frappe.show_alert({
        message: __('Legs synced successfully'),
        indicator: 'green'
      });
    }
  } catch (error) {
    frappe.show_alert({
      message: __('Error syncing legs: ') + error.message,
      indicator: 'red'
    });
  }
}

// Update missing leg data from Transport Leg
function update_legs_missing_data_rs(frm) {
  // Fetch and update missing data from Transport Leg for all legs
  // Only works for draft documents (docstatus = 0)
  if (frm.doc.docstatus !== 0) {
    return;
  }
  
  const legs = frm.doc.legs || [];
  
  legs.forEach((leg, idx) => {
    if (!leg.transport_leg) {
      // Skip if transport_leg is not set
      return;
    }
    
    // Check if any required fields are missing
    const required_fields = [
      'transport_job', 'facility_type_from', 'facility_from', 'pick_mode', 'address_from',
      'facility_type_to', 'facility_to', 'drop_mode', 'address_to'
    ];
    
    const has_missing = required_fields.some(field => !leg[field]);
    
    if (has_missing) {
      // Fetch data from Transport Leg and update missing fields
      frappe.model.get_value('Transport Leg', leg.transport_leg, 
        ['transport_job', 'facility_type_from', 'facility_from', 'facility_type_to', 'facility_to',
         'pick_mode', 'drop_mode', 'pick_address', 'drop_address'],
        (r) => {
          if (r) {
            // Update only missing fields
            if (!leg.transport_job && r.transport_job) {
              frappe.model.set_value(leg.doctype, leg.name, 'transport_job', r.transport_job);
            }
            if (!leg.facility_type_from && r.facility_type_from) {
              frappe.model.set_value(leg.doctype, leg.name, 'facility_type_from', r.facility_type_from);
            }
            if (!leg.facility_from && r.facility_from) {
              frappe.model.set_value(leg.doctype, leg.name, 'facility_from', r.facility_from);
            }
            if (!leg.facility_type_to && r.facility_type_to) {
              frappe.model.set_value(leg.doctype, leg.name, 'facility_type_to', r.facility_type_to);
            }
            if (!leg.facility_to && r.facility_to) {
              frappe.model.set_value(leg.doctype, leg.name, 'facility_to', r.facility_to);
            }
            if (!leg.pick_mode && r.pick_mode) {
              frappe.model.set_value(leg.doctype, leg.name, 'pick_mode', r.pick_mode);
            }
            if (!leg.drop_mode && r.drop_mode) {
              frappe.model.set_value(leg.doctype, leg.name, 'drop_mode', r.drop_mode);
            }
            if (!leg.address_from && r.pick_address) {
              frappe.model.set_value(leg.doctype, leg.name, 'address_from', r.pick_address);
            }
            if (!leg.address_to && r.drop_address) {
              frappe.model.set_value(leg.doctype, leg.name, 'address_to', r.drop_address);
            }
            
            // Fetch customer from transport_job if missing
            if (!leg.customer && r.transport_job) {
              frappe.model.get_value('Transport Job', r.transport_job, 'customer', (r2) => {
                if (r2 && r2.customer) {
                  frappe.model.set_value(leg.doctype, leg.name, 'customer', r2.customer);
                }
              });
            }
          }
        }
      );
    }
  });
}

// Fetch missing leg data via server (works for submitted documents too)
function fetch_missing_leg_data_rs(frm) {
  frappe.call({
    method: 'logistics.transport.doctype.run_sheet.run_sheet.fetch_missing_leg_data',
    args: {
      run_sheet_name: frm.doc.name
    },
    freeze: true,
    freeze_message: __('Fetching missing leg data...'),
    callback: function(r) {
      if (r.message) {
        if (r.message.updated_count > 0) {
          frappe.show_alert({
            message: __('Updated {0} leg(s) with missing data', [r.message.updated_count]),
            indicator: 'green'
          });
          frm.reload_doc();
        } else {
          frappe.show_alert({
            message: __('No missing data found in legs'),
            indicator: 'blue'
          });
        }
      }
    }
  });
}

// Create support legs (Dispatch, Connecting, Return)
function create_support_legs_rs(frm) {
  if (!frm.doc.dispatch_terminal) {
    frappe.msgprint(__('Please set Dispatch Terminal first'));
    return;
  }
  
  if (!frm.doc.return_terminal) {
    frappe.msgprint(__('Please set Return Terminal first'));
    return;
  }
  
  if (!frm.doc.legs || frm.doc.legs.length === 0) {
    frappe.msgprint(__('Please add at least one leg to the Run Sheet first'));
    return;
  }
  
  frappe.call({
    method: 'logistics.transport.doctype.run_sheet.run_sheet.create_support_legs',
    args: {
      run_sheet_name: frm.doc.name
    },
    freeze: true,
    freeze_message: __('Creating support legs...'),
    callback: function(r) {
      if (r.message) {
        if (r.message.status === 'success') {
          frappe.show_alert({
            message: r.message.message || __('Created {0} support leg(s)', [r.message.legs_created || 0]),
            indicator: 'green'
          });
          frm.reload_doc();
        } else {
          frappe.show_alert({
            message: r.message.message || __('Error creating support legs'),
            indicator: 'red'
          });
        }
      }
    }
  });
}

// Initialize drag-and-drop sorting for leg cards
function initializeLegCardSorting(container, frm) {
  if (!container || !frm) return;
  
  // Make the container sortable using simple drag-and-drop
  let draggedElement = null;
  let placeholder = null;
  
  const cards = container.querySelectorAll('.transport-leg-card');
  
  cards.forEach(card => {
    // Make cards draggable
    card.setAttribute('draggable', 'true');
    
    // Add visual cue for draggable items
    card.style.cursor = 'move';
    
    // Drag start
    card.addEventListener('dragstart', function(e) {
      draggedElement = this;
      
      // Add dragging class to actual card (without transparency)
      this.classList.add('dragging');
      
      // Create placeholder that can receive drops
      placeholder = document.createElement('div');
      placeholder.className = 'drag-placeholder';
      placeholder.style.height = this.offsetHeight + 'px';
      
      // Make placeholder accept drops
      placeholder.addEventListener('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        e.dataTransfer.dropEffect = 'move';
        this.classList.add('drag-placeholder-active');
        console.log('📍 Hovering over placeholder');
        return false;
      });
      
      placeholder.addEventListener('dragleave', function(e) {
        this.classList.remove('drag-placeholder-active');
      });
      
      placeholder.addEventListener('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log('💧 DROPPED ON PLACEHOLDER!');
        
        if (!draggedElement) {
          console.warn('⚠️ No dragged element found');
          return false;
        }
        
        // Insert dragged element before placeholder
        if (this.parentNode) {
          this.parentNode.insertBefore(draggedElement, this);
          console.log('✅ Card inserted before placeholder');
          
          // Remove placeholder
          this.parentNode.removeChild(this);
          
          // Update card numbers
          const updatedCards = Array.from(container.children).filter(c => 
            c.classList.contains('transport-leg-card')
          );
          
          updatedCards.forEach((card, idx) => {
            const legNumber = card.querySelector('.leg-card-header h5');
            const badge = card.querySelector('.leg-number');
            
            if (legNumber) {
              const icon = '<i class="fa fa-truck"></i>';
              legNumber.innerHTML = `${icon} Leg ${idx + 1}`;
            }
            
            if (badge) {
              badge.textContent = `#${idx + 1}`;
            }
          });
          
          console.log('🔵 Updated card numbers in DOM');
          
          // Save to backend
          updateLegOrderFromCards(container, frm);
        }
        
        return false;
      });
      
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', this.getAttribute('data-transport-leg'));
      
      console.log('🟢 Started dragging:', this.getAttribute('data-transport-leg'));
    });
    
    // Drag end
    card.addEventListener('dragend', function(e) {
      console.log('🔴 Drag ended');
      
      this.classList.remove('dragging');
      
      // Remove placeholder
      if (placeholder && placeholder.parentNode) {
        placeholder.parentNode.removeChild(placeholder);
      }
      placeholder = null;
      
      // Remove all drag-over classes from all cards
      const allCards = container.querySelectorAll('.transport-leg-card');
      allCards.forEach(c => {
        c.classList.remove('drag-over-top');
        c.classList.remove('drag-over-bottom');
      });
      
      // Reset dragged element reference
      draggedElement = null;
    });
    
    // Drag over
    card.addEventListener('dragover', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      e.dataTransfer.dropEffect = 'move';
      
      if (!draggedElement || draggedElement === this) {
        return false;
      }
      
      // Remove placeholder from all positions
      container.querySelectorAll('.drag-placeholder').forEach(p => {
        if (p !== placeholder) p.remove();
      });
      
      // Remove drag-over from all cards
      container.querySelectorAll('.transport-leg-card').forEach(c => {
        c.classList.remove('drag-over-top');
        c.classList.remove('drag-over-bottom');
      });
      
      // Determine if we should insert before or after
      const allCards = Array.from(container.children).filter(c => 
        c.classList.contains('transport-leg-card')
      );
      
      const draggedIndex = allCards.indexOf(draggedElement);
      const targetIndex = allCards.indexOf(this);
      
      if (draggedIndex !== -1 && targetIndex !== -1) {
        if (draggedIndex < targetIndex) {
          // Dragging down - show placeholder after target
          this.classList.add('drag-over-bottom');
          if (placeholder) {
            if (this.nextSibling && this.nextSibling !== placeholder) {
              container.insertBefore(placeholder, this.nextSibling);
            } else if (!this.nextSibling) {
              container.appendChild(placeholder);
            }
          }
        } else {
          // Dragging up - show placeholder before target
          this.classList.add('drag-over-top');
          if (placeholder && this.previousSibling !== placeholder) {
            container.insertBefore(placeholder, this);
          }
        }
      }
      
      return false;
    });
    
    // Drag enter
    card.addEventListener('dragenter', function(e) {
      e.preventDefault();
      // Handled in dragover
    });
    
    // Drag leave
    card.addEventListener('dragleave', function(e) {
      // Only remove if we're actually leaving (not entering a child element)
      const rect = this.getBoundingClientRect();
      if (e.clientX < rect.left || e.clientX >= rect.right ||
          e.clientY < rect.top || e.clientY >= rect.bottom) {
        this.classList.remove('drag-over-top');
        this.classList.remove('drag-over-bottom');
      }
    });
    
    // Drop
    card.addEventListener('drop', function(e) {
      e.stopPropagation();
      e.preventDefault();
      
      console.log('💧 Drop event triggered on:', this.getAttribute('data-transport-leg'));
      
      if (!draggedElement) {
        console.warn('⚠️ No dragged element found');
        return false;
      }
      
      if (draggedElement === this) {
        console.log('ℹ️ Dropped on self, ignoring');
        return false;
      }
      
      // Get all cards (excluding placeholder)
      const allCards = Array.from(container.children).filter(c => 
        c.classList.contains('transport-leg-card')
      );
      
      const draggedIndex = allCards.indexOf(draggedElement);
      const targetIndex = allCards.indexOf(this);
      
      console.log(`🔄 Moving card from position ${draggedIndex + 1} to ${targetIndex + 1}`);
      
      if (draggedIndex === -1 || targetIndex === -1) {
        console.error('❌ Could not find card indices');
        return false;
      }
      
      // Remove placeholder first
      if (placeholder && placeholder.parentNode) {
        placeholder.parentNode.removeChild(placeholder);
      }
      
      // Determine insert position based on drag direction
      if (draggedIndex < targetIndex) {
        // Moving down - insert after target
        console.log('⬇️ Moving DOWN - inserting after target');
        if (this.nextSibling) {
          container.insertBefore(draggedElement, this.nextSibling);
        } else {
          container.appendChild(draggedElement);
        }
      } else {
        // Moving up - insert before target
        console.log('⬆️ Moving UP - inserting before target');
        container.insertBefore(draggedElement, this);
      }
      
      // Update card numbers immediately
      const updatedCards = Array.from(container.children).filter(c => 
        c.classList.contains('transport-leg-card')
      );
      
      updatedCards.forEach((card, idx) => {
        const legNumber = card.querySelector('.leg-card-header h5');
        const badge = card.querySelector('.leg-number');
        
        if (legNumber) {
          const icon = '<i class="fa fa-truck"></i>';
          legNumber.innerHTML = `${icon} Leg ${idx + 1}`;
        }
        
        if (badge) {
          badge.textContent = `#${idx + 1}`;
        }
      });
      
      console.log('🔵 Updated card numbers in DOM');
      
      // Clean up drag-over classes
      this.classList.remove('drag-over-top');
      this.classList.remove('drag-over-bottom');
      
      // Update the order on backend
      updateLegOrderFromCards(container, frm);
      
      return false;
    });
  });
  
  // Add CSS for smooth drag-and-drop
  if (!document.getElementById('leg-card-drag-styles')) {
    const style = document.createElement('style');
    style.id = 'leg-card-drag-styles';
    style.textContent = `
      /* Smooth transitions for cards */
      .transport-leg-card[draggable="true"] {
        transition: all 0.25s cubic-bezier(0.4, 0.0, 0.2, 1);
        position: relative;
        margin-bottom: 8px;
      }
      
      /* Dragging state - keep card fully visible */
      .transport-leg-card.dragging {
        cursor: grabbing !important;
        z-index: 1000;
        box-shadow: 0 8px 16px rgba(0,0,0,0.3);
        border: 3px solid #667eea;
        opacity: 1 !important;
        background: #ffffff !important;
      }
      
      /* Drop zone indicator - create visible space */
      .transport-leg-card.drag-over-top {
        margin-top: 60px !important;
        border-top: 4px dashed #667eea;
        padding-top: 12px;
        background: linear-gradient(to bottom, rgba(102, 126, 234, 0.15) 0%, transparent 50%);
      }
      
      .transport-leg-card.drag-over-bottom {
        margin-bottom: 60px !important;
        border-bottom: 4px dashed #667eea;
        padding-bottom: 12px;
        background: linear-gradient(to top, rgba(102, 126, 234, 0.15) 0%, transparent 50%);
      }
      
      /* Visual placeholder for drop position */
      .drag-placeholder {
        height: 100px;
        margin: 8px 0;
        border: 3px dashed #667eea;
        border-radius: 6px;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(102, 126, 234, 0.05) 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #667eea;
        font-weight: 600;
        font-size: 14px;
        transition: all 0.2s ease;
        position: relative;
        cursor: pointer;
      }
      
      .drag-placeholder::before {
        content: "↓ Drop here ↓";
        animation: pulse 1.5s ease-in-out infinite;
      }
      
      .drag-placeholder-active {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.25) 0%, rgba(102, 126, 234, 0.15) 100%);
        border-color: #4a5de6;
        border-width: 4px;
        transform: scale(1.02);
      }
      
      .drag-placeholder-active::before {
        content: "✓ Drop now! ✓";
        color: #4a5de6;
      }
      
      @keyframes pulse {
        0%, 100% { opacity: 0.6; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.05); }
      }
      
      /* Drag handle cursor */
      .drag-handle {
        cursor: grab !important;
      }
      
      .drag-handle:active {
        cursor: grabbing !important;
      }
      
      /* Route display styling */
      .route-display {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 8px 0;
        padding: 8px;
        background: #f8f9fa;
        border-radius: 4px;
      }
      
      .route-point {
        flex: 1;
        min-width: 0;
      }
      
      .route-label {
        font-size: 9px;
        color: #6c757d;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
      }
      
      .route-value {
        font-size: 12px;
        color: #2c3e50;
        font-weight: 600;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      
      .route-arrow {
        color: #667eea;
        font-size: 16px;
        flex-shrink: 0;
      }
      
      /* Card footer layout */
      .leg-card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #e0e0e0;
      }
      
      .leg-info-right {
        display: flex;
        align-items: center;
        gap: 6px;
      }
    `;
    document.head.appendChild(style);
  }
}

// Update leg order based on current card positions
async function updateLegOrderFromCards(container, frm) {
  const cards = container.querySelectorAll('.transport-leg-card');
  const legOrder = [];
  
  console.log('📊 Reading current card order from DOM...');
  
  cards.forEach((card, index) => {
    const transportLeg = card.getAttribute('data-transport-leg');
    if (transportLeg) {
      legOrder.push({
        transport_leg: transportLeg,
        idx: index + 1
      });
      // Update the data-idx attribute
      card.setAttribute('data-idx', index + 1);
      console.log(`  ${index + 1}. ${transportLeg}`);
    }
  });
  
  if (legOrder.length === 0) {
    console.warn('⚠️ No legs found in cards');
    return;
  }
  
  console.log('💾 Calling backend to save order...');
  
  try {
    const result = await frappe.call({
      method: 'logistics.transport.doctype.run_sheet.run_sheet.update_leg_order',
      args: {
        run_sheet_name: frm.doc.name,
        leg_order: legOrder
      }
    });
    
    console.log('✅ Backend response:', result.message);
    
    if (result.message && result.message.status === 'success') {
      frappe.show_alert({
        message: __('Saved: {0} legs reordered', [result.message.count]),
        indicator: 'green'
      });
      
      // Update the child table in the form without full reload
      console.log('🔄 Updating child table...');
      
      // Update frm.doc.legs order to match
      if (frm.doc.legs && frm.doc.legs.length > 0) {
        const legMap = {};
        legOrder.forEach((item, idx) => {
          legMap[item.transport_leg] = idx;
        });
        
        frm.doc.legs.sort((a, b) => {
          const orderA = legMap[a.transport_leg] !== undefined ? legMap[a.transport_leg] : 999;
          const orderB = legMap[b.transport_leg] !== undefined ? legMap[b.transport_leg] : 999;
          return orderA - orderB;
        });
        
        frm.refresh_field('legs');
        console.log('✅ Child table updated');
      }
      
      // Reload doc after short delay to sync everything
      setTimeout(() => {
        console.log('🔄 Reloading document...');
        frm.reload_doc();
      }, 800);
    }
  } catch (error) {
    console.error('❌ Error saving order:', error);
    frappe.show_alert({
      message: __('Error: ') + (error.message || error),
      indicator: 'red'
    });
    
    // Reload to restore original order on error
    setTimeout(() => {
      frm.reload_doc();
    }, 1000);
  }
}