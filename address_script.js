// Copyright (c) 2025, www.agilasoft.com and contributors
// Address Form Script - Map Integration
// Version: 2.6 - Removed type restriction for default Google Maps search (shows all places including establishments)

console.log('=== Address map script file loaded ===');
console.log('=== Version 2.2 - Clean Google Maps Implementation ===');

// ============================================================================
// Google Maps API Error Handling
// ============================================================================

window._google_maps_auth_failed = false;
window._google_maps_api_loaded = false;

window.gm_authFailure = function() {
    console.error('Address map: Google Maps API authentication failed - API key is invalid or restricted');
    window._google_maps_auth_failed = true;
    
    var currentDomain = window.location.hostname;
    var domainPattern = currentDomain.indexOf('.') > 0 ? currentDomain.split('.').slice(-2).join('.') : currentDomain;
    
    var containers = document.querySelectorAll('[id*="address_map_container"]');
    containers.forEach(function(container) {
        if (container && !container.querySelector('.google-maps-error')) {
            container.innerHTML = '<div class="google-maps-error" style="padding: 20px; text-align: center; color: #721c24; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; margin: 10px 0;"><strong>⚠️ Google Maps API Authentication Failed</strong><br><small style="display: block; margin-top: 10px; text-align: left;">The API key is invalid, restricted, or billing is not enabled.<br><br><strong>Check in Google Cloud Console:</strong><br>1. Go to <a href="https://console.cloud.google.com/apis/credentials" target="_blank">APIs & Services > Credentials</a><br>2. Click your API key<br>3. Under "API restrictions", ensure "Maps JavaScript API" and "Places API" are enabled<br>4. Under "Application restrictions", if set to "HTTP referrers", add:<br>&nbsp;&nbsp;• <code>https://' + currentDomain + '/*</code><br>&nbsp;&nbsp;• <code>https://*.' + domainPattern + '/*</code><br>5. <strong>Verify billing is enabled</strong> for your Google Cloud project<br><br><strong>Current domain:</strong> <code>' + currentDomain + '</code></small></div>';
        }
    });
};

window._handleGoogleMapsError = function(error) {
    console.error('Address map: Google Maps error:', error);
    if (error && error.message) {
        if (error.message.indexOf('InvalidKey') >= 0 || error.message.indexOf('InvalidKeyMapError') >= 0) {
            if (window.gm_authFailure) {
                window.gm_authFailure();
            }
        }
    }
};

window.addEventListener('error', function(event) {
    if (event.message && (
        event.message.indexOf('InvalidKey') >= 0 || 
        event.message.indexOf('Google Maps') >= 0 ||
        (event.filename && event.filename.indexOf('maps.googleapis.com') >= 0)
    )) {
        console.error('Address map: Detected Google Maps API error:', event.message);
        window._google_maps_auth_failed = true;
        if (window.gm_authFailure) {
            window.gm_authFailure();
        }
    }
}, true);

// ============================================================================
// Main Initialization
// ============================================================================

(function() {
    function initAddressMap() {
        if (typeof frappe === 'undefined' || !frappe.ui || !frappe.ui.form) {
            console.log('Address map: Waiting for Frappe UI...');
            setTimeout(initAddressMap, 100);
            return;
        }
        
        console.log('Address map: Frappe UI available, registering form handler');
        
        frappe.ui.form.on('Address', {
            setup: function(frm) {
                console.log('Address form setup - Map script loaded');
            },
            
            onload: function(frm) {
                console.log('Address form onload');
            },
            
            refresh: function(frm) {
                console.log('Address form refresh - Initializing map');
                var attempts = 0;
                var maxAttempts = 10;
                
                var tryInitialize = function() {
                    attempts++;
                    console.log('Address map: Attempt ' + attempts + ' to initialize');
                    var mapField = frm.get_field('custom_address_map');
                    
                    if (mapField && mapField.$wrapper && mapField.$wrapper.length > 0) {
                        console.log('Address map: Field found, initializing...');
                        initializeAddressMapContent(frm);
                    } else if (attempts < maxAttempts) {
                        console.log('Address map: Field not ready, retrying in ' + (attempts * 300) + 'ms...');
                        setTimeout(tryInitialize, attempts * 300);
                    } else {
                        console.error('Address map: Field not found after ' + maxAttempts + ' attempts');
                    }
                };
                
                setTimeout(tryInitialize, 500);
            },
            
            custom_latitude: function(frm) {
                updateMapFromCoordinates(frm);
            },
            
            custom_longitude: function(frm) {
                updateMapFromCoordinates(frm);
            }
        });
    }
    
    initAddressMap();
})();

