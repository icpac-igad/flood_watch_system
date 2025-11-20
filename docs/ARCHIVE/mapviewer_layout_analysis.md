# East Africa Flood Watch - MapViewer Layout Dimensions and Structure Analysis

## Overview
The MapViewer component uses a fixed-position layout with a sidebar, map container, bottom panel (chart area), and footer. The layout is responsive with multiple breakpoints for mobile, tablet, and desktop views.

---

## 1. NAVBAR (Header)

### Desktop Dimensions
- **Position**: `fixed` (top: 0, left: 0, right: 0)
- **Height**: `80px` (minimum) / `auto` (flexible)
- **Z-Index**: `1000`
- **Background**: `#034930` (dark green)
- **Border**: `2px solid #034930` (bottom)
- **Padding**: `0.5rem`

### Logo/Brand Dimensions
- **Height**: `70px` (desktop)
- **Width**: `auto` (responsive)
- **Max-width**: `100%`

### Responsive Breakpoints for Navbar
- **Tablet (768px - 1023px)**: Min-height: `60px`
- **Mobile (max-width: 768px)**: Logo height: `40px`, max-height: `35px`
- **Small Mobile (max-width: 480px)**: Logo height: `35px`, max-height: `30px`

---

## 2. SIDEBAR

### Desktop Dimensions
- **Position**: `fixed`
- **Width**: `350px` (default) / `280px` (tablet 768-1023px)
- **Height**: `calc(100vh - 80px)` (full viewport height minus navbar)
- **Top**: `80px` (below navbar)
- **Left**: `0`
- **Z-Index**: `998`
- **Background**: `#ffffff`
- **Border**: `2px solid #d0d0d0` (right side)
- **Box-shadow**: `2px 0 6px rgba(0, 0, 0, 0.15)`
- **Overflow**: `overflow-y: auto` (scrollable content)

### Sidebar Tabs (Tab Navigation)
- **Position**: `fixed`
- **Top**: `80px`
- **Left**: `0`
- **Width**: `350px` (same as sidebar)
- **Z-Index**: `999` (above sidebar content)
- **Background**: `#ffffff`
- **Border-bottom**: `1px solid #e9ecef`
- **Display**: `flex`

### Tab Buttons (.tab-link)
- **Width**: `175px` (each tab - 350px / 2)
- **Padding**: `15px 25px`
- **Font-size**: `14px`
- **Border-bottom**: `3px solid transparent` (default), `3px solid #034930` (active)
- **Color**: `#034930` (default), `#FFC107` (hover), `#FFC107` (active)

### Responsive Sidebar
- **Tablet (768-1023px)**: Width: `280px`
- **Mobile (max-width: 768px)**: 
  - Position: `initial` (not fixed)
  - Width: `100%`
  - Height: `auto`
  - Borders and shadows: `none`
  - Displays as bottom sheet (MUI bottom sheet component)

---

## 3. MAP CONTAINER

### Desktop Dimensions
- **Position**: `fixed`
- **Left**: `352px` (350px sidebar + 2px border)
- **Right**: `0`
- **Top**: `80px` (below navbar)
- **Bottom**: `30px` (above footer) or dynamic based on chart panel: `calc(${panelHeight}px + 30px)`
- **Z-Index**: `1`
- **Background**: `#f8f9fa`

### Responsive Map Container
- **Tablet (768-1023px)**:
  - Left: `280px`
  
- **Mobile (max-width: 768px)**:
  - Left: `0`
  - Top: `80px`
  - Bottom: `calc(50vh + 30px)` (50vh for bottom panel + 30px footer)
  - Width: `100vw`
  - Height: `auto`
  
- **Large Desktop (1440px+)**:
  - Left: `350px`

### Map Container Leaflet Styling
- **Height**: `100%`
- **Width**: `100%`
- **Cursor**: `crosshair`

### Leaflet Control Zoom Buttons (Responsive)
- **Desktop**: Default Leaflet sizes
- **Tablet (768-1023px)**: 
  - Width: `36px`
  - Height: `36px`
