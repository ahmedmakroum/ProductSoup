"""
Enhanced TripAdvisor Restaurant Scraper for Morocco

This script scrapes restaurant data from TripAdvisor with improved error handling,
logging, and performance optimizations.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd
from playwright.sync_api import sync_playwright, Page, Browser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TripAdvisorScraper:
    """Enhanced TripAdvisor restaurant scraper with better structure and error handling."""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.base_url = "https://www.tripadvisor.com"
        self.morocco_url = "https://www.tripadvisor.com/Restaurants-g293730-c38-Morocco.html"
        
    def _safe_extract_text(self, page: Page, selector: str, timeout: int = 5000) -> str:
        """Safely extract text from a page element with timeout."""
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                return element.inner_text(timeout=timeout).strip()
        except Exception as e:
            logger.debug(f"Could not extract text for selector '{selector}': {e}")
        return ""
    
    def _safe_extract_attribute(self, page: Page, selector: str, attribute: str, timeout: int = 5000) -> str:
        """Safely extract attribute from a page element."""
        try:
            element = page.locator(selector).first
            if element.count() > 0:
                return element.get_attribute(attribute, timeout=timeout) or ""
        except Exception as e:
            logger.debug(f"Could not extract attribute '{attribute}' for selector '{selector}': {e}")
        return ""
    
    def _extract_restaurant_details(self, browser: Browser, restaurant_url: str) -> Dict[str, str]:
        """Extract detailed information from a restaurant's page."""
        details = {
            "Phone": "",
            "Rating": "",
            "Address": "",
            "Cuisine": "",
            "Price_Range": "",
            "Reviews_Count": ""
        }
        
        detail_page = None
        try:
            detail_page = browser.new_page()
            detail_page.goto(restaurant_url, timeout=self.timeout)
            detail_page.wait_for_load_state("networkidle", timeout=10000)
            
            # Extract phone number
            details["Phone"] = self._safe_extract_text(
                detail_page, 
                'span:has-text("Phone") + span, [data-test-target="phone-number"]'
            )
            
            # Extract rating
            details["Rating"] = self._safe_extract_text(
                detail_page,
                'span[class*="ZDEqb"], [data-testid="review-rating"] span'
            )
            
            # Extract address
            details["Address"] = self._safe_extract_text(
                detail_page,
                'a[href*="maps"], [data-test-target="restaurant-detail-info"] a[href*="geo"]'
            )
            
            # Extract cuisine tags
            cuisine_elements = detail_page.locator(
                'div[data-test-target="restaurant-detail-info"] span, '
                '.restaurant-details-card span[class*="cuisine"]'
            )
            
            if cuisine_elements.count() > 0:
                cuisine_tags = [
                    tag.strip() for tag in cuisine_elements.all_inner_texts()
                    if tag.strip() and tag.lower() not in ['details', 'menu', 'photos']
                ]
                details["Cuisine"] = ", ".join(cuisine_tags[:5])  # Limit to 5 tags
            
            # Extract price range
            details["Price_Range"] = self._safe_extract_text(
                detail_page,
                '[data-test-target="price-range"], span:has-text("$")'
            )
            
            # Extract review count
            details["Reviews_Count"] = self._safe_extract_text(
                detail_page,
                'span:has-text("review"), [data-testid="review-count"]'
            )
            
        except Exception as e:
            logger.error(f"Error extracting details from {restaurant_url}: {e}")
        finally:
            if detail_page:
                detail_page.close()
                
        return details
    
    def scrape_restaurants(self, limit: int = 100, output_file: str = None) -> pd.DataFrame:
        """
        Scrape restaurant data from TripAdvisor Morocco page.
        
        Args:
            limit: Maximum number of restaurants to scrape
            output_file: Output CSV filename (auto-generated if None)
            
        Returns:
            DataFrame containing scraped restaurant data
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"moroccan_restaurants_{timestamp}.csv"
        
        logger.info(f"Starting scrape of {limit} restaurants from TripAdvisor Morocco")
        
        data = []
        scraped_count = 0
        page_count = 0
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            
            try:
                page = browser.new_page()
                page.set_default_timeout(self.timeout)
                page.goto(self.morocco_url)
                page.wait_for_load_state("networkidle")
                
                while scraped_count < limit:
                    page_count += 1
                    logger.info(f"Processing page {page_count}, scraped {scraped_count}/{limit} restaurants")
                    
                    # Wait for restaurant cards to load
                    page.wait_for_selector('[data-test="restaurant-list"]', timeout=15000)
                    
                    # Get restaurant cards using multiple possible selectors
                    cards = page.locator(
                        '[data-test="restaurant-list"] div[class*="YHnoF"], '
                        '[data-test="restaurant-list"] .restaurant-item, '
                        '.restaurant-card'
                    )
                    
                    cards_count = cards.count()
                    logger.info(f"Found {cards_count} restaurant cards on page {page_count}")
                    
                    if cards_count == 0:
                        logger.warning("No restaurant cards found on page")
                        break
                    
                    for i in range(cards_count):
                        if scraped_count >= limit:
                            break
                            
                        try:
                            card = cards.nth(i)
                            
                            # Extract basic info from card
                            name = self._safe_extract_text(card, 'div[class*="biGQs"], .restaurant-name, h3')
                            if not name:
                                continue
                                
                            link = self._safe_extract_attribute(card, 'a', 'href')
                            if not link:
                                continue
                                
                            full_link = f"{self.base_url}{link}" if link.startswith('/') else link
                            
                            # Extract detailed information
                            details = self._extract_restaurant_details(browser, full_link)
                            
                            restaurant_data = {
                                "Name": name,
                                "Link": full_link,
                                "Page_Number": page_count,
                                "Scraped_At": datetime.now().isoformat(),
                                **details
                            }
                            
                            data.append(restaurant_data)
                            scraped_count += 1
                            
                            logger.info(f"✅ Scraped restaurant {scraped_count}: {name}")
                            
                            # Small delay to be respectful
                            time.sleep(1)
                            
                        except Exception as e:
                            logger.error(f"Error processing restaurant {i+1} on page {page_count}: {e}")
                            continue
                    
                    # Try to go to next page
                    if scraped_count < limit:
                        next_selectors = [
                            '[aria-label="Next"]',
                            'a[aria-label="Next page"]',
                            '.next',
                            'a:has-text("Next")'
                        ]
                        
                        next_clicked = False
                        for selector in next_selectors:
                            try:
                                next_btn = page.locator(selector).first
                                if next_btn.count() > 0 and next_btn.is_enabled():
                                    next_btn.click()
                                    page.wait_for_load_state("networkidle", timeout=10000)
                                    next_clicked = True
                                    break
                            except Exception as e:
                                logger.debug(f"Next button selector '{selector}' failed: {e}")
                        
                        if not next_clicked:
                            logger.info("No more pages available or next button not found")
                            break
                
            except Exception as e:
                logger.error(f"Critical error during scraping: {e}")
            finally:
                browser.close()
        
        # Save data
        df = pd.DataFrame(data)
        if not df.empty:
            df.to_csv(output_file, index=False)
            logger.info(f"✅ Successfully saved {len(df)} restaurants to {output_file}")
        else:
            logger.warning("No data was scraped")
            
        return df


def main():
    """Main function to run the scraper."""
    scraper = TripAdvisorScraper(headless=True)
    
    try:
        df = scraper.scrape_restaurants(limit=100)
        print(f"\n🎉 Scraping completed! Found {len(df)} restaurants.")
        
        if not df.empty:
            print("\nSample data:")
            print(df[['Name', 'Rating', 'Cuisine', 'Address']].head())
            
    except Exception as e:
        logger.error(f"Failed to run scraper: {e}")


if __name__ == "__main__":
    main()
