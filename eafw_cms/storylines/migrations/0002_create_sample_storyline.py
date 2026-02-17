"""
Create sample E4DRR East Africa Flood Disaster Events storyline.
Data from: https://icpac-igad.github.io/e4drr/blog/2025-04-flood-events/
"""
import json
import uuid
from django.db import migrations


def make_id():
    return str(uuid.uuid4())[:8]


COUNTRY_EVENTS = [
    {"country": "BI", "event_period": "October-December 2023", "emdat_codes": ""},
    {"country": "DJ", "event_period": "November 2019", "emdat_codes": "2019-0579-DJI"},
    {"country": "ER", "event_period": "April-May 2024", "emdat_codes": ""},
    {"country": "ET", "event_period": "April-May 2024", "emdat_codes": "2024-0341-ETH"},
    {"country": "KE", "event_period": "March-April 2024", "emdat_codes": "2024-0150-KEN, 2024-0210-KEN, 2024-0247-KEN, 2024-0892-KEN"},
    {"country": "RW", "event_period": "May 2023", "emdat_codes": "2023-0267-RWA"},
    {"country": "SO", "event_period": "October-December 2023", "emdat_codes": "2023-0172-SOM, 2023-0295-SOM, 2023-0683-SOM, 2023-0741-SOM"},
    {"country": "SS", "event_period": "September-October 2024", "emdat_codes": "2024-0673-SSD"},
    {"country": "SD", "event_period": "July-August 2024", "emdat_codes": "2024-0544-SDN"},
    {"country": "TZ", "event_period": "November 2023 - April 2024", "emdat_codes": "2023-0226-TZA, 2023-0236-TZA, 2023-0807-TZA, 2024-0203-TZA, 2024-0879-TZA"},
    {"country": "UG", "event_period": "August-September 2023", "emdat_codes": "2023-0262-UGA"},
]

