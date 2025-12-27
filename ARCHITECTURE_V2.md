# Архитектура SayDo v2 (Модульная)

## Обзор

SayDo теперь использует модульную архитектуру, которая позволяет легко добавлять поддержку новых программ и действий.

## Структура проекта

```
saydo2/
├── agent.py              # Главный файл (legacy, будет рефакторен)
├── config/
│   └── config.json       # Конфигурация драйверов
├── drivers/              # Драйверы программ
│   ├── __init__.py
│   ├── base.py           # Базовый класс Driver
│   ├── telegram.py       # Драйвер Telegram
│   └── manager.py        # Менеджер драйверов
├── actions/              # Действия
│   ├── __init__.py
│   ├── base.py           # Базовый класс Action
│   └── telegram_actions.py  # Действия для Telegram
├── parsers/              # Парсеры команд
│   ├── __init__.py
│   ├── base.py           # Базовый класс CommandParser
│   └── telegram_parser.py  # Парсер команд Telegram
├── core/                 # Основная логика
│   ├── __init__.py
│   └── executor.py       # Исполнитель команд
└── utils/                # Утилиты
    ├── __init__.py
    └── chat_resolver.py  # Разрешение имен чатов
```

## Компоненты

### 1. Drivers (Драйверы)

Драйвер - это абстракция над программой (Telegram, WhatsApp, Discord и т.д.).

**Базовый класс:** `Driver`

**Методы:**
- `open_chat(target, **kwargs)` - открыть чат
- `send_message(text, **kwargs)` - отправить сообщение
- `paste_from_clipboard(**kwargs)` - вставить из буфера
- `supported_actions` - список поддерживаемых действий

**Пример:** `TelegramDriver` - управляет Telegram Desktop через Hammerspoon.

### 2. Actions (Действия)

Действие - это конкретная операция, которую можно выполнить в программе.

**Базовый класс:** `Action`

**Методы:**
- `execute(context)` - выполнить действие
- `validate(context)` - валидировать контекст

**Примеры действий для Telegram:**
- `OpenChatOnlyAction` - открыть чат без отправки сообщения
- `SendMessageAction` - открыть чат и отправить сообщение
- `PasteToChatAction` - открыть чат и вставить из буфера

### 3. Parsers (Парсеры)

Парсер превращает естественный язык в структурированную команду.

**Базовый класс:** `CommandParser`

**Методы:**
- `parse(text)` - распарсить команду
- `get_supported_intents()` - получить список поддерживаемых намерений

**Результат:** `ParsedCommand` с полями:
- `intent` - тип действия
- `target` - цель (имя чата)
- `message` - текст сообщения (если есть)
- `driver` - имя драйвера

### 4. Executor (Исполнитель)

`CommandExecutor` координирует работу всех компонентов:
1. Получает текстовую команду
2. Использует парсер для разбора
3. Получает драйвер из менеджера
4. Выбирает действие из реестра
5. Выполняет действие через драйвер

## Как добавить новую программу

### Шаг 1: Создать драйвер

```python
# drivers/myapp.py
from .base import Driver, DriverResult

class MyAppDriver(Driver):
    def open_chat(self, target: str, **kwargs) -> DriverResult:
        # Реализация открытия чата
        pass
    
    def send_message(self, text: str, **kwargs) -> DriverResult:
        # Реализация отправки сообщения
        pass
    
    def paste_from_clipboard(self, **kwargs) -> DriverResult:
        # Реализация вставки из буфера
        pass
    
    @property
    def supported_actions(self) -> List[str]:
        return ["open_chat", "send_message", "paste"]
```

### Шаг 2: Зарегистрировать драйвер

В `drivers/manager.py`:
```python
_DRIVER_CLASSES = {
    "telegram": TelegramDriver,
    "myapp": MyAppDriver,  # Добавить
}
```

### Шаг 3: Создать действия

```python
# actions/myapp_actions.py
from .base import Action, ActionContext
from ..drivers.base import DriverResult

class MyAppOpenChatAction(Action):
    def execute(self, context: ActionContext) -> DriverResult:
        # Реализация
        pass

MYAPP_ACTIONS = {
    "open_chat_only": MyAppOpenChatAction(),
    # ...
}
```

### Шаг 4: Создать парсер

```python
# parsers/myapp_parser.py
from .base import CommandParser, ParsedCommand

class MyAppCommandParser(CommandParser):
    def parse(self, text: str) -> Optional[ParsedCommand]:
        # Логика парсинга
        pass
```

### Шаг 5: Добавить в конфигурацию

В `config/config.json`:
```json
{
  "drivers": {
    "myapp": {
      "enabled": true,
      "api_url": "..."
    }
  }
}
```

## Конфигурация

Файл `config/config.json` содержит:
- Настройки драйверов
- Настройки парсеров (LLM и т.д.)
- Настройки голосового ввода
- Настройки логирования

## Использование

```python
from core.executor import CommandExecutor
from utils.chat_resolver import build_alias_map, load_tracked_chats

# Создать исполнитель
executor = CommandExecutor()

# Загрузить конфигурацию чатов
tracked = load_tracked_chats("tracked_chats.json")
alias_map, result_index_map = build_alias_map(tracked)

# Распарсить команду
parsed = executor.parse("напиши в избранное: привет")

# Выполнить команду
success = executor.execute(parsed, alias_map, result_index_map)
```

## Преимущества модульной архитектуры

1. **Расширяемость** - легко добавлять новые программы
2. **Тестируемость** - каждый компонент можно тестировать отдельно
3. **Переиспользование** - общие части (парсеры, действия) можно переиспользовать
4. **Гибкость** - можно менять реализации без изменения других компонентов
5. **Читаемость** - четкое разделение ответственности

## Миграция со старой архитектуры

Старый код в `agent.py` постепенно будет переноситься на новую архитектуру:

- ✅ `parse_command` -> `TelegramCommandParser`
- ✅ `hs_call` -> `TelegramDriver`
- ✅ `execute_command` -> `CommandExecutor`
- ⏳ Голосовой ввод - будет перенесен
- ⏳ LLM парсинг - будет интегрирован в парсеры

