# Interactive API Reference

Explore the FloodWatch API using the interactive Swagger UI below.

## Live Swagger UI

<div id="swagger-ui"></div>

<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
SwaggerUIBundle({
    url: "https://floodwatch.icpac.net/api/openapi.json",
    dom_id: '#swagger-ui',
    presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIBundle.SwaggerUIStandalonePreset
    ],
    layout: "BaseLayout",
    deepLinking: true,
    defaultModelsExpandDepth: -1,
    docExpansion: "list"
})
</script>

!!! note "Local Development"
    If running locally, the OpenAPI spec is available at:

    - Swagger UI: [http://127.0.0.1:9068/api/docs](http://127.0.0.1:9068/api/docs)
    - ReDoc: [http://127.0.0.1:9068/api/redoc](http://127.0.0.1:9068/api/redoc)
    - OpenAPI JSON: [http://127.0.0.1:9068/api/openapi.json](http://127.0.0.1:9068/api/openapi.json)
