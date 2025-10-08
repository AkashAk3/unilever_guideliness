import requests
from bs4 import BeautifulSoup

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


def extract_content_chunks(html):
    soup = BeautifulSoup(html, 'html.parser')
    unwanted_tags = ['header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript', 'iframe']
    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()

    chunks = []

    # --- NEW PRODUCT TITLE EXTRACTION BLOCK ---
    # Try to find a main product title (h1 or central large heading)
    product_title = soup.find('h1')
    if not product_title:
        product_title = soup.find(class_=lambda x: x and 'product-title' in x.lower())
    if product_title:
        # Gather related contents: immediate siblings, next elements, etc.
        content = []
        # Gather adjacent paragraphs, spans, divs or list items directly after the title
        for sibling in product_title.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            if sibling.name in ['p', 'span', 'div', 'li', 'ul', 'ol']:
                text = sibling.get_text(strip=True)
                if text and len(text) > 0:
                    content.append(text)
        # If content found, add as distinct product-title chunk
        if content:
            chunks.append({
                'heading': product_title.get_text(strip=True),
                'level': product_title.name if hasattr(product_title, 'name') else 'product-title',
                'content': content
            })

    # --- EXISTING MAIN CONTENT EXTRACTION ---
    main_content = (
        soup.find('main') or
        soup.find('article') or
        soup.find('div', class_=lambda x: x and 'content' in x.lower()) or
        soup.find('body')
    )

    headings = main_content.find_all(['h2', 'h3', 'h4', 'h5', 'h6']) if main_content else []
    for heading in headings:
        chunk = {
            'heading': heading.get_text(strip=True),
            'level': heading.name,
            'content': []
        }
        for sibling in heading.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            if sibling.name in ['p', 'strong', 'li', 'div']:
                text = sibling.get_text(strip=True)
                if text:
                    chunk['content'].append(text)
            elif isinstance(sibling, str):
                text = sibling.strip()
                if text:
                    chunk['content'].append(text)
        if chunk['content']:
            chunks.append(chunk)
    return chunks

def extract_clean_text(html):
    """
    Extract all text content as simple chunks without structure.
    """
    # headers = {
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    # }
    # response = requests.get(url, headers=headers)
    # response.raise_for_status()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove unwanted elements
    for tag in ['header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript', 'iframe']:
        for element in soup.find_all(tag):
            element.decompose()
    
    # Get main content
    main_content = (
        soup.find('main') or 
        soup.find('article') or 
        soup.find('div', class_=lambda x: x and 'content' in x.lower()) or
        soup.find('body')
    )
    
    # Extract all text blocks
    chunks = []
    for element in main_content.find_all(['p', 'div', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text = element.get_text(strip=True)
        if text and len(text) > 15:
            chunks.append(text)
    
    return chunks

def save_chunks_to_file(chunks, filename="content_chunks.txt"):
    """
    Save structured chunks to a text file.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("EXTRACTED CONTENT CHUNKS\n")
        f.write("=" * 80 + "\n\n")
        
        for i, chunk in enumerate(chunks, 1):
            if chunk['heading']:
                f.write(f"CHUNK {i}: {chunk['heading']} ({chunk['level']})\n")
                f.write("-" * 80 + "\n")
                for content in chunk['content']:
                    f.write(f"{content}\n\n")
            else:
                f.write(f"CHUNK {i}: Standalone Content\n")
                f.write("-" * 80 + "\n")
                for content in chunk['content']:
                    f.write(f"{content}\n\n")
            f.write("\n" + "=" * 80 + "\n\n")
    
    print(f"✓ Saved {len(chunks)} chunks to {filename}")


def save_clean_chunks_to_file(chunks, filename="clean_chunks.txt"):
    """
    Save clean text chunks to a text file.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CLEAN TEXT CHUNKS\n")
        f.write("=" * 80 + "\n\n")
        
        for i, chunk in enumerate(chunks, 1):
            f.write(f"CHUNK {i}:\n")
            f.write("-" * 80 + "\n")
            f.write(f"{chunk}\n\n")
            f.write("=" * 80 + "\n\n")
    
    print(f"✓ Saved {len(chunks)} chunks to {filename}")


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
MAX_PAGES = 10  # Set to a number to limit pages, None for all
SAVE_BATCH_SIZE = 100  # Save to disk every N pages
MAX_WORKERS = 10  # Number of parallel threads
REQUEST_TIMEOUT = 30  
def scrape_single_page(url: str):
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
        return raw_html
    except requests.exceptions.Timeout:
        print("time out exception") 
        
# Example usage
if __name__ == "__main__":
    url = "https://www.degreedeodorant.com/us/en/sweat-zone/your-lunchtime-workout-6-ways-to-move-more.html"  
    url = "https://www.dove.com/us/en/campaigns/purpose/sourcing-and-sustainability/circular-care.html"# Replace with your URL
    # html = open("sample_html.html", "r", encoding="utf-8").read()  # Load HTML from file for testing
    
    # Method 1: Get structured chunks with headings
    html = scrape_single_page(url)
    print("=== Structured Content Chunks ===\n")
    chunks = extract_content_chunks(html)
    save_chunks_to_file(chunks, "content_chunks.txt")
    print(f"Total chunks extracted: {len(chunks)}\n")
    