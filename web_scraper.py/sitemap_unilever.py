#!/usr/bin/env python3
"""
sitemap_fetcher_static.py

- Uses a static sitemap URL (no CLI required).
- First attempts a requests-based fetch with realistic headers.
- Falls back to headless Playwright if blocked.
- Supports sitemap-index recursion and saves unique URLs to a file.
"""

import time
import random
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import re
from typing import List, Set, Optional

# ---------- STATIC INPUT ----------
# Replace this with the single sitemap URL you want to fetch
SITEMAP_URL = "https://www.degreedeodorant.com/us/en/sitemap.xml"
#SITEMAP_URL = "https://www.rexona.com/br/sitemap-index.xml"
#SITEMAP_URL = "https://www.unilever.com/sitemap.xml"

# ---------- Config ----------
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}

REQUESTS_TIMEOUT = 12  # seconds
SLEEP_BEFORE_FALLBACK = 1.0  # small wait (human-like)
OUTPUT_FILENAME = "sitemap_urls.txt"

PROXIES = None
# Example proxy dict if needed:
# PROXIES = {"http": "http://user:pass@proxy:port", "https": "http://user:pass@proxy:port"}

# ---------- Helpers ----------
def parse_sitemap_xml(xml_bytes: bytes) -> List[str]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        text = xml_bytes.decode("utf-8", errors="ignore")
        text = text.strip()
        return re.findall(r"<loc>(.*?)</loc>", text, re.IGNORECASE | re.DOTALL)

    urls = []
    for elem in root.iter():
        tag = elem.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        if tag.lower() == "loc" and elem.text:
            urls.append(elem.text.strip())
    return urls

def is_sitemap_index(xml_bytes: bytes) -> bool:
    text = xml_bytes.decode("utf-8", errors="ignore").lower()
    return "<sitemapindex" in text or "<sitemap>" in text

# ---------- Requests fetch ----------
def fetch_with_requests(url: str, session: Optional[requests.Session] = None) -> Optional[bytes]:
    sess = session or requests.Session()
    sess.headers.update(DEFAULT_HEADERS)
    try:
        print(f"[requests] GET {url}")
        resp = sess.get(url, timeout=REQUESTS_TIMEOUT, proxies=PROXIES)
        if resp.status_code == 403:
            print(f"[requests] 403 Forbidden for {url}")
            return None
        if resp.status_code != 200:
            print(f"[requests] Received status {resp.status_code} for {url}")
            return None
        return resp.content
    except requests.RequestException as e:
        print(f"[requests] Exception: {e}")
        return None

# ---------- Playwright fallback ----------
def fetch_with_playwright(url: str, headless: bool = True) -> Optional[bytes]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("[playwright] Playwright not installed or import failed:", e)
        return None

    print(f"[playwright] Launching headless browser for {url} ... (headless={headless})")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless, args=["--no-sandbox", "--disable-setuid-sandbox"])
            context = browser.new_context(
                user_agent=DEFAULT_UA,
                locale="en-US",
                java_script_enabled=True,
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.set_extra_http_headers({"referer": "https://www.google.com/"})
            page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(random.uniform(0.4, 1.2))
            content = page.content()
            page.close()
            context.close()
            browser.close()
            return content.encode("utf-8")
    except Exception as e:
        print("[playwright] Error while fetching:", e)
        return None

# ---------- Collector ----------
def collect_sitemap_urls(start_url: str, use_playwright_fallback: bool = True) -> Set[str]:
    to_process = [start_url]
    seen_sitemaps = set()
    collected_urls: Set[str] = set()
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    while to_process:
        sitemap = to_process.pop(0)
        if sitemap in seen_sitemaps:
            continue
        seen_sitemaps.add(sitemap)

        xml_bytes = fetch_with_requests(sitemap, session=session)
        if xml_bytes is None and use_playwright_fallback:
            time.sleep(SLEEP_BEFORE_FALLBACK + random.random() * 0.5)
            xml_bytes = fetch_with_playwright(sitemap, headless=True)

        if not xml_bytes:
            print(f"[warning] Failed to fetch sitemap: {sitemap}")
            continue

        locs = parse_sitemap_xml(xml_bytes)
        if not locs:
            print(f"[warning] No <loc> found in {sitemap} (trying regex fallback).")
            text = xml_bytes.decode("utf-8", errors="ignore")
            locs = re.findall(r"<loc>(.*?)</loc>", text, re.IGNORECASE | re.DOTALL)

        if is_sitemap_index(xml_bytes):
            print(f"[info] Sitemap-index detected: {sitemap} -> {len(locs)} nested sitemaps")
            for loc in locs:
                nested = urljoin(sitemap, loc.strip())
                if nested not in seen_sitemaps:
                    to_process.append(nested)
            continue

        for loc in locs:
            url = urljoin(sitemap, loc.strip())
            collected_urls.add(url)

        print(f"[info] Collected {len(collected_urls)} URLs so far (processed sitemap: {sitemap})")
        time.sleep(random.uniform(0.2, 0.6))

    return collected_urls

# ---------- Run ----------
def main():
    print(f"Starting sitemap collection for: {SITEMAP_URL}")
    urls = collect_sitemap_urls(SITEMAP_URL, use_playwright_fallback=True)

    if urls:
        print(f"\nTotal unique URLs found: {len(urls)}")
        with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
            for u in sorted(urls):
                f.write(u + "\n")
        print(f"Saved URLs to: {OUTPUT_FILENAME}")
    else:
        print("No URLs found.")

if __name__ == "__main__":
    main()
