# Move Weather placeholders to Impact:
# - "Inundation Maps"
# - "Flood Extent / Hazard"
#
# Weather category is expected to keep only Weekly Rainfall (handled elsewhere).

from django.db import migrations


def move_inundation_subcategories_to_impact(apps, schema_editor):
    Category = apps.get_model("geomanager", "Category")
    SubCategory = apps.get_model("geomanager", "SubCategory")
    Dataset = apps.get_model("geomanager", "Dataset")

    impact_category = Category.objects.filter(title__icontains="impact").first()
    if not impact_category:
        # Nothing to do if Impact doesn't exist in this DB.
        return

    targets = [
        ("Inundation Maps", 2),
        ("Flood Extent / Hazard", 3),
    ]

    for title, sort_order in targets:
        subcat = SubCategory.objects.filter(title__iexact=title).first()
        if subcat:
            changed = False
            if subcat.category_id != impact_category.id:
                subcat.category = impact_category
                changed = True
            if subcat.sort_order != sort_order:
                subcat.sort_order = sort_order
                changed = True
            if not subcat.active:
                subcat.active = True
                changed = True
            if not subcat.public:
                subcat.public = True
                changed = True
            if changed:
                subcat.save()
        else:
            subcat = SubCategory.objects.create(
                category=impact_category,
                title=title,
                sort_order=sort_order,
                active=True,
                public=True,
            )

        # Ensure datasets in this subcategory appear under Impact.
        Dataset.objects.filter(sub_category=subcat).exclude(category=impact_category).update(category=impact_category)


def reverse_noop(apps, schema_editor):
    # Non-destructive forward migration; reverse left intentionally as no-op.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("geomanager", "0067_add_exposure_subcategory"),
    ]

    operations = [
        migrations.RunPython(move_inundation_subcategories_to_impact, reverse_noop),
    ]
