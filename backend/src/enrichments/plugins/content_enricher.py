"""
LLM-based content enrichment plugin.
Uses OpenAI/Anthropic with Instructor for structured extraction.
"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
import logging
import os

from ..engine import EnrichmentPlugin, EnrichmentResult

logger = logging.getLogger(__name__)


class ContentSummaryEnricher(EnrichmentPlugin):
    """
    Generate summaries of content using LLMs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = config.get("api_key") if config else None
        self.provider = config.get("provider", "openai") if config else "openai"
        self.model = config.get("model", "gpt-4") if config else "gpt-4"
        self.max_length = config.get("max_length", 200) if config else 200

    async def enrich(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnrichmentResult:
        """
        Generate a summary of the content.
        """
        result = EnrichmentResult(self.name)

        try:
            # Check if we have API credentials
            api_key = self.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                result.error = "No API key configured for LLM provider"
                return result

            # Generate summary
            summary = await self._generate_summary(content)

            result.data = {
                "summary": summary,
                "word_count": len(content.split()),
                "char_count": len(content),
            }
            result.success = True

        except Exception as e:
            result.error = str(e)
            logger.error(f"Content summary enrichment failed: {e}")

        return result

    async def _generate_summary(self, content: str) -> str:
        """Generate summary using LLM."""
        try:
            if self.provider == "openai":
                return await self._openai_summary(content)
            elif self.provider == "anthropic":
                return await self._anthropic_summary(content)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
        except Exception as e:
            logger.error(f"LLM summary generation failed: {e}")
            # Fallback to simple truncation
            return self._simple_summary(content)

    async def _openai_summary(self, content: str) -> str:
        """Generate summary using OpenAI."""
        try:
            import openai

            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            client = openai.AsyncOpenAI(api_key=api_key)

            # Truncate content if too long
            max_tokens = 3000
            if len(content) > max_tokens * 4:  # Rough estimate: 1 token ~= 4 chars
                content = content[:max_tokens * 4]

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Summarize the following text in {self.max_length} words or less. Be concise and focus on key points.",
                    },
                    {
                        "role": "user",
                        "content": content,
                    },
                ],
                max_tokens=self.max_length * 2,  # Rough estimate for tokens
                temperature=0.3,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"OpenAI summary failed: {e}")
            raise

    async def _anthropic_summary(self, content: str) -> str:
        """Generate summary using Anthropic."""
        try:
            import anthropic

            api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            client = anthropic.AsyncAnthropic(api_key=api_key)

            # Truncate content if too long
            max_chars = 10000
            if len(content) > max_chars:
                content = content[:max_chars]

            response = await client.messages.create(
                model=self.model or "claude-3-5-sonnet-20241022",
                max_tokens=self.max_length * 2,
                messages=[
                    {
                        "role": "user",
                        "content": f"Summarize the following text in {self.max_length} words or less. Be concise and focus on key points.\n\n{content}",
                    }
                ],
            )

            return response.content[0].text.strip()

        except Exception as e:
            logger.error(f"Anthropic summary failed: {e}")
            raise

    def _simple_summary(self, content: str) -> str:
        """Fallback simple summary (first N words)."""
        words = content.split()
        summary_words = words[:self.max_length]
        summary = " ".join(summary_words)
        if len(words) > self.max_length:
            summary += "..."
        return summary

    def get_schema(self) -> Dict[str, Any]:
        """Get the output schema."""
        return {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Content summary",
                },
                "word_count": {
                    "type": "integer",
                    "description": "Total word count of content",
                },
                "char_count": {
                    "type": "integer",
                    "description": "Total character count of content",
                },
            },
        }


