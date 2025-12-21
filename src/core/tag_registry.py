"""
Tag Registry
===========

Defines a controlled vocabulary for tags with three orthogonal dimensions:
- tech/: Technologies, languages, frameworks
- activity/: What you were doing
- topic/: Problem domains

Each tag includes aliases for normalization and patterns for auto-detection.
"""
import re
from typing import Dict, List, Optional, Set

# Type alias for tag registry structure
TagDefinition = Dict[str, Dict[str, Dict[str, List[str]]]]


TAG_REGISTRY: TagDefinition = {
    "tech": {
        "python": {
            "aliases": ["py", "python3", "cpython"],
            "file_extensions": [".py", ".pyi", ".pyx"],
            "patterns": [
                r"import\s+\w+",
                r"from\s+\w+\s+import",
                r"def\s+\w+\(",
                r"class\s+\w+",
                r"@\w+",
                r"pip\s+install",
                r"python\s+",
            ],
        },
        "dagster": {
            "aliases": [],
            "patterns": [
                r"@asset",
                r"@op",
                r"Definitions\(",
                r"dagster\.",
                r"from\s+dagster\s+import",
            ],
        },
        "dbt": {
            "aliases": ["data-build-tool"],
            "patterns": [
                r"dbt\s+run",
                r"dbt\s+test",
                r"dbt\s+compile",
                r"{{.*}}",
                r"ref\(",
                r"source\(",
            ],
        },
        "javascript": {
            "aliases": ["js", "node", "nodejs"],
            "file_extensions": [".js", ".mjs", ".cjs"],
            "patterns": [
                r"const\s+\w+\s*=",
                r"let\s+\w+\s*=",
                r"function\s+\w+\(",
                r"require\(",
                r"import\s+.*\s+from",
            ],
        },
        "typescript": {
            "aliases": ["ts"],
            "file_extensions": [".ts", ".tsx"],
            "patterns": [
                r"interface\s+\w+",
                r"type\s+\w+\s*=",
                r":\s*\w+\s*[=;]",
                r"<.*>",
            ],
        },
        "react": {
            "aliases": ["reactjs"],
            "patterns": [
                r"import\s+.*\s+from\s+['\"]react['\"]",
                r"<[A-Z]\w+",
                r"useState\(",
                r"useEffect\(",
                r"React\.",
            ],
        },
        "postgres": {
            "aliases": ["postgresql", "psql"],
            "patterns": [
                r"CREATE\s+TABLE",
                r"SELECT\s+.*\s+FROM",
                r"INSERT\s+INTO",
                r"postgresql://",
                r"psycopg2",
            ],
        },
        "sqlite": {
            "aliases": ["sqlite3"],
            "patterns": [
                r"sqlite3\.",
                r"\.db\b",
                r"CREATE\s+TABLE.*\(.*\)",
            ],
        },
        "docker": {
            "aliases": [],
            "patterns": [
                r"FROM\s+\w+",
                r"RUN\s+",
                r"docker\s+run",
                r"docker\s+build",
                r"Dockerfile",
            ],
        },
        "git": {
            "aliases": ["github", "gitlab"],
            "patterns": [
                r"git\s+commit",
                r"git\s+push",
                r"git\s+pull",
                r"git\s+branch",
                r"\.git/",
            ],
        },
        "flask": {
            "aliases": [],
            "patterns": [
                r"from\s+flask\s+import",
                r"@app\.route",
                r"Flask\(",
            ],
        },
        "fastapi": {
            "aliases": [],
            "patterns": [
                r"from\s+fastapi\s+import",
                r"@app\.(get|post|put|delete)",
                r"FastAPI\(",
            ],
        },
        "pandas": {
            "aliases": ["pd"],
            "patterns": [
                r"import\s+pandas",
                r"pd\.DataFrame",
                r"\.read_csv\(",
                r"\.groupby\(",
            ],
        },
        "pytest": {
            "aliases": [],
            "patterns": [
                r"def\s+test_\w+",
                r"pytest\.",
                r"@pytest\.",
                r"assert\s+",
            ],
        },
    },
    "activity": {
        "debugging": {
            "aliases": ["debug", "bugfix", "troubleshooting", "error"],
            "chat_modes": ["debug"],
            "patterns": [
                r"Traceback",
                r"Error:",
                r"Exception:",
                r"failed",
                r"bug",
                r"fix",
                r"broken",
                r"not working",
            ],
        },
        "refactoring": {
            "aliases": ["refactor", "cleanup", "restructure"],
            "patterns": [
                r"refactor",
                r"clean up",
                r"restructure",
                r"improve code",
                r"code review",
            ],
        },
        "learning": {
            "aliases": ["tutorial", "documentation", "explain"],
            "patterns": [
                r"how to",
                r"what is",
                r"explain",
                r"tutorial",
                r"learn",
                r"understand",
            ],
        },
        "feature-dev": {
            "aliases": ["feature", "implementation", "new feature"],
            "patterns": [
                r"implement",
                r"add feature",
                r"new functionality",
                r"create",
                r"build",
            ],
        },
        "testing": {
            "aliases": ["test", "unit-test", "integration-test"],
            "patterns": [
                r"write test",
                r"test case",
                r"unit test",
                r"integration test",
                r"test coverage",
            ],
        },
        "deployment": {
            "aliases": ["deploy", "production", "release"],
            "patterns": [
                r"deploy",
                r"production",
                r"release",
                r"CI/CD",
                r"pipeline",
            ],
        },
        "optimization": {
            "aliases": ["performance", "optimize", "speed"],
            "patterns": [
                r"optimize",
                r"performance",
                r"speed up",
                r"faster",
                r"bottleneck",
            ],
        },
        "documentation": {
            "aliases": ["docs", "docstring", "comment"],
            "patterns": [
                r"documentation",
                r"docstring",
                r"add comments",
                r"README",
            ],
        },
    },
    "topic": {
        "auth": {
            "aliases": ["authentication", "authorization", "oauth", "jwt"],
            "patterns": [
                r"login",
                r"password",
                r"token",
                r"session",
                r"oauth",
                r"jwt",
                r"authentication",
                r"authorization",
            ],
        },
        "api": {
            "aliases": ["rest", "graphql", "endpoint"],
            "patterns": [
                r"API",
                r"endpoint",
                r"REST",
                r"GraphQL",
                r"request",
                r"response",
            ],
        },
        "database-design": {
            "aliases": ["schema", "migration", "sql"],
            "patterns": [
                r"database schema",
                r"migration",
                r"CREATE TABLE",
                r"foreign key",
                r"index",
            ],
        },
        "caching": {
            "aliases": ["cache", "redis", "memcached"],
            "patterns": [
                r"cache",
                r"redis",
                r"memcached",
                r"TTL",
                r"cache hit",
            ],
        },
        "deployment": {
            "aliases": ["production", "infrastructure", "devops"],
            "patterns": [
                r"deploy",
                r"production",
                r"infrastructure",
                r"server",
                r"hosting",
            ],
        },
        "security": {
            "aliases": ["vulnerability", "encryption", "ssl"],
            "patterns": [
                r"security",
                r"vulnerability",
                r"encryption",
                r"SSL",
                r"TLS",
                r"XSS",
                r"SQL injection",
            ],
        },
        "ui": {
            "aliases": ["frontend", "interface", "design"],
            "patterns": [
                r"UI",
                r"frontend",
                r"interface",
                r"design",
                r"component",
                r"CSS",
            ],
        },
        "data-processing": {
            "aliases": ["etl", "transformation", "pipeline"],
            "patterns": [
                r"ETL",
                r"transform",
                r"pipeline",
                r"data processing",
                r"extract",
                r"load",
            ],
        },
    },
}


