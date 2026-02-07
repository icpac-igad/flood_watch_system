# Data migration to seed the Google Flood Inundation History layer
# Adds the layer to the Climate Information category in the CMS

from django.db import migrations
import uuid


def seed_inundation_layer(apps, schema_editor):
    """
    Create the Flood Inundation History dataset and layer in the CMS.
    """
    Category = apps.get_model('geomanager', 'Category')
    SubCategory = apps.get_model('geomanager', 'SubCategory')
    Dataset = apps.get_model('geomanager', 'Dataset')
    VectorTileLayer = apps.get_model('geomanager', 'VectorTileLayer')
    Metadata = apps.get_model('geomanager', 'Metadata')

    # Find or create the Climate Information category
    climate_category, created = Category.objects.get_or_create(
        title='Climate',
        defaults={
            'icon': 'climate',
            'active': True,
            'public': True,
        }
    )

    # Find or create a sub-category for Flood data
    flood_subcategory, created = SubCategory.objects.get_or_create(
        category=climate_category,
        title='Flood History',
        defaults={
            'active': True,
            'public': True,
        }
    )

    # Create metadata for the dataset
    metadata = Metadata.objects.create(
        id=uuid.uuid4(),
        title='Flood Inundation History (1999-2020)',
        subtitle='Google Floods Historical Data',
        function='Shows areas historically prone to flooding based on 21 years of satellite imagery',
        resolution='128 meters',
        geographic_coverage='Greater Horn of Africa',
        source='Google Floods Team / GLAD Dataset',
        license='CC-BY-4.0',
        frequency_of_update='Static (historical data)',
        overview='''
<p>This dataset provides historical flood inundation areas derived from satellite imagery
between 1999 and 2020. It shows how often each 128-meter pixel has been wet during this period.</p>

<p><strong>Risk Levels:</strong></p>
<ul>
<li><strong>High Risk:</strong> Areas wet at least 5% of the time</li>
<li><strong>Medium Risk:</strong> Areas wet at least 1% of the time</li>
<li><strong>Low Risk:</strong> Areas wet at least 0.5% of the time</li>
</ul>

<p>Constant water bodies have been removed from the dataset. Areas not covered by any
polygons were wet less than 0.5% of the time during the observation period.</p>
''',
        cautions='This is historical data (1999-2020) and may not reflect current conditions or future flood risk. Land use changes and climate variability can affect flood patterns.',
        citation='Google Floods Team. Flood Inundation History Dataset based on GLAD satellite imagery (1999-2020).',
        learn_more='https://console.cloud.google.com/storage/browser/flood-forecasting/inundation_history',
    )

    # Create the dataset
    dataset_id = uuid.uuid4()
    dataset = Dataset.objects.create(
        id=dataset_id,
        title='Flood Inundation History',
        category=climate_category,
        sub_category=flood_subcategory,
        summary='Historical flood-prone areas from satellite imagery (1999-2020)',
        metadata=metadata,
        layer_type='vector_tile',
        dataset_slug='flood-inundation-history',
        published=True,
        public=True,
        initial_visible=False,
        multi_temporal=False,
        multi_layer=False,
        near_realtime=False,
        current_time_method='latest_from_source',
        can_clip=True,
    )

    # Render layers configuration for the vector tile
    render_layers_json = [
        # High Risk - Red
        {
            "type": "fill",
            "source-layer": "climate.inundation_history_clipped",
            "filter": ["==", ["get", "risk_level"], "High_risk"],
            "paint": {
                "fill-color": "#d72f2a",
                "fill-opacity": 0.7
            }
        },
        {
            "type": "line",
            "source-layer": "climate.inundation_history_clipped",
            "filter": ["==", ["get", "risk_level"], "High_risk"],
            "paint": {
                "line-color": "#a82420",
                "line-width": 0.5
            }
        },
        # Medium Risk - Orange
        {
            "type": "fill",
            "source-layer": "climate.inundation_history_clipped",
            "filter": ["==", ["get", "risk_level"], "Medium_risk"],
            "paint": {
                "fill-color": "#fe9900",
                "fill-opacity": 0.6
            }
        },
        {
            "type": "line",
            "source-layer": "climate.inundation_history_clipped",
            "filter": ["==", ["get", "risk_level"], "Medium_risk"],
            "paint": {
                "line-color": "#cc7a00",
                "line-width": 0.5
            }
        },
        # Low Risk - Yellow
        {
            "type": "fill",
            "source-layer": "climate.inundation_history_clipped",
            "filter": ["==", ["get", "risk_level"], "Low_risk"],
            "paint": {
                "fill-color": "#ffff00",
                "fill-opacity": 0.5
            }
        },
        {
            "type": "line",
            "source-layer": "climate.inundation_history_clipped",
            "filter": ["==", ["get", "risk_level"], "Low_risk"],
            "paint": {
                "line-color": "#cccc00",
                "line-width": 0.5
            }
        },
    ]

    # Legend configuration
    legend_config = [
        {
            "type": "legend",
            "value": {
                "type": "basic",
                "items": [
                    {"value": "High Risk (wet >= 5%)", "color": "#d72f2a"},
                    {"value": "Medium Risk (wet >= 1%)", "color": "#fe9900"},
                    {"value": "Low Risk (wet >= 0.5%)", "color": "#ffff00"},
                ]
            }
        }
    ]

    # Create the vector tile layer
    # Base URL points to pg_tileserv function
    VectorTileLayer.objects.create(
        id=uuid.uuid4(),
        dataset=dataset,
        title='Flood Inundation History',
        default=True,
        base_url='{TILESERV_URL}/climate.inundation_history_clipped/{z}/{x}/{y}.pbf',
        use_render_layers_json=True,
        render_layers_json=render_layers_json,
        legend=legend_config,
        get_time_from_tile_json=False,
    )

    print(f"Created Flood Inundation History dataset: {dataset_id}")


def remove_inundation_layer(apps, schema_editor):
    """
    Remove the Flood Inundation History dataset and related objects.
    """
    Dataset = apps.get_model('geomanager', 'Dataset')
    Metadata = apps.get_model('geomanager', 'Metadata')

    try:
        dataset = Dataset.objects.get(dataset_slug='flood-inundation-history')
        if dataset.metadata:
            dataset.metadata.delete()
        dataset.delete()
        print("Removed Flood Inundation History dataset")
    except Dataset.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0028_create_inundation_history_table'),
        ('geomanager', '0065_alter_vectortilelayer_popup_config'),
    ]

    operations = [
        migrations.RunPython(seed_inundation_layer, remove_inundation_layer),
    ]
