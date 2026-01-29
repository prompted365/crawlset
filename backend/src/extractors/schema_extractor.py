"""
Pydantic model-based structured data extraction using instructor library.
Provides type-safe extraction of structured information from text and HTML.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, get_args, get_origin

from pydantic import BaseModel, Field, ValidationError
import instructor
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# Example schema models for common use cases
class Person(BaseModel):
    """Represents a person mentioned in content."""
    name: str = Field(..., description="Full name of the person")
    title: Optional[str] = Field(None, description="Job title or role")
    organization: Optional[str] = Field(None, description="Organization or company")
    email: Optional[str] = Field(None, description="Email address")
    social_links: List[str] = Field(default_factory=list, description="Social media profile URLs")


class Organization(BaseModel):
    """Represents an organization."""
    name: str = Field(..., description="Organization name")
    industry: Optional[str] = Field(None, description="Industry sector")
    location: Optional[str] = Field(None, description="Location or headquarters")
    website: Optional[str] = Field(None, description="Website URL")
    description: Optional[str] = Field(None, description="Brief description")


class Event(BaseModel):
    """Represents an event."""
    title: str = Field(..., description="Event title")
    date: Optional[str] = Field(None, description="Event date (ISO format)")
    location: Optional[str] = Field(None, description="Event location")
    description: Optional[str] = Field(None, description="Event description")
    organizer: Optional[str] = Field(None, description="Event organizer")
    url: Optional[str] = Field(None, description="Event URL")


class Product(BaseModel):
    """Represents a product or service."""
    name: str = Field(..., description="Product name")
    category: Optional[str] = Field(None, description="Product category")
    price: Optional[str] = Field(None, description="Price (with currency)")
    description: Optional[str] = Field(None, description="Product description")
    features: List[str] = Field(default_factory=list, description="Key features")
    url: Optional[str] = Field(None, description="Product URL")


class Article(BaseModel):
    """Represents an article or blog post."""
    title: str = Field(..., description="Article title")
    author: Optional[str] = Field(None, description="Author name")
    published_date: Optional[str] = Field(None, description="Publication date (ISO format)")
    summary: Optional[str] = Field(None, description="Article summary")
    key_points: List[str] = Field(default_factory=list, description="Key points or takeaways")
    topics: List[str] = Field(default_factory=list, description="Main topics covered")
    sentiment: Optional[str] = Field(None, description="Overall sentiment (positive/negative/neutral)")


class ResearchPaper(BaseModel):
    """Represents a research paper."""
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="Author names")
    abstract: Optional[str] = Field(None, description="Abstract")
    published_date: Optional[str] = Field(None, description="Publication date")
    journal: Optional[str] = Field(None, description="Journal or conference name")
    doi: Optional[str] = Field(None, description="DOI identifier")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    methodology: Optional[str] = Field(None, description="Research methodology")
    findings: List[str] = Field(default_factory=list, description="Key findings")


class Contact(BaseModel):
    """Represents contact information."""
    name: Optional[str] = Field(None, description="Contact name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Physical address")
    website: Optional[str] = Field(None, description="Website URL")
    social_media: Dict[str, str] = Field(default_factory=dict, description="Social media links")


class FAQ(BaseModel):
    """Represents a FAQ item."""
    question: str = Field(..., description="Question")
    answer: str = Field(..., description="Answer")
    category: Optional[str] = Field(None, description="FAQ category")


class KeyValuePair(BaseModel):
    """Generic key-value pair."""
    key: str = Field(..., description="Key or label")
    value: str = Field(..., description="Value or content")


class ExtractedList(BaseModel):
    """Represents a list of items."""
    items: List[str] = Field(..., description="List items")
    title: Optional[str] = Field(None, description="List title or heading")


class SchemaExtractor:
    """
    Extract structured data from text using Pydantic models and LLMs.
    Uses instructor library for type-safe extraction.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        max_retries: int = 3,
    ):
        """
        Initialize schema extractor.

        Args:
            api_key: OpenAI API key (or Requesty API key if using base_url)
            base_url: Base URL for OpenAI-compatible API (e.g., Requesty)
            model: Model name
            temperature: Sampling temperature
            max_retries: Maximum retry attempts for failed extractions
        """
        import os

        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("REQUESTY_API_KEY")
        self.base_url = base_url or os.getenv("REQUESTY_BASE_URL")
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries

        # Initialize OpenAI client with instructor
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = instructor.from_openai(AsyncOpenAI(**client_kwargs))

    async def extract(
        self,
        text: str,
        schema: Type[T],
        context: Optional[str] = None,
        mode: instructor.Mode = instructor.Mode.TOOLS,
    ) -> T:
        """
        Extract structured data from text using a Pydantic schema.

        Args:
            text: Text to extract from
            schema: Pydantic model class to extract into
            context: Additional context or instructions
            mode: Instructor extraction mode

        Returns:
            Instance of schema with extracted data

        Raises:
            ValidationError: If extraction fails validation
            Exception: If extraction fails after retries
        """
        # Build prompt
        prompt = self._build_extraction_prompt(text, schema, context)

        try:
            # Use instructor to extract
            result = await self.client.chat.completions.create(
                model=self.model,
                response_model=schema,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured information from text. Extract the requested information accurately and completely.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_retries=self.max_retries,
            )

            return result

        except ValidationError as e:
            logger.error(f"Validation error during extraction: {e}")
            raise
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise

    async def extract_multiple(
        self,
        text: str,
        schema: Type[T],
        context: Optional[str] = None,
    ) -> List[T]:
        """
        Extract multiple instances of a schema from text.

        Args:
            text: Text to extract from
            schema: Pydantic model class to extract into
            context: Additional context or instructions

        Returns:
            List of schema instances
        """
        # Create a wrapper model for multiple items
        class MultipleItems(BaseModel):
            items: List[schema]  # type: ignore

        # Build prompt for multiple extraction
        prompt = self._build_multiple_extraction_prompt(text, schema, context)

        try:
            result = await self.client.chat.completions.create(
                model=self.model,
                response_model=MultipleItems,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured information from text. Extract ALL instances of the requested information.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_retries=self.max_retries,
            )

            return result.items

        except Exception as e:
            logger.error(f"Multiple extraction failed: {e}")
            raise

    async def extract_with_fallback(
        self,
        text: str,
        schema: Type[T],
        fallback_values: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
    ) -> T:
        """
        Extract with fallback values for missing fields.

        Args:
            text: Text to extract from
            schema: Pydantic model class to extract into
            fallback_values: Default values for fields if extraction fails
            context: Additional context or instructions

        Returns:
            Instance of schema with extracted or fallback data
        """
        try:
            return await self.extract(text, schema, context)
        except Exception as e:
            logger.warning(f"Extraction failed, using fallback: {e}")

            # Create instance with fallback values
            if fallback_values:
                try:
                    return schema(**fallback_values)
                except ValidationError:
                    pass

            # Return minimal valid instance
            return schema(**self._get_minimal_values(schema))

    async def extract_batch(
        self,
        texts: List[str],
        schema: Type[T],
        context: Optional[str] = None,
    ) -> List[T]:
        """
        Extract from multiple texts in batch.

        Args:
            texts: List of texts to extract from
            schema: Pydantic model class to extract into
            context: Additional context or instructions

        Returns:
            List of schema instances (one per input text)
        """
        import asyncio

        tasks = [self.extract(text, schema, context) for text in texts]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def _build_extraction_prompt(
        self,
        text: str,
        schema: Type[BaseModel],
        context: Optional[str]
    ) -> str:
        """Build extraction prompt."""
        schema_name = schema.__name__
        schema_description = schema.__doc__ or f"Extract {schema_name} information"

        prompt_parts = [
            f"Extract {schema_name} information from the following text.",
            f"\n{schema_description}\n",
        ]

        if context:
            prompt_parts.append(f"Context: {context}\n")

        prompt_parts.append(f"Text:\n{text}")

        return "\n".join(prompt_parts)

    def _build_multiple_extraction_prompt(
        self,
        text: str,
        schema: Type[BaseModel],
        context: Optional[str]
    ) -> str:
        """Build prompt for extracting multiple instances."""
        schema_name = schema.__name__
        schema_description = schema.__doc__ or f"Extract {schema_name} information"

        prompt_parts = [
            f"Extract ALL {schema_name} instances from the following text.",
            f"\n{schema_description}\n",
            "Return all instances you can find, even if there are many.",
        ]

        if context:
            prompt_parts.append(f"\nContext: {context}\n")

        prompt_parts.append(f"\nText:\n{text}")

        return "\n".join(prompt_parts)

    def _get_minimal_values(self, schema: Type[BaseModel]) -> Dict[str, Any]:
        """Get minimal valid values for a schema."""
        values = {}

        for field_name, field_info in schema.model_fields.items():
            # Skip fields with defaults
            if field_info.default is not None:
                continue

            # Get field type
            field_type = field_info.annotation

            # Handle optional fields
            origin = get_origin(field_type)
            if origin is not None:
                args = get_args(field_type)
                if type(None) in args:
                    # Optional field, skip
                    continue
                if origin is list:
                    values[field_name] = []
                    continue
                if origin is dict:
                    values[field_name] = {}
                    continue

            # Provide minimal value based on type
            if field_type is str:
                values[field_name] = ""
            elif field_type is int:
                values[field_name] = 0
            elif field_type is float:
                values[field_name] = 0.0
            elif field_type is bool:
                values[field_name] = False
            elif field_type is list:
                values[field_name] = []
            elif field_type is dict:
                values[field_name] = {}

        return values


