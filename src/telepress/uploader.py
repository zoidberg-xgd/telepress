import os
import time
from typing import Optional
from .exceptions import UploadError, DependencyError
from .utils import validate_file_size, MAX_IMAGE_SIZE

try:
    from telegraph import upload_file
except ImportError:
    upload_file = None

class ImageUploader:
    def __init__(self):
        if upload_file is None:
            raise DependencyError("telegraph library is required")

    def upload(self, path: str, retries: int = 3) -> str:
        """
        Uploads an image to Telegraph and returns the URL.
        Includes validation and retries.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Image not found: {path}")
            
        validate_file_size(path, MAX_IMAGE_SIZE, "Image file too large")

        attempt = 0
        while attempt < retries:
            try:
                with open(path, 'rb') as f:
                    response = upload_file(f)
                
                if isinstance(response, list) and len(response) > 0 and 'src' in response[0]:
                    return "https://telegra.ph" + response[0]['src']
                
                # If response format is unexpected but no exception, maybe server issue
                raise UploadError(f"Invalid response from upload server: {response}")
                
            except Exception as e:
                attempt += 1
                if attempt >= retries:
                    raise UploadError(f"Failed to upload image {path} after {retries} attempts: {e}")
                time.sleep(1) # Wait before retry