- **Mobile (max-width: 768px)**:
  - Width: `40px`
  - Height: `40px`
  - Line-height: `40px`
  - Font-size: `20px`

### Leaflet Font Sizes (Responsive)
- **Desktop**: `15px`
- **Tablet**: `14px`
- **Mobile**: `13px`
- **Popup content**: `14px`
- **Attribution**: `10px` (mobile)

---

## 4. BOTTOM PANEL (Chart/Data Panel)

### Desktop Dimensions
- **Position**: `fixed`
- **Bottom**: `30px` (above footer)
- **Left**: `352px` (aligns with map container)
- **Right**: `0`
- **Height**: `330px` (default) / `380px` (state-managed: `panelHeight` variable)
- **Z-Index**: `900`
- **Background**: `white`
- **Border-top**: `1px solid #ddd`
- **Box-shadow**: `0 -2px 5px rgba(0, 0, 0, 0.1)`
- **Transition**: `height 0.3s ease`

### Chart Header
- **Height**: `45px`
- **Display**: `flex`
- **Justify-content**: `space-between`
- **Align-items**: `center`
- **Padding**: `10px 20px`
- **Background**: `#f8f9fa`
- **Border-bottom**: `1px solid #ddd`

### Chart Container
- **Width**: `100%`
- **Height**: `100%`
- **Padding**: `10px 20px`

### Responsive Bottom Panel
- **Tablet (768-1023px)**: Left: `280px`
- **Mobile (max-width: 768px)**:
  - Left: `0`
  - Height: `320px` (smaller on small mobile)
- **Small Mobile (max-width: 575px)**:
  - Height: `320px`
  - Padding: `0 10px 5px 10px`

### Panel Resizing
- **State-managed dimensions**:
  - `panelHeight`: Height of bottom panel (adjustable)
  - `panelWidth`: Width of panel (adjustable)
  - `isResizing`: Boolean flag for resize state
  - `resizeDirection`: Direction of resize (not implemented)
  - `isDragging`: Boolean flag for drag state
  - `dragOffset`: Offset for dragging
  - `panelPosition`: Position of panel (x, y)

---

## 5. FOOTER

### Dimensions
- **Position**: `fixed`
- **Bottom**: `0`
- **Left**: `0`
- **Right**: `0`
- **Height**: `30px`
- **Z-Index**: `1000`
- **Background**: `#034930` (dark green)
- **Color**: `white`
- **Padding**: `0.5rem`
- **Font-size**: `0.9rem`
- **Text-align**: `center`

---

## 6. LEGEND COMPONENTS

### Map Legend (.map-legend)
- **Position**: `fixed` (not absolute)
- **Bottom**: `50px` (above bottom panel/footer area)
- **Left**: `370px` (sidebar 350px + 20px gap)
- **Z-Index**: `1005`
- **Background**: `white`
- **Border-radius**: `8px`
- **Box-shadow**: `0 2px 10px rgba(0,0,0,0.2)`
- **Padding**: `15px`
- **Min-width**: `200px`
- **Max-width**: `300px`
- **Max-height**: `calc(100vh - 200px)`
- **Overflow-y**: `auto`

### Responsive Legend
- **Tablet (768-1023px)**:
  - Bottom: `40px`
  - Left: `290px` (280px sidebar + 10px gap)
  - Max-width: `250px`
  
- **Mobile (max-width: 768px)**:
  - Bottom: `40px`
  - Left: `10px` (left edge)
  - Right: `auto`
  - Max-width: `200px`
  - Font-size: `12px`

- **Small Mobile (max-width: 575px)**:
  - Max-width: `180px`
  - Padding: `10px`
  - Bottom: `40px`
  - Left: `10px`

---

## 7. MODALS AND POPUPS

