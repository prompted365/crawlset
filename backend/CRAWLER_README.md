# Advanced Web Crawler & Content Parsers

Comprehensive web intelligence pipeline with advanced crawling, parsing, and extraction capabilities.

## Overview

This implementation provides a production-ready web intelligence system with:

- **Advanced Browser Control** - Playwright-based crawling with anti-bot detection
- **Intelligent Rate Limiting** - Per-domain rate limiting with exponential backoff
- **Proxy Management** - Rotating proxy pool with health checking
- **Content Parsing** - Multiple specialized parsers for different content types
- **LLM-Powered Extraction** - Pydantic schemas and natural language extraction
- **Metadata Extraction** - Open Graph, Schema.org, Twitter Cards, and more

## Architecture

```
src/
├── crawler/          # Web crawling infrastructure
│   ├── browser.py           # Playwright wrapper with anti-bot detection
│   ├── proxy_pool.py        # Rotating proxy manager
│   └── rate_limiter.py      # Per-domain rate limiting
├── parser/           # Content parsing
│   ├── trafilatura_parser.py    # Main content extraction
│   ├── metadata_extractor.py    # Metadata extraction
│   ├── citation_tracker.py      # Citation tracking
│   └── podcast_parser.py        # Podcast RSS/episode parsing
└── extractors/       # LLM-powered extraction
    ├── llm_router.py            # Requesty.ai integration
    ├── schema_extractor.py      # Pydantic model-based extraction
    └── prompt_extractor.py      # Natural language extraction
```

## Module Documentation

### 1. Crawler Module (`src/crawler/`)

#### `browser.py` - Advanced Playwright Browser

**Features:**
- Smart wait strategies (network idle, DOM mutations, custom selectors)
- Anti-bot detection bypass (removes webdriver flags, mocks navigator properties)
- Cookie and session management with persistence
- Screenshot capture (PNG/JPEG, full page)
- JavaScript execution with result extraction
- Console and network logging
- Browser pooling for resource efficiency

**Usage:**
```python
from crawler import PlaywrightBrowser, BrowserConfig, WaitStrategy

# Configure browser
config = BrowserConfig(
    headless=True,
    user_agent="Mozilla/5.0 ...",
    proxy={"server": "http://proxy:8080"},
)

# Advanced fetch with custom wait strategy
async with PlaywrightBrowser(config=config) as browser:
    result = await browser.fetch(
        url="https://example.com",
        wait_strategy=WaitStrategy(
            wait_until="networkidle",
            additional_wait_ms=1000,
            wait_for_selector=".content-loaded"
        ),
        take_screenshot=True,
    )

    print(f"Status: {result.status}")
    print(f"Load time: {result.load_time_ms}ms")
    print(f"Console logs: {result.console_logs}")
```

#### `proxy_pool.py` - Rotating Proxy Manager

**Features:**
- Automatic health checking with configurable intervals
- Multiple rotation strategies (round-robin, least-used, fastest, priority)
- Per-proxy rate limiting and concurrent request limits
- Health metrics and statistics tracking
- Automatic failover and retry logic

**Usage:**
```python
from crawler import ProxyPool, ProxyConfig

# Initialize proxy pool
proxies = [
    ProxyConfig(url="http://proxy1:8080", priority=10),
    ProxyConfig(url="http://proxy2:8080", priority=5),
]

pool = ProxyPool(
    proxies=proxies,
    rotation_strategy="priority",
    health_check_interval=300.0
)

await pool.start()

# Use with automatic rotation
async def fetch_with_proxy(proxy, url):
    # Your fetch logic here
    pass

result = await pool.execute_with_proxy(
    fetch_with_proxy,
    url="https://example.com",
    retry_on_failure=True,
    max_retries=3
)
```

#### `rate_limiter.py` - Per-Domain Rate Limiting

**Features:**
- Token bucket algorithm for burst handling
- Exponential backoff on errors (configurable base and max)
- Respect for Retry-After headers
- Domain-based request queuing
- Auto-adjustment based on success/failure rates
- Concurrent request limits per domain

