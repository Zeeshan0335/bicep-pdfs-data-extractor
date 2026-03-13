import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse
import time # For adding delays to avoid overwhelming the server

# --- CONFIGURATION (YOU MUST CUSTOMIZE THESE!) ---
# Base URL of your LMS (e.g., "https://my.lms.com/")
LMS_BASE_URL = "https://www.biceps.ch/"

# Login Page URL (the URL where you submit your login credentials)
# Inspect your browser's network tab or form 'action' attribute
LOGIN_URL = "https://admin.biceps.ch/login"

# Your LMS Username and Password
USERNAME = "safiullahrahu1555@gmail.com"
PASSWORD = "@Quantum1555"

# Path to the main dashboard or courses page after successful login
# This is where you expect to see the list of subjects/courses
DASHBOARD_URL = "https://desktop.biceps.ch/prive/accueil.html?_r=1"

# Directory where all downloaded PDFs will be saved
MAIN_DOWNLOAD_DIR = "lms_exercise_pdfs"

# Delay between requests to avoid overwhelming the server (in seconds)
# Be polite! Increase this if you get blocked.
REQUEST_DELAY = 1

# --- GLOBAL SESSION ---
session = requests.Session()

# --- HELPER FUNCTIONS ---

def get_absolute_url(base, relative_url):
    """Combines a base URL and a relative URL to get a full URL."""
    return urljoin(base, relative_url)

def download_file(url, folder_path, filename):
    """Downloads a file to a specified folder."""
    try:
        print(f"  Attempting to download: {filename} from {url}")
        response = session.get(url, stream=True)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, filename)

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  Successfully downloaded: {filename}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  ERROR downloading {url}: {e}")
        return False

def login_lms():
    """
    Attempts to log into the LMS.
    Returns True on success, False on failure.
    YOU MUST CUSTOMIZE THE `login_payload`!
    """
    print("Attempting to log into the LMS...")
    # --- IMPORTANT: CUSTOMIZE THIS PAYLOAD! ---
    # Inspect your LMS login form using browser developer tools (Network tab, Form Data).
    # Find the 'name' attributes for username/email and password fields,
    # and any hidden fields like CSRF tokens.
    login_payload = {
        "username_field_name": USERNAME,  # e.g., 'email', 'user', 'username'
        "password_field_name": PASSWORD,  # e.g., 'pass', 'pwd', 'password'
        # Add any other hidden fields or CSRF tokens here if your LMS requires them.
        # "csrf_token": "VALUE_FROM_PAGE_SOURCE_OR_NETWORK_REQUEST",
        # "remember_me": "on", # Example for a checkbox
    }
    headers = {
        # Sometimes a User-Agent header is needed, or Referer.
        # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        # 'Referer': LOGIN_URL,
    }

    try:
        # Send the POST request to the login URL
        response = session.post(LOGIN_URL, data=login_payload, headers=headers, allow_redirects=True)
        response.raise_for_status() # Check for HTTP errors (4xx or 5xx)

        # A simple check to see if login was successful.
        # You might need to refine this:
        # 1. Check the final URL after redirection (should not be LOGIN_URL).
        # 2. Check for specific text on the expected dashboard page ("Welcome, User!", "My Courses").
        if response.url == LOGIN_URL or "login failed" in response.text.lower() or "incorrect username or password" in response.text.lower():
            print("Login failed. Please verify LOGIN_URL, USERNAME, PASSWORD, and login_payload field names.")
            print(f"Final URL after login attempt: {response.url}")
            return False
        else:
            print(f"Login successful! Redirected to: {response.url}")
            # Optional: Verify we are on the dashboard by fetching it directly
            dashboard_response = session.get(DASHBOARD_URL)
            if dashboard_response.status_code == 200:
                print("Successfully accessed dashboard after login.")
                return True
            else:
                print("Login appeared successful, but couldn't access dashboard.")
                return False

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during login: {e}")
        return False

