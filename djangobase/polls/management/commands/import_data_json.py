from django.core.management.base import BaseCommand
from polls.models import State, County, Ordinance
import json

class Command(BaseCommand):
    help = 'Import all data from JSON files'

    def handle(self, *args, **kwargs):
        try:
            # Import States
            with open('exported_states.json', 'r') as f:
                states = json.load(f)
                for state_data in states:
                    State.objects.get_or_create(
                        code=state_data['code'],
                        defaults={
                            'name': state_data['name'],
                            'link': state_data['link']
                        }
                    )

            # Import Counties
            with open('exported_counties.json', 'r') as f:
                counties = json.load(f)
                for county_data in counties:
                    state = State.objects.get(code=county_data['state_code'])
                    County.objects.get_or_create(
                        state=state,
                        name=county_data['name'],
                        defaults={'link': county_data['link']}
                    )

            # Import Ordinances
            with open('exported_ordinances.json', 'r') as f:
                ordinances = json.load(f)
                for ord_data in ordinances:
                    state = State.objects.get(code=ord_data['state_code'])
                    county = County.objects.get(state=state, name=ord_data['county_name'])
                    Ordinance.objects.update_or_create(
                        url=ord_data['url'],
                        defaults={
                            'county': county,
                            'text': ord_data['text']
                        }
                    )

            self.stdout.write(self.style.SUCCESS('Data imported successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing data: {str(e)}'))
