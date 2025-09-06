import React, { useCallback, useState, useEffect } from 'react';
import { useMap, useMapEvents, Popup } from 'react-leaflet';

// Configuration for available IBEW layers - maps dynamic to static names
const IBEW_LAYER_CONFIG = [
  { layer: "healthtot_%date%", name: "Health Facilities Affected", staticPrefix: "healthtot" },
  { layer: "popaff100_%date%", name: "People Affected (100cm)", staticPrefix: "popaff100" },
  { layer: "popaff25_%date%", name: "People Affected (25cm)", staticPrefix: "popaff25" },
  { layer: "popafftot_%date%", name: "Total People Affected", staticPrefix: "popafftot" },
  { layer: "popage100_%date%", name: "Vulnerable Age Groups (100cm)", staticPrefix: "popage100" },
  { layer: "popage25_%date%", name: "Vulnerable Age Groups (25cm)", staticPrefix: "popage25" },
  { layer: "popmob100_%date%", name: "Reduced Mobility (100cm)", staticPrefix: "popmob100" },
  { layer: "popmob25_%date%", name: "Reduced Mobility (25cm)", staticPrefix: "popmob25" },
];

// Debug component to handle feature info clicks
const FeatureInfoHandler = ({ selectedLayers, onFeatureInfo, selectedDate, mapConfig }) => {
  const map = useMap();
  
  useMapEvents({
    click: async (e) => {
      console.log('=== DEBUG: Click Event ===');
      console.log('1. Click coordinates:', e.latlng);
      console.log('2. Selected date:', selectedDate);
      console.log('3. All selected layers:', Array.from(selectedLayers));
      console.log('4. IBEW_LAYER_CONFIG:', IBEW_LAYER_CONFIG);
      
      if (!map || !selectedLayers || selectedLayers.size === 0) {
        console.log('5. No map or selected layers, returning');
        return;
      }
      
      // Get IBEW layers that are currently selected and convert to static layer names
      const selectedIBEWLayers = Array.from(selectedLayers).map(layerId => {
        console.log(`6. Checking layer: ${layerId}`);
        
        // Try to find exact match first
        let config = IBEW_LAYER_CONFIG.find(c => c.layer === layerId);
        
        // If no exact match, try to find by checking if layerId contains the static prefix
        if (!config) {
          config = IBEW_LAYER_CONFIG.find(c => 
            layerId.includes(c.staticPrefix) || 
            c.staticPrefix.includes(layerId.replace('%date%', '').replace('_%date%', ''))
          );
        }
        
        if (config && selectedDate) {
          const formattedDate = selectedDate.replace(/-/g, ''); // 2025-06-24 -> 20250624
          const staticLayerName = `${config.staticPrefix}_${formattedDate}`;
          console.log(`7. Mapped ${layerId} -> ${staticLayerName}`);
          return staticLayerName;
        } else {
          console.log(`8. No config found for layer: ${layerId}`);
          return null;
        }
      }).filter(Boolean);
      
      console.log('9. Resolved static layer names:', selectedIBEWLayers);
      
      if (selectedIBEWLayers.length === 0) {
        console.log('10. No IBEW layers selected, returning');
        return;
      }
      
      // Get map bounds and size for proper coordinate transformation
      const bounds = map.getBounds();
      const size = map.getSize();
      const point = map.latLngToContainerPoint(e.latlng);
      
      // Create proper bbox string (west,south,east,north)
      const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
      
      console.log('11. Map parameters:', {
        point: { x: point.x, y: point.y },
        size: { width: size.x, height: size.y },
        bbox: bbox,
        bounds: {
          west: bounds.getWest(),
          south: bounds.getSouth(), 
          east: bounds.getEast(),
          north: bounds.getNorth()
        }
      });
      
      // Use the static GetFeatureInfo mapfile - construct base URL without map parameter
      const baseUrl = mapConfig.mapserverWMSUrl.split('?')[0]; // Get just the CGI URL
      const getFeatureInfoUrl = baseUrl;
      
      console.log('12. GetFeatureInfo base URL:', getFeatureInfoUrl);
      
      // Collect all results
      const allResults = [];
      
      for (const staticLayerName of selectedIBEWLayers) {
        console.log(`\n13. Processing layer: ${staticLayerName}`);
        
        // Build GetFeatureInfo URL for static layers
        const params = new URLSearchParams({
          map: "/etc/mapserver/ibew_getfeatureinfo.map",
          SERVICE: "WMS",
          VERSION: "1.1.0",
          REQUEST: "GetFeatureInfo",
          QUERY_LAYERS: staticLayerName,
          LAYERS: staticLayerName,
          INFO_FORMAT: "text/plain",
          X: Math.round(point.x).toString(),
          Y: Math.round(point.y).toString(),
          WIDTH: size.x.toString(),
          HEIGHT: size.y.toString(),
          BBOX: bbox,
          SRS: "EPSG:4326",
          FEATURE_COUNT: "10"
        });

        const requestUrl = `${getFeatureInfoUrl}?${params.toString()}`;
        console.log('14. Full request URL:', requestUrl);
        
        try {
          const response = await fetch(requestUrl);
          const responseText = await response.text();
          
          console.log('15. Response status:', response.status);
          console.log('16. Response text:', responseText);

          if (response.ok && responseText && !responseText.includes('ServiceException') && !responseText.includes('Search returned no results')) {
            // Parse the GetFeatureInfo response
            const features = parseGetFeatureInfoResponse(responseText);
            
            // Find the original layer config for display name
            const layerConfig = IBEW_LAYER_CONFIG.find(config => 
              staticLayerName.startsWith(config.staticPrefix)
            );
            
            // Always show features if we got valid data, even if flood_tot is 0
            if (features.length > 0) {
              allResults.push({
                layerName: layerConfig?.name || staticLayerName,
                staticLayerName: staticLayerName,
                features: features
              });
              console.log(`17. Added ${features.length} features for layer ${staticLayerName}`);
            } else {
              console.log(`18. No features parsed for layer ${staticLayerName}`);
            }
          } else {
            console.log(`19. Invalid response for layer ${staticLayerName}: ${responseText.substring(0, 100)}`);
          }
        } catch (error) {
          console.error(`20. Error fetching layer ${staticLayerName}:`, error);
        }
      }
      
      console.log('21. All results:', allResults);
      
      // Display results
      if (allResults.length > 0) {
        onFeatureInfo({
          position: e.latlng,
          results: allResults,
          selectedDate: selectedDate
        });
      } else {
        // Show helpful message when clicking but no flood data found
        console.log('22. No flood data found, showing helpful message');
        onFeatureInfo({
          position: e.latlng,
          results: [{
            layerName: "No Flood Data",
            features: [{
              properties: {
                message: "No flood impact data at this location",
                hint: "Try clicking on areas where you can see colored flood impacts on the map",
                coordinates: `${e.latlng.lat.toFixed(4)}°N, ${e.latlng.lng.toFixed(4)}°E`,
                selectedDate: selectedDate
              }
            }]
          }],
          selectedDate: selectedDate
        });
      }
    },
  });
  
  return null;
};

