import React from 'react';

interface InfoIconProps {
  layerName: string;
  onClick: (layerName: string) => void;
}

export const InfoIcon: React.FC<InfoIconProps> = ({ layerName, onClick }) => (
  <span 
    className="info-icon" 
    onClick={(e) => {
      e.stopPropagation();
      onClick(layerName);
    }}
    style={{
      cursor: 'pointer',
      marginLeft: '8px',
      fontSize: '14px',
      color: '#007bff',
      fontWeight: 'bold',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '20px',
      height: '20px',
      borderRadius: '50%',
      border: '1px solid #007bff',
      lineHeight: '1'
    }}
  >
    i
  </span>
);
