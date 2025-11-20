import React, { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  MapContainer,
  TileLayer,
  WMSTileLayer,
  useMapEvents,
  useMap,
  LayersControl,
  GeoJSON,
  LayerGroup,
  ZoomControl,
} from "react-leaflet";
import MarkerClusterGroup from 'react-leaflet-markercluster';
import { List, ListItem, Dialog, DialogTitle, DialogContent, DialogActions, Button, Box, useMediaQuery, useTheme, Switch, IconButton, Typography, CircularProgress, Fab } from "@mui/material";
import MenuIcon from '@mui/icons-material/Menu';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faWater, faExclamationTriangle } from '@fortawesome/free-solid-svg-icons';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { TextField, FormControl, InputLabel, Select, MenuItem } from '@mui/material';
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "leaflet.vectorgrid"; // Import vectorgrid for TiPg layers
// Bootstrap CSS removed - using MUI instead
import L from "leaflet";
import { DischargeChart, GeoSFMChart, EnsembleForecastChart } from "../../utils/chartUtils.jsx";
import IBEWPopupHandler from "../../utils/IBEWPopupHandler.jsx";
import { MuiSidebar } from "../layout/MuiSidebar.jsx";
import { fetchWithTiming } from "../../utils/apiLogger";
import { forecastCache } from "../../services/cacheService";
import { AlertStatusLegend, MapLegend, MultimodalLegend } from "../map/MapLegends.jsx";

// TEST: Import new modular hooks
import { useAvailableDates } from "../../hooks/useAvailableDates";
import { LayerSelector } from "../map/LayerSelector";
import { StableWMSLayer } from "../map/StableWMSLayer";
// Legends removed - only show for point data
// import RiverLegend from "../map/RiverLegend";
// import Admin0Legend from "../map/Admin0Legend";
// import LakesLegend from "../map/LakesLegend";
// @ts-ignore
import { CountryMask } from "../map/CountryMask.tsx";
// @ts-ignore
import { CountryZoomHandler } from "../map/CountryZoomHandler.tsx";
import {
  MAP_CONFIG,
  API_BASE_URL,
  FASTAPI_BASE_URL,
  MONITORING_STATIONS_CONFIG,
  GEOFSM_CONFIG,
  createWMSLayer,
  IMPACT_LAYERS,
  IBEW_LAYERS,
  BOUNDARY_LAYERS,
  BASE_MAPS
} from "../../config/layers";
import { getAlertStatus } from "../../utils/map/alertStatus";
import { formatLayerIdWithDate, handleLayerError } from "../../utils/map/layerHelpers";
import { getMarkerIcon } from "../../utils/map/markerIcons";
// @ts-ignore
import { getCountryBounds, extractCountriesFromAdminData, filterPointsByCountry } from "../../utils/map/countryFilter.ts";
// @ts-ignore
import { createHexbins, getHexagonStyle } from "../../utils/map/hexbinUtils.ts";
import { InfoIcon } from "../ui/InfoIcon";
import { MetadataModal } from "../ui/MetadataModal";
import { useEnsembleData } from "../../hooks/useEnsembleData";
// @ts-ignore
import { EnsembleLayer } from "../map/layers/EnsembleLayer.tsx";
// @ts-ignore
import { TiPgVectorLayer } from "../map/layers/TiPgVectorLayer.tsx";

// Fix Leaflet default icon issue
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
import iconRetina from 'leaflet/dist/images/marker-icon-2x.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: iconRetina,
  iconUrl: icon,
  shadowUrl: iconShadow,
});

