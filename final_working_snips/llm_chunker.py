import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json

import os 
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BROWSER_HEADERS = os.getenv("BROWSER_HEADERS")
COOKIE_HEADER = os.getenv("COOKIE_HEADER")


REQUEST_TIMEOUT = 30  


client = OpenAI(api_key=OPENAI_API_KEY)

def generate_semantic_chunks(raw_text: str, model="gpt-4o-mini", max_chunk_tokens=500):
    """
    Send raw text to OpenAI and get structured JSON chunks.
    """
    prompt = f"""
        You are a content structuring assistant. You are given raw text content from a webpage.
        Split this content into coherent chunks (sections) such that:
        - Each chunk is semantically complete (doesn't cut off mid-thought).
        - Each chunk stays under roughly {max_chunk_tokens} tokens.

        Rules:
        - Give the exact word content, do not add or remove any words while chunking.
        - Do not neglect any important sections.
        - Every content must belong to some chunk.
        Return the result as valid JSON list of objects with:
        Return the result as valid JSON list of strings, where each string is a complete chunk:
    [
        "Full text content of first section...",
        "Full text content of second section...",
        ...
    ]

        Here is the raw text content:

        {raw_text}
"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You split text into logical, readable chunks for structured storage."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}  # Ensures valid JSON output
    )

    json_output = response.choices[0].message.content

    try:
        chunks = json.loads(json_output)
        return chunks
    except json.JSONDecodeError:
        print("Warning: LLM output was not valid JSON. Raw output saved to debug.")
        return {"raw_output": json_output}


def extract_raw_text(soup):
    """
    Extract clean raw text from BeautifulSoup object.
    Preserves paragraph structure and removes extra whitespace.
    Only extracts visible/rendered content, not hidden data attributes.
    """
    # Remove elements that have data-quotes attribute (they contain all possible quotes, not just visible ones)
    for element in soup.find_all(attrs={'data-quotes': True}):
        element.decompose()
    
    # Get regular text content (only what's visible in the DOM)
    raw_text = soup.get_text(separator='\n', strip=True)
    
    # Remove excessive newlines
    lines = raw_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:  # Only keep non-empty lines
            cleaned_lines.append(line)
    
    # Join with single newlines
    clean_text = '\n'.join(cleaned_lines)
    
    return clean_text
    

def extract_content_chunks(html):
    soup = BeautifulSoup(html, 'html.parser')

    # --- Clean unwanted tags ---
    unwanted_tags = ['header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript', 'iframe']
    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()

    # --- Extract raw text from cleaned HTML ---
    print("🧹 Extracting raw text from cleaned HTML...")
    raw_text = extract_raw_text(soup)
    
    print("Raw Text (first 500 chars):\n", raw_text[:500], "\n...")
    
    # Save raw text for inspection
    with open("raw_text_extracted.txt", "w", encoding="utf-8") as f:
        f.write(raw_text)
    print("✅ Saved raw text to raw_text_extracted.txt")

    # --- Generate LLM chunks from raw text ---
    print("🧠 Sending raw text to LLM for structured chunking...")
    chunks = generate_semantic_chunks(raw_text)

    print("chunks:\n", chunks)

    # --- Save JSON output ---
    with open("llm_chunks_dove.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print("✅ Saved structured LLM chunks to llm_chunks_dove.json")

    # --- Save plain text version for easy reading ---
    txt_filename = "llm_chunks_dove.txt"
    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write("=" * 100 + "\n")
        f.write("LLM-GENERATED SEMANTIC CHUNKS\n")
        f.write("=" * 100 + "\n\n")

        if isinstance(chunks, dict) and "sections" in chunks:
            for i, chunk in enumerate(chunks["sections"], 1):
                f.write(f"CHUNK {i}: {chunk.get('title', 'Untitled Section')}\n")
                f.write("-" * 100 + "\n")
                f.write(f"{chunk.get('content', '').strip()}\n\n")
                f.write("=" * 100 + "\n\n")

        elif isinstance(chunks, list):
            for i, chunk in enumerate(chunks, 1):
                f.write(f"CHUNK {i}: {chunk.get('title', 'Untitled Section')}\n")
                f.write("-" * 100 + "\n")
                f.write(f"{chunk.get('content', '').strip()}\n\n")
                f.write("=" * 100 + "\n\n")

        elif isinstance(chunks, dict) and "raw_output" in chunks:
            f.write("⚠️ RAW OUTPUT (Invalid JSON from LLM):\n")
            f.write(chunks["raw_output"])

    print(f"📝 Saved readable chunks to {txt_filename}\n")
    return chunks


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
    # url = "https://www.degreedeodorant.com/us/en/sweat-zone/why-do-i-sweat-in-my-sleep.html"
    url = "https://www.dove.com/us/en/stories/tips-and-how-to/hair-care-tips-advice/how-to-get-shiny-hair.html"
    # url = "https://www.dove.com/us/en/campaigns/purpose/sourcing-and-sustainability/circular-care.html"
    url  = "https://www.dove.com/us/en/baby/more-from-baby-dove/baby-care-tips/6-tips-for-bathing-a-baby.html"
    url = "https://www.dove.com/us/en/men-care/about/5-ways-men-can-be-positive-role-models.html"
    url = "https://www.dove.com/us/en/dove-self-esteem-project/help-for-parents.html"
    url = "https://www.dove.com/us/en/campaigns/purpose/keep-beauty-real.html"
    url = "https://www.dove.com/us/en/p/niacinamide-eventone-cream-serum.html/00011111051454"
    url = "https://www.degreedeodorant.com/us/en/p/ultraclear-blackwhite-driftwood-antiperspirant-deodorant-stick.html/00079400448699"
    
    # Method 1: Get structured chunks with headings
    html = scrape_single_page(url)
    print("=== Structured Content Chunks ===\n")
    chunks = extract_content_chunks(html)
    print(f"Total chunks extracted: {len(chunks)}\n")