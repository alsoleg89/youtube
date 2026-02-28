from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str, model: str) -> str:
        """Generate a text completion."""
        ...

    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str, model: str) -> dict:
        """Generate a completion and parse the result as JSON."""
        ...
