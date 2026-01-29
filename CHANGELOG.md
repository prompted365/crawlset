# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-28

### Added
- Initial release of Crawlset
- Advanced web crawler with Playwright
  - Anti-bot detection bypass
  - Proxy rotation with health checking
  - Per-domain rate limiting
  - Session and cookie management
- Content extraction and parsing
  - Trafilatura for main content
  - BeautifulSoup for structured data
  - Podcast RSS feed parser
  - Citation tracking
- LLM-powered extraction
  - Schema-based extraction with Pydantic
  - Prompt-based extraction
  - Requesty.ai router integration
- Webset management system
  - Create and organize collections
  - Multiple deduplication strategies (SHA256, SimHash, MinHash)
  - Hybrid search with Milvus
- Automated monitoring
  - Cron-based scheduling
  - Three behavior types (Search, Refresh, Hybrid)
  - Run history and statistics
- Enrichment engine
  - Plugin architecture
  - Company, Person, and Content enrichers
  - LLM-powered enrichment
- Distributed processing
  - Celery task queue
  - Three priority levels (realtime, batch, background)
  - Automatic retry with exponential backoff
- Milvus vector database integration
  - Hybrid search (semantic + keyword)
  - sentence-transformers embeddings
  - Redis caching
- Frontend application
  - React 19 with TypeScript
  - 40+ components with shadcn/ui
  - 6 main pages (Dashboard, Websets, Extraction, Monitors, Search, Analytics)
  - Real-time updates with React Query
- Docker Compose deployment
  - 8 services (Redis, Backend, 3 Celery workers, Beat, Flower, Frontend)
  - Development and production configurations
- Comprehensive documentation
  - API documentation with Swagger
  - Quick start guide
  - System summary
  - Contribution guidelines

### Infrastructure
- MIT License
- Python 3.11+ backend
- Node.js 22+ frontend
- SQLite for operational data
- Milvus for vector storage
- Redis for caching and task queue

[0.1.0]: https://github.com/prompted365/crawlset/releases/tag/v0.1.0
