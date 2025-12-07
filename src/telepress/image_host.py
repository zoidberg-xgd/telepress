"""
External Image Hosting Module

Supports multiple image hosting services as Telegraph's upload API is unavailable.
"""
import os
import base64
import requests
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from .exceptions import UploadError


class ImageHost(ABC):
    """Abstract base class for image hosting services."""
    
    @abstractmethod
    def upload(self, image_path: str) -> str:
        """Upload image and return URL."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return host name."""
        pass


class ImgbbHost(ImageHost):
    """imgbb.com image hosting (free, requires API key)."""
    
    API_URL = "https://api.imgbb.com/1/upload"
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("imgbb requires an API key. Get one at https://api.imgbb.com/")
        self.api_key = api_key
    
    @property
    def name(self) -> str:
        return "imgbb"
    
    def upload(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        response = requests.post(
            self.API_URL,
            data={
                'key': self.api_key,
                'image': image_data
            },
            timeout=60
        )
        
        if response.status_code != 200:
            raise UploadError(f"imgbb upload failed: {response.status_code} - {response.text[:100]}")
        
        data = response.json()
        if not data.get('success'):
            error = data.get('error', {}).get('message', 'Unknown error')
            raise UploadError(f"imgbb upload failed: {error}")
        
        return data['data']['url']


class ImgurHost(ImageHost):
    """imgur.com image hosting (requires Client ID)."""
    
    API_URL = "https://api.imgur.com/3/image"
    
    def __init__(self, client_id: str):
        if not client_id:
            raise ValueError("imgur requires a Client ID. Get one at https://api.imgur.com/oauth2/addclient")
        self.client_id = client_id
    
    @property
    def name(self) -> str:
        return "imgur"
    
    def upload(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        response = requests.post(
            self.API_URL,
            headers={'Authorization': f'Client-ID {self.client_id}'},
            data={'image': image_data, 'type': 'base64'},
            timeout=60
        )
        
        if response.status_code != 200:
            raise UploadError(f"imgur upload failed: {response.status_code} - {response.text[:100]}")
        
        data = response.json()
        if not data.get('success'):
            error = data.get('data', {}).get('error', 'Unknown error')
            raise UploadError(f"imgur upload failed: {error}")
        
        return data['data']['link']


class SmmsHost(ImageHost):
    """sm.ms image hosting (requires API token now)."""
    
    API_URL = "https://sm.ms/api/v2/upload"
    
    def __init__(self, api_token: str):
        if not api_token:
            raise ValueError("sm.ms now requires an API token. Get one at https://sm.ms/home/apitoken")
        self.api_token = api_token
    
    @property
    def name(self) -> str:
        return "smms"
    
    def upload(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        headers = {'Authorization': self.api_token}
        
        with open(image_path, 'rb') as f:
            response = requests.post(
                self.API_URL,
                headers=headers,
                files={'smfile': f},
                timeout=60
            )
        
        if response.status_code != 200:
            raise UploadError(f"sm.ms upload failed: {response.status_code}")
        
        data = response.json()
        if not data.get('success'):
            # sm.ms returns existing URL if image was uploaded before
            if data.get('code') == 'image_repeated':
                return data.get('images', data.get('data', {}).get('url', ''))
            error = data.get('message', 'Unknown error')
            raise UploadError(f"sm.ms upload failed: {error}")
        
        return data['data']['url']


class S3Host(ImageHost):
    """
    S3-compatible storage (AWS S3, Cloudflare R2, Aliyun OSS, MinIO, etc).
    
    Requires:
    - access_key_id: Access key ID
    - secret_access_key: Secret access key
    - bucket: Bucket name
    - public_url: Public URL prefix for the bucket
    - endpoint_url: Optional endpoint URL (required for non-AWS providers like R2/OSS/MinIO)
    - region_name: Optional region name (default: auto)
    """
    
    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        public_url: str,
        endpoint_url: Optional[str] = None,
        region_name: str = 'auto',
        account_id: Optional[str] = None  # Kept for R2 convenience
    ):
        if not all([access_key_id, secret_access_key, bucket, public_url]):
            raise ValueError(
                "S3 requires: access_key_id, secret_access_key, bucket, public_url"
            )
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket = bucket
        self.public_url = public_url.rstrip('/')
        self.endpoint_url = endpoint_url
        self.region_name = region_name
        self.account_id = account_id
        self._client = None
        
        # Auto-construct R2 endpoint if account_id provided but no endpoint
        if not self.endpoint_url and self.account_id:
            self.endpoint_url = f'https://{self.account_id}.r2.cloudflarestorage.com'
    
    @property
    def name(self) -> str:
        return "s3"
    
    def _get_client(self):
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError("boto3 is required for S3 support. Install with: pip install boto3")
            
            self._client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region_name
            )
        return self._client
    
    def upload(self, image_path: str) -> str:
        import os
        import uuid
        import mimetypes
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        ext = os.path.splitext(image_path)[1].lower() or '.jpg'
        filename = f"{uuid.uuid4().hex}{ext}"
        content_type = mimetypes.guess_type(image_path)[0] or 'image/jpeg'
        
        client = self._get_client()
        
        with open(image_path, 'rb') as f:
            client.upload_fileobj(
                f,
                self.bucket,
                filename,
                ExtraArgs={'ContentType': content_type}
            )
        
        return f"{self.public_url}/{filename}"


class R2Host(S3Host):
    """Cloudflare R2 image hosting (alias for S3Host with R2 defaults)."""
    
    @property
    def name(self) -> str:
        return "r2"


class CustomHost(ImageHost):
    """
    Custom HTTP-based image host for any API.
    
    Configure with:
    - upload_url: The upload endpoint URL
    - method: HTTP method (default: POST)
    - file_field: Form field name for the file (default: 'file')
    - headers: Optional headers dict
    - response_url_path: JSON path to URL in response (e.g., 'data.url' or 'url')
    - extra_data: Optional extra form data
    
    Example:
        CustomHost(
            upload_url='https://api.example.com/upload',
            headers={'Authorization': 'Bearer xxx'},
            response_url_path='data.url'
        )
    """
    
    def __init__(
        self,
        upload_url: str,
        method: str = 'POST',
        file_field: str = 'file',
        headers: Optional[Dict[str, str]] = None,
        response_url_path: str = 'url',
        extra_data: Optional[Dict[str, str]] = None
    ):
        if not upload_url:
            raise ValueError("upload_url is required for custom host")
        self.upload_url = upload_url
        self.method = method.upper()
        self.file_field = file_field
        self.headers = headers or {}
        self.response_url_path = response_url_path
        self.extra_data = extra_data or {}
    
    @property
    def name(self) -> str:
        return "custom"
    
    def _extract_url(self, data: Any, path: str) -> str:
        """Extract URL from response using dot-notation path."""
        parts = path.split('.')
        result = data
        for part in parts:
            if isinstance(result, dict):
                result = result.get(part)
            elif isinstance(result, list) and part.isdigit():
                result = result[int(part)]
            else:
                raise UploadError(f"Cannot extract '{path}' from response: {data}")
            if result is None:
                raise UploadError(f"Path '{path}' not found in response: {data}")
        return str(result)
    
    def upload(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        with open(image_path, 'rb') as f:
            files = {self.file_field: f}
            
            if self.method == 'POST':
                response = requests.post(
                    self.upload_url,
                    files=files,
                    data=self.extra_data,
                    headers=self.headers,
                    timeout=60
                )
            else:
                raise UploadError(f"Unsupported method: {self.method}")
        
        if response.status_code not in (200, 201):
            raise UploadError(f"Upload failed: {response.status_code} - {response.text[:200]}")
        
        try:
            data = response.json()
        except:
            raise UploadError(f"Invalid JSON response: {response.text[:200]}")
        
        return self._extract_url(data, self.response_url_path)


# Registry of available hosts
IMAGE_HOSTS = {
    'imgbb': ImgbbHost,
    'imgur': ImgurHost,
    'smms': SmmsHost,
    's3': S3Host,
    'r2': R2Host,
    'custom': CustomHost,
}


def create_image_host(host_name: str = None, **kwargs) -> ImageHost:
    """
    Create an image host instance.
    
    If no host_name is provided, loads from config file or environment.
    
    Args:
        host_name: Name of the host ('imgbb', 'imgur', 'smms', 's3', 'r2', 'custom')
                   If None, loads from ~/.telepress.json or TELEPRESS_* env vars
        **kwargs: Host-specific configuration (api_key, client_id, etc.)
    
    Returns:
        ImageHost instance
    
    Example:
        >>> host = create_image_host('imgbb', api_key='your_key')
        >>> host = create_image_host()  # Load from config
        >>> url = host.upload('image.jpg')
    """
    # Load from config if not specified
    if host_name is None:
        from .config import get_image_host_config
        config = get_image_host_config()
        if not config:
            raise ValueError(
                "No image host configured. Either:\n"
                "1. Pass host_name parameter: create_image_host('imgbb', api_key='xxx')\n"
                "2. Create ~/.telepress.json with image_host config\n"
                "3. Set TELEPRESS_IMAGE_HOST_TYPE and TELEPRESS_IMAGE_HOST_* env vars"
            )
        host_name = config.pop('type', None)
        if not host_name:
            raise ValueError("Config missing 'type' field for image_host")
        kwargs = {**config, **kwargs}  # kwargs override config
    if host_name not in IMAGE_HOSTS:
        available = ', '.join(IMAGE_HOSTS.keys())
        raise ValueError(f"Unknown image host: {host_name}. Available: {available}")
    
    return IMAGE_HOSTS[host_name](**kwargs)
