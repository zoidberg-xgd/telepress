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
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

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
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

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
        """Test publishing empty markdown file raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            self.publisher.publish_markdown('/fake/path.md', title="Empty")
        self.assertIn("empty", str(ctx.exception).lower())


class TestPublishText(unittest.TestCase):
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

    def test_publish_text_success(self):
        """Test publishing text content directly."""
        self.mock_client.create_page.return_value = {'url': 'http://telegra.ph/page', 'path': 'path'}
        
        url = self.publisher.publish_text("# Hello\n\nWorld!", title="Test")
        
        self.assertEqual(url, 'http://telegra.ph/page')
        self.mock_client.create_page.assert_called_once()

    def test_publish_text_empty_content(self):
        """Test publishing empty content raises ValidationError."""
        with self.assertRaises(ValidationError) as ctx:
            self.publisher.publish_text("", title="Empty")
        self.assertIn("empty", str(ctx.exception).lower())

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
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

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
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)
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
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

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
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

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
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

    @patch('telepress.core.time.sleep')
    def test_text_page_limit_enforced(self, mock_sleep):
        """Test that text files are limited to MAX_PAGES."""
        # Create content for ~5 pages to keep test fast
        # (actual MAX_PAGES test would be too slow)
        content = "x" * (5 * 20000)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            tmp_path = f.name
        
        try:
            self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            self.publisher.publish_markdown(tmp_path, title="Large")
            
            # Should create 5 pages
            self.assertEqual(self.mock_client.create_page.call_count, 5)
        finally:
            os.unlink(tmp_path)

    @patch('telepress.core.time.sleep')
    def test_image_limit_enforced(self, mock_sleep):
        """Test that zip galleries are paginated correctly."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                # Create 250 images (2.5 pages worth, keeps test fast)
                for i in range(250):
                    zf.writestr(f'{i}.jpg', b'img')
            zip_path = tmp_zip.name
        
        try:
            self.publisher.uploader = MagicMock()
            self.publisher.uploader.upload.return_value = "http://url"
            self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            self.publisher.publish_zip_gallery(zip_path, title="Gallery")
            
            # Should upload 250 images across 3 pages
            self.assertEqual(self.publisher.uploader.upload.call_count, 250)
            self.assertEqual(self.mock_client.create_page.call_count, 3)
        finally:
            os.unlink(zip_path)


class TestDeduplication(unittest.TestCase):
    """Tests for content deduplication feature."""
    
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=True)

    @patch('telepress.core._load_cache')
    @patch('telepress.core._save_cache')
    def test_skip_duplicate_returns_cached_url(self, mock_save, mock_load):
        """Test that duplicate content returns cached URL."""
        mock_load.return_value = {}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("Test content")
            tmp_path = f.name
        
        try:
            # First publish
            self.mock_client.create_page.return_value = {'url': 'http://cached.url', 'path': 'path'}
            url1 = self.publisher.publish_markdown(tmp_path, title="Test")
            
            # Simulate cache hit
            from telepress.core import _content_hash
            content_key = _content_hash("Test content" + "Test")
            self.publisher._cache[content_key] = 'http://cached.url'
            
            # Second publish should skip
            self.mock_client.create_page.reset_mock()
            url2 = self.publisher.publish_markdown(tmp_path, title="Test")
            
            self.assertEqual(url2, 'http://cached.url')
            self.mock_client.create_page.assert_not_called()
        finally:
            os.unlink(tmp_path)

    def test_skip_duplicate_disabled(self):
        """Test that skip_duplicate=False always publishes."""
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = mock_client
            publisher = TelegraphPublisher(token="fake", skip_duplicate=False)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("Test content")
            tmp_path = f.name
        
        try:
            mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            # Should publish both times
            publisher.publish_markdown(tmp_path, title="Test")
            publisher.publish_markdown(tmp_path, title="Test")
            
            self.assertEqual(mock_client.create_page.call_count, 2)
        finally:
            os.unlink(tmp_path)


class TestEmptyContentValidation(unittest.TestCase):
    """Tests for empty content validation."""
    
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

    def test_empty_file_raises_error(self):
        """Test that empty file raises ValidationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("")
            tmp_path = f.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                self.publisher.publish_markdown(tmp_path, title="Test")
            self.assertIn("empty", str(ctx.exception).lower())
        finally:
            os.unlink(tmp_path)

    def test_whitespace_only_file_raises_error(self):
        """Test that whitespace-only file raises ValidationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("   \n\n\t  \n  ")
            tmp_path = f.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                self.publisher.publish_markdown(tmp_path, title="Test")
            self.assertIn("empty", str(ctx.exception).lower())
        finally:
            os.unlink(tmp_path)