**Usage:**
```python
from crawler import RateLimiter, RateLimitConfig

# Initialize limiter
limiter = RateLimiter(
    default_config=RateLimitConfig(
        requests_per_second=2.0,
        max_concurrent=5,
        burst_size=10
    ),
    auto_adjust=True
)

# Use with context manager
async def fetch_url(url):
    domain = await limiter.acquire(url)
    try:
        # Make request
        result = await make_request(url)
        limiter.record_success(domain)
        return result
    except Exception as e:
        limiter.record_failure(domain, is_rate_limit=True)
        raise
    finally:
        limiter.release(domain)

# Or use convenience method
result = await limiter.execute(
    url="https://example.com",
    func=make_request,
    record_result=True
)
```

### 2. Parser Module (`src/parser/`)

#### `trafilatura_parser.py` - Main Content Extraction

**Features:**
- Main content extraction with trafilatura
- Link extraction (internal/external classification)
- Image extraction with captions
- Table extraction with headers
- Heading hierarchy extraction (h1-h6)
- Language detection
- Reading time estimation
- Markdown conversion

**Usage:**
```python
from parser import TrafilaturaParser, parse_html

# Parse HTML content
result = parse_html(url="https://example.com", html=html_content)

print(f"Title: {result['title']}")
print(f"Author: {result['author']}")
print(f"Word count: {result['word_count']}")
print(f"Reading time: {result['reading_time_minutes']} min")
print(f"Links found: {len(result['links'])}")
print(f"Images found: {len(result['images'])}")

# Advanced parser with custom settings
parser = TrafilaturaParser(
    include_comments=False,
    include_tables=True,
    favor_precision=True,
    target_language="en"
)

parsed = parser.parse(url, html)
print(f"Markdown:\n{parsed.markdown}")
```

#### `metadata_extractor.py` - Comprehensive Metadata

**Features:**
- Open Graph protocol (og:*) tags
- Twitter Card metadata
- Schema.org JSON-LD structured data
- Dublin Core metadata
- Standard HTML meta tags
- RSS/Atom feed discovery
- Published/modified dates
- SEO metadata (robots, viewport, etc.)

**Usage:**
```python
from parser import extract_metadata

metadata = extract_metadata(html, url="https://example.com")

# Open Graph
print(f"OG Title: {metadata.open_graph.title}")
print(f"OG Image: {metadata.open_graph.image}")
print(f"OG Type: {metadata.open_graph.type}")

# Twitter Card
print(f"Twitter Card: {metadata.twitter_card.card}")
print(f"Twitter Creator: {metadata.twitter_card.creator}")

# Schema.org
for schema in metadata.schema_org:
    print(f"Schema Type: {schema.type}")
    print(f"Schema Data: {schema.data}")

# Feeds
for feed in metadata.rss_feeds:
    print(f"RSS Feed: {feed['url']}")
```

#### `citation_tracker.py` - Citation Tracking

**Features:**
- Extract blockquotes as citations
- Track figures with captions
- Citation-style link detection
- Inline citation patterns ([1], (Author 2020))
- XPath and CSS selector generation
- Context extraction (before/after text)
- Custom selector-based extraction

**Usage:**
```python
from parser import CitationTracker, track_citations

# Track all citations
collection = track_citations(html, url="https://example.com")

print(f"Total citations: {collection.total_count}")
print(f"By type: {collection.by_type}")

# Get specific types
blockquotes = collection.get_by_type("blockquote")
for cite in blockquotes:
    print(f"Quote: {cite.text}")
    print(f"Source: {cite.source_url}")
    print(f"XPath: {cite.xpath}")

# Extract with custom selector
tracker = CitationTracker()
citations = tracker.extract_with_selector(
    html,
    selector="blockquote.citation",
    selector_type="css"
)
```

#### `podcast_parser.py` - Podcast Content

**Features:**
- RSS feed parsing with iTunes extensions
- Episode metadata extraction
- Show notes extraction from HTML
- Transcript extraction
- Duration parsing (HH:MM:SS)
- Chapter markers
- Host/guest identification

**Usage:**
```python
from parser import parse_podcast_feed, parse_podcast_episode

# Parse RSS feed
show = parse_podcast_feed(rss_xml, feed_url="https://podcast.com/feed")

print(f"Show: {show.title}")
print(f"Episodes: {len(show.episodes)}")

for episode in show.episodes:
    print(f"\nEpisode: {episode.title}")
    print(f"Duration: {episode.duration}s")
    print(f"Audio: {episode.audio_url}")
    print(f"Published: {episode.published_date}")

# Parse episode page
episode = parse_podcast_episode(html, url="https://podcast.com/ep1")
print(f"Show notes:\n{episode.show_notes}")
print(f"Transcript:\n{episode.transcript}")
```

