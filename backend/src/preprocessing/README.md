# Preprocessing Module - Content Processing Utilities

This module provides utilities for text preprocessing, chunking, cleaning, and result reranking.

## Features

- **Text Chunking**: Multiple strategies (sentence, sliding window, paragraph, semantic)
- **Content Cleaning**: Boilerplate removal, normalization, HTML entity decoding
- **Result Reranking**: Score-based, diversity, recency, hybrid, MMR strategies

## Modules

### 1. Chunker (`chunker.py`)

Semantic text chunking for processing large documents.

#### Strategies

- **Sentence-based**: Split by sentences, combine to target size
- **Sliding Window**: Fixed-size chunks with overlap
- **Paragraph-based**: Split by paragraphs
- **Fixed Size**: Simple character-based chunking
- **Semantic**: (Coming soon) Embedding-based boundary detection

#### Usage

```python
from src.preprocessing import chunk_text, ChunkingStrategy, chunk_for_embedding

# Basic sentence chunking
chunks = chunk_text(
    text="Your long text here...",
    strategy=ChunkingStrategy.SENTENCE,
    chunk_size=512,
    chunk_overlap=50
)

for chunk in chunks:
    print(f"Chunk {chunk.index}: {chunk.text[:100]}...")
    print(f"Position: {chunk.start_char}-{chunk.end_char}")

# Optimized for embeddings (handles token estimation)
embedding_chunks = chunk_for_embedding(
    text="Your text...",
    max_tokens=512,
    overlap_tokens=50
)

# Sliding window with sentence boundaries
chunks = chunk_text(
    text="Your text...",
    strategy=ChunkingStrategy.SLIDING_WINDOW,
    chunk_size=1000,
    chunk_overlap=200,
    respect_sentence_boundaries=True
)

# Paragraph-based chunking
chunks = chunk_text(
    text="Your text...",
    strategy=ChunkingStrategy.PARAGRAPH,
    chunk_size=800,
    min_chunk_size=200
)
```

#### Advanced Usage

```python
from src.preprocessing import TextChunker, ChunkingConfig

# Custom configuration
config = ChunkingConfig(
    strategy=ChunkingStrategy.SENTENCE,
    chunk_size=512,
    chunk_overlap=50,
    min_chunk_size=100,
    max_chunk_size=2000,
    respect_sentence_boundaries=True,
    strip_whitespace=True
)

chunker = TextChunker(config)
chunks = chunker.chunk(text)

# Access chunk metadata
for chunk in chunks:
    print(chunk.metadata)  # e.g., {"sentence_count": 5}
```

#### Helper Functions

```python
from src.preprocessing import split_into_sentences, split_into_paragraphs

# Split text into sentences
sentences = split_into_sentences(text)

# Split text into paragraphs
paragraphs = split_into_paragraphs(text)
```

### 2. Cleaner (`cleaner.py`)

Content cleaning and normalization utilities.

#### Usage

```python
from src.preprocessing import clean_content, clean_for_embedding, clean_for_display

# Basic cleaning
cleaned = clean_content(
    text="Your HTML-extracted text...",
    remove_boilerplate=True,
    normalize_whitespace=True
)

# Aggressive cleaning for embeddings
cleaned = clean_for_embedding(text)
# - Removes boilerplate
# - Removes URLs and emails
# - Normalizes unicode
# - Extracts main content
# - Removes duplicates

# Minimal cleaning for display
cleaned = clean_for_display(text)
# - Preserves formatting
# - Normalizes whitespace
# - Decodes HTML entities
```

#### Advanced Usage

```python
from src.preprocessing import ContentCleaner

# Custom cleaner
cleaner = ContentCleaner(
    remove_boilerplate=True,
    normalize_whitespace=True,
    normalize_unicode=True,
    decode_html_entities=True,
    remove_urls=True,
    remove_emails=True,
    min_word_length=2,
    max_consecutive_chars=4
)

cleaned = cleaner.clean(text)
```

#### Specific Cleaning Functions

