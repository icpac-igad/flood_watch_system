'use client';

import React from 'react';
import {
  DevseedUiThemeProvider,
  VedaUIProvider,
  ReactQueryProvider,
} from '@teamimpact/veda-ui';
import { createUITheme } from '@devseed-ui/theme-provider';
import Link from 'next/link';

const FLOODWATCH_THEME = {
  zIndices: {
    hide: -1,
    docked: 10,
    sticky: 900,
    dropdown: 1550,
    overlay: 1300,
    modal: 1400,
    popover: 1500,
    skipLink: 1600,
    toast: 1700,
    tooltip: 1800,
  },
  color: {
    base: '#2c3e50',
    primary: '#1a73a7',
    link: '#1a5276',
    danger: '#e74c3c',
    infographicA: '#f39c12',
    infographicB: '#e74c3c',
    infographicC: '#8e44ad',
    infographicD: '#27ae60',
    infographicE: '#2980b9',
  },
  type: {
    base: {
      leadSize: '1.25rem',
      extrabold: '800',
      line: 'inherit',
      sizeIncrement: {
        small: '0rem',
        medium: '0rem',
        large: '0.25rem',
        xlarge: '0.25rem',
      },
    },
    heading: {
      settings: '"wdth" 100, "wght" 700',
    },
  },
  layout: {
    min: '384px',
    max: '1440px',
    glspMultiplier: {
      xsmall: 1,
      small: 1,
      medium: 1.5,
      large: 2,
      xlarge: 2,
    },
  },
};

export default function Providers({ children }) {
  return (
    <DevseedUiThemeProvider theme={createUITheme(FLOODWATCH_THEME)}>
      <VedaUIProvider
        config={{
          envMapboxToken: '',
          envApiStacEndpoint:
            process.env.NEXT_PUBLIC_STAC_API || '/stac-browser/api',
          envApiRasterEndpoint:
            process.env.NEXT_PUBLIC_RASTER_API || '/cog-tiles',
          navigation: {
            LinkComponent: Link,
            linkProps: {
              pathAttributeKeyName: 'href',
            },
          },
        }}
      >
        <ReactQueryProvider>{children}</ReactQueryProvider>
      </VedaUIProvider>
    </DevseedUiThemeProvider>
  );
}
