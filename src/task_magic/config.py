"""
Configuration Management for Task Magic Framework

This module provides a sophisticated configuration system that supports:
- Multiple configuration sources (files, environment variables, command line)
- Configuration validation and type checking
- Hierarchical configuration merging
- Environment-specific configurations
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ConfigError(Exception):
    """Exception raised for configuration-related errors."""

    pass


@dataclass
class ConfigSource:
    """Represents a configuration source with priority and metadata."""

    name: str
    data: Dict[str, Any]
    priority: int = 0
    source_type: str = "unknown"
    file_path: Optional[Path] = None


class Config:
    """
    Sophisticated configuration management system.

    This class handles loading, merging, and validating configuration from
    multiple sources with a clear priority system.
    """

    def __init__(self, config_dir: Union[str, Path] = None):
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.sources: List[ConfigSource] = []
        self._data: Dict[str, Any] = {}
        self._loaded = False

    def load(self, reload: bool = False) -> "Config":
        """
        Load configuration from all available sources.

        Args:
            reload: Force reload even if already loaded

        Returns:
            Self for method chaining
        """
        if self._loaded and not reload:
            return self

        self.sources.clear()
        self._data.clear()

        # Load in priority order (higher priority overwrites lower)
        self._load_default_config()  # Priority 0
        self._load_file_configs()  # Priority 10-50
        self._load_environment_vars()  # Priority 60
        self._load_runtime_config()  # Priority 70

        # Merge all sources
        self._merge_sources()
        self._loaded = True

        return self

    def _load_default_config(self):
        """Load default configuration values."""
        defaults = {
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": None,
            },
            "tasks": {
                "discovery_paths": ["src.tasks"],
                "parallel_execution": False,
                "timeout": 300,
            },
            "output": {"format": "json", "directory": "output", "verbose": False},
            "database": {"auto_discover": True, "backup_before_read": False},
        }

        self.sources.append(
            ConfigSource(
                name="defaults", data=defaults, priority=0, source_type="internal"
            )
        )

    def _load_file_configs(self):
        """Load configuration from files in priority order."""
        config_files = [
            ("config.yaml", 10),
            ("config.yml", 10),
            ("config.json", 10),
            (f"config.{self._get_environment()}.yaml", 20),
            (f"config.{self._get_environment()}.yml", 20),
            (f"config.{self._get_environment()}.json", 20),
            ("local.config.yaml", 30),
            ("local.config.yml", 30),
            ("local.config.json", 30),
            (".taskmagic.yaml", 40),
            (".taskmagic.yml", 40),
            (".taskmagic.json", 40),
            (".taskmagic", 50),  # YAML format assumed
        ]

        for filename, priority in config_files:
            file_path = self.config_dir / filename
            if file_path.exists():
                try:
                    data = self._load_file(file_path)
                    self.sources.append(
                        ConfigSource(
                            name=filename,
                            data=data,
                            priority=priority,
                            source_type="file",
                            file_path=file_path,
                        )
                    )
                except Exception as e:
                    raise ConfigError(f"Error loading config file {file_path}: {e}")

    def _load_environment_vars(self):
        """Load configuration from environment variables."""
        env_data = {}
        prefix = "TASKMAGIC_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert TASKMAGIC_LOGGING_LEVEL -> logging.level
                config_key = key[len(prefix) :].lower().replace("_", ".")

                # Try to parse as JSON first, then as string
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    parsed_value = value

                # Set nested value
                self._set_nested_value(env_data, config_key, parsed_value)

        if env_data:
            self.sources.append(
                ConfigSource(
                    name="environment",
                    data=env_data,
                    priority=60,
                    source_type="environment",
                )
            )

    def _load_runtime_config(self):
        """Load runtime configuration (command line args, etc.)."""
        # This would be populated by the CLI or other runtime sources
        # For now, we'll just create a placeholder
        pass

    def _load_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from a specific file."""
        with open(file_path, "r", encoding="utf-8") as f:
            if (
                file_path.suffix.lower() in [".yaml", ".yml"]
                or file_path.name == ".taskmagic"
            ):
                if not HAS_YAML:
                    raise ConfigError(
                        "PyYAML is required to load YAML config files. Install with: pip install pyyaml"
                    )
                return yaml.safe_load(f) or {}
            elif file_path.suffix.lower() == ".json":
                return json.load(f)
            else:
                # Try YAML first, then JSON
                content = f.read()
                if HAS_YAML:
                    try:
                        return yaml.safe_load(content) or {}
                    except:
                        pass
                try:
                    return json.loads(content)
                except:
                    raise ConfigError(f"Unknown config file format: {file_path}")

    def _merge_sources(self):
        """Merge all configuration sources by priority."""
        # Sort by priority (lower numbers first)
        sorted_sources = sorted(self.sources, key=lambda s: s.priority)

        for source in sorted_sources:
            self._deep_merge(self._data, source.data)

    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Deep merge source dictionary into target dictionary."""
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(target[key], value)
            else:
                target[key] = value

    def _set_nested_value(self, data: Dict[str, Any], key_path: str, value: Any):
        """Set a nested value using dot notation (e.g., 'logging.level')."""
        keys = key_path.split(".")
        current = data

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _get_environment(self) -> str:
        """Get the current environment (development, production, etc.)."""
        return os.getenv("TASKMAGIC_ENV", os.getenv("ENV", "development")).lower()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'logging.level')
            default: Default value if key is not found

        Returns:
            The configuration value or default
        """
        if not self._loaded:
            self.load()

        keys = key.split(".")
        current = self._data

        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any, priority: int = 100):
        """
        Set a configuration value at runtime.

        Args:
            key: Configuration key in dot notation
            value: Value to set
            priority: Priority for this configuration source
        """
        # Create a runtime source for this value
        runtime_data = {}
        self._set_nested_value(runtime_data, key, value)

        # Remove any existing runtime source with the same key
        self.sources = [
            s
            for s in self.sources
            if not (s.name == f"runtime.{key}" and s.source_type == "runtime")
        ]

        # Add new runtime source
        self.sources.append(
            ConfigSource(
                name=f"runtime.{key}",
                data=runtime_data,
                priority=priority,
                source_type="runtime",
            )
        )

        # Re-merge
        self._merge_sources()

    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return self.get(key, None) is not None

    def to_dict(self) -> Dict[str, Any]:
        """Return the complete configuration as a dictionary."""
        if not self._loaded:
            self.load()
        return self._data.copy()

    def save(self, file_path: Union[str, Path] = None, format: str = "yaml"):
        """
        Save the current configuration to a file.

        Args:
            file_path: Path to save the configuration
            format: File format ('yaml', 'json')
        """
        if file_path is None:
            file_path = self.config_dir / f"config.{format}"
        else:
            file_path = Path(file_path)

        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            if format.lower() == "json":
                json.dump(self._data, f, indent=2, sort_keys=True)
            else:  # yaml
                if not HAS_YAML:
                    raise ConfigError(
                        "PyYAML is required to save YAML config files. Install with: pip install pyyaml"
                    )
                yaml.dump(self._data, f, default_flow_style=False, sort_keys=True)

    def validate(self, schema: Dict[str, Any]) -> bool:
        """
        Validate the configuration against a schema.

        Args:
            schema: Validation schema

        Returns:
            True if validation passes

        Raises:
            ConfigError: If validation fails
        """

        # Simple validation implementation
        # In a real-world scenario, you might use jsonschema or similar
        def validate_recursive(data, schema_part, path=""):
            for key, expected_type in schema_part.items():
                current_path = f"{path}.{key}" if path else key

                if key not in data:
                    raise ConfigError(f"Missing required configuration: {current_path}")

                value = data[key]

                if isinstance(expected_type, dict):
                    if not isinstance(value, dict):
                        raise ConfigError(
                            f"Configuration {current_path} must be a dictionary"
                        )
                    validate_recursive(value, expected_type, current_path)
                elif isinstance(expected_type, type):
                    if not isinstance(value, expected_type):
                        raise ConfigError(
                            f"Configuration {current_path} must be of type {expected_type.__name__}"
                        )

        validate_recursive(self._data, schema)
        return True

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any):
        """Allow dictionary-style assignment."""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator."""
        return self.has(key)

    def __str__(self) -> str:
        return f"Config(sources={len(self.sources)}, loaded={self._loaded})"

    def __repr__(self) -> str:
        return f"<Config(config_dir='{self.config_dir}', sources={len(self.sources)})>"
