"""
Tests for TextOptimizer in converter module.
"""
import unittest
from telepress.converter import TextOptimizer

class TestTextOptimizer(unittest.TestCase):
    
    def test_chapter_detection_chinese(self):
        """Test detection of Chinese chapter titles."""
        content = """
        第1章 开始
        正文内容...
        
        第一千零一章 结束
        正文内容...
        """
        result = TextOptimizer.process(content)
        self.assertIn('### 第1章 开始', result)
        self.assertIn('### 第一千零一章 结束', result)

    def test_chapter_detection_english(self):
        """Test detection of English chapter titles."""
        content = """
        Chapter 1 Beginning
        Content...
        
        Chapter 100 End
        Content...
        """
        result = TextOptimizer.process(content)
        self.assertIn('### Chapter 1 Beginning', result)
        self.assertIn('### Chapter 100 End', result)

    def test_chapter_detection_numeric(self):
        """Test detection of numeric chapter titles."""
        content = """
        1. Start
        Content...
        
        2. End
        Content...
        """
        result = TextOptimizer.process(content)
        self.assertIn('### 1. Start', result)
        self.assertIn('### 2. End', result)

    def test_chapter_detection_keywords(self):
        """Test detection of special keywords."""
        content = """
        序言
        Content...
        
        尾声
        Content...
        """
        result = TextOptimizer.process(content)
        self.assertIn('### 序言', result)
        self.assertIn('### 尾声', result)

    def test_paragraph_formatting(self):
        """Test paragraph formatting."""
        content = """
        Line 1
        
        Line 2
            Line 3 with indent
        """
        result = TextOptimizer.process(content)
        # Should preserve lines but clean up formatting
        # TextOptimizer currently just joins with \n and adds formatting for chapters
        # It splits by lines and rejoins.
        self.assertIn('Line 1', result)
        self.assertIn('Line 2', result)
        self.assertIn('Line 3 with indent', result)

    def test_empty_lines_handling(self):
        """Test handling of empty lines."""
        content = """
        Line 1
        
        
        Line 2
        """
        result = TextOptimizer.process(content)
        # TextOptimizer strips empty lines in the loop `if not line: continue`
        # And joins paragraphs with double newlines
        self.assertIn('Line 1\n\nLine 2', result)

if __name__ == '__main__':
    unittest.main()
