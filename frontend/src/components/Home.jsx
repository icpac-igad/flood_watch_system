import React from 'react';
import { Container, Row, Col, Carousel } from 'react-bootstrap';
import { Link } from 'react-router-dom';

const Home = () => {
  const carouselImages = [
    {
      src: '/assets/flood-aerial.jpg',
      title: 'Real-time Flood Monitoring',
      desc: 'Advanced monitoring systems across East Africa'
    },
    {
      src: '/assets/flood-banner.jpg',
      title: 'Early Warning Systems',
      desc: 'Timely alerts for flood risk areas'
    },
    {
      src: '/assets/flood-rescue.jpg',
      title: 'Community Resilience',
      desc: 'Building stronger flood-resistant communities'
    },
    {
      src: '/assets/calibration-map.jpg',
      title: 'Data-Driven Insights',
      desc: 'Comprehensive flood analysis and prediction'
    }
  ];

  return (
    <div className="home-page">
      <Carousel fade className="hero-carousel" interval={5000}>
        {carouselImages.map((image, index) => (
          <Carousel.Item key={index}>
            <div 
              className="carousel-image"
              style={{ backgroundImage: `url(${image.src})` }}
            >
              <Container>
                <Row className="align-items-center min-vh-100">
                  <Col md={8} className="text-white">
                    <h1 className="display-4 fw-bold mb-4 animate-text">{image.title}</h1>
                    <p className="lead mb-4 animate-text-delay">{image.desc}</p>
                    <Link to="/map" className="btn btn-light btn-lg animate-button">Explore Map</Link>
                  </Col>
                </Row>
              </Container>
            </div>
          </Carousel.Item>
        ))}
      </Carousel>
    </div>
  );
};

export default Home;