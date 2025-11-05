# GHC Session Data Scraper

Python Selenium script to scrape session details from GHC Conference website.

### Features
- Scrapes session titles, descriptions, speakers, date/time, location & tracks
- Firefox (GeckoDriver) support — Mac M2 optimized
- Handles lazy-loaded content & show-more expansion
- CSV export

### Run Script

//Full Script
```bash
python3 ghc_scraper.py full ghc_full.csv

//Test Script
Test 25 rows:
```bash
python3 ghc_scraper.py
