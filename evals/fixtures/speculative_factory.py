"""Speculative factory architecture with single implementor and unearned generality."""
from abc import ABC, abstractmethod

class IMessageFormatter(ABC):
    @abstractmethod
    def format_text(self, text: str) -> str:
        pass

class IFormatterFactory(ABC):
    @abstractmethod
    def create_formatter(self) -> IMessageFormatter:
        pass

class StandardUppercaseFormatter(IMessageFormatter):
    """The only implementor in the entire repository."""
    def format_text(self, text: str) -> str:
        return text.upper()

class StandardFormatterFactory(IFormatterFactory):
    def create_formatter(self) -> IMessageFormatter:
        return StandardUppercaseFormatter()

class FormatterRegistry:
    """YAGNI: 3 layers of indirection to uppercase a string."""
    def __init__(self):
        self._factories = {"standard": StandardFormatterFactory()}

    def get_formatted(self, key: str, text: str) -> str:
        factory = self._factories.get(key)
        formatter = factory.create_formatter()
        return formatter.format_text(text)
