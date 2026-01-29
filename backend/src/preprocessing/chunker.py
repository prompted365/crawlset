"""
Text chunking strategies for semantic processing.

Provides multiple chunking strategies:
- Sentence-based: Split by sentences with configurable overlap
- Sliding window: Fixed-size chunks with overlap
- Paragraph-based: Split by paragraphs
- Semantic: Use embeddings for semantic boundary detection
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ChunkingStrategy(str, Enum):
    """Available chunking strategies."""
    SENTENCE = "sentence"
    SLIDING_WINDOW = "sliding_window"
    PARAGRAPH = "paragraph"
    SEMANTIC = "semantic"
    FIXED_SIZE = "fixed_size"


@dataclass
class Chunk:
    """Represents a text chunk."""
    text: str
    index: int
    start_char: int
    end_char: int
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ChunkingConfig:
    """Configuration for chunking."""
    strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE
    chunk_size: int = 512  # Target size in characters
    chunk_overlap: int = 50  # Overlap in characters
    min_chunk_size: int = 100  # Minimum chunk size
    max_chunk_size: int = 2000  # Maximum chunk size
    respect_sentence_boundaries: bool = True
    strip_whitespace: bool = True


# Sentence boundary detection patterns
SENTENCE_ENDINGS = re.compile(r'([.!?]+[\s\n]+|[\n]{2,})')
PARAGRAPH_ENDINGS = re.compile(r'\n\n+')


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences.

    Uses simple heuristics to detect sentence boundaries while handling
    common abbreviations and edge cases.
    """
    # Handle common abbreviations that shouldn't break sentences
    text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|vs|etc|Inc|Ltd|Corp)\.\s', r'\1<PERIOD> ', text)

    # Split on sentence boundaries
    sentences = SENTENCE_ENDINGS.split(text)

    # Restore abbreviations
    sentences = [s.replace('<PERIOD>', '.') for s in sentences]

    # Combine sentence text with their endings
    result = []
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        ending = sentences[i + 1] if i + 1 < len(sentences) else ''
        combined = (sentence + ending).strip()
        if combined:
            result.append(combined)

    # Handle last sentence if it doesn't end with punctuation
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())

    return result


