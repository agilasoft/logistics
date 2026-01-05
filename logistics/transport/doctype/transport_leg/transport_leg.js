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

// ---------- Route Map (Uses Map Renderer from Transport Settings) ----------
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
    // Get map renderer setting (same as Run Sheet)
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
    const mapId = `transport-leg-map-${frm.doc.name || 'new'}-${Date.now()}`;
    
    // Create HTML with map container (same structure as Run Sheet)
    const mapHtml = `
      <div class="text-muted small" style="margin-bottom: 10px; display: flex; gap: 20px; align-items: center; justify-content: center; flex-wrap: wrap;">
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
      <div id="${mapId}" style="width: 100%; height: 500px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"></div>
    `;
    
    $wrapper.html(mapHtml);
    
    // Initialize map based on renderer (same as Run Sheet)
    // Use the map initialization functions from run_sheet.js
    const legCoords = [{
      pick: pickCoords,
      drop: dropCoords,
      order: 1
    }];
    
    setTimeout(() => {
      // Initialize map based on renderer
      if (mapRenderer && mapRenderer.toLowerCase() === 'google maps') {
        initializeTransportLegGoogleMap(mapId, legCoords, frm);
      } else if (mapRenderer && mapRenderer.toLowerCase() === 'mapbox') {
        initializeTransportLegMapboxMap(mapId, legCoords, frm);
      } else if (mapRenderer && mapRenderer.toLowerCase() === 'maplibre') {
        initializeTransportLegMapLibreMap(mapId, legCoords, frm);
      } else {
        initializeTransportLegOpenStreetMap(mapId, legCoords, frm);
      }
    }, 100);
    
  } catch (error) {
    console.error('Error rendering route map:', error);
    if ($wrapper) {
      $wrapper.html('<div class="text-muted">Unable to load map</div>');
    }
  }
}

// ---------- Single-leg Map Initialization Functions ----------

// Initialize OpenStreetMap for single leg
function initializeTransportLegOpenStreetMap(mapId, legCoords, frm) {
  if (!window.L) {
    const leafletCSS = document.createElement('link');
    leafletCSS.rel = 'stylesheet';
    leafletCSS.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    leafletCSS.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
    leafletCSS.crossOrigin = 'anonymous';
    document.head.appendChild(leafletCSS);
    
    const leafletJS = document.createElement('script');
    leafletJS.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    leafletJS.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
    leafletJS.crossOrigin = 'anonymous';
    leafletJS.onload = () => createTransportLegOpenStreetMap(mapId, legCoords);
    document.head.appendChild(leafletJS);
  } else {
    createTransportLegOpenStreetMap(mapId, legCoords);
  }
}

