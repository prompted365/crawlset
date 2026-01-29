"""
Advanced content extraction using trafilatura with additional features:
- Main content extraction with multiple strategies
- Author, date, and metadata extraction
- Link and image extraction
- Table and list extraction
- Language detection
- Reading time estimation
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import trafilatura
from bs4 import BeautifulSoup
from trafilatura.metadata import extract_metadata


@dataclass
class ExtractedLink:
    """Represents an extracted link."""
    url: str
    text: str
    title: Optional[str] = None
    rel: Optional[str] = None
    is_external: bool = False


@dataclass
class ExtractedImage:
    """Represents an extracted image."""
    url: str
    alt: Optional[str] = None
    title: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    caption: Optional[str] = None


@dataclass
class ExtractedTable:
    """Represents an extracted table."""
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None


@dataclass
class ParsedContent:
    """
    Comprehensive parsed content from a web page.
    """
    # Basic content
    url: str
    title: str
    text: str  # Main content text
    html: Optional[str] = None  # Clean HTML of main content
    markdown: Optional[str] = None  # Markdown version

    # Metadata
    author: Optional[str] = None
    date: Optional[datetime] = None
    description: Optional[str] = None
    site_name: Optional[str] = None
    language: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)

    # Structural elements
    links: List[ExtractedLink] = field(default_factory=list)
    images: List[ExtractedImage] = field(default_factory=list)
    tables: List[ExtractedTable] = field(default_factory=list)
    headings: Dict[str, List[str]] = field(default_factory=dict)  # h1, h2, etc.

    # Statistics
    word_count: int = 0
    reading_time_minutes: int = 0
    excerpt: Optional[str] = None  # First 200 chars

    # Raw data
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


class TrafilaturaParser:
    """
    Advanced parser using trafilatura with fallback strategies
    and comprehensive content extraction.
    """

    def __init__(
        self,
        include_comments: bool = False,
        include_tables: bool = True,
        include_images: bool = True,
        include_links: bool = True,
        favor_precision: bool = False,  # vs favor_recall
        deduplicate: bool = True,
        target_language: Optional[str] = None,
    ):
        """
        Initialize parser with configuration.

        Args:
            include_comments: Include comment sections
            include_tables: Extract tables
            include_images: Extract images
            include_links: Extract links
            favor_precision: Favor precision over recall in extraction
            deduplicate: Remove duplicate content
            target_language: Target language for extraction
        """
        self.include_comments = include_comments
        self.include_tables = include_tables
        self.include_images = include_images
        self.include_links = include_links
        self.favor_precision = favor_precision
        self.deduplicate = deduplicate
        self.target_language = target_language

    def parse(self, url: str, html: str) -> ParsedContent:
        """
        Parse HTML content and extract comprehensive information.

        Args:
            url: Source URL
            html: HTML content

        Returns:
            ParsedContent with all extracted information
        """
        # Extract with trafilatura
        text = self._extract_text(html)
        html_content = self._extract_html(html)
        metadata = self._extract_metadata(html, url)

        # Parse with BeautifulSoup for additional extraction
        soup = BeautifulSoup(html, "html.parser")

        # Extract structural elements
        links = self._extract_links(soup, url) if self.include_links else []
        images = self._extract_images(soup, url) if self.include_images else []
        tables = self._extract_tables(soup) if self.include_tables else []
        headings = self._extract_headings(soup)

        # Get title
        title = metadata.title or self._extract_title(soup) or ""

        # Calculate statistics
        word_count = len(text.split())
        reading_time = max(1, word_count // 200)  # Assume 200 words per minute
        excerpt = text[:200] + "..." if len(text) > 200 else text

        # Extract author and date
        author = metadata.author
        date = self._parse_date(metadata.date) if metadata.date else None

        # Build result
        result = ParsedContent(
            url=url,
            title=title,
            text=text,
            html=html_content,
            markdown=self._convert_to_markdown(html_content) if html_content else None,
            author=author,
            date=date,
            description=metadata.description or None,
            site_name=metadata.sitename or None,
            language=metadata.language or None,
            tags=metadata.tags or [],
            categories=metadata.categories or [],
            links=links,
            images=images,
            tables=tables,
            headings=headings,
            word_count=word_count,
            reading_time_minutes=reading_time,
            excerpt=excerpt,
            raw_metadata=self._metadata_to_dict(metadata),
        )

        return result

    def _extract_text(self, html: str) -> str:
        """Extract main text content using trafilatura."""
        text = trafilatura.extract(
            html,
            include_comments=self.include_comments,
            include_tables=self.include_tables,
            favor_recall=not self.favor_precision,
            deduplicate=self.deduplicate,
            target_language=self.target_language,
        )
        return text or ""

    def _extract_html(self, html: str) -> Optional[str]:
        """Extract clean HTML of main content."""
        html_content = trafilatura.extract(
            html,
            include_comments=self.include_comments,
            include_tables=self.include_tables,
            favor_recall=not self.favor_precision,
            deduplicate=self.deduplicate,
            target_language=self.target_language,
            output_format="html",
        )
        return html_content

    def _extract_metadata(self, html: str, url: str):
        """Extract metadata using trafilatura."""
        return extract_metadata(html, default_url=url)

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML."""
        # Try title tag first
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        # Try h1 tag
        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()

        return ""

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[ExtractedLink]:
        """Extract all links from the page."""
        links = []
        base_domain = urlparse(base_url).netloc

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#"):
                continue

            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)

            # Check if external
            link_domain = urlparse(absolute_url).netloc
            is_external = link_domain != base_domain

            link = ExtractedLink(
                url=absolute_url,
                text=a.get_text().strip() or "",
                title=a.get("title"),
                rel=a.get("rel", [None])[0] if isinstance(a.get("rel"), list) else a.get("rel"),
                is_external=is_external,
            )
            links.append(link)

        return links

    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[ExtractedImage]:
        """Extract all images from the page."""
        images = []

        for img in soup.find_all("img"):
            src = img.get("src", "").strip()
            if not src:
                continue

            # Resolve relative URLs
            absolute_url = urljoin(base_url, src)

            # Try to get dimensions
            width = None
            height = None
            try:
                if img.get("width"):
                    width = int(img["width"])
                if img.get("height"):
                    height = int(img["height"])
            except (ValueError, TypeError):
                pass

            # Try to find caption (check parent figure)
            caption = None
            parent = img.find_parent("figure")
            if parent:
                figcaption = parent.find("figcaption")
                if figcaption:
                    caption = figcaption.get_text().strip()

            image = ExtractedImage(
                url=absolute_url,
                alt=img.get("alt", "").strip() or None,
                title=img.get("title", "").strip() or None,
                width=width,
                height=height,
                caption=caption,
            )
            images.append(image)

        return images

    def _extract_tables(self, soup: BeautifulSoup) -> List[ExtractedTable]:
        """Extract all tables from the page."""
        tables = []

        for table in soup.find_all("table"):
            # Extract headers
            headers = []
            thead = table.find("thead")
            if thead:
                for th in thead.find_all("th"):
                    headers.append(th.get_text().strip())
            else:
                # Try first row
                first_row = table.find("tr")
                if first_row:
                    for th in first_row.find_all(["th", "td"]):
                        headers.append(th.get_text().strip())

            # Extract rows
            rows = []
            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr")[1 if not thead else 0:]:
                row = [td.get_text().strip() for td in tr.find_all(["td", "th"])]
                if row:  # Skip empty rows
                    rows.append(row)

            # Extract caption
            caption = None
            caption_elem = table.find("caption")
            if caption_elem:
                caption = caption_elem.get_text().strip()

            if headers or rows:
                tables.append(ExtractedTable(
                    headers=headers,
                    rows=rows,
                    caption=caption,
                ))

        return tables

    def _extract_headings(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract all headings organized by level."""
        headings = {}

        for level in range(1, 7):  # h1 to h6
            tag = f"h{level}"
            found = soup.find_all(tag)
            if found:
                headings[tag] = [h.get_text().strip() for h in found]

        return headings

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None

        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    def _convert_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown."""
        try:
            # Use trafilatura's markdown output
            result = trafilatura.extract(
                html,
                include_comments=self.include_comments,
                include_tables=self.include_tables,
                output_format="markdown",
            )
            return result or ""
        except Exception:
            return ""

    def _metadata_to_dict(self, metadata) -> Dict[str, Any]:
        """Convert metadata object to dictionary."""
        if not metadata:
            return {}

        result = {}
        for attr in dir(metadata):
            if not attr.startswith("_"):
                value = getattr(metadata, attr, None)
                if value and not callable(value):
                    result[attr] = value

        return result


def parse_html(url: str, html: str) -> Dict[str, Any]:
    """
    Convenience function for parsing HTML.
    Returns a dictionary representation of ParsedContent.

    Args:
        url: Source URL
        html: HTML content

    Returns:
        Dictionary with parsed content
    """
    parser = TrafilaturaParser()
    result = parser.parse(url, html)

    # Convert to dict for backward compatibility
    return {
        "url": result.url,
        "title": result.title,
        "text": result.text,
        "html": result.html,
        "markdown": result.markdown,
        "author": result.author,
        "date": result.date.isoformat() if result.date else None,
        "description": result.description,
        "site_name": result.site_name,
        "language": result.language,
        "tags": result.tags,
        "categories": result.categories,
        "links": [
            {
                "url": link.url,
                "text": link.text,
                "title": link.title,
                "rel": link.rel,
                "is_external": link.is_external,
            }
            for link in result.links
        ],
        "images": [
            {
                "url": img.url,
                "alt": img.alt,
                "title": img.title,
                "width": img.width,
                "height": img.height,
                "caption": img.caption,
            }
            for img in result.images
        ],
        "tables": [
            {
                "headers": table.headers,
                "rows": table.rows,
                "caption": table.caption,
            }
            for table in result.tables
        ],
        "headings": result.headings,
        "word_count": result.word_count,
        "reading_time_minutes": result.reading_time_minutes,
        "excerpt": result.excerpt,
        "metadata": result.raw_metadata,
    }
