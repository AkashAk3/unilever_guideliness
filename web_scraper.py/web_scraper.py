import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import json

# ----------- CONFIG / STATIC INPUT -----------
URL_INPUT = "https://www.tanyapepsodent.com/home.html"
URL_INPUT = "https://www.rexona.com/br/home.html"
URL_INPUT = "https://www.dove.com/us/en/home.html"

url_sitemap_dict = {
    "https://www.degreedeodorant.com/us/en/home.html": "https://www.degreedeodorant.com/us/en/sitemap.xml",
    "https://www.rexona.com/br/home.html": "https://www.rexona.com/br/sitemap-index.xml",
    "https://www.suredeodorant.co.uk/home.html": "https://www.suredeodorant.co.uk/sitemap.xml",
    "https://www.dove.com/us/en/home.html": "https://www.dove.com/us/en/sitemap-index.xml",
    "https://www.tanyapepsodent.com/home.html": "https://www.tanyapepsodent.com/sitemap-index.xml",
    "https://www.unilever.com/": "https://www.unilever.com/sitemap.xml"
}
# ----------------------------------------------

BROWSER_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "connection": "keep-alive",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
}


# COOKIE_HEADER = ("OptanonConsent=...; _ga=...; _scid=...")  # put full cookie string you pasted earlier
COOKIE_HEADER = ("OptanonConsent=isGpcEnabled=0&datestamp=Fri+Oct+03+2025+12%3A42%3A50+GMT%2B0530+(India+Standard+Time)&version=202508.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=d85a3537-f26c-4d13-8bfd-96e8e981b5e7&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1&AwaitingReconsent=false&geolocation=IN%3BTN; "
                 "OptanonAlertBoxClosed=2025-10-03T07:12:50.753Z; fw_se={%22value%22:%22fws2.f7e8399d-c959-4ed7-8ef3-2209f8370c87.1.1759474894364%22%2C%22createTime%22:%222025-10-03T07:01:34.365Z%22}; "
                 "fw_uid={%22value%22:%222b313bcc-dc2e-4e49-9252-ece7df7840c5%22%2C%22createTime%22:%222025-10-03T07:01:34.413Z%22}; "
                 "fw_bid={%22value%22:%22oN1Py9%22%2C%22createTime%22:%222025-10-03T07:01:35.919Z%22}; fw_chid={%22value%22:%22yz0B4DK%22%2C%22createTime%22:%222025-10-03T07:01:36.455Z%22}; "
                 "newsletter-prompt-displayed=seen; _ga=GA1.1.1978214409.1759474900; _gcl_au=1.1.1176742030.1759474900; _tt_enable_cookie=1; _ttp=01K6ME0RJRMPEF81C74VVRTXM9_.tt.1; "
                 "__adroll_fpc=36f834a555e48a6f3d125b71ac050145-1759474902275; _scid=3fSDIiMHnkbv4ADKBFbnwvoJT6PYJUpp; _ScCbts=%5B%5D; _sctr=1%7C1759429800000; "
                 "affinity=\"31a27a91a7f607d7\"; __ar_v4=ZTZKC7PR5JGA3OQ7SYTCCW%3A20251002%3A3%7CNSXGY76ZPJH7TI3EVWWTSJ%3A20251002%3A3; ttcsid=1759474901600::7PhDY7XAbmTOu_pKLu46.1.1759475571992.0; "
                 "ttcsid_CMELBCJC77U4KPGKPGF0=1759474901599::xVbQ3vlEVTG5NDXKNKY3.1.1759475571992.0; _scid_r=53SDIiMHnkbv4ADKBFbnwvoJT6PYJUppz070Ag; "
                 "_ga_K257S23T0D=GS2.1.s1759474899$o1$g1$t1759475577$j33$l0$h845416392; _ga_MF5CFCH8KB=GS2.1.s1759474899$o1$g1$t1759475577$j33$l0$h163805091")

def cookie_header_to_dict(cookie_str: str) -> dict:
    pairs = [c.strip() for c in cookie_str.split(';') if '=' in c]
    d = {}
    for p in pairs:
        k, v = p.split('=', 1)
        d[k.strip()] = v.strip()
    return d

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

if __name__ == "__main__":
    sitemap_url = url_sitemap_dict.get(URL_INPUT)
    if not sitemap_url:
        print("No sitemap mapping found for:", URL_INPUT)
    else:
        session = requests.Session()
        session.headers.update(BROWSER_HEADERS)
        cookies = cookie_header_to_dict(COOKIE_HEADER)
        for k, v in cookies.items():
            session.cookies.set(k, v)

        parsed = urlparse(sitemap_url)
        base_domain = parsed.netloc.lower()

        sitemap_data = {}
        counts_data = {}

        all_urls = extract_urls_from_sitemap(sitemap_url, session, base_domain, sitemap_data, counts_data)

        # Save TXT
        try:
            with open("urls.txt", "w", encoding="utf-8") as f:
                for u in all_urls:
                    f.write(u + "\n")
            print(f"Saved {len(all_urls)} URLs to urls.txt")
        except Exception as e:
            print(f"[ERROR] Failed saving urls.txt: {e}")

        # Save JSON with full structure
        try:
            with open("sitemap.json", "w", encoding="utf-8") as f:
                json.dump({sitemap_url: sitemap_data}, f, indent=4)
            print("Full structure saved to sitemap.json")
        except Exception as e:
            print(f"[ERROR] Failed saving sitemap.json: {e}")

        # Save counts separately
        try:
            with open("sitemap_counts.json", "w", encoding="utf-8") as f:
                json.dump(counts_data, f, indent=4)
            print("Per-sitemap counts saved to sitemap_counts.json")
        except Exception as e:
            print(f"[ERROR] Failed saving sitemap_counts.json: {e}")