class TestLongLineSplitting(unittest.TestCase):
    """Tests for handling very long lines."""
    
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)
            self.publisher._cache = {}  # Clear any loaded cache

    @patch('telepress.core.time.sleep')
    def test_long_line_force_split(self, mock_sleep):
        """Test that lines longer than chunk size are force-split."""
        # Create content with one very long line (30000 chars, > 20000 limit)
        long_line = "x" * 30000
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(long_line)
            tmp_path = f.name
        
        try:
            self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            self.publisher.publish_markdown(tmp_path, title="LongLine")
            
            # Should create 2 pages (30000 / 20000 = 2)
            self.assertEqual(self.mock_client.create_page.call_count, 2)
        finally:
            os.unlink(tmp_path)

    @patch('telepress.core.time.sleep')
    def test_multiple_long_lines(self, mock_sleep):
        """Test handling multiple long lines."""
        # 3 lines of 25000 chars each = 75000 chars total
        content = ("y" * 25000 + "\n") * 3
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            tmp_path = f.name
        
        try:
            self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
            
            self.publisher.publish_markdown(tmp_path, title="MultiLong")
            
            # Each 25000 char line needs 2 chunks, but with smart splitting
            # Should create at least 4 pages
            self.assertGreaterEqual(self.mock_client.create_page.call_count, 4)
        finally:
            os.unlink(tmp_path)


class TestFloodControlRetry(unittest.TestCase):
    """Tests for flood control retry logic."""
    
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

    @patch('telepress.core.time.sleep')
    def test_flood_control_retry_success(self, mock_sleep):
        """Test that flood control triggers retry with proper wait time."""
        # First call raises flood control, second succeeds
        self.mock_client.create_page.side_effect = [
            Exception("Flood control exceeded. Retry in 5 seconds"),
            {'url': 'http://url', 'path': 'path'}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("Short content")
            tmp_path = f.name
        
        try:
            url = self.publisher.publish_markdown(tmp_path, title="Test")
            
            self.assertEqual(url, 'http://url')
            # Should have waited 6 seconds (5 + 1)
            mock_sleep.assert_any_call(6)
        finally:
            os.unlink(tmp_path)

    @patch('telepress.core.time.sleep')
    def test_flood_control_max_retries_exceeded(self, mock_sleep):
        """Test that max retries raises error."""
        # All calls fail with flood control - use side_effect function to always raise
        self.mock_client.create_page.side_effect = Exception("Flood control exceeded. Retry in 5 seconds")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write("Short content")
            tmp_path = f.name
        
        try:
            with self.assertRaises(RuntimeError) as ctx:
                self.publisher.publish_markdown(tmp_path, title="Test")
            self.assertIn("Failed to publish Part 1", str(ctx.exception))
        finally:
            os.unlink(tmp_path)


class TestLinkPagesRetry(unittest.TestCase):
    """Tests for link pages retry logic."""
    
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

    @patch('telepress.core.time.sleep')
    def test_link_pages_retry_on_flood_control(self, mock_sleep):
        """Test that link_pages retries on flood control."""
        pages_info = [
            {'path': 'path1', 'url': 'http://url1', 'title': 'T1', 'content': [], 'part_num': 1},
            {'path': 'path2', 'url': 'http://url2', 'title': 'T2', 'content': [], 'part_num': 2},
        ]
        
        # First edit fails, second succeeds for each page
        self.mock_client.edit_page.side_effect = [
            Exception("Flood control exceeded. Retry in 3 seconds"),
            None,  # Success for page 1
            None,  # Success for page 2
        ]
        
        self.publisher._link_pages(pages_info)
        
        # Should have called edit_page 3 times (1 retry + 2 successes)
        self.assertEqual(self.mock_client.edit_page.call_count, 3)

    @patch('telepress.core.time.sleep')
    def test_link_pages_continues_on_failure(self, mock_sleep):
        """Test that link_pages continues even if one page fails."""
        pages_info = [
            {'path': 'path1', 'url': 'http://url1', 'title': 'T1', 'content': [], 'part_num': 1},
            {'path': 'path2', 'url': 'http://url2', 'title': 'T2', 'content': [], 'part_num': 2},
        ]
        
        # First page always fails, second page succeeds
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if kwargs.get('path') == 'path1':
                raise Exception("Error")
            return None
        
        self.mock_client.edit_page.side_effect = side_effect
        
        # Should not raise, just print warning
        self.publisher._link_pages(pages_info)


class TestContentHashFunction(unittest.TestCase):
    """Tests for content hash function."""
    
    def test_hash_deterministic(self):
        """Test that same content produces same hash."""
        from telepress.core import _content_hash
        
        hash1 = _content_hash("test content")
        hash2 = _content_hash("test content")
        
        self.assertEqual(hash1, hash2)

    def test_hash_different_for_different_content(self):
        """Test that different content produces different hash."""
        from telepress.core import _content_hash
        
        hash1 = _content_hash("content a")
        hash2 = _content_hash("content b")
        
        self.assertNotEqual(hash1, hash2)

    def test_hash_length(self):
        """Test that hash has expected length."""
        from telepress.core import _content_hash
        
        hash_val = _content_hash("test")
        
        self.assertEqual(len(hash_val), 16)


class TestCacheFunctions(unittest.TestCase):
    """Tests for cache load/save functions."""
    
    def test_load_cache_returns_empty_dict_on_missing_file(self):
        """Test that missing cache file returns empty dict."""
        from telepress.core import _load_cache
        
        with patch('os.path.exists', return_value=False):
            cache = _load_cache()
        
        self.assertEqual(cache, {})

    def test_load_cache_handles_corrupt_file(self):
        """Test that corrupt cache file returns empty dict."""
        from telepress.core import _load_cache
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="not valid json{")):
                cache = _load_cache()
        
        self.assertEqual(cache, {})

    @patch('builtins.open', new_callable=mock_open)
    def test_save_cache_writes_json(self, mock_file):
        """Test that save_cache writes valid JSON."""
        from telepress.core import _save_cache
        
        _save_cache({'key': 'value'})
        
        mock_file.assert_called()


