import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import glob
import shutil # For moving files
from urllib.parse import urlparse
from webdriver_manager.chrome import ChromeDriverManager


# --- Configuration ---
BASE_URL = 'http://desktop.biceps.ch/prive/accueil.html'
DOWNLOAD_ROOT_DIR = 'downloaded_pdfs_selenium' # Main directory for all downloads
CHROMEDRIVER_PATH = 'path/to/your/chromedriver.exe' # <--- IMPORTANT: REPLACE WITH YOUR CHROMEDRIVER PATH!

# Define how long to wait for elements to appear (in seconds)
WAIT_TIME = 10

# --- Helper Functions for Download Management ---
def configure_chrome_options(download_dir):
    """Configures Chrome options for Selenium, including download directory."""
    options = webdriver.ChromeOptions()
    # Set preferences to handle file downloads automatically
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True # Important: Prevents PDFs from opening in a new tab
    }
    options.add_experimental_option("prefs", prefs)
    # options.add_argument("--headless") # Uncomment to run Chrome in the background (no UI)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return options

def get_latest_downloaded_pdf(download_dir, initial_files):
    """Waits for a new PDF file to appear in the download directory."""
    start_time = time.time()
    while time.time() - start_time < WAIT_TIME * 2: # Give it extra time for download
        current_files = set(os.listdir(download_dir))
        new_files = current_files - initial_files
        pdf_files = [f for f in new_files if f.lower().endswith('.pdf')]
        if pdf_files:
            # Sort to get the most recent if multiple (though unlikely for single download)
            latest_pdf = max([os.path.join(download_dir, f) for f in pdf_files], key=os.path.getctime)
            # Ensure download is complete (check if .crdownload or .tmp exists)
            if not latest_pdf.endswith(('.crdownload', '.tmp')):
                print(f"Detected new PDF: {os.path.basename(latest_pdf)}")
                return latest_pdf
        time.sleep(0.5) # Check every half second
    return None

def move_pdf_to_subject_folder(downloaded_file_path, subject_folder):
    """Moves a downloaded PDF from the temp download dir to the subject's folder."""
    if downloaded_file_path and os.path.exists(downloaded_file_path):
        filename = os.path.basename(downloaded_file_path)
        destination_path = os.path.join(subject_folder, filename)
        if not os.path.exists(destination_path): # Avoid overwriting if file already moved/exists
            try:
                shutil.move(downloaded_file_path, destination_path)
                print(f"Moved '{filename}' to '{subject_folder}'")
            except Exception as e:
                print(f"Error moving file {filename}: {e}")
        else:
            print(f"File '{filename}' already exists in '{subject_folder}', skipping move.")
            os.remove(downloaded_file_path) # Clean up duplicate in temp folder
    elif downloaded_file_path:
        print(f"Warning: Downloaded file '{downloaded_file_path}' not found to move.")

# --- Main Scraping Logic ---
def scrape_and_download_pdfs(driver, url, current_subject_folder, visited_urls):
    """
    Recursively explores links on a page, clicks them, and downloads PDFs.
    url: The current URL to scrape.
    current_subject_folder: The local directory to save PDFs for the current subject.
    visited_urls: A set to keep track of visited URLs to prevent infinite loops.
    """
    if url in visited_urls:
        return
    visited_urls.add(url)

    print(f"\nVisiting: {url}")
    try:
        driver.get(url)
        WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, 'body'))) # Wait for body to load
    except TimeoutException:
        print(f"Timeout while loading {url}. Skipping.")
        return
    except Exception as e:
        print(f"Error loading {url}: {e}. Skipping.")
        return

    # Get a list of files already in the download directory BEFORE potential new downloads
    initial_download_files = set(os.listdir(TEMP_DOWNLOAD_DIR))

    # Find all links on the current page
    links_on_page = driver.find_elements(By.TAG_NAME, 'a')
    # Use a list to store hrefs because elements might become stale after clicks
    hrefs_to_explore = []
    for link in links_on_page:
        try:
            href = link.get_attribute('href')
            if href and href not in visited_urls:
                hrefs_to_explore.append(href)
        except StaleElementReferenceException:
            continue # Element went away, skip

    # Try to find elements that might directly trigger a download (e.g., specific buttons, input types)
    # This part might need custom adjustments based on the website's exact HTML structure.
    # For instance, if there's an image that when clicked downloads a PDF.
    # Example: If there are buttons or images that act as download triggers
    download_triggers = driver.find_elements(By.XPATH, "//a[contains(@class, 'download-btn')] | //img[contains(@alt, 'Download PDF')] | //*[contains(@onclick, '.pdf')]")
    for trigger in download_triggers:
        try:
            print(f"Attempting to click a potential download trigger: {trigger.tag_name}")
            trigger.click()
            # Wait for potential download to complete
            downloaded_pdf_path = get_latest_downloaded_pdf(TEMP_DOWNLOAD_DIR, initial_download_files)
            if downloaded_pdf_path:
                move_pdf_to_subject_folder(downloaded_pdf_path, current_subject_folder)
                initial_download_files = set(os.listdir(TEMP_DOWNLOAD_DIR)) # Update after successful move
        except Exception as e:
            print(f"Error clicking download trigger or during download: {e}")
            pass # Continue trying other triggers

    # Now, iterate through the collected links and explore them recursively
    for href in hrefs_to_explore:
        if href.startswith('http') or href.startswith('https'): # Only explore absolute URLs for now
            # Heuristic: If it looks like a PDF link, try to download directly
            if href.lower().endswith('.pdf'):
                print(f"Attempting direct PDF download from: {href}")
                # Selenium's configured browser will handle this if "plugins.always_open_pdf_externally" is True
                # We still need to wait for it to appear in the download directory
                driver.get(href) # Navigating to the PDF link will trigger a download
                downloaded_pdf_path = get_latest_downloaded_pdf(TEMP_DOWNLOAD_DIR, initial_download_files)
                if downloaded_pdf_path:
                    move_pdf_to_subject_folder(downloaded_pdf_path, current_subject_folder)
                    initial_download_files = set(os.listdir(TEMP_DOWNLOAD_DIR)) # Update after successful move
                # Go back to the previous page to continue exploration
                driver.back()
                WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
            elif urlparse(href).netloc == urlparse(BASE_URL).netloc: # Only explore links within the same domain
                # Recursively call for other links that are likely sub-folders/pages
                scrape_and_download_pdfs(driver, href, current_subject_folder, visited_urls)
            else:
                print(f"Skipping external link: {href}")
        else:
            print(f"Skipping relative link (not yet handled for recursive exploration): {href}") # Relative links need urljoin

