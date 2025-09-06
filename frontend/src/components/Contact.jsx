import React, { useState } from 'react';
import { Container, Row, Col, Form, Button, Alert } from 'react-bootstrap';

const ContactUs = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: ''
  });
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prevState => ({
      ...prevState,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('Form submitted:', formData);
    setSubmitted(true);
    setFormData({
      name: '',
      email: '',
      message: ''
    });
  };

  return (
    <Container className="contact-page mt-4">
      <h1 className="text-center mb-4">Contact Us 📩</h1>
      <Row>
        <Col md={6} className="mx-auto">
          {submitted && (
            <Alert variant="success" onClose={() => setSubmitted(false)} dismissible>
              Thank you for your message! We'll get back to you soon.
            </Alert>
          )}
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Name</Form.Label>
              <Form.Control
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Email</Form.Label>
              <Form.Control
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label>Message</Form.Label>
              <Form.Control
                as="textarea"
                name="message"
                value={formData.message}
                onChange={handleChange}
                rows={4}
                required
              />
            </Form.Group>
            <div className="text-center">
              <Button variant="primary" type="submit">
                Send Message
              </Button>
            </div>
          </Form>
        </Col>
      </Row>
      <Row className="mt-4">
        <Col md={8} className="mx-auto text-center">
          <h4>Contact Information 📞</h4>
          <p>
            IGAD Climate Prediction & Applications Centre (ICPAC)<br />
            P.O. Box 10304 - 00100, Nairobi, Kenya<br />
            Email: info@icpac.net<br />
            Phone: +254 20 3742000
          </p>
        </Col>
      </Row>
    </Container>
  );
};

export default ContactUs;