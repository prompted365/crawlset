# Intelligence Pipeline

Web intelligence system: crawl, parse, extract, store in RuVector, and monitor websets.

## Overview

The Intelligence Pipeline is a comprehensive web intelligence system that provides:
- Web crawling and content extraction
- Content parsing and preprocessing
- LLM-powered enrichment and analysis
- Vector storage and semantic search via RuVector
- Webset monitoring and change detection
- Distributed task processing with Celery
- Real-time API access

## Architecture

### Components

- **Backend**: FastAPI + Celery + Playwright + SQLAlchemy + RuVector client
- **Frontend**: React + Vite + TypeScript + TailwindCSS
- **Message Broker**: Redis
- **Vector Database**: RuVector (git submodule)
- **Task Queue**: Celery with 3 priority queues (realtime, batch, background)
- **Monitoring**: Flower (Celery task monitoring)

### Services

1. **Redis** - Message broker and cache
2. **Backend** - FastAPI REST API server
3. **Celery Worker (Realtime)** - High-priority tasks (4 concurrent workers)
4. **Celery Worker (Batch)** - Batch processing tasks (2 concurrent workers)
5. **Celery Worker (Background)** - Low-priority background tasks (1 worker)
6. **Celery Beat** - Periodic task scheduler
7. **Flower** - Celery monitoring UI
8. **Frontend** - React application

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git (for submodules)

### Installation

1. Clone the repository with submodules:
```bash
git clone --recursive <repository-url>
cd intelligence-pipeline
```

2. Create environment configuration:
```bash
cp .env.example .env
```

3. Edit `.env` and add your API keys:
```bash
# Required: Add your LLM API key
REQUESTY_API_KEY=your_key_here
# Or use OpenAI/Anthropic directly
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

4. Start all services:
```bash
docker-compose up -d
```

5. Check service health:
```bash
# Backend API
curl http://localhost:8000/health

# View logs
docker-compose logs -f backend
```

### Service URLs

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **Flower Monitoring**: http://localhost:5555
- **Redis**: localhost:6379

## Development

### Project Structure

```
intelligence-pipeline/
├── backend/
│   ├── src/
│   │   ├── api/          # FastAPI routes and endpoints
│   │   ├── crawler/      # Web crawling logic
│   │   ├── parser/       # Content parsing
│   │   ├── extractors/   # Data extraction
│   │   ├── enrichments/  # LLM enrichment
│   │   ├── preprocessing/# Content preprocessing
│   │   ├── queue/        # Celery tasks and workers
│   │   ├── database/     # SQLAlchemy models
│   │   ├── websets/      # Webset management
│   │   ├── monitors/     # Change detection
│   │   └── ruvector/     # Vector DB client
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── vendor/
│   └── ruvector/        # Git submodule
├── data/                # Persistent data
├── logs/                # Application logs
├── docker-compose.yml
├── docker-compose.test.yml
└── .env.example
```

### Running Tests

Run the test suite using the test Docker Compose configuration:

```bash
# Run all tests
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Run backend tests only
docker-compose -f docker-compose.test.yml run --rm backend-test pytest

# Run with coverage
docker-compose -f docker-compose.test.yml run --rm backend-test pytest --cov=src --cov-report=html
```

### Development Workflow

1. **Start services in development mode**:
```bash
docker-compose up -d
```

2. **View logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker-realtime
```

3. **Restart a service**:
```bash
docker-compose restart backend
```

4. **Stop all services**:
```bash
docker-compose down
```

5. **Clean up volumes** (WARNING: deletes all data):
```bash
docker-compose down -v
```

### Making Changes

The following directories are mounted as volumes for hot-reloading:
- `backend/src/` - Backend code changes reload automatically
- `frontend/src/` - Frontend code changes reload automatically
- `data/` - Persistent database and vector storage
- `logs/` - Application logs

## Docker Commands

### Build and Start

```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend

# Start all services
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# View logs
docker-compose logs -f [service-name]
```

### Management

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Restart service
docker-compose restart [service-name]

# Scale workers
docker-compose up -d --scale celery-worker-realtime=3

