import requests
from bs4 import BeautifulSoup
import os
import time
import re

# --- Configuration ---
# IMPORTANT: Updated base URL to reflect the new subjects list domain
LMS_BASE_URL = "https://desktop.biceps.ch/"
# IMPORTANT: This is the URL where the login form *submits* its data.
LOGIN_URL = "https://admin.biceps.ch/login"

# IMPORTANT: YOU MUST VERIFY THESE 'name' ATTRIBUTES by inspecting the login page HTML.
# 1. Open https://admin.biceps.ch/login in your browser.
# 2. Right-click on the email/username input field and choose "Inspect" (or "Inspect Element").
# 3. Look for the 'name' attribute in the <input> tag. E.g., <input type="text" name="user_email">
# 4. Do the same for the password input field.
# 5. Update the keys in LOGIN_PAYLOAD below with the EXACT 'name' values you find.
LOGIN_PAYLOAD = {
    'email': 'safiullahrahu1555@gmail.com', # <--- VERIFY THIS 'name' ATTRIBUTE
    'password': '@Quantum1555'  # <--- VERIFY THIS 'name' ATTRIBUTE
}

# IMPORTANT: After logging in, you will be redirected to a dashboard or subjects page.
# Find the URL of that page and put it here. This is the page that lists all subjects.
SUBJECTS_LIST_URL = "https://desktop.biceps.ch/prive/accueil.html?_r=1"

# IMPORTANT: Path where PDFs will be saved
DOWNLOAD_DIRECTORY = "lms_pdfs"

# User-Agent to mimic a browser, sometimes helps avoid blocking
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": LMS_BASE_URL # May be useful for some sites
}

# Create a session to persist cookies and headers across requests
session = requests.Session()
session.headers.update(HEADERS)


# Ensure the download directory exists
if not os.path.exists(DOWNLOAD_DIRECTORY):
    os.makedirs(DOWNLOAD_DIRECTORY)
    print(f"Created download directory: {DOWNLOAD_DIRECTORY}")

