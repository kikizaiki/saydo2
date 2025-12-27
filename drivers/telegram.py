"""
Telegram driver - реализация драйвера для Telegram Desktop через Hammerspoon.
"""

import os
import requests
from typing import Dict, Any, Optional, List

from .base import Driver, DriverResult

# Глобальная сессия для HTTP запросов
_session = requests.Session()
_session.trust_env = False
_session.headers.update({"Connection": "close"})


class TelegramDriver(Driver):
    """
    Драйвер для управления Telegram Desktop через Hammerspoon.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация Telegram драйвера.
        
        Args:
            config: Конфигурация с ключами:
                - hammer_url: URL Hammerspoon HTTP сервера (по умолчанию http://127.0.0.1:7733)
                - timeout: Таймаут запросов в секундах (по умолчанию 5)
        """
        super().__init__(config)
        self.hammer_url = config.get("hammer_url", os.environ.get("HAMMER_URL", "http://127.0.0.1:7733"))
        self.timeout = config.get("timeout", 5)
    
    def _call_hammer(self, payload: Dict[str, Any]) -> DriverResult:
        """
        Вызов Hammerspoon через HTTP.
        
        Args:
            payload: JSON payload для отправки в Hammerspoon
        
        Returns:
            DriverResult с результатом
        """
        url = f"{self.hammer_url}/cmd"
        try:
            r = _session.post(url, json=payload, timeout=self.timeout)
        except Exception as e:
            return DriverResult(ok=False, error=f"Request failed: {e}")
        
        if r.status_code != 200:
            return DriverResult(
                ok=False,
                error=f"HTTP {r.status_code}",
                data={"raw": r.text[:5000], "url": url}
            )
        
        try:
            response = r.json()
            if response.get("ok", False):
                return DriverResult(ok=True, data=response)
            else:
                return DriverResult(
                    ok=False,
                    error=response.get("error", "Unknown error"),
                    data=response
                )
        except Exception as e:
            return DriverResult(
                ok=False,
                error="Non-JSON response",
                data={"raw": r.text[:5000], "url": url, "exception": str(e)}
            )
    
    def open_chat(self, target: str, auto_select: bool = True, result_index: Optional[int] = None, **kwargs) -> DriverResult:
        """
        Открыть чат в Telegram.
        
        Args:
            target: Имя чата (canonical)
            auto_select: Использовать OCR для автоматического выбора (True) или полагаться на result_index
            result_index: Индекс результата в поиске (0-based, None для OCR)
            **kwargs: Дополнительные параметры (игнорируются)
        
        Returns:
            DriverResult
        """
        payload = {
            "cmd": "open_chat",
            "query": target,
            "auto_select": auto_select
        }
        if result_index is not None:
            payload["result_index"] = result_index
        
        return self._call_hammer(payload)
    
    def send_message(self, text: str, use_clipboard: bool = True, draft: bool = True, **kwargs) -> DriverResult:
        """
        Отправить сообщение в открытый чат.
        
        Args:
            text: Текст сообщения
            use_clipboard: Использовать буфер обмена для вставки (безопаснее)
            draft: Не отправлять сразу, только вставить как черновик
            **kwargs: Дополнительные параметры (игнорируются)
        
        Returns:
            DriverResult
        """
        payload = {
            "cmd": "send",
            "text": text,
            "use_clipboard": use_clipboard,
            "draft": draft
        }
        
        return self._call_hammer(payload)
    
    def paste_from_clipboard(self, draft: bool = True, **kwargs) -> DriverResult:
        """
        Вставить содержимое буфера обмена в открытый чат.
        
        Args:
            draft: Не отправлять сразу, только вставить как черновик
            **kwargs: Дополнительные параметры (игнорируются)
        
        Returns:
            DriverResult
        """
        payload = {
            "cmd": "paste",
            "draft": draft
        }
        
        return self._call_hammer(payload)
    
    @property
    def supported_actions(self) -> List[str]:
        """Список поддерживаемых действий."""
        return ["open_chat", "send_message", "paste_from_clipboard"]

