"""
Drivers module - абстракция для управления разными программами.

Каждый драйвер отвечает за взаимодействие с конкретной программой
(Telegram, WhatsApp, Discord и т.д.).
"""

from .base import Driver, DriverResult
from .telegram import TelegramDriver
from .manager import DriverManager

__all__ = ["Driver", "DriverResult", "TelegramDriver", "DriverManager"]

