"""
Modern Mubawab Scraper - 2026 Edition
Collects current real estate prices from Mubawab.ma using Selenium + BeautifulSoup
Extracts data directly from listing pages (no per-property visits needed)
Correct URL pattern: /en/sc/apartments-for-sale
Correct CSS classes: listingBox, priceTag, listingH3, adDetailFeature, adFeature
"""

import csv
import re
import time
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mubawab_scraping.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),          # stdout on Windows may need this
    ],
)
logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
BASE_URL = "https://www.mubawab.ma"
SALE_URL = f"{BASE_URL}/en/sc/apartments-for-sale"
RENT_URL = f"{BASE_URL}/en/sc/apartments-for-rent"

TARGET_FEATURES = ["terrace", "garage", "elevator", "concierge", "pool", "security", "garden"]


# ── Driver ─────────────────────────────────────────────────────────────────────

def create_driver() -> webdriver.Chrome:
    """Initialize Chrome with anti-detection flags."""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(options=opts)


# ── Parsers ────────────────────────────────────────────────────────────────────

def clean_price(text: str) -> Optional[float]:
    """Parse 'X,XXX,XXX DH' → float MAD."""
    if not text:
        return None
    try:
        value = float(re.sub(r"[^\d.]", "", text.replace(",", "")))
        return value if 10_000 <= value <= 200_000_000 else None
    except (ValueError, TypeError):
        return None


def clean_surface(text: str) -> Optional[float]:
    """Parse '144 m²' → float."""
    if not text:
        return None
    m = re.search(r"(\d+\.?\d*)", text.replace(",", "."))
    if m:
        v = float(m.group(1))
        return v if 10 <= v <= 5000 else None
    return None


def clean_int(text: str, lo: int = 0, hi: int = 30) -> int:
    """Parse integer, clamp to [lo, hi]."""
    if not text:
        return 0
    try:
        v = int(re.sub(r"[^\d]", "", text))
        return v if lo <= v <= hi else 0
    except (ValueError, TypeError):
        return 0


def parse_listing_box(box) -> Optional[Dict]:
    """
    Parse a single `div.listingBox` element into a property dict.
    All data lives in the card — no extra page visit needed.
    """
    try:
        # ── URL ────────────────────────────────────────────────────────────────
        url = box.get("linkref", "")
        if not url:
            link_tag = box.select_one("h2.listingTit a")
            url = link_tag["href"] if link_tag else ""

        # ── Title ──────────────────────────────────────────────────────────────
        title_tag = box.select_one("h2.listingTit a")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # ── Price ──────────────────────────────────────────────────────────────
        price_tag = box.select_one("span.priceTag")
        price = clean_price(price_tag.get_text(strip=True)) if price_tag else None

        # ── Location ──────────────────────────────────────────────────────────
        loc_tag = box.select_one("span.listingH3")
        location = loc_tag.get_text(strip=True).lstrip("").strip() if loc_tag else ""
        # remove leading icon text artifacts
        location = re.sub(r"^\W+", "", location).strip()

        # ── Details (surface, rooms, bedrooms, bathrooms) ──────────────────────
        surface = rooms = bedrooms = bathrooms = 0
        surface_raw = None

        for feat in box.select("div.adDetailFeature"):
            icon = feat.select_one("i")
            span = feat.select_one("span")
            if not icon or not span:
                continue
            icon_cls = " ".join(icon.get("class", []))
            text = span.get_text(strip=True)

            if "triangle" in icon_cls:          # surface icon
                surface_raw = text
                surface = clean_surface(text) or 0
            elif "house-boxes" in icon_cls:     # pieces / rooms total
                rooms = clean_int(text)
            elif "icon-bed" in icon_cls:        # bedrooms
                bedrooms = clean_int(text)
            elif "icon-bath" in icon_cls:       # bathrooms
                bathrooms = clean_int(text)

        # ── Amenity Features ───────────────────────────────────────────────────
        feature_texts = [
            f.get_text(strip=True).lower()
            for f in box.select("div.adFeature span")
        ]
        features_str = ", ".join(feature_texts)

        amenities = {f: any(f in t for t in feature_texts) for f in TARGET_FEATURES}

        # ── Skip if missing critical fields ────────────────────────────────────
        if price is None or surface == 0:
            return None

        return {
            "title": title,
            "price": price,
            "location": location,
            "surface": surface,
            "rooms": rooms,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "property_category": "Apartment",
            "type": "",                   # filled by caller
            "description": "",
            "features": features_str,
            **amenities,
            "url": url,
            "scraped_date": datetime.now().isoformat(),
        }

    except Exception as exc:
        logger.warning(f"Error parsing listing box: {exc}")
        return None


