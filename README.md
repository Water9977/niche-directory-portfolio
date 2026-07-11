# 🗂️ Niche Directory Portfolio

A portfolio of **three hyper-focused local directory websites**, built with static site generation for maximum SEO performance and zero hosting costs. Each site targets an underserved Google search niche where users are actively searching but existing results are fragmented or lack key data (pricing, verified amenities, connectivity).

---

## 📋 The Three Directories

| # | Directory | Target Audience | Unique Value Proposition |
|---|-----------|----------------|--------------------------|
| 1 | **Memory Care Finder** | Adult children searching for dementia/memory care for aging parents | Verified monthly pricing, Medicaid acceptance, staff ratios — data Google Maps doesn't show |
| 2 | **Luxury Restroom Rentals** | Event planners & wedding coordinators | Side-by-side trailer comparisons with stall counts, ADA compliance, and delivery radius |
| 3 | **Camp Connected** | Digital nomads & remote-working RVers | Carrier-by-carrier cell signal reports (Verizon/T-Mobile/AT&T) and verified Wi-Fi speeds |

---

## 🏗️ Architecture

The system is designed around a **scrape → enrich → build → deploy** pipeline:

```
Google Maps → Python Scrapers → Gemini AI Extraction → SQLite → JSON → Astro SSG → Cloudflare Pages
```

### Data Pipeline
1. **`google_maps.py`** — Scrapes Google Maps for business listings in target cities
2. **`web_enricher.py`** — Downloads each listing's website via Firecrawl MCP and converts to Markdown
3. **`ai_processor.py`** — Sends page content to Gemini 2.5 Flash to extract structured pricing, amenities, and signals
4. **`export_json.py`** — Exports enriched data as JSON for Astro's static build

### Key Design Decisions
- **Zero-JS Runtime:** Astro compiles to pure HTML/CSS — 100/100 Lighthouse scores guaranteed
- **No Live Database:** SQLite is only used during build. Production sites are fully static
- **Free Hosting:** Cloudflare Pages (unlimited bandwidth) or Vercel/Netlify free tiers
- **Privacy-First Analytics:** Plausible or Umami — no cookie banners needed

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Static Site Generator | [Astro 5.x](https://astro.build) |
| Styling | Vanilla CSS |
| Data Pipeline | Python 3.12 + SQLite |
| Scraping | Firecrawl MCP + Playwright MCP |
| AI Extraction | Gemini 2.5 Flash API |
| Hosting | Cloudflare Pages |
| Analytics | Plausible / Umami |

---

## 📁 Project Structure

```
├── .agents/              # AI agent rules and skill mappings
├── Manual/               # Market validation screenshots (Google search audits)
├── architecture.md       # Complete system blueprint (source of truth)
├── pipeline/             # Python scraping & enrichment engine (coming soon)
│   ├── data/
│   │   └── directory.db  # SQLite database (local only, not committed)
│   └── scripts/
├── web1-memorycare/      # Astro site: Memory Care Directory
├── web2-restroomrentals/ # Astro site: Luxury Restroom Trailer Directory
└── web3-rvparks/         # Astro site: RV Parks with Signal Reports
```

---

## 💰 Revenue Model

Each directory monetizes through a mix of:
- **Display Ads** (Mediavine/Raptive) on informational pages
- **Featured Listings** — businesses pay for highlighted placement
- **Lead Referral Fees** — qualified inquiry forwarding
- **Affiliate Links** — relevant product recommendations

**Projected portfolio revenue at Month 12: $1,950–$5,685/month** (zero ad spend)

---

## 📊 Current Status

| Phase | Status |
|-------|--------|
| ✅ Niche Research & Validation | Complete |
| ✅ Market Audit (Manual Google Searches) | Complete |
| ✅ Architecture & Schema Design | Complete |
| ✅ Target City Lists | Complete |
| ✅ AI Prompt Templates | Complete |
| ✅ Data Pipeline Implementation | Complete (Playwright + Firecrawl + Gemini Fallbacks) |
| ✅ Astro Site Scaffolding | Complete (Clean Vanilla CSS + Interactive Filters) |
| ✅ First Scrape & Build | Complete (Texas / Montana Seed Sets) |
| 🔲 Domain Purchase & Deployment | Planned |

---

## 📖 Documentation

The single source of truth for this project is [`architecture.md`](architecture.md). It contains:
- Database schemas (4 tables with full SQL DDL)
- Target city lists per niche (45 cities across 3 niches)
- Crawling configuration and rate limits
- AI extraction prompt templates (per niche)
- JSON export format for Astro
- SEO strategy with keyword tables
- Monetization channels and revenue projections
- Page-level content requirements
- Structured data markup (Schema.org)
- Build-to-deploy workflow

---

## 📄 License

This project is proprietary. All rights reserved.
