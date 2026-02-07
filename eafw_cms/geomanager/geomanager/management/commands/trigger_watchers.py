from django.core.management.base import BaseCommand
from geomanager.tasks.watchers import update_all_datasets

class Command(BaseCommand):
    
    def handle(self, *args, **options):
        self.stdout.write("Triggering dataset watchers...")
        update_all_datasets()
        self.stdout.write(self.style.SUCCESS("Watchers completed"))