import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DB_DIR, "directory.db")

# Target Cities Seed Data
TARGET_CITIES = [
    # Niche 1: memorycare
    ("memorycare", "Sarasota", "FL", 57000, 69000, 1, "memory care facilities in Sarasota FL"),
    ("memorycare", "Mesa", "AZ", 508000, 65000, 1, "memory care in Mesa AZ"),
    ("memorycare", "The Villages", "FL", 80000, 68000, 1, "dementia care The Villages FL"),
    ("memorycare", "Sun City", "AZ", 39000, 52000, 1, "memory care Sun City AZ"),
    ("memorycare", "Cape Coral", "FL", 204000, 65000, 1, "memory care Cape Coral FL"),
    ("memorycare", "Clearwater", "FL", 117000, 58000, 2, "memory care facilities Clearwater FL"),
    ("memorycare", "Scottsdale", "AZ", 241000, 94000, 2, "memory care Scottsdale AZ"),
    ("memorycare", "Lakeland", "FL", 112000, 52000, 2, "memory care Lakeland FL"),
    ("memorycare", "Gilbert", "AZ", 267000, 105000, 2, "memory care Gilbert AZ"),
    ("memorycare", "Ocala", "FL", 63000, 48000, 2, "dementia care Ocala FL"),
    ("memorycare", "Georgetown", "TX", 75000, 85000, 2, "memory care Georgetown TX"),
    ("memorycare", "Port St. Lucie", "FL", 217000, 68000, 2, "memory care Port St Lucie FL"),
    ("memorycare", "Venice", "FL", 25000, 62000, 3, "memory care Venice FL"),
    ("memorycare", "Peoria", "AZ", 190000, 78000, 3, "memory care Peoria AZ"),
    ("memorycare", "Boynton Beach", "FL", 80000, 60000, 3, "memory care Boynton Beach FL"),

    # Niche 2: restroomrentals
    ("restroomrentals", "McKinney", "TX", 199000, 100000, 1, "luxury restroom trailer rental McKinney TX"),
    ("restroomrentals", "Richardson", "TX", 121000, 85000, 1, "portable restroom trailer rental Richardson TX"),
    ("restroomrentals", "Franklin", "TN", 83000, 115000, 1, "luxury restroom trailer rental Franklin TN"),
    ("restroomrentals", "Dripping Springs", "TX", 5000, 11000, 1, "restroom trailer rental Dripping Springs TX"),
    ("restroomrentals", "Huntersville", "NC", 60000, 102000, 1, "luxury portable restroom Huntersville NC"),
    ("restroomrentals", "Frisco", "TX", 210000, 130000, 2, "restroom trailer rental Frisco TX"),
    ("restroomrentals", "Brentwood", "TN", 44000, 168000, 2, "luxury restroom trailer Brentwood TN"),
    ("restroomrentals", "Georgetown", "TX", 75000, 85000, 2, "portable restroom trailer Georgetown TX"),
    ("restroomrentals", "Cornelius", "NC", 32000, 93000, 2, "restroom trailer rental Cornelius NC"),
    ("restroomrentals", "Leander", "TX", 75000, 102000, 2, "restroom trailer rental Leander TX"),
    ("restroomrentals", "Murfreesboro", "TN", 152000, 66000, 2, "luxury portable restroom Murfreesboro TN"),
    ("restroomrentals", "Wimberley", "TX", 3000, 78000, 3, "restroom trailer rental Wimberley TX"),
    ("restroomrentals", "Nolensville", "TN", 14000, 125000, 3, "portable restroom trailer Nolensville TN"),
    ("restroomrentals", "Weddington", "NC", 12000, 160000, 3, "restroom trailer rental Weddington NC"),

    # Niche 3: rvparks
    ("rvparks", "West Glacier", "MT", 400, 55000, 1, "RV parks near Glacier National Park"),
    ("rvparks", "Moab", "UT", 5300, 52000, 1, "RV parks with wifi Moab UT"),
    ("rvparks", "Sedona", "AZ", 10000, 60000, 1, "RV parks near Sedona AZ"),
    ("rvparks", "Pigeon Forge", "TN", 6300, 48000, 1, "campgrounds near Great Smoky Mountains"),
    ("rvparks", "Estes Park", "CO", 6000, 62000, 1, "RV parks near Rocky Mountain National Park"),
    ("rvparks", "Springdale", "UT", 600, 68000, 2, "RV parks near Zion National Park"),
    ("rvparks", "Tusayan", "AZ", 600, 55000, 2, "campgrounds near Grand Canyon"),
    ("rvparks", "Bar Harbor", "ME", 5800, 72000, 2, "RV parks near Acadia National Park"),
    ("rvparks", "Kanab", "UT", 5000, 54000, 2, "RV parks with cell service Kanab UT"),
    ("rvparks", "Townsend", "TN", 500, 50000, 2, "campgrounds with wifi Townsend TN"),
    ("rvparks", "Custer", "SD", 2100, 52000, 2, "RV parks near Mount Rushmore"),
    ("rvparks", "Cooke City", "MT", 140, 45000, 3, "campgrounds Cooke City MT"),
    ("rvparks", "Gardiner", "MT", 900, 51000, 3, "RV parks near Yellowstone"),
    ("rvparks", "Valle", "AZ", 600, 48000, 3, "campgrounds near Grand Canyon South Rim")
]

