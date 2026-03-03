/**
 * Global Options Component for Flood Report
 * Based on mukau-viz-components params/global.jsx
 * Provides time and area selection for flood forecast reports
 * Uses native HTML components for compatibility
 */
import React, { useEffect, useMemo, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { isEmpty } from "lodash";

import Button from "@/components/ui/button";
import { CMS_API } from "@/utils/constants";
import { setParamInteractions } from "@/components/map/actions";
import { selectCmsScopes, selectDefaultScope } from "@/components/map/selectors";

import "./global-options.scss";

// Alert level filter options (no Normal per feedback)
const ALERT_LEVELS = [
  { value: "all", label: "All Points" },
  { value: "emergency", label: "Extreme" },
  { value: "alarm", label: "Severe" },
  { value: "warning", label: "Moderate" },
];

// Countries to exclude from dropdown (merge into parent country)
const EXCLUDED_COUNTRIES = new Set(["zanzibar"]);

// Projects are loaded from CMS via Redux (selectCmsScopes).
// Fallback if CMS scopes haven't loaded yet.
const FALLBACK_PROJECTS = [
  { code: "whca", name: "WHCA (Water at Heart of Climate Action)" },
];

const DEFAULT_COUNTRIES = [
  { code: "Burundi", name: "Burundi" },
  { code: "Djibouti", name: "Djibouti" },
  { code: "Ethiopia", name: "Ethiopia" },
  { code: "Kenya", name: "Kenya" },
  { code: "Rwanda", name: "Rwanda" },
  { code: "Somalia", name: "Somalia" },
  { code: "South Sudan", name: "South Sudan" },
  { code: "Sudan", name: "Sudan" },
  { code: "Tanzania", name: "Tanzania" },
  { code: "Uganda", name: "Uganda" },
];

const WHCA_COUNTRY_SET = new Set([
  "ethiopia",
  "rwanda",
  "south sudan",
  "sudan",
  "uganda",
]);

// Date selector component
const DateSelector = ({ value, onChange, disabled, label }) => (
  <div className="form-group">
    <label className="form-label">{label}</label>
    <input
      type="date"
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className="form-input"
    />
  </div>
);

// Select component
const SelectInput = ({ label, value, options, onChange, disabled, placeholder }) => (
  <div className="form-group">
    <label className="form-label">{label}</label>
    <select
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled || isEmpty(options)}
      className="form-select"
    >
      <option value="">{placeholder || `Select ${label}`}</option>
      {options?.map((opt) => (
        <option key={opt.value || opt.code || opt} value={opt.value || opt.code || opt}>
          {opt.label || opt.name || opt}
        </option>
      ))}
    </select>
  </div>
);

// Radio group component
const RadioGroup = ({ name, options, value, onChange, disabled }) => (
  <div className="radio-group">
    {options.map((option) => (
      <label key={option} className="radio-label">
        <input
          type="radio"
          name={name}
          value={option}
          checked={value === option}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        />
        <span className="radio-text">{option}</span>
      </label>
    ))}
  </div>
);

