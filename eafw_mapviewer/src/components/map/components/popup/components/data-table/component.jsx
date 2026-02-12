import React, { useMemo } from "react";
import PropTypes from "prop-types";
import { connect } from "react-redux";
import { formatNumber } from "@/utils/format";

import Button from "@/components/ui/button";
import DischargeChart from "../discharge-chart";
import MultiModelChart from "../multimodel-chart";
import { getMultimodalClusterConfig } from "@/providers/config-provider/selectors";
import { getActiveDatasetsFromState } from "@/components/map/selectors";

import "./styles.scss";

/**
 * Get selected date from multimodal layer params
 * activeDatasets structure: [{ dataset: "id", layers: [...], params: { time: "YYYY-MM-DD" } }]
 */
const getMultimodalSelectedDate = (activeDatasets) => {
  if (!activeDatasets || !Array.isArray(activeDatasets)) return null;

  // Find multimodal dataset by checking dataset id or layers
  for (const datasetConfig of activeDatasets) {
    const isMultimodal =
      datasetConfig.dataset?.toLowerCase().includes('multimodal') ||
      datasetConfig.dataset?.toLowerCase().includes('multi-model') ||
      datasetConfig.layers?.some(l =>
        l?.toLowerCase().includes('multimodal') ||
        l?.toLowerCase().includes('multi-model')
      );

    if (isMultimodal && datasetConfig.params?.time) {
      return datasetConfig.params.time;
    }
  }

  // Fallback: use any dataset with time param
  for (const datasetConfig of activeDatasets) {
    if (datasetConfig.params?.time) {
      return datasetConfig.params.time;
    }
  }

  return null;
};

const renderString = ({ suffix, type, linkText, value }) => {
  let valueString = value !== null && value !== "" ? value : "n/a";

  if (type === "number" && value !== null && value !== "") {
    valueString = formatNumber({ num: value, unit: suffix });
  } else if (type === "link" && value && linkText) {
    valueString = (
      <a
        className="table-link"
        href={value}
        alt="Read More"
        target="_blank"
        rel="noopener noreferrer"
      >
        {linkText}
      </a>
    );
  }
  return valueString;
};

