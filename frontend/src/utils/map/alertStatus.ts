import { AlertStatus, Station, StationProperties } from '../../types/map.types';

/**
 * Determines the alert status of a station based on thresholds and current discharge
 */
export const getAlertStatus = (
  station: Station | StationProperties | null,
  currentDischarge: number | null = null
): AlertStatus => {
  if (!station) return 'Normal';
  
  const props: StationProperties = 'properties' in station ? station.properties : station;
  
  const q_thr1 = parseFloat(String(props.Q_THR1 || props.q_thr1 || 0));
  const q_thr2 = parseFloat(String(props.Q_THR2 || props.q_thr2 || 0));
  const q_thr3 = parseFloat(String(props.Q_THR3 || props.q_thr3 || 0));
  
  if (currentDischarge !== null && currentDischarge !== undefined && !isNaN(currentDischarge)) {
    if (!isNaN(q_thr3) && q_thr3 > 0 && currentDischarge >= q_thr3) return 'Emergency';
    if (!isNaN(q_thr2) && q_thr2 > 0 && currentDischarge >= q_thr2) return 'Alarm';
    if (!isNaN(q_thr1) && q_thr1 > 0 && currentDischarge >= q_thr1) return 'Warning';
    return 'Normal';
  }
  
  return (props.status || props.Status || 'Normal') as AlertStatus;
};
