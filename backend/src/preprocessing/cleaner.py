"""
Content cleaning utilities for text preprocessing.

Provides:
- Boilerplate removal (navigation, footers, ads)
- Text normalization (whitespace, encoding)
- HTML entity decoding
- Language-specific cleaning
- Noise reduction
"""

from __future__ import annotations
import re
import html
import unicodedata
from typing import Optional, List, Set
import logging

logger = logging.getLogger(__name__)

# Common boilerplate patterns to remove
BOILERPLATE_PATTERNS = [
    # Navigation and UI elements
    re.compile(r'Skip to (main )?content', re.IGNORECASE),
    re.compile(r'Click here to (subscribe|sign up|login)', re.IGNORECASE),
    re.compile(r'Sign up for (our|the) newsletter', re.IGNORECASE),
    re.compile(r'Follow us on (Facebook|Twitter|Instagram|LinkedIn)', re.IGNORECASE),
    re.compile(r'Share this (article|post|page)', re.IGNORECASE),

    # Cookie and privacy notices
    re.compile(r'This (site|website) uses cookies', re.IGNORECASE),
    re.compile(r'By continuing to use', re.IGNORECASE),
    re.compile(r'Cookie (Policy|Settings|Preferences)', re.IGNORECASE),

    # Advertisements
    re.compile(r'Advertisement|Sponsored Content|Promoted', re.IGNORECASE),

    # Common footer text
    re.compile(r'© \d{4}.*?All rights reserved', re.IGNORECASE),
    re.compile(r'Terms (of Use|and Conditions)|Privacy Policy', re.IGNORECASE),
]

# Common navigation words to filter out
NAVIGATION_WORDS = {
    'home', 'menu', 'search', 'login', 'logout', 'register', 'signin', 'signout',
    'subscribe', 'unsubscribe', 'previous', 'next', 'back', 'forward',
    'close', 'open', 'expand', 'collapse', 'toggle', 'more', 'less',
}

# Excessive whitespace patterns
WHITESPACE_PATTERNS = [
    (re.compile(r'\s+'), ' '),  # Multiple spaces to single space
    (re.compile(r'\n\s*\n\s*\n+'), '\n\n'),  # Multiple newlines to double newline
    (re.compile(r'[ \t]+\n'), '\n'),  # Trailing whitespace on lines
    (re.compile(r'\n[ \t]+'), '\n'),  # Leading whitespace on lines
]

# Special characters and symbols
SPECIAL_CHAR_PATTERNS = [
    (re.compile(r'[\u200b-\u200d\ufeff]'), ''),  # Zero-width characters
    (re.compile(r'[\u2018\u2019]'), "'"),  # Smart quotes to regular quotes
    (re.compile(r'[\u201c\u201d]'), '"'),  # Smart double quotes
    (re.compile(r'\u2026'), '...'),  # Ellipsis
    (re.compile(r'[\u2013\u2014]'), '-'),  # En/em dashes
]


class ContentCleaner:
    """Content cleaning utility."""

    def __init__(
        self,
        remove_boilerplate: bool = True,
        normalize_whitespace: bool = True,
        normalize_unicode: bool = True,
        decode_html_entities: bool = True,
        remove_urls: bool = False,
        remove_emails: bool = False,
        min_word_length: int = 2,
        max_consecutive_chars: int = 4,
    ):
        """
        Initialize content cleaner.

        Args:
            remove_boilerplate: Remove common boilerplate text
            normalize_whitespace: Normalize whitespace
            normalize_unicode: Normalize unicode characters
            decode_html_entities: Decode HTML entities
            remove_urls: Remove URLs from text
            remove_emails: Remove email addresses from text
            min_word_length: Minimum word length to keep
            max_consecutive_chars: Maximum consecutive repeated characters
        """
        self.remove_boilerplate = remove_boilerplate
        self.normalize_whitespace = normalize_whitespace
        self.normalize_unicode = normalize_unicode
        self.decode_html_entities = decode_html_entities
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.min_word_length = min_word_length
        self.max_consecutive_chars = max_consecutive_chars

    def clean(self, text: str) -> str:
        """
        Clean text content.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Decode HTML entities
        if self.decode_html_entities:
            text = html.unescape(text)

        # Normalize Unicode
        if self.normalize_unicode:
            text = self._normalize_unicode(text)

        # Remove URLs
        if self.remove_urls:
            text = self._remove_urls(text)

        # Remove emails
        if self.remove_emails:
            text = self._remove_emails(text)

        # Remove boilerplate
        if self.remove_boilerplate:
            text = self._remove_boilerplate(text)

        # Normalize special characters
        text = self._normalize_special_chars(text)

        # Normalize whitespace
        if self.normalize_whitespace:
            text = self._normalize_whitespace(text)

        # Remove excessive character repetition
        text = self._remove_excessive_repetition(text)

        # Final cleanup
        text = text.strip()

        return text

    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode characters to standard forms."""
        # NFKC normalization (compatibility decomposition, then canonical composition)
        text = unicodedata.normalize('NFKC', text)

        # Remove control characters except newlines and tabs
        text = ''.join(
            char for char in text
            if unicodedata.category(char)[0] != 'C' or char in '\n\t'
        )

        return text

    def _normalize_special_chars(self, text: str) -> str:
        """Normalize special characters and symbols."""
        for pattern, replacement in SPECIAL_CHAR_PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        for pattern, replacement in WHITESPACE_PATTERNS:
            text = pattern.sub(replacement, text)
        return text

    def _remove_boilerplate(self, text: str) -> str:
        """Remove common boilerplate patterns."""
        for pattern in BOILERPLATE_PATTERNS:
            text = pattern.sub('', text)
        return text

    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text."""
        # Remove http(s) URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove www URLs
        text = re.sub(r'www\.\S+', '', text)
        return text

    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text."""
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        return text

    def _remove_excessive_repetition(self, text: str) -> str:
        """Remove excessive character repetition."""
        if self.max_consecutive_chars <= 0:
            return text

        # Replace excessive repetition (e.g., "hellooooo" -> "hello")
        pattern = re.compile(r'(.)\1{' + str(self.max_consecutive_chars) + ',}')
        text = pattern.sub(r'\1' * self.max_consecutive_chars, text)

        return text