const DataTable = ({
  data,
  selected,
  zoomToShape,
  onAnalyze,
  onClose,
  isPoint,
  setMapSettings,
  setAnalysisSettings,
  setMainMapSettings,
  clusterConfig,
  activeDatasets,
  popupLat,
  popupLon,
  onPopupDragStart,
}) => {
  // Get hybas_id from raw selected data (works for both GeoJSON and MVT layers)
  const rawHybasId = selected?.data?.hybas_id;
  // Get selected date for multimodal layer (updates when date selector changes)
  const selectedDate = useMemo(
    () => getMultimodalSelectedDate(activeDatasets),
    [activeDatasets]
  );
  // Check if this is forecast data (multimodal or floodproofs)
  const {
    hasTimeSeriesData,
    hasMultiModelData,
    regularData,
    chartData,
    multiModelData,
  } = useMemo(() => {
    if (!data || !Array.isArray(data)) {
      return {
        hasTimeSeriesData: false,
        hasMultiModelData: false,
        regularData: data || [],
        chartData: {},
        multiModelData: {},
      };
    }

    try {
      // Check for multimodal forecasts field (can be 'forecasts' or 'forecasts_json')
      const forecastsJsonField = data.find(
        (d) => d && (d.column === "forecasts_json" || d.column === "forecasts")
      );
      const adminNameField = data.find(
        (d) => d && d.column === "admin_name"
      );
      const pointIdField = data.find(
        (d) => d && d.column === "point_id"
      );
      const dataEndpointField = data.find(
        (d) => d && d.column === "data_endpoint"
      );
      const hybasIdField = data.find(
        (d) => d && d.column === "hybas_id"
      );
      // Get coordinates from feature_lon/feature_lat (injected from geometry) or x/y/lon/lat
      const lonField = data.find(
        (d) => d && (d.column === "feature_lon" || d.column === "x" || d.column === "lon" || d.column === "longitude")
      );
      const latField = data.find(
        (d) => d && (d.column === "feature_lat" || d.column === "y" || d.column === "lat" || d.column === "latitude")
      );

      // Detect multi-model data: either has forecasts_json value OR has point_id (can fetch from API)
      const hasMultiModel = !!(
        (forecastsJsonField && forecastsJsonField.value) ||
        (pointIdField && pointIdField.value && adminNameField)
      );

      // Check for Floodproofs discharge time series
      const gfsField = data.find((d) =>
        d && d.column && (
          d.column.includes("time_series_discharge_simulated_gfs") ||
          d.column.includes("time_series_discharge_simulated-gfs")
        )
      );
      const iconField = data.find((d) =>
        d && d.column && (
          d.column.includes("time_series_discharge_simulated_icon") ||
          d.column.includes("time_series_discharge_simulated-icon")
        )
      );
      const stationField = data.find((d) => d && d.column === "sec_name");
      const warningField = data.find((d) => d && d.column === "q_thr1");
      const alarmField = data.find((d) => d && d.column === "q_thr2");
      const emergencyField = data.find((d) => d && d.column === "q_thr3");

      // Also check for floodproofs simplified format (from discharge_points)
      const stationNameField = data.find((d) => d && d.column === "station_name");
      const alertLevelField = data.find((d) => d && d.column === "alert_level");
      const multimodelAlertLevelField = data.find((d) => d && d.column === "alert_level" && adminNameField);
      const thresholdAlertField = data.find((d) => d && d.column === "threshold_alert");
      const thresholdAlarmField = data.find((d) => d && d.column === "threshold_alarm");
      const thresholdEmergencyField = data.find((d) => d && d.column === "threshold_emergency");

      const toThreshold = (value) => {
        const parsed = parseFloat(value);
        return Number.isFinite(parsed) ? parsed : null;
      };

      const modelThresholds = {
        warning: toThreshold(warningField?.value) ?? toThreshold(thresholdAlertField?.value),
        alarm: toThreshold(alarmField?.value) ?? toThreshold(thresholdAlarmField?.value),
        emergency: toThreshold(emergencyField?.value) ?? toThreshold(thresholdEmergencyField?.value),
      };
      const hasModelThresholds = Object.values(modelThresholds).some(
        (value) => value !== null && value > 0
      );

      const hasTimeSeries = !!(gfsField || iconField);

      // Separate chart fields from regular display fields
      const chartFieldColumns = [
        "time_series_discharge_simulated_gfs",
        "time_series_discharge_simulated-gfs",
        "time_series_discharge_simulated_icon",
        "time_series_discharge_simulated-icon",
        "forecasts_json",
        "forecasts",
      ];

      // Filter out chart data columns and hidden fields from display
      const regularFields = data.filter(
        (d) =>
          d &&
          d.column &&
          !d.hidden &&
          !chartFieldColumns.some((col) => d.column.includes(col))
      );

      return {
        hasTimeSeriesData: hasTimeSeries,
        hasMultiModelData: hasMultiModel,
        regularData: regularFields,
        chartData: {
          gfsData: gfsField?.value,
          iconData: iconField?.value,
          stationName: stationField?.value || stationNameField?.value,
          warningThreshold:
            parseFloat(warningField?.value) ||
            parseFloat(thresholdAlertField?.value) ||
            0,
          alarmThreshold:
            parseFloat(alarmField?.value) ||
            parseFloat(thresholdAlarmField?.value) ||
            0,
          emergencyThreshold:
            parseFloat(emergencyField?.value) ||
            parseFloat(thresholdEmergencyField?.value) ||
            0,
        },
        multiModelData: {
          forecastsJson: forecastsJsonField?.value,
          layerName: selected?.layer?.name || selected?.layer?.label,
          adminName: adminNameField?.value,
          pointId: pointIdField?.value,
          dataEndpoint: dataEndpointField?.value,
          hybasId: hybasIdField?.value || rawHybasId,  // Fallback to raw selected data
          lon: lonField?.value,
          lat: latField?.value,
          alertLevel: alertLevelField?.value,
          thresholds: hasModelThresholds ? modelThresholds : null,
          // Note: popupLon/popupLat will be used as fallback in component
        },
      };
    } catch (error) {
      console.error("Error processing forecast chart data:", error);
      return {
        hasTimeSeriesData: false,
        hasMultiModelData: false,
        regularData: data,
        chartData: {},
        multiModelData: {},
      };
    }
  }, [data, rawHybasId, selected?.layer?.name, selected?.layer?.label]);

  // Determine if we should show chart or table
  const showChart = hasTimeSeriesData || hasMultiModelData;

  return (
    <div className="c-data-table">
      {/* Show MultiModel chart for multimodal forecast data */}
      {hasMultiModelData && (
        <MultiModelChart
          forecastsJson={multiModelData.forecastsJson}
          layerName={multiModelData.layerName}
          adminName={multiModelData.adminName}
          pointId={multiModelData.pointId}
          dataEndpoint={multiModelData.dataEndpoint}
          hybasId={multiModelData.hybasId}
          lon={multiModelData.lon || popupLon}
          lat={multiModelData.lat || popupLat}
          alertLevel={multiModelData.alertLevel}
          selectedDate={selectedDate}
          thresholds={multiModelData.thresholds || clusterConfig?.thresholds}
          onDragStart={onPopupDragStart}
        />
      )}

      {/* Show discharge chart if time series data is available */}
      {hasTimeSeriesData && !hasMultiModelData && (
        <DischargeChart
          gfsData={chartData.gfsData}
          iconData={chartData.iconData}
          stationName={chartData.stationName}
          warningThreshold={chartData.warningThreshold}
          alarmThreshold={chartData.alarmThreshold}
          emergencyThreshold={chartData.emergencyThreshold}
        />
      )}

      {/* Show data table for non-chart data or alongside charts */}
      {!showChart && regularData?.length > 0 && (
        <div className="table">
          {regularData?.map((d) => (
            <div key={`${d.label}-${d?.value}`} className="wrapper">
              <div className="label">{d?.label}:</div>

              <div
                className={
                  d?.type === "link" && d?.linkText ? "table-link" : "value"
                }
              >
                {renderString(d)} {d?.units}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Show summary info below chart - only for discharge charts, not multimodel */}
      {hasTimeSeriesData && !hasMultiModelData && regularData?.length > 0 && (
        <div className="chart-summary">
          {regularData
            ?.filter((d) => ["station_name", "river_name", "alert_level", "admin_name", "forecast_date"].includes(d.column))
            .map((d) => (
              <div key={`${d.label}-${d?.value}`} className="summary-item">
                <span className="summary-label">{d?.label}:</span>
                <span className="summary-value">{renderString(d)}</span>
              </div>
            ))}
        </div>
      )}

      {!isPoint && !zoomToShape && <Button onClick={onAnalyze}>analyze</Button>}
    </div>
  );
};

DataTable.propTypes = {
  data: PropTypes.array,
  selected: PropTypes.object,
  zoomToShape: PropTypes.bool,
  isPoint: PropTypes.bool,
  onClose: PropTypes.func,
  onAnalyze: PropTypes.func,
  setMapSettings: PropTypes.func,
  setAnalysisSettings: PropTypes.func,
  setMainMapSettings: PropTypes.func,
  clusterConfig: PropTypes.object,
  activeDatasets: PropTypes.array,
  popupLat: PropTypes.number,
  popupLon: PropTypes.number,
  onPopupDragStart: PropTypes.func,
};

const mapStateToProps = (state) => ({
  clusterConfig: getMultimodalClusterConfig(state),
  activeDatasets: getActiveDatasetsFromState(state),
});

export default connect(mapStateToProps)(DataTable);
