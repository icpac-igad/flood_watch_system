from django.db import migrations
from django.utils import timezone


def publish_unpublished_storylines(apps, schema_editor):
    StorylinePage = apps.get_model("storylines", "StorylinePage")
    now = timezone.now()

    StorylinePage.objects.filter(live=False).update(
        live=True,
        has_unpublished_changes=False,
        latest_revision_created_at=now,
        first_published_at=now,
        last_published_at=now,
    )


def noop_reverse(apps, schema_editor):
    # Keep pages published on reverse.
    return


class Migration(migrations.Migration):
    dependencies = [
        ("storylines", "0003_alter_storylineindexpage_intro_and_more"),
    ]

    operations = [
        migrations.RunPython(publish_unpublished_storylines, noop_reverse),
    ]

