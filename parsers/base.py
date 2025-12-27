"""
Базовые классы для парсеров команд.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class ParsedCommand:
    """
    Результат парсинга команды.
    
    Attributes:
        intent: Тип действия (например, "open_chat_only", "send_message")
        target: Цель действия (например, имя чата)
        message: Текст сообщения (если применимо)
        driver: Имя драйвера для выполнения команды
    """
    intent: str
    target: Optional[str] = None
    message: Optional[str] = None
    driver: str = "telegram"  # По умолчанию Telegram
    
    def is_valid(self) -> bool:
        """Проверка валидности распарсенной команды."""
        return bool(self.intent and self.target)


class CommandParser(ABC):
    """
    Базовый класс для парсеров команд.
    
    Парсер превращает естественный язык пользователя в структурированную команду.
    """
    
    def __init__(self, driver_name: str = "telegram"):
        """
        Инициализация парсера.
        
        Args:
            driver_name: Имя драйвера, для которого работает парсер
        """
        self.driver_name = driver_name
    
    @abstractmethod
    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        Распарсить текстовую команду.
        
        Args:
            text: Текст команды от пользователя
        
        Returns:
            ParsedCommand или None, если команда не распознана
        """
        pass
    
    @abstractmethod
    def get_supported_intents(self) -> List[str]:
        """
        Получить список поддерживаемых намерений (intents).
        
        Returns:
            Список строк с названиями intents
        """
        pass

