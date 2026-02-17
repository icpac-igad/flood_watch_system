import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
import wagtail.images.blocks
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("wagtailcore", "0089_log_entry_data_json_null_to_object"),
        ("wagtailimages", "0025_alter_image_file_alter_rendition_file"),
    ]

    operations = [
        migrations.CreateModel(
            name="StorylineIndexPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "intro",
                    wagtail.fields.RichTextField(
                        blank=True,
                        verbose_name="Introduction",
                    ),
                ),
            ],
            options={
                "verbose_name": "Storyline Index",
            },
            bases=("wagtailcore.page",),
        ),
        migrations.CreateModel(
            name="StorylinePage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
                (
                    "description",
                    models.TextField(verbose_name="Short Description"),
                ),
                (
                    "event_start",
                    models.DateField(verbose_name="Event Start Date"),
                ),
                (
                    "event_end",
                    models.DateField(verbose_name="Event End Date"),
                ),
                (
                    "region",
                    models.CharField(
                        default="East Africa",
                        max_length=100,
                        verbose_name="Region",
                    ),
                ),
                (
                    "total_affected",
                    models.IntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Total People Affected",
                    ),
                ),
                (
                    "total_displaced",
                    models.IntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Total People Displaced",
                    ),
                ),
                (
                    "total_deaths",
                    models.IntegerField(
                        blank=True,
                        null=True,
                        verbose_name="Total Deaths",
                    ),
                ),
                (
                    "country_events",
                    wagtail.fields.StreamField(
                        [("event", wagtail.blocks.StructBlock([
                            ("country", wagtail.blocks.ChoiceBlock(choices=[])),
                            ("event_period", wagtail.blocks.CharBlock(max_length=50)),
                            ("emdat_codes", wagtail.blocks.CharBlock(max_length=200, required=False)),
                        ]))],
                        blank=True,
                        verbose_name="Country Events",
                    ),
                ),
                (
                    "chapters",
                    wagtail.fields.StreamField(
                        [("chapter", wagtail.blocks.StructBlock([
                            ("title", wagtail.blocks.CharBlock(max_length=200)),
                            ("prose", wagtail.blocks.RichTextBlock(features=["bold", "italic", "ol", "ul", "link", "h3", "h4", "blockquote"])),
                            ("map_state", wagtail.blocks.StructBlock([
                                ("center_lon", wagtail.blocks.FloatBlock()),
                                ("center_lat", wagtail.blocks.FloatBlock()),
                                ("zoom", wagtail.blocks.FloatBlock(default=5)),
                                ("bearing", wagtail.blocks.FloatBlock(default=0, required=False)),
                                ("pitch", wagtail.blocks.FloatBlock(default=0, required=False)),
                            ], required=False)),
                            ("transition", wagtail.blocks.ChoiceBlock(choices=[("fly", "Fly To"), ("jump", "Jump To"), ("ease", "Ease To")], default="fly")),
                            ("date_start", wagtail.blocks.DateBlock(required=False)),
                            ("date_end", wagtail.blocks.DateBlock(required=False)),
                            ("media", wagtail.blocks.StreamBlock([
                                ("image", wagtail.images.blocks.ImageChooserBlock()),
                                ("external_image", wagtail.blocks.StructBlock([
                                    ("url", wagtail.blocks.URLBlock()),
                                    ("alt", wagtail.blocks.CharBlock(max_length=200)),
                                    ("caption", wagtail.blocks.CharBlock(max_length=500, required=False)),
                                ])),
                                ("embed", wagtail.blocks.StructBlock([
                                    ("url", wagtail.blocks.URLBlock()),
                                    ("title", wagtail.blocks.CharBlock(max_length=200, required=False)),
                                    ("height", wagtail.blocks.IntegerBlock(default=400)),
                                ])),
                            ], required=False)),
                            ("references", wagtail.blocks.ListBlock(wagtail.blocks.StructBlock([
                                ("title", wagtail.blocks.CharBlock(max_length=300)),
                                ("url", wagtail.blocks.URLBlock()),
                            ]), required=False)),
                        ]))],
                        verbose_name="Story Chapters",
                    ),
                ),
                (
                    "cover_image",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="wagtailimages.image",
                        verbose_name="Cover Image",
                    ),
                ),
            ],
            options={
                "verbose_name": "Storyline",
                "verbose_name_plural": "Storylines",
            },
            bases=("wagtailcore.page",),
        ),
    ]
