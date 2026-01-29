"""
Content hash-based deduplication for webset items.
Supports multiple hashing strategies and fuzzy matching.
"""
from __future__ import annotations
from typing import Optional, Set, List, Dict, Any
import hashlib
import re
from dataclasses import dataclass


@dataclass
class DuplicateMatch:
    """Represents a duplicate content match."""
    content_hash: str
    similarity: float
    matched_item_id: Optional[str] = None
    matched_url: Optional[str] = None


class ContentDeduplicator:
    """Hash-based content deduplication with multiple strategies."""

    def __init__(self, strategy: str = "sha256"):
        """
        Initialize deduplicator with a specific strategy.

        Args:
            strategy: Hashing strategy (sha256, simhash, minhash)
        """
        self.strategy = strategy

    def compute_hash(self, content: str) -> str:
        """
        Compute content hash using the configured strategy.

        Args:
            content: Text content to hash

        Returns:
            Hexadecimal hash string
        """
        if self.strategy == "sha256":
            return self._sha256_hash(content)
        elif self.strategy == "simhash":
            return self._simhash(content)
        elif self.strategy == "minhash":
            return self._minhash(content)
        else:
            raise ValueError(f"Unknown hashing strategy: {self.strategy}")

    def _sha256_hash(self, content: str) -> str:
        """Standard SHA256 hash for exact duplicate detection."""
        normalized = self._normalize_content(content)
        return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()

    def _normalize_content(self, content: str) -> str:
        """
        Normalize content for more robust deduplication.

        Args:
            content: Raw text content

        Returns:
            Normalized content
        """
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        # Convert to lowercase
        content = content.lower()
        # Remove common boilerplate patterns
        content = self._remove_boilerplate(content)
        # Trim
        content = content.strip()
        return content

    def _remove_boilerplate(self, content: str) -> str:
        """
        Remove common boilerplate text (footers, headers, etc.).

        Args:
            content: Text content

        Returns:
            Content with boilerplate removed
        """
        # Common footer patterns
        footer_patterns = [
            r'copyright \d{4}.*$',
            r'all rights reserved.*$',
            r'privacy policy.*$',
            r'terms of service.*$',
            r'cookie policy.*$',
        ]

        for pattern in footer_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)

        return content

    def _simhash(self, content: str) -> str:
        """
        Compute SimHash for near-duplicate detection.

        SimHash is a locality-sensitive hashing technique that produces
        similar hashes for similar content.

        Args:
            content: Text content

        Returns:
            64-bit hash as hexadecimal string
        """
        # Tokenize content
        tokens = self._tokenize(content)

        # Initialize vector
        vector = [0] * 64

        # Process each token
        for token in tokens:
            # Hash the token
            token_hash = hashlib.md5(token.encode()).hexdigest()
            token_bits = bin(int(token_hash, 16))[2:].zfill(64)[:64]

            # Update vector
            for i, bit in enumerate(token_bits):
                if bit == '1':
                    vector[i] += 1
                else:
                    vector[i] -= 1

        # Generate final hash
        fingerprint = ['1' if v > 0 else '0' for v in vector]
        return hex(int(''.join(fingerprint), 2))[2:].zfill(16)

    def _minhash(self, content: str, num_hashes: int = 128) -> str:
        """
        Compute MinHash for near-duplicate detection.

        MinHash is used for estimating Jaccard similarity.

        Args:
            content: Text content
            num_hashes: Number of hash functions to use

        Returns:
            Concatenated min hashes as hexadecimal string
        """
        tokens = set(self._tokenize(content))

        if not tokens:
            return "0" * 32  # Empty content

        # Generate multiple hash values
        min_hashes = []
        for i in range(num_hashes):
            min_hash = float('inf')
            for token in tokens:
                # Use different seeds for each hash function
                hash_val = int(
                    hashlib.md5(f"{i}:{token}".encode()).hexdigest(), 16
                )
                min_hash = min(min_hash, hash_val)
            min_hashes.append(min_hash)

        # Combine hashes into a single signature
        signature = hashlib.sha256(
            str(min_hashes).encode()
        ).hexdigest()

        return signature

    def _tokenize(self, content: str, n: int = 3) -> List[str]:
        """
        Tokenize content into n-grams.

        Args:
            content: Text content
            n: N-gram size

        Returns:
            List of n-gram tokens
        """
        normalized = self._normalize_content(content)
        words = normalized.split()

        # Generate n-grams
        tokens = []
        for i in range(len(words) - n + 1):
            tokens.append(' '.join(words[i:i+n]))

        return tokens

    def compute_similarity(self, hash1: str, hash2: str) -> float:
        """
        Compute similarity between two hashes.

        Args:
            hash1: First content hash
            hash2: Second content hash

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if self.strategy == "sha256":
            # Exact match only
            return 1.0 if hash1 == hash2 else 0.0
        elif self.strategy == "simhash":
            return self._simhash_similarity(hash1, hash2)
        elif self.strategy == "minhash":
            return self._minhash_similarity(hash1, hash2)
        else:
            return 0.0

    def _simhash_similarity(self, hash1: str, hash2: str) -> float:
        """
        Compute similarity between two SimHash values.
        Uses Hamming distance.

        Args:
            hash1: First SimHash
            hash2: Second SimHash

        Returns:
            Similarity score (1.0 - normalized Hamming distance)
        """
        try:
            bits1 = bin(int(hash1, 16))[2:].zfill(64)
            bits2 = bin(int(hash2, 16))[2:].zfill(64)

            hamming_distance = sum(b1 != b2 for b1, b2 in zip(bits1, bits2))
            return 1.0 - (hamming_distance / 64.0)
        except:
            return 0.0

    def _minhash_similarity(self, hash1: str, hash2: str) -> float:
        """
        Compute similarity between two MinHash values.

        Args:
            hash1: First MinHash
            hash2: Second MinHash

        Returns:
            Similarity score (approximation of Jaccard similarity)
        """
        # For MinHash, we use exact match as a proxy
        # A more sophisticated implementation would compare signature sets
        return 1.0 if hash1 == hash2 else 0.0

    def is_duplicate(
        self,
        content: str,
        existing_hashes: Set[str],
        threshold: float = 0.95,
    ) -> Optional[DuplicateMatch]:
        """
        Check if content is a duplicate of existing content.

        Args:
            content: Content to check
            existing_hashes: Set of existing content hashes
            threshold: Similarity threshold for near-duplicates

        Returns:
            DuplicateMatch if duplicate found, None otherwise
        """
        content_hash = self.compute_hash(content)

        # Check for exact match first
        if content_hash in existing_hashes:
            return DuplicateMatch(
                content_hash=content_hash,
                similarity=1.0,
            )

        # For fuzzy strategies, check similarity against all hashes
        if self.strategy in ["simhash", "minhash"]:
            for existing_hash in existing_hashes:
                similarity = self.compute_similarity(content_hash, existing_hash)
                if similarity >= threshold:
                    return DuplicateMatch(
                        content_hash=content_hash,
                        similarity=similarity,
                    )

        return None

    def deduplicate_list(
        self,
        items: List[Dict[str, Any]],
        content_key: str = "content",
        threshold: float = 0.95,
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate a list of items based on content.

        Args:
            items: List of items with content
            content_key: Key for content field in items
            threshold: Similarity threshold

        Returns:
            List of unique items
        """
        unique_items = []
        seen_hashes = set()

        for item in items:
            content = item.get(content_key, "")
            if not content:
                unique_items.append(item)
                continue

            match = self.is_duplicate(content, seen_hashes, threshold)
            if not match:
                content_hash = self.compute_hash(content)
                seen_hashes.add(content_hash)
                unique_items.append(item)

        return unique_items


