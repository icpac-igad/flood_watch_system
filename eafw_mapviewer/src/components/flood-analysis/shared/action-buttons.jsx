/**
 * Action Buttons Component
 * Browser-based PDF export - no API required
 */
import React, { useState, useCallback } from "react";
import { isEmpty } from "lodash";

import Button from "@/components/ui/button";

import "./action-buttons.scss";

const ActionButtons = ({ params, settings, forecastData, updateSettings }) => {
  const [pdfLoading, setPdfLoading] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [subscribeDialogOpen, setSubscribeDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState({ show: false, message: "", type: "info" });
  const [shareUrl, setShareUrl] = useState("");

  // Show snackbar notification
  const showSnackbar = (message, type = "info") => {
    setSnackbar({ show: true, message, type });
    setTimeout(() => setSnackbar({ show: false, message: "", type: "info" }), 4000);
  };

  // Generate PDF report - opens in new window for Chrome PDF viewer
  const handleGeneratePdf = useCallback(async () => {
    setPdfLoading(true);

    try {
      // Get the report content
      const reportContent = document.querySelector(".c-flood-analysis");
      if (!reportContent) {
        showSnackbar("Report content not found", "error");
        return;
      }

      // Clone the content
      const clonedContent = reportContent.cloneNode(true);

      // Remove unwanted elements from clone
      const elementsToRemove = clonedContent.querySelectorAll(
        ".c-action-buttons, .c-global-options, .top-rects"
      );
      elementsToRemove.forEach((el) => el.remove());

      // Create new window
      const printWindow = window.open("", "_blank", "width=900,height=700");

      if (!printWindow) {
        showSnackbar("Please allow popups to export PDF", "error");
        return;
      }

      // Get current styles
      const styles = Array.from(document.styleSheets)
        .map((sheet) => {
          try {
            return Array.from(sheet.cssRules)
              .map((rule) => rule.cssText)
              .join("\n");
          } catch (e) {
            // External stylesheets may throw CORS errors
            return "";
          }
        })
        .join("\n");

      // Write the document
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>Flood Forecast Analysis Report - ${params?.placename || "East Africa Region"}</title>
          <style>
            ${styles}

            body {
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              margin: 0;
              padding: 20px;
              background: white;
            }

            .c-flood-analysis {
              max-width: 1000px;
              margin: 0 auto;
            }

            .report-header {
              background: linear-gradient(135deg, #1a5d1a 0%, #2e7d32 100%) !important;
              color: white;
              padding: 20px;
              border-radius: 8px;
              margin-bottom: 20px;
              -webkit-print-color-adjust: exact;
              print-color-adjust: exact;
            }

            .report-title {
              font-size: 24px;
              font-weight: bold;
              margin-bottom: 10px;
            }

            .print-instructions {
              background: #f5f5f5;
              border: 1px solid #ddd;
              border-radius: 8px;
              padding: 15px;
              margin-bottom: 20px;
              text-align: center;
            }

            .print-instructions button {
              background: #1a5d1a;
              color: white;
              border: none;
              padding: 10px 24px;
              border-radius: 4px;
              cursor: pointer;
              font-size: 14px;
              margin: 5px;
            }

            .print-instructions button:hover {
              background: #145214;
            }

            @media print {
              .print-instructions { display: none !important; }
              body { padding: 0; }
              @page { size: A4; margin: 10mm; }
            }
          </style>
        </head>
        <body>
          <div class="print-instructions">
            <p><strong>To save as PDF:</strong> Press Ctrl+P (or Cmd+P on Mac) and select "Save as PDF"</p>
            <button onclick="window.print()">🖨️ Print / Save as PDF</button>
            <button onclick="window.close()">✕ Close</button>
          </div>
          ${clonedContent.outerHTML}
        </body>
        </html>
      `);

      printWindow.document.close();
      showSnackbar("Report opened in new window - use Print to save as PDF", "info");
    } catch (error) {
      console.error("PDF generation error:", error);
      showSnackbar("Failed to generate PDF. Please try again.", "error");
    } finally {
      setPdfLoading(false);
    }
  }, [params]);

  // Handle share button click
  const handleShare = useCallback(() => {
    const currentUrl = window.location.href;
    setShareUrl(currentUrl);
    setShareDialogOpen(true);
  }, []);

  // Copy share URL to clipboard
  const handleCopyUrl = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      showSnackbar("Link copied to clipboard!", "success");
    } catch (error) {
      console.error("Copy failed:", error);
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = shareUrl;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
      showSnackbar("Link copied to clipboard!", "success");
    }
  }, [shareUrl]);

  // Handle print
  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  // Handle subscribe
  const handleSubscribe = useCallback(() => {
    setSubscribeDialogOpen(true);
  }, []);

  return (
    <div className="c-action-buttons">
      {/* PDF Export Button */}
      <button
        className="action-btn pdf-btn"
        onClick={handleGeneratePdf}
        disabled={pdfLoading}
      >
        {pdfLoading ? (
          <>
            <span className="spinner"></span>
            Generating...
          </>
        ) : (
          <>📄 Export PDF</>
        )}
      </button>

      {/* Share Button */}
      <button className="action-btn share-btn" onClick={handleShare}>
        🔗 Share
      </button>

      {/* Print Button */}
      <button className="action-btn print-btn" onClick={handlePrint}>
        🖨️ Print
      </button>

      {/* Subscribe Button */}
      <button className="action-btn subscribe-btn" onClick={handleSubscribe}>
        🔔 Subscribe
      </button>

      {/* Share Dialog */}
      {shareDialogOpen && (
        <div className="dialog-overlay" onClick={() => setShareDialogOpen(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <h3>Share Report</h3>
              <button
                className="dialog-close"
                onClick={() => setShareDialogOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="dialog-content">
              <div className="share-url-container">
                <input
                  type="text"
                  value={shareUrl}
                  readOnly
                  className="share-url-input"
                />
                <button className="copy-btn" onClick={handleCopyUrl}>
                  📋 Copy
                </button>
              </div>
              <p className="share-note">
                Share this link to allow others to view the same analysis with
                your current parameters.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Subscribe Dialog */}
      {subscribeDialogOpen && (
        <div className="dialog-overlay" onClick={() => setSubscribeDialogOpen(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <h3>Subscribe to Alerts</h3>
              <button
                className="dialog-close"
                onClick={() => setSubscribeDialogOpen(false)}
              >
                ×
              </button>
            </div>
            <div className="dialog-content">
              <p>
                Get notified when flood alerts are issued for {params?.placename || "this region"}.
              </p>
              <input
                type="email"
                placeholder="your.email@example.com"
                className="email-input"
              />
              <div className="info-alert">
                Subscription functionality will be available soon. Contact ICPAC
                for more information.
              </div>
              <div className="dialog-actions">
                <button
                  className="cancel-btn"
                  onClick={() => setSubscribeDialogOpen(false)}
                >
                  Cancel
                </button>
                <button
                  className="subscribe-submit-btn"
                  onClick={() => {
                    setSubscribeDialogOpen(false);
                    showSnackbar("Subscription feature coming soon!", "info");
                  }}
                >
                  Subscribe
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Snackbar */}
      {snackbar.show && (
        <div className={`snackbar snackbar-${snackbar.type}`}>
          {snackbar.message}
        </div>
      )}
    </div>
  );
};

export default ActionButtons;
