import React from 'react';

const LakesLegend = ({ isSidebarActive, isVisible }) => {
  // Only render if the Lakes layer is active
  if (!isVisible) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '240px',
      left: isSidebarActive ? '340px' : '20px',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      padding: '12px 16px',
      borderRadius: '8px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
      zIndex: 1000,
      transition: 'left 0.3s ease',
      fontSize: '13px',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      maxWidth: '250px'
    }}>
      <div style={{
        fontWeight: '600',
        marginBottom: '10px',
        color: '#333',
        fontSize: '14px'
      }}>
        Water Bodies
      </div>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        {/* Lakes */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <div style={{
            width: '40px',
            height: '25px',
            backgroundColor: 'rgb(30, 90, 160)',
            borderRadius: '4px',
            flexShrink: 0,
            opacity: 0.6
          }}></div>
          <span style={{
            color: '#555',
            fontSize: '12px',
            lineHeight: '1.3'
          }}>
            Lakes and Reservoirs
          </span>
        </div>
      </div>
    </div>
  );
};

export default LakesLegend;
