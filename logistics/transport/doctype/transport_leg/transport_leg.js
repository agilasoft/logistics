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
        initializeGoogleMap(mapId, pickCoords, dropCoords, apiKey);
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

// Initialize Google Maps
function initializeGoogleMap(mapId, pickCoords, dropCoords, apiKey) {
  const staticMapUrl = `https://maps.googleapis.com/maps/api/staticmap?key=${apiKey}&size=600x400&maptype=roadmap&markers=color:red|label:A|${pickCoords.lat},${pickCoords.lon}&markers=color:green|label:B|${dropCoords.lat},${dropCoords.lon}&path=color:0x0000ff|weight:5|${pickCoords.lat},${pickCoords.lon}|${dropCoords.lat},${dropCoords.lon}`;
  
  const mapElement = document.getElementById(mapId);
  if (mapElement) {
    // Create a test image to check if the API key works
    const testImg = new Image();
    testImg.onload = function() {
      // API key works, hide fallback and show the map
      hideMapFallback(mapId);
      mapElement.innerHTML = `
        <img 
          src="${staticMapUrl}" 
          alt="Route Map" 
          style="width: 100%; height: 100%; object-fit: cover;"
        />
      `;
    };
    testImg.onerror = function() {
      // API key doesn't work, keep fallback visible
      console.warn('Google Maps Static API failed, showing fallback');
    };
    testImg.src = staticMapUrl;
  }
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

  facility_type_from(frm) { set_pick_query(frm); if (frm.doc.pick_address) frm.set_value('pick_address', null); },
  facility_from(frm)      { set_pick_query(frm); if (frm.doc.pick_address) frm.set_value('pick_address', null); },
  facility_type_to(frm)   { set_drop_query(frm); if (frm.doc.drop_address) frm.set_value('drop_address', null); },
  facility_to(frm)        { set_drop_query(frm); if (frm.doc.drop_address) frm.set_value('drop_address', null); },
});
