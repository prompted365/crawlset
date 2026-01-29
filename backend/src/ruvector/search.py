"""
Hybrid Search Engine combining lexical and semantic search.

Implements BM25 for lexical matching and vector similarity for semantic search,
with result fusion using Reciprocal Rank Fusion (RRF).
"""
from __future__ import annotations

import logging
import math
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class BM25:
    """
    BM25 (Best Matching 25) lexical search implementation.

    BM25 is a probabilistic retrieval function that ranks documents
    based on query term frequency and inverse document frequency.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25.

        Args:
            k1: Term frequency saturation parameter (typical: 1.2-2.0)
            b: Length normalization parameter (typical: 0.75)
        """
        self.k1 = k1
        self.b = b
        self.corpus: List[List[str]] = []
        self.doc_ids: List[str] = []
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.idf: Dict[str, float] = {}
        self.doc_len: List[int] = []
        self.avgdl: float = 0.0

    def tokenize(self, text: str) -> List[str]:
        """Simple whitespace tokenization with lowercase."""
        return text.lower().split()

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Index documents for BM25 search.

        Args:
            documents: List of dicts with 'id' and 'text' fields
        """
        self.corpus = []
        self.doc_ids = []
        self.doc_len = []

        # Tokenize all documents
        for doc in documents:
            tokens = self.tokenize(doc["text"])
            self.corpus.append(tokens)
            self.doc_ids.append(doc["id"])
            self.doc_len.append(len(tokens))

        # Calculate average document length
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0

        # Calculate document frequencies
        self.doc_freqs.clear()
        for tokens in self.corpus:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] += 1

        # Calculate IDF scores
        num_docs = len(self.corpus)
        self.idf = {
            term: math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)
            for term, df in self.doc_freqs.items()
        }

        logger.info(f"Indexed {num_docs} documents for BM25")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Search documents using BM25.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of (doc_id, score) tuples
        """
        if not self.corpus:
            return []

        query_tokens = self.tokenize(query)
        scores = []

        for idx, doc_tokens in enumerate(self.corpus):
            score = self._score_document(query_tokens, doc_tokens, idx)
            if score > 0:
                scores.append((self.doc_ids[idx], score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def _score_document(
        self, query_tokens: List[str], doc_tokens: List[str], doc_idx: int
    ) -> float:
        """Calculate BM25 score for a document."""
        score = 0.0
        doc_len = self.doc_len[doc_idx]
        term_freqs = Counter(doc_tokens)

        for token in query_tokens:
            if token not in self.idf:
                continue

            tf = term_freqs[token]
            idf = self.idf[token]

            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * (doc_len / self.avgdl)
            )
            score += idf * (numerator / denominator)

        return score


class HybridSearchEngine:
    """
    Hybrid search combining lexical (BM25) and semantic (vector) search.

    Uses Reciprocal Rank Fusion (RRF) to combine results from both
    search methods, with configurable weighting.
    """

    def __init__(
        self,
        client: Any,  # RuVectorClient
        alpha: float = 0.5,
        k1: float = 1.5,
        b: float = 0.75,
        rrf_k: int = 60,
    ):
        """
        Initialize hybrid search engine.

        Args:
            client: RuVectorClient instance
            alpha: Weight for semantic search (0.0 = lexical only, 1.0 = semantic only)
            k1: BM25 term frequency parameter
            b: BM25 length normalization parameter
            rrf_k: RRF constant (typical: 60)
        """
        self.client = client
        self.alpha = alpha
        self.bm25 = BM25(k1=k1, b=b)
        self.rrf_k = rrf_k
        self._indexed = False

        logger.info(f"Initialized HybridSearchEngine with alpha={alpha}")

    async def index_documents(self) -> None:
        """Index all documents in the client for BM25 search."""
        if not self.client._initialized:
            await self.client.initialize()

        # Get all documents
        documents = [
            {"id": doc_id, "text": doc["text"]}
            for doc_id, doc in self.client._documents.items()
        ]

        if documents:
            self.bm25.index_documents(documents)
            self._indexed = True
            logger.info(f"Indexed {len(documents)} documents for hybrid search")
        else:
            logger.warning("No documents to index")

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        rerank: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining lexical and semantic results.

        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Metadata filters to apply
            rerank: Apply reranking to final results

        Returns:
            List of search results with scores
        """
        if not self._indexed:
            await self.index_documents()

        # Perform both searches
        lexical_results = []
        semantic_results = []

        # Lexical search (BM25)
        if self.alpha < 1.0 and self._indexed:
            lexical_results = self.bm25.search(query, top_k=top_k * 2)

        # Semantic search (vector similarity)
        if self.alpha > 0.0:
            semantic_results_raw = await self.client.hybrid_search(
                query=query,
                top_k=top_k * 2,
                filter_metadata=filter_metadata,
            )
            semantic_results = [
                (result["id"], result["score"]) for result in semantic_results_raw
            ]

        # Combine results using weighted fusion
        if self.alpha == 0.0:
            # Lexical only
            combined_scores = self._normalize_scores(lexical_results)
        elif self.alpha == 1.0:
            # Semantic only
            combined_scores = self._normalize_scores(semantic_results)
        else:
            # Hybrid: use RRF to combine
            combined_scores = self._reciprocal_rank_fusion(
                lexical_results, semantic_results
            )

        # Get top results
        top_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        # Build result objects
        results = []
        for doc_id, score in top_ids:
            doc = self.client._documents.get(doc_id)
            if doc:
                # Apply metadata filtering if specified
                if filter_metadata:
                    doc_meta = doc.get("metadata", {})
                    if not all(
                        doc_meta.get(k) == v for k, v in filter_metadata.items()
                    ):
                        continue

                results.append({
                    "id": doc_id,
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "score": float(score),
                })

        # Apply reranking if requested
        if rerank and len(results) > 1:
            results = await self._rerank_results(query, results)

        return results[:top_k]

    def _normalize_scores(
        self, results: List[Tuple[str, float]]
    ) -> Dict[str, float]:
        """Normalize scores to [0, 1] range."""
        if not results:
            return {}

        scores = [score for _, score in results]
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score

        if score_range == 0:
            return {doc_id: 1.0 for doc_id, _ in results}

        return {
            doc_id: (score - min_score) / score_range for doc_id, score in results
        }

    def _reciprocal_rank_fusion(
        self,
        lexical_results: List[Tuple[str, float]],
        semantic_results: List[Tuple[str, float]],
    ) -> Dict[str, float]:
        """
        Combine results using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank)) for each result list
        """
        rrf_scores: Dict[str, float] = defaultdict(float)

        # Add lexical ranks with weight (1 - alpha)
        for rank, (doc_id, _) in enumerate(lexical_results, start=1):
            rrf_scores[doc_id] += (1 - self.alpha) / (self.rrf_k + rank)

        # Add semantic ranks with weight alpha
        for rank, (doc_id, _) in enumerate(semantic_results, start=1):
            rrf_scores[doc_id] += self.alpha / (self.rrf_k + rank)

        return dict(rrf_scores)

    async def _rerank_results(
        self, query: str, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using cross-encoder (placeholder).

        In production, this would use a cross-encoder model to
        compute more accurate relevance scores.

        Args:
            query: Original query
            results: Initial search results

        Returns:
            Reranked results
        """
        # Placeholder: For now, just return as-is
        # TODO: Integrate cross-encoder model for reranking
        logger.debug("Reranking not implemented, returning original results")
        return results

    def set_alpha(self, alpha: float) -> None:
        """
        Update semantic search weight.

        Args:
            alpha: Weight for semantic search (0.0-1.0)
        """
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be between 0.0 and 1.0")
        self.alpha = alpha
        logger.info(f"Updated alpha to {alpha}")

    async def get_similar_documents(
        self,
        doc_id: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find documents similar to a given document.

        Args:
            doc_id: Document ID to find similar docs for
            top_k: Number of results to return
            filter_metadata: Metadata filters to apply

        Returns:
            List of similar documents
        """
        # Get the source document
        doc = self.client._documents.get(doc_id)
        if not doc:
            return []

        # Use the document text as the query
        return await self.search(
            query=doc["text"],
            top_k=top_k + 1,  # +1 because source doc will be in results
            filter_metadata=filter_metadata,
        )

    async def multi_query_search(
        self,
        queries: List[str],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search using multiple queries and combine results.

        Useful for query expansion or multi-aspect search.

        Args:
            queries: List of search queries
            top_k: Number of results to return
            filter_metadata: Metadata filters to apply

        Returns:
            Combined search results
        """
        all_results: Dict[str, float] = defaultdict(float)

        # Execute all queries
        for query in queries:
            results = await self.search(
                query=query,
                top_k=top_k * 2,
                filter_metadata=filter_metadata,
            )

            # Aggregate scores
            for result in results:
                all_results[result["id"]] += result["score"]

        # Normalize by number of queries
        for doc_id in all_results:
            all_results[doc_id] /= len(queries)

        # Get top results
        top_ids = sorted(all_results.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        # Build result objects
        results = []
        for doc_id, score in top_ids:
            doc = self.client._documents.get(doc_id)
            if doc:
                results.append({
                    "id": doc_id,
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {}),
                    "score": float(score),
                })

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            "alpha": self.alpha,
            "indexed_documents": len(self.bm25.corpus) if self._indexed else 0,
            "bm25_vocab_size": len(self.bm25.idf),
            "rrf_k": self.rrf_k,
        }

    def __repr__(self) -> str:
        return (
            f"HybridSearchEngine(alpha={self.alpha}, "
            f"indexed={self._indexed}, "
            f"docs={len(self.bm25.corpus) if self._indexed else 0})"
        )


async def create_search_engine(
    client: Any,  # RuVectorClient
    alpha: float = 0.5,
) -> HybridSearchEngine:
    """
    Factory function to create and initialize a HybridSearchEngine.

    Args:
        client: Initialized RuVectorClient
        alpha: Semantic search weight (0.0-1.0)

    Returns:
        Initialized HybridSearchEngine
    """
    search_engine = HybridSearchEngine(client=client, alpha=alpha)
    await search_engine.index_documents()
    return search_engine
