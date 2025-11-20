import React from 'react';
import { Button, Box } from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import PrintIcon from '@mui/icons-material/Print';

export const ReportDownloadButton = ({ reportTitle, finalStatus }) => {
  
  const handlePrint = () => {
    window.print();
  };

  const handleDownloadHTML = () => {
    // Create a clean HTML version for download
    const reportContent = document.getElementById('flood-report-content');
    if (!reportContent) return;

    const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>${reportTitle}</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 40px;
      color: #333;
    }
    h1, h2, h3 {
      color: #1B6840;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
    }
    th, td {
      border: 1px solid #ddd;
      padding: 12px;
      text-align: left;
    }
    th {
      background-color: #1B6840;
      color: white;
    }
    .status-badge {
      padding: 4px 12px;
      border-radius: 4px;
      color: white;
      font-weight: bold;
      display: inline-block;
    }
    .critical { background-color: #b71c1c; }
    .high-risk { background-color: #f44336; }
    .moderate { background-color: #ff9800; }
    .low-risk { background-color: #4caf50; }
    .approved { background-color: #4caf50; }
    .pending { background-color: #ff9800; }
  </style>
</head>
<body>
  ${reportContent.innerHTML}
  <footer style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #1B6840;">
    <p><strong>IGAD Climate Prediction and Applications Centre (ICPAC)</strong></p>
    <p>East Africa Flood Watch | Generated: ${new Date().toLocaleString()}</p>
  </footer>
</body>
</html>`;

    // Create blob and download
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${reportTitle.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Only show download if report is approved
  const isApproved = finalStatus === 'approved';

  return (
    <Box sx={{ display: 'flex', gap: 2, my: 2 }}>
      <Button
        variant="contained"
        startIcon={<PrintIcon />}
        onClick={handlePrint}
        sx={{ backgroundColor: '#1B6840', '&:hover': { backgroundColor: '#145030' } }}
      >
        Print Report
      </Button>
      
      {isApproved && (
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={handleDownloadHTML}
          color="success"
        >
          Download Approved Report
        </Button>
      )}
    </Box>
  );
};

// Print-specific styles
export const PrintStyles = () => (
  <style>{`
    @media print {
      .no-print {
        display: none !important;
      }
      body {
        margin: 0;
        padding: 20px;
      }
      @page {
        margin: 2cm;
      }
    }
  `}</style>
);
