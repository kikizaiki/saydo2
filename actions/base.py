"""
Базовый класс для действий.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Используем абсолютный импорт для совместимости
try:
    from drivers.base import Driver, DriverResult
except ImportError:
    # Fallback для относительного импорта
    from ..drivers.base import Driver, DriverResult


@dataclass
class ActionContext:
    """Контекст выполнения действия."""
    driver: Driver
    target: Optional[str] = None
    message: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Инициализация дополнительных параметров."""
        if self.extra_params is None:
            self.extra_params = {}


class Action(ABC):
    """
    Базовый класс для всех действий.
    
    Действие - это абстракция над операциями, которые можно выполнить
    в рамках программы через драйвер (например, "открыть чат", "отправить сообщение").
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        Инициализация действия.
        
        Args:
            name: Название действия (например, "open_chat_only")
            description: Описание действия для документации
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, context: ActionContext) -> DriverResult:
        """
        Выполнить действие.
        
        Args:
            context: Контекст выполнения с драйвером и параметрами
        
        Returns:
            DriverResult с результатом выполнения
        """
        pass
    
    @abstractmethod
    def validate(self, context: ActionContext) -> tuple[bool, Optional[str]]:
        """
        Валидировать возможность выполнения действия.
        
        Args:
            context: Контекст выполнения
        
        Returns:
            (is_valid, error_message) - кортеж с результатом валидации
        """
        pass

