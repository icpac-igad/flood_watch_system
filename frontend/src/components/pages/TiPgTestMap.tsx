/**
 * TiPg Vector Tiles Test Map
 * Quick test page to verify TiPg vector tiles are rendering correctly
 * Access at: http://localhost:8094/tipg-test
 */

import { useState } from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import { TiPgVectorLayer } from '../map/layers/TiPgVectorLayer';
import 'leaflet/dist/leaflet.css';

export const TiPgTestMap = () => {
  const [layers, setLayers] = useState({
    admin0: true,
    admin1: false,
    admin2: false,
    rivers: true,
    lakes: true
  });

  const toggleLayer = (layer: keyof typeof layers) => {
    setLayers(prev => ({ ...prev, [layer]: !prev[layer] }));
  };

  return (
    <div style={{
      display: 'flex',
      position: 'fixed',
      top: '80px',
      left: 0,
      right: 0,
      bottom: '30px',
      backgroundColor: '#fff'
    }}>
      {/* Sidebar */}
      <div style={{
        width: '250px',
        padding: '20px',
        backgroundColor: '#f5f5f5',
        overflowY: 'auto',
        height: '100%'
      }}>
        <h3>TiPg Vector Tiles Test</h3>
        <p style={{ fontSize: '12px', color: '#666' }}>
          Testing vector tiles from TiPg server
        </p>

        <hr />

        <h4>Layers</h4>

        <label style={{ display: 'block', marginBottom: '10px' }}>
          <input
            type="checkbox"
            checked={layers.admin0}
            onChange={() => toggleLayer('admin0')}
          />
          {' '}Country Boundaries (Admin0)
        </label>

        <label style={{ display: 'block', marginBottom: '10px' }}>
          <input
            type="checkbox"
            checked={layers.admin1}
            onChange={() => toggleLayer('admin1')}
          />
          {' '}Province Boundaries (Admin1)
        </label>

        <label style={{ display: 'block', marginBottom: '10px' }}>
          <input
            type="checkbox"
            checked={layers.admin2}
            onChange={() => toggleLayer('admin2')}
          />
          {' '}District Boundaries (Admin2)
        </label>

        <label style={{ display: 'block', marginBottom: '10px' }}>
          <input
            type="checkbox"
            checked={layers.rivers}
            onChange={() => toggleLayer('rivers')}
          />
          {' '}Rivers
        </label>

        <label style={{ display: 'block', marginBottom: '10px' }}>
          <input
            type="checkbox"
            checked={layers.lakes}
            onChange={() => toggleLayer('lakes')}
          />
          {' '}Lakes
        </label>

        <hr />

        <div style={{ fontSize: '11px', color: '#999' }}>
          <p><strong>Benefits:</strong></p>
          <ul>
            <li>90% smaller than WMS PNG</li>
            <li>Sharp at all zoom levels</li>
            <li>Interactive features</li>
            <li>Client-side styling</li>
          </ul>
        </div>
      </div>

      {/* Map */}
      <div style={{ flex: 1 }}>
        <MapContainer
          center={[0.3, 37.5]} // Kenya
          zoom={6}
          style={{ height: '100%', width: '100%' }}
          zoomControl={true}
        >
          {/* Base map */}
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />

          {/* TiPg Vector Tiles */}
          {layers.admin0 && (
            <TiPgVectorLayer
              collection="admin0"
              visible={layers.admin0}
              interactive={true}
              onFeatureClick={(props) => {
                console.log('Clicked admin0:', props);
                alert(`Country: ${props.country || 'Unknown'}`);
              }}
            />
          )}

          {layers.admin1 && (
            <TiPgVectorLayer
              collection="admin1"
              visible={layers.admin1}
            />
          )}

          {layers.admin2 && (
            <TiPgVectorLayer
              collection="admin2"
              visible={layers.admin2}
            />
          )}

          {layers.rivers && (
            <TiPgVectorLayer
              collection="rivers"
              visible={layers.rivers}
              interactive={true}
              onFeatureClick={(props) => {
                console.log('Clicked river:', props);
              }}
            />
          )}

          {layers.lakes && (
            <TiPgVectorLayer
              collection="lakes"
              visible={layers.lakes}
              interactive={true}
              onFeatureClick={(props) => {
                console.log('Clicked lake:', props);
              }}
            />
          )}
        </MapContainer>
      </div>
    </div>
  );
};

export default TiPgTestMap;
