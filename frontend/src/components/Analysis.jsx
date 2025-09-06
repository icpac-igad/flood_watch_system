import React from 'react';
import { Container, Row, Col, Card } from 'react-bootstrap';

const Analysis = () => {
  return (
    <Container fluid className="py-5">
      <Row className="justify-content-center">
        <Col lg={6} md={8}>
          <Card className="text-center shadow-lg border-0">
            <Card.Body className="py-5">
              <div className="mb-4">
                {/* <h1 className="display-4 fw-bold text-primary mb-3">
                  Analysis
                </h1> */}
                <h3 className="text-warning fw-bold mb-4">
                  🚧 Coming Soon - Under Development 🚧
                </h3>
                <p className="text-muted lead">
                  This feature is currently being developed and will be available soon.
                </p>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Analysis;

/*
COMMENTED OUT - FULL ANALYSIS COMPONENT FOR FUTURE DEVELOPMENT

import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Form, Button, Spinner, Table, Alert, OverlayTrigger, Tooltip } from 'react-bootstrap';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell
} from 'recharts';
import { FileText, FileSpreadsheet, AlertTriangle } from 'lucide-react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

// Mock data to ensure the component works (will replace with actual fetching)
const MOCK_IMPACT_DATA = {
  features: [
    {
      properties: {
        name_0: "CountryA",
        name_1: "Region1",
        stock: 100000,
        flood_tot: 20000,
        flood_perc: 20
      }
    },
    {
      properties: {
        name_0: "CountryA",
        name_1: "Region2",
        stock: 150000,
        flood_tot: 30000,
        flood_perc: 20
      }
    },
    {
      properties: {
        name_0: "CountryB",
        name_1: "Region3",
        stock: 200000,
        flood_tot: 50000,
        flood_perc: 25
      }
    }
  ]
};

const MOCK_MONITORING_DATA = {
  features: [
    {
      properties: {
        name_0: "CountryA",
        name_1: "Region1",
        time_period: "2025-03-01,2025-03-02,2025-03-03",
        "time_series_discharge_simulated-gfs": "100,120,150",
        "time_series_discharge_simulated-icon": "110,130,160"
      }
    },
    {
      properties: {
        name_0: "CountryA",
        name_1: "Region2",
        time_period: "2025-03-01,2025-03-02,2025-03-03",
        "time_series_discharge_simulated-gfs": "90,110,140",
        "time_series_discharge_simulated-icon": "100,120,150"
      }
    }
  ]
};

const MOCK_GEOFSM_DATA = {
  features: [
    {
      properties: {
        name_0: "CountryA",
        name_1: "Region1",
        Id: "1",
        timestamp: "2025-03-01",
        data_type: "riverdepth",
        value: 2.5
      }
    },
    {
      properties: {
        name_0: "CountryA",
        name_1: "Region1",
        Id: "1",
        timestamp: "2025-03-02",
        data_type: "riverdepth",
        value: 3.0
      }
    },
    {
      properties: {
        name_0: "CountryA",
        name_1: "Region1",
        Id: "1",
        timestamp: "2025-03-03",
        data_type: "riverdepth",
        value: 3.5
      }
    }
  ]
};

const Analysis = () => {
  const [loading, setLoading] = useState(true);
  const [geoData, setGeoData] = useState({});
  const [monitoringData, setMonitoringData] = useState(null);
  const [geoSFMData, setGeoSFMData] = useState(null);
  const [selectedCountry, setSelectedCountry] = useState('');
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedLayer, setSelectedLayer] = useState('');
  const [availableCountries, setAvailableCountries] = useState([]);
  const [availableRegions, setAvailableRegions] = useState([]);
  const [impactData, setImpactData] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [geoSFMTimeSeriesData, setGeoSFMTimeSeriesData] = useState([]);
  const [riskScore, setRiskScore] = useState(null);
  const [error, setError] = useState(null);

  // API Endpoints with fallback mechanism
  const PRIMARY_HOST = "http://197.254.1.10:8090";
  const SECONDARY_HOST = "http://10.10.1.13:8090";
  
  // Initialize endpoints with primary host
  const API_ENDPOINTS = {
    affectedPop: `${PRIMARY_HOST}/api/affectedPop/`,
    affectedGDP: `${PRIMARY_HOST}/api/affectedGDP/`,
    affectedCrops: `${PRIMARY_HOST}/api/affectedCrops/`,
    affectedRoads: `${PRIMARY_HOST}/api/affectedRoads/`,
    displacedPop: `${PRIMARY_HOST}/api/displacedPop/`,
    affectedLivestock: `${PRIMARY_HOST}/api/affectedLivestock/`,
    affectedGrazingLand: `${PRIMARY_HOST}/api/affectedGrazingLand/`
  };
  
  // Function to switch to secondary host if primary fails
  const getEndpointWithFallback = async (endpoint) => {
    try {
      // Try primary endpoint
      const response = await fetch(endpoint);
      if (response.ok) return endpoint;
      // If primary fails, switch to secondary
      return endpoint.replace(PRIMARY_HOST, SECONDARY_HOST);
    } catch (error) {
      console.warn(`Primary endpoint ${endpoint} failed, switching to fallback`);
      return endpoint.replace(PRIMARY_HOST, SECONDARY_HOST);
    }
  };

  const LAYERS = {
    affectedPop: { label: 'Affected Population', unit: 'people' },
    affectedGDP: { label: 'Affected GDP', unit: 'USD' },
    affectedCrops: { label: 'Affected Crops', unit: 'hectares' },
    affectedRoads: { label: 'Affected Roads', unit: 'km' },
    displacedPop: { label: 'Displaced Population', unit: 'people' },
    affectedLivestock: { label: 'Affected Livestock', unit: 'heads' },
    affectedGrazingLand: { label: 'Affected Grazing Land', unit: 'hectares' }
  };

  const THRESHOLDS = { alert: 0.3, alarm: 0.6, emergency: 0.9 };

  // Utility Functions
  const calculateRiskScore = (floodTotal, discharge, depth) => {
    const floodImpact = floodTotal / (1000000 + floodTotal); // Normalize flood impact (cap at 1M)
    const dischargeImpact = Math.min(discharge / 1000, 1); // Normalize discharge (cap at 1000 m³/s)
    const depthImpact = Math.min(depth / 10, 1); // Normalize depth (cap at 10m)
    const rawScore = (floodImpact + dischargeImpact + depthImpact) / 3;
    return Math.min(rawScore, 1); // Scale to 0-1
  };

  const analyzeTrends = (data) => {
    return data.map(d => ({
      ...(d.timestamp ? { timestamp: new Date(d.timestamp) } : { time: new Date(d.time) }),
      gfs: Number(d.gfs) || 0,
      icon: Number(d.icon) || 0,
      depth: Number(d.depth) || 0
    })).sort((a, b) => (a.timestamp || a.time) - (b.timestamp || b.time));
  };

  // Initial data load
  useEffect(() => {
    const fetchInitialData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Try the primary endpoint first, then fallback if needed
        const affectedPopEndpoint = await getEndpointWithFallback(API_ENDPOINTS.affectedPop);
        
        // Replace mock data with actual fetching from API with fallback mechanism
        const [popResponse, monitoringResponse, geoSFMResponse] = await Promise.all([
          fetch(affectedPopEndpoint).catch(() => ({ ok: false, json: () => MOCK_IMPACT_DATA })),
          fetch('merged_data.geojson').catch(() => ({ ok: false, json: () => MOCK_MONITORING_DATA })),
          fetch('hydro_data_with_locations.geojson').catch(() => ({ ok: false, json: () => MOCK_GEOFSM_DATA }))
        ]);

        const popData = await popResponse.json();
        const monitoringData = await monitoringResponse.json();
        const geoSFMData = await geoSFMResponse.json();

        // Log the data for debugging
        console.log('Pop Data:', popData);
        console.log('Monitoring Data:', monitoringData);
        console.log('GeoSFM Data:', geoSFMData);

        // Validate data
        if (!popData.features || !Array.isArray(popData.features)) {
          console.warn('Using mock impact data due to invalid response');
          setGeoData({ affectedPop: MOCK_IMPACT_DATA.features });
          setAvailableCountries([...new Set(MOCK_IMPACT_DATA.features.map(f => f.properties?.name_0).filter(Boolean))].sort());
        } else {
          setGeoData({ affectedPop: popData.features });
          setAvailableCountries([...new Set(popData.features.map(f => f.properties?.name_0).filter(Boolean))].sort());
        }

        if (!monitoringData.features || !Array.isArray(monitoringData.features)) {
          console.warn('Using mock monitoring data due to invalid response');
          setMonitoringData(MOCK_MONITORING_DATA);
        } else {
          setMonitoringData(monitoringData);
        }

        if (!geoSFMData.features || !Array.isArray(geoSFMData.features)) {
          console.warn('Using mock GeoSFM data due to invalid response');
          setGeoSFMData(MOCK_GEOFSM_DATA);
        } else {
          setGeoSFMData(geoSFMData);
        }
      } catch (error) {
        console.error('Error fetching initial data:', error);
        setError(`Failed to load initial data: ${error.message}. Using mock data.`);
        setGeoData({ affectedPop: MOCK_IMPACT_DATA.features });
        setMonitoringData(MOCK_MONITORING_DATA);
        setGeoSFMData(MOCK_GEOFSM_DATA);
        setAvailableCountries([...new Set(MOCK_IMPACT_DATA.features.map(f => f.properties?.name_0).filter(Boolean))].sort());
      } finally {
        setLoading(false);
      }
    };
    fetchInitialData();
  }, []);

  // Fetch layer data and perform analysis
  useEffect(() => {
    if (!selectedLayer) {
      setAvailableRegions([]);
      setSelectedRegion('');
      setImpactData(null);
      setTimeSeriesData([]);
      setGeoSFMTimeSeriesData([]);
      setRiskScore(null);
      return;
    }

    const fetchLayerData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Get the endpoint with fallback if needed
        const layerEndpoint = await getEndpointWithFallback(API_ENDPOINTS[selectedLayer]);
        
        // Use the API endpoint directly with fallback mechanism
        const response = await fetch(layerEndpoint).catch(() => ({ ok: false, json: () => MOCK_IMPACT_DATA }));
        const data = await response.json();

        console.log(`Layer Data (${selectedLayer}):`, data);

        if (!data.features || !Array.isArray(data.features)) {
          console.warn(`Using mock data for layer ${selectedLayer}`);
          setGeoData(prev => ({ ...prev, [selectedLayer]: MOCK_IMPACT_DATA.features }));
        } else {
          setGeoData(prev => ({ ...prev, [selectedLayer]: data.features }));
        }

        const layerData = data.features || MOCK_IMPACT_DATA.features;
        if (selectedCountry) {
          const regions = [...new Set(layerData.filter(f => f.properties.name_0 === selectedCountry).map(f => f.properties?.name_1).filter(Boolean))].sort();
          setAvailableRegions(regions);
          setSelectedRegion('');
        }

        const regionData = selectedRegion
          ? layerData.find(f => f.properties.name_1 === selectedRegion && f.properties.name_0 === selectedCountry)?.properties
          : layerData.find(f => f.properties.name_0 === selectedCountry)?.properties;

        setImpactData(regionData);

        // Extract time-series data for the selected region
        const station = monitoringData?.features.find(f => f.properties.name_1 === selectedRegion && f.properties.name_0 === selectedCountry) ||
                       MOCK_MONITORING_DATA.features.find(f => f.properties.name_1 === selectedRegion && f.properties.name_0 === selectedCountry);
        if (station) {
          const timePeriod = station.properties.time_period?.split(',')?.map(t => t.trim()) || [];
          const gfsValues = station.properties['time_series_discharge_simulated-gfs']?.split(',').map(val => Number(val.trim()) || 0) || [];
          const iconValues = station.properties['time_series_discharge_simulated-icon']?.split(',').map(val => Number(val.trim()) || 0) || [];
          const dischargeData = timePeriod.map((time, index) => ({
            time: new Date(time),
            gfs: gfsValues[index],
            icon: iconValues[index]
          })).filter(item => !isNaN(item.time.getTime()) && !isNaN(item.gfs) && !isNaN(item.icon));
          setTimeSeriesData(dischargeData);
        }

        const geoSFMStation = geoSFMData?.features.find(f => f.properties.name_1 === selectedRegion && f.properties.name_0 === selectedCountry) ||
                             MOCK_GEOFSM_DATA.features.find(f => f.properties.name_1 === selectedRegion && f.properties.name_0 === selectedCountry);
        if (geoSFMStation) {
          const geoSFMTimeSeries = (geoSFMData?.features || MOCK_GEOFSM_DATA.features)
            .filter(f => f.properties.Id === geoSFMStation.properties.Id)
            .reduce((acc, f) => {
              const timestamp = new Date(f.properties.timestamp);
              if (isNaN(timestamp.getTime())) return acc;
              const existing = acc.find(item => item.timestamp.getTime() === timestamp.getTime());
              if (existing) {
                if (f.properties.data_type === 'riverdepth') existing.depth = Number(f.properties.value) || 0;
                else if (f.properties.data_type === 'streamflow') existing.streamflow = Number(f.properties.value) || 0;
              } else {
                acc.push({
                  timestamp,
                  depth: f.properties.data_type === 'riverdepth' ? Number(f.properties.value) || 0 : 0,
                  streamflow: f.properties.data_type === 'streamflow' ? Number(f.properties.value) || 0 : 0
                });
              }
              return acc;
            }, [])
            .sort((a, b) => a.timestamp - b.timestamp);
          setGeoSFMTimeSeriesData(geoSFMTimeSeries);
        }

        // Perform analysis: Calculate risk score
        if (regionData && timeSeriesData.length) {
          const maxDischarge = Math.max(...timeSeriesData.map(d => Math.max(d.gfs, d.icon)));
          const maxDepth = Math.max(...geoSFMTimeSeriesData.map(d => d.depth));
          const score = calculateRiskScore(regionData.flood_tot || 0, maxDischarge, maxDepth);
          setRiskScore(score);
        }
      } catch (error) {
        console.error(`Error fetching ${selectedLayer} data:`, error);
        setError(`Failed to load ${selectedLayer} data: ${error.message}. Using mock data.`);
        setGeoData(prev => ({ ...prev, [selectedLayer]: MOCK_IMPACT_DATA.features }));
      } finally {
        setLoading(false);
      }
    };
    fetchLayerData();
  }, [selectedLayer, selectedCountry, selectedRegion, monitoringData, geoSFMData]);

  // Event Handlers - Fixed region selection issue
  const handleCountryChange = (e) => {
    const country = e.target.value;
    setSelectedCountry(country);
    
    // When country changes, reset region and update available regions
    setSelectedRegion('');
    
    if (country && selectedLayer && geoData[selectedLayer]) {
      const regions = [...new Set(
        geoData[selectedLayer]
          .filter(f => f.properties.name_0 === country)
          .map(f => f.properties?.name_1)
          .filter(Boolean)
      )].sort();
      setAvailableRegions(regions);
    } else {
      setAvailableRegions([]);
    }
  };
  
  const handleRegionChange = (e) => setSelectedRegion(e.target.value);
  
  const handleLayerChange = (e) => {
    setSelectedLayer(e.target.value);
    setSelectedCountry('');
    setSelectedRegion('');
    setImpactData(null);
    setTimeSeriesData([]);
    setGeoSFMTimeSeriesData([]);
    setRiskScore(null);
    setAvailableRegions([]);
  };

  // Export to PDF
  const exportToPDF = async () => {
    const element = document.getElementById('analysis-content');
    const pdf = new jsPDF('p', 'mm', 'a4');
    try {
      const canvas = await html2canvas(element);
      const imgData = canvas.toDataURL('image/png');
      const imgProps = pdf.getImageProperties(imgData);
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
      
      // Add title
      pdf.setFontSize(16);
      pdf.setFont('helvetica', 'bold');
      pdf.text('FloodProofs EA Impact Analysis', pdfWidth / 2, 20, { align: 'center' });
      
      // Add metadata
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(11);
      pdf.text(`Generated: ${new Date().toLocaleString()}`, pdfWidth / 2, 30, { align: 'center' });
      
      const metadataY = 40;
      const lineSpacing = 7;
      
      if (selectedLayer) {
        pdf.text(`Layer: ${LAYERS[selectedLayer].label}`, pdfWidth / 2, metadataY, { align: 'center' });
      }
      
      if (selectedCountry) {
        pdf.text(`Country: ${selectedCountry}`, pdfWidth / 2, metadataY + lineSpacing, { align: 'center' });
      }
      
      if (selectedRegion) {
        pdf.text(`Region: ${selectedRegion}`, pdfWidth / 2, metadataY + lineSpacing * 2, { align: 'center' });
      }
      
      if (riskScore !== null) {
        pdf.text(`Risk Score: ${riskScore.toFixed(2)}`, pdfWidth / 2, metadataY + lineSpacing * 3, { align: 'center' });
      }
      
      // Add the main content
      pdf.addImage(imgData, 'PNG', 0, 65, pdfWidth, pdfHeight * 0.8);
      pdf.save(`floodproofs_ea_${selectedLayer}_${selectedCountry || 'all'}_${selectedRegion || 'all'}.pdf`);
    } catch (error) {
      console.error('PDF generation error:', error);
      setError('Failed to generate PDF: ' + error.message);
    }
  };

  // Export to CSV
  const exportToCSV = () => {
    const headers = ['Country', 'Region', 'Stock', 'Flood Total', 'Flood Percentage', 'Risk Score', 'Max Discharge (m³/s)', 'Max Depth (m)'];
    const rows = selectedRegion && impactData
      ? [[
          selectedCountry,
          selectedRegion,
          impactData.stock?.toLocaleString() || '',
          impactData.flood_tot?.toLocaleString() || '',
          impactData.flood_perc?.toFixed(1) || '',
          riskScore?.toFixed(2) || '',
          timeSeriesData.length ? Math.max(...timeSeriesData.map(d => Math.max(d.gfs, d.icon))).toFixed(1) : '',
          geoSFMTimeSeriesData.length ? Math.max(...geoSFMTimeSeriesData.map(d => d.depth)).toFixed(2) : ''
        ]]
      : geoData[selectedLayer]?.filter(f => f.properties.name_0 === selectedCountry).map(f => [
          f.properties.name_0,
          f.properties.name_1,
          f.properties.stock?.toLocaleString() || '',
          f.properties.flood_tot?.toLocaleString() || '',
          f.properties.flood_perc?.toFixed(1) || '',
          calculateRiskScore(f.properties.flood_tot || 0, 0, 0).toFixed(2),
          '',
          ''
        ]) || [];

    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `floodproofs_ea_${selectedLayer}_${selectedCountry || 'all'}_${selectedRegion || 'all'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Render
  if (loading) return (
    <Container className="text-center py-5">
      <Spinner animation="border" role="status"><span className="visually-hidden">Loading...</span></Spinner>
    </Container>
  );

  return (
    <Container fluid className="py-4" id="analysis-content">
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <h2 className="display-6 fw-bold">FloodProofs EA Impact Analysis</h2>
            <div>
              <Button variant="outline-primary" className="me-2" onClick={exportToPDF} disabled={!selectedCountry}>
                <FileText className="me-1" size={16} /> Export PDF
              </Button>
              <Button variant="outline-primary" onClick={exportToCSV} disabled={!selectedCountry}>
                <FileSpreadsheet className="me-1" size={16} /> Export CSV
              </Button>
            </div>
          </div>
        </Col>
      </Row>

      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          <Alert.Heading>Error</Alert.Heading><p>{error}</p>
        </Alert>
      )}

      <Card className="mb-4 shadow-sm">
        <Card.Header className="bg-primary text-white">
          <h5 className="mb-0 fw-bold">Analysis Filters</h5>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={4}>
              <Form.Group>
                <Form.Label className="fw-bold">Impact Layer</Form.Label>
                <Form.Select value={selectedLayer} onChange={handleLayerChange} className="border-2">
                  <option value="">Select Layer</option>
                  {Object.entries(LAYERS).map(([key, { label }]) => (
                    <option key={key} value={key}>{label}</option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={4}>
              <Form.Group>
                <Form.Label className="fw-bold">Country</Form.Label>
                <Form.Select value={selectedCountry} onChange={handleCountryChange} className="border-2" disabled={!selectedLayer}>
                  <option value="">Select Country</option>
                  {availableCountries.map(country => (
                    <option key={country} value={country}>{country}</option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={4}>
              <Form.Group>
                <Form.Label className="fw-bold">Region</Form.Label>
                <Form.Select value={selectedRegion} onChange={handleRegionChange} className="border-2" disabled={!selectedCountry || !availableRegions.length}>
                  <option value="">Select Region (Optional)</option>
                  {availableRegions.map(region => (
                    <option key={region} value={region}>{region}</option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {selectedLayer && selectedCountry && geoData[selectedLayer] && (
        <Card className="mb-4 shadow-sm">
          <Card.Header className="bg-warning text-dark">
            <h5 className="mb-0 fw-bold">
              {LAYERS[selectedLayer].label} Analysis - {selectedCountry} 
              {selectedRegion ? ` - ${selectedRegion}` : ' (All Regions)'}
              {riskScore !== null && (
                <OverlayTrigger placement="top" overlay={<Tooltip>{`Risk Level: ${riskScore >= THRESHOLDS.emergency ? 'Emergency' : riskScore >= THRESHOLDS.alarm ? 'Alarm' : riskScore >= THRESHOLDS.alert ? 'Alert' : 'Normal'}`}</Tooltip>}>
                  <span className="ms-2"><AlertTriangle color={riskScore >= THRESHOLDS.emergency ? '#ff0000' : riskScore >= THRESHOLDS.alarm ? '#ffa500' : riskScore >= THRESHOLDS.alert ? '#ffff00' : '#00ff00'} size={18} /></span>
                </OverlayTrigger>
              )}
            </h5>
          </Card.Header>
          <Card.Body>
            {selectedRegion && impactData ? (
              <Row>
                <Col md={4}>
                  <Card className="mb-3">
                    <Card.Header className="bg-primary text-white"><h6 className="mb-0 fw-bold">Impact Breakdown</h6></Card.Header>
                    <Card.Body>
                      <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                          <Pie
                            data={[
                              { name: 'Flooded', value: impactData.flood_tot || 0 },
                              { name: 'Stock', value: impactData.stock || 0 }
                            ]}
                            cx="50%" cy="50%" innerRadius={50} outerRadius={90}
                            label={({ name, value }) => `${name}: ${value.toLocaleString()}`}
                            labelLine={false}
                          >
                            <Cell fill="#ff7675" />
                            <Cell fill="#74b9ff" />
                          </Pie>
                          <RechartsTooltip formatter={(value) => value.toLocaleString()} />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </Card.Body>
                  </Card>
                </Col>
                <Col md={8}>
                  <Table striped bordered hover responsive>
                    <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                    <tbody>
                      <tr><td>Stock ({LAYERS[selectedLayer].unit})</td><td>{impactData.stock?.toLocaleString()}</td></tr>
                      <tr><td>Flood Total ({LAYERS[selectedLayer].unit})</td><td>{impactData.flood_tot?.toLocaleString()}</td></tr>
                      <tr><td>Flood Percentage</td><td>{impactData.flood_perc?.toFixed(1)}%</td></tr>
                      <tr><td>Risk Score</td><td>{riskScore?.toFixed(2)}</td></tr>
                      <tr><td>Max Discharge (m³/s)</td><td>{timeSeriesData.length ? Math.max(...timeSeriesData.map(d => Math.max(d.gfs, d.icon))).toFixed(1) : 'N/A'}</td></tr>
                      <tr><td>Max Depth (m)</td><td>{geoSFMTimeSeriesData.length ? Math.max(...geoSFMTimeSeriesData.map(d => d.depth)).toFixed(2) : 'N/A'}</td></tr>
                      <tr><td>Country</td><td>{impactData.name_0}</td></tr>
                      <tr><td>Region</td><td>{impactData.name_1}</td></tr>
                    </tbody>
                  </Table>
                  <Card className="mt-3">
                    <Card.Header className="bg-info text-white"><h6 className="mb-0 fw-bold">Forecast Trends</h6></Card.Header>
                    <Card.Body>
                      <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={analyzeTrends(timeSeriesData)}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="time" tickFormatter={(t) => new Date(t).toLocaleDateString('en-GB')} />
                          <YAxis label={{ value: 'Discharge (m³/s)', angle: -90, position: 'insideLeft' }} />
                          <RechartsTooltip labelFormatter={(t) => new Date(t).toLocaleDateString('en-GB')} />
                          <Legend />
                          <Line type="monotone" dataKey="gfs" stroke="#1f77b4" name="GFS Forecast" dot={false} />
                          <Line type="monotone" dataKey="icon" stroke="#ff7f0e" name="ICON Forecast" dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                      <ResponsiveContainer width="100%" height={200} className="mt-3">
                        <LineChart data={analyzeTrends(geoSFMTimeSeriesData)}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="timestamp" tickFormatter={(t) => new Date(t).toLocaleDateString('en-GB')} />
                          <YAxis label={{ value: 'River Depth (m)', angle: -90, position: 'insideLeft' }} />
                          <RechartsTooltip labelFormatter={(t) => new Date(t).toLocaleDateString('en-GB')} />
                          <Legend />
                          <Line type="monotone" dataKey="depth" stroke="#2c7fb8" name="Depth" dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </Card.Body>
                  </Card>
                </Col>
              </Row>
            ) : (
              <Row>
                <Col>
                  <h6 className="fw-bold mb-3">Regional Impact Distribution</h6>
                  <ResponsiveContainer width="100%" height={400}>
                    <BarChart data={geoData[selectedLayer]
                      ?.filter(f => f.properties.name_0 === selectedCountry)
                      .map(f => ({
                        name: f.properties.name_1,
                        stock: f.properties.stock || 0,
                        flood_tot: f.properties.flood_tot || 0
                      }))}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" angle={-45} textAnchor="end" height={60} />
                      <YAxis />
                      <RechartsTooltip formatter={(value) => value.toLocaleString()} />
                      <Legend />
                      <Bar dataKey="stock" fill="#74b9ff" name="Stock" />
                      <Bar dataKey="flood_tot" fill="#ff7675" name="Flooded" />
                    </BarChart>
                  </ResponsiveContainer>
                </Col>
              </Row>
            )}
          </Card.Body>
        </Card>
      )}
    </Container>
  );
};

export default Analysis;

*/