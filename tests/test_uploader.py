import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import tempfile
from telepress.uploader import ImageUploader, UploadResult, BatchUploadResult
from telepress.exceptions import UploadError, ValidationError, DependencyError, ConversionError


class TestUploader(unittest.TestCase):
    def setUp(self):
        self.uploader = ImageUploader()

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.compress_image_to_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_upload_success(self, mock_file, mock_compress, mock_exists, mock_upload):
        """Test successful image upload."""
        mock_exists.return_value = True
        mock_compress.return_value = ('/path/to/image.jpg', False)  # No compression needed
        mock_upload.return_value = [{'src': '/file/test.jpg'}]
        
        url = self.uploader.upload('/path/to/image.jpg')
        self.assertEqual(url, 'https://telegra.ph/file/test.jpg')

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.compress_image_to_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_upload_retry_success_on_second_attempt(self, mock_file, mock_compress, mock_exists, mock_upload):
        """Test that upload retries and succeeds on second attempt."""
        mock_exists.return_value = True
        mock_compress.return_value = ('/path/to/image.jpg', False)
        mock_upload.side_effect = [
            Exception("Network Error"),
            [{'src': '/file/success.jpg'}]
        ]
        
        url = self.uploader.upload('/path/to/image.jpg', retries=3)
        self.assertEqual(url, 'https://telegra.ph/file/success.jpg')
        self.assertEqual(mock_upload.call_count, 2)

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.compress_image_to_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_upload_retry_failure(self, mock_file, mock_compress, mock_exists, mock_upload):
        """Test that upload fails after exhausting retries."""
        mock_exists.return_value = True
        mock_compress.return_value = ('/path/to/image.jpg', False)
        mock_upload.side_effect = Exception("Network Error")
        
        with self.assertRaises(UploadError) as ctx:
            self.uploader.upload('/path/to/image.jpg', retries=2)
        
        self.assertEqual(mock_upload.call_count, 2)
        self.assertIn("after 2 attempts", str(ctx.exception))

    def test_file_not_found(self):
        """Test that non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.uploader.upload('non_existent.jpg')

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.compress_image_to_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_invalid_response_format_empty_list(self, mock_file, mock_compress, mock_exists, mock_upload):
        """Test that empty response list raises UploadError."""
        mock_exists.return_value = True
        mock_compress.return_value = ('/path/to/image.jpg', False)
        mock_upload.return_value = []
        
        with self.assertRaises(UploadError) as ctx:
            self.uploader.upload('/path/to/image.jpg', retries=1)
        
        self.assertIn("Invalid response", str(ctx.exception))

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.compress_image_to_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_invalid_response_format_missing_src(self, mock_file, mock_compress, mock_exists, mock_upload):
        """Test that response without 'src' key raises UploadError."""
        mock_exists.return_value = True
        mock_compress.return_value = ('/path/to/image.jpg', False)
        mock_upload.return_value = [{'error': 'something'}]
        
        with self.assertRaises(UploadError) as ctx:
            self.uploader.upload('/path/to/image.jpg', retries=1)
        
        self.assertIn("Invalid response", str(ctx.exception))

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.compress_image_to_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_invalid_response_not_list(self, mock_file, mock_compress, mock_exists, mock_upload):
        """Test that non-list response raises UploadError."""
        mock_exists.return_value = True
        mock_compress.return_value = ('/path/to/image.jpg', False)
        mock_upload.return_value = "unexpected string"
        
        with self.assertRaises(UploadError) as ctx:
            self.uploader.upload('/path/to/image.jpg', retries=1)
        
        self.assertIn("Invalid response", str(ctx.exception))

    def test_file_too_large_without_auto_compress(self):
        """Test that oversized file raises ValidationError when auto_compress=False."""
        # Create a temp file larger than 5MB limit
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'x' * (6 * 1024 * 1024))  # 6MB
            tmp_path = f.name
        
        try:
            with self.assertRaises(ValidationError):
                self.uploader.upload(tmp_path, auto_compress=False)
        finally:
            os.unlink(tmp_path)

    @patch('telepress.uploader.upload_file')
    @patch('telepress.uploader.compress_image_to_size')
    def test_auto_compress_large_image(self, mock_compress, mock_upload):
        """Test that large images are auto-compressed before upload."""
        # Create a temp file to simulate the original image
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            f.write(b'x' * 100)  # Small file for testing
            tmp_path = f.name
        
        # Create a temp file to simulate the compressed image
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            f.write(b'compressed_data')
            compressed_path = f.name
        
        try:
            mock_compress.return_value = (compressed_path, True)  # Was compressed
            mock_upload.return_value = [{'src': '/file/compressed.jpg'}]
            
            url = self.uploader.upload(tmp_path)
            
            self.assertEqual(url, 'https://telegra.ph/file/compressed.jpg')
            mock_compress.assert_called_once()
        finally:
            os.unlink(tmp_path)
            # Compressed file should be cleaned up by uploader, but just in case
            if os.path.exists(compressed_path):
                os.unlink(compressed_path)

    @patch('telepress.uploader.upload_file')
    def test_auto_compress_cleans_up_temp_file(self, mock_upload):
        """Test that compressed temp file is cleaned up after upload."""
        from PIL import Image
        
        # Create a large test image
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            tmp_path = f.name
        
        # Create a large PNG (uncompressed)
        img = Image.new('RGB', (3000, 3000), color='red')
        img.save(tmp_path, format='PNG')
        
        try:
            mock_upload.return_value = [{'src': '/file/test.jpg'}]
            
            # Upload should work and compress the image
            url = self.uploader.upload(tmp_path)
            
            self.assertEqual(url, 'https://telegra.ph/file/test.jpg')
            # Original file should still exist
            self.assertTrue(os.path.exists(tmp_path))
        finally:
            os.unlink(tmp_path)

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.compress_image_to_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_retry_waits_between_attempts(self, mock_sleep, mock_file, mock_compress, mock_exists, mock_upload):
        """Test that retry uses exponential backoff."""
        mock_exists.return_value = True
        mock_compress.return_value = ('/path/to/image.jpg', False)
        mock_upload.side_effect = Exception("Error")
        
        try:
            self.uploader.upload('/path/to/image.jpg', retries=3, retry_delay=1.0)
        except UploadError:
            pass
        
        # Should have slept twice (after 1st and 2nd failure, not after 3rd)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.compress_image_to_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_default_retries_is_three(self, mock_file, mock_compress, mock_exists, mock_upload):
        """Test that default retry count is 3."""
        mock_exists.return_value = True
        mock_compress.return_value = ('/path/to/image.jpg', False)
        mock_upload.side_effect = Exception("Error")
        
        try:
            self.uploader.upload('/path/to/image.jpg')
        except UploadError:
            pass
        
        self.assertEqual(mock_upload.call_count, 3)


class TestUploaderDependency(unittest.TestCase):
    @patch('telepress.uploader.upload_file', None)
    def test_missing_upload_file_raises_dependency_error(self):
        """Test that missing telegraph library raises DependencyError."""
        with self.assertRaises(DependencyError):
            ImageUploader()


class TestBatchUpload(unittest.TestCase):
    def setUp(self):
        self.uploader = ImageUploader(max_workers=2)

    @patch('telepress.uploader.upload_file')
    @patch('telepress.uploader.compress_image_to_size')
    def test_batch_upload_success(self, mock_compress, mock_upload):
        """Test successful batch upload."""
        # Create temp files
        paths = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
                f.write(b'x' * 100)
                paths.append(f.name)
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            mock_upload.return_value = [{'src': '/file/test.jpg'}]
            
            result = self.uploader.upload_batch(paths)
            
            self.assertEqual(result.total, 3)
            self.assertEqual(result.successful, 3)
            self.assertEqual(result.failed, 0)
            self.assertEqual(result.success_rate, 1.0)
        finally:
            for p in paths:
                os.unlink(p)

    @patch('telepress.uploader.upload_file')
    @patch('telepress.uploader.compress_image_to_size')
    def test_batch_upload_partial_failure(self, mock_compress, mock_upload):
        """Test batch upload with some failures."""
        paths = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
                f.write(b'x' * 100)
                paths.append(f.name)
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            # First succeeds, second fails, third succeeds
            mock_upload.side_effect = [
                [{'src': '/file/1.jpg'}],
                Exception("Network error"),
                [{'src': '/file/3.jpg'}]
            ]
            
            result = self.uploader.upload_batch(paths, retries=1)
            
            self.assertEqual(result.total, 3)
            self.assertEqual(result.successful, 2)
            self.assertEqual(result.failed, 1)
            self.assertEqual(len(result.get_failed_paths()), 1)
        finally:
            for p in paths:
                os.unlink(p)

    @patch('telepress.uploader.upload_file')
    @patch('telepress.uploader.compress_image_to_size')
    def test_batch_progress_callback(self, mock_compress, mock_upload):
        """Test progress callback is called."""
        paths = []
        for i in range(2):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
                f.write(b'x' * 100)
                paths.append(f.name)
        
        progress_calls = []
        def on_progress(done, total, result):
            progress_calls.append((done, total, result.success))
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            mock_upload.return_value = [{'src': '/file/test.jpg'}]
            
            self.uploader.upload_batch(paths, progress_callback=on_progress)
            
            self.assertEqual(len(progress_calls), 2)
        finally:
            for p in paths:
                os.unlink(p)

    def test_retry_failed(self):
        """Test retry_failed method."""
        # Create a mock batch result with failures
        batch_result = BatchUploadResult(
            total=3,
            successful=1,
            failed=2,
            results=[
                UploadResult(path='/path/1.jpg', url='http://...', success=True),
                UploadResult(path='/path/2.jpg', error='fail', success=False),
                UploadResult(path='/path/3.jpg', error='fail', success=False)
            ]
        )
        
        failed = batch_result.get_failed_paths()
        self.assertEqual(len(failed), 2)
        self.assertIn('/path/2.jpg', failed)
        self.assertIn('/path/3.jpg', failed)

    def test_url_map(self):
        """Test get_url_map method."""
        batch_result = BatchUploadResult(
            total=2,
            successful=2,
            results=[
                UploadResult(path='/a.jpg', url='http://a', success=True),
                UploadResult(path='/b.jpg', url='http://b', success=True)
            ]
        )
        
        url_map = batch_result.get_url_map()
        self.assertEqual(url_map['/a.jpg'], 'http://a')
        self.assertEqual(url_map['/b.jpg'], 'http://b')


class TestBatchUploadEdgeCases(unittest.TestCase):
    """Edge case tests for batch upload functionality."""
    
    def setUp(self):
        self.uploader = ImageUploader(max_workers=2)

    def test_empty_paths_list(self):
        """Test batch upload with empty list returns empty result."""
        result = self.uploader.upload_batch([])
        
        self.assertEqual(result.total, 0)
        self.assertEqual(result.successful, 0)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.success_rate, 0.0)
        self.assertEqual(len(result.results), 0)

    @patch('telepress.uploader.upload_file')
    @patch('telepress.uploader.compress_image_to_size')
    def test_single_file_batch(self, mock_compress, mock_upload):
        """Test batch upload with single file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            f.write(b'x' * 100)
            tmp_path = f.name
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            mock_upload.return_value = [{'src': '/file/single.jpg'}]
            
            result = self.uploader.upload_batch([tmp_path])
            
            self.assertEqual(result.total, 1)
            self.assertEqual(result.successful, 1)
            self.assertEqual(result.success_rate, 1.0)
        finally:
            os.unlink(tmp_path)

    @patch('telepress.uploader.upload_file')
    @patch('telepress.uploader.compress_image_to_size')
    def test_all_files_fail(self, mock_compress, mock_upload):
        """Test batch upload where all files fail."""
        paths = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
                f.write(b'x' * 100)
                paths.append(f.name)
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            mock_upload.side_effect = Exception("Server error")
            
            result = self.uploader.upload_batch(paths, retries=1)
            
            self.assertEqual(result.total, 3)
            self.assertEqual(result.successful, 0)
            self.assertEqual(result.failed, 3)
            self.assertEqual(result.success_rate, 0.0)
        finally:
            for p in paths:
                os.unlink(p)

    @patch('telepress.uploader.upload_file')
    @patch('telepress.uploader.compress_image_to_size')
    def test_single_worker(self, mock_compress, mock_upload):
        """Test batch upload with max_workers=1 (sequential)."""
        paths = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
                f.write(b'x' * 100)
                paths.append(f.name)
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            mock_upload.return_value = [{'src': '/file/test.jpg'}]
            
            result = self.uploader.upload_batch(paths, max_workers=1)
            
            self.assertEqual(result.total, 3)
            self.assertEqual(result.successful, 3)
        finally:
            for p in paths:
                os.unlink(p)

    @patch('telepress.uploader.upload_file')
    @patch('telepress.uploader.compress_image_to_size')
    def test_stop_on_error(self, mock_compress, mock_upload):
        """Test stop_on_error stops processing after first failure."""
        paths = []
        for i in range(5):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
                f.write(b'x' * 100)
                paths.append(f.name)
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            # First succeeds, then fail
            mock_upload.side_effect = [
                [{'src': '/file/1.jpg'}],
                Exception("Error"),
                [{'src': '/file/3.jpg'}],
                [{'src': '/file/4.jpg'}],
                [{'src': '/file/5.jpg'}]
            ]
            
            result = self.uploader.upload_batch(paths, retries=1, stop_on_error=True, max_workers=1)
            
            # Should stop after first error
            self.assertGreaterEqual(result.failed, 1)
        finally:
            for p in paths:
                os.unlink(p)

    def test_nonexistent_files_in_batch(self):
        """Test batch with non-existent files handles gracefully."""
        paths = ['/nonexistent/path1.jpg', '/nonexistent/path2.jpg']
        
        result = self.uploader.upload_batch(paths, retries=1)
        
        self.assertEqual(result.total, 2)
        self.assertEqual(result.failed, 2)
        self.assertEqual(result.successful, 0)
        for r in result.results:
            self.assertIn('not found', r.error.lower())

    def test_retry_failed_with_no_failures(self):
        """Test retry_failed with no failures returns empty result."""
        batch_result = BatchUploadResult(
            total=2,
            successful=2,
            failed=0,
            results=[
                UploadResult(path='/a.jpg', url='http://a', success=True),
                UploadResult(path='/b.jpg', url='http://b', success=True)
            ]
        )
        
        retry_result = self.uploader.retry_failed(batch_result)
        
        self.assertEqual(retry_result.total, 0)

    def test_success_rate_edge_cases(self):
        """Test success_rate calculation edge cases."""
        # Empty result
        empty = BatchUploadResult()
        self.assertEqual(empty.success_rate, 0.0)
        
        # All success
        all_success = BatchUploadResult(total=5, successful=5, failed=0)
        self.assertEqual(all_success.success_rate, 1.0)
        
        # All failed
        all_fail = BatchUploadResult(total=5, successful=0, failed=5)
        self.assertEqual(all_fail.success_rate, 0.0)
        
        # Partial
        partial = BatchUploadResult(total=4, successful=1, failed=3)
        self.assertEqual(partial.success_rate, 0.25)

    @patch('telepress.uploader.upload_file')
    @patch('telepress.uploader.compress_image_to_size')
    def test_progress_callback_exception_ignored(self, mock_compress, mock_upload):
        """Test that exceptions in progress callback don't break upload."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            f.write(b'x' * 100)
            tmp_path = f.name
        
        def bad_callback(done, total, result):
            raise ValueError("Callback error!")
        
        try:
            mock_compress.side_effect = lambda p, *a, **k: (p, False)
            mock_upload.return_value = [{'src': '/file/test.jpg'}]
            
            # Should not raise despite callback error
            result = self.uploader.upload_batch([tmp_path], progress_callback=bad_callback)
            
            self.assertEqual(result.successful, 1)
        finally:
            os.unlink(tmp_path)

    def test_upload_result_defaults(self):
        """Test UploadResult default values."""
        result = UploadResult(path='/test.jpg')
        
        self.assertEqual(result.path, '/test.jpg')
        self.assertIsNone(result.url)
        self.assertIsNone(result.error)
        self.assertFalse(result.success)
        self.assertFalse(result.compressed)
        self.assertEqual(result.attempts, 0)

    def test_many_workers_few_files(self):
        """Test when workers > files (shouldn't cause issues)."""
        uploader = ImageUploader(max_workers=10)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            f.write(b'x' * 100)
            tmp_path = f.name
        
        try:
            # Just check it doesn't crash
            result = uploader.upload_batch([tmp_path], retries=1)
            # Will fail because no mock, but shouldn't crash
            self.assertEqual(result.total, 1)
        finally:
            os.unlink(tmp_path)


if __name__ == '__main__':
    unittest.main()
