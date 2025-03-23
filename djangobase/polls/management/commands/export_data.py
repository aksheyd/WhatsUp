from django.core.management.base import BaseCommand
from polls.models import State, County, Ordinance
import json

class Command(BaseCommand):
    help = 'Export all data to JSON files'

    def handle(self, *args, **kwargs):
        # Export States
        states = []
        for state in State.objects.all():
            states.append({
                'code': state.code,
                'name': state.name,
                'link': state.link
            })
        
        # Export Counties
        counties = []
        for county in County.objects.all():
            counties.append({
                'state_code': county.state.code,
                'name': county.name,
                'link': county.link
            })
        
        # Export Ordinances
        ordinances = []
        for ordinance in Ordinance.objects.all():
            ordinances.append({
                'state_code': ordinance.county.state.code,
                'county_name': ordinance.county.name,
                'url': ordinance.url,
                'text': ordinance.text
            })
        
        # Save to files
        with open('exported_states.json', 'w') as f:
            json.dump(states, f, indent=2)
        
        with open('exported_counties.json', 'w') as f:
            json.dump(counties, f, indent=2)
        
        with open('exported_ordinances.json', 'w') as f:
            json.dump(ordinances, f, indent=2)
        
        self.stdout.write(self.style.SUCCESS('Data exported successfully'))
