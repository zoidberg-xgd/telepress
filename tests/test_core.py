import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import tempfile
import zipfile
import shutil
from telepress.core import TelegraphPublisher
from telepress.exceptions import ValidationError


class TestTelegraphPublisherInit(unittest.TestCase):
    @patch('telepress.core.TelegraphAuth')
    def test_init_with_token(self, MockAuth):
        """Test publisher initialization with explicit token."""
        TelegraphPublisher(token="test_token")
        MockAuth.return_value.get_client.assert_called_with("test_token", "TelegraphPublisher")

    @patch('telepress.core.TelegraphAuth')
    def test_init_with_custom_short_name(self, MockAuth):
        """Test publisher initialization with custom short name."""
        TelegraphPublisher(short_name="MyApp")
        MockAuth.return_value.get_client.assert_called_with(None, "MyApp")

    @patch('telepress.core.TelegraphAuth')
    def test_init_default(self, MockAuth):
        """Test publisher initialization with defaults."""
        TelegraphPublisher()
        MockAuth.return_value.get_client.assert_called_with(None, "TelegraphPublisher")


class TestPublishRouting(unittest.TestCase):
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake")

    @patch.object(TelegraphPublisher, 'publish_zip_gallery')
    @patch('os.path.getsize', return_value=1024)
    @patch('os.path.exists', return_value=True)
    def test_publish_routes_zip_to_gallery(self, mock_exists, mock_size, mock_gallery):
        """Test that .zip files are routed to publish_zip_gallery."""
        mock_gallery.return_value = 'http://result.url'
        result = self.publisher.publish('/path/to/file.zip', title='Test')
        mock_gallery.assert_called_once_with('/path/to/file.zip', 'Test')

    @patch.object(TelegraphPublisher, 'publish_image')
    @patch('os.path.getsize', return_value=1024)
    @patch('os.path.exists', return_value=True)
    def test_publish_routes_jpg_to_image(self, mock_exists, mock_size, mock_image):
        """Test that .jpg files are routed to publish_image."""
        mock_image.return_value = 'http://result.url'
        self.publisher.publish('/path/to/file.jpg', title='Test')
        mock_image.assert_called_once()

    @patch.object(TelegraphPublisher, 'publish_image')
    @patch('os.path.getsize', return_value=1024)
    @patch('os.path.exists', return_value=True)
    def test_publish_routes_png_to_image(self, mock_exists, mock_size, mock_image):
        """Test that .png files are routed to publish_image."""
        mock_image.return_value = 'http://result.url'
        self.publisher.publish('/path/to/file.png', title='Test')
        mock_image.assert_called_once()

    @patch.object(TelegraphPublisher, 'publish_markdown')
    @patch('os.path.getsize', return_value=1024)
    @patch('os.path.exists', return_value=True)
    def test_publish_routes_md_to_markdown(self, mock_exists, mock_size, mock_md):
        """Test that .md files are routed to publish_markdown."""
        mock_md.return_value = 'http://result.url'
        self.publisher.publish('/path/to/file.md', title='Test')
        mock_md.assert_called_once()

    @patch.object(TelegraphPublisher, 'publish_markdown')
    @patch('os.path.getsize', return_value=1024)
    @patch('os.path.exists', return_value=True)
    def test_publish_routes_txt_to_markdown(self, mock_exists, mock_size, mock_md):
        """Test that .txt files are routed to publish_markdown."""
        mock_md.return_value = 'http://result.url'
        self.publisher.publish('/path/to/file.txt', title='Test')
        mock_md.assert_called_once()

    @patch('os.path.getsize', return_value=1024)
    @patch('os.path.exists', return_value=True)
    def test_publish_uses_filename_as_default_title(self, mock_exists, mock_size):
        """Test that filename without extension is used as default title."""
        with patch.object(self.publisher, 'publish_markdown') as mock_md:
            mock_md.return_value = 'http://result.url'
            self.publisher.publish('/path/to/my_article.md')
            mock_md.assert_called_with('/path/to/my_article.md', 'my_article')

    def test_publish_file_not_found(self):
        """Test that non-existent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.publisher.publish('/nonexistent/file.md')


class TestPublishMarkdown(unittest.TestCase):
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake")

    @patch('builtins.open', new_callable=mock_open, read_data="# Test Content")
    def test_publish_markdown_small_file(self, mock_file):
        """Test publishing small markdown file."""
        self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/page', 'path': 'path'}
        
        url = self.publisher.publish_markdown('/fake/path.md', title="Test")
        
        self.assertEqual(url, 'http://telegra.ph/page')
        self.mock_client.create_page.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    def test_publish_markdown_large_file_splits(self, mock_file):
        """Test that large markdown file is split into multiple pages."""
        # Create content larger than SAFE_CHUNK_SIZE (40000)
        large_content = "Line\n" * 10000  # ~50000 chars
        mock_file.return_value.read.return_value = large_content
        
        self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/page', 'path': 'page'}
        
        url = self.publisher.publish_markdown('/fake/path.md', title="LargeDoc")
        
        # Should have called create_page multiple times (at least 2)
        self.assertGreater(self.mock_client.create_page.call_count, 1)

    @patch('builtins.open', new_callable=mock_open)
    def test_publish_markdown_pagination_titles(self, mock_file):
        """Test that paginated pages have correct titles."""
        large_content = "x" * 50000
        mock_file.return_value.read.return_value = large_content
        
        self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/page', 'path': 'page'}
        
        self.publisher.publish_markdown('/fake/path.md', title="MyDoc")
        
        # Check that first call includes "(1/" in title
        first_call_title = self.mock_client.create_page.call_args_list[0][1]['title']
        self.assertIn("(1/", first_call_title)
        self.assertIn("MyDoc", first_call_title)

    @patch('builtins.open', new_callable=mock_open, read_data="")
    def test_publish_markdown_empty_file(self, mock_file):
        """Test publishing empty markdown file."""
        self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/page', 'path': 'path'}
        
        url = self.publisher.publish_markdown('/fake/path.md', title="Empty")
        self.assertEqual(url, 'http://telegra.ph/page')


class TestPublishText(unittest.TestCase):
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake")

    def test_publish_text_success(self):
        """Test publishing text content directly."""
        self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/page', 'path': 'path'}
        
        url = self.publisher.publish_text("# Hello\n\nWorld!", title="Test")
        
        self.assertEqual(url, 'http://telegra.ph/page')
        self.mock_client.create_page.assert_called_once()

    def test_publish_text_empty_content(self):
        """Test publishing empty content."""
        self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/page', 'path': 'path'}
        
        url = self.publisher.publish_text("", title="Empty")
        self.assertEqual(url, 'http://telegra.ph/page')

    def test_publish_text_unicode(self):
        """Test publishing unicode content."""
        self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/page', 'path': 'path'}
        
        url = self.publisher.publish_text("中文内容 🎉", title="Unicode Test")
        self.assertEqual(url, 'http://telegra.ph/page')


class TestPublishImage(unittest.TestCase):
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake")

    def test_publish_image_success(self):
        """Test successful image publishing."""
        self.publisher.uploader = MagicMock()
        self.publisher.uploader.upload.return_value = "http://telegra.ph/file/img.jpg"
        self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/img', 'path': 'path'}

        url = self.publisher.publish_image('/fake/image.jpg', title="MyImage")
        
        self.assertEqual(url, 'http://telegra.ph/img')
        self.publisher.uploader.upload.assert_called_with('/fake/image.jpg')
        
        # Verify content structure
        call_args = self.mock_client.create_page.call_args
        content = call_args[1]['content']
        self.assertEqual(content[0]['tag'], 'img')
        self.assertIn('src', content[0]['attrs'])


class TestPublishZipGallery(unittest.TestCase):
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake")
            self.publisher.uploader = MagicMock()

    def test_publish_zip_gallery_success(self):
        """Test successful zip gallery publishing."""
        # Create a test zip with images
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                zf.writestr('1.jpg', b'fake image data')
                zf.writestr('2.jpg', b'fake image data')
            zip_path = tmp_zip.name
        
        try:
            self.publisher.uploader.upload.return_value = "http://telegra.ph/file/img.jpg"
            self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/gallery', 'path': 'gallery'}
            
            url = self.publisher.publish_zip_gallery(zip_path, title="TestGallery")
            
            self.assertEqual(url, 'http://telegra.ph/gallery')
            self.assertEqual(self.publisher.uploader.upload.call_count, 2)
        finally:
            os.unlink(zip_path)

    def test_publish_zip_gallery_natural_sort(self):
        """Test that images are sorted naturally (1, 2, 10 not 1, 10, 2)."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                zf.writestr('10.jpg', b'img10')
                zf.writestr('2.jpg', b'img2')
                zf.writestr('1.jpg', b'img1')
            zip_path = tmp_zip.name
        
        try:
            upload_order = []
            def track_upload(path):
                upload_order.append(os.path.basename(path))
                return "http://url"
            
            self.publisher.uploader.upload.side_effect = track_upload
            self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            self.publisher.publish_zip_gallery(zip_path, title="Test")
            
            self.assertEqual(upload_order, ['1.jpg', '2.jpg', '10.jpg'])
        finally:
            os.unlink(zip_path)

    def test_publish_zip_gallery_empty_zip(self):
        """Test that empty zip raises ValidationError."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                pass  # Empty zip
            zip_path = tmp_zip.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                self.publisher.publish_zip_gallery(zip_path, title="Empty")
            self.assertIn("No images found", str(ctx.exception))
        finally:
            os.unlink(zip_path)

    def test_publish_zip_gallery_no_images(self):
        """Test that zip without images raises ValidationError."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                zf.writestr('readme.txt', 'not an image')
                zf.writestr('data.json', '{}')
            zip_path = tmp_zip.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                self.publisher.publish_zip_gallery(zip_path, title="NoImages")
            self.assertIn("No images found", str(ctx.exception))
        finally:
            os.unlink(zip_path)

    def test_publish_zip_gallery_invalid_zip(self):
        """Test that invalid zip file raises ValidationError."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            tmp.write(b'not a valid zip file')
            zip_path = tmp.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                self.publisher.publish_zip_gallery(zip_path, title="Invalid")
            self.assertIn("Invalid zip", str(ctx.exception))
        finally:
            os.unlink(zip_path)

    def test_publish_zip_gallery_pagination(self):
        """Test that large galleries are paginated."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                # Create 150 images (should split into 2 pages at 100 per page)
                for i in range(150):
                    zf.writestr(f'{i}.jpg', b'img')
            zip_path = tmp_zip.name
        
        try:
            self.publisher.uploader.upload.return_value = "http://url"
            self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            self.publisher.publish_zip_gallery(zip_path, title="LargeGallery")
            
            # Should create 2 pages
            self.assertEqual(self.mock_client.create_page.call_count, 2)
        finally:
            os.unlink(zip_path)

    def test_publish_zip_gallery_handles_upload_failure(self):
        """Test that individual upload failures don't crash the whole gallery."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                zf.writestr('1.jpg', b'img1')
                zf.writestr('2.jpg', b'img2')
            zip_path = tmp_zip.name
        
        try:
            # First upload fails, second succeeds
            from telepress.exceptions import UploadError
            self.publisher.uploader.upload.side_effect = [
                UploadError("Network error"),
                "http://url"
            ]
            self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            # Should not raise, just warn
            url = self.publisher.publish_zip_gallery(zip_path, title="Test")
            self.assertEqual(url, 'http://url')
        finally:
            os.unlink(zip_path)


class TestLinkPages(unittest.TestCase):
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake")

    def test_link_pages_single_page_no_op(self):
        """Test that single page doesn't get navigation."""
        pages_info = [{
            'path': 'page1',
            'url': 'http://url1',
            'title': 'Page 1',
            'content': [{'tag': 'p', 'children': ['content']}]
        }]
        
        self.publisher._link_pages(pages_info)
        
        # edit_page should not be called for single page
        self.mock_client.edit_page.assert_not_called()

    def test_link_pages_multiple_pages(self):
        """Test that multiple pages get navigation links."""
        pages_info = [
            {'path': 'page1', 'url': 'http://url1', 'title': 'Page 1', 'content': []},
            {'path': 'page2', 'url': 'http://url2', 'title': 'Page 2', 'content': []},
        ]
        
        self.publisher._link_pages(pages_info)
        
        # edit_page should be called for each page
        self.assertEqual(self.mock_client.edit_page.call_count, 2)

    def test_link_pages_handles_edit_failure(self):
        """Test that edit failure doesn't crash linking."""
        pages_info = [
            {'path': 'page1', 'url': 'http://url1', 'title': 'Page 1', 'content': []},
            {'path': 'page2', 'url': 'http://url2', 'title': 'Page 2', 'content': []},
        ]
        
        self.mock_client.edit_page.side_effect = Exception("API Error")
        
        # Should not raise
        self.publisher._link_pages(pages_info)


