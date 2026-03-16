const category = 28;
const subCategory = 99;

const layerId = "nile2-ffpi_adjusted";
const name = "FFPI (Flash Flood Potential Index)";

const wmsBaseUrl =
  "https://nilebasin-dss-data.azurewebsites.net/geoserver/nile2/wms";

const datasets = [
  {
    id: layerId,
    dataset: layerId,
    name: name,
    layer: layerId,
    category: category,
    sub_category: subCategory,
    metadata: "",
    summary:
      "FFPI quantifies the flash flood potential of a catchment based on its static physiographic properties.",
    global: false,
    capabilities: [],
    layers: [
      {
        name: name,
        id: layerId,
        type: "layer",
        default: true,
        dataset: layerId,
        layerConfig: {
          type: "raster",
          source: {
            type: "raster",
            tiles: [
              `${wmsBaseUrl}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=ffpi_adjusted&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}`,
            ],
            minzoom: 3,
            maxzoom: 12,
          },
        },
        params: {},
        paramsSelectorConfig: [],
        legendConfig: {
          type: "basic",
          items: [
            { name: "Low", color: "#FFFFB2" },
            { name: "Medium", color: "#FECC5C" },
            { name: "High", color: "#FD8D3C" },
            { name: "Very High", color: "#E31A1C" },
          ],
        },
      },
    ],
  },
];

const updates = [];

export default { datasets, updates };
