import React, { useEffect, useState } from "react";
import Link from "next/link";
import { FASTAPI_API } from "@/utils/constants";
import "./styles.scss";

const formatNumber = (num) => {
  if (!num) return "N/A";
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
  return num.toLocaleString();
};

const StoryCard = ({ story }) => {
  const {
    slug, title, description, event_start, event_end,
    region, total_affected, total_displaced, total_deaths,
    cover_image, country_events,
  } = story;

  return (
    <Link href={`/storylines/${slug}/`} className="story-card">
      <div className="story-card__visual">
        {cover_image ? (
          <img src={cover_image} alt={title} />
        ) : (
          <div className="story-card__placeholder">
            <i className="fas fa-water" />
          </div>
        )}
        <div className="story-card__overlay" />
        <span className="story-card__region">{region}</span>
      </div>
      <div className="story-card__content">
        <h3 className="story-card__title">{title}</h3>
        <p className="story-card__period">
          {event_start} &mdash; {event_end}
        </p>
        <p className="story-card__description">{description}</p>
        {country_events?.length > 0 && (
          <div className="story-card__countries">
            {country_events.map((e, i) => (
              <span key={i} className="story-card__chip">{e.country}</span>
            ))}
          </div>
        )}
        <div className="story-card__stats">
          {total_affected && (
            <div className="story-card__stat">
              <span className="story-card__stat-value">{formatNumber(total_affected)}</span>
              <span className="story-card__stat-label">Affected</span>
            </div>
          )}
          {total_displaced && (
            <div className="story-card__stat">
              <span className="story-card__stat-value">{formatNumber(total_displaced)}</span>
              <span className="story-card__stat-label">Displaced</span>
            </div>
          )}
          {total_deaths && (
            <div className="story-card__stat">
              <span className="story-card__stat-value">{formatNumber(total_deaths)}</span>
              <span className="story-card__stat-label">Deaths</span>
            </div>
          )}
        </div>
        <div className="story-card__cta">
          <span>Explore Story</span>
          <i className="fas fa-arrow-right" />
        </div>
      </div>
    </Link>
  );
};

const StorylinesHub = () => {
  const [storylines, setStorylines] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStorylines = async () => {
      try {
        const res = await fetch(`${FASTAPI_API}/storylines/`);
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        const data = await res.json();
        setStorylines(data.storylines || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchStorylines();
  }, []);

  return (
    <div className="c-storylines-hub">
      <div className="hub-header">
        <div className="hub-header__content">
          <span className="hub-header__badge">
            <i className="fas fa-book-open" /> Storylines
          </span>
          <h1>Flood Event Narratives</h1>
          <p>
            Interactive scrollytelling narratives documenting major flood events
            across East Africa. Each story maps the timeline, causes, and
            humanitarian impact.
          </p>
        </div>
      </div>

      {loading && (
        <div className="hub-status">
          <div className="hub-status__spinner" />
          <span>Loading storylines...</span>
        </div>
      )}

      {error && (
        <div className="hub-status hub-status--error">
          <i className="fas fa-exclamation-triangle" />
          <p>Failed to load storylines: {error}</p>
        </div>
      )}

      {!loading && !error && storylines.length === 0 && (
        <div className="hub-status">
          <i className="fas fa-book-open" />
          <p>No storylines published yet. Check back soon.</p>
        </div>
      )}

      {!loading && storylines.length > 0 && (
        <div className="hub-grid">
          {storylines.map((story) => (
            <StoryCard key={story.id} story={story} />
          ))}
        </div>
      )}
    </div>
  );
};

export default StorylinesHub;
