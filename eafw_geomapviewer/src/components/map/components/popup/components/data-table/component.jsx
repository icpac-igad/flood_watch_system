import React, { useMemo } from "react";
import PropTypes from "prop-types";
import { formatNumber } from "@/utils/format";

import Button from "@/components/ui/button";
import MultiModelChart from "../multimodel-chart";

import "./styles.scss";

const getMultimodalSelectedDate = (activeDatasets) => {
  if (!Array.isArray(activeDatasets)) {
    return null;
  }

  for (const datasetConfig of activeDatasets) {
    const datasetId = datasetConfig?.dataset?.toLowerCase?.() || "";
    const layerIds = datasetConfig?.layers || [];
    const isMultimodal =
      datasetId.includes("multimodal") ||
      datasetId.includes("multi-model") ||
      layerIds.some((layerId) => {
        const lower = layerId?.toLowerCase?.() || "";
        return lower.includes("multimodal") || lower.includes("multi-model");
      });

    if (isMultimodal && datasetConfig?.params?.time) {
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
  activeDatasets,
  data,
  selected,
  zoomToShape,
  onAnalyze,
  onClose,
  isPoint,
  setMapSettings,
  setAnalysisSettings,
  setMainMapSettings,
}) => {
  const selectedDate = useMemo(
    () => getMultimodalSelectedDate(activeDatasets),
    [activeDatasets]
  );

  const { hasMultiModelData, multiModelData } = useMemo(() => {
    if (!Array.isArray(data)) {
      return {
        hasMultiModelData: false,
        multiModelData: {},
      };
    }

    const findField = (columns) =>
      data.find((entry) => columns.includes(entry?.column));

    const pointIdField = findField(["point_id"]);
    const adminNameField = findField(["admin_name"]);
    const geosfmField = findField(["geosfm"]);
    const floodproofField = findField(["floodproof"]);
    const mikeRfeField = findField(["mike_hydro_rfe"]);
    const mikeChirpField = findField(["mike_hydro_chirp"]);
    const mikeImergField = findField(["mike_hydro_imerg"]);
    const warningField = findField(["threshold_alert", "warning_threshold"]);
    const alarmField = findField(["threshold_alarm", "alarm_threshold"]);
    const emergencyField = findField([
      "threshold_emergency",
      "emergency_threshold",
    ]);

    const layerName = selected?.layer?.name || selected?.layer?.label || "";
    const isMultiModelLayer = layerName.toLowerCase().includes("multi");
    const hasForecastColumns = !!(
      geosfmField ||
      floodproofField ||
      mikeRfeField ||
      mikeChirpField ||
      mikeImergField
    );

    return {
      hasMultiModelData: !!(pointIdField?.value && (isMultiModelLayer || hasForecastColumns)),
      multiModelData: {
        pointId: pointIdField?.value,
        adminName: adminNameField?.value,
        layerName,
        thresholds: {
          warning: warningField?.value,
          alarm: alarmField?.value,
          emergency: emergencyField?.value,
        },
      },
    };
  }, [data, selected]);

  if (hasMultiModelData) {
    return (
      <div className="c-data-table">
        <MultiModelChart
          pointId={multiModelData.pointId}
          adminName={multiModelData.adminName}
          layerName={multiModelData.layerName}
          selectedDate={selectedDate}
          thresholds={multiModelData.thresholds}
        />
      </div>
    );
  }

  return (
    <div className="c-data-table">
      <div className="table">
        {data?.map((d) => (
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
      {!isPoint && !zoomToShape && <Button onClick={onAnalyze}>analyze</Button>}
    </div>
  );
};

DataTable.propTypes = {
  activeDatasets: PropTypes.array,
  data: PropTypes.array,
  selected: PropTypes.object,
  zoomToShape: PropTypes.bool,
  isPoint: PropTypes.bool,
  onClose: PropTypes.func,
  onAnalyze: PropTypes.func,
  setMapSettings: PropTypes.func,
  setAnalysisSettings: PropTypes.func,
  setMainMapSettings: PropTypes.func,
};

export default DataTable;
