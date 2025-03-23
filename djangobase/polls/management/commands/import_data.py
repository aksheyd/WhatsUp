# filepath: djangobase/polls/management/commands/import_data.py
import csv
import os
from django.core.management.base import BaseCommand
from polls.models import State, County  # Replace with your actual models

class Command(BaseCommand):
    help = 'Import state and county data from CSV files into the database'

    def handle(self, *args, **kwargs):
        # Import states
        try: 
            states_file = 'web_scraper/state_urls.csv'
            if not os.path.exists(states_file):
                self.stdout.write(self.style.ERROR(f'File not found: {states_file}'))
                return

            with open(states_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                states_created = 0
                
                for row in reader:
                    state, created = State.objects.get_or_create(
                        code=row['State Code'],
                        defaults={
                            'name': row['State'],
                            'link': row['URL']
                        }
                    )
                    if created:
                        states_created += 1

            self.stdout.write(
                self.style.SUCCESS(f'Successfully imported {states_created} states')
            )

            # Import counties for each state
            data_dir = 'web_scraper/data'
            if os.path.exists(data_dir):
                for filename in os.listdir(data_dir):
                    if filename.endswith('_county_urls.csv'):
                        state_code = filename.split('_')[0]

                        try:
                            state = State.objects.get(code=state_code)
                        
                            counties_created = 0
                            
                            with open(os.path.join(data_dir, filename), 'r', encoding='utf-8') as file:
                                reader = csv.DictReader(file)
                                for row in reader:
                                    county, created = County.objects.get_or_create(
                                        state=state,
                                        name=row['county'],
                                        defaults={'link': row['url']}
                                    )
                                    if created:
                                        counties_created += 1
                            
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Successfully imported {counties_created} counties for {state.name}'
                                )
                            )
                        except State.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f'State not found for code: {state_code}')
                            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error importing data: {str(e)}')
            )