def get_page_content(url):
    """Fetches the content of a given URL using the active session."""
    try:
        response = session.get(url, timeout=10) # Set a timeout for requests
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def download_file(url, folder_path, filename=None):
    """Downloads a file from a URL to a specified folder using the active session."""
    try:
        response = session.get(url, stream=True, timeout=30) # Use stream=True for large files
        response.raise_for_status()

        if not filename:
            # Try to get filename from Content-Disposition header, otherwise from URL
            if "Content-Disposition" in response.headers:
                fname = re.findall(r"filename=\"?([^\"]+)\"?", response.headers["Content-Disposition"])
                if fname:
                    filename = fname[0]
            if not filename:
                filename = os.path.basename(url.split("?")[0]) # Remove query parameters

        file_path = os.path.join(folder_path, filename)

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded: {filename} to {folder_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return False
    except IOError as e:
        print(f"Error writing file {filename}: {e}")
        return False

def scrape_lms():
    """Main function to scrape the LMS and download PDFs."""
    print("Attempting to log in...")
    print(f"Login URL: {LOGIN_URL}")
    print(f"Login Payload (field names are crucial): {LOGIN_PAYLOAD}") # Print payload to confirm

    try:
        # First, fetch the login page to potentially get CSRF tokens or other dynamic data
        login_page_response = session.get(LOGIN_URL, headers=HEADERS)
        login_page_soup = BeautifulSoup(login_page_response.text, "html.parser")

        # Check for CSRF token (common security measure)
        # Inspect the login page for a hidden input field, often named like 'csrf_token' or '__RequestVerificationToken'
        # Example: <input type="hidden" name="csrf_token" value="some_random_value">
        csrf_token_field = login_page_soup.find('input', {'name': 'csrf_token'}) # Adjust 'csrf_token' if needed
        if not csrf_token_field:
            # Try other common names for CSRF tokens
            csrf_token_field = login_page_soup.find('input', {'name': '__RequestVerificationToken'})
        
        if csrf_token_field:
            csrf_token_name = csrf_token_field.get('name')
            csrf_token_value = csrf_token_field.get('value')
            print(f"Found CSRF token: name='{csrf_token_name}', value='{csrf_token_value}'")
            # Add the CSRF token to your payload with its actual name
            LOGIN_PAYLOAD[csrf_token_name] = csrf_token_value
        else:
            print("No common CSRF token field found on the login page.")


        # Perform the login POST request
        login_response = session.post(LOGIN_URL, data=LOGIN_PAYLOAD, headers=HEADERS, timeout=15, allow_redirects=True)
        
        print(f"Login attempt status code: {login_response.status_code}")
        print(f"Final URL after login attempt: {login_response.url}")
        print(f"Response content (first 1000 chars): {login_response.text[:1000]}...") # Print snippet for debugging

        # Check for explicit error messages on the login page itself
        error_message = None
        for selector in ['div.alert.danger', 'span.error', '.error-message', 'div[role="alert"]']:
            found_error = BeautifulSoup(login_response.text, "html.parser").select_one(selector)
            if found_error and found_error.get_text(strip=True):
                error_message = found_error.get_text(strip=True)
                break
        
        if error_message:
            print(f"Login failed. Website error message: {error_message}")
            print("Please correct your LOGIN_PAYLOAD field names or credentials based on this message.")
            return

        # Check if login was successful. This often involves checking the final URL after redirects,
        # or looking for specific elements on the page that only appear after login.
        if login_response.url != LOGIN_URL and (LMS_BASE_URL in login_response.url or "dashboard" in login_response.url.lower() or "accueil" in login_response.url.lower()):
             print(f"Successfully logged in. Redirected to: {login_response.url}")
        elif "logout" in login_response.text.lower() or "my courses" in login_response.text.lower() or "welcome" in login_response.text.lower() or "profil" in login_response.text.lower():
            # Look for common success indicators in the response text, even if URL didn't change
            print("Login successful (indicated by page content).")
        else:
            print("\nLogin might have failed. No clear success indicators found after POSTing to login page.")
            print("To debug: Carefully verify 'name' attributes in LOGIN_PAYLOAD and check for CAPTCHA or other security measures.")
            return # Exit if login seems to fail

    except requests.exceptions.RequestException as e:
        print(f"Login failed: {e}")
        print("Please check LOGIN_URL, LOGIN_PAYLOAD, and your internet connection.")
        return

    print(f"\nStarting scraping from subject list: {SUBJECTS_LIST_URL}")

    # Step 1: Get the list of subjects after login
    subject_list_soup = get_page_content(SUBJECTS_LIST_URL)
    if not subject_list_soup:
        print("Could not retrieve subject list page after login. Exiting.")
        print("Ensure SUBJECTS_LIST_URL is correct for the logged-in state and that authentication was successful.")
        return

    # IMPORTANT: Adjust this selector to find links to individual subjects.
    # For 'accueil.html', subjects might be listed in specific divs or tables.
    # You will NEED to inspect the HTML of https://desktop.biceps.ch/prive/accueil.html?_r=1
    # to find the correct selector for subject links.
    # I'm using a very general `find_all("a", href=True)` here, which might pick up too many links.
    subject_links = subject_list_soup.find_all("a", href=True) # Finds all <a> tags with an href attribute
    
    subjects = {}
    for link in subject_links:
        href = link.get('href')
        if not href:
            continue

        # Construct full URL. Handle relative paths and absolute paths.
        if href.startswith("http"):
            full_url = href
        elif href.startswith("/"):
            full_url = f"{LMS_BASE_URL.rstrip('/')}{href}"
        else:
            # Assumes relative to current page if not starting with / or http
            # This might need adjustment based on how the LMS constructs relative URLs
            current_path = "/".join(SUBJECTS_LIST_URL.split('/')[:-1]) # Get parent directory of current subject list URL
            full_url = f"{current_path}/{href}"
            
            # Ensure it's under the base LMS URL
            if not full_url.startswith(LMS_BASE_URL):
                continue # Skip if it's not part of the LMS domain

        # IMPORTANT: Refine this condition to only include actual subject pages
        # For 'accueil.html', subject links might contain specific keywords, path segments, or query parameters.
        # Example: if "subject_id=" in full_url or "/course/" in full_url or "/courses/" in full_url
        # You need to manually identify patterns in the subject links on that page.
        # As a general heuristic, I'll look for links within the same domain that are not for 'accueil.html' itself
        # and have some descriptive text.
        if (LMS_BASE_URL in full_url and 
            "accueil.html" not in full_url and # Exclude the main page itself
            "login" not in full_url and # Exclude login links
            link.get_text(strip=True) and # Ensure link has text
            len(link.get_text(strip=True)) > 5): # Ensure text is reasonably long for a subject title

            subject_name = link.get_text(strip=True).replace(" ", "_").replace("/", "").replace(":", "").replace("?", "").lower()
            if subject_name and len(subject_name) > 0:
                subjects[subject_name] = full_url

    if not subjects:
        print("No subjects found. Please carefully inspect https://desktop.biceps.ch/prive/accueil.html?_r=1")
        print("You need to identify the HTML structure for subject links and refine the `subject_links` selector and filtering logic.")
        return

    print(f"Found {len(subjects)} subjects. Processing...")

    for subject_name, subject_url in subjects.items():
        print(f"\n--- Processing Subject: {subject_name} ({subject_url}) ---")
        subject_folder = os.path.join(DOWNLOAD_DIRECTORY, subject_name)
        if not os.path.exists(subject_folder):
            os.makedirs(subject_folder)
            print(f"Created subject folder: {subject_folder}")

        subject_page_soup = get_page_content(subject_url)
        if not subject_page_soup:
            print(f"Could not retrieve subject page for {subject_name}. Skipping.")
            continue

        # Step 2: Find PDF links on the subject page
        # IMPORTANT: Adjust this selector to find links pointing to PDF files.
        # This looks for <a> tags where the href attribute ends with ".pdf"
        pdf_links = subject_page_soup.find_all("a", href=lambda href: href and href.endswith(".pdf"))

        if not pdf_links:
            print(f"No PDF links found for {subject_name}. Skipping.")
            continue

        print(f"Found {len(pdf_links)} PDF files for {subject_name}.")

        for pdf_link in pdf_links:
            pdf_href = pdf_link["href"]
            
            # Construct full PDF URL carefully
            if pdf_href.startswith("http"):
                pdf_full_url = pdf_href
            elif pdf_href.startswith("/"):
                pdf_full_url = f"{LMS_BASE_URL.rstrip('/')}{pdf_href}"
            else:
                # Assumes relative to the current subject page URL
                pdf_full_url = f"{'/'.join(subject_url.split('/')[:-1])}/{pdf_href}"
                if not pdf_full_url.startswith("http"):
                     pdf_full_url = f"{LMS_BASE_URL.rstrip('/')}/{pdf_full_url.lstrip('/')}"

            # Optional: Extract a more descriptive filename from the link text or title attribute
            suggested_filename = pdf_link.get_text(strip=True)
            if suggested_filename:
                # Sanitize filename (remove invalid characters) and ensure it ends with .pdf
                suggested_filename = re.sub(r'[\\/:*?"<>|]', '', suggested_filename)
                if not suggested_filename.lower().endswith(".pdf"):
                    suggested_filename += ".pdf"
            else:
                suggested_filename = None # Let download_file determine from URL/header

            print(f"Attempting to download PDF from: {pdf_full_url}")
            download_file(pdf_full_url, subject_folder, suggested_filename)

            # IMPORTANT: Be polite! Add a delay between downloads to avoid overwhelming the server.
            time.sleep(1) # Wait 1 second before the next download

    print("\nScraping complete!")

if __name__ == "__main__":
    # Consider adding a check for robots.txt before starting
    # robots_url = f"{LMS_BASE_URL.rstrip('/')}/robots.txt"
    # print(f"Checking robots.txt at {robots_url} (manual check required)")
    # You should manually review the website's robots.txt and Terms of Service.

    scrape_lms()
