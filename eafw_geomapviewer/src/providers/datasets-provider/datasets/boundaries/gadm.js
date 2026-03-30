/**
 * Political boundaries via gha.admin_by_zoom tileserv function.
 * Auto-selects admin level based on zoom:
 *   z<=5: country (admin0)
 *   z<=7: region  (admin1)
 *   z>7:  district (admin2)
 *
 * Source-layer: gha.admin_clipped
 * Properties: country, region (admin1+), district (admin2+)
 */
// Read scope from URL for project-scoped boundary filtering
const urlScope = typeof window !== "undefined"
  ? new URLSearchParams(window.location.search).get("scope") || ""
  : "";
const scopeParam = urlScope ? `?scope=${encodeURIComponent(urlScope)}` : "";

const datasets = [
  {
    id: "political-boundaries",
    dataset: "political-boundaries",
    name: "Admin Boundaries",
    layer: "political-boundaries",
    isBoundary: true,
    layers: [
      {
        isBoundary: true,
        analysisEndpoint: "admin",
        name: "Admin Boundaries",
        id: "political-boundaries",
        type: "layer",
        description: "GHoA Administrative Boundaries (zoom-adaptive)",
        provider: "geojson",
        default: true,
        active: true,
        layerConfig: {
          type: "vector",
          source: {
            tiles: [
              `/pg/tileserv/gha.admin_by_zoom/{z}/{x}/{y}.pbf${scopeParam}`,
            ],
            type: "vector",
          },
          render: {
            layers: [
              // ── Invisible fill for click interaction ──
              {
                "source-layer": "gha.admin_clipped",
                type: "fill",
                paint: {
                  "fill-color": "#ffffff",
                  "fill-opacity": 0,
                },
              },
              // ── Country lines — all zoom levels, thicker ──
              {
                "source-layer": "gha.admin_clipped",
                type: "line",
                maxzoom: 6,
                paint: {
                  "line-color": "#555555",
                  "line-width": 1.5,
                  "line-opacity": 0.8,
                },
              },
              {
                "source-layer": "gha.admin_clipped",
                type: "line",
                minzoom: 6,
                paint: {
                  "line-color": "#444444",
                  "line-width": 2,
                  "line-opacity": 0.9,
                },
              },
            ],
          },
        },
        interactionConfig: {
          output: [
            {
              column: "country",
              property: "Country",
              type: "string",
            },
            {
              column: "region",
              property: "Region",
              type: "string",
            },
            {
              column: "district",
              property: "District",
              type: "string",
            },
          ],
          type: "intersection",
        },
      },
    ],
  },
];

export default { datasets };
