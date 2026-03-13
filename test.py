import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page, TimeoutError

# --- Configuration ---
URL = "https://conjugaison.tatitotu.ch/accueil"
# A list of all the challenges you want to download. You can add "7H", "8H", etc.
LEVELS_TO_PROCESS = ["Par groupe"]

async def perform_workflow_for_level(page: Page, level: str):
    try:
        print(f"\n--- [WORKFLOW] Starting for Level: {level} ---")

        # STEP 1: Click the main dropdown (e.g., "Par groupe")
        await page.locator(f'a.dropdown-toggle:has-text("{level}")').click(timeout=15000)
        await page.wait_for_selector('div.dropdown-menu.show', timeout=5000)

        # STEP 2: Get all group options inside dropdown (e.g., "1er groupe", "2e groupe", etc.)
        group_links = await page.locator('div.dropdown-menu.show a').all()
        group_names = []
        for link in group_links:
            name = await link.inner_text()
            group_names.append(name.strip())

        # STEP 3: Loop through each group name and run download workflow
        for group_name in group_names:
            print(f"\n--> Processing group: {group_name}")
            # Click the dropdown again (if closed)
            await page.locator(f'a.dropdown-toggle:has-text("{level}")').click(timeout=5000)
            await page.locator(f'div.dropdown-menu.show a:has-text("{group_name}")').click(timeout=10000)
            
            await page.wait_for_selector('div.card:has(h5:has-text("Mes verbes")) div[role="info"]', timeout=20000)
            print("✅ Verb list loaded.")

            # Set Options
            await page.get_by_text("Tout cocher").click(timeout=10000)
            await page.select_option("#nombre-de-questions", "50", timeout=10000)
            await page.click("a:has-text('Normal')", timeout=10000)

            # Print and Download
            await page.locator('a:has-text("Imprimer")').first.click(timeout=10000)
            async with page.expect_download(timeout=60000) as download_info:
                await page.locator('li.dropdown:has(a:has-text("Imprimer")) a:has-text("PDF")').click(timeout=10000)

            download = await download_info.value
            output_file = f"conjugaison_{level.replace(' ', '_')}_{group_name.replace(' ', '_').replace('/', '-')}.pdf"
            await download.save_as(Path(output_file))
            print(f"✅ PDF saved as: {output_file}")

            # تھوڑا انتظار اگر ضروری ہو
            await page.wait_for_timeout(1000)

    except TimeoutError as e:
        print(f"❌ Timeout occurred while processing level '{level}'")
        print(f"Error details: {e}")
    except Exception as e:
        print(f"❌ Unexpected error during level '{level}': {e}")
