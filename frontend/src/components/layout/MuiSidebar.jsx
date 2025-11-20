import React, { useState, useMemo } from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  Typography,
  Switch,
  FormControlLabel,
  IconButton,
  Tooltip,
  Divider,
  Stack,
  List,
  ListItem,
  ListItemButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  useMediaQuery,
  useTheme,
  TextField,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
// @ts-ignore
import { extractCountriesFromAdminData } from '../../utils/map/countryFilter.ts';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import WaterIcon from '@mui/icons-material/Water';
import WarningIcon from '@mui/icons-material/Warning';
import PlaceIcon from '@mui/icons-material/Place';
import BorderStyleIcon from '@mui/icons-material/BorderStyle';
import VisibilityIcon from '@mui/icons-material/Visibility';
import InfoIcon from '@mui/icons-material/Info';

/**
 * LayerToggleItem - Individual layer with toggle switch and info button
 */
const LayerToggleItem = ({ layer, isChecked, onToggle, onInfoClick, loading }) => (
  <ListItem
    disablePadding
    secondaryAction={
      onInfoClick && (
        <Tooltip title="Layer Information" arrow>
          <IconButton
            edge="end"
            size="small"
            onClick={() => {
              onInfoClick(layer.id);
            }}
            sx={{ color: 'primary.main' }}
          >
            <InfoIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )
    }
  >
    <ListItemButton dense onClick={() => onToggle(layer.id)}>
      <FormControlLabel
        control={
          <Switch
            checked={isChecked}
            onChange={() => {
              onToggle(layer.id);
            }}
            size="small"
            color="info"
            disabled={loading}
          />
        }
        label={
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
              {layer.name}
            </Typography>
            {loading && <CircularProgress size={12} />}
          </Stack>
        }
        sx={{ m: 0, width: '100%' }}
      />
    </ListItemButton>
  </ListItem>
);

/**
 * MuiSidebar - Main sidebar component with MUI design
 * Supports all the props from TabSidebar for full compatibility
 */
