import React, { useState, useEffect } from 'react';
import { Container, Alert } from 'react-bootstrap';

const Reports = () => {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate loading state for the purpose of the example
    setTimeout(() => {
      setLoading(false);
    }, 2000);
  }, []);

  return (
    <Container className="text-center py-5">
      <Alert variant="info">
        This feature is under development. Please bear with us as we work on improving Flood Reporting.
      </Alert>
    </Container>
  );
};

export default Reports;
