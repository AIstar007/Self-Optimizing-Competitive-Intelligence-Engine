"""
LLM infrastructure module for language model providers.

This module implements the LLMProvider interface for multiple services:
- OpenAI (GPT-4, GPT-3.5-turbo)
- Anthropic (Claude 3 models)
- Ollama (local open-source models)

Features:
    - Async/await support for all operations
    - Streaming response support
    - Token counting and usage tracking
    - Automatic model selection and routing
    - Error handling and retry logic
    - Support for tool calling and function definitions

Usage:
    from core.infrastructure.llm import OpenAIProvider, LLMRouter
    
    # Single provider
    openai = OpenAIProvider(api_key="sk-...")
    response = await openai.complete(messages, model="gpt-4-turbo")
    
    # Intelligent routing
    router = LLMRouter(openai_provider=openai, anthropic_provider=anthropic)
    provider, model = await router.select_model(TaskType.ANALYSIS)
    response = await provider.complete(messages, model)
"""

from core.infrastructure.llm.providers import (
    OpenAIProvider,
    AnthropicProvider,
    OllamaProvider,
    LLMRouter,
)

__all__ = [
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "LLMRouter",
]
