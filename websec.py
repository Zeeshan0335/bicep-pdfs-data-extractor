import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import csv
import re
import time

# --- Configuration ---
LOGIN_URL = "https://citysquares.com/users/sign_in"
HOMEPAGE_URL = "https://citysquares.com/"

EMAIL = "zeshanq1999@gmail.com"
PASSWORD = "Dothedew123"
SEARCH_TERM = "Medical clinics"
SEARCH_LOCATION = "Texas City-league City, TX"
OUTPUT_FILE = "citysquares_medical_clinic_data.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def init_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Uncomment for headless
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--incognito")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    driver = webdriver.Chrome(options=options)
    return driver

def perform_login(driver):
    print("Logging in...")
    driver.get(LOGIN_URL)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "user_email"))
    )
    driver.find_element(By.ID, "user_email").send_keys(EMAIL)
    driver.find_element(By.ID, "user_password").send_keys(PASSWORD)
    driver.find_element(By.NAME, "commit").click()
    WebDriverWait(driver, 20).until(EC.url_changes(LOGIN_URL))
    print("Login successful!")
    return True

def scrape_citysquares():
    driver = init_driver()
    all_data = []

    try:
        if not perform_login(driver):
            print("Login failed.")
            return

        driver.get(HOMEPAGE_URL)
        time.sleep(3)

        print("Performing search...")
        search_term_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[placeholder='I\\'m looking for']"))
        )
        search_location_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Near']")
        search_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Start searching')]")

        search_term_input.send_keys(SEARCH_TERM)
        search_location_input.send_keys(SEARCH_LOCATION)
        search_button.click()

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        print("Search results loaded.")

        # --- NEW: Use page_source & BeautifulSoup ---
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")

        # Get text by lines
        all_text = soup.get_text(separator="\n")
        lines = [line.strip() for line in all_text.split("\n") if line.strip()]

        # Regex for phone numbers
        phone_pattern = re.compile(r"\(\d{3}\)\s*\d{3}-\d{4}")

        temp = {"Name": "", "Address": "", "Phone": ""}
        for line in lines:
            if phone_pattern.search(line):
                temp["Phone"] = line
                all_data.append(temp.copy())
                temp = {"Name": "", "Address": "", "Phone": ""}
            else:
                if not temp["Name"]:
                    temp["Name"] = line
                elif not temp["Address"]:
                    temp["Address"] = line
                else:
                    temp["Address"] += ", " + line  # In case address spans multiple lines

    finally:
        driver.quit()

    if all_data:
        keys = ["Name", "Address", "Phone"]
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_data)
        print(f"✅ Done! Data saved to: {OUTPUT_FILE}")
        print(f"Total listings: {len(all_data)}")
    else:
        print("❌ No data found. Please check selectors or page structure.")

if __name__ == "__main__":
    scrape_citysquares()