# --- Main Execution ---
if __name__ == "__main__":
    # Ensure root download directory exists
    os.makedirs(DOWNLOAD_ROOT_DIR, exist_ok=True)
    TEMP_DOWNLOAD_DIR = os.path.join(DOWNLOAD_ROOT_DIR, 'temp_downloads')
    os.makedirs(TEMP_DOWNLOAD_DIR, exist_ok=True)
    print(f"Temporary download directory set to: {TEMP_DOWNLOAD_DIR}")

    chrome_options = configure_chrome_options(TEMP_DOWNLOAD_DIR)
    service = Service(CHROMEDRIVER_PATH)

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.maximize_window() # Optional: maximize browser window

        driver.get(BASE_URL)
        WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        print(f"Successfully loaded main page: {BASE_URL}")

        # Find all subject "folder" links on the main page
        # You'll need to inspect the HTML of desktop.biceps.ch/prive/accueil.html
        # to find the correct selector for these subject boxes.
        # Example: if each subject is within an <a> tag with a specific class or structure
        # I'm making an assumption here based on the image, you'll likely need to refine this selector.
        subject_elements = WebDriverWait(driver, WAIT_TIME).until(
            EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'subject-box')]//ancestor::a"))
            # This XPath looks for a div with class 'subject-box' and then finds its closest ancestor <a> tag.
            # You might need to adjust this depending on the exact HTML.
            # For example, if they are just <a> tags around images: "//a[img]"
        )

        initial_subject_hrefs = [elem.get_attribute('href') for elem in subject_elements]
        initial_subject_names = [elem.text.strip() for elem in subject_elements] # Get text for folder name

        print(f"Found {len(initial_subject_hrefs)} subject links.")

        for i, subject_url in enumerate(initial_subject_hrefs):
            subject_name = initial_subject_names[i] if i < len(initial_subject_names) and initial_subject_names[i] else f"Subject_{i+1}"
            subject_name = subject_name.replace(" ", "_").replace("/", "_").replace("\\", "_") # Sanitize for folder name
            current_subject_folder = os.path.join(DOWNLOAD_ROOT_DIR, subject_name)
            os.makedirs(current_subject_folder, exist_ok=True)
            print(f"\n--- Exploring Subject: {subject_name} ---")

            # A set to keep track of visited URLs for the current subject's exploration path
            visited_urls_for_subject = set()

            # Start recursive scraping from the subject's main URL
            scrape_and_download_pdfs(driver, subject_url, current_subject_folder, visited_urls_for_subject)

            # After exploring a subject, ensure we return to the main page to click the next subject
            driver.get(BASE_URL)
            WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    except Exception as e:
        print(f"An error occurred during the main process: {e}")
    finally:
        if driver:
            driver.quit()
        # Clean up any leftover files in the temporary download directory
        if os.path.exists(TEMP_DOWNLOAD_DIR):
            print(f"Cleaning up temporary download directory: {TEMP_DOWNLOAD_DIR}")
            for f in os.listdir(TEMP_DOWNLOAD_DIR):
                os.remove(os.path.join(TEMP_DOWNLOAD_DIR, f))
            os.rmdir(TEMP_DOWNLOAD_DIR)

    print("\n--- Download process complete ---")