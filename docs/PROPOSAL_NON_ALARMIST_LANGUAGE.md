# Proposal: Non-Alarmist Language for FloodWatch

## Context
The current FloodWatch system uses alarmist language (Extreme, Severe, Moderate, Flood Alerts) which may cause unnecessary public concern. The system should present data objectively as discharge exceedance thresholds rather than emergency alerts.

## Proposed Changes

### 1. Ticker Bar
**Current:** "Latest Situation of Flood Conditions" with labels: Extreme, Severe, Moderate
**Proposed:** "Discharge Exceedance per Threshold" with labels: High, Medium, Low

### 2. Country Summary Chart
**Current:** "Flood Alert Level per Country" with badges: Extreme (red), Severe (orange), Moderate (yellow)
**Proposed:** "Discharge Exceedance Level per Country" with badges: High (red), Medium (orange), Low (yellow)

### 3. Multimodal Legend
**Current:** Extreme, Severe, Moderate, Normal
**Proposed:** High Exceedance, Medium Exceedance, Low Exceedance, Normal

### 4. Scope Titles
**Current:** "Latest Situation of Flood Conditions" / "...for Nile"
**Proposed:** "Discharge Exceedance per Threshold" / "...for Nile Basin"

### 5. Remove Pulse Animation
The red "Extreme" dot currently has a pulsing animation (`animation:pulse 1.6s infinite`) which creates a sense of emergency. Proposal: remove the animation.

## Files to Modify
- `eafw_geomanager_web/home/templates/home/home_page.html` — ticker, chart labels, scope titles
- `eafw_geomanager_web/mapwidget/templates/mapwidget/map_widget.html` — minimap legend
- Database: `geomanager_vectortilelayer` legend config for Multimodal layer

## Impact
- No backend changes required
- Pure frontend/template text changes
- Database legend text update for Multimodal category

## Decision
Pending team review. These changes should be discussed with the ICPAC team before implementation to ensure alignment with communication guidelines.
