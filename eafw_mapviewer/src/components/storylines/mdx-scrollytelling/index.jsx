import React, { useMemo, useEffect, useState, useRef, useCallback } from "react";
import PropTypes from "prop-types";
import maplibregl from "maplibre-gl";
import { FASTAPI_API } from "@/utils/constants";
import "@/components/storylines/viewer/styles.scss";

const DEFAULT_CENTER = [40.5, 5.0];
const DEFAULT_ZOOM = 4;

const OVERLAY_SOURCE_PREFIX = "storyline-overlay-src";
const OVERLAY_LAYER_PREFIX = "storyline-overlay-lyr";
const ADMIN0_SOURCE_PREFIX = "storyline-admin0-src";
const ADMIN0_FILL_LAYER_PREFIX = "storyline-admin0-fill";
const ADMIN0_LINE_LAYER_PREFIX = "storyline-admin0-line";
const ADMIN0_MASK_SOURCE_PREFIX = "storyline-admin0-mask-src";
const ADMIN0_MASK_LAYER_PREFIX = "storyline-admin0-mask-lyr";
const PINPOINT_SOURCE_PREFIX = "storyline-pinpoint-src";
const PINPOINT_LAYER_PREFIX = "storyline-pinpoint-lyr";
const PINPOINT_LABEL_LAYER_PREFIX = "storyline-pinpoint-label-lyr";
const PINPOINT_AREA_SOURCE_PREFIX = "storyline-pinpoint-area-src";
const PINPOINT_AREA_FILL_LAYER_PREFIX = "storyline-pinpoint-area-fill-lyr";
const PINPOINT_AREA_LINE_LAYER_PREFIX = "storyline-pinpoint-area-line-lyr";

const MASK_WORLD_RING = [
  [-180, -85],
  [180, -85],
  [180, 85],
  [-180, 85],
  [-180, -85],
];

const FALLBACK_BASEMAP_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [
    {
      id: "osm",
      type: "raster",
      source: "osm",
      minzoom: 0,
      maxzoom: 22,
    },
  ],
};

const MIN_CONTAINER_WIDTH = 320;
const MIN_CONTAINER_HEIGHT = 260;

const clamp01 = (value, fallback = 0.45) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return fallback;
  return Math.max(0, Math.min(1, num));
};

const toPositiveNumber = (value, fallback) => {
  const num = Number(value);
  if (!Number.isFinite(num) || num < 0) return fallback;
  return num;
};

const parseOverlayList = (value) => {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch (err) {
      return [];
    }
  }
  return [];
};

const normalizePlaceName = (value) => {
  if (typeof value !== "string") return "";
  return value.trim().toLowerCase();
};

const normalizeAdmin0Code = (value) => {
  if (typeof value !== "string") return null;
  const code = value.trim().toUpperCase();
  return code || null;
};

const parsePinpointList = (value) => {
  let parsed = value;
  if (typeof value === "string") {
    try {
      parsed = JSON.parse(value);
    } catch (err) {
      parsed = [];
    }
  }

  if (!Array.isArray(parsed)) return [];

  return parsed
    .map((item, idx) => {
      if (typeof item === "string") {
        return {
          id: `pinpoint-${idx}`,
          label: item,
          placeName: item,
          center: null,
          color: null,
        };
      }

      if (!item || typeof item !== "object") return null;

      const centerFromCoords = toCenterCoordinate(
        item.center ||
          item.coordinates ||
          item.coord ||
          item.centralPoint ||
          item.central_point
      );

      const centerFromLngLat =
        (item.lng !== undefined || item.lon !== undefined) && item.lat !== undefined
          ? toCenterCoordinate([item.lng ?? item.lon, item.lat])
          : null;

      return {
        id: item.id || `pinpoint-${idx}`,
        label:
          item.label ||
          item.name ||
          item.place ||
          item.district ||
          item.title ||
          `Location ${idx + 1}`,
        placeName:
          item.name || item.place || item.district || item.location || item.label || "",
        center: centerFromCoords || centerFromLngLat || null,
        color: typeof item.color === "string" ? item.color : null,
      };
    })
    .filter(Boolean);
};

const toCenterCoordinate = (value) => {
  if (Array.isArray(value) && value.length >= 2) {
    const lng = Number(value[0]);
    const lat = Number(value[1]);
    if (Number.isFinite(lng) && Number.isFinite(lat)) {
      return [lng, lat];
    }
    return null;
  }

  if (typeof value === "string") {
    const parts = value
      .split(",")
      .map((p) => Number(p.trim()))
      .filter((num) => Number.isFinite(num));
    if (parts.length >= 2) {
      return [parts[0], parts[1]];
    }
  }

  if (value && typeof value === "object") {
    if (Array.isArray(value.coordinates) && value.coordinates.length >= 2) {
      return toCenterCoordinate(value.coordinates);
    }
    if ("lng" in value && "lat" in value) {
      return toCenterCoordinate([value.lng, value.lat]);
    }
    if ("lon" in value && "lat" in value) {
      return toCenterCoordinate([value.lon, value.lat]);
    }
  }

  return null;
};

