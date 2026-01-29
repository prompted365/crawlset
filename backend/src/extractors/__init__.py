"""
Data extraction module with LLM-powered extractors.
"""
from .llm_router import (
    LLMRouter,
    ModelConfig,
    ModelTier,
    RoutingStrategy,
    complete,
    complete_expert,
    complete_fast,
    complete_smart,
    complete_with_json,
    get_global_router,
    set_global_router,
)
from .prompt_extractor import (
    EXTRACTION_TEMPLATES,
    ExtractionResult,
    ExtractionTemplate,
    PromptExtractor,
    analyze_sentiment,
    extract_key_points,
    extract_with_prompt,
    summarize_text,
)
from .requesty_client import RequestyClient, RequestyError
from .schema_extractor import (
    Article,
    Contact,
    Event,
    FAQ,
    Organization,
    Person,
    Product,
    ResearchPaper,
    SchemaExtractor,
    extract_article,
    extract_contact,
    extract_custom,
    extract_faqs,
    extract_organization,
    extract_person,
)

__all__ = [
    # Requesty Client
    "RequestyClient",
    "RequestyError",
    # LLM Router
    "LLMRouter",
    "ModelConfig",
    "ModelTier",
    "RoutingStrategy",
    "complete",
    "complete_expert",
    "complete_fast",
    "complete_smart",
    "complete_with_json",
    "get_global_router",
    "set_global_router",
    # Prompt Extractor
    "EXTRACTION_TEMPLATES",
    "ExtractionResult",
    "ExtractionTemplate",
    "PromptExtractor",
    "analyze_sentiment",
    "extract_key_points",
    "extract_with_prompt",
    "summarize_text",
    # Schema Extractor
    "Article",
    "Contact",
    "Event",
    "FAQ",
    "Organization",
    "Person",
    "Product",
    "ResearchPaper",
    "SchemaExtractor",
    "extract_article",
    "extract_contact",
    "extract_custom",
    "extract_faqs",
    "extract_organization",
    "extract_person",
]
