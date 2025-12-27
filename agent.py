#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
import requests
from datetime import datetime

from typing import Dict, List, Optional, Tuple

SESSION = requests.Session()
SESSION.trust_env = False
SESSION.headers.update({"Connection": "close"})



HAMMER_URL = os.environ.get("HAMMER_URL", "http://127.0.0.1:7733")
TRACKED_CHATS_PATH = os.environ.get(
    "TRACKED_CHATS_PATH",
    os.path.join(os.path.dirname(__file__), "tracked_chats.json"),
)
COMMANDS_LOG_PATH = os.path.join(
    os.path.dirname(__file__), "unrecognized_commands.log"
)
ALL_RECOGNIZED_LOG_PATH = os.path.join(
    os.path.dirname(__file__), "all_recognized_speech.log"
)
# Set DISABLE_WHITELIST=1 to allow any chat name
DISABLE_WHITELIST = os.environ.get("DISABLE_WHITELIST", "").lower() in ("1", "true", "yes")

TIMEOUT_SEC = 5


def norm(s: str) -> str:
    """Case-insensitive + ё->е + trim + collapse spaces."""
    s = (s or "").strip().lower()
    s = s.replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    return s


def clean_one_line(text: str) -> str:
    text = text or ""
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_tracked_chats(path: str) -> List[Dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"tracked_chats.json not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tracked = data.get("tracked", [])
    if not isinstance(tracked, list):
        raise ValueError("tracked_chats.json: 'tracked' must be a list")
    return tracked


def build_alias_map(tracked: List[Dict]) -> Tuple[Dict[str, str], Dict[str, Optional[int]]]:
    """
    Returns:
    - alias_map: normalized_alias -> canonical
    - result_index_map: canonical -> result_index (0-based, None if not specified)
    Includes canonical itself as an alias.
    """
    alias_map: Dict[str, str] = {}
    result_index_map: Dict[str, Optional[int]] = {}
    
    for item in tracked:
        canonical = item.get("canonical", "")
        if not canonical:
            continue
        canonical_n = norm(canonical)
        alias_map[canonical_n] = canonical
        
        # Store result_index only if explicitly specified in JSON
        # None means "use OCR to find automatically"
        if "result_index" in item:
            result_index_map[canonical] = item.get("result_index")
        # If not specified, don't add to map (will return None when accessed)

        aliases = item.get("aliases", []) or []
        for a in aliases:
            a_n = norm(str(a))
            if a_n:
                alias_map[a_n] = canonical
    
    return alias_map, result_index_map


def resolve_chat(user_target: str, alias_map: Dict[str, str]) -> Optional[str]:
    """
    Resolve chat alias -> canonical (case-insensitive + ё/е)
    """
    key = norm(user_target)
    if not key:
        return None
    return alias_map.get(key)


def parse_command(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Returns: (intent, target, message)
    intent: open_and_type | type_to_chat | paste_to_chat
    """
    t = (text or "").strip()

    # 1) открой чат X и напиши "..."
    m = re.search(
        r"""открой\s+чат\s+(?P<target>.+?)\s+и\s+напиши\s+[«"](?P<msg>.+?)[»"]\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "open_and_type", m.group("target").strip(), m.group("msg").strip()

    # 2) напиши в X: msg
    m = re.search(
        r"""напиши\s+в\s+(?P<target>.+?)\s*:\s*(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "type_to_chat", m.group("target").strip(), m.group("msg").strip()

    # 3) напиши в чат X: msg
    m = re.search(
        r"""напиши\s+в\s+чат\s+(?P<target>.+?)\s*:\s*(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "type_to_chat", m.group("target").strip(), m.group("msg").strip()

    # 4) напиши в X что msg
    m = re.search(
        r"""напиши\s+в\s+(?P<target>.+?)\s+что\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "type_to_chat", m.group("target").strip(), m.group("msg").strip()

    # 4a) напиши X сообщение msg (без "в")
    m = re.search(
        r"""напиши\s+(?P<target>.+?)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        target = m.group("target").strip()
        # Убираем возможные предлоги в начале
        target = re.sub(r'^(в|к|ко)\s+', '', target)
        return "type_to_chat", target, m.group("msg").strip()

    # 5) написать в чат X, что msg
    m = re.search(
        r"""написа(ть|ться|ть)\s+в\s+чат\s+(?P<target>.+?)\s*,?\s+что\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "type_to_chat", m.group("target").strip(), m.group("msg").strip()

    # 5a) отправь в телеграм/telegram в X сообщение msg (голосовая команда)
    m = re.search(
        r"""отправ(ь|и)\s+в\s+(телегра(м|мма?)|telegram)\s+в\s+(?P<target>.+?)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "type_to_chat", m.group("target").strip(), m.group("msg").strip()

    # 5b) отправь в телеграм/telegram в чат X сообщение msg (голосовая команда)
    m = re.search(
        r"""отправ(ь|и)\s+в\s+(телегра(м|мма?)|telegram)\s+в\s+чат\s+(?P<target>.+?)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "type_to_chat", m.group("target").strip(), m.group("msg").strip()

    # 5c) отправь в телеграм/telegram X сообщение msg (голосовая команда, без "в" перед именем)
    m = re.search(
        r"""отправ(ь|и)\s+в\s+(телегра(м|мма?)|telegram)\s+(?P<target>.+?)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        target = m.group("target").strip()
        # Если есть "в" перед именем, убираем его
        target = re.sub(r'^в\s+', '', target)
        return "type_to_chat", target, m.group("msg").strip()

    # 5c1) отправь X сообщение msg (без "в телеграм")
    m = re.search(
        r"""отправ(ь|и)\s+(?P<target>.+?)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        target = m.group("target").strip()
        # Убираем "в" в начале если есть
        target = re.sub(r'^в\s+', '', target)
        # Убираем "в telegram" или "в телеграм" из target, если там есть
        target = re.sub(r'\s+в\s+(телегра(м|мма?)|telegram)\s*$', '', target, flags=re.IGNORECASE)
        target = re.sub(r'^\s*(телегра(м|мма?)|telegram)\s+', '', target, flags=re.IGNORECASE)
        return "type_to_chat", target.strip(), m.group("msg").strip()

    # 5c2) отправь X в telegram сообщение msg (порядок слов: имя потом "в telegram")
    m = re.search(
        r"""отправ(ь|и)\s+(?P<target>.+?)\s+в\s+(телегра(м|мма?)|telegram)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        target = m.group("target").strip()
        return "type_to_chat", target, m.group("msg").strip()

    # 5c1) отправь X сообщение msg (без "в телеграм")
    # Обрабатывает: "отправь Максиму ершову сообщение Привет"
    m = re.search(
        r"""отправ(ь|и)\s+(?P<target>.+?)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        target = m.group("target").strip()
        # Убираем "в" в начале если есть
        target = re.sub(r'^в\s+', '', target)
        # Убираем "Telegram" или "телеграм" если остался в target
        target = re.sub(r'\s+(?:в\s+)?(?:телегра(м|мма?)|telegram)\s*$', '', target, flags=re.IGNORECASE)
        target = re.sub(r'^\s*(?:телегра(м|мма?)|telegram)\s+', '', target, flags=re.IGNORECASE)
        # Очищаем от лишних пробелов
        target = re.sub(r'\s+', ' ', target).strip()
        if target:  # Убеждаемся что target не пустой
            return "type_to_chat", target, m.group("msg").strip()

    # 5c2) отправь сообщение X msg (порядок: сообщение перед именем)
    # Обрабатывает: "отправь сообщение Максиму ершову Привет мир"
    # Простой подход: имя обычно 1-3 слова, остальное - сообщение
    # Берем последние 1-2 слова как часть имени, остальное - сообщение
    m = re.search(
        r"""отправ(ь|и)\s+сообщение\s+(?P<rest>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        rest = m.group("rest").strip()
        words = rest.split()
        
        if len(words) >= 3:
            # Если 3+ слова, берем первые 2 как имя, остальное - сообщение
            # Например: "Максиму ершову Привет мир" -> имя="Максиму ершову", msg="Привет мир"
            target = ' '.join(words[:2])
            msg = ' '.join(words[2:])
        elif len(words) >= 2:
            # Если 2 слова, берем первое как имя, второе как начало сообщения
            target = words[0]
            msg = ' '.join(words[1:])
        else:
            # Если 1 слово - это имя, сообщение пустое (но это странно)
            target = words[0] if words else ""
            msg = ""
        
        # Убираем "в" в начале если есть
        target = re.sub(r'^в\s+', '', target)
        # Убираем "Telegram" или "телеграм" если есть
        target = re.sub(r'\s+(?:в\s+)?(?:телегра(м|мма?)|telegram)\s*$', '', target, flags=re.IGNORECASE)
        target = re.sub(r'^\s*(?:телегра(м|мма?)|telegram)\s+', '', target, flags=re.IGNORECASE)
        target = re.sub(r'\s+', ' ', target).strip()
        if target and msg:
            return "type_to_chat", target, msg.strip()

    # 5c3) отправь X в telegram сообщение msg (порядок слов: имя потом "в telegram")
    # Обрабатывает: "отправь ершову Максиму в Telegram сообщение Привет"
    m = re.search(
        r"""отправ(ь|и)\s+(?P<target>.+?)\s+в\s+(телегра(м|мма?)|telegram)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        target = m.group("target").strip()
        target = re.sub(r'\s+', ' ', target).strip()
        if target:
            return "type_to_chat", target, m.group("msg").strip()

    # 5d) отправь в телеграм/telegram X (просто открыть чат, без сообщения)
    m = re.search(
        r"""отправ(ь|и)\s+в\s+(телегра(м|мма?)|telegram)\s+(?P<target>.+?)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        target = m.group("target").strip()
        # Если есть "в" перед именем, убираем его
        target = re.sub(r'^в\s+', '', target)
        return "open_chat_only", target, None

    # 5e) отправь X сообщение msg (без "в телеграм", просто "отправь")
    m = re.search(
        r"""отправ(ь|и)\s+(?P<target>.+?)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        target = m.group("target").strip()
        # Убираем возможные предлоги в начале
        target = re.sub(r'^(в|к|ко)\s+', '', target)
        return "type_to_chat", target, m.group("msg").strip()

    # 5f) отправь в X сообщение msg (без "телеграм")
    m = re.search(
        r"""отправ(ь|и)\s+в\s+(?P<target>.+?)\s+сообщение\s+(?P<msg>.+)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        target = m.group("target").strip()
        # Пропускаем если это "telegram" или "телеграм"
        if target.lower() not in ["telegram", "телеграм", "телеграмма"]:
            return "type_to_chat", target, m.group("msg").strip()

    # 6) отправь из буфера в X
    m = re.search(
        r"""отправ(ь|и)\s+из\s+буфер(а|а обмена|а обмена|а)\s+в\s+(?P<target>.+?)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "paste_to_chat", m.group("target").strip(), None

    # 7) отправь из буфера в чат X
    m = re.search(
        r"""отправ(ь|и)\s+из\s+буфер(а|а обмена|а обмена|а)\s+в\s+чат\s+(?P<target>.+?)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "paste_to_chat", m.group("target").strip(), None

    # 8) вставь в X (из буфера обмена) - старый вариант для совместимости
    m = re.search(
        r"""встав(ь|и)\s+в\s+(?P<target>.+?)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "paste_to_chat", m.group("target").strip(), None

    # 9) вставь в чат X (из буфера обмена) - старый вариант для совместимости
    m = re.search(
        r"""встав(ь|и)\s+в\s+чат\s+(?P<target>.+?)\s*$""",
        t,
        flags=re.IGNORECASE,
    )
    if m:
        return "paste_to_chat", m.group("target").strip(), None

    return None, None, None


def hs_call(payload: Dict) -> Dict:
    url = f"{HAMMER_URL}/cmd"
    try:
        r = SESSION.post(url, json=payload, timeout=TIMEOUT_SEC)
    except Exception as e:
        return {"ok": False, "error": f"Request failed: {e}", "url": url}

    if r.status_code != 200:
        return {
            "ok": False,
            "error": f"HTTP {r.status_code}",
            "url": url,
            "raw": r.text[:5000],
        }

    try:
        return r.json()
    except Exception:
        return {"ok": False, "error": "Non-JSON response", "raw": r.text[:5000], "url": url}



def listen_for_voice(timeout=5, phrase_time_limit=10):
    """Listen for voice input and return recognized text."""
    try:
        import speech_recognition as sr
    except ImportError:
        print("❌ speech_recognition не установлен. Установите: pip install SpeechRecognition pyaudio")
        return None
    
    recognizer = sr.Recognizer()
    
    # Use default microphone
    try:
        with sr.Microphone() as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("🎤 Слушаю... (скажите команду после 'saydo')")
            
            # Listen for audio
            try:
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                print("⏱️  Время ожидания истекло")
                return None
    except Exception as e:
        print(f"❌ Ошибка доступа к микрофону: {e}")
        print("💡 Убедитесь, что разрешён доступ к микрофону в настройках macOS")
        return None
    
    # Recognize speech using macOS speech recognition
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
        print(f"🗣️  Распознано: {text}")
        return text
    except sr.UnknownValueError:
        print("❌ Не удалось распознать речь")
        return None
    except sr.RequestError as e:
        print(f"❌ Ошибка сервиса распознавания речи: {e}")
        return None


def log_unrecognized_command(command: str, full_text: Optional[str] = None):
    """Log unrecognized command to file for later analysis."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "command": command,
            "full_text": full_text if full_text else command,
        }
        
        # Append to log file
        with open(COMMANDS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # Also print to console for immediate feedback
        print(f"📝 Команда записана в лог: {COMMANDS_LOG_PATH}")
    except Exception as e:
        # Don't fail if logging fails
        pass


def execute_command(user_text: str, full_recognized_text: Optional[str] = None) -> bool:
    """
    Execute a single command.
    Returns True if command was executed successfully, False otherwise.
    
    Args:
        user_text: The command text to execute (after keyword removal)
        full_recognized_text: Optional full recognized text (before keyword removal) for logging
    """
    intent, target, msg = parse_command(user_text)

    if not intent:
        # Log unrecognized command
        log_unrecognized_command(user_text, full_recognized_text)
        
        print("❌ Не понял команду. Примеры:")
        print('  "открой чат прокачка и напиши «всем привет»"')
        print('  "напиши в избранное: тест"')
        print('  "отправь из буфера в избранное"')
        print('  "отправь в телеграм в избранное сообщение привет мир"')
        print('  "отправь в телеграм Максим Ершов"  # просто открыть чат')
        return False

    try:
        tracked = load_tracked_chats(TRACKED_CHATS_PATH)
    except Exception as e:
        print(f"❌ Ошибка чтения tracked_chats.json: {e}")
        return False

    alias_map, result_index_map = build_alias_map(tracked)

    canonical = resolve_chat(target, alias_map)
    if not canonical:
        if DISABLE_WHITELIST:
            # Whitelist disabled: use target as-is
            canonical = target
            result_index = 0  # Default to first result
            print(f"⚠️  Whitelist отключен, используем '{canonical}' как есть")
        else:
            print(f"❌ Чат '{target}' не в whitelist (tracked_chats.json). Hammerspoon не вызываю.")
            print(f"💡 Чтобы отключить whitelist, установите: export DISABLE_WHITELIST=1")
            return False
    else:
        # Get result_index for this canonical chat (None if not specified, meaning use OCR)
        result_index = result_index_map.get(canonical)  # Returns None if key doesn't exist

    # 1) open_chat (always canonical, with auto_select enabled)
    # auto_select=True means use OCR to find exact match
    # Only pass result_index if it was explicitly set in JSON (overrides OCR)
    payload = {"cmd": "open_chat", "query": canonical, "auto_select": True}
    if result_index is not None:
        payload["result_index"] = result_index
    resp1 = hs_call(payload)
    if not resp1.get("ok", False):
        print(f"❌ open_chat failed: {resp1}")
        return False

    # 2) Handle different intents
    if intent == "open_chat_only":
        # Just open chat, don't send anything
        print("✅ Чат открыт.")
        return True
    elif intent == "paste_to_chat":
        # Paste from clipboard
        resp2 = hs_call({"cmd": "paste", "draft": True})
        if not resp2.get("ok", False):
            print(f"❌ paste failed: {resp2}")
            return False
        print("✅ Готово: чат открыт, данные из буфера обмена вставлены (draft), ничего не отправлено.")
        return True
    else:
        # Type text (existing behavior)
        msg_clean = clean_one_line(msg or "")
        if not msg_clean:
            print("❌ Пустой текст сообщения после чистки.")
            return False

        resp2 = hs_call(
            {
                "cmd": "send",
                "text": msg_clean,
                "use_clipboard": True,  # safest: paste via clipboard
                "draft": True,
            }
        )
        if not resp2.get("ok", False):
            print(f"❌ send failed: {resp2}")
            return False

        print("✅ Готово: чат открыт, текст вставлен (draft), ничего не отправлено.")
        return True


def main():
    # Check if voice mode is enabled (no arguments = voice mode)
    if len(sys.argv) == 1:
        # Voice mode: listen for "saydo" keyword in infinite loop
        print("🎤 Голосовой режим активирован. Скажите 'агент' (или 'saydo') затем команду...")
        print("💡 Для выхода нажмите Ctrl+C\n")
        
        try:
            import speech_recognition as sr
        except ImportError:
            print("❌ speech_recognition не установлен. Установите: pip install SpeechRecognition pyaudio")
            sys.exit(1)
        
        while True:
            recognizer = sr.Recognizer()
            
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    print("🎤 Слушаю ключевое слово 'агент' или 'saydo'...")
                    
                    try:
                        audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                    except sr.WaitTimeoutError:
                        continue
            except Exception as e:
                print(f"❌ Ошибка доступа к микрофону: {e}")
                break
            
            try:
                text = recognizer.recognize_google(audio, language="ru-RU")
                text_lower = text.lower()
                
                # Log ALL recognized speech for debugging
                try:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(ALL_RECOGNIZED_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"[{timestamp}] {text}\n")
                    print(f"🗣️  Распознано: {text}")
                except Exception:
                    pass  # Don't fail if logging fails
                
                # List of possible keyword variations (how "saydo" or "агент" might be recognized)
                keywords = [
                    # English "saydo"
                    "saydo", "say do",
                    # Russian "saydo" variations
                    "сейдо", "сойду", "сейду", "сейдоу", "зейду",
                    "сей до", "сой ду", "сей ду", "зей ду",
                    # Russian "агент" variations
                    "агент", "агента", "агенту", "агенте", "агентом", "агенты"
                ]
                
                # Check for any keyword variation
                keyword_found = None
                keyword_pos = -1
                keyword_len = 5
                
                for keyword in keywords:
                    if keyword in text_lower:
                        keyword_found = keyword
                        keyword_pos = text_lower.find(keyword)
                        keyword_len = len(keyword)
                        break
                
                if keyword_found:
                    # Extract command after the keyword
                    command_start = keyword_pos + keyword_len
                    command = text[command_start:].strip()
                    # Remove leading spaces/punctuation
                    command = command.lstrip(" ,.?!;:")
                    
                    if command:
                        print(f"✅ Ключевое слово '{keyword_found}' найдено!")
                        print(f"📝 Команда: {command}\n")
                        # Execute command (pass full recognized text for logging)
                        execute_command(command, text)
                        print()  # Empty line after command execution
                        # Continue listening (don't break)
                    else:
                        print("⚠️  Команда не найдена после ключевого слова, продолжаю слушать...\n")
                        continue
                else:
                    # Already printed above with 🗣️
                    print("💡 Подсказка: скажите 'агент' или 'saydo' перед командой\n")
                    continue
                    
            except sr.UnknownValueError:
                continue
            except sr.RequestError as e:
                print(f"❌ Ошибка сервиса распознавания речи: {e}\n")
                continue
            except KeyboardInterrupt:
                print("\n\n👋 Голосовой режим остановлен")
                break
    
    elif len(sys.argv) == 2:
        # Text mode: use provided text
        user_text = sys.argv[1]
        success = execute_command(user_text, user_text)
        sys.exit(0 if success else 1)
    else:
        print('Usage:')
        print('  python agent.py "команда на русском"  # текстовый режим')
        print('  python agent.py                        # голосовой режим')
        sys.exit(1)


if __name__ == "__main__":
    main()
