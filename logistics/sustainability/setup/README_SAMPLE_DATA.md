# Sample Data Generator for Sustainability Module

This script generates realistic sample data for the Sustainability module without hard coding values. It dynamically uses data from your system (companies, branches, dates, etc.).

## Features

✅ **No Hard Coding** - All values are dynamically calculated based on:
- System companies and branches
- Date ranges (last 6 months)
- Module types (Transport, Warehousing, Air Freight, Sea Freight)
- Realistic variations and distributions

✅ **Comprehensive Data** - Generates:
- **Energy Consumption** records (~weekly for each module)
- **Carbon Footprint** records (linked to energy consumption)
- **Sustainability Metrics** records (weekly aggregations)
- **Emission Breakdowns** (Scope 1, 2, 3)

✅ **Realistic Values** - Includes:
- Proper date ranges and distributions
- Module-specific energy types and consumption patterns
- Carbon emission calculations
- Efficiency scores and compliance statuses
- Renewable energy percentages

## How to Use

### Method 1: Command Line (Recommended)

```bash
cd /home/frappe/frappe-bench
bench --site <your-site> console
```

Then in the console:
```python
from logistics.sustainability.setup.create_sample_data import create_sample_sustainability_data
create_sample_sustainability_data()
```

### Method 2: Via bench execute

```bash
cd /home/frappe/frappe-bench
bench --site <your-site> execute logistics.sustainability.setup.create_sample_data.create_sample_sustainability_data
```

### Method 3: Via Python Script

```bash
cd /home/frappe/frappe-bench
bench --site <your-site> run python apps/logistics/logistics/sustainability/setup/create_sample_data.py
```

### Method 4: From UI (if whitelisted)

The function `generate_sample_data()` is whitelisted and can be called via API if needed.

## What Gets Generated

For each company in your system:

### Energy Consumption Records
- **Frequency**: ~Weekly for last 6 months
- **Modules**: Transport, Warehousing, Air Freight, Sea Freight
- **Fields**: Energy type, consumption value, cost, renewable percentage, carbon footprint
- **Variations**: Realistic ranges based on module type

### Carbon Footprint Records
- **Frequency**: Same as energy consumption
- **Linked to**: Energy consumption records (when available)
- **Fields**: Total emissions, scope breakdown, carbon offsets
- **Scopes**: Properly distributed Scope 1, 2, and 3

### Sustainability Metrics Records
- **Frequency**: Weekly aggregations
- **Fields**: Aggregated energy, carbon, waste, water consumption
- **Scores**: Energy efficiency, carbon efficiency, waste efficiency, overall sustainability score
- **Status**: Compliance, certification, and verification statuses

## Data Characteristics

### Energy Consumption by Module:
- **Transport**: 200-800 Liters (diesel/gasoline/electric)
- **Warehousing**: 1200-2800 kWh (electricity)
- **Air Freight**: 400-1200 Liters (jet fuel)
- **Sea Freight**: 300-900 Liters (marine diesel)

### Carbon Footprint by Module:
- **Transport**: 500-2500 kg CO2e
- **Warehousing**: 400-1600 kg CO2e
- **Air Freight**: 1000-4000 kg CO2e
- **Sea Freight**: 800-3200 kg CO2e

### Scores (0-100 scale):
- Energy Efficiency: 60-95
- Carbon Efficiency: 55-90
- Waste Efficiency: 50-85

## Prerequisites

1. **Companies** must exist in the system
2. **Emission Factors** should be set up (optional, but recommended)
3. **Branches** (optional) - will be used if available

## Notes

- The script checks for existing records to avoid duplicates
- Data is generated for the **last 6 months** from today
- Records are distributed throughout the period (not every day)
- Values include realistic variations and randomness
- All calculations are based on module-specific patterns

## Troubleshooting

If you encounter errors:
1. Ensure at least one Company exists
2. Check that Emission Factors are set up (run `setup_sustainability()` first)
3. Verify date ranges are valid
4. Check Error Log in Frappe for details

## Example Output

```
🔧 Creating sample sustainability data...

📊 Processing company: Your Company
  📦 Generating data for Transport...
  📦 Generating data for Warehousing...
  📦 Generating data for Air Freight...
  📦 Generating data for Sea Freight...

✅ Sample data creation completed!
   📊 Sustainability Metrics: 48
   🔥 Carbon Footprint: 96
   ⚡ Energy Consumption: 96
```

