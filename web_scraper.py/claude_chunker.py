"""
HTML Content Chunker for Web Page Auditing
Extracts main content (excluding header/footer) and creates semantic chunks
WITHOUT DUPLICATES
"""

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

from bs4 import BeautifulSoup, NavigableString, Comment
import re
import json
from typing import List, Dict, Set

class HTMLContentChunker:
    def __init__(self, html_content: str):
        """
        Initialize the chunker with HTML content
        
        Args:
            html_content: Raw HTML content as string
        """
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.chunks = []
        self.seen_texts = set()  # Track seen text to avoid duplicates
        
        # Tags to remove (header, footer, navigation, scripts, etc.)
        self.exclude_tags = [
            'header', 'footer', 'nav', 'script', 'style', 'noscript',
            'iframe', 'meta', 'link', 'aside'
        ]
        
        # Common header/footer class/id patterns
        self.exclude_patterns = [
            r'header', r'footer', r'nav', r'menu', r'sidebar',
            r'cookie', r'banner', r'advertisement', r'ad-', r'ads',
            r'breadcrumb', r'social', r'share', r'newsletter',
            r'modal', r'popup', r'overlay', r'dialog'
        ]
    
    def _should_exclude_element(self, element) -> bool:
        """
        Check if element should be excluded based on tag, class, or id
        """
        # Skip if element doesn't have a name (text nodes, etc.)
        if not hasattr(element, 'name') or element.name is None:
            return False
        
        # Check tag name
        if element.name in self.exclude_tags:
            return True
        
        # Check class and id attributes safely
        attrs = []
        try:
            if element.get('class'):
                attrs.extend(element.get('class'))
            if element.get('id'):
                attrs.append(element.get('id'))
            
            # Check against patterns
            attrs_str = ' '.join(str(a) for a in attrs).lower()
            for pattern in self.exclude_patterns:
                if re.search(pattern, attrs_str):
                    return True
            
            # Check for role attribute
            role = element.get('role', '').lower()
            if role in ['navigation', 'banner', 'contentinfo', 'complementary', 'dialog']:
                return True
        except (AttributeError, TypeError):
            pass
        
        return False
    
    def _remove_unwanted_elements(self):
        """
        Remove header, footer, navigation, and other unwanted elements
        """
        # Remove comments
        for comment in self.soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Remove script, style tags
        for tag in self.exclude_tags:
            for element in self.soup.find_all(tag):
                element.decompose()
        
        # Remove elements with exclude patterns in class/id
        for element in self.soup.find_all(True):
            try:
                if self._should_exclude_element(element):
                    element.decompose()
            except (AttributeError, TypeError):
                continue
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for duplicate detection"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()
    
    def _is_duplicate(self, text: str) -> bool:
        """Check if text is a duplicate"""
        normalized = self._normalize_text(text)
        if not normalized or len(normalized) < 10:
            return True
        
        # Check if exact match exists
        if normalized in self.seen_texts:
            return True
        
        # Check if this text is contained in or contains existing text
        for seen in self.seen_texts:
            # If new text is substring of existing, it's duplicate
            if normalized in seen:
                return True
            # If existing is substring of new, keep new (it's more complete)
            if seen in normalized:
                self.seen_texts.discard(seen)
                break
        
        self.seen_texts.add(normalized)
        return False
    
    def _find_main_content(self):
        """
        Find the main content area of the page
        """
        # Try to find main content tags first
        main_content = None
        
        # Priority 1: <main> tag
        main_content = self.soup.find('main')
        
        # Priority 2: role="main"
        if not main_content:
            main_content = self.soup.find(attrs={'role': 'main'})
        
        # Priority 3: article tag
        if not main_content:
            articles = self.soup.find_all('article')
            if articles:
                main_content = articles[0]
        
        # Priority 4: Look for content-rich divs
        if not main_content:
            content_patterns = [
                r'content', r'main', r'body', r'article', r'post',
                r'page', r'container', r'wrapper', r'product'
            ]
            
            for div in self.soup.find_all(['div', 'section']):
                attrs = []
                if div.get('class'):
                    attrs.extend(div.get('class'))
                if div.get('id'):
                    attrs.append(div.get('id'))
                
                attrs_str = ' '.join(str(a) for a in attrs).lower()
                for pattern in content_patterns:
                    if re.search(pattern, attrs_str):
                        text = div.get_text(strip=True)
                        if len(text) > 200:
                            main_content = div
                            break
                
                if main_content:
                    break
        
        # Fallback: use body
        if not main_content:
            main_content = self.soup.find('body')
        
        return main_content if main_content else self.soup
    
    def _create_semantic_chunks(self, content_element) -> List[Dict]:
        """
        Create chunks based on semantic HTML structure
        Uses bottom-up approach to avoid duplicates
        """
        chunks = []
        chunk_id = 0
        processed_elements = set()  # Track processed elements
        
        # Find all leaf elements (paragraphs, list items, etc.) first
        # These are the actual content containers
        leaf_tags = ['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                     'blockquote', 'figcaption', 'dd', 'dt']
        
        leaf_elements = content_element.find_all(leaf_tags)
        
        for elem in leaf_elements:
            # Skip if already processed as part of parent
            if id(elem) in processed_elements:
                continue
            
            # Get text
            text = elem.get_text(strip=True)
            word_count = len(text.split())
            
            # Skip if too short or duplicate
            if word_count < 5 or self._is_duplicate(text):
                continue
            
            # Find parent heading
            parent_heading = None
            parent = elem.find_parent(['section', 'article', 'div'])
            if parent:
                heading = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if heading:
                    parent_heading = heading.get_text(strip=True)
            
            # Determine chunk type
            if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                chunk_type = 'heading'
            else:
                chunk_type = elem.name
            
            # Create chunk
            chunk = {
                'id': chunk_id,
                'type': chunk_type,
                'heading': parent_heading,
                'text': text,
                'word_count': word_count,
                'html_classes': elem.get('class', []),
                'html_id': elem.get('id', ''),
                'html_tag': elem.name
            }
            chunks.append(chunk)
            chunk_id += 1
            processed_elements.add(id(elem))
        
        return chunks
    
    def _merge_small_chunks(self, chunks: List[Dict], min_words: int = 20) -> List[Dict]:
        """
        Merge chunks that are too small
        """
        if not chunks:
            return []
        
        merged = []
        current = chunks[0].copy()
        
        for i in range(1, len(chunks)):
            if current['word_count'] < min_words:
                # Merge with next chunk
                current['text'] += '\n\n' + chunks[i]['text']
                current['word_count'] += chunks[i]['word_count']
                current['type'] = 'merged'
                if chunks[i]['heading'] and not current['heading']:
                    current['heading'] = chunks[i]['heading']
            else:
                merged.append(current)
                current = chunks[i].copy()
        
        # Add last chunk
        merged.append(current)
        
        # Reassign IDs
        for idx, chunk in enumerate(merged):
            chunk['id'] = idx
        
        return merged
    
    def extract_and_chunk(self, min_chunk_words: int = 5, 
                          merge_small: bool = True) -> List[Dict]:
        """
        Main method to extract content and create chunks
        
        Args:
            min_chunk_words: Minimum words per chunk (default: 5)
            merge_small: Whether to merge small chunks (default: True)
            
        Returns:
            List of chunk dictionaries
        """
        # Step 1: Remove unwanted elements
        self._remove_unwanted_elements()
        
        # Step 2: Find main content area
        main_content = self._find_main_content()
        
        # Step 3: Create semantic chunks (no duplicates)
        chunks = self._create_semantic_chunks(main_content)
        
        # Step 4: Optionally merge very small chunks
        if merge_small and chunks:
            chunks = self._merge_small_chunks(chunks, min_words=20)
        
        self.chunks = chunks
        return chunks
    
    def save_chunks(self, output_file: str, format: str = 'json'):
        """
        Save chunks to file
        
        Args:
            output_file: Output file path
            format: 'json' or 'txt'
        """
        if format == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.chunks, f, indent=2, ensure_ascii=False)
        
        elif format == 'txt':
            with open(output_file, 'w', encoding='utf-8') as f:
                for chunk in self.chunks:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"CHUNK {chunk['id']} | Type: {chunk['type']} | Words: {chunk['word_count']}\n")
                    if chunk['heading']:
                        f.write(f"Heading: {chunk['heading']}\n")
                    f.write(f"{'='*80}\n")
                    f.write(chunk['text'])
                    f.write(f"\n\n")
    
    def get_summary(self) -> Dict:
        """
        Get summary statistics of chunks
        """
        if not self.chunks:
            return {}
        
        total_words = sum(chunk['word_count'] for chunk in self.chunks)
        
        return {
            'total_chunks': len(self.chunks),
            'total_words': total_words,
            'avg_words_per_chunk': total_words / len(self.chunks) if self.chunks else 0,
            'chunks_with_headings': sum(1 for c in self.chunks if c['heading']),
            'chunk_types': list(set(c['type'] for c in self.chunks))
        }



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
        