def clean_content(
    text: str,
    remove_boilerplate: bool = True,
    normalize_whitespace: bool = True,
    **kwargs
) -> str:
    """
    Clean text content with default settings.

    Args:
        text: Text to clean
        remove_boilerplate: Remove common boilerplate text
        normalize_whitespace: Normalize whitespace
        **kwargs: Additional cleaner options

    Returns:
        Cleaned text
    """
    cleaner = ContentCleaner(
        remove_boilerplate=remove_boilerplate,
        normalize_whitespace=normalize_whitespace,
        **kwargs
    )
    return cleaner.clean(text)


def remove_navigation_text(text: str, additional_words: Optional[Set[str]] = None) -> str:
    """
    Remove navigation-related text from content.

    Args:
        text: Text to clean
        additional_words: Additional navigation words to remove

    Returns:
        Text with navigation words removed
    """
    words_to_remove = NAVIGATION_WORDS.copy()
    if additional_words:
        words_to_remove.update(additional_words)

    # Split into lines and filter
    lines = text.split('\n')
    filtered_lines = []

    for line in lines:
        line_lower = line.lower().strip()
        # Skip lines that are just navigation words
        if line_lower in words_to_remove:
            continue
        # Skip very short lines that might be navigation
        if len(line_lower) < 10 and any(word in line_lower for word in words_to_remove):
            continue
        filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def extract_main_content(text: str, min_paragraph_length: int = 50) -> str:
    """
    Extract main content by filtering out short paragraphs and boilerplate.

    Args:
        text: Text to process
        min_paragraph_length: Minimum paragraph length to keep

    Returns:
        Main content text
    """
    # Split into paragraphs
    paragraphs = text.split('\n\n')

    # Filter paragraphs
    main_paragraphs = []
    for para in paragraphs:
        para = para.strip()

        # Skip very short paragraphs
        if len(para) < min_paragraph_length:
            continue

        # Skip paragraphs that are likely navigation or boilerplate
        para_lower = para.lower()
        if any(word in para_lower for word in ['cookie', 'privacy policy', 'terms of use']):
            if len(para) < 200:  # Only skip if short
                continue

        main_paragraphs.append(para)

    return '\n\n'.join(main_paragraphs)


def normalize_quotes_and_dashes(text: str) -> str:
    """
    Normalize various quote and dash styles to standard ASCII.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized quotes and dashes
    """
    # Smart quotes to regular quotes
    text = text.replace('\u2018', "'").replace('\u2019', "'")  # ' and '
    text = text.replace('\u201c', '"').replace('\u201d', '"')  # " and "

    # Various dashes to hyphen
    text = text.replace('\u2013', '-')  # en dash
    text = text.replace('\u2014', '-')  # em dash
    text = text.replace('\u2015', '-')  # horizontal bar

    return text


def remove_duplicate_lines(text: str, case_sensitive: bool = False) -> str:
    """
    Remove duplicate consecutive lines from text.

    Args:
        text: Text to deduplicate
        case_sensitive: Whether comparison should be case-sensitive

    Returns:
        Text with duplicate lines removed
    """
    lines = text.split('\n')
    deduplicated = []
    prev_line = None

    for line in lines:
        compare_line = line if case_sensitive else line.lower()
        prev_compare = prev_line if case_sensitive else (prev_line.lower() if prev_line else None)

        if compare_line != prev_compare:
            deduplicated.append(line)
            prev_line = line

    return '\n'.join(deduplicated)


def clean_for_embedding(text: str) -> str:
    """
    Clean text specifically for embedding generation.

    Applies aggressive cleaning suitable for semantic search.

    Args:
        text: Text to clean

    Returns:
        Cleaned text optimized for embeddings
    """
    cleaner = ContentCleaner(
        remove_boilerplate=True,
        normalize_whitespace=True,
        normalize_unicode=True,
        decode_html_entities=True,
        remove_urls=True,
        remove_emails=True,
        min_word_length=2,
        max_consecutive_chars=3,
    )

    text = cleaner.clean(text)
    text = remove_navigation_text(text)
    text = extract_main_content(text, min_paragraph_length=30)
    text = remove_duplicate_lines(text)

    return text


def clean_for_display(text: str) -> str:
    """
    Clean text for display purposes.

    Applies minimal cleaning to preserve readability.

    Args:
        text: Text to clean

    Returns:
        Cleaned text suitable for display
    """
    cleaner = ContentCleaner(
        remove_boilerplate=False,
        normalize_whitespace=True,
        normalize_unicode=True,
        decode_html_entities=True,
        remove_urls=False,
        remove_emails=False,
        max_consecutive_chars=4,
    )

    return cleaner.clean(text)
