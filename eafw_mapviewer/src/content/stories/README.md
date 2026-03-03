# Storyline MDX Authoring (Reproducible)

Storylines in this folder are version-controlled and reproducible from source.

## How it works

- Hub page (`/storylines/`) auto-discovers `*.mdx` files in this folder.
- Detail page (`/storylines/<slug>/`) first tries MDX by slug.
- If no matching MDX file exists, it falls back to API/CMS storyline data.

## Create a new storyline

1. Add a file: `src/content/stories/<slug>.mdx`
2. Add frontmatter metadata and a `<ScrollytellingBlock>` with `<Chapter>` entries.
3. Optional: add chapter overlays as GeoJSON in `public/storylines/geojson/*.geojson` and reference them using `mapOverlays`.

## Minimal template

```mdx
---
title: Flood Storyline Title
description: Short description
region: Greater Horn of Africa
event_start: "2024"
event_end: "2025"
cover_image: "https://..."
---

<ScrollytellingBlock>
  <Chapter title="Chapter 1" center={[39.0, 0.0]} zoom={6}>
    Chapter prose goes here.
  </Chapter>
</ScrollytellingBlock>
```

## Available MDX components

- `ScrollytellingBlock`
- `Chapter`
- `Video` (iframe wrapper)

`Chapter` useful props:

- `title`
- `dateStart` / `dateEnd`
- `center` (required map center array: `[lng, lat]`)
- `zoom`
- `transition` (`fly`, `ease`, `jump`)
- `mapOverlays` (array of GeoJSON overlay objects)