// Add CSS styles for blinking animation
const style = document.createElement('style');
style.innerHTML = `
  @keyframes blink-warning {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  
  @keyframes blink-alarm {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
  
  @keyframes blink-emergency {
    0%, 100% { opacity: 1; }
    25% { opacity: 0.2; }
    50% { opacity: 1; }
    75% { opacity: 0.2; }
  }
  
  .marker-warning, .cluster-warning {
    animation: blink-warning 2s infinite;
  }
  
  .marker-alarm, .cluster-alarm {
    animation: blink-alarm 1.5s infinite;
  }
  
  .marker-emergency, .cluster-emergency {
    animation: blink-emergency 1s infinite;
  }
  
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);

// Component for the unified sidebar (removed tabs)
const TabSidebar = ({
  hazardLayers,
  impactLayers,
  ibewLayers,
  boundaryLayers,
  selectedLayers,
  selectedBoundaryLayers,
  onLayerSelect,
  onBoundaryLayerSelect,
  showMonitoringStations,
  setShowMonitoringStations,
  showGeoFSM,
  setShowGeoFSM,
  geoFSMLoading,
  selectedStation,
  showMikeHydro,
  setShowMikeHydro,
  showFastFlood,
  setShowFastFlood,
  showGlofas,
  setShowGlofas,
  onInfoClick,
  selectedDates,
  onDateChange,
  selectedCountry,
  setSelectedCountry,
  isLoadingData,
  availableDates,
  isLayersLoading,
}) => {
  const [stationDate, setStationDate] = useState(new Date().toISOString().split('T')[0]);
  const [impactLayersExpanded, setImpactLayersExpanded] = useState(false);
  // Station info is always visible like in original (removed collapsible behavior)
  const [inundationMapsExpanded, setInundationMapsExpanded] = useState(false);

  // Handle country change
  const handleCountryChange = (countryValue) => {
    // Handle both 'regional' (old) and empty string (new "All Countries" from utility)
    setSelectedCountry(countryValue === 'regional' || countryValue === '' || !countryValue ? null : countryValue);
  };
  
  return (
    <Box sx={{
      width: '100%',
      maxWidth: '320px',
      minWidth: '280px',
      p: '15px 20px',
      height: '100%',
      overflowY: 'auto',
      fontSize: 'clamp(0.75rem, 2vw, 0.85rem)',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      {/* Compact Global Filters */}
      <Box sx={{ 
        mb: '12px', 
        p: '8px 10px',
        backgroundColor: 'white',
        borderRadius: '4px',
        border: '1px solid #ddd'
      }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {/* Date Filter - Compact */}
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '6px',
            p: '2px',
            borderRadius: '3px',
            transition: 'all 0.2s ease',
            '&:hover': {
              backgroundColor: '#f0f0f0'
            }
          }}>
            <Box component="span" sx={{ 
              fontSize: '10px',
              color: '#000000',
              minWidth: '16px'
            }}>📅</Box>
            {isLoadingData && (
              <Box component="span" className="animate-spin" sx={{
                fontSize: '10px',
                color: '#007bff',
                mr: '4px'
              }}>⟳</Box>
            )}
            {isLayersLoading && (
              <Box component="span" className="animate-spin" sx={{
                fontSize: '10px',
                color: '#ff6b35',
                mr: '4px'
              }} title="Updating layers...">🔄</Box>
            )}
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                value={selectedDates?.global ? new Date(selectedDates.global) : null}
                onChange={(newDate) => {
                  if (newDate) {
                    const formattedDate = newDate.toISOString().split('T')[0];
                    // Check if data exists for this date
                    if (availableDates.includes(formattedDate)) {
                      onDateChange('global', formattedDate);
                    } else {
                      // Show message that no data exists for this date
                      alert(`No flood forecast data available for ${new Date(newDate).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}. Please select a date with available data.`);
                    }
                  }
                }}
                shouldDisableDate={(date) => {
                  const formattedDate = date.toISOString().split('T')[0];
                  return !availableDates.includes(formattedDate);
                }}
                slotProps={{
                  textField: {
                    size: 'small',
                    sx: {
                      '& .MuiInputBase-root': {
                        fontSize: '12px',
                        backgroundColor: 'white',
                        border: '1px solid #056B42',
                        borderRadius: '3px',
                        minWidth: '160px',
                      },
                      '& .MuiInputBase-input': {
                        padding: '6px 8px',
                        fontWeight: '500',
                        color: '#000000',
                      },
                      '& .MuiOutlinedInput-notchedOutline': {
                        border: 'none',
                      },
                    },
                  },
                }}
                format="MMM dd, yyyy"
              />
            </LocalizationProvider>
          </Box>

          {/* Country Filter - MUI Select */}
          <Box sx={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            p: '2px',
            borderRadius: '3px',
            transition: 'all 0.2s ease',
            '&:hover': {
              backgroundColor: '#f0f0f0'
            }
          }}>
            <Box component="span" sx={{
              fontSize: '10px',
              color: '#000000',
              minWidth: '16px'
            }}>🌍</Box>
            <FormControl
              size="small"
              sx={{
                flex: 1,
                minWidth: '140px',
                backgroundColor: 'white',
                '& .MuiOutlinedInput-root': {
                  fontSize: '12px',
                  '& fieldset': {
                    borderColor: '#056B42',
                  },
                  '&:hover fieldset': {
                    borderColor: '#056B42',
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: '#056B42',
                  },
                },
                '& .MuiInputLabel-root': {
                  fontSize: '12px',
                  fontWeight: 500,
                  '&.Mui-focused': {
                    color: '#056B42',
                  }
                },
                '& .MuiSelect-select': {
                  padding: '6px 8px',
                  fontWeight: '500',
                  color: '#000000',
                }
              }}
            >
              <Select
                value={selectedCountry || ''}
                onChange={(e) => handleCountryChange(e.target.value || null)}
                displayEmpty
                sx={{
                  fontSize: '12px',
                  fontWeight: '500',
                  borderRadius: '3px',
                }}
              >
                {availableCountries.length === 0 ? (
                  <MenuItem value="" disabled sx={{ fontSize: '12px', fontStyle: 'italic' }}>
                    Loading countries...
                  </MenuItem>
                ) : (
                  availableCountries.map(country => (
                    <MenuItem
                      key={country.code}
                      value={country.value}
                      sx={{ fontSize: '12px' }}
                    >
                      {country.name}
                    </MenuItem>
                  ))
                )}
              </Select>
            </FormControl>
          </Box>
        </Box>
      </Box>

      {/* Station Information Section - Always Visible like Original */}
      <Box sx={{ 
        p: '15px', 
        borderBottom: '2px solid #e9ecef', 
        backgroundColor: '#f8f9fa',
        flexShrink: 0,
        maxHeight: '40%',
        overflowY: 'auto'
      }}>
        <Typography variant="h6" sx={{ m: '0 0 10px 0', color: '#034930', fontWeight: 600, fontSize: '16px' }}>Station Information</Typography>
        <ListGroup style={{ fontSize: '14px' }}>
              <ListGroup.Item>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Switch
                      id="monitoring-stations-toggle"
                      checked={showMonitoringStations}
                      onChange={() => setShowMonitoringStations((prev) => !prev)}
                      size="small"
                      sx={{
                        '& .MuiSwitch-switchBase.Mui-checked': {
                          color: '#1B6840',
                        },
                        '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                          backgroundColor: '#1B6840',
                        }
                      }}
                    />
                    <Typography component="label" htmlFor="monitoring-stations-toggle" sx={{ fontSize: '0.875rem', cursor: 'pointer' }}>
                      FloodProofs East Africa
                    </Typography>
                  </Box>
                  <InfoIcon layerName="FloodProofs East Africa" onClick={onInfoClick} />
                </Box>
              </ListGroup.Item>
              <ListGroup.Item>
                <Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Switch
                        id="geofsm-toggle"
                        checked={showGeoFSM}
                        onChange={() => setShowGeoFSM((prev) => !prev)}
                        size="small"
                        sx={{
                          '& .MuiSwitch-switchBase.Mui-checked': {
                            color: '#1B6840',
                          },
                          '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                            backgroundColor: '#1B6840',
                          }
                        }}
                      />
                      <Typography component="label" htmlFor="geofsm-toggle" sx={{ fontSize: '0.875rem', cursor: 'pointer' }}>
                        GeoSFM
                      </Typography>
                    </Box>
                    <InfoIcon layerName="GeoSFM" onClick={onInfoClick} />
                  </Box>
                  {showGeoFSM && geoFSMLoading && (
                    <Box sx={{ ml: "38px", mt: "8px", display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <CircularProgress size={16} sx={{ color: '#1976d2' }} />
                      <Typography variant="caption" sx={{ color: '#6c757d' }}>
                        Loading GeoSFM data...
                      </Typography>
                    </Box>
                  )}
                  {showGeoFSM && !geoFSMLoading && (
                    <Box sx={{ ml: "38px", mt: "8px", display: 'flex', alignItems: 'center', gap: '8px' }}>
                    </Box>
                  )}
                </Box>
              </ListGroup.Item>
              <ListGroup.Item>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Switch
                      id="mike-hydro-toggle"
                      checked={showMikeHydro}
                      onChange={() => setShowMikeHydro(!showMikeHydro)}
                      size="small"
                      sx={{
                        '& .MuiSwitch-switchBase.Mui-checked': {
                          color: '#1B6840',
                        },
                        '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                          backgroundColor: '#1B6840',
                        }
                      }}
                    />
                    <Typography component="label" htmlFor="mike-hydro-toggle" sx={{ fontSize: '0.875rem', cursor: 'pointer' }}>
                      Mike Hydro
                    </Typography>
                  </Box>
                  <InfoIcon layerName="Mike Hydro" onClick={onInfoClick} />
                </Box>
              </ListGroup.Item>
            </ListGroup>
      </Box>

      {selectedStation && (
        <Box sx={{
          p: '16px',
          backgroundColor: '#f8f9fa',
          borderRadius: '6px',
          mb: '16px',
          border: '1px solid #dee2e6'
        }}>
          <Typography variant="h6" sx={{ mb: '12px', fontSize: '1rem', fontWeight: 600 }}>
            {selectedStation.properties?.SEC_NAME}
          </Typography>
          <Box sx={{
            display: 'grid',
            gridTemplateColumns: '1fr',
            gap: '10px'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '6px', borderBottom: '1px solid #e9ecef' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#495057', fontSize: '0.875rem' }}>
                Basin:
              </Typography>
              <Typography component="span" sx={{ color: '#212529', fontSize: '0.875rem' }}>
                {selectedStation.properties?.BASIN}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '6px', borderBottom: '1px solid #e9ecef' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#495057', fontSize: '0.875rem' }}>
                Area:
              </Typography>
              <Typography component="span" sx={{ color: '#212529', fontSize: '0.875rem' }}>
                {selectedStation.properties?.AREA} km²
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '6px', borderBottom: '1px solid #e9ecef' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#495057', fontSize: '0.875rem' }}>
                Location:
              </Typography>
              <Typography component="span" sx={{ color: '#212529', fontSize: '0.875rem' }}>
                {selectedStation.properties?.latitude?.toFixed(4)}°N,{" "}
                {selectedStation.properties?.longitude?.toFixed(4)}°E
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '6px', borderBottom: '1px solid #e9ecef' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#495057', fontSize: '0.875rem' }}>
                Alert Threshold:
              </Typography>
              <Typography component="span" sx={{ color: '#ff9800', fontWeight: 600, fontSize: '0.875rem' }}>
                {selectedStation.properties?.Q_THR1} m³/s
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '6px', borderBottom: '1px solid #e9ecef' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#495057', fontSize: '0.875rem' }}>
                Alarm Threshold:
              </Typography>
              <Typography component="span" sx={{ color: '#ff5722', fontWeight: 600, fontSize: '0.875rem' }}>
                {selectedStation.properties?.Q_THR2} m³/s
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '6px' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#495057', fontSize: '0.875rem' }}>
                Emergency Threshold:
              </Typography>
              <Typography component="span" sx={{ color: '#d32f2f', fontWeight: 600, fontSize: '0.875rem' }}>
                {selectedStation.properties?.Q_THR3} m³/s
              </Typography>
            </Box>
          </Box>
        </Box>
      )}

      {selectedEnsemblePoint && (
        <Box sx={{
          p: '16px',
          backgroundColor: '#f3e5f5',
          borderRadius: '6px',
          mb: '16px',
          border: '2px solid #9C27B0'
        }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: '12px' }}>
            <Typography variant="h6" sx={{ fontSize: '1rem', fontWeight: 600, color: '#6a1b9a' }}>
              Ensemble Point #{selectedEnsemblePoint.properties?.ID}
            </Typography>
            <Button
              size="small"
              variant="outlined"
              onClick={() => setSelectedEnsemblePoint(null)}
              sx={{ minWidth: 'auto', p: '2px 8px', fontSize: '0.75rem' }}
            >
              Close
            </Button>
          </Box>
          <Box sx={{
            display: 'grid',
            gridTemplateColumns: '1fr',
            gap: '8px'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '4px', borderBottom: '1px solid #d1c4e9' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#6a1b9a', fontSize: '0.875rem' }}>
                Grid Code:
              </Typography>
              <Typography component="span" sx={{ color: '#4a148c', fontSize: '0.875rem' }}>
                {selectedEnsemblePoint.properties?.GRIDCODE}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '4px', borderBottom: '1px solid #d1c4e9' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#6a1b9a', fontSize: '0.875rem' }}>
                Zone:
              </Typography>
              <Typography component="span" sx={{ color: '#4a148c', fontSize: '0.875rem' }}>
                Zone {selectedEnsemblePoint.properties?.Zone}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '4px', borderBottom: '1px solid #d1c4e9' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#6a1b9a', fontSize: '0.875rem' }}>
                Admin:
              </Typography>
              <Typography component="span" sx={{ color: '#4a148c', fontSize: '0.875rem' }}>
                {selectedEnsemblePoint.properties?.admin_name || 'N/A'}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', py: '4px' }}>
              <Typography component="span" sx={{ fontWeight: 600, color: '#6a1b9a', fontSize: '0.875rem' }}>
                Location:
              </Typography>
              <Typography component="span" sx={{ color: '#4a148c', fontSize: '0.875rem' }}>
                {selectedEnsemblePoint.properties?.y?.toFixed(4)}°,{" "}
                {selectedEnsemblePoint.properties?.x?.toFixed(4)}°
              </Typography>
            </Box>
            {selectedEnsemblePoint.properties?.has_data && selectedEnsemblePoint.properties?.forecasts && (
              <Box sx={{ mt: '12px' }}>
                <Typography sx={{ fontSize: '0.85rem', fontWeight: 600, color: '#6a1b9a', mb: '8px' }}>
                  📊 Ensemble Forecast ({selectedEnsemblePoint.properties.forecast_count} records)
                </Typography>
                <Box sx={{ backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #d1c4e9', p: '8px' }}>
                  <EnsembleForecastChart
                    forecasts={selectedEnsemblePoint.properties.forecasts}
                    height={300}
                  />
                </Box>
              </Box>
            )}
          </Box>
        </Box>
      )}

      {/* Inundation Maps Group - Collapsible */}
      <Box
        sx={{
          mb: '10px',
          mt: '20px',
          backgroundColor: '#034930',
          color: 'white',
          p: '12px 16px',
          cursor: 'pointer',
          borderRadius: '4px',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          touchAction: 'manipulation'
        }}
        onClick={() => setInundationMapsExpanded(!inundationMapsExpanded)}
      >
        <FontAwesomeIcon icon={faExclamationTriangle} style={{ fontSize: '18px' }} />
        <Typography variant="h6" sx={{
          m: 0,
          fontSize: '0.95rem',
          fontWeight: 500,
          flex: 1
        }}>
          Inundation Maps
        </Typography>
      </Box>

      {inundationMapsExpanded && (
        <Box sx={{ p: '12px 16px', backgroundColor: '#f8f9fa', mb: '10px' }}>
          {/* Date picker for Inundation Maps */}
          <Box sx={{ mb: '16px' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px', mb: '8px' }}>
              <FontAwesomeIcon icon={faExclamationTriangle} style={{ fontSize: '16px', color: '#6c757d' }} />
              <Box
                component="input"
                type="date"
                value={selectedDates?.inundation || new Date().toISOString().split('T')[0]}
                onChange={(e) => onDateChange && onDateChange('inundation', e.target.value)}
                sx={{
                  flex: 1,
                  p: '8px',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '0.875rem'
                }}
              />
            </Box>
          </Box>

          {/* Layer toggles */}
          {hazardLayers.map((layer) => (
            <Box
              key={layer.name}
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                p: '10px 0',
                borderBottom: '1px solid #e9ecef'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                <Switch
                  id={`inundation-${layer.name}`}
                  checked={selectedLayers.has(layer.layer)}
                  onChange={() => onLayerSelect(layer)}
                  disabled={layer.disabled}
                  size="small"
                  sx={{
                    '& .MuiSwitch-switchBase.Mui-checked': {
                      color: '#1B6840',
                    },
                    '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                      backgroundColor: '#1B6840',
                    }
                  }}
                />
                <Typography
                  component="label"
                  htmlFor={`inundation-${layer.name}`}
                  sx={{
                    fontSize: '0.875rem',
                    color: layer.disabled ? '#999' : '#333',
                    cursor: layer.disabled ? 'not-allowed' : 'pointer',
                    m: 0
                  }}
                >
                  {layer.name}
                </Typography>
              </Box>
              <InfoIcon layerName={layer.name} onClick={onInfoClick} />
            </Box>
          ))}
        </Box>
      )}

      {/* Impact Layers Group - Collapsible */}
      <Box
        sx={{
          mb: '10px',
          mt: '20px',
          backgroundColor: '#034930',
          color: 'white',
          p: '12px 16px',
          cursor: 'pointer',
          borderRadius: '4px',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          touchAction: 'manipulation'
        }}
        onClick={() => setImpactLayersExpanded(!impactLayersExpanded)}
      >
        <FontAwesomeIcon icon={faWater} style={{ fontSize: '18px' }} />
        <Typography variant="h6" sx={{
          m: 0,
          fontSize: '0.95rem',
          fontWeight: 500,
          flex: 1
        }}>
          Impact Layers
        </Typography>
      </Box>

      {impactLayersExpanded && (
        <Box sx={{ p: '12px 16px', backgroundColor: '#f8f9fa', mb: '10px' }}>
          {/* Date picker for Impact Layers */}
          <Box sx={{ mb: '16px' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px', mb: '8px' }}>
              <FontAwesomeIcon icon={faWater} style={{ fontSize: '16px', color: '#6c757d' }} />
              <Box
                component="input"
                type="date"
                value={selectedDates?.impact || new Date().toISOString().split('T')[0]}
                onChange={(e) => onDateChange && onDateChange('impact', e.target.value)}
                sx={{
                  flex: 1,
                  p: '8px',
                  border: '1px solid #ced4da',
                  borderRadius: '4px',
                  fontSize: '0.875rem'
                }}
              />
            </Box>
          </Box>

          {/* IBEW v2 Section */}
          <Box sx={{ mb: '20px' }}>
            <Typography variant="h6" sx={{
              fontSize: '0.85rem',
              fontWeight: '600',
              color: '#333',
              mb: '12px',
              mt: 0
            }}>
              IBEW v2
            </Typography>
            {ibewLayers.map((layer) => (
              <Box
                key={layer.name}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  p: '10px 0',
                  borderBottom: '1px solid #e9ecef'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                  <Switch
                    id={`ibew-${layer.name}`}
                    checked={selectedLayers.has(layer.layer)}
                    onChange={() => onLayerSelect(layer)}
                    disabled={layer.disabled}
                    size="small"
                    sx={{
                      '& .MuiSwitch-switchBase.Mui-checked': {
                        color: '#1B6840',
                      },
                      '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                        backgroundColor: '#1B6840',
                      }
                    }}
                  />
                  <Typography
                    component="label"
                    htmlFor={`ibew-${layer.name}`}
                    sx={{
                      fontSize: '0.875rem',
                      color: layer.disabled ? '#999' : '#333',
                      cursor: layer.disabled ? 'not-allowed' : 'pointer',
                      m: 0
                    }}
                  >
                    {layer.name}
                  </Typography>
                </Box>
                <InfoIcon layerName={layer.name} onClick={onInfoClick} />
              </Box>
            ))}
          </Box>

          {/* Impact Layers (IBEW v1) Section */}
          {impactLayers.length > 0 && (
            <Box>
              <Typography variant="h6" sx={{
                fontSize: '0.85rem',
                fontWeight: '600',
                color: '#333',
                mb: '12px',
                mt: 0
              }}>
                IBEW v1
              </Typography>
              {impactLayers.map((layer) => (
                <Box
                  key={layer.name}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    p: '10px 0',
                    borderBottom: '1px solid #e9ecef'
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                    <Switch
                      id={`impact-${layer.name}`}
                      checked={selectedLayers.has(layer.layer)}
                      onChange={() => onLayerSelect(layer)}
                      disabled={layer.disabled}
                      size="small"
                      sx={{
                        '& .MuiSwitch-switchBase.Mui-checked': {
                          color: '#1B6840',
                        },
                        '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                          backgroundColor: '#1B6840',
                        }
                      }}
                    />
                    <Typography
                      component="label"
                      htmlFor={`impact-${layer.name}`}
                      sx={{
                        fontSize: '0.875rem',
                        color: layer.disabled ? '#999' : '#333',
                        cursor: layer.disabled ? 'not-allowed' : 'pointer',
                        m: 0
                      }}
                    >
                      {layer.name}
                    </Typography>
                  </Box>
                  <InfoIcon layerName={layer.name} onClick={onInfoClick} />
                </Box>
              ))}
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
};

// Component to handle map overlay events
const MapEventHandler = ({ onOverlayAdd, onOverlayRemove }) => {
  useMapEvents({
    overlayadd: (e) => {
      onOverlayAdd(e);
    },
    overlayremove: (e) => {
      onOverlayRemove(e);
    }
  });
  return null;
};

// Main MapViewer component
const MapViewer = () => {
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [selectedLayers, setSelectedLayers] = useState(new Set());
  // Sidebar: closed on mobile by default, open on desktop
  const [isSidebarActive, setIsSidebarActive] = useState(!isMobile);
  const [selectedBoundaryLayers, setSelectedBoundaryLayers] = useState(new Set([
    'admin_level_1'  // Only Admin1 loads by default
  ]));
  const [activeLegend, setActiveLegend] = useState(null);

  // State to track which overlay layers are active for conditional legends
  // Initialize with default checked layers
  const [activeOverlays, setActiveOverlays] = useState(new Set([
    'Rivers',
    'Lakes (Water Bodies)',
    'Admin 0 (Countries)'
  ]));
  const [mapKey, setMapKey] = useState(0);
  const [showMonitoringStations, setShowMonitoringStations] = useState(true); // Enabled to show flood data
  const [showGeoFSM, setShowGeoFSM] = useState(false);
  const [showMikeHydro, setShowMikeHydro] = useState(false);
  const [showHype, setShowHype] = useState(false);
  const [showEnsemble, setShowEnsemble] = useState(false);
  const [monitoringData, setMonitoringData] = useState(null);
  const [geoFSMData, setGeoFSMData] = useState(null);
  const [selectedStation, setSelectedStation] = useState(null);
  const [selectedEnsemblePoint, setSelectedEnsemblePoint] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [adminBoundariesData, setAdminBoundariesData] = useState(null);
  const [admin2BoundariesData, setAdmin2BoundariesData] = useState(null); // For Admin2 data
  const [lakesData, setLakesData] = useState(null); // For lakes data
  const [riversData, setRiversData] = useState(null); // For rivers data
  const [availableCountries, setAvailableCountries] = useState([]); // Countries from database
  const [geoFSMLoading, setGeoFSMLoading] = useState(false);
  const [geoFSMTimeSeriesData, setGeoFSMTimeSeriesData] = useState([]);
  const [chartType, setChartType] = useState("discharge");
  const [geoFSMDataType, setGeoFSMDataType] = useState("riverdepth");
  const [selectedSeries, setSelectedSeries] = useState("both");

  // State for metadata modal
  const [showMetadataModal, setShowMetadataModal] = useState(false);
  const [currentMetadata, setCurrentMetadata] = useState(null);

  // TEST: Use new modular hook for available dates
  const {
    dates: hookAvailableDates,
    latestDate: hookLatestDate,
    isLoading: hookDatesLoading,
    error: hookDatesError
  } = useAvailableDates();

  // State for global date filter - will be set to latest available date from API
  const [selectedDates, setSelectedDates] = useState({
    global: null
  });

  // Set default date to today if available, otherwise use latest date
  useEffect(() => {
    if (hookAvailableDates && hookAvailableDates.length > 0 && !selectedDates.global) {
      const today = new Date().toISOString().split('T')[0];
      const defaultDate = hookAvailableDates.includes(today) ? today : hookLatestDate;

      if (defaultDate) {
        setSelectedDates({ global: defaultDate });
      }
    }
  }, [hookAvailableDates, hookLatestDate, selectedDates.global]);

  // Fetch ensemble control points when ensemble layer is enabled
  const {
    data: ensembleData,
    isLoading: ensembleLoading,
    error: ensembleError
  } = useEnsembleData({
    enabled: showEnsemble,
    selectedDate: selectedDates?.global || null
  });

  // Debug logging and error handling for ensemble
  useEffect(() => {
    if (showEnsemble && !ensembleLoading && ensembleError && selectedDates?.global) {
      const dateObj = new Date(selectedDates.global);
      const formattedDate = dateObj.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      alert(`No ensemble forecast data available for ${formattedDate}. Please select a date with available data.`);
      setShowEnsemble(false);
    }
  }, [showEnsemble, ensembleLoading, ensembleError, selectedDates.global]);
  
  // State for layer loading indication
  const [isLayersLoading, setIsLayersLoading] = useState(false);
  
  // State for country filter - default to regional (all countries)
  const [selectedCountry, setSelectedCountry] = useState(null);

  // State for data fallback notification
  const [showFallbackNotification, setShowFallbackNotification] = useState(false);
  const [fallbackMessage, setFallbackMessage] = useState('');
  
  // State for loading and caching
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [availableDates, setAvailableDates] = useState([]);
  const [datesLoaded, setDatesLoaded] = useState(false);
  const [geosfmAvailableDates, setGeosfmAvailableDates] = useState([]);
  const [geosfmDatesLoaded, setGeosfmDatesLoaded] = useState(false);

  // Handlers for overlay layer add/remove to track active layers for conditional legends
  const handleOverlayAdd = useCallback((e) => {
    setActiveOverlays(prev => {
      const newSet = new Set([...prev, e.name]);
      return newSet;
    });
  }, []);

  const handleOverlayRemove = useCallback((e) => {
    setActiveOverlays(prev => {
      const updated = new Set(prev);
      updated.delete(e.name);
      return updated;
    });
  }, []);

  // Function to fetch available dates for deterministic data and ensemble forecasts
  const fetchAvailableDates = useCallback(async () => {
    try {
      // Fetch FloodProofs dates
      const floodproofsPromise = fetchWithTiming(`${FASTAPI_BASE_URL}/merged-forecast/dates/`)
        .then(async (response) => {
          if (response.ok) {
            const data = await response.json();
            return data.dates ? data.dates.map(d => d.date) : [];
          }
          return [];
        })
        .catch(error => {
          console.error('Error fetching FloodProofs dates:', error);
          return [];
        });

      // Fetch Ensemble dates
      const ensemblePromise = fetchWithTiming(`${FASTAPI_BASE_URL}/ensemble-forecast-dates/`)
        .then(async (response) => {
          if (response.ok) {
            const data = await response.json();
            return data.dates ? data.dates.map(d => d.date) : [];
          }
          return [];
        })
        .catch(error => {
          return [];
        });

      // Wait for both requests
      const [floodproofsDates, ensembleDates] = await Promise.all([
        floodproofsPromise,
        ensemblePromise
      ]);

      // Merge and deduplicate dates
      const allDates = [...new Set([...floodproofsDates, ...ensembleDates])];

      // Filter out invalid dates
      const validDates = allDates.filter(date => {
        const dateObj = new Date(date);
        return !isNaN(dateObj.getTime());
      }).sort((a, b) => new Date(b) - new Date(a)); // Sort descending (newest first)

      setAvailableDates(validDates);
      setDatesLoaded(true);
      return validDates;
    } catch (error) {
      console.error('Error fetching available dates:', error);
    }
    return [];
  }, []);

  // Function to fetch and cache available dates for GeoSFM data
  const fetchGeosfmAvailableDates = useCallback(async () => {
    if (geosfmDatesLoaded) return geosfmAvailableDates;

    try {
      const response = await fetchWithTiming(`${API_BASE_URL}/geosfm/available-dates/`);
      if (response.ok) {
        const data = await response.json();
        const rawDates = data.dates || [];

        // Filter out invalid dates
        const validDates = rawDates.filter(date => {
          const dateObj = new Date(date);
          return !isNaN(dateObj.getTime());
        });

        setGeosfmAvailableDates(validDates);
        setGeosfmDatesLoaded(true);
        return validDates;
      }
    } catch (error) {
      console.error('Error fetching GeoSFM dates:', error);
    }
    return [];
  }, [geosfmDatesLoaded, geosfmAvailableDates]);


  // Helper function to filter monitoring data by selected country
  const filterDataByCountry = useCallback((data, country) => {
    if (!data || !data.features || !country || !adminBoundariesData) return data;
    
    // Use spatial filtering for point data (like flood monitoring stations)
    const spatialFiltered = filterPointsByCountry(data, adminBoundariesData, country);
    
    // If spatial filtering returned results, use it
    if (spatialFiltered && spatialFiltered.features && spatialFiltered.features.length > 0) {
      return spatialFiltered;
    }
    
    // Fallback: Filter features based on country property - check multiple possible property names
    const filteredFeatures = data.features.filter(feature => {
      const props = feature.properties || {};
      const featureCountry = (
        props.COUNTRY || 
        props.Country || 
        props.country || 
        props.ADMIN || 
        props.admin ||
        props.NAME_EN ||
        props.name_en ||
        props.ISO ||
        props.iso ||
        ''
      ).toLowerCase();
      
      // Check if feature country matches selected country
      const match = featureCountry === country.toLowerCase() || 
                   featureCountry.includes(country.toLowerCase()) ||
                   country.toLowerCase().includes(featureCountry);
      
      return match;
    });
    
    if (filteredFeatures.length > 0) {
    }
    
    return {
      ...data,
      features: filteredFeatures
    };
  }, [adminBoundariesData]);

  // Apply spatial filtering to monitoring data (Floodproofs East Africa) based on selected country
  const filteredMonitoringData = useMemo(() => {
    if (!monitoringData) {
      return null;
    }

    if (!selectedCountry || selectedCountry === '') {
      // No filter: return all data
      return monitoringData;
    }

    if (!adminBoundariesData) {
      return monitoringData;
    }

    // Handle WHCA Countries filter
    if (selectedCountry === 'WHCA') {
      const whcaCountries = ['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'];
      let combinedFeatures = [];

      whcaCountries.forEach(country => {
        const result = filterPointsByCountry(monitoringData, adminBoundariesData, country);
        if (result?.features) {
          combinedFeatures = [...combinedFeatures, ...result.features];
        }
      });

      // Remove duplicates
      const uniqueFeatures = Array.from(
        new Map(combinedFeatures.map(f => [f.properties.ID || f.properties.SEC_CODE, f])).values()
      );

      return {
        type: 'FeatureCollection',
        features: uniqueFeatures
      };
    }

    // Single country filter
    const result = filterPointsByCountry(monitoringData, adminBoundariesData, selectedCountry);
    if (result) {
      return result;
    }

    return monitoringData;
  }, [monitoringData, selectedCountry, adminBoundariesData]);

  // Force map remount when country filter changes
  useEffect(() => {
    setMapKey(prev => prev + 1);
  }, [selectedCountry]);

  // Apply spatial filtering to GeoSFM data based on selected country
  const filteredGeosfmData = useMemo(() => {
    if (!geoFSMData) {
      return null;
    }

    if (!selectedCountry || selectedCountry === '') {
      return geoFSMData;
    }

    if (!adminBoundariesData) {
      return geoFSMData;
    }

    // Handle WHCA Countries filter
    if (selectedCountry === 'WHCA') {
      const whcaCountries = ['Uganda', 'Rwanda', 'South Sudan', 'Ethiopia', 'Sudan'];
      let combinedFeatures = [];

      whcaCountries.forEach(country => {
        const result = filterPointsByCountry(geoFSMData, adminBoundariesData, country);
        if (result?.features) {
          combinedFeatures = [...combinedFeatures, ...result.features];
        }
      });

      const uniqueFeatures = Array.from(
        new Map(combinedFeatures.map(f => [f.properties.ID || f.properties.Id, f])).values()
      );

      return {
        type: 'FeatureCollection',
        features: uniqueFeatures
      };
    }

    // Single country filter
    const result = filterPointsByCountry(geoFSMData, adminBoundariesData, selectedCountry);
    if (result) {
      return result;
    }

    return geoFSMData;
  }, [geoFSMData, selectedCountry, adminBoundariesData]);

  // Function to generate report - navigate to station-specific report
  const generateReport = useCallback((clickedFeature = null) => {
    if (!clickedFeature || !clickedFeature.properties) {
      alert('No station selected for report generation');
      return;
    }

    // Use unique ID field (ID or SEC_CODE are unique, section_id is NOT unique!)
    const stationId = clickedFeature.properties.ID ||
                     clickedFeature.properties.SEC_CODE ||
                     clickedFeature.properties.section_id ||
                     clickedFeature.properties.station_id;

    if (!stationId) {
      alert('Station ID not found in properties: ' + JSON.stringify(Object.keys(clickedFeature.properties)));
      return;
    }

    // Pass selected country to station report for filtered statistics
    const countryParam = selectedCountry ? `?country=${encodeURIComponent(selectedCountry)}` : '';
    navigate(`/reports/station/${stationId}${countryParam}`);
  }, [navigate, selectedCountry]);

  // Handler for date changes - immediate hand-in-hand updates
  const handleDateChange = useCallback((layerType, date) => {
    // Validate date format before using it
    const dateObj = new Date(date);
    if (isNaN(dateObj.getTime())) {
      console.error(`❌ Invalid date format: ${date}`);
      return;
    }

    // Clear cached data for the old date to force fresh fetch
    if (selectedDates?.global && selectedDates.global !== date) {
      forecastCache.clear();
    }

    // Generate unique map key for cache busting
    const timestamp = Date.now();
    const uniqueKey = timestamp + Math.floor(Math.random() * 1000000);

    // Toggle monitoring stations off and on to force complete refresh
    if (showMonitoringStations) {
      setShowMonitoringStations(false);

      // Use setTimeout to ensure the off state is processed before turning back on
      setTimeout(() => {
        setSelectedDates({ global: date });
        setMapKey(uniqueKey);
        setShowMonitoringStations(true);
        setIsLayersLoading(false);
      }, 50);
    } else {
      // If monitoring stations are off, just update date normally
      setSelectedDates({ global: date });
      setMapKey(uniqueKey);
      setIsLayersLoading(false);
    }
  }, [selectedDates, showMonitoringStations]);

  // Handler for info icon clicks
  const handleInfoClick = (layerName) => {
    // For now, show a simple placeholder since metadata is empty
    const metadata = LAYER_METADATA[layerName] || {
      title: layerName,
      description: `Information about ${layerName}`,
      details: ["Details will be added soon"],
      source: "East Africa Flood Watch"
    };
    
    metadata.title = layerName;
    setCurrentMetadata(metadata);
    setShowMetadataModal(true);
  };

  // Handler for closing metadata modal
  const handleCloseMetadata = () => {
    setShowMetadataModal(false);
  };

  // Function to fetch GeoJSON data for selected date with loading states
  const fetchMonitoringData = useCallback(async () => {
    // Always use server-provided dates, never default to today
    const requestedDate = selectedDates?.global;

    // Don't fetch if we don't have a date yet (still loading from server)
    if (!requestedDate) {
      return;
    }

    // Validate the date before making API call
    const dateObj = new Date(requestedDate);
    if (isNaN(dateObj.getTime())) {
      console.error(`❌ Invalid date in fetchMonitoringData: ${requestedDate}`);
      return;
    }

    // Check cache first for instant loading (cache by date only, not country - filtering is client-side)
    const cachedData = forecastCache.get(requestedDate, '');
    if (cachedData) {
      setMonitoringData(cachedData);
      setIsLoadingData(false);
      return;
    }

    setIsLoadingData(true);

    try {
      // Fetch all data - filtering by country is done client-side
      // Correct endpoint: /fast/merged-forecast/{date}/ NOT /fast/merged-forecast/dates/{date}/
      const url = `${FASTAPI_BASE_URL}/merged-forecast/${requestedDate}/`;

      // Use FastAPI endpoint for high-performance deterministic forecasts
      const response = await fetchWithTiming(url);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Check if fallback was used via response headers (FastAPI sends X-Fallback and X-Fallback-Date)
      const fallbackUsed = response.headers.get('X-Fallback') === 'true';
      const fallbackDate = response.headers.get('X-Fallback-Date');
      const actualDate = fallbackDate || response.headers.get('X-Forecast-Date');

      if (fallbackUsed && actualDate) {
        const message = `Data for ${requestedDate} not available. Showing data from ${actualDate} (latest available).`;

        setFallbackMessage(message);
        setShowFallbackNotification(true);
        setTimeout(() => setShowFallbackNotification(false), 5000);

        // Update the selected date to the actual fallback date
        setSelectedDates(prev => ({
          ...prev,
          global: actualDate
        }));

        console.warn(`⚠️ Fallback: Requested ${requestedDate}, showing ${actualDate}`);
      }
      
      // Process and set the data
      if (!data.features || data.features.length === 0) {
        setMonitoringData(null);
        return;
      }
      
      // Add lat/lng properties for easy access
      data.features.forEach((feature) => {
        if (feature.geometry?.coordinates) {
          feature.properties.latitude = feature.geometry.coordinates[1];
          feature.properties.longitude = feature.geometry.coordinates[0];
        }
      });
      
      // Store all data - filtering by country is done client-side using filteredMonitoringData
      const featureCount = data?.features?.length || 0;

      // Store in cache for instant future access (cache by date only)
      forecastCache.set(requestedDate, '', data);

      setMonitoringData(data);
      
      
    } catch (error) {
      setMonitoringData(null);
      
      if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
        setFallbackMessage(`Connection error. Please check your network.`);
        setShowFallbackNotification(true);
        setTimeout(() => setShowFallbackNotification(false), 4000);
      }
    } finally {
      setIsLoadingData(false);
    }
  }, [selectedDates?.global]); // Only date triggers refetch - country filtering is client-side

  // Effect to refetch data when selectedDates changes (NOT country - country is filtered client-side)
  useEffect(() => {
    if (showMonitoringStations) {
      fetchMonitoringData();

      // Set up auto-refresh every 60 seconds
      const interval = setInterval(fetchMonitoringData, 60000);
      return () => clearInterval(interval);
    } else {
      setMonitoringData(null);
      setTimeSeriesData([]);
      setSelectedStation(null);
    }
  }, [selectedDates?.global, showMonitoringStations, fetchMonitoringData]); // Removed selectedCountry - filtering is client-side

  // Load admin0 (country) boundaries from database API for spatial filtering
  useEffect(() => {
    const loadAdminBoundaries = async () => {
      try {
        // Load Admin0 (country boundaries) with geometries for spatial filtering
        const response = await fetchWithTiming(`${API_BASE_URL}/admin0/geojson/`);

        if (response.ok) {
          const data = await response.json();
          console.log('✅ Loaded Admin0 boundaries:', data?.features?.length, 'countries');
          setAdminBoundariesData(data); // API returns GeoJSON FeatureCollection

          // Extract unique countries from the data using the utility function
          const countryList = extractCountriesFromAdminData(data);
          setAvailableCountries(countryList);
        } else {
          console.error('Admin0 GeoJSON API fetch failed with status:', response.status);
        }
      } catch (error) {
        console.error('Error loading Admin0 boundaries from API:', error);
      }
    };

    loadAdminBoundaries();

    // Load Admin2 boundaries from API
    const loadAdmin2Boundaries = async () => {
      try {
        const response = await fetchWithTiming(`${API_BASE_URL}/admin2/`);

        if (response.ok) {
          const data = await response.json();
          setAdmin2BoundariesData(data); // API returns GeoJSON directly
        } else {
          console.error('Admin2 API fetch failed with status:', response.status);
        }
      } catch (error) {
        console.error('Error loading Admin2 boundaries from API:', error);
      }
    };

    loadAdmin2Boundaries();
  }, []);

  // Load lakes data on mount
  useEffect(() => {
    const loadLakesData = async () => {
      try {
        const response = await fetchWithTiming(`${API_BASE_URL}/water-bodies/`);
        if (response.ok) {
          const data = await response.json();
          setLakesData(data); // API returns GeoJSON directly
        } else {
          console.error('Lakes API fetch failed with status:', response.status);
        }
      } catch (error) {
        console.error('Error loading Lakes from API:', error);
      }
    };

    loadLakesData();
  }, []);

  // Load available dates on mount and set initial date - single source of truth
  useEffect(() => {
    const loadDatesAndInitialize = async () => {
      // Fetch both deterministic and GeoSFM dates in parallel
      const [deterministicDates, geosfmDates] = await Promise.all([
        fetchAvailableDates(),
        fetchGeosfmAvailableDates()
      ]);

      // Only set date if not already set
      if (!selectedDates?.global) {
        // Prefer deterministic (Floodproof) dates - they're most up-to-date, fallback to GeoSFM
        const latestDate = (deterministicDates && deterministicDates.length > 0)
          ? deterministicDates[0]
          : (geosfmDates && geosfmDates.length > 0)
            ? geosfmDates[0]
            : null;

        // Validate and set the date - this will trigger data fetching via other useEffects
        if (latestDate) {
          const dateObj = new Date(latestDate);
          if (!isNaN(dateObj.getTime())) {
            setSelectedDates({ global: latestDate });
          } else {
            console.error(`❌ Invalid latest date from API: ${latestDate}`);
          }
        }
      }
    };

    loadDatesAndInitialize();
  }, []); // Run only once on mount

  useEffect(() => {
    const loadGeoFSMData = async () => {
      if (showGeoFSM) {
        setGeoFSMLoading(true);
        try {
          // Use the selected date or fetch latest if no date is selected
          const selectedDate = selectedDates?.global;
          let baseApiUrl = selectedDate
            ? `${API_BASE_URL}/geosfm/${selectedDate}/`
            : `${API_BASE_URL}/geosfm/latest/`;

          // Add country filter if selected
          let apiUrl = selectedCountry
            ? `${baseApiUrl}?country=${encodeURIComponent(selectedCountry)}`
            : baseApiUrl;

          let response = await fetchWithTiming(apiUrl);

          // If no data for selected date, try fetching the latest available
          if (!response.ok && response.status === 404 && selectedDate) {
            let latestUrl = `${API_BASE_URL}/geosfm/latest/`;
            apiUrl = selectedCountry
              ? `${latestUrl}?country=${encodeURIComponent(selectedCountry)}`
              : latestUrl;
            response = await fetchWithTiming(apiUrl);
          }

          if (!response.ok) {
            setGeoFSMData(null);
            setGeoFSMTimeSeriesData([]);
            setGeoFSMLoading(false);
            return;
          }

          const data = await response.json();

          // Ensure coordinates are in properties for compatibility
          if (data.features) {
            data.features.forEach((feature) => {
              if (feature.geometry?.coordinates) {
                feature.properties.latitude = feature.geometry.coordinates[1];
                feature.properties.longitude = feature.geometry.coordinates[0];
              }
            });
          }

          setGeoFSMData(data);
          const validTypes = ["riverdepth", "streamflow"];
          const dataTypes = [
            ...new Set(
              data.features
                .map((f) => f.properties.data_type)
                .filter((type) => type && validTypes.includes(type)),
            ),
          ];
          setGeoFSMDataType(dataTypes[0] || "riverdepth");

          const allTimeSeries = data.features
            .reduce((acc, f) => {
              const timestamp = new Date(f.properties.timestamp);
              if (isNaN(timestamp.getTime())) return acc;
              const existing = acc.find(
                (item) => item.timestamp.getTime() === timestamp.getTime(),
              );
              if (existing) {
                if (f.properties.data_type === "riverdepth")
                  existing.depth = Number(f.properties.value) || 0;
                else if (f.properties.data_type === "streamflow")
                  existing.streamflow = Number(f.properties.value) || 0;
              } else {
                acc.push({
                  timestamp,
                  depth:
                    f.properties.data_type === "riverdepth"
                      ? Number(f.properties.value) || 0
                      : 0,
                  streamflow:
                    f.properties.data_type === "streamflow"
                      ? Number(f.properties.value) || 0
                      : 0,
                });
              }
              return acc;
            }, [])
            .sort((a, b) => a.timestamp - b.timestamp);
          setGeoFSMTimeSeriesData(allTimeSeries);
        } catch (error) {
          console.error('Error loading GeoSFM data:', error);
          setGeoFSMData(null);
          setGeoFSMTimeSeriesData([]);
        } finally {
          setGeoFSMLoading(false);
        }
      } else {
        setGeoFSMData(null);
        setGeoFSMTimeSeriesData([]);
        setSelectedStation(null);
        setGeoFSMLoading(false);
      }
    };

    loadGeoFSMData();
  }, [showGeoFSM, selectedDates?.global, selectedCountry]);

  // Enhanced layer selection with proper date handling
  const handleLayerSelection = useCallback(
    (layer) => {
      // Safety check: ensure layer object exists and has required properties
      if (!layer || !layer.layer) {
        console.error('Invalid layer object passed to handleLayerSelection:', layer);
        return;
      }

      setSelectedLayers((prev) => {
        const newSelectedLayers = new Set(prev);
        const isImpactLayer = IMPACT_LAYERS.some((l) => l.layer === layer.layer);
        const isIBEWLayer = IBEW_LAYERS.some((l) => l.layer === layer.layer);
        
        if (newSelectedLayers.has(layer.layer)) {
          newSelectedLayers.delete(layer.layer);
          if (activeLegend === layer.legend) setActiveLegend(null);
        } else {
          if (isImpactLayer) {
            IMPACT_LAYERS.forEach((l) => newSelectedLayers.delete(l.layer));
          }
          if (isIBEWLayer) {
            IBEW_LAYERS.forEach((l) => newSelectedLayers.delete(l.layer));
          }
          
          newSelectedLayers.add(layer.layer);
          setActiveLegend(layer.legend);
        }
        return newSelectedLayers;
      });

      setSelectedStation(null);
      setTimeSeriesData([]);
      setGeoFSMTimeSeriesData([]);
    },
    [activeLegend],
  );
  
  const handleBoundaryLayerSelection = useCallback(
    (layer) => {
      // Allow toggling of admin_level_1 now that we use GeoJSON
      
      setSelectedBoundaryLayers((prev) => {
        const newSelected = new Set(prev);
        if (newSelected.has(layer.layer)) {
          newSelected.delete(layer.layer);
          if (activeLegend === layer.legend) setActiveLegend(null);
        } else {
          newSelected.add(layer.layer);
          setActiveLegend(layer.legend);
        }
        return newSelected;
      });
    },
    [activeLegend],
  );

  const handleStationClick = useCallback(
    (feature, event = null) => {
      setSelectedStation(feature);
    },
    [],
  );

  const handleEnsembleClick = useCallback(
    (feature) => {
      setSelectedEnsemblePoint(feature);
      // Clear selected station when ensemble point is clicked
      setSelectedStation(null);
    },
    [],
  );


  // Render chart directly in popup using React Recharts
  const renderChartInPopup = useCallback(async (feature, stationId, forecastDate = null) => {
    const container = document.getElementById(`popup-chart-container-${stationId}`);
    if (!container) return;

    // Process time series data same way as handleStationClick
    const timePeriod = feature.properties.time_period?.split(",")?.map((t) => t.trim()) || [];
    const gfsValues = feature.properties["time_series_discharge_simulated-gfs"]?.split(",").map((val) => Number(val.trim()) || 0) || [];
    const iconValues = feature.properties["time_series_discharge_simulated-icon"]?.split(",").map((val) => Number(val.trim()) || 0) || [];

    const rawData = timePeriod
      .map((time, index) => ({
        time: new Date(time),
        gfs: gfsValues[index],
        icon: iconValues[index],
      }))
      .filter((item) =>
        !isNaN(item.time.getTime()) &&
        ((!isNaN(item.gfs) && item.gfs !== null) || (!isNaN(item.icon) && item.icon !== null))
      );

    // Aggregate data by day (daily averages) - same as main chart
    const dailyData = rawData.reduce((acc, item) => {
      const dateKey = item.time.toISOString().split('T')[0];

      if (!acc[dateKey]) {
        acc[dateKey] = {
          date: new Date(dateKey),
          gfsValues: [],
          iconValues: []
        };
      }

      if (!isNaN(item.gfs) && item.gfs !== null && item.gfs !== 0) {
        acc[dateKey].gfsValues.push(item.gfs);
      }
      if (!isNaN(item.icon) && item.icon !== null && item.icon !== 0) {
        acc[dateKey].iconValues.push(item.icon);
      }

      return acc;
    }, {});

    const chartData = Object.values(dailyData)
      .map(day => ({
        time: day.date,
        gfs: day.gfsValues.length > 0 ? day.gfsValues.reduce((a, b) => a + b, 0) / day.gfsValues.length : null,
        icon: day.iconValues.length > 0 ? day.iconValues.reduce((a, b) => a + b, 0) / day.iconValues.length : null,
      }))
      .sort((a, b) => a.time - b.time);

    // Set the time series data for this station (so exports work)
    setTimeSeriesData(chartData);

    // Format the forecast date for display
    let dateLabel = '';
    if (forecastDate) {
      const date = new Date(forecastDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);
      const dateToCompare = new Date(date);
      dateToCompare.setHours(0, 0, 0, 0);

      if (dateToCompare.getTime() === today.getTime()) {
        dateLabel = ' - Today';
      } else if (dateToCompare.getTime() === tomorrow.getTime()) {
        dateLabel = ' - Tomorrow';
      } else {
        dateLabel = ' - ' + date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      }
    }

    // Create React chart container with unique ID
    const chartContainerId = `react-chart-${stationId}`;
    container.innerHTML = `
      <div style="position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 8px;">
          <h4 style="margin: 0; font-size: 13px; color: #333;">Discharge Forecast${dateLabel}</h4>
          <select
            id="series-selector-${stationId}"
            style="padding: 4px 8px; background-color: white; border: 1px solid #ccc; border-radius: 3px; cursor: pointer; font-size: 11px;"
          >
            <option value="both">GFS + ICON</option>
            <option value="gfs">GFS only</option>
            <option value="icon">ICON only</option>
          </select>
        </div>
        <div id="${chartContainerId}"></div>
      </div>
    `;

    // Import React and ReactDOM dynamically to render chart
    const ReactDOM = await import('react-dom/client');
    const React = await import('react');
    const chartUtils = await import('../../utils/chart/chartUtils');
    const { DischargeChart } = chartUtils;

    // Create chart root and render function
    const chartRoot = ReactDOM.createRoot(document.getElementById(chartContainerId));
    const renderChart = (selectedSeries) => {
      chartRoot.render(
        React.createElement(DischargeChart, {
          timeSeriesData: chartData,
          selectedSeries: selectedSeries,
          stationName: feature.properties.SEC_NAME || 'Station',
          height: 250
        })
      );
    };

    // Initial render with 'both' series
    renderChart('both');

    // Add series selector handler
    const seriesSelector = document.getElementById(`series-selector-${stationId}`);
    if (seriesSelector) {
      seriesSelector.onchange = (e) => {
        renderChart(e.target.value);
      };
    }

    // Enable export buttons with handlers
    const csvBtn = document.getElementById(`export-csv-btn-${stationId}`);
    const pngBtn = document.getElementById(`export-png-btn-${stationId}`);

    if (csvBtn) {
      csvBtn.disabled = false;
      csvBtn.style.opacity = '1';
      csvBtn.style.cursor = 'pointer';
      csvBtn.onmouseover = () => csvBtn.style.backgroundColor = '#0052a3';
      csvBtn.onmouseout = () => csvBtn.style.backgroundColor = '#0066cc';

      // CSV export handler
      csvBtn.onclick = () => {
        const stationName = feature.properties.SEC_NAME || 'Station';
        const csvRows = [
          ['Date', 'Time', 'GFS Discharge (m³/s)', 'ICON Discharge (m³/s)'],
          ...chartData.map(item => [
            item.time.toLocaleDateString('en-GB'),
            item.time.toLocaleTimeString('en-GB'),
            item.gfs?.toFixed(2) || '',
            item.icon?.toFixed(2) || ''
          ])
        ];

        const csvContent = csvRows.map(row => row.join(',')).join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${stationName}_discharge_data.csv`;
        link.click();
      };
    }

    if (pngBtn) {
      pngBtn.disabled = false;
      pngBtn.style.opacity = '1';
      pngBtn.style.cursor = 'pointer';
      pngBtn.onmouseover = () => pngBtn.style.backgroundColor = '#218838';
      pngBtn.onmouseout = () => pngBtn.style.backgroundColor = '#28a745';

      // PNG export handler - uses html2canvas to capture the chart
      pngBtn.onclick = async () => {
        const chartElement = document.getElementById(chartContainerId);
        if (!chartElement) return;

        try {
          // Dynamically import html2canvas
          const html2canvas = (await import('html2canvas')).default;
          const canvas = await html2canvas(chartElement, {
            backgroundColor: '#ffffff',
            scale: 2
          });

          const link = document.createElement('a');
          link.download = `discharge-forecast-${feature.properties.SEC_NAME || 'station'}-${new Date().toISOString().split('T')[0]}.png`;
          link.href = canvas.toDataURL('image/png');
          link.click();
        } catch (error) {
          console.error('Error exporting chart as PNG:', error);
        }
      };
    }
  }, []);

  // Expand chart in fullscreen modal (Google Earth Engine style)
  const expandChartView = useCallback((feature) => {
    // This will trigger the sidebar to show with the full chart
    handleStationClick(feature);
    setShowRightPanel(true);
  }, [handleStationClick]);

  // Export chart as PNG
  const exportChartAsPNG = useCallback((stationId) => {
    const canvas = document.getElementById(`chart-canvas-${stationId}`);
    if (!canvas) return;

    const link = document.createElement('a');
    link.download = `discharge-forecast-${selectedStation?.properties?.SEC_NAME || 'station'}-${new Date().toISOString().split('T')[0]}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, [selectedStation]);

  // CSV Download Handler for discharge data
  const handleDownloadCSV = useCallback(() => {
    if (!timeSeriesData || timeSeriesData.length === 0) return;

    const stationName = selectedStation?.properties?.SEC_NAME || 'Station';
    const csvRows = [
      ['Date', 'Time', 'GFS Discharge (m³/s)', 'ICON Discharge (m³/s)'],
      ...timeSeriesData.map(item => [
        item.time.toLocaleDateString('en-GB'),
        item.time.toLocaleTimeString('en-GB'),
        item.gfs?.toFixed(2) || '',
        item.icon?.toFixed(2) || ''
      ])
    ];

    const csvContent = csvRows.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${stationName}_discharge_data.csv`;
    link.click();
  }, [timeSeriesData, selectedStation]);

  // Hazard layers - Placeholder layers (same as original, disabled)
  const hazardLayersWithDate = React.useMemo(() => [
    { name: "fp_inundation map", layer: "flood_hazard", legend: null, disabled: true },
    { name: "fp_discharge", layer: "fp_discharge", legend: null, disabled: true },
    { name: "wrf_discharge", layer: "wrf_discharge", legend: null, disabled: true },
  ], []);

  // Get the appropriate date for a layer type - now uses global date for synchronization
  const getDateForLayerType = (layerConfig) => {
    if (!layerConfig.needsDate) return null;
    
    // All layers now use the global date for synchronized updates
    // Only return date if we have a valid selected date - no fallbacks
    return selectedDates?.global || null;
  };

  return (
    <Box 
      sx={{
        display: 'flex',
        height: {
          xs: 'calc(100vh - 60px - 30px)',
          md: 'calc(100vh - 80px - 30px)'
        },
        width: '100%',
        position: 'fixed',
        top: {
          xs: '60px',
          md: '80px'
        },
        bottom: '30px',
        left: 0,
        overflow: 'hidden'
      }}
    >
      {/* Mobile Drawer (slides in as overlay) */}
      <Box
        sx={{
          display: { xs: 'block', md: 'none' }
        }}
      >
        {isSidebarActive && (
          <Box
            onClick={() => setIsSidebarActive(false)}
            sx={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              zIndex: 999,
            }}
          />
        )}
        <Box
          className={`${isSidebarActive ? 'translate-x-0' : '-translate-x-full'} transition-transform duration-300 ease-in-out`}
          sx={{
            position: 'fixed',
            left: 0,
            top: {
              xs: '60px',
              md: '80px'
            },
            bottom: '30px',
            width: {
              xs: '280px',
              sm: '320px'
            },
            backgroundColor: '#f5f5f5',
            zIndex: 1000,
            overflowY: 'auto',
            boxShadow: '2px 0 8px rgba(0,0,0,0.15)'
          }}
        >
          <MuiSidebar
            hazardLayers={hazardLayersWithDate}
            impactLayers={IMPACT_LAYERS}
            ibewLayers={IBEW_LAYERS}
            boundaryLayers={BOUNDARY_LAYERS}
            selectedLayers={selectedLayers}
            selectedBoundaryLayers={selectedBoundaryLayers}
            onLayerSelect={handleLayerSelection}
            onBoundaryLayerSelect={handleBoundaryLayerSelection}
            showMonitoringStations={showMonitoringStations}
            setShowMonitoringStations={setShowMonitoringStations}
            showGeoFSM={showGeoFSM}
            setShowGeoFSM={setShowGeoFSM}
            geoFSMLoading={geoFSMLoading}
            selectedStation={selectedStation}
            showMikeHydro={showMikeHydro}
            setShowMikeHydro={setShowMikeHydro}
            showHype={showHype}
            setShowHype={setShowHype}
            adminBoundariesData={adminBoundariesData}
            showEnsemble={showEnsemble}
            setShowEnsemble={setShowEnsemble}
            onInfoClick={handleInfoClick}
            selectedDates={selectedDates}
            onDateChange={handleDateChange}
            selectedCountry={selectedCountry}
            setSelectedCountry={setSelectedCountry}
            isLoadingData={isLoadingData}
            availableDates={availableDates}
            isLayersLoading={isLayersLoading}
          />
        </Box>
      </Box>

      {/* Desktop Sidebar (fixed, always visible) */}
      <Box
        sx={{
          display: { xs: 'none', md: 'block' },
          width: isSidebarActive ? '330px' : 0,
          flexShrink: 0,
          height: '100%',
          transition: 'width 0.3s ease-in-out',
          backgroundColor: '#f5f5f5',
          borderRight: isSidebarActive ? '2px solid rgba(0, 0, 0, 0.3)' : 'none',
          overflow: 'hidden'
        }}
      >
        {isSidebarActive && (
          <MuiSidebar
            hazardLayers={hazardLayersWithDate}
            impactLayers={IMPACT_LAYERS}
            ibewLayers={IBEW_LAYERS}
            boundaryLayers={BOUNDARY_LAYERS}
            selectedLayers={selectedLayers}
            selectedBoundaryLayers={selectedBoundaryLayers}
            onLayerSelect={handleLayerSelection}
            onBoundaryLayerSelect={handleBoundaryLayerSelection}
            showMonitoringStations={showMonitoringStations}
            setShowMonitoringStations={setShowMonitoringStations}
            showGeoFSM={showGeoFSM}
            setShowGeoFSM={setShowGeoFSM}
            geoFSMLoading={geoFSMLoading}
            selectedStation={selectedStation}
            showMikeHydro={showMikeHydro}
            setShowMikeHydro={setShowMikeHydro}
            showHype={showHype}
            setShowHype={setShowHype}
            adminBoundariesData={adminBoundariesData}
            showEnsemble={showEnsemble}
            setShowEnsemble={setShowEnsemble}
            onInfoClick={handleInfoClick}
            selectedDates={selectedDates}
            onDateChange={handleDateChange}
            selectedCountry={selectedCountry}
            setSelectedCountry={setSelectedCountry}
            isLoadingData={isLoadingData}
            availableDates={availableDates}
            isLayersLoading={isLayersLoading}
          />
        )}
      </Box>

      {/* Center Panel - Map */}
      <Box
        sx={{
          flex: 1,
          position: 'relative',
          height: '100%',
          overflow: 'hidden'
        }}
      >
        {/* Hamburger Menu Button (Mobile Only) */}
        <Fab
          onClick={() => setIsSidebarActive(!isSidebarActive)}
          sx={{
            position: 'absolute',
            top: { xs: 16, sm: 20 },
            left: { xs: 16, sm: 20 },
            zIndex: 1000,
            display: { xs: 'flex', md: 'none' },
            backgroundColor: '#1B6840',
            color: 'white',
            width: { xs: 48, sm: 56 },
            height: { xs: 48, sm: 56 },
            '&:hover': {
              backgroundColor: '#145432'
            },
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
          }}
        >
          <MenuIcon />
        </Fab>

        <Box sx={{ width: '100%', height: '100%', position: 'relative' }}>
          {/* Fallback Notification Popup */}
          {showFallbackNotification && (
            <Box sx={{
              position: 'absolute',
              top: '20px',
              left: '50%',
              transform: 'translateX(-50%)',
              backgroundColor: '#fff3cd',
              border: '1px solid #ffeeba',
              borderRadius: '6px',
              p: '12px 16px',
              zIndex: 1000,
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              maxWidth: '400px',
              fontSize: '14px',
              color: '#856404',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <FontAwesomeIcon icon={faExclamationTriangle} style={{ color: '#f39c12' }} />
              <Typography component="span">{fallbackMessage}</Typography>
              <IconButton
                onClick={() => setShowFallbackNotification(false)}
                sx={{
                  ml: 'auto',
                  p: '0 4px',
                  fontSize: '18px',
                  color: '#856404'
                }}
              >
                ×
              </IconButton>
            </Box>
          )}
          <MapContainer
            center={MAP_CONFIG.initialPosition}
            zoom={MAP_CONFIG.initialZoom}
            minZoom={MAP_CONFIG.minZoom}
            maxZoom={MAP_CONFIG.maxZoom}
            maxBounds={MAP_CONFIG.maxBounds}
            maxBoundsViscosity={1.0}
            scrollWheelZoom={true}
            zoomControl={false}
            style={{ height: "100%", width: "100%" }}
            key={mapKey}
          >
            <TileLayer
              url={BASE_MAPS[0].url}
              attribution={BASE_MAPS[0].attribution}
            />

            {/* Zoom control positioned at bottom-right on mobile, top-left on desktop */}
            <ZoomControl position={isMobile ? 'bottomright' : 'topleft'} />

            {/* Map event handler for LayersControl overlay add/remove */}
            <MapEventHandler onOverlayAdd={handleOverlayAdd} onOverlayRemove={handleOverlayRemove} />

            {/* Render WMS layers with proper date handling */}
            {Array.from(selectedLayers).map((layerId) => {
              const layerConfig = [
                ...hazardLayersWithDate, 
                ...IMPACT_LAYERS, 
                ...IBEW_LAYERS
              ].find(l => l.layer === layerId);
              
              if (!layerConfig) {
                return null;
              }
              
              const layerDate = getDateForLayerType(layerConfig);
              const layerType = IMPACT_LAYERS.some(l => l.layer === layerId) ? 'impact' :
                              IBEW_LAYERS.some(l => l.layer === layerId) ? 'ibew' :
                              layerId.includes('flood_hazard') ? 'inundation' : null;
              
              return (
                <StableWMSLayer
                  key={`layer-${layerId}-${layerDate || 'no-date'}-${mapKey}`}
                  url={layerConfig.useCache ? MAP_CONFIG.mapcacheWMSUrl : MAP_CONFIG.mapserverWMSUrl}
                  layers={layerId}
                  transparent={true}
                  format="image/png"
                  version="1.1.0"
                  zIndex={100}
                  layerConfig={layerConfig}
                  selectedDate={layerDate}
                  layerType={layerType}
                  globalMapKey={mapKey}
                />
              );
            })}

            {/* TiPg Vector Tiles - Rendered in overlayPane (above basemap) */}
            {/* Render order maintained by zIndex: Rivers (100) → Lakes (200) → Admin 0 (300) → Admin 1 (400) → Admin 2 (500) */}

            {/* Rivers - Bottom layer - DEFAULT ON */}
            <TiPgVectorLayer
              collection="rivers"
              visible={activeOverlays.has('Rivers')}
              interactive={false}
              zIndex={100}
            />

            {/* Lakes/Water Bodies - Middle layer - DEFAULT ON */}
            <TiPgVectorLayer
              collection="lakes"
              visible={activeOverlays.has('Lakes (Water Bodies)')}
              interactive={false}
              zIndex={200}
            />

            {/* Admin 0 - Countries - Top layer - DEFAULT ON */}
            <TiPgVectorLayer
              collection="admin0"
              visible={activeOverlays.has('Admin 0 (Countries)')}
              interactive={false}
              zIndex={300}
            />

            {/* Admin 1 - Provinces - OFF by default */}
            <TiPgVectorLayer
              collection="admin1"
              visible={activeOverlays.has('Admin 1 (Provinces)')}
              interactive={false}
              zIndex={400}
            />

            {/* Admin 2 - Districts - OFF by default */}
            <TiPgVectorLayer
              collection="admin2"
              visible={activeOverlays.has('Admin 2 (Districts)')}
              interactive={false}
              zIndex={500}
            />

            <LayersControl
              position="topright"
              onOverlayAdd={handleOverlayAdd}
              onOverlayRemove={handleOverlayRemove}
            >
              {BASE_MAPS.map((basemap) => (
                <LayersControl.BaseLayer
                  key={basemap.name}
                  name={basemap.name}
                  checked={basemap.name === "ICPAC"}
                >
                  <TileLayer
                    url={basemap.url}
                    attribution={basemap.attribution}
                  />
                </LayersControl.BaseLayer>
              ))}

              {/* Custom Overlay Controls for TiPg Layers */}
              {/* LayerGroup components to trigger handleOverlayAdd/Remove events */}
              <LayersControl.Overlay name="Rivers" checked={true}>
                <LayerGroup />
              </LayersControl.Overlay>

              <LayersControl.Overlay name="Admin 2 (Districts)" checked={false}>
                <LayerGroup />
              </LayersControl.Overlay>

              <LayersControl.Overlay name="Lakes (Water Bodies)" checked={true}>
                <LayerGroup />
              </LayersControl.Overlay>

              <LayersControl.Overlay name="Admin 1 (Provinces)" checked={false}>
                <LayerGroup />
              </LayersControl.Overlay>

              <LayersControl.Overlay name="Admin 0 (Countries)" checked={true}>
                <LayerGroup />
              </LayersControl.Overlay>

              <LayersControl.Overlay name="Basins" checked={false}>
                <LayerGroup />
              </LayersControl.Overlay>
            </LayersControl>

            {showMonitoringStations && !isLoadingData && filteredMonitoringData?.features && filteredMonitoringData.features.length > 0 && (
              <MarkerClusterGroup
                key={`cluster-monitoring-${selectedDates?.global || 'no-date'}-${selectedCountry || 'all'}-${mapKey}-${filteredMonitoringData.features.length}`}
                maxClusterRadius={50}
                disableClusteringAtZoom={15}
                spiderfyOnMaxZoom={false}
                showCoverageOnHover={false}
                spiderLegPolylineOptions={{ weight: 1.5, color: '#222', opacity: 0.5 }}
                spiderfyDistanceMultiplier={1.5}
                iconCreateFunction={(cluster) => {
                  const markers = cluster.getAllChildMarkers();
                  const alertLevels = markers.map(marker => marker.alertStatus || 'Normal');
                  
                  // Count stations by alert level
                  const emergencyCount = alertLevels.filter(level => level === 'Emergency').length;
                  const alarmCount = alertLevels.filter(level => level === 'Alarm').length;
                  const warningCount = alertLevels.filter(level => level === 'Warning').length;
                  
                  // Determine highest severity (use balloon marker for clusters)
                  let alertStatus;
                  
                  if (emergencyCount > 0) {
                    alertStatus = 'Emergency';
                  } else if (alarmCount > 0) {
                    alertStatus = 'Alarm';
                  } else if (warningCount > 0) {
                    alertStatus = 'Warning';
                  } else {
                    alertStatus = 'Normal';
                  }
                  
                  // Return a larger balloon marker for the cluster (isCluster=true)
                  return getMarkerIcon(alertStatus, true, markers.length, false);
                }}
              >
                <GeoJSON
                  key={`monitoring-stations-${selectedDates?.global || 'no-date'}-${selectedCountry || 'all'}-${mapKey}-${filteredMonitoringData.features.length}`}
                  data={filteredMonitoringData}
                  pointToLayer={(feature, latlng) => {
                    const isSelected = selectedStation?.properties?.SEC_NAME === feature.properties.SEC_NAME;
                    
                    // Calculate current discharge the same way as the legend
                    let currentDischarge = null;
                    const gfsData = feature.properties["time_series_discharge_simulated-gfs"];
                    const iconData = feature.properties["time_series_discharge_simulated-icon"];
                    
                    if (gfsData || iconData) {
                      let latestGfs = 0;
                      let latestIcon = 0;
                      
                      if (gfsData) {
                        const gfsValues = gfsData.split(",").map(val => Number(val.trim()) || 0);
                        latestGfs = gfsValues[gfsValues.length - 1] || 0;
                      }
                      
                      if (iconData) {
                        const iconValues = iconData.split(",").map(val => Number(val.trim()) || 0);
                        latestIcon = iconValues[iconValues.length - 1] || 0;
                      }
                      
                      currentDischarge = Math.max(latestGfs, latestIcon);
                    }
                    
                    // Use the same alert status calculation as the legend for consistency
                    const alertStatus = getAlertStatus(feature, currentDischarge);
                    
                    // Use balloon marker icon
                    const markerIcon = getMarkerIcon(alertStatus, false, 0, isSelected);
                    
                    const marker = L.marker(latlng, {
                      icon: markerIcon
                    });
                    
                    // Store alert status for clustering
                    marker.alertStatus = alertStatus;
                    
                    return marker;
                  }}
                  onEachFeature={(feature, layer) => {
                    layer.on({ click: (e) => handleStationClick(feature, e) });
                    const props = feature.properties;
                    
                    // Recalculate discharge and alert status for popup
                    const dischargeGFS = feature.properties["time_series_discharge_simulated-gfs"];
                    let currentDischarge = 0;
                    
                    if (dischargeGFS) {
                      const gfsValues = dischargeGFS.split(',').map(v => parseFloat(v)).filter(v => v !== -9998 && !isNaN(v));
                      currentDischarge = gfsValues[gfsValues.length - 1] || 0;
                    }
                    
                    // Calculate alert status based on thresholds
                    let alertStatus = 'Normal';
                    const alertThreshold = parseFloat(feature.properties.Q_THR1 || 0);
                    const alarmThreshold = parseFloat(feature.properties.Q_THR2 || 0);
                    const emergencyThreshold = parseFloat(feature.properties.Q_THR3 || 0);
                    
                    if (currentDischarge >= emergencyThreshold && emergencyThreshold > 0) {
                      alertStatus = 'Emergency';
                    } else if (currentDischarge >= alarmThreshold && alarmThreshold > 0) {
                      alertStatus = 'Alarm';
                    } else if (currentDischarge >= alertThreshold && alertThreshold > 0) {
                      alertStatus = 'Warning';
                    }
                    
                    const discharge = currentDischarge.toFixed(2);
                    const popupContent = `
                      <div class="station-popup" style="min-width: 450px; max-width: 500px;">
                        <div style="background-color: #f8f9fa; padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                          <h3 style="margin: 0 0 10px 0; color: #1B6840; font-size: 16px;">${props.SEC_NAME || "Station"}</h3>
                          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px;">
                            <div><strong>Basin:</strong> ${props.BASIN || "N/A"}</div>
                            <div><strong>Status:</strong> <span style="padding: 2px 8px; border-radius: 4px; background-color: ${alertStatus === 'Normal' ? '#d4edda' : alertStatus === 'Alert' ? '#fff3cd' : '#f8d7da'}; color: ${alertStatus === 'Normal' ? '#155724' : alertStatus === 'Alert' ? '#856404' : '#721c24'};">${alertStatus}</span></div>
                            <div><strong>Discharge:</strong> ${discharge} m³/s</div>
                            <div><strong>Alert:</strong> ${alertThreshold.toFixed(1)} m³/s</div>
                            <div><strong>Alarm:</strong> ${alarmThreshold.toFixed(1)} m³/s</div>
                            <div><strong>Emergency:</strong> ${emergencyThreshold.toFixed(1)} m³/s</div>
                          </div>
                        </div>

                        <div id="popup-chart-container-${props.ID}" style="background-color: white; padding: 10px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 12px; min-height: 250px;">
                          <div style="text-align: center; padding: 20px; color: #666;">
                            <p style="margin: 0;">Click "Show Chart" to view discharge forecast</p>
                          </div>
                        </div>

                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;">
                          <button
                            id="show-chart-btn-${props.ID}"
                            style="padding: 8px 12px; background-color: #1B6840; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; font-size: 12px;"
                            onmouseover="this.style.backgroundColor='#145432'"
                            onmouseout="this.style.backgroundColor='#1B6840'"
                          >
                            📊 Show Chart
                          </button>
                          <button
                            id="export-csv-btn-${props.ID}"
                            style="padding: 8px 12px; background-color: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; font-size: 12px; opacity: 0.5;"
                            disabled
                          >
                            📄 Export CSV
                          </button>
                          <button
                            id="export-png-btn-${props.ID}"
                            style="padding: 8px 12px; background-color: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; font-size: 12px; opacity: 0.5;"
                            disabled
                          >
                            🖼️ Export PNG
                          </button>
                        </div>

                        <button
                          id="generate-report-btn-${props.ID}"
                          style="margin-top: 10px; padding: 8px 15px; background-color: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; width: 100%; font-size: 13px;"
                          onmouseover="this.style.backgroundColor='#5a6268'"
                          onmouseout="this.style.backgroundColor='#6c757d'"
                        >
                          📋 Generate Full Report
                        </button>
                      </div>`;

                    const popup = L.popup({
                      maxWidth: 550,
                      minWidth: 450,
                      autoPan: true,
                      autoPanPadding: [50, 50],
                      keepInView: true,
                      autoPanPaddingTopLeft: [10, 100],
                      autoPanPaddingBottomRight: [10, 10],
                      offset: [0, -10]
                    }).setContent(popupContent);
                    layer.bindPopup(popup);

                    // Add event listeners when popup opens
                    layer.on('popupopen', (e) => {
                      const stationId = props.ID;

                      // Adjust popup position based on marker location
                      const map = e.target._map;
                      const popupLatLng = e.popup.getLatLng();
                      const point = map.latLngToContainerPoint(popupLatLng);
                      const mapSize = map.getSize();

                      // If marker is in top 30% of screen, open popup below marker
                      if (point.y < mapSize.y * 0.3) {
                        e.popup.options.offset = [0, 30]; // Offset downward (larger for bigger popup)
                        e.popup.update();
                      }

                      // Show Chart button
                      const showChartBtn = document.getElementById(`show-chart-btn-${stationId}`);
                      if (showChartBtn) {
                        showChartBtn.onclick = () => {
                          handleStationClick(feature);
                          renderChartInPopup(feature, stationId, selectedDates?.global);
                        };
                      }

                      // Export CSV button
                      const exportCsvBtn = document.getElementById(`export-csv-btn-${stationId}`);
                      if (exportCsvBtn) {
                        exportCsvBtn.onclick = () => handleDownloadCSV();
                      }

                      // Export PNG button
                      const exportPngBtn = document.getElementById(`export-png-btn-${stationId}`);
                      if (exportPngBtn) {
                        exportPngBtn.onclick = () => exportChartAsPNG(stationId);
                      }

                      // Generate Report button
                      const reportBtn = document.getElementById(`generate-report-btn-${stationId}`);
                      if (reportBtn) {
                        reportBtn.onclick = () => generateReport(feature);
                      }
                    });
                  }}
                />
              </MarkerClusterGroup>
            )}
            {showGeoFSM && filteredGeosfmData?.features && (
              <GeoJSON
                key={`geofsm-points-${filteredGeosfmData.features.length}`}
                data={filteredGeosfmData}
                pointToLayer={(feature, latlng) => {
                  const isSelected =
                    selectedStation?.properties?.Id === feature.properties.Id;
                  
                  // Use same marker system as FloodProofs stations
                  const alertStatus = 'Normal'; // GeoSFM stations are typically normal status
                  const markerIcon = getMarkerIcon(alertStatus, false, 0, isSelected);
                  
                  return L.marker(latlng, { icon: markerIcon });
                }}
                onEachFeature={(feature, layer) => {
                  const props = feature.properties;
                  layer.bindPopup(
                    `<div class="geofsm-popup"><strong>${props.Name || "GeoFSM Point"}</strong><br/>Description: ${props.Descriptio || "N/A"}<br/>Gridcode: ${props.Gridcode || "N/A"}<br/>Latitude: ${props.Y?.toFixed(4) || "N/A"}°N<br/>Longitude: ${props.X?.toFixed(4) || "N/A"}°E<br/>ID: ${props.Id || "N/A"}</div>`,
                    {
                      autoPan: true,
                      autoPanPadding: [50, 50],
                      maxWidth: 300,
                      keepInView: true
                    }
                  );
                  layer.on({ click: (e) => handleStationClick(feature, e) });
                }}
              />
            )}

            {/* Ensemble Control Points Layer */}
            {showEnsemble && ensembleData && (
              <EnsembleLayer
                data={ensembleData}
                selectedCountry={selectedCountry}
                adminBoundariesData={adminBoundariesData}
              />
            )}

            {/* IBEW Popup Handler - replaces old FeatureInfoHandler */}
            <IBEWPopupHandler
              selectedLayers={selectedLayers}
              selectedDate={selectedDates?.ibew}
              mapConfig={MAP_CONFIG}
            />
            
            {/* Country Mask - Clips map to selected country */}
            <CountryMask 
              adminData={adminBoundariesData}
              selectedCountry={selectedCountry}
            />
            
            {/* Country Zoom Handler - Zooms to selected country */}
            <CountryZoomHandler 
              adminData={adminBoundariesData}
              selectedCountry={selectedCountry}
            />
            
          </MapContainer>
          
          {/* Alert Status Legend (FP_EA) */}
          {showMonitoringStations && filteredMonitoringData?.features && (
            <AlertStatusLegend
              monitoringData={filteredMonitoringData}
              geoFSMData={filteredGeosfmData}
              showGeoFSM={showGeoFSM}
            />
          )}

          {/* Multi-modal Legend */}
          {showEnsemble && ensembleData?.features && (
            <MultimodalLegend
              ensembleData={ensembleData}
              selectedCountry={selectedCountry}
              adminBoundariesData={adminBoundariesData}
            />
          )}

          {activeLegend && (
            <div className="map-legend" style={{
              position: 'absolute',
              bottom: '50px', // Start properly above footer
              left: '240px', // Positioned next to monitoring legend to avoid overlap
              backgroundColor: 'white',
              padding: '15px',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              zIndex: 1000,
              maxWidth: '300px'
            }}>
              <MapLegend
                legendUrl={activeLegend}
                title={
                  [...hazardLayersWithDate, ...IMPACT_LAYERS, ...IBEW_LAYERS, ...BOUNDARY_LAYERS].find(
                    (layer) => layer.legend === activeLegend,
                  )?.name || "Legend"
                }
              />
            </div>
          )}

        </Box>
      </Box>


      {/* HIDDEN: Old bottom chart panel for reference */}
      <Box sx={{ display: 'none' }}>
        {false && (
          <Box sx={{
            position: 'fixed',
            bottom: panelPosition.y ? 'auto' : '30px',
            top: panelPosition.y ? `${panelPosition.y}px` : 'auto',
            left: `${(isSidebarActive ? (isMobile ? 0 : 350) : 0) + panelPosition.x}px`,
            right: (panelPosition.x || panelPosition.y) ? 'auto' : '0px',
            width: (panelPosition.x || panelPosition.y) ? `${panelWidth}px` : 'auto',
            height: `${panelHeight}px`,
            backgroundColor: 'white',
            border: '1px solid #ddd',
            borderBottom: 'none',
            borderTop: '2px solid #1B6840',
            boxShadow: '0 -4px 12px rgba(0, 0, 0, 0.15)',
            zIndex: 1100,
            display: 'block',
            borderRadius: (panelPosition.x || panelPosition.y) ? '8px' : '0'
          }}>
            {/* Resize Handles - only show when panel is dragged/floating */}
            {(panelPosition.x || panelPosition.y) && (
              <>
                {/* Top */}
                <Box
                  onMouseDown={(e) => handleResizeStart('top', e)}
                  sx={{
                    position: 'absolute',
                    top: '-4px',
                    left: '8px',
                    right: '8px',
                    height: '8px',
                    cursor: 'ns-resize',
                    backgroundColor: 'transparent',
                    zIndex: 902
                  }}
                />
                {/* Bottom */}
                <Box
                  onMouseDown={(e) => handleResizeStart('bottom', e)}
                  sx={{
                    position: 'absolute',
                    bottom: '-4px',
                    left: '8px',
                    right: '8px',
                    height: '8px',
                    cursor: 'ns-resize',
                    backgroundColor: 'transparent',
                    zIndex: 902
                  }}
                />
                {/* Left */}
                <Box
                  onMouseDown={(e) => handleResizeStart('left', e)}
                  sx={{
                    position: 'absolute',
                    left: '-4px',
                    top: '8px',
                    bottom: '8px',
                    width: '8px',
                    cursor: 'ew-resize',
                    backgroundColor: 'transparent',
                    zIndex: 902
                  }}
                />
                {/* Right */}
                <Box
                  onMouseDown={(e) => handleResizeStart('right', e)}
                  sx={{
                    position: 'absolute',
                    right: '-4px',
                    top: '8px',
                    bottom: '8px',
                    width: '8px',
                    cursor: 'ew-resize',
                    backgroundColor: 'transparent',
                    zIndex: 902
                  }}
                />
                {/* Top-Left Corner */}
                <Box
                  onMouseDown={(e) => handleResizeStart('top-left', e)}
                  sx={{
                    position: 'absolute',
                    top: '-4px',
                    left: '-4px',
                    width: '12px',
                    height: '12px',
                    cursor: 'nw-resize',
                    backgroundColor: 'transparent',
                    zIndex: 903
                  }}
                />
                {/* Top-Right Corner */}
                <Box
                  onMouseDown={(e) => handleResizeStart('top-right', e)}
                  sx={{
                    position: 'absolute',
                    top: '-4px',
                    right: '-4px',
                    width: '12px',
                    height: '12px',
                    cursor: 'ne-resize',
                    backgroundColor: 'transparent',
                    zIndex: 903
                  }}
                />
                {/* Bottom-Left Corner */}
                <Box
                  onMouseDown={(e) => handleResizeStart('bottom-left', e)}
                  sx={{
                    position: 'absolute',
                    bottom: '-4px',
                    left: '-4px',
                    width: '12px',
                    height: '12px',
                    cursor: 'sw-resize',
                    backgroundColor: 'transparent',
                    zIndex: 903
                  }}
                />
                {/* Bottom-Right Corner */}
                <Box
                  onMouseDown={(e) => handleResizeStart('bottom-right', e)}
                  sx={{
                    position: 'absolute',
                    bottom: '-4px',
                    right: '-4px',
                    width: '12px',
                    height: '12px',
                    cursor: 'se-resize',
                    backgroundColor: 'transparent',
                    zIndex: 903
                  }}
                />
              </>
            )}
            
            {/* Original resize handle for docked position */}
            {!panelPosition.x && !panelPosition.y && (
              <Box
                onMouseDown={(e) => handleResizeStart('top', e)}
                sx={{
                  position: 'absolute',
                  top: '-5px',
                  left: '0',
                  right: '0',
                  height: '10px',
                  cursor: 'ns-resize',
                  backgroundColor: 'transparent',
                  zIndex: 901,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <Box sx={{
                  width: '80px',
                  height: '4px',
                  backgroundColor: '#ccc',
                  borderRadius: '2px',
                  transition: 'background-color 0.2s',
                  '&:hover': {
                    backgroundColor: '#999'
                  }
                }} />
              </Box>
            )}
            <Box 
              onMouseDown={handleDragStart}
              sx={{
                cursor: 'move',
                userSelect: 'none',
                background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                borderBottom: '1px solid #ddd',
                p: '10px 16px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Box sx={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: '2px',
                  opacity: 0.6 
                }}>
                  <Box sx={{ width: '4px', height: '4px', backgroundColor: '#666', borderRadius: '50%' }} />
                  <Box sx={{ width: '4px', height: '4px', backgroundColor: '#666', borderRadius: '50%' }} />
                  <Box sx={{ width: '4px', height: '4px', backgroundColor: '#666', borderRadius: '50%' }} />
                </Box>
                <Typography variant="h6" sx={{ m: 0, fontSize: '1rem' }}>
                  {selectedStation?.properties?.SEC_NAME ||
                    (chartType === "riverdepth" || chartType === "streamflow"
                      ? `${selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station'} - ${geoFSMDataType === 'riverdepth' ? 'River Depth' : 'Streamflow'}`
                      : "Discharge Forecast")}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {(chartType === "riverdepth" || chartType === "streamflow") && (
                  <Box 
                    sx={{ zIndex: 1000, position: 'relative' }}
                    onMouseDown={(e) => e.stopPropagation()}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Box
                      component="select"
                      value={geoFSMDataType}
                      onChange={(e) => {
                        setGeoFSMDataType(e.target.value);
                      }}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                      sx={{ 
                        mr: "10px", 
                        p: "6px 12px",
                        border: "2px solid #1976D2",
                        borderRadius: "4px",
                        backgroundColor: "#E3F2FD",
                        color: "#1976D2",
                        fontWeight: "500",
                        minWidth: "140px",
                        fontSize: "14px",
                        cursor: "pointer",
                        zIndex: 1001,
                        position: "relative",
                        pointerEvents: "auto",
                        boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                        transition: "all 0.2s ease",
                        '&:hover': {
                          backgroundColor: "#BBDEFB",
                          borderColor: "#0D47A1"
                        }
                      }}
                    >
                      <option value="riverdepth">River Depth</option>
                      <option value="streamflow">Streamflow</option>
                    </Box>
                  </Box>
                )}
                
                {/* Export buttons */}
                <Button
                  onClick={() => {
                    if (chartType === "riverdepth" || chartType === "streamflow") {
                      const stationName = selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station';
                      const csvData = geoFSMTimeSeriesData.map(item => ({
                        Date: new Date(item.timestamp).toISOString().split('T')[0],
                        [`${chartType === 'riverdepth' ? 'River Depth' : 'Streamflow'} (${chartType === 'riverdepth' ? 'm' : 'm³/s'})`]: item[chartType === 'riverdepth' ? 'depth' : 'streamflow'] || ''
                      }));
                      const headers = Object.keys(csvData[0]).join(',');
                      const csvContent = [
                        `# ${stationName} - ${chartType}`,
                        `# Generated on: ${new Date().toLocaleString()}`,
                        headers,
                        ...csvData.map(row => Object.values(row).join(','))
                      ].join('\n');
                      const blob = new Blob([csvContent], { type: 'text/csv' });
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${stationName}_${chartType}.csv`;
                      a.click();
                      window.URL.revokeObjectURL(url);
                    } else {
                      const stationName = selectedStation?.properties?.SEC_NAME || 'FloodProofs Station';
                      const csvData = timeSeriesData.map(item => ({
                        Date: item.time.toISOString().split('T')[0],
                        'GFS Forecast (m³/s)': item.gfs || '',
                        'ICON Forecast (m³/s)': item.icon || ''
                      }));
                      const headers = Object.keys(csvData[0]).join(',');
                      const csvContent = [
                        `# ${stationName} - discharge_forecast`,
                        `# Generated on: ${new Date().toLocaleString()}`,
                        headers,
                        ...csvData.map(row => Object.values(row).join(','))
                      ].join('\n');
                      const blob = new Blob([csvContent], { type: 'text/csv' });
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${stationName}_discharge_forecast.csv`;
                      a.click();
                      window.URL.revokeObjectURL(url);
                    }
                  }}
                  sx={{
                    p: '4px 8px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    fontSize: '11px',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: '#218838'
                    }
                  }}
                >
                  📊 CSV
                </Button>
                
                <Button
                  onClick={() => {
                    // FloodProofs: Create professional 3-chart layout
                    if (chartType === "discharge" && timeSeriesData && timeSeriesData.length > 0) {
                      const canvas = document.createElement('canvas');
                      const ctx = canvas.getContext('2d');
                      
                      canvas.width = 1200;
                      canvas.height = 900;
                      
                      // Fill background
                      ctx.fillStyle = 'white';
                      ctx.fillRect(0, 0, canvas.width, canvas.height);
                      
                      const stationName = selectedStation?.properties?.SEC_NAME || 'FloodProofs Station';
                      
                      // Header section
                      ctx.fillStyle = '#f8f9fa';
                      ctx.fillRect(0, 0, canvas.width, 80);
                      ctx.strokeStyle = '#dee2e6';
                      ctx.lineWidth = 1;
                      ctx.strokeRect(0, 0, canvas.width, canvas.height);
                      ctx.strokeRect(0, 0, canvas.width, 80);
                      
                      // Title
                      ctx.fillStyle = '#1B6840';
                      ctx.font = 'bold 20px Arial';
                      ctx.fillText(`${stationName} - Discharge Forecast Analysis`, 20, 25);
                      
                      // Station details
                      ctx.fillStyle = '#333';
                      ctx.font = '12px Arial';
                      const basin = selectedStation?.properties?.BASIN || 'N/A';
                      const area = selectedStation?.properties?.AREA || 'N/A';
                      const lat = selectedStation?.properties?.latitude?.toFixed(4) || 'N/A';
                      const lng = selectedStation?.properties?.longitude?.toFixed(4) || 'N/A';
                      
                      ctx.fillText(`Basin: ${basin} | Area: ${area} km² | Location: ${lat}°N, ${lng}°E`, 20, 45);
                      
                      // Thresholds
                      const alertThreshold = selectedStation?.properties?.Q_THR1 || 'N/A';
                      const alarmThreshold = selectedStation?.properties?.Q_THR2 || 'N/A';
                      const emergencyThreshold = selectedStation?.properties?.Q_THR3 || 'N/A';
                      
                      ctx.fillStyle = '#ff9800';
                      ctx.fillText(`Alert: ${alertThreshold} m³/s`, 20, 62);
                      ctx.fillStyle = '#f44336';
                      ctx.fillText(`| Alarm: ${alarmThreshold} m³/s`, 150, 62);
                      ctx.fillStyle = '#d32f2f';
                      ctx.fillText(`| Emergency: ${emergencyThreshold} m³/s`, 300, 62);
                      
                      // Branding
                      ctx.fillStyle = '#1B6840';
                      ctx.font = 'bold 14px Arial';
                      ctx.fillText('East Africa Flood Watch | IGAD-ICPAC', canvas.width - 320, 25);
                      ctx.fillStyle = '#666';
                      ctx.font = '10px Arial';
                      ctx.fillText(`Generated: ${new Date().toLocaleString()}`, canvas.width - 200, 45);
                      
                      // Chart dimensions
                      const chartWidth = 540;
                      const chartHeight = 240;
                      const margin = { top: 40, right: 40, bottom: 60, left: 80 };
                      
                      // Helper function to draw professional chart
                      const drawProfessionalChart = (x, y, data, title, isLine = true, modelKey = null) => {
                        // Chart background
                        ctx.fillStyle = 'white';
                        ctx.fillRect(x, y, chartWidth, chartHeight);
                        ctx.strokeStyle = '#e0e0e0';
                        ctx.lineWidth = 1;
                        ctx.strokeRect(x, y, chartWidth, chartHeight);
                        
                        // Plot area
                        const plotX = x + margin.left;
                        const plotY = y + margin.top;
                        const plotWidth = chartWidth - margin.left - margin.right;
                        const plotHeight = chartHeight - margin.top - margin.bottom;
                        
                        // Title
                        ctx.fillStyle = '#333';
                        ctx.font = 'bold 14px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText(title, x + chartWidth / 2, y + 20);
                        ctx.textAlign = 'left';
                        
                        if (isLine) {
                          // Line chart for individual models
                          const maxValue = Math.max(...data.map(d => d[modelKey]));
                          const yScale = plotHeight / (maxValue * 1.1);
                          const xScale = plotWidth / (data.length - 1);
                          
                          // Grid lines
                          ctx.strokeStyle = '#f0f0f0';
                          ctx.lineWidth = 1;
                          for (let i = 0; i <= 5; i++) {
                            const gridY = plotY + plotHeight - (i * plotHeight / 5);
                            ctx.beginPath();
                            ctx.moveTo(plotX, gridY);
                            ctx.lineTo(plotX + plotWidth, gridY);
                            ctx.stroke();
                          }
                          
                          // Y-axis
                          ctx.strokeStyle = '#333';
                          ctx.lineWidth = 2;
                          ctx.beginPath();
                          ctx.moveTo(plotX, plotY);
                          ctx.lineTo(plotX, plotY + plotHeight);
                          ctx.stroke();
                          
                          // X-axis
                          ctx.beginPath();
                          ctx.moveTo(plotX, plotY + plotHeight);
                          ctx.lineTo(plotX + plotWidth, plotY + plotHeight);
                          ctx.stroke();
                          
                          // Y-axis labels
                          ctx.fillStyle = '#666';
                          ctx.font = '10px Arial';
                          ctx.textAlign = 'right';
                          for (let i = 0; i <= 5; i++) {
                            const value = (maxValue * i) / 5;
                            const labelY = plotY + plotHeight - (i * plotHeight / 5);
                            ctx.fillText(value.toFixed(1), plotX - 10, labelY + 3);
                          }
                          
                          // Y-axis title
                          ctx.save();
                          ctx.translate(plotX - 50, plotY + plotHeight / 2);
                          ctx.rotate(-Math.PI / 2);
                          ctx.font = 'bold 12px Arial';
                          ctx.textAlign = 'center';
                          ctx.fillText('Discharge (m³/s)', 0, 0);
                          ctx.restore();
                          
                          // X-axis labels (dates)
                          ctx.textAlign = 'center';
                          ctx.font = '9px Arial';
                          data.forEach((point, i) => {
                            if (i % Math.ceil(data.length / 6) === 0) {
                              const labelX = plotX + (i * xScale);
                              ctx.save();
                              ctx.translate(labelX, plotY + plotHeight + 15);
                              ctx.rotate(-Math.PI / 6);
                              ctx.fillText(point.time.toLocaleDateString('en-GB'), 0, 0);
                              ctx.restore();
                            }
                          });
                          
                          // Draw line
                          const color = modelKey === 'gfs' ? '#1f77b4' : '#ff7f0e';
                          ctx.strokeStyle = color;
                          ctx.lineWidth = 3;
                          ctx.beginPath();
                          
                          data.forEach((point, i) => {
                            const pointX = plotX + (i * xScale);
                            const pointY = plotY + plotHeight - (point[modelKey] * yScale);
                            
                            if (i === 0) ctx.moveTo(pointX, pointY);
                            else ctx.lineTo(pointX, pointY);
                          });
                          ctx.stroke();
                          
                          // Draw points
                          ctx.fillStyle = color;
                          data.forEach((point, i) => {
                            const pointX = plotX + (i * xScale);
                            const pointY = plotY + plotHeight - (point[modelKey] * yScale);
                            ctx.beginPath();
                            ctx.arc(pointX, pointY, 3, 0, 2 * Math.PI);
                            ctx.fill();
                          });
                        } else {
                          // Bar chart for comparison
                          const recentData = data.slice(-7);
                          const maxValue = Math.max(...recentData.flatMap(d => [d.gfs, d.icon]));
                          const yScale = plotHeight / (maxValue * 1.1);
                          const barGroupWidth = plotWidth / recentData.length;
                          const barWidth = barGroupWidth * 0.35;
                          
                          // Grid lines
                          ctx.strokeStyle = '#f0f0f0';
                          ctx.lineWidth = 1;
                          for (let i = 0; i <= 5; i++) {
                            const gridY = plotY + plotHeight - (i * plotHeight / 5);
                            ctx.beginPath();
                            ctx.moveTo(plotX, gridY);
                            ctx.lineTo(plotX + plotWidth, gridY);
                            ctx.stroke();
                          }
                          
                          // Axes
                          ctx.strokeStyle = '#333';
                          ctx.lineWidth = 2;
                          ctx.beginPath();
                          ctx.moveTo(plotX, plotY);
                          ctx.lineTo(plotX, plotY + plotHeight);
                          ctx.moveTo(plotX, plotY + plotHeight);
                          ctx.lineTo(plotX + plotWidth, plotY + plotHeight);
                          ctx.stroke();
                          
                          // Y-axis labels
                          ctx.fillStyle = '#666';
                          ctx.font = '10px Arial';
                          ctx.textAlign = 'right';
                          for (let i = 0; i <= 5; i++) {
                            const value = (maxValue * i) / 5;
                            const labelY = plotY + plotHeight - (i * plotHeight / 5);
                            ctx.fillText(value.toFixed(1), plotX - 10, labelY + 3);
                          }
                          
                          // Y-axis title
                          ctx.save();
                          ctx.translate(plotX - 50, plotY + plotHeight / 2);
                          ctx.rotate(-Math.PI / 2);
                          ctx.font = 'bold 12px Arial';
                          ctx.textAlign = 'center';
                          ctx.fillText('Discharge (m³/s)', 0, 0);
                          ctx.restore();
                          
                          // Draw bars
                          recentData.forEach((dataPoint, i) => {
                            const groupX = plotX + (i * barGroupWidth) + barGroupWidth * 0.1;
                            
                            // GFS bar
                            const gfsHeight = dataPoint.gfs * yScale;
                            ctx.fillStyle = '#1f77b4';
                            ctx.fillRect(groupX, plotY + plotHeight - gfsHeight, barWidth, gfsHeight);
                            
                            // ICON bar
                            const iconHeight = dataPoint.icon * yScale;
                            ctx.fillStyle = '#ff7f0e';
                            ctx.fillRect(groupX + barWidth + 2, plotY + plotHeight - iconHeight, barWidth, iconHeight);
                            
                            // Date label
                            ctx.fillStyle = '#666';
                            ctx.font = '9px Arial';
                            ctx.textAlign = 'center';
                            ctx.save();
                            ctx.translate(groupX + barWidth, plotY + plotHeight + 15);
                            ctx.rotate(-Math.PI / 6);
                            ctx.fillText(dataPoint.time.toLocaleDateString('en-GB'), 0, 0);
                            ctx.restore();
                          });
                        }
                        ctx.textAlign = 'left';
                      };
                      
                      // Draw charts
                      drawProfessionalChart((canvas.width - chartWidth) / 2, 100, timeSeriesData, 'Model Comparison (Last 7 Days)', false);
                      drawProfessionalChart(30, 380, timeSeriesData, 'GFS Model Forecast', true, 'gfs');
                      drawProfessionalChart(630, 380, timeSeriesData, 'ICON Model Forecast', true, 'icon');
                      
                      // Legend
                      const legendY = 650;
                      ctx.fillStyle = '#1f77b4';
                      ctx.fillRect(canvas.width / 2 - 80, legendY, 15, 15);
                      ctx.fillStyle = '#333';
                      ctx.font = '12px Arial';
                      ctx.fillText('GFS Model', canvas.width / 2 - 60, legendY + 12);
                      
                      ctx.fillStyle = '#ff7f0e';
                      ctx.fillRect(canvas.width / 2 + 10, legendY, 15, 15);
                      ctx.fillText('ICON Model', canvas.width / 2 + 30, legendY + 12);
                      
                      const link = document.createElement('a');
                      link.download = `${stationName}_forecast_analysis.png`;
                      link.href = canvas.toDataURL();
                      link.click();
                      return;
                    }
                    
                    // GeoSFM: Professional vertical stacked layout (depth and streamflow)
                    if ((chartType === "riverdepth" || chartType === "streamflow") && geoFSMTimeSeriesData && geoFSMTimeSeriesData.length > 0) {
                      const canvas = document.createElement('canvas');
                      const ctx = canvas.getContext('2d');
                      
                      canvas.width = 1000;
                      canvas.height = 900;
                      
                      // Fill background
                      ctx.fillStyle = 'white';
                      ctx.fillRect(0, 0, canvas.width, canvas.height);
                      
                      const stationName = selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station';
                      
                      // Header section with centered branding
                      ctx.fillStyle = '#1B6840';
                      ctx.font = 'bold 24px Arial';
                      ctx.textAlign = 'center';
                      ctx.fillText('IGAD-ICPAC East Africa Flood Watch', canvas.width / 2, 30);
                      
                      // Station title
                      ctx.font = 'bold 18px Arial';
                      ctx.fillText(`${stationName} - GeoSFM Monitoring Data`, canvas.width / 2, 60);
                      
                      // Generation date
                      ctx.fillStyle = '#666';
                      ctx.font = '12px Arial';
                      ctx.fillText(`Generated: ${new Date().toLocaleDateString('en-GB', {day: 'numeric', month: 'long', year: 'numeric'})}`, canvas.width / 2, 80);
                      
                      ctx.textAlign = 'left';
                      
                      // Chart dimensions
                      const chartWidth = 900;
                      const chartHeight = 320;
                      const margin = { top: 60, right: 120, bottom: 80, left: 80 };
                      
                      // Helper function to draw professional GeoSFM chart with legend
                      const drawProfessionalGeoSFMChart = (x, y, dataKey, color, title, unit) => {
                        // Plot area
                        const plotX = x + margin.left;
                        const plotY = y + margin.top;
                        const plotWidth = chartWidth - margin.left - margin.right;
                        const plotHeight = chartHeight - margin.top - margin.bottom;
                        
                        // Title
                        ctx.fillStyle = '#333';
                        ctx.font = 'bold 16px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText(`${title} (${unit})`, x + chartWidth / 2, y + 25);
                        ctx.textAlign = 'left';
                        
                        // Get data values
                        const values = geoFSMTimeSeriesData.map(d => d[dataKey] || 0);
                        const maxValue = Math.max(...values);
                        const yScale = plotHeight / (maxValue * 1.1);
                        const xScale = plotWidth / (geoFSMTimeSeriesData.length - 1);
                        
                        // Grid lines
                        ctx.strokeStyle = '#f0f0f0';
                        ctx.lineWidth = 1;
                        for (let i = 0; i <= 6; i++) {
                          const gridY = plotY + plotHeight - (i * plotHeight / 6);
                          ctx.beginPath();
                          ctx.moveTo(plotX, gridY);
                          ctx.lineTo(plotX + plotWidth, gridY);
                          ctx.stroke();
                        }
                        
                        // Y-axis
                        ctx.strokeStyle = '#333';
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.moveTo(plotX, plotY);
                        ctx.lineTo(plotX, plotY + plotHeight);
                        ctx.stroke();
                        
                        // X-axis
                        ctx.beginPath();
                        ctx.moveTo(plotX, plotY + plotHeight);
                        ctx.lineTo(plotX + plotWidth, plotY + plotHeight);
                        ctx.stroke();
                        
                        // Y-axis labels
                        ctx.fillStyle = '#666';
                        ctx.font = '11px Arial';
                        ctx.textAlign = 'right';
                        for (let i = 0; i <= 6; i++) {
                          const value = (maxValue * i) / 6;
                          const labelY = plotY + plotHeight - (i * plotHeight / 6);
                          ctx.fillText(value.toFixed(1), plotX - 10, labelY + 4);
                        }
                        
                        // Y-axis title
                        ctx.save();
                        ctx.translate(plotX - 50, plotY + plotHeight / 2);
                        ctx.rotate(-Math.PI / 2);
                        ctx.font = 'bold 12px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillText(`${title} (${unit})`, 0, 0);
                        ctx.restore();
                        
                        // X-axis labels (dates)
                        ctx.textAlign = 'center';
                        ctx.font = '10px Arial';
                        ctx.fillStyle = '#666';
                        geoFSMTimeSeriesData.forEach((point, i) => {
                          if (i % Math.ceil(geoFSMTimeSeriesData.length / 10) === 0) {
                            const labelX = plotX + (i * xScale);
                            const date = new Date(point.timestamp);
                            const dateStr = date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
                            ctx.fillText(dateStr, labelX, plotY + plotHeight + 15);
                          }
                        });
                        
                        // X-axis title
                        ctx.font = 'bold 12px Arial';
                        ctx.textAlign = 'center';
                        ctx.fillStyle = '#333';
                        ctx.fillText('Date', plotX + plotWidth / 2, plotY + plotHeight + 40);
                        
                        // Draw line
                        ctx.strokeStyle = color;
                        ctx.lineWidth = 3;
                        ctx.beginPath();
                        
                        geoFSMTimeSeriesData.forEach((point, i) => {
                          const pointX = plotX + (i * xScale);
                          const pointY = plotY + plotHeight - ((point[dataKey] || 0) * yScale);
                          
                          if (i === 0) ctx.moveTo(pointX, pointY);
                          else ctx.lineTo(pointX, pointY);
                        });
                        ctx.stroke();
                        
                        // Draw points
                        ctx.fillStyle = color;
                        geoFSMTimeSeriesData.forEach((point, i) => {
                          const pointX = plotX + (i * xScale);
                          const pointY = plotY + plotHeight - ((point[dataKey] || 0) * yScale);
                          ctx.beginPath();
                          ctx.arc(pointX, pointY, 3, 0, 2 * Math.PI);
                          ctx.fill();
                        });
                        
                        // Legend box
                        const legendX = plotX + plotWidth - 150;
                        const legendY = plotY + 20;
                        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                        ctx.fillRect(legendX, legendY, 130, 30);
                        ctx.strokeStyle = '#ddd';
                        ctx.lineWidth = 1;
                        ctx.strokeRect(legendX, legendY, 130, 30);
                        
                        // Legend line
                        ctx.strokeStyle = color;
                        ctx.lineWidth = 3;
                        ctx.beginPath();
                        ctx.moveTo(legendX + 10, legendY + 15);
                        ctx.lineTo(legendX + 30, legendY + 15);
                        ctx.stroke();
                        
                        // Legend text
                        ctx.fillStyle = '#333';
                        ctx.font = '12px Arial';
                        ctx.textAlign = 'left';
                        ctx.fillText(title, legendX + 35, legendY + 19);
                        
                        ctx.textAlign = 'left';
                      };
                      
                      // Draw charts vertically stacked
                      drawProfessionalGeoSFMChart(50, 120, 'depth', '#2196F3', 'River Depth', 'm');
                      drawProfessionalGeoSFMChart(50, 480, 'streamflow', '#FF6B35', 'Streamflow', 'm³/s');
                      
                      const link = document.createElement('a');
                      link.download = `${stationName}_geosfm_analysis.png`;
                      link.href = canvas.toDataURL();
                      link.click();
                      return;
                    }
                  }}
                  sx={{
                    p: '4px 8px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    fontSize: '11px',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: '#0056b3'
                    }
                  }}
                >
                  📸 PNG
                </Button>
                
                <Button
                  onClick={() => generateReport(selectedStation)}
                  sx={{
                    p: '4px 8px',
                    backgroundColor: '#1B6840',
                    color: 'white',
                    border: 'none',
                    fontSize: '11px',
                    cursor: 'pointer',
                    ml: '5px',
                    '&:hover': {
                      backgroundColor: '#145432'
                    }
                  }}
                >
                  📊 Report
                </Button>
                
                <IconButton
                  onClick={() => {
                    setSelectedStation(null);
                    setTimeSeriesData([]);
                    setGeoFSMTimeSeriesData([]);
                  }}
                  sx={{
                    fontSize: '24px',
                    p: '4px',
                    color: '#666',
                    '&:hover': {
                      color: '#000',
                      backgroundColor: 'rgba(0,0,0,0.04)'
                    }
                  }}
                >
                  ×
                </IconButton>
              </Box>
            </Box>
            <Box sx={{ 
              height: `${Math.max(panelHeight - 45, 155)}px`, 
              width: '100%', 
              p: '0 20px 10px 20px',
              overflow: 'hidden'
            }}>
              {chartType === "riverdepth" || chartType === "streamflow" ? (
                <GeoSFMChart
                  timeSeriesData={geoFSMTimeSeriesData}
                  dataType={geoFSMDataType}
                  stationName={selectedStation?.properties?.Name || selectedStation?.properties?.Descriptio || 'GeoSFM Station'}
                  height={Math.max(panelHeight - 65, 135)}
                />
              ) : (
                <Box>
                  <Box sx={{ mb: '10px' }}>
                    <Box
                      component="select"
                      value={selectedSeries}
                      onChange={(e) => setSelectedSeries(e.target.value)}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                      }}
                      sx={{ 
                        mr: '10px', 
                        p: '4px 8px',
                        border: '1px solid #FF9800',
                        borderRadius: '3px',
                        backgroundColor: '#FFF3E0',
                        color: '#E65100',
                        fontSize: '12px',
                        cursor: 'pointer',
                        outline: 'none',
                        pointerEvents: 'auto',
                        boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                        transition: 'all 0.2s ease',
                        '&:hover': {
                          backgroundColor: '#FFCC80',
                          borderColor: '#E65100'
                        }
                      }}
                    >
                      <option value="both">Both GFS & ICON</option>
                      <option value="gfs">GFS Only</option>
                      <option value="icon">ICON Only</option>
                    </Box>
                  </Box>
                  {timeSeriesData && timeSeriesData.length > 0 ? (
                    <DischargeChart
                      timeSeriesData={timeSeriesData}
                      selectedSeries={selectedSeries}
                      stationName={selectedStation?.properties?.SEC_NAME || 'FloodProofs Station'}
                      height={Math.max(panelHeight - 105, 115)}
                    />
                  ) : (
                    <Box sx={{ p: '20px', textAlign: 'center' }}>
                      <Typography>Loading chart data... ({timeSeriesData?.length || 0} data points)</Typography>
                    </Box>
                  )}
                </Box>
              )}
            </Box>
          </Box>
        )}
      </Box>

      {/* Vector layer legends disabled - only show legends for point data */}
      {/* <RiverLegend
        isSidebarActive={isSidebarActive}
        isVisible={activeOverlays.has('Rivers')}
      />

      <Admin0Legend
        isSidebarActive={isSidebarActive}
        isVisible={activeOverlays.has('Admin 0 (Countries)')}
      />

      <LakesLegend
        isSidebarActive={isSidebarActive}
        isVisible={activeOverlays.has('Lakes (Water Bodies)')}
      /> */}

      {/* Metadata Modal */}
      <MetadataModal
        show={showMetadataModal}
        handleClose={handleCloseMetadata}
        metadata={currentMetadata}
      />
    </Box>
  );
};

export default MapViewer;