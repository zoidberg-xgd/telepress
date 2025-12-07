"""
TelePress - Publish content to Telegraph easily.

Basic usage:
    >>> from telepress import publish, TelegraphPublisher
    >>> 
    >>> # Quick publish (one-liner)
    >>> url = publish("article.md", title="My Article")
    >>> 
    >>> # Or use the class for more control
    >>> publisher = TelegraphPublisher()
    >>> url = publisher.publish("article.md")
    >>> url = publisher.publish_text("# Hello\n\nWorld!", title="Test")
"""

from .core import TelegraphPublisher
from .exceptions import (
    TelePressError,
    ValidationError,
    UploadError,
    AuthenticationError,
    SecurityError,
    DependencyError,
    ConversionError
)
from .utils import (
    MAX_FILE_SIZE,
    MAX_PAGES,
    MAX_TOTAL_IMAGES,
    MAX_IMAGES_PER_PAGE,
    ALLOWED_TEXT_EXTENSIONS,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_ARCHIVE_EXTENSIONS
)

__version__ = "0.1.0"
__all__ = [
    # Main class
    'TelegraphPublisher',
    
    # Convenience function
    'publish',
    'publish_text',
    
    # Exceptions
    'TelePressError',
    'ValidationError', 
    'UploadError',
    'AuthenticationError',
    'SecurityError',
    'DependencyError',
    'ConversionError',
    
    # Constants
    'MAX_FILE_SIZE',
    'MAX_PAGES',
    'MAX_TOTAL_IMAGES',
    'MAX_IMAGES_PER_PAGE',
    'ALLOWED_TEXT_EXTENSIONS',
    'ALLOWED_IMAGE_EXTENSIONS',
    'ALLOWED_ARCHIVE_EXTENSIONS',
]

# Singleton publisher for convenience functions
_default_publisher = None

def _get_publisher(token=None):
    """Get or create default publisher instance."""
    global _default_publisher
    if token:
        return TelegraphPublisher(token=token)
    if _default_publisher is None:
        _default_publisher = TelegraphPublisher()
    return _default_publisher


def publish(file_path: str, title: str = None, token: str = None) -> str:
    """
    Convenience function to publish a file to Telegraph.
    
    Args:
        file_path: Path to file (.md, .txt, .jpg, .png, .zip, etc.)
        title: Optional title (defaults to filename)
        token: Optional Telegraph token (uses cached token if not provided)
    
    Returns:
        str: URL of the published Telegraph page
    
    Example:
        >>> from telepress import publish
        >>> url = publish("article.md", title="My Article")
        >>> print(url)
        https://telegra.ph/My-Article-12-07
    """
    return _get_publisher(token).publish(file_path, title=title)


def publish_text(content: str, title: str, token: str = None) -> str:
    """
    Convenience function to publish text content directly to Telegraph.
    
    Args:
        content: Markdown or plain text content
        title: Page title (required)
        token: Optional Telegraph token
    
    Returns:
        str: URL of the published Telegraph page
    
    Example:
        >>> from telepress import publish_text
        >>> url = publish_text("# Hello\n\nThis is my article.", title="Hello World")
        >>> print(url)
        https://telegra.ph/Hello-World-12-07
    """
    return _get_publisher(token).publish_text(content, title=title)
