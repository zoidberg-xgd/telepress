import os
import tempfile
import zipfile
from typing import Optional, List, Dict
from .auth import TelegraphAuth
from .converter import MarkdownConverter
from .uploader import ImageUploader
from .utils import (
    natural_sort_key, safe_extract_zip, validate_file_size,
    MAX_TEXT_SIZE, MAX_IMAGES_PER_PAGE, MAX_PAGES, MAX_TOTAL_IMAGES, MAX_FILE_SIZE,
    ALLOWED_TEXT_EXTENSIONS, ALLOWED_ARCHIVE_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS
)
from .exceptions import UploadError, ValidationError
from .interfaces import IPublisher

class TelegraphPublisher(IPublisher):
    """
    Main interface for publishing content to Telegraph.
    """
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    def __init__(self, token: Optional[str] = None, short_name: str = "TelegraphPublisher"):
        self.auth = TelegraphAuth()
        self.client = self.auth.get_client(token, short_name)
        self.converter = MarkdownConverter()
        self.uploader = ImageUploader()

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

        file_name = os.path.basename(file_path)
        if not title:
            title = os.path.splitext(file_name)[0]
        ext = os.path.splitext(file_name)[1].lower()
        
        # Validate file size
        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            raise ValidationError(
                f"File too large: {file_size / 1024 / 1024:.1f}MB. "
                f"Maximum allowed: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )
        
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
        """
        total_parts = len(pages_info)
        if total_parts <= 1:
            return

        print(f"Linking {total_parts} pages...")
        for i, info in enumerate(pages_info):
            nav_nodes = []
            
            # 1. Navigation Links (Prev/Next)
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
            
            # 2. Pagination Index (Page Numbers)
            # Limit index if too many pages to avoid hitting node limits on the index itself
            # Show: [1] ... [current-2] [current-1] [current] [current+1] [current+2] ... [last]
            page_index_nodes = ["Pages: "]
            
            # Simple full list for now, optimized for < 100 pages
            if total_parts < 50:
                for p_idx, p_info in enumerate(pages_info):
                    label = str(p_idx + 1)
                    if p_idx == i:
                        page_index_nodes.append({'tag': 'b', 'children': [f"[{label}]"]})
                    else:
                        page_index_nodes.append({'tag': 'a', 'attrs': {'href': p_info['url']}, 'children': [f"[{label}]"]})
                    page_index_nodes.append(" ")
            else:
                # Simplified index for very large sets
                page_index_nodes.append(f"{i+1} / {total_parts}")

            nav_nodes.append({'tag': 'p', 'children': page_index_nodes})

            if nav_nodes:
                new_content = info['content'] + [{'tag': 'hr'}] + nav_nodes
                try:
                    self.client.edit_page(
                        path=info['path'],
                        title=info['title'],
                        content=new_content
                    )
                except Exception as e:
                    print(f"Warning: Failed to add navigation to Part {i+1}: {e}")

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
        
        # Split content if too large
        # Telegraph safe limit is around 60KB JSON, so ~30-40KB text is safe.
        SAFE_CHUNK_SIZE = 40000 
        
        chunks = []
        if len(content) > SAFE_CHUNK_SIZE:
            print(f"Text too large ({len(content)} chars). Splitting...")
            current_chunk = []
            current_len = 0
            # Split by lines to preserve markdown structure somewhat
            for line in content.splitlines(keepends=True):
                if current_len + len(line) > SAFE_CHUNK_SIZE:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                current_chunk.append(line)
                current_len += len(line)
            if current_chunk:
                chunks.append("".join(current_chunk))
        else:
            chunks = [content]
        
        # Enforce page limit
        if len(chunks) > MAX_PAGES:
            original_count = len(chunks)
            chunks = chunks[:MAX_PAGES]
            print(f"Warning: Content truncated from {original_count} to {MAX_PAGES} pages (max limit).")

        total_parts = len(chunks)
        pages_info = []

        for i, chunk_text in enumerate(chunks):
            part_num = i + 1
            page_title = title
            if total_parts > 1:
                page_title = f"{title} ({part_num}/{total_parts})"
            
            print(f"Publishing Part {part_num}/{total_parts} ({len(chunk_text)} chars)...")
            nodes = self.converter.convert(chunk_text)
            
            try:
                response = self.client.create_page(title=page_title, content=nodes)
                pages_info.append({
                    'path': response['path'],
                    'url': response['url'],
                    'title': page_title,
                    'content': nodes
                })
            except Exception as e:
                 raise RuntimeError(f"Failed to publish Part {part_num}: {e}")

        # Link pages if multiple
        self._link_pages(pages_info)

        return pages_info[0]['url'] if pages_info else ""

    def publish_image(self, image_path: str, title: str) -> str:
        """Publish a single image to Telegraph."""
        url = self.uploader.upload(image_path)
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
            
            # Enforce image limit
            if len(images) > MAX_TOTAL_IMAGES:
                print(f"Warning: Gallery truncated from {len(images)} to {MAX_TOTAL_IMAGES} images (max limit).")
                images = images[:MAX_TOTAL_IMAGES]
            
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
                
                content = []
                for img_path in chunk_images:
                    try:
                        url = self.uploader.upload(img_path)
                        content.append({'tag': 'img', 'attrs': {'src': url}})
                    except UploadError as e:
                        print(f"Warning: Failed to upload {os.path.basename(img_path)}: {e}")
                
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
