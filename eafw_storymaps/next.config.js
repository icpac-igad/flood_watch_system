const path = require('path');

/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath: '/storymaps',
  reactStrictMode: false,
  compiler: {
    styledComponents: true,
  },
  // Transpile VEDA UI and devseed packages
  transpilePackages: [
    '@teamimpact/veda-ui',
    '@devseed-ui/theme-provider',
  ],
  sassOptions: {
    includePaths: [
      path.join(__dirname, 'node_modules', '@uswds', 'uswds', 'packages'),
    ],
  },
  webpack: (config, { isServer }) => {
    // Jotai singleton — prevent VEDA UI from bundling its own copy
    config.resolve.alias['jotai'] = path.resolve(__dirname, 'node_modules', 'jotai');

    // Mapbox GL → MapLibre GL swap (avoids Mapbox token requirement)
    // Uses a shim package that re-exports maplibre-gl and its CSS
    config.resolve.alias['mapbox-gl'] = path.resolve(__dirname, 'shims', 'mapbox-gl');

    return config;
  },
};

module.exports = nextConfig;
