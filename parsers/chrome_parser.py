"""
Парсер команд для Chrome.
"""

import re
from typing import Optional, List

# Используем абсолютный импорт для совместимости
try:
    from parsers.base import CommandParser, ParsedCommand
    from utils.speech_corrections import normalize_keywords
except ImportError:
    # Fallback для относительного импорта
    from .base import CommandParser, ParsedCommand
    try:
        from utils.speech_corrections import normalize_keywords
    except ImportError:
        # Если модуль недоступен, используем простую функцию
        def normalize_keywords(kw: str) -> str:
            # Убираем лишние слова
            stop_words = ["chrome", "браузер", "вкладка", "вкладку", "открой", "найди"]
            words = kw.lower().split()
            filtered = [w for w in words if w not in stop_words]
            return " ".join(filtered).strip()


class ChromeCommandParser(CommandParser):
    """
    Парсер команд для управления Chrome.
    
    Распознает команды вида:
    - "открой вкладку X"
    - "открой в Chrome X"
    - "открой в C X"
    - "найди вкладку X"
    """
    
    def __init__(self):
        super().__init__(driver_name="chrome")
    
    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        Распарсить текстовую команду для Chrome.
        
        Args:
            text: Текст команды от пользователя
        
        Returns:
            ParsedCommand или None, если команда не распознана
        """
        t = (text or "").strip()
        
        # Нормализация: lowercase, убираем лишние пробелы
        t_lower = t.lower()
        t_lower = re.sub(r'\s+', ' ', t_lower).strip()
        
        # Паттерны для распознавания команд открытия вкладки
        
        # 1) "открой вкладку X" или "открой вкладку с X"
        m = re.search(
            r"""открой\s+вкладку\s+(?:с\s+)?(.+?)\s*$""",
            t_lower,
            flags=re.IGNORECASE,
        )
        if m:
            keywords = m.group(1).strip()
            if keywords:
                # Нормализуем ключевые слова (убираем лишние слова, исправляем ошибки)
                keywords = normalize_keywords(keywords)
                if keywords:
                    return ParsedCommand(
                        intent="open_tab",
                        target=keywords,
                        driver="chrome"
                    )
        
        # 2) "открой в Chrome X" или "открой в Chrome вкладку X"
        m = re.search(
            r"""открой\s+в\s+chrome\s+(?:вкладку\s+)?(.+?)\s*$""",
            t_lower,
            flags=re.IGNORECASE,
        )
        if m:
            keywords = m.group(1).strip()
            if keywords:
                # Нормализуем ключевые слова (убираем лишние слова, исправляем ошибки)
                keywords = normalize_keywords(keywords)
                if keywords:
                    return ParsedCommand(
                        intent="open_tab",
                        target=keywords,
                        driver="chrome"
                    )
        
        # 3) "открой в C X" (C = Chrome)
        m = re.search(
            r"""открой\s+в\s+[cс]\s+(?:вкладку\s+)?(.+?)\s*$""",
            t_lower,
            flags=re.IGNORECASE,
        )
        if m:
            keywords = m.group(1).strip()
            if keywords:
                # Нормализуем ключевые слова (убираем лишние слова, исправляем ошибки)
                keywords = normalize_keywords(keywords)
                if keywords:
                    return ParsedCommand(
                        intent="open_tab",
                        target=keywords,
                        driver="chrome"
                    )
        
        # 4) "найди вкладку X" или "найди в Chrome X"
        m = re.search(
            r"""найди\s+(?:в\s+chrome\s+)?(?:вкладку\s+)?(.+?)\s*$""",
            t_lower,
            flags=re.IGNORECASE,
        )
        if m:
            keywords = m.group(1).strip()
            if keywords:
                # Нормализуем ключевые слова (убираем лишние слова, исправляем ошибки)
                keywords = normalize_keywords(keywords)
                if keywords:
                    return ParsedCommand(
                        intent="open_tab",
                        target=keywords,
                        driver="chrome"
                    )
        
        # 5) "открой X в Chrome" или "открой X в C"
        m = re.search(
            r"""открой\s+(.+?)\s+в\s+(?:chrome|[cс])\s*$""",
            t_lower,
            flags=re.IGNORECASE,
        )
        if m:
            keywords = m.group(1).strip()
            if keywords:
                # Нормализуем ключевые слова (убираем лишние слова, исправляем ошибки)
                keywords = normalize_keywords(keywords)
                if keywords:
                    return ParsedCommand(
                        intent="open_tab",
                        target=keywords,
                        driver="chrome"
                    )
        
        return None
    
    def get_supported_intents(self) -> List[str]:
        """Получить список поддерживаемых намерений."""
        return ["open_tab"]

