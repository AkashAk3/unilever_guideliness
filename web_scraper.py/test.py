import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import json
import time
import os
import re
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import pandas as pd

# ----------- CONFIG / STATIC INPUT -----------
# URL_INPUT = "https://www.tanyapepsodent.com/home.html"
# URL_INPUT = "https://www.rexona.com/br/home.html"
URL_INPUT = "https://www.dove.com/us/en/home.html"
# URL_INPUT = "https://www.suredeodorant.co.uk/home.html"

url_sitemap_dict = {
    "https://www.degreedeodorant.com/us/en/home.html": "https://www.degreedeodorant.com/us/en/sitemap.xml",
    "https://www.rexona.com/br/home.html": "https://www.rexona.com/br/sitemap-index.xml",
    "https://www.suredeodorant.co.uk/home.html": "https://www.suredeodorant.co.uk/sitemap.xml",
    "https://www.dove.com/us/en/home.html": "https://www.dove.com/us/en/sitemap-index.xml",
    "https://www.tanyapepsodent.com/home.html": "https://www.tanyapepsodent.com/sitemap-index.xml",
    "https://www.unilever.com/": "https://www.unilever.com/sitemap.xml"
}

# Scraping config
MAX_PAGES = 10  # Set to a number to limit pages, None for all
SAVE_BATCH_SIZE = 100  # Save to disk every N pages
MAX_WORKERS = 10  # Number of parallel threads
REQUEST_TIMEOUT = 30  # Timeout per request in seconds
OUTPUT_DIR = "scraped_html_files"  # Directory to save .txt files
# ----------------------------------------------

BROWSER_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "connection": "keep-alive",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}

COOKIE_HEADER = ("OptanonConsent=isGpcEnabled=0&datestamp=Fri+Oct+03+2025+12%3A42%3A50+GMT%2B0530+(India+Standard+Time)&version=202508.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=d85a3537-f26c-4d13-8bfd-96e8e981b5e7&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&AwaitingReconsent=false&geolocation=IN%3BTN; "
                 "OptanonAlertBoxClosed=2025-10-03T07:12:50.753Z; fw_se={%22value%22:%22fws2.f7e8399d-c959-4ed7-8ef3-2209f8370c87.1.1759474894364%22%2C%22createTime%22:%222025-10-03T07:01:34.365Z%22}; "
                 "fw_uid={%22value%22:%222b313bcc-dc2e-4e49-9252-ece7df7840c5%22%2C%22createTime%22:%222025-10-03T07:01:34.413Z%22}; "
                 "fw_bid={%22value%22:%22oN1Py9%22%2C%22createTime%22:%222025-10-03T07:01:35.919Z%22}; fw_chid={%22value%22:%22yz0B4DK%22%2C%22createTime%22:%222025-10-03T07:01:36.455Z%22}; "
                 "newsletter-prompt-displayed=seen; _ga=GA1.1.1978214409.1759474900; _gcl_au=1.1.1176742030.1759474900; _tt_enable_cookie=1; _ttp=01K6ME0RJRMPEF81C74VVRTXM9_.tt.1; "
                 "__adroll_fpc=36f834a555e48a6f3d125b71ac050145-1759474902275; _scid=3fSDIiMHnkbv4ADKBFbnwvoJT6PYJUpp; _ScCbts=%5B%5D; _sctr=1%7C1759429800000; "
                 "affinity=\"31a27a91a7f607d7\"; __ar_v4=ZTZKC7PR5JGA3OQ7SYTCCW%3A20251002%3A3%7CNSXGY76ZPJH7TI3EVWWTSJ%3A20251002%3A3; ttcsid=1759474901600::7PhDY7XAbmTOu_pKLu46.1.1759475571992.0; "
                 "ttcsid_CMELBCJC77U4KPGKPGF0=1759474901599::xVbQ3vlEVTG5NDXKNKY3.1.1759475571992.0; _scid_r=53SDIiMHnkbv4ADKBFbnwvoJT6PYJUppz070Ag; "
                 "_ga_K257S23T0D=GS2.1.s1759474899$o1$g1$t1759475577$j33$l0$h845416392; _ga_MF5CFCH8KB=GS2.1.s1759474899$o1$g1$t1759475577$j33$l0$h163805091")

# Thread-safe counter and lock
progress_lock = threading.Lock()
progress_counter = {"completed": 0, "failed": 0}


def cookie_header_to_dict(cookie_str: str) -> dict:
    pairs = [c.strip() for c in cookie_str.split(';') if '=' in c]
    d = {}
    for p in pairs:
        k, v = p.split('=', 1)
        d[k.strip()] = v.strip()
    return d