```python
from src.preprocessing import (
    remove_navigation_text,
    extract_main_content,
    normalize_quotes_and_dashes,
    remove_duplicate_lines
)

# Remove navigation elements
text = remove_navigation_text(text, additional_words={'menu', 'footer'})

# Extract main content (filter short paragraphs)
main_text = extract_main_content(text, min_paragraph_length=50)

# Normalize typography
text = normalize_quotes_and_dashes(text)

# Remove duplicate lines
text = remove_duplicate_lines(text, case_sensitive=False)
```

### 3. Reranker (`reranker.py`)

Result reranking for search and retrieval.

#### Strategies

- **Score**: Sort by relevance score
- **Recency**: Prioritize recent content
- **Diversity**: Maximize result diversity
- **Hybrid**: Combine score and recency
- **MMR**: Maximal Marginal Relevance (with embeddings)

#### Usage

```python
from src.preprocessing import (
    SearchResult,
    rerank_results,
    RerankingStrategy,
    rerank_by_recency,
    rerank_for_diversity
)

# Create search results
results = [
    SearchResult(
        id="1",
        text="First result...",
        score=0.95,
        metadata={"date": "2024-01-15T00:00:00Z"}
    ),
    SearchResult(
        id="2",
        text="Second result...",
        score=0.90,
        metadata={"date": "2024-01-20T00:00:00Z"}
    ),
]

# Score-based reranking (default)
reranked = rerank_results(results, strategy=RerankingStrategy.SCORE)

# Recency-based reranking
reranked = rerank_by_recency(
    results,
    recency_weight=0.6,
    score_weight=0.4,
    recency_decay_days=30
)

# Diversity reranking
reranked = rerank_for_diversity(
    results,
    diversity_lambda=0.5  # Balance relevance vs diversity
)

# Hybrid reranking (score + recency)
reranked = rerank_results(
    results,
    strategy=RerankingStrategy.HYBRID,
    recency_weight=0.3,
    score_weight=0.7
)

# Limit results
reranked = rerank_results(
    results,
    strategy=RerankingStrategy.SCORE,
    top_k=10
)
```

#### Advanced Usage

```python
from src.preprocessing import ResultReranker, RerankingConfig

# Custom configuration
config = RerankingConfig(
    strategy=RerankingStrategy.HYBRID,
    diversity_lambda=0.5,
    recency_weight=0.3,
    score_weight=0.7,
    recency_decay_days=30.0,
    top_k=10
)

reranker = ResultReranker(config)
reranked = reranker.rerank(results)
```

#### MMR Reranking (with embeddings)

```python
# Results must have embeddings
results = [
    SearchResult(
        id="1",
        text="Result text...",
        score=0.95,
        embedding=[0.1, 0.2, 0.3, ...]  # Vector embedding
    ),
]

# MMR reranking
reranked = rerank_results(
    results,
    strategy=RerankingStrategy.MMR,
    diversity_lambda=0.5
)
```

#### Custom Reranking

```python
from src.preprocessing import apply_custom_reranking

# Define custom scoring function
def custom_score(result: SearchResult) -> float:
    # Your custom logic
    base_score = result.score
    length_bonus = len(result.text) / 1000
    return base_score + length_bonus

# Apply custom reranking
reranked = apply_custom_reranking(results, score_fn=custom_score)
```

#### Deduplication

```python
from src.preprocessing import deduplicate_results

# Remove duplicates
deduplicated = deduplicate_results(
    results,
    similarity_threshold=0.9,
    use_embeddings=True  # Use embeddings if available
)
```

## Common Workflows

### 1. Process Raw HTML Content

```python
from src.preprocessing import clean_content, chunk_text

# Clean extracted HTML text
cleaned_text = clean_content(
    raw_html_text,
    remove_boilerplate=True,
    normalize_whitespace=True,
    decode_html_entities=True
)

# Chunk for processing
chunks = chunk_text(
    cleaned_text,
    strategy=ChunkingStrategy.SENTENCE,
    chunk_size=512,
    chunk_overlap=50
)
```

### 2. Prepare Text for Embeddings