# Main execution
if __name__ == "__main__":
    # Example usage
    import requests
    
    # 1. Read HTML from file
    # input_file = 'webpage.txt'  # Your HTML file
    
    # with open(input_file, 'r', encoding='utf-8') as f:
    #     html_content = f.read()
    url = "https://www.dove.com/us/en/p/calming-moisture-night-time-lotion.html/00011111012028"
    html_content=scrape_single_page(url)
    # 2. Create chunker and extract chunks
    chunker = HTMLContentChunker(html_content)
    chunks = chunker.extract_and_chunk(min_chunk_words=5, merge_small=True)
    
    # 3. Display summary
    summary = chunker.get_summary()
    print("\n" + "="*80)
    print("CHUNKING SUMMARY")
    print("="*80)
    print(f"Total Chunks: {summary['total_chunks']}")
    print(f"Total Words: {summary['total_words']}")
    print(f"Average Words per Chunk: {summary['avg_words_per_chunk']:.1f}")
    print(f"Chunks with Headings: {summary['chunks_with_headings']}")
    print(f"Chunk Types: {', '.join(summary['chunk_types'])}")
    print("="*80 + "\n")
    
    # 4. Preview first 10 chunks
    print("PREVIEW OF FIRST 10 CHUNKS:")
    print("-"*80)
    for chunk in chunks[:10]:
        print(f"\nChunk {chunk['id']} [{chunk['type']}] - {chunk['word_count']} words")
        if chunk['heading']:
            print(f"Heading: {chunk['heading']}")
        print(f"Text: {chunk['text'][:150]}..." if len(chunk['text']) > 150 else chunk['text'])
        print("-"*80)
    
    # 5. Save chunks
    chunker.save_chunks('chunks_output.json', format='json')
    chunker.save_chunks('chunks_output.txt', format='txt')
    
    print("\n✓ Chunks saved to 'chunks_output.json' and 'chunks_output.txt'")
    print(f"✓ Total {len(chunks)} chunks created (no duplicates)")