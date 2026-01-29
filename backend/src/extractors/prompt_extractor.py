"""
Natural language extraction using prompts and LLMs.
Provides flexible, prompt-based extraction for unstructured tasks.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of a prompt-based extraction."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[str] = None
    tokens_used: Optional[int] = None
    model: Optional[str] = None


@dataclass
class ExtractionTemplate:
    """Template for structured extraction tasks."""
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    output_format: str = "text"  # text, json, markdown, list
    examples: List[Dict[str, str]] = field(default_factory=list)


# Pre-defined extraction templates
EXTRACTION_TEMPLATES = {
    "summary": ExtractionTemplate(
        name="Summary",
        description="Generate a concise summary of the content",
        system_prompt="You are an expert at creating concise, accurate summaries. Focus on the main points and key takeaways.",
        user_prompt_template="Summarize the following text in {length} sentences:\n\n{text}",
        output_format="text",
    ),
    "key_points": ExtractionTemplate(
        name="Key Points",
        description="Extract key points and takeaways",
        system_prompt="You are an expert at identifying and extracting key points from text. Focus on the most important and actionable information.",
        user_prompt_template="Extract the key points from the following text as a bulleted list:\n\n{text}",
        output_format="list",
    ),
    "entities": ExtractionTemplate(
        name="Named Entities",
        description="Extract named entities (people, organizations, locations)",
        system_prompt="You are an expert at named entity recognition. Extract all relevant entities accurately.",
        user_prompt_template="Extract all people, organizations, and locations mentioned in this text. Return as JSON with keys 'people', 'organizations', 'locations':\n\n{text}",
        output_format="json",
    ),
    "questions": ExtractionTemplate(
        name="Questions",
        description="Extract or generate questions from content",
        system_prompt="You are an expert at identifying or generating relevant questions from text.",
        user_prompt_template="Extract all questions mentioned or implied in this text, or generate important questions that this text answers:\n\n{text}",
        output_format="list",
    ),
    "action_items": ExtractionTemplate(
        name="Action Items",
        description="Extract action items and tasks",
        system_prompt="You are an expert at identifying action items and tasks from text. Focus on actionable steps.",
        user_prompt_template="Extract all action items and tasks from this text:\n\n{text}",
        output_format="list",
    ),
    "sentiment": ExtractionTemplate(
        name="Sentiment Analysis",
        description="Analyze sentiment and tone",
        system_prompt="You are an expert at sentiment analysis. Analyze text for overall sentiment, tone, and emotional content.",
        user_prompt_template="Analyze the sentiment of this text. Return JSON with 'sentiment' (positive/negative/neutral), 'confidence' (0-1), and 'explanation':\n\n{text}",
        output_format="json",
    ),
    "categorization": ExtractionTemplate(
        name="Categorization",
        description="Categorize content into topics",
        system_prompt="You are an expert at content categorization. Assign appropriate categories and topics.",
        user_prompt_template="Categorize this text into relevant topics and themes. Return as JSON with 'primary_category', 'secondary_categories' (list), and 'topics' (list):\n\n{text}",
        output_format="json",
    ),
    "quotes": ExtractionTemplate(
        name="Quotes",
        description="Extract notable quotes",
        system_prompt="You are an expert at identifying notable and important quotes from text.",
        user_prompt_template="Extract all notable quotes from this text. Return as JSON array with 'quote' and 'context' for each:\n\n{text}",
        output_format="json",
    ),
    "facts": ExtractionTemplate(
        name="Facts",
        description="Extract factual statements",
        system_prompt="You are an expert at identifying factual statements and claims in text.",
        user_prompt_template="Extract all factual statements from this text. Return as a list:\n\n{text}",
        output_format="list",
    ),
    "comparison": ExtractionTemplate(
        name="Comparison",
        description="Extract comparisons and contrasts",
        system_prompt="You are an expert at identifying comparisons, contrasts, and differences in text.",
        user_prompt_template="Extract all comparisons mentioned in this text. Return as JSON with items being compared and their differences:\n\n{text}",
        output_format="json",
    ),
}


class PromptExtractor:
    """
    Extract information from text using natural language prompts and LLMs.
    Supports custom prompts and pre-defined extraction templates.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize prompt extractor.

        Args:
            api_key: OpenAI API key (or compatible API key)
            base_url: Base URL for API (e.g., Requesty)
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        import os

        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("REQUESTY_API_KEY")
        self.base_url = base_url or os.getenv("REQUESTY_BASE_URL")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize client
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = AsyncOpenAI(**client_kwargs)

    async def extract(
        self,
        text: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        output_format: str = "text",
        **kwargs
    ) -> ExtractionResult:
        """
        Extract information using a custom prompt.

        Args:
            text: Text to extract from
            prompt: User prompt or instruction
            system_prompt: System prompt for context
            output_format: Expected output format (text, json, markdown, list)
            **kwargs: Additional parameters for the API

        Returns:
            ExtractionResult with extracted content
        """
        # Build messages
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system",
                "content": "You are a helpful assistant that extracts information from text accurately and concisely."
            })

        # Format the user prompt
        user_content = f"{prompt}\n\nText:\n{text}"
        messages.append({"role": "user", "content": user_content})

        # Make API call
        try:
            response = await self.client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )

            # Extract content
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None

            # Parse output based on format
            if output_format == "json":
                try:
                    metadata = {"parsed": json.loads(content)}
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON output, returning raw text")
                    metadata = {}
            elif output_format == "list":
                # Try to parse as list (assuming bulleted or numbered)
                lines = content.strip().split("\n")
                items = []
                for line in lines:
                    # Remove bullet points, numbers, etc.
                    cleaned = line.strip().lstrip("-*•►▪▸").lstrip("0123456789.).").strip()
                    if cleaned:
                        items.append(cleaned)
                metadata = {"items": items}
            else:
                metadata = {}

            return ExtractionResult(
                content=content,
                metadata=metadata,
                raw_response=content,
                tokens_used=tokens_used,
                model=self.model,
            )

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise

    async def extract_with_template(
        self,
        text: str,
        template_name: str,
        **template_vars
    ) -> ExtractionResult:
        """
        Extract using a pre-defined template.

        Args:
            text: Text to extract from
            template_name: Name of the template to use
            **template_vars: Variables to fill in the template

        Returns:
            ExtractionResult with extracted content
        """
        if template_name not in EXTRACTION_TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}. Available: {list(EXTRACTION_TEMPLATES.keys())}")

        template = EXTRACTION_TEMPLATES[template_name]

        # Fill in template variables
        template_vars["text"] = text
        user_prompt = template.user_prompt_template.format(**template_vars)

        return await self.extract(
            text=text,
            prompt=user_prompt,
            system_prompt=template.system_prompt,
            output_format=template.output_format,
        )

    async def summarize(
        self,
        text: str,
        length: int = 3,
        style: str = "concise"
    ) -> str:
        """
        Generate a summary of the text.

        Args:
            text: Text to summarize
            length: Number of sentences in summary
            style: Summary style (concise, detailed, bullet-points)

        Returns:
            Summary text
        """
        result = await self.extract_with_template(
            text,
            "summary",
            length=length
        )
        return result.content

    async def extract_key_points(self, text: str, max_points: int = 5) -> List[str]:
        """
        Extract key points from text.

        Args:
            text: Text to extract from
            max_points: Maximum number of points

        Returns:
            List of key points
        """
        result = await self.extract_with_template(text, "key_points")
        items = result.metadata.get("items", [])
        return items[:max_points]

    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text.

        Args:
            text: Text to extract from

        Returns:
            Dictionary with entities by type
        """
        result = await self.extract_with_template(text, "entities")
        return result.metadata.get("parsed", {})

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment analysis
        """
        result = await self.extract_with_template(text, "sentiment")
        return result.metadata.get("parsed", {})

    async def categorize(self, text: str) -> Dict[str, Any]:
        """
        Categorize text into topics.

        Args:
            text: Text to categorize

        Returns:
            Dictionary with categories and topics
        """
        result = await self.extract_with_template(text, "categorization")
        return result.metadata.get("parsed", {})

    async def extract_questions(self, text: str) -> List[str]:
        """
        Extract questions from text.

        Args:
            text: Text to extract from

        Returns:
            List of questions
        """
        result = await self.extract_with_template(text, "questions")
        return result.metadata.get("items", [])

    async def extract_quotes(self, text: str) -> List[Dict[str, str]]:
        """
        Extract notable quotes from text.

        Args:
            text: Text to extract from

        Returns:
            List of quotes with context
        """
        result = await self.extract_with_template(text, "quotes")
        return result.metadata.get("parsed", [])

    async def extract_action_items(self, text: str) -> List[str]:
        """
        Extract action items from text.

        Args:
            text: Text to extract from

        Returns:
            List of action items
        """
        result = await self.extract_with_template(text, "action_items")
        return result.metadata.get("items", [])

    async def extract_custom(
        self,
        text: str,
        instruction: str,
        context: Optional[str] = None,
        examples: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Extract using custom instructions.

        Args:
            text: Text to extract from
            instruction: What to extract
            context: Additional context
            examples: Few-shot examples

        Returns:
            Extracted content
        """
        # Build prompt with examples if provided
        prompt_parts = [instruction]

        if context:
            prompt_parts.append(f"\nContext: {context}")

        if examples:
            prompt_parts.append("\nExamples:")
            for i, example in enumerate(examples, 1):
                prompt_parts.append(f"\nExample {i}:")
                prompt_parts.append(f"Input: {example.get('input', '')}")
                prompt_parts.append(f"Output: {example.get('output', '')}")

        prompt = "\n".join(prompt_parts)

        result = await self.extract(text, prompt)
        return result.content

    async def extract_batch(
        self,
        texts: List[str],
        template_name: str,
        **template_vars
    ) -> List[ExtractionResult]:
        """
        Extract from multiple texts using a template.

        Args:
            texts: List of texts to extract from
            template_name: Template to use
            **template_vars: Template variables

        Returns:
            List of extraction results
        """
        import asyncio

        tasks = [
            self.extract_with_template(text, template_name, **template_vars)
            for text in texts
        ]

        return await asyncio.gather(*tasks, return_exceptions=True)


# Convenience functions

async def summarize_text(
    text: str,
    length: int = 3,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> str:
    """
    Summarize text.

    Args:
        text: Text to summarize
        length: Number of sentences
        api_key: API key
        base_url: Base URL

    Returns:
        Summary text
    """
    extractor = PromptExtractor(api_key=api_key, base_url=base_url)
    return await extractor.summarize(text, length)


async def extract_key_points(
    text: str,
    max_points: int = 5,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> List[str]:
    """
    Extract key points from text.

    Args:
        text: Text to extract from
        max_points: Maximum points
        api_key: API key
        base_url: Base URL

    Returns:
        List of key points
    """
    extractor = PromptExtractor(api_key=api_key, base_url=base_url)
    return await extractor.extract_key_points(text, max_points)


async def analyze_sentiment(
    text: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze text sentiment.

    Args:
        text: Text to analyze
        api_key: API key
        base_url: Base URL

    Returns:
        Sentiment analysis
    """
    extractor = PromptExtractor(api_key=api_key, base_url=base_url)
    return await extractor.analyze_sentiment(text)


async def extract_with_prompt(
    text: str,
    prompt: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    output_format: str = "text",
) -> str:
    """
    Extract using custom prompt.

    Args:
        text: Text to extract from
        prompt: Extraction instruction
        api_key: API key
        base_url: Base URL
        output_format: Output format

    Returns:
        Extracted content
    """
    extractor = PromptExtractor(api_key=api_key, base_url=base_url)
    result = await extractor.extract(text, prompt, output_format=output_format)
    return result.content
