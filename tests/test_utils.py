import unittest
import os
import tempfile
import zipfile
import shutil
from telepress.utils import (
    natural_sort_key, sanitize_nodes, validate_file_size, safe_extract_zip,
    compress_image_to_size,
    MAX_TEXT_SIZE, MAX_IMAGE_SIZE, MAX_IMAGES_PER_PAGE,
    ALLOWED_IMAGE_EXTENSIONS, ALLOWED_TEXT_EXTENSIONS, ALLOWED_ARCHIVE_EXTENSIONS
)
from telepress.exceptions import SecurityError, ValidationError, ConversionError
from PIL import Image


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


class TestCompressImageToSize(unittest.TestCase):
    def test_small_image_no_compression(self):
        """Test that images under the limit are not compressed."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            tmp_path = f.name
        
        # Create a small image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(tmp_path, format='JPEG')
        
        try:
            result_path, was_compressed = compress_image_to_size(tmp_path, MAX_IMAGE_SIZE)
            self.assertEqual(result_path, tmp_path)
            self.assertFalse(was_compressed)
        finally:
            os.unlink(tmp_path)

    def test_large_image_gets_compressed(self):
        """Test that large images are compressed."""
        import numpy as np
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            tmp_path = f.name
        
        # Create a noisy image that won't compress well
        noise = np.random.randint(0, 255, (1500, 1500, 3), dtype=np.uint8)
        img = Image.fromarray(noise, 'RGB')
        img.save(tmp_path, format='PNG')
        
        original_size = os.path.getsize(tmp_path)
        # Use a limit smaller than the file
        max_size = min(original_size - 100000, 500000)  # Ensure we need compression
        
        try:
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size)
            self.assertTrue(was_compressed)
            self.assertNotEqual(result_path, tmp_path)
            self.assertTrue(os.path.exists(result_path))
            
            # Verify compressed file is under limit
            compressed_size = os.path.getsize(result_path)
            self.assertLessEqual(compressed_size, max_size)
            
            # Clean up temp file
            os.unlink(result_path)
        finally:
            os.unlink(tmp_path)

    def test_rgba_image_conversion(self):
        """Test that RGBA images are converted to RGB for JPEG compression."""
        import numpy as np
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            tmp_path = f.name
        
        # Create an RGBA image with noise (harder to compress)
        noise = np.random.randint(0, 255, (1000, 1000, 4), dtype=np.uint8)
        img = Image.fromarray(noise, 'RGBA')
        img.save(tmp_path, format='PNG')
        
        original_size = os.path.getsize(tmp_path)
        # Use a limit that will trigger compression
        max_size = min(original_size - 50000, 200000)
        
        try:
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size)
            self.assertTrue(was_compressed)
            
            # Verify the output is a valid JPEG (RGB mode)
            result_img = Image.open(result_path)
            self.assertEqual(result_img.mode, 'RGB')
            result_img.close()
            
            os.unlink(result_path)
        finally:
            os.unlink(tmp_path)

    def test_gif_raises_error(self):
        """Test that GIF files raise ConversionError (due to animation complexity)."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.gif') as f:
            tmp_path = f.name
        
        # Create a large GIF
        img = Image.new('RGB', (100, 100), color='green')
        img.save(tmp_path, format='GIF')
        
        # Make it appear larger than limit by checking the condition
        try:
            # Artificially test by setting a very small max_size
            with self.assertRaises(ConversionError) as ctx:
                compress_image_to_size(tmp_path, max_size=10)  # 10 bytes
            self.assertIn("GIF", str(ctx.exception))
        finally:
            os.unlink(tmp_path)

    def test_compression_preserves_original_file(self):
        """Test that compression does not modify the original file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            tmp_path = f.name
        
        img = Image.new('RGB', (3000, 3000), color='yellow')
        img.save(tmp_path, format='PNG')
        
        original_size = os.path.getsize(tmp_path)
        
        try:
            result_path, was_compressed = compress_image_to_size(tmp_path, MAX_IMAGE_SIZE)
            
            # Original file should still exist with same size
            self.assertTrue(os.path.exists(tmp_path))
            self.assertEqual(os.path.getsize(tmp_path), original_size)
            
            if was_compressed:
                os.unlink(result_path)
        finally:
            os.unlink(tmp_path)

    def test_compression_with_custom_limits(self):
        """Test compression with custom size limit."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            tmp_path = f.name
        
        img = Image.new('RGB', (1000, 1000), color='purple')
        img.save(tmp_path, format='JPEG', quality=95)
        
        try:
            # Compress to a very small size
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size=50000)  # 50KB
            
            if was_compressed:
                self.assertLessEqual(os.path.getsize(result_path), 50000)
                os.unlink(result_path)
        finally:
            os.unlink(tmp_path)

    def test_exact_boundary_size(self):
        """Test image exactly at the size limit (should not compress)."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            tmp_path = f.name
        
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(tmp_path, format='JPEG')
        file_size = os.path.getsize(tmp_path)
        
        try:
            # Use exact file size as limit
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size=file_size)
            self.assertEqual(result_path, tmp_path)
            self.assertFalse(was_compressed)
        finally:
            os.unlink(tmp_path)

    def test_one_byte_over_limit(self):
        """Test image one byte over limit triggers compression."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            tmp_path = f.name
        
        img = Image.new('RGB', (500, 500), color='red')
        img.save(tmp_path, format='JPEG', quality=95)
        file_size = os.path.getsize(tmp_path)
        
        try:
            # Set limit to one byte less than file size
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size=file_size - 1)
            self.assertTrue(was_compressed)
            self.assertLess(os.path.getsize(result_path), file_size)
            os.unlink(result_path)
        finally:
            os.unlink(tmp_path)

    def test_corrupted_image_file(self):
        """Test handling of corrupted/invalid image file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            f.write(b'not a valid image data')
            tmp_path = f.name
        
        try:
            with self.assertRaises(ConversionError):
                compress_image_to_size(tmp_path, max_size=10)
        finally:
            os.unlink(tmp_path)

    def test_empty_file(self):
        """Test handling of empty file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f:
            tmp_path = f.name
            # File is empty (0 bytes)
        
        try:
            # Empty file is under limit, should return as-is
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size=1000)
            self.assertEqual(result_path, tmp_path)
            self.assertFalse(was_compressed)
        finally:
            os.unlink(tmp_path)

    def test_webp_input_format(self):
        """Test WebP input format is handled correctly."""
        import numpy as np
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webp') as f:
            tmp_path = f.name
        
        # Create noisy image that will be larger
        noise = np.random.randint(0, 255, (800, 800, 3), dtype=np.uint8)
        img = Image.fromarray(noise, 'RGB')
        img.save(tmp_path, format='WEBP', quality=95)
        file_size = os.path.getsize(tmp_path)
        
        try:
            # Use a reasonable target size
            target = max(file_size // 2, 50000)
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size=target)
            self.assertTrue(was_compressed)
            os.unlink(result_path)
        finally:
            os.unlink(tmp_path)

    def test_bmp_input_format(self):
        """Test BMP input format is handled correctly."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bmp') as f:
            tmp_path = f.name
        
        # BMP is uncompressed, will be large
        img = Image.new('RGB', (500, 500), color='magenta')
        img.save(tmp_path, format='BMP')
        file_size = os.path.getsize(tmp_path)
        
        try:
            # BMP should compress very well to JPEG
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size=50000)
            self.assertTrue(was_compressed)
            self.assertLess(os.path.getsize(result_path), file_size)
            os.unlink(result_path)
        finally:
            os.unlink(tmp_path)

    def test_palette_mode_image(self):
        """Test palette mode (P) image with transparency."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            tmp_path = f.name
        
        # Create palette mode image
        img = Image.new('P', (500, 500))
        img.putpalette([i for i in range(256)] * 3)
        img.save(tmp_path, format='PNG')
        file_size = os.path.getsize(tmp_path)
        
        try:
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size=file_size - 100)
            if was_compressed:
                # Should be converted to RGB
                result_img = Image.open(result_path)
                self.assertEqual(result_img.mode, 'RGB')
                result_img.close()
                os.unlink(result_path)
        finally:
            os.unlink(tmp_path)

    def test_grayscale_image(self):
        """Test grayscale (L mode) image conversion."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            tmp_path = f.name
        
        img = Image.new('L', (500, 500), color=128)
        img.save(tmp_path, format='PNG')
        file_size = os.path.getsize(tmp_path)
        
        try:
            result_path, was_compressed = compress_image_to_size(tmp_path, max_size=file_size - 100)
            if was_compressed:
                result_img = Image.open(result_path)
                self.assertEqual(result_img.mode, 'RGB')
                result_img.close()
                os.unlink(result_path)
        finally:
            os.unlink(tmp_path)

    def test_impossible_compression_target(self):
        """Test that impossibly small target raises ConversionError."""
        import numpy as np
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as f:
            tmp_path = f.name
        
        # Create complex image that can't compress to 100 bytes
        noise = np.random.randint(0, 255, (1000, 1000, 3), dtype=np.uint8)
        img = Image.fromarray(noise, 'RGB')
        img.save(tmp_path, format='PNG')
        
        try:
            with self.assertRaises(ConversionError) as ctx:
                compress_image_to_size(tmp_path, max_size=100)  # 100 bytes impossible
            self.assertIn("Unable to compress", str(ctx.exception))
        finally:
            os.unlink(tmp_path)


if __name__ == '__main__':
    unittest.main()
