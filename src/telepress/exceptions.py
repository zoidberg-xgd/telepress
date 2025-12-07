class TelePressError(Exception):
    """Base exception for TelePress."""
    pass

class DependencyError(TelePressError):
    """Raised when required dependencies are missing."""
    pass

class AuthenticationError(TelePressError):
    """Raised when authentication fails."""
    pass

class ConversionError(TelePressError):
    """Raised when file conversion fails."""
    pass

class UploadError(TelePressError):
    """Raised when file upload fails."""
    pass

class SecurityError(TelePressError):
    """Raised when a security violation is detected (e.g. Zip Slip, huge file)."""
    pass

class ValidationError(TelePressError):
    """Raised when input data validation fails (e.g. invalid format, limits exceeded)."""
    pass