// Parse GetFeatureInfo text/plain response
function parseGetFeatureInfoResponse(responseText) {
  const features = [];
  const lines = responseText.split('\n');
  let currentFeature = null;
  
  for (const line of lines) {
    const trimmedLine = line.trim();
    
    // Skip empty lines and headers
    if (!trimmedLine || trimmedLine.startsWith('GetFeatureInfo results') || trimmedLine.startsWith('Layer \'')) {
      continue;
    }
    
    // Check for feature start (Feature N:)
    if (trimmedLine.match(/Feature \d+:/)) {
      // Save previous feature if it exists and has properties
      if (currentFeature && Object.keys(currentFeature.properties).length > 0) {
        features.push(currentFeature);
      }
      currentFeature = {
        id: trimmedLine,
        properties: {}
      };
    }
    // Parse attribute lines (key = value format)
    else if (trimmedLine.includes('=') && currentFeature) {
      const [key, ...valueParts] = trimmedLine.split('=');
      const value = valueParts.join('=').trim().replace(/^['"]|['"]$/g, '');
      if (key && value !== undefined) {
        currentFeature.properties[key.trim()] = value;
      }
    }
  }
  
  // Add the last feature
  if (currentFeature && Object.keys(currentFeature.properties).length > 0) {
    features.push(currentFeature);
  }
  
  return features;
}

// Enhanced Popup component
const IBEWPopup = ({ popupData, onClose }) => {
  if (!popupData) return null;
  
  const formatValue = (key, value) => {
    if (!value || value === 'null' || value === '') {
      return 'No data';
    }
    
    // Special formatting for known fields
    if (key === 'flood_tot' || key === 'pop_tot') {
      const numValue = parseFloat(value);
      if (!isNaN(numValue)) {
        if (numValue === 0) return '0';
        if (numValue < 1) return numValue.toFixed(3);
        return Math.round(numValue).toLocaleString();
      }
    }
    
    if (key === 'flood_perc') {
      const numValue = parseFloat(value);
      if (!isNaN(numValue)) {
        return `${(numValue * 100).toFixed(2)}%`;
      }
    }
    
    return value;
  };
  
  const getImpactColor = (floodTot) => {
    const value = parseFloat(floodTot);
    if (isNaN(value) || value === 0) return '#28a745'; // Green for no impact
    if (value <= 100) return '#ffc107'; // Yellow for low impact
    if (value <= 1000) return '#fd7e14'; // Orange for medium impact
    return '#dc3545'; // Red for high impact
  };
  
  return (
    <Popup
      position={popupData.position}
      onClose={onClose}
      maxWidth={450}
      minWidth={350}
    >
      <div style={{ fontFamily: 'Arial, sans-serif', fontSize: '15px', lineHeight: '1.4' }}>
        <h4 style={{ 
          margin: '0 0 15px 0',
          fontSize: '18px',
          fontWeight: 'bold',
          color: '#1B6840',
          borderBottom: '2px solid #1B6840',
          paddingBottom: '8px'
        }}>
          Flood Impact Information
        </h4>
        
        {popupData.selectedDate && (
          <div style={{ 
            marginBottom: '12px',
            padding: '8px 12px',
            backgroundColor: '#f0f8ff',
            borderRadius: '5px',
            fontSize: '14px',
            fontWeight: 'bold'
          }}>
            <strong>Date:</strong> {popupData.selectedDate}
          </div>
        )}
        
        {popupData.results.map((result, idx) => (
          <div key={idx} style={{ marginBottom: '15px' }}>
            <h5 style={{ 
              margin: '0 0 12px 0',
              fontSize: '16px',
              fontWeight: 'bold',
              color: '#333'
            }}>
              {result.layerName}
            </h5>
            
            {result.features.map((feature, fIdx) => {
              const floodTot = feature.properties.flood_tot || '0';
              const impactColor = getImpactColor(floodTot);
              
              // Calculate visible properties count dynamically
              const visibleProperties = Object.entries(feature.properties)
                .filter(([key]) => {
                  // For popafftot layer, show all properties in "View all properties"
                  if (result.staticLayerName && result.staticLayerName.includes('popafftot')) {
                    return true; // Show all properties for popafftot
                  }
                  // For other layers, only hide administrative fields, show all data fields
                  return !['NAME_0', 'NAME_1', 'CODE_ADM', 'GID_0', 'ENGTYPE_1', 'COD'].includes(key);
                });
              
              return (
                <div key={fIdx} style={{ 
                  marginBottom: '10px',
                  padding: '10px',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '4px',
                  borderLeft: `4px solid ${impactColor}`
                }}>
                  {feature.properties.message ? (
                    <div>
                      <p style={{ margin: '0 0 8px 0', fontWeight: 'bold', fontSize: '15px' }}>
                        {feature.properties.message}
                      </p>
                      {feature.properties.hint && (
                        <p style={{ margin: '0 0 8px 0', fontSize: '13px', fontStyle: 'italic', color: '#666' }}>
                          {feature.properties.hint}
                        </p>
                      )}
                      {feature.properties.coordinates && (
                        <p style={{ margin: '0', fontSize: '13px', color: '#888', fontWeight: 'bold' }}>
                          📍 {feature.properties.coordinates}
                        </p>
                      )}
                    </div>
                  ) : (
                    <>
                      {/* Location Info */}
                      {(feature.properties.NAME_0 || feature.properties.NAME_1) && (
                        <div style={{ marginBottom: '10px', fontSize: '15px', fontWeight: 'bold', color: '#2c3e50' }}>
                          📍 {[feature.properties.NAME_1, feature.properties.NAME_0]
                            .filter(Boolean)
                            .join(', ')}
                        </div>
                      )}
                      
                      {/* Dynamic Key Metrics - Show the most relevant properties for each layer */}
                      {(() => {
                        const props = feature.properties;
                        const entries = Object.entries(props);
                        
                        // Special handling for Total People Affected layer - only show pop_tot and flood_tot
                        let importantProps;
                        if (result.staticLayerName && result.staticLayerName.includes('popafftot')) {
                          // For Total People Affected, only show pop_tot and flood_tot attributes
                          importantProps = entries.filter(([key, value]) => {
                            const numValue = parseFloat(value);
                            return !isNaN(numValue) && (key === 'pop_tot' || key === 'flood_tot');
                          });
                        } else {
                          // For other layers, find the most important numeric properties (excluding administrative fields)
                          importantProps = entries.filter(([key, value]) => {
                            const numValue = parseFloat(value);
                            return !isNaN(numValue) && 
                                   !['LACK_CC', 'GID_0'].includes(key) &&
                                   !key.startsWith('NAME_') &&
                                   !key.startsWith('CODE_') &&
                                   !key.startsWith('ENGTYPE_') &&
                                   !key.startsWith('COD');
                          }).slice(0, 4); // Show top 4 important metrics
                        }
                        
                        if (importantProps.length === 0) return null;
                        
                        return (
                          <div style={{ 
                            display: 'grid', 
                            gridTemplateColumns: importantProps.length <= 2 ? '1fr 1fr' : '1fr 1fr 1fr 1fr',
                            gap: '6px',
                            marginBottom: '8px'
                          }}>
                            {importantProps.map(([key, value]) => {
                              // Color coding based on key type - using colors that contrast well
                              let bgColor = '#495057'; // Dark gray default
                              if (key.includes('flood')) bgColor = getImpactColor(value);
                              else if (key.includes('pop')) bgColor = '#2c3e50'; // Dark blue-gray
                              else if (key.includes('health')) bgColor = '#8b4513'; // Saddle brown  
                              else if (key.includes('tot_')) bgColor = '#4a4a4a'; // Dark gray
                              else if (key.includes('perc')) bgColor = '#5a5a5a'; // Medium gray
                              
                              return (
                                <div key={key} style={{ 
                                  padding: '8px',
                                  backgroundColor: bgColor,
                                  color: 'white',
                                  borderRadius: '4px',
                                  textAlign: 'center',
                                  fontSize: '11px',
                                  fontWeight: 'bold'
                                }}>
                                  <div style={{ fontSize: '10px', opacity: 0.9, marginBottom: '2px' }}>
                                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                  </div>
                                  <div style={{ fontWeight: 'bold', fontSize: '13px' }}>
                                    {formatValue(key, value)}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        );
                      })()}
                      
                      {/* Flood Percentage and Classification - Only show if they exist and not for popafftot */}
                      {(() => {
                        // Skip flood percentage and class for Total People Affected layer
                        if (result.staticLayerName && result.staticLayerName.includes('popafftot')) {
                          return null;
                        }
                        
                        const props = feature.properties;
                        const additionalMetrics = [];
                        
                        if (props.flood_perc !== undefined && props.flood_perc !== '0.000000000000000') {
                          additionalMetrics.push(['flood_perc', props.flood_perc, '#495057', 'Flood %']);
                        }
                        if (props.flood_clas !== undefined && props.flood_clas !== '0') {
                          additionalMetrics.push(['flood_clas', props.flood_clas, '#343a40', 'Flood Class']);
                        }
                        
                        if (additionalMetrics.length === 0) return null;
                        
                        return (
                          <div style={{ 
                            display: 'grid', 
                            gridTemplateColumns: additionalMetrics.length === 1 ? '1fr' : '1fr 1fr',
                            gap: '8px',
                            marginBottom: '8px'
                          }}>
                            {additionalMetrics.map(([key, value, color, label]) => (
                              <div key={key} style={{ 
                                padding: '8px',
                                backgroundColor: color,
                                color: 'white',
                                borderRadius: '4px',
                                textAlign: 'center',
                                fontWeight: 'bold'
                              }}>
                                <div style={{ fontSize: '12px', marginBottom: '2px' }}>{label}</div>
                                <div style={{ fontWeight: 'bold', fontSize: '14px' }}>
                                  {formatValue(key, value)}
                                </div>
                              </div>
                            ))}
                          </div>
                        );
                      })()}
                      
                      {/* Other Properties - Enhanced Formatting with Dynamic Count */}
                      <details style={{ marginTop: '10px' }}>
                        <summary style={{ 
                          cursor: 'pointer', 
                          fontSize: '14px',
                          color: '#007bff',
                          marginBottom: '8px',
                          fontWeight: 'bold'
                        }}>
                          📋 View all properties ({visibleProperties.length})
                        </summary>
                        <div style={{ 
                          marginTop: '8px',
                          fontSize: '13px',
                          maxHeight: '300px',
                          overflowY: 'auto',
                          backgroundColor: '#fafafa',
                          border: '1px solid #e0e0e0',
                          borderRadius: '4px',
                          padding: '8px'
                        }}>
                          {visibleProperties.map(([key, value]) => (
                            <div key={key} style={{ 
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '8px 10px',
                              marginBottom: '3px',
                              backgroundColor: 'white',
                              borderRadius: '4px',
                              border: '1px solid #f0f0f0',
                              boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                            }}>
                              <span style={{ 
                                fontWeight: 'bold',
                                color: '#495057',
                                textTransform: 'none',
                                fontSize: '12px',
                                flex: '0 0 40%',
                                wordBreak: 'break-word'
                              }}>
                                {key}:
                              </span>
                              <span style={{ 
                                color: '#6c757d',
                                fontSize: '12px',
                                flex: '1',
                                textAlign: 'right',
                                fontFamily: 'monospace',
                                wordBreak: 'break-word',
                                paddingLeft: '8px',
                                fontWeight: 'bold'
                              }}>
                                {value || 'N/A'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </details>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </Popup>
  );
};

// Main component
const IBEWPopupHandler = ({ selectedLayers, selectedDate, mapConfig }) => {
  const [popupData, setPopupData] = useState(null);
  
  useEffect(() => {
    // Clear popup when layers or date changes
    setPopupData(null);
  }, [selectedLayers, selectedDate]);
  
  const handleFeatureInfo = useCallback((data) => {
    setPopupData(data);
  }, []);
  
  const handlePopupClose = useCallback(() => {
    setPopupData(null);
  }, []);
  
  return (
    <>
      <FeatureInfoHandler
        selectedLayers={selectedLayers}
        onFeatureInfo={handleFeatureInfo}
        selectedDate={selectedDate}
        mapConfig={mapConfig}
      />
      {popupData && (
        <IBEWPopup
          popupData={popupData}
          onClose={handlePopupClose}
        />
      )}
    </>
  );
};

export { IBEW_LAYER_CONFIG };
export default IBEWPopupHandler;