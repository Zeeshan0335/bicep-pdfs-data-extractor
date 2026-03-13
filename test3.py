import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page, TimeoutError

# --- Configuration ---
URL = "https://conjugaison.tatitotu.ch/accueil"

async def get_all_verb_groups(page: Page) -> list[str]:
    """
    Clicks the 'Par groupe' dropdown and scrapes all available verb group names.
    """
    print("\n--- [INIT] Discovering all verb groups ---")
    
    # Click 'Par groupe' to reveal the dropdown
    print("   [INIT] Clicking 'Pronominaux' dropdown...")
    # Increased timeout for dropdown click as well, just in case
    await page.locator('a.dropdown-toggle:has-text("Pronominaux")').click(timeout=30000) 
    
    # Wait for the dropdown menu to be visible
    dropdown_menu_selector = 'div.dropdown-menu.show'
    await page.wait_for_selector(dropdown_menu_selector, state='visible', timeout=15000) # Increased timeout
    print("   [INIT] Dropdown menu is visible.")

    # Get all the 'a' tags within the visible dropdown menu that are the verb group options
    # We filter out the 'Tous' (All) link if it exists, as we're processing groups individually.
    # We also exclude "Par groupe" itself if it somehow appears as a clickable item in its own dropdown
    group_links = await page.locator(f'{dropdown_menu_selector} a.dropdown-item:not(:has-text("Tous")):not(:has-text("Difficiles"))').all_text_contents()
    
    # Remove any empty strings or whitespace-only strings
    group_links = [link.strip() for link in group_links if link.strip()]
    
    print(f"   [INIT] Discovered verb groups: {group_links}")
    
    # Reload the page to reset the state after opening the dropdown
    # This is important so the subsequent workflow can start clean
    print("   [INIT] Reloading page after group discovery...")
    # Increased timeout for reload as well
    await page.reload(timeout=90000) 
    await page.wait_for_load_state('domcontentloaded', timeout=30000) # Increased timeout
    
    return group_links

async def perform_workflow_for_level(page: Page, level_name: str):
    """
    This function controls the entire workflow for a given verb group name.
    """
    # Sanitize level_name for filename (replace problematic characters)
    # Using a more robust sanitization for broader character sets
    sanitized_level_name = "".join(c for c in level_name if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
    output_file = f"conjugaison_defi_{sanitized_level_name}.pdf"
    
    try:
        print(f"\n--- [WORKFLOW] Starting for Verb Group: {level_name} ---")

        # STEP 1: Select Verbs
        print(f"   [1] Clicking 'Pronominaux' dropdown...")
        await page.locator('a.dropdown-toggle:has-text("Pronominaux")').click(timeout=30000) # Increased timeout

        print(f"   [1] Waiting for and clicking '{level_name}'...")
        # This locator specifically finds the link for the current verb group inside the visible dropdown menu
        group_button = page.locator(f'div.dropdown-menu.show a:has-text("{level_name}")')
        await group_button.wait_for(state='visible', timeout=15000) # Increased timeout
        await group_button.click(timeout=15000) # Increased timeout
        print(f"       -> Clicked '{level_name}'.")
        
        print("   [1] Now, waiting for verb list to populate...")
        await page.wait_for_selector('div.card:has(h5:has-text("Mes verbes")) div[role="info"]', timeout=30000) # Increased timeout
        print("   ✅ Step 1 Complete: Verbs successfully detected.")

        # STEP 2: Set Options
        print("\n   [2] Setting options...")
        await page.get_by_text("Tout cocher").click(timeout=15000) # Increased timeout
        await page.select_option("#nombre-de-questions", "50", timeout=15000) # Increased timeout
        await page.click("a:has-text('Normal')", timeout=15000) # Increased timeout
        print("   ✅ Step 2 Complete: Options set.")

        # STEP 3: Click Print to reveal the dropdown
        print("\n   [3] Clicking 'Imprimer' to reveal dropdown...")
        await page.locator('a:has-text("Imprimer")').first.click(timeout=15000) # Increased timeout
        print("       -> 'Imprimer' button clicked.")

        # STEP 4: Download PDF
        print("\n   [4] Triggering PDF download from the dropdown...")
        async with page.expect_download(timeout=90000) as download_info: # Increased timeout for download expectation
            pdf_link_selector = 'li.dropdown:has(a:has-text("Imprimer")) a:has-text("PDF")'
            await page.locator(pdf_link_selector).click(timeout=15000) # Increased timeout
            
        download = await download_info.value
        
        output_path = Path(output_file)
        await download.save_as(output_path)
        print(f"✅✅✅ SUCCESS! File for verb group '{level_name}' downloaded and saved to: {output_path.resolve()}")

    except TimeoutError as e:
        print(f"\n❌ A specific action timed out for verb group '{level_name}'.")
        print(f"   Error details: {e}")
        # Optionally, take a screenshot on timeout for debugging
        screenshot_path = Path(f"timeout_error_{sanitized_level_name}.png")
        await page.screenshot(path=screenshot_path)
        print(f"   Screenshot saved to: {screenshot_path.resolve()}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred during the workflow for verb group '{level_name}': {e}")
        screenshot_path = Path(f"unexpected_error_{sanitized_level_name}.png")
        await page.screenshot(path=screenshot_path)
        print(f"   Screenshot saved to: {screenshot_path.resolve()}")

async def main():
    """
    The main function to launch the browser, discover verb groups, and loop through them.
    """
    print(f"🚀 Starting multi-group workflow on: {URL}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Keep headless=False for visual debugging
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # --- KEY CHANGE: Increased timeout for initial page load and set wait_until ---
        print(f"Attempting to navigate to {URL} with 120s timeout...")
        try:
            await page.goto(URL, timeout=120000, wait_until='domcontentloaded')
            print("Initial page loaded successfully.")
        except TimeoutError as e:
            print(f"\nCRITICAL ERROR: Initial page load timed out at {URL}.")
            print(f"Please check your internet connection and if the website is accessible manually.")
            print(f"Error details: {e}")
            await browser.close()
            return # Exit the script if the initial page load fails

        # First, discover all verb groups
        all_verb_groups = await get_all_verb_groups(page)

        if not all_verb_groups:
            print("No verb groups found to process. Exiting.")
            await browser.close()
            return

        for group_name in all_verb_groups:
            # The get_all_verb_groups function already reloads the page once it's done.
            # So, for the first iteration of this loop, the page is already in a clean state.
            
            await perform_workflow_for_level(page, group_name)
            
            # After finishing a group, reload the page to get a fresh start for the next one.
            # This is crucial because selecting a group changes the page state, and we need
            # to go back to the original state to click "Par groupe" again.
            print(f"\n--- Reloading page for next verb group workflow ---")
            await page.reload(timeout=90000) # Increased timeout for reload
            await page.wait_for_load_state('domcontentloaded', timeout=30000) # Increased timeout
        
        await browser.close()
    print(f"\n🏁 All workflows finished.")


if __name__ == "__main__":
    asyncio.run(main())