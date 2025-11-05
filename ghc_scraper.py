import csv
import sys
import time
import random
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


CATALOG_URL = "https://ghc.anitab.org/session-catalog?search=&tab.eventday=1759115846891001vg9z#/"

def norm(text):
    return " ".join(text.split()).strip() if text else ""

def scroll_center(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    time.sleep(0.3)

@dataclass
class SessionRow:
    title: str
    desc: str
    date: str
    time: str
    location: str
    tracks: str
    speakers: str

class GHCScraper:
    def __init__(self, test_mode=True, csv_path="ghc_sessions.csv", headless=False):
        self.test_mode = test_mode
        self.csv_path = csv_path

        options = FirefoxOptions()
        if headless:
            options.add_argument("-headless")

        self.driver = webdriver.Firefox(options=options, service=FirefoxService())
        self.wait = WebDriverWait(self.driver, 15)

    def open_site(self):
        self.driver.get(CATALOG_URL)
        self.driver.maximize_window()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#catalogtabpanel")))

    def switch_to_list(self):
        try:
            btn = self.driver.find_element(
                By.CSS_SELECTOR, 'div.mdBtnR-toggle button[data-test="rf-button-1"]'
            )
            scroll_center(self.driver, btn)
            btn.click()
        except:
            pass

        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.search-results")))

    def cards(self):
        return self.driver.find_elements(By.CSS_SELECTOR, "ul.search-results > li")

    def click_show_more_desc(self, li):
        try:
            btn = li.find_element(By.CSS_SELECTOR, 'button[data-test="rf-button-show-more-less-link"]')
            scroll_center(self.driver, btn)
            btn.click()
            time.sleep(random.uniform(1.1, 2.0))  # Required wait
        except:
            pass  # No show-more button, move on

    def extract_desc(self, li):
        self.click_show_more_desc(li)
        try:
            desc_div = li.find_element(By.CSS_SELECTOR, "div.description")
            ps = desc_div.find_elements(By.CSS_SELECTOR, "p")
            return " ".join(norm(p.text) for p in ps if p.text.strip())
        except:
            return ""

    def extract_time_date_location(self, li):
        try:
            base = li.find_element(By.CSS_SELECTOR, "div.session-time-and-location")
            dt = base.find_element(By.CSS_SELECTOR, "div.session-date-time")

            date = norm(dt.find_element(By.CSS_SELECTOR, "span.session-date").text)
            time_txt = norm(dt.find_element(By.CSS_SELECTOR, "span.session-time").text)

            loc_el = base.find_element(By.CSS_SELECTOR, 'span.session-location[data-test="room-name"]')
            inner = loc_el.find_elements(By.CSS_SELECTOR, "span")
            location = norm(inner[0].text if inner else loc_el.text)

            return date, time_txt, location
        except:
            return "", "", ""

    def extract_tracks(self, li):
        try:
            el = li.find_element(By.CSS_SELECTOR, "div.attribute-SessionTracks span.attribute-values")
            return norm(el.text)
        except:
            return ""

    def extract_speakers(self, li):
        """Scrape speakers only if speaker section exists"""
        try:
            container = li.find_element(
                By.CSS_SELECTOR,
                'div.session-details.speaker-details[data-test="session-participants-area"]'
            )
        except:
            return ""  # No speakers for this session

        speakers = []
        ps = container.find_elements(By.CSS_SELECTOR, "p")

        for p in ps:
            try:
                name = p.find_element(By.CSS_SELECTOR, "button").text.strip()
            except:
                continue  # skip malformed blocks

            full = p.text.strip()
            details = full.replace(name, "").strip(",-– ")

            if details:
                speakers.append(f"{name} – {details}")
            else:
                speakers.append(name)

        return " | ".join(speakers)

    def click_show_more_page(self):
        try:
            btn = self.driver.find_element(By.CSS_SELECTOR, "button.show-more-btn")
            scroll_center(self.driver, btn)
            btn.click()
            time.sleep(1.2)
            return True
        except:
            return False

    def scrape_card(self, li):
        scroll_center(self.driver, li)

        # Title
        try:
            title = li.find_element(
                By.CSS_SELECTOR,
                "div.catalog-result-title.session-title.rf-simple-flex-frame div.title-text"
            ).text
        except:
            title = ""
        title = norm(title)

        desc = self.extract_desc(li)
        date, time_txt, location = self.extract_time_date_location(li)
        tracks = self.extract_tracks(li)
        speakers = self.extract_speakers(li)  # ✅ Only scraped if exists

        return SessionRow(title, desc, date, time_txt, location, tracks, speakers)

    def write_csv(self, rows):
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "Session Title", "Description", "Date", "Time", "Location",
                "Session tracks", "Speakers and Details"
            ])
            for r in rows:
                w.writerow([r.title, r.desc, r.date, r.time, r.location, r.tracks, r.speakers])

        print(f"\n✅ Saved {len(rows)} rows → {self.csv_path}")

    def run(self):
        rows, seen = [], set()

        self.open_site()
        self.switch_to_list()

        while True:
            for li in self.cards():
                sid = li.get_attribute("data-session-id") or id(li)
                if sid in seen:
                    continue
                seen.add(sid)

                row = self.scrape_card(li)

                if row.title.strip():
                    rows.append(row)
                    print(f"✅ {row.title}")

                if self.test_mode and len(rows) >= 25:
                    self.write_csv(rows)
                    self.driver.quit()
                    return

            if self.test_mode:
                self.write_csv(rows)
                self.driver.quit()
                return

            if not self.click_show_more_page():
                break

        self.write_csv(rows)
        self.driver.quit()


if __name__ == "__main__":
    test = not (len(sys.argv) > 1 and sys.argv[1].lower() == "full")
    out = "ghc_sessions.csv" if test else (
        sys.argv[2] if len(sys.argv) > 2 else "ghc_full.csv"
    )

    GHCScraper(test_mode=test, csv_path=out, headless=False).run()