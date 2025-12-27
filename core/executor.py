"""
Executor - исполнитель команд с использованием модульной архитектуры.
"""

import os
import sys
from typing import Optional

# Добавляем родительскую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drivers import DriverManager
from actions.telegram_actions import TELEGRAM_ACTIONS
from actions.base import ActionContext
from parsers.telegram_parser import TelegramCommandParser
from parsers.base import ParsedCommand


class CommandExecutor:
    """
    Исполнитель команд.
    
    Управляет выполнением команд через драйверы и действия.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация исполнителя.
        
        Args:
            config_path: Путь к config.json
        """
        self.driver_manager = DriverManager(config_path)
        self.parser = TelegramCommandParser()
        
        # Регистр действий по имени драйвера
        self.action_registry = {
            "telegram": TELEGRAM_ACTIONS,
        }
    
    def execute(self, parsed_command: ParsedCommand, alias_map: dict, result_index_map: dict, 
                disable_whitelist: bool = False) -> bool:
        """
        Выполнить распарсенную команду.
        
        Args:
            parsed_command: Распарсенная команда
            alias_map: Карта алиасов для разрешения имен чатов
            result_index_map: Карта индексов результатов для чатов
            disable_whitelist: Отключить проверку whitelist
        
        Returns:
            True если команда выполнена успешно, False иначе
        """
        # Получаем драйвер
        driver = self.driver_manager.get_driver(parsed_command.driver)
        if not driver:
            print(f"❌ Драйвер '{parsed_command.driver}' не найден или не включен")
            return False
        
        # Разрешаем имя чата через alias_map
        from utils.chat_resolver import resolve_chat
        canonical = resolve_chat(parsed_command.target, alias_map)
        
        if not canonical:
            if disable_whitelist:
                canonical = parsed_command.target
                result_index = 0
                print(f"⚠️  Whitelist отключен, используем '{canonical}' как есть")
            else:
                print(f"❌ Чат '{parsed_command.target}' не в whitelist")
                print(f"💡 Чтобы отключить whitelist, установите: export DISABLE_WHITELIST=1")
                return False
        else:
            result_index = result_index_map.get(canonical)
        
        # Получаем действие
        actions = self.action_registry.get(parsed_command.driver, {})
        action = actions.get(parsed_command.intent)
        
        if not action:
            print(f"❌ Действие '{parsed_command.intent}' не найдено для драйвера '{parsed_command.driver}'")
            return False
        
        # Создаем контекст
        context = ActionContext(
            driver=driver,
            target=canonical,
            message=parsed_command.message,
            extra_params={
                "auto_select": True,
                "result_index": result_index
            }
        )
        
        # Выполняем действие
        result = action.execute(context)
        
        if not result.ok:
            print(f"❌ Ошибка выполнения действия: {result.error}")
            if result.data:
                print(f"   Данные: {result.data}")
        
        return result.ok
    
    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        Распарсить текстовую команду.
        
        Args:
            text: Текст команды
        
        Returns:
            ParsedCommand или None
        """
        return self.parser.parse(text)