class TestPublishTextMethod(unittest.TestCase):
    """Tests for publish_text method."""
    
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

    def test_publish_text_creates_temp_file(self):
        """Test that publish_text works with direct content."""
        self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
        
        url = self.publisher.publish_text("# Hello\n\nWorld", title="Test")
        
        self.assertEqual(url, 'http://url')
        self.mock_client.create_page.assert_called_once()

    def test_publish_text_handles_unicode(self):
        """Test that publish_text handles unicode content."""
        self.mock_client.create_page.return_value = {'url': 'http://url', 'path': 'path'}
        
        url = self.publisher.publish_text("中文内容 🎉 émojis", title="Unicode")
        
        self.assertEqual(url, 'http://url')

    def test_publish_text_empty_raises_error(self):
        """Test that empty text raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.publisher.publish_text("", title="Empty")

    def test_publish_text_whitespace_raises_error(self):
        """Test that whitespace-only text raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.publisher.publish_text("   \n\t  ", title="Whitespace")


class TestPartialPublishFailure(unittest.TestCase):
    """Tests for partial publish failure handling."""
    
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

    @patch('telepress.core.time.sleep')
    def test_failure_reports_successful_pages(self, mock_sleep):
        """Test that failure message includes successfully published pages."""
        # Content that will be split into 3 pages
        content = "x" * 50000  # ~3 pages at 20000 each
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            tmp_path = f.name
        
        try:
            # First 2 pages succeed, third fails
            self.mock_client.create_page.side_effect = [
                {'url': 'http://url1', 'path': 'path1'},
                {'url': 'http://url2', 'path': 'path2'},
                Exception("Network error"),
                Exception("Network error"),
                Exception("Network error"),
                Exception("Network error"),
                Exception("Network error"),
            ]
            
            with self.assertRaises(RuntimeError) as ctx:
                self.publisher.publish_markdown(tmp_path, title="Test")
            
            error_msg = str(ctx.exception)
            self.assertIn("Successfully published: 2 pages", error_msg)
            self.assertIn("http://url1", error_msg)
        finally:
            os.unlink(tmp_path)