### 3. Extractors Module (`src/extractors/`)

#### `llm_router.py` - Requesty.ai Integration

**Features:**
- OpenAI-compatible client with Requesty.ai routing
- Intelligent model selection (cost/performance optimization)
- Multiple model tiers (fast, smart, expert, vision, long_context)
- Automatic fallback on errors
- Usage tracking (requests, tokens, cost)
- Batch processing

**Usage:**
```python
from extractors import LLMRouter, RoutingStrategy, ModelTier

# Initialize router
router = LLMRouter(
    api_key="your-requesty-key",
    base_url="https://router.requesty.ai/v1",
    default_model="gpt-4o"
)

# Simple completion
response = await router.complete(
    prompt="Summarize this article...",
    system_prompt="You are a summarization expert."
)

# With routing strategy
strategy = RoutingStrategy(
    prefer_tier=ModelTier.FAST,
    max_cost_per_request=0.01,
    fallback_models=["gpt-3.5-turbo", "claude-3-5-haiku"]
)

response = await router.complete(
    prompt="Extract key points...",
    strategy=strategy
)

# JSON response
data = await router.complete_with_json(
    prompt="Extract entities as JSON with keys: people, orgs, locations"
)

# Usage stats
stats = router.get_usage_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Estimated cost: ${stats['estimated_cost']:.2f}")
```

#### `schema_extractor.py` - Pydantic Model Extraction

**Features:**
- Type-safe extraction using Pydantic models
- Built-in schemas (Person, Organization, Article, Event, Product, etc.)
- Custom schema support
- Multiple instance extraction
- Batch processing
- Fallback values on failure

**Usage:**
```python
from extractors import SchemaExtractor, Person, Article, extract_custom
from pydantic import BaseModel, Field

# Use built-in schemas
extractor = SchemaExtractor()

person = await extractor.extract(
    text=article_text,
    schema=Person,
    context="Focus on the main subject of the article"
)

print(f"Name: {person.name}")
print(f"Title: {person.title}")
print(f"Organization: {person.organization}")

# Extract multiple instances
article = await extractor.extract(text, Article)
print(f"Title: {article.title}")
print(f"Key points: {article.key_points}")
print(f"Sentiment: {article.sentiment}")

# Custom schema
class CompanyInfo(BaseModel):
    name: str = Field(..., description="Company name")
    founded: str = Field(None, description="Year founded")
    employees: int = Field(None, description="Number of employees")
    products: list[str] = Field(default_factory=list)

company = await extract_custom(
    text=company_page,
    schema=CompanyInfo,
    context="Extract from the about page"
)
```

#### `prompt_extractor.py` - Natural Language Extraction

**Features:**
- Template-based extraction (summary, key_points, entities, etc.)
- Custom prompt support
- Output format handling (text, JSON, list, markdown)
- Pre-defined templates for common tasks
- Batch processing
- Few-shot learning support

**Usage:**
```python
from extractors import PromptExtractor, summarize_text, extract_key_points

# Use convenience functions
summary = await summarize_text(
    text=article,
    length=3  # 3 sentences
)

key_points = await extract_key_points(
    text=article,
    max_points=5
)

# Advanced extractor
extractor = PromptExtractor()

# Template-based extraction
sentiment = await extractor.analyze_sentiment(text)
print(f"Sentiment: {sentiment['sentiment']}")
print(f"Confidence: {sentiment['confidence']}")

entities = await extractor.extract_entities(text)
print(f"People: {entities['people']}")
print(f"Organizations: {entities['organizations']}")

# Custom extraction
result = await extractor.extract_custom(
    text=text,
    instruction="Extract all dates mentioned",
    context="Focus on historical events",
    examples=[
        {"input": "War ended in 1945", "output": "1945"},
        {"input": "Born March 15, 1990", "output": "March 15, 1990"}
    ]
)
```

## Complete Pipeline Example

Here's a complete example combining all modules:

