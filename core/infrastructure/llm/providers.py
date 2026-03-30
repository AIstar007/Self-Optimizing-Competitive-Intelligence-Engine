"""
LLM provider implementations for multiple language model services.

This module implements the LLMProvider interface for OpenAI, Anthropic, and Ollama,
providing unified async access to various language models with automatic model selection,
streaming support, and comprehensive error handling.

Providers:
    - OpenAI: GPT-4, GPT-3.5-turbo, and other OpenAI models
    - Anthropic: Claude models (Claude 3 Opus, Sonnet, Haiku)
    - Ollama: Local open-source models
    - LLMRouter: Automatic model selection based on task and requirements
"""

import asyncio
import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import AsyncGenerator, Optional

from core.domain import (
    LLMProvider,
    ModelProvider,
    TaskType,
    Message,
    ModelConfig,
    CompletionResponse,
    EmbeddingResponse,
    TokenUsage,
    ToolDefinition,
    ToolCall,
)


class OpenAIProvider(LLMProvider):
    """
    OpenAI language model provider.
    
    Supports GPT-4, GPT-3.5-turbo, and other OpenAI models.
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
        """
        import os
        from openai import AsyncOpenAI

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided and OPENAI_API_KEY environment variable not set"
            )
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.provider = ModelProvider.OPENAI

    async def complete(
        self,
        messages: list[Message],
        model: str = "gpt-4-turbo",
        config: Optional[ModelConfig] = None,
    ) -> CompletionResponse:
        """
        Get completion from OpenAI model.
        
        Args:
            messages: List of messages for conversation
            model: Model name (default: gpt-4-turbo)
            config: Model configuration parameters
            
        Returns:
            CompletionResponse with content and token usage
        """
        if config is None:
            config = ModelConfig()

        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                timeout=config.timeout,
            )

            return CompletionResponse(
                content=response.choices[0].message.content,
                model=response.model,
                provider=self.provider,
                usage=TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                ),
                finish_reason=response.choices[0].finish_reason,
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

    async def complete_stream(
        self,
        messages: list[Message],
        model: str = "gpt-4-turbo",
        config: Optional[ModelConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Get streaming completion from OpenAI model.
        
        Yields:
            Streamed content chunks as they arrive
        """
        if config is None:
            config = ModelConfig()

        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ],
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                stream=True,
                timeout=config.timeout,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming error: {str(e)}")

    async def embed(self, text: str, model: str = "text-embedding-3-small") -> EmbeddingResponse:
        """
        Get embeddings from OpenAI model.
        
        Args:
            text: Text to embed
            model: Embedding model name
            
        Returns:
            EmbeddingResponse with vector embedding
        """
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=model,
            )

            return EmbeddingResponse(
                embedding=response.data[0].embedding,
                model=response.model,
                provider=self.provider,
                usage=TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=0,
                    total_tokens=response.usage.total_tokens,
                ),
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI embedding error: {str(e)}")

    async def tokenize(self, text: str, model: str = "gpt-4-turbo") -> int:
        """
        Count tokens in text for a model.
        
        Args:
            text: Text to tokenize
            model: Model to use for tokenization
            
        Returns:
            Number of tokens
        """
        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model(model)
            tokens = encoding.encode(text)
            return len(tokens)
        except Exception:
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4

    async def get_models(self) -> list[dict]:
        """
        Get available OpenAI models.
        
        Returns:
            List of available model information
        """
        try:
            models = await self.client.models.list()
            return [
                {
                    "id": m.id,
                    "provider": "openai",
                    "owned_by": m.owned_by,
                }
                for m in models.data
            ]
        except Exception:
            # Return known models if API fails
            return [
                {"id": "gpt-4-turbo", "provider": "openai"},
                {"id": "gpt-4", "provider": "openai"},
                {"id": "gpt-3.5-turbo", "provider": "openai"},
            ]


class AnthropicProvider(LLMProvider):
    """
    Anthropic language model provider.
    
    Supports Claude 3 models (Opus, Sonnet, Haiku).
    Requires ANTHROPIC_API_KEY environment variable.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        """
        import os
        from anthropic import AsyncAnthropic

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not provided and ANTHROPIC_API_KEY environment variable not set"
            )
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.provider = ModelProvider.ANTHROPIC

    async def complete(
        self,
        messages: list[Message],
        model: str = "claude-3-opus-20240229",
        config: Optional[ModelConfig] = None,
    ) -> CompletionResponse:
        """
        Get completion from Anthropic model.
        
        Args:
            messages: List of messages for conversation
            model: Model name (default: claude-3-opus-20240229)
            config: Model configuration parameters
            
        Returns:
            CompletionResponse with content and token usage
        """
        if config is None:
            config = ModelConfig()

        # Filter out system messages for Anthropic
        system_messages = [m.content for m in messages if m.role == "system"]
        user_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role != "system"
        ]

        try:
            response = await self.client.messages.create(
                model=model,
                max_tokens=config.max_tokens,
                system=system_messages[0] if system_messages else None,
                messages=user_messages,
                temperature=config.temperature,
                timeout=config.timeout,
            )

            return CompletionResponse(
                content=response.content[0].text,
                model=response.model,
                provider=self.provider,
                usage=TokenUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                ),
                finish_reason=response.stop_reason,
            )
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")

    async def complete_stream(
        self,
        messages: list[Message],
        model: str = "claude-3-opus-20240229",
        config: Optional[ModelConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Get streaming completion from Anthropic model.
        
        Yields:
            Streamed content chunks
        """
        if config is None:
            config = ModelConfig()

        system_messages = [m.content for m in messages if m.role == "system"]
        user_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role != "system"
        ]

        try:
            async with self.client.messages.stream(
                model=model,
                max_tokens=config.max_tokens,
                system=system_messages[0] if system_messages else None,
                messages=user_messages,
                temperature=config.temperature,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise RuntimeError(f"Anthropic streaming error: {str(e)}")

    async def embed(self, text: str, model: str = "claude-3-opus-20240229") -> EmbeddingResponse:
        """
        Anthropic doesn't provide native embeddings, use OpenAI or other provider.
        
        Raises:
            NotImplementedError: Anthropic doesn't support embeddings
        """
        raise NotImplementedError(
            "Anthropic doesn't provide native embeddings. Use OpenAI provider instead."
        )

    async def tokenize(self, text: str, model: str = "claude-3-opus-20240229") -> int:
        """
        Estimate token count for Anthropic model.
        
        Args:
            text: Text to tokenize
            model: Model name
            
        Returns:
            Estimated number of tokens
        """
        # Anthropic: rough estimate (1 token ≈ 3-4 characters)
        return len(text) // 3

    async def get_models(self) -> list[dict]:
        """
        Get available Anthropic models.
        
        Returns:
            List of known Anthropic models
        """
        return [
            {
                "id": "claude-3-opus-20240229",
                "provider": "anthropic",
                "capabilities": ["text", "vision"],
            },
            {
                "id": "claude-3-sonnet-20240229",
                "provider": "anthropic",
                "capabilities": ["text", "vision"],
            },
            {
                "id": "claude-3-haiku-20240307",
                "provider": "anthropic",
                "capabilities": ["text", "vision"],
            },
        ]


class OllamaProvider(LLMProvider):
    """
    Ollama local LLM provider.
    
    Supports running open-source models locally (Llama 2, Mistral, etc.).
    Requires Ollama to be running at specified endpoint.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.
        
        Args:
            base_url: Ollama API endpoint (default: http://localhost:11434)
        """
        import httpx

        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=300)
        self.provider = ModelProvider.OLLAMA

    async def complete(
        self,
        messages: list[Message],
        model: str = "llama2",
        config: Optional[ModelConfig] = None,
    ) -> CompletionResponse:
        """
        Get completion from Ollama model.
        
        Args:
            messages: List of messages
            model: Model name (default: llama2)
            config: Model configuration
            
        Returns:
            CompletionResponse
        """
        if config is None:
            config = ModelConfig()

        try:
            # Combine messages into prompt
            prompt = self._format_messages(messages)

            response = await self.client.post(
                "/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": config.temperature,
                },
            )
            response.raise_for_status()
            data = response.json()

            return CompletionResponse(
                content=data.get("response", ""),
                model=model,
                provider=self.provider,
                usage=TokenUsage(
                    prompt_tokens=0,  # Ollama doesn't provide token counts
                    completion_tokens=0,
                    total_tokens=0,
                ),
                finish_reason="stop",
            )
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {str(e)}")

    async def complete_stream(
        self,
        messages: list[Message],
        model: str = "llama2",
        config: Optional[ModelConfig] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Get streaming completion from Ollama model.
        
        Yields:
            Streamed content chunks
        """
        if config is None:
            config = ModelConfig()

        try:
            prompt = self._format_messages(messages)

            response = await self.client.post(
                "/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "temperature": config.temperature,
                },
            )
            response.raise_for_status()

            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
        except Exception as e:
            raise RuntimeError(f"Ollama streaming error: {str(e)}")

    async def embed(self, text: str, model: str = "nomic-embed-text") -> EmbeddingResponse:
        """
        Get embeddings from Ollama model.
        
        Args:
            text: Text to embed
            model: Embedding model name
            
        Returns:
            EmbeddingResponse
        """
        try:
            response = await self.client.post(
                "/api/embeddings",
                json={
                    "model": model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            return EmbeddingResponse(
                embedding=data.get("embedding", []),
                model=model,
                provider=self.provider,
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )
        except Exception as e:
            raise RuntimeError(f"Ollama embedding error: {str(e)}")

    async def tokenize(self, text: str, model: str = "llama2") -> int:
        """
        Estimate token count (Ollama doesn't provide exact counts).
        
        Args:
            text: Text to tokenize
            model: Model name
            
        Returns:
            Estimated token count
        """
        # Rough estimate
        return len(text) // 4

    async def get_models(self) -> list[dict]:
        """
        Get available Ollama models.
        
        Returns:
            List of available models
        """
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()

            return [
                {
                    "id": m["name"],
                    "provider": "ollama",
                    "size": m.get("size"),
                }
                for m in data.get("models", [])
            ]
        except Exception:
            return [
                {"id": "llama2", "provider": "ollama"},
                {"id": "mistral", "provider": "ollama"},
                {"id": "neural-chat", "provider": "ollama"},
            ]

    def _format_messages(self, messages: list[Message]) -> str:
        """Format messages into a single prompt string."""
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}\n")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}\n")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}\n")

        return "".join(prompt_parts)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class LLMRouter:
    """
    Intelligent router for selecting the best LLM provider and model
    based on task type, complexity, latency requirements, and cost.
    """

    def __init__(
        self,
        openai_provider: Optional[OpenAIProvider] = None,
        anthropic_provider: Optional[AnthropicProvider] = None,
        ollama_provider: Optional[OllamaProvider] = None,
    ):
        """
        Initialize LLM router with available providers.
        
        Args:
            openai_provider: OpenAI provider instance
            anthropic_provider: Anthropic provider instance
            ollama_provider: Ollama provider instance
        """
        self.providers = {}
        if openai_provider:
            self.providers[ModelProvider.OPENAI] = openai_provider
        if anthropic_provider:
            self.providers[ModelProvider.ANTHROPIC] = anthropic_provider
        if ollama_provider:
            self.providers[ModelProvider.OLLAMA] = ollama_provider

    async def select_model(
        self,
        task_type: TaskType,
        complexity: str = "medium",
        latency_sensitive: bool = False,
        cost_sensitive: bool = False,
    ) -> tuple[LLMProvider, str]:
        """
        Select best provider and model for task.
        
        Args:
            task_type: Type of task
            complexity: Task complexity (low, medium, high)
            latency_sensitive: Whether response time is critical
            cost_sensitive: Whether cost is important
            
        Returns:
            Tuple of (provider, model_name)
        """
        # Simple routing logic - can be enhanced with more sophisticated rules
        if latency_sensitive and self.providers.get(ModelProvider.OLLAMA):
            # Use local model for speed
            return self.providers[ModelProvider.OLLAMA], "llama2"

        if cost_sensitive and self.providers.get(ModelProvider.OLLAMA):
            # Use local model for cost
            return self.providers[ModelProvider.OLLAMA], "llama2"

        # Default: use Claude for complex tasks, GPT for others
        if complexity == "high" and self.providers.get(ModelProvider.ANTHROPIC):
            return self.providers[ModelProvider.ANTHROPIC], "claude-3-opus-20240229"

        if self.providers.get(ModelProvider.OPENAI):
            return self.providers[ModelProvider.OPENAI], "gpt-4-turbo"

        # Fallback
        if self.providers.get(ModelProvider.ANTHROPIC):
            return self.providers[ModelProvider.ANTHROPIC], "claude-3-sonnet-20240229"

        return self.providers[ModelProvider.OLLAMA], "llama2"

    async def route(
        self,
        messages: list[Message],
        task_type: TaskType,
        stream: bool = False,
    ) -> CompletionResponse | AsyncGenerator[str, None]:
        """
        Route request to best provider and get response.
        
        Args:
            messages: Conversation messages
            task_type: Type of task
            stream: Whether to stream response
            
        Returns:
            CompletionResponse or async generator for streaming
        """
        provider, model = await self.select_model(task_type)

        if stream:
            return provider.complete_stream(messages, model)
        else:
            return await provider.complete(messages, model)


__all__ = [
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "LLMRouter",
]
