import unittest
from unittest.mock import patch, MagicMock
from telepress.core import TelegraphPublisher
from telepress.utils import MAX_IMAGE_SIZE

class TestImageOptions(unittest.TestCase):
    def setUp(self):
        # Mock TelegraphAuth to avoid network calls
        self.auth_patcher = patch('telepress.core.TelegraphAuth')
        self.MockAuth = self.auth_patcher.start()
        self.mock_client = MagicMock()
        self.MockAuth.return_value.get_client.return_value = self.mock_client

        # Mock ImageUploader to avoid real initialization and network calls
        self.uploader_patcher = patch('telepress.core.ImageUploader')
        self.MockUploader = self.uploader_patcher.start()
        self.mock_uploader_instance = MagicMock()
        self.MockUploader.return_value = self.mock_uploader_instance
        self.mock_uploader_instance.upload.return_value = 'http://example.com/image.jpg'

        # Mock config loading
        self.config_patcher = patch('telepress.core.load_config')
        self.mock_load_config = self.config_patcher.start()
        self.mock_load_config.return_value = {}

    def tearDown(self):
        self.auth_patcher.stop()
        self.uploader_patcher.stop()
        self.config_patcher.stop()

    def test_init_defaults(self):
        """Test default values for image options."""
        publisher = TelegraphPublisher(token="fake")
        self.assertEqual(publisher.max_image_size, MAX_IMAGE_SIZE)
        self.assertTrue(publisher.auto_compress)

    def test_init_custom_size_limit(self):
        """Test initializing with custom image size limit."""
        # 10 MB
        publisher = TelegraphPublisher(token="fake", image_size_limit=10.0)
        self.assertEqual(publisher.max_image_size, 10 * 1024 * 1024)

    def test_init_disable_compression(self):
        """Test initializing with auto_compress=False."""
        publisher = TelegraphPublisher(token="fake", auto_compress=False)
        self.assertFalse(publisher.auto_compress)

    def test_init_from_config(self):
        """Test initializing max_image_size from config file."""
        self.mock_load_config.return_value = {
            'image_host': {'max_size_mb': 2.5}
        }
        publisher = TelegraphPublisher(token="fake")
        self.assertEqual(publisher.max_image_size, int(2.5 * 1024 * 1024))

    def test_publish_image_passes_options(self):
        """Test that publish_image passes correct options to uploader."""
        publisher = TelegraphPublisher(
            token="fake",
            image_size_limit=8.0,
            auto_compress=False
        )
        
        with patch('os.path.exists', return_value=True):
            publisher.publish_image('/path/to/image.jpg', 'Title')
            
        self.mock_uploader_instance.upload.assert_called_with(
            '/path/to/image.jpg',
            auto_compress=False,
            max_size=8 * 1024 * 1024
        )

    def test_publish_zip_gallery_passes_options(self):
        """Test that publish_zip_gallery passes correct options to uploader."""
        publisher = TelegraphPublisher(
            token="fake",
            image_size_limit=1.0,
            auto_compress=True
        )

        with patch('telepress.core.safe_extract_zip'), \
             patch('os.walk', return_value=[('/tmp', [], ['img1.jpg', 'img2.png'])]), \
             patch('os.path.splitext', side_effect=lambda x: (x[:-4], x[-4:])), \
             patch('tempfile.TemporaryDirectory'):
            
            # Need to mock os.path.exists because verify checks it, but we are mocking os.walk
            # Actually core.py doesn't check existence for zip contents in this loop, 
            # but it does verify zip_path exists in publish method if called from there.
            # Here we call publish_zip_gallery directly.
            
            # We need to mock open/read for uploader? No, uploader is mocked.
            
            publisher.publish_zip_gallery('/path/to/gallery.zip', 'Title')
            
        # Check that upload was called with correct args for each image
        self.mock_uploader_instance.upload.assert_any_call(
            '/tmp/img1.jpg',
            auto_compress=True,
            max_size=1 * 1024 * 1024
        )
        self.mock_uploader_instance.upload.assert_any_call(
            '/tmp/img2.png',
            auto_compress=True,
            max_size=1 * 1024 * 1024
        )

if __name__ == '__main__':
    unittest.main()