class KeyPointsEnricher(EnrichmentPlugin):
    """
    Extract key points and main topics from content using LLMs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = config.get("api_key") if config else None
        self.provider = config.get("provider", "openai") if config else "openai"
        self.model = config.get("model", "gpt-4") if config else "gpt-4"
        self.num_points = config.get("num_points", 5) if config else 5

    async def enrich(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnrichmentResult:
        """
        Extract key points from content.
        """
        result = EnrichmentResult(self.name)

        try:
            api_key = self.api_key or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                result.error = "No API key configured for LLM provider"
                return result

            key_points = await self._extract_key_points(content)

            result.data = {
                "key_points": key_points,
                "num_points": len(key_points),
            }
            result.success = True

        except Exception as e:
            result.error = str(e)
            logger.error(f"Key points enrichment failed: {e}")

        return result

    async def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points using LLM."""
        try:
            if self.provider == "openai":
                return await self._openai_key_points(content)
            elif self.provider == "anthropic":
                return await self._anthropic_key_points(content)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
        except Exception as e:
            logger.error(f"LLM key points extraction failed: {e}")
            return []

    async def _openai_key_points(self, content: str) -> List[str]:
        """Extract key points using OpenAI."""
        try:
            import openai

            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            client = openai.AsyncOpenAI(api_key=api_key)

            # Truncate content if too long
            max_tokens = 3000
            if len(content) > max_tokens * 4:
                content = content[:max_tokens * 4]

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"Extract {self.num_points} key points from the text. Return them as a bullet list, one per line, starting with '-'.",
                    },
                    {
                        "role": "user",
                        "content": content,
                    },
                ],
                max_tokens=500,
                temperature=0.3,
            )

            # Parse bullet points
            text = response.choices[0].message.content.strip()
            points = [
                line.strip("- ").strip()
                for line in text.split("\n")
                if line.strip().startswith("-")
            ]

            return points[:self.num_points]

        except Exception as e:
            logger.error(f"OpenAI key points failed: {e}")
            raise

    async def _anthropic_key_points(self, content: str) -> List[str]:
        """Extract key points using Anthropic."""
        try:
            import anthropic

            api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            client = anthropic.AsyncAnthropic(api_key=api_key)

            max_chars = 10000
            if len(content) > max_chars:
                content = content[:max_chars]

            response = await client.messages.create(
                model=self.model or "claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": f"Extract {self.num_points} key points from the following text. Return them as a bullet list, one per line, starting with '-'.\n\n{content}",
                    }
                ],
            )

            # Parse bullet points
            text = response.content[0].text.strip()
            points = [
                line.strip("- ").strip()
                for line in text.split("\n")
                if line.strip().startswith("-")
            ]

            return points[:self.num_points]

        except Exception as e:
            logger.error(f"Anthropic key points failed: {e}")
            raise

    def get_schema(self) -> Dict[str, Any]:
        """Get the output schema."""
        return {
            "type": "object",
            "properties": {
                "key_points": {
                    "type": "array",
                    "description": "List of key points",
                    "items": {"type": "string"},
                },
                "num_points": {
                    "type": "integer",
                    "description": "Number of key points extracted",
                },
            },
        }


class StructuredDataEnricher(EnrichmentPlugin):
    """
    Extract structured data from content using Instructor + LLMs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_key = config.get("api_key") if config else None
        self.provider = config.get("provider", "openai") if config else "openai"
        self.model = config.get("model", "gpt-4") if config else "gpt-4"
        self.schema = config.get("schema") if config else None

    async def enrich(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnrichmentResult:
        """
        Extract structured data based on provided schema.
        """
        result = EnrichmentResult(self.name)

        try:
            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                result.error = "No API key configured"
                return result

            if not self.schema:
                result.error = "No schema provided for structured extraction"
                return result

            # Use Instructor for structured extraction
            extracted_data = await self._extract_with_instructor(content)

            result.data = extracted_data
            result.success = True

        except Exception as e:
            result.error = str(e)
            logger.error(f"Structured data enrichment failed: {e}")

        return result

    async def _extract_with_instructor(self, content: str) -> Dict[str, Any]:
        """Extract structured data using Instructor."""
        try:
            import instructor
            import openai
            from pydantic import BaseModel, create_model

            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            client = instructor.from_openai(openai.AsyncOpenAI(api_key=api_key))

            # Create dynamic Pydantic model from schema
            # TODO: Implement proper schema to Pydantic conversion
            # For now, return empty dict
            return {}

        except Exception as e:
            logger.error(f"Instructor extraction failed: {e}")
            raise

    def get_schema(self) -> Dict[str, Any]:
        """Get the output schema."""
        return self.schema or {
            "type": "object",
            "description": "Custom structured data based on provided schema",
        }