// ============================================================================
// Map Initialization Functions
// ============================================================================

async function initializeAddressMapContent(frm) {
    console.log('Initializing address map for:', frm.doc.name || 'new record');
    
    var mapField = frm.get_field('custom_address_map');
    if (!mapField || !mapField.$wrapper) {
        console.error('Address map: Field or wrapper not found');
        return;
    }
    
    var $wrapper = mapField.$wrapper;
    var mapContainerId = 'address_map_container_' + (frm.doc.name || 'new').replace(/[^a-zA-Z0-9]/g, '_');
    var searchInputId = 'address_search_input_' + (frm.doc.name || 'new').replace(/[^a-zA-Z0-9]/g, '_');
    var mapHTML = '<div style="margin-bottom: 10px;"><input type="text" id="' + searchInputId + '" placeholder="Search for an address..." style="width: 100%; padding: 8px 12px; border: 1px solid #d1d8dd; border-radius: 4px; font-size: 14px; box-sizing: border-box;"/></div><div id="' + mapContainerId + '" style="width: 100%; height: 400px; border: 1px solid #d1d8dd; border-radius: 4px; margin-top: 10px; background: #f8f9fa;"></div><div style="margin-top: 10px; font-size: 12px; color: #6c757d;"><i class="fa fa-info-circle"></i> Search for an address or click on the map to set coordinates</div>';
    
    try {
        var $target = $wrapper.find('.html-content, .control-value, .control-input-wrapper').first();
        if (!$target || $target.length === 0) {
            $target = $wrapper.children().first();
            if ($target.length === 0) {
                $target = $wrapper;
            }
        }
        $target.html(mapHTML);
        $wrapper.html(mapHTML);
    } catch (error) {
        console.error('Address map: Error setting HTML:', error);
    }
    
    setTimeout(function() {
        var container = document.getElementById(mapContainerId);
        if (container) {
            console.log('Address map: Container verified in DOM!');
        }
    }, 500);
    
    var mapRenderer = 'OpenStreetMap';
    var tilesUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    var tilesAttr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
    var googleApiKey = null;
    var mapboxApiKey = null;
    
    try {
        var settings = await frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Transport Settings',
                name: 'Transport Settings'
            }
        });
        
        if (settings.message) {
            mapRenderer = settings.message.map_renderer || 'OpenStreetMap';
            tilesUrl = settings.message.routing_tiles_url || tilesUrl;
            tilesAttr = settings.message.routing_tiles_attr || tilesAttr;
            
            // Get Google Maps API key using proper endpoint (decrypts Password field)
            try {
                var apiKeyResponse = await frappe.call({
                    method: 'logistics.transport.api.address_map_api.get_google_maps_api_key'
                });
                if (apiKeyResponse.message && apiKeyResponse.message.api_key) {
                    googleApiKey = apiKeyResponse.message.api_key;
                }
                console.log('Address map: Google API Key retrieved:', googleApiKey ? 'Present' : 'Missing');
            } catch (error) {
                console.error('Address map: Error getting API key:', error);
            }
            
            mapboxApiKey = settings.message.routing_mapbox_api_key;
            console.log('Address map: Map Renderer:', mapRenderer);
            console.log('Address map: Google API Key present:', !!googleApiKey);
        }
    } catch (e) {
        console.error('Address map: Error getting Transport Settings:', e);
    }
    
    var lat = parseFloat(frm.doc.custom_latitude);
    var lon = parseFloat(frm.doc.custom_longitude);
    
    initializeMapRenderer(frm, mapContainerId, lat, lon, mapRenderer, tilesUrl, tilesAttr, googleApiKey, mapboxApiKey);
}

