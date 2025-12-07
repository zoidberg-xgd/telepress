"""
Tests for uploader module with external image host support.
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import tempfile
from telepress.uploader import ImageUploader, UploadResult, BatchUploadResult
from telepress.image_host import ImageHost, ImgbbHost
from telepress.exceptions import UploadError


class MockImageHost(ImageHost):
    """Mock image host for testing."""
    
    def __init__(self, return_url='https://example.com/image.jpg', fail=False):
        self.return_url = return_url
        self.fail = fail
        self.upload_count = 0
    
    @property
    def name(self):
        return 'mock'
    
    def upload(self, image_path):
        self.upload_count += 1
        if self.fail:
            raise UploadError("Mock upload failed")
        return self.return_url


class TestImageUploaderInit(unittest.TestCase):
    """Tests for ImageUploader initialization."""
    
    def test_init_with_host_instance(self):
        """Test initialization with ImageHost instance."""
        mock_host = MockImageHost()
        uploader = ImageUploader(host=mock_host)
        self.assertEqual(uploader.host, mock_host)
    
    def test_init_with_host_name(self):
        """Test initialization with host name."""
        uploader = ImageUploader('imgbb', api_key='test_key')
        self.assertIsInstance(uploader.host, ImgbbHost)
    
    @patch('telepress.uploader.create_image_host')
    def test_init_from_config(self, mock_create):
        """Test initialization from config when no host specified."""
        mock_host = MockImageHost()
        mock_create.return_value = mock_host
        
        uploader = ImageUploader()
        mock_create.assert_called_once_with(None)
    
    def test_init_custom_max_workers(self):
        """Test setting custom max_workers."""
        mock_host = MockImageHost()
        uploader = ImageUploader(host=mock_host, max_workers=8)
        self.assertEqual(uploader.max_workers, 8)


class TestImageUploaderUpload(unittest.TestCase):
    """Tests for ImageUploader.upload method."""
    
    def setUp(self):
        self.mock_host = MockImageHost()
        self.uploader = ImageUploader(host=self.mock_host)
    
    @patch('telepress.uploader.compress_image_to_size')
    def test_upload_success(self, mock_compress):
        """Test successful image upload."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'test image data')
            tmp_path = f.name
        
        try:
            mock_compress.return_value = (tmp_path, False)
            url = self.uploader.upload(tmp_path)
            self.assertEqual(url, 'https://example.com/image.jpg')
        finally:
            os.unlink(tmp_path)
    
    def test_upload_file_not_found(self):
        """Test that non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.uploader.upload('/nonexistent/path.jpg')
    
    @patch('telepress.uploader.compress_image_to_size')
    @patch('time.sleep')
    def test_upload_retry_success(self, mock_sleep, mock_compress):
        """Test that upload retries on failure and succeeds."""
        # Host fails first time, succeeds second time
        call_count = [0]
        def side_effect(path):
            call_count[0] += 1
            if call_count[0] == 1:
                raise UploadError("First attempt failed")
            return 'https://example.com/success.jpg'
        
        self.mock_host.upload = side_effect
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'test')
            tmp_path = f.name
        
        try:
            mock_compress.return_value = (tmp_path, False)
            url = self.uploader.upload(tmp_path, retries=3)
            self.assertEqual(url, 'https://example.com/success.jpg')
            self.assertEqual(call_count[0], 2)
        finally:
            os.unlink(tmp_path)
    
    @patch('telepress.uploader.compress_image_to_size')
    @patch('time.sleep')
    def test_upload_retry_failure(self, mock_sleep, mock_compress):
        """Test that upload fails after exhausting retries."""
        self.mock_host = MockImageHost(fail=True)
        self.uploader = ImageUploader(host=self.mock_host)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'test')
            tmp_path = f.name
        
        try:
            mock_compress.return_value = (tmp_path, False)
            with self.assertRaises(UploadError) as ctx:
                self.uploader.upload(tmp_path, retries=2)
            self.assertIn('after 2 attempts', str(ctx.exception))
        finally:
            os.unlink(tmp_path)
    
    @patch('telepress.uploader.compress_image_to_size')
    def test_upload_with_compression(self, mock_compress):
        """Test that compression is applied when auto_compress=True."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'original')
            tmp_path = f.name
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'compressed')
            compressed_path = f.name
        
        try:
            mock_compress.return_value = (compressed_path, True)
            self.uploader.upload(tmp_path, auto_compress=True)
            mock_compress.assert_called_once()
        finally:
            os.unlink(tmp_path)
            if os.path.exists(compressed_path):
                os.unlink(compressed_path)
    
    @patch('telepress.uploader.compress_image_to_size')
    def test_upload_cleans_up_compressed_file(self, mock_compress):
        """Test that compressed temp file is cleaned up."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'original')
            tmp_path = f.name
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'compressed')
            compressed_path = f.name
        
        try:
            mock_compress.return_value = (compressed_path, True)
            self.uploader.upload(tmp_path)
            # Compressed file should be cleaned up
            self.assertFalse(os.path.exists(compressed_path))
        finally:
            os.unlink(tmp_path)
            if os.path.exists(compressed_path):
                os.unlink(compressed_path)
    
    @patch('telepress.uploader.compress_image_to_size')
    @patch('time.sleep')
    def test_retry_exponential_backoff(self, mock_sleep, mock_compress):
        """Test that retry uses exponential backoff."""
        self.mock_host = MockImageHost(fail=True)
        self.uploader = ImageUploader(host=self.mock_host)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'test')
            tmp_path = f.name
        
        try:
            mock_compress.return_value = (tmp_path, False)
            try:
                self.uploader.upload(tmp_path, retries=3, retry_delay=1.0)
            except UploadError:
                pass
            # Should sleep after 1st and 2nd failure
            self.assertEqual(mock_sleep.call_count, 2)
        finally:
            os.unlink(tmp_path)


class TestImageUploaderUploadSafe(unittest.TestCase):
    """Tests for ImageUploader.upload_safe method."""
    
    def setUp(self):
        self.mock_host = MockImageHost()
        self.uploader = ImageUploader(host=self.mock_host)
    
    @patch('telepress.uploader.compress_image_to_size')
    def test_upload_safe_success(self, mock_compress):
        """Test upload_safe returns UploadResult on success."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'test')
            tmp_path = f.name
        
        try:
            mock_compress.return_value = (tmp_path, False)
            result = self.uploader.upload_safe(tmp_path)
            self.assertTrue(result.success)
            self.assertEqual(result.url, 'https://example.com/image.jpg')
            self.assertIsNone(result.error)
        finally:
            os.unlink(tmp_path)
    
    @patch('telepress.uploader.compress_image_to_size')
    def test_upload_safe_failure(self, mock_compress):
        """Test upload_safe returns UploadResult with error on failure."""
        self.mock_host = MockImageHost(fail=True)
        self.uploader = ImageUploader(host=self.mock_host)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b'test')
            tmp_path = f.name
        
        try:
            mock_compress.return_value = (tmp_path, False)
            result = self.uploader.upload_safe(tmp_path, retries=1)
            self.assertFalse(result.success)
            self.assertIsNone(result.url)
            self.assertIsNotNone(result.error)
        finally:
            os.unlink(tmp_path)


