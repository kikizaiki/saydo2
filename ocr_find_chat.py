#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR helper script to find chat name in Telegram search results.
Takes a screenshot of the search area and returns the index of matching chat.
"""

import sys
import os
import json
import subprocess
import tempfile
from pathlib import Path

def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, trim, collapse spaces)."""
    text = (text or "").strip().lower()
    text = text.replace("ё", "е")
    # Collapse multiple spaces
    import re
    text = re.sub(r"\s+", " ", text)
    return text

def find_chat_in_screenshot(screenshot_path: str, target_name: str) -> int:
    """
    Analyze screenshot to find target chat name.
    Returns 0-based index of matching chat, or -1 if not found.
    """
    try:
        # Try using tesseract if available
        import pytesseract
        from PIL import Image
    except ImportError:
        return -1
    
    try:
        # Open image
        img = Image.open(screenshot_path)
        
        # Get image dimensions to check if it's valid
        if img.size[0] == 0 or img.size[1] == 0:
            return -1
        
        # Enhance image for better OCR
        # Convert to grayscale
        img_gray = img.convert('L')
        
        # Increase contrast (optional, but can help)
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img_gray)
        img_gray = enhancer.enhance(2.0)
        
        # Use OCR to extract text with better configuration
        # Try with Russian + English languages
        # Use --psm 6 for uniform block of text (list of results)
        custom_config = r'--oem 3 --psm 6'
        try:
            ocr_text = pytesseract.image_to_string(img_gray, lang='rus+eng', config=custom_config)
        except:
            # Fallback to default if lang not available
            ocr_text = pytesseract.image_to_string(img_gray, config=custom_config)
        
        # Split into lines and filter empty ones
        lines = []
        for line in ocr_text.split('\n'):
            line = line.strip()
            if line and len(line) > 1:  # Ignore single characters/noise
                lines.append(line)
        
        if not lines:
            return -1
        
        # Normalize target name
        target_norm = normalize_text(target_name)
        
        # Strategy 1: Find exact match (case-insensitive, normalized)
        for i, line in enumerate(lines):
            line_norm = normalize_text(line)
            if line_norm == target_norm:
                return i
        
        # Strategy 2: Find where target is a substring of line (handles prefixes/suffixes)
        for i, line in enumerate(lines):
            line_norm = normalize_text(line)
            if target_norm in line_norm or line_norm in target_norm:
                # Prefer exact match or close match
                if abs(len(line_norm) - len(target_norm)) <= 2:
                    return i
        
        # Strategy 3: Fuzzy match - find best similarity (simple approach)
        # Count common characters
        best_match_idx = -1
        best_score = 0
        target_chars = set(target_norm.replace(" ", ""))
        
        for i, line in enumerate(lines):
            line_norm = normalize_text(line)
            line_chars = set(line_norm.replace(" ", ""))
            common = len(target_chars & line_chars)
            score = common / max(len(target_chars), 1)
            if score > best_score and score > 0.7:  # At least 70% match
                best_score = score
                best_match_idx = i
        
        return best_match_idx if best_match_idx >= 0 else -1
        
    except Exception as e:
        # Silent failure - OCR is optional
        return -1

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: ocr_find_chat.py <screenshot_path> <target_name>"}), file=sys.stderr)
        sys.exit(1)
    
    screenshot_path = sys.argv[1]
    target_name = sys.argv[2]
    
    if not os.path.exists(screenshot_path):
        print(json.dumps({"error": f"Screenshot not found: {screenshot_path}"}), file=sys.stderr)
        sys.exit(1)
    
    index = find_chat_in_screenshot(screenshot_path, target_name)
    
    result = {"index": index, "found": index >= 0}
    print(json.dumps(result))
    
    sys.exit(0 if index >= 0 else 1)

if __name__ == "__main__":
    main()
