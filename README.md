# 🕸️ Crawlset

<div align="center">

**Production-grade web intelligence pipeline that rivals Firecrawl + Exa + Spark**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## ⚡ Why Crawlset?

Build powerful web intelligence systems without vendor lock-in or API costs. Crawlset combines the best of **Firecrawl's extraction**, **Exa's websets**, and **Spark's distributed processing** into one self-hosted platform.

```bash
# Extract, enrich, and monitor any website
curl -X POST http://localhost:8000/api/extraction/extract \
  -d '{"url": "https://news.ycombinator.com"}'

# Set up automated monitoring
curl -X POST http://localhost:8000/api/monitors \
  -d '{"webset_id": "...", "cron": "0 */6 * * *", "behavior": "hybrid"}'
```

## 🎯 Features

### Advanced Web Crawling
- 🤖 **Anti-bot Detection Bypass** - Playwright with webdriver removal, navigator mocking
- 🔄 **Proxy Rotation** - Multiple rotation strategies with health checking
- ⚡ **Rate Limiting** - Per-domain token bucket with exponential backoff
- 🍪 **Session Management** - Cookie persistence, authentication support
- 📸 **Screenshot Capture** - Full page and element-specific captures

### Intelligent Extraction
- 📄 **Content Parsing** - Trafilatura, BeautifulSoup, custom extractors
- 🎙️ **Podcast Support** - RSS feeds, transcripts, metadata extraction
- 🏷️ **Structured Data** - Schema.org, Open Graph, JSON-LD
- 🤖 **LLM Extraction** - Pydantic models, prompt-based extraction
- 📚 **Citation Tracking** - XPath/CSS selectors with context

### Webset Management
- 📦 **Collections** - Organize content by topic/entity
- 🔍 **Hybrid Search** - Milvus vector + BM25 keyword search
- 🔄 **Deduplication** - SHA256, SimHash, MinHash strategies
- 💎 **Enrichments** - Company, person, content enrichers with LLM
- 📊 **Analytics** - Trending topics, insights, entity graphs

### Automated Monitoring
- ⏰ **Cron Scheduling** - Timezone-aware job execution
- 🎯 **Behaviors** - Search (find new), Refresh (update existing), Hybrid
- 📈 **Run History** - Statistics, error tracking, change detection
- 🔔 **Notifications** - Ready for webhook/email integration

### Distributed Processing
- 🚀 **Priority Queues** - Realtime, batch, background workers
- ♻️ **Auto-retry** - Exponential backoff with dead letter queue
- 📊 **Flower UI** - Real-time task monitoring
- 🎛️ **Resource Management** - Memory limits, connection pooling

### Vector Storage
- 🗄️ **Milvus Integration** - Production-grade vector database
- 🔍 **Hybrid Search** - Semantic + keyword with configurable weighting
- 🧠 **Embeddings** - sentence-transformers with Redis caching
- 📈 **Scalable** - Horizontal scaling, distributed deployment

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Python 3.11+ and Node.js 22+ for local development

### 1-Minute Setup

```bash
# Clone the repository
git clone https://github.com/prompted365/crawlset.git
cd crawlset

# Configure environment
cp .env.example .env
# Edit .env and add your LLM API key (Requesty.ai, OpenAI, or Anthropic)

# Start all services
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Access Points
- 🎨 **Frontend**: http://localhost:3000
- 📡 **API Docs**: http://localhost:8000/docs
- 🌸 **Flower (Tasks)**: http://localhost:5555
- 🗄️ **Milvus**: localhost:19530

## 📖 Usage Examples

### Extract Web Content

```python
# Python SDK
from crawlset import CrawlsetClient

client = CrawlsetClient("http://localhost:8000")

# Extract content
job = client.extract("https://example.com")
result = job.wait()

print(result.title, result.content, result.metadata)
```

```bash
# REST API
curl -X POST http://localhost:8000/api/extraction/extract \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Create and Monitor Webset

```python
# Create collection
webset = client.create_webset(
    name="AI News",
    search_query="artificial intelligence news 2025",
    entity_type="article"
)

# Set up automated monitoring (every 6 hours)
monitor = client.create_monitor(
    webset_id=webset.id,
    cron="0 */6 * * *",
    behavior="hybrid"  # Search for new + refresh existing
)
```

