"""
Конкретные действия для Chrome.
"""

from typing import Optional

# Используем абсолютные импорты для совместимости
try:
    from actions.base import Action, ActionContext
    from drivers.base import DriverResult
except ImportError:
    # Fallback для относительных импортов
    from .base import Action, ActionContext
    from ..drivers.base import DriverResult


class OpenTabAction(Action):
    """Действие: открыть вкладку в Chrome по ключевым словам."""
    
    def __init__(self):
        super().__init__(
            name="open_tab",
            description="Открыть вкладку в Chrome по ключевым словам (проверяет открытые вкладки, историю и закладки)"
        )
    
    def validate(self, context: ActionContext) -> tuple[bool, Optional[str]]:
        """Валидация контекста."""
        if not context.target:
            return False, "Target (ключевые слова) обязательно для open_tab"
        return True, None
    
    def execute(self, context: ActionContext) -> DriverResult:
        """Выполнить открытие вкладки."""
        is_valid, error = self.validate(context)
        if not is_valid:
            return DriverResult(ok=False, error=error)
        
        # Используем target как ключевые слова
        result = context.driver.open_tab(keywords=context.target)
        
        if result.ok:
            print("✅ Вкладка открыта или найдена в Chrome.")
        else:
            # Улучшенное сообщение об ошибке
            error_msg = result.error or "Unknown error"
            print(f"❌ Ошибка открытия вкладки: {error_msg}")
            
            # Если ошибка связана с Hammerspoon, даем более детальную информацию
            if "not running" in error_msg.lower() or "connection" in error_msg.lower():
                print("\n💡 Устранение неполадок:")
                print("   1. Откройте приложение Hammerspoon")
                print("   2. Нажмите Cmd+R для перезагрузки конфигурации")
                print("   3. Проверьте консоль Hammerspoon на наличие ошибок")
                print("   4. Убедитесь, что init.lua загружен и сервер запущен на порту 7733")
        
        return result


# Регистр действий для Chrome
CHROME_ACTIONS = {
    "open_tab": OpenTabAction(),
    "open_chat": OpenTabAction(),  # Алиас для совместимости
}

