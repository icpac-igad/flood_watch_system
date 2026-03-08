import React from "react";
import PropTypes from "prop-types";
import Link from "next/link";
import { MDXRemote } from "next-mdx-remote";
import MdxScrollytellingBlock, {
  Chapter,
} from "@/components/storylines/mdx-scrollytelling";
import "./styles.scss";

const ExternalLink = ({ href, children, ...props }) => {
  const isExternal = typeof href === "string" && /^https?:\/\//.test(href);

  if (isExternal) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
        {children}
      </a>
    );
  }

  return (
    <Link href={href || "#"} {...props}>
      {children}
    </Link>
  );
};

ExternalLink.propTypes = {
  href: PropTypes.string,
  children: PropTypes.node,
};

const MdxVideo = ({ src, title }) => (
  <div className="c-story-mdx-video">
    <iframe
      src={src}
      title={title || "Storyline video"}
      loading="lazy"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      referrerPolicy="strict-origin-when-cross-origin"
      allowFullScreen
    />
  </div>
);

MdxVideo.propTypes = {
  src: PropTypes.string.isRequired,
  title: PropTypes.string,
};

const formatMetricValue = (value) => {
  const num = Number(value);
  if (!Number.isFinite(num) || num <= 0) return null;
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(num);
};

const MdxStorylineViewer = ({ source, frontmatter }) => {
  const title = frontmatter?.title || frontmatter?.name || "Flood Storyline";
  const description = frontmatter?.description || "";
  const region = frontmatter?.region || "East Africa";
  const eventStart = frontmatter?.event_start || frontmatter?.eventStart;
  const eventEnd = frontmatter?.event_end || frontmatter?.eventEnd;
  const coverImage =
    frontmatter?.cover_image || frontmatter?.coverImage || frontmatter?.media?.src;
  const totalAffected =
    frontmatter?.total_affected || frontmatter?.totalAffected || null;
  const totalDisplaced =
    frontmatter?.total_displaced || frontmatter?.totalDisplaced || null;
  const totalDeaths = frontmatter?.total_deaths || frontmatter?.totalDeaths || null;
  const countryCount = Array.isArray(frontmatter?.country_events)
    ? frontmatter.country_events.length
    : Array.isArray(frontmatter?.countries)
      ? frontmatter.countries.length
      : null;

  const metrics = [
    { label: "Countries", value: countryCount },
    { label: "Affected", value: formatMetricValue(totalAffected) },
    { label: "Displaced", value: formatMetricValue(totalDisplaced) },
    { label: "Deaths", value: formatMetricValue(totalDeaths) },
  ].filter((item) => item.value !== null && item.value !== undefined && item.value !== "");

  const components = {
    ScrollytellingBlock: MdxScrollytellingBlock,
    Chapter,
    a: ExternalLink,
    Video: MdxVideo,
  };

  return (
    <div className="c-story-mdx-viewer">
      <header className="story-mdx-hero">
        {coverImage && (
          <div className="story-mdx-hero__media">
            <img src={coverImage} alt={title} />
            <div className="story-mdx-hero__media-shade" />
          </div>
        )}
        <div className="story-mdx-hero__content">
          <div className="story-mdx-hero__text">
            <span className="story-mdx-hero__region">{region}</span>
            <h1>{title}</h1>
            {(eventStart || eventEnd) && (
              <p className="story-mdx-hero__period">
                {eventStart || ""}
                {eventStart && eventEnd ? " — " : ""}
                {eventEnd || ""}
              </p>
            )}
          </div>
          {metrics.length > 0 && (
            <div className="story-mdx-hero__metrics">
              {metrics.map((metric) => (
                <div className="story-mdx-hero__metric" key={metric.label}>
                  <span className="story-mdx-hero__metric-value">{metric.value}</span>
                  <span className="story-mdx-hero__metric-label">{metric.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </header>

      <article className="story-mdx-content">
        <MDXRemote {...source} components={components} />
      </article>
    </div>
  );
};

MdxStorylineViewer.propTypes = {
  source: PropTypes.object.isRequired,
  frontmatter: PropTypes.object,
};

export default MdxStorylineViewer;
