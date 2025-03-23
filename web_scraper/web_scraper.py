"""
Web scraper module for extracting state and county information from municode.com.
Uses Selenium and BeautifulSoup to parse and extract data from the website.
"""
import re
import time

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
import os


def get_states(driver: webdriver.Chrome):
    """
    Get a list of states from municode.com

    Args:
    driver (webdriver.Chrome): the webdriver to use

    Returns:
    data_out (pd.DataFrame): a dataframe of states
    """
    assert isinstance(driver, webdriver.Chrome)
    driver.refresh()

    url = "https://library.municode.com"
    driver.get(url)

    time.sleep(2)

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    state_links = soup.find_all('a', href=True)

    r1 = []
    for link in state_links:
        href = link['href']
        if re.match(r'https://library\.municode\.com/[a-z]{2}$', href):
            state_name = link.text.strip()
            if state_name:
                r1.append({
                    'state_name': state_name,
                    'state_code': href[-2:],
                    'state_url': href
                })

    state_list = pd.DataFrame(r1)
    state_list = state_list.drop_duplicates().reset_index(drop=True)
    state_list = state_list.rename(
        columns={
            'state_name': 'State',
            'state_code': 'State Code',
            'state_url': 'URL'
        }
    )

    csv_filename = 'state_urls.csv'
    state_list.to_csv(csv_filename, index=False)

    return state_list


def get_counties_by_state(state: str, driver: webdriver.Chrome):
    """
    Get a list of counties by state from municode.com

    Args:
    state (str): the state to get counties from
    driver (webdriver.Chrome): the webdriver to use

    Returns:
    data_out (pd.DataFrame): a dataframe of counties by state
    """
    assert isinstance(driver, webdriver.Chrome)
    driver.refresh()

    url = f"https://library.municode.com/{state}"
    driver.get(url)

    time.sleep(2)

    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    county_links = soup.find_all('a', class_='index-link', href=True)

    r1 = []
    for link in county_links:
        href = link['href']
        if re.match(r'https://library\.municode\.com/\S+', href):
            county_name = link.text.strip()
            if county_name:
                r1.append({'state': state.upper(), 'county': county_name, 'url': href})

    counties_list = pd.DataFrame(r1)

    csv_filename = f'data/{state}_county_urls.csv'
    counties_list.to_csv(csv_filename, index=False)

    return counties_list

def get_ordinance_by_county(csv_file, driver: webdriver.Chrome):
    counties_data = pd.read_csv(os.path.join('data', csv_file))

    for _, row in counties_data.iterrows():
        county_url = row['url'] + '/codes/code_of_ordinances'
        driver.get(county_url)
        time.sleep(2)

        # Check if the URL redirects
        if driver.current_url != county_url:
            print(f"Skipping {row['county']} as the URL redirects.")
            continue

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        specific_links = soup.find_all('a', href=True)
        r2 = []
        for link in specific_links:
            href = link['href']

            if re.match(county_url + r'\?nodeId=\S+', href):
                link_text = link.text.strip()
                if link_text:
                    r2.append({'county': row['county'], 'url': href, 'link_text': link_text})

        specific_data = pd.DataFrame(r2)

        # Create a folder for the state if it doesn't exist
        state_folder = os.path.join('data', csv_file[:2])
        os.makedirs(state_folder, exist_ok=True)

        # Save the county-specific URLs in the state's folder
        specific_csv_filename = os.path.join(
            state_folder, f'{row["county"].replace(" ", "_")}_specific_urls.csv'
        )
        specific_data.to_csv(specific_csv_filename, index=False)


def main():
    """Main function to scrape state and county data from municode.com."""
    driver = webdriver.Chrome()
    all_states = pd.read_csv('state_urls.csv')
    
    data_folder = 'data'
    list_states = list(all_states["State Code"])
    for state in list_states:
        csv_files = [f for f in os.listdir(data_folder) if f.endswith('_county_urls.csv')]

        for csv_file in csv_files:
            get_ordinance_by_county(csv_file, driver)
            
        # get_counties_by_state(state, driver)

    driver.quit()
    return 0


if __name__ == '__main__':
    main()
