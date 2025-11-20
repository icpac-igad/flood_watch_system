import React, { useState, useEffect } from 'react';
import { Container, Card, CardContent, Button, Table, TableHead, TableBody, TableRow, TableCell, Chip, CircularProgress, Alert, ButtonGroup, Menu, MenuItem } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import './Reports.css';

const Reports = () => {
  const navigate = useNavigate();
  const [savedReports, setSavedReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSavedReports();
  }, []);

  const fetchSavedReports = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/saved-reports');
      if (!response.ok) throw new Error('Failed to fetch reports');
      const data = await response.json();
      // API returns {results: [...], count, next, previous}
      setSavedReports(data.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const colors = {
      'approved': 'success',
      'pending': 'warning',
      'rejected': 'error',
      'changes_requested': 'info'
    };
    return <Chip label={status?.toUpperCase() || 'PENDING'} color={colors[status] || 'default'} size="small" />;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const shareReport = (report, platform) => {
    // Use relative URL to avoid HTTPS issues
    const reportUrl = `/api/saved-reports/${report.id}/pdf/`;
    const fullUrl = `${window.location.protocol}//${window.location.host}${reportUrl}`;
    const text = `East Africa FloodWatch Report: ${report.report_title}`;

    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(fullUrl)}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(fullUrl)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(fullUrl)}`,
      whatsapp: `https://wa.me/?text=${encodeURIComponent(text + ' ' + fullUrl)}`,
      email: `mailto:?subject=${encodeURIComponent(text)}&body=${encodeURIComponent('View the full report: ' + fullUrl)}`
    };

    window.open(urls[platform], '_blank', 'width=600,height=400');
  };

  if (loading) {
    return (
      <Container sx={{ mt: 5, textAlign: 'center' }}>
        <CircularProgress />
        <p style={{ marginTop: '1rem' }}>Loading saved reports...</p>
      </Container>
    );
  }

  if (error) {
    return (
      <Container sx={{ mt: 5 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          <strong>Error Loading Reports</strong>
          <p>{error}</p>
          <Button variant="outlined" color="error" onClick={fetchSavedReports} sx={{ mt: 1 }}>
            Retry
          </Button>
        </Alert>
      </Container>
    );
  }

  if (savedReports.length === 0) {
    return (
      <Container sx={{ mt: 5 }}>
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 5 }}>
            <h3>No Reports Generated</h3>
            <p style={{ color: '#666' }}>
              To generate a flood analysis report:
            </p>
            <ol style={{ textAlign: 'left', maxWidth: '600px', margin: '0 auto' }}>
              <li>Go to the <strong>MAPVIEWER</strong> tab</li>
              <li>Select a country from the dropdown</li>
              <li>Click on any flood monitoring station</li>
              <li>Click the <strong>"📊 Report"</strong> button in the popup</li>
            </ol>
            <Button 
              variant="contained" 
              color="primary"
              onClick={() => navigate('/map')}
              sx={{ mt: 3 }}
            >
              Go to Map Viewer
            </Button>
          </CardContent>
        </Card>
      </Container>
    );
  }

  return (
    <Container className="reports-container mt-4 mb-5">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Saved Flood Analysis Reports</h2>
        <Button 
          variant="primary" 
          onClick={() => navigate('/map')}
        >
          + Generate New Report
        </Button>
      </div>

      <Card>
        <Card.Body>
          <div className="table-responsive">
            <Table hover>
              <thead className="table-light">
                <tr>
                  <th>Report Title</th>
                  <th>Country</th>
                  <th>Generated</th>
                  <th>Stations</th>
                  <th>Member State</th>
                  <th>ICPAC</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {savedReports.map((report) => (
                  <tr key={report.id}>
                    <td>
                      <strong>{report.report_title}</strong>
                      {report.station_id && (
                        <div className="text-muted small">Station: {report.station_id}</div>
                      )}
                    </td>
                    <td>{report.country || 'N/A'}</td>
                    <td className="small">{formatDate(report.created_at)}</td>
                    <td>
                      <div className="small">
                        <span className="text-danger">🚨 {report.emergency_count || 0}</span> | 
                        <span className="text-danger"> ⚠️ {report.alarm_count || 0}</span> | 
                        <span className="text-warning"> ⚡ {report.warning_count || 0}</span> | 
                        <span className="text-success"> ✓ {report.normal_count || 0}</span>
                      </div>
                      <div className="text-muted small">Total: {report.total_stations}</div>
                    </td>
                    <td className="small">
                      {report.member_state_approver ? (
                        <>
                          <div>{report.member_state_approver}</div>
                          <div className="text-muted">{report.member_state_organization}</div>
                          <div>{getStatusBadge(report.member_state_status)}</div>
                        </>
                      ) : (
                        <span className="text-muted">Pending</span>
                      )}
                    </td>
                    <td className="small">
                      {report.icpac_approver ? (
                        <>
                          <div>{report.icpac_approver}</div>
                          <div>{getStatusBadge(report.icpac_status)}</div>
                        </>
                      ) : (
                        <span className="text-muted">Pending</span>
                      )}
                    </td>
                    <td>{getStatusBadge(report.final_status)}</td>
                    <td>
                      <ButtonGroup size="sm">
                        <Button
                          variant="outline-primary"
                          onClick={() => window.open(`/api/saved-reports/${report.id}/pdf/`, '_blank')}
                          title="View PDF"
                        >
                          📄 View
                        </Button>
                        <Dropdown as={ButtonGroup} size="sm">
                          <Dropdown.Toggle variant="outline-secondary" id={`dropdown-share-${report.id}`} title="Share Report">
                            📤 Share
                          </Dropdown.Toggle>
                          <Dropdown.Menu>
                            <Dropdown.Item onClick={() => shareReport(report, 'twitter')}>
                              🐦 Twitter
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => shareReport(report, 'facebook')}>
                              👍 Facebook
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => shareReport(report, 'linkedin')}>
                              💼 LinkedIn
                            </Dropdown.Item>
                            <Dropdown.Item onClick={() => shareReport(report, 'whatsapp')}>
                              💬 WhatsApp
                            </Dropdown.Item>
                            <Dropdown.Divider />
                            <Dropdown.Item onClick={() => shareReport(report, 'email')}>
                              ✉️ Email
                            </Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                      </ButtonGroup>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default Reports;
