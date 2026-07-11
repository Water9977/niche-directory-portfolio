import sqlite3
import os
import json
import sys

# Reconfigure terminal output to support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "directory.db")
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NICHE_OUTPUTS = {
    "memorycare": os.path.join(WORKSPACE_DIR, "web1-memorycare", "src", "data", "listings.json"),
    "restroomrentals": os.path.join(WORKSPACE_DIR, "web2-restroomrentals", "src", "data", "listings.json"),
    "rvparks": os.path.join(WORKSPACE_DIR, "web3-rvparks", "src", "data", "listings.json")
}

def export_listings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query all published listings
    cursor.execute("""
        SELECT 
            niche, slug, display_name, city, state, zip_code, full_address, latitude, longitude, phone, website, rating, reviews_count,
            pricing_min, pricing_max, pricing_period, pricing_note,
            amenities_json, ai_summary, ai_pros_json, ai_cons_json, source_snippet,
            -- memorycare fields
            dementia_certified, staff_to_resident_ratio, monthly_fee_est, medicaid_accepted, secure_wander_guard, memory_care_levels, respite_care_available,
            -- restroomrentals fields
            stalls_count, climate_controlled, ada_compliant, rental_price_est, delivery_radius_miles, suited_for_events_json, has_running_water, has_flushing_toilets,
            -- rvparks fields
            verizon_signal, tmobile_signal, att_signal, wifi_available, wifi_speed_mbps, hookups_available, nightly_rate, pet_friendly, coworking_space, max_rv_length_ft,
            last_verified
        FROM listings
        WHERE published = 1
    """)
    
    rows = cursor.fetchall()
    if not rows:
        print("No published listings found to export.")
        conn.close()
        return

    # Categorize by niche
    niche_data = {
        "memorycare": [],
        "restroomrentals": [],
        "rvparks": []
    }
    
    for row in rows:
        niche = row[0]
        if niche not in niche_data:
            continue
            
        # Parse JSON lists safely
        try:
            amenities = json.loads(row[17]) if row[17] else []
        except:
            amenities = []
            
        try:
            ai_pros = json.loads(row[19]) if row[19] else []
        except:
            ai_pros = []
            
        try:
            ai_cons = json.loads(row[20]) if row[20] else []
        except:
            ai_cons = []

        item = {
            "slug": row[1],
            "displayName": row[2],
            "city": row[3],
            "state": row[4],
            "zipCode": row[5],
            "fullAddress": row[6],
            "latitude": row[7],
            "longitude": row[8],
            "phone": row[9],
            "website": row[10],
            "rating": row[11],
            "reviewsCount": row[12],
            "pricingMin": row[13],
            "pricingMax": row[14],
            "pricingPeriod": row[15],
            "pricingNote": row[16],
            "amenities": amenities,
            "aiSummary": row[18],
            "aiPros": ai_pros,
            "aiCons": ai_cons,
            "sourceSnippet": row[21],
            "nicheFields": {},
            "lastVerified": row[47]
        }
        
        # Populate niche specific fields
        if niche == "memorycare":
            try:
                care_levels = json.loads(row[27]) if row[27] else []
            except:
                care_levels = []
            item["nicheFields"] = {
                "dementiaCertified": bool(row[22]),
                "staffToResidentRatio": row[23],
                "monthlyFeeEst": row[24],
                "medicaidAccepted": bool(row[25]),
                "secureWanderGuard": bool(row[26]),
                "memoryCareLevels": care_levels,
                "respiteCareAvailable": bool(row[28])
            }
        elif niche == "restroomrentals":
            try:
                suited_events = json.loads(row[34]) if row[34] else []
            except:
                suited_events = []
            item["nicheFields"] = {
                "stallsCount": row[29],
                "climateControlled": bool(row[30]),
                "adaCompliant": bool(row[31]),
                "rentalPriceEst": row[32],
                "deliveryRadiusMiles": row[33],
                "suitedForEvents": suited_events,
                "hasRunningWater": bool(row[35]),
                "hasFlushingToilets": bool(row[36])
            }
        elif niche == "rvparks":
            try:
                hookups = json.loads(row[42]) if row[42] else []
            except:
                hookups = []
            item["nicheFields"] = {
                "verizonSignal": row[37],
                "tmobileSignal": row[38],
                "attSignal": row[39],
                "wifiAvailable": bool(row[40]),
                "wifiSpeedMbps": row[41],
                "hookupsAvailable": hookups,
                "nightlyRate": row[43],
                "petFriendly": bool(row[44]),
                "coworkingSpace": bool(row[45]),
                "maxRvLengthFt": row[46] # max_rv_length_ft is indexed at row[46]
            }
            
        niche_data[niche].append(item)
        
    conn.close()
    
    # Write to target files
    for niche, data in niche_data.items():
        output_path = NICHE_OUTPUTS[niche]
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Exported {len(data)} listings for {niche} to: {output_path}")
        except Exception as e:
            print(f"Failed to export {niche} JSON: {e}")

if __name__ == "__main__":
    export_listings()
