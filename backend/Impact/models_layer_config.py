from django.db import models


class MapLayerConfig(models.Model):
    """
    Simple layer configuration - just metadata for external WMS/tile layers
    No MapServer, no complexity - just admin-managed URLs
    """
    
    CATEGORY_CHOICES = [
        ('hazard', 'Flood Hazard'),
        ('boundary', 'Boundary'),
        ('monitoring', 'Monitoring'),
    ]
    
    # Basic info
    name = models.CharField(max_length=200, help_text="Layer display name")
    technical_name = models.CharField(max_length=200, unique=True, help_text="Unique identifier")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='hazard')
    
    # External URL (WMS, tile server, etc.)
    external_url = models.URLField(max_length=500, help_text="External WMS/tile server URL")
    layer_names = models.CharField(max_length=500, blank=True, help_text="Comma-separated layer names")
    
    # Display settings
    enabled = models.BooleanField(default=True, help_text="Show in map")
    default_visible = models.BooleanField(default=False, help_text="Visible on load")
    display_order = models.IntegerField(default=0, help_text="Sort order")
    
    class Meta:
        ordering = ['category', 'display_order', 'name']
        verbose_name = "Map Layer"
        verbose_name_plural = "Map Layers"
    
    def __str__(self):
        status = "✓" if self.enabled else "✗"
        return f"{status} {self.name}"