class URLDeduplicator:
    """URL-based deduplication with normalization."""

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL for comparison.

        Args:
            url: Raw URL

        Returns:
            Normalized URL
        """
        # Remove protocol
        url = re.sub(r'^https?://', '', url)
        # Remove www prefix
        url = re.sub(r'^www\.', '', url)
        # Remove trailing slash
        url = url.rstrip('/')
        # Remove common tracking parameters
        url = re.sub(r'[?&](utm_|ref=|source=)[^&]*', '', url)
        # Convert to lowercase
        url = url.lower()
        return url

    @staticmethod
    def is_duplicate_url(url1: str, url2: str) -> bool:
        """
        Check if two URLs are duplicates.

        Args:
            url1: First URL
            url2: Second URL

        Returns:
            True if URLs are duplicates
        """
        norm1 = URLDeduplicator.normalize_url(url1)
        norm2 = URLDeduplicator.normalize_url(url2)
        return norm1 == norm2

    @staticmethod
    def deduplicate_urls(urls: List[str]) -> List[str]:
        """
        Deduplicate a list of URLs.

        Args:
            urls: List of URLs

        Returns:
            List of unique URLs
        """
        seen = set()
        unique_urls = []

        for url in urls:
            normalized = URLDeduplicator.normalize_url(url)
            if normalized not in seen:
                seen.add(normalized)
                unique_urls.append(url)

        return unique_urls
