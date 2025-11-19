#!/usr/bin/env python3
"""Thin shim script to keep the standalone runner small and delegate
to the package entrypoint.
"""
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so `from web_crawler.__main__ import main`
# resolves to the package, not to this script file as a top-level module.
repo_root = Path(__file__).resolve().parent
if repo_root.name == "web_crawler":
    repo_root = repo_root.parent
sys.path.insert(0, str(repo_root))

from web_crawler.__main__ import main


if __name__ == "__main__":
    main()
