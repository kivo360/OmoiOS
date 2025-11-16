"""Pattern loader for loading and parsing coordination pattern configurations."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class PatternLoader:
    """Loads and parses coordination pattern configurations from YAML files."""

    def __init__(self, patterns_dir: Optional[str] = None):
        """
        Initialize pattern loader.

        Args:
            patterns_dir: Directory containing pattern YAML files.
                         Defaults to omoi_os/config/patterns
        """
        if patterns_dir is None:
            # Default to omoi_os/config/patterns relative to this file
            base_dir = Path(__file__).parent.parent
            patterns_dir = str(base_dir / "config" / "patterns")
        self.patterns_dir = Path(patterns_dir)

    def load_pattern(self, pattern_name: str) -> Dict[str, Any]:
        """
        Load a pattern configuration by name.

        Args:
            pattern_name: Name of the pattern (without .yaml extension)

        Returns:
            Pattern configuration dictionary

        Raises:
            FileNotFoundError: If pattern file not found
            yaml.YAMLError: If pattern file is invalid YAML
        """
        pattern_file = self.patterns_dir / f"{pattern_name}.yaml"
        if not pattern_file.exists():
            raise FileNotFoundError(f"Pattern file not found: {pattern_file}")

        with open(pattern_file, "r") as f:
            pattern_data = yaml.safe_load(f)

        return pattern_data

    def list_patterns(self) -> List[str]:
        """
        List all available pattern names.

        Returns:
            List of pattern names (without .yaml extension)
        """
        if not self.patterns_dir.exists():
            return []

        patterns = []
        for pattern_file in self.patterns_dir.glob("*.yaml"):
            patterns.append(pattern_file.stem)

        return patterns

    def resolve_pattern(
        self, pattern_config: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve template variables in pattern configuration.

        Args:
            pattern_config: Pattern configuration dictionary
            context: Context dictionary with variable values

        Returns:
            Resolved pattern configuration
        """
        import json
        import re

        # Convert to JSON string for template substitution
        config_str = json.dumps(pattern_config)

        # Replace ${variable} with values from context
        def replace_var(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))

        resolved_str = re.sub(r"\$\{(\w+)\}", replace_var, config_str)
        resolved_config = json.loads(resolved_str)

        return resolved_config

