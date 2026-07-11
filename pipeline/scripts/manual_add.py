import sqlite3
import os
import sys
import hashlib

# Reconfigure terminal output to support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "directory.db")

def add_manual_listing():
    print("=== Niche Directory Portfolio: Manual Listing Adder ===")
    
    niche = input("Enter Niche (restroomrentals / memorycare / rvparks): ").strip().lower()
    if niche not in ["restroomrentals", "memorycare", "rvparks"]:
        print("Invalid niche! Must be one of the three target niches.")
        return
        
    name = input("Business Name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return
        
    website = input("Website URL: ").strip()
    full_address = input("Full Address: ").strip()
    phone = input("Phone Number: ").strip()
    
    city = input("City (e.g. McKinney): ").strip()
    state = input("State (2-letter code, e.g. TX): ").strip().upper()
    
    try:
        rating_input = input("Rating (0.0 - 5.0, default 4.5): ").strip()
        rating = float(rating_input) if rating_input else 4.5
    except ValueError:
        rating = 4.5
        
    try:
        reviews_input = input("Review Count (default 10): ").strip()
        reviews_count = int(reviews_input) if reviews_input else 10
    except ValueError:
        reviews_count = 10
        
    category = input("Google Category (e.g. Portable Toilet Supplier): ").strip()
    
    # Calculate coordinate defaults or ask
    lat_input = input("Latitude (optional): ").strip()
    latitude = float(lat_input) if lat_input else None
    
    lng_input = input("Longitude (optional): ").strip()
    longitude = float(lng_input) if lng_input else None

    google_place_id = hashlib.md5(f"manual_{name}_{website}".encode("utf-8")).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO raw_listings 
            (niche, google_place_id, name, full_address, city, state, latitude, longitude, phone, website, rating, reviews_count, google_category, scrape_source, scrape_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual', 'scraped')
        """, (niche, google_place_id, name, full_address, city, state, latitude, longitude, phone, website, rating, reviews_count, category))
        
        listing_id = cursor.lastrowid
        conn.commit()
        print(f"\n[SUCCESS] Added raw listing with ID: {listing_id}")
        
        # Insert a dummy scraped page content to bypass enrichment
        dummy_markdown = f"""# {name} (Manually Added)
Address: {full_address}
Phone: {phone}
Website: {website}
Category: {category}
Rating: {rating} ({reviews_count} reviews)
"""
        cursor.execute("""
            INSERT INTO scraped_pages (raw_listing_id, url, page_markdown, page_title, word_count, http_status, scrape_status)
            VALUES (?, ?, ?, ?, ?, 200, 'scraped')
        """, (listing_id, website, dummy_markdown, name, len(dummy_markdown.split())))
        conn.commit()
        print("[SUCCESS] Seeded scraped_pages. Listing is now ready for AI enrichment!")
        
    except Exception as e:
        print(f"Error adding manual listing: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_manual_listing()
