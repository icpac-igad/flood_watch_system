import React, { useState } from 'react';
import { List, ListItem } from '@mui/material';
import { WMSLayer } from '../../types/map.types';
import { InfoIcon } from '../ui/InfoIcon';

interface LayerSelectorProps {
  title: string;
  layers: WMSLayer[];
  selectedLayers: Set<string>;
  onLayerSelect: (layer: WMSLayer) => void;
  onInfoClick: (layerName: string) => void;
  selectedDate: string | null;
  onDateChange: (date: string) => void;
  showCalendar?: boolean;
}

export const LayerSelector: React.FC<LayerSelectorProps> = ({
  title,
  layers,
  selectedLayers,
  onLayerSelect,
  onInfoClick,
  selectedDate,
  onDateChange,
  showCalendar = true
}) => {
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);

  return (
    <div className="layers-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h6 style={{ margin: 0 }}>{title}</h6>
        {showCalendar && (
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setIsCalendarOpen(!isCalendarOpen)}
              title={`Filter by date: ${selectedDate || new Date().toISOString().split('T')[0]}`}
              style={{
                padding: '2px 6px',
                fontSize: '10px',
                backgroundColor: '#034930',
                color: 'white',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
                minHeight: '20px',
                lineHeight: '1'
              }}
            >
              📅
            </button>
            {isCalendarOpen && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '2px',
                backgroundColor: 'white',
                border: '1px solid #ddd',
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                zIndex: 1000,
                padding: '6px'
              }}>
                <input
                  type="date"
                  value={selectedDate || new Date().toISOString().split('T')[0]}
                  onChange={(e) => {
                    onDateChange(e.target.value);
                    setIsCalendarOpen(false);
                  }}
                  max={new Date().toISOString().split('T')[0]}
                  style={{
                    padding: '3px',
                    border: '1px solid #ddd',
                    borderRadius: '3px',
                    fontSize: '12px',
                    width: '120px'
                  }}
                />
              </div>
            )}
          </div>
        )}
      </div>
      <ListGroup className="layer-selector">
        {layers.map((layer) => (
          <ListGroup.Item key={layer.name}>
            <div className="layer-content">
              <div className="toggle-switch-small">
                <input
                  type="checkbox"
                  id={`layer-${layer.name}`}
                  checked={selectedLayers.has(layer.layer)}
                  onChange={() => onLayerSelect(layer)}
                />
                <label
                  htmlFor={`layer-${layer.name}`}
                  className="toggle-slider-small"
                />
              </div>
              <label htmlFor={`layer-${layer.name}`} className="layer-label">
                {layer.name}
              </label>
            </div>
            <InfoIcon layerName={layer.name} onClick={onInfoClick} />
          </ListGroup.Item>
        ))}
      </ListGroup>
    </div>
  );
};
