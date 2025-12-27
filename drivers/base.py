"""
Базовый класс для всех драйверов.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from dataclasses import dataclass


@dataclass
class DriverResult:
    """Результат выполнения действия драйвером."""
    ok: bool
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    def __bool__(self) -> bool:
        """Позволяет использовать DriverResult как bool."""
        return self.ok


class Driver(ABC):
    """
    Базовый класс для всех драйверов программ.
    
    Каждый драйвер управляет конкретной программой и может выполнять
    различные действия через неё.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация драйвера.
        
        Args:
            config: Конфигурация драйвера из config.json
        """
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def open_chat(self, target: str, **kwargs) -> DriverResult:
        """
        Открыть чат/диалог в программе.
        
        Args:
            target: Имя чата/контакта для открытия
            **kwargs: Дополнительные параметры (например, result_index для Telegram)
        
        Returns:
            DriverResult с результатом операции
        """
        pass
    
    @abstractmethod
    def send_message(self, text: str, **kwargs) -> DriverResult:
        """
        Отправить текстовое сообщение.
        
        Args:
            text: Текст сообщения
            **kwargs: Дополнительные параметры
        
        Returns:
            DriverResult с результатом операции
        """
        pass
    
    @abstractmethod
    def paste_from_clipboard(self, **kwargs) -> DriverResult:
        """
        Вставить содержимое буфера обмена.
        
        Args:
            **kwargs: Дополнительные параметры
        
        Returns:
            DriverResult с результатом операции
        """
        pass
    
    @property
    @abstractmethod
    def supported_actions(self) -> list[str]:
        """
        Список поддерживаемых действий (для документации и валидации).
        
        Returns:
            Список строк с названиями действий, например: ["open_chat", "send_message", "paste"]
        """
        pass

