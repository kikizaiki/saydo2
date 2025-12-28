"""
Конкретные действия для Telegram.
"""

from .base import Action, ActionContext
from ..drivers.base import DriverResult


class OpenChatOnlyAction(Action):
    """Действие: открыть чат без отправки сообщения."""
    
    def __init__(self):
        super().__init__(
            name="open_chat_only",
            description="Открыть чат в Telegram без отправки сообщения"
        )
    
    def validate(self, context: ActionContext) -> tuple[bool, Optional[str]]:
        """Валидация контекста."""
        if not context.target:
            return False, "Target (имя чата) обязательно для open_chat_only"
        return True, None
    
    def execute(self, context: ActionContext) -> DriverResult:
        """Выполнить открытие чата."""
        is_valid, error = self.validate(context)
        if not is_valid:
            return DriverResult(ok=False, error=error)
        
        # Извлекаем параметры из extra_params
        auto_select = context.extra_params.get("auto_select", True)
        result_index = context.extra_params.get("result_index")
        
        result = context.driver.open_chat(
            target=context.target,
            auto_select=auto_select,
            result_index=result_index
        )
        
        if result.ok:
            print("✅ Чат открыт.")
        
        return result


class SendMessageAction(Action):
    """Действие: отправить текстовое сообщение."""
    
    def __init__(self):
        super().__init__(
            name="send_message",
            description="Отправить текстовое сообщение в открытый чат"
        )
    
    def validate(self, context: ActionContext) -> tuple[bool, Optional[str]]:
        """Валидация контекста."""
        if not context.target:
            return False, "Target (имя чата) обязательно для send_message"
        if not context.message:
            return False, "Message (текст сообщения) обязательно для send_message"
        return True, None
    
    def execute(self, context: ActionContext) -> DriverResult:
        """Выполнить отправку сообщения."""
        is_valid, error = self.validate(context)
        if not is_valid:
            return DriverResult(ok=False, error=error)
        
        # Сначала открываем чат
        auto_select = context.extra_params.get("auto_select", True)
        result_index = context.extra_params.get("result_index")
        
        open_result = context.driver.open_chat(
            target=context.target,
            auto_select=auto_select,
            result_index=result_index
        )
        
        if not open_result.ok:
            return open_result
        
        # Затем отправляем сообщение
        use_clipboard = context.extra_params.get("use_clipboard", True)
        draft = context.extra_params.get("draft", True)
        
        send_result = context.driver.send_message(
            text=context.message,
            use_clipboard=use_clipboard,
            draft=draft
        )
        
        if send_result.ok:
            print("✅ Готово: чат открыт, текст вставлен (draft), ничего не отправлено.")
        
        return send_result


class PasteToChatAction(Action):
    """Действие: вставить содержимое буфера обмена."""
    
    def __init__(self):
        super().__init__(
            name="paste_to_chat",
            description="Вставить содержимое буфера обмена в чат"
        )
    
    def validate(self, context: ActionContext) -> tuple[bool, Optional[str]]:
        """Валидация контекста."""
        if not context.target:
            return False, "Target (имя чата) обязательно для paste_to_chat"
        return True, None
    
    def execute(self, context: ActionContext) -> DriverResult:
        """Выполнить вставку из буфера."""
        is_valid, error = self.validate(context)
        if not is_valid:
            return DriverResult(ok=False, error=error)
        
        # Сначала открываем чат
        auto_select = context.extra_params.get("auto_select", True)
        result_index = context.extra_params.get("result_index")
        
        open_result = context.driver.open_chat(
            target=context.target,
            auto_select=auto_select,
            result_index=result_index
        )
        
        if not open_result.ok:
            return open_result
        
        # Затем вставляем из буфера
        draft = context.extra_params.get("draft", True)
        
        paste_result = context.driver.paste_from_clipboard(draft=draft)
        
        if paste_result.ok:
            print("✅ Готово: чат открыт, данные из буфера обмена вставлены (draft), ничего не отправлено.")
        
        return paste_result


# Регистр действий для Telegram
TELEGRAM_ACTIONS = {
    "open_chat_only": OpenChatOnlyAction(),
    "send_message": SendMessageAction(),
    "paste_to_chat": PasteToChatAction(),
}


