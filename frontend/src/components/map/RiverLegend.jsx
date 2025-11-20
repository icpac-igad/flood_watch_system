import React from 'react';

const RiverLegend = ({ isSidebarActive, isVisible }) => {
  // Only render if the Rivers layer is active
  if (!isVisible) return null;

  return (
    <div style={{
      position: 'fixed',
      bottom: '40px',
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
        River Classification
      </div>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        {/* Order 6+ - White */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <div style={{
            width: '50px',
            height: '1.2px',
            backgroundColor: 'rgb(245, 250, 255)',
            border: '1px solid #ddd',
            borderRadius: '2px',
            flexShrink: 0
          }}></div>
          <span style={{
            color: '#555',
            fontSize: '12px',
            lineHeight: '1.3'
          }}>
            Order 6+ (White)
          </span>
        </div>

        {/* Order 4-5 - Semi-white */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <div style={{
            width: '40px',
            height: '0.8px',
            backgroundColor: 'rgb(220, 235, 245)',
            border: '1px solid #ccc',
            borderRadius: '1px',
            flexShrink: 0,
            marginLeft: '5px'
          }}></div>
          <span style={{
            color: '#555',
            fontSize: '12px',
            lineHeight: '1.3'
          }}>
            Order 4-5 (Semi-white)
          </span>
        </div>

        {/* Order 1-3 - DARK BLUE */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <div style={{
            width: '30px',
            height: '0.5px',
            backgroundColor: 'rgb(30, 90, 160)',
            borderRadius: '1px',
            flexShrink: 0,
            marginLeft: '10px'
          }}></div>
          <span style={{
            color: '#555',
            fontSize: '12px',
            lineHeight: '1.3'
          }}>
            Order 1-3 (Dark Blue)
          </span>
        </div>
      </div>
    </div>
  );
};

export default RiverLegend;
