# Shared Map Utilities Usage Guide

## Overview
The `map_utils.js` file provides a centralized way to render maps across all modules in the Logistics app. This eliminates code duplication and ensures consistent map behavior.

## Setup

1. Include the shared map utility in your module:
```html
<script src="/assets/logistics/js/map_utils.js"></script>
```

## Basic Usage

### Initialize a Simple Map
```javascript
// Basic map with default settings
await window.MapUtils.initializeMap(
    'map-container-id',    // HTML element ID
    [lat1, lon1],          // Origin coordinates [latitude, longitude]
    [lat2, lon2],          // Destination coordinates [latitude, longitude]
    'Origin Location',     // Origin label
    'Destination Location' // Destination label
);
```

### Initialize Map with Custom Options
```javascript
await window.MapUtils.initializeMap(
    'map-container-id',
    [lat1, lon1],
    [lat2, lon2],
    'Origin Location',
    'Destination Location',
    {
        zoom: 6,                    // Zoom level (default: 4)
        showRouteLine: true,        // Show route line (default: true)
        markerColors: {
            origin: 'blue',         // Origin marker color (default: 'green')
            destination: 'orange'   // Destination marker color (default: 'red')
        },
        onMapReady: function() {    // Callback when map is ready
            console.log('Map loaded successfully');
        }
    }
);
```

### Generate External Map Links
```javascript
const linksHtml = window.MapUtils.generateExternalMapLinks(
    'Origin Location',
    'Destination Location'
);

// Insert into your HTML
document.querySelector('.map-container').insertAdjacentHTML('beforeend', linksHtml);
```

### Show Fallback Map
```javascript
window.MapUtils.showMapFallback(
    'map-container-id',
    'Origin Location',
    'Destination Location'
);
```

## Supported Map Renderers

The utility automatically selects the map renderer based on Transport Settings:

1. **OpenStreetMap (Leaflet)** - Default, no API key required
2. **MapLibre** - Open source alternative to Mapbox
3. **Google Maps** - Requires API key in Transport Settings
4. **Mapbox** - Placeholder implementation

## Integration Examples

### In Air Freight Job
```javascript
async function initializeAirFreightMap() {
    const originPort = 'PHMNL';
    const destPort = 'HKHKG';
    const originCoords = [14.6042, 120.9822];
    const destCoords = [22.3080, 113.9185];
    
    await window.MapUtils.initializeMap(
        'route-map',
        originCoords,
        destCoords,
        originPort,
        destPort,
        {
            zoom: 4,
            showRouteLine: true
        }
    );
}
```

### In Transport Leg
```javascript
async function initializeTransportMap() {
    const pickCoords = [lat1, lon1];
    const dropCoords = [lat2, lon2];
    
    await window.MapUtils.initializeMap(
        'transport-map',
        pickCoords,
        dropCoords,
        'Pickup Location',
        'Drop Location',
        {
            zoom: 10,
            markerColors: {
                origin: 'green',
                destination: 'red'
            }
        }
    );
}
```

## Benefits

1. **Code Reusability** - No need to duplicate map logic
2. **Consistent Behavior** - Same map rendering across all modules
3. **Easy Maintenance** - Update map logic in one place
4. **Automatic Renderer Selection** - Respects Transport Settings
5. **Built-in Error Handling** - Fallback display when maps fail
6. **External Links** - Automatic generation of map service links

## File Structure
```
logistics/
├── common/
│   ├── map_utils.js          # Shared map utilities
│   └── map_utils_usage.md    # This documentation
├── air_freight/              # Uses map_utils.js
├── transport/                # Uses map_utils.js
└── other_modules/            # Can use map_utils.js
```

## Future Enhancements

- Support for multiple waypoints
- Custom marker icons
- Geocoding integration
- Real-time traffic data
- Map clustering for multiple locations
