import re
from typing import List, Dict, Union
from .utils import sanitize_nodes
from .exceptions import DependencyError

try:
    import markdown
    from telegraph.utils import html_to_nodes
except ImportError:
    markdown = None
    html_to_nodes = None

class MarkdownConverter:
    def __init__(self):
        if markdown is None:
            raise DependencyError("markdown library is required")

    def _has_markdown_syntax(self, content: str) -> bool:
        """Check if content contains Markdown formatting."""
        patterns = [
            r'^#{1,6}\s',      # Headers
            r'\*\*.+\*\*',     # Bold
            r'\[.+\]\(.+\)',   # Links
            r'^\s*[-*+]\s',    # Unordered lists
            r'^\s*\d+\.\s',    # Ordered lists
            r'^>\s',           # Blockquotes
            r'```',            # Code blocks
        ]
        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def convert(self, md_content: str) -> List[Dict]:
        """Converts Markdown content to Telegraph DOM nodes."""
        # Pre-process: preserve line breaks for plain text
        # Convert single newlines to double newlines (paragraph breaks)
        if not self._has_markdown_syntax(md_content):
            # Plain text: treat each line as a paragraph
            md_content = re.sub(r'\n(?!\n)', '\n\n', md_content)
        
        html_content = markdown.markdown(md_content)
        
        # Pre-process HTML string for headers
        # Telegraph doesn't support h1/h2
        html_content = re.sub(r'<h1', '<h3', html_content)
        html_content = re.sub(r'</h1>', '</h3>', html_content)
        html_content = re.sub(r'<h2', '<h4', html_content)
        html_content = re.sub(r'</h2>', '</h4>', html_content)
        html_content = re.sub(r'<h[56]', '<h4', html_content)
        html_content = re.sub(r'</h[56]>', '</h4>', html_content)

        if html_to_nodes:
            nodes = html_to_nodes(html_content)
            return sanitize_nodes(nodes)
        else:
            return [{'tag': 'p', 'children': [md_content]}]
