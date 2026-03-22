# FloodWatch Platform Feedback — WHCA / WMO

**Source:** Ramesh Tripathi (WMO) — rtripathi@wmo.int
**Date:** March 20, 2026

---

## 1. Homepage & Footer Updates

### Add SMHI as Technical Partner

Add the **SMHI logo** under the Technical Partners / "Our Partners" section on the homepage.

![SMHI Logo](feedback-images/feedback_image_16.png)

![Current homepage showing partner logos](feedback-images/feedback_image_1.png)

### Contact Information

Add to footer or contact section:
> For any issues or additional information: contact ICPAC email address or rtripathi@wmo.int

### WHCA Project Description

Add the following project context (e.g. in footer or About section):

> **Water at the Heart of Climate Action (WHCA)**
>
> The WHCA project is strengthening water action to mitigate the impacts of water-related risks and increase the climate resilience of affected communities. The project is implemented under the overall Early Warning For All (EW4All) initiative to ensure everyone on this planet is protected by the early warning system.
>
> More information: https://www.waterattheheartofclimateaction.org/

![WHCA page on current site](feedback-images/feedback_image_14.png)

### **Comment (RT):** WHCA Launch Page
> I suggest to still keep the Launch page for WHCA. If integrated into http://floodwatch.icpac.net/ or stand alone WHCA page where NMHSs can go there at the start and on Login to platform click goes to http://floodwatch.icpac.net/
>
> This will be good for visibility to donor and also partners and specific support that can be provided in the Launch page.
>
> - Contact for HelpDesk
> - Training materials can be added such as user guide or operational procedures
> - Partners model specific info etc.

---

## 2. Platform Title & Branding

### **Comment (RT):** Title and Icons
> - **"Nile Flood Watch"** as the title and project icon
> - On the side, put **WHCA icon**

---

## 3. Map Icons — Differentiate Station Types

Currently all points use the same icon. The proposal is to differentiate:

1. **Actual stations** (with observed data) → Show with a **station icon** ![station icon](feedback-images/feedback_image_20.png)
2. **Forecasting points** (dummy flood plain locations) → Show as **round points** (circles)

This helps users distinguish between real station locations and modeled flood plain points.

![Zoomed view showing station points](feedback-images/feedback_image_2.png)

---

## 4. Alert Color Coding — Use CAP Standard

### **Comment (RT):** Standard CAP Warning Colors
> I suggest to keep icon and marked levels as standard colour coding with the CAP type warning so that country understanding remains from Hydrology and Meteorology Thresholds:
>
> - 🟢 **GREEN (No Warning/Normal):** No meteorological risk is expected. Normal conditions prevail, with no special precautions required.
> - 🟡 **YELLOW (Be Aware/Moderate):** Hazardous weather is possible, which may cause minor damage, localized, or short-term impacts. This is the most common alert level, requiring monitoring of the situation.
> - 🟠 **ORANGE (Be Prepared/Severe):** Severe weather is expected, likely to cause significant damage, major disruptions, or serious health impacts. These are less common than yellow alerts and require immediate precautionary measures.
> - 🔴 **RED (Take Action/Extreme):** Very dangerous, extreme, or life-threatening weather is expected, likely causing widespread, severe damage or disruption. Immediate action to ensure safety should be taken.

### **Comment (RT):** Regional Variations
> - **Canada (ECCC):** Uses a tri-coloured system (Yellow, Orange, Red) for warnings/watches
> - **Meteoalarm (Europe):** Uses a four-level system (Green, Yellow, Orange, Red) to harmonize alerts across Europe
> - **India (IMD):** Follows a four-stage system (Green, Yellow, Orange, Red) for various meteorological phenomena

**Note:** Current FloodWatch thresholds use flow-based levels: Warning (≥300 m³/s), Alarm (≥500 m³/s), Emergency (≥750 m³/s). Mapping these to CAP Green/Yellow/Orange/Red needs alignment.

---

## 5. Sidebar Panel Reorganization

The sidebar (black circle area in screenshot) should be reorganized into two tabs:

![Current sidebar with layer categories](feedback-images/feedback_image_17.png)

### Proposed Structure

**Observations Tab:**
- Rainfall — Real-time data from AWS (country-level) or near-real-time global products (NOAA/NASA)
- Water levels — Observations from stations

**Forecasts Tab:**
- Multi-model forecast products (current "Multimodal" content)

---

## 6. Date/Time Selector Bar

Add a **Start Time** and **End Time** selector bar (red circle area in screenshot), visible in the map toolbar.

![Current date/time selector](feedback-images/feedback_image_7.png)

The selector should allow users to pick a time range for viewing forecasts and observations.

---

## 7. Show All Forecasting Points at All Zoom Levels

![Map view showing partial points](feedback-images/feedback_image_9.png)

Currently, only a few forecasting points are shown at lower zoom levels; others only appear when zooming in.

**Request:** Show **all forecasting points** — both stations and dummy flood plain points — at all zoom levels.

---

## 8. Hazard Layers

- Add a **Hazards** icon in the layer panel
- Show **hazard maps for different return periods** as static layers:
  - 25-year flood extent
  - 100-year flood extent
  - (Other return periods as available)

These are already in the system as raster tile layers (`flood_extent_rp25`, `flood_extent_rp100`) served via MapCache.