class TestImageExtensions(unittest.TestCase):
    def test_image_extensions_constant(self):
        """Test that IMAGE_EXTENSIONS contains expected formats."""
        expected = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        self.assertEqual(TelegraphPublisher.IMAGE_EXTENSIONS, expected)


class TestFileValidation(unittest.TestCase):
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake")

    def test_unsupported_file_type_pdf(self):
        """Test that PDF files raise ValidationError."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4 fake pdf content')
            tmp_path = f.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                self.publisher.publish(tmp_path, title="Test")
            self.assertIn("Unsupported file type", str(ctx.exception))
            self.assertIn(".pdf", str(ctx.exception))
        finally:
            os.unlink(tmp_path)

    def test_unsupported_file_type_docx(self):
        """Test that DOCX files raise ValidationError."""
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            f.write(b'PK fake docx content')
            tmp_path = f.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                self.publisher.publish(tmp_path, title="Test")
            self.assertIn("Unsupported file type", str(ctx.exception))
        finally:
            os.unlink(tmp_path)

    def test_file_too_large(self):
        """Test that files over 100MB raise ValidationError."""
        with patch('os.path.getsize', return_value=150 * 1024 * 1024):  # 150MB
            with patch('os.path.exists', return_value=True):
                with self.assertRaises(ValidationError) as ctx:
                    self.publisher.publish('/fake/large.md', title="Test")
                self.assertIn("too large", str(ctx.exception))

    def test_binary_file_with_txt_extension(self):
        """Test that binary file with .txt extension raises ValidationError."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            # Write binary content that will fail UTF-8 decode
            f.write(bytes([0x80, 0x81, 0x82, 0xff, 0xfe]))
            tmp_path = f.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                self.publisher.publish(tmp_path, title="Test")
            self.assertIn("Cannot read file as text", str(ctx.exception))
        finally:
            os.unlink(tmp_path)

    def test_supported_extensions(self):
        """Test that error message lists supported formats."""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write(b'content')
            tmp_path = f.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                self.publisher.publish(tmp_path, title="Test")
            error_msg = str(ctx.exception)
            self.assertIn(".md", error_msg)
            self.assertIn(".txt", error_msg)
            self.assertIn(".jpg", error_msg)
            self.assertIn(".zip", error_msg)
        finally:
            os.unlink(tmp_path)


