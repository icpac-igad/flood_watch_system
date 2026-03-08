import React, { useEffect, useState, useRef, useCallback } from "react";
import { Scrollama, Step } from "react-scrollama";
import maplibregl from "maplibre-gl";
import { FASTAPI_API } from "@/utils/constants";
import "./styles.scss";

const DEFAULT_CENTER = [40.5, 5.0];
const DEFAULT_ZOOM = 4;
const OVERLAY_SOURCE_PREFIX = "storyline-overlay-src";
const OVERLAY_LAYER_PREFIX = "storyline-overlay-lyr";

// Fallback when mapviewer-config is unavailable.
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

const formatNumber = (num) => {
  if (!num) return null;
  return num.toLocaleString();
};

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

const toMediaSrc = (value) => {
  if (!value) return null;
  if (typeof value === "string") {
    if (
      value.startsWith("http://") ||
      value.startsWith("https://") ||
      value.startsWith("/")
    ) {
      return value;
    }
    return `/media/${value}`;
  }
  if (typeof value === "object") {
    if (value.url) return value.url;
    if (value.src) return value.src;
  }
  return null;
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

/* ── Main Viewer ── */
const StorylineViewer = ({ slug }) => {
  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeChapterIdx, setActiveChapterIdx] = useState(0);
  const [mapReady, setMapReady] = useState(false);
  const [basemapConfig, setBasemapConfig] = useState(null);
  const [basemapResolved, setBasemapResolved] = useState(false);

  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const activeOverlayRefs = useRef([]);

  const clearChapterOverlays = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;

    for (let i = activeOverlayRefs.current.length - 1; i >= 0; i -= 1) {
      const { layerId, sourceId } = activeOverlayRefs.current[i];
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
    }

    activeOverlayRefs.current = [];
  }, []);

  // Fetch storyline and current mapviewer basemap configuration.
  useEffect(() => {
    let cancelled = false;

    const fetchStory = async () => {
      setLoading(true);
      setError(null);
      setBasemapResolved(false);

      try {
        const storylineRes = await fetch(`${FASTAPI_API}/storylines/${slug}`);
        if (!storylineRes.ok) {
          throw new Error(`Storyline not found (${storylineRes.status})`);
        }
        const storylineData = await storylineRes.json();

        let resolvedBasemap = null;
        try {
          const mapConfigRes = await fetch(`${FASTAPI_API}/mapviewer-config`);
          if (mapConfigRes.ok) {
            const mapConfigData = await mapConfigRes.json();
            resolvedBasemap = extractBasemapConfig(mapConfigData);
          }
        } catch (mapConfigErr) {
          // Keep storyline functional with fallback style.
          console.warn("Failed to fetch mapviewer basemap config", mapConfigErr);
        }

        if (cancelled) return;
        setStory(storylineData);
        setActiveChapterIdx(0);
        setBasemapConfig(resolvedBasemap);
      } catch (err) {
        if (cancelled) return;
        setError(err.message);
      } finally {
        if (!cancelled) {
          setLoading(false);
          setBasemapResolved(true);
        }
      }
    };

    if (slug) fetchStory();

    return () => {
      cancelled = true;
    };
  }, [slug]);

  // Initialize map after basemap config resolution.
  useEffect(() => {
    if (!basemapResolved || !mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
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

    return () => {
      clearChapterOverlays();
      map.remove();
      mapRef.current = null;
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
    if (!mapReady || !mapRef.current) return;
    applyBasemapGroupVisibility(mapRef.current, basemapConfig);
  }, [mapReady, basemapConfig]);

  const applyChapterOverlays = useCallback(
    (chapter, chapterIdx) => {
      const map = mapRef.current;
      if (!map) return;

      clearChapterOverlays();
      const overlays = Array.isArray(chapter?.map_overlays)
        ? chapter.map_overlays
        : [];
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
          // Keep the chapter usable if one overlay URL fails.
          console.error("Failed to add storyline map overlay", err);
        }
      });
    },
    [clearChapterOverlays]
  );

  // Fly to chapter and load chapter overlays.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !story?.chapters) return;

    const chapter = story.chapters[activeChapterIdx];
    if (!chapter) {
      clearChapterOverlays();
      return;
    }

    const center =
      toCenterCoordinate(chapter?.map_state?.center) ||
      toCenterCoordinate(chapter?.central_point) ||
      toCenterCoordinate(chapter?.centralPoint);

    if (center) {
      const { zoom, bearing, pitch } = chapter.map_state || {};
      const transition = chapter.transition || "fly";
      const opts = {
        center,
        zoom: zoom || DEFAULT_ZOOM,
        bearing: bearing || 0,
        pitch: pitch || 0,
      };

      if (transition === "jump") map.jumpTo(opts);
      else if (transition === "ease") map.easeTo({ ...opts, duration: 2000 });
      else map.flyTo({ ...opts, duration: 2500, essential: true });
    }

    applyChapterOverlays(chapter, activeChapterIdx);
  }, [
    activeChapterIdx,
    story,
    mapReady,
    applyChapterOverlays,
    clearChapterOverlays,
  ]);

  useEffect(
    () => () => {
      clearChapterOverlays();
    },
    [clearChapterOverlays]
  );

  const onStepEnter = useCallback(({ data }) => {
    setActiveChapterIdx(data);
  }, []);

  const scrollToChapter = (idx) => {
    const el = document.getElementById(`chapter-${idx}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  if (loading) {
    return (
      <div className="c-storyline-viewer">
        <div className="sv-loading">
          <div className="sv-loading__spinner" />
          <span>Loading storyline...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="c-storyline-viewer">
        <div className="sv-error">
          <i className="fas fa-exclamation-triangle" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!story) return null;

  const chapters = story.chapters || [];

  return (
    <div className="c-storyline-viewer">
      {/* Full-bleed map */}
      <div className="sv-map" ref={mapContainerRef} />

      {/* Scroll overlay */}
      <div className="sv-scroll-container">
        {/* Hero card */}
        <div className="sv-hero">
          <div className="sv-hero__card">
            {story.region && <span className="sv-hero__region">{story.region}</span>}
            <h1 className="sv-hero__title">{story.title}</h1>
            <p className="sv-hero__period">
              {story.event_start} &mdash; {story.event_end}
            </p>
            <p className="sv-hero__description">{story.description}</p>

            {/* Key stats */}
            <div className="sv-hero__stats">
              {story.total_affected && (
                <div className="sv-stat">
                  <span className="sv-stat__value">
                    {formatNumber(story.total_affected)}
                  </span>
                  <span className="sv-stat__label">People Affected</span>
                </div>
              )}
              {story.total_displaced && (
                <div className="sv-stat">
                  <span className="sv-stat__value">
                    {formatNumber(story.total_displaced)}
                  </span>
                  <span className="sv-stat__label">Displaced</span>
                </div>
              )}
              {story.total_deaths && (
                <div className="sv-stat">
                  <span className="sv-stat__value">
                    {formatNumber(story.total_deaths)}
                  </span>
                  <span className="sv-stat__label">Deaths</span>
                </div>
              )}
            </div>

            {/* Country chips */}
            {story.country_events?.length > 0 && (
              <div className="sv-hero__countries">
                {story.country_events.map((evt, i) => (
                  <span key={i} className="sv-hero__chip">
                    {evt.country}
                  </span>
                ))}
              </div>
            )}

            <div className="sv-hero__scroll-cta">
              <i className="fas fa-chevron-down" />
              <span>Scroll to explore the story</span>
            </div>
          </div>
        </div>

        {/* Chapter cards */}
        <Scrollama offset={0.45} onStepEnter={onStepEnter}>
          {chapters.map((chapter, idx) => (
            <Step key={chapter.id || idx} data={idx}>
              <div
                id={`chapter-${idx}`}
                className={`sv-chapter ${
                  idx === activeChapterIdx ? "sv-chapter--active" : ""
                }`}
              >
                <div className="sv-chapter__header">
                  <span className="sv-chapter__number">{idx + 1}</span>
                  <div>
                    <h3 className="sv-chapter__title">{chapter.title}</h3>
                    {chapter.date_start && (
                      <p className="sv-chapter__dates">
                        {chapter.date_start}
                        {chapter.date_end && ` — ${chapter.date_end}`}
                      </p>
                    )}
                  </div>
                </div>

                <div className="sv-chapter__body">
                  <div
                    className="chapter-prose__html"
                    dangerouslySetInnerHTML={{ __html: chapter.prose }}
                  />

                  {chapter.map_overlays?.length > 0 && (
                    <div className="sv-chapter__overlays">
                      {chapter.map_overlays.map((overlay, oi) => (
                        <span
                          key={`${chapter.id || idx}-overlay-${oi}`}
                          className="sv-overlay-chip"
                        >
                          {overlay.label || `Flood Layer ${oi + 1}`}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Media */}
                  {chapter.media?.length > 0 && (
                    <div className="sv-chapter__media">
                      {chapter.media.map((m, mi) => {
                        if (m.type === "image" && m.value) {
                          const src = toMediaSrc(m.value);
                          if (!src) return null;
                          return (
                            <img
                              key={mi}
                              src={src}
                              alt={m.value?.alt || chapter.title}
                              className="sv-chapter__img"
                            />
                          );
                        }
                        if (m.type === "external_image" && m.value) {
                          const src = toMediaSrc(m.value.url);
                          if (!src) return null;
                          return (
                            <figure key={mi}>
                              <img
                                src={src}
                                alt={m.value.alt || chapter.title}
                                className="sv-chapter__img"
                              />
                              {m.value.caption && (
                                <figcaption>{m.value.caption}</figcaption>
                              )}
                            </figure>
                          );
                        }
                        if (
                          (m.type === "external_video" ||
                            m.type === "uploaded_video") &&
                          m.value
                        ) {
                          const src = toMediaSrc(m.value.url);
                          if (!src) return null;
                          return (
                            <figure key={mi} className="sv-chapter__video-wrap">
                              <video
                                className="sv-chapter__video"
                                src={src}
                                controls
                                playsInline
                                poster={m.value.poster_url || undefined}
                                autoPlay={Boolean(m.value.autoplay)}
                                muted={m.value.muted !== false}
                                loop={Boolean(m.value.loop)}
                              />
                              {(m.value.caption || m.value.title) && (
                                <figcaption>
                                  {m.value.caption || m.value.title}
                                </figcaption>
                              )}
                            </figure>
                          );
                        }
                        if (m.type === "embed" && m.value) {
                          return (
                            <iframe
                              key={mi}
                              src={m.value.url}
                              title={m.value.title || "Embed"}
                              height={m.value.height || 400}
                              className="sv-chapter__embed"
                              loading="lazy"
                              allowFullScreen
                            />
                          );
                        }
                        return null;
                      })}
                    </div>
                  )}

                  {/* References */}
                  {chapter.references?.length > 0 && (
                    <details className="sv-chapter__refs">
                      <summary>References ({chapter.references.length})</summary>
                      <ul>
                        {chapter.references.map((ref, ri) => (
                          <li key={ri}>
                            <a
                              href={ref.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {ref.title || ref.url}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              </div>
            </Step>
          ))}
        </Scrollama>

        {/* End card */}
        <div className="sv-end">
          <div className="sv-end__card">
            <i className="fas fa-flag-checkered" />
            <h3>End of Story</h3>
            <p>
              This storyline covered {chapters.length} chapters across{" "}
              {story.country_events?.length || 0} countries.
            </p>
            <a href="/storylines/" className="sv-end__back">
              <i className="fas fa-arrow-left" /> Back to all storylines
            </a>
          </div>
        </div>
      </div>

      {/* Progress dots */}
      {chapters.length > 0 && (
        <div className="sv-progress">
          {chapters.map((ch, idx) => (
            <button
              key={idx}
              className={`sv-progress__dot ${
                idx === activeChapterIdx ? "sv-progress__dot--active" : ""
              } ${idx < activeChapterIdx ? "sv-progress__dot--done" : ""}`}
              title={ch.title || `Chapter ${idx + 1}`}
              onClick={() => scrollToChapter(idx)}
            />
          ))}
        </div>
      )}

      {/* Chapter counter */}
      {activeChapterIdx >= 0 && (
        <div className="sv-counter">
          {activeChapterIdx + 1} / {chapters.length}
        </div>
      )}
    </div>
  );
};

export default StorylineViewer;
