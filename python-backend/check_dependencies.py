#!/usr/bin/env python3
"""
Diagnostic script to check if all dependencies are installed correctly.
"""

import subprocess
import sys

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✓ FFmpeg installed: {version_line}")
            return True
    except FileNotFoundError:
        pass
    
    print("✗ FFmpeg not found!")
    print("\n  Installation instructions:")
    print("  Windows (with chocolatey): choco install ffmpeg")
    print("  Windows (with scoop): scoop install ffmpeg")
    print("  Windows (manual): Download from https://ffmpeg.org/download.html")
    print("  macOS (with brew): brew install ffmpeg")
    print("  Linux (Ubuntu/Debian): sudo apt-get install ffmpeg")
    print("  Linux (Fedora): sudo dnf install ffmpeg")
    return False

def check_python_packages():
    """Check if required Python packages are installed."""
    required = ["fastapi", "uvicorn", "faster_whisper"]
    all_good = True
    
    for package in required:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package} installed")
        except ImportError:
            print(f"✗ {package} NOT installed")
            all_good = False
    
    return all_good

def main():
    print("=" * 60)
    print("Dependency Diagnostic Check")
    print("=" * 60)
    
    ffmpeg_ok = check_ffmpeg()
    print()
    python_ok = check_python_packages()
    
    print("\n" + "=" * 60)
    if ffmpeg_ok and python_ok:
        print("✓ All dependencies are installed!")
        sys.exit(0)
    else:
        print("✗ Some dependencies are missing. Please install them.")
        if not python_ok:
            print("\n  Run: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()