# ── Main Scraper ───────────────────────────────────────────────────────────────

class MubawabModernScraper:
    """Scrapes Mubawab listing pages, extracts data from cards directly."""

    def __init__(self, output_dir: str = "../../data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scraped_data: List[Dict] = []
        self.driver: Optional[webdriver.Chrome] = None

    # ── Internals ──────────────────────────────────────────────────────────────

    def _get_page_source(self, url: str) -> Optional[str]:
        """Load a URL and wait for listing cards to appear."""
        try:
            self.driver.get(url)
            # Wait for at least one listingBox to exist
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.listingBox"))
            )
            time.sleep(2)       # let lazy images/JS settle
            return self.driver.page_source
        except Exception as exc:
            logger.warning(f"Timeout/error loading {url}: {exc}")
            return None

    def _scrape_one_page(self, url: str, listing_type: str) -> int:
        """Scrape a single result page; return count of properties scraped."""
        html = self._get_page_source(url)
        if not html:
            return 0

        soup = BeautifulSoup(html, "html.parser")
        boxes = soup.select("div.listingBox")
        logger.info(f"  Found {len(boxes)} listing cards on: {url}")

        count = 0
        for box in boxes:
            prop = parse_listing_box(box)
            if prop:
                prop["type"] = listing_type
                self.scraped_data.append(prop)
                count += 1

        return count

    # ── Public ─────────────────────────────────────────────────────────────────

    def scrape_type(self, base_url: str, listing_type: str, max_pages: int = 10):
        """Scrape paginated results for one listing type."""
        logger.info(f"[START] Scraping {listing_type} — up to {max_pages} pages")
        total = 0

        for page in range(1, max_pages + 1):
            url = f"{base_url}?page={page}"
            logger.info(f"  Page {page}/{max_pages}: {url}")
            n = self._scrape_one_page(url, listing_type)
            total += n

            if n == 0:
                logger.info(f"  No results on page {page} — stopping early.")
                break

            time.sleep(1.5)     # polite delay between pages

        logger.info(f"[DONE] {listing_type}: {total} properties collected")

    def save_to_csv(self, filename: str = "mubawab_current_listings.csv") -> Optional[Path]:
        """Write all scraped data to CSV."""
        if not self.scraped_data:
            logger.warning("No data to save.")
            return None

        path = self.output_dir / filename
        fieldnames = [
            "title", "price", "location", "surface", "rooms", "bedrooms", "bathrooms",
            "property_category", "type", "description", "features",
            "terrace", "garage", "elevator", "concierge", "pool", "security", "garden",
            "url", "scraped_date",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.scraped_data)

        logger.info(f"[SAVED] {len(self.scraped_data)} records -> {path}")
        return path

    def run(self, max_pages: int = 10):
        """Full run: sale + rent."""
        try:
            self.driver = create_driver()

            self.scrape_type(SALE_URL, "For_Sale", max_pages=max_pages)
            self.scrape_type(RENT_URL, "For_Rent", max_pages=max_pages)

            output_file = self.save_to_csv("mubawab_current_listings.csv")

            logger.info(
                f"\n{'='*50}\n"
                f"  SCRAPING COMPLETE\n"
                f"  Total properties: {len(self.scraped_data)}\n"
                f"  Output: {output_file}\n"
                f"{'='*50}"
            )
            return self.scraped_data

        finally:
            if self.driver:
                self.driver.quit()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mubawab 2026 Scraper")
    parser.add_argument("--pages", type=int, default=5,
                        help="Max pages to scrape per listing type (default: 5)")
    parser.add_argument("--output-dir", type=str, default="../../data",
                        help="Directory to save CSV output")
    args = parser.parse_args()

    scraper = MubawabModernScraper(output_dir=args.output_dir)
    data = scraper.run(max_pages=args.pages)
    logger.info(f"Total records collected: {len(data)}")
