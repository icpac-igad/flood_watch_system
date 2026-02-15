from django.db import migrations
from django.db.models import Max


TARGET_SUBCATEGORIES = [
    "Exposure",
    "Susceptibility",
    "Vulnerability",
    "Resilience",
]


def ensure_impact_subcategories(apps, schema_editor):
    Category = apps.get_model("geomanager", "Category")
    SubCategory = apps.get_model("geomanager", "SubCategory")
    Dataset = apps.get_model("geomanager", "Dataset")

    impact_category = Category.objects.filter(title__icontains="impact").first()
    if not impact_category:
        return

    max_sort_order = (
        SubCategory.objects.filter(category=impact_category).aggregate(max_order=Max("sort_order")).get("max_order") or 0
    )

    for title in TARGET_SUBCATEGORIES:
        subcat = SubCategory.objects.filter(category=impact_category, title__iexact=title).first()

        if not subcat:
            # Reuse existing global subcategory if present, otherwise create one.
            subcat = SubCategory.objects.filter(title__iexact=title).first()

        if subcat:
            changed = False

            if subcat.category_id != impact_category.id:
                subcat.category = impact_category
                changed = True

                if not subcat.sort_order:
                    max_sort_order += 1
                    subcat.sort_order = max_sort_order

            if not subcat.active:
                subcat.active = True
                changed = True

            if not subcat.public:
                subcat.public = True
                changed = True

            if changed:
                subcat.save()
        else:
            max_sort_order += 1
            subcat = SubCategory.objects.create(
                category=impact_category,
                title=title,
                sort_order=max_sort_order,
                active=True,
                public=True,
            )

        Dataset.objects.filter(sub_category=subcat).exclude(category=impact_category).update(category=impact_category)


def reverse_noop(apps, schema_editor):
    # Forward migration is intentionally non-destructive.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("geomanager", "0068_move_inundation_subcategories_to_impact"),
    ]

    operations = [
        migrations.RunPython(ensure_impact_subcategories, reverse_noop),
    ]
