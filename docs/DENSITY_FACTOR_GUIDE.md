# Density Factor: How to Read and Use It

This guide explains the **Density Factor** shown in the Measurements section on Air Booking, Sea Booking, Air Shipment, and Sea Shipment. It helps you see at a glance whether your cargo is **dense** (heavy for its size) or **volumetric** (light for its size), and how that affects chargeable weight and pricing.

---

## What Is the Density Factor?

The **density factor** is the ratio:

**Density Factor = Volume (cm³) ÷ Weight (kg)**

- It is computed from the **header** volume and weight (either aggregated from packages or manually overridden).
- Volume is expressed in **cm³** and weight in **kg**, so the result is in **cm³ per kg**.
- The scale used in the bar is **1** (dense) to **6000** (volumetric), matching the common air freight divisor (e.g. IATA 1:6000).

---

## How to Read the Bar Indicator

The density factor is shown in two ways:

1. **Fill bar**  
   A blue bar that fills from the **left** toward the **right**. The more it fills, the more **volumetric** (light for size) the cargo is.

2. **Numeric badge**  
   A small label on the bar showing the exact density factor value (e.g. `167.0`, `3000.0`).

### Scale Under the Bar

- **(1:1) Dense** (left)  
  Low ratio: heavy for the volume. Actual weight typically drives chargeable weight.

- **1:6** (middle)  
  Mid-range: mixed density.

- **Volumetric (1:6000)** (right)  
  High ratio: light for the volume. Volumetric weight typically drives chargeable weight (e.g. volume in cm³ ÷ 6000).

### Examples

| Bar position | Approx. factor | Meaning |
|-------------|----------------|--------|
| Far left    | &lt; 500        | Very dense; chargeable weight ≈ actual weight |
| Left–centre | 500–2000       | Moderate density |
| Centre–right| 2000–6000      | Light; chargeable weight often = volume weight |
| Far right   | &gt; 6000       | Very volumetric; chargeable weight = volume weight |

---

## Where You See It

The density factor bar appears in the **Measurements** section on:

- **Air Booking**
- **Sea Booking**
- **Air Shipment**
- **Sea Shipment**

Header **Volume** and **Weight** are usually filled from the **packages** table. If you use **Override Volume & Weight**, you can enter volume and weight manually; the density factor is then calculated from those overridden values.

---

## How It’s Used in Freight

1. **Chargeable weight**  
   Carriers (especially in air freight) charge on the **higher** of:
   - **Actual weight** (kg), and  
   - **Volumetric weight** = volume (cm³) ÷ divisor (e.g. 6000 for IATA).

   The density factor is exactly **volume (cm³) ÷ weight (kg)**. So:
   - If the factor **&lt; divisor** (e.g. &lt; 6000): cargo is dense → chargeable weight = actual weight.
   - If the factor **≥ divisor**: cargo is volumetric → chargeable weight = volume weight.

2. **Pricing and capacity**  
   Knowing whether you are “left” (dense) or “right” (volumetric) on the bar helps you:
   - Anticipate whether you will be charged on weight or on volume.
   - Compare different shipments and packaging choices.

3. **Override Volume & Weight**  
   When you check **Override Volume & Weight**, header volume and weight are no longer updated from package totals. You can enter totals manually (e.g. from a master AWB or different system). The density factor bar and number always reflect the **current** header volume and weight, whether from packages or overridden.

---

## Practical Tips

- **Bar mostly empty (left)**  
  Cargo is dense. Focus on actual weight and weight limits.

- **Bar mostly full (right)**  
  Cargo is volumetric. Improving packing (smaller volume for same weight) can reduce chargeable weight and cost.

- **Factor near 167 (≈ 1:167)**  
  Equivalent to about 167 kg/m³, often used as a “break-even” density when the divisor is 6000 (1 m³ = 1,000,000 cm³ → 1,000,000 ÷ 6000 ≈ 167 kg/m³).

- **Changing packages**  
  When you add or edit packages and do **not** use Override Volume & Weight, header volume and weight (and thus the density factor) update from package totals. After changing packages, the bar and number refresh automatically.

---

## Summary

- **Density factor** = Volume (cm³) ÷ Weight (kg).
- **Bar**: left = dense, right = volumetric (scale 1 to 6000).
- **Use it** to see whether chargeable weight will be driven by actual weight or volumetric weight, and to compare or optimize shipments.
- **Override Volume & Weight** lets you set header totals manually; the density factor is always based on the current header volume and weight.
