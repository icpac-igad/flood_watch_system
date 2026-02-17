/**
 * Flood Widgets Container Component
 * Comprehensive flood analysis with regional maps, timeseries,
 * model comparison, and expert assessments
 */
import React, { useState } from "react";
import { isEmpty } from "lodash";

import Loader from "@/components/ui/loader";
import AlertSummaryWidget from "./alert-summary-widget.jsx";
import RegionalMapsWidget from "./regional-maps";
import TimeseriesChartWidget from "./timeseries-chart";
import ExpertAssessmentWidget from "./expert-assessment";

import "./widgets.scss";

const FloodWidgets = ({ params, settings, forecastData, loading, updateParams }) => {
  const [selectedCountry, setSelectedCountry] = useState(null);

  // Loading state
  if (loading && isEmpty(forecastData)) {
    return (
      <div className="c-flood-widgets">
        <div className="widget-loader">
          <Loader />
        </div>
      </div>
    );
  }

  // No data state
  if (isEmpty(forecastData)) {
    return (
      <div className="c-flood-widgets">
        <div className="empty-state">
          <p>
            Select parameters above and click &quot;Generate Analysis&quot; to view flood
            forecast data.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="c-flood-widgets">
      <div className="widgets-container">
        {/* Alert Summary Widget */}
        <AlertSummaryWidget
          params={params}
          alertData={forecastData?.alert_summary}
          loading={loading}
        />

        {/* Regional Maps - One per GHA country */}
        <RegionalMapsWidget
          params={params}
          forecastDate={params?.forecast_date}
          alertFilter={params?.alert_filter}
          onCountrySelect={(country) => {
            setSelectedCountry(country);
            if (updateParams && country?.code) {
              updateParams({
                admin0_code: country.code,
                placename: country.name || country.code,
              });
            }
          }}
          updateParams={updateParams}
          scope={params?.scope}
        />

        {/* Timeseries Chart with Model Comparison */}
        <TimeseriesChartWidget
          params={params}
          selectedCountry={selectedCountry?.code}
          forecastDate={params?.forecast_date}
        />

        {/* Expert Assessment - Hydrologists & Meteorologists with comments */}
        <ExpertAssessmentWidget
          params={params}
          forecastDate={params?.forecast_date}
          selectedCountry={selectedCountry?.code || params?.admin0_code}
          forecastData={forecastData}
        />
      </div>
    </div>
  );
};

export default FloodWidgets;
