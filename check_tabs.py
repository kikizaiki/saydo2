#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка открытых вкладок Chrome"""

import subprocess
import json
import sys

script = '''
tell application "Google Chrome"
    set tabList to {}
    set windowIndex to 1
    repeat with w in windows
        set tabIndex to 1
        repeat with t in tabs of w
            set end of tabList to {windowIndex, tabIndex, title of t, URL of t}
            set tabIndex to tabIndex + 1
        end repeat
        set windowIndex to windowIndex + 1
    end repeat
    return tabList
end tell
'''

result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=5)
if result.returncode != 0:
    print(f"Ошибка: {result.stderr}")
    sys.exit(1)

output = result.stdout.strip()
parts = output.split(', ')
i = 0
tabs = []
while i < len(parts) - 3:
    try:
        window_idx = int(parts[i])
        tab_idx = int(parts[i+1])
        title = parts[i+2].strip('"')
        url = parts[i+3].strip('"')
        tabs.append({'window': window_idx, 'tab': tab_idx, 'title': title, 'url': url})
        i += 4
    except (ValueError, IndexError):
        i += 1

print(f"Всего вкладок: {len(tabs)}\n")

# Ищем вкладки с ключевыми словами
keywords = sys.argv[1] if len(sys.argv) > 1 else "голосовой помощник смета фин"
keywords_lower = keywords.lower().replace("смита", "смета")

print(f"Ищем вкладки содержащие: {keywords_lower}\n")
keyword_words = keywords_lower.split()

matches = []
for tab in tabs:
    title_lower = tab['title'].lower()
    url_lower = tab['url'].lower()
    combined = f"{title_lower} {url_lower}"
    
    matched_words = [w for w in keyword_words if w in combined]
    if matched_words:
        matches.append((len(matched_words), tab, matched_words))

matches.sort(reverse=True, key=lambda x: x[0])

print(f"Найдено {len(matches)} вкладок с совпадениями:\n")
for i, (match_count, tab, matched) in enumerate(matches[:10]):
    print(f"{i+1}. [{match_count} совпадений: {matched}]")
    print(f"   [{tab['window']},{tab['tab']}] {tab['title']}")
    print(f"   {tab['url'][:80]}")
    print()