async function initializeMapRenderer(frm, mapContainerId, lat, lon, mapRenderer, tilesUrl, tilesAttr, googleApiKey, mapboxApiKey) {
    await new Promise(function(resolve) {
        setTimeout(resolve, 500);
    });
    
    var container = document.getElementById(mapContainerId);
    if (!container) {
        var allContainers = document.querySelectorAll('[id*="address_map"]');
        if (allContainers.length > 0) {
            container = allContainers[0];
            mapContainerId = container.id;
        }
    }
    
    if (!container) {
        console.error('Address map: Container not found');
        return;
    }
    
    console.log('Address map: Container found, initializing map with renderer:', mapRenderer);
    var rendererLower = (mapRenderer || '').toLowerCase().trim();
    
    if (rendererLower === 'google maps' || rendererLower === 'googlemaps' || rendererLower.indexOf('google') >= 0) {
        console.log('Address map: Using Google Maps renderer');
        await initializeGoogleMap(frm, mapContainerId, lat, lon, googleApiKey);
    } else if (rendererLower === 'mapbox') {
        await initializeMapboxMap(frm, mapContainerId, lat, lon, mapboxApiKey);
    } else if (rendererLower === 'maplibre') {
        await initializeMapLibreMap(frm, mapContainerId, lat, lon, tilesUrl, tilesAttr);
    } else {
        await initializeOpenStreetMap(frm, mapContainerId, lat, lon, tilesUrl, tilesAttr);
    }
}

