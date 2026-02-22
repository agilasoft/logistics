# Transport Settings

**Transport Settings** is a single-document configuration that defines default values and behavior for the Transport module. It controls routing, telematics, constraints, loading/unloading times, carbon footprint, and automation.

To access Transport Settings, go to:

**Home > Transport > Transport Settings**

## 1. Prerequisites

Before configuring Transport Settings, ensure the following are set up:

- [Load Type](welcome/load-type) – For capacity and planning
- [Vehicle Type](welcome/vehicle-type) – For transport planning
- [Transport Capacity Settings](welcome/transport-capacity-settings) – For capacity management

## 2. How to Configure

1. Go to **Transport Settings** (single document; no list).
2. Configure each tab as needed.
3. **Save** the document.

## 3. Features

### 3.1 Transport Plan

- **Forward Days in Transport Plan** – Days ahead to plan
- **Backward Days in Transport Plan** – Days back to include in plan

### 3.2 Automation

- **Enable Auto Billing** – Automatically create invoices for transport jobs
- **Enable Auto Vehicle Assignment** – Automatically assign vehicles to legs

### 3.3 Routing

- **Routing Provider** – OSRM, Mapbox, Google for route calculation
- **OSRM Base URL** – OSRM server URL
- **Routing Mapbox API Key** – Mapbox API key
- **Routing Google API Key** – Google Maps API key
- **Routing Default Avg Speed (km/h)** – Default speed for time estimation
- **Routing Auto Compute** – Automatically compute routes
- **Routing Show Map** – Show map on transport forms
- **Map Renderer** – Map display engine
- **Use Routing Service for Distance** – Use routing API for distance
- **Cache Route Distances** – Cache distances for performance
- **Distance Cache TTL Hours** – Cache validity period

### 3.4 Telematics

- **Default Telematics Provider** – Telematics integration
- **Telematics Poll Interval (min)** – How often to poll vehicle data

### 3.5 Constraint Features

- **Enable Constraint System** – Enable transport planning constraints
- **Constraint Checking Mode** – Strict or warning mode
- **Enable Time Window Constraints** – Respect delivery time windows
- **Enable Address Day Availability** – Restrict by day of week
- **Enable Plate Coding Constraints** – Restrict by vehicle plate
- **Enable Truck Ban Constraints** – Respect truck bans
- **Enable Adhoc Factors** – Allow ad-hoc delay/blocking factors
- **Require Vehicle Avg Speed** – Require speed for planning
- **Allow Vehicle Assignment with Warnings** – Allow assignment despite warnings
- **Block Incompatible Vehicle Types in Consolidation** – Prevent incompatible consolidations

### 3.6 Loading/Unloading

- **Default Base Loading Time (minutes)** – Base time for loading
- **Default Loading Time Calculation Method** – By volume, weight, or fixed
- **Default Loading Time Per Volume (m³)** – Minutes per CBM
- **Default Loading Time Per Weight (kg)** – Minutes per kg
- **Default Base Unloading Time (minutes)** – Base time for unloading
- **Default Unloading Time Calculation Method** – Same options as loading

### 3.7 Adhoc Factors

- **Adhoc Factor Delay Threshold (minutes)** – When to apply delay factors
- **Adhoc Factor Blocking Impact Types** – Which impact types block planning

### 3.8 Default UOM

- **Default Weight UOM** – kg, lb
- **Default Volume UOM** – CBM, CFT
- **Default Chargeable UOM** – For charges
- **Volume to Weight Divisor** – For chargeable weight

### 3.9 Carbon

- **Carbon Autocompute** – Automatically calculate carbon footprint
- **Carbon Default Factor (g/km)** – Default emission factor per km
- **Carbon Default Factor (g/ton-km)** – Default emission factor per ton-km
- **Carbon Provider** – External carbon calculation provider
- **Carbon Provider API Key** – API key for provider
- **Carbon Provider URL** – Provider endpoint

## 4. Related Topics

- [Transport Order](welcome/transport-order)
- [Transport Job](welcome/transport-job)
- [Transport Plan](welcome/transport-plan)
- [Run Sheet](welcome/run-sheet)
- [Transport Capacity Settings](welcome/transport-capacity-settings)
