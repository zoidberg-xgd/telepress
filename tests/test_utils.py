import unittest
import os
import tempfile
import zipfile
import shutil
from telepress.utils import (
    natural_sort_key, sanitize_nodes, validate_file_size, safe_extract_zip,
    MAX_TEXT_SIZE, MAX_IMAGE_SIZE, MAX_IMAGES_PER_PAGE, MAX_PAGES, MAX_TOTAL_IMAGES,
    MAX_FILE_SIZE, ALLOWED_IMAGE_EXTENSIONS, ALLOWED_TEXT_EXTENSIONS, ALLOWED_ARCHIVE_EXTENSIONS
)
from telepress.exceptions import SecurityError, ValidationError


class TestNaturalSortKey(unittest.TestCase):
    def test_numeric_sorting(self):
        """Test that numbers are sorted naturally."""
        files = ['1.png', '10.png', '2.png']
        files.sort(key=natural_sort_key)
        self.assertEqual(files, ['1.png', '2.png', '10.png'])

    def test_alphanumeric_sorting(self):
        """Test mixed alphanumeric sorting."""
        files = ['img1.jpg', 'img10.jpg', 'img2.jpg']
        files.sort(key=natural_sort_key)
        self.assertEqual(files, ['img1.jpg', 'img2.jpg', 'img10.jpg'])

    def test_case_insensitive_sorting(self):
        """Test that sorting is case insensitive."""
        files = ['A.png', 'b.png', 'C.png']
        files.sort(key=natural_sort_key)
        self.assertEqual(files, ['A.png', 'b.png', 'C.png'])

    def test_multiple_numbers(self):
        """Test strings with multiple number segments."""
        files = ['ch1_p10.png', 'ch1_p2.png', 'ch2_p1.png']
        files.sort(key=natural_sort_key)
        self.assertEqual(files, ['ch1_p2.png', 'ch1_p10.png', 'ch2_p1.png'])

    def test_no_numbers(self):
        """Test strings without numbers."""
        files = ['apple.png', 'banana.png', 'cherry.png']
        files.sort(key=natural_sort_key)
        self.assertEqual(files, ['apple.png', 'banana.png', 'cherry.png'])

    def test_leading_zeros(self):
        """Test numbers with leading zeros."""
        files = ['001.png', '010.png', '002.png']
        files.sort(key=natural_sort_key)
        self.assertEqual(files, ['001.png', '002.png', '010.png'])

    def test_empty_string(self):
        """Test empty string doesn't crash."""
        result = natural_sort_key('')
        self.assertIsInstance(result, list)