class TestLargeContentLimits(unittest.TestCase):
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake")

    def test_text_page_limit_enforced(self):
        """Test that text files are limited to MAX_PAGES."""
        # Create a temp file with content that would generate 150 pages (over 100 limit)
        huge_content = "line\n" * (150 * 8000)  # ~150 pages at 40000 chars each
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(huge_content)
            tmp_path = f.name
        
        try:
            self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            self.publisher.publish_markdown(tmp_path, title="Huge")
            
            # Should only create 100 pages (MAX_PAGES limit)
            self.assertEqual(self.mock_client.create_page.call_count, 100)
        finally:
            os.unlink(tmp_path)

    def test_image_limit_enforced(self):
        """Test that zip galleries are limited to MAX_TOTAL_IMAGES."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                # Create 6000 images (over 5000 limit)
                for i in range(6000):
                    zf.writestr(f'{i}.jpg', b'img')
            zip_path = tmp_zip.name
        
        try:
            self.publisher.uploader = MagicMock()
            self.publisher.uploader.upload.return_value = "http://url"
            self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            self.publisher.publish_zip_gallery(zip_path, title="HugeGallery")
            
            # Should only upload 5000 images (MAX_TOTAL_IMAGES limit)
            self.assertEqual(self.publisher.uploader.upload.call_count, 5000)
        finally:
            os.unlink(zip_path)


if __name__ == '__main__':
    unittest.main()