CHAPTERS = [
    {
        "title": "Overview: A Region Under Water",
        "prose": "<p>Between 2019 and 2024, East Africa experienced some of the most devastating flood events in recent history. Driven by El Ni\u00f1o, the Indian Ocean Dipole (IOD), and intensifying seasonal rains, 11 countries across the region were struck by catastrophic flooding.</p><p>This storyline documents these events \u2014 their causes, their human toll, and the early warning signals that preceded them. Scroll through to explore each country's experience.</p>",
        "map_state": {"center_lon": 38.0, "center_lat": 2.0, "zoom": 4.5, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2019-11-01",
        "date_end": "2024-10-31",
        "references": [],
    },
    {
        "title": "Burundi: El Ni\u00f1o Floods (Oct\u2013Dec 2023)",
        "prose": "<p>El Ni\u00f1o-induced heavy rainfall devastated Burundi between October and December 2023. ICPAC had issued forecast warnings as early as July 2023.</p><p><b>Impact:</b> Over 203,944 people affected, 98,000+ internally displaced, and 19,250+ homes destroyed. Flooding continued into April 2024.</p>",
        "map_state": {"center_lon": 29.36, "center_lat": -3.37, "zoom": 7.5, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2023-10-01",
        "date_end": "2023-12-31",
        "references": [
            {"title": "Anticipatory Action Activation - Burundi", "url": "https://reliefweb.int/report/burundi/anticipatory-action-activation-burundi-november-2023"},
            {"title": "East Africa Battles Catastrophic Floods", "url": "https://www.arise.tv/from-burundi-to-kenya-east-africa-battles-catastrophic-floods-with-death-toll-rising/"},
        ],
    },
    {
        "title": "Djibouti: Two Years of Rain in One Day (Nov 2019)",
        "prose": "<p>In November 2019, Djibouti city received approximately 300mm of rainfall \u2014 roughly three times its annual average \u2014 in a matter of days.</p><p><b>Impact:</b> 9 deaths reported (including 7 children), 250,000 people affected nationwide across a population of under one million.</p>",
        "map_state": {"center_lon": 43.15, "center_lat": 11.59, "zoom": 9, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2019-11-21",
        "date_end": "2019-11-23",
        "references": [
            {"title": "UNICEF Djibouti Flood Response Report", "url": "https://reliefweb.int/report/djibouti/unicef-djibouti-humanitarian-situation-report-no-2-flood-response-05122019-reporting"},
            {"title": "Djibouti Receives Two Years of Rain in a Single Day", "url": "https://www.downtoearth.org.in/natural-disasters/djibouti-receives-two-years-worth-of-rain-in-a-single-day-68226"},
        ],
    },
    {
        "title": "Ethiopia: Highland Floods (Apr\u2013May 2024)",
        "prose": "<p>Heavy rainfall during the 2024 rainy season, particularly in highland areas, caused widespread flooding across seven regions: Afar, Amhara, Central Ethiopia, Oromia, Sidama, Somali, South Ethiopia, and Tigray.</p><p><b>Impact:</b> More than 590,000 people affected. Around 95,000 people displaced from their homes.</p>",
        "map_state": {"center_lon": 39.5, "center_lat": 8.5, "zoom": 5.5, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2024-04-01",
        "date_end": "2024-05-31",
        "references": [
            {"title": "Ethiopia Flood Disaster 2024", "url": "https://reliefweb.int/disaster/fl-2024-000074-eth"},
        ],
    },
    {
        "title": "Kenya: El Ni\u00f1o and Cyclone Hidaya (Mar\u2013Apr 2024)",
        "prose": "<p>Torrential rains amplified by the El Ni\u00f1o phenomenon, combined with the threat from Cyclone Hidaya, caused widespread flooding across Kenya in March and April 2024.</p><p><b>Impact:</b> 188 deaths, 165,000 people displaced, 90 people reported missing. Multiple counties declared disaster areas.</p>",
        "map_state": {"center_lon": 37.9, "center_lat": -0.5, "zoom": 6, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2024-03-01",
        "date_end": "2024-04-30",
        "references": [
            {"title": "Kenya Floods Death Toll Rises to 188", "url": "https://www.voanews.com/a/kenya-floods-death-toll-rises-to-188-as-heavy-rains-persist-/7594872.html"},
        ],
    },
    {
        "title": "Rwanda: Floods and Landslides (May 2023)",
        "prose": "<p>Heavy rainfall triggered devastating floods and landslides across Rwanda between May 1\u20133, 2023, killing over 109 people.</p><p><b>Impact:</b> 109\u2013131 deaths, 51,905 people (10,381 households) affected, 5,472 houses completely destroyed. Rwanda later sought $451M for post-flood reconstruction.</p>",
        "map_state": {"center_lon": 29.87, "center_lat": -1.94, "zoom": 8, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2023-05-01",
        "date_end": "2023-05-03",
        "references": [
            {"title": "Rwanda Seeks $451M for Post-Floods Reconstruction", "url": "https://www.ktpress.rw/2024/12/rwanda-seeks-451m-for-post-floods-reconstruction"},
            {"title": "Floods Kill at Least 109 in Rwanda", "url": "https://www.theeastafrican.co.ke/tea/news/east-africa/floods-kill-at-least-109-in-rwanda-4221500"},
        ],
    },
    {
        "title": "Somalia: Unprecedented Deyr Flooding (Oct\u2013Dec 2023)",
        "prose": "<p>Somalia experienced unprecedented flooding during the Deyr rainy season (October\u2013December 2023), caused by El Ni\u00f1o. The Gu season (April\u2013June 2024) brought additional flash floods.</p><p><b>Impact:</b> 2.48 million people affected, over 1.2 million displaced. Estimated damages of $193.4 million. An additional 4 deaths in the 2024 Gu season.</p>",
        "map_state": {"center_lon": 45.3, "center_lat": 5.15, "zoom": 5.5, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2023-10-01",
        "date_end": "2023-12-31",
        "references": [
            {"title": "Somalia 2023 Deyr Floods - Rapid Post-Disaster Needs Assessment", "url": "https://reliefweb.int/report/somalia/somalia-2023-deyr-floods-rapid-post-disaster-needs-assessment-report"},
            {"title": "Flash Floods in Somalia - Urgent Calls for Funding", "url": "https://reliefweb.int/report/somalia/flash-floods-somalia-urgent-calls-funding-and-action"},
        ],
    },
    {
        "title": "South Sudan: Nile Floods (Sep\u2013Oct 2024)",
        "prose": "<p>Intense seasonal rainfall, high lake levels upstream in Uganda, and elevated water levels in the Nile River caused massive flooding that peaked in early October 2024.</p><p><b>Impact:</b> 1.4 million people affected, 379,000 displaced. Flood extent of approximately 48,000 km\u00b2 \u2014 an area larger than Denmark.</p>",
        "map_state": {"center_lon": 31.6, "center_lat": 6.87, "zoom": 6, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2024-09-01",
        "date_end": "2024-10-31",
        "references": [
            {"title": "South Sudan Floods Snapshot - October 2024", "url": "https://www.unocha.org/publications/report/south-sudan/south-sudan-floods-snapshot-18-october-2024"},
        ],
    },
    {
        "title": "Sudan: Rainy Season Crisis (Jul\u2013Aug 2024)",
        "prose": "<p>Heavy rainfall during the 2024 rainy season severely affected Kassala State, North Darfur State, and Sennar State. The flooding crisis compounded an already devastating humanitarian situation due to the ongoing civil conflict.</p><p><b>Impact:</b> At least 5 deaths, thousands displaced, over 1,000 houses destroyed.</p>",
        "map_state": {"center_lon": 32.5, "center_lat": 15.5, "zoom": 5.5, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2024-07-01",
        "date_end": "2024-08-30",
        "references": [
            {"title": "Sudan's Flood Crisis Worsens Amid War", "url": "https://www.newarab.com/features/sudans-flood-crisis-worsens-amid-ongoing-war-and-aid-shortages"},
        ],
    },
    {
        "title": "Tanzania: El Ni\u00f1o + IOD (Nov 2023\u2013Apr 2024)",
        "prose": "<p>Heavy rains caused by El Ni\u00f1o and intensified by the Indian Ocean Dipole (IOD) system battered Tanzania from November 2023 through April 2024, affecting 51,000 households across the country.</p><p><b>Impact:</b> 155 deaths, 236 injuries, approximately 200,000 people affected.</p>",
        "map_state": {"center_lon": 34.9, "center_lat": -6.37, "zoom": 5.5, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2023-11-01",
        "date_end": "2024-04-30",
        "references": [
            {"title": "BBC: Tanzania Floods", "url": "https://www.bbc.com/news/world-africa-68896454"},
            {"title": "Tanzania Floods Emergency Appeal", "url": "https://reliefweb.int/report/united-republic-tanzania/tanzania-africa-floods-and-landslides-202324-revised-emergency-appeal-mdrtz035"},
        ],
    },
    {
        "title": "Uganda: El Ni\u00f1o Storms (Aug\u2013Sep 2023)",
        "prose": "<p>Heavy storms, floods, and landslides triggered by El Ni\u00f1o affected Uganda throughout 2023, intensifying in August and September.</p><p><b>Impact:</b> From January to September 2023, disasters affected 97,727 individuals and displaced over 7,908 people.</p>",
        "map_state": {"center_lon": 32.3, "center_lat": 1.37, "zoom": 6.5, "bearing": 0, "pitch": 0},
        "transition": "fly",
        "date_start": "2023-08-01",
        "date_end": "2023-09-30",
        "references": [
            {"title": "Uganda Multi-Hazard Infographic - October 2023", "url": "https://reliefweb.int/report/uganda/uganda-multi-hazard-infographic-responsedrr-platform-published-10th-october-2023"},
        ],
    },
    {
        "title": "Lessons and the Path Forward",
        "prose": "<p>These flood events across East Africa underscore the critical importance of early warning systems, anticipatory action, and coordinated regional response.</p><p>Key takeaways:</p><ul><li><b>Early warnings save lives</b> \u2014 ICPAC's seasonal forecasts provided advance notice months before many events</li><li><b>Climate drivers are intensifying</b> \u2014 El Ni\u00f1o and IOD are producing more extreme rainfall</li><li><b>Cross-border coordination is essential</b> \u2014 river systems and weather systems don't respect national boundaries</li><li><b>Preparedness reduces impact</b> \u2014 countries with anticipatory action frameworks showed better outcomes</li></ul><p>The East Africa Flood Watch system continues to monitor and forecast flood conditions across the region, supporting timely decision-making for disaster risk reduction.</p>",
        "map_state": {"center_lon": 38.0, "center_lat": 2.0, "zoom": 4, "bearing": 0, "pitch": 20},
        "transition": "ease",
        "date_start": None,
        "date_end": None,
        "references": [],
    },
]


def create_sample_storyline(apps, schema_editor):
    """Create the StorylineIndexPage and a sample StorylinePage."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    Page = apps.get_model("wagtailcore", "Page")
    Locale = apps.get_model("wagtailcore", "Locale")
    StorylineIndexPage = apps.get_model("storylines", "StorylineIndexPage")
    StorylinePage = apps.get_model("storylines", "StorylinePage")

    # Get the root page
    try:
        root_page = Page.objects.get(depth=1)
    except Page.DoesNotExist:
        return

    # Get default locale (English)
    try:
        locale = Locale.objects.get(language_code="en")
    except Locale.DoesNotExist:
        locale = Locale.objects.first()
    if not locale:
        return

    # Get or create content types
    index_ct, _ = ContentType.objects.get_or_create(
        app_label="storylines", model="storylineindexpage"
    )
    story_ct, _ = ContentType.objects.get_or_create(
        app_label="storylines", model="storylinepage"
    )

    # Find the next available path under root
    last_child = Page.objects.filter(depth=2).order_by("-path").first()
    if last_child:
        last_num = int(last_child.path[-4:])
        next_path = root_page.path + str(last_num + 1).zfill(4)
    else:
        next_path = root_page.path + "0002"

    # Create index page under root
    index_page = StorylineIndexPage(
        title="Storylines",
        slug="storylines-index",
        intro="<p>Interactive narratives documenting major flood events across East Africa.</p>",
        content_type=index_ct,
        locale=locale,
        path=next_path,
        depth=root_page.depth + 1,
        live=True,
    )
    index_page.save()

    # Update root's numchild
    root_page.numchild = Page.objects.filter(depth=2).count()
    root_page.save(update_fields=["numchild"])

    # Build country_events StreamField JSON
    country_events_json = json.dumps([
        {"type": "event", "value": evt, "id": make_id()}
        for evt in COUNTRY_EVENTS
    ])

    # Build chapters StreamField JSON
    chapters_json = json.dumps([
        {
            "type": "chapter",
            "id": make_id(),
            "value": {
                "title": ch["title"],
                "prose": ch["prose"],
                "map_state": ch["map_state"],
                "transition": ch["transition"],
                "date_start": ch["date_start"],
                "date_end": ch["date_end"],
                "media": [],
                "references": [
                    {"title": r["title"], "url": r["url"]}
                    for r in ch["references"]
                ],
            },
        }
        for ch in CHAPTERS
    ])

    # Create the sample storyline
    story_page = StorylinePage(
        title="East Africa Flood Disaster Events (2019\u20132024)",
        slug="east-africa-flood-events-2019-2024",
        description="A comprehensive narrative of major flood disaster events across 11 East African countries, documenting the causes, impacts, and humanitarian response from 2019 to 2024.",
        event_start="2019-11-01",
        event_end="2024-10-31",
        region="East Africa",
        total_affected=5500000,
        total_displaced=3200000,
        total_deaths=600,
        country_events=country_events_json,
        chapters=chapters_json,
        content_type=story_ct,
        locale=locale,
        path=index_page.path + "0001",
        depth=index_page.depth + 1,
        live=True,
    )
    story_page.save()

    # Update index numchild
    index_page.numchild = 1
    index_page.save(update_fields=["numchild"])


def remove_sample_storyline(apps, schema_editor):
    Page = apps.get_model("wagtailcore", "Page")
    Page.objects.filter(slug="storylines-index").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("storylines", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_sample_storyline, remove_sample_storyline),
    ]