def setup_database():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Setting up raw_listings table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw_listings (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        niche           TEXT    NOT NULL,                    -- 'memorycare' | 'restroomrentals' | 'rvparks'
        google_place_id TEXT    UNIQUE NOT NULL,             -- Google Maps Place ID (dedupe key)
        name            TEXT    NOT NULL,
        full_address    TEXT,                                -- Full formatted address string
        city            TEXT,
        state           TEXT,                                -- 2-letter US state code (e.g. 'FL')
        zip_code        TEXT,
        latitude        REAL,
        longitude       REAL,
        phone           TEXT,
        website         TEXT,                                -- Homepage URL (NULL if none listed)
        rating          REAL,                                -- Google Maps average rating (1.0–5.0)
        reviews_count   INTEGER DEFAULT 0,
        google_category TEXT,                                -- Primary Maps category (e.g. 'Memory care center')
        business_hours  TEXT,                                -- JSON string: {"Mon":"8AM-6PM", ...}
        photo_url       TEXT,                                -- First Google Maps photo URL (for thumbnail)
        scrape_source   TEXT    DEFAULT 'firecrawl',         -- 'outscraper' | 'firecrawl' | 'manual'
        scraped_at      TEXT    DEFAULT (datetime('now')),
        scrape_status   TEXT    DEFAULT 'pending'            -- 'pending' | 'scraped' | 'failed' | 'skipped'
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_niche_state ON raw_listings(niche, state);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_niche_city ON raw_listings(niche, city);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_scrape_status ON raw_listings(scrape_status);")

    print("Setting up scraped_pages table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scraped_pages (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_listing_id  INTEGER NOT NULL REFERENCES raw_listings(id),
        url             TEXT    NOT NULL,                    -- The exact URL that was scraped
        page_markdown   TEXT,                                -- Full page content as Markdown (Firecrawl output)
        page_title      TEXT,                                -- <title> tag content
        word_count      INTEGER DEFAULT 0,                   -- For quality filtering (skip pages < 50 words)
        http_status     INTEGER,                             -- 200, 404, 503, etc.
        scraped_at      TEXT    DEFAULT (datetime('now')),
        scrape_status   TEXT    DEFAULT 'pending'            -- 'pending' | 'scraped' | 'failed' | 'blocked'
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_raw_id ON scraped_pages(raw_listing_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pages_status ON scraped_pages(scrape_status);")

    print("Setting up listings table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_listing_id      INTEGER NOT NULL REFERENCES raw_listings(id),
        niche               TEXT    NOT NULL,                -- Redundant for fast niche-filtered queries
        slug                TEXT    UNIQUE NOT NULL,         -- URL slug
        display_name        TEXT    NOT NULL,                -- Clean display name
        city                TEXT    NOT NULL,
        state               TEXT    NOT NULL,
        zip_code            TEXT,
        full_address        TEXT,
        latitude            REAL,
        longitude           REAL,
        phone               TEXT,
        website             TEXT,
        rating              REAL,
        reviews_count       INTEGER DEFAULT 0,

        -- Common pricing fields
        pricing_min         REAL,
        pricing_max         REAL,
        pricing_period      TEXT,
        pricing_note        TEXT,

        -- Common enrichment fields
        amenities_json      TEXT,
        ai_summary          TEXT,
        ai_pros_json        TEXT,
        ai_cons_json        TEXT,
        source_snippet      TEXT,

        -- Niche-specific: memorycare
        dementia_certified      INTEGER,
        staff_to_resident_ratio TEXT,
        monthly_fee_est         REAL,
        medicaid_accepted       INTEGER,
        secure_wander_guard     INTEGER,
        memory_care_levels      TEXT,
        respite_care_available  INTEGER,

        -- Niche-specific: restroomrentals
        stalls_count            INTEGER,
        climate_controlled      INTEGER,
        ada_compliant           INTEGER,
        rental_price_est        REAL,
        delivery_radius_miles   INTEGER,
        suited_for_events_json  TEXT,
        has_running_water       INTEGER,
        has_flushing_toilets    INTEGER,

        -- Niche-specific: rvparks
        verizon_signal          TEXT,
        tmobile_signal          TEXT,
        att_signal              TEXT,
        wifi_available          INTEGER,
        wifi_speed_mbps         REAL,
        hookups_available       TEXT,
        nightly_rate            REAL,
        pet_friendly            INTEGER,
        coworking_space         INTEGER,
        max_rv_length_ft        INTEGER,

        -- Metadata
        enrichment_status   TEXT    DEFAULT 'pending',
        enrichment_model    TEXT,
        last_verified       TEXT    DEFAULT (datetime('now')),
        published           INTEGER DEFAULT 0
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_niche_state ON listings(niche, state);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_niche_city ON listings(niche, city);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_slug ON listings(slug);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_published ON listings(published);")

    print("Setting up target_cities table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS target_cities (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        niche           TEXT    NOT NULL,
        city            TEXT    NOT NULL,
        state           TEXT    NOT NULL,
        population      INTEGER,
        median_income   INTEGER,
        priority        INTEGER DEFAULT 2,
        search_query    TEXT    NOT NULL,
        scrape_status   TEXT    DEFAULT 'pending',
        listings_found  INTEGER DEFAULT 0,
        UNIQUE(niche, city, state)
    );
    """)

    # Seed the cities
    print(f"Seeding {len(TARGET_CITIES)} target cities...")
    for city_data in TARGET_CITIES:
        cursor.execute("""
        INSERT OR IGNORE INTO target_cities (niche, city, state, population, median_income, priority, search_query)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, city_data)

    conn.commit()
    conn.close()
    print("Database setup complete.")

if __name__ == "__main__":
    setup_database()
