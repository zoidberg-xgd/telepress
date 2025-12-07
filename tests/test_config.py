"""
Tests for config module.
"""
import unittest
import os
import json
import tempfile
from unittest.mock import patch
from pathlib import Path

from telepress.config import (
    load_config, get_image_host_config,
    _load_config_file, _load_from_env, _merge_config
)


class TestLoadConfigFile(unittest.TestCase):
    """Tests for _load_config_file function."""
    
    def test_load_json_file(self):
        """Test loading JSON config file."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({'key': 'value', 'nested': {'a': 1}}, f)
            tmp_path = f.name
        
        try:
            config = _load_config_file(tmp_path)
            self.assertEqual(config['key'], 'value')
            self.assertEqual(config['nested']['a'], 1)
        finally:
            os.unlink(tmp_path)
    
    def test_load_empty_json_file(self):
        """Test loading empty JSON file."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            f.write('')
            tmp_path = f.name
        
        try:
            config = _load_config_file(tmp_path)
            self.assertEqual(config, {})
        finally:
            os.unlink(tmp_path)
    
    def test_load_nonexistent_file(self):
        """Test loading non-existent file returns empty dict."""
        config = _load_config_file('/nonexistent/path/config.json')
        self.assertEqual(config, {})
    
    def test_load_yaml_file(self):
        """Test loading YAML config file (if PyYAML installed)."""
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")
        
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.yaml', delete=False
        ) as f:
            f.write('key: yaml_value')
            tmp_path = f.name
        
        try:
            config = _load_config_file(tmp_path)
            self.assertEqual(config['key'], 'yaml_value')
        finally:
            os.unlink(tmp_path)


class TestLoadFromEnv(unittest.TestCase):
    """Tests for _load_from_env function."""
    
    def test_load_simple_env_var(self):
        """Test loading simple environment variable."""
        with patch.dict(os.environ, {'TELEPRESS_TOKEN': 'test_token'}):
            config = _load_from_env()
            self.assertEqual(config['token'], 'test_token')
    
    def test_load_image_host_env_vars(self):
        """Test loading image host environment variables."""
        env_vars = {
            'TELEPRESS_IMAGE_HOST_TYPE': 'imgbb',
            'TELEPRESS_IMAGE_HOST_API_KEY': 'my_key'
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = _load_from_env()
            self.assertEqual(config['image_host']['type'], 'imgbb')
            self.assertEqual(config['image_host']['api_key'], 'my_key')
    
    def test_ignores_non_telepress_vars(self):
        """Test that non-TELEPRESS_ vars are ignored."""
        with patch.dict(os.environ, {'OTHER_VAR': 'value'}, clear=False):
            config = _load_from_env()
            self.assertNotIn('other_var', config)


class TestMergeConfig(unittest.TestCase):
    """Tests for _merge_config function."""
    
    def test_merge_simple(self):
        """Test simple merge."""
        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        result = _merge_config(base, override)
        self.assertEqual(result, {'a': 1, 'b': 3, 'c': 4})
    
    def test_merge_nested(self):
        """Test nested dict merge."""
        base = {'a': {'x': 1, 'y': 2}}
        override = {'a': {'y': 3, 'z': 4}}
        result = _merge_config(base, override)
        self.assertEqual(result, {'a': {'x': 1, 'y': 3, 'z': 4}})
    
    def test_merge_does_not_modify_original(self):
        """Test that merge doesn't modify original dicts."""
        base = {'a': 1}
        override = {'b': 2}
        _merge_config(base, override)
        self.assertEqual(base, {'a': 1})
        self.assertEqual(override, {'b': 2})


class TestLoadConfig(unittest.TestCase):
    """Tests for load_config function."""
    
    def test_load_from_explicit_path(self):
        """Test loading config from explicit path."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({'explicit': True}, f)
            tmp_path = f.name
        
        try:
            config = load_config(config_path=tmp_path)
            self.assertTrue(config['explicit'])
        finally:
            os.unlink(tmp_path)
    
    def test_load_from_env_var_path(self):
        """Test loading config from TELEPRESS_CONFIG env var."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({'from_env_path': True}, f)
            tmp_path = f.name
        
        try:
            with patch.dict(os.environ, {'TELEPRESS_CONFIG': tmp_path}):
                config = load_config()
                self.assertTrue(config['from_env_path'])
        finally:
            os.unlink(tmp_path)
    
    def test_env_vars_override_file(self):
        """Test that environment variables override file config."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False
        ) as f:
            json.dump({'key': 'from_file'}, f)
            tmp_path = f.name
        
        try:
            with patch.dict(os.environ, {'TELEPRESS_KEY': 'from_env'}):
                config = load_config(config_path=tmp_path)
                self.assertEqual(config['key'], 'from_env')
        finally:
            os.unlink(tmp_path)


class TestGetImageHostConfig(unittest.TestCase):
    """Tests for get_image_host_config function."""
    
    @patch('telepress.config.load_config')
    def test_returns_image_host_section(self, mock_load):
        """Test that it returns the image_host section."""
        mock_load.return_value = {
            'other': 'stuff',
            'image_host': {'type': 'imgbb', 'api_key': 'key'}
        }
        
        config = get_image_host_config()
        self.assertEqual(config, {'type': 'imgbb', 'api_key': 'key'})
    
    @patch('telepress.config.load_config')
    def test_returns_empty_if_no_image_host(self, mock_load):
        """Test that it returns empty dict if no image_host section."""
        mock_load.return_value = {'other': 'stuff'}
        
        config = get_image_host_config()
        self.assertEqual(config, {})


if __name__ == '__main__':
    unittest.main()