def create_session():
    """Create a new session for each thread"""
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    cookies = cookie_header_to_dict(COOKIE_HEADER)
    for k, v in cookies.items():
        session.cookies.set(k, v)
    return session


def url_to_filename(url: str) -> str:
    """Convert URL to a safe filename"""
    # Remove protocol
    filename = url.replace("https://", "").replace("http://", "")
    # Replace special characters with underscores
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    # Limit length to 200 characters
    if len(filename) > 200:
        filename = filename[:200]
    return filename + ".txt"


def extract_urls_from_sitemap(sitemap_url, session, base_domain, result_dict, counts_dict):
    """Extract URLs from either sitemap.xml or sitemap-index.xml and save in dict"""
    urls = []
    try:
        resp = session.get(sitemap_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch {sitemap_url}: {e}")
        return urls

    try:
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"[ERROR] Failed to parse XML from {sitemap_url}: {e}")
        return urls

    try:
        if root.tag.endswith("sitemapindex"):
            result_dict[sitemap_url] = {}
            counts_dict[sitemap_url] = 0
            for loc in root.findall(".//{*}loc"):
                if loc is not None and loc.text:
                    child_sitemap = loc.text.strip()
                    try:
                        child_urls = extract_urls_from_sitemap(child_sitemap, session, base_domain, result_dict[sitemap_url], counts_dict)
                        urls.extend(child_urls)
                        counts_dict[sitemap_url] += len(child_urls)
                    except Exception as e:
                        print(f"[ERROR] Failed processing child sitemap {child_sitemap}: {e}")
        elif root.tag.endswith("urlset"):
            page_urls = []
            for loc in root.findall(".//{*}loc"):
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    if urlparse(url).netloc.lower() == base_domain:
                        page_urls.append(url)
            result_dict[sitemap_url] = page_urls
            counts_dict[sitemap_url] = len(page_urls)
            urls.extend(page_urls)
    except Exception as e:
        print(f"[ERROR] Unexpected error processing {sitemap_url}: {e}")

    return urls


def save_html_to_file(url: str, html_content: str, output_dir: str) -> str:
    """Save HTML content to a .txt file with URL at the top"""
    filename = url_to_filename(url)
    filepath = os.path.join(output_dir, filename)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            # Write URL first
            f.write(f"URL: {url}\n")
            f.write("="*80 + "\n\n")
            # Then write HTML content
            f.write(html_content)
        return filepath
    except Exception as e:
        print(f"[ERROR] Failed to save {filepath}: {e}")
        return None


def scrape_single_page(url: str, idx: int, total: int, output_dir: str) -> tuple:
    """Scrape a single page and save to .txt file (thread-safe)"""
    session = create_session()
    result = {
        "url": url,
        "status_code": None,
        "error": None,
        "content_length": 0,
        "file_path": None
    }
    
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        result["status_code"] = resp.status_code
        resp.raise_for_status()
        
        raw_html = resp.text
        result["content_length"] = len(raw_html)
        
        # Save to .txt file
        filepath = save_html_to_file(url, raw_html, output_dir)
        result["file_path"] = filepath
        
        # Update progress
        with progress_lock:
            progress_counter["completed"] += 1
            completed = progress_counter["completed"]
            failed = progress_counter["failed"]
        
        print(f"[{completed + failed}/{total}] ✓ {url[:60]}... ({result['content_length']:,}b) -> {os.path.basename(filepath)}")
            
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
        with progress_lock:
            progress_counter["failed"] += 1
        print(f"[{progress_counter['completed'] + progress_counter['failed']}/{total}] ❌ Timeout: {url[:60]}...")
    except requests.exceptions.HTTPError as e:
        result["error"] = f"HTTP Error: {e}"
        with progress_lock:
            progress_counter["failed"] += 1
        print(f"[{progress_counter['completed'] + progress_counter['failed']}/{total}] ❌ HTTP Error: {url[:60]}...")
    except Exception as e:
        result["error"] = f"Error: {str(e)}"
        with progress_lock:
            progress_counter["failed"] += 1
        print(f"[{progress_counter['completed'] + progress_counter['failed']}/{total}] ❌ Error: {url[:60]}...")
    finally:
        session.close()
    
    return url, result