### Hybrid Search

```python
# Search across all websets
results = client.search(
    query="machine learning breakthroughs",
    mode="hybrid",  # Combines semantic + keyword
    alpha=0.7,      # 70% semantic, 30% keyword
    top_k=20
)

for result in results:
    print(f"{result.score}: {result.title} - {result.url}")
```

### Enrich with LLM

```python
# Enrich webset items
client.enrich_webset(
    webset_id=webset.id,
    plugins=["company_enricher", "content_enricher"]
)

# Get enriched data
items = client.get_webset_items(webset.id)
for item in items:
    print(item.enrichments["summary"])
    print(item.enrichments["key_points"])
```

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   Milvus    │
│  React/TS   │     │   FastAPI   │     │   Vectors   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐     ┌─────────────┐
                    │    Redis    │────▶│   Celery    │
                    │   Broker    │     │   Workers   │
                    └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   SQLite    │
                    │ Operational │
                    └─────────────┘
```

## 📊 Comparison

| Feature | Crawlset | Firecrawl | Exa | Spark |
|---------|----------|-----------|-----|-------|
| **Self-hosted** | ✅ | ❌ | ❌ | ✅ |
| **No API costs** | ✅ | ❌ | ❌ | ✅ |
| **Anti-bot detection** | ✅ | ✅ | ❌ | ❌ |
| **LLM extraction** | ✅ | ✅ | ✅ | ❌ |
| **Webset management** | ✅ | ❌ | ✅ | ❌ |
| **Hybrid search** | ✅ | ❌ | ✅ | ❌ |
| **Distributed tasks** | ✅ | ❌ | ❌ | ✅ |
| **Docker deployment** | ✅ | ❌ | ❌ | ⚠️ Complex |
| **Graph operations** | ✅ | ❌ | ⚠️ Limited | ❌ |

## 📚 Documentation

- [Quick Start Guide](QUICK_START_GUIDE.md) - Get running in 5 minutes
- [System Summary](SYSTEM_SUMMARY.md) - Complete feature overview
- [API Documentation](http://localhost:8000/docs) - Interactive Swagger docs
- [Milvus Integration](docs/MILVUS_GUIDE.md) - Vector database deep dive
- [Contributing Guide](CONTRIBUTING.md) - How to contribute
- [Deployment Guide](DEPLOYMENT.md) - Production deployment

## 🛠️ Technology Stack

**Backend**
- FastAPI - High-performance async API
- Playwright - Browser automation
- Celery - Distributed task queue
- SQLAlchemy - ORM with SQLite/PostgreSQL
- Milvus - Vector database
- sentence-transformers - Embeddings

**Frontend**
- React 19 - UI framework
- TypeScript - Type safety
- Vite - Build tool
- shadcn/ui - Component library
- React Query - Server state

## 🎯 Use Cases

- 🔍 **Competitive Intelligence** - Monitor competitor websites, track changes
- 📰 **News Aggregation** - Collect and organize news from multiple sources
- 🎙️ **Podcast Research** - Extract transcripts, analyze episodes
- 🏢 **Lead Generation** - Extract company/person data from web
- 📚 **Research** - Build searchable knowledge bases
- 📈 **SEO Analysis** - Track rankings, backlinks, content
- 🤖 **AI Training** - Collect and curate web data for models

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`docker-compose -f docker-compose.test.yml up`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Firecrawl](https://firecrawl.dev) - Inspiration for advanced crawling
- [Exa](https://exa.ai) - Inspiration for webset management
- [Milvus](https://milvus.io) - Vector database foundation
- [Playwright](https://playwright.dev) - Browser automation
- [FastAPI](https://fastapi.tiangolo.com) - API framework

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=prompted365/crawlset&type=Date)](https://star-history.com/#prompted365/crawlset&Date)

## 💬 Community

- [GitHub Issues](https://github.com/prompted365/crawlset/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/prompted365/crawlset/discussions) - Questions and discussions

---

<div align="center">

**Built with ❤️ by the open source community**

[Give us a ⭐](https://github.com/prompted365/crawlset) if you find this project useful!

</div>