def scrape_lms_pdfs():
    """Main function to orchestrate the scraping process."""

    # --- Step 1: Login to the LMS ---
    if not login_lms():
        print("Scraping aborted due to login failure.")
        return

    time.sleep(REQUEST_DELAY)

    # --- Step 2: Get Subjects/Courses from Dashboard ---
    print(f"\n--- Scraping Subjects from Dashboard: {DASHBOARD_URL} ---")
    try:
        dashboard_response = session.get(DASHBOARD_URL)
        dashboard_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching dashboard page {DASHBOARD_URL}: {e}")
        return

    dashboard_soup = BeautifulSoup(dashboard_response.text, 'html.parser')
    subject_links = {} # Stores { 'Subject Name': 'Subject URL' }

    # --- IMPORTANT: CUSTOMIZE THIS PART TO FIND SUBJECT LINKS ---
    # Inspect the HTML of your dashboard. Find common patterns for course/subject links.
    # Examples:
    # <a href="/course/math101">Mathematics 101</a>
    # <div class="course-card"><a href="/course/physics">Physics</a></div>
    # <li class="subject-item"><a data-id="123" href="/courses/123">Chemistry</a></li>
    #
    # You might need to look for specific CSS classes, IDs, or HTML tags.
    # This example looks for all 'a' tags with an 'href' that seems to be a course.
    for link_tag in dashboard_soup.find_all('a', href=True):
        href = link_tag['href']
        full_url = get_absolute_url(LMS_BASE_URL, href)

        # Simple heuristic: filter out links that are not likely subject pages
        # This will need to be refined based on your LMS's URL structure
        if '/course/' in full_url or '/subject/' in full_url or '/program/' in full_url:
            # Try to get a meaningful name for the subject (e.g., from the link text)
            subject_name = link_tag.get_text(strip=True) or os.path.basename(urlparse(full_url).path)
            if subject_name and full_url not in subject_links.values(): # Avoid duplicates
                print(f"Found subject: {subject_name} -> {full_url}")
                subject_links[subject_name] = full_url

    if not subject_links:
        print("No subject/course links found on the dashboard.")
        print("Please inspect your LMS dashboard HTML and update the subject link finding logic.")
        return

    total_pdfs_downloaded = 0

    # --- Step 3: Iterate through each Subject/Course ---
    for subject_name, subject_url in subject_links.items():
        print(f"\n--- Entering Subject: {subject_name} ({subject_url}) ---")
        time.sleep(REQUEST_DELAY)

        try:
            subject_response = session.get(subject_url)
            subject_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"ERROR fetching subject page {subject_url}: {e}")
            continue

        subject_soup = BeautifulSoup(subject_response.text, 'html.parser')
        exercise_links = {} # Stores { 'Exercise Name': 'Exercise URL' }

        # --- IMPORTANT: CUSTOMIZE THIS PART TO FIND EXERCISE LINKS WITHIN A SUBJECT ---
        # Similar to finding subjects, inspect the HTML of a subject page.
        # Look for links that lead to individual exercises or sections containing exercises.
        for link_tag in subject_soup.find_all('a', href=True):
            href = link_tag['href']
            full_url = get_absolute_url(subject_url, href) # Use subject_url as base for relative links

            # Simple heuristic: filter for likely exercise or document pages
            if '/exercise/' in full_url or '/quiz/' in full_url or '/lesson/' in full_url or full_url.endswith(('.html', '.php', '.asp')):
                exercise_name = link_tag.get_text(strip=True) or os.path.basename(urlparse(full_url).path)
                if exercise_name and full_url not in exercise_links.values():
                    print(f"  Found exercise/lesson: {exercise_name} -> {full_url}")
                    exercise_links[exercise_name] = full_url

        if not exercise_links:
            print(f"  No exercise/lesson links found in {subject_name}. Moving to next subject.")
            # Even if no exercise links, check for direct PDFs on the subject page itself
            print(f"  Checking for direct PDFs on {subject_name} page...")
            pdfs_found_on_subject_page = 0
            for pdf_link_tag in subject_soup.find_all('a', href=True):
                pdf_href = pdf_link_tag['href']
                full_pdf_url = get_absolute_url(subject_url, pdf_href)
                if full_pdf_url.lower().endswith('.pdf'):
                    pdf_filename = os.path.basename(urlparse(full_pdf_url).path)
                    print(f"  Found direct PDF: {pdf_filename}")
                    subject_download_path = os.path.join(MAIN_DOWNLOAD_DIR, subject_name.replace(" ", "_").replace("/", "-").strip())
                    if download_file(full_pdf_url, subject_download_path, pdf_filename):
                        total_pdfs_downloaded += 1
                        pdfs_found_on_subject_page += 1
            if pdfs_found_on_subject_page == 0:
                print(f"  No direct PDFs found on {subject_name} page either.")
            continue # Move to the next subject

        # --- Step 4: Iterate through each Exercise and Download PDFs ---
        for exercise_name, exercise_url in exercise_links.items():
            print(f"  --- Entering Exercise: {exercise_name} ({exercise_url}) ---")
            time.sleep(REQUEST_DELAY)

            try:
                exercise_response = session.get(exercise_url)
                exercise_response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"  ERROR fetching exercise page {exercise_url}: {e}")
                continue

            exercise_soup = BeautifulSoup(exercise_response.text, 'html.parser')
            pdfs_found_in_exercise = 0

            # Find all 'a' tags that link to PDFs
            for pdf_link_tag in exercise_soup.find_all('a', href=True):
                pdf_href = pdf_link_tag['href']
                full_pdf_url = get_absolute_url(exercise_url, pdf_href) # Use exercise_url as base

                if full_pdf_url.lower().endswith('.pdf'):
                    pdf_filename = os.path.basename(urlparse(full_pdf_url).path)
                    # Create a folder for each subject within the main download directory
                    subject_download_path = os.path.join(MAIN_DOWNLOAD_DIR, subject_name.replace(" ", "_").replace("/", "-").strip())

                    print(f"    Found PDF: {pdf_filename}")
                    if download_file(full_pdf_url, subject_download_path, pdf_filename):
                        total_pdfs_downloaded += 1
                        pdfs_found_in_exercise += 1

            if pdfs_found_in_exercise == 0:
                print(f"    No PDFs found directly linked on {exercise_name} page.")
                print("    (PDFs might be embedded, linked from iframes, or require more interaction.)")

    print(f"\n--- SCRAPING COMPLETE ---")
    print(f"Total PDFs downloaded across all subjects: {total_pdfs_downloaded}")

# --- Run the Scraper ---
if __name__ == "__main__":
    scrape_lms_pdfs()
