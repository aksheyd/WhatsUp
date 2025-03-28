from playwright.sync_api import sync_playwright

def scrape_with_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://library.municode.com/ca/amador_city/codes/code_of_ordinances?nodeId=AMADOR_MUNICIPAL_CODE")
        page.wait_for_timeout(5000)  # Wait for JavaScript to load (adjust as needed)
        content = page.content()
        browser.close()
        return content

html_content = scrape_with_playwright()

# Parse the HTML content with BeautifulSoup
from bs4 import BeautifulSoup

soup = BeautifulSoup(html_content, "html.parser")
elements = soup.find_all("p")
for element in elements:
    print(element.text)
