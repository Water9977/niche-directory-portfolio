import sqlite3
import os
import requests
import json
import hashlib
import sys
import re
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

# Reconfigure terminal output to support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load environment variables
from dotenv import load_dotenv
load_dotenv(dotenv_path="e:/Claude/Workspaces/Niche Directory W/.env")

EXA_API_KEY = os.environ.get("EXA_API_KEY")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "directory.db")

# Known aggregator domains to filter out
EXCLUDED_DOMAINS = {
    # Senior Care aggregators
    "aplaceformom.com", "caring.com", "assistedliving.org", "seniorly.com", "seniorhousingnet.com",
    "yelp.com", "yellowpages.com", "mapquest.com", "groupon.com", "facebook.com", "instagram.com",
    "linkedin.com", "twitter.com", "youtube.com", "wikipedia.org", "reddit.com", "local.yahoo.com",
    # Restroom aggregators / weddings
    "theknot.com", "weddingwire.com", "zola.com", "angi.com", "thumbtack.com", "homeadvisor.com",
    # RV / Campground aggregators
    "goodsam.com", "campgroundreviews.com", "tripadvisor.com", "rvparky.com", "campendium.com",
    "thedyrt.com", "recreation.gov", "reserveamerica.com", "alltrails.com", "bringfido.com",
    "booking.com", "expedia.com", "hotels.com", "airbnb.com", "vrbo.com"
}

def is_valid_business_website(url):
    if not url:
        return False
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    for excluded in EXCLUDED_DOMAINS:
        if domain == excluded or domain.endswith("." + excluded):
            return False
    return True

def clean_business_name(title, url):
    separators = [" - ", " | ", " : ", " – ", " — "]
    name = title
    for sep in separators:
        if sep in name:
            parts = name.split(sep)
            for part in parts:
                p_lower = part.lower()
                if "best" not in p_lower and "top" not in p_lower and "near me" not in p_lower:
                    name = part.strip()
                    break
    if len(name) < 3 or len(name) > 80:
        parsed = urlparse(url)
        name = parsed.netloc.replace("www.", "").split(".")[0].capitalize()
    return name.strip()

def parse_single_place(page):
    try:
        page.wait_for_selector('h1', state='attached', timeout=6000)
        name_elem = page.locator('h1').first
        name = name_elem.text_content().strip() if name_elem.count() > 0 else ""
        if not name:
            return None
            
        # Address
        address = ""
        addr_elem = page.locator('button[data-item-id="address"]').first
        if addr_elem.count() > 0 and addr_elem.is_visible():
            raw_addr = addr_elem.text_content().replace("Address: ", "").strip()
            address = re.sub(r'^[^\w\d\s\#\.\,]+', '', raw_addr).strip()
            
        # Phone
        phone = ""
        phone_elem = page.locator('button[data-item-id^="phone:tel:"]').first
        if phone_elem.count() > 0 and phone_elem.is_visible():
            raw_phone = phone_elem.text_content().replace("Phone: ", "").strip()
            phone = re.sub(r'[^\d\+\-\s\(\)]', '', raw_phone).strip()
            
        # Website
        website = ""
        web_elem = page.locator('a[data-item-id="authority"]').first
        if web_elem.count() > 0 and web_elem.is_visible():
            website = web_elem.get_attribute("href")
            
        # Rating & Reviews Count
        rating = 0.0
        reviews_count = 0
        rating_container = page.locator('div.F7nice').first
        if rating_container.count() > 0:
            span_rating = rating_container.locator('span[aria-hidden="true"]').first
            if span_rating.count() > 0:
                try:
                    rating = float(span_rating.text_content().strip())
                except:
                    pass
            # Review count
            reviews_text = rating_container.text_content()
            match = re.search(r'\((\d+[\d,]*)\)', reviews_text)
            if match:
                try:
                    reviews_count = int(match.group(1).replace(",", ""))
                except:
                    pass
                    
        # Latitude / Longitude
        latitude = None
        longitude = None
        url = page.url
        match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
        if match:
            latitude = float(match.group(1))
            longitude = float(match.group(2))
        else:
            match_data = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
            if match_data:
                latitude = float(match_data.group(1))
                longitude = float(match_data.group(2))
            
        # Category
        category = ""
        cat_elem = page.locator('button[jsaction*="category"]').first
        if cat_elem.count() > 0:
            category = cat_elem.text_content().strip()
            
        return {
            "name": name,
            "address": address,
            "phone": phone,
            "website": website,
            "rating": rating,
            "reviews_count": reviews_count,
            "latitude": latitude,
            "longitude": longitude,
            "google_category": category,
            "url": url
        }
    except Exception as e:
        print(f"Error parsing place details: {e}")
        return None

