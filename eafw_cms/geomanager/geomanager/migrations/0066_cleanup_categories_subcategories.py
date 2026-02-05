# Generated migration to clean up categories and subcategories
# - Weather Information: keep only "Weekly Rainfall Forecasts"
# - Delete "Climate" category entirely
# - Impact: keep only "Landscan Population"

from django.db import migrations


def cleanup_categories_and_subcategories(apps, schema_editor):
    """
    Clean up categories and subcategories:
    1. Weather Information - only keep "Weekly Rainfall Forecasts"
    2. Delete "Climate" category entirely
    3. Impact - only keep "Landscan Population"

    Note: Datasets associated with deleted subcategories will also be deleted.
    """
    Category = apps.get_model('geomanager', 'Category')
    SubCategory = apps.get_model('geomanager', 'SubCategory')
    Dataset = apps.get_model('geomanager', 'Dataset')

    # 1. Weather Information - delete all subcategories except "Weekly Rainfall Forecasts"
    weather_categories = Category.objects.filter(title__icontains='weather')
    for weather_cat in weather_categories:
        # Get subcategories to delete
        subcats_to_delete = SubCategory.objects.filter(
            category=weather_cat
        ).exclude(
            title__icontains='weekly rainfall'
        )

        # Delete datasets associated with subcategories to be deleted
        for subcat in subcats_to_delete:
            Dataset.objects.filter(sub_category=subcat).delete()
            print(f"Deleted datasets for subcategory: {subcat.title}")

        # Now delete the subcategories
        subcats_to_delete.delete()
        print(f"Cleaned up Weather category: {weather_cat.title}")

    # 2. Delete "Climate" category entirely (this will cascade delete subcategories)
    climate_categories = Category.objects.filter(title__icontains='climate')
    for climate_cat in climate_categories:
        # First delete all datasets associated with this category's subcategories
        subcats = SubCategory.objects.filter(category=climate_cat)
        for subcat in subcats:
            Dataset.objects.filter(sub_category=subcat).delete()
            print(f"Deleted datasets for subcategory: {subcat.title}")

        # Delete subcategories
        subcats.delete()
        # Delete category
        climate_cat.delete()
        print(f"Deleted Climate category: {climate_cat.title}")

    # 3. Impact - delete all subcategories except "Landscan Population"
    impact_categories = Category.objects.filter(title__icontains='impact')
    for impact_cat in impact_categories:
        # Get subcategories to delete
        subcats_to_delete = SubCategory.objects.filter(
            category=impact_cat
        ).exclude(
            title__icontains='landscan'
        )

        # Delete datasets associated with subcategories to be deleted
        for subcat in subcats_to_delete:
            Dataset.objects.filter(sub_category=subcat).delete()
            print(f"Deleted datasets for subcategory: {subcat.title}")

        # Now delete the subcategories
        subcats_to_delete.delete()
        print(f"Cleaned up Impact category: {impact_cat.title}")


def reverse_cleanup(apps, schema_editor):
    """
    This migration cannot be fully reversed as we're deleting data.
    This is a no-op reverse migration.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('geomanager', '0065_alter_vectortilelayer_popup_config'),
    ]

    operations = [
        migrations.RunPython(
            cleanup_categories_and_subcategories,
            reverse_cleanup,
        ),
    ]
