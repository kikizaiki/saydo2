#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR helper script to find Chrome tab by keywords.
Takes a screenshot of Chrome tabs area and returns the index of matching tab.
"""

import sys
import os
import json
import re
from typing import List, Tuple

def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, trim, collapse spaces)."""
    text = (text or "").strip().lower()
    text = text.replace("ё", "е")
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    return text

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts (0.0 to 1.0)."""
    text1_norm = normalize_text(text1)
    text2_norm = normalize_text(text2)
    
    if text1_norm == text2_norm:
        return 1.0
    
    # Check if one contains the other
    if text1_norm in text2_norm or text2_norm in text1_norm:
        return 0.9
    
    # Calculate character overlap
    chars1 = set(text1_norm.replace(" ", ""))
    chars2 = set(text2_norm.replace(" ", ""))
    
    if not chars1 or not chars2:
        return 0.0
    
    intersection = len(chars1 & chars2)
    union = len(chars1 | chars2)
    
    return intersection / union if union > 0 else 0.0

def find_tab_in_screenshot(screenshot_path: str, keywords: str) -> Tuple[int, float]:
    """
    Analyze screenshot to find Chrome tab matching keywords.
    Returns (0-based index, similarity_score) of matching tab, or (-1, 0.0) if not found.
    """
    try:
        # Try using tesseract if available
        import pytesseract
        from PIL import Image
    except ImportError:
        return (-1, 0.0)
    
    try:
        # Open image
        img = Image.open(screenshot_path)
        
        # Get image dimensions to check if it's valid
        if img.size[0] == 0 or img.size[1] == 0:
            return (-1, 0.0)
        
        # Enhance image for better OCR
        # Convert to grayscale
        img_gray = img.convert('L')
        
        # Increase contrast (optional, but can help)
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(img_gray)
        img_gray = enhancer.enhance(2.0)
        
        # Use OCR to extract text
        # Try with Russian + English languages
        # Use --psm 6 for uniform block of text (list of tabs)
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
            return (-1, 0.0)
        
        # Normalize keywords
        keywords_norm = normalize_text(keywords)
        keyword_words = keywords_norm.split()
        
        # Find best match
        best_match_idx = -1
        best_score = 0.0
        
        for i, line in enumerate(lines):
            line_norm = normalize_text(line)
            
            # Strategy 1: Exact match
            if line_norm == keywords_norm:
                return (i, 1.0)
            
            # Strategy 2: All keywords present in line
            all_keywords_present = True
            for keyword_word in keyword_words:
                if keyword_word not in line_norm:
                    all_keywords_present = False
                    break
            
            if all_keywords_present:
                # Calculate similarity based on how many keywords matched
                score = len(keyword_words) / max(len(line_norm.split()), 1)
                if score > best_score:
                    best_score = score
                    best_match_idx = i
                continue
            
            # Strategy 3: Calculate similarity score
            similarity = calculate_similarity(keywords_norm, line_norm)
            
            # Also check if any keyword words match
            word_matches = 0
            for keyword_word in keyword_words:
                if keyword_word in line_norm or line_norm in keyword_word:
                    word_matches += 1
            
            # Combine similarity and word matches
            combined_score = (similarity * 0.6) + (word_matches / len(keyword_words) * 0.4) if keyword_words else similarity
            
            if combined_score > best_score and combined_score > 0.5:  # At least 50% match
                best_score = combined_score
                best_match_idx = i
        
        return (best_match_idx, best_score) if best_match_idx >= 0 else (-1, 0.0)
        
    except Exception as e:
        # Silent failure - OCR is optional
        return (-1, 0.0)

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: ocr_find_chrome_tab.py <screenshot_path> <keywords>"}), file=sys.stderr)
        sys.exit(1)
    
    screenshot_path = sys.argv[1]
    keywords = sys.argv[2]
    
    if not os.path.exists(screenshot_path):
        print(json.dumps({"error": f"Screenshot not found: {screenshot_path}"}), file=sys.stderr)
        sys.exit(1)
    
    index, score = find_tab_in_screenshot(screenshot_path, keywords)
    
    result = {
        "index": index,
        "found": index >= 0,
        "score": round(score, 2)
    }
    print(json.dumps(result))
    
    sys.exit(0 if index >= 0 else 1)

if __name__ == "__main__":
    main()

