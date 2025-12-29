#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health check utilities for system components.
"""

import os
import sys
import subprocess
import requests
from typing import Dict, List, Tuple, Optional

def check_hammerspoon_server(hammer_url: str = "http://127.0.0.1:7733", timeout: int = 2) -> Tuple[bool, str]:
    """
    Check if Hammerspoon HTTP server is running.
    
    Returns:
        (is_available, error_message)
    """
    try:
        response = requests.get(hammer_url.replace("/cmd", "/health"), timeout=timeout)
        if response.status_code == 200:
            return True, "Hammerspoon server is running"
    except requests.exceptions.ConnectionError:
        return False, f"Hammerspoon server is not running at {hammer_url}. Please start Hammerspoon and reload the configuration."
    except requests.exceptions.Timeout:
        return False, f"Hammerspoon server timeout at {hammer_url}"
    except Exception as e:
        return False, f"Error checking Hammerspoon server: {e}"
    
    # Try to check if server responds to /cmd endpoint
    try:
        response = requests.post(
            f"{hammer_url}/cmd",
            json={"cmd": "ping"},
            timeout=timeout
        )
        if response.status_code in [200, 404]:  # 404 is ok, means server is running
            return True, "Hammerspoon server is running"
    except requests.exceptions.ConnectionError:
        return False, f"Hammerspoon server is not running at {hammer_url}. Please start Hammerspoon and reload the configuration."
    except Exception as e:
        return False, f"Error checking Hammerspoon server: {e}"
    
    return False, "Hammerspoon server status unknown"

def check_tesseract() -> Tuple[bool, str]:
    """Check if Tesseract OCR is installed."""
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split('\n')[0] if result.stdout else "unknown"
            return True, f"Tesseract OCR is installed ({version})"
        return False, "Tesseract OCR is not installed"
    except FileNotFoundError:
        return False, "Tesseract OCR is not installed. Install with: brew install tesseract"
    except Exception as e:
        return False, f"Error checking Tesseract: {e}"

def check_python_packages() -> Tuple[bool, List[str]]:
    """Check if required Python packages are installed."""
    required_packages = {
        "pytesseract": "pytesseract",
        "PIL": "Pillow",
        "requests": "requests"
    }
    
    missing = []
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)
    
    return len(missing) == 0, missing

def check_chrome_running() -> Tuple[bool, str]:
    """Check if Chrome is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "Google Chrome"],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            return True, "Google Chrome is running"
        return False, "Google Chrome is not running. Please start Chrome."
    except Exception as e:
        return False, f"Error checking Chrome: {e}"

def run_health_checks(hammer_url: str = "http://127.0.0.1:7733") -> Dict[str, Tuple[bool, str]]:
    """
    Run all health checks.
    
    Returns:
        Dictionary with check name -> (is_ok, message)
    """
    results = {}
    
    # Check Hammerspoon
    results["hammerspoon"] = check_hammerspoon_server(hammer_url)
    
    # Check Tesseract (optional for OCR)
    results["tesseract"] = check_tesseract()
    
    # Check Python packages
    packages_ok, missing = check_python_packages()
    if packages_ok:
        results["python_packages"] = (True, "All required Python packages are installed")
    else:
        results["python_packages"] = (False, f"Missing packages: {', '.join(missing)}. Install with: pip install {' '.join(missing)}")
    
    # Check Chrome (optional, only for Chrome commands)
    results["chrome"] = check_chrome_running()
    
    return results

def print_health_report(results: Dict[str, Tuple[bool, str]]) -> bool:
    """Print health check report. Returns True if all critical checks passed."""
    print("\n" + "="*60)
    print("🔍 HEALTH CHECK REPORT")
    print("="*60)
    
    critical_checks = ["hammerspoon"]
    all_critical_ok = True
    
    for check_name, (is_ok, message) in results.items():
        status = "✅" if is_ok else "❌"
        critical = " (CRITICAL)" if check_name in critical_checks else ""
        print(f"{status} {check_name.upper()}{critical}: {message}")
        
        if check_name in critical_checks and not is_ok:
            all_critical_ok = False
    
    print("="*60 + "\n")
    
    return all_critical_ok