const extractOuterRings = (geometry) => {
  if (!geometry?.type || !geometry?.coordinates) return [];

  if (geometry.type === "Polygon") {
    return geometry.coordinates[0] ? [geometry.coordinates[0]] : [];
  }

  if (geometry.type === "MultiPolygon") {
    return geometry.coordinates
      .map((polygon) => polygon?.[0])
      .filter((ring) => Array.isArray(ring) && ring.length >= 4);
  }

  return [];
};

const buildMaskGeometry = (geometry) => {
  const holes = extractOuterRings(geometry);
  if (!holes.length) return null;

  return {
    type: "Polygon",
    coordinates: [MASK_WORLD_RING, ...holes],
  };
};

const computeBoundsFromGeometry = (geometry) => {
  if (!geometry?.coordinates) return null;

  const bounds = [Infinity, Infinity, -Infinity, -Infinity];

  const walk = (coords) => {
    if (!Array.isArray(coords)) return;

    if (
      coords.length >= 2 &&
      Number.isFinite(Number(coords[0])) &&
      Number.isFinite(Number(coords[1]))
    ) {
      const lng = Number(coords[0]);
      const lat = Number(coords[1]);
      if (lng < bounds[0]) bounds[0] = lng;
      if (lat < bounds[1]) bounds[1] = lat;
      if (lng > bounds[2]) bounds[2] = lng;
      if (lat > bounds[3]) bounds[3] = lat;
      return;
    }

    coords.forEach(walk);
  };

  walk(geometry.coordinates);

  if (!Number.isFinite(bounds[0]) || !Number.isFinite(bounds[1])) {
    return null;
  }

  return bounds;
};

const computeCenterFromGeometry = (geometry) => {
  const bounds = computeBoundsFromGeometry(geometry);
  if (!bounds) return null;

  return [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2];
};

const computeBoundsFromFeatures = (features) => {
  if (!Array.isArray(features) || !features.length) return null;

  const merged = [Infinity, Infinity, -Infinity, -Infinity];

  features.forEach((feature) => {
    const featureBounds = computeBoundsFromGeometry(feature?.geometry);
    if (!featureBounds) return;

    if (featureBounds[0] < merged[0]) merged[0] = featureBounds[0];
    if (featureBounds[1] < merged[1]) merged[1] = featureBounds[1];
    if (featureBounds[2] > merged[2]) merged[2] = featureBounds[2];
    if (featureBounds[3] > merged[3]) merged[3] = featureBounds[3];
  });

  if (!Number.isFinite(merged[0]) || !Number.isFinite(merged[1])) return null;
  return merged;
};

const extractBasemapConfig = (payload) => {
  const basemaps = Array.isArray(payload?.basemaps)
    ? payload.basemaps
    : Array.isArray(payload?.data?.basemaps)
      ? payload.data.basemaps
      : [];

  if (!basemaps.length) return null;

  const active = basemaps.find((b) => Boolean(b?.default)) || basemaps[0];
  if (!active) return null;

  return {
    mapStyle: active.mapStyle || null,
    basemapGroup: active.basemapGroup || null,
    labelsGroup: active.labelsGroup || null,
  };
};

const applyBasemapGroupVisibility = (map, basemapConfig) => {
  if (!map || !basemapConfig) return;

  const style = map.getStyle();
  const layers = style?.layers || [];
  const mapboxGroups = style?.metadata?.["mapbox:groups"] || {};

  if (!layers.length || !Object.keys(mapboxGroups).length) return;

  const { basemapGroup, labelsGroup } = basemapConfig;

  layers.forEach((layer) => {
    const groupId = layer?.metadata?.["mapbox:group"];
    if (!groupId) return;

    const groupName = mapboxGroups[groupId]?.name;
    if (!groupName) return;

    try {
      if (basemapGroup && groupName.startsWith("basemap-")) {
        map.setLayoutProperty(
          layer.id,
          "visibility",
          groupName === basemapGroup ? "visible" : "none"
        );
      } else if (labelsGroup && groupName.startsWith("labels-")) {
        map.setLayoutProperty(
          layer.id,
          "visibility",
          groupName === labelsGroup ? "visible" : "none"
        );
      }
    } catch (err) {
      // Ignore layers that do not support visibility toggling.
    }
  });
};

