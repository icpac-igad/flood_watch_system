import { notFound } from 'next/navigation';
import { serialize } from 'next-mdx-remote/serialize';
import { getStoryBySlug, getAllStories } from '../../lib/mdx-utils';
import nextDynamic from 'next/dynamic';

// Dynamic import with SSR disabled — VEDA UI components use browser globals
const StoryClient = nextDynamic(() => import('./StoryClient'), { ssr: false });

export const dynamic = 'force-dynamic';

export async function generateStaticParams() {
  const stories = getAllStories();
  return stories.map((s) => ({ slug: s.slug }));
}

export async function generateMetadata({ params }) {
  const story = getStoryBySlug(params.slug);
  if (!story) return {};
  return {
    title: story.metadata.name || story.slug,
    description: story.metadata.description || '',
  };
}

export default async function StoryPage({ params }) {
  const story = getStoryBySlug(params.slug);
  if (!story) notFound();

  const mdxSource = await serialize(story.content, {
    parseFrontmatter: false,
  });

  return <StoryClient source={mdxSource} metadata={story.metadata} />;
}
