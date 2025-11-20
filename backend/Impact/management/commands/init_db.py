"""
Management command to initialize database with admin users and sample data.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Initialize database with admin users and sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='Skip creating admin users',
        )

    def handle(self, *args, **options):
        if not options['skip_users']:
            self.create_admin_users()

        self.stdout.write(self.style.SUCCESS('\nDatabase initialization complete!'))

    def create_admin_users(self):
        """Create superuser and member state admin accounts"""
        self.stdout.write('\n=== Creating Admin Users ===\n')

        # Create superuser
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@floodwatch.icpac.net',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        if created:
            admin_user.set_password('floodwatch2024')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('✓ Created superuser: admin'))
        else:
            self.stdout.write('- Superuser admin already exists')

        # Create member state admin accounts
        member_states = [
            ('kenya_admin', 'kenya@floodwatch.icpac.net', 'Kenya'),
            ('ethiopia_admin', 'ethiopia@floodwatch.icpac.net', 'Ethiopia'),
            ('uganda_admin', 'uganda@floodwatch.icpac.net', 'Uganda'),
            ('tanzania_admin', 'tanzania@floodwatch.icpac.net', 'Tanzania'),
            ('sudan_admin', 'sudan@floodwatch.icpac.net', 'Sudan'),
            ('south_sudan_admin', 'southsudan@floodwatch.icpac.net', 'South Sudan'),
            ('djibouti_admin', 'djibouti@floodwatch.icpac.net', 'Djibouti'),
            ('somalia_admin', 'somalia@floodwatch.icpac.net', 'Somalia'),
            ('rwanda_admin', 'rwanda@floodwatch.icpac.net', 'Rwanda'),
            ('burundi_admin', 'burundi@floodwatch.icpac.net', 'Burundi'),
            ('eritrea_admin', 'eritrea@floodwatch.icpac.net', 'Eritrea'),
        ]

        for username, email, country in member_states:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_staff': True,
                    'is_active': True,
                }
            )
            if created:
                user.set_password('memberstate2024')
                user.save()
                self.stdout.write(self.style.SUCCESS(f'✓ Created {username} ({country})'))
            else:
                self.stdout.write(f'- {username} already exists')

        # Create ICPAC admin account
        icpac_user, created = User.objects.get_or_create(
            username='icpac_admin',
            defaults={
                'email': 'icpac@floodwatch.icpac.net',
                'is_staff': True,
                'is_active': True,
            }
        )
        if created:
            icpac_user.set_password('icpac2024')
            icpac_user.save()
            self.stdout.write(self.style.SUCCESS('✓ Created icpac_admin'))
        else:
            self.stdout.write('- icpac_admin already exists')

        total_users = User.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\nTotal users in database: {total_users}'))