# Convenience functions for common extractions

async def extract_person(text: str, context: Optional[str] = None) -> Person:
    """Extract person information from text."""
    extractor = SchemaExtractor()
    return await extractor.extract(text, Person, context)


async def extract_organization(text: str, context: Optional[str] = None) -> Organization:
    """Extract organization information from text."""
    extractor = SchemaExtractor()
    return await extractor.extract(text, Organization, context)


async def extract_article(text: str, context: Optional[str] = None) -> Article:
    """Extract article information from text."""
    extractor = SchemaExtractor()
    return await extractor.extract(text, Article, context)


async def extract_contact(text: str, context: Optional[str] = None) -> Contact:
    """Extract contact information from text."""
    extractor = SchemaExtractor()
    return await extractor.extract(text, Contact, context)


async def extract_faqs(text: str, context: Optional[str] = None) -> List[FAQ]:
    """Extract FAQ items from text."""
    extractor = SchemaExtractor()
    return await extractor.extract_multiple(text, FAQ, context)


async def extract_custom(
    text: str,
    schema: Type[T],
    context: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> T:
    """
    Extract custom schema from text.

    Args:
        text: Text to extract from
        schema: Custom Pydantic model class
        context: Additional context or instructions
        api_key: OpenAI API key
        base_url: Base URL for API

    Returns:
        Instance of schema with extracted data
    """
    extractor = SchemaExtractor(api_key=api_key, base_url=base_url)
    return await extractor.extract(text, schema, context)
