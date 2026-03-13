import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException, WebDriverException

def setup_driver(download_dir):
    """
    Sets up the Selenium WebDriver with preferences for headless mode and PDF downloads.

    Args:
        download_dir (str): The directory where downloaded files will be saved.

    Returns:
        webdriver.Chrome: The configured Chrome WebDriver instance.
    """
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Run in headless mode (no browser UI) - Uncomment for production
    chrome_options.add_argument("--no-sandbox") # Required for some environments
    chrome_options.add_argument("--disable-dev-shm-usage") # Required for some environments

    # Set download preferences for Chrome
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,  # Do not ask where to save
        "download.directory_upgrade": True,
        # Crucial: Ensures PDFs are downloaded instead of opening in the browser tab
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Use WebDriver Manager to automatically download and manage ChromeDriver
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
    except ImportError:
        print("webdriver_manager not found. Please install it using 'pip install webdriver_manager'.")
        print("Alternatively, ensure 'chromedriver' is in your system's PATH or specify its path manually.")
        # Fallback: assuming chromedriver is in PATH or manually specified
        service = Service() # Default service assumes chromedriver in PATH

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login(driver, login_url, username, password):
    """
    Handles the login process for the website.

    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance.
        login_url (str): The URL of the login page.
        username (str): The username for login.
        password (str): The password for login.

    Returns:
        bool: True if login is successful, False otherwise.
    """
    print(f"\n--- Attempting to log in to: {login_url} ---")
    try:
        driver.get(login_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2) # Give page time to render

        # Attempt to find username/email input field
        try:
            username_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='email' or @type='text' or @name='email' or @id='email' or @name='username' or @id='username']"))
            )
            username_field.send_keys(username)
            print("  Entered username.")
        except TimeoutException:
            print("  Could not find username/email input field. Check selectors.")
            return False

        # Attempt to find password input field
        try:
            password_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='password' or @name='password' or @id='password']"))
            )
            password_field.send_keys(password)
            print("  Entered password.")
        except TimeoutException:
            print("  Could not find password input field. Check selectors.")
            return False

        # Attempt to find and click the login button
        try:
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' or contains(text(),'Login') or contains(text(),'Connexion')] | //input[@type='submit' and (@value='Login' or @value='Connexion')]"))
            )
            login_button.click()
            print("  Clicked login button.")
        except TimeoutException:
            print("  Could not find or click login button. Check selectors.")
            return False

        # Wait for navigation after login.
        # The output shows redirection to 'https://admin.biceps.ch/front'
        WebDriverWait(driver, 15).until(
            EC.url_contains("front") # Check if the URL contains "front"
        )
        print(f"  Login attempt complete. Current URL: {driver.current_url}")

        # Now, check if the current URL is the expected post-login page.
        # If it contains "front", we consider it successful for now.
        if "front" in driver.current_url:
            print("  Successfully logged in and redirected to the 'front' page.")

            # --- Handle the "Force Logout" pop-up ---
            try:
                # Increased timeout for the force logout button
                force_logout_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'FORCER LA DÉCONNEXION')]"))
                )
                print("  'Force Logout' pop-up detected. Clicking 'FORCER LA DÉCONNEXION'.")
                force_logout_button.click()
                time.sleep(5) # Increased sleep after clicking to allow for redirect/action
                print("  Clicked 'FORCER LA DÉCONNEXION'.")
                # After forcing logout, it might redirect back to login or to the main page.
                # We'll assume it eventually leads to the main content page or allows re-login.
                # For this script, we'll just continue as if it resolved the issue.
            except TimeoutException:
                print("  'Force Logout' pop-up not detected or did not appear within timeout.")
            except Exception as e:
                print(f"  Error handling 'Force Logout' pop-up: {e}")
            # --- End of pop-up handling ---

            return True
        else:
            print("  Login might not have been successful or redirected to an unexpected page.")
            return False

    except Exception as e:
        print(f"An error occurred during login: {e}")
        return False

