# filepath: djangobase/polls/management/commands/import_data.py
import csv
from django.core.management.base import BaseCommand
from polls.models import State, County  # Replace with your actual models

class Command(BaseCommand):
    help = 'Import state and county data into the database'

    def handle(self, *args, **kwargs):
        with open('web_scraper/state_urls.csv', 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                state, created = State.objects.get_or_create(name=row['state_name'])
                County.objects.get_or_create(name=row['county_name'], state=state)
        self.stdout.write(self.style.SUCCESS('Data imported successfully!'))