```python
from src.preprocessing import clean_for_embedding, chunk_for_embedding

# Clean and optimize for embeddings
cleaned = clean_for_embedding(raw_text)

# Chunk with token-aware sizing
chunks = chunk_for_embedding(
    cleaned,
    max_tokens=512,
    overlap_tokens=50
)

# Generate embeddings for each chunk
for chunk in chunks:
    embedding = generate_embedding(chunk.text)
    # Store embedding with chunk metadata
```

### 3. Search Result Processing

```python
from src.preprocessing import deduplicate_results, rerank_by_recency

# Get search results
results = search_index(query)

# Remove duplicates
unique_results = deduplicate_results(results, similarity_threshold=0.85)

# Rerank by recency and relevance
final_results = rerank_by_recency(
    unique_results,
    recency_weight=0.4,
    score_weight=0.6,
    recency_decay_days=60
)

# Return top 20
return final_results[:20]
```

### 4. Content Extraction Pipeline

```python
from src.preprocessing import (
    clean_content,
    remove_navigation_text,
    extract_main_content,
    chunk_text
)

# Full cleaning pipeline
def process_extracted_content(html_text: str):
    # Step 1: Basic cleaning
    cleaned = clean_content(html_text)

    # Step 2: Remove navigation
    cleaned = remove_navigation_text(cleaned)

    # Step 3: Extract main content
    main_content = extract_main_content(cleaned, min_paragraph_length=50)

    # Step 4: Chunk for storage
    chunks = chunk_text(main_content, chunk_size=800, chunk_overlap=100)

    return chunks
```

## Best Practices

### Chunking

1. **Choose appropriate strategy**:
   - Sentence: Best for semantic coherence
   - Sliding window: Good for overlapping context
   - Paragraph: Maintains document structure

2. **Set reasonable sizes**:
   - Embeddings: 512 tokens (~2000 chars)
   - LLM context: 4000-8000 tokens
   - Display: 200-500 chars per preview

3. **Use overlap**: 10-20% overlap helps maintain context

4. **Respect boundaries**: Enable `respect_sentence_boundaries` for readability

### Cleaning

1. **Context-specific cleaning**:
   - Embeddings: Aggressive (remove URLs, emails, boilerplate)
   - Display: Minimal (preserve formatting)
   - Analysis: Balanced (normalize but preserve content)

2. **Unicode normalization**: Always normalize for consistent processing

3. **Whitespace**: Normalize to avoid matching issues

4. **Test patterns**: Verify boilerplate patterns match your content

### Reranking

1. **Choose strategy based on use case**:
   - News/blog: Hybrid with high recency weight
   - Documentation: Score-based
   - Research: Diversity or MMR

2. **Tune weights**: Balance relevance vs other signals

3. **Use MMR with embeddings**: Best diversity with semantic understanding

4. **Deduplicate first**: Remove duplicates before reranking

## Performance Considerations

### Chunking

- Sentence splitting: O(n) where n = text length
- Memory: Creates new string objects for each chunk
- Optimization: Use generators for very large texts (future enhancement)

### Cleaning

- Regex operations: O(n) per pattern
- Unicode normalization: O(n)
- Optimization: Disable unused cleaning operations

### Reranking

- Score sort: O(n log n)
- MMR: O(n²) due to similarity calculations
- Optimization: Use top_k to limit result set

## Testing

```python
# Test chunking
from src.preprocessing import chunk_text, ChunkingStrategy

text = "Your test text. " * 100
chunks = chunk_text(text, chunk_size=200)
assert all(len(c.text) <= 220 for c in chunks)  # With overlap

# Test cleaning
from src.preprocessing import clean_content

dirty = "Hello   world!\\n\\n\\n\\nTest"
clean = clean_content(dirty)
assert "\\n\\n\\n" not in clean

# Test reranking
from src.preprocessing import SearchResult, rerank_results

results = [
    SearchResult("1", "text", 0.5),
    SearchResult("2", "text", 0.9),
]
reranked = rerank_results(results)
assert reranked[0].score > reranked[1].score
```

## Related Documentation

- [Queue Module](../queue/README.md)
- [Parser Module](../parser/)
- [Crawler Module](../crawler/)
