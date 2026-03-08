import Link from 'next/link';
import { getAllStories } from './lib/mdx-utils';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'FloodWatch Storymaps',
  description:
    'Interactive data stories about flood risk in the Greater Horn of Africa.',
};

export default function StorymapsHub() {
  const stories = getAllStories();

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', padding: '2rem 1.5rem' }}>
      <h1>Storymaps</h1>
      <p style={{ color: '#555', marginBottom: '2rem' }}>
        Interactive data stories exploring flood risk, weather patterns, and
        population exposure across the Greater Horn of Africa.
      </p>

      {stories.length === 0 ? (
        <p>No stories available yet.</p>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1.5rem',
          }}
        >
          {stories.map((story) => (
            <Link
              key={story.slug}
              href={`/stories/${story.slug}`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <div
                style={{
                  border: '1px solid #ddd',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  transition: 'box-shadow 0.2s',
                }}
              >
                {story.metadata.media?.src && (
                  <img
                    src={story.metadata.media.src}
                    alt={story.metadata.media.alt || story.metadata.name}
                    style={{
                      width: '100%',
                      height: '180px',
                      objectFit: 'cover',
                    }}
                  />
                )}
                <div style={{ padding: '1rem' }}>
                  <h3 style={{ margin: '0 0 0.5rem' }}>
                    {story.metadata.name || story.slug}
                  </h3>
                  {story.metadata.description && (
                    <p
                      style={{
                        color: '#666',
                        fontSize: '0.875rem',
                        margin: 0,
                        lineHeight: 1.5,
                      }}
                    >
                      {story.metadata.description}
                    </p>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
