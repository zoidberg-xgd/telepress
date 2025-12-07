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

class TextOptimizer:
    """
    Optimizes raw text content into Markdown, especially for Chinese novels.
    """
    
    # Regex for chapter titles
    # Matches: 第1章, 第一章, Chapter 1, 1., 1、, 卷一
    CHAPTER_PATTERNS = [
        r'^\s*第[0-9零一二三四五六七八九十百千]+[章卷节部篇].*',
        r'^\s*Chapter\s+\d+.*',
        r'^\s*(序|前言|楔子|尾声|后记).*',
        r'^\s*\d+\.\s+.*',  # 1. Title
        r'^\s*\d+、\s*.*',  # 1、Title
        r'^\s*卷[0-9零一二三四五六七八九十百千]+.*', # 卷一 Title
    ]
    
    @classmethod
    def process(cls, content: str) -> str:
        """Convert raw text to formatted Markdown."""
        lines = content.splitlines()
        output_lines = []
        
        for line in lines:
            # Handle full-width spaces and strip
            line = line.replace('\u3000', ' ').strip()
            
            if not line:
                continue
            
            # Check if line is a chapter title
            is_title = False
            for pattern in cls.CHAPTER_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    # Convert to H3 (Telegraph H3 is good for chapters)
                    # Telegraph support: H3, H4. H1/H2 are usually Title/Author.
                    output_lines.append(f"\n### {line}\n")
                    is_title = True
                    break
            
            if not is_title:
                # Regular paragraph
                output_lines.append(f"{line}")
        
        return "\n\n".join(output_lines)

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
            r'^\s*\|.+\|',     # Tables
        ]
        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False

    def convert(self, md_content: str) -> List[Dict]:
        """Converts Markdown content to Telegraph DOM nodes."""
        
        # Heuristic: If strict Markdown syntax is not detected, 
        # try to optimize it as a novel/article text.
        if not self._has_markdown_syntax(md_content):
            md_content = TextOptimizer.process(md_content)
        
        # Extension configuration
        extensions = [
            'fenced_code',
            'tables',
            'sane_lists',
            'nl2br'  # Convert newlines to br, but we usually want paragraphs
        ]
        
        html_content = markdown.markdown(md_content, extensions=extensions)
        
        # Pre-process HTML string for headers
        # Telegraph doesn't support h1/h2 mapping well (usually Title/Description)
        # Map h1->h3, h2->h4 to fit Telegraph style
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
