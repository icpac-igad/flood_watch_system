/**
 * Storylines Hub Page
 * Lists MDX-authored + API-published flood event storylines
 */
import React from "react";
import PageLayout from "@/wrappers/page";
import StorylinesHub from "@/components/storylines/hub";
import MdxStorylineViewer from "@/components/storylines/mdx-viewer";

const StorylinesPage = ({ mdxStorylines, featuredStorySource, featuredStoryFrontmatter }) => {
  const featuredTitle =
    featuredStoryFrontmatter?.title || featuredStoryFrontmatter?.name || "Flood Event Storylines";
  const featuredDescription =
    featuredStoryFrontmatter?.description ||
    "Interactive narratives documenting major flood events across East Africa";

  return (
    <PageLayout
      title={`${featuredTitle} | East Africa Flood Watch`}
      description={featuredDescription}
    >
      {featuredStorySource ? (
        <MdxStorylineViewer
          source={featuredStorySource}
          frontmatter={featuredStoryFrontmatter}
        />
      ) : (
        <StorylinesHub initialStorylines={mdxStorylines} />
      )}
    </PageLayout>
  );
};

export const getServerSideProps = async () => {
  try {
    const fs = require("fs/promises");
    const path = require("path");
    const matter = require("gray-matter");
    const { serialize } = await import("next-mdx-remote/serialize");

    const storiesDir = path.join(process.cwd(), "src", "content", "stories");
    const files = await fs.readdir(storiesDir);
    const mdxFiles = files.filter((file) => file.endsWith(".mdx"));

    const mdxEntries = await Promise.all(
      mdxFiles.map(async (fileName) => {
        const slug = fileName.replace(/\.mdx$/, "");
        const raw = await fs.readFile(path.join(storiesDir, fileName), "utf8");
        const { data, content } = matter(raw);

        const countries = Array.isArray(data?.country_events)
          ? data.country_events
          : Array.isArray(data?.countries)
            ? data.countries.map((country) => ({ country }))
            : [];

        return {
          slug,
          frontmatter: data || {},
          content,
          card: {
            id: `mdx-${slug}`,
            slug,
            title: data?.title || data?.name || slug,
            description: data?.description || "",
            event_start: data?.event_start || data?.eventStart || "",
            event_end: data?.event_end || data?.eventEnd || "",
            region: data?.region || "Greater Horn of Africa",
            total_affected: data?.total_affected || data?.totalAffected || null,
            total_displaced: data?.total_displaced || data?.totalDisplaced || null,
            total_deaths: data?.total_deaths || data?.totalDeaths || null,
            cover_image:
              data?.cover_image || data?.coverImage || data?.media?.src || null,
            country_events: countries,
            source: "mdx",
          },
        };
      })
    );

    const stories = mdxEntries.map((entry) => entry.card);
    const featuredEntry =
      mdxEntries.find((entry) => Boolean(entry?.frontmatter?.featured_home)) ||
      mdxEntries.find((entry) => entry.slug === "east-africa-flood-events-2019-2024") ||
      (mdxEntries.length === 1 ? mdxEntries[0] : null);

    let featuredStorySource = null;
    let featuredStoryFrontmatter = null;

    if (featuredEntry?.content) {
      featuredStorySource = await serialize(featuredEntry.content);
      featuredStoryFrontmatter = featuredEntry.frontmatter || {};
    }

    return {
      props: {
        mdxStorylines: JSON.parse(JSON.stringify(stories)),
        featuredStorySource,
        featuredStoryFrontmatter: JSON.parse(
          JSON.stringify(featuredStoryFrontmatter || null)
        ),
      },
    };
  } catch (error) {
    if (error?.code !== "ENOENT") {
      console.error("Failed to load MDX storylines for hub", error);
    }

    return {
      props: {
        mdxStorylines: [],
        featuredStorySource: null,
        featuredStoryFrontmatter: null,
      },
    };
  }
};

export default StorylinesPage;
