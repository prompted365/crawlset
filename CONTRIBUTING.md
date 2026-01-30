# Contributing to Crawlset

Thanks for your interest in contributing! This guide will help you get started.

## Code of Conduct

Be respectful, inclusive, and constructive. We follow the [Contributor Covenant](CODE_OF_CONDUCT.md).

## Ways to Contribute

- Report bugs
- Suggest features
- Improve documentation
- Write code
- Review pull requests
- Help others in issues/discussions

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/crawlset.git
cd crawlset
```

### 2. Set Up Development Environment

**Backend**:
```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

**Frontend**:
```bash
cd frontend
npm install
```

**Full Stack**:
```bash
cp .env.example .env
# Add your API keys
docker-compose up -d
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

## Development Workflow

### Making Changes

1. Write code following our [style guide](#code-style)
2. Add/update tests
3. Update documentation
4. Test locally
5. Commit with a [good message](#commit-messages)

### Testing

**Backend**:
```bash
# Run tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Type check
mypy backend/src

# Format check
black --check backend/src
ruff check backend/src
```

**Frontend**:
```bash
npm test
npm run lint
npm run type-check
```

**Integration**:
```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Code Style

**Python**:
- Use `black` for formatting (line length: 100)
- Use `ruff` for linting
- Use `mypy --strict` for type checking
- Write docstrings for public functions
- Use async/await for I/O operations

**TypeScript**:
- Use `prettier` for formatting
- Use ESLint for linting
- Write JSDoc comments for complex functions
- Use functional components with hooks

### Commit Messages

Good commit messages help others understand your changes.

Format:
```
type: brief description

Detailed explanation if needed.

Fixes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

Examples:
```
feat: add podcast RSS feed parser

Adds support for parsing podcast RSS feeds with iTunes extensions.
Extracts episode metadata, show notes, and audio file info.

Closes #45
```

```
fix: prevent duplicate items in websets

The deduplication check was using URL only. Now checks content hash too.

Fixes #67
```

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally
- [ ] Code is formatted
- [ ] Type checking passes
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] No secrets or API keys in code

### Submitting

1. Push your branch to your fork
2. Open a Pull Request to `main`
3. Fill out the PR template
4. Wait for CI checks
5. Address review feedback
6. Get approval and merge

### PR Template

Your PR description should include:

**What**: What does this PR do?
**Why**: Why is this change needed?
**How**: How does it work?
**Testing**: How was it tested?
**Screenshots**: (if UI changes)

Example:
```markdown
## Add company enrichment plugin

### What
Adds a new enrichment plugin that extracts company information (CEO, revenue, employee count, industry, headquarters).

### Why
Users want to automatically enrich company data in their websets without manual research.

### How
Uses LLM extraction with a Pydantic schema. Falls back to pattern matching if LLM fails. Caches results in Redis for 24 hours.

### Testing
- Unit tests for pattern matching
- Integration test with real LLM
- Tested on 50 company websites

### Checklist
- [x] Tests pass
- [x] Documentation updated
- [x] CHANGELOG.md updated
```

## Project Structure

### Backend

```
backend/src/
├── api/          # FastAPI routes and schemas
├── crawler/      # Browser automation
├── parser/       # Content extraction
├── extractors/   # LLM-powered extraction
├── websets/      # Collection management
├── monitors/     # Cron monitoring
├── enrichments/  # Plugin system
├── queue/        # Celery tasks
├── ruvector/     # Vector database (Rust HTTP client)
├── preprocessing/# Content processing
└── database/     # SQLAlchemy models
```

### Frontend

```
frontend/src/
├── components/   # React components
│   ├── ui/      # shadcn/ui base components
│   ├── websets/ # Webset-specific components
│   ├── extraction/
│   ├── monitors/
│   └── ...
├── pages/        # Main pages
├── lib/          # Utilities
│   ├── api.ts   # API client
│   ├── hooks.ts # React Query hooks
│   └── utils.ts # Helper functions
└── main.tsx      # Entry point
```

## Common Contributions

### Adding a New API Endpoint

1. Define route in `backend/src/api/routes/`:
```python
@router.post("/websets/{id}/export")
async def export_webset(
    id: str,
    format: str = "json",
    db: AsyncSession = Depends(get_db_session)
) -> Response:
    manager = WebsetManager(db)
    data = await manager.export(id, format)
    return Response(content=data, media_type=f"application/{format}")
