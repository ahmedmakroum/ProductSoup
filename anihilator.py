# This script generates a Python script that scrapes restaurant data from TripAdvisor for Morocco.
from playwright.sync_api import sync_playwright
import pandas as pd

def scrape_tripadvisor_restaurants(limit=100):
    url = "https://www.tripadvisor.com/Restaurants-g293730-c38-Morocco.html"
    data = []
    scraped_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)

        while scraped_count < limit:
            page.wait_for_timeout(3000)
            cards = page.locator('[data-test="restaurant-list"] div[class*="YHnoF"]')

            for i in range(cards.count()):
                try:
                    card = cards.nth(i)
                    name = card.locator('div[class*="biGQs"]').inner_text()
                    link = card.locator('a').get_attribute('href')
                    full_link = f"https://www.tripadvisor.com{link}" if link else None

                    # Go to the individual restaurant page to get more info
                    if full_link:
                        detail_page = browser.new_page()
                        detail_page.goto(full_link)
                        detail_page.wait_for_timeout(2000)

                        phone = detail_page.locator('span:has-text("Phone") + span').nth(0).inner_text(timeout=1000) if detail_page.locator('span:has-text("Phone") + span').count() > 0 else ""
                        rating = detail_page.locator('span[class*="ZDEqb"]').first.inner_text() if detail_page.locator('span[class*="ZDEqb"]').count() > 0 else ""
                        address = detail_page.locator('a[href*="maps"]').first.inner_text() if detail_page.locator('a[href*="maps"]').count() > 0 else ""
                        cuisine_tags = detail_page.locator('div[data-test-target="restaurant-detail-info"] span').all_inner_texts()
                        cuisine = ", ".join([tag for tag in cuisine_tags if tag.lower() != 'details'])

                        data.append({
                            "Name": name,
                            "Link": full_link,
                            "Phone": phone,
                            "Rating": rating,
                            "Address": address,
                            "Cuisine": cuisine
                        })
                        scraped_count += 1
                        detail_page.close()
                except Exception as e:
                    print(f"Error scraping a restaurant: {e}")

                if scraped_count >= limit:
                    break

            next_btn = page.locator('[aria-label="Next"]')
            if next_btn.is_enabled():
                next_btn.click()
            else:
                break

        browser.close()

    df = pd.DataFrame(data)
    df.to_csv("moroccan_restaurants_detailed.csv", index=False)
    print("✅ Saved to moroccan_restaurants_detailed.csv")

if __name__ == "__main__":
    scrape_tripadvisor_restaurants(limit=100)
(scraper_file := output_dir / "tripadvisor_restaurant_scraper.py").write_text(scraper_code.strip())

scraper_file.name