export const MuiSidebar = ({
  hazardLayers = [],
  impactLayers = [],
  ibewLayers = [],
  boundaryLayers = [],
  selectedLayers = new Set(),
  selectedBoundaryLayers = new Set(),
  onLayerSelect,
  onBoundaryLayerSelect,
  showMonitoringStations,
  setShowMonitoringStations,
  showGeoFSM,
  setShowGeoFSM,
  geoFSMLoading = false,
  selectedYear,
  setSelectedYear,
  selectedStation,
  showMikeHydro,
  setShowMikeHydro,
  showHype,
  setShowHype,
  showEnsemble,
  setShowEnsemble,
  onInfoClick,
  selectedDates = {},
  onDateChange,
  selectedCountry,
  setSelectedCountry,
  selectedBasin,
  setSelectedBasin,
  isLoadingData = false,
  availableDates = {},
  isLayersLoading = false,
  showInundationMap,
  setShowInundationMap,
  showAlertLevels,
  setShowAlertLevels,
  titilerLayerData = {},
  adminBoundariesData = null,
}) => {
  const [expandedGroups, setExpandedGroups] = useState({
    stationInfo: true,
    realTimeRaster: false,
    inundationMaps: false,
    impactLayers: false,
    boundaryLayers: false,
  });

  const handleExpandChange = (groupId) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  };

  // Country-to-basin mapping for smart filtering
  const countryBasinMap = {
    kenya: ['rift_valley', 'victoria', 'turkana', 'awash'],
    ethiopia: ['nile', 'rift_valley', 'awash', 'omo_gibe'],
    uganda: ['nile', 'victoria', 'congo'],
    tanzania: ['victoria', 'tanganyika', 'malawi', 'rift_valley'],
    somalia: ['juba_shabelle', 'awash'],
    sudan: ['nile', 'lake_chad'],
    south_sudan: ['nile', 'congo'],
    eritrea: ['nile', 'awash'],
    djibouti: ['awash'],
    rwanda: ['nile', 'congo', 'victoria'],
    burundi: ['nile', 'congo', 'tanganyika']
  };

  // Extract countries from Admin1 data - memoize to avoid recalculation
  // Add WHCA Countries as a special option
  const availableCountries = useMemo(() => {
    const allCountries = extractCountriesFromAdminData(adminBoundariesData);

    // Insert "WHCA Countries" option after "All Countries"
    const whcaOption = { code: 'WHCA', name: 'WHCA Countries', value: 'WHCA' };

    // Find index of "All Countries" (should be first)
    const allCountriesIndex = allCountries.findIndex(c => c.code === 'ALL');

    if (allCountriesIndex >= 0) {
      // Insert WHCA option right after "All Countries"
      return [
        ...allCountries.slice(0, allCountriesIndex + 1),
        whcaOption,
        ...allCountries.slice(allCountriesIndex + 1)
      ];
    }

    // Fallback: add WHCA at the beginning
    return [whcaOption, ...allCountries];
  }, [adminBoundariesData]);

  // Get filtered basins based on selected country
  const getFilteredBasins = () => {
    const basinLabels = {
      nile: 'Nile Basin',
      congo: 'Congo Basin',
      niger: 'Niger Basin',
      lake_chad: 'Lake Chad Basin',
      rift_valley: 'East African Rift Valley',
      turkana: 'Lake Turkana Basin',
      victoria: 'Lake Victoria Basin',
      tanganyika: 'Lake Tanganyika Basin',
      malawi: 'Lake Malawi Basin',
      juba_shabelle: 'Juba-Shabelle Basin',
      awash: 'Awash Basin',
      omo_gibe: 'Omo-Gibe Basin'
    };

    // No country selected - show all basins
    if (!selectedCountry) {
      return [
        { value: 'all_basins', label: 'All Basins' },
        { value: 'nile', label: 'Nile Basin' },
        { value: 'congo', label: 'Congo Basin' },
        { value: 'niger', label: 'Niger Basin' },
        { value: 'lake_chad', label: 'Lake Chad Basin' },
        { value: 'rift_valley', label: 'East African Rift Valley' },
        { value: 'turkana', label: 'Lake Turkana Basin' },
        { value: 'victoria', label: 'Lake Victoria Basin' },
        { value: 'tanganyika', label: 'Lake Tanganyika Basin' },
        { value: 'malawi', label: 'Lake Malawi Basin' },
        { value: 'juba_shabelle', label: 'Juba-Shabelle Basin' },
        { value: 'awash', label: 'Awash Basin' },
        { value: 'omo_gibe', label: 'Omo-Gibe Basin' }
      ];
    }

    // WHCA Countries selected - show basins from all 5 WHCA countries
    if (selectedCountry === 'WHCA') {
      const whcaCountries = ['uganda', 'rwanda', 'south_sudan', 'ethiopia', 'sudan'];
      const whcaBasins = new Set();
      whcaCountries.forEach(country => {
        const basins = countryBasinMap[country] || [];
        basins.forEach(basin => whcaBasins.add(basin));
      });

      return [
        { value: 'all_basins', label: 'All Basins in WHCA Countries' },
        ...Array.from(whcaBasins).map(basin => ({
          value: basin,
          label: basinLabels[basin]
        }))
      ];
    }

    // Single country selected
    const countryKey = selectedCountry.toLowerCase().replace(' ', '_');
    const countryBasins = countryBasinMap[countryKey] || [];

    return [
      { value: 'all_basins', label: `All Basins in ${selectedCountry}` },
      ...countryBasins.map(basin => ({
        value: basin,
        label: basinLabels[basin]
      }))
    ];
  };

  return (
    <Box
      sx={{
        // Responsive width - accounts for padding to match map offset
        width: {
          xs: '100%',      // Mobile: full width
          sm: 280,         // Tablet: narrower
          md: 330,         // Medium desktop: 330px (content width without header padding)
          lg: 330          // Large desktop: 330px
        },
        // Height should be 100% to inherit from parent
        height: '100%',
        bgcolor: 'background.paper',
        overflowY: 'hidden',
        overflowX: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        boxSizing: 'border-box',

        // Keep same position on all screen sizes
        position: 'relative',

        // Smooth transitions
        transition: 'all 0.3s ease-in-out',
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: { xs: 1.5, sm: 2 },  // Reduce padding on mobile
          bgcolor: '#034930',
          color: 'white',
          borderBottom: '1px solid #dee2e6',
          width: '100%',
          boxSizing: 'border-box',
          flexShrink: 0,  // Prevent header from shrinking
        }}
      >
        <Typography variant="h6" sx={{ fontSize: { xs: 14, sm: 16 }, fontWeight: 600, m: 0, color: 'white' }}>
          Layers
        </Typography>
      </Box>

      {/* Scrollable Content */}
      <Box
        sx={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          p: {
            xs: 1,           // Mobile: very compact to reduce white space
            sm: 2,           // Tablet+: normal
            md: 2.5          // Desktop: spacious
          },
          // Custom scrollbar
          '&::-webkit-scrollbar': {
            width: { xs: '4px', sm: '8px' },
          },
          '&::-webkit-scrollbar-track': {
            bgcolor: 'grey.100',
          },
          '&::-webkit-scrollbar-thumb': {
            bgcolor: 'grey.400',
            borderRadius: '4px',
            '&:hover': {
              bgcolor: 'grey.500',
            },
          },
        }}
      >
      {/* Country Filter - At Top */}
      {setSelectedCountry && (
        <FormControl
          fullWidth
          size="small"
          sx={{
            mb: { xs: 1, sm: 2 }
          }}
        >
          <InputLabel
            sx={{
              fontSize: { xs: '0.875rem', sm: '1rem' },
              fontWeight: 500
            }}
          >
            Filter by Country
          </InputLabel>
          <Select
            value={selectedCountry || ''}
            onChange={(e) => setSelectedCountry(e.target.value || null)}
            label="Filter by Country"
            sx={{
              fontSize: { xs: '0.875rem', sm: '1rem' },
              '& .MuiSelect-select': {
                py: { xs: 1, sm: 1.5 }
              }
            }}
          >
            {availableCountries.map(country => (
              <MenuItem key={country.code} value={country.value}>
                {country.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {/* Basin Filter - At Top */}
      {setSelectedBasin && (
        <FormControl
          fullWidth
          size="small"
          sx={{ mb: { xs: 1, sm: 2 } }}
        >
          <InputLabel 
            sx={{ 
              fontSize: { xs: '0.875rem', sm: '1rem' },
              fontWeight: 500
            }}
          >
            Select Basin
          </InputLabel>
          <Select
            value={selectedBasin || 'all_basins'}
            onChange={(e) => setSelectedBasin(e.target.value)}
            label="Select Basin"
            sx={{ 
              fontSize: { xs: '0.875rem', sm: '1rem' },
              '& .MuiSelect-select': {
                py: { xs: 1, sm: 1.5 }
              }
            }}
          >
            {getFilteredBasins().map(basin => (
              <MenuItem key={basin.value} value={basin.value}>
                {basin.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {/* Multi-Model Discharge Group */}
      <Accordion
        expanded={expandedGroups.stationInfo}
        onChange={() => handleExpandChange('stationInfo')}
        sx={{
          '&:before': { display: 'none' },
          boxShadow: 'none',
          border: '1px solid #dee2e6',
          borderRadius: '4px !important',
          mb: 2,
        }}
      >
        <AccordionSummary
          sx={{
            bgcolor: expandedGroups.stationInfo ? 'primary.main' : 'background.paper',
            color: expandedGroups.stationInfo ? 'primary.contrastText' : 'text.primary',
            '&:hover': {
              bgcolor: expandedGroups.stationInfo ? 'primary.dark' : 'grey.100',
            },
            borderRadius: expandedGroups.stationInfo ? '4px 4px 0 0' : '4px',
            transition: 'all 0.3s ease',
          }}
        >
          <Stack direction="row" spacing={1.5} alignItems="center">
            <PlaceIcon sx={{ fontSize: 20 }} />
            <Typography variant="body1" fontWeight={600} sx={{ fontSize: '0.9375rem' }}>
              Multi-Model Discharge
            </Typography>
          </Stack>
        </AccordionSummary>

        <AccordionDetails sx={{ p: 2 }}>

          {/* Date filter - Calendar date picker */}
          {onDateChange && selectedDates && (
            <Box sx={{ mb: 2 }}>
              <LocalizationProvider dateAdapter={AdapterDateFns}>
                <DatePicker
                  label="Select Date"
                  value={selectedDates?.global ? new Date(selectedDates.global) : new Date()}
                  onChange={(newDate) => {
                    if (newDate) {
                      const formattedDate = newDate.toISOString().split('T')[0];
                      onDateChange('global', formattedDate);
                    }
                  }}
                  shouldDisableDate={(date) => {
                    // Only enable dates that are in availableDates
                    if (!availableDates || availableDates.length === 0) return false;
                    const dateStr = date.toISOString().split('T')[0];
                    return !availableDates.includes(dateStr);
                  }}
                  slotProps={{
                    textField: {
                      fullWidth: true,
                      size: 'small',
                      sx: { fontSize: '0.875rem' }
                    }
                  }}
                />
              </LocalizationProvider>
            </Box>
          )}

          {/* Station Toggles */}
          <List dense disablePadding>
            {setShowMonitoringStations && (
              <ListItem 
                disablePadding
                secondaryAction={
                  onInfoClick && (
                    <Tooltip title="Layer Information" arrow>
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={() => {
                          onInfoClick('floodproofs_east_africa');
                        }}
                        sx={{ color: 'primary.main' }}
                      >
                        <InfoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )
                }
              >
                <ListItemButton dense onClick={() => setShowMonitoringStations(!showMonitoringStations)}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={showMonitoringStations}
                        onChange={() => {
                          setShowMonitoringStations(!showMonitoringStations);
                        }}
                        size="small"
                        color="info"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                        Floodproofs East Africa
                      </Typography>
                    }
                    sx={{ m: 0, width: '100%' }}
                  />
                </ListItemButton>
              </ListItem>
            )}

            {setShowGeoFSM && (
              <ListItem 
                disablePadding
                secondaryAction={
                  onInfoClick && (
                    <Tooltip title="Layer Information" arrow>
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={() => {
                          onInfoClick('geosfm');
                        }}
                        sx={{ color: 'primary.main' }}
                      >
                        <InfoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )
                }
              >
                <ListItemButton dense onClick={() => setShowGeoFSM(!showGeoFSM)}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={showGeoFSM}
                        onChange={() => {
                          
                          setShowGeoFSM(!showGeoFSM);
                        }}
                        size="small"
                        color="info"
                        disabled={geoFSMLoading}
                      />
                    }
                    label={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                          GeoSFM
                        </Typography>
                        {geoFSMLoading && <CircularProgress size={12} />}
                      </Stack>
                    }
                    sx={{ m: 0, width: '100%' }}
                  />
                </ListItemButton>
              </ListItem>
            )}

            {setShowMikeHydro && (
              <ListItem 
                disablePadding
                secondaryAction={
                  onInfoClick && (
                    <Tooltip title="Layer Information" arrow>
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={() => {
                          
                          onInfoClick('mike_hydro');
                        }}
                        sx={{ color: 'primary.main' }}
                      >
                        <InfoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )
                }
              >
                <ListItemButton dense onClick={() => setShowMikeHydro(!showMikeHydro)}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={showMikeHydro}
                        onChange={() => {
                          
                          setShowMikeHydro(!showMikeHydro);
                        }}
                        size="small"
                        color="info"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                        Mike Hydro
                      </Typography>
                    }
                    sx={{ m: 0, width: '100%' }}
                  />
                </ListItemButton>
              </ListItem>
            )}

            {setShowHype && (
              <ListItem 
                disablePadding
                secondaryAction={
                  onInfoClick && (
                    <Tooltip title="Layer Information" arrow>
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={() => {
                          
                          onInfoClick('hype');
                        }}
                        sx={{ color: 'primary.main' }}
                      >
                        <InfoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )
                }
              >
                <ListItemButton dense onClick={() => setShowHype(!showHype)}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={showHype}
                        onChange={() => {
                          
                          setShowHype(!showHype);
                        }}
                        size="small"
                        color="info"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                        Hype
                      </Typography>
                    }
                    sx={{ m: 0, width: '100%' }}
                  />
                </ListItemButton>
              </ListItem>
            )}

            {setShowEnsemble && (
              <ListItem 
                disablePadding
                secondaryAction={
                  onInfoClick && (
                    <Tooltip title="Layer Information" arrow>
                      <IconButton
                        edge="end"
                        size="small"
                        onClick={() => {
                          
                          onInfoClick('ensemble');
                        }}
                        sx={{ color: 'primary.main' }}
                      >
                        <InfoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )
                }
              >
                <ListItemButton dense onClick={() => setShowEnsemble(!showEnsemble)}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={showEnsemble}
                        onChange={() => {
                          
                          setShowEnsemble(!showEnsemble);
                        }}
                        size="small"
                        color="info"
                      />
                    }
                    label={
                      <Typography variant="body2" sx={{ fontSize: '0.875rem', fontWeight: 600 }}>
                        Multi-modal
                      </Typography>
                    }
                    sx={{ m: 0, width: '100%' }}
                  />
                </ListItemButton>
              </ListItem>
            )}
          </List>
        </AccordionDetails>
      </Accordion>

      {/* Inundation Maps (Hazard Layers) Group */}
      {hazardLayers && hazardLayers.length > 0 && (
        <Accordion
          expanded={expandedGroups.inundationMaps}
          onChange={() => handleExpandChange('inundationMaps')}
          sx={{
            '&:before': { display: 'none' },
            boxShadow: 'none',
            border: '1px solid #dee2e6',
            borderRadius: '4px !important',
            mb: 2,
          }}
        >
          <AccordionSummary
            sx={{
              bgcolor: expandedGroups.inundationMaps ? 'primary.main' : 'background.paper',
              color: expandedGroups.inundationMaps ? 'primary.contrastText' : 'text.primary',
              '&:hover': {
                bgcolor: expandedGroups.inundationMaps ? 'primary.dark' : 'grey.100',
              },
              borderRadius: expandedGroups.inundationMaps ? '4px 4px 0 0' : '4px',
              transition: 'all 0.3s ease',
            }}
          >
            <Stack direction="row" spacing={1.5} alignItems="center">
              <WaterIcon sx={{ fontSize: 20 }} />
              <Typography variant="body1" fontWeight={600} sx={{ fontSize: '0.9375rem' }}>
                Inundation Maps
              </Typography>
            </Stack>
          </AccordionSummary>

          <AccordionDetails sx={{ p: 0 }}>
            {/* Date filter */}
            {onDateChange && selectedDates && (
              <Box sx={{ borderBottom: '1px solid #dee2e6', p: 2 }}>
                <input
                  type="date"
                  value={selectedDates?.inundationMaps || new Date().toISOString().split('T')[0]}
                  onChange={(e) => onDateChange({ ...selectedDates, inundationMaps: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid #ccc',
                    fontSize: '14px'
                  }}
                />
              </Box>
            )}

            <List dense disablePadding>
              {hazardLayers.map((layer) => (
                <LayerToggleItem
                  key={layer.id}
                  layer={layer}
                  isChecked={selectedLayers.has(layer.id)}
                  onToggle={onLayerSelect}
                  onInfoClick={onInfoClick}
                  loading={isLayersLoading}
                />
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Impact Layers Group */}
      {((impactLayers && impactLayers.length > 0) || (ibewLayers && ibewLayers.length > 0)) && (
        <Accordion
          expanded={expandedGroups.impactLayers}
          onChange={() => handleExpandChange('impactLayers')}
          sx={{
            '&:before': { display: 'none' },
            boxShadow: 'none',
            border: '1px solid #dee2e6',
            borderRadius: '4px !important',
            mb: 2,
          }}
        >
          <AccordionSummary
            sx={{
              bgcolor: expandedGroups.impactLayers ? 'primary.main' : 'background.paper',
              color: expandedGroups.impactLayers ? 'primary.contrastText' : 'text.primary',
              '&:hover': {
                bgcolor: expandedGroups.impactLayers ? 'primary.dark' : 'grey.100',
              },
              borderRadius: expandedGroups.impactLayers ? '4px 4px 0 0' : '4px',
              transition: 'all 0.3s ease',
            }}
          >
            <Stack direction="row" spacing={1.5} alignItems="center">
              <WarningIcon sx={{ fontSize: 20 }} />
              <Typography variant="body1" fontWeight={600} sx={{ fontSize: '0.9375rem' }}>
                Impact Layers
              </Typography>
            </Stack>
          </AccordionSummary>

          <AccordionDetails sx={{ p: 0 }}>
            {/* Date filter */}
            {onDateChange && selectedDates && (
              <Box sx={{ borderBottom: '1px solid #dee2e6', p: 2 }}>
                <input
                  type="date"
                  value={selectedDates?.impactLayers || new Date().toISOString().split('T')[0]}
                  onChange={(e) => onDateChange({ ...selectedDates, impactLayers: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '8px',
                    borderRadius: '4px',
                    border: '1px solid #ccc',
                    fontSize: '14px'
                  }}
                />
              </Box>
            )}

            {/* Impact Layers - Only IBEW Layers */}
            {ibewLayers && ibewLayers.length > 0 && (
              <List dense disablePadding>
                {ibewLayers.map((layer) => (
                  <LayerToggleItem
                    key={layer.id}
                    layer={layer}
                    isChecked={selectedLayers.has(layer.id)}
                    onToggle={onLayerSelect}
                    onInfoClick={onInfoClick}
                    loading={isLayersLoading}
                  />
                ))}
              </List>
            )}
          </AccordionDetails>
        </Accordion>
      )}
      </Box>
    </Box>
  );
};

export default MuiSidebar;