def get_clickable_elements(driver):
    """
    Identifies clickable elements on the current page that are likely navigation options or folders.
    This version will be even more aggressive in finding potential clickable elements,
    especially focusing on `div` elements with text that match the subject names
    from the screenshots, and other general interactive elements.
    """
    found_elements = []
    original_frame = None

    # Store the current frame context before attempting to switch
    try:
        original_frame = driver.execute_script("return window.frameElement;")
    except WebDriverException:
        # This can happen if not in an iframe, or if driver state is problematic
        original_frame = None

    # Check for iframes first and switch to them if found
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    if iframes:
        print(f"  Found {len(iframes)} iframe(s). Searching within each.")
        for i, iframe in enumerate(iframes):
            try:
                driver.switch_to.frame(iframe)
                print(f"  Switched to iframe {i+1}.")
                time.sleep(1) # Give it a moment to load content

                # Search for elements within this iframe
                elements_in_iframe = _find_elements_in_current_frame(driver)
                if elements_in_iframe:
                    print(f"    Found {len(elements_in_iframe)} elements in iframe {i+1}.")
                    found_elements.extend(elements_in_iframe)
                else:
                    print(f"    No elements found in iframe {i+1}.")

                # Switch back to default content or parent frame to continue searching other iframes
                driver.switch_to.default_content()
                if original_frame: # If we started in a nested iframe, switch back to it
                    driver.switch_to.frame(original_frame)
                print(f"  Switched back from iframe {i+1}.")
            except Exception as e:
                print(f"  Error processing iframe {i+1}: {e}")
                # Try to switch back to default content if an error occurs within an iframe
                try:
                    driver.switch_to.default_content()
                    if original_frame:
                        driver.switch_to.frame(original_frame)
                except:
                    pass # Ignore errors during emergency switch back
                continue
    else:
        # If no iframes, search in the default content
        print("  No iframes found. Searching in default content.")
        found_elements.extend(_find_elements_in_current_frame(driver))

    # Deduplicate elements by their outerHTML or a unique identifier
    unique_elements = {}
    for elem in found_elements:
        try:
            # Use a robust attribute for uniqueness, like outerHTML, a unique ID, or the text content
            element_key = elem.get_attribute('id') or elem.get_attribute('href') or elem.text.strip() or elem.get_attribute('outerHTML')
            if element_key and element_key not in unique_elements:
                unique_elements[element_key] = elem
        except StaleElementReferenceException:
            continue

    return list(unique_elements.values())

