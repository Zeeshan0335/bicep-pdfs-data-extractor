import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import csv
import time

# --- Configuration ---
LOGIN_URL = "https://citysquares.com/users/sign_in"
HOMEPAGE_URL = "https://citysquares.com/" # Navigate to homepage after login for interactive search

EMAIL = "zeshanq1999@gmail.com"
PASSWORD = "Dothedew123"
SEARCH_TERM = "Medical clinics" # Confirmed: Medical clinics
SEARCH_LOCATION = "Texas City-league City, TX" # Confirmed: Texas City-league City, TX
OUTPUT_FILE = "citysquares_medical_clinic_data.csv" # Output file name

# Path to your WebDriver executable (e.g., chromedriver.exe)
# If it's in your system PATH, you can just use webdriver.Chrome()
# Otherwise, specify the full path:
# DRIVER_PATH = "/path/to/your/chromedriver" # Uncomment and update if needed

# Headers for BeautifulSoup (used after Selenium gets the page source)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Connection": "keep-alive",
}

# --- Function to initialize WebDriver ---
def init_driver():
    """Initializes and returns a Chrome WebDriver."""
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Run in headless mode (no browser UI)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--incognito") # Use incognito mode
    options.add_argument(f"user-agent={HEADERS['User-Agent']}") # Set user-agent
    try:
        # If chromedriver is in PATH, simply use:
        driver = webdriver.Chrome(options=options)
        # If you need to specify path:
        # driver = webdriver.Chrome(executable_path=DRIVER_PATH, options=options)
        return driver
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        print("Please ensure you have downloaded the correct WebDriver for your browser and it's in your system PATH or specified correctly.")
        return None

# --- Function to perform login ---
def perform_login(driver):
    """
    Navigates to the login page, fills credentials, and attempts login.
    """
    print("Attempting to log in...")
    try:
        driver.get(LOGIN_URL)
        # Wait for the email field to be present.
        # These are common IDs/Names. If login fails, inspect the page.
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "user_email"))
        )

        email_field = driver.find_element(By.ID, "user_email")
        password_field = driver.find_element(By.ID, "user_password")
        login_button = driver.find_element(By.NAME, "commit") # Common name for submit button

        email_field.send_keys(EMAIL)
        password_field.send_keys(PASSWORD)
        login_button.click()

        # Wait for redirection after login. This waits until the URL changes from the LOGIN_URL.
        WebDriverWait(driver, 20).until(
            EC.url_changes(LOGIN_URL)
        )
        print("Login attempt complete. Checking if successful...")
        return True
    except TimeoutException:
        print("Login timed out. Could not find login elements or page did not redirect after login.")
        return False
    except NoSuchElementException as e:
        print(f"Login failed: Could not find an element. Check your selectors for email, password, or login button. Error: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during login: {e}")
        return False

# --- Function to parse a single listing ---
def parse_listing(listing_soup):
    """
    Parses a single business listing and extracts relevant data.
    *** These selectors are guesses. You MUST verify them on the search results page. ***
    """
    data = {}
    try:
        # Attempt to find title, detail URL, address, and phone number
        # Inspect the search results page (e.g., https://citysquares.com/search?utf8=%E2%9C%93&search%5Bterm%5D=medical+clinics+&search%5Blocation%5D=Texas+City-league+City%2C+TX)
        # Right-click on a business title, address, phone number and select "Inspect" (F12) to find their actual tags and classes.

        # Title and Detail URL (often combined in an <a> tag)
        title_tag = listing_soup.find("a", class_="listing-name") # Common class for listing titles
        if title_tag:
            data["Title"] = title_tag.text.strip()
            data["Detail URL"] = title_tag.get("href", "N/A")
        else:
            data["Title"] = "N/A"
            data["Detail URL"] = "N/A"

        # Address
        address_tag = listing_soup.find("span", class_="address-line") # Common class for address
        data["Address"] = address_tag.text.strip() if address_tag else "N/A"

        # Phone Number
        phone_tag = listing_soup.find("span", class_="phone-number") # Common class for phone number
        data["Phone"] = phone_tag.text.strip() if phone_tag else "N/A"

        # Add more fields here if needed, following the same inspection process.

    except Exception as e:
        print(f"Error parsing listing: {e}")
        return {}
    return data

# --- Main scraping logic ---
def scrape_citysquares():
    """
    Main function to orchestrate the scraping process, including login, interactive search, and data export.
    """
    driver = init_driver()
    if not driver:
        return

    all_data = []

    try:
        # 1. Perform Login
        if not perform_login(driver):
            print("Login failed or timed out. Exiting scraper.")
            return

        print("Successfully logged in. Proceeding to homepage for interactive search.")

        # 2. Navigate to the homepage
        driver.get(HOMEPAGE_URL)
        time.sleep(3) # Give page a moment to render after navigation

        # 3. Perform interactive search on the homepage
        print("Performing interactive search...")
        try:
            # These selectors are based on the image provided and common website structures.
            # If search fails, manually inspect citysquares.com homepage using DevTools (F12)
            # to find the correct selectors for the search inputs and button.

            # "I'm looking for" input field (using placeholder text)
            search_term_input = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[placeholder='I\\'m looking for']"))
            )

            # "Near" input field (using placeholder text)
            search_location_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Near']")

            # "Start searching" button (using XPath for button text)
            search_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Start searching')]")

            search_term_input.send_keys(SEARCH_TERM)
            search_location_input.send_keys(SEARCH_LOCATION)
            search_button.click()

            # Wait for the search results page to load after clicking the search button
            # This waits for an element that is *unique* to the search results page and indicates it has loaded.
            # Inspect the search results page (e.g., https://citysquares.com/search?utf8=%E2%9C%93&search%5Bterm%5D=medical+clinics+&search%5Blocation%5D=Texas+City-league+City%2C+TX)
            # Right-click on a business listing and select "Inspect" (F12) to find its main container tag and class.
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.listing-card")) # Common class for a listing container
            )
            print("Interactive search complete. Search results page loaded.")

        except TimeoutException:
            print("Timeout during interactive search. Could not find search elements or results page did not load.")
            return
        except NoSuchElementException as e:
            print(f"Interactive search failed: Could not find an element. Check your selectors for search inputs or button. Error: {e}")
            return

        # 4. Get page source and parse with BeautifulSoup
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")

        # --- IMPORTANT: UPDATE THIS SELECTOR ---
        # This selector must match the main container for each individual listing on the search results page.
        # It should be the same selector you used in the WebDriverWait above.
        listings = soup.find_all("div", class_="listing-card") # Common class for a listing container

        if not listings:
            print("No listings found on this page with the current selector. Please inspect HTML and update 'listings' selector.")
        else:
            print(f"Found {len(listings)} listings on the current page.")
            for listing in listings:
                parsed_data = parse_listing(listing)
                if parsed_data:
                    all_data.append(parsed_data)

        # --- Basic Pagination (for the first page only as requested) ---
        # To scrape multiple pages, you would add a loop here.
        # You'd need to find the "Next" button selector on the search results page,
        # click it, wait for the next page to load, and repeat the scraping process.

    finally:
        if driver:
            driver.quit() # Close the browser when done

    # --- Save data to CSV ---
    if all_data:
        # Determine CSV headers from the keys of the first dictionary
        keys = all_data[0].keys()
        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_data)
        print(f"\nScraping complete! Data saved to {OUTPUT_FILE}")
        print(f"Total listings scraped: {len(all_data)}")
    else:
        print("No data was scraped or saved. Please check selectors and website structure.")

# --- Run the scraper ---
if __name__ == "__main__":
    scrape_citysquares()