```python
import asyncio
from crawler import PlaywrightBrowser, RateLimiter, ProxyPool, ProxyConfig
from parser import parse_html, extract_metadata, track_citations
from extractors import SchemaExtractor, Article, PromptExtractor

async def crawl_and_extract(url: str):
    # Initialize components
    rate_limiter = RateLimiter(auto_adjust=True)

    proxy_pool = ProxyPool(
        proxies=[ProxyConfig(url="http://proxy:8080")],
    )
    await proxy_pool.start()

    # Crawl with browser
    async with PlaywrightBrowser() as browser:
        # Rate limit
        domain = await rate_limiter.acquire(url)

        try:
            # Fetch page
            result = await browser.fetch(url, take_screenshot=True)
            html = result.html

            # Parse content
            content = parse_html(url, html)
            metadata = extract_metadata(html, url)
            citations = track_citations(html, url)

            # Extract with LLM
            schema_extractor = SchemaExtractor()
            article = await schema_extractor.extract(content['text'], Article)

            prompt_extractor = PromptExtractor()
            summary = await prompt_extractor.summarize(content['text'], length=3)
            key_points = await prompt_extractor.extract_key_points(content['text'])

            # Compile results
            intelligence = {
                "url": url,
                "title": content['title'],
                "author": content['author'],
                "published_date": content['date'],
                "word_count": content['word_count'],
                "metadata": {
                    "og_image": metadata.open_graph.image,
                    "description": metadata.description,
                },
                "content": {
                    "text": content['text'],
                    "markdown": content['markdown'],
                    "summary": summary,
                    "key_points": key_points,
                },
                "structure": {
                    "links": len(content['links']),
                    "images": len(content['images']),
                    "citations": citations.total_count,
                },
                "analysis": {
                    "topics": article.topics,
                    "sentiment": article.sentiment,
                },
                "screenshot": result.screenshot,
            }

            rate_limiter.record_success(domain)
            return intelligence

        except Exception as e:
            rate_limiter.record_failure(domain)
            raise
        finally:
            rate_limiter.release(domain)

# Run
intelligence = asyncio.run(crawl_and_extract("https://example.com/article"))
```

## Environment Variables

```bash
# Playwright
USE_PLAYWRIGHT=1

# Proxies (comma-separated)
PROXY_URLS=http://proxy1:8080,http://proxy2:8080

# Requesty.ai / OpenAI
REQUESTY_API_KEY=your-key
REQUESTY_BASE_URL=https://router.requesty.ai/v1
REQUESTY_DEFAULT_MODEL=openai/gpt-4o

# Alternative OpenAI
OPENAI_API_KEY=your-key
```

## Dependencies

All dependencies are in `requirements.txt`:
- `playwright` - Browser automation
- `trafilatura` - Content extraction
- `beautifulsoup4` - HTML parsing
- `lxml` - XML/HTML processing
- `httpx` - HTTP client
- `openai` - LLM client
- `instructor` - Pydantic extraction
- `pydantic` - Data validation

## Testing

```python
# Test browser
from crawler import fetch_page

html = await fetch_page("https://example.com", use_playwright=True)

# Test parser
from parser import parse_html

content = parse_html("https://example.com", html)
assert content['title']
assert content['text']

# Test extractor
from extractors import summarize_text

summary = await summarize_text(content['text'])
assert len(summary) > 0
```

## Performance Considerations

1. **Browser Pooling**: Use `BrowserPool` for multiple concurrent crawls
2. **Rate Limiting**: Configure per-domain limits to avoid blocks
3. **Proxy Rotation**: Use proxy pool for distributed crawling
4. **Batch Processing**: Use batch methods for multiple items
5. **Caching**: Implement caching layer for frequently accessed content

## Error Handling

All modules include comprehensive error handling with:
- Automatic retries with exponential backoff
- Fallback mechanisms (proxy fallback, model fallback)
- Detailed logging
- Graceful degradation

## Production Deployment

For production use:

1. Set up Playwright browsers: `playwright install chromium`
2. Configure environment variables
3. Set up proxy pool for distributed crawling
4. Implement request queuing (Celery/Redis)
5. Add monitoring and alerting
6. Set up rate limit persistence
7. Implement result caching (Redis)

## License

This implementation is part of the intelligence-pipeline project.
