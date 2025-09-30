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

// ---------- External map shortcuts only ----------
async function addExternalMapButtons(frm) {
  if (frm._tl_buttons_added) return;
  frm._tl_buttons_added = true;

  const group = __("Action");

  frm.page.add_action_item(__("Regenerate Routing"), () => run_regenerate_routing(frm));
  frm.add_custom_button(__("Regenerate Routing"), () => run_regenerate_routing(frm), group);

  frm.page.add_action_item(__("Regenerate Carbon (CO₂e)"), () => run_regenerate_carbon(frm));
  frm.add_custom_button(__("Regenerate Carbon (CO₂e)"), () => run_regenerate_carbon(frm), group);

  try {
    const [pick, drop] = await Promise.all([
      getAddressLatLon(frm.doc.pick_address),
      getAddressLatLon(frm.doc.drop_address),
    ]);

    if (pick && drop) {
      frm.add_custom_button(__("Open in Google Maps"), () => {
        const url = `https://www.google.com/maps/dir/?api=1&origin=${pick.lat},${pick.lon}&destination=${drop.lat},${drop.lon}`;
        window.open(url, "_blank");
      }, group);

      frm.add_custom_button(__("Open in OpenStreetMap"), () => {
        const url = `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${pick.lat}%2C${pick.lon}%3B${drop.lat}%2C${drop.lon}`;
        window.open(url, "_blank");
      }, group);

      frm.add_custom_button(__("Open in Apple Maps"), () => {
        const url = `https://maps.apple.com/?saddr=${pick.lat},${pick.lon}&daddr=${drop.lat},${drop.lon}`;
        window.open(url, "_blank");
      }, group);
    }
  } catch (e) {
    // ignore
  }
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

// ---------- Google Map Integration ----------
// To enable embedded Google Maps:
// 1. Get a Google Maps API key from Google Cloud Console
// 2. Enable "Maps Embed API" for the key
// 3. Add the API key to Transport Settings > Routing > Google API Key
// 4. The map will automatically appear when both pick and drop addresses are set
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

    // Try to get Google Maps API key from settings
    let apiKey = '';
    try {
      const settings = await frappe.call({
        method: 'frappe.client.get_value',
        args: {
          doctype: 'Transport Settings',
          fieldname: 'routing_google_api_key'
        }
      });
      apiKey = settings.message?.routing_google_api_key || '';
    } catch (e) {
      // Settings not found or no API key configured
    }

    const origin = `${pickCoords.lat},${pickCoords.lon}`;
    const destination = `${dropCoords.lat},${dropCoords.lon}`;
    
    let mapHtml;
    
    if (apiKey) {
      // Use Google Maps Embed API with API key
      mapHtml = `
        <div style="width: 100%; height: 400px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
          <iframe 
            width="100%" 
            height="400" 
            frameborder="0" 
            style="border:0" 
            src="https://www.google.com/maps/embed/v1/directions?key=${apiKey}&origin=${origin}&destination=${destination}&mode=driving"
            allowfullscreen>
          </iframe>
        </div>
        <div class="text-muted small" style="margin-top: 8px; display: flex; gap: 15px; align-items: center;">
          <a href="https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}" target="_blank" rel="noopener" style="text-decoration: none;">
            <i class="fa fa-external-link"></i> Open in Google Maps
          </a>
          <a href="https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${pickCoords.lat}%2C${pickCoords.lon}%3B${dropCoords.lat}%2C${dropCoords.lon}" target="_blank" rel="noopener" style="text-decoration: none;">
            <i class="fa fa-external-link"></i> Open in OpenStreetMap
          </a>
        </div>
      `;
    } else {
      // Fallback to static map or external link
      mapHtml = `
        <div style="width: 100%; height: 400px; border: 1px solid #ddd; border-radius: 4px; background: #f8f9fa; display: flex; align-items: center; justify-content: center; flex-direction: column;">
          <div class="text-muted">
            <i class="fa fa-map-marker" style="font-size: 24px; margin-bottom: 10px;"></i>
            <div>Route Map</div>
            <div style="font-size: 12px; margin-top: 5px;">
              From: ${pickCoords.lat.toFixed(4)}, ${pickCoords.lon.toFixed(4)}<br>
              To: ${dropCoords.lat.toFixed(4)}, ${dropCoords.lon.toFixed(4)}
            </div>
          </div>
        </div>
        <div class="text-muted small" style="margin-top: 5px;">
          <a href="https://www.google.com/maps/dir/?api=1&origin=${origin}&destination=${destination}" target="_blank" rel="noopener">
            <i class="fa fa-external-link"></i> Open in Google Maps
          </a>
          <span style="margin: 0 10px;">|</span>
          <a href="https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${pickCoords.lat}%2C${pickCoords.lon}%3B${dropCoords.lat}%2C${dropCoords.lon}" target="_blank" rel="noopener">
            <i class="fa fa-external-link"></i> Open in OpenStreetMap
          </a>
        </div>
      `;
    }
    
    $wrapper.html(mapHtml);
  } catch (error) {
    console.error('Error rendering route map:', error);
    $wrapper.html('<div class="text-muted">Unable to load map</div>');
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
    render_route_map(frm);

    addExternalMapButtons(frm);

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
