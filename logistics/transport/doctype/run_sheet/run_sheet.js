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
    
    const mapHtml = `
      <div class="text-muted small" style="margin-bottom: 10px; display: flex; gap: 20px; align-items: center; justify-content: center;">
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
      <div style="width: 100%; height: 500px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative;">
        <div id="${mapId}" style="width: 100%; height: 100%;"></div>
        <div style="position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.9); padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; z-index: 1000;">
          <span style="color: blue;">●</span> ${legs.length} Stops
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
    `;
    
    $wrapper.html(mapHtml);
    
    // Show fallback initially
    showMapFallback(mapId);
    
    // Initialize multi-leg route map
    setTimeout(() => {
      initializeRunSheetRouteMap(mapId, legs, mapRenderer);
    }, 100);
    
  } catch (error) {
    console.error('Error rendering run sheet route map:', error);
    $wrapper.html('<div class="text-muted">Unable to load route map</div>');
  }
}

// Initialize multi-leg route map
async function initializeRunSheetRouteMap(mapId, legs, mapRenderer) {
  try {
    // Get coordinates for all legs
    const legCoords = [];
    const allCoords = [];
    
    const missingAddresses = [];
    
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
    
    // Update external links with first and last coordinates
    updateExternalLinks(mapId, legCoords);
    
    // Initialize map based on renderer
    if (mapRenderer && mapRenderer.toLowerCase() === 'google maps') {
      initializeGoogleRouteMap(mapId, legCoords);
    } else if (mapRenderer && mapRenderer.toLowerCase() === 'mapbox') {
      initializeMapboxRouteMap(mapId, legCoords);
    } else if (mapRenderer && mapRenderer.toLowerCase() === 'maplibre') {
      initializeMapLibreRouteMap(mapId, legCoords);
    } else {
      initializeOpenStreetRouteMap(mapId, legCoords);
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
function initializeOpenStreetRouteMap(mapId, legCoords) {
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
      createOpenStreetRouteMap(mapId, legCoords);
    };
    document.head.appendChild(leafletJS);
  } else {
    createOpenStreetRouteMap(mapId, legCoords);
  }
}

function createOpenStreetRouteMap(mapId, legCoords) {
  const checkElement = () => {
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      try {
        // Calculate bounds
        const allLats = [];
        const allLons = [];
        legCoords.forEach(leg => {
          allLats.push(leg.pick.lat, leg.drop.lat);
          allLons.push(leg.pick.lon, leg.drop.lon);
        });
        
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
        
        legCoords.forEach((legData, index) => {
          const { leg, pick, drop } = legData;
          
          // Pick marker (red)
          const pickMarker = L.marker([pick.lat, pick.lon], {
            icon: L.divIcon({
              className: 'custom-div-icon',
              html: `<div style="background-color: red; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 10px;">P${index + 1}</div>`,
              iconSize: [20, 20],
              iconAnchor: [10, 10]
            })
          }).addTo(map);
          
          // Drop marker (green)
          const dropMarker = L.marker([drop.lat, drop.lon], {
            icon: L.divIcon({
              className: 'custom-div-icon',
              html: `<div style="background-color: green; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 10px;">D${index + 1}</div>`,
              iconSize: [20, 20],
              iconAnchor: [10, 10]
            })
          }).addTo(map);
          
          // Add popups
          pickMarker.bindPopup(`<strong>Stop ${index + 1} - Pickup</strong><br>Leg: ${leg.transport_leg || 'N/A'}<br>Coordinates: ${pick.lat.toFixed(4)}, ${pick.lon.toFixed(4)}`);
          dropMarker.bindPopup(`<strong>Stop ${index + 1} - Drop</strong><br>Leg: ${leg.transport_leg || 'N/A'}<br>Coordinates: ${drop.lat.toFixed(4)}, ${drop.lon.toFixed(4)}`);
          
          // Add individual leg route line
          const routeLine = L.polyline([
            [pick.lat, pick.lon],
            [drop.lat, drop.lon]
          ], {
            color: index === 0 ? 'blue' : 'orange',
            weight: 3,
            opacity: 0.6,
            dashArray: index === 0 ? '5, 5' : '10, 10'
          }).addTo(map);
          
          allMarkers.push(pickMarker, dropMarker);
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
        
        // Fit map to show all markers
        const group = new L.featureGroup(allMarkers);
        map.fitBounds(group.getBounds().pad(0.1));
        
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
function initializeGoogleRouteMap(mapId, legCoords) {
  // For Google Maps, we'll use a static map with waypoints
  // This is more reliable than trying to load the full Google Maps API
  const waypoints = [];
  legCoords.forEach(legData => {
    waypoints.push(`${legData.pick.lat},${legData.pick.lon}`);
    waypoints.push(`${legData.drop.lat},${legData.drop.lon}`);
  });
  
  const firstPick = legCoords[0].pick;
  const lastDrop = legCoords[legCoords.length - 1].drop;
  
  // Get API key from settings
  frappe.call({
    method: 'frappe.client.get_value',
    args: {
      doctype: 'Transport Settings',
      fieldname: 'routing_google_api_key'
    }
  }).then(settings => {
    const apiKey = settings.message?.routing_google_api_key;
    
    if (apiKey && apiKey.length > 10) {
      // Use Google Static Maps API with waypoints
      const waypointStr = waypoints.slice(1, -1).join('|');
      const staticMapUrl = `https://maps.googleapis.com/maps/api/staticmap?key=${apiKey}&size=600x400&maptype=roadmap&markers=color:red|label:A|${firstPick.lat},${firstPick.lon}&markers=color:green|label:B|${lastDrop.lat},${lastDrop.lon}&path=color:0x0000ff|weight:5|${waypoints.join('|')}`;
      
      const mapElement = document.getElementById(mapId);
      if (mapElement) {
        const testImg = new Image();
        testImg.onload = function() {
          hideMapFallback(mapId);
          mapElement.innerHTML = `
            <img 
              src="${staticMapUrl}" 
              alt="Multi-leg Route Map" 
              style="width: 100%; height: 100%; object-fit: cover;"
            />
          `;
        };
        testImg.onerror = function() {
          console.warn('Google Maps Static API failed, showing fallback');
        };
        testImg.src = staticMapUrl;
      }
    } else {
      console.warn('Google Maps API key not configured, showing fallback');
      showMapFallback(mapId);
    }
  }).catch(() => {
    showMapFallback(mapId);
  });
}

// Initialize Mapbox for multi-leg route
function initializeMapboxRouteMap(mapId, legCoords) {
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
      createMapboxRouteMap(mapId, legCoords);
    };
    document.head.appendChild(mapboxJS);
  } else {
    createMapboxRouteMap(mapId, legCoords);
  }
}

function createMapboxRouteMap(mapId, legCoords) {
  const checkElement = () => {
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      try {
        // Calculate bounds
        const allLats = [];
        const allLons = [];
        legCoords.forEach(leg => {
          allLats.push(leg.pick.lat, leg.drop.lat);
          allLons.push(leg.pick.lon, leg.drop.lon);
        });
        
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

function initializeMapLibreRouteMap(mapId, legCoords) {
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
      createMapLibreRouteMap(mapId, legCoords);
    };
    document.head.appendChild(mapLibreJS);
  } else {
    createMapLibreRouteMap(mapId, legCoords);
  }
}

function createMapLibreRouteMap(mapId, legCoords) {
  const checkElement = () => {
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      try {
        // Calculate bounds
        const allLats = [];
        const allLons = [];
        legCoords.forEach(leg => {
          allLats.push(leg.pick.lat, leg.drop.lat);
          allLons.push(leg.pick.lon, leg.drop.lon);
        });
        
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

// ---------- form bindings ----------
frappe.ui.form.on('Run Sheet', {
  refresh(frm) {
    if (frm.doc.name) {
      render_run_sheet_route_map(frm);
    }
  },
  
  legs(frm) {
    if (frm.doc.name) {
      render_run_sheet_route_map(frm);
    }
  }
});