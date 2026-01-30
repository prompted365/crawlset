"""
Search query execution and result processing for websets.
Integrates with RuVector for hybrid search capabilities.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from ..ruvector.client import RuVectorClient
from ..crawler.browser import fetch_page
from ..parser.trafilatura_parser import parse_html
from .deduplication import ContentDeduplicator


class SearchResult:
    """Represents a single search result."""

    def __init__(
        self,
        url: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        score: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.url = url
        self.title = title
        self.content = content
        self.score = score
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
        }


class SearchExecutor:
    """Executes search queries and processes results."""

    def __init__(
        self,
        ruvector_client: Optional[RuVectorClient] = None,
        deduplicator: Optional[ContentDeduplicator] = None,
    ):
        self.ruvector_client = ruvector_client or RuVectorClient()
        self.deduplicator = deduplicator or ContentDeduplicator()

    async def execute_ruvector_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Execute a hybrid search query using RuVector.

        Args:
            query: Search query string
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of SearchResult objects
        """
        try:
            # Execute hybrid search (semantic + keyword)
            results = await self.ruvector_client.hybrid_search(query, top_k=top_k)

            search_results = []
            for result in results:
                search_results.append(
                    SearchResult(
                        url=result.get("url", ""),
                        title=result.get("title", ""),
                        content=result.get("text", ""),
                        score=result.get("score", 0.0),
                        metadata=result.get("metadata", {}),
                    )
                )

            return search_results

        except Exception as e:
            print(f"Error executing RuVector search: {e}")
            return []

    async def execute_web_search(
        self,
        query: str,
        search_engine: str = "google",
        num_results: int = 10,
    ) -> List[SearchResult]:
        """
        Execute a web search using external search engines.
        This is a placeholder for integration with search APIs.

        Args:
            query: Search query string
            search_engine: Search engine to use (google, bing, etc.)
            num_results: Number of results to fetch

        Returns:
            List of SearchResult objects with URLs (content not yet fetched)
        """
        # TODO: Integrate with search APIs (SerpAPI, Bing API, etc.)
        # For now, return empty list
        print(f"Web search not yet implemented for query: {query}")
        return []

    async def crawl_and_parse_urls(
        self,
        urls: List[str],
        use_playwright: bool = False,
        max_concurrent: int = 5,
    ) -> List[SearchResult]:
        """
        Crawl and parse a list of URLs.

        Args:
            urls: List of URLs to crawl
            use_playwright: Whether to use Playwright for rendering
            max_concurrent: Maximum concurrent requests

        Returns:
            List of SearchResult objects with parsed content
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def crawl_one(url: str) -> Optional[SearchResult]:
            async with semaphore:
                try:
                    html = await fetch_page(url, use_playwright=use_playwright)
                    parsed = parse_html(url, html)

                    return SearchResult(
                        url=url,
                        title=parsed.get("title", ""),
                        content=parsed.get("text", ""),
                        metadata={
                            "crawled_at": datetime.utcnow().isoformat(),
                            "links": parsed.get("links", []),
                        },
                    )
                except Exception as e:
                    print(f"Error crawling {url}: {e}")
                    return None

        tasks = [crawl_one(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None and exceptions
        return [r for r in results if isinstance(r, SearchResult)]

    async def process_search_results(
        self,
        results: List[SearchResult],
        deduplicate: bool = True,
        existing_content_hashes: Optional[set] = None,
    ) -> List[SearchResult]:
        """
        Process search results with deduplication.

        Args:
            results: List of SearchResult objects
            deduplicate: Whether to deduplicate results
            existing_content_hashes: Set of existing content hashes to check against

        Returns:
            List of unique SearchResult objects
        """
        if not deduplicate:
            return results

        unique_results = []
        seen_hashes = existing_content_hashes or set()

        for result in results:
            if not result.content:
                # Always include results without content (URLs only)
                unique_results.append(result)
                continue

            content_hash = self.deduplicator.compute_hash(result.content)

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)
            else:
                print(f"Duplicate content detected for URL: {result.url}")

        return unique_results

    async def search_and_crawl(
        self,
        query: str,
        search_type: str = "ruvector",
        top_k: int = 10,
        crawl_results: bool = True,
        deduplicate: bool = True,
        existing_content_hashes: Optional[set] = None,
    ) -> List[SearchResult]:
        """
        Execute a search query and optionally crawl the results.

        Args:
            query: Search query string
            search_type: Type of search (ruvector, web)
            top_k: Number of results to fetch
            crawl_results: Whether to crawl and parse result URLs
            deduplicate: Whether to deduplicate results
            existing_content_hashes: Set of existing content hashes

        Returns:
            List of processed SearchResult objects
        """
        # Execute search
        if search_type == "ruvector":
            results = await self.execute_ruvector_search(query, top_k=top_k)
        elif search_type == "web":
            results = await self.execute_web_search(query, num_results=top_k)
        else:
            raise ValueError(f"Unknown search type: {search_type}")

        # Crawl URLs if content not already present
        if crawl_results:
            urls_to_crawl = [r.url for r in results if not r.content]
            if urls_to_crawl:
                crawled = await self.crawl_and_parse_urls(urls_to_crawl)
                # Merge crawled content back into results
                crawled_map = {r.url: r for r in crawled}
                for result in results:
                    if result.url in crawled_map:
                        crawled_result = crawled_map[result.url]
                        result.content = crawled_result.content
                        result.title = result.title or crawled_result.title
                        result.metadata.update(crawled_result.metadata)

        # Process and deduplicate
        return await self.process_search_results(
            results,
            deduplicate=deduplicate,
            existing_content_hashes=existing_content_hashes,
        )


class SearchQueryBuilder:
    """Builds and optimizes search queries."""

    @staticmethod
    def build_entity_query(
        entity_type: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build a search query for a specific entity type.

        Args:
            entity_type: Type of entity (company, person, product, etc.)
            filters: Optional filters (location, industry, etc.)

        Returns:
            Formatted search query string
        """
        filters = filters or {}

        query_parts = [entity_type]

        # Add filters to query
        if "location" in filters:
            query_parts.append(f"in {filters['location']}")
        if "industry" in filters:
            query_parts.append(f"{filters['industry']}")
        if "keywords" in filters:
            keywords = filters["keywords"]
            if isinstance(keywords, list):
                query_parts.extend(keywords)
            else:
                query_parts.append(keywords)

        return " ".join(query_parts)

    @staticmethod
    def build_temporal_query(
        base_query: str,
        time_range: Optional[str] = None,
    ) -> str:
        """
        Add temporal constraints to a query.

        Args:
            base_query: Base search query
            time_range: Time range (e.g., "last week", "2024")

        Returns:
            Query with temporal constraints
        """
        if time_range:
            return f"{base_query} {time_range}"
        return base_query

    @staticmethod
    def expand_query_with_synonyms(
        query: str,
        synonyms: Optional[Dict[str, List[str]]] = None,
    ) -> List[str]:
        """
        Expand a query with synonyms for better recall.

        Args:
            query: Original query
            synonyms: Dictionary mapping terms to their synonyms

        Returns:
            List of expanded queries
        """
        if not synonyms:
            return [query]

        queries = [query]
        for term, syn_list in synonyms.items():
            if term.lower() in query.lower():
                for synonym in syn_list:
                    expanded = query.lower().replace(term.lower(), synonym)
                    if expanded not in queries:
                        queries.append(expanded)

        return queries
