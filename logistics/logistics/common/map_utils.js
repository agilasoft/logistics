/**
 * Common Map Rendering Utilities
 * Shared functions for map rendering across all modules
 */

// Global map utilities object
window.MapUtils = {
    
    /**
     * Initialize map based on Logistics Settings
     * @param {string} mapContainerId - ID of the map container element
     * @param {Array} originCoords - [lat, lon] for origin
     * @param {Array} destCoords - [lat, lon] for destination  
     * @param {string} originLabel - Label for origin marker
     * @param {string} destLabel - Label for destination marker
     * @param {Object} options - Additional options
     */
    async initializeMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, options = {}) {
        const defaultOptions = {
            zoom: 4,
            showRouteLine: true,
            markerColors: {
                origin: 'green',
                destination: 'red'
            },
            onMapReady: null
        };
        
        const config = { ...defaultOptions, ...options };
        
        try {
            // Get map renderer setting from Logistics Settings
            let mapRenderer = 'openstreetmap'; // default
            try {
                const settings = await frappe.call({
                    method: 'frappe.client.get_value',
                    args: {
                        doctype: 'Logistics Settings',
                        fieldname: 'map_renderer'
                    }
                });
                mapRenderer = settings.message?.map_renderer || 'openstreetmap';
                console.log('Map Renderer from Logistics Settings:', mapRenderer);
            } catch (e) {
                console.log('Error getting map renderer settings:', e);
            }
            
            // Initialize map based on renderer
            console.log('Initializing map with renderer:', mapRenderer);
            if (mapRenderer && mapRenderer.toLowerCase() === 'google maps') {
                await this.initializeGoogleMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config);
            } else if (mapRenderer && mapRenderer.toLowerCase() === 'mapbox') {
                await this.initializeMapboxMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config);
            } else if (mapRenderer && mapRenderer.toLowerCase() === 'maplibre') {
                await this.initializeMapLibreMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config);
            } else {
                await this.initializeOpenStreetMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config);
            }
            
            // Call onMapReady callback if provided
            if (config.onMapReady && typeof config.onMapReady === 'function') {
                config.onMapReady();
            }
            
        } catch (error) {
            console.error('Error initializing map:', error);
            this.showMapFallback(mapContainerId, originLabel, destLabel);
        }
    },

    /**
     * Initialize OpenStreetMap with Leaflet
     */
    async initializeOpenStreetMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config) {
        console.log('Initializing OpenStreetMap...');
        try {
            // Check if Leaflet is available
            if (typeof L === 'undefined') {
                console.error('Leaflet not loaded');
                this.showMapFallback(mapContainerId, originLabel, destLabel);
                return;
            }
            
            // Calculate center point
            const centerLat = (originCoords[0] + destCoords[0]) / 2;
            const centerLon = (originCoords[1] + destCoords[1]) / 2;
            
            // Initialize Leaflet map
            console.log('Creating Leaflet map...');
            const map = L.map(mapContainerId).setView([centerLat, centerLon], config.zoom);
            
            // Add OpenStreetMap tiles
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                maxZoom: 19
            }).addTo(map);
            
            let markers = [];
            
            // Add origin marker if origin coords exist
            if (originCoords && originCoords.length === 2) {
                const originMarker = L.marker(originCoords, {
                    icon: L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div style="background-color: ${config.markerColors.origin}; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 10px;">O</div>`,
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    })
                }).addTo(map);
                
                originMarker.bindPopup(`<strong>Origin</strong><br>${originLabel}<br>Coordinates: ${originCoords[0].toFixed(4)}, ${originCoords[1].toFixed(4)}`);
                markers.push(originMarker);
            }
            
            // Add destination marker if destination coords exist
            if (destCoords && destCoords.length === 2) {
                const destMarker = L.marker(destCoords, {
                    icon: L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div style="background-color: ${config.markerColors.destination}; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 10px;">D</div>`,
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    })
                }).addTo(map);
                
                destMarker.bindPopup(`<strong>Destination</strong><br>${destLabel}<br>Coordinates: ${destCoords[0].toFixed(4)}, ${destCoords[1].toFixed(4)}`);
                markers.push(destMarker);
            }
            
            // Add route line if both coords exist and showRouteLine is true
            if (config.showRouteLine && originCoords && destCoords && 
                originCoords.length === 2 && destCoords.length === 2) {
                const routeLine = L.polyline([originCoords, destCoords], {
                    color: 'blue',
                    weight: 3,
                    opacity: 0.6,
                    dashArray: '5, 5'
                }).addTo(map);
                markers.push(routeLine);
            }
            
            // Fit map to show markers if any exist
            if (markers.length > 0) {
                const group = new L.featureGroup(markers);
                map.fitBounds(group.getBounds().pad(0.1));
            } else {
                // If no markers, show a default view centered on the calculated center
                map.setView([centerLat, centerLon], config.zoom);
            }
            
            console.log('OpenStreetMap created successfully');
            
        } catch (error) {
            console.error('Error creating OpenStreetMap:', error);
            this.showMapFallback(mapContainerId, originLabel, destLabel);
        }
    },

    /**
     * Initialize MapLibre map
     */
    async initializeMapLibreMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config) {
        // Load MapLibre GL JS if not already loaded
        if (!window.maplibregl) {
            console.log('Loading MapLibre GL JS...');
            // Load MapLibre CSS
            const maplibreCSS = document.createElement('link');
            maplibreCSS.rel = 'stylesheet';
            maplibreCSS.href = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css';
            document.head.appendChild(maplibreCSS);
            
            // Load MapLibre JS
            const maplibreJS = document.createElement('script');
            maplibreJS.src = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js';
            maplibreJS.onload = () => {
                this.createMapLibreMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config);
            };
            document.head.appendChild(maplibreJS);
        } else {
            this.createMapLibreMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config);
        }
    },

    /**
     * Create MapLibre map
     */
    createMapLibreMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config) {
        const checkElement = () => {
            const mapElement = document.getElementById(mapContainerId);
            if (mapElement) {
                try {
                    console.log('Creating MapLibre map...');
                    
                    // Create map centered between the two points
                    const centerLat = (originCoords[0] + destCoords[0]) / 2;
                    const centerLon = (originCoords[1] + destCoords[1]) / 2;
                    
                    const map = new maplibregl.Map({
                        container: mapContainerId,
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
                        zoom: config.zoom
                    });
                    
                    // Add origin marker if coords exist
                    if (originCoords && originCoords.length === 2) {
                        const originMarker = new maplibregl.Marker({ color: config.markerColors.origin })
                            .setLngLat([originCoords[1], originCoords[0]])
                            .setPopup(new maplibregl.Popup().setHTML(`<strong>Origin</strong><br>${originLabel}<br>Coordinates: ${originCoords[0].toFixed(4)}, ${originCoords[1].toFixed(4)}`))
                            .addTo(map);
                    }
                    
                    // Add destination marker if coords exist
                    if (destCoords && destCoords.length === 2) {
                        const destMarker = new maplibregl.Marker({ color: config.markerColors.destination })
                            .setLngLat([destCoords[1], destCoords[0]])
                            .setPopup(new maplibregl.Popup().setHTML(`<strong>Destination</strong><br>${destLabel}<br>Coordinates: ${destCoords[0].toFixed(4)}, ${destCoords[1].toFixed(4)}`))
                            .addTo(map);
                    }
                    
                    // Add route line if both coords exist and showRouteLine is true
                    if (config.showRouteLine && originCoords && destCoords && 
                        originCoords.length === 2 && destCoords.length === 2) {
                        map.on('load', function() {
                            map.addSource('route', {
                                'type': 'geojson',
                                'data': {
                                    'type': 'Feature',
                                    'properties': {},
                                    'geometry': {
                                        'type': 'LineString',
                                        'coordinates': [[originCoords[1], originCoords[0]], [destCoords[1], destCoords[0]]]
                                    }
                                }
                            });
                            
                            map.addLayer({
                                'id': 'route',
                                'type': 'line',
                                'source': 'route',
                                'layout': {
                                    'line-join': 'round',
                                    'line-cap': 'round'
                                },
                                'paint': {
                                    'line-color': '#3887be',
                                    'line-width': 5,
                                    'line-opacity': 0.75
                                }
                            });
                        });
                    }
                    
                    console.log('MapLibre map created successfully');
                    
                } catch (error) {
                    console.error('Error creating MapLibre map:', error);
                    this.showMapFallback(mapContainerId, originLabel, destLabel);
                }
            } else {
                setTimeout(checkElement, 100);
            }
        };
        
        checkElement();
    },

    /**
     * Initialize Google Maps (Static API)
     */
    async initializeGoogleMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config) {
        // Get Google Maps API key from Logistics Settings
        try {
            const settings = await frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Logistics Settings',
                    fieldname: 'routing_google_api_key'
                }
            });
            
            const apiKey = settings.message?.routing_google_api_key;
            
            if (apiKey && apiKey.length > 10) {
                const staticMapUrl = `https://maps.googleapis.com/maps/api/staticmap?key=${apiKey}&size=600x450&maptype=roadmap&markers=color:${config.markerColors.origin}|label:O|${originCoords[0]},${originCoords[1]}&markers=color:${config.markerColors.destination}|label:D|${destCoords[0]},${destCoords[1]}&path=color:0x0000ff|weight:5|${originCoords[0]},${originCoords[1]}|${destCoords[0]},${destCoords[1]}`;
                
                const mapElement = document.getElementById(mapContainerId);
                if (mapElement) {
                    const testImg = new Image();
                    testImg.onload = function() {
                        mapElement.innerHTML = `
                            <img 
                                src="${staticMapUrl}" 
                                alt="Route Map" 
                                style="width: 100%; height: 100%; object-fit: cover;"
                            />
                        `;
                    };
                    testImg.onerror = function() {
                        console.warn('Google Maps Static API failed, showing fallback');
                        this.showMapFallback(mapContainerId, originLabel, destLabel);
                    };
                    testImg.src = staticMapUrl;
                }
            } else {
                console.warn('Google Maps API key not configured, showing fallback');
                this.showMapFallback(mapContainerId, originLabel, destLabel);
            }
        } catch (error) {
            console.error('Error with Google Maps:', error);
            this.showMapFallback(mapContainerId, originLabel, destLabel);
        }
    },

    /**
     * Initialize Mapbox map (placeholder)
     */
    async initializeMapboxMap(mapContainerId, originCoords, destCoords, originLabel, destLabel, config) {
        console.log('Mapbox map initialization - placeholder');
        this.showMapFallback(mapContainerId, originLabel, destLabel);
    },

    /**
     * Show map fallback when map fails to load
     */
    showMapFallback(mapContainerId, originLabel, destLabel) {
        const mapElement = document.getElementById(mapContainerId);
        if (mapElement) {
            mapElement.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; flex-direction: column; height: 100%; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
                    <div style="text-align: center; color: #6c757d;">
                        <i class="fa fa-map" style="font-size: 32px; margin-bottom: 15px;"></i>
                        <div style="font-size: 18px; font-weight: 500; margin-bottom: 10px;">Route Map</div>
                        <div style="font-size: 14px; margin-bottom: 15px; line-height: 1.4;">
                            <strong>Origin:</strong> ${originLabel || 'Not specified'}<br>
                            <strong>Destination:</strong> ${destLabel || 'Not specified'}
                        </div>
                        <div style="font-size: 12px; color: #999;">
                            Map unavailable
                        </div>
                    </div>
                </div>
            `;
        }
    },

    /**
     * Generate external map links
     */
    generateExternalMapLinks(originLabel, destLabel) {
        const links = {
            google: `https://www.google.com/maps/dir/${encodeURIComponent(originLabel)}/${encodeURIComponent(destLabel)}`,
            osm: `https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=${encodeURIComponent(originLabel)};${encodeURIComponent(destLabel)}`,
            apple: `https://maps.apple.com/?daddr=${encodeURIComponent(destLabel)}&saddr=${encodeURIComponent(originLabel)}`
        };
        
        return `
            <div class="text-muted small" style="margin-top: 10px; display: flex; gap: 20px; align-items: center; justify-content: center;">
                <a href="${links.google}" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
                    <i class="fa fa-external-link"></i> Google Maps
                </a>
                <a href="${links.osm}" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
                    <i class="fa fa-external-link"></i> OpenStreetMap
                </a>
                <a href="${links.apple}" target="_blank" rel="noopener" style="text-decoration: none; color: #6c757d; font-size: 12px;">
                    <i class="fa fa-external-link"></i> Apple Maps
                </a>
            </div>
        `;
    }
};

// Auto-load Leaflet CSS and JS if not already loaded
if (typeof L === 'undefined') {
    const leafletCSS = document.createElement('link');
    leafletCSS.rel = 'stylesheet';
    leafletCSS.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(leafletCSS);
    
    const leafletJS = document.createElement('script');
    leafletJS.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    document.head.appendChild(leafletJS);
}
