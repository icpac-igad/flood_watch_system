/**
 * Flood Analysis Report Page
 * Uses real API data only - no fallback/demo data
 */
import React, { useEffect, useState, useCallback } from "react";
import { isEmpty } from "lodash";
import queryString from "query-string";

import FullscreenLayout from "@/wrappers/fullscreen";
import Loader from "@/components/ui/loader";
import { CMS_API } from "@/utils/constants";

import GlobalOptions from "@/components/flood-analysis/params/global-options";
import FloodWidgets from "@/components/flood-analysis/widgets";
import ActionButtons from "@/components/flood-analysis/shared/action-buttons";

import { encodeJsonToBase64, decodeBase64ToJson } from "@/utils/url-encoding";

import "./flood-analysis.scss";

// Default parameters
const DEFAULT_PARAMS = {
  reporting_unit: "East Africa Region",
  forecast_date: null, // Will be set from available dates in DB
  alert_filter: "all", // Filter points by alert level
  admin_level: null,
  unit_id: null,
  placename: "East Africa Region",
};

// Default settings
const DEFAULT_SETTINGS = {
  reporting_units: [
    "East Africa Region",
    "Administrative Boundary",
    "River Basin",
  ],
  pdf: { loading: false, url: null },
};

const FloodAnalysisPage = () => {
  const [params, setParams] = useState({});
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [forecastData, setForecastData] = useState(null);

  // Decode URL params on mount
  useEffect(() => {
    if (isEmpty(params)) {
      const pathParams = queryString.parse(window.location.search);

      if (!isEmpty(pathParams?.qstr)) {
        try {
          const decoded = decodeBase64ToJson(pathParams.qstr);
          setParams(decoded.params || DEFAULT_PARAMS);
          setSettings((prev) => ({ ...prev, ...decoded.settings }));
        } catch (e) {
          console.error("Failed to decode URL params:", e);
          setParams(DEFAULT_PARAMS);
        }
      } else {
        setParams(DEFAULT_PARAMS);
      }
      setLoading(false);
    }
  }, [params]);

  // Encode params to URL when they change
  useEffect(() => {
    if (!isEmpty(params) && !isEmpty(settings)) {
      const encoded = encodeJsonToBase64({ params, settings });
      window.history.replaceState("", "", `?qstr=${encoded}`);
    }
  }, [params, settings]);

  // Fetch forecast data when params change - NO FALLBACK DATA
  const fetchForecastData = useCallback(async () => {
    if (isEmpty(params?.forecast_date)) return;

    setLoading(true);
    setError(null);

    try {
      const queryParams = new URLSearchParams({
        date: params.forecast_date,
        forecast_date: params.forecast_date, // backward compatibility with endpoints expecting forecast_date
        ...(params.unit_id && { unit_id: params.unit_id }),
        ...(params.admin_level && { admin_level: params.admin_level }),
      });

      // Fetch from situation-summary API for alert data
      const summaryResponse = await fetch(`${CMS_API}/situation-summary/?${queryParams}`);

      if (!summaryResponse.ok) {
        throw new Error(`API returned ${summaryResponse.status}: Failed to fetch forecast data`);
      }

      const summaryData = await summaryResponse.json();

      // Transform API response to expected format
      const forecastData = {
        alert_summary: {
          overall_level: getOverallLevel(summaryData.risk_counts),
          total_points: summaryData.risk_counts?.total || 0,
          last_updated: new Date().toISOString(),
          by_level: {
            emergency: summaryData.risk_counts?.emergency || 0,
            alarm: summaryData.risk_counts?.alarm || 0,
            warning: summaryData.risk_counts?.warning || 0,
            normal: summaryData.risk_counts?.normal || 0,
          },
        },
        data_date: summaryData.data_date,
        country_breakdown: summaryData.country_breakdown,
      };

      setForecastData(forecastData);
    } catch (err) {
      console.error("Error fetching forecast data:", err);
      setError(err.message || "Failed to fetch forecast data from API");
      setForecastData(null);
    } finally {
      setLoading(false);
    }
  }, [params]);

  // Helper to determine overall level
  const getOverallLevel = (counts) => {
    if (!counts) return "normal";
    if (counts.emergency > 0) return "emergency";
    if (counts.alarm > 0) return "alarm";
    if (counts.warning > 0) return "warning";
    return "normal";
  };

  useEffect(() => {
    if (!isEmpty(params)) {
      fetchForecastData();
    }
  }, [params.forecast_date, params.unit_id, fetchForecastData]);

  // Update params
  const updateParams = useCallback((newParams) => {
    setParams((prev) => ({ ...prev, ...newParams }));
  }, []);

  // Update settings
  const updateSettings = useCallback((newSettings) => {
    setSettings((prev) => ({ ...prev, ...newSettings }));
  }, []);

  // Generate analysis (refresh data)
  const handleGenerateAnalysis = useCallback(() => {
    fetchForecastData();
  }, [fetchForecastData]);

  // Render loading state
  if (loading && isEmpty(params)) {
    return (
      <FullscreenLayout
        title="Flood Analysis Report"
        description="Multi-model flood forecast analysis"
      >
        <div className="c-flood-analysis">
          <div className="loading-container">
            <Loader />
          </div>
        </div>
      </FullscreenLayout>
    );
  }

  return (
    <FullscreenLayout
      title="Flood Analysis Report"
      description="Multi-model flood forecast analysis"
    >
      <div className="c-flood-analysis">
        {/* ICPAC Header - matching drought report */}
        <header className="icpac-header">
          <div className="logo-container">
            <img
              src="/favicon/logo.png"
              alt="IGAD ICPAC"
              className="icpac-logo"
              onError={(e) => { e.target.style.display = 'none'; }}
            />
            <div className="logo-text">
              <span className="igad-text">IGAD</span>
              <span className="icpac-text">ICPAC</span>
              <span className="icpac-subtitle">IGAD Climate Prediction<br/>and Applications Centre</span>
            </div>
          </div>
        </header>

        {/* Alert Level Color Bar */}
        <div className="alert-color-bar">
          <div className="color-segment normal"></div>
          <div className="color-segment watch"></div>
          <div className="color-segment warning"></div>
          <div className="color-segment alarm"></div>
          <div className="color-segment emergency"></div>
        </div>

        <div className="c-flood-analysis-body">
          {/* Report Title */}
          <div className="report-title-section">
            <h1 className="report-main-title">
              Flood Analysis Report for {params.placename}
            </h1>
            <p className="report-reference-date">
              Reference Date: {params.forecast_date}
            </p>
          </div>

          {/* Global Options - Time and Area Selection */}
          <GlobalOptions
            params={params}
            settings={settings}
            loading={loading}
            updateParams={updateParams}
            updateSettings={updateSettings}
            onGenerateAnalysis={handleGenerateAnalysis}
          />

          {/* Error Display */}
          {error && (
            <div className="error-container">
              <div className="error-message">
                <strong>⚠️ API Error:</strong> {error}
              </div>
            </div>
          )}

          {/* Flood Model Widgets - only show if we have data */}
          <FloodWidgets
            params={params}
            settings={settings}
            forecastData={forecastData}
            loading={loading}
            error={error}
          />

          {/* Action Buttons */}
          <ActionButtons
            params={params}
            settings={settings}
            forecastData={forecastData}
            updateSettings={updateSettings}
          />

          {/* Report Footer */}
          <footer className="report-footer">
            <div className="footer-left">East Africa Flood Watch</div>
            <div className="footer-center">Page 1 of 1</div>
            <div className="footer-right">https://floodwatch.icpac.net</div>
          </footer>
        </div>
      </div>
    </FullscreenLayout>
  );
};

export default FloodAnalysisPage;
