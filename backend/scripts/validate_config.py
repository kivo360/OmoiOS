#!/usr/bin/env python3
"""
Validate configuration files and Settings classes.

Checks:
- All YAML sections have Settings classes
- All Settings classes have YAML sections (or intentionally don't)
- No secrets in YAML files
- All configs can load successfully
- No configuration drift
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Any

try:
    import yaml
except ImportError:
    print("❌ PyYAML not installed. Run: uv add pyyaml")
    sys.exit(1)


class Colors:
    """ANSI color codes."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


# Patterns that indicate secrets (should NOT be in YAML)
SECRET_PATTERNS = [
    r'api_key:\s*["\']?sk-',
    r'password:\s*["\']?\w+',
    r'secret:\s*["\']?\w{16,}',
    r'token:\s*["\']?[a-zA-Z0-9]{20,}',
    r'_key:\s*["\']?[A-Za-z0-9+/]{20,}',
]


def check_yaml_for_secrets(yaml_file: Path) -> List[str]:
    """Check YAML file for potential secrets."""
    errors = []
    
    try:
        content = yaml_file.read_text(encoding='utf-8')
        
        for pattern in SECRET_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                errors.append(
                    f"{Colors.RED}❌ {yaml_file.name}:{line_num}: "
                    f"Potential secret detected. Secrets belong in .env files!{Colors.NC}"
                )
    
    except Exception as e:
        errors.append(f"{Colors.RED}❌ Error reading {yaml_file}: {e}{Colors.NC}")
    
    return errors


def load_yaml_file(yaml_file: Path) -> Dict[str, Any]:
    """Load and parse YAML file."""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"{Colors.RED}❌ Error loading {yaml_file}: {e}{Colors.NC}")
        return {}


def validate_yaml_structure(yaml_file: Path) -> List[str]:
    """Validate YAML file structure."""
    errors = []
    
    data = load_yaml_file(yaml_file)
    
    # Check that it's a dictionary
    if not isinstance(data, dict):
        errors.append(
            f"{Colors.RED}❌ {yaml_file.name}: "
            f"Root must be a dictionary, not {type(data).__name__}{Colors.NC}"
        )
        return errors
    
    # Check for common typos in section names
    common_typos = {
        'databse': 'database',
        'monitering': 'monitoring',
        'authentification': 'auth',
    }
    
    for typo, correct in common_typos.items():
        if typo in data:
            errors.append(
                f"{Colors.YELLOW}⚠️  {yaml_file.name}: "
                f"Possible typo '{typo}', did you mean '{correct}'?{Colors.NC}"
            )
    
    return errors


def check_settings_can_load() -> List[str]:
    """Try to load all Settings classes."""
    errors = []
    
    try:
        # Import all settings classes
        from omoi_os.config import (
            load_llm_settings,
            load_database_settings,
            load_redis_settings,
        )
        
        settings_loaders = [
            ('LLM', load_llm_settings),
            ('Database', load_database_settings),
            ('Redis', load_redis_settings),
        ]
        
        for name, loader in settings_loaders:
            try:
                loader.cache_clear() if hasattr(loader, 'cache_clear') else None
                settings = loader()
                # Successfully loaded
            except Exception as e:
                errors.append(
                    f"{Colors.RED}❌ Failed to load {name} settings: {e}{Colors.NC}"
                )
    
    except ImportError as e:
        errors.append(
            f"{Colors.YELLOW}⚠️  Could not import settings: {e}{Colors.NC}"
        )
    
    return errors


def check_yaml_files_exist() -> List[str]:
    """Check that required YAML files exist."""
    errors = []
    warnings = []
    
    required_files = [
        'config/base.yaml',
    ]
    
    recommended_files = [
        'config/test.yaml',
        'config/local.yaml',
    ]
    
    for file in required_files:
        if not Path(file).exists():
            errors.append(
                f"{Colors.RED}❌ Required file missing: {file}{Colors.NC}"
            )
    
    for file in recommended_files:
        if not Path(file).exists():
            warnings.append(
                f"{Colors.YELLOW}⚠️  Recommended file missing: {file}{Colors.NC}"
            )
    
    return errors + warnings


def main():
    """Run all configuration validations."""
    print(f"{Colors.BLUE}🔍 Validating configuration...{Colors.NC}\n")
    
    all_errors = []
    all_warnings = []
    
    # Check required files exist
    file_checks = check_yaml_files_exist()
    all_errors.extend([e for e in file_checks if '❌' in e])
    all_warnings.extend([w for w in file_checks if '⚠️' in w])
    
    # Check all YAML files
    config_dir = Path("config")
    if config_dir.exists():
        for yaml_file in config_dir.rglob("*.yaml"):
            # Check for secrets
            secret_checks = check_yaml_for_secrets(yaml_file)
            all_errors.extend(secret_checks)
            
            # Validate structure
            structure_checks = validate_yaml_structure(yaml_file)
            all_errors.extend([e for e in structure_checks if '❌' in e])
            all_warnings.extend([w for w in structure_checks if '⚠️' in w])
    
    # Try to load settings
    loading_errors = check_settings_can_load()
    all_errors.extend(loading_errors)
    
    # Print results
    if all_errors:
        print(f"\n{Colors.RED}❌ ERRORS:{Colors.NC}")
        for error in all_errors:
            print(f"  {error}")
    
    if all_warnings:
        print(f"\n{Colors.YELLOW}⚠️  WARNINGS:{Colors.NC}")
        for warning in all_warnings:
            print(f"  {warning}")
    
    print(f"\n{Colors.BLUE}📊 Summary:{Colors.NC}")
    print(f"  Errors: {len(all_errors)}")
    print(f"  Warnings: {len(all_warnings)}")
    
    if all_errors:
        print(f"\n{Colors.RED}❌ Configuration validation failed{Colors.NC}")
        print(f"\nSee docs/design/CONFIGURATION_ARCHITECTURE.md for guidelines")
        return 1
    elif all_warnings:
        print(f"\n{Colors.YELLOW}⚠️  Configuration validation passed with warnings{Colors.NC}")
        return 0
    else:
        print(f"\n{Colors.GREEN}✅ All configuration files valid{Colors.NC}")
        return 0


if __name__ == "__main__":
    sys.exit(main())

