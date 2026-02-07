/**
 * Action Buttons Component
 * Professional PDF export using jsPDF and html2canvas
 */
import React, { useState, useCallback } from "react";
import { isEmpty } from "lodash";
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";

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

  // Convert WebGL map canvases to static images for PDF capture
  const convertMapsToImages = async () => {
    const mapContainers = document.querySelectorAll(".maplibregl-canvas");
    const replacements = [];

    for (const canvas of mapContainers) {
      try {
        // Get the WebGL canvas data
        const dataUrl = canvas.toDataURL("image/png");

        // Create a static image
        const img = document.createElement("img");
        img.src = dataUrl;
        img.style.width = canvas.style.width || `${canvas.width}px`;
        img.style.height = canvas.style.height || `${canvas.height}px`;
        img.style.position = "absolute";
        img.style.top = "0";
        img.style.left = "0";
        img.className = "map-snapshot";

        // Store original canvas and insert image
        const parent = canvas.parentNode;
        replacements.push({ canvas, parent, img });

        // Hide the WebGL canvas and add the static image
        canvas.style.visibility = "hidden";
        parent.appendChild(img);
      } catch (e) {
        console.warn("Could not convert map canvas:", e);
      }
    }

    return replacements;
  };

  // Restore original map canvases
  const restoreMaps = (replacements) => {
    for (const { canvas, parent, img } of replacements) {
      canvas.style.visibility = "visible";
      if (img.parentNode) {
        img.parentNode.removeChild(img);
      }
    }
  };

  // Generate professional PDF report using jsPDF and html2canvas
  const handleGeneratePdf = useCallback(async () => {
    setPdfLoading(true);
    showSnackbar("Generating PDF report...", "info");

    let mapReplacements = [];

    try {
      // Get the report content
      const reportContent = document.querySelector(".c-flood-analysis");
      if (!reportContent) {
        showSnackbar("Report content not found", "error");
        return;
      }

      // Hide elements we don't want in PDF
      const elementsToHide = document.querySelectorAll(
        ".c-action-buttons, .c-global-options, .generate-btn"
      );
      elementsToHide.forEach((el) => el.style.display = "none");

      // Convert WebGL maps to static images for capture
      mapReplacements = await convertMapsToImages();

      // Small delay to ensure images are rendered
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Create canvas from the report content
      const canvas = await html2canvas(reportContent, {
        scale: 2, // Higher resolution
        useCORS: true,
        allowTaint: true,
        backgroundColor: "#ffffff",
        logging: false,
        windowWidth: 1200,
      });

      // Restore hidden elements and maps
      elementsToHide.forEach((el) => el.style.display = "");
      restoreMaps(mapReplacements);

      // Calculate PDF dimensions (A4 size)
      const imgWidth = 210; // A4 width in mm
      const pageHeight = 297; // A4 height in mm
      const imgHeight = (canvas.height * imgWidth) / canvas.width;

      // Create PDF
      const pdf = new jsPDF({
        orientation: imgHeight > pageHeight ? "portrait" : "portrait",
        unit: "mm",
        format: "a4",
      });

      // Add metadata
      pdf.setProperties({
        title: `Flood Analysis Report - ${params?.placename || "East Africa Region"}`,
        subject: "Flood Forecast Analysis",
        author: "IGAD ICPAC - East Africa Flood Watch",
        creator: "East Africa Flood Watch System",
      });

      const imgData = canvas.toDataURL("image/png");

      // Handle multi-page PDF if content is too long
      let heightLeft = imgHeight;
      let position = 0;
      const margin = 5; // 5mm margin

      // First page
      pdf.addImage(imgData, "PNG", margin, position, imgWidth - (2 * margin), imgHeight);
      heightLeft -= pageHeight;

      // Add more pages if needed
      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, "PNG", margin, position, imgWidth - (2 * margin), imgHeight);
        heightLeft -= pageHeight;
      }

      // Add footer to each page
      const pageCount = pdf.internal.getNumberOfPages();
      const currentDate = new Date().toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });

      for (let i = 1; i <= pageCount; i++) {
        pdf.setPage(i);
        pdf.setFontSize(8);
        pdf.setTextColor(128, 128, 128);

        // Footer text
        pdf.text(
          `East Africa Flood Watch - Generated ${currentDate}`,
          margin,
          pageHeight - 5
        );
        pdf.text(
          `Page ${i} of ${pageCount}`,
          imgWidth - margin - 20,
          pageHeight - 5
        );
        pdf.text(
          "https://floodwatch.icpac.net",
          imgWidth / 2 - 20,
          pageHeight - 5
        );
      }

      // Generate filename
      const dateStr = params?.forecast_date || new Date().toISOString().split("T")[0];
      const regionStr = (params?.placename || "East_Africa").replace(/\s+/g, "_");
      const filename = `FloodAnalysis_${regionStr}_${dateStr}.pdf`;

      // Save the PDF
      pdf.save(filename);

      showSnackbar(`PDF saved as ${filename}`, "success");
    } catch (error) {
      console.error("PDF generation error:", error);
      showSnackbar("Failed to generate PDF. Please try again.", "error");
      // Restore maps on error
      restoreMaps(mapReplacements);
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
