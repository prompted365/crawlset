# Quick Start Guide

Fast reference for working with the backend infrastructure.

## Installation & Setup

```bash
cd /Users/breydentaylor/operationTorque/intelligence-pipeline/backend

# Install dependencies (if not already done)
pip install -r requirements.txt

# Verify setup
python3 verify_setup.py

# Run development server
uvicorn src.api.main:app --reload --port 8080
```

## Common Imports

```python
# Database models
from src.database import (
    Webset, WebsetItem, Monitor, MonitorRun, ExtractionJob,
    get_db_session, init_database
)

# API schemas
from src.api.schemas import (
    WebsetCreate, WebsetResponse,
    MonitorCreate, MonitorResponse,
    ExtractionJobCreate, ExtractionJobResponse
)

# Configuration
from src.config import get_settings

# FastAPI dependencies
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
```

## Database Operations

### Create a new webset

```python
from sqlalchemy import select
from src.database import Webset, get_db_session

async def create_webset(db: AsyncSession):
    webset = Webset(
        id="my-webset",
        name="My Webset",
        entity_type="podcast",
        search_query="tech podcasts"
    )
    db.add(webset)
    await db.commit()
    await db.refresh(webset)
    return webset
```

### Query websets

```python
async def get_all_websets(db: AsyncSession):
    result = await db.execute(select(Webset))
    return result.scalars().all()

async def get_webset_by_id(db: AsyncSession, webset_id: str):
    result = await db.execute(
        select(Webset).where(Webset.id == webset_id)
    )
    return result.scalar_one_or_none()
```

### Update a webset

```python
async def update_webset(db: AsyncSession, webset_id: str, name: str):
    result = await db.execute(
        select(Webset).where(Webset.id == webset_id)
    )
    webset = result.scalar_one_or_none()
    if webset:
        webset.name = name
        await db.commit()
        await db.refresh(webset)
    return webset
```

### Delete a webset

```python
async def delete_webset(db: AsyncSession, webset_id: str):
    result = await db.execute(
        select(Webset).where(Webset.id == webset_id)
    )
    webset = result.scalar_one_or_none()
    if webset:
        await db.delete(webset)
        await db.commit()
```

## FastAPI Route Example

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import Webset, get_db_session
from src.api.schemas import WebsetCreate, WebsetResponse

router = APIRouter()

@router.post("/websets", response_model=WebsetResponse)
async def create_webset(
    webset_data: WebsetCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new webset."""
    # Check if webset already exists
    result = await db.execute(
        select(Webset).where(Webset.id == webset_data.id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Webset already exists")

    # Create new webset
    webset = Webset(**webset_data.model_dump())
    db.add(webset)
    await db.commit()
    await db.refresh(webset)

    return webset

@router.get("/websets/{webset_id}", response_model=WebsetResponse)
async def get_webset(
    webset_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """Get a webset by ID."""
    result = await db.execute(
        select(Webset).where(Webset.id == webset_id)
    )
    webset = result.scalar_one_or_none()
    if not webset:
        raise HTTPException(status_code=404, detail="Webset not found")

    return webset
```

## Configuration Access

```python
from src.config import get_settings

settings = get_settings()

# Access configuration values
database_url = settings.database_url
requesty_api_key = settings.requesty_api_key
cors_origins = settings.cors_origins
port = settings.port
```

## Testing

```python
import pytest
from httpx import AsyncClient
from src.api.main import app

@pytest.mark.asyncio
async def test_create_webset():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/websets",
            json={
                "id": "test-webset",
                "name": "Test Webset",
                "entity_type": "podcast"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Webset"
```

## Common Patterns

### Get or Create

```python
async def get_or_create_webset(db: AsyncSession, webset_id: str, name: str):
    result = await db.execute(
        select(Webset).where(Webset.id == webset_id)
    )
    webset = result.scalar_one_or_none()

    if not webset:
        webset = Webset(id=webset_id, name=name)
        db.add(webset)
        await db.commit()
        await db.refresh(webset)

    return webset
```

### Bulk Insert

```python
async def bulk_insert_items(db: AsyncSession, items: list[dict]):
    webset_items = [WebsetItem(**item) for item in items]
    db.add_all(webset_items)
    await db.commit()
```

### Join Query

```python
async def get_websets_with_item_count(db: AsyncSession):
    from sqlalchemy import func

    result = await db.execute(
        select(
            Webset.id,
            Webset.name,
            func.count(WebsetItem.id).label('item_count')
        )
        .outerjoin(WebsetItem)
        .group_by(Webset.id, Webset.name)
    )
    return result.all()
```

## Environment Variables

Create `.env` file:

```bash
# Required
DATABASE_URL=sqlite+aiosqlite:///./data/websets.db
REQUESTY_API_KEY=your-api-key-here

# Optional (with defaults)
PORT=8080
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:5173"]
```

## API Endpoints

Once running at http://localhost:8080:

- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc
- **OpenAPI JSON**: http://localhost:8080/openapi.json
- **Health Check**: http://localhost:8080/health

## Debugging

### Enable SQL logging

```python
# In .env
DATABASE_ECHO=true

# Or in code
from src.config import reload_settings
settings = reload_settings()
```

### Check database state

```python
from src.database import get_db_manager

db_manager = get_db_manager()
async with db_manager.get_session() as session:
    result = await session.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = result.fetchall()
    print(tables)
```

### Enable debug logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Common Issues

### Import Error

```python
# Wrong
from database import Webset  # ❌

# Correct
from src.database import Webset  # ✓
```

### Not using async/await

```python
# Wrong
def create_webset(db: AsyncSession):  # ❌
    db.add(webset)
    db.commit()

# Correct
async def create_webset(db: AsyncSession):  # ✓
    db.add(webset)
    await db.commit()
```

### Database not initialized

```python
# Error: Database not initialized
# Solution: Ensure lifespan context manager runs
# The FastAPI app handles this automatically
```

## Next Steps

1. Implement remaining API routes
2. Add Alembic migrations
3. Write tests with pytest
4. Add authentication
5. Deploy to production
