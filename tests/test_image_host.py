"""
Tests for image_host module.
"""
import unittest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock, Mock

from telepress.image_host import (
    ImageHost, ImgbbHost, ImgurHost, SmmsHost, R2Host, S3Host, CustomHost,
    create_image_host, IMAGE_HOSTS
)
from telepress.exceptions import UploadError


class TestImgbbHost(unittest.TestCase):
    """Tests for ImgbbHost."""
    
    def test_init_requires_api_key(self):
        """Test that ImgbbHost requires an API key."""
        with self.assertRaises(ValueError) as ctx:
            ImgbbHost(api_key='')
        self.assertIn('API key', str(ctx.exception))
    
    def test_init_success(self):
        """Test successful initialization."""
        host = ImgbbHost(api_key='test_key')
        self.assertEqual(host.name, 'imgbb')
        self.assertEqual(host.api_key, 'test_key')
    
    @patch('telepress.image_host.requests.post')
    def test_upload_success(self, mock_post):
        """Test successful upload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'data': {'url': 'https://i.ibb.co/xxx/image.jpg'}
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = ImgbbHost(api_key='test_key')
            url = host.upload(tmp_path)
            self.assertEqual(url, 'https://i.ibb.co/xxx/image.jpg')
        finally:
            os.unlink(tmp_path)
    
    @patch('telepress.image_host.requests.post')
    def test_upload_failure(self, mock_post):
        """Test upload failure handling."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = 'Bad request'
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = ImgbbHost(api_key='test_key')
            with self.assertRaises(UploadError):
                host.upload(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_upload_file_not_found(self):
        """Test upload with non-existent file."""
        host = ImgbbHost(api_key='test_key')
        with self.assertRaises(FileNotFoundError):
            host.upload('/nonexistent/path.jpg')


class TestImgurHost(unittest.TestCase):
    """Tests for ImgurHost."""
    
    def test_init_requires_client_id(self):
        """Test that ImgurHost requires a client ID."""
        with self.assertRaises(ValueError) as ctx:
            ImgurHost(client_id='')
        self.assertIn('Client ID', str(ctx.exception))
    
    def test_init_success(self):
        """Test successful initialization."""
        host = ImgurHost(client_id='test_client_id')
        self.assertEqual(host.name, 'imgur')
        self.assertEqual(host.client_id, 'test_client_id')
    
    @patch('telepress.image_host.requests.post')
    def test_upload_success(self, mock_post):
        """Test successful upload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'data': {'link': 'https://i.imgur.com/xxx.jpg'}
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = ImgurHost(client_id='test_client_id')
            url = host.upload(tmp_path)
            self.assertEqual(url, 'https://i.imgur.com/xxx.jpg')
        finally:
            os.unlink(tmp_path)


class TestSmmsHost(unittest.TestCase):
    """Tests for SmmsHost."""
    
    def test_init_requires_api_token(self):
        """Test that SmmsHost requires an API token."""
        with self.assertRaises(ValueError) as ctx:
            SmmsHost(api_token='')
        self.assertIn('API token', str(ctx.exception))
    
    def test_init_success(self):
        """Test successful initialization."""
        host = SmmsHost(api_token='test_token')
        self.assertEqual(host.name, 'smms')
        self.assertEqual(host.api_token, 'test_token')
    
    @patch('telepress.image_host.requests.post')
    def test_upload_success(self, mock_post):
        """Test successful upload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'data': {'url': 'https://i.loli.net/xxx.jpg'}
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = SmmsHost(api_token='test_token')
            url = host.upload(tmp_path)
            self.assertEqual(url, 'https://i.loli.net/xxx.jpg')
        finally:
            os.unlink(tmp_path)
    
    @patch('telepress.image_host.requests.post')
    def test_upload_image_repeated(self, mock_post):
        """Test handling of repeated image upload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': False,
            'code': 'image_repeated',
            'images': 'https://existing.url/image.jpg'
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = SmmsHost(api_token='test_token')
            url = host.upload(tmp_path)
            self.assertEqual(url, 'https://existing.url/image.jpg')
        finally:
            os.unlink(tmp_path)


class TestS3Host(unittest.TestCase):
    """Tests for S3Host."""
    
    def test_init_requires_credentials(self):
        """Test that S3Host requires necessary credentials."""
        with self.assertRaises(ValueError) as ctx:
            S3Host(access_key_id='', secret_access_key='', bucket='', public_url='')
        self.assertIn('S3 requires', str(ctx.exception))
    
    def test_init_success(self):
        """Test successful initialization."""
        host = S3Host(
            access_key_id='key123',
            secret_access_key='secret123',
            bucket='my-bucket',
            public_url='https://s3.example.com',
            endpoint_url='https://endpoint'
        )
        self.assertEqual(host.name, 's3')
        self.assertEqual(host.bucket, 'my-bucket')
        self.assertEqual(host.public_url, 'https://s3.example.com')
    
    def test_r2_alias(self):
        """Test R2Host alias."""
        host = R2Host(
            account_id='acc123',
            access_key_id='key123',
            secret_access_key='secret123',
            bucket='my-bucket',
            public_url='https://pub.r2.dev'
        )
        self.assertEqual(host.name, 'r2')
        self.assertEqual(host.endpoint_url, 'https://acc123.r2.cloudflarestorage.com')

    def test_public_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from public_url."""
        host = S3Host(
            access_key_id='key123',
            secret_access_key='secret123',
            bucket='my-bucket',
            public_url='https://s3.example.com/',
            endpoint_url='https://endpoint'
        )
        self.assertEqual(host.public_url, 'https://s3.example.com')
    
    def test_upload_success(self):
        """Test successful upload to S3 (requires boto3)."""
        try:
            import boto3
        except ImportError:
            self.skipTest("boto3 not installed")
        
        # Mock boto3.client
        with patch.object(boto3, 'client') as mock_boto_client:
            mock_client = MagicMock()
            mock_boto_client.return_value = mock_client
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(b'fake image data')
                tmp_path = f.name
            
            try:
                host = S3Host(
                    access_key_id='key123',
                    secret_access_key='secret123',
                    bucket='my-bucket',
                    public_url='https://s3.example.com',
                    endpoint_url='https://endpoint'
                )
                url = host.upload(tmp_path)
                
                self.assertTrue(url.startswith('https://s3.example.com/'))
                self.assertTrue(url.endswith('.jpg'))
                mock_client.upload_fileobj.assert_called_once()
            finally:
                os.unlink(tmp_path)


class TestCustomHost(unittest.TestCase):
    """Tests for CustomHost."""
    
    def test_init_requires_upload_url(self):
        """Test that CustomHost requires upload_url."""
        with self.assertRaises(ValueError) as ctx:
            CustomHost(upload_url='')
        self.assertIn('upload_url', str(ctx.exception))
    
    def test_init_success(self):
        """Test successful initialization."""
        host = CustomHost(
            upload_url='https://api.example.com/upload',
            headers={'Authorization': 'Bearer token'},
            response_url_path='data.url'
        )
        self.assertEqual(host.name, 'custom')
        self.assertEqual(host.upload_url, 'https://api.example.com/upload')
        self.assertEqual(host.response_url_path, 'data.url')
    
    def test_init_defaults(self):
        """Test default values."""
        host = CustomHost(upload_url='https://api.example.com/upload')
        self.assertEqual(host.method, 'POST')
        self.assertEqual(host.file_field, 'file')
        self.assertEqual(host.response_url_path, 'url')
        self.assertEqual(host.headers, {})
        self.assertEqual(host.extra_data, {})
    
    @patch('telepress.image_host.requests.post')
    def test_upload_success_simple_path(self, mock_post):
        """Test upload with simple response URL path."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'url': 'https://example.com/image.jpg'}
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = CustomHost(
                upload_url='https://api.example.com/upload',
                response_url_path='url'
            )
            url = host.upload(tmp_path)
            self.assertEqual(url, 'https://example.com/image.jpg')
        finally:
            os.unlink(tmp_path)
    
    @patch('telepress.image_host.requests.post')
    def test_upload_success_nested_path(self, mock_post):
        """Test upload with nested response URL path."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'data': {
                'url': 'https://example.com/nested/image.jpg'
            }
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = CustomHost(
                upload_url='https://api.example.com/upload',
                response_url_path='data.url'
            )
            url = host.upload(tmp_path)
            self.assertEqual(url, 'https://example.com/nested/image.jpg')
        finally:
            os.unlink(tmp_path)
    
    @patch('telepress.image_host.requests.post')
    def test_upload_success_array_path(self, mock_post):
        """Test upload with array index in response URL path."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'files': [
                {'url': 'https://example.com/first.jpg'},
                {'url': 'https://example.com/second.jpg'}
            ]
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = CustomHost(
                upload_url='https://api.example.com/upload',
                response_url_path='files.0.url'
            )
            url = host.upload(tmp_path)
            self.assertEqual(url, 'https://example.com/first.jpg')
        finally:
            os.unlink(tmp_path)
    
    @patch('telepress.image_host.requests.post')
    def test_upload_invalid_response_path(self, mock_post):
        """Test upload with invalid response path."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'other': 'data'}
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = CustomHost(
                upload_url='https://api.example.com/upload',
                response_url_path='data.url'
            )
            with self.assertRaises(UploadError):
                host.upload(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    @patch('telepress.image_host.requests.post')
    def test_upload_with_headers(self, mock_post):
        """Test that headers are sent with request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'url': 'https://example.com/image.jpg'}
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'fake image data')
            tmp_path = f.name
        
        try:
            host = CustomHost(
                upload_url='https://api.example.com/upload',
                headers={'Authorization': 'Bearer token123', 'X-Custom': 'value'}
            )
            host.upload(tmp_path)
            
            call_kwargs = mock_post.call_args[1]
            self.assertEqual(call_kwargs['headers']['Authorization'], 'Bearer token123')
            self.assertEqual(call_kwargs['headers']['X-Custom'], 'value')
        finally:
            os.unlink(tmp_path)


class TestCreateImageHost(unittest.TestCase):
    """Tests for create_image_host function."""
    
    def test_create_imgbb(self):
        """Test creating imgbb host."""
        host = create_image_host('imgbb', api_key='test_key')
        self.assertIsInstance(host, ImgbbHost)
    
    def test_create_imgur(self):
        """Test creating imgur host."""
        host = create_image_host('imgur', client_id='test_id')
        self.assertIsInstance(host, ImgurHost)
    
    def test_create_smms(self):
        """Test creating smms host."""
        host = create_image_host('smms', api_token='test_token')
        self.assertIsInstance(host, SmmsHost)
    
    def test_create_s3(self):
        """Test creating s3 host."""
        host = create_image_host('s3',
            access_key_id='key',
            secret_access_key='secret',
            bucket='bucket',
            public_url='https://s3.example.com',
            endpoint_url='https://endpoint'
        )
        self.assertIsInstance(host, S3Host)
        self.assertEqual(host.name, 's3')

    def test_create_r2(self):
        """Test creating r2 host."""
        host = create_image_host('r2',
            account_id='acc123',
            access_key_id='key',
            secret_access_key='secret',
            bucket='bucket',
            public_url='https://example.com'
        )
        self.assertIsInstance(host, R2Host)
        self.assertEqual(host.name, 'r2')
    
    def test_create_custom(self):
        """Test creating custom host."""
        host = create_image_host('custom', upload_url='https://api.example.com/upload')
        self.assertIsInstance(host, CustomHost)
    
    def test_create_unknown_host(self):
        """Test creating unknown host raises error."""
        with self.assertRaises(ValueError) as ctx:
            create_image_host('unknown_host')
        self.assertIn('Unknown image host', str(ctx.exception))
        self.assertIn('Available:', str(ctx.exception))
    
    @patch('telepress.config.load_config')
    def test_create_from_config(self, mock_load_config):
        """Test creating host from config when no name specified."""
        mock_load_config.return_value = {
            'image_host': {
                'type': 'imgbb',
                'api_key': 'config_key'
            }
        }
        
        host = create_image_host()
        self.assertIsInstance(host, ImgbbHost)
        self.assertEqual(host.api_key, 'config_key')
    
    @patch('telepress.config.load_config')
    def test_create_from_empty_config_raises(self, mock_load_config):
        """Test that empty config raises error."""
        mock_load_config.return_value = {}
        
        with self.assertRaises(ValueError) as ctx:
            create_image_host()
        self.assertIn('No image host configured', str(ctx.exception))
    
    @patch('telepress.config.load_config')
    def test_create_config_missing_type_raises(self, mock_load_config):
        """Test that config without type raises error."""
        mock_load_config.return_value = {'image_host': {'api_key': 'some_key'}}
        
        with self.assertRaises(ValueError) as ctx:
            create_image_host()
        self.assertIn("missing 'type'", str(ctx.exception))


class TestImageHostsRegistry(unittest.TestCase):
    """Tests for IMAGE_HOSTS registry."""
    
    def test_all_hosts_registered(self):
        """Test that all expected hosts are registered."""
        expected = {'imgbb', 'imgur', 'smms', 'r2', 's3', 'custom'}
        self.assertEqual(set(IMAGE_HOSTS.keys()), expected)
    
    def test_all_hosts_are_image_host_subclass(self):
        """Test that all registered hosts inherit from ImageHost."""
        for name, host_class in IMAGE_HOSTS.items():
            self.assertTrue(
                issubclass(host_class, ImageHost),
                f"{name} should be a subclass of ImageHost"
            )


if __name__ == '__main__':
    unittest.main()
