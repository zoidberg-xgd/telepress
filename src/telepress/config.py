"""
Configuration management for TelePress.

Supports:
- Config file (~/.telepress.json or ~/.telepress.yaml)
- Environment variables (TELEPRESS_*)
"""
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path


DEFAULT_CONFIG_PATHS = [
    Path.home() / '.telepress.json',
    Path.home() / '.telepress.yaml',
    Path.home() / '.telepress.yml',
    Path.home() / '.config' / 'telepress.json',
]


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file or environment variables.
    
    Priority (highest first):
    1. Explicit config_path parameter
    2. TELEPRESS_CONFIG environment variable
    3. Default config file locations
    4. Environment variables (TELEPRESS_*)
    
    Returns:
        Configuration dictionary
    """
    config = {}
    
    # Try to load from file
    if config_path:
        config = _load_config_file(config_path)
    elif os.environ.get('TELEPRESS_CONFIG'):
        config = _load_config_file(os.environ['TELEPRESS_CONFIG'])
    else:
        for path in DEFAULT_CONFIG_PATHS:
            if path.exists():
                config = _load_config_file(str(path))
                break
    
    # Override with environment variables
    env_config = _load_from_env()
    config = _merge_config(config, env_config)
    
    return config


def _load_config_file(path: str) -> Dict[str, Any]:
    """Load config from JSON or YAML file."""
    path = Path(path)
    if not path.exists():
        return {}
    
    content = path.read_text()
    
    if path.suffix in ('.yaml', '.yml'):
        try:
            import yaml
            return yaml.safe_load(content) or {}
        except ImportError:
            raise ImportError("PyYAML is required for YAML config. Install with: pip install pyyaml")
    else:
        return json.loads(content) if content.strip() else {}


def _load_from_env() -> Dict[str, Any]:
    """Load config from environment variables."""
    config = {}
    prefix = 'TELEPRESS_'
    
    for key, value in os.environ.items():
        if key.startswith(prefix):
            # Convert TELEPRESS_IMAGE_HOST_API_KEY to image_host.api_key
            parts = key[len(prefix):].lower().split('_')
            
            # Handle nested keys (e.g., IMAGE_HOST_API_KEY -> image_host.api_key)
            if len(parts) >= 2 and parts[0] == 'image' and parts[1] == 'host':
                nested_key = '_'.join(parts[2:])
                if 'image_host' not in config:
                    config['image_host'] = {}
                config['image_host'][nested_key] = value
            else:
                config['_'.join(parts)] = value
    
    return config


def _merge_config(base: Dict, override: Dict) -> Dict:
    """Deep merge two config dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_config(result[key], value)
        else:
            result[key] = value
    return result


def get_image_host_config() -> Dict[str, Any]:
    """Get image host configuration from config file or environment."""
    config = load_config()
    return config.get('image_host', {})


# Example config file format:
"""
~/.telepress.json:
{
    "image_host": {
        "type": "imgbb",
        "api_key": "your_api_key"
    }
}

Or for R2:
{
    "image_host": {
        "type": "r2",
        "account_id": "xxx",
        "access_key_id": "xxx",
        "secret_access_key": "xxx",
        "bucket": "my-bucket",
        "public_url": "https://pub-xxx.r2.dev"
    }
}

Or for custom webhook:
{
    "image_host": {
        "type": "custom",
        "upload_url": "https://your-api.com/upload",
        "method": "POST",
        "file_field": "file",
        "headers": {"Authorization": "Bearer xxx"},
        "response_url_path": "data.url"
    }
}

Environment variables:
TELEPRESS_IMAGE_HOST_TYPE=imgbb
TELEPRESS_IMAGE_HOST_API_KEY=your_key
"""
