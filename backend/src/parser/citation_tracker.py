"""
Citation tracker to track and extract citations from web content using XPath and CSS selectors.
Supports multiple citation formats and provides provenance tracking.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from lxml import etree, html as lxml_html


@dataclass
class Citation:
    """Represents a citation or reference."""
    # Identification
    id: str  # Unique identifier
    type: str  # Type: 'text', 'link', 'blockquote', 'figure', etc.

    # Content
    text: str  # Citation text
    html: Optional[str] = None  # Original HTML

    # Location
    xpath: Optional[str] = None  # XPath to element
    css_selector: Optional[str] = None  # CSS selector
    position: Optional[int] = None  # Position in document

    # Context
    context_before: Optional[str] = None  # Text before citation
    context_after: Optional[str] = None  # Text after citation
    parent_text: Optional[str] = None  # Parent element text

    # Source information
    source_url: Optional[str] = None  # Link URL if applicable
    source_title: Optional[str] = None  # Link title/alt text
    source_author: Optional[str] = None  # Author if available

    # Metadata
    attributes: Dict[str, str] = field(default_factory=dict)  # HTML attributes
    tags: Set[str] = field(default_factory=set)  # Classification tags
    confidence: float = 1.0  # Confidence score (0-1)

    # Temporal
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CitationCollection:
    """Collection of citations from a document."""
    url: str
    citations: List[Citation] = field(default_factory=list)
    citation_index: Dict[str, Citation] = field(default_factory=dict)  # id -> citation
    total_count: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)  # type -> count

    def add(self, citation: Citation):
        """Add a citation to the collection."""
        self.citations.append(citation)
        self.citation_index[citation.id] = citation
        self.total_count += 1
        self.by_type[citation.type] = self.by_type.get(citation.type, 0) + 1

    def get_by_type(self, citation_type: str) -> List[Citation]:
        """Get all citations of a specific type."""
        return [c for c in self.citations if c.type == citation_type]

    def get_by_tag(self, tag: str) -> List[Citation]:
        """Get all citations with a specific tag."""
        return [c for c in self.citations if tag in c.tags]


class CitationTracker:
    """
    Track and extract citations from HTML content using XPath and CSS selectors.
    """

    def __init__(
        self,
        extract_blockquotes: bool = True,
        extract_links: bool = True,
        extract_figures: bool = True,
        extract_lists: bool = True,
        extract_code: bool = True,
        context_chars: int = 100,
    ):
        """
        Initialize citation tracker.

        Args:
            extract_blockquotes: Extract blockquote elements as citations
            extract_links: Extract links as citations
            extract_figures: Extract figure elements as citations
            extract_lists: Extract list items as citations
            extract_code: Extract code blocks as citations
            context_chars: Number of characters to extract for context
        """
        self.extract_blockquotes = extract_blockquotes
        self.extract_links = extract_links
        self.extract_figures = extract_figures
        self.extract_lists = extract_lists
        self.extract_code = extract_code
        self.context_chars = context_chars

    def track(self, html: str, url: Optional[str] = None) -> CitationCollection:
        """
        Extract all citations from HTML content.

        Args:
            html: HTML content
            url: Source URL

        Returns:
            CitationCollection with all extracted citations
        """
        collection = CitationCollection(url=url or "")

        # Parse with BeautifulSoup and lxml
        soup = BeautifulSoup(html, "html.parser")
        tree = lxml_html.fromstring(html)

        position = 0

        # Extract blockquotes
        if self.extract_blockquotes:
            for elem in soup.find_all("blockquote"):
                citation = self._extract_blockquote(elem, tree, url, position)
                if citation:
                    collection.add(citation)
                    position += 1

        # Extract figures
        if self.extract_figures:
            for elem in soup.find_all("figure"):
                citation = self._extract_figure(elem, tree, url, position)
                if citation:
                    collection.add(citation)
                    position += 1

        # Extract links (selective - only those that look like citations)
        if self.extract_links:
            for elem in soup.find_all("a", href=True):
                citation = self._extract_link(elem, tree, url, position)
                if citation:
                    collection.add(citation)
                    position += 1

        # Extract code blocks
        if self.extract_code:
            for elem in soup.find_all(["pre", "code"]):
                citation = self._extract_code(elem, tree, url, position)
                if citation:
                    collection.add(citation)
                    position += 1

        # Extract special citation patterns (e.g., [1], (Smith 2020), etc.)
        inline_citations = self._extract_inline_citations(soup, tree, url)
        for citation in inline_citations:
            collection.add(citation)

        return collection

    def _extract_blockquote(
        self,
        elem: Tag,
        tree: etree.Element,
        url: Optional[str],
        position: int
    ) -> Optional[Citation]:
        """Extract citation from blockquote element."""
        text = elem.get_text().strip()
        if not text:
            return None

        # Get cite attribute if present
        cite_url = elem.get("cite")
        if cite_url and url:
            cite_url = urljoin(url, cite_url)

        # Get author from footer or cite element
        author = None
        footer = elem.find("footer")
        if footer:
            author = footer.get_text().strip()
        else:
            cite_elem = elem.find("cite")
            if cite_elem:
                author = cite_elem.get_text().strip()

        # Get XPath
        xpath = self._get_xpath(elem, tree)

        # Get context
        context_before, context_after = self._get_context(elem)

        citation = Citation(
            id=self._generate_id(text, position),
            type="blockquote",
            text=text,
            html=str(elem),
            xpath=xpath,
            css_selector=self._get_css_selector(elem),
            position=position,
            context_before=context_before,
            context_after=context_after,
            source_url=cite_url,
            source_author=author,
            attributes=dict(elem.attrs),
            tags={"quote", "citation"},
        )

        return citation

    def _extract_figure(
        self,
        elem: Tag,
        tree: etree.Element,
        url: Optional[str],
        position: int
    ) -> Optional[Citation]:
        """Extract citation from figure element."""
        # Get caption
        caption = elem.find("figcaption")
        caption_text = caption.get_text().strip() if caption else ""

        # Get image or other content
        img = elem.find("img")
        if img:
            img_url = img.get("src", "")
            if img_url and url:
                img_url = urljoin(url, img_url)
            alt_text = img.get("alt", "")

            text = f"{alt_text}\n{caption_text}".strip()
            source_url = img_url
        else:
            text = caption_text
            source_url = None

        if not text:
            return None

        citation = Citation(
            id=self._generate_id(text, position),
            type="figure",
            text=text,
            html=str(elem),
            xpath=self._get_xpath(elem, tree),
            css_selector=self._get_css_selector(elem),
            position=position,
            source_url=source_url,
            attributes=dict(elem.attrs),
            tags={"figure", "visual"},
        )

        return citation

    def _extract_link(
        self,
        elem: Tag,
        tree: etree.Element,
        url: Optional[str],
        position: int
    ) -> Optional[Citation]:
        """Extract citation from link element if it looks like a citation."""
        href = elem.get("href", "").strip()
        text = elem.get_text().strip()
        title = elem.get("title", "")

        # Only extract links that look like citations
        # Skip navigation, social media, etc.
        if not text or len(text) < 5:
            return None

        # Check for citation-like patterns
        is_citation = (
            elem.find_parent(["blockquote", "cite", "q"]) or
            "cite" in elem.get("class", []) or
            "reference" in elem.get("class", []) or
            "source" in elem.get("class", []) or
            re.search(r"\[\d+\]|\(\d{4}\)", text)  # [1] or (2020) patterns
        )

        if not is_citation:
            return None

        # Resolve URL
        if href and url:
            href = urljoin(url, href)

        # Get context
        context_before, context_after = self._get_context(elem)

        citation = Citation(
            id=self._generate_id(text, position),
            type="link",
            text=text,
            html=str(elem),
            xpath=self._get_xpath(elem, tree),
            css_selector=self._get_css_selector(elem),
            position=position,
            context_before=context_before,
            context_after=context_after,
            source_url=href,
            source_title=title,
            attributes=dict(elem.attrs),
            tags={"link", "citation"},
        )

        return citation

    def _extract_code(
        self,
        elem: Tag,
        tree: etree.Element,
        url: Optional[str],
        position: int
    ) -> Optional[Citation]:
        """Extract citation from code block."""
        text = elem.get_text().strip()
        if not text or len(text) < 10:
            return None

        # Determine language
        language = None
        if elem.get("class"):
            for cls in elem["class"]:
                if cls.startswith("language-"):
                    language = cls.replace("language-", "")
                    break

        citation = Citation(
            id=self._generate_id(text, position),
            type="code",
            text=text,
            html=str(elem),
            xpath=self._get_xpath(elem, tree),
            css_selector=self._get_css_selector(elem),
            position=position,
            attributes=dict(elem.attrs),
            tags={"code"},
        )

        if language:
            citation.tags.add(f"lang:{language}")

        return citation

    def _extract_inline_citations(
        self,
        soup: BeautifulSoup,
        tree: etree.Element,
        url: Optional[str]
    ) -> List[Citation]:
        """Extract inline citation patterns like [1], (Smith 2020), etc."""
        citations = []

        # Find text nodes with citation patterns
        text_content = soup.get_text()

        # Pattern: [1], [2], etc.
        bracket_citations = re.finditer(r'\[(\d+)\]', text_content)
        for match in bracket_citations:
            citation_text = match.group(0)
            citation_number = match.group(1)

            citation = Citation(
                id=self._generate_id(citation_text, match.start()),
                type="inline_reference",
                text=citation_text,
                position=match.start(),
                attributes={"number": citation_number},
                tags={"inline", "numbered"},
            )
            citations.append(citation)

        # Pattern: (Author Year) or (Author et al. Year)
        author_year_citations = re.finditer(
            r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?)\s+(\d{4}[a-z]?)\)',
            text_content
        )
        for match in author_year_citations:
            citation_text = match.group(0)
            author = match.group(1)
            year = match.group(2)

            citation = Citation(
                id=self._generate_id(citation_text, match.start()),
                type="inline_author_year",
                text=citation_text,
                position=match.start(),
                source_author=author,
                attributes={"author": author, "year": year},
                tags={"inline", "author-year"},
            )
            citations.append(citation)

        return citations

    def _get_xpath(self, elem: Tag, tree: etree.Element) -> Optional[str]:
        """Generate XPath for an element."""
        try:
            # Find element in lxml tree by matching text content
            text = elem.get_text()[:50]  # Use first 50 chars as identifier
            if not text.strip():
                return None

            # This is a simplified approach - in production, use a better matching strategy
            for node in tree.iter():
                if node.text and text in node.text:
                    return tree.getpath(node)
        except Exception:
            pass
        return None

    def _get_css_selector(self, elem: Tag) -> Optional[str]:
        """Generate CSS selector for an element."""
        try:
            # Build selector from tag, id, and classes
            selector_parts = [elem.name]

            if elem.get("id"):
                selector_parts.append(f"#{elem['id']}")

            if elem.get("class"):
                classes = elem["class"]
                if isinstance(classes, list):
                    for cls in classes[:3]:  # Limit to first 3 classes
                        selector_parts.append(f".{cls}")

            return "".join(selector_parts)
        except Exception:
            return None

    def _get_context(self, elem: Tag) -> tuple[Optional[str], Optional[str]]:
        """Get text context before and after an element."""
        try:
            # Get all text from parent
            parent = elem.parent
            if not parent:
                return None, None

            parent_text = parent.get_text()
            elem_text = elem.get_text()

            # Find element position in parent text
            elem_pos = parent_text.find(elem_text)
            if elem_pos == -1:
                return None, None

            # Extract context
            before_start = max(0, elem_pos - self.context_chars)
            before = parent_text[before_start:elem_pos].strip()

            after_end = min(len(parent_text), elem_pos + len(elem_text) + self.context_chars)
            after = parent_text[elem_pos + len(elem_text):after_end].strip()

            return before or None, after or None

        except Exception:
            return None, None

    def _generate_id(self, text: str, position: int) -> str:
        """Generate unique ID for a citation."""
        # Use hash of text + position for uniqueness
        content = f"{text[:100]}{position}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def extract_with_selector(
        self,
        html: str,
        selector: str,
        selector_type: str = "css",
        url: Optional[str] = None
    ) -> List[Citation]:
        """
        Extract citations using a custom CSS or XPath selector.

        Args:
            html: HTML content
            selector: CSS selector or XPath expression
            selector_type: "css" or "xpath"
            url: Source URL

        Returns:
            List of Citation objects
        """
        citations = []

        if selector_type == "css":
            soup = BeautifulSoup(html, "html.parser")
            elements = soup.select(selector)

            for i, elem in enumerate(elements):
                text = elem.get_text().strip()
                if not text:
                    continue

                citation = Citation(
                    id=self._generate_id(text, i),
                    type="custom",
                    text=text,
                    html=str(elem),
                    css_selector=selector,
                    position=i,
                    attributes=dict(elem.attrs),
                    tags={"custom"},
                )
                citations.append(citation)

        elif selector_type == "xpath":
            tree = lxml_html.fromstring(html)
            elements = tree.xpath(selector)

            for i, elem in enumerate(elements):
                if isinstance(elem, str):
                    text = elem
                    elem_html = None
                else:
                    text = elem.text_content().strip()
                    elem_html = etree.tostring(elem, encoding="unicode")

                if not text:
                    continue

                citation = Citation(
                    id=self._generate_id(text, i),
                    type="custom",
                    text=text,
                    html=elem_html,
                    xpath=selector,
                    position=i,
                    tags={"custom"},
                )
                citations.append(citation)

        return citations


def track_citations(html: str, url: Optional[str] = None) -> CitationCollection:
    """
    Convenience function to track citations in HTML.

    Args:
        html: HTML content
        url: Source URL

    Returns:
        CitationCollection with all extracted citations
    """
    tracker = CitationTracker()
    return tracker.track(html, url)