const normalizeChapter = (element, index) => {
  const props = element?.props || {};
  const explicitCenter =
    toCenterCoordinate(props.center) ||
    toCenterCoordinate(props.centralPoint) ||
    toCenterCoordinate(props.central_point);
  const center = explicitCenter || DEFAULT_CENTER;

  return {
    key: props.id || props.slug || index,
    title: props.title || `Chapter ${index + 1}`,
    dateStart: props.dateStart || props.date_start || null,
    dateEnd: props.dateEnd || props.date_end || null,
    transition: props.transition || "fly",
    admin0: normalizeAdmin0Code(props.admin0 || props.countryCode || props.gid0),
    mapState: {
      center,
      zoom: Number.isFinite(Number(props.zoom)) ? Number(props.zoom) : DEFAULT_ZOOM,
      bearing: Number.isFinite(Number(props.bearing)) ? Number(props.bearing) : 0,
      pitch: Number.isFinite(Number(props.pitch)) ? Number(props.pitch) : 0,
    },
    explicitCenter,
    overlays: parseOverlayList(props.mapOverlays || props.map_overlays),
    pinpoints: parsePinpointList(props.pinpoints || props.pin_points || props.locations),
    content: props.children,
  };
};

export const Chapter = ({ children }) => <>{children}</>;

Chapter.displayName = "Chapter";
Chapter.propTypes = {
  children: PropTypes.node,
};

