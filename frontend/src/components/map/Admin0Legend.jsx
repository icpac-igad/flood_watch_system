import React from 'react';

const Admin0Legend = ({ isSidebarActive, isVisible }) => {
  // Only render if the Admin 0 layer is active
  if (!isVisible) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '160px',
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
        Country Boundaries
      </div>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        {/* Admin 0 Boundary */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <div style={{
            width: '50px',
            height: '3px',
            backgroundColor: '#2c5f2d',
            borderRadius: '2px',
            flexShrink: 0
          }}></div>
          <span style={{
            color: '#555',
            fontSize: '12px',
            lineHeight: '1.3'
          }}>
            International Boundaries
          </span>
        </div>
      </div>
    </div>
  );
};

export default Admin0Legend;
