import sqlite3
import os
import json
import re
import sys
import time
from google import genai
from google.genai import types

# Reconfigure terminal output to support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "directory.db")

# Load API key from env or .env file
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # Try reading from .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("GEMINI_API_KEY="):
                    GEMINI_API_KEY = line.replace("GEMINI_API_KEY=", "").strip()
                    break

# Configure genai client
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in environment or .env file.")

# Niche Prompts
PROMPTS = {
    "memorycare": """
You are a data extraction assistant. Given the following webpage content from a memory care facility's website, extract the following fields as a JSON object. If a field is not mentioned, use null. Do not infer or guess values — only extract what is explicitly stated or clearly implied.

Fields to extract:
- "pricing_min": number (lowest monthly cost mentioned, in USD)
- "pricing_max": number (highest monthly cost mentioned, in USD)
- "pricing_period": "monthly" (always monthly for this niche)
- "pricing_note": string (any caveats like "starting from" or "depends on level of care")
- "dementia_certified": boolean (does the facility mention Alzheimer's/dementia certification?)
- "staff_to_resident_ratio": string (e.g. "1:6")
- "medicaid_accepted": boolean (does it mention Medicaid or Medicaid waiver?)
- "secure_wander_guard": boolean (mentions secure memory unit, wander guard, locked doors?)
- "memory_care_levels": array of strings (e.g. ["early_stage", "mid_stage", "late_stage"])
- "respite_care_available": boolean
- "amenities": array of strings (e.g. ["garden", "art_therapy", "music_therapy", "pet_therapy"])
- "summary": string (2-3 sentence summary of what this facility offers)
- "pros": array of strings (up to 3 positive highlights)
- "cons": array of strings (up to 2 negatives or warnings)
- "source_snippet": string (a verbatim sentence from the website that mentions pricing or care level)

Respond ONLY with valid JSON. No explanation.
""",
    "restroomrentals": """
You are a data extraction assistant. Given the following webpage content from a portable restroom trailer rental company's website, extract the following fields as a JSON object. If a field is not mentioned, use null.

Fields to extract:
- "pricing_min": number (lowest rental price mentioned, in USD)
- "pricing_max": number (highest rental price mentioned, in USD)
- "pricing_period": "per_event" (always per_event for this niche)
- "pricing_note": string (e.g. "delivery fee extra", "minimum 4-hour rental")
- "stalls_count": number (number of stalls in largest trailer)
- "climate_controlled": boolean (air conditioning/heating mentioned?)
- "ada_compliant": boolean (ADA-accessible unit mentioned?)
- "delivery_radius_miles": number (how far they deliver)
- "has_running_water": boolean
- "has_flushing_toilets": boolean
- "suited_for_events": array of strings (e.g. ["weddings", "festivals", "construction", "corporate"])
- "amenities": array of strings (e.g. ["vanity_mirrors", "music_system", "hand_towels", "fresh_flowers"])
- "summary": string (2-3 sentence summary)
- "pros": array of strings (up to 3)
- "cons": array of strings (up to 2)
- "source_snippet": string (verbatim sentence proving pricing or service area)

Respond ONLY with valid JSON. No explanation.
""",
    "rvparks": """
You are a data extraction assistant. Given the following webpage content from an RV park or campground's website, extract the following fields as a JSON object. If a field is not mentioned, use null. Pay special attention to any mentions of cellular signal quality, Wi-Fi, or internet connectivity.

Fields to extract:
- "pricing_min": number (lowest nightly rate, in USD)
- "pricing_max": number (highest nightly rate, in USD)
- "pricing_period": "nightly"
- "pricing_note": string (e.g. "weekly/monthly discounts available", "peak season rates")
- "verizon_signal": "strong" | "medium" | "weak" | "none" | null
- "tmobile_signal": "strong" | "medium" | "weak" | "none" | null
- "att_signal": "strong" | "medium" | "weak" | "none" | null
- "wifi_available": boolean
- "wifi_speed_mbps": number (if a speed is mentioned)
- "hookups_available": array of strings (e.g. ["full_hookup", "water_electric", "dry_camping"])
- "pet_friendly": boolean
- "coworking_space": boolean (dedicated work area, business center?)
- "max_rv_length_ft": number
- "nightly_rate": number (most common rate)
- "amenities": array of strings (e.g. ["pool", "laundry", "dump_station", "propane", "store"])
- "summary": string (2-3 sentence summary)
- "pros": array of strings (up to 3)
- "cons": array of strings (up to 2)
- "source_snippet": string (verbatim sentence about connectivity or pricing)

Respond ONLY with valid JSON. No explanation.
"""
}

