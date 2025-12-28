# Модульная архитектура SayDo

## Быстрый старт

### Использование новой архитектуры

```python
from core.executor import CommandExecutor
from utils.chat_resolver import build_alias_map, load_tracked_chats

# 1. Создать исполнитель
executor = CommandExecutor()

# 2. Загрузить конфигурацию чатов
tracked = load_tracked_chats("tracked_chats.json")
alias_map, result_index_map = build_alias_map(tracked)

# 3. Распарсить команду
parsed = executor.parse("напиши в избранное: привет")
if parsed:
    # 4. Выполнить команду
    success = executor.execute(parsed, alias_map, result_index_map)
```

## Добавление новой программы

См. подробную инструкцию в `ARCHITECTURE_V2.md`.

Краткая версия:
1. Создать драйвер в `drivers/`
2. Создать действия в `actions/`
3. Создать парсер в `parsers/`
4. Зарегистрировать в `drivers/manager.py`
5. Добавить конфигурацию в `config/config.json`


