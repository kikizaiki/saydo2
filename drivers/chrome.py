"""
Chrome driver - реализация драйвера для Google Chrome через Hammerspoon.
"""

import os
import requests
from typing import Dict, Any, Optional, List

from .base import Driver, DriverResult

# Глобальная сессия для HTTP запросов
_session = requests.Session()
_session.trust_env = False
_session.headers.update({"Connection": "close"})


class ChromeDriver(Driver):
    """
    Драйвер для управления Google Chrome через Hammerspoon.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация Chrome драйвера.
        
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
        except requests.exceptions.ConnectionError as e:
            error_msg = (
                f"Hammerspoon server is not running at {self.hammer_url}.\n"
                f"💡 Please:\n"
                f"   1. Start Hammerspoon application\n"
                f"   2. Reload configuration (Cmd+R in Hammerspoon)\n"
                f"   3. Check that server is running on port 7733"
            )
            return DriverResult(ok=False, error=error_msg)
        except requests.exceptions.Timeout as e:
            error_msg = f"Hammerspoon server timeout. Server may be overloaded or not responding."
            return DriverResult(ok=False, error=error_msg)
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
    
    def open_tab(self, keywords: str, **kwargs) -> DriverResult:
        """
        Открыть вкладку в Chrome по ключевым словам.
        
        Проверяет:
        1. Открытые вкладки - если найдена, переходит на неё
        2. История браузера - если найдена, открывает
        3. Закладки - если найдена, открывает
        4. Если ничего не найдено - открывает новую вкладку с поиском
        
        Args:
            keywords: Ключевые слова для поиска
            **kwargs: Дополнительные параметры (игнорируются)
        
        Returns:
            DriverResult
        """
        payload = {
            "cmd": "open_chrome_tab",
            "keywords": keywords
        }
        
        return self._call_hammer(payload)
    
    def open_chat(self, target: str, **kwargs) -> DriverResult:
        """
        Метод для совместимости с базовым интерфейсом.
        Перенаправляет на open_tab.
        """
        return self.open_tab(target, **kwargs)
    
    def send_message(self, text: str, **kwargs) -> DriverResult:
        """
        Не поддерживается для Chrome.
        """
        return DriverResult(ok=False, error="send_message not supported for Chrome")
    
    def paste_from_clipboard(self, **kwargs) -> DriverResult:
        """
        Не поддерживается для Chrome.
        """
        return DriverResult(ok=False, error="paste_from_clipboard not supported for Chrome")
    
    @property
    def supported_actions(self) -> List[str]:
        """Список поддерживаемых действий."""
        return ["open_tab", "open_chat"]

