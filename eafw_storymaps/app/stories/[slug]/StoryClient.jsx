'use client';

import React, { useMemo } from 'react';
import { MDXRemote } from 'next-mdx-remote';
import Link from 'next/link';
import {
  ScrollytellingBlock,
  Chapter,
  Block,
  Prose,
  Figure,
  Caption,
  Image,
  MapBlock,
  LegacyGlobalStyles,
} from '@teamimpact/veda-ui';
import datasets, { transformToVedaData } from '../../lib/datasets';

/**
 * Enhanced ScrollytellingBlock that auto-injects the datasets prop
 * so MDX authors don't need to pass it manually.
 */
function EnhancedScrollytellingBlock(props) {
  const vedaData = useMemo(() => transformToVedaData(datasets), []);
  return <ScrollytellingBlock {...props} datasets={vedaData} />;
}

/**
 * Enhanced MapBlock that auto-injects datasets prop
 * matching the pattern from eoviz-esip2025 / next-veda-ui.
 */
function EnhancedMapBlock(props) {
  const vedaData = useMemo(() => transformToVedaData(datasets), []);
  return <MapBlock {...props} datasets={vedaData} />;
}

/**
 * MDX component map — these names are available as JSX tags inside .mdx files.
 */
const mdxComponents = {
  ScrollytellingBlock: EnhancedScrollytellingBlock,
  Chapter,
  Block,
  Prose,
  Figure,
  Caption,
  Image,
  Map: EnhancedMapBlock,
  Link,
};

export default function StoryClient({ source, metadata }) {
  return (
    <article className="story-page">
      <LegacyGlobalStyles />
      {metadata.name && (
        <div
          style={{
            padding: '3rem 1.5rem 2rem',
            maxWidth: '800px',
            margin: '0 auto',
          }}
        >
          <h1>{metadata.name}</h1>
          {metadata.description && (
            <p style={{ fontSize: '1.125rem', color: '#555' }}>
              {metadata.description}
            </p>
          )}
        </div>
      )}
      <MDXRemote {...source} components={mdxComponents} />
    </article>
  );
}