class TestPublishOptimizedGallery(unittest.TestCase):
    """Tests for publish_optimized_gallery method."""
    
    def setUp(self):
        with patch('telepress.core.TelegraphAuth') as MockAuth:
            self.mock_client = MagicMock()
            MockAuth.return_value.get_client.return_value = self.mock_client
            self.publisher = TelegraphPublisher(token="fake", skip_duplicate=False)

    def test_publish_optimized_gallery_single_page(self):
        """Test publishing a small gallery that fits in one page."""
        image_urls = [
            "http://example.com/img1.jpg",
            "http://example.com/img2.jpg",
            "http://example.com/img3.jpg"
        ]
        
        self.mock_client.create_page.return_value = {
            'url': 'http://telegra.ph/test',
            'path': 'test'
        }
        
        result = self.publisher.publish_optimized_gallery(image_urls, title="Test Gallery")
        
        self.assertEqual(result, 'http://telegra.ph/test')
        self.mock_client.create_page.assert_called_once()
        
        # Verify content structure
        call_args = self.mock_client.create_page.call_args
        content = call_args.kwargs.get('content') or call_args[1].get('content')
        self.assertEqual(len(content), 3)  # 3 images
        for i, node in enumerate(content):
            self.assertEqual(node['tag'], 'img')
            self.assertEqual(node['attrs']['src'], image_urls[i])

    def test_publish_optimized_gallery_empty_urls(self):
        """Test that empty URL list raises ValidationError."""
        with self.assertRaises(ValidationError):
            self.publisher.publish_optimized_gallery([], title="Test")

    def test_publish_optimized_gallery_pagination(self):
        """Test that large galleries are split into multiple pages."""
        # Create 150 image URLs (should be split into 2 pages at 100 per page)
        image_urls = [f"http://example.com/img{i}.jpg" for i in range(150)]
        
        self.mock_client.create_page.side_effect = [
            {'url': 'http://telegra.ph/page1', 'path': 'page1'},
            {'url': 'http://telegra.ph/page2', 'path': 'page2'},
        ]
        self.mock_client.edit_page.return_value = {}
        
        result = self.publisher.publish_optimized_gallery(image_urls, title="Test Gallery")
        
        self.assertEqual(result, 'http://telegra.ph/page1')
        self.assertEqual(self.mock_client.create_page.call_count, 2)
        
        # First page should have title with (1/2)
        first_call = self.mock_client.create_page.call_args_list[0]
        self.assertIn("1/2", first_call.kwargs.get('title', first_call[1].get('title', '')))
        
        # Second page should have title with (2/2)
        second_call = self.mock_client.create_page.call_args_list[1]
        self.assertIn("2/2", second_call.kwargs.get('title', second_call[1].get('title', '')))

    def test_publish_optimized_gallery_no_upload(self):
        """Test that no image upload is performed (URLs used directly)."""
        image_urls = ["http://myserver.com/gallery/1.jpg"]
        
        self.mock_client.create_page.return_value = {
            'url': 'http://telegra.ph/test',
            'path': 'test'
        }
        
        with patch.object(self.publisher.uploader, 'upload') as mock_upload:
            self.publisher.publish_optimized_gallery(image_urls, title="Test")
            mock_upload.assert_not_called()  # No upload should happen

    def test_publish_optimized_gallery_preserves_url_order(self):
        """Test that image URLs maintain their order."""
        image_urls = [
            "http://example.com/z.jpg",
            "http://example.com/a.jpg",
            "http://example.com/m.jpg"
        ]
        
        self.mock_client.create_page.return_value = {
            'url': 'http://telegra.ph/test',
            'path': 'test'
        }
        
        self.publisher.publish_optimized_gallery(image_urls, title="Test")
        
        call_args = self.mock_client.create_page.call_args
        content = call_args.kwargs.get('content') or call_args[1].get('content')
        
        # Order should be preserved exactly as input
        self.assertEqual(content[0]['attrs']['src'], "http://example.com/z.jpg")
        self.assertEqual(content[1]['attrs']['src'], "http://example.com/a.jpg")
        self.assertEqual(content[2]['attrs']['src'], "http://example.com/m.jpg")

    @patch('telepress.core.time.sleep')
    def test_publish_optimized_gallery_links_pages(self, mock_sleep):
        """Test that multi-page galleries get navigation links."""
        image_urls = [f"http://example.com/img{i}.jpg" for i in range(150)]
        
        self.mock_client.create_page.side_effect = [
            {'url': 'http://telegra.ph/page1', 'path': 'page1'},
            {'url': 'http://telegra.ph/page2', 'path': 'page2'},
        ]
        self.mock_client.edit_page.return_value = {}
        
        self.publisher.publish_optimized_gallery(image_urls, title="Test")
        
        # edit_page should be called to add navigation links
        self.assertTrue(self.mock_client.edit_page.called)


if __name__ == '__main__':
    unittest.main()

