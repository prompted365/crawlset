"""
Result reranking utilities for search results.

Provides multiple reranking strategies:
- Score-based: Rerank by relevance scores
- Diversity: Maximize diversity in results
- Recency: Prioritize recent content
- Hybrid: Combine multiple signals
- Cross-encoder: Use cross-encoder models for semantic reranking
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)


class RerankingStrategy(str, Enum):
    """Available reranking strategies."""
    SCORE = "score"
    DIVERSITY = "diversity"
    RECENCY = "recency"
    HYBRID = "hybrid"
    CROSS_ENCODER = "cross_encoder"
    MMR = "mmr"  # Maximal Marginal Relevance


@dataclass
class SearchResult:
    """Represents a search result."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = None
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RerankingConfig:
    """Configuration for reranking."""
    strategy: RerankingStrategy = RerankingStrategy.SCORE
    diversity_lambda: float = 0.5  # For MMR: balance relevance vs diversity
    recency_weight: float = 0.3  # Weight for recency in hybrid scoring
    score_weight: float = 0.7  # Weight for original score in hybrid scoring
    recency_decay_days: float = 30.0  # Days for recency to decay
    top_k: Optional[int] = None  # Return top K results


class ResultReranker:
    """Result reranker with multiple strategies."""

    def __init__(self, config: RerankingConfig = None):
        self.config = config or RerankingConfig()

    def rerank(self, results: List[SearchResult], query: Optional[str] = None) -> List[SearchResult]:
        """
        Rerank search results according to configured strategy.

        Args:
            results: List of search results to rerank
            query: Optional query text for semantic reranking

        Returns:
            Reranked list of search results
        """
        if not results:
            return []

        strategy = self.config.strategy

        if strategy == RerankingStrategy.SCORE:
            reranked = self._rerank_by_score(results)
        elif strategy == RerankingStrategy.DIVERSITY:
            reranked = self._rerank_by_diversity(results)
        elif strategy == RerankingStrategy.RECENCY:
            reranked = self._rerank_by_recency(results)
        elif strategy == RerankingStrategy.HYBRID:
            reranked = self._rerank_hybrid(results)
        elif strategy == RerankingStrategy.MMR:
            reranked = self._rerank_by_mmr(results)
        elif strategy == RerankingStrategy.CROSS_ENCODER:
            if not query:
                logger.warning("Cross-encoder reranking requires query, falling back to score")
                reranked = self._rerank_by_score(results)
            else:
                reranked = self._rerank_by_cross_encoder(results, query)
        else:
            raise ValueError(f"Unknown reranking strategy: {strategy}")

        # Apply top-k filtering if configured
        if self.config.top_k and self.config.top_k < len(reranked):
            reranked = reranked[:self.config.top_k]

        return reranked

    def _rerank_by_score(self, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank by original relevance score (descending)."""
        return sorted(results, key=lambda r: r.score, reverse=True)

    def _rerank_by_recency(self, results: List[SearchResult]) -> List[SearchResult]:
        """Rerank by recency (most recent first)."""
        def get_recency_score(result: SearchResult) -> float:
            # Try to extract date from metadata
            date_str = result.metadata.get('date') or result.metadata.get('published_at')
            if not date_str:
                return 0.0

            try:
                # Parse date (assuming ISO format or similar)
                if isinstance(date_str, str):
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                elif isinstance(date_str, datetime):
                    date = date_str
                else:
                    return 0.0

                # Calculate age in days
                age_days = (datetime.now(date.tzinfo) - date).days

                # Apply exponential decay
                decay_factor = math.exp(-age_days / self.config.recency_decay_days)
                return decay_factor

            except (ValueError, TypeError) as e:
                logger.debug(f"Failed to parse date {date_str}: {e}")
                return 0.0

        # Calculate recency scores
        for result in results:
            recency_score = get_recency_score(result)
            result.metadata['recency_score'] = recency_score

        # Sort by recency score
        return sorted(results, key=lambda r: r.metadata.get('recency_score', 0), reverse=True)

    def _rerank_hybrid(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Hybrid reranking combining relevance score and recency.

        Combines original score with recency using weighted average.
        """
        # First calculate recency scores
        for result in results:
            date_str = result.metadata.get('date') or result.metadata.get('published_at')
            recency_score = 0.0

            if date_str:
                try:
                    if isinstance(date_str, str):
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    elif isinstance(date_str, datetime):
                        date = date_str
                    else:
                        date = None

                    if date:
                        age_days = (datetime.now(date.tzinfo) - date).days
                        recency_score = math.exp(-age_days / self.config.recency_decay_days)

                except (ValueError, TypeError):
                    pass

            result.metadata['recency_score'] = recency_score

        # Normalize scores to [0, 1]
        max_score = max(r.score for r in results) if results else 1.0
        min_score = min(r.score for r in results) if results else 0.0
        score_range = max_score - min_score if max_score > min_score else 1.0

        # Calculate hybrid scores
        for result in results:
            normalized_score = (result.score - min_score) / score_range
            recency_score = result.metadata.get('recency_score', 0.0)

            hybrid_score = (
                self.config.score_weight * normalized_score +
                self.config.recency_weight * recency_score
            )

            result.metadata['hybrid_score'] = hybrid_score

        # Sort by hybrid score
        return sorted(results, key=lambda r: r.metadata.get('hybrid_score', 0), reverse=True)

    def _rerank_by_diversity(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Rerank to maximize diversity in results.

        Uses simple text-based diversity (different from MMR which uses embeddings).
        """
        if not results:
            return []

        # Start with highest scoring result
        reranked = [results[0]]
        remaining = results[1:]

        while remaining:
            # Find result most different from already selected results
            max_diversity_score = -1
            most_diverse = None

            for candidate in remaining:
                # Calculate diversity score (simple text overlap)
                diversity_score = self._calculate_text_diversity(candidate, reranked)

                if diversity_score > max_diversity_score:
                    max_diversity_score = diversity_score
                    most_diverse = candidate

            if most_diverse:
                reranked.append(most_diverse)
                remaining.remove(most_diverse)
            else:
                break

        return reranked

    def _calculate_text_diversity(
        self,
        candidate: SearchResult,
        selected: List[SearchResult]
    ) -> float:
        """Calculate text diversity score (lower overlap = higher diversity)."""
        if not selected:
            return 1.0

        # Tokenize text
        candidate_tokens = set(candidate.text.lower().split())

        # Calculate average similarity with selected results
        similarities = []
        for result in selected:
            result_tokens = set(result.text.lower().split())
            if not candidate_tokens or not result_tokens:
                similarity = 0.0
            else:
                overlap = len(candidate_tokens & result_tokens)
                union = len(candidate_tokens | result_tokens)
                similarity = overlap / union if union > 0 else 0.0
            similarities.append(similarity)

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        # Diversity is inverse of similarity
        diversity = 1.0 - avg_similarity

        return diversity

    def _rerank_by_mmr(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Rerank using Maximal Marginal Relevance (MMR).

        Balances relevance and diversity using embeddings.
        Requires results to have embeddings.
        """
        if not results:
            return []

        # Check if results have embeddings
        if not all(r.embedding for r in results):
            logger.warning("MMR reranking requires embeddings, falling back to diversity")
            return self._rerank_by_diversity(results)

        # Start with highest scoring result
        reranked = [results[0]]
        remaining = results[1:]

        lambda_param = self.config.diversity_lambda

        while remaining:
            max_mmr_score = -float('inf')
            best_candidate = None

            for candidate in remaining:
                # Relevance score
                relevance = candidate.score

                # Calculate maximum similarity to already selected results
                max_similarity = 0.0
                for selected in reranked:
                    similarity = self._cosine_similarity(
                        candidate.embedding,
                        selected.embedding
                    )
                    max_similarity = max(max_similarity, similarity)

                # MMR score: balance relevance and diversity
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity

                if mmr_score > max_mmr_score:
                    max_mmr_score = mmr_score
                    best_candidate = candidate

            if best_candidate:
                reranked.append(best_candidate)
                remaining.remove(best_candidate)
            else:
                break

        return reranked

    def _rerank_by_cross_encoder(
        self,
        results: List[SearchResult],
        query: str
    ) -> List[SearchResult]:
        """
        Rerank using cross-encoder model.

        This is a placeholder - implement with actual cross-encoder model.
        """
        logger.warning("Cross-encoder reranking not yet implemented, using score-based")
        return self._rerank_by_score(results)

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


# Convenience functions

def rerank_results(
    results: List[SearchResult],
    strategy: RerankingStrategy = RerankingStrategy.SCORE,
    query: Optional[str] = None,
    top_k: Optional[int] = None,
    **kwargs
) -> List[SearchResult]:
    """
    Rerank search results with specified strategy.

    Args:
        results: List of search results
        strategy: Reranking strategy to use
        query: Optional query for semantic reranking
        top_k: Optional limit on number of results
        **kwargs: Additional configuration options

    Returns:
        Reranked list of search results
    """
    config = RerankingConfig(strategy=strategy, top_k=top_k, **kwargs)
    reranker = ResultReranker(config)
    return reranker.rerank(results, query=query)


def rerank_by_recency(
    results: List[SearchResult],
    recency_weight: float = 0.5,
    score_weight: float = 0.5,
    recency_decay_days: float = 30.0,
) -> List[SearchResult]:
    """
    Rerank results with emphasis on recency.

    Args:
        results: List of search results
        recency_weight: Weight for recency (0-1)
        score_weight: Weight for original score (0-1)
        recency_decay_days: Days for recency to decay

    Returns:
        Reranked list of search results
    """
    return rerank_results(
        results,
        strategy=RerankingStrategy.HYBRID,
        recency_weight=recency_weight,
        score_weight=score_weight,
        recency_decay_days=recency_decay_days,
    )


def rerank_for_diversity(
    results: List[SearchResult],
    diversity_lambda: float = 0.5,
) -> List[SearchResult]:
    """
    Rerank results to maximize diversity.

    Args:
        results: List of search results
        diversity_lambda: Balance between relevance and diversity (0-1)

    Returns:
        Reranked list of search results
    """
    strategy = RerankingStrategy.MMR if all(r.embedding for r in results) else RerankingStrategy.DIVERSITY

    return rerank_results(
        results,
        strategy=strategy,
        diversity_lambda=diversity_lambda,
    )


def apply_custom_reranking(
    results: List[SearchResult],
    score_fn: Callable[[SearchResult], float],
) -> List[SearchResult]:
    """
    Apply custom reranking function.

    Args:
        results: List of search results
        score_fn: Function that takes SearchResult and returns score

    Returns:
        Reranked list of search results
    """
    # Calculate custom scores
    for result in results:
        custom_score = score_fn(result)
        result.metadata['custom_score'] = custom_score

    # Sort by custom score
    return sorted(results, key=lambda r: r.metadata.get('custom_score', 0), reverse=True)


def deduplicate_results(
    results: List[SearchResult],
    similarity_threshold: float = 0.9,
    use_embeddings: bool = True,
) -> List[SearchResult]:
    """
    Remove duplicate or highly similar results.

    Args:
        results: List of search results
        similarity_threshold: Similarity threshold for deduplication
        use_embeddings: Whether to use embeddings for similarity

    Returns:
        Deduplicated list of search results
    """
    if not results:
        return []

    deduplicated = [results[0]]

    for candidate in results[1:]:
        is_duplicate = False

        for existing in deduplicated:
            # Check for duplicates
            if use_embeddings and candidate.embedding and existing.embedding:
                similarity = ResultReranker._cosine_similarity(
                    candidate.embedding,
                    existing.embedding
                )
            else:
                # Text-based similarity
                candidate_tokens = set(candidate.text.lower().split())
                existing_tokens = set(existing.text.lower().split())
                overlap = len(candidate_tokens & existing_tokens)
                union = len(candidate_tokens | existing_tokens)
                similarity = overlap / union if union > 0 else 0.0

            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            deduplicated.append(candidate)

    return deduplicated
