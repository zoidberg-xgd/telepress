import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import tempfile
from telepress.uploader import ImageUploader
from telepress.exceptions import UploadError, ValidationError, DependencyError


class TestUploader(unittest.TestCase):
    def setUp(self):
        self.uploader = ImageUploader()

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.validate_file_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_upload_success(self, mock_file, mock_validate, mock_exists, mock_upload):
        """Test successful image upload."""
        mock_exists.return_value = True
        mock_upload.return_value = [{'src': '/file/test.jpg'}]
        
        url = self.uploader.upload('/path/to/image.jpg')
        self.assertEqual(url, 'https://telegra.ph/file/test.jpg')

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.validate_file_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_upload_retry_success_on_second_attempt(self, mock_file, mock_validate, mock_exists, mock_upload):
        """Test that upload retries and succeeds on second attempt."""
        mock_exists.return_value = True
        mock_upload.side_effect = [
            Exception("Network Error"),
            [{'src': '/file/success.jpg'}]
        ]
        
        url = self.uploader.upload('/path/to/image.jpg', retries=3)
        self.assertEqual(url, 'https://telegra.ph/file/success.jpg')
        self.assertEqual(mock_upload.call_count, 2)

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.validate_file_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_upload_retry_failure(self, mock_file, mock_validate, mock_exists, mock_upload):
        """Test that upload fails after exhausting retries."""
        mock_exists.return_value = True
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
    @patch('telepress.uploader.validate_file_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_invalid_response_format_empty_list(self, mock_file, mock_validate, mock_exists, mock_upload):
        """Test that empty response list raises UploadError."""
        mock_exists.return_value = True
        mock_upload.return_value = []
        
        with self.assertRaises(UploadError) as ctx:
            self.uploader.upload('/path/to/image.jpg', retries=1)
        
        self.assertIn("Invalid response", str(ctx.exception))

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.validate_file_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_invalid_response_format_missing_src(self, mock_file, mock_validate, mock_exists, mock_upload):
        """Test that response without 'src' key raises UploadError."""
        mock_exists.return_value = True
        mock_upload.return_value = [{'error': 'something'}]
        
        with self.assertRaises(UploadError) as ctx:
            self.uploader.upload('/path/to/image.jpg', retries=1)
        
        self.assertIn("Invalid response", str(ctx.exception))

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.validate_file_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_invalid_response_not_list(self, mock_file, mock_validate, mock_exists, mock_upload):
        """Test that non-list response raises UploadError."""
        mock_exists.return_value = True
        mock_upload.return_value = "unexpected string"
        
        with self.assertRaises(UploadError) as ctx:
            self.uploader.upload('/path/to/image.jpg', retries=1)
        
        self.assertIn("Invalid response", str(ctx.exception))

    def test_file_too_large(self):
        """Test that oversized file raises ValidationError."""
        # Create a temp file larger than 5MB limit
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'x' * (6 * 1024 * 1024))  # 6MB
            tmp_path = f.name
        
        try:
            with self.assertRaises(ValidationError):
                self.uploader.upload(tmp_path)
        finally:
            os.unlink(tmp_path)

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.validate_file_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_retry_waits_between_attempts(self, mock_sleep, mock_file, mock_validate, mock_exists, mock_upload):
        """Test that retry waits 1 second between attempts."""
        mock_exists.return_value = True
        mock_upload.side_effect = Exception("Error")
        
        try:
            self.uploader.upload('/path/to/image.jpg', retries=3)
        except UploadError:
            pass
        
        # Should have slept twice (after 1st and 2nd failure, not after 3rd)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(1)

    @patch('telepress.uploader.upload_file')
    @patch('os.path.exists')
    @patch('telepress.uploader.validate_file_size')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    def test_default_retries_is_three(self, mock_file, mock_validate, mock_exists, mock_upload):
        """Test that default retry count is 3."""
        mock_exists.return_value = True
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


if __name__ == '__main__':
    unittest.main()