def split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs."""
    paragraphs = PARAGRAPH_ENDINGS.split(text)
    return [p.strip() for p in paragraphs if p.strip()]


class TextChunker:
    """Text chunker with multiple strategies."""

    def __init__(self, config: ChunkingConfig = None):
        self.config = config or ChunkingConfig()

    def chunk(self, text: str) -> List[Chunk]:
        """
        Chunk text according to configured strategy.

        Args:
            text: Text to chunk

        Returns:
            List of Chunk objects
        """
        if self.config.strip_whitespace:
            text = text.strip()

        if not text:
            return []

        strategy = self.config.strategy

        if strategy == ChunkingStrategy.SENTENCE:
            return self._chunk_by_sentences(text)
        elif strategy == ChunkingStrategy.SLIDING_WINDOW:
            return self._chunk_by_sliding_window(text)
        elif strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraphs(text)
        elif strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_by_fixed_size(text)
        elif strategy == ChunkingStrategy.SEMANTIC:
            # Fall back to sentence chunking for now
            # TODO: Implement semantic chunking with embeddings
            logger.warning("Semantic chunking not yet implemented, using sentence chunking")
            return self._chunk_by_sentences(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

    def _chunk_by_sentences(self, text: str) -> List[Chunk]:
        """
        Chunk by sentences, combining sentences to reach target size.

        Creates chunks by combining sentences until reaching the target size,
        with configurable overlap.
        """
        sentences = split_into_sentences(text)
        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_size = 0
        char_position = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            # If adding this sentence exceeds max size, save current chunk
            if current_size + sentence_size > self.config.max_chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(Chunk(
                    text=chunk_text,
                    index=len(chunks),
                    start_char=char_position - current_size,
                    end_char=char_position,
                    metadata={"sentence_count": len(current_chunk)}
                ))

                # Handle overlap by keeping last few sentences
                if self.config.chunk_overlap > 0:
                    overlap_text = []
                    overlap_size = 0
                    for s in reversed(current_chunk):
                        if overlap_size + len(s) <= self.config.chunk_overlap:
                            overlap_text.insert(0, s)
                            overlap_size += len(s)
                        else:
                            break
                    current_chunk = overlap_text
                    current_size = overlap_size
                else:
                    current_chunk = []
                    current_size = 0

            current_chunk.append(sentence)
            current_size += sentence_size
            char_position += sentence_size

        # Add remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    text=chunk_text,
                    index=len(chunks),
                    start_char=char_position - current_size,
                    end_char=char_position,
                    metadata={"sentence_count": len(current_chunk)}
                ))

        return chunks

    def _chunk_by_sliding_window(self, text: str) -> List[Chunk]:
        """
        Chunk using sliding window with fixed size and overlap.

        Creates overlapping chunks by moving a window across the text.
        """
        if len(text) <= self.config.chunk_size:
            return [Chunk(
                text=text,
                index=0,
                start_char=0,
                end_char=len(text),
                metadata={}
            )]

        chunks = []
        stride = self.config.chunk_size - self.config.chunk_overlap

        for i in range(0, len(text), stride):
            chunk_text = text[i:i + self.config.chunk_size]

            # Respect sentence boundaries if configured
            if self.config.respect_sentence_boundaries and len(chunk_text) > self.config.min_chunk_size:
                # Try to end at a sentence boundary
                for pattern in ['. ', '! ', '? ', '.\n', '!\n', '?\n']:
                    last_period = chunk_text.rfind(pattern)
                    if last_period > self.config.min_chunk_size:
                        chunk_text = chunk_text[:last_period + 1].strip()
                        break

            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    text=chunk_text,
                    index=len(chunks),
                    start_char=i,
                    end_char=i + len(chunk_text),
                    metadata={}
                ))

            # Stop if we've covered the entire text
            if i + len(chunk_text) >= len(text):
                break

        return chunks

    def _chunk_by_paragraphs(self, text: str) -> List[Chunk]:
        """
        Chunk by paragraphs, combining small paragraphs to reach target size.
        """
        paragraphs = split_into_paragraphs(text)
        if not paragraphs:
            return []

        chunks = []
        current_chunk = []
        current_size = 0
        char_position = 0

        for paragraph in paragraphs:
            paragraph_size = len(paragraph)

            # If this paragraph alone is too large, split it further
            if paragraph_size > self.config.max_chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append(Chunk(
                        text=chunk_text,
                        index=len(chunks),
                        start_char=char_position - current_size,
                        end_char=char_position,
                        metadata={"paragraph_count": len(current_chunk)}
                    ))
                    current_chunk = []
                    current_size = 0

                # Split large paragraph by sentences
                paragraph_chunker = TextChunker(
                    ChunkingConfig(
                        strategy=ChunkingStrategy.SENTENCE,
                        chunk_size=self.config.chunk_size,
                        chunk_overlap=self.config.chunk_overlap,
                        min_chunk_size=self.config.min_chunk_size,
                        max_chunk_size=self.config.max_chunk_size,
                    )
                )
                para_chunks = paragraph_chunker.chunk(paragraph)
                for chunk in para_chunks:
                    chunk.index = len(chunks)
                    chunks.append(chunk)

                char_position += paragraph_size
                continue

            # If adding this paragraph exceeds target, save current chunk
            if current_size + paragraph_size > self.config.chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(Chunk(
                    text=chunk_text,
                    index=len(chunks),
                    start_char=char_position - current_size,
                    end_char=char_position,
                    metadata={"paragraph_count": len(current_chunk)}
                ))
                current_chunk = []
                current_size = 0

            current_chunk.append(paragraph)
            current_size += paragraph_size
            char_position += paragraph_size

        # Add remaining chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    text=chunk_text,
                    index=len(chunks),
                    start_char=char_position - current_size,
                    end_char=char_position,
                    metadata={"paragraph_count": len(current_chunk)}
                ))

        return chunks

    def _chunk_by_fixed_size(self, text: str) -> List[Chunk]:
        """Chunk by fixed character size without overlap."""
        chunks = []
        chunk_size = self.config.chunk_size

        for i in range(0, len(text), chunk_size):
            chunk_text = text[i:i + chunk_size].strip()
            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(Chunk(
                    text=chunk_text,
                    index=len(chunks),
                    start_char=i,
                    end_char=i + len(chunk_text),
                    metadata={}
                ))

        return chunks


# Convenience functions

def chunk_text(
    text: str,
    strategy: ChunkingStrategy = ChunkingStrategy.SENTENCE,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    **kwargs
) -> List[Chunk]:
    """
    Chunk text with specified strategy and parameters.

    Args:
        text: Text to chunk
        strategy: Chunking strategy to use
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        **kwargs: Additional configuration options

    Returns:
        List of Chunk objects
    """
    config = ChunkingConfig(
        strategy=strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        **kwargs
    )
    chunker = TextChunker(config)
    return chunker.chunk(text)


def chunk_for_embedding(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
) -> List[Chunk]:
    """
    Chunk text optimized for embedding models.

    Assumes roughly 4 characters per token for estimation.

    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk
        overlap_tokens: Overlap in tokens

    Returns:
        List of Chunk objects
    """
    # Estimate characters per token (rough approximation)
    chars_per_token = 4
    chunk_size = max_tokens * chars_per_token
    overlap_size = overlap_tokens * chars_per_token

    return chunk_text(
        text,
        strategy=ChunkingStrategy.SENTENCE,
        chunk_size=chunk_size,
        chunk_overlap=overlap_size,
        min_chunk_size=100,
    )
