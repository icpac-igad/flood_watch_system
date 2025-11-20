# MapViewer Layout - Quick Reference Guide

## Essential Measurements at a Glance

### Fixed Offsets (Key for positioning)
- **Navbar height**: 80px (desktop) / 60px (tablet)
- **Sidebar width**: 350px (desktop) / 280px (tablet) / 100% (mobile)
- **Map left offset**: 352px (desktop) / 280px (tablet) / 0 (mobile)
- **Footer height**: 30px (always fixed at bottom)
- **Bottom panel height**: 330px default, up to 380px (state-managed)

### Component Positioning Formula
```
Map Container Bottom = panelHeight + 30px (when chart is shown)
Legend Left Position = Sidebar Width + 20px
Legend Bottom Position = 50px (desktop) / 40px (tablet/mobile)
Modal Dialog Left = Sidebar Width + 20px
```

### Mobile Responsive Pattern
On mobile (< 768px), the layout shifts from **sidebar-left** to **bottom-sheet**:
- Sidebar becomes an MUI BottomSheet component
- Map takes full width (100vw)
- Bottom panel height set to 50vh
- Legend repositioned to left: 10px (left edge)

---

## CSS Class Names to Know

### Layout Containers
- `.map-viewer` - Main wrapper for the entire map interface
- `.main-content` - Container for map and chart areas
- `.map-container` - Fixed position map area
- `.sidebar` - Left sidebar (fixed position on desktop)
- `.bottom-panel` - Chart/data display panel (fixed position)

### Navigation & UI
- `.navbar-custom` - Top navigation bar
- `.nav-tabs` - Tab navigation container
- `.tab-link` - Individual tab button
- `.footer` - Bottom footer bar

### Map & Legend
- `.leaflet-container` - Leaflet map container
- `.map-legend` - Legend box for layer information
- `.leaflet-popup` - Popup markers on map

### Sidebar Content
- `.tab-pane` - Tab content area
- `.toggle-switch-small` - Layer visibility toggles
- `.layer-content` - Layer item container

### Modals
- `.modal` - Bootstrap modal wrapper
- `.modal-dialog` - Modal dialog box
- `.metadata-modal` - Custom metadata modal

---

## Responsive Breakpoints Quick Reference

```css
/* Mobile first approach */
< 480px      /* Extra small phones - minimum styling */
480px-768px  /* Phones - Logo: 40px, buttons: 44px min */
768px-1023px /* Tablets - Sidebar: 280px, Navbar: 60px */
1024px+      /* Desktop - Full layout with 350px sidebar */
1440px+      /* Large desktop - Optimized spacing */
```

---

## State Variables That Affect Layout

### In MapViewer Component
```javascript
// Mobile detection
isMobile = window.innerWidth < 768

// Chart panel sizing
panelHeight = 380px    // Height of bottom chart panel
panelWidth = 600px     // Width (for potential future drag)
showChart = boolean    // Controls visibility

// Sidebar state
isSidebarActive = boolean  // Toggle sidebar visibility
mapKey = number            // Cache busting for map re-renders

// Position for dragging (future enhancement)
panelPosition = {x: number, y: number}
isDragging = boolean
isResizing = boolean
```

### How Layout Responds to State
When `showChart` is true:
- Bottom margin of map: `panelHeight + 30px`
- Bottom panel becomes visible
- Chart data loads and displays

When `isMobile` is true:
- Sidebar becomes position: initial (not fixed)
- Map takes 100% width
- Legend repositions to left: 10px
- All components use mobile-optimized sizes

---

## Layer Ordering (Z-Index Stack)

| Priority | Component | Z-Index | Notes |
|----------|-----------|---------|-------|
| 1 | Map (background) | 1 | Lowest - base layer |
| 2 | Boundary layers | 40-44 | Rivers, admin boundaries |
| 3 | Data layers | 100 | Impact, IBEW, WMS layers |
| 4 | Chart panel | 900 | Over map, under everything else |
| 5 | Sidebar | 998 | Left panel |
| 6 | Sidebar tabs | 999 | Tab navigation bar |
| 7 | Navbar/Footer | 1000 | Top and bottom bars |
| 8 | Map legend | 1005 | Legend box |
| 9 | Map popups | 1010 | Marker information popups |
| 10 | Modals | 1050+ | Dialog boxes (highest on top) |

---

## How to Find/Edit These Dimensions

### CSS Files
- **Main styles**: `/frontend/src/App.css`
- Global styles: `/frontend/src/index.css`
- Component styles: Inline in JSX or dedicated CSS files

### Component Files
- **MapViewer**: `/frontend/src/components/pages/MapViewer.jsx`
- **Sidebar**: `/frontend/src/components/layout/MuiSidebar.jsx`
- **Legend**: `/frontend/src/components/map/MapLegends.jsx`
- **Config**: `/frontend/src/config/layers.js`

### Key CSS Selectors to Find
```css
.navbar-custom        /* Top bar styling */
.sidebar              /* Left panel styling */
.map-container        /* Map area styling */
.bottom-panel         /* Chart area styling */
.footer               /* Bottom bar styling */
.map-legend           /* Legend box styling */
@media (max-width: 768px) /* Mobile overrides */
```

---

## Common Layout Issues & Solutions

