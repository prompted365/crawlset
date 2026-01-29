# Deployment Instructions

## Docker Compose Setup

Create at `/Users/breydentaylor/operationTorque/intelligence-pipeline/docker-compose.yml`

### Services

1. **redis**
   - Image: redis:7-alpine
   - Port: 6379
   - Volume: ./data/redis:/data
   - Health check

2. **backend**
   - Build: ./backend
   - Port: 8000
   - Environment: .env
   - Volumes: ./backend/src, ./data, ./logs
   - Depends on: redis
   - Command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000

3. **celery-worker-realtime**
   - Build: ./backend
   - Command: celery -A src.queue.celery_app worker -Q realtime -l info --concurrency=4
   - Depends on: redis, backend

4. **celery-worker-batch**
   - Build: ./backend
   - Command: celery -A src.queue.celery_app worker -Q batch -l info --concurrency=2

5. **celery-worker-background**
   - Build: ./backend
   - Command: celery -A src.queue.celery_app worker -Q background -l info --concurrency=1

6. **celery-beat**
   - Build: ./backend
   - Command: celery -A src.queue.celery_app beat -l info

7. **frontend**
   - Build: ./frontend
   - Port: 3000
   - Environment: VITE_API_URL=http://localhost:8000
   - Depends on: backend
   - Command: npm run dev

8. **flower** (optional - Celery monitoring)
   - Build: ./backend
   - Port: 5555
   - Command: celery -A src.queue.celery_app flower

## Dockerfiles

### backend/Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps chromium
COPY . .
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### frontend/Dockerfile
```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

## Environment Files

### .env.example
Create with all necessary variables:
- Database URLs
- Redis URL
- API keys (Requesty, OpenAI, Anthropic)
- RuVector settings
- Security settings

## Production Considerations

### Nginx Reverse Proxy
- SSL/TLS termination
- Rate limiting
- Static file serving
- WebSocket support

### Monitoring
- Prometheus metrics
- Grafana dashboards
- Celery Flower
- Health checks

### Scaling
- Multiple worker instances
- Redis Sentinel for HA
- Database replication
- CDN for frontend

## Development Setup

Create `.env` from `.env.example`
```bash
cp .env.example .env
# Edit .env with your settings
```

Start services:
```bash
docker-compose up -d
```

Stop services:
```bash
docker-compose down
```

View logs:
```bash
docker-compose logs -f [service-name]
```

## Testing
Include docker-compose.test.yml for testing environment