### Metadata Modal
- **Position**: `fixed`
- **Top**: `150px`
- **Left**: `380px` (sidebar 350px + 30px gap)
- **Width**: `450px`
- **Max-width**: `500px`
- **Max-height**: `80vh`
- **Background**: `white`
- **Padding**: `20px`
- **Border-radius**: `8px`
- **Box-shadow**: `0 5px 15px rgba(0,0,0,0.2)`
- **Z-Index**: `2000`
- **Overflow-y**: `auto`

### Bootstrap Modal Dialog
- **Position**: `fixed`
- **Left**: `370px` (sidebar + gap)
- **Top**: `100px` (below navbar)
- **Width**: `calc(100% - 370px - 40px)`
- **Max-width**: `450px`
- **Z-Index**: `1050`
- **Backdrop**: `rgba(0, 0, 0, 0.3)`

### Responsive Modals
- **Tablet (768-1023px)**:
  - Left: `300px`
  - Width: `calc(100% - 300px - 40px)`
  
- **Mobile (max-width: 768px)**:
  - Left: `20px`
  - Right: `20px`
  - Width: `auto`
  
- **Small Mobile (max-width: 576px)**:
  - Left: `10px`
  - Right: `10px`
  - Max-width: `100%`

### Leaflet Popups
- **Z-Index**: `1010`
- **Max-width**: `350px`
- **Max-height**: `400px`
- **Padding**: `12px 15px`
- **Font-size**: `14px`
- **Border-radius**: `8px`
- **Box-shadow**: `0 3px 14px rgba(0,0,0,0.15)`
- **Overflow-y**: `auto`

---

## 8. MAIN CONTENT AREA

### .main-content
- **Display**: `flex`
- **Flex**: `1`
- **Margin-top**: `80px` (below navbar)
- **Height**: `calc(100vh - 90px)` (total viewport minus navbar + footer)
- **Position**: `relative`

### Responsive Main Content
- **Mobile (max-width: 768px)**:
  - Flex-direction: `column`

---

## 9. OVERALL LAYOUT STRUCTURE (JSX)

```
<div class="map-viewer">
  <div class="sidebar">
    <MuiSidebar />  {/* Left sidebar */}
  </div>
  
  <div class="main-content">
    <div class="map-container">
      <MapContainer>  {/* Leaflet map */}
      </MapContainer>
      <div class="map-legend" />  {/* Legend */}
      <Modal />  {/* Metadata modal */}
    </div>
    
    <div class="bottom-panel">  {/* Chart panel */}
      <div class="chart-header" />
      <div class="chart-container" />
    </div>
  </div>
</div>

<footer class="footer" />  {/* Footer */}
```

---

## 10. RESPONSIVE DESIGN BREAKPOINTS SUMMARY

| Breakpoint | Use Case | Key Changes |
|-----------|----------|------------|
| **1440px+** | Large Desktop | Sidebar: 350px, Map left: 350px |
| **1024px-1439px** | Desktop | Sidebar: 350px, Map left: 352px |
| **768px-1023px** | Tablet | Sidebar: 280px, Navbar: 60px, Map left: 280px |
| **< 768px** | Mobile | Sidebar: 100% (bottom sheet), Map: full width, Bottom panel: 50vh |
| **< 576px** | Small Mobile | Reduced margins, compressed layout |
| **< 480px** | Extra Small | Minimum spacing, logo: 35px |

---

## 11. STATE-MANAGED DIMENSIONS (Component State Variables)

### Chart/Panel State
```javascript
panelHeight = 380px      // Height of bottom panel
panelWidth = 600px       // Width of panel (not actively used in CSS)
panelPosition = {x, y}   // Position for dragging (dynamically calculated)
isResizing = boolean     // Flag for resize operation
isDragging = boolean     // Flag for drag operation
showChart = boolean      // Visibility toggle
```

### Layout State
```javascript
isMobile = window.innerWidth < 768    // Mobile detection
mapKey = number                        // Cache busting for map re-renders
isSidebarActive = boolean              // Sidebar toggle state
```

---

## 12. CSS COLOR SCHEME

