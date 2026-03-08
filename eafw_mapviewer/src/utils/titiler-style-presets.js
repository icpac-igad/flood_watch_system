import { isTitilerTileUrl } from './stac-tiles';

export const TITILER_COLORMAPS = {
  floodExtent: {
    0: [0, 0, 0, 0],
    1: [222, 235, 247, 255],
    2: [198, 219, 239, 255],
    3: [158, 202, 225, 255],
    4: [107, 174, 214, 255],
    5: [49, 130, 189, 255],
    6: [8, 81, 156, 255],
  },
  croplandRangeland: {
    0: [0, 0, 0, 0],
    1: [207, 198, 201, 255],
    20: [207, 198, 201, 255],
    21: [255, 255, 203, 255],
    40: [255, 255, 203, 255],
    41: [204, 225, 172, 255],
    80: [204, 225, 172, 255],
    81: [152, 195, 141, 255],
    120: [152, 195, 141, 255],
    121: [100, 164, 110, 255],
    160: [100, 164, 110, 255],
    161: [48, 134, 80, 255],
    255: [48, 134, 80, 255],
  },
  landscan: {
    0: [0, 0, 0, 0],
    1: [255, 255, 190, 255],
    5: [255, 255, 190, 255],
    6: [255, 255, 115, 255],
    25: [255, 255, 115, 255],
    26: [255, 255, 0, 255],
    50: [255, 255, 0, 255],
    51: [255, 170, 0, 255],
    100: [255, 170, 0, 255],
    101: [255, 102, 0, 255],
    500: [255, 102, 0, 255],
    501: [255, 0, 0, 255],
    2500: [255, 0, 0, 255],
    2501: [204, 0, 0, 255],
    5000: [204, 0, 0, 255],
    5001: [115, 0, 0, 255],
    65535: [115, 0, 0, 255],
  },
  wrfDaily: {
    0: [0, 0, 0, 0],
    1: [217, 217, 217, 255],
    10: [217, 217, 217, 255],
    11: [255, 176, 0, 255],
    30: [255, 176, 0, 255],
    31: [255, 242, 51, 255],
    50: [255, 242, 51, 255],
    51: [157, 255, 88, 255],
    100: [157, 255, 88, 255],
    101: [50, 230, 70, 255],
    200: [50, 230, 70, 255],
    201: [27, 157, 55, 255],
    2000: [27, 157, 55, 255],
  },
  wrfF90: {
    0: [0, 0, 0, 0],
    1: [152, 223, 238, 255],
    255: [152, 223, 238, 255],
  },
  wrfF95: {
    0: [0, 0, 0, 0],
    1: [43, 123, 216, 255],
    255: [43, 123, 216, 255],
  },
  wrfF99: {
    0: [0, 0, 0, 0],
    1: [9, 26, 136, 255],
    255: [9, 26, 136, 255],
  },
};

export const TITILER_STYLE_DEFAULTS = [
  {
    match: '/collections/flood-extent-return-periods/',
    params: {
      assets: 'data',
      resampling: 'nearest',
      colormap: JSON.stringify(TITILER_COLORMAPS.floodExtent),
    },
  },
  {
    match: '/collections/asap-cropland/',
    params: {
      assets: 'data',
      resampling: 'nearest',
      colormap: JSON.stringify(TITILER_COLORMAPS.croplandRangeland),
    },
  },
  {
    match: '/collections/asap-rangeland/',
    params: {
      assets: 'data',
      resampling: 'nearest',
      colormap: JSON.stringify(TITILER_COLORMAPS.croplandRangeland),
    },
  },
  {
    match: '/collections/landscan-population/',
    params: {
      assets: 'data',
      resampling: 'bilinear',
      rescale: '1,5001',
      colormap: JSON.stringify(TITILER_COLORMAPS.landscan),
    },
  },
  {
    match: '/collections/wrf-daily-rainfall/',
    params: {
      assets: 'data',
      resampling: 'bilinear',
      rescale: '0,200',
      colormap: JSON.stringify(TITILER_COLORMAPS.wrfDaily),
    },
  },
  {
    match: '-f90/tiles/',
    params: {
      assets: 'data',
      resampling: 'nearest',
      rescale: '0,1',
      colormap: JSON.stringify(TITILER_COLORMAPS.wrfF90),
    },
  },
  {
    match: '-f95/tiles/',
    params: {
      assets: 'data',
      resampling: 'nearest',
      rescale: '0,1',
      colormap: JSON.stringify(TITILER_COLORMAPS.wrfF95),
    },
  },
  {
    match: '-f99/tiles/',
    params: {
      assets: 'data',
      resampling: 'nearest',
      rescale: '0,1',
      colormap: JSON.stringify(TITILER_COLORMAPS.wrfF99),
    },
  },
];

export const applyTitilerStyleDefaults = (url) => {
  if (!url || typeof url !== 'string' || !isTitilerTileUrl(url)) return url;

  const [baseUrl, rawQuery = ''] = url.split('?');
  const baseUrlLower = baseUrl.toLowerCase();
  const style = TITILER_STYLE_DEFAULTS.find((entry) => baseUrlLower.includes(entry.match));
  if (!style) return url;

  const searchParams = new URLSearchParams(rawQuery);
  Object.entries(style.params).forEach(([key, value]) => {
    const existing = searchParams.get(key);
    if (existing !== null && String(existing).trim() !== '') return;
    if (key === 'colormap' && searchParams.has('colormap_name')) return;
    searchParams.set(key, value);
  });

  const query = searchParams.toString();
  return query ? `${baseUrl}?${query}` : baseUrl;
};
