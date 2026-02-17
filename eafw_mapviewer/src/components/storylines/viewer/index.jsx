import React, { useEffect, useState, useRef, useCallback } from "react";
import { Scrollama, Step } from "react-scrollama";
import maplibregl from "maplibre-gl";
import { FASTAPI_API } from "@/utils/constants";
import "./styles.scss";

const DEFAULT_CENTER = [40.5, 5.0];
const DEFAULT_ZOOM = 4;

const formatNumber = (num) => {
  if (!num) return null;
  return num.toLocaleString();
};

/* ── Main Viewer ── */
const StorylineViewer = ({ slug }) => {
  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeChapterIdx, setActiveChapterIdx] = useState(-1);
  const [mapReady, setMapReady] = useState(false);
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);

  // Fetch storyline
  useEffect(() => {
    const fetchStory = async () => {
      try {
        const res = await fetch(`${FASTAPI_API}/storylines/${slug}`);
        if (!res.ok) throw new Error(`Storyline not found (${res.status})`);
        setStory(await res.json());
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    if (slug) fetchStory();
  }, [slug]);

  // Initialize map — dark basemap
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      attributionControl: false,
    });

    map.addControl(
      new maplibregl.NavigationControl({ showCompass: true }),
      "bottom-right"
    );
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-left"
    );

    map.on("load", () => setMapReady(true));
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Fly to chapter
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !story?.chapters) return;

    const chapter = story.chapters[activeChapterIdx];
    if (!chapter?.map_state) return;

    const { center, zoom, bearing, pitch } = chapter.map_state;
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
  }, [activeChapterIdx, story, mapReady]);

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
            {story.region && (
              <span className="sv-hero__region">{story.region}</span>
            )}
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

                  {/* Media */}
                  {chapter.media?.length > 0 && (
                    <div className="sv-chapter__media">
                      {chapter.media.map((m, mi) => {
                        if (m.type === "image" && m.value) {
                          const src =
                            typeof m.value === "string"
                              ? `/media/${m.value}`
                              : m.value.url || `/media/${m.value}`;
                          return (
                            <img
                              key={mi}
                              src={src}
                              alt={chapter.title}
                              className="sv-chapter__img"
                            />
                          );
                        }
                        if (m.type === "external_image" && m.value) {
                          return (
                            <figure key={mi}>
                              <img
                                src={m.value.url}
                                alt={m.value.alt || chapter.title}
                                className="sv-chapter__img"
                              />
                              {m.value.caption && (
                                <figcaption>{m.value.caption}</figcaption>
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
                      <summary>
                        References ({chapter.references.length})
                      </summary>
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
