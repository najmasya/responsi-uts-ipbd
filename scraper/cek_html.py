from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

try:
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
except Exception:
    driver = webdriver.Chrome(options=options)

driver.get("https://www.wired.com")
time.sleep(3)

cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/story/']")
print(f"Total cards: {len(cards)}")

for card in cards:
    html = card.get_attribute("innerHTML")
    if html and len(html) > 50:
        ancestor = card
        for i in range(5):
            parent = driver.execute_script("return arguments[0].parentElement;", ancestor)
            if parent is None:
                break
            ancestor = parent
            print(f"\n=== LEVEL {i+1} UP ===")
            print(ancestor.get_attribute("innerHTML")[:1000])
            print("="*60)
        break

driver.quit()