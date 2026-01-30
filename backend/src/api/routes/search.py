"""
Search API routes for querying webset content.

Provides hybrid search, semantic search, and lexical search capabilities
across websets using RuVector integration.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ...websets.search import SearchExecutor, SearchResult
from ...ruvector.client import RuVectorClient
from ...config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Get settings
settings = get_settings()


def get_search_executor() -> SearchExecutor:
    """Dependency for SearchExecutor."""
    ruvector_client = RuVectorClient(ruvector_url=settings.ruvector_url)
    return SearchExecutor(ruvector_client=ruvector_client)


# ============================================================================
# Request/Response Schemas
# ============================================================================


class SearchRequest(BaseModel):
    """Request schema for search queries."""
    query: str = Field(..., description="Search query string")
    webset_id: Optional[str] = Field(None, description="Optional webset ID to search within")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filters")


class SemanticSearchRequest(BaseModel):
    """Request schema for semantic search."""
    query: str = Field(..., description="Semantic search query")
    webset_id: Optional[str] = Field(None, description="Optional webset ID to search within")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")


class LexicalSearchRequest(BaseModel):
    """Request schema for lexical/keyword search."""
    query: str = Field(..., description="Keyword search query")
    webset_id: Optional[str] = Field(None, description="Optional webset ID to search within")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")


class SearchResultResponse(BaseModel):
    """Response schema for search results."""
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """Response schema for search operations."""
    query: str
    total_results: int
    results: List[SearchResultResponse]
    search_type: str


class SuggestionResponse(BaseModel):
    """Response schema for search suggestions."""
    query: str
    suggestions: List[str]


# ============================================================================
# Search Endpoints
# ============================================================================


@router.post("/query", response_model=SearchResponse)
async def hybrid_search(
    request: SearchRequest,
    executor: SearchExecutor = Depends(get_search_executor),
) -> SearchResponse:
    """
    Execute hybrid search (semantic + keyword) across websets.

    Args:
        request: Search request
        executor: Search executor

    Returns:
        Search results
    """
    try:
        logger.info(f"Executing hybrid search: {request.query}")

        # Execute search
        results = await executor.execute_ruvector_search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters,
        )

        # Convert to response format
        result_responses = [
            SearchResultResponse(
                url=result.url,
                title=result.title,
                content=result.content,
                score=result.score,
                metadata=result.metadata,
            )
            for result in results
        ]

        return SearchResponse(
            query=request.query,
            total_results=len(result_responses),
            results=result_responses,
            search_type="hybrid",
        )

    except Exception as e:
        logger.error(f"Failed to execute hybrid search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute search: {str(e)}",
        )


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    executor: SearchExecutor = Depends(get_search_executor),
) -> SearchResponse:
    """
    Execute pure semantic search using embeddings.

    Args:
        request: Semantic search request
        executor: Search executor

    Returns:
        Search results
    """
    try:
        logger.info(f"Executing semantic search: {request.query}")

        # For semantic-only search, we use RuVector with semantic mode
        # In practice, this would use the RuVector client's semantic_search method
        results = await executor.execute_ruvector_search(
            query=request.query,
            top_k=request.top_k,
        )

        # Convert to response format
        result_responses = [
            SearchResultResponse(
                url=result.url,
                title=result.title,
                content=result.content,
                score=result.score,
                metadata=result.metadata,
            )
            for result in results
        ]

        return SearchResponse(
            query=request.query,
            total_results=len(result_responses),
            results=result_responses,
            search_type="semantic",
        )

    except Exception as e:
        logger.error(f"Failed to execute semantic search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute semantic search: {str(e)}",
        )


@router.post("/lexical", response_model=SearchResponse)
async def lexical_search(
    request: LexicalSearchRequest,
    executor: SearchExecutor = Depends(get_search_executor),
) -> SearchResponse:
    """
    Execute pure keyword/lexical search.

    Args:
        request: Lexical search request
        executor: Search executor

    Returns:
        Search results
    """
    try:
        logger.info(f"Executing lexical search: {request.query}")

        # For lexical-only search, we would use RuVector's keyword search
        # This is a placeholder - actual implementation would use keyword-only mode
        results = await executor.execute_ruvector_search(
            query=request.query,
            top_k=request.top_k,
        )

        # Convert to response format
        result_responses = [
            SearchResultResponse(
                url=result.url,
                title=result.title,
                content=result.content,
                score=result.score,
                metadata=result.metadata,
            )
            for result in results
        ]

        return SearchResponse(
            query=request.query,
            total_results=len(result_responses),
            results=result_responses,
            search_type="lexical",
        )

    except Exception as e:
        logger.error(f"Failed to execute lexical search: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute lexical search: {str(e)}",
        )


@router.get("/suggest", response_model=SuggestionResponse)
async def get_suggestions(
    q: str = Query(..., description="Partial query for suggestions"),
    limit: int = Query(5, ge=1, le=20, description="Number of suggestions to return"),
) -> SuggestionResponse:
    """
    Get search suggestions/autocomplete.

    Args:
        q: Partial query string
        limit: Maximum number of suggestions

    Returns:
        Search suggestions
    """
    try:
        logger.info(f"Getting search suggestions for: {q}")

        # This is a placeholder implementation
        # In a real system, this would query a suggestion index or recent searches
        suggestions = []

        # Simple placeholder logic
        if len(q) >= 2:
            # Could use:
            # - Recent search history
            # - Popular queries
            # - Entity/topic suggestions based on webset content
            # - Prefix matching on indexed terms

            # For now, return basic suggestions
            base_suggestions = [
                f"{q} company",
                f"{q} person",
                f"{q} technology",
                f"{q} news",
                f"{q} research",
            ]
            suggestions = base_suggestions[:limit]

        return SuggestionResponse(
            query=q,
            suggestions=suggestions,
        )

    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}",
        )
