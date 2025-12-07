import os
import re
import time
import sys
import tempfile
import zipfile
import json
import hashlib
from typing import Optional, List, Dict
from .auth import TelegraphAuth
from .config import load_config
from .converter import MarkdownConverter
from .uploader import ImageUploader
from .utils import (
    natural_sort_key, safe_extract_zip, validate_file_size,
    MAX_TEXT_SIZE, MAX_IMAGES_PER_PAGE, MAX_IMAGE_SIZE,
    ALLOWED_TEXT_EXTENSIONS, ALLOWED_ARCHIVE_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS
)
from .exceptions import UploadError, ValidationError
from .interfaces import IPublisher

# Cache file for deduplication
CACHE_FILE = os.path.expanduser("~/.telepress_cache.json")

def _load_cache() -> Dict:
    """Load published content cache."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def _save_cache(cache: Dict):
    """Save published content cache."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except:
        pass

def _content_hash(content: str) -> str:
    """Generate hash for content deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


class TelegraphPublisher(IPublisher):
    """
    Main interface for publishing content to Telegraph.
    """
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    def __init__(
        self, 
        token: Optional[str] = None, 
        short_name: str = "TelegraphPublisher", 
        skip_duplicate: bool = True,
        image_size_limit: Optional[float] = None,
        auto_compress: bool = True
    ):
        self.auth = TelegraphAuth()
        self.client = self.auth.get_client(token, short_name)
        self.converter = MarkdownConverter()
        self.skip_duplicate = skip_duplicate
        self._cache = _load_cache() if skip_duplicate else {}
        self.auto_compress = auto_compress

        # Determine image size limit and max workers
        if image_size_limit is not None:
            self.max_image_size = int(image_size_limit * 1024 * 1024)
            max_workers = 4  # Default
        else:
            config = load_config()
            # Check config for limit (in MB)
            config_limit = config.get('image_host', {}).get('max_size_mb')
            if config_limit:
                 self.max_image_size = int(float(config_limit) * 1024 * 1024)
            else:
                 self.max_image_size = MAX_IMAGE_SIZE
            
            # Check config for max_workers
            config_workers = config.get('image_host', {}).get('max_workers')
            max_workers = int(config_workers) if config_workers else 4

        self.uploader = ImageUploader(max_workers=max_workers)

    def publish(self, file_path: str, title: Optional[str] = None) -> str:
        """
        Publishes a file (md, txt, image, zip) to Telegraph.
        
        Supported formats:
        - Text: .txt, .md, .markdown, .rst, .text
        - Images: .jpg, .jpeg, .png, .gif, .webp, .bmp
        - Archives: .zip (containing images)
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If file type not supported or file too large
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Safety check for huge files (2GB)
        validate_file_size(file_path, 2048 * 1024 * 1024, "File too large")

        file_name = os.path.basename(file_path)
        if not title:
            title = os.path.splitext(file_name)[0]
        ext = os.path.splitext(file_name)[1].lower()
        
        # Validate file type and route to appropriate handler
        if ext in ALLOWED_ARCHIVE_EXTENSIONS:
            return self.publish_zip_gallery(file_path, title)
        elif ext in self.IMAGE_EXTENSIONS:
            return self.publish_image(file_path, title)
        elif ext in ALLOWED_TEXT_EXTENSIONS:
            return self.publish_markdown(file_path, title)
        else:
            # Unsupported file type
            supported = sorted(ALLOWED_TEXT_EXTENSIONS | self.IMAGE_EXTENSIONS | ALLOWED_ARCHIVE_EXTENSIONS)
            raise ValidationError(
                f"Unsupported file type: '{ext}'. "
                f"Supported formats: {', '.join(supported)}"
            )

    def _link_pages(self, pages_info: List[Dict]):
        """
        Helper to add navigation links (Prev/Next/Index) to a list of pages.
        Robust: retries on failure, verifies links are correct.
        """
        total_parts = len(pages_info)
        if total_parts <= 1:
            return

        print(f"Linking {total_parts} pages...", end="", flush=True)
        failed_links = []
        
        for i, info in enumerate(pages_info):
            # Show progress every 10 pages
            if (i + 1) % 10 == 0:
                print(f" {i+1}", end="", flush=True)
            nav_nodes = []
            
            # 1. Navigation Links (Prev/Next) - only link to valid pages
            nav_links = []
            if i > 0:
                prev_url = pages_info[i-1]['url']
                nav_links.append({
                    'tag': 'a',
                    'attrs': {'href': prev_url},
                    'children': [f'◀ Previous / 上一页']
                })
                nav_links.append(" | ")
            
            if i < total_parts - 1:
                next_url = pages_info[i+1]['url']
                nav_links.append({
                    'tag': 'a',
                    'attrs': {'href': next_url},
                    'children': [f'Next / 下一页 ▶']
                })
            
            if nav_links:
                nav_nodes.append({'tag': 'p', 'children': nav_links})
            
            # 2. Pagination Index - only include successfully published pages
            page_index_nodes = ["Pages: "]
            
            if total_parts < 50:
                for p_idx, p_info in enumerate(pages_info):
                    label = str(p_info.get('part_num', p_idx + 1))
                    if p_idx == i:
                        page_index_nodes.append({'tag': 'b', 'children': [f"[{label}]"]})
                    else:
                        page_index_nodes.append({'tag': 'a', 'attrs': {'href': p_info['url']}, 'children': [f"[{label}]"]})
                    page_index_nodes.append(" ")
            else:
                page_index_nodes.append(f"{info.get('part_num', i+1)} / {total_parts}")

            nav_nodes.append({'tag': 'p', 'children': page_index_nodes})

            if nav_nodes:
                new_content = info['content'] + [{'tag': 'hr'}] + nav_nodes
                
                # Retry logic for linking
                max_retries = 3
                success = False
                for attempt in range(max_retries):
                    try:
                        self.client.edit_page(
                            path=info['path'],
                            title=info['title'],
                            content=new_content
                        )
                        success = True
                        break
                    except Exception as e:
                        error_msg = str(e)
                        match = re.search(r'Retry in (\d+)', error_msg)
                        if 'Flood control' in error_msg and match:
                            wait_time = int(match.group(1)) + 1
                            time.sleep(wait_time)
                        elif attempt < max_retries - 1:
                            time.sleep(1)
                        else:
                            failed_links.append(i + 1)
                            print(f"Warning: Failed to link Part {i+1}: {e}")
                
                if success and i < total_parts - 1:
                    time.sleep(0.3)  # Small delay between edits
        
        print()  # End the progress line
        if failed_links:
            print(f"Note: Navigation failed for parts: {failed_links}. Content is still accessible.")

    def publish_markdown(self, file_path: str, title: str) -> str:
        """
        Publish a markdown/text file to Telegraph.
        Large files are automatically split into multiple pages.
        
        Limits:
        - Maximum ~4 million characters (100 pages × 40000 chars)
        - Files exceeding this will be truncated with a warning
        """
        # Validate file can be read as text
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            raise ValidationError(
                f"Cannot read file as text. File may be binary (PDF, DOCX, etc.). "
                f"Only plain text files (.txt, .md) are supported."
            )
        
        # Check for empty content
        if not content.strip():
            raise ValidationError("File is empty or contains only whitespace")
        
        # Generate content key for deduplication
        content_key = _content_hash(content + title) if self.skip_duplicate else None
        
        # Check for duplicate content
        if content_key and content_key in self._cache:
            cached_url = self._cache[content_key]
            print(f"Skipping duplicate content, already published: {cached_url}")
            return cached_url
        
        # Split content if too large
        # Telegraph limit is ~64KB JSON. After markdown conversion, text expands.
        # Plain text with line breaks expands ~2x, so use 10KB to be safe.
        SAFE_CHUNK_SIZE = 10000 
        
        chunks = []
        if len(content) > SAFE_CHUNK_SIZE:
            print(f"Text too large ({len(content)} chars). Splitting...")
            current_chunk = []
            current_len = 0
            # Split by lines to preserve markdown structure
            for line in content.splitlines(keepends=True):
                # Handle very long lines by force-splitting
                while len(line) > SAFE_CHUNK_SIZE:
                    if current_chunk:
                        chunks.append("".join(current_chunk))
                        current_chunk = []
                        current_len = 0
                    # Split long line at chunk size
                    chunks.append(line[:SAFE_CHUNK_SIZE])
                    line = line[SAFE_CHUNK_SIZE:]
                
                if current_len + len(line) > SAFE_CHUNK_SIZE and current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                current_chunk.append(line)
                current_len += len(line)
            if current_chunk:
                chunks.append("".join(current_chunk))
        else:
            chunks = [content]

        total_parts = len(chunks)
        pages_info = []
        
        for i, chunk_text in enumerate(chunks):
            part_num = i + 1
            page_title = title
            if total_parts > 1:
                page_title = f"{title} ({part_num}/{total_parts})"
            
            print(f"Publishing Part {part_num}/{total_parts} ({len(chunk_text)} chars)...")
            nodes = self.converter.convert(chunk_text)
            
            # Retry with delay for flood control
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    response = self.client.create_page(title=page_title, content=nodes)
                    pages_info.append({
                        'path': response['path'],
                        'url': response['url'],
                        'title': page_title,
                        'content': nodes,
                        'part_num': part_num
                    })
                    # Small delay between requests to avoid flood control
                    if i < len(chunks) - 1:
                        time.sleep(0.5)
                    break
                except Exception as e:
                    error_msg = str(e)
                    # Check if max retries reached
                    if attempt >= max_retries - 1:
                        raise RuntimeError(
                            f"Failed to publish Part {part_num}/{total_parts} after {max_retries} attempts: {e}\n"
                            f"Successfully published: {len(pages_info)} pages. First page: {pages_info[0]['url'] if pages_info else 'none'}"
                        )
                    # Handle flood control - extract wait time
                    match = re.search(r'Retry in (\d+)', error_msg)
                    if 'Flood control' in error_msg and match:
                        wait_time = int(match.group(1)) + 1
                        print(f"  Waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        time.sleep(2)

        # Link pages if multiple
        self._link_pages(pages_info)

        result_url = pages_info[0]['url'] if pages_info else ""
        
        # Save to cache for deduplication
        if content_key and result_url:
            self._cache[content_key] = result_url
            _save_cache(self._cache)
        
        return result_url

    def publish_image(self, image_path: str, title: str) -> str:
        """Publish a single image to Telegraph."""
        url = self.uploader.upload(
            image_path,
            auto_compress=self.auto_compress,
            max_size=self.max_image_size
        )
        content = [{'tag': 'img', 'attrs': {'src': url}}]
        response = self.client.create_page(title=title, content=content)
        return response['url']

    def publish_text(self, content: str, title: str) -> str:
        """
        Publish text/markdown content directly to Telegraph.
        
        This is useful for programmatic publishing without creating a temp file.
        
        Args:
            content: Markdown or plain text content
            title: Page title
        
        Returns:
            str: URL of the published Telegraph page
        
        Example:
            >>> publisher = TelegraphPublisher()
            >>> url = publisher.publish_text("# Hello\n\nWorld!", title="Test")
        """
        import tempfile
        import os
        
        # Write content to temp file and use existing publish_markdown logic
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            tmp_path = f.name
        
        try:
            return self.publish_markdown(tmp_path, title)
        finally:
            os.unlink(tmp_path)

    def publish_zip_gallery(self, zip_path: str, title: str) -> str:
        """
        Publish a zip file containing images as a gallery.
        
        Limits:
        - Maximum 5000 images (50 pages × 100 images)
        - Images exceeding this will be truncated with a warning
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                safe_extract_zip(zip_path, temp_dir)
            except zipfile.BadZipFile:
                raise ValidationError("Invalid zip file")

            images = []
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    if os.path.splitext(file)[1].lower() in self.IMAGE_EXTENSIONS:
                        images.append(os.path.join(root, file))
            
            images.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
            
            if not images:
                raise ValidationError("No images found in zip file")
            
            # Pagination logic
            chunk_size = MAX_IMAGES_PER_PAGE
            chunks = [images[i:i + chunk_size] for i in range(0, len(images), chunk_size)]
            total_parts = len(chunks)
            
            if total_parts > 1:
                print(f"Gallery has {len(images)} images. Splitting into {total_parts} pages.")
            
            # Two-pass approach to support Prev/Next links
            # Pass 1: Create all pages
            pages_info = [] # Stores {'path': str, 'url': str, 'title': str, 'content': list}
            
            for i, chunk_images in enumerate(chunks):
                part_num = i + 1
                page_title = title
                if total_parts > 1:
                    page_title = f"{title} ({part_num}/{total_parts})"
                
                print(f"Uploading Part {part_num}/{total_parts} ({len(chunk_images)} images)...")
                
                # Use batch upload with progress bar
                def progress_callback(completed, total, result):
                    percent = (completed / total) * 100
                    bar_length = 30
                    filled_length = int(bar_length * completed // total)
                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                    sys.stdout.write(f'\rProgress: |{bar}| {percent:.1f}% ({completed}/{total})')
                    sys.stdout.flush()
                
                batch_result = self.uploader.upload_batch(
                    chunk_images,
                    auto_compress=self.auto_compress,
                    max_size=self.max_image_size,
                    progress_callback=progress_callback
                )
                print()  # Newline after progress bar
                
                url_map = batch_result.get_url_map()
                failed_paths = batch_result.get_failed_paths()
                
                if failed_paths:
                    print(f"Warning: {len(failed_paths)} images failed to upload.")
                    for p in failed_paths:
                         # Find the specific result for error message
                        err = next((r.error for r in batch_result.results if r.path == p), "Unknown error")
                        print(f"  - {os.path.basename(p)}: {err}")

                content = []
                for img_path in chunk_images:
                    if img_path in url_map:
                        content.append({'tag': 'img', 'attrs': {'src': url_map[img_path]}})
                
                if not content and len(chunk_images) > 0:
                     print(f"Warning: Part {part_num} resulted in empty content.")


                try:
                    # Create initial page
                    response = self.client.create_page(
                        title=page_title,
                        html_content=None,
                        content=content if content else [{'tag': 'p', 'children': ['(Empty Page)']}]
                    )
                    pages_info.append({
                        'path': response['path'],
                        'url': response['url'],
                        'title': page_title,
                        'content': content
                    })
                except Exception as e:
                    raise RuntimeError(f"Failed to publish Part {part_num}: {e}")

            # Pass 2: Update pages with navigation
            self._link_pages(pages_info)

            return pages_info[0]['url'] if pages_info else ""

    def publish_optimized_gallery(self, image_urls: List[str], title: str) -> str:
        """
        Publish a gallery using existing image URLs (no upload needed).
        Handles pagination and navigation linking automatically.
        """
        if not image_urls:
            raise ValidationError("No image URLs provided")
        
        # Pagination logic
        chunk_size = MAX_IMAGES_PER_PAGE
        chunks = [image_urls[i:i + chunk_size] for i in range(0, len(image_urls), chunk_size)]
        total_parts = len(chunks)
        
        if total_parts > 1:
            print(f"Gallery has {len(image_urls)} images. Splitting into {total_parts} pages.")
        
        # Two-pass approach to support Prev/Next links
        pages_info = [] 
        
        for i, chunk_urls in enumerate(chunks):
            part_num = i + 1
            page_title = title
            if total_parts > 1:
                page_title = f"{title} ({part_num}/{total_parts})"
            
            print(f"Creating Part {part_num}/{total_parts} ({len(chunk_urls)} images)...")
            
            content = []
            for url in chunk_urls:
                content.append({'tag': 'img', 'attrs': {'src': url}})
            
            try:
                # Create initial page
                response = self.client.create_page(
                    title=page_title,
                    html_content=None,
                    content=content if content else [{'tag': 'p', 'children': ['(Empty Page)']}]
                )
                pages_info.append({
                    'path': response['path'],
                    'url': response['url'],
                    'title': page_title,
                    'content': content
                })
            except Exception as e:
                raise RuntimeError(f"Failed to publish Part {part_num}: {e}")

        # Link pages
        self._link_pages(pages_info)

        return pages_info[0]['url'] if pages_info else ""
