import React from 'react';
import { Container, Grid, Card, CardContent, CardMedia, Typography, Box } from '@mui/material';
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
    <Container maxWidth={false} sx={{ py: 4 }}>
      <Typography variant="h3" align="center" sx={{ mb: 5, color: '#1B5E20', fontWeight: 600 }}>
        Project Partners
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {partners.map((partner, pIndex) => (
          <Grid item key={pIndex} xs={12} md={4}>
            <Card sx={{ height: '100%', boxShadow: 2, textAlign: 'center' }}>
              <CardContent>
                <CardMedia
                  component="img"
                  image={partner.logo}
                  alt={`${partner.name} logo`}
                  sx={{ maxHeight: '100px', maxWidth: '150px', objectFit: 'contain', margin: '0 auto 16px' }}
                />
                <Typography variant="h6" component="div" gutterBottom>
                  {partner.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {partner.description}
                </Typography>
                <Typography variant="body2" sx={{ fontStyle: 'italic', mt: 1 }}>
                  {partner.role}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

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