"""
LLM router with Requesty.ai integration for intelligent model selection and routing.
Uses OpenAI client with base_url override to route through Requesty.ai.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

logger = logging.getLogger(__name__)


class ModelTier(str, Enum):
    """Model tier for cost/performance tradeoffs."""
    FAST = "fast"  # Fast, cheap models
    SMART = "smart"  # Balanced models
    EXPERT = "expert"  # Most capable models
    VISION = "vision"  # Vision-capable models
    LONG_CONTEXT = "long_context"  # Long context models


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str
    provider: str  # openai, anthropic, google, etc.
    tier: ModelTier
    max_tokens: int
    supports_streaming: bool = True
    supports_functions: bool = True
    supports_vision: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    context_window: int = 4096


# Pre-configured models (Requesty model names)
MODELS = {
    # OpenAI models
    "gpt-4o": ModelConfig(
        name="openai/gpt-4o",
        provider="openai",
        tier=ModelTier.EXPERT,
        max_tokens=16384,
        supports_vision=True,
        context_window=128000,
        cost_per_1k_input=2.5,
        cost_per_1k_output=10.0,
    ),
    "gpt-4o-mini": ModelConfig(
        name="openai/gpt-4o-mini",
        provider="openai",
        tier=ModelTier.SMART,
        max_tokens=16384,
        supports_vision=True,
        context_window=128000,
        cost_per_1k_input=0.15,
        cost_per_1k_output=0.6,
    ),
    "gpt-3.5-turbo": ModelConfig(
        name="openai/gpt-3.5-turbo",
        provider="openai",
        tier=ModelTier.FAST,
        max_tokens=4096,
        context_window=16385,
        cost_per_1k_input=0.5,
        cost_per_1k_output=1.5,
    ),
    # Anthropic models
    "claude-3-5-sonnet": ModelConfig(
        name="anthropic/claude-3-5-sonnet-20241022",
        provider="anthropic",
        tier=ModelTier.EXPERT,
        max_tokens=8192,
        supports_vision=True,
        context_window=200000,
        cost_per_1k_input=3.0,
        cost_per_1k_output=15.0,
    ),
    "claude-3-5-haiku": ModelConfig(
        name="anthropic/claude-3-5-haiku-20241022",
        provider="anthropic",
        tier=ModelTier.FAST,
        max_tokens=8192,
        context_window=200000,
        cost_per_1k_input=0.8,
        cost_per_1k_output=4.0,
    ),
    # Google models
    "gemini-pro": ModelConfig(
        name="google/gemini-pro",
        provider="google",
        tier=ModelTier.SMART,
        max_tokens=8192,
        context_window=32760,
        cost_per_1k_input=0.5,
        cost_per_1k_output=1.5,
    ),
}


@dataclass
class RoutingStrategy:
    """Strategy for routing requests to models."""
    prefer_tier: Optional[ModelTier] = None
    max_cost_per_request: Optional[float] = None
    require_streaming: bool = False
    require_functions: bool = False
    require_vision: bool = False
    preferred_providers: List[str] = field(default_factory=list)
    fallback_models: List[str] = field(default_factory=list)


class LLMRouter:
    """
    Intelligent LLM router with Requesty.ai integration.
    Routes requests to appropriate models based on requirements and costs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: str = "gpt-4o",
        enable_fallback: bool = True,
    ):
        """
        Initialize LLM router.

        Args:
            api_key: Requesty API key
            base_url: Requesty base URL
            default_model: Default model to use
            enable_fallback: Enable automatic fallback on errors
        """
        self.api_key = api_key or os.getenv("REQUESTY_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("REQUESTY_BASE_URL", "https://router.requesty.ai/v1")
        self.default_model = default_model
        self.enable_fallback = enable_fallback

        if not self.api_key:
            raise ValueError("API key is required. Set REQUESTY_API_KEY or OPENAI_API_KEY environment variable.")

        # Initialize OpenAI client with Requesty base URL
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        # Track usage
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0

    def select_model(
        self,
        strategy: Optional[RoutingStrategy] = None,
        estimated_input_tokens: Optional[int] = None,
    ) -> str:
        """
        Select the best model based on routing strategy.

        Args:
            strategy: Routing strategy
            estimated_input_tokens: Estimated input tokens

        Returns:
            Selected model name
        """
        if not strategy:
            return MODELS[self.default_model].name

        # Filter models based on requirements
        candidates = []

        for key, model in MODELS.items():
            # Check tier preference
            if strategy.prefer_tier and model.tier != strategy.prefer_tier:
                continue

            # Check capabilities
            if strategy.require_streaming and not model.supports_streaming:
                continue
            if strategy.require_functions and not model.supports_functions:
                continue
            if strategy.require_vision and not model.supports_vision:
                continue

            # Check providers
            if strategy.preferred_providers and model.provider not in strategy.preferred_providers:
                continue

            # Check cost
            if strategy.max_cost_per_request and estimated_input_tokens:
                estimated_cost = (
                    (estimated_input_tokens / 1000) * model.cost_per_1k_input +
                    (estimated_input_tokens / 1000) * model.cost_per_1k_output  # Rough estimate
                )
                if estimated_cost > strategy.max_cost_per_request:
                    continue

            candidates.append(model)

        if not candidates:
            logger.warning("No models match routing strategy, using default")
            return MODELS[self.default_model].name

        # Select cheapest among candidates
        selected = min(candidates, key=lambda m: m.cost_per_1k_input)
        logger.info(f"Selected model: {selected.name} (tier: {selected.tier})")

        return selected.name

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        strategy: Optional[RoutingStrategy] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ChatCompletion, AsyncIterator[ChatCompletionChunk]]:
        """
        Create a chat completion.

        Args:
            messages: Chat messages
            model: Model name (overrides strategy)
            strategy: Routing strategy
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            **kwargs: Additional parameters

        Returns:
            ChatCompletion or async iterator of chunks
        """
        # Select model
        if not model:
            # Estimate input tokens (rough approximation)
            estimated_tokens = sum(len(m.get("content", "").split()) * 1.3 for m in messages)
            model = self.select_model(strategy, int(estimated_tokens))
        else:
            # Ensure model has provider prefix for Requesty
            if "/" not in model and model in MODELS:
                model = MODELS[model].name

        # Make request
        try:
            self.total_requests += 1

            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs
            )

            # Track usage
            if not stream and hasattr(response, "usage") and response.usage:
                self.total_tokens += response.usage.total_tokens
                # Estimate cost (rough)
                self._update_cost(model, response.usage.total_tokens)

            return response

        except Exception as e:
            logger.error(f"Chat completion failed with {model}: {e}")

            # Try fallback if enabled
            if self.enable_fallback and strategy and strategy.fallback_models:
                for fallback_model in strategy.fallback_models:
                    try:
                        logger.info(f"Trying fallback model: {fallback_model}")
                        return await self.client.chat.completions.create(
                            model=fallback_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stream=stream,
                            **kwargs
                        )
                    except Exception as fallback_error:
                        logger.error(f"Fallback failed with {fallback_model}: {fallback_error}")
                        continue

            raise

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        strategy: Optional[RoutingStrategy] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Simple text completion.

        Args:
            prompt: User prompt
            model: Model name
            strategy: Routing strategy
            system_prompt: System prompt
            **kwargs: Additional parameters

        Returns:
            Completion text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = await self.chat_completion(
            messages=messages,
            model=model,
            strategy=strategy,
            stream=False,
            **kwargs
        )

        return response.choices[0].message.content

    async def complete_with_json(
        self,
        prompt: str,
        model: Optional[str] = None,
        strategy: Optional[RoutingStrategy] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Complete with JSON response.

        Args:
            prompt: User prompt
            model: Model name
            strategy: Routing strategy
            **kwargs: Additional parameters

        Returns:
            Parsed JSON response
        """
        import json

        system_prompt = "You are a helpful assistant that responds in JSON format."

        response_text = await self.complete(
            prompt=prompt,
            model=model,
            strategy=strategy,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
            **kwargs
        )

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response")
            raise

    async def batch_complete(
        self,
        prompts: List[str],
        model: Optional[str] = None,
        strategy: Optional[RoutingStrategy] = None,
        **kwargs
    ) -> List[str]:
        """
        Batch completion for multiple prompts.

        Args:
            prompts: List of prompts
            model: Model name
            strategy: Routing strategy
            **kwargs: Additional parameters

        Returns:
            List of completions
        """
        import asyncio

        tasks = [
            self.complete(prompt, model=model, strategy=strategy, **kwargs)
            for prompt in prompts
        ]

        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "estimated_cost": self.total_cost,
        }

    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0

    def _update_cost(self, model_name: str, tokens: int):
        """Update cost estimation."""
        # Find model config
        for model in MODELS.values():
            if model.name == model_name:
                # Rough estimate: assume 50/50 input/output split
                cost = (tokens / 2000) * (model.cost_per_1k_input + model.cost_per_1k_output)
                self.total_cost += cost
                break


# Global router instance
_global_router: Optional[LLMRouter] = None


def get_global_router() -> LLMRouter:
    """Get or create global router instance."""
    global _global_router
    if _global_router is None:
        _global_router = LLMRouter()
    return _global_router


def set_global_router(router: LLMRouter):
    """Set global router instance."""
    global _global_router
    _global_router = router


# Convenience functions

async def complete(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.7,
    **kwargs
) -> str:
    """
    Simple completion using global router.

    Args:
        prompt: User prompt
        model: Model name
        temperature: Sampling temperature
        **kwargs: Additional parameters

    Returns:
        Completion text
    """
    router = get_global_router()
    return await router.complete(prompt, model=model, temperature=temperature, **kwargs)


async def complete_fast(prompt: str, **kwargs) -> str:
    """Complete with fast model."""
    strategy = RoutingStrategy(prefer_tier=ModelTier.FAST)
    router = get_global_router()
    return await router.complete(prompt, strategy=strategy, **kwargs)


async def complete_smart(prompt: str, **kwargs) -> str:
    """Complete with smart model."""
    strategy = RoutingStrategy(prefer_tier=ModelTier.SMART)
    router = get_global_router()
    return await router.complete(prompt, strategy=strategy, **kwargs)


async def complete_expert(prompt: str, **kwargs) -> str:
    """Complete with expert model."""
    strategy = RoutingStrategy(prefer_tier=ModelTier.EXPERT)
    router = get_global_router()
    return await router.complete(prompt, strategy=strategy, **kwargs)


async def complete_with_json(prompt: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Complete with JSON response.

    Args:
        prompt: User prompt
        model: Model name
        **kwargs: Additional parameters

    Returns:
        Parsed JSON response
    """
    router = get_global_router()
    return await router.complete_with_json(prompt, model=model, **kwargs)
