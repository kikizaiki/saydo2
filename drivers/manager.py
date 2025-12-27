"""
Менеджер драйверов - управление и инициализация драйверов.
"""

import json
import os
from typing import Dict, Optional

from .base import Driver
from .telegram import TelegramDriver

# Регистр доступных драйверов
_DRIVER_CLASSES = {
    "telegram": TelegramDriver,
}


class DriverManager:
    """
    Менеджер для инициализации и управления драйверами.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация менеджера драйверов.
        
        Args:
            config_path: Путь к config.json (если None, используется config/config.json)
        """
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(base_dir, "config", "config.json")
        
        self.config_path = config_path
        self.config = self._load_config()
        self._drivers: Dict[str, Driver] = {}
    
    def _load_config(self) -> Dict:
        """Загрузить конфигурацию из JSON."""
        if not os.path.exists(self.config_path):
            # Используем конфигурацию по умолчанию
            return {
                "drivers": {
                    "telegram": {
                        "enabled": True,
                        "hammer_url": os.environ.get("HAMMER_URL", "http://127.0.0.1:7733"),
                        "timeout": 5,
                        "tracked_chats_path": "tracked_chats.json"
                    }
                },
                "default_driver": "telegram"
            }
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_driver(self, driver_name: Optional[str] = None) -> Optional[Driver]:
        """
        Получить драйвер по имени.
        
        Args:
            driver_name: Имя драйвера (если None, используется default_driver из конфига)
        
        Returns:
            Экземпляр драйвера или None, если драйвер не найден/не включен
        """
        if driver_name is None:
            driver_name = self.config.get("default_driver", "telegram")
        
        # Проверяем кэш
        if driver_name in self._drivers:
            return self._drivers[driver_name]
        
        # Проверяем, есть ли драйвер в конфигурации
        drivers_config = self.config.get("drivers", {})
        if driver_name not in drivers_config:
            return None
        
        driver_config = drivers_config[driver_name]
        
        # Проверяем, включен ли драйвер
        if not driver_config.get("enabled", False):
            return None
        
        # Инициализируем драйвер
        driver_class = _DRIVER_CLASSES.get(driver_name)
        if driver_class is None:
            return None
        
        try:
            driver = driver_class(driver_config)
            self._drivers[driver_name] = driver
            return driver
        except Exception as e:
            print(f"❌ Ошибка инициализации драйвера '{driver_name}': {e}")
            return None
    
    def list_available_drivers(self) -> list[str]:
        """Получить список доступных драйверов."""
        return list(_DRIVER_CLASSES.keys())
    
    def list_enabled_drivers(self) -> list[str]:
        """Получить список включенных драйверов из конфигурации."""
        drivers_config = self.config.get("drivers", {})
        return [
            name for name, config in drivers_config.items()
            if config.get("enabled", False) and name in _DRIVER_CLASSES
        ]

