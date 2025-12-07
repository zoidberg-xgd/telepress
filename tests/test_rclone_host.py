"""
Tests for RcloneHost in image_host module.
"""
import unittest
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock
from telepress.image_host import RcloneHost, UploadError

class TestRcloneHost(unittest.TestCase):
    
    def setUp(self):
        # Mock shutil.which to pretend rclone exists
        self.patcher = patch('shutil.which')
        self.mock_which = self.patcher.start()
        self.mock_which.return_value = '/usr/bin/rclone'

    def tearDown(self):
        self.patcher.stop()

    def test_init_success(self):
        """Test successful initialization."""
        host = RcloneHost(
            remote_path='remote:bucket',
            public_url='https://example.com'
        )
        self.assertEqual(host.name, 'rclone')
        self.assertTrue(host.supports_native_batch)
        self.assertEqual(host.remote_path, 'remote:bucket')
        self.assertEqual(host.public_url, 'https://example.com')

    def test_init_missing_args(self):
        """Test initialization with missing arguments."""
        with self.assertRaises(ValueError):
            RcloneHost(remote_path='', public_url='https://example.com')
        
        with self.assertRaises(ValueError):
            RcloneHost(remote_path='remote:bucket', public_url='')

    def test_init_rclone_not_found(self):
        """Test initialization when rclone is missing."""
        self.mock_which.return_value = None
        with self.assertRaises(ValueError) as ctx:
            RcloneHost(
                remote_path='remote:bucket',
                public_url='https://example.com'
            )
        self.assertIn('rclone executable not found', str(ctx.exception))

    @patch('subprocess.run')
    def test_upload_batch_success(self, mock_run):
        """Test successful batch upload."""
        host = RcloneHost(
            remote_path='remote:bucket',
            public_url='https://example.com'
        )
        
        # Create temp files
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f1, \
             tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f2:
            f1.close()
            f2.close()
            
            try:
                paths = [f1.name, f2.name]
                results = host.upload_batch(paths)
                
                # Verify subprocess.run was called
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                self.assertEqual(args[0], 'rclone')
                self.assertEqual(args[1], 'copy')
                self.assertEqual(args[3], 'remote:bucket')
                
                # Verify results
                self.assertEqual(len(results), 2)
                
                name1 = os.path.basename(f1.name)
                name2 = os.path.basename(f2.name)
                
                self.assertEqual(results[f1.name], f'https://example.com/{name1}')
                self.assertEqual(results[f2.name], f'https://example.com/{name2}')
                
            finally:
                if os.path.exists(f1.name): os.unlink(f1.name)
                if os.path.exists(f2.name): os.unlink(f2.name)

    @patch('subprocess.run')
    def test_upload_batch_failure(self, mock_run):
        """Test batch upload failure."""
        host = RcloneHost(
            remote_path='remote:bucket',
            public_url='https://example.com'
        )
        
        # Mock subprocess failure
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, ['rclone'], stderr="Rclone error")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.close()
            try:
                results = host.upload_batch([f.name])
                
                # Should return exception in results
                self.assertIsInstance(results[f.name], Exception)
                self.assertIn("Rclone error", str(results[f.name]))
            finally:
                os.unlink(f.name)

    def test_upload_single_delegates_to_batch(self):
        """Test single upload delegates to upload_batch."""
        host = RcloneHost(
            remote_path='remote:bucket',
            public_url='https://example.com'
        )
        
        with patch.object(host, 'upload_batch') as mock_batch:
            mock_batch.return_value = {'/path/image.jpg': 'https://example.com/image.jpg'}
            
            url = host.upload('/path/image.jpg')
            
            self.assertEqual(url, 'https://example.com/image.jpg')
            mock_batch.assert_called_once_with(['/path/image.jpg'])

if __name__ == '__main__':
    unittest.main()
