"""
agt_sea — LLM Provider Abstraction

A single entry point that returns a LangChain chat model for whichever
provider is configured. All agents import from here rather than
instantiating models directly.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from agt_sea.config import get_llm_provider, get_model_name
from agt_sea.models.state import LLMProvider


def get_llm(
    provider: LLMProvider | None = None,
    temperature: float = 0.7,
) -> BaseChatModel:
    """Return a LangChain chat model for the specified provider.

    Args:
        provider: Which LLM provider to use. Defaults to the value
            from config / environment.
        temperature: Sampling temperature. Higher values produce more
            creative output.

    Returns:
        A BaseChatModel instance ready to use with .invoke(),
        .stream(), or .with_structured_output().
    """
    provider = provider or get_llm_provider()
    model_name = get_model_name(provider)

    if provider == LLMProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
        )

    if provider == LLMProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
        )

    if provider == LLMProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
        )

    # This should be unreachable due to the enum, but guards against
    # future additions that aren't wired up yet.
    valid = ", ".join(p.value for p in LLMProvider)
    raise ValueError(f"Unsupported provider '{provider}'. Must be one of: {valid}")