// Utility functions for boundary data management with Redux
import { adminBoundaryRequest } from "@/utils/request";

export const generateBoundaryKey = (adminLevel, unitId) => {
  return `${adminLevel ?? 'all'}_${unitId || 'none'}`;
};

export const fetchAdminBoundaries = async (
  adminLevel = null,
  unitId = '',
  withBbox = true,
  { boundaryData, setBoundaryData } = {}
) => {
  
  if (boundaryData && setBoundaryData) {
    const key = generateBoundaryKey(adminLevel, unitId);
    if (boundaryData[key]) {
      return boundaryData[key];
    }
  }

  try {
    const params = {};
    if (adminLevel !== null) params.admin_level = adminLevel;
    if (unitId) params.unit_id = unitId;
    if (withBbox) params.with_bbox = 'true';

    const response = await adminBoundaryRequest.get('', { params });
    const data = response.data;

    if (setBoundaryData && boundaryData) {
      const key = generateBoundaryKey(adminLevel, unitId);
      setBoundaryData({ key, data });
    }

    return data;
  } catch (error) {
    console.error('Error fetching admin boundaries:', error);
    return [];
  }
};
