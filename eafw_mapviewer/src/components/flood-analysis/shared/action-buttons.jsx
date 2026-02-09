/**
 * Action Buttons Component
 * Server-side PDF export via WeasyPrint, share, print, subscribe
 */
import React, { useState, useCallback } from "react";
import { isEmpty } from "lodash";

import { REPORTS_API } from "@/utils/constants";
import Button from "@/components/ui/button";

import "./action-buttons.scss";

/**
 * Capture a MapLibre GL canvas as a base64 PNG string (without the data URI prefix).
 */
const captureMapCanvas = () => {
  const canvas = document.querySelector(".maplibregl-canvas");
  if (!canvas) return null;

  try {
    const dataUrl = canvas.toDataURL("image/png");
    // Strip the "data:image/png;base64," prefix
    return dataUrl.replace(/^data:image\/png;base64,/, "");
  } catch (e) {
    console.warn("Could not capture map canvas:", e);
    return null;
  }
};

/**
 * Capture a Recharts SVG chart as base64 PNG.
 */
const captureChartSvg = () => {
  const svgEl = document.querySelector(".c-timeseries-chart .recharts-wrapper svg");
  if (!svgEl) return null;

  try {
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(svgEl);
    const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(svgBlob);

    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = img.width * 2;
        canvas.height = img.height * 2;
        const ctx = canvas.getContext("2d");
        ctx.scale(2, 2);
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        const dataUrl = canvas.toDataURL("image/png");
        resolve(dataUrl.replace(/^data:image\/png;base64,/, ""));
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(null);
      };
      img.src = url;
    });
  } catch (e) {
    console.warn("Could not capture chart:", e);
    return null;
  }
};

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

  // Generate PDF via server-side WeasyPrint
  const handleGeneratePdf = useCallback(async () => {
    setPdfLoading(true);
    showSnackbar("Generating PDF report...", "info");

    try {
      // Capture map and chart images from the DOM
      const mapImage = captureMapCanvas();
      const chartImage = await captureChartSvg();

      // Build request payload
      const payload = {
        forecast_date: params?.forecast_date || new Date().toISOString().split("T")[0],
        placename: params?.placename || "East Africa Region",
        unit_id: params?.unit_id || null,
        admin_level: params?.admin_level || null,
        map_image: mapImage,
        chart_image: chartImage,
      };

      // POST to server-side PDF endpoint
      const response = await fetch(`${REPORTS_API}/flood-analysis/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned ${response.status}`);
      }

      // Download the PDF blob
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const dateStr = params?.forecast_date || new Date().toISOString().split("T")[0];
      const regionStr = (params?.placename || "East_Africa").replace(/\s+/g, "_");
      a.href = url;
      a.download = `FloodAnalysis_${regionStr}_${dateStr}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      showSnackbar("PDF downloaded successfully!", "success");
    } catch (error) {
      console.error("PDF generation error:", error);
      showSnackbar(error.message || "Failed to generate PDF. Please try again.", "error");
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
          <>Export PDF</>
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
