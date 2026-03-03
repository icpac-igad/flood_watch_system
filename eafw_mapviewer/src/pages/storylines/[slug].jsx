/**
 * Individual Storyline Page
 * Priority:
 * 1. Load local MDX story by slug (EOviz-style authoring).
 * 2. Fallback to API-driven storyline viewer.
 */
import React from "react";
import PageLayout from "@/wrappers/page";
import StorylineViewer from "@/components/storylines/viewer";
import MdxStorylineViewer from "@/components/storylines/mdx-viewer";

const StorylineDetailPage = ({ slug, useMdx, mdxSource, frontmatter }) => {
  return (
    <PageLayout
      title="Storyline | East Africa Flood Watch"
      description="Interactive flood event narrative"
    >
      {useMdx ? (
        <MdxStorylineViewer source={mdxSource} frontmatter={frontmatter} />
      ) : (
        <StorylineViewer slug={slug} />
      )}
    </PageLayout>
  );
};

export const getServerSideProps = async ({ params }) => {
  const rawSlug = params?.slug;
  const slug = Array.isArray(rawSlug) ? rawSlug[0] : rawSlug;

  if (!slug) {
    return { notFound: true };
  }

  try {
    const fs = require("fs/promises");
    const path = require("path");
    const matter = require("gray-matter");
    const { serialize } = await import("next-mdx-remote/serialize");

    const storiesDir = path.join(process.cwd(), "src", "content", "stories");
    const mdxPath = path.join(storiesDir, `${slug}.mdx`);

    const rawMdx = await fs.readFile(mdxPath, "utf8");
    const { data, content } = matter(rawMdx);
    const mdxSource = await serialize(content);

    return {
      props: {
        slug,
        useMdx: true,
        mdxSource,
        frontmatter: JSON.parse(JSON.stringify(data || {})),
      },
    };
  } catch (error) {
    if (error?.code !== "ENOENT") {
      console.error("Failed to load storyline MDX file", error);
    }

    return {
      props: {
        slug,
        useMdx: false,
        mdxSource: null,
        frontmatter: null,
      },
    };
  }
};

export default StorylineDetailPage;
