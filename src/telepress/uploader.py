"""
Image Uploader Module (DEPRECATED)

Note: Telegraph's /upload API is currently returning "Unknown error" for all uploads.
This module is kept for reference but image upload functionality is not available.
Use external image hosting services instead.
"""
import os
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Callable, Any
from dataclasses import dataclass, field
from .exceptions import UploadError, DependencyError
from .utils import validate_file_size, compress_image_to_size, MAX_IMAGE_SIZE

# Telegraph upload API is currently broken
_UPLOAD_DISABLED = True
_UPLOAD_ERROR_MSG = (
    "Telegraph image upload is currently unavailable (API returns 'Unknown error'). "
    "Please use external image hosting services (e.g., imgbb.com, imgur.com) "
    "and paste image URLs into your Telegraph article."
)

try:
    from telegraph import upload_file
except ImportError:
    upload_file = None


@dataclass
class UploadResult:
    """Result of a single upload operation."""
    path: str
    url: Optional[str] = None
    error: Optional[str] = None
    success: bool = False
    compressed: bool = False
    attempts: int = 0


@dataclass 
class BatchUploadResult:
    """Result of a batch upload operation."""
    total: int = 0
    successful: int = 0
    failed: int = 0
    results: List[UploadResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        return self.successful / self.total if self.total > 0 else 0.0
    
    def get_failed_paths(self) -> List[str]:
        """Get list of paths that failed to upload."""
        return [r.path for r in self.results if not r.success]
    
    def get_url_map(self) -> Dict[str, str]:
        """Get mapping of original path -> uploaded URL."""
        return {r.path: r.url for r in self.results if r.success and r.url}


class ImageUploader:
    """Thread-safe image uploader with compression, retry and batch support."""
    
    # Supported formats for compression
    COMPRESSIBLE_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'}
    # GIF needs special handling (animated)
    SKIP_COMPRESSION_FORMATS = {'.gif'}
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize uploader.
        
        Args:
            max_workers: Maximum concurrent uploads for batch operations (default: 4)
        """
        if upload_file is None:
            raise DependencyError("telegraph library is required")
        self.max_workers = max_workers

    def upload(
        self, 
        path: str, 
        retries: int = 3, 
        auto_compress: bool = True,
        retry_delay: float = 1.0,
        max_retry_delay: float = 30.0
    ) -> str:
        """
        Upload a single image to Telegraph with auto-compression and retry.
        
        Args:
            path: Path to the image file
            retries: Number of retry attempts (default: 3)
            auto_compress: Auto-compress images over 5MB (default: True)
            retry_delay: Initial delay between retries in seconds (default: 1.0)
            max_retry_delay: Maximum retry delay with exponential backoff (default: 30.0)
        
        Returns:
            str: Telegraph URL of the uploaded image
        
        Raises:
            FileNotFoundError: If file doesn't exist
            UploadError: If upload fails after all retries
        
        Note:
            Telegraph upload API is currently broken. This method will raise UploadError.
        """
        if _UPLOAD_DISABLED:
            raise UploadError(_UPLOAD_ERROR_MSG)
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Image not found: {path}")
        
        upload_path = path
        compressed = False
        
        try:
            if auto_compress:
                upload_path, compressed = compress_image_to_size(path, MAX_IMAGE_SIZE)
            else:
                validate_file_size(path, MAX_IMAGE_SIZE, "Image file too large")

            return self._upload_with_retry(
                upload_path, path, retries, retry_delay, max_retry_delay
            )
        finally:
            # Clean up temp file if we compressed
            if compressed and upload_path != path and os.path.exists(upload_path):
                try:
                    os.unlink(upload_path)
                except OSError:
                    pass
    
    def _upload_with_retry(
        self,
        upload_path: str,
        original_path: str,
        retries: int,
        retry_delay: float,
        max_retry_delay: float
    ) -> str:
        """Upload with exponential backoff retry."""
        last_error = None
        delay = retry_delay
        
        for attempt in range(retries):
            try:
                with open(upload_path, 'rb') as f:
                    response = upload_file(f)
                
                if isinstance(response, list) and len(response) > 0 and 'src' in response[0]:
                    return "https://telegra.ph" + response[0]['src']
                
                raise UploadError(f"Invalid response: {response}")
                
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    # Exponential backoff with jitter
                    jitter = random.uniform(0, 0.1 * delay)
                    time.sleep(min(delay + jitter, max_retry_delay))
                    delay *= 2
        
        raise UploadError(
            f"Failed to upload {original_path} after {retries} attempts: {last_error}"
        )
    
    def upload_safe(
        self,
        path: str,
        retries: int = 3,
        auto_compress: bool = True
    ) -> UploadResult:
        """
        Upload without raising exceptions. Returns UploadResult with status.
        
        Useful for batch operations where you don't want one failure to stop everything.
        """
        result = UploadResult(path=path)
        try:
            result.url = self.upload(path, retries=retries, auto_compress=auto_compress)
            result.success = True
            result.compressed = os.path.getsize(path) > MAX_IMAGE_SIZE
        except Exception as e:
            result.error = str(e)
            result.success = False
        return result
    
    def upload_batch(
        self,
        paths: List[str],
        retries: int = 3,
        auto_compress: bool = True,
        max_workers: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, UploadResult], Any]] = None,
        stop_on_error: bool = False
    ) -> BatchUploadResult:
        """
        Upload multiple images concurrently with thread pool.
        
        Args:
            paths: List of image file paths to upload
            retries: Number of retry attempts per image (default: 3)
            auto_compress: Auto-compress large images (default: True)
            max_workers: Override max concurrent workers (default: use instance setting)
            progress_callback: Called after each upload with (completed, total, result)
            stop_on_error: Stop batch on first error (default: False)
        
        Returns:
            BatchUploadResult with all results and statistics
        
        Example:
            >>> uploader = ImageUploader(max_workers=4)
            >>> def on_progress(done, total, result):
            ...     print(f"[{done}/{total}] {result.path}: {'OK' if result.success else result.error}")
            >>> results = uploader.upload_batch(image_paths, progress_callback=on_progress)
            >>> print(f"Success rate: {results.success_rate:.1%}")
        """
        workers = max_workers or self.max_workers
        batch_result = BatchUploadResult(total=len(paths))
        
        if not paths:
            return batch_result
        
        completed = 0
        should_stop = False
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(
                    self.upload_safe, path, retries, auto_compress
                ): path for path in paths
            }
            
            # Process results as they complete
            for future in as_completed(future_to_path):
                if should_stop:
                    future.cancel()
                    continue
                    
                result = future.result()
                batch_result.results.append(result)
                
                if result.success:
                    batch_result.successful += 1
                else:
                    batch_result.failed += 1
                    if stop_on_error:
                        should_stop = True
                
                completed += 1
                
                if progress_callback:
                    try:
                        progress_callback(completed, len(paths), result)
                    except Exception:
                        pass  # Don't let callback errors break upload
        
        return batch_result
    
    def retry_failed(
        self,
        batch_result: BatchUploadResult,
        retries: int = 3,
        auto_compress: bool = True,
        progress_callback: Optional[Callable[[int, int, UploadResult], Any]] = None
    ) -> BatchUploadResult:
        """
        Retry only the failed uploads from a previous batch.
        
        Useful for resuming interrupted uploads.
        
        Args:
            batch_result: Previous BatchUploadResult with failures
            retries: Number of retry attempts (default: 3)
            auto_compress: Auto-compress large images (default: True)
            progress_callback: Progress callback function
        
        Returns:
            BatchUploadResult for the retry attempt
        """
        failed_paths = batch_result.get_failed_paths()
        if not failed_paths:
            return BatchUploadResult()  # Nothing to retry
        
        return self.upload_batch(
            failed_paths,
            retries=retries,
            auto_compress=auto_compress,
            progress_callback=progress_callback
        )
