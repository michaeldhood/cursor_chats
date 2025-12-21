"""
Main entry point for running the package as a module.

Supports both old argparse-based CLI and new Click-based CLI via feature flag.
Set USE_NEW_CLI=true to use the new Click CLI during migration.
"""
import os
import sys
import importlib.util

# Feature flag for incremental CLI migration
# Note: src/cli.py (old) and src/cli/ (new package) both exist during migration
# We must be explicit about which to import to avoid Python's package preference
if os.getenv('USE_NEW_CLI', 'false').lower() == 'true':
    # New Click-based CLI from src/cli/__init__.py
    from src.cli import main
else:
    # Old argparse-based CLI from src/cli.py (explicitly load the module file)
    import pathlib
    cli_py_path = pathlib.Path(__file__).parent / 'cli.py'
    spec = importlib.util.spec_from_file_location('old_cli', cli_py_path)
    old_cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_cli)
    main = old_cli.main

if __name__ == "__main__":
    sys.exit(main())

