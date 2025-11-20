import React, { useEffect, useRef, useState } from 'react';
import { Box, Button, Typography } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';

const StaticMapCanvas = ({ stationData, stationCoordinates, allFloodPoints, selectedCountry }) => {
  const canvasRef = useRef(null);
  const [mapImage, setMapImage] = useState(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear canvas
    ctx.fillStyle = '#e8f4f8';
    ctx.fillRect(0, 0, width, height);

    // Get station coordinates
    let stationLat = 0;
    let stationLon = 0;
    
    if (stationCoordinates && stationCoordinates.length === 2) {
      stationLon = stationCoordinates[0];
      stationLat = stationCoordinates[1];
    }

    if (!stationLat || !stationLon) {
      // Draw error message
      ctx.fillStyle = '#666';
      ctx.font = '14px Arial';
      ctx.textAlign = 'center';
      ctx.fillText('No location data available', width / 2, height / 2);
      return;
    }

    // Calculate bounds for nearby stations (within ~2 degrees)
    const nearbyStations = allFloodPoints?.features?.filter(feature => {
      const coords = feature.geometry.coordinates;
      const lat = coords[1];
      const lon = coords[0];
      const distance = Math.sqrt(
        Math.pow(lat - stationLat, 2) + Math.pow(lon - stationLon, 2)
      );
      return distance < 2; // ~220km radius
    }) || [];

    // Calculate map bounds
    let minLat = stationLat - 1.5;
    let maxLat = stationLat + 1.5;
    let minLon = stationLon - 1.5;
    let maxLon = stationLon + 1.5;

    if (nearbyStations.length > 0) {
      nearbyStations.forEach(feature => {
        const coords = feature.geometry.coordinates;
        minLat = Math.min(minLat, coords[1]);
        maxLat = Math.max(maxLat, coords[1]);
        minLon = Math.min(minLon, coords[0]);
        maxLon = Math.max(maxLon, coords[0]);
      });
    }

    // Add padding
    const latPadding = (maxLat - minLat) * 0.1;
    const lonPadding = (maxLon - minLon) * 0.1;
    minLat -= latPadding;
    maxLat += latPadding;
    minLon -= lonPadding;
    maxLon += lonPadding;

    // Map projection functions
    const latToY = (lat) => height - ((lat - minLat) / (maxLat - minLat)) * height;
    const lonToX = (lon) => ((lon - minLon) / (maxLon - minLon)) * width;

    // Draw grid lines
    ctx.strokeStyle = '#d0d0d0';
    ctx.lineWidth = 1;
    for (let i = 1; i < 5; i++) {
      const y = (height / 5) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();

      const x = (width / 5) * i;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    // Draw nearby stations
    nearbyStations.forEach(feature => {
      const props = feature.properties;
      const coords = feature.geometry.coordinates;
      const x = lonToX(coords[0]);
      const y = latToY(coords[1]);

      // Calculate alert status
      const discharge = parseFloat(props.section_discharge_ref || 0);
      const alert = parseFloat(props.section_discharge_thr_alert || 9999);
      const alarm = parseFloat(props.section_discharge_thr_alarm || 9999);
      const emergency = parseFloat(props.section_discharge_thr_emergency || 9999);

      let color = '#4caf50'; // Normal - green
      if (discharge >= emergency && emergency < 9999) {
        color = '#b71c1c'; // Emergency - dark red
      } else if (discharge >= alarm && alarm < 9999) {
        color = '#f44336'; // Alarm - red
      } else if (discharge >= alert && alert < 9999) {
        color = '#ff9800'; // Warning - orange
      }

      // Draw station dot
      ctx.beginPath();
      ctx.arc(x, y, 6, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    // Draw selected station (larger, with highlight)
    const stationX = lonToX(stationLon);
    const stationY = latToY(stationLat);

    // Highlight circle
    ctx.beginPath();
    ctx.arc(stationX, stationY, 20, 0, 2 * Math.PI);
    ctx.fillStyle = 'rgba(27, 104, 64, 0.2)';
    ctx.fill();
    ctx.strokeStyle = '#1B6840';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Station dot
    ctx.beginPath();
    ctx.arc(stationX, stationY, 10, 0, 2 * Math.PI);
    ctx.fillStyle = '#1B6840';
    ctx.fill();
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 3;
    ctx.stroke();

    // Draw title and legend
    ctx.fillStyle = '#1B6840';
    ctx.font = 'bold 16px Arial';
    ctx.textAlign = 'left';
    ctx.fillText('Station Location Map', 10, 25);

    // Draw country name if available
    if (selectedCountry) {
      ctx.fillStyle = '#666';
      ctx.font = '12px Arial';
      ctx.fillText(selectedCountry, 10, 45);
    }

    // Draw legend
    const legendY = height - 80;
    const legendItems = [
      { color: '#4caf50', label: 'Normal' },
      { color: '#ff9800', label: 'Warning' },
      { color: '#f44336', label: 'Alarm' },
      { color: '#b71c1c', label: 'Emergency' },
      { color: '#1B6840', label: 'Selected' }
    ];

    ctx.font = '11px Arial';
    legendItems.forEach((item, idx) => {
      const x = 10 + (idx * 70);
      
      // Legend dot
      ctx.beginPath();
      ctx.arc(x + 5, legendY + 5, 5, 0, 2 * Math.PI);
      ctx.fillStyle = item.color;
      ctx.fill();
      ctx.strokeStyle = idx === 4 ? '#000' : '#fff';
      ctx.lineWidth = idx === 4 ? 2 : 1;
      ctx.stroke();

      // Legend label
      ctx.fillStyle = '#333';
      ctx.fillText(item.label, x + 15, legendY + 9);
    });

    // Convert to image for download
    setMapImage(canvas.toDataURL('image/png'));
  }, [stationData, stationCoordinates, allFloodPoints, selectedCountry]);

  const handleDownload = () => {
    if (!mapImage) return;

    const link = document.createElement('a');
    link.download = `station-map-${stationData?.section_id || 'location'}-${new Date().toISOString().split('T')[0]}.png`;
    link.href = mapImage;
    link.click();
  };

  return (
    <Box>
      <Box sx={{ 
        border: '2px solid #e0e0e0', 
        borderRadius: 1, 
        overflow: 'hidden',
        backgroundColor: '#fff',
        mb: 2
      }}>
        <canvas 
          ref={canvasRef} 
          width={400} 
          height={400}
          style={{ display: 'block', width: '100%', height: 'auto' }}
        />
      </Box>
      
      <Button
        variant="outlined"
        fullWidth
        startIcon={<DownloadIcon />}
        onClick={handleDownload}
        disabled={!mapImage}
        sx={{ 
          borderColor: '#1B6840',
          color: '#1B6840',
          '&:hover': {
            borderColor: '#145032',
            backgroundColor: 'rgba(27, 104, 64, 0.04)'
          }
        }}
      >
        Export Map as PNG
      </Button>
    </Box>
  );
};

export default StaticMapCanvas;