def scrape_google_maps_via_playwright(query, max_results=12):
    print(f"Starting Playwright Google Maps scraper for query: '{query}'...")
    results = []
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            search_url = f"https://www.google.com/maps/search/{requests.utils.quote(query)}"
            page.goto(search_url, timeout=30000)
            
            try:
                consent_btn = page.locator('button[aria-label="Reject all"]').first
                if consent_btn.count() > 0 and consent_btn.is_visible():
                    consent_btn.click()
                    page.wait_for_timeout(1000)
            except Exception:
                pass
                
            try:
                page.wait_for_selector('a[href*="/maps/place/"]', timeout=8000)
            except Exception:
                if "/maps/place/" in page.url:
                    print("Redirected directly to place page.")
                    place_data = parse_single_place(page)
                    if place_data:
                        results.append(place_data)
                    browser.close()
                    return results
                else:
                    print("No listings found in Maps view.")
                    browser.close()
                    return results
                    
            feed_selector = 'div[role="feed"]'
            feed_element = page.locator(feed_selector).first
            if feed_element.count() > 0:
                for _ in range(3):
                    feed_element.evaluate("el => el.scrollBy(0, 5000)")
                    page.wait_for_timeout(1200)
                    
            card_links = page.locator('a[href*="/maps/place/"]').all()
            urls = []
            for link in card_links:
                href = link.get_attribute("href")
                if href and href not in urls:
                    urls.append(href)
                    if len(urls) >= max_results:
                        break
                        
            print(f"Discovered {len(urls)} business details pages. Scraping individually...")
            
            for url in urls:
                try:
                    page.goto(url, timeout=20000)
                    place_data = parse_single_place(page)
                    if place_data:
                        results.append(place_data)
                        print(f"  Scraped Maps Entity: {place_data['name']} | Phone: {place_data['phone']} | Website: {place_data['website']}")
                except Exception as place_err:
                    print(f"  Error loading place URL: {place_err}")
                    
            browser.close()
        except Exception as e:
            print(f"Playwright crawler error: {e}")
            
    return results

def search_exa(query):
    url = "https://api.exa.ai/search"
    headers = {"x-api-key": EXA_API_KEY, "content-type": "application/json"}
    payload = {"query": query, "useAutoprompt": True, "numResults": 20, "type": "neural"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get("results", [])
    except Exception as e:
        print(f"Exa fallback error: {e}")
    return []

def search_firecrawl(query):
    url = "https://api.firecrawl.dev/v1/search"
    headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
    payload = {"query": query, "limit": 15}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("data", {}).get("web", [])
    except Exception as e:
        print(f"Firecrawl fallback error: {e}")
    return []

def scrape_pending_cities():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, niche, city, state, search_query 
        FROM target_cities 
        WHERE scrape_status = 'pending'
        ORDER BY priority ASC
    """)
    cities = cursor.fetchall()
    
    if not cities:
        print("No pending cities to scrape.")
        conn.close()
        return

    print(f"Found {len(cities)} pending target cities.")
    
    for city_id, niche, city, state, search_query in cities:
        print(f"\nProcessing: {niche} in {city}, {state} (Query: '{search_query}')")
        
        cursor.execute("UPDATE target_cities SET scrape_status = 'in_progress' WHERE id = ?", (city_id,))
        conn.commit()
        
        source = "google_maps_playwright"
        results = scrape_google_maps_via_playwright(search_query, max_results=12)
        
        if not results:
            print("Playwright Maps Scraper returned nothing. Falling back to Exa Search...")
            results = search_exa(search_query)
            source = "exa"
            
        if not results:
            print("Exa Search returned nothing. Falling back to Firecrawl Search...")
            results = search_firecrawl(search_query)
            source = "firecrawl"
            
        if not results:
            print(f"No listings found for query: '{search_query}'")
            cursor.execute("UPDATE target_cities SET scrape_status = 'failed' WHERE id = ?", (city_id,))
            conn.commit()
            continue
            
        listings_added = 0
        for item in results:
            is_playwright = "address" in item
            
            if is_playwright:
                url = item.get("website")
                name = item.get("name")
                google_place_id = item.get("google_place_id") or hashlib.md5(item["url"].encode("utf-8")).hexdigest()
                address = item.get("address")
                phone = item.get("phone")
                rating = item.get("rating")
                reviews_count = item.get("reviews_count")
                latitude = item.get("latitude")
                longitude = item.get("longitude")
                category = item.get("google_category")
                hours_str = ""
            else:
                url = item.get("url")
                title = item.get("title", "")
                name = clean_business_name(title, url)
                google_place_id = hashlib.md5(url.encode("utf-8")).hexdigest()
                address, phone, rating, reviews_count, latitude, longitude, category, hours_str = None, None, None, 0, None, None, None, ""

            if url and not is_valid_business_website(url):
                print(f"Skipping aggregator/invalid URL: {url}")
                continue
                
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO raw_listings 
                    (niche, google_place_id, name, full_address, city, state, latitude, longitude, phone, website, rating, reviews_count, google_category, business_hours, scrape_source, scrape_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (niche, google_place_id, name, address, city, state, latitude, longitude, phone, url, rating, reviews_count, category, hours_str, source))
                
                if cursor.rowcount > 0:
                    listings_added += 1
                    print(f"Added raw listing: {name} (Website: {url})")
            except Exception as e:
                print(f"Database insertion error for {name}: {e}")
                
        cursor.execute("""
            UPDATE target_cities 
            SET scrape_status = 'complete', listings_found = ? 
            WHERE id = ?
        """, (listings_added, city_id))
        conn.commit()
        print(f"Finished {city}, {state}. Found and added {listings_added} local listings.")
        
    conn.close()
    print("\nBatch scraping completed.")

if __name__ == "__main__":
    scrape_pending_cities()