class TestSanitizeNodes(unittest.TestCase):
    def test_h1_to_h3(self):
        """Test H1 is downgraded to H3."""
        nodes = [{'tag': 'h1', 'children': ['Title']}]
        sanitized = sanitize_nodes(nodes)
        self.assertEqual(sanitized[0]['tag'], 'h3')

    def test_h2_to_h4(self):
        """Test H2 is downgraded to H4."""
        nodes = [{'tag': 'h2', 'children': ['Subtitle']}]
        sanitized = sanitize_nodes(nodes)
        self.assertEqual(sanitized[0]['tag'], 'h4')

    def test_h5_h6_to_h4(self):
        """Test H5 and H6 are downgraded to H4."""
        nodes = [
            {'tag': 'h5', 'children': ['H5']},
            {'tag': 'h6', 'children': ['H6']}
        ]
        sanitized = sanitize_nodes(nodes)
        self.assertEqual(sanitized[0]['tag'], 'h4')
        self.assertEqual(sanitized[1]['tag'], 'h4')

    def test_h3_h4_unchanged(self):
        """Test H3 and H4 remain unchanged."""
        nodes = [
            {'tag': 'h3', 'children': ['H3']},
            {'tag': 'h4', 'children': ['H4']}
        ]
        sanitized = sanitize_nodes(nodes)
        self.assertEqual(sanitized[0]['tag'], 'h3')
        self.assertEqual(sanitized[1]['tag'], 'h4')

    def test_other_tags_unchanged(self):
        """Test non-header tags are unchanged."""
        nodes = [
            {'tag': 'p', 'children': ['Text']},
            {'tag': 'a', 'attrs': {'href': '#'}, 'children': ['Link']}
        ]
        sanitized = sanitize_nodes(nodes)
        self.assertEqual(sanitized[0]['tag'], 'p')
        self.assertEqual(sanitized[1]['tag'], 'a')

    def test_nested_headers(self):
        """Test nested headers are also sanitized."""
        nodes = [
            {'tag': 'div', 'children': [
                {'tag': 'h1', 'children': ['Nested Title']},
                {'tag': 'div', 'children': [
                    {'tag': 'h2', 'children': ['Deep Nested']}
                ]}
            ]}
        ]
        sanitized = sanitize_nodes(nodes)
        self.assertEqual(sanitized[0]['children'][0]['tag'], 'h3')
        self.assertEqual(sanitized[0]['children'][1]['children'][0]['tag'], 'h4')

    def test_empty_list(self):
        """Test empty list returns empty list."""
        self.assertEqual(sanitize_nodes([]), [])

    def test_non_dict_items_unchanged(self):
        """Test that string items in list are unchanged."""
        nodes = ['plain text', {'tag': 'p', 'children': ['text']}]
        sanitized = sanitize_nodes(nodes)
        self.assertEqual(sanitized[0], 'plain text')

    def test_non_list_input(self):
        """Test non-list input returns as-is."""
        self.assertEqual(sanitize_nodes('string'), 'string')
        self.assertEqual(sanitize_nodes(None), None)


class TestValidateFileSize(unittest.TestCase):
    def test_file_within_limit(self):
        """Test file within size limit passes."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'x' * 100)
            tmp_path = tmp.name
        
        try:
            validate_file_size(tmp_path, 200, "Test Error")
        finally:
            os.remove(tmp_path)

    def test_file_exceeds_limit(self):
        """Test file exceeding size limit raises ValidationError."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'x' * 100)
            tmp_path = tmp.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                validate_file_size(tmp_path, 50, "File too big")
            self.assertIn("File too big", str(ctx.exception))
        finally:
            os.remove(tmp_path)

    def test_exact_limit(self):
        """Test file at exact limit passes."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'x' * 100)
            tmp_path = tmp.name
        
        try:
            validate_file_size(tmp_path, 100, "Error")
        finally:
            os.remove(tmp_path)

    def test_error_message_contains_sizes(self):
        """Test error message includes actual and max sizes."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b'x' * (2 * 1024 * 1024))  # 2MB
            tmp_path = tmp.name
        
        try:
            with self.assertRaises(ValidationError) as ctx:
                validate_file_size(tmp_path, 1024 * 1024, "Error")
            error_msg = str(ctx.exception)
            self.assertIn("Size:", error_msg)
            self.assertIn("Max:", error_msg)
        finally:
            os.remove(tmp_path)