const MdxScrollytellingBlock = ({ children }) => {
  const chapters = useMemo(() => {
    return React.Children.toArray(children)
      .filter((child) => React.isValidElement(child))
      .map((child, index) => normalizeChapter(child, index));
  }, [children]);

  const [activeChapterIdx, setActiveChapterIdx] = useState(0);
  const [mapReady, setMapReady] = useState(false);
  const [basemapConfig, setBasemapConfig] = useState(null);
  const [basemapResolved, setBasemapResolved] = useState(false);
  const [chapterLocationLabels, setChapterLocationLabels] = useState({});

  const mapContainerRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const mapRef = useRef(null);
  const activeOverlayRefs = useRef([]);
  const admin0FeatureCacheRef = useRef(new Map());
  const admin2FeatureCacheRef = useRef(new Map());
  const reverseGeocodeCacheRef = useRef(new Map());

  useEffect(() => {
    if (!chapters.length) return;
    setActiveChapterIdx((prev) =>
      prev < 0 || prev >= chapters.length ? 0 : prev
    );
  }, [chapters.length]);

  const clearChapterOverlays = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;

    const sourcesToRemove = new Set();

    for (let i = activeOverlayRefs.current.length - 1; i >= 0; i -= 1) {
      const { layerId, sourceId } = activeOverlayRefs.current[i];
      if (map.getLayer(layerId)) map.removeLayer(layerId);
      if (sourceId) sourcesToRemove.add(sourceId);
    }

    sourcesToRemove.forEach((sourceId) => {
      if (map.getSource(sourceId)) map.removeSource(sourceId);
    });

    activeOverlayRefs.current = [];
  }, []);

  const fetchAdmin0Feature = useCallback(async (admin0Code) => {
    const code = normalizeAdmin0Code(admin0Code);
    if (!code) return null;

    if (admin0FeatureCacheRef.current.has(code)) {
      return admin0FeatureCacheRef.current.get(code);
    }

    try {
      const res = await fetch(
        `${FASTAPI_API}/boundaries/admin0?country=${encodeURIComponent(code)}`
      );
      if (!res.ok) throw new Error(`admin0 fetch failed for ${code}`);

      const payload = await res.json();
      const rawFeature = payload?.features?.[0] || null;
      const rawGeometry = rawFeature?.geometry;
      let geometry = rawGeometry;

      if (typeof rawGeometry === "string") {
        try {
          geometry = JSON.parse(rawGeometry);
        } catch (err) {
          geometry = null;
        }
      }

      const feature = rawFeature && geometry
        ? { ...rawFeature, geometry }
        : null;
      admin0FeatureCacheRef.current.set(code, feature);
      return feature;
    } catch (err) {
      admin0FeatureCacheRef.current.set(code, null);
      return null;
    }
  }, []);

  const fetchAllAdmin0Features = useCallback(async () => {
    const cacheKey = "__ALL_ADMIN0__";
    if (admin0FeatureCacheRef.current.has(cacheKey)) {
      return admin0FeatureCacheRef.current.get(cacheKey);
    }

    try {
      const res = await fetch(`${FASTAPI_API}/boundaries/admin0`);
      if (!res.ok) throw new Error("admin0 fetch failed");

      const payload = await res.json();
      const features = Array.isArray(payload?.features)
        ? payload.features
            .map((rawFeature) => {
              if (!rawFeature) return null;
              const rawGeometry = rawFeature.geometry;
              let geometry = rawGeometry;

              if (typeof rawGeometry === "string") {
                try {
                  geometry = JSON.parse(rawGeometry);
                } catch (err) {
                  geometry = null;
                }
              }

              const parsedFeature = geometry ? { ...rawFeature, geometry } : null;
              const gid0 = normalizeAdmin0Code(rawFeature?.properties?.gid_0);
              if (gid0 && parsedFeature) {
                admin0FeatureCacheRef.current.set(gid0, parsedFeature);
              }
              return parsedFeature;
            })
            .filter(Boolean)
        : [];

      admin0FeatureCacheRef.current.set(cacheKey, features);
      return features;
    } catch (err) {
      admin0FeatureCacheRef.current.set(cacheKey, []);
      return [];
    }
  }, []);

  const fetchAdmin2Features = useCallback(async (admin0Code) => {
    const code = normalizeAdmin0Code(admin0Code);
    if (!code) return [];

    if (admin2FeatureCacheRef.current.has(code)) {
      return admin2FeatureCacheRef.current.get(code);
    }

    try {
      const res = await fetch(
        `${FASTAPI_API}/boundaries/admin2?country=${encodeURIComponent(code)}`
      );
      if (!res.ok) throw new Error(`admin2 fetch failed for ${code}`);

      const payload = await res.json();
      const features = Array.isArray(payload?.features)
        ? payload.features
            .map((rawFeature) => {
              if (!rawFeature) return null;
              const rawGeometry = rawFeature.geometry;
              let geometry = rawGeometry;

              if (typeof rawGeometry === "string") {
                try {
                  geometry = JSON.parse(rawGeometry);
                } catch (err) {
                  geometry = null;
                }
              }

              return geometry ? { ...rawFeature, geometry } : null;
            })
            .filter(Boolean)
        : [];

      admin2FeatureCacheRef.current.set(code, features);
      return features;
    } catch (err) {
      admin2FeatureCacheRef.current.set(code, []);
      return [];
    }
  }, []);

  const fetchReverseGeocodedLabel = useCallback(async (chapter) => {
    const center = chapter?.explicitCenter;
    if (!Array.isArray(center) || center.length < 2) return null;

    const lon = Number(center[0]);
    const lat = Number(center[1]);
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;

    const admin0Code = normalizeAdmin0Code(chapter?.admin0);
    const cacheKey = `${lon.toFixed(5)},${lat.toFixed(5)}:${admin0Code || ""}`;
    if (reverseGeocodeCacheRef.current.has(cacheKey)) {
      return reverseGeocodeCacheRef.current.get(cacheKey);
    }

    try {
      const params = new URLSearchParams({
        lon: String(lon),
        lat: String(lat),
      });
      if (admin0Code) {
        params.set("country", admin0Code);
      }

      const res = await fetch(
        `${FASTAPI_API}/boundaries/reverse-geocode?${params.toString()}`
      );
      if (!res.ok) {
        reverseGeocodeCacheRef.current.set(cacheKey, null);
        return null;
      }

      const payload = await res.json();
      const label = payload?.match?.display_name || null;
      reverseGeocodeCacheRef.current.set(cacheKey, label);
      return label;
    } catch (err) {
      reverseGeocodeCacheRef.current.set(cacheKey, null);
      return null;
    }
  }, []);

  const resolveChapterPinpoints = useCallback(
    async (chapter) => {
      const pinpoints = Array.isArray(chapter?.pinpoints) ? chapter.pinpoints : [];
      if (!pinpoints.length) {
        return { pointFeatures: [], areaFeatures: [] };
      }

      const admin0Code = normalizeAdmin0Code(chapter?.admin0);
      const requiresLookup = pinpoints.some(
        (point) => !point.center && normalizePlaceName(point.placeName || point.label)
      );

      const admin2Features =
        requiresLookup && admin0Code ? await fetchAdmin2Features(admin0Code) : [];

      const admin2ByName = new Map();
      admin2Features.forEach((feature) => {
        const name = normalizePlaceName(feature?.properties?.name_2);
        if (name && !admin2ByName.has(name)) {
          admin2ByName.set(name, feature);
        }
      });

      const areaFeatures = [];
      const seenAreaKeys = new Set();

      const pointFeatures = pinpoints
        .map((point, idx) => {
          let center = point.center;
          let matchedFeature = null;
          const normalized = normalizePlaceName(point.placeName || point.label);
          if (admin2ByName.size && normalized) {
            let match = normalized ? admin2ByName.get(normalized) : null;

            if (!match && normalized) {
              const fuzzyMatch = Array.from(admin2ByName.entries()).find(
                ([name]) => name.includes(normalized) || normalized.includes(name)
              );
              match = fuzzyMatch?.[1] || null;
            }

            matchedFeature = match || null;
            if (!center) {
              center = matchedFeature?.geometry
              ? computeCenterFromGeometry(matchedFeature.geometry)
              : null;
            }
          }

          if (matchedFeature?.geometry) {
            const gid2 = matchedFeature?.properties?.gid_2 || "";
            const areaLabel =
              point.label || matchedFeature?.properties?.name_2 || `Area ${idx + 1}`;
            const areaKey = `${gid2}:${areaLabel}`;
            if (!seenAreaKeys.has(areaKey)) {
              seenAreaKeys.add(areaKey);
              areaFeatures.push({
                type: "Feature",
                properties: {
                  id: areaKey,
                  label: areaLabel,
                  color: point.color || "#f97316",
                },
                geometry: matchedFeature.geometry,
              });
            }
          }

          if (!center) return null;

          return {
            type: "Feature",
            properties: {
              id: point.id || `pinpoint-${idx}`,
              label: point.label || point.placeName || `Location ${idx + 1}`,
              color: point.color || "#ef4444",
            },
            geometry: {
              type: "Point",
              coordinates: center,
            },
          };
        })
        .filter(Boolean);

      return { pointFeatures, areaFeatures };
    },
    [fetchAdmin2Features]
  );

  const applyChapterPinpoints = useCallback(
    async (chapter, chapterIdx) => {
      const map = mapRef.current;
      if (!map) return;

      const { pointFeatures, areaFeatures } = await resolveChapterPinpoints(chapter);
      if (!pointFeatures.length && !areaFeatures.length) return;

      const areaSourceId = `${PINPOINT_AREA_SOURCE_PREFIX}-${chapterIdx}`;
      const areaFillLayerId = `${PINPOINT_AREA_FILL_LAYER_PREFIX}-${chapterIdx}`;
      const areaLineLayerId = `${PINPOINT_AREA_LINE_LAYER_PREFIX}-${chapterIdx}`;
      const pointSourceId = `${PINPOINT_SOURCE_PREFIX}-${chapterIdx}`;
      const circleLayerId = `${PINPOINT_LAYER_PREFIX}-${chapterIdx}`;
      const labelLayerId = `${PINPOINT_LABEL_LAYER_PREFIX}-${chapterIdx}`;

      if (areaFeatures.length) {
        try {
          map.addSource(areaSourceId, {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              features: areaFeatures,
            },
          });

          map.addLayer({
            id: areaFillLayerId,
            type: "fill",
            source: areaSourceId,
            paint: {
              "fill-color": ["coalesce", ["get", "color"], "#f97316"],
              "fill-opacity": 0.18,
            },
          });
          activeOverlayRefs.current.push({ sourceId: areaSourceId, layerId: areaFillLayerId });

          map.addLayer({
            id: areaLineLayerId,
            type: "line",
            source: areaSourceId,
            paint: {
              "line-color": ["coalesce", ["get", "color"], "#ea580c"],
              "line-width": 2,
              "line-opacity": 0.95,
            },
          });
          activeOverlayRefs.current.push({ sourceId: areaSourceId, layerId: areaLineLayerId });
        } catch (err) {
          // Keep chapter scroll functional even when area rendering fails.
        }
      }

      if (!pointFeatures.length) return;

      try {
        map.addSource(pointSourceId, {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: pointFeatures,
          },
        });

        map.addLayer({
          id: circleLayerId,
          type: "circle",
          source: pointSourceId,
          paint: {
            "circle-color": ["coalesce", ["get", "color"], "#ef4444"],
            "circle-radius": 7.2,
            "circle-opacity": 0.96,
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.8,
          },
        });
        activeOverlayRefs.current.push({ sourceId: pointSourceId, layerId: circleLayerId });
      } catch (err) {
        return;
      }

      try {
        map.addLayer({
          id: labelLayerId,
          type: "symbol",
          source: pointSourceId,
          layout: {
            "text-field": ["get", "label"],
            "text-size": 12,
            "text-anchor": "top",
            "text-offset": [0, 1.15],
          },
          paint: {
            "text-color": "#0f172a",
            "text-halo-color": "#ffffff",
            "text-halo-width": 1.2,
          },
        });
        activeOverlayRefs.current.push({ sourceId: pointSourceId, layerId: labelLayerId });
      } catch (err) {
        // Keep chapter scroll functional even when label rendering fails.
      }
    },
    [resolveChapterPinpoints]
  );

  useEffect(() => {
    let cancelled = false;

    const fetchBasemap = async () => {
      setBasemapResolved(false);

      try {
        const mapConfigRes = await fetch(`${FASTAPI_API}/mapviewer-config`);
        if (mapConfigRes.ok) {
          const mapConfigData = await mapConfigRes.json();
          if (!cancelled) {
            setBasemapConfig(extractBasemapConfig(mapConfigData));
          }
        }
      } catch (err) {
        // Keep scrollytelling map functional with fallback style.
      } finally {
        if (!cancelled) setBasemapResolved(true);
      }
    };

    fetchBasemap();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!basemapResolved || mapRef.current || typeof window === "undefined") return;

    let cancelled = false;
    let frameId = null;
    let map = null;

    const initMap = () => {
      if (cancelled || mapRef.current) return;

      const container = mapContainerRef.current;
      if (!container) {
        frameId = window.requestAnimationFrame(initMap);
        return;
      }

      const { clientWidth, clientHeight } = container;
      if (clientWidth < MIN_CONTAINER_WIDTH || clientHeight < MIN_CONTAINER_HEIGHT) {
        frameId = window.requestAnimationFrame(initMap);
        return;
      }

      map = new maplibregl.Map({
        container,
        style: basemapConfig?.mapStyle || FALLBACK_BASEMAP_STYLE,
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
        attributionControl: false,
        scrollZoom: false,
      });
      map.scrollZoom.disable();

      map.addControl(
        new maplibregl.NavigationControl({ showCompass: true }),
        "bottom-right"
      );
      map.addControl(
        new maplibregl.AttributionControl({ compact: true }),
        "bottom-left"
      );

      map.on("load", () => {
        applyBasemapGroupVisibility(map, basemapConfig);
        const safeResize = () => {
          try {
            map.resize();
          } catch (err) {
            // Ignore transient resize errors during style boot.
          }
        };
        // Resize after initial paint and again after layout settles (hero/media load).
        safeResize();
        window.requestAnimationFrame(safeResize);
        window.setTimeout(safeResize, 250);
        window.setTimeout(safeResize, 1000);
        setMapReady(true);
      });

      map.on("styledata", () => {
        applyBasemapGroupVisibility(map, basemapConfig);
      });

      mapRef.current = map;
    };

    initMap();

    return () => {
      cancelled = true;
      if (frameId) {
        window.cancelAnimationFrame(frameId);
      }
      clearChapterOverlays();
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      } else if (map) {
        map.remove();
      }
      setMapReady(false);
    };
  }, [basemapResolved, basemapConfig, clearChapterOverlays]);

  useEffect(() => {
    const map = mapRef.current;
    const container = mapContainerRef.current;
    if (!map || !container || typeof window === "undefined") return undefined;

    const safeResize = () => {
      try {
        map.resize();
      } catch (err) {
        // Ignore resize race conditions during map teardown.
      }
    };

    let observer = null;
    if (typeof window.ResizeObserver !== "undefined") {
      observer = new window.ResizeObserver(() => {
        safeResize();
      });
      observer.observe(container);
    }

    window.addEventListener("resize", safeResize, { passive: true });
    window.requestAnimationFrame(safeResize);

    return () => {
      window.removeEventListener("resize", safeResize);
      if (observer) observer.disconnect();
    };
  }, [mapReady]);

  useEffect(() => {
    reverseGeocodeCacheRef.current.clear();
    setChapterLocationLabels({});
  }, [chapters]);

  useEffect(() => {
    if (activeChapterIdx < 0) return;
    if (chapterLocationLabels[activeChapterIdx] !== undefined) return;

    const chapter = chapters[activeChapterIdx];
    if (!chapter?.explicitCenter) return;

    let cancelled = false;

    const loadLabel = async () => {
      const label = await fetchReverseGeocodedLabel(chapter);
      if (cancelled) return;

      setChapterLocationLabels((prev) => {
        if (prev[activeChapterIdx] !== undefined) return prev;
        return { ...prev, [activeChapterIdx]: label };
      });
    };

    loadLabel();

    return () => {
      cancelled = true;
    };
  }, [activeChapterIdx, chapterLocationLabels, chapters, fetchReverseGeocodedLabel]);

  const applyChapterAdmin0Focus = useCallback(
    async (chapter, chapterIdx) => {
      const map = mapRef.current;
      const admin0Code = normalizeAdmin0Code(chapter?.admin0);
      if (!map || !admin0Code) return false;

      const feature = await fetchAdmin0Feature(admin0Code);
      const geometry = feature?.geometry;
      if (!geometry) return false;

      const focusSourceId = `${ADMIN0_SOURCE_PREFIX}-${chapterIdx}`;
      const focusFillId = `${ADMIN0_FILL_LAYER_PREFIX}-${chapterIdx}`;
      const focusLineId = `${ADMIN0_LINE_LAYER_PREFIX}-${chapterIdx}`;
      const maskSourceId = `${ADMIN0_MASK_SOURCE_PREFIX}-${chapterIdx}`;
      const maskLayerId = `${ADMIN0_MASK_LAYER_PREFIX}-${chapterIdx}`;

      try {
        const maskGeometry = buildMaskGeometry(geometry);
        if (maskGeometry) {
          map.addSource(maskSourceId, {
            type: "geojson",
            data: {
              type: "FeatureCollection",
              features: [{ type: "Feature", properties: {}, geometry: maskGeometry }],
            },
          });

          map.addLayer({
            id: maskLayerId,
            type: "fill",
            source: maskSourceId,
            paint: {
              "fill-color": "#dce2e8",
              "fill-opacity": 0.8,
            },
          });

          activeOverlayRefs.current.push({
            sourceId: maskSourceId,
            layerId: maskLayerId,
          });
        }

        map.addSource(focusSourceId, {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: [feature],
          },
        });

        map.addLayer({
          id: focusFillId,
          type: "fill",
          source: focusSourceId,
          paint: {
            "fill-color": "#7dd3fc",
            "fill-opacity": 0.18,
          },
        });
        activeOverlayRefs.current.push({ sourceId: focusSourceId, layerId: focusFillId });

        map.addLayer({
          id: focusLineId,
          type: "line",
          source: focusSourceId,
          paint: {
            "line-color": "#0b5cab",
            "line-width": 2.2,
            "line-opacity": 0.96,
          },
        });
        activeOverlayRefs.current.push({ sourceId: focusSourceId, layerId: focusLineId });
      } catch (err) {
        return false;
      }

      const bounds = computeBoundsFromGeometry(geometry);
      if (!bounds) return false;

      map.fitBounds(
        [
          [bounds[0], bounds[1]],
          [bounds[2], bounds[3]],
        ],
        {
          padding: { top: 90, right: 90, bottom: 80, left: 90 },
          duration: 1700,
          essential: true,
        }
      );

      return true;
    },
    [fetchAdmin0Feature]
  );

  const applyChapterRegionalAdmin0Focus = useCallback(
    async (chapter, chapterIdx) => {
      const map = mapRef.current;
      const admin0Code = normalizeAdmin0Code(chapter?.admin0);
      if (!map || admin0Code) return false;

      const features = await fetchAllAdmin0Features();
      if (!features.length) return false;

      const sourceId = `${ADMIN0_SOURCE_PREFIX}-regional-${chapterIdx}`;
      const fillId = `${ADMIN0_FILL_LAYER_PREFIX}-regional-${chapterIdx}`;
      const lineId = `${ADMIN0_LINE_LAYER_PREFIX}-regional-${chapterIdx}`;

      try {
        map.addSource(sourceId, {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features,
          },
        });

        map.addLayer({
          id: fillId,
          type: "fill",
          source: sourceId,
          paint: {
            "fill-color": "#7dd3fc",
            "fill-opacity": 0.09,
          },
        });
        activeOverlayRefs.current.push({ sourceId, layerId: fillId });

        map.addLayer({
          id: lineId,
          type: "line",
          source: sourceId,
          paint: {
            "line-color": "#0b5cab",
            "line-width": 1.15,
            "line-opacity": 0.68,
          },
        });
        activeOverlayRefs.current.push({ sourceId, layerId: lineId });
      } catch (err) {
        return false;
      }

      const bounds = computeBoundsFromFeatures(features);
      if (!bounds) return true;

      map.fitBounds(
        [
          [bounds[0], bounds[1]],
          [bounds[2], bounds[3]],
        ],
        {
          padding: { top: 84, right: 84, bottom: 72, left: 84 },
          duration: 1650,
          essential: true,
        }
      );

      return true;
    },
    [fetchAllAdmin0Features]
  );

  const applyChapterOverlays = useCallback((chapter, chapterIdx) => {
    const map = mapRef.current;
    if (!map) return;

    const overlays = Array.isArray(chapter?.overlays) ? chapter.overlays : [];
    if (!overlays.length) return;

    overlays.forEach((overlay, overlayIdx) => {
      if (!overlay?.url) return;

      const sourceId = `${OVERLAY_SOURCE_PREFIX}-${chapterIdx}-${overlayIdx}`;
      const layerId = `${OVERLAY_LAYER_PREFIX}-${chapterIdx}-${overlayIdx}`;
      const color = overlay.color || "#38bdf8";
      const layerType = overlay.layer_type || "fill";
      const opacity = clamp01(overlay.opacity, 0.45);
      const lineWidth = toPositiveNumber(overlay.line_width, 2);
      const pointRadius = toPositiveNumber(overlay.point_radius, 5);

      try {
        map.addSource(sourceId, {
          type: "geojson",
          data: overlay.url,
        });

        if (layerType === "line") {
          map.addLayer({
            id: layerId,
            type: "line",
            source: sourceId,
            paint: {
              "line-color": color,
              "line-width": lineWidth,
              "line-opacity": opacity,
            },
          });
        } else if (layerType === "circle") {
          map.addLayer({
            id: layerId,
            type: "circle",
            source: sourceId,
            paint: {
              "circle-color": color,
              "circle-radius": pointRadius,
              "circle-opacity": opacity,
              "circle-stroke-color": "#ffffff",
              "circle-stroke-width": 0.8,
            },
          });
        } else {
          map.addLayer({
            id: layerId,
            type: "fill",
            source: sourceId,
            paint: {
              "fill-color": color,
              "fill-opacity": opacity,
              "fill-outline-color": color,
            },
          });
        }

        activeOverlayRefs.current.push({ sourceId, layerId });
      } catch (err) {
        // Keep chapter scroll functional even when one overlay fails.
      }
    });
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || activeChapterIdx < 0) return;

    let cancelled = false;

    const chapter = chapters[activeChapterIdx];
    if (!chapter) {
      clearChapterOverlays();
      return;
    }

    const applyChapter = async () => {
      clearChapterOverlays();

      let focusedByAdmin0 = await applyChapterAdmin0Focus(chapter, activeChapterIdx);
      if (!focusedByAdmin0) {
        focusedByAdmin0 = await applyChapterRegionalAdmin0Focus(
          chapter,
          activeChapterIdx
        );
      }
      if (cancelled) {
        clearChapterOverlays();
        return;
      }

      if (!focusedByAdmin0) {
        const { center, zoom, bearing, pitch } = chapter.mapState;
        const opts = { center, zoom, bearing, pitch };

        if (chapter.transition === "jump") {
          map.jumpTo(opts);
        } else if (chapter.transition === "ease") {
          map.easeTo({ ...opts, duration: 2000 });
        } else {
          map.flyTo({ ...opts, duration: 2500, essential: true });
        }
      }

      applyChapterOverlays(chapter, activeChapterIdx);
      await applyChapterPinpoints(chapter, activeChapterIdx);
      if (cancelled) {
        clearChapterOverlays();
      }
    };

    applyChapter();

    return () => {
      cancelled = true;
    };
  }, [
    activeChapterIdx,
    chapters,
    mapReady,
    applyChapterAdmin0Focus,
    applyChapterRegionalAdmin0Focus,
    applyChapterOverlays,
    applyChapterPinpoints,
    clearChapterOverlays,
  ]);

  useEffect(
    () => () => {
      clearChapterOverlays();
    },
    [clearChapterOverlays]
  );

  const syncActiveChapterFromSidebar = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container || !chapters.length) return;

    const anchorY = container.clientHeight * 0.45;
    let nearestIdx = 0;
    let nearestDistance = Number.POSITIVE_INFINITY;

    for (let idx = 0; idx < chapters.length; idx += 1) {
      const chapterEl = document.getElementById(`mdx-chapter-${idx}`);
      if (!chapterEl) continue;

      const chapterCenterY =
        chapterEl.offsetTop - container.scrollTop + chapterEl.offsetHeight / 2;
      const distance = Math.abs(chapterCenterY - anchorY);
      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestIdx = idx;
      }
    }

    setActiveChapterIdx((prev) => (prev === nearestIdx ? prev : nearestIdx));
  }, [chapters]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return undefined;

    const onScroll = () => {
      syncActiveChapterFromSidebar();
    };

    container.addEventListener("scroll", onScroll, { passive: true });
    window.requestAnimationFrame(onScroll);

    return () => {
      container.removeEventListener("scroll", onScroll);
    };
  }, [syncActiveChapterFromSidebar]);

  const scrollToChapter = (idx) => {
    const container = scrollContainerRef.current;
    const el = document.getElementById(`mdx-chapter-${idx}`);
    if (!container || !el) return;

    const targetTop = Math.max(0, el.offsetTop - 16);
    container.scrollTo({ top: targetTop, behavior: "smooth" });
  };

  if (!chapters.length) return null;

  return (
    <div className="c-storyline-viewer">
      <div className="sv-map" ref={mapContainerRef} />

      <div className="sv-scroll-container" ref={scrollContainerRef}>
        {chapters.map((chapter, idx) => (
          <div
            key={chapter.key}
            id={`mdx-chapter-${idx}`}
            className={`sv-chapter ${
              idx === activeChapterIdx ? "sv-chapter--active" : ""
            }`}
          >
            <div className="sv-chapter__header">
              <span className="sv-chapter__number">{idx + 1}</span>
              <div>
                <h3 className="sv-chapter__title">{chapter.title}</h3>
                {chapter.dateStart && (
                  <p className="sv-chapter__dates">
                    {chapter.dateStart}
                    {chapter.dateEnd && ` — ${chapter.dateEnd}`}
                  </p>
                )}
                {chapterLocationLabels[idx] && (
                  <p className="sv-chapter__location">
                    <i className="fas fa-location-dot" aria-hidden="true" />{" "}
                    {chapterLocationLabels[idx]}
                  </p>
                )}
              </div>
            </div>

            <div className="sv-chapter__body">
              <div className="chapter-prose__mdx">{chapter.content}</div>
            </div>
          </div>
        ))}
        <div className="sv-scroll-end-spacer" aria-hidden="true" />
      </div>

      {chapters.length > 0 && (
        <div className="sv-progress">
          {chapters.map((ch, idx) => (
            <button
              key={`${ch.key}-dot`}
              className={`sv-progress__dot ${
                idx === activeChapterIdx ? "sv-progress__dot--active" : ""
              } ${idx < activeChapterIdx ? "sv-progress__dot--done" : ""}`}
              title={ch.title || `Chapter ${idx + 1}`}
              onClick={() => scrollToChapter(idx)}
            />
          ))}
        </div>
      )}

      {activeChapterIdx >= 0 && (
        <div className="sv-counter">
          {activeChapterIdx + 1} / {chapters.length}
        </div>
      )}
    </div>
  );
};

MdxScrollytellingBlock.propTypes = {
  children: PropTypes.node,
};

export default MdxScrollytellingBlock;
