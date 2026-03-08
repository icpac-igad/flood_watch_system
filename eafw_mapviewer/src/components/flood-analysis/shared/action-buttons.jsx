/**
 * Action Buttons Component
 * Client-side PDF export via jsPDF, share, print, subscribe
 */
import React, { useState, useCallback, useEffect } from "react";

import "./action-buttons.scss";

/**
 * Render the active report UI to a canvas for jsPDF export.
 */
const captureReportCanvas = async () => {
  const reportRoot = document.querySelector(".c-flood-analysis-body");
  if (!reportRoot) return null;

  const html2canvas = (await import("html2canvas")).default;
  try {
    return await html2canvas(reportRoot, {
      scale: 2,
      useCORS: true,
      backgroundColor: "#ffffff",
      logging: false,
      windowWidth: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
      windowHeight: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight),
    });
  } catch (e) {
    console.warn("Could not capture report body:", e);
    return null;
  }
};

const ActionButtons = ({ params }) => {
  const [pdfLoading, setPdfLoading] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [subscribeDialogOpen, setSubscribeDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState({ show: false, message: "", type: "info" });
  const [shareUrl, setShareUrl] = useState("");
  const [activeReport, setActiveReport] = useState(null);

  useEffect(() => {
    const handleActiveSelection = (event) => {
      const selected = event?.detail;
      if (!selected || !selected.id) {
        setActiveReport(null);
        return;
      }
      setActiveReport(selected);
    };

    window.addEventListener("flood-report-active-selection", handleActiveSelection);
    return () => window.removeEventListener("flood-report-active-selection", handleActiveSelection);
  }, []);

  // Show snackbar notification
  const showSnackbar = (message, type = "info") => {
    setSnackbar({ show: true, message, type });
    setTimeout(() => setSnackbar({ show: false, message: "", type: "info" }), 4000);
  };

  // Generate PDF directly in browser via jsPDF + html2canvas
  const handleGeneratePdf = useCallback(async () => {
    setPdfLoading(true);
    showSnackbar("Generating PDF report...", "info");

    try {
      const { jsPDF } = await import("jspdf");
      const canvas = await captureReportCanvas();
      const pdf = new jsPDF("p", "mm", "a4");
      const margin = 8;
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();

      if (canvas) {
        const imageData = canvas.toDataURL("image/jpeg", 0.92);
        const printableWidth = pageWidth - (margin * 2);
        const printableHeight = (canvas.height * printableWidth) / canvas.width;
        const pageBodyHeight = pageHeight - (margin * 2);

        let heightLeft = printableHeight;
        let yPosition = margin;

        pdf.addImage(
          imageData,
          "JPEG",
          margin,
          yPosition,
          printableWidth,
          printableHeight,
          undefined,
          "FAST"
        );
        heightLeft -= pageBodyHeight;

        while (heightLeft > 0) {
          pdf.addPage();
          yPosition = margin - (printableHeight - heightLeft);
          pdf.addImage(
            imageData,
            "JPEG",
            margin,
            yPosition,
            printableWidth,
            printableHeight,
            undefined,
            "FAST"
          );
          heightLeft -= pageBodyHeight;
        }
      } else {
        // Fallback text-only PDF when canvas capture fails.
        let y = 16;
        const lineGap = 7;
        const maxTextWidth = pageWidth - (margin * 2);

        pdf.setFontSize(15);
        pdf.text("Flood Analysis Report", margin, y);
        y += lineGap + 1;

        pdf.setFontSize(10);
        const fallbackLines = [
          `Reference date: ${params?.forecast_date || "N/A"}`,
          `Area: ${params?.placename || "East Africa Region"}`,
          activeReport?.report_key ? `Selected report: ${activeReport.report_key}` : "Selected report: none",
          activeReport?.status ? `Status: ${activeReport.status}` : "Status: draft/unapproved",
          "Report body screenshot failed, so this fallback summary was generated.",
        ];
        fallbackLines.forEach((line) => {
          const wrapped = pdf.splitTextToSize(line, maxTextWidth);
          pdf.text(wrapped, margin, y);
          y += (wrapped.length * 4.8) + 1;
        });
      }

      const dateStr = params?.forecast_date || new Date().toISOString().split("T")[0];
      const regionStr = (params?.placename || "East_Africa_Region").replace(/\s+/g, "_");
      const reportKey = activeReport?.report_key ? `_${activeReport.report_key}` : "";
      pdf.save(`FloodAnalysis_${regionStr}_${dateStr}${reportKey}.pdf`);

      if (activeReport?.id) {
        showSnackbar(
          `Interactive ${activeReport.status === "published" ? "published" : "draft"} PDF downloaded.`,
          "success"
        );
      } else {
        showSnackbar("PDF downloaded successfully!", "success");
      }
    } catch (error) {
      console.error("PDF generation error:", error);
      showSnackbar(error.message || "Failed to generate PDF. Please try again.", "error");
    } finally {
      setPdfLoading(false);
    }
  }, [params, activeReport]);

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
          <>{activeReport?.id ? "Export Interactive PDF" : "Export PDF"}</>
        )}
      </button>

      {/* Share Button */}
      <button className="action-btn share-btn" onClick={handleShare}>
        Share
      </button>

      {/* Print Button */}
      <button className="action-btn print-btn" onClick={handlePrint}>
        Print
      </button>

      {/* Subscribe Button */}
      <button className="action-btn subscribe-btn" onClick={handleSubscribe}>
        Subscribe
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
                &times;
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
                  Copy
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
                &times;
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