class TestUploadResult(unittest.TestCase):
    """Tests for UploadResult dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        result = UploadResult(path='/test.jpg')
        self.assertEqual(result.path, '/test.jpg')
        self.assertIsNone(result.url)
        self.assertIsNone(result.error)
        self.assertFalse(result.success)
        self.assertFalse(result.compressed)
        self.assertEqual(result.attempts, 0)


class TestBatchUploadResult(unittest.TestCase):
    """Tests for BatchUploadResult dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        result = BatchUploadResult()
        self.assertEqual(result.total, 0)
        self.assertEqual(result.successful, 0)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.results, [])
    
    def test_success_rate_empty(self):
        """Test success_rate with no uploads."""
        result = BatchUploadResult()
        self.assertEqual(result.success_rate, 0.0)
    
    def test_success_rate_all_success(self):
        """Test success_rate with all successful."""
        result = BatchUploadResult(total=5, successful=5, failed=0)
        self.assertEqual(result.success_rate, 1.0)
    
    def test_success_rate_partial(self):
        """Test success_rate with partial success."""
        result = BatchUploadResult(total=4, successful=1, failed=3)
        self.assertEqual(result.success_rate, 0.25)
    
    def test_get_failed_paths(self):
        """Test get_failed_paths method."""
        result = BatchUploadResult(
            results=[
                UploadResult(path='/a.jpg', success=True),
                UploadResult(path='/b.jpg', success=False),
                UploadResult(path='/c.jpg', success=False)
            ]
        )
        failed = result.get_failed_paths()
        self.assertEqual(failed, ['/b.jpg', '/c.jpg'])
    
    def test_get_url_map(self):
        """Test get_url_map method."""
        result = BatchUploadResult(
            results=[
                UploadResult(path='/a.jpg', url='https://a', success=True),
                UploadResult(path='/b.jpg', success=False),
                UploadResult(path='/c.jpg', url='https://c', success=True)
            ]
        )
        url_map = result.get_url_map()
        self.assertEqual(url_map, {'/a.jpg': 'https://a', '/c.jpg': 'https://c'})


