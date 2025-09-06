import React from 'react';
import { Container, Row, Col, Card } from 'react-bootstrap';

const About = () => {
  const keyFeatures = [
    {
      title: "Mission 🎯",
      description: "Enhance regional resilience through innovative flood monitoring"
    },
    {
      title: "Regional Coverage 🌍",
      description: "Comprehensive monitoring across East African river basins"
    },
    {
      title: "Community Impact 🏙️",
      description: "Empowering communities with early warning systems"
    },
    {
      title: "Technological Innovation 🤖",
      description: "Leveraging AI and satellite technology for precise predictions"
    }
  ];

  return (
    <Container fluid className="about-page p-4">
      <h1 className="text-center mb-5" style={{ color: '#1B5E20' }}>About East Africa Flood Watch</h1>
      <Row className="mb-5">
        <Col md={8} className="mx-auto text-center">
          <p className="lead">A collaborative initiative dedicated to mitigating flood risks through advanced monitoring, early warning systems, and community resilience strategies.</p>
        </Col>
      </Row>
      <Row>
        {keyFeatures.map((feature, index) => (
          <Col key={index} md={12} className="mb-4">
            <Card className="h-100 shadow-sm text-center">
              <Card.Body>
                <Card.Title>{feature.title}</Card.Title>
                <Card.Text className="text-muted">{feature.description}</Card.Text>
              </Card.Body>
            </Card>
          </Col>
        ))}
      </Row>
    </Container>
  );
};

export default About;