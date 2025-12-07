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

    def convert(self, md_content: str) -> List[Dict]:
        """Converts Markdown content to Telegraph DOM nodes."""
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
            # Fallback (though utils should be present if telegraph is installed)
            return [{'tag': 'p', 'children': [md_content]}]
