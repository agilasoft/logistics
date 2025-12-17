// logistics/transport/doctype/transport_leg/transport_leg.js
// Map-free: uses only external map links (GMaps/OSM/Apple Maps). No Leaflet, no polyline.

// ---------- utils ----------
function isFiniteNum(n) { return typeof n === "number" && isFinite(n); }
function toNumber(v) {
  const n = typeof v === "number" ? v : parseFloat(v);
  return isNaN(n) ? 0 : n;
}
function parseJSONSafe(v) {
  try { return typeof v === "string" ? JSON.parse(v) : v; } catch { return null; }
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

// Extract one {lat, lon} from Address.custom_geolocation (GeoJSON) or legacy lat/long fields
async function getAddressLatLon(addrname) {
  if (!addrname) return null;

  let d = null;
  try {
    d = await frappe.db.get_doc("Address", addrname);
  } catch (e) {
    return null;
  }
  if (!d) return null;

  const lat = d.custom_latitude;
  const lon = d.custom_longitude;

  const nlat = typeof lat === "number" ? lat : parseFloat(lat);
  const nlon = typeof lon === "number" ? lon : parseFloat(lon);

  if (isFinite(nlat) && isFinite(nlon)) {
    return { lat: nlat, lon: nlon };
  }
  return null;
}

function extractLatLonFromGeo(geo) {
  if (!geo) return null;
  if (typeof geo === "object" && isFiniteNum(toNumber(geo.lat)) && isFiniteNum(toNumber(geo.lng))) {
    return { lat: toNumber(geo.lat), lon: toNumber(geo.lng) };
  }
  if (geo && geo.type === "FeatureCollection" && Array.isArray(geo.features)) {
    for (const f of geo.features) {
      const r = extractLatLonFromGeo(f);
      if (r) return r;
    }
    return null;
  }
  if (geo && geo.type === "Feature" && geo.geometry) {
    return extractLatLonFromGeo(geo.geometry);
  }
  if (geo && geo.type === "Point" && Array.isArray(geo.coordinates) && geo.coordinates.length >= 2) {
    const [lon, lat] = geo.coordinates;
    if (isFiniteNum(toNumber(lat)) && isFiniteNum(toNumber(lon))) {
      return { lat: toNumber(lat), lon: toNumber(lon) };
    }
  }
  return null;
}

// ---------- Address filters + HTML ----------
function set_pick_query(frm) {
  frm.set_query('pick_address', () => {
    if (frm.doc.facility_type_from && frm.doc.facility_from) {
      return { filters: { link_doctype: frm.doc.facility_type_from, link_name: frm.doc.facility_from } };
    }
    return { filters: { name: '__none__' } };
  });
}
function set_drop_query(frm) {
  frm.set_query('drop_address', () => {
    if (frm.doc.facility_type_to && frm.doc.facility_to) {
      return { filters: { link_doctype: frm.doc.facility_type_to, link_name: frm.doc.facility_to } };
    }
    return { filters: { name: '__none__' } };
  });
}

// ---------- Auto-fill Address Functions ----------
async function auto_fill_pick_address(frm) {
  if (!frm.doc.facility_type_from || !frm.doc.facility_from) {
    return;
  }
  
  try {
    const result = await frappe.call({
      method: 'logistics.transport.doctype.transport_leg.transport_leg.get_primary_address',
      args: {
        facility_type: frm.doc.facility_type_from,
        facility_name: frm.doc.facility_from
      }
    });
    
    if (result.message && !frm.doc.pick_address) {
      frm.set_value('pick_address', result.message);
    }
  } catch (error) {
    console.error('Error auto-filling pick address:', error);
  }
}

async function auto_fill_drop_address(frm) {
  if (!frm.doc.facility_type_to || !frm.doc.facility_to) {
    return;
  }
  
  try {
    const result = await frappe.call({
      method: 'logistics.transport.doctype.transport_leg.transport_leg.get_primary_address',
      args: {
        facility_type: frm.doc.facility_type_to,
        facility_name: frm.doc.facility_to
      }
    });
    
    if (result.message && !frm.doc.drop_address) {
      frm.set_value('drop_address', result.message);
    }
  } catch (error) {
    console.error('Error auto-filling drop address:', error);
  }
}

function render_address_html(frm, src_field, html_field_candidates) {
  const addr = frm.doc[src_field];
  const html_field = html_field_candidates.find((f) => frm.fields_dict[f]);
  if (!html_field) return;
  const $wrapper = frm.get_field(html_field).$wrapper;
  if (!addr) { $wrapper && $wrapper.html(''); frm.set_value(html_field, ''); return; }
  frappe.call({
    method: 'frappe.contacts.doctype.address.address.get_address_display',
    args: { address_dict: addr },
    callback: (r) => {
      const html = r.message || '';
      if ($wrapper) $wrapper.html(html);
      frm.set_value(html_field, html);
    },
  });
}
function render_pick_address(frm) { render_address_html(frm, 'pick_address', ['pick_address_html', 'pick_address_format']); }
function render_drop_address(frm) { render_address_html(frm, 'drop_address', ['drop_address_html']); }

// ---------- Action buttons ----------
async function addActionButtons(frm) {
  if (frm._tl_buttons_added) return;
  frm._tl_buttons_added = true;

  frm.page.add_action_item(__("Regenerate Routing"), () => run_regenerate_routing(frm));
  frm.page.add_action_item(__("Regenerate Carbon (CO₂e)"), () => run_regenerate_carbon(frm));
}

// ---------- actions ----------
async function run_regenerate_routing(frm) {
  if (!frm.doc.name) return;
  if (!frm.doc.pick_address || !frm.doc.drop_address) {
    frappe.msgprint({ title: __("Regenerate Routing"), message: __("Pick and Drop Address must be set before computing routing."), indicator: "red" });
    return;
  }
  frappe.dom.freeze(__("Computing route…"));
  try {
    const r = await frappe.call({
      method: "logistics.transport.doctype.transport_leg.transport_leg.regenerate_routing",
      args: { leg_name: frm.doc.name },
    });
    await frm.reload_doc();
    const m = (r && r.message) || {};
    frappe.show_alert(
      {
        message: __("{0}: {1} km • {2} min • {3}", [
          __("Route"),
          fmt_num(m.distance_km, 3),
          fmt_num(m.duration_min, 1),
          m.provider || "—",
        ]),
        indicator: "green",
      },
      7
    );
  } catch (e) {
    frappe.show_alert({ message: __("Routing failed"), indicator: "red" }, 7);
  } finally {
    frappe.dom.unfreeze();
  }
}

async function run_regenerate_carbon(frm) {
  if (!frm.doc.name) return;
  const dist = frm.doc.route_distance_km ?? frm.doc.distance_km;
  if (!isFiniteNum(toNumber(dist))) {
    frappe.msgprint({ title: __("Carbon"), message: __("No distance on this leg. Please compute routing first."), indicator: "orange" });
    return;
  }
  frappe.dom.freeze(__("Computing CO₂e…"));
  try {
    const r = await frappe.call({
      method: "logistics.transport.doctype.transport_leg.transport_leg.regenerate_carbon",
      args: { leg_name: frm.doc.name },
    });
    await frm.reload_doc();
    const m = (r && r.message) || {};
    const lines = [
      `${__("CO₂e")}: ${fmt_num(m.co2e_kg, 3)} kg`,
      `${__("Method")}: ${m.method || "—"} ${m.scope ? `(${m.scope})` : ""}`,
      `${__("Provider")}: ${m.provider || "—"}`,
      `${__("Factor")}: ${fmt_num(m.factor, 3)} ${m.scope === "PER_TON_KM" ? "g/ton-km" : "g/km"}`,
    ];
    frappe.show_alert({ message: lines.join(" · "), indicator: "green" }, 8);
  } catch (e) {
    frappe.show_alert({ message: __("Carbon compute failed"), indicator: "red" }, 7);
  } finally {
    frappe.dom.unfreeze();
  }
}

// ---------- OpenStreetMap Integration ----------
// Uses Leaflet.js for interactive maps - no API key required
// Automatically loads when both pick and drop addresses are set
async function render_route_map(frm) {
  const $wrapper = frm.get_field('route_map').$wrapper;
  if (!$wrapper) return;
  
  const pick = frm.doc.pick_address;
  const drop = frm.doc.drop_address;
  
  if (!pick || !drop) {
    $wrapper.html('<div class="text-muted">Set Pick and Drop addresses to view route map</div>');
    return;
  }

  try {
    // Get coordinates for both addresses
    const [pickCoords, dropCoords] = await Promise.all([
      getAddressLatLon(pick),
      getAddressLatLon(drop)
    ]);

    if (!pickCoords || !dropCoords) {
      $wrapper.html('<div class="text-muted">Coordinates not available for addresses</div>');
      return;
    }

    const distance = frm.doc.route_distance_km ?? frm.doc.distance_km;
    const duration = frm.doc.route_duration_min ?? frm.doc.duration_min;
    
    // Create unique map container ID
    const mapId = `route-map-${frm.doc.name || 'new'}-${Date.now()}`;
    
    // Get map renderer setting and API key
    let mapRenderer = 'openstreetmap'; // default
    let apiKey = null;
    try {
      const settings = await frappe.call({
        method: 'frappe.client.get_value',
        args: {
          doctype: 'Transport Settings',
          fieldname: 'map_renderer'
        }
      });
      mapRenderer = settings.message?.map_renderer || 'openstreetmap';
      
      // Get Google Maps API key if needed
      if (mapRenderer && mapRenderer.toLowerCase() === 'google maps') {
        try {
          const apiResponse = await frappe.call({
            method: 'logistics.transport.api_vehicle_tracking.get_google_maps_api_key'
          });
          apiKey = apiResponse.message?.api_key || null;
        } catch (e) {
          console.warn('Error fetching Google Maps API key:', e);
        }
      }
    } catch (e) {
      // Use default
    }

    const mapHtml = `
      <div class="text-muted small" style="margin-bottom: 10px; display: flex; gap: 20px; align-items: center; justify-content: center;">
        <a href="https://www.google.com/maps/dir/?api=1&origin=${pickCoords.lat},${pickCoords.lon}&destination=${dropCoords.lat},${dropCoords.lon}" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
          <i class="fa fa-external-link"></i> Google Maps
        </a>
        <a href="https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${pickCoords.lat}%2C${pickCoords.lon}%3B${dropCoords.lat}%2C${dropCoords.lon}" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
          <i class="fa fa-external-link"></i> OpenStreetMap
        </a>
        <a href="https://maps.apple.com/?saddr=${pickCoords.lat},${pickCoords.lon}&daddr=${dropCoords.lat},${dropCoords.lon}" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
          <i class="fa fa-external-link"></i> Apple Maps
        </a>
      </div>
      <div style="width: 100%; height: 400px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative;">
        <div id="${mapId}" style="width: 100%; height: 100%;"></div>
        <div style="position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.9); padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; z-index: 1000;">
          <span style="color: red;">●</span> A <span style="margin-left: 10px; color: green;">●</span> B
        </div>
        <div id="${mapId}-fallback" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); display: flex; align-items: center; justify-content: center; flex-direction: column;">
          <div style="text-align: center; color: #6c757d;">
            <i class="fa fa-map" style="font-size: 32px; margin-bottom: 15px;"></i>
            <div style="font-size: 18px; font-weight: 500; margin-bottom: 10px;">Map Loading...</div>
            <div style="font-size: 14px; margin-bottom: 15px; line-height: 1.4;">
              <strong>From:</strong> ${pickCoords.lat.toFixed(4)}, ${pickCoords.lon.toFixed(4)}<br>
              <strong>To:</strong> ${dropCoords.lat.toFixed(4)}, ${dropCoords.lon.toFixed(4)}
            </div>
            <div style="font-size: 12px; color: #6c757d;">
              <i class="fa fa-info-circle"></i> Use the links above to view the route
            </div>
          </div>
        </div>
      </div>
      ${distance || duration ? `
        <div style="margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 4px; font-size: 12px;">
          ${distance ? `<div><i class="fa fa-road"></i> <strong>Distance:</strong> ${distance.toFixed(1)} km</div>` : ''}
          ${duration ? `<div><i class="fa fa-clock-o"></i> <strong>Duration:</strong> ${duration.toFixed(0)} min</div>` : ''}
        </div>
      ` : ''}
    `;
    
    $wrapper.html(mapHtml);
    
    // Show fallback initially
    showMapFallback(mapId, pickCoords, dropCoords);
    
    // Initialize map based on setting with timeout
    setTimeout(() => {
      if (mapRenderer && mapRenderer.toLowerCase() === 'google maps' && apiKey && apiKey.length > 10) {
        initializeGoogleMap(mapId, pickCoords, dropCoords, apiKey, frm);
      } else if (mapRenderer && mapRenderer.toLowerCase() === 'mapbox') {
        initializeMapboxMap(mapId, pickCoords, dropCoords);
      } else if (mapRenderer && mapRenderer.toLowerCase() === 'maplibre') {
        initializeMapLibreMap(mapId, pickCoords, dropCoords);
      } else {
        initializeOpenStreetMap(mapId, pickCoords, dropCoords);
      }
    }, 100);
    
  } catch (error) {
    console.error('Error rendering route map:', error);
    $wrapper.html('<div class="text-muted">Unable to load map</div>');
  }
}

// Show map fallback display
function showMapFallback(mapId, pickCoords, dropCoords) {
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

// Initialize Google Maps with actual road routing (interactive)
function initializeGoogleMap(mapId, pickCoords, dropCoords, apiKey, frm) {
  // First, get the actual route polyline from Google Directions API
  const waypoints = `${pickCoords.lat},${pickCoords.lon}|${dropCoords.lat},${dropCoords.lon}`;
  
  frappe.call({
    method: 'logistics.transport.api_vehicle_tracking.get_google_route_polyline',
    args: {
      waypoints: waypoints
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
        if (!window.transportLegRoutes) window.transportLegRoutes = {};
        window.transportLegRoutes[mapId] = routes;
        
        // Load Google Maps JavaScript API if not already loaded
        if (window.google && window.google.maps) {
          initializeInteractiveLegMap(mapId, routes, routeIndex, pickCoords, dropCoords, frm, apiKey);
        } else {
          // Load Google Maps JavaScript API
          const script = document.createElement('script');
          script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=geometry`;
          script.async = true;
          script.defer = true;
          script.onload = () => {
            initializeInteractiveLegMap(mapId, routes, routeIndex, pickCoords, dropCoords, frm, apiKey);
          };
          script.onerror = () => {
            console.warn('Failed to load Google Maps JavaScript API, showing fallback');
            showMapFallback(mapId, pickCoords, dropCoords);
          };
          document.head.appendChild(script);
        }
      } else {
        console.warn('No routes available');
        showMapFallback(mapId, pickCoords, dropCoords);
      }
    } else {
      console.warn('Google Directions API failed:', polylineResponse.message?.error);
      showMapFallback(mapId, pickCoords, dropCoords);
    }
  }).catch(() => {
    console.warn('Error getting route polyline');
    showMapFallback(mapId, pickCoords, dropCoords);
  });
}

// Initialize interactive Google Maps for Transport Leg
function initializeInteractiveLegMap(mapId, routes, selectedRouteIndex, pickCoords, dropCoords, frm, apiKey) {
  const mapElement = document.getElementById(mapId);
  if (!mapElement) return;
  
  // Clear any existing content
  mapElement.innerHTML = '';
  
  // Create route selector UI - always show if multiple routes
  let routeSelectorHtml = '';
  console.log(`Initializing Transport Leg map with ${routes.length} routes, selected index: ${selectedRouteIndex}`);
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
            onclick="window.selectLegRouteByIndex('${mapId}', ${route.index}, '${(frm && frm.doc && frm.doc.name) ? frm.doc.name : ''}')"
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
    center: { lat: (pickCoords.lat + dropCoords.lat) / 2, lng: (pickCoords.lon + dropCoords.lon) / 2 },
    mapTypeControl: true,
    streetViewControl: true,
    fullscreenControl: true,
    zoomControl: true,
    scaleControl: true,
    rotateControl: true
  });
  
  // Store map instance globally for route updates
  if (!window.transportLegMaps) window.transportLegMaps = {};
  window.transportLegMaps[mapId] = map;
  
  // Store polylines for route updates
  if (!window.transportLegPolylines) window.transportLegPolylines = {};
  window.transportLegPolylines[mapId] = [];
  
  // Add markers
  const startMarker = new google.maps.Marker({
    position: { lat: pickCoords.lat, lng: pickCoords.lon },
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
    title: 'Pick Location'
  });
  bounds.extend({ lat: pickCoords.lat, lng: pickCoords.lon });
  
  const endMarker = new google.maps.Marker({
    position: { lat: dropCoords.lat, lng: dropCoords.lon },
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
    title: 'Drop Location'
  });
  bounds.extend({ lat: dropCoords.lat, lng: dropCoords.lon });
  
  // Add all route polylines
  const selectedRoute = routes[selectedRouteIndex];
  const routeIndex = selectedRoute.index;
  
  console.log(`Adding ${routes.length} routes to Transport Leg map`);
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
            window.selectLegRouteByIndex(mapId, route.index, frm.doc.name);
          }
        });
      }
      
      window.transportLegPolylines[mapId].push({
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

// Initialize Mapbox
function initializeMapboxMap(mapId, pickCoords, dropCoords) {
  // Load Mapbox GL JS if not already loaded
  if (!window.mapboxgl) {
    // Load Mapbox CSS
    const mapboxCSS = document.createElement('link');
    mapboxCSS.rel = 'stylesheet';
    mapboxCSS.href = 'https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css';
    document.head.appendChild(mapboxCSS);
    
    // Load Mapbox JS
    const mapboxJS = document.createElement('script');
    mapboxJS.src = 'https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js';
    mapboxJS.onload = () => {
      createMapboxMap(mapId, pickCoords, dropCoords);
    };
    document.head.appendChild(mapboxJS);
  } else {
    createMapboxMap(mapId, pickCoords, dropCoords);
  }
}

// Initialize MapLibre
function initializeMapLibreMap(mapId, pickCoords, dropCoords) {
  // Load MapLibre GL JS if not already loaded
  if (!window.maplibregl) {
    // Load MapLibre CSS
    const maplibreCSS = document.createElement('link');
    maplibreCSS.rel = 'stylesheet';
    maplibreCSS.href = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css';
    document.head.appendChild(maplibreCSS);
    
    // Load MapLibre JS
    const maplibreJS = document.createElement('script');
    maplibreJS.src = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js';
    maplibreJS.onload = () => {
      createMapLibreMap(mapId, pickCoords, dropCoords);
    };
    document.head.appendChild(maplibreJS);
  } else {
    createMapLibreMap(mapId, pickCoords, dropCoords);
  }
}

// Initialize OpenStreetMap with Leaflet
function initializeOpenStreetMap(mapId, pickCoords, dropCoords) {
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
      createMap(mapId, pickCoords, dropCoords);
    };
    document.head.appendChild(leafletJS);
  } else {
    createMap(mapId, pickCoords, dropCoords);
  }
}

function createMap(mapId, pickCoords, dropCoords) {
  // Wait for DOM element to be available
  const checkElement = () => {
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      try {
        // Create map centered between the two points
        const centerLat = (pickCoords.lat + dropCoords.lat) / 2;
        const centerLon = (pickCoords.lon + dropCoords.lon) / 2;
        
        const map = L.map(mapId).setView([centerLat, centerLon], 13);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          maxZoom: 19
        }).addTo(map);
        
        // Add pickup marker (red)
        const pickupMarker = L.marker([pickCoords.lat, pickCoords.lon], {
          icon: L.divIcon({
            className: 'custom-div-icon',
            html: '<div style="background-color: red; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
          })
        }).addTo(map);
        
        // Add drop marker (green)
        const dropMarker = L.marker([dropCoords.lat, dropCoords.lon], {
          icon: L.divIcon({
            className: 'custom-div-icon',
            html: '<div style="background-color: green; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
          })
        }).addTo(map);
        
        // Add popups
        pickupMarker.bindPopup('<strong>Pickup Location</strong><br>Coordinates: ' + pickCoords.lat.toFixed(4) + ', ' + pickCoords.lon.toFixed(4));
        dropMarker.bindPopup('<strong>Drop Location</strong><br>Coordinates: ' + dropCoords.lat.toFixed(4) + ', ' + dropCoords.lon.toFixed(4));
        
        // Add route line
        const routeLine = L.polyline([
          [pickCoords.lat, pickCoords.lon],
          [dropCoords.lat, dropCoords.lon]
        ], {
          color: 'blue',
          weight: 4,
          opacity: 0.7,
          dashArray: '10, 10'
        }).addTo(map);
        
        // Fit map to show both markers
        const group = new L.featureGroup([pickupMarker, dropMarker]);
        map.fitBounds(group.getBounds().pad(0.1));
        
        // Hide fallback when map loads successfully
        hideMapFallback(mapId);
        
      } catch (error) {
        console.error('Error creating OpenStreetMap:', error);
        // Keep fallback visible on error
      }
    } else {
      // Retry after a short delay
      setTimeout(checkElement, 100);
    }
  };
  
  checkElement();
}

// Create Mapbox map
function createMapboxMap(mapId, pickCoords, dropCoords) {
  const checkElement = () => {
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      try {
        // Create map centered between the two points
        const centerLat = (pickCoords.lat + dropCoords.lat) / 2;
        const centerLon = (pickCoords.lon + dropCoords.lon) / 2;
        
        const map = new mapboxgl.Map({
          container: mapId,
          style: 'https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/{z}/{x}/{y}?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw',
          center: [centerLon, centerLat],
          zoom: 13
        });
        
        // Add pickup marker
        const pickupMarker = new mapboxgl.Marker({ color: 'red' })
          .setLngLat([pickCoords.lon, pickCoords.lat])
          .setPopup(new mapboxgl.Popup().setHTML('<strong>Pickup Location</strong><br>Coordinates: ' + pickCoords.lat.toFixed(4) + ', ' + pickCoords.lon.toFixed(4)))
          .addTo(map);
        
        // Add drop marker
        const dropMarker = new mapboxgl.Marker({ color: 'green' })
          .setLngLat([dropCoords.lon, dropCoords.lat])
          .setPopup(new mapboxgl.Popup().setHTML('<strong>Drop Location</strong><br>Coordinates: ' + dropCoords.lat.toFixed(4) + ', ' + dropCoords.lon.toFixed(4)))
          .addTo(map);
        
        // Add route line
        map.on('load', () => {
          map.addSource('route', {
            type: 'geojson',
            data: {
              type: 'Feature',
              properties: {},
              geometry: {
                type: 'LineString',
                coordinates: [
                  [pickCoords.lon, pickCoords.lat],
                  [dropCoords.lon, dropCoords.lat]
                ]
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
              'line-color': 'blue',
              'line-width': 4,
              'line-dasharray': [2, 2]
            }
          });
        });
        
        // Fit map to show both markers
        const bounds = new mapboxgl.LngLatBounds();
        bounds.extend([pickCoords.lon, pickCoords.lat]);
        bounds.extend([dropCoords.lon, dropCoords.lat]);
        map.fitBounds(bounds, { padding: 50 });
        
        // Hide fallback when map loads successfully
        hideMapFallback(mapId);
        
      } catch (error) {
        console.error('Error creating Mapbox map:', error);
        // Keep fallback visible on error
      }
    } else {
      setTimeout(checkElement, 100);
    }
  };
  
  checkElement();
}

// Create MapLibre map
function createMapLibreMap(mapId, pickCoords, dropCoords) {
  const checkElement = () => {
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      try {
        // Create map centered between the two points
        const centerLat = (pickCoords.lat + dropCoords.lat) / 2;
        const centerLon = (pickCoords.lon + dropCoords.lon) / 2;
        
        const map = new maplibregl.Map({
          container: mapId,
          style: {
            version: 8,
            sources: {
              'osm': {
                type: 'raster',
                tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
                tileSize: 256,
                attribution: '&copy; OpenStreetMap contributors'
              }
            },
            layers: [
              {
                id: 'osm',
                type: 'raster',
                source: 'osm'
              }
            ]
          },
          center: [centerLon, centerLat],
          zoom: 13
        });
        
        // Add pickup marker
        const pickupMarker = new maplibregl.Marker({ color: 'red' })
          .setLngLat([pickCoords.lon, pickCoords.lat])
          .setPopup(new maplibregl.Popup().setHTML('<strong>Pickup Location</strong><br>Coordinates: ' + pickCoords.lat.toFixed(4) + ', ' + pickCoords.lon.toFixed(4)))
          .addTo(map);
        
        // Add drop marker
        const dropMarker = new maplibregl.Marker({ color: 'green' })
          .setLngLat([dropCoords.lon, dropCoords.lat])
          .setPopup(new maplibregl.Popup().setHTML('<strong>Drop Location</strong><br>Coordinates: ' + dropCoords.lat.toFixed(4) + ', ' + dropCoords.lon.toFixed(4)))
          .addTo(map);
        
        // Add route line
        map.on('load', () => {
          map.addSource('route', {
            type: 'geojson',
            data: {
              type: 'Feature',
              properties: {},
              geometry: {
                type: 'LineString',
                coordinates: [
                  [pickCoords.lon, pickCoords.lat],
                  [dropCoords.lon, dropCoords.lat]
                ]
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
              'line-color': 'blue',
              'line-width': 4,
              'line-dasharray': [2, 2]
            }
          });
        });
        
        // Fit map to show both markers
        const bounds = new maplibregl.LngLatBounds();
        bounds.extend([pickCoords.lon, pickCoords.lat]);
        bounds.extend([dropCoords.lon, dropCoords.lat]);
        map.fitBounds(bounds, { padding: 50 });
        
        // Hide fallback when map loads successfully
        hideMapFallback(mapId);
        
      } catch (error) {
        console.error('Error creating MapLibre map:', error);
        // Keep fallback visible on error
      }
    } else {
      setTimeout(checkElement, 100);
    }
  };
  
  checkElement();
}

// ---------- form bindings ----------
frappe.ui.form.on('Transport Leg', {
  setup(frm) {
    set_pick_query(frm);
    set_drop_query(frm);
  },

  refresh(frm) {
    frm._tl_buttons_added = false;

    set_pick_query(frm);
    set_drop_query(frm);
    render_pick_address(frm);
    render_drop_address(frm);
    render_route_map(frm);

    addActionButtons(frm);

    const dist = frm.doc.route_distance_km ?? frm.doc.distance_km;
    const dur  = frm.doc.route_duration_min ?? frm.doc.duration_min;
    if (dist || dur) {
      frm.dashboard.clear_headline();
      const chips = [];
      if (isFiniteNum(toNumber(dist))) chips.push(`<span class="indicator blue">${fmt_num(dist, 3)} km</span>`);
      if (isFiniteNum(toNumber(dur)))  chips.push(`<span class="indicator green">${fmt_num(dur, 1)} min</span>`);
      if (chips.length) frm.dashboard.set_headline(chips.join("&nbsp;"));
    }
  },

  pick_address(frm)  { 
    render_pick_address(frm); 
    render_route_map(frm);
  },
  drop_address(frm)  { 
    render_drop_address(frm); 
    render_route_map(frm);
  },

  facility_type_from(frm) { 
    set_pick_query(frm); 
    if (frm.doc.pick_address) frm.set_value('pick_address', null); 
    auto_fill_pick_address(frm);
  },
  facility_from(frm) { 
    set_pick_query(frm); 
    if (frm.doc.pick_address) frm.set_value('pick_address', null); 
    auto_fill_pick_address(frm);
  },
  facility_type_to(frm) { 
    set_drop_query(frm); 
    if (frm.doc.drop_address) frm.set_value('drop_address', null); 
    auto_fill_drop_address(frm);
  },
  facility_to(frm) { 
    set_drop_query(frm); 
    if (frm.doc.drop_address) frm.set_value('drop_address', null); 
    auto_fill_drop_address(frm);
  },
});

// Select a route for Transport Leg and save it (global function for onclick handler)
window.selectLegRouteByIndex = function(mapId, routeIndex, transportLegName) {
  if (!transportLegName) {
    frappe.show_alert({
      message: __('Please save the Transport Leg first before selecting a route'),
      indicator: 'orange'
    });
    return;
  }
  
  // Get the route from stored routes
  const routes = window.transportLegRoutes && window.transportLegRoutes[mapId];
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
  const map = window.transportLegMaps && window.transportLegMaps[mapId];
  const polylines = window.transportLegPolylines && window.transportLegPolylines[mapId];
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
  
  // Save the selected route to Transport Leg (will sync to Run Sheet automatically)
  frappe.call({
    method: 'logistics.transport.api_vehicle_tracking.save_selected_route',
    args: {
      transport_leg_name: transportLegName,
      route_index: routeIndex,
      polyline: selectedRoute.polyline,
      distance_km: selectedRoute.distance_km,
      duration_min: selectedRoute.duration_min,
      route_type: 'transport_leg'
    }
  }).then(response => {
    if (response.message && response.message.success) {
      frappe.show_alert({
        message: __('Route ${0} selected and saved. Run Sheet route cleared for recalculation.', [routeIndex + 1]),
        indicator: 'green'
      });
      
      // Reload the form to refresh the map with saved route
      if (cur_frm && cur_frm.doc.name === transportLegName) {
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