class TagRegistry:
    """
    Manages the tag registry with alias resolution and pattern matching.
    
    Provides methods to:
    - Resolve aliases to canonical tags
    - Match patterns against content
    - Validate tags against registry
    - Get file extension mappings
    """
    
    def __init__(self, registry: Optional[TagDefinition] = None):
        """
        Initialize tag registry.
        
        Parameters
        ----
        registry : TagDefinition, optional
            Tag registry dictionary. If None, uses default TAG_REGISTRY.
        """
        self.registry = registry or TAG_REGISTRY
        
        # Build alias -> canonical tag mapping
        self._alias_map: Dict[str, str] = {}
        self._build_alias_map()
        
        # Build compiled pattern cache
        self._pattern_cache: Dict[str, List[re.Pattern]] = {}
        self._compile_patterns()
    
    def _build_alias_map(self) -> None:
        """Build mapping from aliases to canonical tags."""
        for dimension, tags in self.registry.items():
            for canonical_tag, definition in tags.items():
                full_tag = f"{dimension}/{canonical_tag}"
                # Map canonical tag to itself
                self._alias_map[canonical_tag] = full_tag
                self._alias_map[full_tag] = full_tag
                
                # Map aliases
                for alias in definition.get("aliases", []):
                    self._alias_map[alias] = full_tag
                    self._alias_map[f"{dimension}/{alias}"] = full_tag
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        for dimension, tags in self.registry.items():
            for canonical_tag, definition in tags.items():
                full_tag = f"{dimension}/{canonical_tag}"
                patterns = []
                
                for pattern_str in definition.get("patterns", []):
                    try:
                        patterns.append(re.compile(pattern_str, re.IGNORECASE))
                    except re.error as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Invalid pattern for {full_tag}: {pattern_str} - {e}")
                
                self._pattern_cache[full_tag] = patterns
    
    def resolve_alias(self, raw_tag: str) -> Optional[str]:
        """
        Resolve a tag alias to its canonical form.
        
        Parameters
        ----
        raw_tag : str
            Raw tag string (may be alias or canonical)
            
        Returns
        ----
        str, optional
            Canonical tag in format "dimension/tag", or None if not found
        """
        # Normalize input
        normalized = raw_tag.lower().strip()
        
        # Try exact match first
        if normalized in self._alias_map:
            return self._alias_map[normalized]
        
        # Try without dimension prefix
        if "/" in normalized:
            parts = normalized.split("/", 1)
            if len(parts) == 2:
                dimension, tag = parts
                if tag in self._alias_map:
                    return self._alias_map[tag]
        
        return None
    
    def validate_tag(self, tag: str) -> bool:
        """
        Validate that a tag exists in the registry.
        
        Parameters
        ----
        tag : str
            Tag to validate (can be alias or canonical)
            
        Returns
        ----
        bool
            True if tag is valid, False otherwise
        """
        return self.resolve_alias(tag) is not None
    
    def get_file_extension_tags(self, file_extensions: List[str]) -> Set[str]:
        """
        Get tags based on file extensions.
        
        Parameters
        ----
        file_extensions : List[str]
            List of file extensions (e.g., [".py", ".js"])
            
        Returns
        ----
        Set[str]
            Set of canonical tags matching the extensions
        """
        tags = set()
        
        for dimension, tag_defs in self.registry.items():
            for canonical_tag, definition in tag_defs.items():
                registry_extensions = definition.get("file_extensions", [])
                
                for ext in file_extensions:
                    if ext.lower() in [e.lower() for e in registry_extensions]:
                        tags.add(f"{dimension}/{canonical_tag}")
        
        return tags
    
    def get_chat_mode_tags(self, chat_mode: str) -> Set[str]:
        """
        Get tags based on chat mode.
        
        Parameters
        ----
        chat_mode : str
            Chat mode (e.g., "debug", "edit")
            
        Returns
        ----
        Set[str]
            Set of canonical tags matching the chat mode
        """
        tags = set()
        normalized_mode = chat_mode.lower()
        
        for dimension, tag_defs in self.registry.items():
            for canonical_tag, definition in tag_defs.items():
                chat_modes = definition.get("chat_modes", [])
                
                if normalized_mode in [m.lower() for m in chat_modes]:
                    tags.add(f"{dimension}/{canonical_tag}")
        
        return tags
    
    def match_patterns(self, content: str) -> Set[str]:
        """
        Match content against registry patterns.
        
        Parameters
        ----
        content : str
            Text content to analyze
            
        Returns
        ----
        Set[str]
            Set of canonical tags matching the content
        """
        tags = set()
        
        for full_tag, patterns in self._pattern_cache.items():
            for pattern in patterns:
                if pattern.search(content):
                    tags.add(full_tag)
                    break  # Only need one match per tag
        
        return tags
    
    def get_all_tags(self) -> List[str]:
        """
        Get all canonical tags in the registry.
        
        Returns
        ----
        List[str]
            List of canonical tags in format "dimension/tag"
        """
        all_tags = []
        for dimension, tags in self.registry.items():
            for canonical_tag in tags.keys():
                all_tags.append(f"{dimension}/{canonical_tag}")
        return sorted(all_tags)
    
    def get_tags_by_dimension(self, dimension: str) -> List[str]:
        """
        Get all tags for a specific dimension.
        
        Parameters
        ----
        dimension : str
            Dimension name (e.g., "tech", "activity", "topic")
            
        Returns
        ----
        List[str]
            List of canonical tags in that dimension
        """
        if dimension not in self.registry:
            return []
        
        return [f"{dimension}/{tag}" for tag in self.registry[dimension].keys()]

