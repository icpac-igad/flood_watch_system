import React from 'react';
import { Container, Row, Col, Card } from 'react-bootstrap';
import icpacLogo from '@assets/icpac.jpg';
import cimaLogo from '@assets/cima_research_foundation_logo.jpg';
import undrrLogo from '@assets/banner-logo-undrr.png';


const Partners = () => {
  const partners = [
    {
      name: "ICPAC",
      description: "IGAD Climate Prediction and Applications Centre",
      role: "Regional Climate Centre for Eastern Africa and Host Flood Watch System",
      logo: icpacLogo
    },
    {
      name: "CIMA Research Foundation",
      description: "Research and Collaboration Partner",
      role: "Implementing FloodPROOFS East Africa (FPEA) Forecasting Chain",
      logo: cimaLogo
    },
    {
      name: "UNDRR",
      description: "United Nations Office for Disaster Risk Reduction",
      role: "Program Implementation and Early Warning Systems",
      logo: undrrLogo
    }
  ];

  // const fundingSources = [
  //   {
  //     name: "Italian Ministry of Foreign Affairs",
  //     description: "Primary Funding Source",
  //     logo: '/src/assets/Logo_MAECI_colori_EN.png'
  //   },
  //   {
  //     name: "Agency for International Cooperation (AICS)",
  //     description: "Collaborative Funding Partner",
  //     logo: '/src/assets/italian-aid-logo.png'
  //   }
  // ];

  return (
    <Container fluid className="partners-page p-4">
      <h1 className="text-center mb-5" style={{ color: '#1B5E20' }}>Project Partners</h1>
      
      <Row className="mb-4">
        {partners.map((partner, pIndex) => (
          <Col key={pIndex} md={4} className="mb-3">
            <Card className="h-100 shadow-sm text-center">
              <Card.Body>
                <img
                  src={partner.logo}
                  alt={`${partner.name} logo`}
                  style={{ maxHeight: '100px', maxWidth: '150px', objectFit: 'contain' }}
                  className="mb-3"
                />
                <Card.Title>{partner.name}</Card.Title>
                <Card.Text>
                  <small>{partner.description}</small>
                  <br />
                  <em>{partner.role}</em>
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>

      {/* <Row className="mb-4">
        <Col md={12}>
          <h3>Funding and Support 💡</h3>
        </Col>
        {fundingSources.map((source, index) => (
          <Col key={index} md={6} className="mb-3">
            <Card className="h-100 shadow-sm text-center">
              <Card.Body>
                <img
                  src={source.logo}
                  alt={`${source.name} logo`}
                  style={{ maxHeight: '100px', maxWidth: '150px', objectFit: 'contain' }}
                  className="mb-3"
                />
                <Card.Title>{source.name}</Card.Title>
                <Card.Text>
                  <em>{source.description}</em>
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row> */}

      {/* <Row>
        <Col md={12} className="text-center">
          <p className="text-muted">
            Funding for the "Programme for a Continental Coordination, 
            Early Warning and Action System in Africa - Phase 3"
          </p>
        </Col>
      </Row> */}
    </Container>
  );
};
export default Partners;