import re
import os
import io
import zipfile
import tempfile
from typing import List, Dict, Union, Optional, Tuple
from .exceptions import SecurityError, ValidationError, ConversionError

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Constants for limits
MAX_TEXT_SIZE = 60 * 1024  # ~60KB safe limit for text content per page
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB limit per image (Telegraph hard limit)
MAX_IMAGES_PER_PAGE = 100  # Images per page to avoid browser performance issues
# No artificial limits on pages/total images - let Telegraph's rate limiting handle it
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
ALLOWED_TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.rst', '.text'}
ALLOWED_ARCHIVE_EXTENSIONS = {'.zip'}

def natural_sort_key(s: str) -> List[Union[int, str]]:
    """
    Sorts strings containing numbers naturally.
    e.g. ['1.png', '10.png', '2.png'] -> ['1.png', '2.png', '10.png']
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def validate_file_size(path: str, max_size: int, error_msg: str):
    """Checks if file size is within limits."""
    if os.path.getsize(path) > max_size:
        raise ValidationError(f"{error_msg} (Size: {os.path.getsize(path)/1024/1024:.2f}MB, Max: {max_size/1024/1024}MB)")

def safe_extract_zip(zip_path: str, extract_to: str):
    """
    Safely extracts a zip file, preventing Zip Slip vulnerabilities.
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for member in zf.namelist():
            # Resolve the path to ensure it doesn't escape the target directory
            member_path = os.path.join(extract_to, member)
            abs_member_path = os.path.abspath(member_path)
            abs_target_path = os.path.abspath(extract_to)
            
            if not abs_member_path.startswith(abs_target_path):
                raise SecurityError(f"Zip Slip attempt detected: {member}")
            
            # Extract only if safe
            zf.extract(member, extract_to)

def sanitize_nodes(nodes: List[Dict]) -> List[Dict]:
    """
    Recursively downgrades headers h1->h3, h2->h4 because Telegraph
    only supports h3 and h4.
    """
    if not isinstance(nodes, list):
        return nodes
    
    for node in nodes:
        if isinstance(node, dict):
            tag = node.get('tag')
            if tag == 'h1':
                node['tag'] = 'h3'
            elif tag == 'h2':
                node['tag'] = 'h4'
            elif tag in ['h5', 'h6']:
                node['tag'] = 'h4'
            
            if 'children' in node:
                sanitize_nodes(node['children'])
    return nodes


# Formats that support compression
COMPRESSIBLE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}
SKIP_COMPRESSION_FORMATS = {'.gif'}  # Animated, complex to handle


def compress_image_to_size(
    image_path: str,
    max_size: int = MAX_IMAGE_SIZE,
    min_quality: int = 30,
    min_scale: float = 0.3,
    prefer_webp: bool = False
) -> Tuple[str, bool]:
    """
    Compress an image to fit within max_size bytes.
    
    Supports: JPEG, PNG, WebP, BMP, TIFF formats.
    
    Strategy (prioritizing quality):
    1. Try quality reduction (95 -> min_quality)
    2. If still too large, progressively scale down
    3. Uses JPEG output for best compression ratio (or WebP if prefer_webp=True)
    
    Args:
        image_path: Path to the source image
        max_size: Maximum file size in bytes (default: 5MB)
        min_quality: Minimum quality to try before scaling (default: 30)
        min_scale: Minimum scale factor before giving up (default: 0.3)
        prefer_webp: Use WebP output format instead of JPEG (default: False)
    
    Returns:
        Tuple of (output_path, was_compressed):
        - output_path: Path to the (possibly compressed) image
        - was_compressed: True if compression was applied
    
    Raises:
        ConversionError: If unable to compress to target size
        ValidationError: If Pillow is not available
    """
    if not PIL_AVAILABLE:
        raise ValidationError(
            "Pillow library is required for image compression. "
            "Install with: pip install Pillow"
        )
    
    file_size = os.path.getsize(image_path)
    if file_size <= max_size:
        return image_path, False
    
    ext = os.path.splitext(image_path)[1].lower()
    
    # GIF compression is complex (animated frames), skip
    if ext in SKIP_COMPRESSION_FORMATS:
        raise ConversionError(
            f"Cannot auto-compress {ext.upper()} files (may be animated). "
            f"File size: {file_size / 1024 / 1024:.2f}MB, max: {max_size / 1024 / 1024:.0f}MB"
        )
    
    # Output format
    out_format = 'WEBP' if prefer_webp else 'JPEG'
    out_ext = '.webp' if prefer_webp else '.jpg'
    
    img = None
    try:
        img = Image.open(image_path)
        
        # Convert to RGB for JPEG/WebP compatibility
        img = _convert_to_rgb(img)
        original_size = img.size
        
        # Phase 1: Try quality reduction only (faster, less memory)
        result = _try_quality_compression(img, max_size, min_quality, out_format)
        if result:
            return _save_compressed_image(result, out_ext)
        
        # Phase 2: Scale down progressively
        result = _try_scale_compression(
            img, original_size, max_size, min_quality, min_scale, out_format
        )
        if result:
            return _save_compressed_image(result, out_ext)
        
        raise ConversionError(
            f"Unable to compress image to under {max_size / 1024 / 1024:.0f}MB. "
            f"Original: {file_size / 1024 / 1024:.2f}MB, "
            f"dimensions: {original_size[0]}x{original_size[1]}"
        )
        
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError(f"Failed to compress image: {e}")
    finally:
        # Explicitly close to free memory
        if img:
            img.close()


def _convert_to_rgb(img: 'Image.Image') -> 'Image.Image':
    """Convert image to RGB mode for JPEG/WebP compatibility."""
    if img.mode == 'RGB':
        return img
    
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        # Has alpha channel - composite on white background
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode in ('RGBA', 'LA'):
            # Split and use alpha as mask
            if img.mode == 'LA':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
        return background
    
    return img.convert('RGB')


def _try_quality_compression(
    img: 'Image.Image',
    max_size: int,
    min_quality: int,
    out_format: str
) -> Optional[io.BytesIO]:
    """Try to compress by reducing quality only."""
    for quality in range(95, min_quality - 1, -5):
        buffer = io.BytesIO()
        img.save(buffer, format=out_format, quality=quality, optimize=True)
        if buffer.tell() <= max_size:
            return buffer
        buffer.close()  # Free memory
    return None


def _try_scale_compression(
    img: 'Image.Image',
    original_size: Tuple[int, int],
    max_size: int,
    min_quality: int,
    min_scale: float,
    out_format: str
) -> Optional[io.BytesIO]:
    """Try to compress by scaling down progressively."""
    scale = 0.9
    while scale >= min_scale:
        new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
        scaled_img = img.resize(new_size, Image.LANCZOS)
        
        try:
            for quality in range(85, min_quality - 1, -10):
                buffer = io.BytesIO()
                scaled_img.save(buffer, format=out_format, quality=quality, optimize=True)
                if buffer.tell() <= max_size:
                    return buffer
                buffer.close()
        finally:
            scaled_img.close()  # Free scaled image memory
        
        scale -= 0.1
    return None


def _save_compressed_image(buffer: io.BytesIO, suffix: str = '.jpg') -> Tuple[str, bool]:
    """Save compressed image buffer to a temp file and return path."""
    buffer.seek(0)
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(buffer.read())
        return temp_path, True
    except Exception:
        os.close(fd)
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
