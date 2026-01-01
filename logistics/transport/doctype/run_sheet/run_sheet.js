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

// ---------- Multi-leg Route Map ----------
async function render_run_sheet_route_map(frm) {
  const $wrapper = frm.get_field('route_map').$wrapper;
  if (!$wrapper) return;
  
  const legs = frm.doc.legs || [];
  if (legs.length === 0) {
    $wrapper.html('<div class="text-muted">No transport legs added to this run sheet</div>');
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
          top: 10px;
          left: 10px;
          display: flex;
          gap: 6px;
          z-index: 1000;
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
            top: 8px;
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
            top: 6px;
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
            top: 4px;
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
            <div style="position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.9); padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; z-index: 1000;">
              <span style="color: blue;">●</span> ${legs.length} Stops
            </div>
            <div class="map-controls">
              <button id="${mapId}-refresh-vehicle" class="map-btn" title="Refresh vehicle position">
                <i class="fa fa-refresh"></i>
              </button>
              <button id="${mapId}-locate-vehicle" class="map-btn locate-btn" title="Locate vehicle on map">
                <i class="fa fa-location-arrow"></i> Locate
              </button>
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
        
        // Build action icons - hide start if started, hide end if ended
        const actionIcons = [];
        
        // Add drag handle icon (always first)
        actionIcons.push(`<i class="fa fa-grip-vertical drag-handle" 
           title="Drag to Reorder" 
           style="color: #6c757d; cursor: move;"></i>`);
        
        if (!startDate) {
          actionIcons.push(`<i class="fa fa-play-circle action-icon" 
             title="Start Leg" 
             onclick="startTransportLeg('${leg.transport_leg}')"
             style="color: #28a745; cursor: pointer;"></i>`);
        }
        if (!endDate) {
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
            // Call the new refresh API to get fresh telematics data
            const refreshResult = await frappe.call({
              method: 'logistics.transport.api_vehicle_tracking.refresh_vehicle_data',
              args: {
                vehicle_name: frm.doc.vehicle
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
    $wrapper.html('<div class="text-muted">Unable to load route map</div>');
  }
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
    if (frm && frm.doc && frm.doc.vehicle) {
      try {
        console.log('Fetching vehicle position for:', frm.doc.vehicle);
        const vehicleData = await frappe.call({
          method: 'logistics.transport.api_vehicle_tracking.get_vehicle_position',
          args: {
            vehicle_name: frm.doc.vehicle
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
    
    // Update external links with first and last coordinates
    updateExternalLinks(mapId, legCoords);
    
    // Initialize map based on renderer (pass vehicle position for tracking and consolidation info)
    const consolidationInfo = {
      isPickConsolidated: isPickConsolidated,
      isDropConsolidated: isDropConsolidated
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
        const pickMarkersMap = new Map(); // Track pick markers for consolidation
        const dropMarkersMap = new Map(); // Track drop markers for consolidation
        
        const isPickConsolidated = consolidationInfo && consolidationInfo.isPickConsolidated;
        const isDropConsolidated = consolidationInfo && consolidationInfo.isDropConsolidated;
        
        legCoords.forEach((legData, index) => {
          const { leg, pick, drop } = legData;
          const pickKey = `${pick.lat.toFixed(6)},${pick.lon.toFixed(6)}`;
          const dropKey = `${drop.lat.toFixed(6)},${drop.lon.toFixed(6)}`;
          
          // For pick consolidated: only create one pick marker if it's the same location
          let pickMarker = null;
          if (isPickConsolidated && pickMarkersMap.has(pickKey)) {
            pickMarker = pickMarkersMap.get(pickKey);
            // Update popup to include this leg
            const existingPopup = pickMarker.getPopup();
            const existingContent = existingPopup ? existingPopup.getContent() : '';
            pickMarker.setPopupContent(
              existingContent + `<br>Leg ${index + 1}: ${leg.transport_leg || 'N/A'}`
            );
          } else {
            // Create new pick marker
            const markerLabel = isPickConsolidated ? 'P' : `P${index + 1}`;
            pickMarker = L.marker([pick.lat, pick.lon], {
              icon: L.divIcon({
                className: 'custom-div-icon',
                html: `<div style="background-color: red; width: ${isPickConsolidated ? '24' : '20'}px; height: ${isPickConsolidated ? '24' : '20'}px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: ${isPickConsolidated ? '12' : '10'}px;">${markerLabel}</div>`,
                iconSize: [isPickConsolidated ? 24 : 20, isPickConsolidated ? 24 : 20],
                iconAnchor: [isPickConsolidated ? 12 : 10, isPickConsolidated ? 12 : 10]
              })
            }).addTo(map);
            
            pickMarker.bindPopup(`<strong>${isPickConsolidated ? 'Consolidated Pickup' : `Stop ${index + 1} - Pickup`}</strong><br>Leg ${index + 1}: ${leg.transport_leg || 'N/A'}<br>Coordinates: ${pick.lat.toFixed(4)}, ${pick.lon.toFixed(4)}`);
            pickMarkersMap.set(pickKey, pickMarker);
          }
          
          // For drop consolidated: only create one drop marker if it's the same location
          let dropMarker = null;
          if (isDropConsolidated && dropMarkersMap.has(dropKey)) {
            dropMarker = dropMarkersMap.get(dropKey);
            // Update popup to include this leg
            const existingPopup = dropMarker.getPopup();
            const existingContent = existingPopup ? existingPopup.getContent() : '';
            dropMarker.setPopupContent(
              existingContent + `<br>Leg ${index + 1}: ${leg.transport_leg || 'N/A'}`
            );
          } else {
            // Create new drop marker
            const markerLabel = isDropConsolidated ? 'D' : `D${index + 1}`;
            dropMarker = L.marker([drop.lat, drop.lon], {
              icon: L.divIcon({
                className: 'custom-div-icon',
                html: `<div style="background-color: green; width: ${isDropConsolidated ? '24' : '20'}px; height: ${isDropConsolidated ? '24' : '20'}px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: ${isDropConsolidated ? '12' : '10'}px;">${markerLabel}</div>`,
                iconSize: [isDropConsolidated ? 24 : 20, isDropConsolidated ? 24 : 20],
                iconAnchor: [isDropConsolidated ? 12 : 10, isDropConsolidated ? 12 : 10]
              })
            }).addTo(map);
            
            dropMarker.bindPopup(`<strong>${isDropConsolidated ? 'Consolidated Drop' : `Stop ${index + 1} - Drop`}</strong><br>Leg ${index + 1}: ${leg.transport_leg || 'N/A'}<br>Coordinates: ${drop.lat.toFixed(4)}, ${drop.lon.toFixed(4)}`);
            dropMarkersMap.set(dropKey, dropMarker);
          }
          
          // Add individual leg route line
          const routeColor = isPickConsolidated ? '#007bff' : (isDropConsolidated ? '#28a745' : (index === 0 ? 'blue' : 'orange'));
          const routeLine = L.polyline([
            [pick.lat, pick.lon],
            [drop.lat, drop.lon]
          ], {
            color: routeColor,
            weight: isPickConsolidated || isDropConsolidated ? 4 : 3,
            opacity: isPickConsolidated || isDropConsolidated ? 0.7 : 0.6,
            dashArray: isPickConsolidated || isDropConsolidated ? '0' : (index === 0 ? '5, 5' : '10, 10')
          }).addTo(map);
          
          if (!allMarkers.includes(pickMarker)) allMarkers.push(pickMarker);
          if (!allMarkers.includes(dropMarker)) allMarkers.push(dropMarker);
          allWaypoints.push([pick.lat, pick.lon], [drop.lat, drop.lon]);
        });
        
        // Add overall route line connecting all waypoints in sequence
        if (allWaypoints.length > 2) {
          const overallRoute = L.polyline(allWaypoints, {
            color: 'purple',
            weight: 5,
            opacity: 0.8,
            dashArray: '15, 10'
          }).addTo(map);
          
          // Add route info popup
          overallRoute.bindPopup(`
            <strong>Complete Route</strong><br>
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
          const ignition = vehiclePosition.ignition ? 'ON' : 'OFF';
          const ignitionOn = vehiclePosition.ignition;
          
          // Font Awesome truck in white circle
          const truckIcon = L.divIcon({
            className: 'custom-truck-marker',
            html: `
              <div style="position: relative; width: 80px; height: 68px;">
                <!-- Ignition status card (above truck) -->
                <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: ${ignitionOn ? '#10b981' : '#6b7280'}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 9px; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                  Ignition: ${ignition}
                </div>
                
                <!-- White circle with blue truck icon -->
                <div style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 40px; height: 40px; background: white; border-radius: 50%; border: 2px solid #e5e7eb; box-shadow: 0 3px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                  <i class="fa fa-truck" style="color: #2563eb; font-size: 20px;"></i>
                  <!-- Small ignition circle -->
                  <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; background: ${ignitionOn ? '#10b981' : '#ef4444'}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
                </div>
                
                <!-- Vehicle name label (below truck) -->
                <div style="position: absolute; top: 62px; left: 50%; transform: translateX(-50%); background: white; color: #007bff; padding: 2px 8px; border-radius: 3px; white-space: nowrap; font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid #e5e7eb;">
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
                <strong>Ignition:</strong> ${ignition === 'ON' ? '<span style="color: #10b981;">ON</span>' : '<span style="color: #6b7280;">OFF</span>'}<br>
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
                  // First refresh vehicle data to get latest position and ignition status
                  const refreshResult = await frappe.call({
                    method: 'logistics.transport.api_vehicle_tracking.refresh_vehicle_data',
                    args: {
                      vehicle_name: frm.doc.vehicle
                    }
                  });
                  
                  let currentPosition = vehiclePosition;
                  let refreshMessage = '';
                  
                  if (refreshResult.message && refreshResult.message.success) {
                    console.log('✓ Vehicle data refreshed for location:', refreshResult.message);
                    currentPosition = refreshResult.message;
                    
                    // Update stored position
                    window[`${mapId}_vehiclePosition`] = currentPosition;
                    
                    refreshMessage = ` - Ignition: ${currentPosition.ignition ? 'ON' : 'OFF'}, Speed: ${currentPosition.speed_kph ? currentPosition.speed_kph.toFixed(1) : 'N/A'} km/h`;
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
                      
                      // Update marker popup with fresh data
                      const speedDisplay = currentPosition.speed_kph ? `${currentPosition.speed_kph.toFixed(1)} km/h` : 'N/A';
                      const fuelDisplay = currentPosition.fuel_level ? `${currentPosition.fuel_level}%` : null;
                      const odometerDisplay = currentPosition.odometer_km ? `${currentPosition.odometer_km.toFixed(1)} km` : null;
                      const ignition = currentPosition.ignition ? 'ON' : 'OFF';
                      const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
                      
                      storedMarker.setPopupContent(`
                        <div style="padding: 6px;">
                          <div style="font-weight: 600; font-size: 13px; color: #007bff; margin-bottom: 8px;">${vehicleName}</div>
                          <div style="font-size: 11px; color: #6b7280; line-height: 1.6;">
                            <strong>Ignition:</strong> ${ignition === 'ON' ? '<span style="color: #10b981;">ON</span>' : '<span style="color: #6b7280;">OFF</span>'}<br>
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
function initializeGoogleRouteMap(mapId, legCoords, vehiclePosition, frm) {
  // Use interactive Google Maps JavaScript API instead of static maps
  const waypoints = [];
  legCoords.forEach(legData => {
    waypoints.push(`${legData.pick.lat},${legData.pick.lon}`);
    waypoints.push(`${legData.drop.lat},${legData.drop.lon}`);
  });
  
  // Add vehicle position as a marker if available
  if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
    waypoints.push(`${vehiclePosition.latitude},${vehiclePosition.longitude}`);
  }
  
  const firstPick = legCoords[0].pick;
  const lastDrop = legCoords[legCoords.length - 1].drop;
  
  // Get API key from settings
  frappe.call({
    method: 'logistics.transport.api_vehicle_tracking.get_google_maps_api_key'
  }).then(response => {
    const apiKey = response.message?.api_key;
    
    if (apiKey && apiKey.length > 10) {
      // First, get the actual route polyline from Google Directions API
      const waypointStr = waypoints.join('|');
      
      frappe.call({
        method: 'logistics.transport.api_vehicle_tracking.get_google_route_polyline',
        args: {
          waypoints: waypointStr
        }
      }).then(polylineResponse => {
        const mapElement = document.getElementById(mapId);
        if (!mapElement) return;
        
        if (polylineResponse.message && polylineResponse.message.success) {
          const routes = polylineResponse.message.routes || [];
          const savedRouteIndex = frm && frm.doc && frm.doc.selected_route_index !== undefined ? frm.doc.selected_route_index : null;
          
          // Determine which route to show (saved route or first route)
          let selectedRouteIndex = 0;
          if (savedRouteIndex !== null && savedRouteIndex >= 0 && savedRouteIndex < routes.length) {
            const savedRoute = routes.find(r => r.index === savedRouteIndex);
            if (savedRoute) {
              selectedRouteIndex = routes.indexOf(savedRoute);
            }
          }
          
          const selectedRoute = routes[selectedRouteIndex];
          
          if (selectedRoute) {
            const routeIndex = selectedRoute.index;
            
            // Store routes globally for selection
            if (!window.runSheetRoutes) window.runSheetRoutes = {};
            window.runSheetRoutes[mapId] = routes;
            
            // Load Google Maps JavaScript API if not already loaded
            if (window.google && window.google.maps) {
              initializeInteractiveGoogleMap(mapId, routes, routeIndex, firstPick, lastDrop, vehiclePosition, frm, apiKey);
            } else {
              // Load Google Maps JavaScript API
              const script = document.createElement('script');
              script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=geometry`;
              script.async = true;
              script.defer = true;
              script.onload = () => {
                initializeInteractiveGoogleMap(mapId, routes, routeIndex, firstPick, lastDrop, vehiclePosition, frm, apiKey);
              };
              script.onerror = () => {
                console.warn('Failed to load Google Maps JavaScript API, showing fallback');
                showMapFallback(mapId);
              };
              document.head.appendChild(script);
            }
          } else {
            console.warn('No routes available');
            showMapFallback(mapId);
          }
        } else {
          console.warn('Google Directions API failed:', polylineResponse.message?.error);
          showMapFallback(mapId);
        }
      }).catch(() => {
        console.warn('Error getting route polyline');
        showMapFallback(mapId);
      });
    } else {
      console.warn('Google Maps API key not configured, showing fallback');
      showMapFallback(mapId);
    }
  }).catch(() => {
    showMapFallback(mapId);
  });
}

// Initialize interactive Google Maps with routes
function initializeInteractiveGoogleMap(mapId, routes, selectedRouteIndex, firstPick, lastDrop, vehiclePosition, frm, apiKey) {
  const mapElement = document.getElementById(mapId);
  if (!mapElement) return;
  
  // Clear any existing content
  mapElement.innerHTML = '';
  
  // Create route selector UI - always show if multiple routes
  let routeSelectorHtml = '';
  console.log(`Initializing map with ${routes.length} routes, selected index: ${selectedRouteIndex}`);
  if (routes.length > 1) {
    const routeIndex = routes[selectedRouteIndex].index;
    routeSelectorHtml = `
      <div style="position: absolute; top: 10px; left: 10px; background: white; padding: 10px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); z-index: 1000; max-width: 300px;">
        <div style="font-weight: bold; margin-bottom: 8px; font-size: 12px;">Select Route (${routes.length} options):</div>
        ${routes.map((route, idx) => {
          const isSelected = route.index === routeIndex;
          return `
          <div 
            class="route-option" 
            data-route-index="${route.index}"
            style="padding: 8px; margin: 4px 0; border: 2px solid ${isSelected ? '#007bff' : '#ddd'}; border-radius: 4px; cursor: pointer; background: ${isSelected ? '#e7f3ff' : '#fff'}; font-size: 11px; transition: all 0.2s;"
            onmouseover="this.style.background='#f0f0f0'"
            onmouseout="this.style.background='${isSelected ? '#e7f3ff' : '#fff'}'"
            onclick="window.selectRouteByIndex('${mapId}', ${route.index}, '${(frm && frm.doc && frm.doc.name) ? frm.doc.name : ''}')"
          >
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong>Route ${route.index + 1}</strong>
                ${isSelected ? '<span style="color: #007bff; margin-left: 5px;">✓ Selected</span>' : ''}
              </div>
            </div>
            <div style="margin-top: 4px; color: #666;">
              ${route.distance_km} km • ${route.duration_min} min
            </div>
          </div>
        `;
        }).join('')}
      </div>
    `;
  }
  
  mapElement.innerHTML = routeSelectorHtml;
  
  // Initialize the map
  const bounds = new google.maps.LatLngBounds();
  const map = new google.maps.Map(mapElement, {
    zoom: 10,
    center: { lat: (firstPick.lat + lastDrop.lat) / 2, lng: (firstPick.lon + lastDrop.lon) / 2 },
    mapTypeControl: true,
    streetViewControl: true,
    fullscreenControl: true,
    zoomControl: true,
    scaleControl: true,
    rotateControl: true
  });
  
  // Store map instance globally for route updates
  if (!window.runSheetMaps) window.runSheetMaps = {};
  window.runSheetMaps[mapId] = map;
  
  // Store polylines for route updates
  if (!window.runSheetPolylines) window.runSheetPolylines = {};
  window.runSheetPolylines[mapId] = [];
  
  // Add markers and routes
  const selectedRoute = routes[selectedRouteIndex];
  const routeIndex = selectedRoute.index;
  
  // Add start marker
  const startMarker = new google.maps.Marker({
    position: { lat: firstPick.lat, lng: firstPick.lon },
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
  bounds.extend({ lat: firstPick.lat, lng: firstPick.lon });
  
  // Add end marker
  const endMarker = new google.maps.Marker({
    position: { lat: lastDrop.lat, lng: lastDrop.lon },
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
  bounds.extend({ lat: lastDrop.lat, lng: lastDrop.lon });
  
  // Add vehicle position marker if available
  if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
    const vehicleMarker = new google.maps.Marker({
      position: { lat: vehiclePosition.latitude, lng: vehiclePosition.longitude },
      map: map,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: '#0000ff',
        fillOpacity: 1,
        strokeColor: '#ffffff',
        strokeWeight: 2
      },
      title: 'Vehicle Position'
    });
    bounds.extend({ lat: vehiclePosition.latitude, lng: vehiclePosition.longitude });
  }
  
  // Add all route polylines
  console.log(`Adding ${routes.length} routes to map`);
  routes.forEach((route) => {
    const isSelected = route.index === routeIndex;
    try {
      const path = google.maps.geometry.encoding.decodePath(route.polyline);
      
      if (!path || path.length === 0) {
        console.warn(`Route ${route.index} has invalid polyline`);
        return;
      }
      
      // Extend bounds with route path
      path.forEach(point => bounds.extend(point));
      
      const polyline = new google.maps.Polyline({
        path: path,
        geodesic: true,
        strokeColor: isSelected ? '#007bff' : '#dc3545',  // Red for alternate routes to make them more visible
        strokeOpacity: isSelected ? 1.0 : 0.8,  // High opacity for better visibility
        strokeWeight: isSelected ? 6 : 4,  // Thicker lines for better visibility
        map: map,
        zIndex: isSelected ? 2 : 1,
        clickable: true  // Make routes clickable
      });
      
      // Add click handler to select route when clicking on polyline
      if (!isSelected) {
        polyline.addListener('click', () => {
          const frm = cur_frm;
          if (frm && frm.doc && frm.doc.name) {
            window.selectRouteByIndex(mapId, route.index, frm.doc.name);
          }
        });
      }
      
      window.runSheetPolylines[mapId].push({
        polyline: polyline,
        routeIndex: route.index
      });
      
      console.log(`Added route ${route.index} (selected: ${isSelected})`);
    } catch (error) {
      console.error(`Error adding route ${route.index}:`, error);
    }
  });
  
  // Fit map to show all routes
  map.fitBounds(bounds);
  
  // Hide fallback
  hideMapFallback(mapId);
}

// Select a route by index and save it (global function for onclick handler)
window.selectRouteByIndex = function(mapId, routeIndex, runSheetName) {
  if (!runSheetName) {
    frappe.show_alert({
      message: __('Please save the Run Sheet first before selecting a route'),
      indicator: 'orange'
    });
    return;
  }
  
  // Get the route from stored routes
  const routes = window.runSheetRoutes && window.runSheetRoutes[mapId];
  if (!routes) {
    frappe.show_alert({
      message: __('Route data not available. Please refresh the map.'),
      indicator: 'orange'
    });
    return;
  }
  
  const selectedRoute = routes.find(r => r.index === routeIndex);
  if (!selectedRoute) {
    frappe.show_alert({
      message: __('Route not found'),
      indicator: 'red'
    });
    return;
  }
  
  // Update UI
  const mapElement = document.getElementById(mapId);
  if (mapElement) {
    const routeOptions = mapElement.querySelectorAll('.route-option');
    routeOptions.forEach(option => {
      const currentIdx = parseInt(option.dataset.routeIndex);
      if (currentIdx === routeIndex) {
        option.style.borderColor = '#007bff';
        option.style.backgroundColor = '#e7f3ff';
        const checkmark = option.querySelector('span');
        if (checkmark) checkmark.innerHTML = '✓ Selected';
      } else {
        option.style.borderColor = '#ddd';
        option.style.backgroundColor = '#fff';
        const checkmark = option.querySelector('span');
        if (checkmark && checkmark.textContent.includes('Selected')) {
          checkmark.innerHTML = '';
        }
      }
    });
  }
  
  // Update interactive map polylines if available
  const map = window.runSheetMaps && window.runSheetMaps[mapId];
  const polylines = window.runSheetPolylines && window.runSheetPolylines[mapId];
  if (map && polylines && window.google && window.google.maps) {
    polylines.forEach(polylineData => {
      const isSelected = polylineData.routeIndex === routeIndex;
      polylineData.polyline.setOptions({
        strokeColor: isSelected ? '#007bff' : '#dc3545',
        strokeOpacity: isSelected ? 1.0 : 0.8,
        strokeWeight: isSelected ? 6 : 4,
        zIndex: isSelected ? 2 : 1
      });
    });
  }
  
  // Save the selected route to Run Sheet (will sync to legs automatically)
  frappe.call({
    method: 'logistics.transport.api_vehicle_tracking.save_selected_route',
    args: {
      run_sheet_name: runSheetName,
      route_index: routeIndex,
      polyline: selectedRoute.polyline,
      distance_km: selectedRoute.distance_km,
      duration_min: selectedRoute.duration_min,
      route_type: 'run_sheet'
    }
  }).then(response => {
    if (response.message && response.message.success) {
      frappe.show_alert({
        message: __('Route ${0} selected and saved. Individual leg routes cleared for recalculation.', [routeIndex + 1]),
        indicator: 'green'
      });
      
      // Reload the form to refresh the map with saved route
      if (cur_frm && cur_frm.doc.name === runSheetName) {
        cur_frm.reload_doc();
      }
    } else {
      frappe.show_alert({
        message: __('Failed to save route: ${0}', [response.message?.error || 'Unknown error']),
        indicator: 'red'
      });
    }
  }).catch(error => {
    frappe.show_alert({
      message: __('Error saving route: ${0}', [error.message || 'Unknown error']),
      indicator: 'red'
    });
  });
}

// Initialize Mapbox for multi-leg route
function initializeMapboxRouteMap(mapId, legCoords, vehiclePosition, frm) {
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
      createMapboxRouteMap(mapId, legCoords, vehiclePosition, frm);
    };
    document.head.appendChild(mapboxJS);
  } else {
    createMapboxRouteMap(mapId, legCoords, vehiclePosition, frm);
  }
}

function createMapboxRouteMap(mapId, legCoords, vehiclePosition, frm) {
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
        
        legCoords.forEach((legData, index) => {
          const { leg, pick, drop } = legData;
          
          // Pick marker (red)
          const pickMarker = new mapboxgl.Marker({
            element: createMarkerElement('P' + (index + 1), 'red'),
            anchor: 'center'
          }).setLngLat([pick.lon, pick.lat]).addTo(map);
          
          // Drop marker (green)
          const dropMarker = new mapboxgl.Marker({
            element: createMarkerElement('D' + (index + 1), 'green'),
            anchor: 'center'
          }).setLngLat([drop.lon, drop.lat]).addTo(map);
          
          // Add popups
          pickMarker.setPopup(new mapboxgl.Popup().setHTML(`
            <strong>Stop ${index + 1} - Pickup</strong><br>
            Leg: ${leg.transport_leg || 'N/A'}<br>
            Coordinates: ${pick.lat.toFixed(4)}, ${pick.lon.toFixed(4)}
          `));
          
          dropMarker.setPopup(new mapboxgl.Popup().setHTML(`
            <strong>Stop ${index + 1} - Drop</strong><br>
            Leg: ${leg.transport_leg || 'N/A'}<br>
            Coordinates: ${drop.lat.toFixed(4)}, ${drop.lon.toFixed(4)}
          `));
          
          allMarkers.push(pickMarker, dropMarker);
          allWaypoints.push([pick.lon, pick.lat], [drop.lon, drop.lat]);
        });
        
        // Add overall route line connecting all waypoints in sequence
        if (allWaypoints.length > 2) {
          map.on('load', () => {
            map.addSource('route', {
              type: 'geojson',
              data: {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: allWaypoints
                }
              }
            });
            
            map.addLayer({
              id: 'route',
              type: 'line',
              source: 'route',
              layout: {
                'line-join': 'round',
                'line-cap': 'round'
              },
              paint: {
                'line-color': 'purple',
                'line-width': 5,
                'line-opacity': 0.8,
                'line-dasharray': [2, 2]
              }
            });
          });
        }
        
        // Add vehicle/truck marker if position is available (Mapbox)
        console.log('=== MAPBOX TRUCK MARKER SECTION ===');
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          console.log('Mapbox: ✓ Adding truck marker');
          
          const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
          const ignition = vehiclePosition.ignition ? 'ON' : 'OFF';
          const ignitionOn = vehiclePosition.ignition;
          
          // Font Awesome truck in white circle (Mapbox)
          const truckEl = document.createElement('div');
          truckEl.innerHTML = `
            <div style="position: relative; width: 80px; height: 68px;">
              <!-- Ignition status card (above truck) -->
              <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: ${ignitionOn ? '#10b981' : '#6b7280'}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 9px; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                Ignition: ${ignition}
              </div>
              
              <!-- White circle with blue truck icon -->
              <div style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 40px; height: 40px; background: white; border-radius: 50%; border: 2px solid #e5e7eb; box-shadow: 0 3px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                <i class="fa fa-truck" style="color: #2563eb; font-size: 20px;"></i>
                <!-- Small ignition circle -->
                <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; background: ${ignitionOn ? '#10b981' : '#ef4444'}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
              </div>
              
              <!-- Vehicle name label (below truck) -->
              <div style="position: absolute; top: 62px; left: 50%; transform: translateX(-50%); background: white; color: #007bff; padding: 2px 8px; border-radius: 3px; white-space: nowrap; font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid #e5e7eb;">
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
                <strong>Ignition:</strong> ${ignition === 'ON' ? '<span style="color: #10b981;">ON</span>' : '<span style="color: #6b7280;">OFF</span>'}<br>
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
                  // First refresh vehicle data to get latest position and ignition status
                  const refreshResult = await frappe.call({
                    method: 'logistics.transport.api_vehicle_tracking.refresh_vehicle_data',
                    args: {
                      vehicle_name: frm.doc.vehicle
                    }
                  });
                  
                  let currentPosition = vehiclePosition;
                  let refreshMessage = '';
                  
                  if (refreshResult.message && refreshResult.message.success) {
                    console.log('Mapbox: ✓ Vehicle data refreshed for location:', refreshResult.message);
                    currentPosition = refreshResult.message;
                    
                    // Update stored position
                    window[`${mapId}_vehiclePosition`] = currentPosition;
                    
                    refreshMessage = ` - Ignition: ${currentPosition.ignition ? 'ON' : 'OFF'}, Speed: ${currentPosition.speed_kph ? currentPosition.speed_kph.toFixed(1) : 'N/A'} km/h`;
                    
                    // Update marker position if we have fresh data
                    truckMarker.setLngLat([currentPosition.longitude, currentPosition.latitude]);
                    
                    // Update marker popup with fresh data
                    const speedDisplay = currentPosition.speed_kph ? `${currentPosition.speed_kph.toFixed(1)} km/h` : 'N/A';
                    const fuelDisplay = currentPosition.fuel_level ? `${currentPosition.fuel_level}%` : null;
                    const odometerDisplay = currentPosition.odometer_km ? `${currentPosition.odometer_km.toFixed(1)} km` : null;
                    const ignition = currentPosition.ignition ? 'ON' : 'OFF';
                    const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
                    
                    truckMarker.setPopup(new mapboxgl.Popup({offset: 25}).setHTML(`
                      <div style="padding: 6px;">
                        <div style="font-weight: 600; font-size: 13px; color: #007bff; margin-bottom: 8px;">${vehicleName}</div>
                        <div style="font-size: 11px; color: #6b7280; line-height: 1.6;">
                          <strong>Ignition:</strong> ${ignition === 'ON' ? '<span style="color: #10b981;">ON</span>' : '<span style="color: #6b7280;">OFF</span>'}<br>
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

function initializeMapLibreRouteMap(mapId, legCoords, vehiclePosition, frm) {
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
      createMapLibreRouteMap(mapId, legCoords, vehiclePosition, frm);
    };
    document.head.appendChild(mapLibreJS);
  } else {
    createMapLibreRouteMap(mapId, legCoords, vehiclePosition, frm);
  }
}

function createMapLibreRouteMap(mapId, legCoords, vehiclePosition, frm) {
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
        
        legCoords.forEach((legData, index) => {
          const { leg, pick, drop } = legData;
          
          // Pick marker (red)
          const pickMarker = new maplibregl.Marker({
            element: createMarkerElement('P' + (index + 1), 'red'),
            anchor: 'center'
          }).setLngLat([pick.lon, pick.lat]).addTo(map);
          
          // Drop marker (green)
          const dropMarker = new maplibregl.Marker({
            element: createMarkerElement('D' + (index + 1), 'green'),
            anchor: 'center'
          }).setLngLat([drop.lon, drop.lat]).addTo(map);
          
          // Add popups
          pickMarker.setPopup(new maplibregl.Popup().setHTML(`
            <strong>Stop ${index + 1} - Pickup</strong><br>
            Leg: ${leg.transport_leg || 'N/A'}<br>
            Coordinates: ${pick.lat.toFixed(4)}, ${pick.lon.toFixed(4)}
          `));
          
          dropMarker.setPopup(new maplibregl.Popup().setHTML(`
            <strong>Stop ${index + 1} - Drop</strong><br>
            Leg: ${leg.transport_leg || 'N/A'}<br>
            Coordinates: ${drop.lat.toFixed(4)}, ${drop.lon.toFixed(4)}
          `));
          
          allMarkers.push(pickMarker, dropMarker);
          allWaypoints.push([pick.lon, pick.lat], [drop.lon, drop.lat]);
        });
        
        // Add overall route line connecting all waypoints in sequence
        if (allWaypoints.length > 2) {
          map.on('load', () => {
            map.addSource('route', {
              type: 'geojson',
              data: {
                type: 'Feature',
                properties: {},
                geometry: {
                  type: 'LineString',
                  coordinates: allWaypoints
                }
              }
            });
            
            map.addLayer({
              id: 'route',
              type: 'line',
              source: 'route',
              layout: {
                'line-join': 'round',
                'line-cap': 'round'
              },
              paint: {
                'line-color': 'purple',
                'line-width': 5,
                'line-opacity': 0.8,
                'line-dasharray': [2, 2]
              }
            });
          });
        }
        
        // Add vehicle/truck marker if position is available (MapLibre)
        console.log('=== MAPLIBRE TRUCK MARKER SECTION ===');
        console.log('Checking if we should add truck marker...');
        console.log('vehiclePosition exists?', !!vehiclePosition);
        console.log('vehiclePosition.latitude?', vehiclePosition?.latitude);
        console.log('vehiclePosition.longitude?', vehiclePosition?.longitude);
        
        if (vehiclePosition && vehiclePosition.latitude && vehiclePosition.longitude) {
          console.log('MapLibre: ✓ CONDITION MET - Adding truck marker');
          
          const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
          const ignition = vehiclePosition.ignition ? 'ON' : 'OFF';
          const ignitionOn = vehiclePosition.ignition;
          
          // Font Awesome truck in white circle (MapLibre)
          const truckEl = document.createElement('div');
          truckEl.className = 'maplibre-truck-marker';
          truckEl.innerHTML = `
            <div style="position: relative; width: 80px; height: 68px;">
              <!-- Ignition status card (above truck) -->
              <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); background: ${ignitionOn ? '#10b981' : '#6b7280'}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 9px; font-weight: 600; white-space: nowrap; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                Ignition: ${ignition}
              </div>
              
              <!-- White circle with blue truck icon -->
              <div style="position: absolute; top: 20px; left: 50%; transform: translateX(-50%); width: 40px; height: 40px; background: white; border-radius: 50%; border: 2px solid #e5e7eb; box-shadow: 0 3px 8px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                <i class="fa fa-truck" style="color: #2563eb; font-size: 20px;"></i>
                <!-- Small ignition circle -->
                <div style="position: absolute; top: -2px; right: -2px; width: 12px; height: 12px; background: ${ignitionOn ? '#10b981' : '#ef4444'}; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.4);"></div>
              </div>
              
              <!-- Vehicle name label (below truck) -->
              <div style="position: absolute; top: 62px; left: 50%; transform: translateX(-50%); background: white; color: #007bff; padding: 2px 8px; border-radius: 3px; white-space: nowrap; font-size: 11px; font-weight: 700; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid #e5e7eb;">
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
                <strong>Ignition:</strong> ${ignition === 'ON' ? '<span style="color: #10b981;">ON</span>' : '<span style="color: #6b7280;">OFF</span>'}<br>
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
                  // First refresh vehicle data to get latest position and ignition status
                  const refreshResult = await frappe.call({
                    method: 'logistics.transport.api_vehicle_tracking.refresh_vehicle_data',
                    args: {
                      vehicle_name: frm.doc.vehicle
                    }
                  });
                  
                  let currentPosition = vehiclePosition;
                  let refreshMessage = '';
                  
                  if (refreshResult.message && refreshResult.message.success) {
                    console.log('MapLibre: ✓ Vehicle data refreshed for location:', refreshResult.message);
                    currentPosition = refreshResult.message;
                    
                    // Update stored position
                    window[`${mapId}_vehiclePosition`] = currentPosition;
                    
                    refreshMessage = ` - Ignition: ${currentPosition.ignition ? 'ON' : 'OFF'}, Speed: ${currentPosition.speed_kph ? currentPosition.speed_kph.toFixed(1) : 'N/A'} km/h`;
                    
                    // Update marker position if we have fresh data
                    truckMarker.setLngLat([currentPosition.longitude, currentPosition.latitude]);
                    
                    // Update marker popup with fresh data
                    const speedDisplay = currentPosition.speed_kph ? `${currentPosition.speed_kph.toFixed(1)} km/h` : 'N/A';
                    const fuelDisplay = currentPosition.fuel_level ? `${currentPosition.fuel_level}%` : null;
                    const odometerDisplay = currentPosition.odometer_km ? `${currentPosition.odometer_km.toFixed(1)} km` : null;
                    const ignition = currentPosition.ignition ? 'ON' : 'OFF';
                    const vehicleName = (frm && frm.doc && frm.doc.vehicle) || 'Vehicle';
                    
                    truckMarker.setPopup(new maplibregl.Popup({offset: 25}).setHTML(`
                      <div style="padding: 6px;">
                        <div style="font-weight: 600; font-size: 13px; color: #007bff; margin-bottom: 8px;">${vehicleName}</div>
                        <div style="font-size: 11px; color: #6b7280; line-height: 1.6;">
                          <strong>Ignition:</strong> ${ignition === 'ON' ? '<span style="color: #10b981;">ON</span>' : '<span style="color: #6b7280;">OFF</span>'}<br>
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

// ---------- Transport Leg Action Functions ----------
window.startTransportLeg = function(transportLegName) {
  console.log('Start Transport Leg:', transportLegName);
  if (!transportLegName) {
    frappe.show_alert({message: __('No transport leg linked'), indicator: 'orange'});
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
        // Refresh the map to update status badges
        if (cur_frm) {
          render_run_sheet_route_map(cur_frm);
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
        // Refresh the map to update status badges
        if (cur_frm) {
          render_run_sheet_route_map(cur_frm);
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
    if (frm.doc.name) {
      render_run_sheet_route_map(frm);
      
      // Fetch and update missing data from Transport Leg
      update_legs_missing_data_rs(frm);
      
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
      }
    }
  },
  
  validate(frm) {
    // Fetch and update missing data from Transport Leg before save
    update_legs_missing_data_rs(frm);
  },
  
  legs(frm) {
    if (frm.doc.name) {
      render_run_sheet_route_map(frm);
    }
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