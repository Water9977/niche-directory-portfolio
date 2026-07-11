import sqlite3
import os
import requests
import json
import time
import sys

# Reconfigure terminal output to support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from dotenv import load_dotenv
load_dotenv()

FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "directory.db")

def scrape_website_content(url):
    api_url = "https://api.firecrawl.dev/v1/scrape"
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True
    }
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                page_data = data.get("data", {})
                markdown = page_data.get("markdown", "")
                metadata = page_data.get("metadata", {})
                title = metadata.get("title", "")
                return markdown, title, 200
            else:
                error = data.get("error", "Unknown error")
                print(f"Firecrawl scrape failed for {url}: {error}")
                return None, None, 500
        else:
            print(f"Firecrawl scrape HTTP error for {url}: {response.status_code}")
            return None, None, response.status_code
    except Exception as e:
        print(f"Firecrawl scrape request error for {url}: {e}")
        return None, None, 500

def enrich_pending_websites(limit=20, niche=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # First: Mark all listings with no website as 'skipped' so we don't try to crawl them
    cursor.execute("""
        UPDATE raw_listings 
        SET scrape_status = 'skipped' 
        WHERE website IS NULL OR website = ''
    """)
    conn.commit()
    
    # Query listings with pending website crawls
    query = """
        SELECT id, name, website 
        FROM raw_listings 
        WHERE scrape_status = 'pending' AND website IS NOT NULL AND website != ''
    """
    params = []
    if niche:
        query += " AND niche = ?"
        params.append(niche)
    query += " LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    listings = cursor.fetchall()
    
    if not listings:
        print("No listings pending website crawls.")
        conn.close()
        return

    print(f"Found {len(listings)} listings pending website crawls in this batch.")
    
    for listing_id, name, url in listings:
        print(f"\nCrawling site for business: '{name}'")
        print(f"URL: {url}")
        
        # Call Firecrawl scrape
        markdown, title, status_code = scrape_website_content(url)
        
        if markdown:
            word_count = len(markdown.split())
            print(f"Successfully scraped site. Word count: {word_count}. Status: {status_code}")
            
            try:
                # Insert into scraped_pages
                cursor.execute("""
                    INSERT INTO scraped_pages (raw_listing_id, url, page_markdown, page_title, word_count, http_status, scrape_status)
                    VALUES (?, ?, ?, ?, ?, ?, 'scraped')
                """, (listing_id, url, markdown, title, word_count, status_code))
                
                # Update raw_listings
                cursor.execute("""
                    UPDATE raw_listings 
                    SET scrape_status = 'scraped' 
                    WHERE id = ?
                """, (listing_id,))
                
                conn.commit()
                print(f"Saved scraped content to DB for {name}.")
            except Exception as e:
                print(f"Database save error for {name}: {e}")
        else:
            print(f"Failed to scrape {name}.")
            try:
                cursor.execute("""
                    UPDATE raw_listings 
                    SET scrape_status = 'failed' 
                    WHERE id = ?
                """, (listing_id,))
                conn.commit()
            except Exception as db_e:
                print(f"DB status update error: {db_e}")
                
        # Polite crawling delay
        time.sleep(3)
        
    conn.close()
    print("\nBatch website scraping completed.")

if __name__ == "__main__":
    limit = 2
    niche = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    if len(sys.argv) > 2:
        niche = sys.argv[2]
    enrich_pending_websites(limit=limit, niche=niche)