def _find_elements_in_current_frame(driver):
    """Helper function to find elements within the currently active frame."""
    elements_in_frame = []

    # Strategy 1: Look for divs, a, or button tags that contain specific known labels
    all_known_labels = ["FRANÇAIS", "SILABO", "ANGLAIS", "GÉOGRAPHIE SCIENCES", "ALLEMAND", "MATHS", "LOGIQUE", "VOCATINO",
                        "CONJUGAISON", "GRAMMAIRE", "ORTHOGRAPHE", "COMPRÉHENSION", "VERBES SEULS", "TEXTES À TROUS",
                        "PDF", "Annexes Théoriques", "PASSÉ - PRÉSENT - FUTUR", "IMPARFAIT - PASSÉ SIMPLE",
                        "LA CONDITION INTRODUITE PAR SI", "FUTUR SIMPLE - CONDITIONNEL PRÉSENT"]

    # Create XPath conditions for each label, ensuring case-insensitivity
    label_xpath_conditions = " or ".join([
        f"contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{label.lower()}')"
        for label in all_known_labels
    ])

    # Broad XPath to capture any div, a, or button with text matching our labels
    broad_text_xpath = f"//*[self::div or self::a or self::button][({label_xpath_conditions})]"

    try:
        elements = driver.find_elements(By.XPATH, broad_text_xpath)
        for elem in elements:
            if elem.is_displayed() and elem.is_enabled() and elem.size['width'] > 0 and elem.size['height'] > 0:
                elements_in_frame.append(elem)
    except Exception as e:
        print(f"  Error with broad_text_xpath: {e}")
        pass

    # Strategy 2: Look for other clickable elements based on common patterns and visual cues
    generic_selectors = [
        (By.CSS_SELECTOR, "div[onclick]"), # Divs with onclick handler
        (By.TAG_NAME, "a"), # Standard links
        (By.TAG_NAME, "button"), # Standard buttons
        # Broader CSS selectors for elements that look like boxes, folders, or interactive items
        (By.CSS_SELECTOR, "div[class*='box'], div[class*='folder'], div[class*='item'], div[class*='option'], div[style*='background-image']"),
        # Any element that has significant text content and is displayed and has a non-zero size
        # and has either a style, class, id, onclick, or href attribute (to filter out purely structural elements)
        (By.XPATH, "//*[self::div or self::a or self::button or self::span or self::li][string-length(normalize-space(.)) > 0 and (@style or @class or @id or @onclick or @href or @tabindex='0')]"),
        # Very broad selector for any element with text, excluding script/style tags
        (By.XPATH, "//*[string-length(normalize-space(.)) > 0 and not(self::script or self::style)]")
    ]

    for selector_type, selector_value in generic_selectors:
        try:
            elements = driver.find_elements(selector_type, selector_value)
            for elem in elements:
                if elem.is_displayed() and elem.is_enabled() and elem.size['width'] > 0 and elem.size['height'] > 0:
                    if elem.text.strip() or elem.get_attribute('href') or elem.get_attribute('onclick'):
                        elements_in_frame.append(elem)
        except Exception as e:
            pass

    # Add more verbose logging for found elements
    if elements_in_frame:
        print(f"  DEBUG: Found {len(elements_in_frame)} elements in current frame:")
        for i, elem in enumerate(elements_in_frame):
            try:
                print(f"    Element {i+1}: Tag: {elem.tag_name}, Text: '{elem.text.strip()}', Class: '{elem.get_attribute('class')}', ID: '{elem.get_attribute('id')}', Onclick: '{elem.get_attribute('onclick')}', Href: '{elem.get_attribute('href')}', OuterHTML (partial): '{elem.get_attribute('outerHTML')[:100]}...'")
            except StaleElementReferenceException:
                print(f"    Element {i+1}: Stale element reference (could not log details).")
            except Exception as log_error:
                print(f"    Element {i+1}: Error logging element details: {log_error}")
    else:
        print("  DEBUG: No elements found in current frame with current selectors.")

    return elements_in_frame


