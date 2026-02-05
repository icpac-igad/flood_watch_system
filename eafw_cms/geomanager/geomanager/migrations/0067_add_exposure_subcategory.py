# Generated migration to add Exposure subcategory under Impact
# Contains: Landscan Population, Google Building Footprints

from django.db import migrations


def add_exposure_subcategory(apps, schema_editor):
    """
    Add 'Exposure' subcategory under the Impact category
    """
    Category = apps.get_model('geomanager', 'Category')
    SubCategory = apps.get_model('geomanager', 'SubCategory')

    # Find the Impact category
    try:
        impact_category = Category.objects.get(title__icontains='impact')
    except Category.DoesNotExist:
        print("Impact category not found, skipping")
        return
    except Category.MultipleObjectsReturned:
        impact_category = Category.objects.filter(title__icontains='impact').first()

    # Create Exposure subcategory if it doesn't exist
    exposure, created = SubCategory.objects.get_or_create(
        category=impact_category,
        title='Exposure',
        defaults={
            'active': True,
            'public': True,
        }
    )

    if created:
        print(f"Created 'Exposure' subcategory under Impact")
    else:
        print(f"'Exposure' subcategory already exists")


def reverse_add_exposure(apps, schema_editor):
    """
    Remove Exposure subcategory
    """
    SubCategory = apps.get_model('geomanager', 'SubCategory')
    SubCategory.objects.filter(title='Exposure').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('geomanager', '0066_cleanup_categories_subcategories'),
    ]

    operations = [
        migrations.RunPython(
            add_exposure_subcategory,
            reverse_add_exposure,
        ),
    ]
