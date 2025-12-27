"""
Парсер команд для Telegram.

Использует существующую логику парсинга из agent.py, но возвращает ParsedCommand.
"""

import re
from typing import Optional, List

from .base import CommandParser, ParsedCommand


class TelegramCommandParser(CommandParser):
    """
    Парсер команд для Telegram.
    
    Поддерживает различные форматы команд на русском языке для управления Telegram.
    """
    
    def __init__(self, driver_name: str = "telegram"):
        """Инициализация парсера."""
        super().__init__(driver_name)
    
    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        Распарсить команду для Telegram.
        
        Поддерживаемые форматы:
        - "напиши в X: msg" -> send_message
        - "открой чат X" -> open_chat_only
        - "отправь из буфера в X" -> paste_to_chat
        - "напиши X сообщение msg" -> send_message
        
        Args:
            text: Текст команды
        
        Returns:
            ParsedCommand или None
        """
        t = (text or "").strip()
        if not t:
            return None
        
        # 1) открой чат X и напиши "..."
        m = re.search(
            r"""открой\s+чат\s+(?P<target>.+?)\s+и\s+напиши\s+[«"](?P<msg>.+?)[»"]\s*$""",
            t,
            flags=re.IGNORECASE,
        )
        if m:
            return ParsedCommand(
                intent="send_message",
                target=m.group("target").strip(),
                message=m.group("msg").strip(),
                driver=self.driver_name
            )
        
        # 2) напиши в X: msg
        m = re.search(
            r"""напиши\s+в\s+(?P<target>.+?)\s*:\s*(?P<msg>.+)\s*$""",
            t,
            flags=re.IGNORECASE,
        )
        if m:
            return ParsedCommand(
                intent="send_message",
                target=m.group("target").strip(),
                message=m.group("msg").strip(),
                driver=self.driver_name
            )
        
        # 3) напиши в чат X: msg
        m = re.search(
            r"""напиши\s+в\s+чат\s+(?P<target>.+?)\s*:\s*(?P<msg>.+)\s*$""",
            t,
            flags=re.IGNORECASE,
        )
        if m:
            return ParsedCommand(
                intent="send_message",
                target=m.group("target").strip(),
                message=m.group("msg").strip(),
                driver=self.driver_name
            )
        
        # 4) напиши в X что msg
        m = re.search(
            r"""напиши\s+в\s+(?P<target>.+?)\s+что\s+(?P<msg>.+)\s*$""",
            t,
            flags=re.IGNORECASE,
        )
        if m:
            return ParsedCommand(
                intent="send_message",
                target=m.group("target").strip(),
                message=m.group("msg").strip(),
                driver=self.driver_name
            )
        
        # 5) напиши X сообщение msg (без "в")
        m = re.search(
            r"""напиши\s+(?P<target>.+?)\s+сообщение\s+(?P<msg>.+)\s*$""",
            t,
            flags=re.IGNORECASE,
        )
        if m:
            target = m.group("target").strip()
            # Убираем "в" в начале если есть
            target = re.sub(r'^в\s+', '', target)
            return ParsedCommand(
                intent="send_message",
                target=target,
                message=m.group("msg").strip(),
                driver=self.driver_name
            )
        
        # 6) отправь из буфера в X
        m = re.search(
            r"""отправ(ь|и)\s+из\s+буфер(а|а обмена)\s+в\s+(?P<target>.+?)\s*$""",
            t,
            flags=re.IGNORECASE,
        )
        if m:
            target = m.group("target").strip()
            # Убираем "чат" если есть
            target = re.sub(r'^\s*чат\s+', '', target, flags=re.IGNORECASE)
            return ParsedCommand(
                intent="paste_to_chat",
                target=target,
                driver=self.driver_name
            )
        
        # 7) открыть чат X (без сообщения)
        m = re.search(
            r"""открой\s+(?:чат\s+)?(?P<target>.+?)\s*$""",
            t,
            flags=re.IGNORECASE,
        )
        if m:
            target = m.group("target").strip()
            # Проверяем, что это не команда "открой чат X и напиши"
            if "и напиши" not in t.lower():
                return ParsedCommand(
                    intent="open_chat_only",
                    target=target,
                    driver=self.driver_name
                )
        
        # Не распознано
        return None
    
    def get_supported_intents(self) -> List[str]:
        """Получить список поддерживаемых намерений."""
        return ["open_chat_only", "send_message", "paste_to_chat"]

