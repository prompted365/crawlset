"""
Specialized parser for podcast episodes and RSS feeds.
Extracts episode metadata, transcripts, show notes, and audio information.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup


@dataclass
class PodcastEpisode:
    """Represents a podcast episode."""
    # Basic info
    title: str
    url: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None

    # Audio
    audio_url: Optional[str] = None
    audio_type: Optional[str] = None
    audio_length: Optional[int] = None  # bytes
    duration: Optional[int] = None  # seconds

    # Metadata
    episode_number: Optional[int] = None
    season_number: Optional[int] = None
    episode_type: Optional[str] = None  # full, trailer, bonus
    published_date: Optional[datetime] = None
    guid: Optional[str] = None

    # People
    author: Optional[str] = None
    hosts: List[str] = field(default_factory=list)
    guests: List[str] = field(default_factory=list)

    # Content
    show_notes: Optional[str] = None
    transcript: Optional[str] = None
    chapters: List[Dict[str, Any]] = field(default_factory=list)

    # Media
    image_url: Optional[str] = None
    video_url: Optional[str] = None

    # Categorization
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    explicit: bool = False

    # Links
    links: List[Dict[str, str]] = field(default_factory=list)

    # Raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PodcastShow:
    """Represents a podcast show/series."""
    title: str
    url: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    image_url: Optional[str] = None
    language: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    explicit: bool = False
    copyright: Optional[str] = None
    episodes: List[PodcastEpisode] = field(default_factory=list)


class PodcastParser:
    """
    Specialized parser for podcast content:
    - RSS/Atom feeds (with iTunes/Spotify podcast extensions)
    - Individual episode pages
    - Show notes and transcripts
    """

    def __init__(self):
        """Initialize podcast parser."""
        pass

    def parse_rss_feed(self, xml: str, feed_url: Optional[str] = None) -> PodcastShow:
        """
        Parse podcast RSS feed.

        Args:
            xml: RSS XML content
            feed_url: URL of the feed

        Returns:
            PodcastShow with episodes
        """
        root = ET.fromstring(xml)

        # Handle different namespaces
        namespaces = {
            "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
            "spotify": "http://www.spotify.com/ns/rss",
            "podcast": "https://podcastindex.org/namespace/1.0",
            "content": "http://purl.org/rss/1.0/modules/content/",
            "atom": "http://www.w3.org/2005/Atom",
        }

        # Get channel (show) info
        channel = root.find("channel")
        if not channel:
            raise ValueError("Invalid RSS feed: no channel element")

        show = PodcastShow(
            title=self._get_text(channel, "title"),
            url=feed_url or self._get_text(channel, "link"),
            description=self._get_text(channel, "description"),
            author=self._get_text_ns(channel, "itunes:author", namespaces),
            image_url=self._get_podcast_image(channel, namespaces),
            language=self._get_text(channel, "language"),
            categories=self._get_categories(channel, namespaces),
            explicit=self._is_explicit(channel, namespaces),
            copyright=self._get_text(channel, "copyright"),
        )

        # Parse episodes
        for item in channel.findall("item"):
            episode = self._parse_episode(item, namespaces, feed_url)
            if episode:
                show.episodes.append(episode)

        return show

    def parse_episode_page(self, html: str, url: Optional[str] = None) -> PodcastEpisode:
        """
        Parse individual podcast episode page.

        Args:
            html: HTML content
            url: Page URL

        Returns:
            PodcastEpisode
        """
        soup = BeautifulSoup(html, "html.parser")

        # Extract basic info
        title = self._extract_title(soup)
        description = self._extract_description(soup)

        # Extract audio player info
        audio_url = self._extract_audio_url(soup, url)

        # Extract metadata
        published_date = self._extract_published_date(soup)
        duration = self._extract_duration(soup)

        # Extract show notes
        show_notes = self._extract_show_notes(soup)

        # Extract transcript
        transcript = self._extract_transcript(soup)

        # Extract links
        links = self._extract_links(soup, url)

        # Extract people (hosts/guests)
        hosts, guests = self._extract_people(soup)

        episode = PodcastEpisode(
            title=title,
            url=url,
            description=description,
            audio_url=audio_url,
            duration=duration,
            published_date=published_date,
            show_notes=show_notes,
            transcript=transcript,
            links=links,
            hosts=hosts,
            guests=guests,
        )

        return episode

    def _parse_episode(
        self,
        item: ET.Element,
        namespaces: Dict[str, str],
        base_url: Optional[str]
    ) -> Optional[PodcastEpisode]:
        """Parse episode from RSS item."""
        title = self._get_text(item, "title")
        if not title:
            return None

        # Get enclosure (audio file)
        enclosure = item.find("enclosure")
        audio_url = None
        audio_type = None
        audio_length = None

        if enclosure is not None:
            audio_url = enclosure.get("url")
            audio_type = enclosure.get("type")
            length_str = enclosure.get("length")
            if length_str:
                try:
                    audio_length = int(length_str)
                except ValueError:
                    pass

        # Get episode metadata
        episode = PodcastEpisode(
            title=title,
            url=self._get_text(item, "link"),
            description=self._get_text_ns(item, "content:encoded", namespaces) or self._get_text(item, "description"),
            summary=self._get_text_ns(item, "itunes:summary", namespaces),
            audio_url=audio_url,
            audio_type=audio_type,
            audio_length=audio_length,
            duration=self._parse_duration(self._get_text_ns(item, "itunes:duration", namespaces)),
            episode_number=self._parse_int(self._get_text_ns(item, "itunes:episode", namespaces)),
            season_number=self._parse_int(self._get_text_ns(item, "itunes:season", namespaces)),
            episode_type=self._get_text_ns(item, "itunes:episodeType", namespaces),
            published_date=self._parse_date(self._get_text(item, "pubDate")),
            guid=self._get_text(item, "guid"),
            author=self._get_text_ns(item, "itunes:author", namespaces),
            image_url=self._get_episode_image(item, namespaces),
            keywords=self._get_keywords(item, namespaces),
            explicit=self._is_explicit(item, namespaces),
        )

        # Extract chapters if available
        chapters = self._extract_chapters(item, namespaces)
        if chapters:
            episode.chapters = chapters

        return episode

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract episode title from HTML."""
        # Try various selectors
        selectors = [
            "h1.episode-title",
            "h1[itemprop='name']",
            ".episode-header h1",
            "h1",
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text().strip()

        # Fallback to page title
        if soup.title:
            return soup.title.string.strip()

        return "Unknown Episode"

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract episode description from HTML."""
        # Try meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        # Try OG description
        meta = soup.find("meta", attrs={"property": "og:description"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        return None

    def _extract_audio_url(self, soup: BeautifulSoup, base_url: Optional[str]) -> Optional[str]:
        """Extract audio URL from HTML."""
        # Try audio tag
        audio = soup.find("audio")
        if audio:
            source = audio.find("source")
            if source and source.get("src"):
                url = source["src"]
                if base_url:
                    url = urljoin(base_url, url)
                return url

        # Try data attributes
        for attr in ["data-audio-url", "data-src", "data-episode-url"]:
            elem = soup.find(attrs={attr: True})
            if elem:
                url = elem[attr]
                if base_url:
                    url = urljoin(base_url, url)
                return url

        return None

    def _extract_published_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract published date from HTML."""
        # Try time tag
        time_tag = soup.find("time", attrs={"datetime": True})
        if time_tag:
            return self._parse_date(time_tag["datetime"])

        # Try meta tag
        meta = soup.find("meta", attrs={"property": "article:published_time"})
        if meta and meta.get("content"):
            return self._parse_date(meta["content"])

        return None

    def _extract_duration(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract duration from HTML."""
        # Look for duration in various formats
        duration_elem = soup.find(attrs={"itemprop": "duration"})
        if duration_elem:
            content = duration_elem.get("content") or duration_elem.get_text()
            return self._parse_duration(content)

        # Look for time display (e.g., "1:23:45")
        time_pattern = re.compile(r'(\d+):(\d+):(\d+)|(\d+):(\d+)')
        for elem in soup.find_all(text=time_pattern):
            match = time_pattern.search(elem)
            if match:
                return self._parse_duration(match.group(0))

        return None

    def _extract_show_notes(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract show notes from HTML."""
        # Try various selectors
        selectors = [
            ".show-notes",
            ".episode-description",
            "#show-notes",
            "[itemprop='description']",
            ".entry-content",
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text().strip()

        return None

    def _extract_transcript(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract transcript from HTML."""
        # Try various selectors
        selectors = [
            ".transcript",
            "#transcript",
            ".episode-transcript",
            "[itemprop='transcript']",
        ]

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get_text().strip()

        return None

    def _extract_links(self, soup: BeautifulSoup, base_url: Optional[str]) -> List[Dict[str, str]]:
        """Extract links from show notes."""
        links = []

        # Find show notes section
        show_notes = soup.select_one(".show-notes, .episode-description, .entry-content")
        if not show_notes:
            return links

        # Extract all links from show notes
        for a in show_notes.find_all("a", href=True):
            url = a["href"]
            if base_url:
                url = urljoin(base_url, url)

            links.append({
                "url": url,
                "text": a.get_text().strip(),
                "title": a.get("title", ""),
            })

        return links

    def _extract_people(self, soup: BeautifulSoup) -> tuple[List[str], List[str]]:
        """Extract hosts and guests from HTML."""
        hosts = []
        guests = []

        # Look for host information
        host_elem = soup.select_one(".hosts, .host, [itemprop='author']")
        if host_elem:
            # Try to split by commas or line breaks
            host_text = host_elem.get_text()
            hosts = [h.strip() for h in re.split(r'[,\n]', host_text) if h.strip()]

        # Look for guest information
        guest_elem = soup.select_one(".guests, .guest")
        if guest_elem:
            guest_text = guest_elem.get_text()
            guests = [g.strip() for g in re.split(r'[,\n]', guest_text) if g.strip()]

        return hosts, guests

    def _get_text(self, elem: ET.Element, tag: str) -> Optional[str]:
        """Get text from XML element."""
        child = elem.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None

    def _get_text_ns(self, elem: ET.Element, tag: str, namespaces: Dict[str, str]) -> Optional[str]:
        """Get text from namespaced XML element."""
        # Parse namespace from tag
        if ":" in tag:
            ns_prefix, local_tag = tag.split(":", 1)
            if ns_prefix in namespaces:
                full_tag = f"{{{namespaces[ns_prefix]}}}{local_tag}"
                child = elem.find(full_tag)
                if child is not None and child.text:
                    return child.text.strip()
        return None

    def _get_podcast_image(self, elem: ET.Element, namespaces: Dict[str, str]) -> Optional[str]:
        """Get podcast image URL."""
        # Try iTunes image
        itunes_image = elem.find(f"{{{namespaces['itunes']}}}image")
        if itunes_image is not None:
            return itunes_image.get("href")

        # Try standard image
        image = elem.find("image")
        if image is not None:
            url = image.find("url")
            if url is not None and url.text:
                return url.text.strip()

        return None

    def _get_episode_image(self, elem: ET.Element, namespaces: Dict[str, str]) -> Optional[str]:
        """Get episode image URL."""
        return self._get_podcast_image(elem, namespaces)

    def _get_categories(self, elem: ET.Element, namespaces: Dict[str, str]) -> List[str]:
        """Get categories from iTunes tags."""
        categories = []

        # iTunes categories
        for cat in elem.findall(f"{{{namespaces['itunes']}}}category"):
            text = cat.get("text")
            if text:
                categories.append(text)

        return categories

    def _get_keywords(self, elem: ET.Element, namespaces: Dict[str, str]) -> List[str]:
        """Get keywords from iTunes tags."""
        keywords_text = self._get_text_ns(elem, "itunes:keywords", namespaces)
        if keywords_text:
            return [k.strip() for k in keywords_text.split(",") if k.strip()]
        return []

    def _is_explicit(self, elem: ET.Element, namespaces: Dict[str, str]) -> bool:
        """Check if content is explicit."""
        explicit = self._get_text_ns(elem, "itunes:explicit", namespaces)
        return explicit and explicit.lower() in ("yes", "true", "explicit")

    def _extract_chapters(self, elem: ET.Element, namespaces: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract chapter markers."""
        # This would require podcast namespace support
        # Simplified implementation
        return []

    def _parse_duration(self, duration_str: Optional[str]) -> Optional[int]:
        """Parse duration string to seconds."""
        if not duration_str:
            return None

        # Try HH:MM:SS format
        time_pattern = re.match(r'(?:(\d+):)?(\d+):(\d+)', duration_str.strip())
        if time_pattern:
            groups = time_pattern.groups()
            hours = int(groups[0]) if groups[0] else 0
            minutes = int(groups[1])
            seconds = int(groups[2])
            return hours * 3600 + minutes * 60 + seconds

        # Try seconds only
        try:
            return int(duration_str)
        except ValueError:
            return None

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string."""
        if not date_str:
            return None

        # Try ISO format
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

        # Try RFC 2822 (RSS pubDate format)
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            pass

        return None

    def _parse_int(self, value: Optional[str]) -> Optional[int]:
        """Parse integer from string."""
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None


def parse_podcast_feed(xml: str, feed_url: Optional[str] = None) -> PodcastShow:
    """
    Convenience function to parse podcast RSS feed.

    Args:
        xml: RSS XML content
        feed_url: URL of the feed

    Returns:
        PodcastShow with episodes
    """
    parser = PodcastParser()
    return parser.parse_rss_feed(xml, feed_url)


def parse_podcast_episode(html: str, url: Optional[str] = None) -> PodcastEpisode:
    """
    Convenience function to parse podcast episode page.

    Args:
        html: HTML content
        url: Page URL

    Returns:
        PodcastEpisode
    """
    parser = PodcastParser()
    return parser.parse_episode_page(html, url)
