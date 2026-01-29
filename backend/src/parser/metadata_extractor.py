"""
Comprehensive metadata extractor supporting:
- Open Graph (og:) tags
- Twitter Card (twitter:) tags
- Schema.org JSON-LD and microdata
- Standard HTML meta tags
- Dublin Core metadata
- Article-specific metadata
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


@dataclass
class OpenGraphMetadata:
    """Open Graph protocol metadata."""
    title: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
    site_name: Optional[str] = None
    locale: Optional[str] = None
    audio: Optional[str] = None
    video: Optional[str] = None
    determiner: Optional[str] = None
    # Article-specific
    article_author: Optional[str] = None
    article_section: Optional[str] = None
    article_tag: List[str] = field(default_factory=list)
    article_published_time: Optional[datetime] = None
    article_modified_time: Optional[datetime] = None
    # Additional properties
    additional: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TwitterCardMetadata:
    """Twitter Card metadata."""
    card: Optional[str] = None
    site: Optional[str] = None
    site_id: Optional[str] = None
    creator: Optional[str] = None
    creator_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    image_alt: Optional[str] = None
    player: Optional[str] = None
    player_width: Optional[int] = None
    player_height: Optional[int] = None
    # Additional properties
    additional: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaOrgData:
    """Schema.org structured data."""
    type: str  # @type
    data: Dict[str, Any]  # All properties
    context: Optional[str] = None  # @context


@dataclass
class PageMetadata:
    """Comprehensive page metadata."""
    # Basic HTML metadata
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    author: Optional[str] = None
    canonical_url: Optional[str] = None
    language: Optional[str] = None

    # Open Graph
    open_graph: Optional[OpenGraphMetadata] = None

    # Twitter Card
    twitter_card: Optional[TwitterCardMetadata] = None

    # Schema.org
    schema_org: List[SchemaOrgData] = field(default_factory=list)

    # Dublin Core
    dublin_core: Dict[str, Any] = field(default_factory=dict)

    # Feeds
    rss_feeds: List[Dict[str, str]] = field(default_factory=list)
    atom_feeds: List[Dict[str, str]] = field(default_factory=list)

    # Dates
    published_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None

    # SEO
    robots: Optional[str] = None
    googlebot: Optional[str] = None
    viewport: Optional[str] = None

    # Other
    generator: Optional[str] = None
    application_name: Optional[str] = None
    theme_color: Optional[str] = None

    # Raw data
    raw_meta_tags: List[Dict[str, str]] = field(default_factory=list)
    all_metadata: Dict[str, Any] = field(default_factory=dict)


class MetadataExtractor:
    """
    Comprehensive metadata extractor for web pages.
    Extracts Open Graph, Twitter Cards, Schema.org, and standard HTML metadata.
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize metadata extractor.

        Args:
            base_url: Base URL for resolving relative URLs
        """
        self.base_url = base_url

    def extract(self, html: str, url: Optional[str] = None) -> PageMetadata:
        """
        Extract all metadata from HTML.

        Args:
            html: HTML content
            url: Page URL (overrides base_url)

        Returns:
            PageMetadata with all extracted information
        """
        base_url = url or self.base_url
        soup = BeautifulSoup(html, "html.parser")

        # Extract different metadata types
        og = self._extract_open_graph(soup, base_url)
        twitter = self._extract_twitter_card(soup, base_url)
        schema = self._extract_schema_org(soup, base_url)
        dublin_core = self._extract_dublin_core(soup)

        # Extract basic HTML metadata
        title = self._extract_title(soup, og, twitter)
        description = self._extract_description(soup, og, twitter)
        keywords = self._extract_keywords(soup)
        author = self._extract_author(soup, og, dublin_core)
        canonical = self._extract_canonical(soup, base_url)
        language = self._extract_language(soup, og)

        # Extract dates
        published_date = self._extract_published_date(soup, og, schema)
        modified_date = self._extract_modified_date(soup, og, schema)

        # Extract feeds
        rss_feeds = self._extract_feeds(soup, "application/rss+xml", base_url)
        atom_feeds = self._extract_feeds(soup, "application/atom+xml", base_url)

        # Extract other metadata
        robots = self._get_meta_content(soup, "robots")
        googlebot = self._get_meta_content(soup, "googlebot")
        viewport = self._get_meta_content(soup, "viewport")
        generator = self._get_meta_content(soup, "generator")
        app_name = self._get_meta_content(soup, "application-name")
        theme_color = self._get_meta_content(soup, "theme-color")

        # Extract all raw meta tags
        raw_tags = self._extract_all_meta_tags(soup)

        # Build comprehensive metadata
        metadata = PageMetadata(
            title=title,
            description=description,
            keywords=keywords,
            author=author,
            canonical_url=canonical,
            language=language,
            open_graph=og,
            twitter_card=twitter,
            schema_org=schema,
            dublin_core=dublin_core,
            rss_feeds=rss_feeds,
            atom_feeds=atom_feeds,
            published_date=published_date,
            modified_date=modified_date,
            robots=robots,
            googlebot=googlebot,
            viewport=viewport,
            generator=generator,
            application_name=app_name,
            theme_color=theme_color,
            raw_meta_tags=raw_tags,
            all_metadata=self._build_all_metadata_dict(
                og, twitter, schema, dublin_core, raw_tags
            ),
        )

        return metadata

    def _extract_title(
        self,
        soup: BeautifulSoup,
        og: Optional[OpenGraphMetadata],
        twitter: Optional[TwitterCardMetadata]
    ) -> Optional[str]:
        """Extract title from various sources."""
        # Priority: OG > Twitter > title tag
        if og and og.title:
            return og.title
        if twitter and twitter.title:
            return twitter.title
        if soup.title:
            return soup.title.string.strip() if soup.title.string else None
        return None

    def _extract_description(
        self,
        soup: BeautifulSoup,
        og: Optional[OpenGraphMetadata],
        twitter: Optional[TwitterCardMetadata]
    ) -> Optional[str]:
        """Extract description from various sources."""
        # Priority: OG > Twitter > meta description
        if og and og.description:
            return og.description
        if twitter and twitter.description:
            return twitter.description
        return self._get_meta_content(soup, "description")

    def _extract_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract keywords from meta tags."""
        keywords_str = self._get_meta_content(soup, "keywords")
        if keywords_str:
            return [k.strip() for k in keywords_str.split(",") if k.strip()]
        return []

    def _extract_author(
        self,
        soup: BeautifulSoup,
        og: Optional[OpenGraphMetadata],
        dublin_core: Dict[str, Any]
    ) -> Optional[str]:
        """Extract author from various sources."""
        # Priority: OG article:author > DC creator > meta author
        if og and og.article_author:
            return og.article_author
        if "creator" in dublin_core:
            return dublin_core["creator"]
        return self._get_meta_content(soup, "author")

    def _extract_canonical(self, soup: BeautifulSoup, base_url: Optional[str]) -> Optional[str]:
        """Extract canonical URL."""
        link = soup.find("link", rel="canonical")
        if link and link.get("href"):
            url = link["href"].strip()
            if base_url:
                return urljoin(base_url, url)
            return url
        return None

    def _extract_language(
        self,
        soup: BeautifulSoup,
        og: Optional[OpenGraphMetadata]
    ) -> Optional[str]:
        """Extract language."""
        # Priority: OG locale > html lang > meta language
        if og and og.locale:
            return og.locale
        if soup.html and soup.html.get("lang"):
            return soup.html["lang"].strip()
        return self._get_meta_content(soup, "language")

    def _extract_open_graph(self, soup: BeautifulSoup, base_url: Optional[str]) -> OpenGraphMetadata:
        """Extract Open Graph metadata."""
        og = OpenGraphMetadata()

        # Find all og: meta tags
        og_tags = soup.find_all("meta", property=re.compile(r"^og:"))

        for tag in og_tags:
            property_name = tag.get("property", "")
            content = tag.get("content", "").strip()

            if not content:
                continue

            # Map to OpenGraphMetadata fields
            if property_name == "og:title":
                og.title = content
            elif property_name == "og:type":
                og.type = content
            elif property_name == "og:url":
                og.url = self._resolve_url(content, base_url)
            elif property_name == "og:image":
                og.image = self._resolve_url(content, base_url)
            elif property_name == "og:description":
                og.description = content
            elif property_name == "og:site_name":
                og.site_name = content
            elif property_name == "og:locale":
                og.locale = content
            elif property_name == "og:audio":
                og.audio = self._resolve_url(content, base_url)
            elif property_name == "og:video":
                og.video = self._resolve_url(content, base_url)
            elif property_name == "og:determiner":
                og.determiner = content
            elif property_name == "article:author":
                og.article_author = content
            elif property_name == "article:section":
                og.article_section = content
            elif property_name == "article:tag":
                og.article_tag.append(content)
            elif property_name == "article:published_time":
                og.article_published_time = self._parse_datetime(content)
            elif property_name == "article:modified_time":
                og.article_modified_time = self._parse_datetime(content)
            else:
                # Store additional properties
                key = property_name.replace("og:", "").replace("article:", "")
                og.additional[key] = content

        return og

    def _extract_twitter_card(self, soup: BeautifulSoup, base_url: Optional[str]) -> TwitterCardMetadata:
        """Extract Twitter Card metadata."""
        twitter = TwitterCardMetadata()

        # Find all twitter: meta tags
        twitter_tags = soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")})

        for tag in twitter_tags:
            name = tag.get("name", "")
            content = tag.get("content", "").strip()

            if not content:
                continue

            # Map to TwitterCardMetadata fields
            if name == "twitter:card":
                twitter.card = content
            elif name == "twitter:site":
                twitter.site = content
            elif name == "twitter:site:id":
                twitter.site_id = content
            elif name == "twitter:creator":
                twitter.creator = content
            elif name == "twitter:creator:id":
                twitter.creator_id = content
            elif name == "twitter:title":
                twitter.title = content
            elif name == "twitter:description":
                twitter.description = content
            elif name == "twitter:image":
                twitter.image = self._resolve_url(content, base_url)
            elif name == "twitter:image:alt":
                twitter.image_alt = content
            elif name == "twitter:player":
                twitter.player = self._resolve_url(content, base_url)
            elif name == "twitter:player:width":
                try:
                    twitter.player_width = int(content)
                except ValueError:
                    pass
            elif name == "twitter:player:height":
                try:
                    twitter.player_height = int(content)
                except ValueError:
                    pass
            else:
                # Store additional properties
                key = name.replace("twitter:", "")
                twitter.additional[key] = content

        return twitter

    def _extract_schema_org(self, soup: BeautifulSoup, base_url: Optional[str]) -> List[SchemaOrgData]:
        """Extract Schema.org JSON-LD structured data."""
        schema_list = []

        # Find all JSON-LD scripts
        scripts = soup.find_all("script", type="application/ld+json")

        for script in scripts:
            try:
                data = json.loads(script.string)

                # Handle array of items
                if isinstance(data, list):
                    for item in data:
                        schema_list.append(self._parse_schema_item(item))
                elif isinstance(data, dict):
                    schema_list.append(self._parse_schema_item(data))

            except (json.JSONDecodeError, AttributeError):
                continue

        return schema_list

    def _parse_schema_item(self, item: Dict[str, Any]) -> SchemaOrgData:
        """Parse a single Schema.org item."""
        return SchemaOrgData(
            type=item.get("@type", "Unknown"),
            context=item.get("@context"),
            data=item,
        )

    def _extract_dublin_core(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract Dublin Core metadata."""
        dc = {}

        # Find all DC meta tags
        dc_tags = soup.find_all("meta", attrs={"name": re.compile(r"^DC\.|^dc\.")})

        for tag in dc_tags:
            name = tag.get("name", "")
            content = tag.get("content", "").strip()

            if content:
                # Normalize key (remove DC. prefix)
                key = re.sub(r"^DC\.|^dc\.", "", name, flags=re.IGNORECASE)
                dc[key] = content

        return dc

    def _extract_feeds(
        self,
        soup: BeautifulSoup,
        feed_type: str,
        base_url: Optional[str]
    ) -> List[Dict[str, str]]:
        """Extract RSS/Atom feed links."""
        feeds = []
        links = soup.find_all("link", type=feed_type)

        for link in links:
            href = link.get("href", "").strip()
            if href:
                feeds.append({
                    "url": self._resolve_url(href, base_url),
                    "title": link.get("title", "").strip() or None,
                })

        return feeds

    def _extract_published_date(
        self,
        soup: BeautifulSoup,
        og: Optional[OpenGraphMetadata],
        schema: List[SchemaOrgData]
    ) -> Optional[datetime]:
        """Extract published date from various sources."""
        # Priority: OG article:published_time > Schema.org > meta
        if og and og.article_published_time:
            return og.article_published_time

        # Check Schema.org
        for item in schema:
            if "datePublished" in item.data:
                dt = self._parse_datetime(item.data["datePublished"])
                if dt:
                    return dt

        # Check meta tags
        date_str = self._get_meta_content(soup, "article:published_time")
        if date_str:
            return self._parse_datetime(date_str)

        return None

    def _extract_modified_date(
        self,
        soup: BeautifulSoup,
        og: Optional[OpenGraphMetadata],
        schema: List[SchemaOrgData]
    ) -> Optional[datetime]:
        """Extract modified date from various sources."""
        # Priority: OG article:modified_time > Schema.org > meta
        if og and og.article_modified_time:
            return og.article_modified_time

        # Check Schema.org
        for item in schema:
            if "dateModified" in item.data:
                dt = self._parse_datetime(item.data["dateModified"])
                if dt:
                    return dt

        # Check meta tags
        date_str = self._get_meta_content(soup, "article:modified_time")
        if date_str:
            return self._parse_datetime(date_str)

        return None

    def _extract_all_meta_tags(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract all meta tags as raw data."""
        tags = []

        for meta in soup.find_all("meta"):
            tag_data = {}

            # Get all attributes
            for attr, value in meta.attrs.items():
                if isinstance(value, list):
                    tag_data[attr] = ", ".join(value)
                else:
                    tag_data[attr] = str(value)

            if tag_data:
                tags.append(tag_data)

        return tags

    def _build_all_metadata_dict(
        self,
        og: Optional[OpenGraphMetadata],
        twitter: Optional[TwitterCardMetadata],
        schema: List[SchemaOrgData],
        dublin_core: Dict[str, Any],
        raw_tags: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Build a comprehensive metadata dictionary."""
        result = {}

        if og:
            result["open_graph"] = {
                k: v for k, v in og.__dict__.items()
                if v and not k.startswith("_")
            }

        if twitter:
            result["twitter_card"] = {
                k: v for k, v in twitter.__dict__.items()
                if v and not k.startswith("_")
            }

        if schema:
            result["schema_org"] = [item.data for item in schema]

        if dublin_core:
            result["dublin_core"] = dublin_core

        result["raw_meta_tags"] = raw_tags

        return result

    def _get_meta_content(self, soup: BeautifulSoup, name: str) -> Optional[str]:
        """Get content from a meta tag by name or property."""
        # Try name attribute
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag["content"].strip()

        # Try property attribute
        tag = soup.find("meta", attrs={"property": name})
        if tag and tag.get("content"):
            return tag["content"].strip()

        return None

    def _resolve_url(self, url: str, base_url: Optional[str]) -> str:
        """Resolve relative URL to absolute."""
        if not base_url or url.startswith(("http://", "https://", "//")):
            return url
        return urljoin(base_url, url)

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string."""
        if not date_str:
            return None

        try:
            # Try ISO format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

        # Try common formats
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None


def extract_metadata(html: str, url: Optional[str] = None) -> PageMetadata:
    """
    Convenience function to extract all metadata from HTML.

    Args:
        html: HTML content
        url: Page URL

    Returns:
        PageMetadata with all extracted information
    """
    extractor = MetadataExtractor(base_url=url)
    return extractor.extract(html, url)
