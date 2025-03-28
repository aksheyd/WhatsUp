import csv
import os
from django.core.management.base import BaseCommand
from polls.models import State, County, Ordinance
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class Command(BaseCommand):
    help = 'Import state, county, and ordinance data from CSV files into the database'

    def setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        return webdriver.Chrome(options=chrome_options)

    def extract_text_from_url(self, driver, url):
        try:
            driver.get(url)
            time.sleep(2)  # Allow JavaScript to load
            
            all_text = []
            # Try different selectors in order of preference
            selectors = [
                '.chunk-content',           # Municode content blocks
                '.codes-chunks-pg',         # Full Municode page
                '.main-content',            # Generic main content
                '#mainContent',             # Alternative main content
                'article',                  # Article content
                'body'                      # Fallback to body
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text:
                            all_text.append(text)
                except:
                    continue
            
            combined_text = '\n\n'.join(all_text)
            if not combined_text:
                self.stdout.write(self.style.WARNING(f'No content found using any selector for {url}'))
            return combined_text

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error extracting text from {url}: {str(e)}'))
            return ""

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
            
            # Import ordinances for each county
            driver = self.setup_selenium()
            try:
                for state_dir in os.listdir(data_dir):
                    state_path = os.path.join(data_dir, state_dir)
                    if os.path.isdir(state_path):
                        state_code = state_dir.lower()
                        try:
                            state = State.objects.get(code=state_code)
                            
                            for filename in os.listdir(state_path):
                                if filename.endswith('_specific_urls.csv'):
                                    county_name = filename.split('_')[0]
                                    
                                    try:
                                        county = County.objects.get(state=state, name=county_name)
                                        ordinances_created = 0
                                        
                                        with open(os.path.join(state_path, filename), 'r', encoding='utf-8') as file:
                                            reader = csv.DictReader(file)
                                            for row in reader:
                                                # Extract text using Selenium
                                                # Check if the URL contains a numeric nodeid
                                                if 'nodeid=' in row['url'].lower() and row['url'].split('nodeid=')[-1].isdigit():
                                                    self.stdout.write(
                                                        self.style.WARNING(f'Skipping and deleting URL with numeric nodeid: {row["url"]}')
                                                    )
                                                    # Delete the ordinance if it exists
                                                    Ordinance.objects.filter(county=county, url=row['url']).delete()
                                                    continue

                                                ordinance_text = self.extract_text_from_url(driver, row['url'])
                                                
                                                # use get_or_create in the future to only create
                                                if ordinance_text:
                                                    # Update or create ordinance
                                                    ordinance, created = Ordinance.objects.update_or_create(
                                                        county=county,
                                                        url=row['url'],
                                                        defaults={'text': ordinance_text}
                                                    )
                                                    
                                                    if created:
                                                        ordinances_created += 1
                                                    else:
                                                        self.stdout.write(
                                                            self.style.SUCCESS(
                                                                f'Updated text for existing ordinance: {row["url"]}'
                                                            )
                                                        )
                                                    
                                        self.stdout.write(
                                            self.style.SUCCESS(
                                                f'Successfully imported {ordinances_created} ordinances for {county.name}'
                                            )
                                        )
                                    except County.DoesNotExist:
                                        self.stdout.write(
                                            self.style.WARNING(f'County not found: {county_name}')
                                        )
                        except State.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f'State not found for code: {state_code}')
                            )
            finally:
                driver.quit()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error importing data: {str(e)}')
            )