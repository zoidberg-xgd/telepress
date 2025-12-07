import re
import os
import zipfile
from typing import List, Dict, Union
from .exceptions import SecurityError, ValidationError

# Constants for limits
MAX_TEXT_SIZE = 60 * 1024  # ~60KB safe limit for text content
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB limit per image (Telegraph limit)
MAX_IMAGES_PER_PAGE = 100  # Avoid browser crashes
MAX_PAGES = 100  # Maximum pages to prevent excessive API calls
MAX_TOTAL_IMAGES = 5000  # Maximum images in a single gallery
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB max file size
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
