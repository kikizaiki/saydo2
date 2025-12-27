"""
Утилиты для разрешения имен чатов через alias_map.
"""

import re
from typing import Dict, List, Optional, Tuple


def norm(s: str) -> str:
    """Case-insensitive + ё->е + trim + collapse spaces."""
    s = (s or "").strip().lower()
    s = s.replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    return s


def resolve_chat(user_target: str, alias_map: Dict[str, str]) -> Optional[str]:
    """
    Resolve user-provided chat name to canonical name using alias map.
    
    Returns canonical name if found, None otherwise.
    """
    key = norm(user_target)
    return alias_map.get(key)


def build_alias_map(tracked: List[Dict]) -> Tuple[Dict[str, str], Dict[str, Optional[int]]]:
    """
    Build alias map from tracked chats configuration.
    
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
            alias_n = norm(a)
            alias_map[alias_n] = canonical
    
    return alias_map, result_index_map