### Issue: Elements overlapping on desktop
**Solution**: Check the z-index stack. Refer to layer ordering table above.

### Issue: Mobile layout broken
**Solution**: Verify the `isMobile` media query breakpoint (768px). Mobile-specific CSS uses:
```css
@media (max-width: 767.98px) { /* Mobile overrides */ }
```

### Issue: Map doesn't fill the space
**Solution**: Ensure `.map-container` has:
```css
position: fixed;
left: [sidebar width + border];
right: 0;
top: 80px;
bottom: [panelHeight + 30px or 30px];
```

### Issue: Chart panel position wrong
**Solution**: Check the `panelHeight` state variable and this CSS rule:
```javascript
style={{
  bottom: showChart ? `${panelHeight + 30}px` : '30px'
}}
```

### Issue: Legend or modal outside viewport
**Solution**: Verify positioning - all fixed elements should account for:
- Navbar (80px from top on desktop)
- Sidebar width (350px on desktop)
- Footer (30px from bottom)

---

## Touch & Accessibility Notes

### Mobile Touch Targets
The app enforces minimum touch target sizes for accessibility:
```css
/* From App.css mobile breakpoint */
.btn, button              { min-height: 44px !important; }
.toggle-switch-small      { transform: scale(1.3); }
input[type="date"], select { min-height: 44px !important; }
.info-icon                { width: 44px; height: 44px; }
```

### Font Sizes (Responsive)
- **Desktop**: 16px base, 15px controls
- **Tablet**: 14px controls
- **Mobile**: 13px minimum, 16px for form inputs

### Leaflet Controls (Responsive)
- **Desktop**: Default sizes
- **Tablet**: 36x36px zoom buttons
- **Mobile**: 40x40px touch-friendly buttons

---

## Color Reference

### Theme Colors
```
Primary (Dark Green):    #034930    /* Used in navbar, footer, accents */
Success/Positive:        #388e3c    /* Low impact */
Warning/Alert:           #FFD700    /* Alert threshold */
Secondary/Alarm:         #FFA500    /* Alarm threshold */
Error/Emergency:         #FF0000    /* Emergency threshold */
Light:                   #f8f9fa    /* Backgrounds */
White:                   #ffffff    /* Panels */
Gray:                    #d0d0d0    /* Borders */
Dark Gray:               #333       /* Text */
```

### Apply Theme Color
```css
/* Navigation bar */
.navbar-custom, .footer {
  background-color: #034930;
}

/* Hover/Active states */
a:hover, .active {
  color: #FFC107;
}

/* Sidebar */
.sidebar {
  background-color: #ffffff;
  border-right: 2px solid #d0d0d0;
}
```

---

## Performance Considerations

### Layout Efficiency
1. **Fixed positioning**: Most components use `position: fixed` for performance
2. **Transform offsets**: Use `left`, `right`, `top`, `bottom` for better GPU acceleration
3. **Media queries**: Separate mobile styles in dedicated breakpoints

### Responsive Optimization
1. **Desktop** (1024px+): Full sidebar + map layout
2. **Tablet** (768px-1023px): Narrower sidebar (280px)
3. **Mobile** (<768px): Full-screen with bottom sheet

### State Management
- `panelHeight` is state-managed for potential user resizing
- `isMobile` is computed on window resize
- `mapKey` forces React re-render for map updates

---

## Migration/Changes Guide

### If changing Sidebar Width
Update these places:
1. `.sidebar { width: 350px; }` 
2. `.map-container { left: 352px; }` (width + 2px border)
3. `.map-legend { left: 370px; }` (width + 20px)
4. `.modal-dialog { left: 370px; }` (width + 20px)
5. `.navbar-custom .navbar-nav { margin-left: 352px; }`

### If changing Navbar Height
Update these places:
1. `.navbar-custom { min-height: 80px; }`
2. `.main-content { margin-top: 80px; }`
3. `.sidebar { top: 80px; height: calc(100vh - 80px); }`
4. `.sidebar-tabs { top: 80px; }`
5. `.map-container { top: 80px; }`
6. All responsive breakpoints that reference navbar height

### If changing Footer Height
Update these places:
1. `.footer { height: 30px; }`
2. `.main-content { height: calc(100vh - 90px); }` (80px navbar + 30px footer)
3. `.map-container { bottom: 30px; }` or `bottom: calc(${panelHeight}px + 30px);`
4. `.bottom-panel { bottom: 30px; }`

---

## Testing Responsive Layout

### Browser DevTools Viewport Sizes to Test
```
Extra Small: 320px  (iPhone SE)
Small:       480px  (iPhone 12)
Tablet:      768px  (iPad)
Landscape:   1024px (iPad Landscape)
Desktop:     1440px (Common laptop)
```

### Manual Testing Checklist
- [ ] Navbar doesn't hide content at all breakpoints
- [ ] Sidebar aligns properly on desktop/tablet
- [ ] Map fills available space
- [ ] Legend doesn't overlap important content
- [ ] Bottom chart panel appears when needed
- [ ] All buttons/inputs meet 44px minimum touch target
- [ ] Font sizes are readable (16px minimum for inputs)
- [ ] Mobile bottom sheet slides properly
- [ ] Modals position correctly relative to sidebar
- [ ] Footer stays at bottom on all views

