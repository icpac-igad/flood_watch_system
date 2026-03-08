import React from 'react';
import './globals.scss';
import dynamic from 'next/dynamic';

const Providers = dynamic(() => import('./providers'), { ssr: false });

export const metadata = {
  title: 'FloodWatch Storymaps',
  description:
    'Interactive data stories about flood risk in the Greater Horn of Africa.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/maplibre-gl@4.5.0/dist/maplibre-gl.css"
        />
      </head>
      <body>
        <Providers>
          <div
            style={{
              minHeight: '100vh',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <header
              style={{
                background: '#1a73a7',
                color: '#fff',
                padding: '0.75rem 1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <a
                href="/storymaps"
                style={{ color: '#fff', textDecoration: 'none' }}
              >
                <strong>FloodWatch Storymaps</strong>
              </a>
              <a
                href="/"
                style={{
                  color: '#fff',
                  textDecoration: 'none',
                  fontSize: '0.875rem',
                }}
              >
                Back to FloodWatch
              </a>
            </header>
            <main style={{ flex: 1 }}>{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
