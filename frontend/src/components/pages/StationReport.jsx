import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Grid,
  Alert,
  Chip,
  Divider,
  Card,
  CardContent
} from '@mui/material';
import { MapContainer, TileLayer, Marker, GeoJSON, CircleMarker } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { DischargeChart } from '../../utils/chart/chartUtils.jsx';
import { filterPointsByCountry } from '../../utils/map/countryFilter.ts';

const StationReport = () => {
  const { stationId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Get selected country from URL parameter
  const selectedCountry = searchParams.get('country');

  const [stationData, setStationData] = useState(null);
  const [stationCoordinates, setStationCoordinates] = useState(null);
  const [approvalData, setApprovalData] = useState({
    pocName: '',
    pocTitle: '',
    pocOrganization: '',
    pocEmail: '',
    status: 'pending',
    summaryText: '',
    pocComments: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [countrySummary, setCountrySummary] = useState(null);
  const [adminBoundariesData, setAdminBoundariesData] = useState(null);
  const [allFloodPoints, setAllFloodPoints] = useState(null);
  const [mapCenter, setMapCenter] = useState([5.0, 40.0]); // East Africa center
  const [mapZoom, setMapZoom] = useState(5);

  useEffect(() => {
    loadAdminData();
    loadStationData();
    loadApprovalStatus();
  }, [stationId]);

  // Recalculate country summary when admin boundaries finish loading
  useEffect(() => {
    if (adminBoundariesData && stationData) {
      // Reload the full flood data from merged forecast database API
      fetch('/api/fast/merged-forecast/dates/')
        .then(res => res.json())
        .then(datesData => {
          const latestDate = datesData.dates && datesData.dates.length > 0 ? datesData.dates[0].date : null;
          if (latestDate) {
            return fetch(`/api/fast/merged-forecast/${latestDate}/`);
          }
          throw new Error('No forecast dates available');
        })
        .then(res => res.json())
        .then(data => {
          const station = data.features.find(f => {
            const props = f.properties;
            const id = props.section_id || props.station_id || props.section_name || props.SEC_NAME;
            return String(id) === String(stationId);
          });
          if (station) {
            generateCountrySummary(data, station);
          }
        })
        .catch(err => console.error('Failed to reload data for summary:', err));
    }
  }, [adminBoundariesData]);

  const loadAdminData = async () => {
    try {
      const response = await fetch('/api/admin1');
      const data = await response.json();
      setAdminBoundariesData(data);
    } catch (err) {
      console.error('Failed to load Admin boundaries:', err);
    }
  };

  const loadStationData = async () => {
    try {
      // Load latest forecast date first from database
      const datesResponse = await fetch('/api/fast/merged-forecast/dates/');
      if (!datesResponse.ok) {
        throw new Error('Failed to load available forecast dates');
      }
      const datesData = await datesResponse.json();
      const latestDate = datesData.dates && datesData.dates.length > 0 ? datesData.dates[0].date : null;

      if (!latestDate) {
        throw new Error('No forecast data available');
      }

      // Load merged forecast data from database API (latest date)
      const response = await fetch(`/api/fast/merged-forecast/${latestDate}/`);
      if (!response.ok) {
        throw new Error(`Failed to load forecast data for ${latestDate}`);
      }
      const data = await response.json();
      
      // Store all flood points for map display
      setAllFloodPoints(data);
      
      // Find station by unique ID field (ID or SEC_CODE are unique, section_id is NOT!)
      const station = data.features.find(f => {
        const props = f.properties;
        const id = props.ID || props.SEC_CODE || props.section_id || props.station_id;
        return String(id) === String(stationId);
      });

      if (station) {
        setStationData(station.properties);
        // Store coordinates separately for the map
        if (station.geometry && station.geometry.coordinates) {
          setStationCoordinates(station.geometry.coordinates);
        }
        loadRealTimeSeries(station.properties);
        
        // Set map center to selected station
        const coords = station.geometry.coordinates;
        setMapCenter([coords[1], coords[0]]); // [lat, lng]
        setMapZoom(8);
        
        // Generate country summary for this station's country
        generateCountrySummary(data, station);
      } else {
        setError('Station not found: ' + stationId);
      }
      setLoading(false);
    } catch (err) {
      setError('Failed to load station data: ' + err.message);
      setLoading(false);
    }
  };

  const generateCountrySummary = (allData, currentStation) => {
    // Filter data by selected country using spatial filtering
    let filteredData = allData;
    let regionName = 'East Africa Region';
    
    if (selectedCountry) {
      regionName = selectedCountry;
      
      if (adminBoundariesData) {
        // Use spatial filtering to get only stations within the selected country
        filteredData = filterPointsByCountry(allData, adminBoundariesData, selectedCountry);
      } else {
        // Admin boundaries not loaded yet, show loading message
        setCountrySummary({
          country: regionName,
          totalStations: 0,
          normalCount: 0,
          warningCount: 0,
          alarmCount: 0,
          emergencyCount: 0,
          loading: true
        });
        return;
      }
    } else {
      // If no country filter, use basin/domain from station
      regionName = currentStation.properties.section_domain || 
                   currentStation.properties.section_basin || 
                   'East Africa Region';
    }
    
    // Calculate statistics from filtered stations
    const countryStations = filteredData.features;
    let normalCount = 0;
    let warningCount = 0;
    let alarmCount = 0;
    let emergencyCount = 0;
    
    countryStations.forEach(feature => {
      const props = feature.properties;
      const discharge = parseFloat(props.section_discharge_ref || 0);
      const alert = parseFloat(props.section_discharge_thr_alert || 9999);
      const alarm = parseFloat(props.section_discharge_thr_alarm || 9999);
      const emergency = parseFloat(props.section_discharge_thr_emergency || 9999);
      
      if (discharge >= emergency && emergency < 9999) {
        emergencyCount++;
      } else if (discharge >= alarm && alarm < 9999) {
        alarmCount++;
      } else if (discharge >= alert && alert < 9999) {
        warningCount++;
      } else {
        normalCount++;
      }
    });
    
    setCountrySummary({
      country: regionName,
      totalStations: countryStations.length,
      normalCount,
      warningCount,
      alarmCount,
      emergencyCount
    });
  };

  const loadRealTimeSeries = (station) => {
    try {
      // Extract time series data from station properties (same as map does)
      const timePeriod = station.time_period?.split(",")?.map((t) => t.trim()) || [];
      const gfsValues = station["time_series_discharge_simulated-gfs"]
        ?.split(",")
        .map((val) => Number(val.trim()) || 0) || [];
      const iconValues = station["time_series_discharge_simulated-icon"]
        ?.split(",")
        .map((val) => Number(val.trim()) || 0) || [];

      if (timePeriod.length === 0) {
        setTimeSeriesData([]);
        return;
      }

      // Create raw data points (same logic as map)
      const rawData = timePeriod
        .map((time, index) => ({
          time: new Date(time),
          gfs: gfsValues[index],
          icon: iconValues[index],
        }))
        .filter(
          (item) =>
            !isNaN(item.time.getTime()) &&
            ((!isNaN(item.gfs) && item.gfs !== null) || (!isNaN(item.icon) && item.icon !== null)),
        );

      // Aggregate data by day (daily averages) - same as map
      const dailyData = rawData.reduce((acc, item) => {
        const dateKey = item.time.toISOString().split('T')[0];

        if (!acc[dateKey]) {
          acc[dateKey] = {
            date: new Date(dateKey),
            gfsValues: [],
            iconValues: []
          };
        }

        // Add all values (including 0) to arrays
        if (!isNaN(item.gfs) && item.gfs !== null) {
          acc[dateKey].gfsValues.push(item.gfs);
        }
        if (!isNaN(item.icon) && item.icon !== null) {
          acc[dateKey].iconValues.push(item.icon);
        }

        return acc;
      }, {});

      // Calculate daily averages
      const aggregatedData = Object.values(dailyData).map(day => ({
        time: day.date,
        gfs: day.gfsValues.length > 0 ?
          (day.gfsValues.reduce((sum, val) => sum + val, 0) / day.gfsValues.length) : null,
        icon: day.iconValues.length > 0 ?
          (day.iconValues.reduce((sum, val) => sum + val, 0) / day.iconValues.length) : null
      })).sort((a, b) => a.time - b.time);

      setTimeSeriesData(aggregatedData);

    } catch (error) {
      console.error('Failed to parse time series data:', error);
      setTimeSeriesData([]);
    }
  };

  const loadApprovalStatus = async () => {
    try {
      const response = await fetch(`/api/station-reports/by-station/${stationId}/`);

      if (response.ok) {
        const data = await response.json();
        setApprovalData({
          pocName: data.member_state_poc_name || data.poc_name || '',
          pocTitle: data.member_state_poc_title || data.poc_title || '',
          pocOrganization: data.member_state_poc_organization || data.poc_organization || '',
          pocEmail: data.member_state_poc_email || data.poc_email || '',
          status: data.member_state_status || data.status || 'pending',
          summaryText: data.member_state_summary || data.summary_text || '',
          pocComments: data.member_state_comments || data.poc_comments || ''
        });
      }
    } catch (err) {
      // No existing approval data, starting fresh
    }
  };

  const handleInputChange = (field, value) => {
    setApprovalData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      // Prepare data with proper backend field names matching StationReportApproval model
      const reportData = {
        station_id: stationId,
        member_state_poc_name: approvalData.pocName,
        member_state_poc_title: approvalData.pocTitle,
        member_state_poc_organization: approvalData.pocOrganization,
        member_state_poc_email: approvalData.pocEmail,
        member_state_status: approvalData.status,
        member_state_comments: approvalData.pocComments,
        summary_text: approvalData.summaryText
      };

      const response = await fetch(`/api/station-reports/by-station/${stationId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(reportData)
      });

      if (response.ok) {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        const errorData = await response.json();
        setError(`Failed to save report: ${JSON.stringify(errorData)}`);
      }
    } catch (err) {
      setError('Error saving report: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved': return 'success';
      case 'changes_requested': return 'warning';
      case 'rejected': return 'error';
      default: return 'default';
    }
  };

  const getAlertStatus = (station) => {
    if (!station) return { status: 'Normal', color: 'success' };
    
    const discharge = station.section_discharge_ref || 0;
    const alert = station.section_discharge_thr_alert || 9999;
    const alarm = station.section_discharge_thr_alarm || 9999;
    const emergency = station.section_discharge_thr_emergency || 9999;
    
    if (discharge >= emergency) return { status: 'Emergency', color: 'error' };
    if (discharge >= alarm) return { status: 'Alarm', color: 'error' };
    if (discharge >= alert) return { status: 'Alert', color: 'warning' };
    return { status: 'Normal', color: 'success' };
  };

  if (loading) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography>Loading station report...</Typography>
      </Box>
    );
  }

  if (error && !stationData) {
    return (
      <Box sx={{ p: 4 }}>
        <Alert severity="error">{error}</Alert>
        <Button onClick={() => navigate('/reports')} sx={{ mt: 2 }}>
          Back to Reports
        </Button>
      </Box>
    );
  }

  const alertStatus = getAlertStatus(stationData);

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, maxWidth: '100%', margin: '0 auto' }}>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Button onClick={() => navigate('/map')} variant="outlined">
          ← Back to Map
        </Button>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h4" sx={{ color: '#1B6840', fontWeight: 'bold' }}>
            Flood Analysis Report for {countrySummary?.country || 'East Africa'}
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Reference Date: {new Date().toLocaleDateString('en-US', { 
              year: 'numeric', month: 'long', day: 'numeric' 
            })}
          </Typography>
        </Box>
        <Chip 
          label={approvalData.status.replace('_', ' ').toUpperCase()} 
          color={getStatusColor(approvalData.status)}
        />
      </Box>

      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Report saved successfully!
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Selected Station Summary */}
      {stationData && (
        <Paper sx={{ p: 3, mb: 3, backgroundColor: '#f9f9f9' }}>
          <Typography variant="h5" gutterBottom sx={{ color: '#1B6840', fontWeight: 'bold', mb: 2 }}>
            Selected Station Summary
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: '#666' }}>
                  Station ID
                </Typography>
                <Typography variant="body1" sx={{ fontSize: '16px' }}>
                  {stationData.section_id || stationData.section_name || stationId}
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: '#666' }}>
                  Basin / Domain
                </Typography>
                <Typography variant="body1" sx={{ fontSize: '16px' }}>
                  {stationData.section_basin || stationData.section_domain || 'N/A'}
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: '#666' }}>
                  Current Discharge
                </Typography>
                <Typography variant="body1" sx={{ fontSize: '18px', fontWeight: 'bold', color: '#1B6840' }}>
                  {parseFloat(
                    stationData.section_discharge_ref ||
                    stationData.discharge_ref ||
                    stationData.discharge ||
                    stationData.section_discharge ||
                    0
                  ).toFixed(2)} m³/s
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: '#666' }}>
                  Alert Status
                </Typography>
                <Chip
                  label={getAlertStatus(stationData).status}
                  color={getAlertStatus(stationData).color}
                  sx={{ fontWeight: 'bold', fontSize: '14px' }}
                />
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 'bold', color: '#666', mb: 1 }}>
                  Flood Thresholds
                </Typography>
                <Box sx={{ pl: 2 }}>
                  {stationData.section_discharge_thr_alert && stationData.section_discharge_thr_alert < 9999 && (
                    <Typography variant="body2" sx={{ color: '#ff9800', mb: 0.5 }}>
                      ⚠ Alert: {parseFloat(stationData.section_discharge_thr_alert).toFixed(2)} m³/s
                    </Typography>
                  )}
                  {stationData.section_discharge_thr_alarm && stationData.section_discharge_thr_alarm < 9999 && (
                    <Typography variant="body2" sx={{ color: '#f44336', mb: 0.5 }}>
                      🔴 Alarm: {parseFloat(stationData.section_discharge_thr_alarm).toFixed(2)} m³/s
                    </Typography>
                  )}
                  {stationData.section_discharge_thr_emergency && stationData.section_discharge_thr_emergency < 9999 && (
                    <Typography variant="body2" sx={{ color: '#b71c1c' }}>
                      🚨 Emergency: {parseFloat(stationData.section_discharge_thr_emergency).toFixed(2)} m³/s
                    </Typography>
                  )}
                </Box>
              </Box>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Regional Flood Risk Statistics */}
      {countrySummary && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom sx={{ color: '#1B6840', fontWeight: 'bold', mb: 3 }}>
            Regional Flood Risk Statistics
          </Typography>
          
          <Box sx={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '20px' }}>
              <thead>
                <tr style={{ backgroundColor: '#1B6840', color: 'white' }}>
                  <th style={{ padding: '12px', textAlign: 'left', fontWeight: 'bold' }}>FLOOD PHASE</th>
                  <th style={{ padding: '12px', textAlign: 'center', fontWeight: 'bold' }}>STATIONS</th>
                  <th style={{ padding: '12px', textAlign: 'center', fontWeight: 'bold' }}>PERCENTAGE</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontWeight: 'bold' }}>STATUS</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #ddd', backgroundColor: '#b71c1c10' }}>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>Emergency</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {countrySummary.emergencyCount}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {((countrySummary.emergencyCount / countrySummary.totalStations) * 100).toFixed(2)}%
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ 
                      backgroundColor: '#b71c1c', 
                      color: 'white', 
                      padding: '4px 12px', 
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      CRITICAL
                    </span>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #ddd', backgroundColor: '#f4433610' }}>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>Alarm</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {countrySummary.alarmCount}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {((countrySummary.alarmCount / countrySummary.totalStations) * 100).toFixed(2)}%
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ 
                      backgroundColor: '#f44336', 
                      color: 'white', 
                      padding: '4px 12px', 
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      HIGH RISK
                    </span>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #ddd', backgroundColor: '#ff980010' }}>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>Warning</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {countrySummary.warningCount}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {((countrySummary.warningCount / countrySummary.totalStations) * 100).toFixed(2)}%
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ 
                      backgroundColor: '#ff9800', 
                      color: 'white', 
                      padding: '4px 12px', 
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      MODERATE
                    </span>
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #ddd', backgroundColor: '#4caf5010' }}>
                  <td style={{ padding: '12px', fontWeight: 'bold' }}>Normal</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {countrySummary.normalCount}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {((countrySummary.normalCount / countrySummary.totalStations) * 100).toFixed(2)}%
                  </td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ 
                      backgroundColor: '#4caf50', 
                      color: 'white', 
                      padding: '4px 12px', 
                      borderRadius: '4px',
                      fontSize: '12px',
                      fontWeight: 'bold'
                    }}>
                      LOW RISK
                    </span>
                  </td>
                </tr>
                <tr style={{ backgroundColor: '#f5f5f5', fontWeight: 'bold' }}>
                  <td style={{ padding: '12px' }}>TOTAL</td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>
                    {countrySummary.totalStations}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'center' }}>100.00%</td>
                  <td style={{ padding: '12px' }}>—</td>
                </tr>
              </tbody>
            </table>
          </Box>
        </Paper>
      )}


      <Box sx={{ width: '100%', mb: 3 }}>
        <Paper sx={{ p: 2, width: '100%' }}>
          <Typography variant="h6" gutterBottom sx={{ px: 1 }}>
            Discharge Time Series
          </Typography>
          <Box sx={{ width: '100%', height: 500 }}>
            {timeSeriesData && timeSeriesData.length > 0 ? (
              <DischargeChart
                timeSeriesData={timeSeriesData}
                selectedSeries="both"
                stationName={stationData?.section_name || stationData?.SEC_NAME || `Station ${stationId}`}
                height={500}
              />
            ) : (
              <div style={{ padding: '20px', textAlign: 'center' }}>No data available.</div>
            )}
          </Box>
          </Paper>
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12}>

          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom sx={{ color: '#1B6840', mb: 3 }}>
              Flood Situation Report
            </Typography>
            
            {/* Executive Summary */}
            <Box sx={{ mb: 3, p: 2, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', color: '#1B6840' }}>
                EXECUTIVE SUMMARY
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                <strong>Region:</strong> {countrySummary?.country || 'East Africa'}
              </Typography>
              <Typography variant="body2" sx={{ mb: 2 }}>
                <strong>Report Date:</strong> {new Date().toLocaleDateString('en-US', { 
                  year: 'numeric', month: 'long', day: 'numeric' 
                })}
              </Typography>
              <Typography variant="body2">
                <strong>Data Source:</strong> FloodProofs Early Action (FP_EA) - GFS & ICON Models
              </Typography>
            </Box>

            {/* Overall Situation */}
            {countrySummary && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                  OVERALL SITUATION
                </Typography>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  Monitoring network: <strong>{countrySummary.totalStations} stations</strong>
                </Typography>
                
                <Box sx={{ pl: 2 }}>
                  <Typography variant="body2" sx={{ color: '#4caf50', mb: 1 }}>
                    ✓ Normal: {countrySummary.normalCount} stations ({Math.round(countrySummary.normalCount / countrySummary.totalStations * 100)}%)
                  </Typography>
                  {countrySummary.warningCount > 0 && (
                    <Typography variant="body2" sx={{ color: '#ff9800', mb: 1 }}>
                      ⚠ Warning: {countrySummary.warningCount} stations ({Math.round(countrySummary.warningCount / countrySummary.totalStations * 100)}%)
                    </Typography>
                  )}
                  {countrySummary.alarmCount > 0 && (
                    <Typography variant="body2" sx={{ color: '#f44336', mb: 1 }}>
                      ⚠ Alarm: {countrySummary.alarmCount} stations ({Math.round(countrySummary.alarmCount / countrySummary.totalStations * 100)}%)
                    </Typography>
                  )}
                  {countrySummary.emergencyCount > 0 && (
                    <Typography variant="body2" sx={{ color: '#b71c1c', mb: 1 }}>
                      🚨 Emergency: {countrySummary.emergencyCount} stations ({Math.round(countrySummary.emergencyCount / countrySummary.totalStations * 100)}%)
                    </Typography>
                  )}
                </Box>
              </Box>
            )}

            {/* EARLY WARNING ALERT */}
            {countrySummary && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', color: '#b71c1c' }}>
                  ⚠️ EARLY WARNING ALERT
                </Typography>
                <Box sx={{ p: 2, backgroundColor: 
                  countrySummary.emergencyCount > 0 ? '#ffebee' : 
                  countrySummary.alarmCount > 0 ? '#fff3e0' : 
                  countrySummary.warningCount > 0 ? '#fff9c4' : 
                  '#e8f5e9',
                  borderRadius: 1,
                  borderLeft: `4px solid ${
                    countrySummary.emergencyCount > 0 ? '#b71c1c' : 
                    countrySummary.alarmCount > 0 ? '#f44336' : 
                    countrySummary.warningCount > 0 ? '#ff9800' : 
                    '#4caf50'
                  }`
                }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                    {countrySummary.emergencyCount > 0 ? '🚨 EMERGENCY - IMMEDIATE ACTION REQUIRED' :
                     countrySummary.alarmCount > 0 ? '⚠️ HIGH ALERT - PREPARE FOR ACTION' :
                     countrySummary.warningCount > 0 ? '⚡ EARLY WARNING - MONITOR CLOSELY' :
                     '✅ NORMAL - ROUTINE MONITORING'}
                  </Typography>
                  <Typography variant="body2">
                    {countrySummary.emergencyCount > 0 ? 
                      `${countrySummary.emergencyCount} station(s) at EMERGENCY level. Flooding is imminent or occurring.` :
                     countrySummary.alarmCount > 0 ? 
                      `${countrySummary.alarmCount} station(s) at ALARM level. Significant flooding expected within 24-48 hours.` :
                     countrySummary.warningCount > 0 ? 
                      `${countrySummary.warningCount} station(s) showing WARNING levels. Potential flooding in next 48-72 hours.` :
                      'All stations within normal operating ranges. No flood threat detected.'}
                  </Typography>
                </Box>
              </Box>
            )}

            {/* RECOMMENDED EARLY ACTIONS */}
            {countrySummary && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', color: '#1B6840' }}>
                  📋 RECOMMENDED EARLY ACTIONS
                </Typography>
                <Box sx={{ p: 2, backgroundColor: '#f5f5f5', borderRadius: 1 }}>
                  {countrySummary.emergencyCount > 0 && (
                    <>
                      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, color: '#b71c1c' }}>
                        IMMEDIATE ACTIONS (0-6 hours):
                      </Typography>
                      <Typography variant="body2" component="div" sx={{ mb: 2, pl: 2 }}>
                        • Activate Emergency Operations Center (EOC)<br/>
                        • Issue evacuation orders for high-risk communities<br/>
                        • Deploy emergency response teams to affected areas<br/>
                        • Establish emergency shelters and relief centers<br/>
                        • Coordinate with military/civil defense for rescue operations
                      </Typography>
                    </>
                  )}
                  {countrySummary.alarmCount > 0 && (
                    <>
                      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, color: '#f44336' }}>
                        URGENT ACTIONS (6-24 hours):
                      </Typography>
                      <Typography variant="body2" component="div" sx={{ mb: 2, pl: 2 }}>
                        • Alert downstream communities and local authorities<br/>
                        • Pre-position emergency supplies and equipment<br/>
                        • Activate early warning dissemination systems (SMS, radio, sirens)<br/>
                        • Prepare evacuation routes and temporary shelters<br/>
                        • Mobilize health services and medical supplies
                      </Typography>
                    </>
                  )}
                  {countrySummary.warningCount > 0 && countrySummary.emergencyCount === 0 && countrySummary.alarmCount === 0 && (
                    <>
                      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, color: '#ff9800' }}>
                        PREPAREDNESS ACTIONS (24-72 hours):
                      </Typography>
                      <Typography variant="body2" component="div" sx={{ mb: 2, pl: 2 }}>
                        • Intensify monitoring of river levels and rainfall<br/>
                        • Issue early warning bulletins to vulnerable areas<br/>
                        • Review and update evacuation plans<br/>
                        • Conduct community awareness and preparedness drills<br/>
                        • Ensure communication systems are operational
                      </Typography>
                    </>
                  )}
                  {countrySummary.normalCount === countrySummary.totalStations && (
                    <>
                      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1, color: '#4caf50' }}>
                        ROUTINE ACTIONS:
                      </Typography>
                      <Typography variant="body2" component="div" sx={{ pl: 2 }}>
                        • Continue regular monitoring schedule<br/>
                        • Maintain readiness of early warning systems<br/>
                        • Review seasonal forecasts and prepare for upcoming rain seasons<br/>
                        • Conduct community risk awareness programs
                      </Typography>
                    </>
                  )}
                </Box>
              </Box>
            )}

            <Divider sx={{ my: 3 }} />

            {/* Approval Section */}
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', mb: 2 }}>
              MEMBER STATE APPROVAL
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
              Point of Contact - Review and approve for official release
            </Typography>

            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Name"
                value={approvalData.pocName}
                onChange={(e) => handleInputChange('pocName', e.target.value)}
                sx={{ mb: 2 }}
                required
              />

              <TextField
                fullWidth
                label="Title"
                value={approvalData.pocTitle}
                onChange={(e) => handleInputChange('pocTitle', e.target.value)}
                sx={{ mb: 2 }}
                required
              />

              <TextField
                fullWidth
                label="Organization"
                value={approvalData.pocOrganization}
                onChange={(e) => handleInputChange('pocOrganization', e.target.value)}
                sx={{ mb: 2 }}
                required
              />

              <TextField
                fullWidth
                label="Email"
                type="email"
                value={approvalData.pocEmail}
                onChange={(e) => handleInputChange('pocEmail', e.target.value)}
                sx={{ mb: 2 }}
                required
              />

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Approval Status</InputLabel>
                <Select
                  value={approvalData.status}
                  label="Approval Status"
                  onChange={(e) => handleInputChange('status', e.target.value)}
                >
                  <MenuItem value="pending">Pending Review</MenuItem>
                  <MenuItem value="approved">Approved</MenuItem>
                  <MenuItem value="changes_requested">Changes Requested</MenuItem>
                  <MenuItem value="rejected">Rejected</MenuItem>
                </Select>
              </FormControl>

              <TextField
                fullWidth
                label="Summary Comments"
                value={approvalData.summaryText}
                onChange={(e) => handleInputChange('summaryText', e.target.value)}
                multiline
                rows={3}
                sx={{ mb: 2 }}
                placeholder="Provide a brief summary of the station conditions..."
              />

              <TextField
                fullWidth
                label="Point of Contact Comments"
                value={approvalData.pocComments}
                onChange={(e) => handleInputChange('pocComments', e.target.value)}
                multiline
                rows={4}
                sx={{ mb: 3 }}
                placeholder="Add your review comments, concerns, or recommendations..."
                required
              />

              <Button
                type="submit"
                variant="contained"
                fullWidth
                disabled={saving}
                sx={{
                  backgroundColor: '#1B6840',
                  '&:hover': {
                    backgroundColor: '#145032'
                  }
                }}
              >
                {saving ? 'Saving...' : 'Save Report'}
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default StationReport;
