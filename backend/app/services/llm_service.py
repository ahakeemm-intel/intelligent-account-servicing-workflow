"""
LLM Service — provider abstraction.

Returns a LangChain chat model (ChatOllama or ChatOpenAI) based on LLM_PROVIDER.
All agent nodes import get_llm() so switching providers is a single env var change.
"""
from functools import lru_cache
from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import settings


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """Return the configured LLM. Cached — one instance for the process lifetime."""
    if settings.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
    # Default: Ollama (local)
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
        timeout=60,  # 60s — avoids indefinite hang when Ollama is not running
    )


@lru_cache(maxsize=1)
def get_vision_llm() -> BaseChatModel:
    """Return the vision-capable LLM (for OCR-assist / forgery detection)."""
    if settings.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,  # gpt-4o supports vision
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
    # Ollama vision model (e.g. llava)
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=settings.OLLAMA_VISION_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
        timeout=60,
    )
