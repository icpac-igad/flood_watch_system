const category = 28;
const subCategory = 99;

const layerId = "nile2-dffpi_tiled";
const name = "DFFPI (Dynamic Flash Flood Potential Index)";

const wmsBaseUrl =
  "https://nilebasin-dss-data.azurewebsites.net/geoserver/nile2/wms";

/**
 * Expand a WMS time range "start/end/period" into an array of ISO timestamps.
 * Supports P1D (daily) period. Returns last 90 days max to keep the selector manageable.
 */
function expandTimeRange(rangeStr) {
  const parts = rangeStr.split("/");
  if (parts.length !== 3) return [rangeStr];

  const start = new Date(parts[0]);
  const end = new Date(parts[1]);
  const period = parts[2]; // e.g. "P1D"

  if (isNaN(start) || isNaN(end)) return [];

  // Parse ISO 8601 duration (supports P1D, P7D, PT6H etc.)
  let stepMs = 86400000; // default 1 day
  const dMatch = period.match(/P(\d+)D/);
  const hMatch = period.match(/PT(\d+)H/);
  if (dMatch) stepMs = parseInt(dMatch[1]) * 86400000;
  else if (hMatch) stepMs = parseInt(hMatch[1]) * 3600000;

  // Only generate last 90 days to keep selector fast
  const maxStart = new Date(end.getTime() - 90 * 86400000);
  const effectiveStart = start > maxStart ? start : maxStart;

  const timestamps = [];
  for (let t = effectiveStart.getTime(); t <= end.getTime(); t += stepMs) {
    timestamps.push(new Date(t).toISOString());
  }
  return timestamps;
}

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
      "DFFPI quantifies the flash flood potential of a catchment based on its static physiographic properties and the actual hydrometeorological conditions.",
    global: false,
    capabilities: ["timeseries"],
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
              `${wmsBaseUrl}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&FORMAT=image/png&TRANSPARENT=true&LAYERS=dffpi_tiled&STYLES=&WIDTH=256&HEIGHT=256&SRS=EPSG:3857&BBOX={bbox-epsg-3857}&TIME={time}`,
            ],
            minzoom: 3,
            maxzoom: 12,
          },
        },
        params: {
          time: "",
        },
        paramsSelectorConfig: [
          {
            key: "time",
            required: true,
            sentence: "{selector}",
            type: "datetime",
            dateFormat: { currentTime: "yyyy-MM-dd HH:mm" },
            availableDates: [],
          },
        ],
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

const updates = [
  {
    layer: layerId,
    getTimestamps: async () => {
      try {
        const res = await fetch(
          `${wmsBaseUrl}?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities`
        );
        const text = await res.text();
        const parser = new DOMParser();
        const xml = parser.parseFromString(text, "text/xml");

        const layers = xml.querySelectorAll("Layer");
        for (const layer of layers) {
          const nameEl = layer.querySelector("Name");
          if (nameEl && nameEl.textContent === "dffpi_tiled") {
            // WMS 1.1.1 uses Extent element for time values
            const extEls = layer.querySelectorAll("Extent");
            for (const ext of extEls) {
              if (ext.getAttribute("name") === "time") {
                const timeStr = ext.textContent.trim();
                // Range format: "start/end/period"
                if (timeStr.includes("/")) {
                  return expandTimeRange(timeStr);
                }
                // Comma-separated list
                return timeStr.split(",").map((t) => t.trim());
              }
            }
          }
        }
      } catch (e) {
        console.warn("[DFFPI] Failed to fetch timestamps:", e);
      }
      return [];
    },
    getCurrentLayerTime: (timestamps) => {
      // Default to the most recent timestamp
      return timestamps.length > 0 ? timestamps[timestamps.length - 1] : null;
    },
    updateInterval: 3600000, // every hour
  },
];

export default { datasets, updates };