const GlobalOptions = ({
  params,
  settings,
  loading,
  updateParams,
  updateSettings,
  onGenerateAnalysis,
}) => {
  const dispatch = useDispatch();
  const cmsScopes = useSelector(selectCmsScopes);
  const defaultScope = useSelector(selectDefaultScope);

  // Build project options from CMS scopes, falling back to hardcoded list
  const projectOptions = useMemo(() => {
    if (cmsScopes && cmsScopes.length > 0) {
      return cmsScopes.map(s => ({ code: s.key, name: s.label }));
    }
    return FALLBACK_PROJECTS;
  }, [cmsScopes]);

  // Build dynamic country set for the active scope
  const scopeCountrySet = useMemo(() => {
    if (!cmsScopes || cmsScopes.length === 0) return WHCA_COUNTRY_SET;
    const scope = cmsScopes.find(s => s.key === (params.unit_id || '').toLowerCase());
    if (scope && scope.countries && scope.countries.length > 0) {
      return new Set(scope.countries.map(c => c.toLowerCase()));
    }
    return null; // No filtering — show all countries
  }, [cmsScopes, params.unit_id]);

  const [adminBoundaries, setAdminBoundaries] = useState({
    admin0: [],
    admin1: [],
    admin2: [],
  });
  const [riverBasins, setRiverBasins] = useState([]);
  const [availableDates, setAvailableDates] = useState([]);
  const [datesLoading, setDatesLoading] = useState(true);

  // On mount, sync with Redux default scope: auto-select Projects/WHCA if that's the default
  useEffect(() => {
    if (defaultScope && defaultScope !== 'all' && !params.reporting_unit) {
      updateParams({
        reporting_unit: 'Projects',
        unit_id: defaultScope,
        scope: defaultScope,
        placename: projectOptions.find(p => p.code === defaultScope)?.name || defaultScope,
      });
    }
  }, [defaultScope]);

  // Fetch available forecast dates from database
  useEffect(() => {
    const fetchAvailableDates = async () => {
      setDatesLoading(true);
      try {
        const response = await fetch(`/api/v1/multimodal/dates/`);
        if (response.ok) {
          const data = await response.json();
          const dates = data.timestamps || [];
          setAvailableDates(dates);
          // Auto-select latest date if none selected
          if (dates.length > 0 && !params.forecast_date) {
            updateParams({ forecast_date: dates[0] });
          }
        } else {
          console.error("Failed to fetch available dates:", response.status);
          setAvailableDates([]);
        }
      } catch (error) {
        console.error("Failed to fetch available dates:", error);
        setAvailableDates([]);
      } finally {
        setDatesLoading(false);
      }
    };

    fetchAvailableDates();
  }, []);

  // Fetch admin boundaries (countries)
  useEffect(() => {
    const fetchAdminBoundaries = async () => {
      try {
        const response = await fetch(`/api/v1/boundaries/admin-boundaries/`);
        if (!response.ok) {
          throw new Error(`Countries endpoint returned ${response.status}`);
        }

        const data = await response.json();
        const countries = (Array.isArray(data) ? data : [])
          .map((item) => {
            const name = (item?.name || item?.code || "").trim();
            return {
              code: name,
              name,
            };
          })
          .filter((item) => item.name && !EXCLUDED_COUNTRIES.has(item.name.toLowerCase()));

        setAdminBoundaries((prev) => ({
          ...prev,
          admin0: countries.length > 0 ? countries : DEFAULT_COUNTRIES,
        }));
      } catch (error) {
        console.error("Failed to fetch admin boundaries:", error);
        // Keep the country selector usable even if API request fails.
        setAdminBoundaries((prev) => ({
          ...prev,
          admin0: DEFAULT_COUNTRIES,
        }));
      }
    };

    fetchAdminBoundaries();
  }, []);

  const projectCountryOptions = useMemo(() => {
    if (!scopeCountrySet) {
      return adminBoundaries.admin0;
    }
    return (adminBoundaries.admin0 || []).filter((item) =>
      scopeCountrySet.has((item.name || "").toLowerCase())
    );
  }, [adminBoundaries.admin0, scopeCountrySet]);

  useEffect(() => {
    if (params.reporting_unit !== "Projects") return;
    if ((params.unit_id || "").toLowerCase() !== "whca") return;
    if (!params.admin0_code) return;

    const exists = projectCountryOptions.some(
      (item) => item.code === params.admin0_code || item.name === params.admin0_code
    );
    if (!exists) {
      updateParams({
        admin0_code: null,
        admin1_code: null,
      });
    }
  }, [
    params.reporting_unit,
    params.unit_id,
    params.admin0_code,
    projectCountryOptions,
    updateParams,
  ]);

  // Fetch admin1 when country is selected
  useEffect(() => {
    const fetchAdmin1 = async () => {
      if (!params.admin0_code) return;

      try {
        // API params: admin_level=0 means get children (admin1) of country
        // unit_id is the country name
        const response = await fetch(
          `/api/v1/boundaries/admin-boundaries/?admin_level=0&unit_id=${encodeURIComponent(params.admin0_code)}`
        );
        if (response.ok) {
          const data = await response.json();
          // Response is direct array
          setAdminBoundaries((prev) => ({
            ...prev,
            admin1: Array.isArray(data) ? data : [],
          }));
        }
      } catch (error) {
        console.error("Failed to fetch admin1:", error);
      }
    };

    fetchAdmin1();
  }, [params.admin0_code]);

  // Fetch river basins when needed - NO FALLBACK, use API data only
  useEffect(() => {
    const fetchRiverBasins = async () => {
      try {
        const response = await fetch(`/api/v1/risk/river-basins`);
        if (response.ok) {
          const data = await response.json();
          setRiverBasins(Array.isArray(data) ? data : []);
        } else {
          console.error("Failed to fetch river basins:", response.status);
          setRiverBasins([]);
        }
      } catch (error) {
        console.error("Failed to fetch river basins:", error);
        setRiverBasins([]);
      }
    };

    if (params.reporting_unit === "River Basin") {
      fetchRiverBasins();
    }
  }, [params.reporting_unit]);

  // Handle reporting unit change
  const handleReportingUnitChange = (unit) => {
    updateParams({
      reporting_unit: unit,
      placename: unit === "East Africa Region" ? unit : params.placename,
      admin_level: null,
      unit_id: null,
      admin0_code: null,
      admin1_code: null,
      scope: unit === "Projects" ? (params.scope || "all") : "all",
    });
  };

  // Handle country selection
  const handleCountryChange = (code) => {
    const country = adminBoundaries.admin0.find((c) => c.code === code);
    updateParams({
      admin0_code: code,
      admin_level: "0",
      unit_id: code,
      placename: country?.name || code,
      admin1_code: null,
    });
    setAdminBoundaries((prev) => ({ ...prev, admin1: [], admin2: [] }));
  };

  // Handle admin1 selection
  const handleAdmin1Change = (code) => {
    const admin1 = adminBoundaries.admin1.find((a) => a.code === code);
    updateParams({
      admin1_code: code,
      admin_level: "1",
      unit_id: code,
      placename: admin1?.name || code,
    });
  };

  // Handle river basin selection
  const handleBasinChange = (code) => {
    const basin = riverBasins.find((b) => b.code === code);
    updateParams({
      unit_id: code,
      admin_level: null,
      placename: basin?.name || code,
    });
  };

  // Handle project selection — also sync scope to Redux for mapviewer
  const handleProjectChange = (code) => {
    const project = projectOptions.find((p) => p.code === code);
    const scopeKey = code || 'all';
    updateParams({
      unit_id: code,
      admin_level: null,
      admin0_code: null,
      admin1_code: null,
      placename: project?.name || code,
      scope: scopeKey,
    });
    // Sync to Redux so mapviewer stays in sync
    dispatch(setParamInteractions({
      scope: scopeKey,
      whca_filter: scopeKey === 'whca',
    }));
  };

  const handleProjectCountryChange = (code) => {
    const country = projectCountryOptions.find((item) => item.code === code || item.name === code);
    if (!country) {
      updateParams({
        admin0_code: null,
        admin1_code: null,
      });
      return;
    }

    updateParams({
      admin0_code: country.code,
      admin1_code: null,
      admin_level: "0",
      placename: country.name,
    });
  };

  // Handle date change
  const handleDateChange = (date) => {
    updateParams({ forecast_date: date });
  };

  // Handle alert filter change
  const handleAlertFilterChange = (value) => {
    updateParams({ alert_filter: value });
  };

  const { reporting_units } = settings;

  // Format available dates for select dropdown
  const dateOptions = availableDates.map((date) => ({
    value: date,
    label: new Date(date).toLocaleDateString("en-GB", {
      weekday: "short",
      day: "numeric",
      month: "short",
      year: "numeric",
    }),
  }));

  return (
    <div className="c-global-options">
      <div className="section-title">Time and Area for Report</div>

      <div className="options-row">
        {/* Date Selection - uses available dates from database */}
        <div className="options-col">
          <div className="options-grid">
            <SelectInput
              label="Forecast Date"
              value={params.forecast_date}
              options={dateOptions}
              onChange={handleDateChange}
              disabled={loading || datesLoading}
              placeholder={datesLoading ? "Loading dates..." : "Select date"}
            />
            {availableDates.length > 0 && (
              <div className="date-info">
                <span className="date-count">{availableDates.length} dates available</span>
              </div>
            )}
            <SelectInput
              label="Alert Level Filter"
              value={params.alert_filter || "all"}
              options={ALERT_LEVELS}
              onChange={handleAlertFilterChange}
              disabled={loading}
              placeholder="Filter by alert level"
            />
          </div>
        </div>

        {/* Reporting Unit Selection */}
        <div className="options-col">
          <div className="reporting-unit-section">
            <label className="form-label">Reporting Unit</label>
            <RadioGroup
              name="reporting_unit"
              options={reporting_units}
              value={params.reporting_unit}
              onChange={handleReportingUnitChange}
              disabled={loading}
            />

            {/* Admin Boundary Selectors */}
            {params.reporting_unit === "Administrative Boundary" && (
              <div className="admin-selectors">
                <SelectInput
                  label="Country"
                  value={params.admin0_code}
                  options={adminBoundaries.admin0}
                  onChange={handleCountryChange}
                  disabled={loading}
                />
                {!isEmpty(adminBoundaries.admin1) && (
                  <SelectInput
                    label="Admin Level 1"
                    value={params.admin1_code}
                    options={adminBoundaries.admin1}
                    onChange={handleAdmin1Change}
                    disabled={loading}
                  />
                )}
              </div>
            )}

            {/* River Basin Selector */}
            {params.reporting_unit === "River Basin" && (
              <div className="admin-selectors">
                <SelectInput
                  label="River Basin"
                  value={params.unit_id}
                  options={riverBasins}
                  onChange={handleBasinChange}
                  disabled={loading}
                  placeholder={isEmpty(riverBasins) ? "Coming soon..." : "Select basin"}
                />
                {isEmpty(riverBasins) && (
                  <div className="info-note">River basin data will be available soon.</div>
                )}
              </div>
            )}

            {/* Projects Selector */}
            {params.reporting_unit === "Projects" && (
              <div className="admin-selectors">
                <SelectInput
                  label="Project"
                  value={params.unit_id}
                  options={projectOptions}
                  onChange={handleProjectChange}
                  disabled={loading}
                  placeholder="Select project"
                />
                {params.unit_id && projectCountryOptions.length > 0 && (
                  <SelectInput
                    label="Country"
                    value={params.admin0_code}
                    options={projectCountryOptions}
                    onChange={handleProjectCountryChange}
                    disabled={loading}
                    placeholder={`Select ${params.unit_id.toUpperCase()} country`}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Generate Report Button */}
      <div className="generate-btn">
        <Button
          theme="theme-button-green"
          onClick={onGenerateAnalysis}
          disabled={loading}
        >
          {loading ? "Loading..." : "Generate Report"}
        </Button>
      </div>
    </div>
  );
};

export default GlobalOptions;