| Element | Color | Hex |
|---------|-------|-----|
| Navbar/Footer | Dark Green | `#034930` |
| Sidebar Border | Light Gray | `#d0d0d0` |
| Sidebar Background | White | `#ffffff` |
| Map Background | Light Gray | `#f8f9fa` |
| Accent (Hover) | Golden | `#FFC107` |
| Text Primary | Dark | `#333` |
| Text Secondary | Gray | `#666` |
| Border | Light Gray | `#e9ecef` |
| Alert | Yellow | `#FFD700` |
| Alarm | Orange | `#FFA500` |
| Emergency | Red | `#FF0000` |

---

## 13. Z-INDEX STACKING ORDER (from lowest to highest)

1. **1**: Map Container
2. **40-44**: Boundary Layers (Rivers, Admin boundaries, Lakes)
3. **100**: Impact/IBEW WMS Layers
4. **900**: Bottom Panel (Charts)
5. **998**: Sidebar
6. **999**: Sidebar Tabs
7. **1000**: Navbar, Footer, Notifications
8. **1002**: Toggle Labels
9. **1005**: Map Legend
10. **1010**: Leaflet Popups
11. **1050**: Bootstrap Modals
12. **1999**: Modal Backdrop
13. **2000**: Metadata Modal

---

## 14. KEY DYNAMIC SIZING LOGIC

### Map Container Bottom Position
The map container's bottom position is dynamically calculated:
```javascript
bottom: showChart ? `${panelHeight + 30}px` : '30px'
// Default: 30px (footer only)
// With chart: panelHeight (380px) + footer (30px) = 410px
```

### Navbar Alignment
The navbar navigation links include left margin to align with sidebar:
```css
margin-left: 352px;  /* Aligns navigation with map area after sidebar */
```

### Map Height Calculation
Mobile map container height dynamically adjusts:
```css
bottom: calc(50vh + 30px);  /* 50% viewport height for bottom panel + footer */
```

---

## 15. IMPORTANT NOTES

1. **Fixed Positioning**: Most UI components (navbar, sidebar, map, footer, legend, bottom panel) use `position: fixed` or `position: absolute`, which creates a complex stacking context.

2. **Sidebar Width Alignment**: The sidebar width (350px) is referenced in multiple places:
   - Map container left offset: 352px (350px + 2px border)
   - Legend position: 370px (350px + 20px gap)
   - Modal position: 370px (350px + 20px gap)

3. **Mobile Transformation**: On mobile (< 768px), the layout shifts from a side-by-side configuration to a stacked configuration using:
   - MUI's responsive Bottom Sheet component for sidebar
   - Full-width map container
   - 50% viewport height bottom panel

4. **Responsive Patterns**:
   - Desktop/Tablet: Sidebar on left, map takes remaining space
   - Mobile: Full-width layout with bottom sheet overlaying the map

5. **Chart Panel State Management**: The bottom panel height and position are controlled by component state, allowing users to potentially resize or drag it (though drag functionality may not be fully implemented).

6. **Container Viewport Coverage**:
   - Total height: `100vh` (full viewport)
   - Navbar: `80px`
   - Sidebar: `100vh - 80px` = `920px` (on 1080px viewport)
   - Map: Full remaining area
   - Footer: `30px` (fixed at bottom)
   - Bottom Panel: `330px` (overlays map, above footer)

---

## 16. ANIMATION AND TRANSITIONS

```css
/* Sidebar smooth transitions */
transition: right 0.3s ease;

/* Bottom panel resizing */
transition: height 0.3s ease;

/* Logo scaling on breakpoints */
transition: height 0.3s ease;

/* Navigation link hover effects */
transition: all 0.3s ease;

/* Modal fade effect */
transition: opacity 0.3s ease-out;

/* Layer control panel slide */
transition: right 0.3s ease;

/* Toggle switch animation */
transition: .4s;

/* UI element interactions */
transition: all 0.2s ease;
```

