"""
Preprocessing module for content processing.

Provides utilities for:
- Text chunking (sentence-based, sliding window, semantic)
- Content cleaning (boilerplate removal, normalization)
- Result reranking (score, diversity, recency, hybrid)
"""

from .chunker import (
    TextChunker,
    ChunkingStrategy,
    ChunkingConfig,
    Chunk,
    chunk_text,
    chunk_for_embedding,
    split_into_sentences,
    split_into_paragraphs,
)
from .cleaner import (
    ContentCleaner,
    clean_content,
    clean_for_embedding,
    clean_for_display,
    remove_navigation_text,
    extract_main_content,
    normalize_quotes_and_dashes,
    remove_duplicate_lines,
)
from .reranker import (
    ResultReranker,
    RerankingStrategy,
    RerankingConfig,
    SearchResult,
    rerank_results,
    rerank_by_recency,
    rerank_for_diversity,
    apply_custom_reranking,
    deduplicate_results,
)

__all__ = [
    # Chunker
    "TextChunker",
    "ChunkingStrategy",
    "ChunkingConfig",
    "Chunk",
    "chunk_text",
    "chunk_for_embedding",
    "split_into_sentences",
    "split_into_paragraphs",
    # Cleaner
    "ContentCleaner",
    "clean_content",
    "clean_for_embedding",
    "clean_for_display",
    "remove_navigation_text",
    "extract_main_content",
    "normalize_quotes_and_dashes",
    "remove_duplicate_lines",
    # Reranker
    "ResultReranker",
    "RerankingStrategy",
    "RerankingConfig",
    "SearchResult",
    "rerank_results",
    "rerank_by_recency",
    "rerank_for_diversity",
    "apply_custom_reranking",
    "deduplicate_results",
]
