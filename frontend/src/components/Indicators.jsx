import React, { useState } from 'react';
import { Container, Row, Col, Card, Modal } from 'react-bootstrap';

const FloodIndicators = () => {
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedIndicator, setSelectedIndicator] = useState(null);

  const indicators = [
    {
      title: "Water Level Monitoring",
      description: "Comprehensive monitoring of major river basins",
      image: "water-level-monitoring.png",
      icon: "🌊",
      details: "Real-time river and reservoir water levels tracked using remote sensors and satellite data. This helps predict potential flooding and informs decision-making."
    },
    {
      title: "Precipitation Forecasts",
      description: "Advanced rainfall prediction models",
      image: "precipitation-forecasts.jpg",
      icon: "☔",
      details: "Utilizing satellite imagery, weather station data, and machine learning to provide accurate rainfall forecasts for the East Africa region."
    },
    {
      title: "Flood Risk Assessment",
      description: "Predictive flood vulnerability mapping",
      image: "flood-risk-assessment.png",
      icon: "⚠️",
      details: "Analyzing historical flood data, terrain models, and other factors to identify high-risk areas and guide targeted interventions."
    },
    {
      title: "Geographic Vulnerability",
      description: "Location-specific flood susceptibility",
      image: "geographic-vulnerability.jpg",
      icon: "🗺️",
      details: "GIS-based mapping of flood-prone regions to inform local disaster preparedness and resource allocation."
    }
  ];

  const handleIndicatorClick = (indicator) => {
    setSelectedIndicator(indicator);
    setShowDetailModal(true);
  };

  return (
    <Container fluid className="flood-indicators-page p-4" style={{ 
      background: 'linear-gradient(to bottom, #f8f9fa, #ffffff)',
      minHeight: '100vh'
    }}>
      <h1 className="text-center mb-5" style={{ 
        color: '#1B5E20',
        fontSize: '2.5rem',
        fontWeight: '500'
      }}>
        Flood Indicators
      </h1>

      <Row className="justify-content-center">
        {indicators.map((indicator, index) => (
          <Col key={index} md={6} lg={6} className="mb-4">
            <Card
              className="h-100 shadow-sm"
              role="button"
              onClick={() => handleIndicatorClick(indicator)}
              style={{
                borderRadius: '12px',
                border: 'none',
                transition: 'all 0.3s ease',
                cursor: 'pointer',
                borderLeft: `5px solid ${
                  indicator.title === 'Flood Risk Assessment' ? '#D32F2F' :
                  indicator.title === 'Geographic Vulnerability' ? '#FFA000' :
                  '#2E7D32'
                }`
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-5px)';
                e.currentTarget.style.boxShadow = '0 4px 15px rgba(0,0,0,0.1)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 2px 5px rgba(0,0,0,0.05)';
              }}
            >
              <Card.Body className="d-flex align-items-center p-4">
                <div className="icon-container me-4" style={{ fontSize: '2.5rem' }}>
                  {indicator.icon}
                </div>
                <div>
                  <Card.Title style={{
                    fontSize: '1.25rem',
                    fontWeight: '600',
                    marginBottom: '0.5rem',
                    color: '#2E7D32'
                  }}>
                    {indicator.title}
                  </Card.Title>
                  <Card.Text style={{
                    color: '#666',
                    marginBottom: 0
                  }}>
                    {indicator.description}
                  </Card.Text>
                </div>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      <Modal
        show={showDetailModal}
        onHide={() => setShowDetailModal(false)}
        size="lg"
        centered
      >
        {selectedIndicator && (
          <>
            <Modal.Header closeButton style={{ border: 'none', padding: '1.5rem' }}>
              <Modal.Title className="d-flex align-items-center">
                <span className="me-3" style={{ fontSize: '2rem' }}>
                  {selectedIndicator.icon}
                </span>
                {selectedIndicator.title}
              </Modal.Title>
            </Modal.Header>
            <Modal.Body className="px-4 pb-4">
              <Row>
                <Col md={8}>
                  <h4 className="mb-3" style={{ color: '#2E7D32' }}>
                    {selectedIndicator.description}
                  </h4>
                  <p className="text-muted">
                    {selectedIndicator.details}
                  </p>
                </Col>
                <Col md={4}>
                  <img
                    src={`/assets/${selectedIndicator.image}`}
                    alt={selectedIndicator.title}
                    className="img-fluid rounded shadow-sm"
                    style={{
                      width: '100%',
                      height: 'auto',
                      objectFit: 'cover'
                    }}
                  />
                </Col>
              </Row>
            </Modal.Body>
          </>
        )}
      </Modal>
    </Container>
  );
};

export default FloodIndicators;