async function initializeGoogleMap(frm, mapContainerId, lat, lon, apiKey) {
    console.log('Address map: Initializing Google Maps - V2.2');
    
    if (!apiKey || apiKey.length < 10) {
        console.error('Address map: Google Maps API key not configured');
        var container = document.getElementById(mapContainerId);
        if (container) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #856404; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px;"><strong>⚠️ Google Maps API Key Not Configured</strong><br><small style="display: block; margin-top: 10px;">Please set the Google API Key in Transport Settings.</small></div>';
        }
        return;
    }
    
    // Load Google Maps API if not already loaded
    if (typeof google === 'undefined' || !google.maps || !google.maps.Map) {
        console.log('Address map: Loading Google Maps API...');
        try {
            await loadGoogleMapsAPI(apiKey);
        } catch (error) {
            console.error('Address map: Failed to load Google Maps API:', error);
            var container = document.getElementById(mapContainerId);
            if (container) {
                container.innerHTML = '<div style="padding: 20px; text-align: center; color: #856404; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px;"><strong>⚠️ Google Maps API Failed to Load</strong><br><small style="display: block; margin-top: 10px;">Please check your Google Cloud Console configuration.</small></div>';
            }
            return;
        }
    }
    
    // Wait for API to be fully ready
    var retries = 0;
    while ((typeof google === 'undefined' || !google.maps || !google.maps.Map) && retries < 50) {
        await new Promise(function(resolve) {
            setTimeout(resolve, 100);
        });
        retries++;
    }
    
    // Final check
    if (typeof google === 'undefined' || !google.maps || !google.maps.Map) {
        console.error('Address map: Google Maps API failed to load - Map constructor not available');
        var container = document.getElementById(mapContainerId);
        if (container) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #856404; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px;"><strong>⚠️ Google Maps API Failed to Load</strong><br><small style="display: block; margin-top: 10px;">The Google Maps API did not load properly. Please check your browser console for errors.</small></div>';
        }
        return;
    }
    
    console.log('Address map: Google Maps API is ready, Map constructor available');
    
    try {
        var container = document.getElementById(mapContainerId);
        if (!container) {
            console.error('Address map: Container not found for Google Maps');
            return;
        }
        
        var defaultLat = lat && !isNaN(lat) ? lat : 0;
        var defaultLon = lon && !isNaN(lon) ? lon : 0;
        var centerLat = defaultLat || 0;
        var centerLon = defaultLon || 0;
        var zoom = (lat && lon && !isNaN(lat) && !isNaN(lon)) ? 15 : 2;
        
        var map = new google.maps.Map(container, {
            center: { lat: centerLat, lng: centerLon },
            zoom: zoom,
            mapTypeId: 'roadmap'
        });
        
        google.maps.event.addListenerOnce(map, 'tilesloaded', function() {
            console.log('Address map: Google Maps tiles loaded successfully');
        });
        
        setTimeout(function() {
            try {
                var center = map.getCenter();
                if (!center) {
                    throw new Error('Map center not available');
                }
            } catch (error) {
                console.error('Address map: Google Maps error detected:', error);
            }
        }, 3000);
        
        var marker = null;
        if (lat && lon && !isNaN(lat) && !isNaN(lon)) {
            marker = new google.maps.Marker({
                position: { lat: lat, lng: lon },
                map: map,
                draggable: true,
                title: 'Address Location'
            });
            
            var infoWindow = new google.maps.InfoWindow({
                content: '<div><strong>Address Location</strong><br>Latitude: ' + lat.toFixed(6) + '<br>Longitude: ' + lon.toFixed(6) + '<br><small>Drag marker to update coordinates</small></div>'
            });
            
            marker.addListener('click', function() {
                infoWindow.open(map, marker);
            });
            
            infoWindow.open(map, marker);
            
            marker.addListener('dragend', function(e) {
                var position = marker.getPosition();
                frm.set_value('custom_latitude', position.lat());
                frm.set_value('custom_longitude', position.lng());
                infoWindow.setContent('<div><strong>Address Location</strong><br>Latitude: ' + position.lat().toFixed(6) + '<br>Longitude: ' + position.lng().toFixed(6) + '<br><small>Drag marker to update coordinates</small></div>');
            });
        }
        
        map.addListener('click', function(e) {
            var clickedLat = e.latLng.lat();
            var clickedLon = e.latLng.lng();
            frm.set_value('custom_latitude', clickedLat);
            frm.set_value('custom_longitude', clickedLon);
            
            if (marker) {
                marker.setPosition({ lat: clickedLat, lng: clickedLon });
            } else {
                marker = new google.maps.Marker({
                    position: { lat: clickedLat, lng: clickedLon },
                    map: map,
                    draggable: true,
                    title: 'Address Location'
                });
                
                var infoWindow = new google.maps.InfoWindow({
                    content: '<div><strong>Address Location</strong><br>Latitude: ' + clickedLat.toFixed(6) + '<br>Longitude: ' + clickedLon.toFixed(6) + '<br><small>Drag marker to update coordinates</small></div>'
                });
                
                marker.addListener('click', function() {
                    infoWindow.open(map, marker);
                });
                
                marker.addListener('dragend', function(e) {
                    var position = marker.getPosition();
                    frm.set_value('custom_latitude', position.lat());
                    frm.set_value('custom_longitude', position.lng());
                });
                
                infoWindow.open(map, marker);
            }
        });
        
        frm._address_map = map;
        frm._address_marker = marker;
        
        // Initialize Places Autocomplete
        initializePlacesAutocomplete(frm, map, marker, apiKey);
        
        console.log('Address map: Google Maps initialized successfully');
        
    } catch (error) {
        console.error('Address map: Error initializing Google Maps:', error);
        var container = document.getElementById(mapContainerId);
        if (container) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #856404; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px;"><strong>⚠️ Error Initializing Google Maps</strong><br><small style="display: block; margin-top: 10px;">' + (error.message || 'Unknown error') + '</small></div>';
        }
    }
}

