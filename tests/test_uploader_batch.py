"""
Tests for ImageUploader batch functionality.
"""
import unittest
import os
import tempfile
from unittest.mock import patch, MagicMock
from telepress.uploader import ImageUploader, BatchUploadResult, UploadResult
from telepress.image_host import ImageHost, RcloneHost

class MockNativeBatchHost(ImageHost):
    def __init__(self):
        pass

    @property
    def name(self):
        return "mock_native"
        
    @property
    def supports_native_batch(self):
        return True
        
    def upload(self, path):
        return f"http://mock/{os.path.basename(path)}"
        
    def upload_batch(self, paths):
        results = {}
        for path in paths:
            results[path] = f"http://mock/{os.path.basename(path)}"
        return results

class TestUploaderBatch(unittest.TestCase):
    
    def test_upload_batch_native(self):
        """Test upload_batch using native host support."""
        host = MockNativeBatchHost()
        uploader = ImageUploader(host=host)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f1, \
             tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f2:
            f1.close()
            f2.close()
            
            try:
                paths = [f1.name, f2.name]
                
                # Mock compression to avoid actual processing
                with patch('telepress.uploader.compress_image_to_size') as mock_compress:
                    # Return original path, false (no compression)
                    mock_compress.side_effect = lambda p, s: (p, False)
                    
                    result = uploader.upload_batch(paths)
                    
                    self.assertIsInstance(result, BatchUploadResult)
                    self.assertEqual(result.total, 2)
                    self.assertEqual(result.successful, 2)
                    self.assertEqual(result.failed, 0)
                    
                    url_map = result.get_url_map()
                    self.assertIn(f1.name, url_map)
                    self.assertIn(f2.name, url_map)
                    
            finally:
                if os.path.exists(f1.name): os.unlink(f1.name)
                if os.path.exists(f2.name): os.unlink(f2.name)

    def test_upload_batch_native_with_compression(self):
        """Test native batch upload with compression."""
        host = MockNativeBatchHost()
        uploader = ImageUploader(host=host)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f1:
            f1.close()
            
            try:
                # Mock compression to return a different path
                with patch('telepress.uploader.compress_image_to_size') as mock_compress:
                    compressed_path = f1.name + "_compressed"
                    # Create dummy compressed file
                    with open(compressed_path, 'w') as f:
                        f.write('compressed')
                        
                    mock_compress.return_value = (compressed_path, True)
                    
                    # Mock host.upload_batch to verify it receives compressed path
                    with patch.object(host, 'upload_batch') as mock_host_batch:
                        mock_host_batch.return_value = {compressed_path: "http://mock/url"}
                        
                        result = uploader.upload_batch([f1.name])
                        
                        self.assertEqual(result.successful, 1)
                        # Verify host received compressed path
                        mock_host_batch.assert_called_with([compressed_path])
                        
                        # Verify result maps ORIGINAL path to URL
                        url_map = result.get_url_map()
                        self.assertIn(f1.name, url_map)
                        self.assertEqual(url_map[f1.name], "http://mock/url")

                        # Verify compressed file was cleaned up is handled by _upload_batch_native
                        # But since we mocked compress, we need to check if uploader cleaned it up?
                        # The uploader should cleanup temp files in finally block.
                        # We can check if file exists. If uploader cleaned it, it should be gone.
                        self.assertFalse(os.path.exists(compressed_path))
                        
            finally:
                if os.path.exists(f1.name): os.unlink(f1.name)
                if os.path.exists(f1.name + "_compressed"): os.unlink(f1.name + "_compressed")

if __name__ == '__main__':
    unittest.main()
