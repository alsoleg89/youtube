from app.core.config import settings
from app.providers.base_llm import BaseLLMProvider

_PROVIDERS = {
    "openai": "app.providers.openai_provider.OpenAIProvider",
    "local_ollama": "app.providers.local_llm_provider.LocalLLMProvider",
}


def get_llm_provider() -> BaseLLMProvider:
    provider_key = settings.llm_provider
    dotted = _PROVIDERS.get(provider_key)
    if dotted is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER={provider_key!r}. "
            f"Supported: {', '.join(_PROVIDERS)}"
        )
    module_path, class_name = dotted.rsplit(".", 1)

    import importlib

    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls()
