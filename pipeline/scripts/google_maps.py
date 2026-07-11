import sqlite3
import os
import requests
import json
import hashlib
import sys
from urllib.parse import urlparse

# Reconfigure terminal output to support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# Load environment variables
EXA_API_KEY = "91f86c5b-b079-4c60-865e-39ba27510725"
FIRECRAWL_API_KEY = "fc-57d857b3980a45009444860f390c1919"

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
    # Remove www.
    if domain.startswith("www."):
        domain = domain[4:]
    
    # Check if domain or any parent domain is in the excluded set
    for excluded in EXCLUDED_DOMAINS:
        if domain == excluded or domain.endswith("." + excluded):
            return False
    return True

def clean_business_name(title, url):
    # Try to extract clean name from Title
    # E.g., "Arden Courts - Memory Care in Sarasota, FL" -> "Arden Courts"
    # E.g., "Liana of Sarasota: Memory Care Community" -> "Liana of Sarasota"
    separators = [" - ", " | ", " : ", " : ", " – ", " — "]
    name = title
    for sep in separators:
        if sep in name:
            parts = name.split(sep)
            # Pick the part that doesn't contain generic words like "assisted living" or "rentals"
            for part in parts:
                p_lower = part.lower()
                if "best" not in p_lower and "top" not in p_lower and "near me" not in p_lower:
                    name = part.strip()
                    break
    
    # Remove city/state suffix if it got appended
    # E.g., "Aviva Senior Living - Sarasota FL" -> "Aviva Senior Living"
    # If name is too short or generic, fallback to domain name
    if len(name) < 3 or len(name) > 80:
        parsed = urlparse(url)
        name = parsed.netloc.replace("www.", "").split(".")[0].capitalize()
    
    return name.strip()

def search_exa(query):
    url = "https://api.exa.ai/search"
    headers = {
        "x-api-key": EXA_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "query": query,
        "useAutoprompt": True,
        "numResults": 20,
        "type": "neural"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            print(f"Exa search failed with status: {response.status_code}, response: {response.text}")
    except Exception as e:
        print(f"Exa request error: {e}")
    return []

def search_firecrawl(query):
    url = "https://api.firecrawl.dev/v1/search"
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "query": query,
        "limit": 15
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("data", {}).get("web", [])
        else:
            print(f"Firecrawl search failed with status: {response.status_code}")
    except Exception as e:
        print(f"Firecrawl request error: {e}")
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
        
        # Mark city in progress
        cursor.execute("UPDATE target_cities SET scrape_status = 'in_progress' WHERE id = ?", (city_id,))
        conn.commit()
        
        # 1. Search Exa (Primary)
        results = search_exa(search_query)
        source = "exa"
        
        # 2. Fallback to Firecrawl Search if Exa returned nothing
        if not results:
            print("Exa returned no results. Trying Firecrawl Search...")
            results = search_firecrawl(search_query)
            source = "firecrawl"
            
        if not results:
            print(f"No listings found for query: '{search_query}'")
            cursor.execute("UPDATE target_cities SET scrape_status = 'failed' WHERE id = ?", (city_id,))
            conn.commit()
            continue
            
        listings_added = 0
        for item in results:
            # Standardize keys between Exa (url, title) and Firecrawl (url, title, description)
            url = item.get("url")
            title = item.get("title", "")
            
            if not is_valid_business_website(url):
                print(f"Skipping aggregator/invalid URL: {url}")
                continue
                
            name = clean_business_name(title, url)
            # Create a unique Place ID hash from URL to prevent duplication
            google_place_id = hashlib.md5(url.encode("utf-8")).hexdigest()
            
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO raw_listings 
                    (niche, google_place_id, name, website, city, state, scrape_source, scrape_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (niche, google_place_id, name, url, city, state, source))
                
                if cursor.rowcount > 0:
                    listings_added += 1
                    print(f"Added raw listing: {name} ({url})")
            except Exception as e:
                print(f"Database insertion error for {name}: {e}")
                
        # Mark city complete
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