class TestSafeExtractZip(unittest.TestCase):
    def test_extract_normal_zip(self):
        """Test extracting a normal zip file."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                zf.writestr('file1.txt', 'content1')
                zf.writestr('file2.txt', 'content2')
            zip_path = tmp_zip.name

        extract_dir = tempfile.mkdtemp()
        try:
            safe_extract_zip(zip_path, extract_dir)
            self.assertTrue(os.path.exists(os.path.join(extract_dir, 'file1.txt')))
            self.assertTrue(os.path.exists(os.path.join(extract_dir, 'file2.txt')))
        finally:
            os.remove(zip_path)
            shutil.rmtree(extract_dir)

    def test_extract_nested_directories(self):
        """Test extracting zip with nested directories."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                zf.writestr('dir1/file1.txt', 'content1')
                zf.writestr('dir1/dir2/file2.txt', 'content2')
            zip_path = tmp_zip.name

        extract_dir = tempfile.mkdtemp()
        try:
            safe_extract_zip(zip_path, extract_dir)
            self.assertTrue(os.path.exists(os.path.join(extract_dir, 'dir1', 'file1.txt')))
            self.assertTrue(os.path.exists(os.path.join(extract_dir, 'dir1', 'dir2', 'file2.txt')))
        finally:
            os.remove(zip_path)
            shutil.rmtree(extract_dir)

    def test_zip_slip_attack_detection(self):
        """Test that Zip Slip attack is detected and blocked."""
        # Create a malicious zip with path traversal
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                # Manually create an entry with path traversal
                info = zipfile.ZipInfo('../../../etc/passwd')
                zf.writestr(info, 'malicious content')
            zip_path = tmp_zip.name

        extract_dir = tempfile.mkdtemp()
        try:
            with self.assertRaises(SecurityError) as ctx:
                safe_extract_zip(zip_path, extract_dir)
            self.assertIn("Zip Slip", str(ctx.exception))
        finally:
            os.remove(zip_path)
            shutil.rmtree(extract_dir)

    def test_zip_slip_with_absolute_path(self):
        """Test that absolute paths in zip are blocked."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                info = zipfile.ZipInfo('/etc/passwd')
                zf.writestr(info, 'malicious')
            zip_path = tmp_zip.name

        extract_dir = tempfile.mkdtemp()
        try:
            with self.assertRaises(SecurityError):
                safe_extract_zip(zip_path, extract_dir)
        finally:
            os.remove(zip_path)
            shutil.rmtree(extract_dir)

    def test_empty_zip(self):
        """Test extracting empty zip file."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            with zipfile.ZipFile(tmp_zip, 'w') as zf:
                pass  # Empty zip
            zip_path = tmp_zip.name

        extract_dir = tempfile.mkdtemp()
        try:
            safe_extract_zip(zip_path, extract_dir)
            # Should not raise, directory should be empty
            self.assertEqual(os.listdir(extract_dir), [])
        finally:
            os.remove(zip_path)
            shutil.rmtree(extract_dir)


class TestConstants(unittest.TestCase):
    def test_max_text_size(self):
        """Test MAX_TEXT_SIZE constant."""
        self.assertEqual(MAX_TEXT_SIZE, 60 * 1024)

    def test_max_image_size(self):
        """Test MAX_IMAGE_SIZE constant."""
        self.assertEqual(MAX_IMAGE_SIZE, 5 * 1024 * 1024)

    def test_max_images_per_page(self):
        """Test MAX_IMAGES_PER_PAGE constant."""
        self.assertEqual(MAX_IMAGES_PER_PAGE, 100)

    def test_max_pages(self):
        """Test MAX_PAGES constant."""
        self.assertEqual(MAX_PAGES, 100)

    def test_max_total_images(self):
        """Test MAX_TOTAL_IMAGES constant."""
        self.assertEqual(MAX_TOTAL_IMAGES, 5000)

    def test_max_file_size(self):
        """Test MAX_FILE_SIZE constant."""
        self.assertEqual(MAX_FILE_SIZE, 100 * 1024 * 1024)

    def test_allowed_image_extensions(self):
        """Test ALLOWED_IMAGE_EXTENSIONS contains expected formats."""
        expected = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        self.assertEqual(ALLOWED_IMAGE_EXTENSIONS, expected)

    def test_allowed_text_extensions(self):
        """Test ALLOWED_TEXT_EXTENSIONS contains expected formats."""
        expected = {'.txt', '.md', '.markdown', '.rst', '.text'}
        self.assertEqual(ALLOWED_TEXT_EXTENSIONS, expected)

    def test_allowed_archive_extensions(self):
        """Test ALLOWED_ARCHIVE_EXTENSIONS contains expected formats."""
        expected = {'.zip'}
        self.assertEqual(ALLOWED_ARCHIVE_EXTENSIONS, expected)


if __name__ == '__main__':
    unittest.main()
