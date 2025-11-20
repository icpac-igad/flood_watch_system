import { useState } from 'react';
import { 
  Box, 
  Typography, 
  Switch, 
  FormControl, 
  Select, 
  MenuItem, 
  CircularProgress,
  List,
  ListItem
} from '@mui/material';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faWater, faExclamationTriangle } from '@fortawesome/free-solid-svg-icons';
import { InfoIcon } from '../ui/InfoIcon';

/**
 * SidebarControls Component
 * 
 * Renders all sidebar controls including:
 * - Country filter dropdown
 * - Date picker for forecasts
 * - Layer toggles (FloodProofs, GeoSFM, Mike Hydro, Hype, Ensemble)
 * - Monitoring station switches
 * - Inundation maps toggles
 * - Impact layers (IBEW v1/v2)
 * - Selected station information display
 */
export const SidebarControls = ({
  // Layer props
  hazardLayers,
  impactLayers,
  ibewLayers,
  boundaryLayers,
  selectedLayers,
  selectedBoundaryLayers,
  onLayerSelect,
  onBoundaryLayerSelect,
  
  // Station toggles
  showMonitoringStations,
  setShowMonitoringStations,
  showGeoFSM,
  setShowGeoFSM,
  geoFSMLoading,
  selectedYear,
  setSelectedYear,
  showMikeHydro,
  setShowMikeHydro,
  showFastFlood,
  setShowFastFlood,
  showGlofas,
  setShowGlofas,
  
  // Metadata
  onInfoClick,
  selectedStation,
  
  // Date/Country filters
  selectedDates,
  onDateChange,
  selectedCountry,
  setSelectedCountry,
  availableCountries,
  availableDates,
  
  // Loading states
  isLoadingData,
  isLayersLoading,
}) => {
  const [stationDate, setStationDate] = useState(new Date().toISOString().split('T')[0]);
  const [impactLayersExpanded, setImpactLayersExpanded] = useState(false);
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

      {/* Station Information Section - Always Visible */}
      <Box sx={{ 
        p: '15px', 
        borderBottom: '2px solid #e9ecef', 
        backgroundColor: '#f8f9fa',
        flexShrink: 0,
        maxHeight: '40%',
        overflowY: 'auto'
      }}>
        <Typography variant="h6" sx={{ m: '0 0 10px 0', color: '#034930', fontWeight: 600, fontSize: '16px' }}>
          Station Information
        </Typography>
        <List sx={{ p: 0 }}>
          <ListItem sx={{ p: '8px 0', borderBottom: '1px solid #e9ecef' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
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
          </ListItem>

          <ListItem sx={{ p: '8px 0', borderBottom: '1px solid #e9ecef' }}>
            <Box sx={{ width: '100%' }}>
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
                  <Typography component="label" htmlFor="year-select" sx={{ fontSize: "0.875rem" }}>
                    Year:
                  </Typography>
                  <FormControl size="small" sx={{ minWidth: 80 }}>
                    <Select
                      id="year-select"
                      value={selectedYear}
                      onChange={(e) => setSelectedYear(e.target.value)}
                      sx={{ 
                        fontSize: "0.875rem",
                        '& .MuiSelect-select': {
                          p: '2px 8px'
                        }
                      }}
                    >
                      <MenuItem value="2025">2025</MenuItem>
                      <MenuItem value="2024">2024</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
              )}
            </Box>
          </ListItem>

          <ListItem sx={{ p: '8px 0', borderBottom: '1px solid #e9ecef' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
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
          </ListItem>
        </List>
      </Box>

      {/* Selected Station Details */}
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

export default SidebarControls;