```

2. Add Pydantic schema if needed in `backend/src/api/schemas/`

3. Include router in `main.py`

4. Add tests in `backend/tests/`

5. Update API client in `frontend/src/lib/api.ts`

6. Document in `backend/API_ROUTES.md`

### Adding an Enrichment Plugin

1. Create `backend/src/enrichments/plugins/my_enricher.py`:
```python
from src.enrichments.engine import BaseEnricher

class MyEnricher(BaseEnricher):
    name = "my_enricher"
    description = "Enriches items with X"

    async def enrich(self, item: WebsetItem) -> dict:
        # Your logic
        return {"my_field": "value"}
```

2. Add tests in `backend/tests/enrichments/`

3. Document in plugin docstring

4. Update `docs/ENRICHMENTS.md`

### Adding a Frontend Component

1. Create component in `frontend/src/components/`:
```typescript
export function MyComponent({ data }: MyComponentProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{data.title}</CardTitle>
      </CardHeader>
      <CardContent>{data.content}</CardContent>
    </Card>
  )
}
```

2. Export from `index.ts` if needed

3. Add to Storybook (if we add it)

4. Use in page

### Improving Documentation

- Fix typos and clarity issues
- Add examples
- Update outdated information
- Add screenshots/diagrams
- Improve code comments

Even small doc improvements help!

## Testing Guidelines

### Unit Tests

Test individual functions/classes:

```python
def test_parse_url():
    result = parse_url("https://example.com/page?q=test")
    assert result.domain == "example.com"
    assert result.path == "/page"
    assert result.query == {"q": "test"}
```

### Integration Tests

Test component interactions:

```python
async def test_create_and_populate_webset(db_session):
    manager = WebsetManager(db_session)
    webset = await manager.create(name="Test")

    await manager.add_item(webset.id, url="https://example.com")
    items = await manager.get_items(webset.id)

    assert len(items) == 1
    assert items[0].url == "https://example.com"
```

### End-to-End Tests

Test full workflows:

```python
async def test_full_extraction_workflow(client):
    # Submit extraction
    response = await client.post("/api/extraction/extract", json={"url": "https://example.com"})
    job_id = response.json()["job_id"]

    # Wait for completion
    await wait_for_job(job_id)

    # Check result
    response = await client.get(f"/api/extraction/jobs/{job_id}/result")
    assert response.status_code == 200
    assert "title" in response.json()
```

## Documentation Standards

### Python Docstrings

Use Google style:

```python
async def create_webset(
    name: str,
    search_query: str = None,
    entity_type: str = None
) -> Webset:
    """Create a new webset collection.

    Args:
        name: Display name for the webset
        search_query: Optional search query for populating the webset
        entity_type: Type of entities to collect (e.g., "company", "person")

    Returns:
        The created webset object

    Raises:
        ValueError: If name is empty
        DatabaseError: If database operation fails

    Example:
        ```python
        webset = await create_webset(
            name="AI Companies",
            entity_type="company"
        )
        ```
    """
```

### TypeScript JSDoc

```typescript
/**
 * Fetches websets from the API with optional filtering.
 *
 * @param filters - Optional filters to apply
 * @param filters.entityType - Filter by entity type
 * @param filters.search - Search query for name
 * @returns Promise resolving to array of websets
 *
 * @example
 * ```typescript
 * const websets = await fetchWebsets({ entityType: 'company' })
 * ```
 */
export async function fetchWebsets(filters?: {
  entityType?: string
  search?: string
}): Promise<Webset[]> {
  // ...
}
```

### Markdown Documentation

- Use clear headings
- Add code examples
- Include screenshots for UI features
- Link to related docs
- Keep it concise

## Review Process

### For Contributors

- Be responsive to feedback
- Ask questions if unclear
- Make requested changes
- Be patient

### For Reviewers

- Be constructive and respectful
- Explain the "why" behind suggestions
- Approve when ready
- Thank the contributor

## Release Process

(Maintainers only)

1. Update version in `pyproject.toml` and `package.json`
2. Update CHANGELOG.md
3. Create git tag: `git tag v0.2.0`
4. Push tag: `git push --tags`
5. GitHub Actions will create release

## Getting Help

- Read the [CLAUDE.md](CLAUDE.md) file
- Check existing issues
- Ask in GitHub Discussions
- Ping maintainers in PR (if stuck)

## Recognition

Contributors are recognized in:
- README.md contributors section
- CHANGELOG.md for each release
- GitHub contributors page

Thank you for contributing to Crawlset! Every contribution makes the project better.