def traverse_and_download(driver, url, current_download_path, visited_urls, target_subject=None):
    """
    Recursively traverses the website, clicking on options and managing PDF downloads.

    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance.
        url (str): The URL of the current page to traverse.
        current_download_path (str): The local directory path corresponding to the current website level.
        visited_urls (set): A set to keep track of visited URLs to prevent infinite loops.
        target_subject (str, optional): If provided, the script will only attempt to click this subject/option.
                                        Otherwise, it will click all found elements.
    """
    if url in visited_urls:
        print(f"Skipping already visited URL: {url}")
        return
    visited_urls.add(url)

    print(f"\n--- Navigating to: {url} ---")
    try:
        driver.get(url)
        # Wait for the page to load (e.g., until the body element is present)
        WebDriverWait(driver, 30).until( # Increased timeout for page load
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(7) # Increased sleep to give more time for dynamic content to load
    except TimeoutException:
        print(f"Timeout while loading {url}. Skipping this path.")
        return
    except Exception as e:
        print(f"Error navigating to {url}: {e}. Skipping this path.")
        return

    # Get potential clickable elements on the current page
    elements_on_page = get_clickable_elements(driver)
    print(f"Found {len(elements_on_page)} potential clickable elements on {url}")

    elements_to_process = []
    if target_subject:
        print(f"Attempting to find and process only '{target_subject}' on this page.")
        found_target_element = None
        for elem in elements_on_page:
            # Case-insensitive comparison for the target subject
            if target_subject.lower() in elem.text.strip().lower():
                found_target_element = elem
                break
        
        if found_target_element:
            elements_to_process.append(found_target_element)
            print(f"  Target subject '{target_subject}' found. Will attempt to click it.")
        else:
            print(f"  Target subject '{target_subject}' not found on this page. Exiting this branch.")
            return # Exit if target not found
    else:
        elements_to_process = elements_on_page # Process all found elements if no target_subject
        print("  No specific target subject. Will attempt to click all found elements.")

    if not elements_to_process:
        print(f"No clickable navigation elements to process at {url}. End of this branch.")
        return

    # Store the original window handle (for multi-tab scenarios, though unlikely here)
    original_window = driver.current_window_handle

    # Iterate over elements_to_process. Need to re-find them in the loop for robustness.
    num_elements_to_process = len(elements_to_process)
    for i in range(num_elements_to_process):
        try:
            # Re-get the elements list for the current page to avoid StaleElementReferenceException
            # This is crucial because `driver.back()` invalidates references.
            # If target_subject is specified, we need to re-find it specifically.
            if target_subject:
                re_found_element = None
                # Re-scan the page for the specific target element
                for elem in get_clickable_elements(driver):
                    if target_subject.lower() in elem.text.strip().lower():
                        re_found_element = elem
                        break
                if not re_found_element:
                    print(f"  Target subject '{target_subject}' became stale or disappeared after re-fetch. Skipping.")
                    continue
                element = re_found_element
                # After clicking the target subject, subsequent recursive calls should explore all options
                # within that new path, so we set target_subject to None for the recursive call.
                next_target_subject = None
            else:
                # If no target subject, re-find all elements and pick by index
                re_found_all_elements = get_clickable_elements(driver)
                if i >= len(re_found_all_elements):
                    print(f"  Element index {i} out of bounds after re-fetching all elements. Skipping remaining on this level.")
                    break
                element = re_found_all_elements[i]
                next_target_subject = None # Always None for general traversal

            element_text = element.text.strip()
            if not element_text:
                # Try to get text from child elements or attributes if available
                try:
                    child_text_element = element.find_element(By.XPATH, ".//*[string-length(normalize-space(.)) > 0]")
                    element_text = child_text_element.text.strip()
                except NoSuchElementException:
                    pass
                if not element_text:
                    element_text = element.get_attribute('alt') or element.get_attribute('title') or f"Unnamed_Option_{i+1}"


            # Create a new subfolder path based on the element's text
            sanitized_element_name = "".join(c for c in element_text if c.isalnum() or c in (' ', '.', '_', '-')).strip()
            sanitized_element_name = sanitized_element_name.replace(" ", "_")
            sanitized_element_name = sanitized_element_name[:100] if len(sanitized_element_name) > 100 else sanitized_element_name
            if not sanitized_element_name:
                sanitized_element_name = f"Option_{i+1}"

            new_download_sub_path = os.path.join(current_download_path, sanitized_element_name)
            os.makedirs(new_download_sub_path, exist_ok=True) # Ensure the subfolder exists

            print(f"  Clicking on '{element_text}' (Element {i+1}/{num_elements_to_process})")

            url_before_click = driver.current_url

            # Ensure element is clickable and scroll into view before clicking
            try:
                WebDriverWait(driver, 20).until(EC.element_to_be_clickable(element)) # Increased wait for clickability
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(1.5) # Increased pause after scrolling
                element.click()
            except ElementClickInterceptedException:
                print(f"  Click intercepted for '{element_text}'. Attempting JavaScript click.")
                driver.execute_script("arguments[0].click();", element)
            except Exception as click_error:
                print(f"  Could not click element '{element_text}' using standard methods or JS: {click_error}")
                continue

            time.sleep(10) # Increased sleep to allow for navigation or download initiation

            # Check if the current URL is a PDF
            if driver.current_url.lower().endswith('.pdf'):
                print(f"  Detected PDF URL: {driver.current_url}. Assuming PDF is downloaded.")
                # We don't need to go back or traverse further if it's a PDF, just continue to next element at current level
                continue # Skip to the next element in the current loop

            if len(driver.window_handles) > 1:
                print("  New window/tab opened. Closing it and returning to original.")
                driver.switch_to.window(driver.window_handles[-1])
                driver.close()
                driver_closed_new_window = True # Flag to indicate a new window was closed
                driver.switch_to.window(original_window)
                # After closing a tab, elements on the original page might become stale.
                # The loop will re-get them in the next iteration.

            if driver.current_url != url_before_click:
                print(f"  Navigated to new URL: {driver.current_url}")
                # Pass next_target_subject (which will be None after the initial target is found)
                traverse_and_download(driver, driver.current_url, new_download_sub_path, visited_urls, target_subject=next_target_subject)
                driver.back()
                time.sleep(7) # Increased sleep for navigating back
            else:
                print(f"  Stayed on same URL after clicking '{element_text}'. Assuming dynamic content or PDF download.")
                # No `driver.back()` needed here as we didn't navigate away.

        except StaleElementReferenceException:
            print(f"  Element became stale. Re-fetching elements for current page.")
            continue
        except NoSuchElementException:
            print(f"  Element not found after click or dynamic changes. Skipping.")
            continue
        except Exception as e:
            print(f"  An error occurred while processing element {i+1} ('{element_text}'): {e}")
            continue

# --- Main execution block ---
if __name__ == "__main__":
    # Define login credentials and URL
    LOGIN_URL = "https://admin.biceps.ch/login"
    USERNAME = "safiullahrahu1555@gmail.com"
    PASSWORD = "@Quantum1555"
    # Define the base URL of the website after successful login
    MAIN_CONTENT_URL = "https://desktop.biceps.ch/prive/accueil.html?_r=1"

    # --- IMPORTANT: Specify the subject you want to download here ---
    # Set to None to traverse all subjects. Set to a specific subject name (e.g., "FRANÇAIS")
    TARGET_SUBJECT = "FRANÇAIS" # <--- Set to "FRANÇAIS" as requested

    # Define the base directory where PDFs will be downloaded and organized.
    download_base_dir = os.path.join(os.getcwd(), "Biceps_Website_Downloads")
    os.makedirs(download_base_dir, exist_ok=True) # Create the base directory if it doesn't exist

    print(f"Starting PDF download process...")
    print(f"PDFs will be organized and downloaded to: {download_base_dir}")

    driver = None
    visited_urls = set()

    try:
        driver = setup_driver(download_base_dir)
        print("Selenium WebDriver initialized.")

        # Perform login first
        if not login(driver, LOGIN_URL, USERNAME, PASSWORD):
            print("Login failed. Exiting program.")
            exit() # Exit if login is not successful

        print("Login successful. Starting website traversal...")
        # Explicitly navigate to the main content URL after login
        driver.get(MAIN_CONTENT_URL)
        WebDriverWait(driver, 30).until( # Increased timeout
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(7) # Give time for the content page to fully load

        # Start the recursive traversal from the main content URL, with optional target subject
        traverse_and_download(driver, MAIN_CONTENT_URL, download_base_dir, visited_urls, target_subject=TARGET_SUBJECT)
        print("\nTraversal complete. Please check your download directory for the organized PDFs.")

    except Exception as e:
        print(f"\nAn unhandled error occurred during the process: {e}")
    finally:
        if driver:
            driver.quit() # Always close the browser when done
            print("WebDriver closed.")
