from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class IPublisher(ABC):
    """
    Abstract Base Class defining the Publisher interface.
    This allows for different implementations (e.g. Telegraph, Medium, Ghost)
    to be interchangeable.
    """
    
    @abstractmethod
    def publish(self, source: Any, title: Optional[str] = None) -> str:
        """
        Publish content from the source.
        
        Args:
            source: The content to publish (file path, raw text, etc.)
            title: Optional title for the publication
            
        Returns:
            str: The URL of the published content
        """
        pass

class IConverter(ABC):
    """Interface for content converters (e.g. Markdown -> Node, RST -> Node)."""
    
    @abstractmethod
    def convert(self, content: str) -> Any:
        pass

class IUploader(ABC):
    """Interface for asset uploaders (e.g. Images)."""
    
    @abstractmethod
    def upload(self, source: Any) -> str:
        """Uploads the asset and returns a public URL."""
        pass