function loadGoogleMapsAPI(apiKey) {
    return new Promise(function(resolve, reject) {
        // Check if already loaded
        if (typeof google !== 'undefined' && google.maps && google.maps.Map) {
            console.log('Address map: Google Maps API already loaded');
            resolve();
            return;
        }
        
        // Check if already loading
        if (window._google_maps_loading) {
            // Wait for existing load to complete
            var checkInterval = setInterval(function() {
                if (typeof google !== 'undefined' && google.maps && google.maps.Map) {
                    clearInterval(checkInterval);
                    resolve();
                } else if (!window._google_maps_loading) {
                    clearInterval(checkInterval);
                    reject(new Error('Google Maps API failed to load'));
                }
            }, 100);
            return;
        }
        
        window._google_maps_loading = true;
        
        // Create callback function
        window._googleMapsInitCallback = function() {
            console.log('Address map: Google Maps API loaded and ready');
            window._google_maps_api_loaded = true;
            window._google_maps_loading = false;
            delete window._googleMapsInitCallback;
            resolve();
        };
        
        var script = document.createElement('script');
        script.src = 'https://maps.googleapis.com/maps/api/js?key=' + apiKey + '&libraries=places&callback=_googleMapsInitCallback';
        script.async = true;
        script.defer = true;
        script.onerror = function() {
            console.error('Address map: Failed to load Google Maps API');
            window._google_maps_loading = false;
            delete window._googleMapsInitCallback;
            reject(new Error('Failed to load Google Maps API'));
        };
        document.head.appendChild(script);
    });
}

function initializeOpenStreetMap(frm, mapContainerId, lat, lon, tilesUrl, tilesAttr) {
    console.log('Address map: Initializing OpenStreetMap');
    // OpenStreetMap implementation would go here
    var container = document.getElementById(mapContainerId);
    if (container) {
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">OpenStreetMap renderer not yet implemented</div>';
    }
}

function initializeMapboxMap(frm, mapContainerId, lat, lon, apiKey) {
    console.log('Address map: Initializing Mapbox');
    // Mapbox implementation would go here
    var container = document.getElementById(mapContainerId);
    if (container) {
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">Mapbox renderer not yet implemented</div>';
    }
}

function initializeMapLibreMap(frm, mapContainerId, lat, lon, tilesUrl, tilesAttr) {
    console.log('Address map: Initializing MapLibre');
    // MapLibre implementation would go here
    var container = document.getElementById(mapContainerId);
    if (container) {
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: #6c757d;">MapLibre renderer not yet implemented</div>';
    }
}


// ============================================================================
// Google Places Autocomplete Functions
// ============================================================================

