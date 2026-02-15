/** @type {import('next').NextConfig} */
const path = require("path");
const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
});

const nextConfig = {
  // disable css-modules component styling
  webpack(config) {
    config.module.rules.forEach((rule) => {
      const { oneOf } = rule;
      if (oneOf) {
        oneOf.forEach((one) => {
          if (!`${one.issuer?.and}`.includes("_app")) return;
          one.issuer.and = [path.resolve(__dirname)];
        });
      }
    });

    // SVG sprite loader for ?sprite imports
    config.module.rules.push({
      test: /\.svg$/,
      resourceQuery: /sprite/,
      use: [
        {
          loader: "svg-sprite-loader",
          options: { extract: false },
        },
      ],
    });

    // Regular SVG imports (without ?sprite) as asset URLs
    config.module.rules.push({
      test: /\.svg$/,
      resourceQuery: { not: [/sprite/] },
      type: "asset/resource",
    });

    // Image imports (PNG, JPG, GIF, WebP, etc.) as asset URLs
    config.module.rules.push({
      test: /\.(png|jpe?g|gif|webp|ico|bmp)$/i,
      type: "asset/resource",
    });

    config.resolve.alias = {
      ...config.resolve.alias,
      "mapbox-gl": "maplibre-gl",
    };

    config.infrastructureLogging = { level: "error" };

    config.resolve.fallback = { fs: false };

    return config;
  },
  images: {
    disableStaticImages: true,
    unoptimized: true,
  },
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    ignoreDuringBuilds: true,
  },
  experimental: {
    esmExternals: 'loose',
  },
  trailingSlash: true,
  basePath: process.env.BASE_URL_PATH ? process.env.BASE_URL_PATH : undefined,
  assetPrefix: process.env.ASSET_PREFIX ? process.env.ASSET_PREFIX : undefined,
  env: {
    DEBUG: process.env.DEBUG,
    FEATURE_ENV: process.env.FEATURE_ENV,
    CMS_API: process.env.CMS_API,
    ADMIN_BOUNDARY_API: process.env.ADMIN_BOUNDARY_API,
    ANALYTICS_PROPERTY_ID: process.env.ANALYTICS_PROPERTY_ID,
    BITLY_TOKEN: process.env.BITLY_TOKEN,
    GOOGLE_CUSTOM_SEARCH_CX: process.env.GOOGLE_CUSTOM_SEARCH_CX,
    GOOGLE_SEARCH_API_KEY: process.env.GOOGLE_SEARCH_API_KEY,
    BASE_URL_PATH: process.env.BASE_URL_PATH,
    ASSET_PREFIX: process.env.ASSET_PREFIX,
  },
};

module.exports = () => {
  const plugins = [withBundleAnalyzer];
  return plugins.reduce((acc, next) => next(acc), nextConfig);
};
