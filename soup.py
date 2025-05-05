from playwright.sync_api import sync_playwright, TimeoutError
import pandas as pd
import time
import random

def scrape_tripadvisor_moroccan_restaurants():
    url = "https://www.tripadvisor.com/Restaurants-g293730-c38-Morocco.html"
    data = []

    with sync_playwright() as p:
        # Configure browser with privacy settings
        browser = p.chromium.launch(
            headless=False,  # Show browser for debugging
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920x1080',
            ]
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            geolocation={'latitude': 31.7917, 'longitude': -7.0926},  # Morocco coordinates
            locale='en-US',
            timezone_id='Africa/Casablanca',
            permissions=['geolocation']
        )
        
        # Add stealth scripts
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = {runtime: {}};
        """)
        
        page = context.new_page()
        
        try:
            print("Navigating to TripAdvisor...")
            page.goto(url, wait_until="networkidle")
            time.sleep(random.uniform(3, 5))  # Random delay
            
            # Check for blocking elements
            if page.locator("text='Access Denied'").count() > 0 or page.locator("text='Please verify you are a human'").count() > 0:
                print("Access is blocked. Try using a VPN or waiting a while before retrying.")
                return
            
            for page_num in range(5):
                print(f"Scraping page {page_num + 1}...")
                time.sleep(random.uniform(2, 4))  # Random delay between pages
                
                # Scroll slowly down the page to simulate human behavior
                for scroll_pos in range(0, 2000, 200):
                    page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                    time.sleep(random.uniform(0.1, 0.3))
                
                # Find restaurant cards with multiple possible selectors
                cards = page.locator("div.location-meta-block, div[data-test='restaurant_list_item']").all()
                print(f"Found {len(cards)} restaurant cards")
                
                for card in cards:
                    try:
                        name_elem = card.locator("a[href*='Restaurant_Review'], div.biGQs").first
                        if name_elem.count() > 0:
                            name = name_elem.inner_text()
                            link = name_elem.get_attribute('href')
                            
                            if name:
                                print(f"Found restaurant: {name}")
                                data.append({
                                    "Name": name.strip(),
                                    "Link": f"https://www.tripadvisor.com{link}" if link else None
                                })
                                time.sleep(random.uniform(0.2, 0.5))  # Random delay between extractions
                    except Exception as e:
                        print(f"Error processing restaurant card: {str(e)}")
                        continue

                try:
                    next_btn = page.locator('[aria-label="Next"], .nav.next, .next').first
                    if next_btn.count() > 0 and next_btn.is_visible():
                        next_btn.click()
                        time.sleep(random.uniform(3, 5))  # Random delay after clicking next
                        page.wait_for_load_state('networkidle')
                    else:
                        print("No more pages to scrape")
                        break
                except Exception as e:
                    print(f"Error during pagination: {str(e)}")
                    break

        except Exception as e:
            print(f"An error occurred: {str(e)}")
        finally:
            print(f"Total restaurants found: {len(data)}")
            browser.close()

    if data:
        df = pd.DataFrame(data)
        df.to_csv("moroccan_restaurants.csv", index=False)
        print(" Saved to moroccan_restaurants.csv")
    else:
        print(" No data was collected og")

if __name__ == "__main__":
    scrape_tripadvisor_moroccan_restaurants()
