/**
 * Dataset registry — maps FloodWatch STAC collections to VEDA layer format.
 *
 * Each entry must have:
 *   id        – matches the STAC collection id
 *   name      – human-readable title
 *   layers[]  – one or more visualisable layers with rendering params
 *
 * The layers are consumed by VEDA UI's ScrollytellingBlock via the
 * `datasets` prop (transformed through transformToVedaData).
 */

const datasets = [
  {
    id: 'flood-extent-return-periods',
    name: 'Flood Extent — Return Periods',
    description:
      'Flood extent maps derived from JRC Global Surface Water for 20, 50, 100, and 200-year return periods across the Greater Horn of Africa.',
    taxonomy: [
      { name: 'Topics', values: [{ id: 'hazard', name: 'Hazard' }] },
    ],
    layers: [
      {
        id: 'flood-extent-rp',
        stacCol: 'flood-extent-return-periods',
        name: 'Flood Extent (Return Periods)',
        type: 'raster',
        description:
          'Flood inundation extent for various return periods (20–200 yr).',
        sourceParams: {
          colormap_name: 'blues',
          rescale: '0,4',
        },
        legend: {
          type: 'categorical',
          stops: [
            { color: '#deebf7', label: 'RP 20yr' },
            { color: '#9ecae1', label: 'RP 50yr' },
            { color: '#4292c6', label: 'RP 100yr' },
            { color: '#08519c', label: 'RP 200yr' },
          ],
        },
        parentDataset: { id: 'flood-extent-return-periods' },
      },
    ],
  },
  {
    id: 'wrf-daily-rainfall',
    name: 'WRF Daily Rainfall',
    description:
      'WRF model daily accumulated rainfall forecasts for the Greater Horn of Africa region.',
    taxonomy: [
      { name: 'Topics', values: [{ id: 'weather', name: 'Weather' }] },
    ],
    layers: [
      {
        id: 'wrf-daily-rain',
        stacCol: 'wrf-daily-rainfall',
        name: 'WRF Daily Rainfall',
        type: 'raster',
        description: 'Daily accumulated rainfall from WRF forecast model.',
        sourceParams: {
          colormap_name: 'ylgnbu',
          rescale: '0,100',
        },
        legend: {
          type: 'gradient',
          min: '0 mm',
          max: '100 mm',
          stops: ['#ffffcc', '#a1dab4', '#41b6c4', '#2c7fb8', '#253494'],
        },
        parentDataset: { id: 'wrf-daily-rainfall' },
      },
    ],
  },
  {
    id: 'landscan-population',
    name: 'LandScan Population',
    description:
      'LandScan ambient population distribution at ~1km resolution.',
    taxonomy: [
      { name: 'Topics', values: [{ id: 'exposure', name: 'Exposure' }] },
    ],
    layers: [
      {
        id: 'landscan-pop',
        stacCol: 'landscan-population',
        name: 'Population Density',
        type: 'raster',
        description:
          'Ambient population count per grid cell from LandScan.',
        sourceParams: {
          colormap_name: 'ylorrd',
          rescale: '0,1000',
        },
        legend: {
          type: 'gradient',
          min: '0',
          max: '1000+',
          stops: ['#ffffb2', '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026'],
        },
        parentDataset: { id: 'landscan-population' },
      },
    ],
  },
];

/**
 * Transform the dataset list into the VEDA VedaData<DatasetData> shape
 * expected by ScrollytellingBlock's `datasets` prop.
 */
export function transformToVedaData(datasetList) {
  const transformed = {};
  for (const ds of datasetList) {
    transformed[ds.id] = { data: ds };
  }
  return transformed;
}

/**
 * Get dataset metadata array (used by DataProvider initialDatasets).
 */
export function getDatasetsMetadata() {
  return datasets.map((ds) => ({ metadata: ds, slug: ds.id }));
}

export default datasets;