function createTransportLegOpenStreetMap(mapId, legCoords) {
  const mapElement = document.getElementById(mapId);
  if (!mapElement) return;
  
  const leg = legCoords[0];
  const centerLat = (leg.pick.lat + leg.drop.lat) / 2;
  const centerLon = (leg.pick.lon + leg.drop.lon) / 2;
  
  const map = L.map(mapId).setView([centerLat, centerLon], 10);
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(map);
  
  // Add pick marker
  L.marker([leg.pick.lat, leg.pick.lon], {
    icon: L.divIcon({
      className: 'custom-div-icon',
      html: '<div style="background-color: red; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    })
  }).addTo(map).bindPopup(`<strong>Pickup</strong><br>Coordinates: ${leg.pick.lat.toFixed(4)}, ${leg.pick.lon.toFixed(4)}`);
  
  // Add drop marker
  L.marker([leg.drop.lat, leg.drop.lon], {
    icon: L.divIcon({
      className: 'custom-div-icon',
      html: '<div style="background-color: green; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    })
  }).addTo(map).bindPopup(`<strong>Drop</strong><br>Coordinates: ${leg.drop.lat.toFixed(4)}, ${leg.drop.lon.toFixed(4)}`);
  
  // Add route line
  L.polyline([
    [leg.pick.lat, leg.pick.lon],
    [leg.drop.lat, leg.drop.lon]
  ], {
    color: 'blue',
    weight: 3,
    opacity: 0.6
  }).addTo(map);
  
  map.fitBounds([
    [leg.pick.lat, leg.pick.lon],
    [leg.drop.lat, leg.drop.lon]
  ], { padding: [50, 50] });
}

// Initialize Google Maps for single leg
function initializeTransportLegGoogleMap(mapId, legCoords, frm) {
  const leg = legCoords[0];
  const mapElement = document.getElementById(mapId);
  if (!mapElement) return;
  
  frappe.call({
    method: 'logistics.transport.api_vehicle_tracking.get_google_maps_api_key'
  }).then(response => {
    const apiKey = response.message?.api_key;
    if (apiKey && apiKey.length > 10) {
      // Load Google Maps JS API first
      if (window.google && window.google.maps) {
        loadGoogleRouteAndMap(mapId, leg, apiKey);
      } else {
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=geometry`;
        script.async = true;
        script.defer = true;
        script.onload = () => loadGoogleRouteAndMap(mapId, leg, apiKey);
        script.onerror = () => {
          mapElement.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">Failed to load Google Maps API</div>';
        };
        document.head.appendChild(script);
      }
    } else {
      mapElement.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">Google Maps API key not configured</div>';
    }
  }).catch((error) => {
    console.error('Error getting Google Maps API key:', error);
    mapElement.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">Error loading Google Maps</div>';
  });
}

function loadGoogleRouteAndMap(mapId, leg, apiKey) {
  const waypointStr = `${leg.pick.lat},${leg.pick.lon}|${leg.drop.lat},${leg.drop.lon}`;
  
  frappe.call({
    method: 'logistics.transport.api_vehicle_tracking.get_google_route_polyline',
    args: { waypoints: waypointStr }
  }).then(polylineResponse => {
    const mapElement = document.getElementById(mapId);
    if (!mapElement) return;
    
    if (polylineResponse.message && polylineResponse.message.success && polylineResponse.message.routes && polylineResponse.message.routes.length > 0) {
      const route = polylineResponse.message.routes[0];
      createTransportLegGoogleMap(mapId, route, leg, apiKey);
    } else {
      // Fallback: create map without route polyline (just markers and straight line)
      console.warn('Route polyline not available, showing fallback map');
      createTransportLegGoogleMapFallback(mapId, leg, apiKey);
    }
  }).catch((error) => {
    console.error('Error getting route polyline:', error);
    const mapElement = document.getElementById(mapId);
    if (mapElement) {
      // Fallback: create map without route polyline
      createTransportLegGoogleMapFallback(mapId, leg, apiKey);
    }
  });
}

function createTransportLegGoogleMap(mapId, route, leg, apiKey) {
  const mapElement = document.getElementById(mapId);
  if (!mapElement || !window.google || !window.google.maps) return;
  
  const map = new google.maps.Map(mapElement, {
    zoom: 10,
    center: { lat: (leg.pick.lat + leg.drop.lat) / 2, lng: (leg.pick.lon + leg.drop.lon) / 2 }
  });
  
  // Add route polyline if available
  if (route && route.polyline) {
    try {
      const decodedPath = google.maps.geometry.encoding.decodePath(route.polyline);
      const routePath = new google.maps.Polyline({
        path: decodedPath,
        geodesic: true,
        strokeColor: '#4285F4',
        strokeOpacity: 0.8,
        strokeWeight: 4
      });
      routePath.setMap(map);
    } catch (e) {
      console.warn('Error decoding polyline, using straight line:', e);
      // Fallback to straight line
      const straightLine = new google.maps.Polyline({
        path: [
          { lat: leg.pick.lat, lng: leg.pick.lon },
          { lat: leg.drop.lat, lng: leg.drop.lon }
        ],
        geodesic: true,
        strokeColor: '#4285F4',
        strokeOpacity: 0.8,
        strokeWeight: 4
      });
      straightLine.setMap(map);
    }
  } else {
    // No polyline, use straight line
    const straightLine = new google.maps.Polyline({
      path: [
        { lat: leg.pick.lat, lng: leg.pick.lon },
        { lat: leg.drop.lat, lng: leg.drop.lon }
      ],
      geodesic: true,
      strokeColor: '#4285F4',
      strokeOpacity: 0.8,
      strokeWeight: 4
    });
    straightLine.setMap(map);
  }
  
  // Add pick marker
  new google.maps.Marker({
    position: { lat: leg.pick.lat, lng: leg.pick.lon },
    map: map,
    label: { text: 'P', color: 'white' },
    icon: { path: google.maps.SymbolPath.CIRCLE, scale: 10, fillColor: 'red', fillOpacity: 1, strokeColor: 'white', strokeWeight: 2 }
  });
  
  // Add drop marker
  new google.maps.Marker({
    position: { lat: leg.drop.lat, lng: leg.drop.lon },
    map: map,
    label: { text: 'D', color: 'white' },
    icon: { path: google.maps.SymbolPath.CIRCLE, scale: 10, fillColor: 'green', fillOpacity: 1, strokeColor: 'white', strokeWeight: 2 }
  });
  
  const bounds = new google.maps.LatLngBounds();
  bounds.extend({ lat: leg.pick.lat, lng: leg.pick.lon });
  bounds.extend({ lat: leg.drop.lat, lng: leg.drop.lon });
  map.fitBounds(bounds);
}

function createTransportLegGoogleMapFallback(mapId, leg, apiKey) {
  const mapElement = document.getElementById(mapId);
  if (!mapElement || !window.google || !window.google.maps) return;
  
  const map = new google.maps.Map(mapElement, {
    zoom: 10,
    center: { lat: (leg.pick.lat + leg.drop.lat) / 2, lng: (leg.pick.lon + leg.drop.lon) / 2 }
  });
  
  // Use DirectionsService to get route
  const directionsService = new google.maps.DirectionsService();
  const directionsRenderer = new google.maps.DirectionsRenderer();
  directionsRenderer.setMap(map);
  
  directionsService.route({
    origin: { lat: leg.pick.lat, lng: leg.pick.lon },
    destination: { lat: leg.drop.lat, lng: leg.drop.lon },
    travelMode: google.maps.TravelMode.DRIVING
  }, (result, status) => {
    if (status === 'OK') {
      directionsRenderer.setDirections(result);
    } else {
      // Final fallback: just show markers and straight line
      const straightLine = new google.maps.Polyline({
        path: [
          { lat: leg.pick.lat, lng: leg.pick.lon },
          { lat: leg.drop.lat, lng: leg.drop.lon }
        ],
        geodesic: true,
        strokeColor: '#4285F4',
        strokeOpacity: 0.8,
        strokeWeight: 4
      });
      straightLine.setMap(map);
      
      new google.maps.Marker({
        position: { lat: leg.pick.lat, lng: leg.pick.lon },
        map: map,
        label: { text: 'P', color: 'white' },
        icon: { path: google.maps.SymbolPath.CIRCLE, scale: 10, fillColor: 'red', fillOpacity: 1, strokeColor: 'white', strokeWeight: 2 }
      });
      
      new google.maps.Marker({
        position: { lat: leg.drop.lat, lng: leg.drop.lon },
        map: map,
        label: { text: 'D', color: 'white' },
        icon: { path: google.maps.SymbolPath.CIRCLE, scale: 10, fillColor: 'green', fillOpacity: 1, strokeColor: 'white', strokeWeight: 2 }
      });
      
      const bounds = new google.maps.LatLngBounds();
      bounds.extend({ lat: leg.pick.lat, lng: leg.pick.lon });
      bounds.extend({ lat: leg.drop.lat, lng: leg.drop.lon });
      map.fitBounds(bounds);
    }
  });
}

// Initialize Mapbox for single leg (placeholder - can be implemented similarly)
function initializeTransportLegMapboxMap(mapId, legCoords, frm) {
  const mapElement = document.getElementById(mapId);
  if (mapElement) {
    mapElement.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">Mapbox map initialization not yet implemented for single legs</div>';
  }
}

// Initialize MapLibre for single leg (placeholder - can be implemented similarly)
function initializeTransportLegMapLibreMap(mapId, legCoords, frm) {
  const mapElement = document.getElementById(mapId);
  if (mapElement) {
    mapElement.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">MapLibre map initialization not yet implemented for single legs</div>';
  }
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
    
    // Try to render map - with delay in case field isn't ready yet
    render_route_map(frm);
    setTimeout(() => render_route_map(frm), 500);

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