def scrape_all_urls_parallel(urls: List[str], output_dir: str) -> Dict[str, Dict]:
    """Scrape HTML content for all URLs in parallel"""
    results_dict = {}
    total = len(urls)
    
    if MAX_PAGES:
        urls = urls[:MAX_PAGES]
        total = len(urls)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n[SCRAPING] Starting parallel scraping of {total} URLs...")
    print(f"[INFO] Max workers (threads): {MAX_WORKERS}")
    print(f"[INFO] Output directory: {output_dir}")
    print("="*80)
    
    # Reset progress counter
    progress_counter["completed"] = 0
    progress_counter["failed"] = 0
    
    start_time = time.time()
    
    # Use ThreadPoolExecutor for parallel scraping
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_url = {
            executor.submit(scrape_single_page, url, idx, total, output_dir): url 
            for idx, url in enumerate(urls, 1)
        }
        
        # Process completed tasks
        for future in as_completed(future_to_url):
            url, result = future.result()
            results_dict[url] = result
    
    elapsed_time = time.time() - start_time
    print("\n" + "="*80)
    print(f"[TIMING] Completed in {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    print(f"[TIMING] Average rate: {total/elapsed_time:.2f} pages/second")
    
    return results_dict


def save_to_excel(urls: List[str], results: Dict[str, Dict], filename: str = "scraped_urls.xlsx"):
    """Save URLs and results to Excel file"""
    data = []
    for url in urls:
        result = results.get(url, {})
        data.append({
            "URL": url,
            "Status Code": result.get("status_code", "N/A"),
            "Content Length (bytes)": result.get("content_length", 0),
            "File Path": result.get("file_path", "N/A"),
            "Error": result.get("error", "None")
        })
    
    df = pd.DataFrame(data)
    
    try:
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"[SAVED] Excel file: {filename}")
    except Exception as e:
        print(f"[ERROR] Failed to save Excel file: {e}")


if __name__ == "__main__":
    sitemap_url = url_sitemap_dict.get(URL_INPUT)
    if not sitemap_url:
        print("No sitemap mapping found for:", URL_INPUT)
    else:
        session = create_session()
        parsed = urlparse(sitemap_url)
        base_domain = parsed.netloc.lower()

        sitemap_data = {}
        counts_data = {}

        print("[STEP 1] Extracting URLs from sitemap...")
        all_urls = extract_urls_from_sitemap(sitemap_url, session, base_domain, sitemap_data, counts_data)
        session.close()

        print(f"[INFO] Found {len(all_urls)} URLs in sitemap")

        # Save URL list to text file
        try:
            with open("urls.txt", "w", encoding="utf-8") as f:
                for u in all_urls:
                    f.write(u + "\n")
            print(f"[SAVED] {len(all_urls)} URLs to urls.txt")
        except Exception as e:
            print(f"[ERROR] Failed saving urls.txt: {e}")

        # Save sitemap structure
        try:
            with open("sitemap.json", "w", encoding="utf-8") as f:
                json.dump({sitemap_url: sitemap_data}, f, indent=4)
            print("[SAVED] Full structure to sitemap.json")
        except Exception as e:
            print(f"[ERROR] Failed saving sitemap.json: {e}")

        try:
            with open("sitemap_counts.json", "w", encoding="utf-8") as f:
                json.dump(counts_data, f, indent=4)
            print("[SAVED] Per-sitemap counts to sitemap_counts.json")
        except Exception as e:
            print(f"[ERROR] Failed saving sitemap_counts.json: {e}")

        # Scrape all pages in parallel
        print("\n" + "="*80)
        print("[STEP 2] Scraping HTML content from all URLs (PARALLEL)...")
        print("="*80)
        
        results = scrape_all_urls_parallel(all_urls, OUTPUT_DIR)
        
        # Statistics
        successful = sum(1 for v in results.values() if v["error"] is None)
        failed = len(results) - successful
        total_size = sum(v.get("content_length", 0) for v in results.values())
        
        print("\n" + "="*80)
        print("[COMPLETE] Scraping finished!")
        print("="*80)
        print(f"Total URLs: {len(results)}")
        print(f"Successful: {successful} ({successful/len(results)*100:.1f}%)")
        print(f"Failed: {failed} ({failed/len(results)*100:.1f}%)")
        print(f"Total content size: {total_size:,} bytes ({total_size/1024/1024:.2f} MB)")
        print(f"HTML files saved in: {OUTPUT_DIR}/")
        
        # Save to Excel
        print("\n[STEP 3] Saving results to Excel...")
        save_to_excel(all_urls, results, "scraped_urls.xlsx")
        
        print("\n" + "="*80)
        print("[ALL DONE] Check the following files:")
        print(f"  - urls.txt (list of all URLs)")
        print(f"  - scraped_urls.xlsx (Excel with all URLs and status)")
        print(f"  - {OUTPUT_DIR}/ (folder with {successful} .txt files)")
        print("="*80)