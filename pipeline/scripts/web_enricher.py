import sqlite3
import os
import requests
import json
import time
import sys
import re
import urllib.parse
from urllib.parse import urlparse

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

def extract_key_subpages(homepage_url, markdown_content):
    # Find links in markdown: [Anchor Text](URL)
    links = re.findall(r'\[([^\]]*?)\]\((https?://[^\)]+|/[^\)]+)\)', markdown_content)
    
    parsed_home = urlparse(homepage_url)
    home_domain = parsed_home.netloc.lower().replace("www.", "")
    
    key_links = []
    seen_urls = set()
    seen_urls.add(homepage_url.rstrip("/"))
    
    # Priority keywords for matching pricing, services, about pages
    priority_keywords = ["price", "pricing", "rate", "cost", "fee", "rent", "rental", "about", "service", "amenities", "package", "packages"]
    
    for anchor, link_url in links:
        # Resolve relative URLs
        absolute_url = urllib.parse.urljoin(homepage_url, link_url).split("#")[0].rstrip("/")
        
        parsed_link = urlparse(absolute_url)
        link_domain = parsed_link.netloc.lower().replace("www.", "")
        
        # Check if internal link
        if link_domain == home_domain or not link_domain:
            if absolute_url not in seen_urls:
                priority = 0
                anchor_lower = anchor.lower()
                url_lower = absolute_url.lower()
                
                # Exclude obvious non-informational files or sections
                if any(ext in url_lower for ext in [".pdf", ".jpg", ".png", ".zip", "tel:", "mailto:"]):
                    continue
                
                for keyword in priority_keywords:
                    if keyword in anchor_lower or keyword in url_lower:
                        priority += 5
                        if keyword in ["price", "pricing", "rate", "cost"]:
                            priority += 5
                            
                key_links.append((absolute_url, priority))
                seen_urls.add(absolute_url)
                
    key_links.sort(key=lambda x: x[1], reverse=True)
    
    # Select top 2 subpages that match priority keywords
    top_subpages = [url for url, score in key_links if score > 0][:2]
    
    # If we still have less than 2, pad with general internal links
    if len(top_subpages) < 2:
        extra_pages = [url for url, score in key_links if score == 0]
        top_subpages.extend(extra_pages[:2 - len(top_subpages)])
        
    return top_subpages

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
        
        # Scrape Homepage
        homepage_markdown, title, status_code = scrape_website_content(url)
        
        if homepage_markdown:
            combined_markdown = f"# Homepage: {url}\n{homepage_markdown}"
            
            # Find and scrape key subpages (e.g. pricing)
            subpages = extract_key_subpages(url, homepage_markdown)
            if subpages:
                print(f"Discovered relevant subpages for enrichment: {subpages}")
                for subpage in subpages:
                    print(f"  Scraping subpage: {subpage}")
                    sub_md, sub_title, sub_status = scrape_website_content(subpage)
                    if sub_md:
                        combined_markdown += f"\n\n--- SUBPAGE: {subpage} ---\n{sub_md}"
                        time.sleep(2)
            
            word_count = len(combined_markdown.split())
            print(f"Successfully scraped site pages. Total word count: {word_count}. Status: {status_code}")
            
            try:
                # Insert into scraped_pages
                cursor.execute("""
                    INSERT INTO scraped_pages (raw_listing_id, url, page_markdown, page_title, word_count, http_status, scrape_status)
                    VALUES (?, ?, ?, ?, ?, ?, 'scraped')
                """, (listing_id, url, combined_markdown, title, word_count, status_code))
                
                # Update raw_listings
                cursor.execute("""
                    UPDATE raw_listings 
                    SET scrape_status = 'scraped' 
                    WHERE id = ?
                """, (listing_id,))
                
                conn.commit()
                print(f"Saved combined scraped content to DB for {name}.")
            except Exception as e:
                print(f"Database save error for {name}: {e}")
        else:
            print(f"Failed to scrape homepage for {name}.")
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