# Execute command in container
docker-compose exec backend bash
```

### Debugging

```bash
# View service status
docker-compose ps

# Check service logs
docker-compose logs --tail=100 backend

# Follow logs
docker-compose logs -f celery-worker-realtime

# Inspect container
docker-compose exec backend bash

# Run Python shell
docker-compose exec backend python

# Check Celery workers
docker-compose exec backend celery -A src.queue.celery_app inspect active
```

## API Usage

### Extract Content from URL

```bash
curl -X POST "http://localhost:8000/extract" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Create Webset

```bash
curl -X POST "http://localhost:8000/websets" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Webset",
    "urls": ["https://example.com"],
    "enabled": true
  }'
```

### Monitor Webset

```bash
curl -X POST "http://localhost:8000/websets/{webset_id}/monitor"
```

See full API documentation at http://localhost:8000/docs

## Configuration

### Environment Variables

All configuration is done through environment variables in `.env`:

#### Required Configuration
- `REQUESTY_API_KEY` or `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - LLM API key
- `REDIS_URL` - Redis connection URL
- `SQLITE_DB` - SQLite database path
- `RUVECTOR_DATA_DIR` - Vector database directory

#### Optional Configuration
- `PORT` - Backend port (default: 8000)
- `LOG_LEVEL` - Logging level (default: INFO)
- `CELERY_*_CONCURRENCY` - Worker concurrency settings
- `ENABLE_*` - Feature flags

See `.env.example` for complete configuration options.

### Scaling Workers

Adjust worker concurrency in `docker-compose.yml` or via command line:

```bash
# Scale realtime workers to 3 instances
docker-compose up -d --scale celery-worker-realtime=3

# Or modify docker-compose.yml:
celery-worker-realtime:
  command: celery -A src.queue.celery_app worker -Q realtime -l info --concurrency=8
```

## Monitoring

### Flower UI

Access Celery Flower monitoring at http://localhost:5555

Features:
- Real-time task monitoring
- Worker status and statistics
- Task history and results
- Queue management
- Worker pool management

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Redis health
docker-compose exec redis redis-cli ping

# Check all services
docker-compose ps
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100 celery-worker-realtime

# Export logs
docker-compose logs > logs/docker-compose.log
```

## Production Deployment

### Prerequisites

1. **Set production environment variables**:
```bash
ENVIRONMENT=production
DEBUG=false
WORKERS=4
```

2. **Use production-grade secrets**:
```bash
# Generate secure JWT secret
openssl rand -hex 32

# Update .env with real API keys
```

3. **Configure reverse proxy** (Nginx/Traefik):
- SSL/TLS termination
- Rate limiting
- WebSocket support for real-time features
- Static file serving

### Production Recommendations

1. **Database**: Replace SQLite with PostgreSQL for production
2. **Redis**: Use Redis Sentinel or Cluster for high availability
3. **Monitoring**: Add Prometheus + Grafana for metrics
4. **Logging**: Centralize logs with ELK stack or similar
5. **Backups**: Implement regular backups of data directory
6. **Secrets**: Use Docker secrets or external secret management
7. **Resources**: Set memory and CPU limits in docker-compose.yml

### Example Nginx Configuration

```nginx
server {
    listen 80;
    server_name intelligence.example.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### Common Issues

**Services won't start**:
```bash
# Check logs
docker-compose logs

# Rebuild containers
docker-compose down
docker-compose up -d --build
```

**Port conflicts**:
```bash
# Change ports in docker-compose.yml or .env
PORT=8001
```

**Database locked**:
```bash
# Stop all services accessing the database
docker-compose down
rm data/websets.db
docker-compose up -d
```

**Celery workers not processing tasks**:
```bash
# Check worker status in Flower
# Restart workers
docker-compose restart celery-worker-realtime celery-worker-batch celery-worker-background
```

**Out of memory**:
```bash
# Reduce worker concurrency in docker-compose.yml
# Add memory limits to services
```

## Contributing

1. Create feature branch
2. Make changes
3. Run tests: `docker-compose -f docker-compose.test.yml up`
4. Submit pull request

## License

[Your License Here]

## Support

For issues and questions, please use the GitHub issue tracker.
