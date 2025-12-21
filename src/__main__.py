"""
Main entry point for running the package as a module.

Uses the new Click-based CLI. The old argparse-based CLI in src/cli.py
is deprecated and will be removed in a future version.
"""
import sys

# New Click-based CLI from src/cli/__init__.py
from src.cli import main

if __name__ == "__main__":
    sys.exit(main())