class TestBatchUpload(unittest.TestCase):
    """Tests for ImageUploader.upload_batch method."""
    
    def setUp(self):
        self.mock_host = MockImageHost()
        self.uploader = ImageUploader(host=self.mock_host, max_workers=2)
    
    def test_empty_paths_list(self):
        """Test batch upload with empty list."""
        result = self.uploader.upload_batch([])
        self.assertEqual(result.total, 0)
        self.assertEqual(result.successful, 0)
    
    @patch('telepress.uploader.compress_image_to_size')
    def test_batch_upload_success(self, mock_compress):
        """Test successful batch upload."""
        paths = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(b'test')
                paths.append(f.name)
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            result = self.uploader.upload_batch(paths)
            self.assertEqual(result.total, 3)
            self.assertEqual(result.successful, 3)
            self.assertEqual(result.failed, 0)
        finally:
            for p in paths:
                os.unlink(p)
    
    @patch('telepress.uploader.compress_image_to_size')
    def test_batch_upload_partial_failure(self, mock_compress):
        """Test batch upload with some failures."""
        paths = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(b'test')
                paths.append(f.name)
        
        call_count = [0]
        def side_effect(path):
            call_count[0] += 1
            if call_count[0] == 2:
                raise UploadError("Failed")
            return 'https://example.com/image.jpg'
        
        self.mock_host.upload = side_effect
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            result = self.uploader.upload_batch(paths, retries=1)
            self.assertEqual(result.total, 3)
            self.assertEqual(result.failed, 1)
            self.assertEqual(result.successful, 2)
        finally:
            for p in paths:
                os.unlink(p)
    
    @patch('telepress.uploader.compress_image_to_size')
    def test_batch_progress_callback(self, mock_compress):
        """Test progress callback is called."""
        paths = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                f.write(b'test')
                paths.append(f.name)
        
        progress_calls = []
        def callback(done, total, result):
            progress_calls.append((done, total, result.success))
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            self.uploader.upload_batch(paths, progress_callback=callback)
            self.assertEqual(len(progress_calls), 2)
        finally:
            for p in paths:
                os.unlink(p)
    
    def test_nonexistent_files_in_batch(self):
        """Test batch with non-existent files."""
        paths = ['/nonexistent/1.jpg', '/nonexistent/2.jpg']
        result = self.uploader.upload_batch(paths, retries=1)
        self.assertEqual(result.total, 2)
        self.assertEqual(result.failed, 2)


class TestRetryFailed(unittest.TestCase):
    """Tests for ImageUploader.retry_failed method."""
    
    def setUp(self):
        self.mock_host = MockImageHost()
        self.uploader = ImageUploader(host=self.mock_host)
    
    def test_retry_with_no_failures(self):
        """Test retry_failed with no failures."""
        batch_result = BatchUploadResult(
            total=2, successful=2, failed=0,
            results=[
                UploadResult(path='/a.jpg', success=True),
                UploadResult(path='/b.jpg', success=True)
            ]
        )
        retry_result = self.uploader.retry_failed(batch_result)
        self.assertEqual(retry_result.total, 0)


if __name__ == '__main__':
    unittest.main()
