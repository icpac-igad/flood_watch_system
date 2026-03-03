"""Create the CAP Alert List Page required by cap-composer."""

from django.db import migrations


def create_cap_alert_list_page(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Page = apps.get_model("wagtailcore", "Page")

    ct, _ = ContentType.objects.get_or_create(
        app_label="cap", model="capalertlistpage"
    )

    # Don't create if a page with this content type already exists
    if Page.objects.filter(content_type=ct).exists():
        return

    root_page = Page.objects.filter(depth=1).first()
    if not root_page:
        return

    # Get default locale (required by wagtail-localize)
    Locale = apps.get_model("wagtailcore", "Locale")
    default_locale = Locale.objects.first()

    # Calculate treebeard path for new child of root
    last_child = (
        Page.objects.filter(depth=2).order_by("-path").first()
    )
    if last_child:
        # Increment the last child's path
        path_len = len(last_child.path)
        step_len = path_len - len(root_page.path)
        last_num = int(last_child.path[-step_len:], 36)
        new_suffix = base36(last_num + 1, step_len)
        new_path = root_page.path + new_suffix
    else:
        new_path = root_page.path + "0001"

    create_kwargs = dict(
        title="CAP Alerts",
        slug="cap-alerts",
        content_type=ct,
        path=new_path,
        depth=2,
        numchild=0,
        live=True,
    )
    if default_locale:
        create_kwargs["locale"] = default_locale

    page = Page.objects.create(**create_kwargs)

    # Create the model-specific row for multi-table inheritance
    CapAlertListPage = apps.get_model("cap", "CapAlertListPage")
    CapAlertListPage.objects.create(
        page_ptr_id=page.pk,
        heading="CAP Flood Alerts",
    )

    # Update root's numchild
    root_page.numchild = Page.objects.filter(depth=2).count()
    root_page.save(update_fields=["numchild"])


def base36(num, pad=4):
    """Convert integer to base-36 string, zero-padded."""
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = ""
    while num:
        result = chars[num % 36] + result
        num //= 36
    return (result or "0").rjust(pad, "0")


def reverse(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Page = apps.get_model("wagtailcore", "Page")
    ct = ContentType.objects.filter(
        app_label="cap", model="capalertlistpage"
    ).first()
    if ct:
        Page.objects.filter(content_type=ct).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0070_include_eritrea_in_admin_boundaries"),
        ("cap", "__first__"),
        ("wagtailcore", "__latest__"),
    ]
    operations = [
        migrations.RunPython(create_cap_alert_list_page, reverse),
    ]
