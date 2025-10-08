import requests
from bs4 import BeautifulSoup

def extract_content_chunks(html):
    """
    Extract main content chunks from HTML, excluding headers, footers, and navigation.
    Returns a list of dictionaries with headings and their associated content.
    """
    # Fetch the HTML content
    # headers = {
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    # }
    # response = requests.get(url, headers=headers)
    # response.raise_for_status()
    
    # # Parse HTML
    soup = BeautifulSoup(html, 'html.parser')
    print("soup", soup)
    
    # Remove unwanted elements
    unwanted_tags = ['header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript', 'iframe']
    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()
    
    # Remove elements by common class/id patterns
    unwanted_patterns = ['header', 'footer', 'nav', 'sidebar', 'menu', 'advertisement', 'ad-']
    for pattern in unwanted_patterns:
        for element in soup.find_all(class_=lambda x: x and pattern in x.lower()):
            element.decompose()
        for element in soup.find_all(id=lambda x: x and pattern in x.lower()):
            element.decompose()
    
    # Find main content area (try common patterns)
    main_content = (
        soup.find('main') or 
        soup.find('article') or 
        soup.find('div', class_=lambda x: x and ('content' in x.lower() or 'main' in x.lower())) or
        soup.find('body')
    )
    
    if not main_content:
        main_content = soup
    
    # Extract content chunks
    chunks = []
    
    # Find all heading tags
    headings = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    
    for heading in headings:
        chunk = {
            'heading': heading.get_text(strip=True),
            'level': heading.name,
            'content': []
        }
        
        # Get all siblings until next heading
        for sibling in heading.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                break
            
            text = sibling.get_text(strip=True)
            if text:
                chunk['content'].append(text)
        
        if chunk['content']:
            chunks.append(chunk)
    
    # Extract standalone paragraphs (content without headings)
    # all_paragraphs = main_content.find_all(['p', 'div', 'section'])
    # standalone_content = []
    
    # for para in all_paragraphs:
    #     # Skip if parent is already captured under a heading
    #     if not any(heading in para.parents for heading in headings):
    #         text = para.get_text(strip=True)
    #         if text and len(text) > 20:  # Filter out very short text
    #             standalone_content.append(text)
    
    # if standalone_content:
    #     chunks.append({
    #         'heading': None,
    #         'level': None,
    #         'content': standalone_content
    #     })
    
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

# Example usage
if __name__ == "__main__":
    # url = "https://example.com"  # Replace with your URL
    html = open("sample_html.html", "r", encoding="utf-8").read()  # Load HTML from file for testing
    
    # Method 1: Get structured chunks with headings
    print("=== Structured Content Chunks ===\n")
    chunks = extract_content_chunks(html)
    save_chunks_to_file(chunks, "content_chunks.txt")
    print(f"Total chunks extracted: {len(chunks)}\n")
    