def clean_json_response(text):
    # Strip markdown block formatting if present
    if "```" in text:
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    
    # Extract the first matching JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text

def generate_slug(name, city, state):
    # Convert name-city-state to url friendly slug
    slug = f"{name}-{city}-{state}".lower()
    # Replace non-alphanumeric characters with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Remove duplicate/trailing hyphens
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug

def process_enrichment(limit=5):
    if not client:
        print("Error: GEMINI_API_KEY is not configured. Cannot proceed with AI enrichment.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query scraped pages that are pending enrichment in listings
    # We join scraped_pages with raw_listings to get name, city, state, niche
    cursor.execute("""
        SELECT p.id, p.page_markdown, r.id, r.name, r.city, r.state, r.niche, r.website, r.rating, r.reviews_count
        FROM scraped_pages p
        JOIN raw_listings r ON p.raw_listing_id = r.id
        LEFT JOIN listings l ON l.raw_listing_id = r.id
        WHERE p.scrape_status = 'scraped' AND (l.enrichment_status IS NULL OR l.enrichment_status = 'pending')
        LIMIT ?
    """, (limit,))
    
    pages = cursor.fetchall()
    if not pages:
        print("No scraped pages pending AI enrichment.")
        conn.close()
        return

    print(f"Found {len(pages)} pages to enrich via Gemini API.")

    for page_id, markdown, raw_id, name, city, state, niche, website, rating, reviews_count in pages:
        print(f"\nProcessing AI Enrichment for: '{name}' ({niche}) in {city}, {state}")
        
        prompt_template = PROMPTS.get(niche)
        if not prompt_template:
            print(f"Error: Unknown niche type '{niche}'. Skipping.")
            continue
            
        prompt = prompt_template + f"\nWebpage content:\n---\n{markdown}\n---"
        
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=4096,
                    thinking_config=types.ThinkingConfig(thinking_budget=1024)
                )
            )
            raw_text = response.text
            clean_text = clean_json_response(raw_text)
            data = json.loads(clean_text)
            
            # Generate slug
            slug = generate_slug(name, city, state)
            
            # Prepare common fields
            pricing_min = data.get("pricing_min")
            pricing_max = data.get("pricing_max")
            pricing_period = data.get("pricing_period")
            pricing_note = data.get("pricing_note")
            
            amenities = json.dumps(data.get("amenities", []))
            ai_summary = data.get("summary", "")
            ai_pros = json.dumps(data.get("pros", []))
            ai_cons = json.dumps(data.get("cons", []))
            source_snippet = data.get("source_snippet", "")
            
            # Check if listing already exists
            cursor.execute("SELECT id FROM listings WHERE raw_listing_id = ?", (raw_id,))
            exists = cursor.fetchone()
            
            if exists:
                listing_id = exists[0]
                cursor.execute("""
                    UPDATE listings SET
                        slug = ?, display_name = ?, city = ?, state = ?, website = ?, rating = ?, reviews_count = ?,
                        pricing_min = ?, pricing_max = ?, pricing_period = ?, pricing_note = ?,
                        amenities_json = ?, ai_summary = ?, ai_pros_json = ?, ai_cons_json = ?, source_snippet = ?,
                        enrichment_status = 'enriched', enrichment_model = 'gemini-3.5-flash', last_verified = datetime('now'), published = 1
                    WHERE id = ?
                """, (slug, name, city, state, website, rating, reviews_count, pricing_min, pricing_max, pricing_period, pricing_note,
                      amenities, ai_summary, ai_pros, ai_cons, source_snippet, listing_id))
            else:
                cursor.execute("""
                    INSERT INTO listings (
                        raw_listing_id, niche, slug, display_name, city, state, website, rating, reviews_count,
                        pricing_min, pricing_max, pricing_period, pricing_note,
                        amenities_json, ai_summary, ai_pros_json, ai_cons_json, source_snippet,
                        enrichment_status, enrichment_model, published
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'enriched', 'gemini-3.5-flash', 1)
                """, (raw_id, niche, slug, name, city, state, website, rating, reviews_count,
                      pricing_min, pricing_max, pricing_period, pricing_note,
                      amenities, ai_summary, ai_pros, ai_cons, source_snippet))
                listing_id = cursor.lastrowid
                
            # Update Niche-Specific fields
            if niche == "memorycare":
                dementia_certified = 1 if data.get("dementia_certified") else 0
                staff_ratio = data.get("staff_to_resident_ratio")
                monthly_fee = data.get("monthly_fee_est") or pricing_min
                medicaid = 1 if data.get("medicaid_accepted") else 0
                wander_guard = 1 if data.get("secure_wander_guard") else 0
                care_levels = json.dumps(data.get("memory_care_levels", []))
                respite = 1 if data.get("respite_care_available") else 0
                
                cursor.execute("""
                    UPDATE listings SET
                        dementia_certified = ?, staff_to_resident_ratio = ?, monthly_fee_est = ?,
                        medicaid_accepted = ?, secure_wander_guard = ?, memory_care_levels = ?, respite_care_available = ?
                    WHERE id = ?
                """, (dementia_certified, staff_ratio, monthly_fee, medicaid, wander_guard, care_levels, respite, listing_id))
                
            elif niche == "restroomrentals":
                stalls = data.get("stalls_count")
                climate = 1 if data.get("climate_controlled") else 0
                ada = 1 if data.get("ada_compliant") else 0
                rental_price = data.get("rental_price_est") or pricing_min
                delivery = data.get("delivery_radius_miles")
                suited = json.dumps(data.get("suited_for_events", []))
                running_water = 1 if data.get("has_running_water") else 0
                flushing = 1 if data.get("has_flushing_toilets") else 0
                
                cursor.execute("""
                    UPDATE listings SET
                        stalls_count = ?, climate_controlled = ?, ada_compliant = ?, rental_price_est = ?,
                        delivery_radius_miles = ?, suited_for_events_json = ?, has_running_water = ?, has_flushing_toilets = ?
                    WHERE id = ?
                """, (stalls, climate, ada, rental_price, delivery, suited, running_water, flushing, listing_id))
                
            elif niche == "rvparks":
                v_sig = data.get("verizon_signal")
                t_sig = data.get("tmobile_signal")
                a_sig = data.get("att_signal")
                wifi = 1 if data.get("wifi_available") else 0
                wifi_speed = data.get("wifi_speed_mbps")
                hookups = json.dumps(data.get("hookups_available", []))
                rate = data.get("nightly_rate") or pricing_min
                pets = 1 if data.get("pet_friendly") else 0
                coworking = 1 if data.get("coworking_space") else 0
                max_len = data.get("max_rv_length_ft")
                
                cursor.execute("""
                    UPDATE listings SET
                        verizon_signal = ?, tmobile_signal = ?, att_signal = ?, wifi_available = ?,
                        wifi_speed_mbps = ?, hookups_available = ?, nightly_rate = ?, pet_friendly = ?,
                        coworking_space = ?, max_rv_length_ft = ?
                    WHERE id = ?
                """, (v_sig, t_sig, a_sig, wifi, wifi_speed, hookups, rate, pets, coworking, max_len, listing_id))
                
            conn.commit()
            print(f"Successfully enriched and saved listing for: {name} (Slug: {slug})")
            
        except Exception as e:
            print(f"AI enrichment failed for {name}: {e}")
            
        # Throttling delay
        time.sleep(2)
        
    conn.close()
    print("\nAI Enrichment batch completed.")

if __name__ == "__main__":
    limit = 5
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    process_enrichment(limit=limit)
