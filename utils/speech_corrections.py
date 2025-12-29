#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для исправления типичных ошибок распознавания речи.
"""

# Словарь типичных ошибок распознавания речи
# Ключ - что распознано неправильно, значение - правильный вариант
SPEECH_CORRECTIONS = {
    # Финансовые термины
    "смита": "смета",
    "смита фин": "смета фин",
    "смита финансовая": "смета финансовая",
    "фин смита": "фин смета",
    
    # Другие типичные ошибки можно добавить здесь
    # "пример": "правильный вариант",
}

def correct_speech_errors(text: str) -> str:
    """
    Исправляет типичные ошибки распознавания речи.
    
    Args:
        text: Текст с возможными ошибками распознавания
    
    Returns:
        Исправленный текст
    """
    if not text:
        return text
    
    text_lower = text.lower()
    corrected = text
    
    # Применяем исправления
    for wrong, correct in SPEECH_CORRECTIONS.items():
        if wrong in text_lower:
            # Заменяем неправильный вариант на правильный
            # Сохраняем регистр оригинального текста где возможно
            corrected = corrected.replace(wrong, correct)
            corrected = corrected.replace(wrong.capitalize(), correct.capitalize())
    
    return corrected

def normalize_keywords(keywords: str) -> str:
    """
    Нормализует ключевые слова для поиска:
    - Исправляет ошибки распознавания речи
    - Убирает лишние слова (chrome, браузер и т.д.)
    - Нормализует пробелы
    
    Args:
        keywords: Исходные ключевые слова
    
    Returns:
        Нормализованные ключевые слова
    """
    if not keywords:
        return keywords
    
    # Убираем слова, которые не нужны для поиска
    stop_words = ["chrome", "браузер", "вкладка", "вкладку", "открой", "найди"]
    
    words = keywords.lower().split()
    filtered_words = [w for w in words if w not in stop_words]
    
    normalized = " ".join(filtered_words)
    
    # Исправляем ошибки распознавания речи
    normalized = correct_speech_errors(normalized)
    
    return normalized.strip()

