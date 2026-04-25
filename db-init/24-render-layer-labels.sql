-- ============================================================================
-- Align multimodal vector-tile layer render config to the tile's emitted labels.
--
-- The tile function gha.multimodal_points_alerts emits alert_level values
-- extreme / severe / moderate / normal via gha.classify_alert. Earlier the
-- layer's render_layers_json was matching on the old emergency / alarm /
-- warning vocabulary, so every point fell through to the grey fallback.
--
-- This migration rewrites any legacy labels in render_layers, render_layers_json
-- across every vector_tile layer so the match expression and the tile output
-- agree.
-- ============================================================================

UPDATE cms.geomanager_vectortilelayer
SET render_layers_json = replace(replace(replace(render_layers_json::text,
      '"emergency"', '"extreme"'),
      '"alarm"',     '"severe"'),
      '"warning"',   '"moderate"')::jsonb,
    render_layers     = replace(replace(replace(render_layers::text,
      '"emergency"', '"extreme"'),
      '"alarm"',     '"severe"'),
      '"warning"',   '"moderate"')::jsonb
WHERE render_layers_json::text ~ 'emergency|alarm|warning'
   OR render_layers::text     ~ 'emergency|alarm|warning';