function initializePlacesAutocomplete(frm, map, marker, apiKey) {
    // Wait for Places library to be available
    if (typeof google === 'undefined' || !google.maps || !google.maps.places) {
        console.log('Address map: Waiting for Places library...');
        setTimeout(function() {
            initializePlacesAutocomplete(frm, map, marker, apiKey);
        }, 100);
        return;
    }
    
    var searchInputId = 'address_search_input_' + (frm.doc.name || 'new').replace(/[^a-zA-Z0-9]/g, '_');
    var searchInput = document.getElementById(searchInputId);
    
    if (!searchInput) {
        console.error('Address map: Search input not found');
        return;
    }
    
    console.log('Address map: Initializing Places Autocomplete');
    
    // Create Autocomplete - no type restriction to show all places like Google Maps app
    var autocomplete = new google.maps.places.Autocomplete(searchInput, {
        fields: ['address_components', 'geometry', 'formatted_address', 'name', 'place_id']
    });
    
    // Bind autocomplete to map bounds
    autocomplete.bindTo('bounds', map);
    
    // When a place is selected
    autocomplete.addListener('place_changed', function() {
        var place = autocomplete.getPlace();
        
        if (!place.geometry || !place.geometry.location) {
            console.warn('Address map: No geometry found for selected place');
            return;
        }
        
        console.log('Address map: Place selected:', place.formatted_address);
        
        // Update map center and zoom
        map.setCenter(place.geometry.location);
        if (place.geometry.viewport) {
            map.fitBounds(place.geometry.viewport);
        } else {
            map.setZoom(17);
        }
        
        // Update or create marker
        var position = place.geometry.location;
        var lat = position.lat();
        var lng = position.lng();
        
        if (marker) {
            marker.setPosition(position);
        } else {
            marker = new google.maps.Marker({
                position: position,
                map: map,
                draggable: true,
                title: 'Address Location'
            });
            
            var infoWindow = new google.maps.InfoWindow({
                content: '<div><strong>Address Location</strong><br>Latitude: ' + lat.toFixed(6) + '<br>Longitude: ' + lng.toFixed(6) + '<br><small>Drag marker to update coordinates</small></div>'
            });
            
            marker.addListener('click', function() {
                infoWindow.open(map, marker);
            });
            
            marker.addListener('dragend', function(e) {
                var pos = marker.getPosition();
                frm.set_value('custom_latitude', pos.lat());
                frm.set_value('custom_longitude', pos.lng());
                infoWindow.setContent('<div><strong>Address Location</strong><br>Latitude: ' + pos.lat().toFixed(6) + '<br>Longitude: ' + pos.lng().toFixed(6) + '<br><small>Drag marker to update coordinates</small></div>');
            });
            
            frm._address_marker = marker;
        }
        
        // Update coordinates
        frm.set_value('custom_latitude', lat);
        frm.set_value('custom_longitude', lng);
        
        // Parse address components and populate form fields
        var addressComponents = place.address_components || [];
        var addressData = {
            address_line1: '',
            address_line2: '',
            city: '',
            county: '',
            state: '',
            country: '',
            pincode: ''
        };
        
        // Parse address components
        for (var i = 0; i < addressComponents.length; i++) {
            var component = addressComponents[i];
            var types = component.types;
            
            if (types.indexOf('street_number') >= 0) {
                addressData.address_line1 = component.long_name;
            } else if (types.indexOf('route') >= 0) {
                if (addressData.address_line1) {
                    addressData.address_line1 += ' ' + component.long_name;
                } else {
                    addressData.address_line1 = component.long_name;
                }
            } else if (types.indexOf('subpremise') >= 0 || types.indexOf('premise') >= 0) {
                addressData.address_line2 = component.long_name;
            } else if (types.indexOf('locality') >= 0 || types.indexOf('sublocality') >= 0) {
                if (!addressData.city) {
                    addressData.city = component.long_name;
                }
            } else if (types.indexOf('administrative_area_level_2') >= 0) {
                addressData.county = component.long_name;
            } else if (types.indexOf('administrative_area_level_1') >= 0) {
                addressData.state = component.long_name;
            } else if (types.indexOf('country') >= 0) {
                addressData.country = component.long_name;
            } else if (types.indexOf('postal_code') >= 0) {
                addressData.pincode = component.long_name;
            }
        }
        
        // If address_line1 is empty, use place name or formatted_address
        if (!addressData.address_line1) {
            if (place.name) {
                addressData.address_line1 = place.name;
            } else if (place.formatted_address) {
                var parts = place.formatted_address.split(',');
                if (parts.length > 0) {
                    addressData.address_line1 = parts[0].trim();
                }
            }
        }
        
        // Update form fields
        if (addressData.address_line1) {
            frm.set_value('address_line1', addressData.address_line1);
        }
        if (addressData.address_line2) {
            frm.set_value('address_line2', addressData.address_line2);
        }
        if (addressData.city) {
            frm.set_value('city', addressData.city);
        }
        if (addressData.county) {
            frm.set_value('county', addressData.county);
        }
        if (addressData.state) {
            frm.set_value('state', addressData.state);
        }
        if (addressData.country) {
            frm.set_value('country', addressData.country);
        }
        if (addressData.pincode) {
            frm.set_value('pincode', addressData.pincode);
        }
        
        console.log('Address map: Address fields populated from Places API');
    });
    
    frm._address_autocomplete = autocomplete;
}

function updateMapFromCoordinates(frm) {
    if (frm._address_map && frm._address_marker) {
        var lat = parseFloat(frm.doc.custom_latitude);
        var lon = parseFloat(frm.doc.custom_longitude);
        
        if (lat && lon && !isNaN(lat) && !isNaN(lon)) {
            var position = { lat: lat, lng: lon };
            frm._address_map.setCenter(position);
            frm._address_marker.setPosition(position);
        }
    }
}
