"""
Content parsing module with specialized parsers.
"""
from .citation_tracker import (
    Citation,
    CitationCollection,
    CitationTracker,
    track_citations,
)
from .metadata_extractor import (
    MetadataExtractor,
    OpenGraphMetadata,
    PageMetadata,
    SchemaOrgData,
    TwitterCardMetadata,
    extract_metadata,
)
from .podcast_parser import (
    PodcastEpisode,
    PodcastParser,
    PodcastShow,
    parse_podcast_episode,
    parse_podcast_feed,
)
from .trafilatura_parser import (
    ExtractedImage,
    ExtractedLink,
    ExtractedTable,
    ParsedContent,
    TrafilaturaParser,
    parse_html,
)

__all__ = [
    # Trafilatura Parser
    "ExtractedImage",
    "ExtractedLink",
    "ExtractedTable",
    "ParsedContent",
    "TrafilaturaParser",
    "parse_html",
    # Metadata Extractor
    "MetadataExtractor",
    "OpenGraphMetadata",
    "PageMetadata",
    "SchemaOrgData",
    "TwitterCardMetadata",
    "extract_metadata",
    # Citation Tracker
    "Citation",
    "CitationCollection",
    "CitationTracker",
    "track_citations",
    # Podcast Parser
    "PodcastEpisode",
    "PodcastParser",
    "PodcastShow",
    "parse_podcast_episode",
    "parse_podcast_feed",
]
