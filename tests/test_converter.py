import unittest
from unittest.mock import patch
from telepress.converter import MarkdownConverter
from telepress.exceptions import DependencyError


class TestConverter(unittest.TestCase):
    def setUp(self):
        self.converter = MarkdownConverter()

    def test_convert_simple_text(self):
        """Test converting plain text to paragraph."""
        content = "Hello World"
        nodes = self.converter.convert(content)
        self.assertEqual(nodes[0]['tag'], 'p')
        self.assertEqual(nodes[0]['children'][0], 'Hello World')

    def test_header_downgrade_h1_to_h3(self):
        """Test that H1 is downgraded to H3."""
        content = "# H1 Title"
        nodes = self.converter.convert(content)
        elements = [n for n in nodes if isinstance(n, dict)]
        self.assertEqual(elements[0]['tag'], 'h3')

    def test_header_downgrade_h2_to_h4(self):
        """Test that H2 is downgraded to H4."""
        content = "## H2 Title"
        nodes = self.converter.convert(content)
        elements = [n for n in nodes if isinstance(n, dict)]
        self.assertEqual(elements[0]['tag'], 'h4')

    def test_header_downgrade_h5_h6_to_h4(self):
        """Test that H5 and H6 are downgraded to H4."""
        content = "##### H5 Title\n###### H6 Title"
        nodes = self.converter.convert(content)
        elements = [n for n in nodes if isinstance(n, dict)]
        self.assertTrue(all(el['tag'] == 'h4' for el in elements))

    def test_h3_h4_unchanged(self):
        """Test that H3 and H4 remain unchanged."""
        content = "### H3 Title\n#### H4 Title"
        nodes = self.converter.convert(content)
        elements = [n for n in nodes if isinstance(n, dict)]
        tags = [el['tag'] for el in elements]
        self.assertIn('h3', tags)
        self.assertIn('h4', tags)

    def test_list_conversion_unordered(self):
        """Test converting unordered list."""
        content = "- Item 1\n- Item 2\n- Item 3"
        nodes = self.converter.convert(content)
        ul = nodes[0]
        self.assertEqual(ul['tag'], 'ul')
        items = [n for n in ul['children'] if isinstance(n, dict) and n.get('tag') == 'li']
        self.assertEqual(len(items), 3)

    def test_list_conversion_ordered(self):
        """Test converting ordered list."""
        content = "1. First\n2. Second\n3. Third"
        nodes = self.converter.convert(content)
        ol = nodes[0]
        self.assertEqual(ol['tag'], 'ol')
        items = [n for n in ol['children'] if isinstance(n, dict) and n.get('tag') == 'li']
        self.assertEqual(len(items), 3)

    def test_bold_text(self):
        """Test bold text conversion."""
        content = "**bold text**"
        nodes = self.converter.convert(content)
        # Should contain strong tag somewhere in the tree
        self._assert_tag_exists(nodes, 'strong')

    def test_italic_text(self):
        """Test italic text conversion."""
        content = "*italic text*"
        nodes = self.converter.convert(content)
        self._assert_tag_exists(nodes, 'em')

    def test_link_conversion(self):
        """Test link conversion."""
        content = "[Link Text](https://example.com)"
        nodes = self.converter.convert(content)
        self._assert_tag_exists(nodes, 'a')

    def test_code_inline(self):
        """Test inline code conversion."""
        content = "Use `code` here"
        nodes = self.converter.convert(content)
        self._assert_tag_exists(nodes, 'code')

    def test_code_block(self):
        """Test code block conversion."""
        content = "```\nprint('hello')\n```"
        nodes = self.converter.convert(content)
        # Code blocks may be converted to 'pre' or 'code' depending on markdown implementation
        has_code = self._find_tag(nodes, 'pre') or self._find_tag(nodes, 'code')
        self.assertTrue(has_code, "Code block should contain 'pre' or 'code' tag")

    def test_blockquote(self):
        """Test blockquote conversion."""
        content = "> This is a quote"
        nodes = self.converter.convert(content)
        self._assert_tag_exists(nodes, 'blockquote')

    def test_horizontal_rule(self):
        """Test horizontal rule conversion."""
        content = "---"
        nodes = self.converter.convert(content)
        self._assert_tag_exists(nodes, 'hr')

    def test_empty_content(self):
        """Test empty content returns empty or minimal nodes."""
        content = ""
        nodes = self.converter.convert(content)
        self.assertIsInstance(nodes, list)

    def test_whitespace_only_content(self):
        """Test whitespace-only content."""
        content = "   \n\n   "
        nodes = self.converter.convert(content)
        self.assertIsInstance(nodes, list)

    def test_special_characters(self):
        """Test content with special characters."""
        content = "Special chars: <>&\"'"
        nodes = self.converter.convert(content)
        self.assertIsInstance(nodes, list)
        self.assertTrue(len(nodes) > 0)

    def test_unicode_content(self):
        """Test content with unicode characters."""
        content = "中文内容 日本語 한국어 🎉"
        nodes = self.converter.convert(content)
        self.assertEqual(nodes[0]['tag'], 'p')

    def test_nested_formatting(self):
        """Test nested formatting like bold italic."""
        content = "***bold and italic***"
        nodes = self.converter.convert(content)
        # Should have both strong and em
        self._assert_tag_exists(nodes, 'strong')

    def test_multiple_paragraphs(self):
        """Test multiple paragraphs separated by blank lines."""
        content = "Paragraph 1\n\nParagraph 2\n\nParagraph 3"
        nodes = self.converter.convert(content)
        p_tags = [n for n in nodes if isinstance(n, dict) and n.get('tag') == 'p']
        self.assertEqual(len(p_tags), 3)

    def _find_tag(self, nodes, tag_name):
        """Helper to recursively check if a tag exists in nodes."""
        def find_tag(items):
            for item in items:
                if isinstance(item, dict):
                    if item.get('tag') == tag_name:
                        return True
                    if 'children' in item:
                        if find_tag(item['children']):
                            return True
            return False
        return find_tag(nodes)

    def _assert_tag_exists(self, nodes, tag_name):
        """Assert that a tag exists in nodes."""
        self.assertTrue(self._find_tag(nodes, tag_name), f"Tag '{tag_name}' not found in nodes")


class TestConverterDependency(unittest.TestCase):
    @patch('telepress.converter.markdown', None)
    def test_missing_markdown_raises_dependency_error(self):
        """Test that missing markdown library raises DependencyError."""
        with self.assertRaises(DependencyError):
            MarkdownConverter()


if __name__ == '__main__':
    unittest.main()
